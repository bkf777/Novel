#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 U01／U02 的内容源回填到「黄金 3 秒」补位批次之后的现盘（U03 已单独完成）。

背景（2026-10-23 11:17–11:19 实测取证，见台账 §176）：
  总控「黄金 3 秒」补位批次备份 `_bak_golden3s_u01_20261023-111728/`（11:17:28）与
  `_bak_golden3s_u02u03_20261023-111850/`（11:18:50），并于 11:19 重写本岗三个单元的
  D08／D09（U01 v1.10→v1.11 / v1.6→v1.7；U02 v1.4→v1.5 / v1.2→v1.3）。批次做两件事：
    ① 各集正文的 `compliance_added` 段整体移出正文，逐条改写入 `compliance_notes`
       （每集追加「【合规交付 · 已从正文移出】」×合规段数 ＋「合规交付口径」×1）；
    ② 「首句台词前移至开场位」：台词不足 3 条的集在开场位补一句新台词
       （U01 ep003／U02 ep012／U02 ep016），其余集台词条数与顺序不变；
       另 U01 ep003 有一处动作行改写。
  **该批次只写了 JSON，没同步本岗内容源** ⇒ 内容源落后现盘一版，重跑会回退批次改动。
  本脚本把内容源补齐到现盘；U03 由 `patch_u03_content_sync_v12.py` 单独处理（已落盘）。

附带（U01 专属）：`build_D08_U01.py`／`build_D09_U01.py` **无版本守卫**（硬编码版本直接写盘），
  跑一次就会静默降级回退 ⇒ 本脚本为二者补上 Q64 守卫（磁盘 version 高于脚本 ⇒ exit 1 拒写，
  正常升版与幂等重跑放行，`--force` 逃生口）。

用法：python3 resync_content_sources_u01u02.py [--dry-run] [--apply]
"""
import argparse
import difflib
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REPORTS = os.path.join(PROJ, "reports")

UNITS = {
    "U01": {
        "style": "call",
        "d08_file": "build_D08_U01.py",
        "d09_file": "build_D09_U01.py",
        "bak_dir": "_bak_golden3s_u01_20261023-111728",
        "bak_d08": "D08.json",
        "bak_d09": "D09.json",
        "cur_d08": "v1.11",
        "cur_d09": "v1.7",
        "old_d08": "v1.10",
        "old_d09": "v1.6",
        "ep_pat": re.compile(r"^#\s*[─━]+\s*EP(\d+)", re.M),
    },
    "U02": {
        "style": "dict",
        "d08_file": "d08_content_U02.py",
        "d09_file": "d09_content_U02.py",
        "bak_dir": "_bak_golden3s_u02u03_20261023-111850",
        "bak_d08": "U02_D08.json",
        "bak_d09": "U02_D09.json",
        "cur_d08": "v1.5",
        "cur_d09": "v1.3",
        "old_d08": "v1.4",
        "old_d09": "v1.2",
        "ep_pat": re.compile(r"^[ \t]*#[ \t]*[═]+\s*ep0*(\d+)", re.M),
    },
}

AI_MARK_TEXT = "画面右下角常驻白色角标：AI 生成。"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def pyq(s):
    """Python 双引号字面量（中文原样保留）。"""
    return json.dumps(s, ensure_ascii=False)


# ────────────────────────── 源码结构定位 ──────────────────────────
def ep_regions(src, pat):
    """返回 [(ep, start, end)]，end 为下一集起点（末段到文件尾）。"""
    ms = list(pat.finditer(src))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(src)
        out.append((int(m.group(1)), m.start(), end))
    return out


def body_span(src, ep_start, ep_end):
    """定位 ep 块内 "body": [ ... ] 的字符区间（返回 (list_start, list_end)）。"""
    i = src.index('"body": [', ep_start)
    if i > ep_end:
        raise RuntimeError("body 起始越界")
    j = i + len('"body": [')
    depth = 1
    k = j
    in_str = False
    quote = ""
    while k < ep_end:
        ch = src[k]
        if in_str:
            if ch == "\\":
                k += 2
                continue
            if ch == quote:
                in_str = False
        elif ch in "\"'":
            in_str = True
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                return j, k
        k += 1
    raise RuntimeError("body 结束未找到")


def entry_spans(src, ls, le, style):
    """在 body 列表区间内切出每条 entry 的字符区间。"""
    spans = []
    k = ls
    if style == "call":
        call_re = re.compile(r"^([ \t]*)(A|S|D|T)\(", re.M)
        while k < le:
            m = call_re.search(src, k, le)
            if not m:
                break
            # 单行条目：A("..."),   多行条目：... 至以 ), 结尾的行
            eol = src.index("\n", m.start())
            line = src[m.start():eol]
            if line.rstrip().endswith("),"):
                end = eol
            else:
                # 跨行：找到第一个以 ), 结尾的行
                p = eol + 1
                while p < le:
                    e2 = src.index("\n", p)
                    if src[p:e2].rstrip().endswith("),"):
                        end = e2
                        break
                    p = e2 + 1
                else:
                    raise RuntimeError("跨行条目未闭合")
            spans.append((m.start(), end + 1))
            k = end + 1
        # AI_MARK 单独条目
        k = ls
        while True:
            i = src.find("AI_MARK,", k, le)
            if i < 0:
                break
            # 不在调用括号内
            if not src[max(ls, i - 40):i].rstrip().endswith("("):
                line_start = src.rfind("\n", ls, i) + 1
                spans.append((line_start, i + len("AI_MARK,")))
            k = i + 1
        spans.sort()
    else:
        while k < le:
            i = src.find("{", k, le)
            if i < 0:
                break
            # 必须是行首的 "            {"
            line_start = src.rfind("\n", ls, i) + 1
            if src[line_start:i].strip():
                k = i + 1
                continue
            depth = 1
            p = i + 1
            in_str = False
            quote = ""
            while p < le:
                ch = src[p]
                if in_str:
                    if ch == "\\":
                        p += 2
                        continue
                    if ch == quote:
                        in_str = False
                elif ch in "\"'":
                    in_str = True
                    quote = ch
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
                    if depth == 0:
                        break
                p += 1
            # 结束处到该行末尾（含逗号）
            eol = src.find("\n", p)
            spans.append((line_start, eol + 1))
            k = eol + 1
        # AI_MARK 独立行（引用式常量条目）
        k = ls
        while True:
            i = src.find("AI_MARK,", k, le)
            if i < 0:
                break
            if not src[max(ls, i - 40):i].rstrip().endswith("("):
                line_start = src.rfind("\n", ls, i) + 1
                spans.append((line_start, i + len("AI_MARK,")))
            k = i + 1
        spans.sort()
    return spans


def emit_entry(e, style):
    """按单元风格生成 entry 字面量。"""
    if style == "call":
        t = e["type"]
        fn = {"action": "A", "sfx": "S", "dialogue": "D", "subtitle": "T"}[t]
        if t == "dialogue":
            core = f'{fn}({pyq(e["char_id"])}, {pyq(e["text"])}, {pyq(e.get("emotion", ""))}'
        else:
            core = f'{fn}({pyq(e["text"])}'
        extra = []
        if e.get("shot_intent"):
            extra.append(f'shot_intent={pyq(e["shot_intent"])}')
        if e.get("sfx"):
            extra.append(f'sfx={pyq(e["sfx"])}')
        if extra:
            core += ", " + ", ".join(extra)
        return core + "),\n"
    lines = ["            {", f'                "type": {pyq(e["type"])},']
    if e.get("char_id"):
        lines.append(f'                "char_id": {pyq(e["char_id"])},')
    lines.append(f'                "text": {pyq(e["text"])},')
    if e.get("emotion"):
        lines.append(f'                "emotion": {pyq(e["emotion"])},')
    if e.get("sfx"):
        lines.append(f'                "sfx": {pyq(e["sfx"])},')
    if e.get("shot_intent"):
        lines.append(f'                "shot_intent": {pyq(e["shot_intent"])},')
    lines.append("            },")
    return "\n".join(lines) + "\n"


# ────────────────────────── 差异对齐 ──────────────────────────
def align(bak_body, disk_body):
    """返回 (removals, additions, replacements)；元素为 (index, entry)。"""
    bk = [e.get("text", "") for e in bak_body]
    dk = [e.get("text", "") for e in disk_body]
    sm = difflib.SequenceMatcher(a=bk, b=dk, autojunk=False)
    removals, additions, replacements = [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        old = bak_body[i1:i2]
        new = disk_body[j1:j2]
        n = min(len(old), len(new))
        for k in range(n):
            if old[k].get("text") != new[k].get("text"):
                replacements.append((i1 + k, old[k], new[k]))
        for k in range(n, len(old)):
            removals.append((i1 + k, old[k]))
        for k in range(n, len(new)):
            additions.append((j1 + k, new[k]))
    return removals, additions, replacements


def plan_unit(unit):
    cfg = UNITS[unit]
    bak_d08 = json.load(open(os.path.join(REPORTS, cfg["bak_dir"], cfg["bak_d08"]), encoding="utf-8"))
    disk_d08 = json.load(open(os.path.join(PROJ, "units", unit, "D08.json"), encoding="utf-8"))
    bak_d09 = json.load(open(os.path.join(REPORTS, cfg["bak_dir"], cfg["bak_d09"]), encoding="utf-8"))
    disk_d09 = json.load(open(os.path.join(PROJ, "units", unit, "D09.json"), encoding="utf-8"))
    plan = []
    for eb, ed in zip(bak_d08["episodes"], disk_d08["episodes"]):
        rem, add, rep = align(eb["body"], ed["body"])
        old_notes = list(eb.get("compliance_notes") or [])
        new_notes = [n for n in (ed.get("compliance_notes") or []) if n not in old_notes]
        plan.append({
            "ep": ed["ep"],
            "removals": rem, "additions": add, "replacements": rep,
            "new_notes": new_notes,
            "title": ed.get("title"),
        })
    # D09：台词条数变化的集 → SUBTEXT key 顺移
    d09_plan = []
    bl = bak_d09["lines"]
    dl = disk_d09["lines"]
    bmap = {}
    for l in bl:
        bmap.setdefault(l["ep"], []).append(l)
    dmap = {}
    for l in dl:
        dmap.setdefault(l["ep"], []).append(l)
    for ep, lines in dmap.items():
        old = bmap.get(ep, [])
        if len(old) != len(lines):
            d09_plan.append((ep, len(old), len(lines)))
    return plan, d09_plan, disk_d09


def apply_d08(unit, plan, dry):
    cfg = UNITS[unit]
    path = os.path.join(HERE, cfg["d08_file"])
    src = read(path)
    for item in plan:
        ep = item["ep"]
        regs = ep_regions(src, cfg["ep_pat"])
        rng = next((r for r in regs if r[0] == ep), None)
        if rng is None:
            raise RuntimeError(f"{unit} 未定位 ep{ep}")
        _, es, ee = rng
        ls, le = body_span(src, es, ee)
        spans = entry_spans(src, ls, le, cfg["style"])
        texts = []
        for s0, s1 in spans:
            texts.append(src[s0:s1])
        # 建立 bak entry → span 的映射（按 text 命中）
        def find_span(txt):
            for i, lit in enumerate(texts):
                if txt and txt in lit:
                    return i
            return -1

        edits = []  # (start, end, replacement)
        for idx, e in item["removals"]:
            si = find_span(e.get("text", ""))
            if si < 0 and e.get("text") == AI_MARK_TEXT:
                si = next((i for i, lit in enumerate(texts) if lit.strip() == "AI_MARK,"), -1)
            if si < 0:
                raise RuntimeError(f"{unit} ep{ep} 未定位待移除条目 {e.get('text','')[:20]}")
            edits.append((spans[si][0], spans[si][1], ""))
        for idx, e_old, e_new in item["replacements"]:
            si = find_span(e_old.get("text", ""))
            if si < 0:
                raise RuntimeError(f"{unit} ep{ep} 未定位待改写条目 {e_old.get('text','')[:20]}")
            edits.append((spans[si][0], spans[si][1], emit_entry(e_new, cfg["style"])))
        for idx, e in item["additions"]:
            # 插到目标位置：找磁盘 body 中该条的前一条在源里的 span
            prev = None
            for i in range(idx - 1, -1, -1):
                cand = item["_disk_body"][i] if "_disk_body" in item else None
            # 用文本定位前一条
            prev_text = item["_prev_text"].get(idx)
            si = find_span(prev_text) if prev_text else -1
            if si < 0:
                raise RuntimeError(f"{unit} ep{ep} 未定位插入锚点（新增 {e.get('text','')[:16]}）")
            edits.append((spans[si][1], spans[si][1], emit_entry(e, cfg["style"])))
        # notes 追加
        if item["new_notes"]:
            # 锚点＝本集 compliance_notes 列表的闭合括号（缩进无关）
            ni = src.index('"compliance_notes": [', es)
            if ni > ee:
                raise RuntimeError(f"{unit} ep{ep} 未定位 compliance_notes")
            depth = 1
            k = ni + len('"compliance_notes": [')
            while k < ee and depth > 0:
                ch = src[k]
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            close = k
            head = src.rfind("\n", ni, close) + 1
            ind = re.match(r"[ \t]*", src[head:close]).group(0)
            add_txt = "".join(f"{ind}{pyq(n)},\n" for n in item["new_notes"])
            edits.append((head, head, add_txt))
        # 合并并应用（倒序，避免偏移）
        edits.sort(key=lambda x: x[0], reverse=True)
        for s0, s1, rep in edits:
            src = src[:s0] + rep + src[s1:]
    # 版本
    src = src.replace(f'VERSION = "{cfg["old_d08"]}"', f'VERSION = "{cfg["cur_d08"]}"', 1)
    src = src.replace(f'"version": "{cfg["old_d08"]}"', f'"version": "{cfg["cur_d08"]}"')
    if dry:
        print(f"  [{unit}] D08 内容源 dry-run：{len(edits)} 处编辑")
        return
    shutil.copy2(path, path + ".bak_sync")
    write(path, src)


def apply_d09(unit, d09_plan, disk_d09, dry):
    cfg = UNITS[unit]
    path = os.path.join(HERE, cfg["d09_file"])
    src = read(path)
    dmap = {}
    for l in disk_d09["lines"]:
        dmap.setdefault(l["ep"], []).append(l)
    # 把操作限定在 SUBTEXT 字典区间内
    m0 = src.index("SUBTEXT = {")
    m1 = src.index("\n}", m0)
    sub_src, sub_tail = src[:m1], src[m1:]
    for ep, n_old, n_new in d09_plan:
        lines = dmap[ep]
        # 旧 key (ep,1..n_old) → 新 key (ep,1+delta..)
        delta = n_new - n_old
        if delta <= 0:
            raise RuntimeError(f"{unit} ep{ep} 台词数未增（{n_old}→{n_new}）")
        # 先把旧的 (ep,k) 改名到 (ep,k+delta)（倒序避免撞键）
        for k in range(n_old, 0, -1):
            sub_src = re.sub(rf"^(\s*)\({ep}, {k}\):", rf"\g<1>({ep}, {k + delta}):", sub_src, count=1, flags=re.M)
        # 新增 (ep,1)
        new_line = lines[0]
        sub = new_line.get("subtext", "")
        if not sub:
            raise RuntimeError(f"{unit} ep{ep} 新首句缺 subtext")
        block = f"    ({ep}, 1): {pyq(sub)},\n"
        sub_src = re.sub(rf"^(\s*)\({ep}, \d+\):", block + r"\g<1>(" + str(ep) + ", 2):", sub_src, count=1, flags=re.M)
    src = sub_src + sub_tail
    src = src.replace(f'VERSION = "{cfg["old_d09"]}"', f'VERSION = "{cfg["cur_d09"]}"', 1)
    src = src.replace(f'"version": "{cfg["old_d09"]}"', f'"version": "{cfg["cur_d09"]}"')
    if dry:
        print(f"  [{unit}] D09 内容源 dry-run：{len(d09_plan)} 集重排")
        return
    shutil.copy2(path, path + ".bak_sync")
    write(path, src)


GUARD_D08 = '''
# ── Q64 版本守卫（2026-10-23 补装）────────────────────────────────────
# 判据：磁盘产物的 version **高于**本脚本要写的 version ⇒ 拒绝覆盖并中止。
#       正常升版（磁盘 ≤ 脚本）与幂等重跑（磁盘 == 脚本）放行；
#       `--force` 为人工确认后的逃生口；版本只进不退。
def _vkey(v):
    m = re.search(r"(\\d+)(?:\\.(\\d+))?", str(v or ""))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def _guard(target, want):
    if not os.path.exists(target):
        return
    try:
        cur = json.load(open(target, encoding="utf-8"))
    except Exception:
        return
    cv = cur.get("version")
    if _vkey(cv) > _vkey(want):
        print(f"❌ 版本守卫：磁盘 {target} 的 version={cv} 高于本脚本要写的 {want} → 拒绝覆盖，未写盘。")
        sys.exit(1)
'''


def add_guard(unit, dry):
    cfg = UNITS[unit]
    for fn, want in ((cfg["d08_file"], cfg["cur_d08"]), (cfg["d09_file"], cfg["cur_d09"])):
        path = os.path.join(HERE, fn)
        src = read(path)
        if "_vkey" in src:
            continue
        m = re.search(r'(out\s*=\s*\{[^\n]*?"doc_id":\s*"(\w+)"[^\n]*\n?)', src)
        if not m:
            print(f"  ⚠️ {fn}: 未定位 out 定义，跳过守卫注入")
            continue
        doc = m.group(2)
        tgt = 'f"{ROOT}/units/' + unit + '/' + doc + '.json"'""
        # 在写盘前插入守卫调用
        write_idx = src.index("open(", m.end())
        guard_call = f'_guard({tgt}, "{want}")\n'
        src = src[:write_idx] + guard_call + src[write_idx:]
        src = src.replace("import json, re, os, sys", "import json, re, os, sys", 1)
        # 追加守卫函数定义（需 re/os/sys/json 均已 import）
        src = src.rstrip() + "\n" + GUARD_D08
        if dry:
            print(f"  [{unit}] {fn}: dry-run 注入 Q64 守卫（目标 {tgt}，版本 {want}）")
            continue
        shutil.copy2(path, path + ".bak_guard")
        write(path, src)
        print(f"  [{unit}] {fn}: 已注入 Q64 版本守卫")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--unit", action="append", default=None)
    a = ap.parse_args()
    units = a.unit or ["U01", "U02"]
    for unit in units:
        print(f"▶ {unit}")
        plan, d09_plan, disk_d09 = plan_unit(unit)
        disk_d08 = json.load(open(os.path.join(PROJ, "units", unit, "D08.json"), encoding="utf-8"))
        dmap = {e["ep"]: e for e in disk_d08["episodes"]}
        for item in plan:
            item["_disk_body"] = dmap[item["ep"]]["body"]
            item["_prev_text"] = {i: (dmap[item["ep"]]["body"][i - 1].get("text") if i > 0 else None)
                                   for i in range(len(dmap[item["ep"]]["body"]))}
            n_ch = len(item["removals"]) + len(item["additions"]) + len(item["replacements"])
            if n_ch:
                print(f"  ep{item['ep']:>3}: 移除{len(item['removals'])} 新增{len(item['additions'])} "
                      f"改写{len(item['replacements'])} notes+{len(item['new_notes'])}")
        print(f"  D09 台词数变化的集: {d09_plan}")
        apply_d08(unit, plan, a.dry_run)
        apply_d09(unit, d09_plan, disk_d09, a.dry_run)
        if unit == "U01":
            add_guard(unit, a.dry_run)
    print("✅ 完成" if a.apply else "（dry-run，未写盘）")
