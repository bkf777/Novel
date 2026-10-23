#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOOL-04 实测结论核销 ＋ U01-R18 登记 ＋ Q50 ＋ S15（企划合规，2026-10-23 04:20）。

起因（本轮最有价值的一条）
--------------------------
声音设计 02:31 提请的 TOOL-04「实际 TTS 时长 vs D15 `dur_sec` 预算」比对缺位，
**已于 03:57 由声音设计执行完毕并落盘**（`preview/U01_tts/tts_budget_check_U01.json`，28,400 B），
**verdict ＝ FAIL**：28 条配音全部实测，**ERR 10／WARN 1／OK 17**；
**D16 侧契约逐条一致（`d16_out_mismatch_count` ＝ 0）** —— 即**文档链内部自洽**，
破的是**「文档 vs 实际音频」这一轴**（此前零覆盖）。

**企划合规 04:20 独立用 ffprobe 复算 28 条**：ERR 10／WARN 1／OK 17，**与声音设计报告逐条一致**
（并以 D09 原文校验了配音↔台词的顺序映射，**零错位**）→ 结论可信。

**本岗口径订正（须如实记）**：此前 TOOL-04 的裁决「归口出片阶段、文档工厂侧不排期不做」**过重** ——
只读比对既不合成也不生成任何音频（既有预演音频已在盘上），且**处置本身纯属文档工作**
（改 D15 `dur_sec`／D16 `out_sec`，必要时改 D09·D08 台词）→ **比对与处置都归文档阶段**；
只有**新合成音频**才归出片阶段。硬边界不变。

本脚本做五件事（命中数断言，对不上即中止不写盘）：
  A. D18 v1.41 → v1.42：TOOL-04 升级为「已执行·FAIL·10 条超预算·待处置」；
     新增 open_issue **U01-R18**（含 10 条分流表）；新增 global_check **Q50**。
  B. project.json：新增 decisions **S15_TTS预算实测口径订正与10条分流处置**。
  C. 00_项目索引.md：§二 状态栏 D18 版本提法刷到 v1.42；新增 §十·N。
  D. 99_交付说明.md：新增 §N（运行时取 max+1）。
  E. 派返修单到声音设计（由调用方在脚本外执行 message_bot，本脚本只登记派单）。

用法
----
python3 scripts/patch_to04_tts_budget_0420.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 04:20"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}

# 10 条超预算条目（企划合规 04:20 独立 ffprobe 复算，ERR=10）
ERR10 = [
    ("D09 ep1 #1", 1, 1, 1.9, 1.6, 0.3, 0.7, "空间允许"),
    ("D09 ep2 #2", 2, 2, 2.8, 2.2, 0.6, 6.2, "空间允许"),
    ("D09 ep2 #3", 2, 3, 1.7, 1.4, 0.3, 3.3, "空间允许"),
    ("D09 ep2 #4", 2, 4, 3.0, 1.8, 1.2, 0.8, "**空间不足·须缩文案**"),
    ("D09 ep3 #2", 3, 3, 2.6, 2.0, 0.6, 2.9, "空间允许"),
    ("D09 ep5 #1", 5, 2, 2.7, 2.6, 0.1, 1.7, "空间允许"),
    ("D09 ep5 #2", 5, 2, 2.7, 2.2, 0.5, 4.9, "空间允许"),
    ("D09 ep5 #4", 5, 4, 1.6, 1.4, 0.2, 3.4, "空间允许"),
    ("D09 ep8 #1", 8, 1, 2.2, 2.0, 0.2, 7.8, "空间允许"),
    ("D09 ep8 #4", 8, 4, 2.8, 2.6, 0.2, 0.0, "**空间不足·须缩文案**"),
]


def cn_to_int(s):
    if "十" in s:
        head, tail = s.split("十", 1)
        return (CN[head] if head else 1) * 10 + (CN[tail] if tail else 0)
    return CN[s]


def int_to_cn(n):
    if n < 10:
        return "零一二三四五六七八九"[n]
    head, tail = divmod(n, 10)
    return ("零一二三四五六七八九"[head] if head > 1 else "") + "十" + \
           ("零一二三四五六七八九"[tail] if tail else "")


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


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
    p_chk = os.path.join(proj, "preview", "U01_tts", "tts_budget_check_U01.json")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检：比对结果文件必须存在且是 FAIL，且与本脚本的 ERR10 一致 ----------
    if not os.path.isfile(p_chk):
        sys.exit(f"[ABORT] 比对结果文件不存在：{p_chk}；不写盘。")
    chk = json.loads(read(p_chk))
    if chk.get("verdict") != "FAIL":
        sys.exit(f"[ABORT] 比对结果 verdict={chk.get('verdict')}，期望 FAIL；不写盘。")
    s = chk.get("summary", {})
    if s.get("error_count") != len(ERR10):
        sys.exit(f"[ABORT] 比对结果 error_count={s.get('error_count')}，本脚本表为 {len(ERR10)} 条；不写盘。")
    if s.get("d16_out_mismatch_count") != 0:
        sys.exit(f"[ABORT] D16 契约不一致数={s.get('d16_out_mismatch_count')}，期望 0；不写盘。")
    if s.get("measured") != 28:
        sys.exit(f"[ABORT] 实测条数={s.get('measured')}，期望 28；不写盘。")

    if d18.get("version") != "v1.41":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.41；不写盘。")

    # ---------- A. D18 ----------
    oi = {o["id"]: o for o in d18["open_issues"]}
    if "U01-R18" in oi:
        sys.exit("[ABORT] open_issues 已含 U01-R18，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if "Q50" in gc_ids:
        sys.exit("[ABORT] global_checks 已含 Q50，不重复登记；不写盘。")
    if gc_ids[-1] != "Q49":
        sys.exit(f"[ABORT] global_checks 末条为 {gc_ids[-1]}，期望 Q49；不写盘。")

    t4 = oi["TOOL-04"]
    if t4.get("status") != "已裁决·双方确认不占文档工厂排期":
        sys.exit(f"[ABORT] TOOL-04 status={t4.get('status')}，与预期不符；不写盘。")
    t4["status"] = "已执行·FAIL·10 条超预算·已派返修单"
    t4["resolution"] = t4["resolution"].rstrip() + (
        "　**2026-10-23 04:20 企划合规核销（以磁盘实测为准）**：该只读比对**已于 03:57 落盘并执行完毕**"
        "（`preview/U01_tts/tts_budget_check_U01.json`，28,400 B），**verdict ＝ FAIL**："
        "28 条配音全部实测（`no_audio` 0）、**ERR 10／WARN 1／OK 17**；"
        "**D16 侧契约逐条一致（`d16_out_mismatch_count` ＝ 0）** —— 即**文档链内部自洽**，"
        "破的是**「文档 vs 实际音频」这一轴**（此前零覆盖）。另 `items_json_dur_mismatch_count` ＝ 1"
        "（缓存 `dur` 字段陈旧，实测为准）。"
        "**企划合规 04:20 独立用 ffprobe 复算 28 条**：ERR 10／WARN 1／OK 17，"
        "**与声音设计报告逐条一致**，并以 D09 原文校验了配音↔台词的顺序映射（**零错位**）→ 结论可信。"
        "**⚠️ 本岗口径订正（如实记）**：此前「归口出片阶段、文档工厂侧不排期不做」的裁决**过重** —— "
        "只读比对既不合成也不生成任何音频（既有预演音频已在盘上），且**处置本身纯属文档工作** "
        "（改 D15 `dur_sec`／D16 `out_sec`，必要时改 D09·D08 台词）→ **比对与处置都归文档阶段**；"
        "只有**新合成音频**才归出片阶段（硬边界不变）。订正见 **decisions.S15** 与 **U01-R18**。"
    )

    rows_md = "\n".join(
        f"| {ref} | ep{e} 镜{sid} | {nom} | {bud} | **+{need}** | {avail} | {note} |"
        for ref, e, sid, nom, bud, need, avail, note in ERR10
    )
    d18["open_issues"].append({
        "id": "U01-R18",
        "issue": "**U01 预演音频 10 条超出 D15 `dur_sec` 预算 → 字幕—配音契约在成片阶段会被打破** —— "
                 "只读比对（`preview/U01_tts/tts_budget_check_U01.json`，03:57 落盘）实测 28 条配音："
                 "**ERR 10**（实际时长超预算）／WARN 1（贴边零余量）／OK 17；"
                 "**最大超出 ep2#4「两小时五十八分……换我用了。」+1.2s**。"
                 "**文档链本身无缺陷**：D16 的 28 条字幕 `out_sec` 与 D15 `at_sec+dur_sec` 逐条一致"
                 "（`d16_out_mismatch_count` ＝ 0）—— 破的是「文档 vs 实际音频」这一轴"
                 "（V1–V11 与现有只读脚本均不覆盖该轴）。"
                 "**若这批音频用于出片，字幕将早于配音结束**"
                 "（D15 `mix` 明写「字幕不得早于配音起音，出点不早于配音收音」）。",
        "owner": "声音设计（D15 侧处置）＋ 台本编剧（2 条空间不足需缩文案）＋ "
                 "分镜导演（D16 `out_sec` 同步须走 S11 口径）＋ 企划合规（核销）",
        "blocks": "**不拦 U01 单元锁**（文档侧 0 不一致、U01 已锁且已核验）；"
                  "**拦成片阶段的字幕—配音对齐** —— 出片前必须清零",
        "priority": "高",
        "status": "已登记·已派返修单",
        "resolution": "2026-10-23 04:20 企划合规核销并派返修单（**裁决 S15**）。"
                      "**10 条分流处置**（可用 Δ ＝ min(镜窗末余量, 下一条字幕 in 余量, 45.0 片尾余量)）：\n\n"
                      "| 配音条目 | 镜位 | 实测标称 | D15 预算 | 需上调 | 可用 Δ | 处置路线 |\n"
                      "|---|---|---|---|---|---|---|\n"
                      f"{rows_md}\n\n"
                      "① **8 条空间允许** → 上调 D15 `dur_sec` 至实测标称值 ＋ D16 对应字幕 `out_sec` 同步 +Δ，"
                      "**走 S11 口径**（D16 的事件溯源字段 `sync_basis` **不改写**，只更新当前复核字段）；"
                      "同步后须过三关：**两两不重叠／不越 D07 段窗口／不越所属镜时段**。"
                      "② **2 条空间不足，必须缩短台词或提速** —— **ep2#4**（需 +1.2s，但镜窗末 45.0、"
                      "下一字幕 in 45.0，可用 Δ 仅 0.8）、**ep8#4**（需 +0.2s，但下一字幕 in 41.4 "
                      "恰在 `at+dur` 处，**可用 Δ ＝ 0.0**）→ 上调预算必然重叠，只能走**文案侧**"
                      "（改 D09／D08 台词后**重跑其生成脚本**，禁止只改 JSON）。"
                      "③ 处置只动 D15／D16／D08 的脚本与 JSON，**不得改 D16 已落盘的事件溯源字段**。"
                      "④ **复算证据**：处置后重跑只读比对脚本，**ERR 必须为 0**（或仅剩明确记录的 WARN）。"
                      "⑤ **边界**：本产线不合成新音频，处置只动文档侧；出片阶段的新合成音频仍归用户/出片工具侧。",
        "detected_by": "声音设计 2026-10-23 03:57（只读比对落盘）＋ 企划合规 2026-10-23 04:20 独立 ffprobe 复算复核",
    })
    d18["global_checks"].append({
        "id": "Q50",
        "item": "**「文档链内部零不一致」不等于「与实际产物一致」—— 预算/时码类契约必须对已落盘的实际产物"
                "做一次只读实测，不得以「文档自洽」结案** —— 本轮实证：D15↔D16 的 28 条配音—字幕时码"
                "逐条一致（0 mismatch）、所有跨文件核验全绿；但只读实测既有预演音频后发现 "
                "**10 条实际 TTS 超出 D15 `dur_sec` 预算**（最大 +1.2s）—— 破的是"
                "**「文档 vs 实际产物」这一轴，而该轴此前零覆盖**（V1–V11 不覆盖、现有只读脚本也不覆盖）。"
                "**做法**：① 凡结论写「零不一致」的跨文件契约，若存在**已落盘的实际产物**（音频/视频/帧），"
                "必须至少做**一次只读实测**（ffprobe/ffmpeg），**不得以文档自洽代替产物实测**；"
                "② 实测结论按**实测值**登记，缓存字段（如 `items.json` 的 `dur`）只作交叉提示、"
                "**不作判定输入**；③ 实测的**判定基准要写死**（0.1s 标称网格、向上取整、"
                "超出即 error／贴边 warn）；④ 实测发现的问题**必须派返修单到产物侧责任岗**，不得只登记不处置；"
                "⑤ 只读实测**不违反硬边界**（不合成、不生成、不付费），因此不必等到出片阶段才做 —— "
                "**处置更应前移到文档阶段**；⑥ 实测与文档不一致时，**先分清是「文档错」还是「产物超预算」**，"
                "两条路的责任岗不同（本轮属后者）。",
        "method": "对已落盘的实际产物做只读实测（ffprobe/ffmpeg）＋ 独立复算（不采信单方报告）＋ "
                  "以缓存字段交叉提示、实测值作判定输入",
        "source": "企划合规 2026-10-23 04:20（TOOL-04 只读比对实测 FAIL 的核销与独立复算）",
        "severity": "高（文档自洽但成片阶段契约会被打破，且该轴此前零覆盖）",
    })
    d18["version"] = "v1.42"
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    if "S15_TTS预算实测口径订正与10条分流处置" in prj["decisions"]:
        sys.exit("[ABORT] project.json decisions 已含 S15，不重复登记；不写盘。")
    prj["decisions"]["S15_TTS预算实测口径订正与10条分流处置"] = (
        "企划合规裁决（2026-10-23 04:20，TOOL-04 只读比对实测结果 FAIL 的核销）："
        "**① 口径订正（如实记）** —— 此前「TOOL-04 归口出片阶段、文档工厂侧不排期不做」**过重**："
        "只读比对**既不合成也不生成任何音频**（既有 U01 预演音频已在盘上），且**处置本身纯属文档工作**"
        "（改 D15 `dur_sec`／D16 `out_sec`，必要时改 D09·D08 台词）→ **比对与处置都归文档阶段**；"
        "只有**新合成音频**才归出片阶段。**硬边界不变**：不生成图片/视频/音频、不合成 TTS/BGM、"
        "不提交 H3 付费生成、不投流上架。"
        "**② 实测结论（以磁盘为准）**：28 条配音全测，**ERR 10／WARN 1／OK 17**，**D16 侧 0 不一致**；"
        "企划合规 04:20 独立 ffprobe 复算与声音设计报告**逐条一致**"
        "（并以 D09 原文校验配音↔台词映射零错位）→ 结论可信。"
        "**③ 10 条分流处置**：**8 条空间允许**（上调 D15 `dur_sec` ＋ D16 `out_sec` 同步，走 S11 口径："
        "事件溯源字段不改写）；**2 条空间不足必须缩文案**（**ep2#4** 需 +1.2s／可用 Δ 0.8；"
        "**ep8#4** 需 +0.2s／可用 Δ **0.0**）。"
        "**④ 处置后须复跑只读比对，ERR 归零**；**⑤ 不拦 U01 单元锁**（文档侧无缺陷），"
        "**拦成片阶段的字幕—配音对齐**。"
        "**Apply when**：任何「零不一致」结论，若存在已落盘的实际产物，必须补一次只读实测（Q50）；"
        "文档自洽 ≠ 产物合规。"
    )
    prj["updated_at"] = NOW
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引 ----------
    old_ver = "D18 **v1.41**（49 条 global_checks / 59 条 open_issues"
    new_ver = (f"D18 **v1.42**（{len(d18['global_checks'])} 条 global_checks / "
               f"{len(d18['open_issues'])} 条 open_issues")
    if old_ver in idx:
        idx = idx.replace(old_ver, new_ver)
    elif new_ver not in idx:
        sys.exit("[ABORT] 索引 §二 D18 版本提法旧串与新串均未命中；不写盘。")
    idx_heads = [l for l in idx.split("\n") if l.startswith("### 十·")]
    idx_nums = []
    for h in idx_heads:
        try:
            idx_nums.append(cn_to_int(h[6:].split(" ", 1)[0].strip()))
        except KeyError:
            pass
    idx_max = max(idx_nums)
    idx_new = int_to_cn(idx_max + 1)
    if f"### 十·{idx_new}" in idx:
        sys.exit(f"[ABORT] 索引已含 §十·{idx_new}；不写盘。")
    idx = idx.rstrip("\n") + "\n" + f"""
### 十·{idx_new} TOOL-04 实测结论核销（FAIL：10 条超预算）＋ U01-R18 ＋ Q50 ＋ S15 · D18 v1.42（**企划合规 2026-10-23 04:15–04:20**）

#### 1. 本轮最重要的发现：**「文档自洽」≠「与实际产物一致」**

声音设计 02:31 提请的 TOOL-04 比对**已于 03:57 执行完毕并落盘**，**verdict ＝ FAIL**：
28 条配音全测，**ERR 10／WARN 1／OK 17**；**D16 侧 `d16_out_mismatch_count` ＝ 0** ——
**文档链内部完全自洽**，破的是**「文档 vs 实际音频」这一轴**（此前零覆盖）。

**企划合规 04:20 独立用 ffprobe 复算 28 条**：ERR 10／WARN 1／OK 17，**与声音设计报告逐条一致**，
并以 D09 原文校验了配音↔台词的顺序映射（**零错位**）→ 结论可信。

#### 2. 本岗口径订正（如实记）：TOOL-04 原裁决过重

原裁决「归口出片阶段、文档工厂侧不排期不做」**过重** —— 只读比对**既不合成也不生成任何音频**
（既有 U01 预演音频在盘上），且**处置本身纯属文档工作** → **比对与处置都归文档阶段**；
只有**新合成音频**才归出片阶段。**硬边界不变**。登记于 `decisions.S15`。

#### 3. 10 条分流处置（U01-R18 · 已派返修单给声音设计）

| 配音条目 | 镜位 | 实测标称 | D15 预算 | 需上调 | 可用 Δ | 处置路线 |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {ref} | ep{e} 镜{sid} | {nom} | {bud} | **+{need}** | {avail} | {note} |" for ref, e, sid, nom, bud, need, avail, note in ERR10)}

- **8 条空间允许** → 上调 D15 `dur_sec` ＋ D16 `out_sec` 同步 +Δ（**走 S11 口径：事件溯源字段不改写**），
  同步后须过「两两不重叠／不越 D07 段窗口／不越所属镜时段」三关。
- **2 条空间不足，必须缩文案**：**ep2#4**（需 +1.2s／可用 Δ 0.8）、**ep8#4**（需 +0.2s／可用 Δ **0.0**）。
- 处置**只改脚本与 JSON**，禁止只改 JSON；**不得改 D16 的 `sync_basis` 事件溯源字段**。
- **不拦 U01 单元锁**（文档侧无缺陷）；**拦成片阶段的字幕—配音对齐**。

#### 4. 新判据 Q50

**「文档链内部零不一致」不等于「与实际产物一致」** —— 凡结论写「零不一致」的跨文件契约，
若存在**已落盘的实际产物**，必须至少做**一次只读实测**，不得以文档自洽结案；
实测结论按**实测值**登记（缓存字段只作交叉提示）；**判定基准要写死**；
实测发现的问题**必须派返修单**，不得只登记不处置；只读实测不越硬边界 → **处置前移到文档阶段**。

#### 5. 出口闸

`validate.mjs --unit U01` → **error 0 / 11-11 / warning 2**（既有项）；`--unit U02` → **error 0 / warning 12**（基线）；
`render-md.mjs` 单向重渲染；**U01 锁态未动**。
"""

    # ---------- D. 交付说明 ----------
    heads = [l for l in deliv.split("\n") if l.startswith("## ")]
    nums = []
    for h in heads:
        try:
            nums.append(cn_to_int(h[3:].split("、", 1)[0].strip()))
        except KeyError:
            pass
    max_n = max(nums)
    new_cn = int_to_cn(max_n + 1)
    if f"## {new_cn}、" in deliv:
        sys.exit(f"[ABORT] 交付说明已含 §{new_cn}；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + f"""
## {new_cn}、TOOL-04 实测结论核销（FAIL：10 条 TTS 超预算）＋ U01-R18 ＋ Q50 ＋ S15（**企划合规 2026-10-23 04:15–04:20**）

### {new_cn}.1 核心结论

TOOL-04 的只读比对**已于 03:57 执行完毕**（`preview/U01_tts/tts_budget_check_U01.json`，28,400 B），
**verdict ＝ FAIL**：28 条配音全测，**ERR 10／WARN 1／OK 17**；**D16 侧 0 不一致**。
**企划合规 04:20 独立 ffprobe 复算，与声音设计报告逐条一致**（并以 D09 原文校验配音↔台词映射零错位）。
→ **文档链内部自洽，但 10 条实际音频超出 D15 `dur_sec` 预算**：若这批音频用于出片，字幕将早于配音结束。

### {new_cn}.2 本岗口径订正（如实记）

原裁决「TOOL-04 归口出片阶段、文档工厂侧不排期不做」**过重**：只读比对不合成、不生成任何音频，
且处置纯属文档工作 → **比对与处置都归文档阶段**；只有**新合成音频**归出片阶段。硬边界不变（**S15**）。

### {new_cn}.3 10 条分流处置（U01-R18 · 已派返修单）

**8 条空间允许**（上调 D15 `dur_sec` ＋ D16 `out_sec` 同步，走 S11 口径）；
**2 条空间不足必须缩文案**（ep2#4 需 +1.2s／可用 Δ 0.8；ep8#4 需 +0.2s／可用 Δ **0.0**）。
**不拦 U01 单元锁**；**拦成片阶段的字幕—配音对齐**。处置后须复跑只读比对、**ERR 归零**。

### {new_cn}.4 新判据 Q50 ＋ 出口闸

**Q50**：文档链零不一致 ≠ 与实际产物一致；有已落盘实际产物必须做一次只读实测，
实测结论按实测值登记、判定基准写死、问题必须派单处置、只读实测不越硬边界故处置前移到文档阶段。
`validate --unit U01` → **11/11、error 0、warning 2**（既有项）；`--unit U02` → error 0（基线）。
本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）、本岗补丁脚本；
**未改**任何交付物 JSON、源素材、规格、工具脚本；未生成图片／视频／音频，未合成 TTS，未提交 H3 付费生成，未投流上架。
"""

    # ---------- E. 自检 ----------
    for k in ("U01-R18", "Q50", "已执行·FAIL·10 条超预算"):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S15_TTS预算实测口径订正与10条分流处置" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S15；不写盘。")
    if idx.count(f"### 十·{idx_new}") != 1:
        sys.exit(f"[ABORT] 索引 §十·{idx_new} 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 v1.41→v1.42（TOOL-04 升级 ＋ U01-R18 ＋ Q50）；project.json（+S15）；"
              f"索引 §二 1 处 ＋ §十·{idx_new}；交付说明 §{new_cn}")
        return

    write(p18, d18_out)
    write(p_prj, prj_out)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] TOOL-04 实测结论核销完成")
    print(f"   shared/D18.json：v1.41 → {d18['version']}（TOOL-04 升级 ＋ U01-R18 ＋ Q50；"
          f"gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：+S15_TTS预算实测口径订正与10条分流处置；updated_at → {NOW}")
    print(f"   00_项目索引.md：§二 版本提法 ＋ §十·{idx_new}")
    print(f"   99_交付说明.md：新增 §{new_cn}")


if __name__ == "__main__":
    main()
