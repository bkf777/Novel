#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_u01r18_split_correction_0445.py —— U01-R18 分流订正 + Q51 + U01-R19 + S16
（企划合规，2026-10-23 04:45）

订正什么、为什么必须订正
------------------------
本岗 04:15–04:20 首记 U01-R18 时，把 10 条超预算条目分流为「**8 条空间允许 ／ 2 条空间不足**」，
并据此给 ep2#4 与 ep8#4 都判了「须缩文案」。**04:45 独立复算证明该分流有误**，订正为
「**9 条走方案 A ／ 1 条走文案侧（仅 ep2#4）**」。

两处错因（都写进台账，不藏）：
  ① **把「零余量」误判成「空间不足」** —— ep8#4 的可用 Δ ＝ 0.0 的真实含义是
     「新出点 41.4 与下一条面板文字 in 41.4 **恰好相接**」，按区间左闭右开（Q51）**不算重叠**；
     首记用了「相接算重叠」的更严口径，却没写明判据，导致同一条数据被算成两种结论。
  ② **漏查片尾标题卡** —— ep2#4 的新出点 44.2 会压到片尾标题卡（in=43，position
     「底部字幕区，叠在最后一镜末段上」，**与对白同带 → 真实视觉冲突**），这是它真正受阻的原因；
     首记的「可用 Δ 0.8」口径没把片尾算进去。

判据来源（可复算）：本岗 04:35 只读复算脚本 `scripts/plan_u01r18_tts_reconcile.py`
——三向映射（items↔D16 对白↔D15 配音）28 条**零错位**，逐条复核越窗／跨硬切／正文重叠／片尾重叠四关。

本脚本做六件事（命中数断言，对不上即中止不写盘）：
  A. D18 v1.42 → v1.43：改写 U01-R18 的 `owner`／`resolution`（**显式声明首记 8/2 作废**，不静默改写）；
     TOOL-04 `resolution` 追加订正溯源；新增 global_check **Q51**、新增 open_issue **U01-R19**。
  B. project.json：S15 **追加**订正子句（不改写原裁决原文）；新增 decisions **S16**。
  C. 00_项目索引.md：新增 §十·N（订正节，**不改写 §十·三十六 原节**，只指向它）。
  D. 99_交付说明.md：新增 §N（订正节，同上）。
  E. 三份返修单已派（batch_2fd55abc2d82）：声音设计①/分镜导演②/台本编剧③。

用法：python3 scripts/patch_u01r18_split_correction_0445.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 04:45"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}

# 9 条方案 A（企划合规 04:35 只读复算，四关全过）
PLAN_A = [
    ("D09 ep1 #1", "ep1 镜1", 1.6, 1.9, "seq6", 12.0, 12.3, 1.9),
    ("D09 ep2 #2", "ep2 镜2", 2.2, 2.8, "seq6", 21.2, 21.8, 2.8),
    ("D09 ep2 #3", "ep2 镜3", 1.4, 1.7, "seq7", 36.4, 36.7, 1.7),
    ("D09 ep3 #2", "ep3 镜3", 2.0, 2.6, "seq8", 32.5, 33.1, 2.6),
    ("D09 ep5 #1", "ep5 镜2", 2.6, 2.7, "seq5", 15.6, 15.7, 2.7),
    ("D09 ep5 #2", "ep5 镜2", 2.2, 2.7, "seq6", 19.6, 20.1, 2.7),
    ("D09 ep5 #4", "ep5 镜4", 1.4, 1.6, "seq8", 41.4, 41.6, 1.6),
    ("D09 ep8 #1", "ep8 镜1", 2.0, 2.2, "seq5", 4.0, 4.2, 2.2),
    ("D09 ep8 #4", "ep8 镜4", 2.6, 2.8, "seq8", 41.2, 41.4, 2.8),
]
BLOCKED = ("D09 ep2 #4", "ep2 镜4", 1.8, 3.0, "seq9", 43.0, 44.2, 3.0)


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
           ("零一二三四五六七八九"[tail] if tail else 0)


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
    p_plan = os.path.join(proj, "scripts", "plan_u01r18_tts_reconcile.py")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检 ----------
    if not os.path.isfile(p_plan):
        sys.exit(f"[ABORT] 04:35 复算脚本不存在：{p_plan}；不写盘。")
    if d18.get("version") != "v1.42":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.42；不写盘。")

    oi = {o["id"]: o for o in d18["open_issues"]}
    if "U01-R18" not in oi:
        sys.exit("[ABORT] open_issues 无 U01-R18；不写盘。")
    if "U01-R19" in oi:
        sys.exit("[ABORT] open_issues 已含 U01-R19，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if "Q51" in gc_ids:
        sys.exit("[ABORT] global_checks 已含 Q51，不重复登记；不写盘。")
    if gc_ids[-1] != "Q50":
        sys.exit(f"[ABORT] global_checks 末条为 {gc_ids[-1]}，期望 Q50；不写盘。")

    r18 = oi["U01-R18"]
    old_res = r18.get("resolution", "")
    if "**8 条空间允许**" not in old_res or "**2 条空间不足" not in old_res:
        sys.exit("[ABORT] U01-R18.resolution 不含待订正的「8 条空间允许／2 条空间不足」原文；不写盘。")
    old_owner = r18.get("owner", "")
    if "2 条空间不足需缩文案" not in old_owner:
        sys.exit("[ABORT] U01-R18.owner 不含待订正的「2 条空间不足需缩文案」原文；不写盘。")

    if "S16_字幕区间口径统一与重叠检查覆盖口径" in prj["decisions"]:
        sys.exit("[ABORT] project.json decisions 已含 S16，不重复登记；不写盘。")
    s15 = prj["decisions"]["S15_TTS预算实测口径订正与10条分流处置"]
    if "2 条空间不足必须缩文案" not in s15:
        sys.exit("[ABORT] S15 不含待订正的「2 条空间不足必须缩文案」原文；不写盘。")

    # ---------- A. D18 ----------
    r18["owner"] = ("声音设计（D15 侧 9 条 `dur_sec` 上调）＋ 台本编剧（**1 条**空间不足需缩文案：ep2 #4）＋ "
                    "分镜导演（D16 `out_sec` 同步 ＋ 区间口径写死，须走 S11 口径）＋ 企划合规（核销）")
    r18["status"] = "已登记·已派返修单（batch_2fd55abc2d82）·04:45 分流订正"

    plan_rows = "\n".join(
        f"| {ref} | {shot} | {bud} | {nom} | **{nom}** | {seq} | **{nout}** | {dwell} | 全过 |"
        for ref, shot, bud, nom, seq, oout, nout, dwell in PLAN_A
    )
    new_res = (
        "2026-10-23 04:20 企划合规核销并派返修单（**裁决 S15**）。\n\n"
        "**⚠️ 2026-10-23 04:45 订正：04:15 首记的「8 条空间允许 ／ 2 条空间不足」分流作废**，"
        "订正为 **9 条走方案 A ／ 1 条走文案侧（仅 ep2#4）**。**作废理由（两处错因，如实记）**：\n"
        "　① **把「零余量」误判成「空间不足」** —— ep8#4 的可用 Δ ＝ 0.0 的真实含义是"
        "「新出点 41.4 与下一条面板文字 in 41.4 **恰好相接**」，按区间左闭右开（判据见 **Q51**）**不算重叠**；"
        "首记采用了「相接算重叠」的更严口径却**未写明判据**，于是同一条数据被算出了两套结论。\n"
        "　② **漏查片尾标题卡** —— ep2#4 的新出点 44.2 会压到 **片尾标题卡（in=43，position「底部字幕区，"
        "叠在最后一镜末段上」，与对白同带 → 真实视觉冲突）**；这才是它真正受阻的原因，"
        "首记的「可用 Δ 0.8」口径没有把片尾算进去。\n"
        "　**订正依据**：企划合规 04:35 只读复算脚本 `scripts/plan_u01r18_tts_reconcile.py` —— "
        "三向映射（items↔D16 对白↔D15 配音）28 条**零错位**，逐条复核越窗／跨硬切／正文重叠／片尾重叠四关。\n\n"
        "**订正后的 9 条方案 A**（上调 D15 `dur_sec` 至实测标称值 ＋ 同步 D16 对应字幕 `out_sec`）：\n\n"
        "| 配音条目 | 镜位 | D15 预算 | 实测标称 | 新 `dur_sec` | D16 seq | 新 `out_sec` | 停留 | 四关复核 |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        f"{plan_rows}\n\n"
        "　ep8#4 的新出点 41.4 与下一条面板文字 in 41.4 **相接**，按 Q51 口径**不重叠**，且恰是"
        "「台词收尾＝面板刷新」的设计同刻（音频止 41.400 ＝ 面板文字 in 41.4），故无需缩文案。\n\n"
        "**1 条走文案侧（ep2#4）**：新出点 44.2 会压到片尾标题卡（同带 → 真实视觉冲突）；"
        "**前移无处可退**（镜4 起点 40.0 是钟声起音、D15 sfx「钟声连响」40.0/4.4s；40.0–41.2 是 D08 body 里的"
        "钟声说明字幕「全城钟楼敲响十一下。」，占 D08 字数结构）；**提速 1.56× 不可接受** → "
        "**只能缩文案**（目标实测 ≤1.5s，预算 1.8s 留 0.3s 余量）。\n\n"
        "① 9 条上调须过三关：**两两不重叠／不越 D07 段窗口／不越所属镜时段**，并经**片尾标题卡单独检查**（Q51）。\n"
        "② 走 **S11 口径**：D16 的事件溯源字段 `sync_basis` **只追加不覆盖**（v1.1 收敛事件保留），"
        "只更新当前复核字段 `verified_against_d15` → D15 **v1.4**。\n"
        "③ 处置只动 D15／D16／D08 的**生成脚本与 JSON**，禁止只改 JSON；**不得改 D16 已落盘的事件溯源字段**。\n"
        "④ **复算证据**：处置后重跑只读比对脚本，**ERR 必须为 0**（或仅剩明确记录的 WARN）。"
        "**当前预期**：9 条上调后 ERR 10 → **1**（仅剩 ep2#4，缩文案＋重合成后再归零）。\n"
        "⑤ **边界**：本产线不合成新音频，处置只动文档侧；出片阶段的新合成音频仍归用户/出片工具侧。\n"
        "⑥ **派单**：batch_2fd55abc2d82（① 声音设计 D15 侧 ／ ② 分镜导演 D16 侧＋脚本缺口 ／ ③ 台本编剧 文案侧）。"
    )
    r18["resolution"] = new_res

    t4 = oi["TOOL-04"]
    if "04:45 订正" not in t4.get("resolution", ""):
        t4["resolution"] = t4["resolution"].rstrip() + (
            "　**2026-10-23 04:45 补充溯源**：该结论经本岗 04:35 只读复算脚本"
            "（`scripts/plan_u01r18_tts_reconcile.py`）逐条复核，ERR 10／WARN 1／OK 17 **与本结论一致**；"
            "但**处置分流**在此轮被订正（首记 8/2 → 订正 **9/1**，且新增判据 **Q51** 与 **U01-R19**），"
            "**本条的实测结论本身不变**。"
        )

    d18["open_issues"].append({
        "id": "U01-R19",
        "issue": "**分镜导演脚本 `scripts/reconcile_tts_actual_vs_d15_budget.mjs` 的 A3 重叠检查存在覆盖缺口 → "
                 "「方案 A 零破口」的结论对 ep2 seq9 不成立** —— 该脚本的重叠候选集 `rows` "
                 "**只含 `type === \"对白\"` 的字幕行**，**漏掉「字幕」「面板文字」「片尾」**；"
                 "因此 ep2 seq9（新出点 44.2 会压到片尾标题卡 in=43，片尾与对白**同在底部字幕区**）"
                 "**根本没进检查视野**，被报成「零破口」。"
                 "**附带问题**：同一批数据仓库里存在两套判据 —— `apply_d15_d16_sync.py` 用 "
                 "`new_out >= nxt_in`（**相接算重叠**）、本脚本用 `new_out > nxt_in`（**相接不算重叠**），"
                 "且**两处判据都没写进被检查的交付物**，只有一个脚本头的注释 —— "
                 "于是同一条数据能被算成两个结论（U01-R18 首记即因此把 ep8#4 误判为空间不足）。",
        "owner": "分镜导演（脚本修复）＋ 企划合规（判据统一与验收）",
        "blocks": "**不拦 U01 单元锁**；**拦「拿该脚本的「零破口」结论直接做处置决策」** —— "
                  "该结论在修好覆盖缺口前，对含片尾/面板文字/字幕的行不可信",
        "priority": "中",
        "status": "已登记·已派返修单（随 U01-R18 返修单② 第③项）",
        "resolution": "2026-10-23 04:45 企划合规登记并随返修单②派单（batch_2fd55abc2d82）。**修复要求**：\n"
                      "① **A3 候选集**改为全部**正文行**（排除 片头／片尾／角标），按 `in_sec` 排序；\n"
                      "② **片尾标题卡单独检查**（`newOut > 片尾.in_sec` → 冲突，因其 position 为"
                      "「底部字幕区，叠在最后一镜末段上」，与对白同带）；\n"
                      "③ **脚本头写死区间口径**：「字幕区间为左闭右开 [in_sec, out_sec)；后一条字幕的 in_sec "
                      "**严格大于**前一条 out_sec 即为不重叠，**相接（in == 前一条 out）不算重叠**」；\n"
                      "④ 与 `apply_d15_d16_sync.py` 的 `>=` **统一为 `>`**，并注明理由 —— "
                      "轮 1 那 11 条是按更严的 `>=` 通过的，必然同时满足 `>`，"
                      "**故本次放宽不会使任何在盘数据失格**（不得反过来说「放宽是为了让 ep8#4 通过」）；\n"
                      "⑤ 口径须**同时写进 D16 `subtitle_style.sync_rule`**（交付物本体），"
                      "**不许只存在于某个人的脚本里**（Q51）。\n"
                      "**复跑判据**：修好后重跑脚本，ep2 seq9 **必须**被新增的片尾检查抓出，"
                      "其余 9 条仍全过；结论贴回台账。",
        "detected_by": "企划合规 2026-10-23 04:45（本岗只读复算时发现两份脚本判据不一致与覆盖缺口）",
    })

    d18["global_checks"].append({
        "id": "Q51",
        "item": "**字幕区间口径必须写死；重叠检查的候选集必须覆盖全部正文行，且片尾标题卡须单独检查** —— "
                "本轮实证：同一批数据，仓库里两个脚本给出两套判据"
                "（`apply_d15_d16_sync.py` 用 `new_out >= nxt_in` ＝ **相接算重叠**；"
                "`reconcile_tts_actual_vs_d15_budget.mjs` 用 `new_out > nxt_in` ＝ **相接不算重叠**），"
                "且后者的候选集只含「对白」、**漏掉「字幕」「面板文字」「片尾」** —— "
                "结果：ep2 seq9（会压到片尾标题卡）被漏检报成「零破口」，"
                "ep8#4（与面板文字**恰好相接**）被算成「空间不足·须缩文案」，**同一条数据两个结论**。"
                "**做法**：① 区间口径**统一写死**为**左闭右开 [in_sec, out_sec)** —— "
                "后一条字幕的 `in_sec` **严格大于**前一条 `out_sec` 即不重叠，**相接不算重叠**"
                "（视频渲染上 A 在 out 时刻结束、B 同一时刻开始，不共帧）；"
                "② 该放宽**不得反向使用**：轮 1 那 11 条按更严的 `>=` 通过，必然同时满足 `>`，"
                "**故放宽不使任何在盘数据失格**（放宽是为了统一口径，不是为了让某条通过）；"
                "③ 重叠检查候选集＝**全部正文行**（排除 片头／片尾／角标，按 `in_sec` 排序）；"
                "④ **片尾标题卡须单独检查**（其 position 与对白同在底部字幕区，是真实视觉冲突）；"
                "⑤ **口径必须写进被检查的交付物本体**（D16 `subtitle_style.sync_rule`）＋ 脚本头注释 —— "
                "**不许只活在某个人的脚本里**，否则下一个读的人会得出另一套结论（Q50 同源）。",
        "method": "只读复算时把「两份脚本的判据并排列出」＋「逐条四关复核（越窗/跨硬切/正文重叠/片尾重叠）」，"
                  "而不是直接采信任一份脚本的总结论",
        "source": "企划合规 2026-10-23 04:45（U01-R18 分流订正的错因分析）",
        "severity": "中（不产生错交付物，但会让同一数据得出两个结论；本轮已实际导致一次误判）",
    })
    d18["version"] = "v1.43"
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj["decisions"]["S15_TTS预算实测口径订正与10条分流处置"] = s15.rstrip() + (
        "　**2026-10-23 04:45 订正子句（不改写上方原文，仅声明其分流部分作废）**："
        "上方第 ③ 项「**2 条空间不足必须缩文案**（ep2#4 需 +1.2s／可用 Δ 0.8；ep8#4 需 +0.2s／可用 Δ **0.0**）」"
        "**分流作废**，订正为 **1 条走文案侧（仅 ep2#4）**、**9 条走方案 A**。"
        "作废理由：① 首记把「零余量」误判成「空间不足」—— ep8#4 的 Δ ＝ 0.0 实为"
        "「新出点 41.4 与下一条面板文字 in 41.4 **恰好相接**」，按区间左闭右开（**S16／Q51**）**不算重叠**；"
        "② 首记**漏查片尾标题卡** —— ep2#4 新出点 44.2 压到片尾（in=43，position「底部字幕区，叠在最后一镜末段上」，"
        "与对白同带 → 真实视觉冲突），这才是它真正受阻的原因。"
        "**订正依据**：企划合规 04:35 只读复算 `scripts/plan_u01r18_tts_reconcile.py`（三向映射 28 条零错位，"
        "四关逐条复核）。**本裁决的其余部分（口径订正、实测结论、闭环判据、边界）全部维持不变。**"
    )
    prj["decisions"]["S16_字幕区间口径统一与重叠检查覆盖口径"] = (
        "企划合规裁决（2026-10-23 04:45，U01-R18 分流订正的错因收口，配套 **Q51**／**U01-R19**）：\n"
        "**① 区间口径统一并写死** —— 字幕区间为**左闭右开 [in_sec, out_sec)**；"
        "后一条字幕的 `in_sec` **严格大于**前一条 `out_sec` 即为不重叠，**相接（in == 前一条 out）不算重叠**"
        "（视频渲染上 A 在 out 时刻结束、B 同一时刻开始，不共帧）。"
        "**② 该放宽只用于统一口径，不得反向使用** —— 轮 1 那 11 条是按更严的 `>=`（相接算重叠）通过的，"
        "必然同时满足 `>`，**故本次统一不会使任何在盘数据失格**。"
        "**③ 重叠检查候选集**＝**全部正文行**（排除 片头／片尾／角标，按 `in_sec` 排序）；"
        "**片尾标题卡须单独检查**（其 position 为「底部字幕区，叠在最后一镜末段上」，与对白同带 → 真实视觉冲突）。"
        "**④ 口径必须落进交付物本体** —— 写入 D16 `subtitle_style.sync_rule` 与各脚本头注释，"
        "**不许只活在某个人的脚本里**（Q50 同源：凡有阈值必写死判定基准与容差）。"
        "**Apply when**：任何「两两不重叠」「不越窗」「不越切」类时码校验；"
        "任何同一批数据被两个脚本判成两个结论时，先查判据是否一致，再查候选集是否有缺口。"
    )
    prj["updated_at"] = NOW
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引 ----------
    old_ver = "D18 **v1.42**（50 条 global_checks / 60 条 open_issues"
    new_ver = (f"D18 **v1.43**（{len(d18['global_checks'])} 条 global_checks / "
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
    idx_new = int_to_cn(max(idx_nums) + 1)
    if f"### 十·{idx_new}" in idx:
        sys.exit(f"[ABORT] 索引已含 §十·{idx_new}；不写盘。")
    idx = idx.rstrip("\n") + "\n" + f"""
### 十·{idx_new} U01-R18 分流订正（8/2 → **9/1**）＋ Q51 ＋ U01-R19 · D18 v1.43（**企划合规 2026-10-23 04:45**）

#### 1. 订正什么

§十·三十六 首记的 U01-R18 分流「**8 条空间允许 ／ 2 条空间不足（ep2#4、ep8#4）**」**作废**，
订正为 **9 条走方案 A ／ 1 条走文案侧（仅 ep2#4）**。

#### 2. 两处错因（如实记，不藏）

① **把「零余量」误判成「空间不足」** —— ep8#4 的可用 Δ ＝ 0.0 的真实含义是
「新出点 41.4 与下一条面板文字 in 41.4 **恰好相接**」，按区间左闭右开（**Q51**）**不算重叠**；
首记用了「相接算重叠」的更严口径却**没写明判据**，同一条数据于是被算出了两套结论。
② **漏查片尾标题卡** —— ep2#4 新出点 44.2 会压到片尾（in=43，position「底部字幕区，叠在最后一镜末段上」，
与对白同带 → **真实视觉冲突**），这才是它真正受阻的原因。

**订正依据**：04:35 只读复算 `scripts/plan_u01r18_tts_reconcile.py` —— 三向映射 28 条**零错位**，
逐条复核越窗／跨硬切／正文重叠／片尾重叠四关。

#### 3. 订正后的 9 条方案 A

| 配音条目 | 镜位 | D15 预算 | 实测标称 | 新 `dur_sec` | D16 seq | 新 `out_sec` | 停留 |
|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {ref} | {shot} | {bud} | {nom} | **{nom}** | {seq} | **{nout}** | {dwell} |" for ref, shot, bud, nom, seq, oout, nout, dwell in PLAN_A)}

**1 条走文案侧**：ep2#4（{BLOCKED[1]}，预算 {BLOCKED[2]} → 实测标称 {BLOCKED[3]}，新出点 {BLOCKED[6]}）——
前移无处可退（镜4 起点 40.0 是钟声起音、40.0–41.2 是钟声说明字幕且占 D08 字数结构）、提速 1.56× 不可接受
→ **只能缩文案**（目标实测 ≤1.5s）。

#### 4. 新判据 Q51 ＋ 新缺陷 U01-R19

- **Q51**：字幕区间口径必须写死（**左闭右开 [in, out)，相接不算重叠**）；重叠检查候选集须覆盖**全部正文行**；
  **片尾标题卡须单独检查**；口径必须**落进交付物本体**（D16 `sync_rule`），不许只活在某个人的脚本里。
  该放宽**只用于统一口径**（轮 1 那 11 条按更严的 `>=` 通过，必然满足 `>`，**不使在盘数据失格**）。
- **U01-R19**：分镜导演 `reconcile_tts_actual_vs_d15_budget.mjs` 的 A3 候选集只含「对白」、
  **漏掉「字幕」「面板文字」「片尾」**，导致 ep2 seq9 被漏检；已随返修单②派单修复。

#### 5. 派单与出口闸

三份返修单已派（**batch_2fd55abc2d82**）：① 声音设计（D15 9 条 `dur_sec`＋口径文本）② 分镜导演
（D16 9 行 `out_sec`＋区间口径写死＋脚本缺口）③ 台本编剧（ep2#4 缩文案）。
出口闸 `validate.mjs --unit U01` → **11/11、error 0、warning 2**（既有项）；`--unit U02` → **error 0**（基线）。
**U01 锁态未动**；本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）、
本岗只读复算脚本；**未改**任何交付物 JSON、源素材、规格、工具脚本。
"""

    # ---------- D. 交付说明 ----------
    heads = [l for l in deliv.split("\n") if l.startswith("## ")]
    nums = []
    for h in heads:
        try:
            nums.append(cn_to_int(h[3:].split("、", 1)[0].strip()))
        except KeyError:
            pass
    new_cn = int_to_cn(max(nums) + 1)
    if f"## {new_cn}、" in deliv:
        sys.exit(f"[ABORT] 交付说明已含 §{new_cn}；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + f"""
## {new_cn}、U01-R18 分流订正（8/2 → **9/1**）＋ Q51 ＋ U01-R19 · S16（**企划合规 2026-10-23 04:45**）

### {new_cn}.1 订正结论

§五十一 首记的 U01-R18 分流「**8 条空间允许 ／ 2 条空间不足**」**作废**，订正为
**9 条走方案 A ／ 1 条走文案侧（仅 ep2#4）**。**实测结论本身不变**（ERR 10／WARN 1／OK 17 仍成立），
订正的只是**处置分流**。

### {new_cn}.2 两处错因

① 「零余量」被误判为「空间不足」—— ep8#4 的 Δ ＝ 0.0 实为「与下一条面板文字**恰好相接**」，
按左闭右开**不算重叠**；② **漏查片尾标题卡** —— ep2#4 新出点 44.2 压到片尾（同带 → 真实视觉冲突）。
**订正依据**：04:35 只读复算 `scripts/plan_u01r18_tts_reconcile.py`（28 条三向映射零错位，四关逐条复核）。

### {new_cn}.3 9 条方案 A（可上调 D15 `dur_sec` ＋ 同步 D16 `out_sec`）

{chr(10).join(f"- {ref}（{shot}）：D15 预算 {bud} → **{nom}**；D16 {seq} out_sec {oout} → **{nout}**（停留 {dwell}s，四关全过）" for ref, shot, bud, nom, seq, oout, nout, dwell in PLAN_A)}

**1 条走文案侧**：ep2#4 —— 前移无处可退、提速不可接受 → **缩文案**（目标实测 ≤1.5s，预算 1.8s 留余量）。

### {new_cn}.4 新判据 Q51 ＋ 新缺陷 U01-R19 ＋ 出口闸

**Q51**：区间口径写死为左闭右开 [in, out)（相接不算重叠）；重叠检查候选集覆盖全部正文行；
片尾标题卡单独检查；口径落进 D16 `sync_rule`。**U01-R19**：分镜导演脚本 A3 候选集缺口，已随返修单②派单。
派单 **batch_2fd55abc2d82**（① 声音设计 ② 分镜导演 ③ 台本编剧）。
出口闸 `validate --unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **error 0**。**U01 锁态未动**。
本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）、本岗只读复算脚本。
"""

    # ---------- E. 自检 ----------
    for k in ("U01-R19", "Q51", "订正后的 9 条方案 A"):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "8 条空间允许 ／ 2 条空间不足" not in d18_out:
        sys.exit("[ABORT] D18 未记录首记作废声明；不写盘。")
    if "S16_字幕区间口径统一与重叠检查覆盖口径" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S16；不写盘。")
    if "订正子句" not in prj_out:
        sys.exit("[ABORT] project.json 未记录 S15 订正子句；不写盘。")
    if idx.count(f"### 十·{idx_new}") != 1:
        sys.exit(f"[ABORT] 索引 §十·{idx_new} 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 v1.42→v1.43（U01-R18 分流订正 8/2→9/1 ＋ TOOL-04 溯源 ＋ Q51 ＋ U01-R19）；"
              f"project.json（S15 订正子句 ＋ S16）；索引 §二 1 处 ＋ §十·{idx_new}；交付说明 §{new_cn}")
        return

    write(p18, d18_out)
    write(p_prj, prj_out)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] U01-R18 分流订正完成")
    print(f"   shared/D18.json：v1.42 → {d18['version']}（U01-R18 订正 ＋ TOOL-04 溯源 ＋ Q51 ＋ U01-R19；"
          f"gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：S15 追加订正子句 ＋ S16；updated_at → {NOW}")
    print(f"   00_项目索引.md：§二 版本提法 ＋ §十·{idx_new}")
    print(f"   99_交付说明.md：新增 §{new_cn}")


if __name__ == "__main__":
    main()
