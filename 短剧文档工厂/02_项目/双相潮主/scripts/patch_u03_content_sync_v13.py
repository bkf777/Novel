#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 U03 内容源回填到「黄金 3 秒」R-026b 批次（12:03–12:04）之后的现盘。

背景（2026-10-23 12:03–12:05 实测取证）：
  · 总控「黄金 3 秒」补位批次 **R-026b**（针对台本编剧 U03）于 **12:03:10** 备份
    `reports/_bak_scriptwriter_u03_golden3s_20261023-120310/`
    （内含 `edit_script.mjs` ＋ 改前 `units/U03/D08.json`、`D09.json`），
    并于 **12:04:13** 重写**本岗单写点**：
      `units/U03/D08.json` v1.4→**v1.5**（46,735 B｜sha16 287001250d5e440c）
      `units/U03/D09.json` v1.1→**v1.2**（18,024 B｜sha16 cba154174704f5b3）
    改法（`edit_script.mjs` 逐字取证）：**ep018／ep019／ep021／ep022／ep024 五集**
    各在 `body[1]`（紧随开场 action）插入一条首句画外音台词 ＋ 同形 `shot_intent`
    （「本集首句台词，以画外音在开场镜入画：…秒码由 D15/D16 承接」），
    D09 侧同步在 `lines[1]` 插入对应台词行；各集原台词行号顺移 1 位。
    脚本自带并发守卫（`EXPECT_D08_VER='v1.4'` / `EXPECT_D09_VER='v1.1'`，不符即 ABORT）。
  · **该批次只写了 JSON，没同步本岗内容源** ⇒ 内容源 VERSION 仍停在 v1.4／v1.1，
    重跑会回退批次改动（Q64 版本守卫会拦下，不静默）。本脚本把内容源补齐到现盘。
  · 连带后果（已实测）：5 集各 +1 条 body ⇒ **其后各条 body 下标整体 +1**
    ⇒ `shotintent_map_U03.mjs` 的 idx 锚**整段作废**（57 条 → 现盘 62 条），
    覆盖轴① 降为 38/57、exit 1 ⇒ 映射表须按现盘重刷（见本岗同轮另做）。

写法：Q40 —— **只改内容源**，JSON 由 `build_D08.py` / `build_D09.py` 重跑生成，
**禁手改 D08.json / D09.json**。

用法：python3 patch_u03_content_sync_v13.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BAK = os.path.join(PROJ, "reports", "_bak_scriptwriter_u03_golden3s_20261023-120310")
SRC_D08 = os.path.join(HERE, "d08_content_U03.py")
SRC_D09 = os.path.join(HERE, "d09_content_U03.py")
DISK_D08 = os.path.join(PROJ, "units", "U03", "D08.json")
DISK_D09 = os.path.join(PROJ, "units", "U03", "D09.json")
BAK_D08 = os.path.join(BAK, "units", "U03", "D08.json")
BAK_D09 = os.path.join(BAK, "units", "U03", "D09.json")

# 批次改动的五集（由改前/改后差分点算，不采信转述）
CHANGED_EPS = [18, 19, 21, 22, 24]


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def py_str(s):
    return json.dumps(s, ensure_ascii=False)


def diff_report():
    """先做全量结构化差分，确认批次只做了「五集各插入一条」这一件事。"""
    old8 = json.load(open(BAK_D08, encoding="utf-8"))
    new8 = json.load(open(DISK_D08, encoding="utf-8"))
    old9 = json.load(open(BAK_D09, encoding="utf-8"))
    new9 = json.load(open(DISK_D09, encoding="utf-8"))
    o8 = {e["ep"]: e for e in old8["episodes"]}
    n8 = {e["ep"]: e for e in new8["episodes"]}
    o9 = {}
    for l in old9["lines"]:
        o9.setdefault(l["ep"], []).append(l)
    n9 = {}
    for l in new9["lines"]:
        n9.setdefault(l["ep"], []).append(l)
    issues = []
    for ep in sorted(n8):
        ob, nb = o8[ep]["body"], n8[ep]["body"]
        if len(nb) != len(ob) + (1 if ep in CHANGED_EPS else 0):
            issues.append(f"ep{ep} body 条数变化异常：{len(ob)}→{len(nb)}")
            continue
        if ep in CHANGED_EPS:
            # 新条目应恰在 body[1]；其余条目应逐条同文
            if nb[0] != ob[0] or nb[2:] != ob[1:]:
                issues.append(f"ep{ep} body 除新增位外存在非预期差异")
        else:
            if ob != nb:
                issues.append(f"ep{ep} body 应无差异却有差异")
        for k in ("title", "scene_heading", "present_characters", "compliance_notes", "duration_sec"):
            if o8[ep].get(k) != n8[ep].get(k):
                issues.append(f"ep{ep}.{k} 非预期变更")
    for ep in sorted(n9):
        ol, nl = o9.get(ep, []), n9[ep]
        if len(nl) != len(ol) + (1 if ep in CHANGED_EPS else 0):
            issues.append(f"ep{ep} D09 lines 条数变化异常：{len(ol)}→{len(nl)}")
            continue
        if ep in CHANGED_EPS:
            for j in range(len(ol)):
                a, b = ol[j], nl[j + 1]
                if a["text"] != b["text"] or a["char_id"] != b["char_id"]:
                    issues.append(f"ep{ep} D09 顺移后第 {j+1} 句文本/角色不符")
                    break
        else:
            if [l["text"] for l in ol] != [l["text"] for l in nl]:
                issues.append(f"ep{ep} D09 应无差异却有差异")
    print(f"  差分点算：改动集 {CHANGED_EPS}｜D08 改前 {old8.get('version')} → 现盘 {new8.get('version')}"
          f"｜D09 改前 {old9.get('version')} → 现盘 {new9.get('version')}")
    if issues:
        for i in issues:
            print(f"  ❌ {i}")
        sys.exit(1)
    print("  ✅ 全量结构化差分：批次只做了「五集各插入一条 body[1] 台词＋一行 D09 lines[1]」")


def _match_brace(s, i):
    """s[i] 必须是 '{'；返回配平右花括号的下标（含）。支持嵌套与字符串。"""
    assert s[i] == "{", s[i - 20:i + 20]
    depth = 0
    in_str = False
    esc = False
    while i < len(s):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise ValueError("花括号未配平")


def patch_d08(dry_run=False):
    disk = json.load(open(DISK_D08, encoding="utf-8"))
    bmap = {e["ep"]: e for e in disk["episodes"]}
    src = read(SRC_D08)
    n_ok = 0
    for ep in CHANGED_EPS:
        new_entry = bmap[ep]["body"][1]
        assert new_entry.get("type") == "dialogue" and new_entry.get("shot_intent"), ep
        # 定位该集块
        m = re.search(r"# ═+ ep0*" + str(ep) + r"[^═]*═+\n", src)
        if not m:
            print(f"❌ 未定位 ep{ep} 块")
            sys.exit(1)
        bstart = src.find('"body": [', m.end())
        if bstart < 0:
            print(f"❌ ep{ep} 未定位 body 列表")
            sys.exit(1)
        obrace = src.index("{", bstart)
        oend = _match_brace(src, obrace)
        # body[0] 必须是开场 action；现盘 body[1] 紧随其后 ⇒ 插入点 = body[0] 结束处
        if src[obrace:oend] != json.dumps(bmap[ep]["body"][0], ensure_ascii=False):
            # 允许缩进/风格差异：用解析比对
            try:
                lit = json.loads(src[obrace:oend + 1])
            except Exception:
                lit = None
            if lit != bmap[ep]["body"][0]:
                print(f"⚠️  ep{ep} body[0] 与现盘不一致（风格差异），仍按 body[0] 之后插入")
        block = json.dumps(new_entry, ensure_ascii=False, indent=4)
        block = "\n".join("            " + ln if k else ln for k, ln in enumerate(block.split("\n")))
        block = block.replace("\n            }", "\n            },")
        new_src = src[:oend + 1] + "\n" + block + src[oend + 1:]
        src = new_src
        n_ok += 1
    # 版本与变更说明
    src = src.replace('VERSION = "v1.4"', 'VERSION = "v1.5"', 1)
    marker = 'VERSION = "v1.5"'
    changelog = (
        "# v1.5（2026-10-23 12:0x）：**回填本岗内容源至「黄金 3 秒」R-026b 批次（12:04:13）后的现盘**\n"
        "#   ① R-026b 批次于 12:03:10 备份 `_bak_scriptwriter_u03_golden3s_20261023-120310/`\n"
        "#      （内含 edit_script.mjs ＋ 改前 D08/D09），12:04:13 重写本岗单写点\n"
        "#      `units/U03/D08.json` v1.4→v1.5：\n"
        "#      **ep018／ep019／ep021／ep022／ep024 五集**各在 `body[1]` 插入一条\n"
        "#      首句画外音台词 ＋ 同形 `shot_intent`（「本集首句台词，以画外音在开场镜入画：\n"
        "#      …秒码由 D15/D16 承接」），原台词行号顺移 1 位。\n"
        "#      **该批次只写 JSON、未同步本岗内容源** ⇒ 重跑会回退其改动（Q64 守卫会拦），\n"
        "#      故本版按现盘逐条回填（插入内容逐字取自现盘 body[1]，非人工复写）。\n"
        "#   ② 连带后果（已实测）：5 集各 +1 条 body ⇒ 其后各条下标整体 +1 ⇒\n"
        "#      `shotintent_map_U03.mjs` 的 idx 锚整段作废（57 → 现盘 62 条）⇒ 须按现盘重刷。\n"
    )
    src = src.replace(marker, changelog + marker, 1)
    print(f"  D08 内容源：{n_ok} 集插入首句台词｜VERSION→v1.5")
    if dry_run:
        return
    shutil.copy2(SRC_D08, SRC_D08 + ".bak_sync_v13")
    write(SRC_D08, src)


def patch_d09(dry_run=False):
    disk = json.load(open(DISK_D09, encoding="utf-8"))
    lines_by_ep = {}
    for l in disk["lines"]:
        lines_by_ep.setdefault(l["ep"], []).append(l)
    src = read(SRC_D09)
    n_ok = 0
    for ep in CHANGED_EPS:
        nl = lines_by_ep[ep]
        new_line = nl[0]  # 批次插入的 idx=1 行
        new_sub = new_line.get("subtext") or ""
        if not new_sub:
            print(f"❌ ep{ep} 现盘新行缺 subtext")
            sys.exit(1)
        # 定位该集在 SUBTEXT 里的条目块（注释行 + (ep, k): "..."）
        blk = re.search(r"(    # ep0*" + str(ep) + r"[^\n]*\n)((?:    \(" + str(ep) + r", \d+\): [^\n]*\n)+)", src)
        if not blk:
            print(f"❌ 未定位 SUBTEXT ep{ep} 块")
            sys.exit(1)
        old_entries = re.findall(r"    \(" + str(ep) + r", (\d+)\): (\".*?\"),\n", blk.group(2))
        if not old_entries:
            print(f"❌ ep{ep} SUBTEXT 条目未解析")
            sys.exit(1)
        # 旧 idx 1..n ⇒ 新 idx 2..n+1；新 idx=1 取现盘 subtext
        new_block = "    (" + str(ep) + ", 1): " + py_str(new_sub) + ",\n"
        for k, v in old_entries:
            new_block += "    (" + str(ep) + ", " + str(int(k) + 1) + "): " + v + ",\n"
        src = src[:blk.start(2)] + new_block + src[blk.end(2):]
        n_ok += 1
    src = src.replace('VERSION = "v1.1"', 'VERSION = "v1.2"', 1)
    marker = 'VERSION = "v1.2"'
    changelog = (
        "# v1.2（2026-10-23 12:0x）：跟随机读 D08 v1.5 —— R-026b 批次为 ep018／ep019／ep021／\n"
        "#   ep022／ep024 五集各新增一条首句画外音台词（原台词行号顺移 1 位），\n"
        "#   故五集 SUBTEXT 的 idx 由 1..n 顺移为 2..n+1，并补齐各集 idx=1 的潜台词\n"
        "#   （逐字取自现盘 D09 v1.2，非人工复写）。\n"
    )
    src = src.replace(marker, changelog + marker, 1)
    print(f"  D09 内容源：{n_ok} 集 SUBTEXT 重排（新增 idx1，旧 1..n→2..n+1）｜VERSION→v1.2")
    if dry_run:
        return
    shutil.copy2(SRC_D09, SRC_D09 + ".bak_sync_v12")
    write(SRC_D09, src)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print("▶ 回填 U03 内容源 → R-026b 批次后的现盘（Q40：只改内容源，JSON 由构建脚本生成）")
    diff_report()
    patch_d08(a.dry_run)
    patch_d09(a.dry_run)
    print("✅ 完成")
