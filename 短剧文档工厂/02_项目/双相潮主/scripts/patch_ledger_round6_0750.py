#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_ledger_round6_0750.py —— 订正块归位 ＋ 追加锚点规则（OPS/Q 编号运行时取 max+1）＋ S29

起因（本岗自纠）：第五轮脚本把两段订正内容**追加在文件末尾**（`idx.rstrip("\n") + "\n" + ...`），
而**同角色的并行企划合规实例在 07:34:43 追加了新章节**（索引 §十·五十九 ／ 交付说明 §一百零三）
⇒ **本岗的订正块一度落在他人章节内部**（索引 1507 行落在 §十·五十九 内、交付说明 7409 行落在 §一百零三 内）。
**这违反「台账章节归属」**：他人会误读为他人的自纠记录。本轮把两块**归位**到本岗自己的章节末尾。

新登记：**{ops_id}**（追加锚点规则）＋ **{q_id}**（追加式写入必须锚定「本岗章节末尾」）＋ **S29**。

⚠️ 本脚本自身的插入逻辑已改为**锚定本岗章节末尾**（在下一节标题之前插入），
不再使用「追加到文件末尾」—— 这正是本轮的根因。

用法：python3 scripts/patch_ledger_round6_0750.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
    s = s.strip()
    if "百" in s:
        head, tail = s.split("百", 1)
        return (CN[head] if head else 1) * 100 + (cn_to_int(tail) if tail else 0)
    if "十" in s:
        head, tail = s.split("十", 1)
        return (CN[head] if head else 1) * 10 + (CN[tail] if tail else 0)
    return CN[s]


def int_to_cn(n):
    if n < 10:
        return "零一二三四五六七八九"[n]
    if n < 20:
        return "十" + ("" if n == 10 else "一二三四五六七八九"[n - 10])
    if n < 100:
        head, tail = divmod(n, 10)
        return ("零一二三四五六七八九"[head] if head > 1 else "") + "十" + \
               ("零一二三四五六七八九"[tail] if tail else 0)
    head, tail = divmod(n, 100)
    out = "零一二三四五六七八九"[head] + "百"
    if tail == 0:
        return out
    if tail < 10:
        return out + "零一二三四五六七八九"[tail]
    return out + int_to_cn(tail)


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


def cut_block(lines, start_pred, note):
    """从 lines 中切出一个以 start_pred 命中的行开头、到下一个空行为止的块（含尾部空行）。"""
    hits = [i for i, l in enumerate(lines) if start_pred(l)]
    if len(hits) != 1:
        sys.exit(f"[ABORT] {note} 起点命中数 {len(hits)} ≠ 1；不写盘。")
    i = hits[0]
    j = i
    while j < len(lines) and lines[j].strip() != "":
        j += 1
    block = lines[i:j + 1]          # 含块后那个空行
    rest = lines[:i] + lines[j + 1:]
    return block, rest


def insert_before(lines, marker_pred, block, note):
    """把 block 插到 marker_pred 命中的行之前（= 本岗章节末尾）。"""
    hits = [i for i, l in enumerate(lines) if marker_pred(l)]
    if len(hits) != 1:
        sys.exit(f"[ABORT] {note} 锚点命中数 {len(hits)} ≠ 1；不写盘。")
    return lines[:hits[0]] + block + lines[hits[0]:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    p_idx = os.path.join(proj, "00_项目索引.md")
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    now = datetime.now()
    stamp_hm = now.strftime("%H:%M")
    stamp_full = f"{now.strftime('%Y-%m-%d')} {stamp_hm}"

    d18_raw = read(p18)
    d18_raw_orig = d18_raw
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj_raw_orig = prj_raw
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检 ----------
    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 74):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.74；不写盘。")
    oi_ids = {o["id"] for o in d18["open_issues"]}
    gc_ids = {g["id"] for g in d18["global_checks"]}
    # ⚠️ 编号**运行时动态取 max+1** —— 同角色并行实例会同时登记新编号（实测 OPS-18／OPS-19 被连续占用）
    ops_max = max(int(i.split("-")[1]) for i in oi_ids if i.startswith("OPS-") and i.split("-")[1].isdigit())
    q_max = max(int(g["id"][1:]) for g in d18["global_checks"]
                if g["id"].startswith("Q") and g["id"][1:].isdigit())
    ops_id = "OPS-%d" % (ops_max + 1)
    q_id = "Q%d" % (q_max + 1)
    if ops_id in oi_ids:
        sys.exit(f"[ABORT] open_issues 已含 {ops_id}，不重复登记；不写盘。")
    if q_id in gc_ids:
        sys.exit(f"[ABORT] global_checks 已含 {q_id}，不重复登记；不写盘。")
    print(f"[ID] 运行时取号：{ops_id}（现 max OPS-{ops_max}）、{q_id}（现 max Q{q_max}）")
    if "S29_追加式写入锚点规则与章节归属" in prj["decisions"]:
        sys.exit("[ABORT] project.json 已含 S29，不重复登记；不写盘。")

    idx_lines = idx.split("\n")
    del_lines = deliv.split("\n")

    # ---------- 1. 索引：把 ⑤ 段从 §十·五十九 归位到 §十·五十八 ----------
    blk5, idx_lines = cut_block(
        idx_lines, lambda l: l.startswith("**⑤ 落款时间口径订正"), "索引 ⑤ 段")
    if not any("### 十·五十八" in l for l in idx_lines):
        sys.exit("[ABORT] 索引缺 §十·五十八；不写盘。")
    blk5 = blk5 + [
        "",
        f"**⑥ 归位说明（{stamp_hm}）**：本段最初被追加在**文件末尾**，"
        f"而**同角色并行企划合规实例于 07:34:43 追加了新章节**（索引 §十·五十九／交付说明 §一百零三）"
        f"⇒ 一度落在**他人章节内部**。本轮已**归位到本节末尾**。"
        f"根因＝追加锚点错误（应锚「本岗章节末尾」，不应锚「文件末尾」）→ **{q_id}／{ops_id}**。",
        "",
    ]
    idx_lines = insert_before(idx_lines, lambda l: l.startswith("### 十·五十九"), blk5,
                              "索引 §十·五十九 锚点")

    # ---------- 2. 交付说明：把 一百零二.6 段从 §一百零三 归位到 §一百零二 ----------
    blk6, del_lines = cut_block(
        del_lines, lambda l: l.startswith("### 一百零二.6 落款时间口径订正"), "交付说明 .6 段")
    blk6 = blk6 + [
        "",
        f"**归位说明（{stamp_hm}）**：本段最初被追加在**文件末尾**，"
        f"而并行企划合规实例于 07:34:43 追加了 §一百零三 ⇒ 一度落在**他人章节内部**；本轮已**归位到本节末尾**。"
        f"根因＝追加锚点错误 → **{q_id}／{ops_id}**。",
        "",
    ]
    del_lines = insert_before(del_lines, lambda l: l.startswith("## 一百零三、"), blk6,
                              "交付说明 §一百零三 锚点")

    idx = "\n".join(idx_lines)
    deliv = "\n".join(del_lines)

    # ---------- 3. D18：OPS 追加条目 + Q 追加条目（编号运行时取 max+1） ----------
    d18["global_checks"].append({
        "id": q_id,
        "item": "**追加式写入必须锚定「本岗自己的章节末尾」，禁止锚定「文件末尾」** —— "
                "本轮实证：第五轮脚本用 `text.rstrip(\"\\n\") + \"\\n\" + 新内容` 追加订正块，"
                "而**同角色的并行企划合规实例在 07:34:43 追加了新章节**（索引 §十·五十九／交付说明 §一百零三）"
                "⇒ 本岗两块订正内容**落在他人章节内部**（索引 1507 行、交付说明 7409 行）。"
                "**危害不是丢内容，是「章节归属被污染」** —— 他人会把本岗的自纠记录读成自己的，"
                "而本岗自己的章节又缺了这块，**两侧台账同时失真**。"
                "**做法**：① **锚点用「下一节标题之前」**，不用「文件末尾」；"
                "② **写前先认盘**：读盘后若他人可能已追加新节，**必须以现盘的最大节号为准**，"
                "**不得假设自己是最后一个写者**；③ **写后回读并验证归属**：确认新内容落在**本岗章节**内"
                "（比对前后章节边界行号）；④ **追加前做归属断言** —— 若锚点命中数 ≠ 1 即中止不写盘。"
                "**Apply when**：任何同角色多实例并发写同一台账文件的场景（追加章节、插入子段、插入留痕）。",
        "method": "写后回读并核对「新内容所在章节」与「本岗章节标题」是否一致；边界行号前后对比",
        "source": f"企划合规 2026-10-23 07:4x（{ops_id} 自纠）",
        "severity": "中（不丢内容，但污染章节归属、两侧台账同时失真）",
    })
    d18["open_issues"].append({
        "id": ops_id,
        "issue": "**本岗两块台账订正内容一度落在并行实例的章节内部** —— 索引「⑤ 落款时间口径订正」"
                 "落在 §十·五十九 内、交付说明「一百零二.6 落款时间口径订正」落在 §一百零三 内。"
                 "根因＝**追加锚点用了「文件末尾」而非「本岗章节末尾」**，"
                 "而并行企划合规实例在 07:34:43 抢先追加了新章节。"
                 f"**⚠️ 编号区分**：本条编号为 **{ops_id}**（运行时取 max+1，避免与并行实例撞号），"
                 "**与并行实例的 OPS-18 是两条不同事项** —— "
                 "并行实例的 OPS-18 ＝「闸门数字须当场实测回填」（与本岗 **Q71** 同向、已互认），"
                 "**本条＝「追加锚点与章节归属」**，勿混作一条。",
        "owner": "企划合规（本岗自纠）",
        "blocks": "不拦锁；**拦「台账章节归属」** —— 不修则后续任何按章节归属的审读都会读错主语",
        "priority": "中",
        "status": "**已归位·已闭环**（企划合规 2026-10-23 07:4x）",
        "resolution": "**2026-10-23 07:4x 本岗归位并闭环**：两段内容**按原文字面整体搬回**"
                      "**本岗自己的章节末尾**（索引 §十·五十八 末尾、交付说明 §一百零二 末尾），"
                      "**他方章节内容一字未动**。**做法改为「锚点＝下一节标题之前」**（插入而非追加到 EOF），"
                      "并加**归属断言**（锚点命中数 ≠ 1 即中止不写盘）与**写后回读核归属**。"
                      f"**本条同时登记为 {q_id}**，作为所有「同角色多实例并发写台账」场景的通用规则。"
                      "**Apply**：任何多实例并发写同一台账文件的后续脚本，**一律不用 EOF 锚点**。",
        "detected_by": "企划合规 2026-10-23 07:4x（本岗归位时自查发现）",
    })
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- 4. project.json：S29 ----------
    prj["decisions"]["S29_追加式写入锚点规则与章节归属"] = (
        f"企划合规裁决（2026-10-23 07:4x，{ops_id} 结清 · 配套 **{q_id}**）："
        "**① 追加锚点＝下一节标题之前**，**禁止锚「文件末尾」** —— "
        "同角色多实例并发写台账时，**「EOF 是我的」是假前提**"
        "（本轮实证：并行企划合规实例 07:34:43 已追加 §十·五十九／§一百零三）。"
        "**② 写前重新认盘** —— 节号**一律取现盘 max+1**，**不得假设自己是最后一个写者**；"
        "**③ 写后回读核归属** —— 比对新内容所在章节边界行号，确认落在**本岗章节**内。"
        "**④ 归属断言** —— 锚点命中数 ≠ 1 即**中止不写盘**。"
        "**⑤ 归位不改他人内容** —— 搬回时**按原文字面整体搬移**，他方章节一字未动。"
        "**Apply when**：任何台账/报告/日志类**多实例并发追加**的场景。"
    )
    prj["updated_at"] = stamp_full
    prj_out = serialize_like(prj, prj_raw)

    # ---------- 5. 索引：§五/§六 D18 版本提法 ----------
    pat_a = r"D18 \*\*v1\.\d+\*\*（\*\*\d+\*\* 条 global_checks / \*\*\d+\*\* 条 open_issues"
    if len(re.findall(pat_a, idx)) != 1:
        sys.exit("[ABORT] 索引 §五 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_a,
                 f"D18 **{d18['version']}**（**{len(d18['global_checks'])}** 条 global_checks / "
                 f"**{len(d18['open_issues'])}** 条 open_issues",
                 idx, count=1)
    pat_c = (r"(\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2}(?::[0-9]{2})? 落｜approved\*\*（字节数不钉，见 D18 \*\*Q34\*\*）。)"
             r"\*\*\d+ 条 global_checks\*\*")
    if len(re.findall(pat_c, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 计数锚点命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_c,
                 lambda m: m.group(1) + f"**{len(d18['global_checks'])} 条 global_checks**",
                 idx, count=1)
    pat_b = r"\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2}(?::[0-9]{2})? 落｜approved\*\*"
    if len(re.findall(pat_b, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_b, f"**{d18['version']}｜«RUN_HM» 落｜approved**", idx, count=1)

    # ---------- 6. 自检：归属 + 残留 ----------
    i58 = idx.find("### 十·五十八")
    i59 = idx.find("### 十·五十九")
    if i58 < 0 or i59 < 0 or i58 > i59:
        sys.exit("[ABORT] 索引章节边界异常；不写盘。")
    seg58 = idx[i58:i59]
    if "**⑤ 落款时间口径订正" not in seg58:
        sys.exit("[ABORT] 索引 ⑤ 段未归位到 §十·五十八；不写盘。")
    if "**⑤ 落款时间口径订正" in idx[i59:]:
        sys.exit("[ABORT] 索引 ⑤ 段仍残留在 §十·五十九 之后；不写盘。")
    d102 = deliv.find("## 一百零二、")
    d103 = deliv.find("## 一百零三、")
    if d102 < 0 or d103 < 0 or d102 > d103:
        sys.exit("[ABORT] 交付说明章节边界异常；不写盘。")
    seg102 = deliv[d102:d103]
    if "### 一百零二.6 落款时间口径订正" not in seg102:
        sys.exit("[ABORT] 交付说明 .6 段未归位到 §一百零二；不写盘。")
    if "### 一百零二.6 落款时间口径订正" in deliv[d103:]:
        sys.exit("[ABORT] 交付说明 .6 段仍残留在 §一百零三 之后；不写盘。")
    for k in (ops_id, q_id):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S29_追加式写入锚点规则与章节归属" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S29；不写盘。")

    # ---------- 7. 并发写盘竞态守卫（compare-and-swap） ----------
    for path, raw0, label in ((p18, d18_raw_orig, "shared/D18.json"),
                               (p_prj, prj_raw_orig, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] 归位：索引 ⑤ 段 → §十·五十八 末尾；交付说明 .6 段 → §一百零二 末尾；"
              f"D18 {ver}→{d18['version']}（＋{ops_id} ＋{q_id}）；project.json ＋S29")
        return

    bak = os.path.join(proj, "reports", "_bak_0750_patch_round6")
    os.makedirs(bak, exist_ok=True)
    for path, name in ((p18, "D18.json"), (p_prj, "project.json"),
                       (p_idx, "00_项目索引.md"), (p_del, "99_交付说明.md")):
        with open(os.path.join(bak, name), "wb") as f:
            f.write(open(path, "rb").read())

    write(p18, d18_out)
    write(p_prj, prj_out)
    run_hm = datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M")
    idx = idx.replace("«RUN_HM»", run_hm)
    write(p_idx, idx)
    write(p_del, deliv)
    print(f"[DONE] 订正块归位 ＋ {ops_id}/{q_id}/S29 落盘")
    print(f"   索引：⑤ 段 → §十·五十八 末尾（§十·五十九 内容未动）")
    print(f"   交付说明：一百零二.6 段 → §一百零二 末尾（§一百零三 内容未动）")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：＋S29；updated_at → {stamp_full}")
    print(f"   00_项目索引.md：§五/§六 版本提法（落款 {run_hm}）")
    print("   99_交付说明.md：§一百零二")


if __name__ == "__main__":
    main()
