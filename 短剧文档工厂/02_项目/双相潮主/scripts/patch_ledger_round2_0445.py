#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ledger_round2_0445.py —— 本轮核销与新登记（D18 v1.43 → v1.44）

派活：企划合规，2026-10-23 04:45–04:55。本轮是「四岗回报后的集中核销 + 一个共享工具缺陷的修复」。

本脚本做七件事（命中数断言，对不上即中止不写盘）：
  A. D18 v1.43 → v1.44：
     · U01-R19 **核销闭环**（分镜导演已修 reconcile 脚本，企划合规 04:42 复核通过）；
     · U01-R18 **追加**第二波与「终表数值」（预算取实测标称+0.1 消贴边）；
     · 新增 open_issue **U02-R09**（U02 D11 ep014 镜3 契约冲突 → 已由分镜导演修复）；
     · 新增 open_issue **U01-R20**（分镜导演转派的 C-019/C-031 **已闭环不成立** → 不派；
       唯一残留 ep5 镜3 negatives 张力 → 派视觉设定）；
     · 新增 open_issue **OPS-13**（validate.mjs 无 --unit 混装缺陷 → **已修**）；
     · 新增 global_check **Q52**（跨单元聚合必须显式声明作用域）。
  B. project.json：新增 decisions **S17_共享校验器单元作用域修复裁定**。
  C. 00_团队章程.md：§四·五 补多单元校验语义；§九 新增 **v2.4 工具侧**变更条目。
  D. 04_工具/validate.mjs：**已就地修复**（本脚本只登记，不改代码）。
  E. 00_项目索引.md：新增 §十·N。
  F. 99_交付说明.md：新增 §N。
  G. 出口闸复跑记录（U01 / U02 / 全项目）。

用法：python3 scripts/patch_ledger_round2_0445.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 04:55"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}

# 终表：9 条（8 条 +0.1 消贴边；ep8#4 Δ=0 只能贴边）
FINAL9 = [
    ("D09 ep1 #1", "ep1 镜1", 10.4, 1.9, 2.0, "seq6", 12.0, 12.4),
    ("D09 ep2 #2", "ep2 镜2", 19.0, 2.8, 2.9, "seq6", 21.2, 21.9),
    ("D09 ep2 #3", "ep2 镜3", 35.0, 1.7, 1.8, "seq7", 36.4, 36.8),
    ("D09 ep3 #2", "ep3 镜3", 30.5, 2.6, 2.7, "seq8", 32.5, 33.2),
    ("D09 ep5 #1", "ep5 镜2", 13.0, 2.7, 2.8, "seq5", 15.6, 15.8),
    ("D09 ep5 #2", "ep5 镜2", 17.4, 2.7, 2.8, "seq6", 19.6, 20.2),
    ("D09 ep5 #4", "ep5 镜4", 40.0, 1.6, 1.7, "seq8", 41.4, 41.7),
    ("D09 ep8 #1", "ep8 镜1", 2.0, 2.2, 2.3, "seq5", 4.0, 4.3),
    ("D09 ep8 #4", "ep8 镜4", 38.6, 2.8, 2.8, "seq8", 41.2, 41.4),
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
    p_charter = os.path.join(factory, "00_团队章程.md")
    p_val = os.path.join(factory, "04_工具", "validate.mjs")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)
    charter = read(p_charter)
    val_src = read(p_val)

    # ---------- 证据自检 ----------
    if not os.path.isfile(p_val):
        sys.exit(f"[ABORT] 校验器不存在：{p_val}；不写盘。")
    if "逐单元独立校验，不跨单元合并" not in val_src:
        sys.exit("[ABORT] validate.mjs 不含「逐单元独立校验」标记，修复未在盘；不写盘。")
    if "const unitReports = []" not in val_src or "function runRulesFor" not in val_src:
        sys.exit("[ABORT] validate.mjs 缺逐单元收集/独立跑规则标记；不写盘。")
    if d18.get("version") != "v1.43":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.43；不写盘。")

    oi = {o["id"]: o for o in d18["open_issues"]}
    for i in ("U02-R09", "U01-R20", "OPS-13"):
        if i in oi:
            sys.exit(f"[ABORT] open_issues 已含 {i}，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if "Q52" in gc_ids:
        sys.exit("[ABORT] global_checks 已含 Q52，不重复登记；不写盘。")
    if gc_ids[-1] != "Q51":
        sys.exit(f"[ABORT] global_checks 末条为 {gc_ids[-1]}，期望 Q51；不写盘。")
    if "U01-R19" not in oi:
        sys.exit("[ABORT] open_issues 无 U01-R19；不写盘。")
    if "已派返修单（随 U01-R18 返修单② 第③项）" not in oi["U01-R19"].get("status", ""):
        sys.exit("[ABORT] U01-R19.status 不符预期；不写盘。")
    if "S17_共享校验器单元作用域修复裁定" in prj["decisions"]:
        sys.exit("[ABORT] project.json decisions 已含 S17，不重复登记；不写盘。")
    if "v2.4 工具侧" in charter:
        sys.exit("[ABORT] 团队章程已含 v2.4 工具侧条目，不重复登记；不写盘。")

    # ---------- A. D18 ----------
    # A1 U01-R19 核销
    oi["U01-R19"]["status"] = "已修复·已复核·闭环"
    oi["U01-R19"]["resolution"] = oi["U01-R19"]["resolution"].rstrip() + (
        "　**2026-10-23 04:42 企划合规复核通过 → 核销闭环**：分镜导演 04:37–04:40 已修 "
        "`scripts/reconcile_tts_actual_vs_d15_budget.mjs` —— 脚本头写死「左闭右开 [in, out)、相接不算重叠」、"
        "A3 候选集改为**全部正文行（排除 片头/片尾/角标）实测 35 条**、**片尾标题卡 8 张单独检查**；"
        "企划合规 04:42 重跑，**ep2 seq9 被新检查抓出**（新出点 44.2 > 片尾标题卡 in 43，同在底部字幕区＝真实视觉冲突），"
        "并报出「最小间隔 0s（ep8 seq8）」→ **与本岗 04:35 独立复算逐条一致**。"
        "**闭环判据达成**：该脚本的「零破口」结论自此对含片尾/面板文字/字幕的行可信。"
    )

    # A2 U01-R18 追加第二波与终表
    oi["U01-R18"]["resolution"] = oi["U01-R18"]["resolution"].rstrip() + (
        "　**2026-10-23 04:45–04:55 第二波启动（终表数值，以本表为准）**："
        "① **文案侧已完成** —— 台本编剧 04:30 落盘 **D08 U01 v1.9 / D09 U01 v1.5**，ep2#4 由"
        "「两小时五十八分……换我用了。」压缩为「**换我用了。**」（4 字，预估 ≈1.1s；钟声字幕行**一字未动**，"
        "ep2 字数 base 211→204 仍在 band 内；D09 subtext 已改写并记明缩文案依据）。"
        "② **终表数值修订** —— 首记与首轮派单取「实测标称」作预算，会留下 **9 条贴边 WARN**；"
        "04:45 复算后改为 **8 条取「实测标称 + 0.1」**（实测标称 < 预算 → 判定**合规 OK** 而非贴边 WARN，"
        "留 0.1s 余量抗重合成漂移），**ep8#4 例外只能贴边**（其 +0.1 会与下一条面板文字 in 41.4 **重叠 0.1s**，"
        "而 out 41.4 与其**恰好相接**，按 Q51 左闭右开不算重叠）。**前两轮派单的表格作废，以本表为准**：\n\n"
        "| 配音条目 | 镜位 | at_sec | 实测标称 | D15 新 `dur_sec` | D16 seq | D16 新 `out_sec` |\n"
        "|---|---|---|---|---|---|---|\n"
        + "\n".join(f"| {ref} | {shot} | {at} | {nom} | **{nd}** | {seq} | **{nout}** |"
                    for ref, shot, at, nom, nd, seq, oout, nout in FINAL9)
        + "\n\n"
        "　③ **ep2#4 的 `dur_sec` 保持 1.8 不动**（新句实测约 1.1s，1.8s 预算仍成立；"
        "下调预算会连带改 D16 `out_sec`，属另一波次，不在本轮），故 D16 ep2 seq9 的 `out_sec` 亦保持 43.0，"
        "**同步口径（out_sec ＝ at_sec + dur_sec）成立**，且与片尾 43.0 **相接不重叠**（Q51）。"
        "④ **待声音设计重合成 ep2#4 一条**（文案改了，盘上音频还是旧句 → items.json 必须同步重生成，"
        "否则比对脚本会报 unmatched），重合成后复跑只读比对，**期望 ERR = 0**。"
    )

    # A3 新增 U02-R09
    d18["open_issues"].append({
        "id": "U02-R09",
        "issue": "**U02 ep014 镜3 的 shot_intent 契约冲突（方向相反，非措辞松）** —— "
                 "D08 body[4]：「成本模型在屏幕上**停住**，最后一栏数字没有合上。」；"
                 "D11 镜3 visual_facts 原文：「一列成本条目**滚过**」。"
                 "「滚过」呈现的恰是模型**算得出来**的样子，**算不出来的那一半没拍到**"
                 "（名单那一半已拍到）→ 契约本身在 D08 侧合规，冲突在 D11 侧未执行。",
        "owner": "分镜导演（D11 侧补句）＋ 台本编剧（已回报）＋ 企划合规（核销）",
        "blocks": "不拦 U02 单元锁（U02 尚未锁）；**拦 U02 锁前的 shot_intent 契约闭环**",
        "priority": "中",
        "status": "已登记·分镜导演已修复·待复核",
        "resolution": "**2026-10-23 04:37 分镜导演已修复并落盘**：units/U02/D11.json → **v1.2**，"
                      "ep014 镜3 visual_facts 已由「一列成本条目滚过」改为「**一列成本条目停在最后一栏，"
                      "最后一栏数字没有合上**」，与 D08 body[4] 逐字对齐。"
                      "**本岗待复核**：须跑 `scripts/shotintent_map_U02.mjs` 确认 **29/29** 覆盖（原 28/29）。"
                      "**Apply**：shot_intent 契约冲突若属「方向相反」（不是措辞松），一律在 D11 侧改，"
                      "**不动上游 shot_intent 原文**（D08 body 原文本就合规）。",
        "detected_by": "台本编剧 2026-10-23 04:35（shotintent_map_U02.mjs 复跑 28/29）",
    })

    # A4 新增 U01-R20
    d18["open_issues"].append({
        "id": "U01-R20",
        "issue": "**分镜导演 04:35 转派视觉设定的 C-019／C-031 两项，磁盘上早已闭环 —— 照单转派会造成"
                 "「同一交付物两个写者」，违反章程 §七·九 单写者纪律 v2.2** —— "
                 "① 「build_D12_U01.py 现文案无霜白」**不成立**：第 205 行 image_prompt 已含完整霜白三层表述"
                 "（剪影被束具缚住／霜白自肩部向下漫开／边缘浮起冷白雾气成块可辨），第 206 行 video_prompt 已含霜白漫开，"
                 "第 207 行 negatives 已含 `frost-layer cold white mist preserved`；"
                 "② 「video 写『拉下袖子**盖住**手腕』与『斑痕必须被看见』相反」**已修复**："
                 "当前第 275–276 行已是「腕上褪尽的斑痕褪成一小块浅色、在远景里可辨」，全仓无「盖住」表述，"
                 "且 scripts/d12_check_data_U01.py:57-58 留痕了修复来源（D18 Q35）。"
                 "**该项已在 D18 Q43（2026-10-23 03:04）判过「回执点名的待转派必须先查是否已被闭环」，"
                 "本轮是同一事项的再次重申。**",
        "owner": "企划合规（核销与唯一残留转派）＋ 视觉设定（唯一残留）",
        "blocks": "不拦任何单元锁；**拦「把已闭环项再派一遍」**",
        "priority": "中",
        "status": "已登记·已复核·唯一残留已派单",
        "resolution": "**2026-10-23 04:45 企划合规处置**：① **C-019「无霜白」、C-031「盖住手腕」两项不予转派** —— "
                      "磁盘实况已闭环（证据：build_D12_U01.py 第 205／207／275-276 行 + d12_check_data_U01.py:57-58），"
                      "重复转派＝同一交付物两个写者。**回报与磁盘冲突一律以磁盘为准**（本岗一贯纪律）。"
                      "② **唯一真残留单独派给视觉设定**：ep5 镜3 的 negatives **同时**含 `no smoke from humans` 与 "
                      "`frost-layer cold white mist preserved`，而 D08 body[9] 要求「霜白从她肩上向下漫开，"
                      "边缘浮起一层白雾」—— 雾气**长在被缚人形剪影上**，「from humans」正好命中该载体 → "
                      "模型极可能把冷白雾气判成「人体冒烟」而压制，**ep5 镜3 的合规改动会在出图环节静默落空**。"
                      "处置：第 207 行 `no smoke from humans` → **`no burning, no smoke`**（去掉命中载体的限定），"
                      "保留 `frost-layer cold white mist preserved`；**影响面已核＝全库仅此 1 处、仅 ep5 镜3 这 1 张卡**。"
                      "③ **不触发 D13/D14 重建**：build_D13.py 读的是 **D11**，D14 的 h3_prompt 由 "
                      "render_contract.json + appearance.json 生成，**D12 的 negatives 不进白模链** → 白模场景师无动作。"
                      "**Apply when**：收到「某项待转派/待修」时，先 grep 磁盘判是否已被闭环，"
                      "已闭环的给明确答复而不是模糊收下（Q43）。",
        "detected_by": "分镜导演 2026-10-23 04:35 回报（企划合规 04:45 磁盘复核判定为已闭环）",
    })

    # A5 新增 OPS-13
    d18["open_issues"].append({
        "id": "OPS-13",
        "issue": "**共享出口校验器 `04_工具/validate.mjs` 的「无 --unit 全项目跑」是混装校验，"
                 "且现状正在朝「假绿」方向走** —— 旧实现 `collectFiles(null)` 把**所有单元压进同一张"
                 "以 doc_id 为键的扁平表**（后遍历单元覆盖先遍历单元），而 `ctx.unit`／`ctx.unitDir` 又恒取 "
                 "`unitIds[0]` → 结果既不是全项目校验也不是单单元校验，而是**混装**：D11 取自后一个单元、"
                 "D13/D14 取自前一个单元。**台本编剧 04:35 实测报出 error 128（64×V2 + 64×V11），全部是跨单元错配**。"
                 "**更危险的方向**：现在之所以报错，是因为后一个单元的 D13/D14 **还没产出**（占位缺失暴露了错配）；"
                 "**一旦后单元产出同名交付物，V11 会用「后单元的 D11」校验「后单元的 D14」而通过，"
                 "先单元的 D11×D14 组合从此不再被校验却报绿** —— 报错是幸运的现状，不是稳定行为。",
        "owner": "企划合规（已修并验收）＋ 全员（改用逐单元口径）",
        "blocks": "不拦任何单元锁；**拦「拿无 --unit 的全项目跑结果当放行依据」**（修前）",
        "priority": "高（共享出口闸，影响五岗；假绿方向比报错方向更危险）",
        "status": "已修复·已验收·闭环",
        "resolution": "**2026-10-23 04:40 企划合规修复并验收**（04_工具/validate.mjs）：\n"
                      "① **逐单元独立校验**：无 `--unit` 时改为**每个单元各自 `collectFiles(unit)` → 各自独立跑规则**，"
                      "**禁止跨单元合并**；共享层文档在每个单元轮次都会被检查（语义＝每个单元都验证一遍共享层），"
                      "错误**按单元分节**呈现，summary 为各单元**合计**；exit = 合计 error>0 则 1。\n"
                      "② **单单元路径行为零变化**：改前/改后逐条比对 `--unit U01`／`--unit U02` 的 "
                      "unit／docs／summary／rules（含每条 error 与 warning 原文）**完全一致**（实测 True/True）。\n"
                      "③ **实测**：改前全项目跑 error 128／exit 1 → 改后 **error 0／warning 11（U01 2 + U02 9）／"
                      "22-22 规则通过／exit 0**；聚合报告内每单元的 rules 与该单元独立报告**逐条一致**。\n"
                      "④ 报告文件：无 `--unit` 时写 `reports/validate-<UNIT>.json`（与 `--unit` 同名同格式）"
                      "＋ 聚合 `reports/validate.json`（新增 `units[]` 字段，summary 为合计）。"
                      "**无程序化消费方读无 unit tag 的聚合文件**（已 grep 全仓：仅 D18 引用 "
                      "`reports/validate-U01.json`），**风险为零**。\n"
                      "⑤ 备份：`/tmp/validate_bak_043852/validate.mjs`（改前原件）。\n"
                      "**Apply when**：任何跨单元聚合的校验/统计入口，**必须显式声明作用域**；"
                      "宁可分节报错，也不可混装出假绿（Q52）。",
        "detected_by": "台本编剧 2026-10-23 04:35 报「全项目单跑 error 128」＋ 企划合规 04:38 定位根因",
    })

    # A6 新增 Q52
    d18["global_checks"].append({
        "id": "Q52",
        "item": "**任何跨单元/跨范围聚合的校验或统计入口，必须显式声明作用域，禁止把多个范围压进一张以"
                "同一标识为键的扁平表** —— 本轮实证：`04_工具/validate.mjs` 的 `collectFiles(null)` "
                "把 U01 与 U02 的交付物压进**同一张以 doc_id 为键的表**，后遍历单元覆盖先遍历单元；"
                "而 `ctx.unit`／`ctx.unitDir` 恒取 `unitIds[0]` → 无 `--unit` 的「全项目跑」是**混装校验**"
                "（实测 error 128＝64×V2 + 64×V11，全是跨单元错配）。**关键教训不是「会报错」，"
                "而是「报错是幸运的现状」**：当前之所以报错，是因为后一个单元的 D13/D14 尚未产出；"
                "**一旦后单元产出同名交付物，V11 就会用后单元的 D11 校验后单元的 D14 而通过，"
                "先单元的 D11×D14 组合从此不再被校验却报绿** —— 假绿比报错危险得多。"
                "**做法**：① 聚合入口**按范围分节**，每节独立汇总、错误按节呈现，合计另行给出；"
        "② 标识冲突时**不得静默覆盖**，要么分节，要么显式报错；③ **范围标识必须一路传到规则上下文**"
        "（`ctx.unit`／`ctx.unitDir` 与 `ctx.files` 必须指向同一范围）；④ 修复后必须做"
        "**「改前 vs 改后逐条比对」**，证明既有单范围路径**零行为变化**（本轮实测 True/True）；"
        "⑤ 报告文件按范围分别落盘，聚合报告另存，避免下游引用错文件。",
        "method": "读实现定位覆盖点 → 用「后范围产出同名交付物」的假绿场景做反向推演 → "
                  "改后逐条比对单范围路径 + 聚合路径与各范围独立报告的一致性",
        "source": "企划合规 2026-10-23 04:38–04:42（OPS-13 根因与修复）",
        "severity": "高（共享出口闸；假绿方向会掩盖未校验的单元）",
    })
    d18["version"] = "v1.44"
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj["decisions"]["S17_共享校验器单元作用域修复裁定"] = (
        "企划合规裁决（2026-10-23 04:40–04:45，OPS-13）：**共享出口校验器的「无 --unit 全项目跑」"
        "口径裁定为「逐单元独立校验，禁止跨单元合并」** —— 背景：台本编剧 04:35 报全项目单跑 error 128，"
        "根因是 `collectFiles(null)` 把多个单元压进**同一张以 doc_id 为键的扁平表**（后遍历单元覆盖先遍历单元），"
        "而 `ctx.unit`／`ctx.unitDir` 恒取 `unitIds[0]` → 无 `--unit` 的跑法是**混装校验**。"
        "**裁定要点**：① **不采「明确多单元同跑不作闸」方案** —— 理由是「不作闸」会丢掉全项目体检入口，"
        "而**现状已在悄悄变成假绿**（后单元一旦产出同名交付物，先单元的 D11×D14 组合就不再被校验却报绿），"
        "**报错是幸运的现状，不是稳定行为**；假绿比报错危险。"
        "② **裁定为修**：无 `--unit` 时**逐单元各自独立校验**，错误按单元分节、summary 合计、exit 取合计；"
        "③ **单单元路径零行为变化**（改前/改后逐条比对 U01／U02 的 unit/docs/summary/rules 含 error 与 warning 原文，"
        "实测完全一致）；④ 报告按范围分别落盘 `reports/validate-<UNIT>.json` ＋ 聚合 `reports/validate.json`；"
        "⑤ **共享工具改动由总控明派并在 D18 登记**（本条即登记，符合 §七·九）。"
        "**Apply when**：任何跨范围聚合的校验/统计入口；任何「改前报错、改后不报」的怀疑场景，"
        "先问「报错是稳定行为还是幸运现状」，假绿方向优先于报错方向。"
    )
    prj["updated_at"] = NOW
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 团队章程 ----------
    old_usage = ("# 校验（每份交付物出口必跑）\n"
                 "node 短剧文档工厂/04_工具/validate.mjs --project 短剧文档工厂/02_项目/<项目名> --unit U01\n"
                 "```")
    new_usage = ("# 校验（每份交付物出口必跑）\n"
                 "node 短剧文档工厂/04_工具/validate.mjs --project 短剧文档工厂/02_项目/<项目名> --unit U01\n"
                 "\n"
                 "# 全项目体检（可选；**v2.4 起为逐单元独立校验**，错误按单元分节、summary 合计）\n"
                 "node 短剧文档工厂/04_工具/validate.mjs --project 短剧文档工厂/02_项目/<项目名>\n"
                 "```\n"
                 "\n"
                 "> **单元作用域（v2.4 · 强制）**：无 `--unit` 的跑法**不是**「把所有单元合并成一份交付物一起校验」，"
                 "而是**逐单元各自独立校验**（共享层文档在每个单元轮次都会检查），错误**按单元分节**呈现、"
                 "summary 为各单元合计。**禁止跨单元合并成一张以 doc_id 为键的表** —— 那样会让单元作用域规则"
                 "（V3/V4/V8/V10/V11）失去作用域，且在后单元产出同名交付物后会产生**假绿**（Q52／OPS-13）。")
    if old_usage in charter:
        charter = charter.replace(old_usage, new_usage)
    elif "单元作用域（v2.4 · 强制）" not in charter:
        sys.exit("[ABORT] 团队章程 §四·五 用法段旧串与新串均未命中；不写盘。")

    anchor = "- **v2.1 D14 逐镜化（2026-10-22 23:25 · 工具侧）**"
    if anchor not in charter:
        sys.exit("[ABORT] 团队章程 §九 变更条目锚点未命中；不写盘。")
    charter = charter.replace(anchor, (
        "- **v2.4 工具侧 · 校验器单元作用域修复（2026-10-23 04:40 · 企划合规 · 裁决 S17 / OPS-13 / Q52）**："
        "`04_工具/validate.mjs` 的 `collectFiles(null)` 原把**所有单元压进同一张以 doc_id 为键的扁平表**"
        "（后遍历单元覆盖先遍历单元），而 `ctx.unit`／`ctx.unitDir` 恒取 `unitIds[0]` → "
        "**无 `--unit` 的「全项目跑」是混装校验**：既不是全项目校验、也不是单单元校验。"
        "实测旧行为 error 128（64×V2 + 64×V11，全是跨单元错配）。"
        "**危险方向不是报错而是假绿**：当前之所以报错，是因为后一单元的 D13/D14 尚未产出；"
        "**一旦后单元产出同名交付物，V11 就会用后单元的 D11 校验后单元的 D14 而通过，"
        "先单元的 D11×D14 组合从此不再被校验却报绿**。"
        "修复：**无 `--unit` 时改为逐单元各自 `collectFiles(unit)` → 各自独立跑规则**，禁止跨单元合并；"
        "错误按单元分节、summary 合计、exit 取合计；报告按范围分别落盘 `reports/validate-<UNIT>.json` ＋ "
        "聚合 `reports/validate.json`。**单单元路径行为零变化**（改前/改后逐条比对 U01／U02 的 "
        "unit/docs/summary/rules 含 error 与 warning 原文，完全一致）。"
        "改后实测全项目跑 **error 0／warning 11／22-22 规则通过／exit 0**。"
        "**Apply**：任何跨范围聚合的校验/统计入口必须显式声明作用域（Q52）。\n" + anchor
    ))

    # ---------- E. 索引 ----------
    old_ver = "D18 **v1.43**（51 条 global_checks / 61 条 open_issues"
    new_ver = (f"D18 **v1.44**（{len(d18['global_checks'])} 条 global_checks / "
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
### 十·{idx_new} 四岗回报核销 ＋ 校验器单元作用域修复（OPS-13）＋ U02-R09／U01-R20 · D18 v1.44（**企划合规 2026-10-23 04:35–04:55**）

#### 1. 本轮四份回报的核销结论

| 回报方 | 内容 | 磁盘实况 | 处置 |
|---|---|---|---|
| 台本编剧 | U01 ep2#4 压缩（D08 v1.9／D09 v1.5） | ✅ 已落盘，钟声字幕行未动，base 204 | **核销**；第二波启动 |
| 台本编剧 | U02 shot_intent 28/29（ep014 镜3） | ✅ 分镜导演 04:37 已修（U02 D11 **v1.2**） | 登记 **U02-R09**，待复核 29/29 |
| 分镜导演 | U01-R19 脚本修复 | ✅ 脚本已写死区间口径、候选集 35 条正文行、片尾 8 张单独检查，重跑抓出 ep2 seq9 | **U01-R19 核销闭环** |
| 分镜导演 | 转派视觉设定 C-019／C-031 | ❌ **磁盘早已闭环**（第 205 行有霜白、第 275-276 行无「盖住」） | 登记 **U01-R20**：**不转派**；唯一残留另行派单 |
| 台本编剧 | 全项目单跑 error 128 | ✅ 根因已定位并**已修** | 登记 **OPS-13**（已修复·已验收） |

**回报与磁盘冲突一律以磁盘为准**：分镜导演报「D11 升 v1.5」，磁盘 `units/U01/D11.json` 实为 **v1.7**（mtime 04:11）→ 以磁盘为准。

#### 2. 终表数值修订（U01-R18 第二波）

预算取「实测标称 + 0.1」→ 实测标称 < 预算 → 判定 **合规 OK** 而非贴边 WARN；**ep8#4 例外只能贴边**
（+0.1 会与下一条面板文字 in 41.4 重叠 0.1s，out 41.4 与其相接，按 Q51 不重叠）。

| 配音条目 | 镜位 | at_sec | 实测标称 | D15 新 `dur_sec` | D16 seq | D16 新 `out_sec` |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {ref} | {shot} | {at} | {nom} | **{nd}** | {seq} | **{nout}** |" for ref, shot, at, nom, nd, seq, oout, nout in FINAL9)}

**ep2#4 的 `dur_sec` 保持 1.8**（新句实测约 1.1s），故 D16 ep2 seq9 的 `out_sec` 保持 43.0，
同步口径（out_sec ＝ at_sec + dur_sec）成立，与片尾 43.0 相接不重叠。

#### 3. OPS-13：共享出口校验器的混装缺陷（**已修**）

`04_工具/validate.mjs` 的 `collectFiles(null)` 把多个单元压进**同一张以 doc_id 为键的扁平表**，
而 `ctx.unit`／`ctx.unitDir` 恒取 `unitIds[0]` → 无 `--unit` 的跑法是**混装校验**（实测 error 128＝64×V2 + 64×V11）。
**危险方向不是报错而是假绿**：现在报错是因为后单元的 D13/D14 尚未产出；一旦后单元产出同名交付物，
V11 会用后单元的 D11 校验后单元的 D14 而通过，**先单元的 D11×D14 组合从此不再被校验却报绿**。
**修复**：无 `--unit` 时**逐单元各自独立校验**，错误按单元分节、summary 合计、exit 取合计；
报告按范围分别落盘 ＋ 聚合报告。**单单元路径零行为变化**（改前/改后逐条比对 True/True）；
改后全项目跑 **error 0／warning 11／22-22 通过／exit 0**。新增判据 **Q52**、裁决 **S17**。

#### 4. U01-R20：重复转派已闭环项 = 两个写者

分镜导演本轮重申的 C-019／C-031，**Q43（03:04）已判过「先查是否已被闭环」** → 磁盘实况早已闭环，
**不予转派**；唯一真残留（ep5 镜3 negatives 同含 `no smoke from humans` 与 `frost-layer cold white mist preserved`，
而雾气长在人形剪影上 → 出图环节可能被压制）**单独派给视觉设定**，影响面＝全库 1 处、1 张卡，
且**不触发 D13/D14 重建**（build_D13.py 读 D11，D14 prompt 读 render_contract/appearance）。

#### 5. 出口闸

`validate --unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **11/11、error 0、warning 9**；
无 `--unit` → **error 0／warning 11／22-22／exit 0**（修前 error 128／exit 1）。**U01 锁态未动**。
本轮**只改** `04_工具/validate.mjs`、`00_团队章程.md`、`shared/D18.json`、`project.json`、
`00_项目索引.md`、`99_交付说明.md`（本节）；**未改**任何交付物 JSON、源素材、规格文件。
"""

    # ---------- F. 交付说明 ----------
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
## {new_cn}、四岗回报核销 ＋ 校验器单元作用域修复（OPS-13）＋ U02-R09／U01-R20 · S17 · Q52（**企划合规 2026-10-23 04:35–04:55**）

### {new_cn}.1 核销结论

· **U01-R19 闭环**：分镜导演已修 `reconcile_tts_actual_vs_d15_budget.mjs`（脚本头写死左闭右开区间口径、
A3 候选集＝全部正文行 35 条、片尾标题卡 8 张单独检查），企划合规 04:42 重跑复核 → **ep2 seq9 被抓出**，与独立复算一致。
· **U02-R09**：U02 ep014 镜3「成本条目滚过」vs D08「停住、最后一栏数字没有合上」→ 分镜导演 04:37 已修（U02 D11 **v1.2**），待复核 29/29。
· **U01-R20**：分镜导演转派的 C-019／C-031 **磁盘早已闭环（Q43 已判过）→ 不转派**（重复派活＝两个写者）；
唯一残留（ep5 镜3 negatives 语义张力）**已单独派给视觉设定**。
· **回报与磁盘冲突以磁盘为准**：报「D11 v1.5」，磁盘实为 **v1.7**。

### {new_cn}.2 OPS-13：校验器混装缺陷（**已修**）

根因：`collectFiles(null)` 把多单元压进**同一张以 doc_id 为键的扁平表**，而 `ctx.unit` 恒取 `unitIds[0]`
→ 无 `--unit` 是**混装校验**（旧实测 error 128）。**危险方向是假绿不是报错**：后单元一旦产出同名交付物，
先单元的 D11×D14 组合就不再被校验却报绿。修复：**逐单元各自独立校验**，错误按单元分节、summary 合计；
单单元路径**零行为变化**（改前/改后逐条比对 True/True）；改后全项目跑 **error 0／warning 11／22-22／exit 0**。
新增判据 **Q52**、裁决 **S17**；团队章程 §四·五 补多单元语义、§九 记 **v2.4 工具侧**。

### {new_cn}.3 U01-R18 终表（第二波）

{chr(10).join(f"- {ref}（{shot}，at {at}）：D15 预算 {nom} → **{nd}**；D16 {seq} out_sec → **{nout}**" for ref, shot, at, nom, nd, seq, oout, nout in FINAL9)}

**ep2#4 预算保持 1.8**（文案已压为「换我用了。」，实测约 1.1s），D16 seq9 out_sec 保持 43.0 → 同步口径成立。

### {new_cn}.4 出口闸与边界

`validate --unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **11/11、error 0、warning 9**；
无 `--unit` → **error 0／warning 11／exit 0**。**U01 锁态未动**。
本轮**只改** `04_工具/validate.mjs`、`00_团队章程.md`、`shared/D18.json`、`project.json`、
`00_项目索引.md`、`99_交付说明.md`（本节）；**未改**任何交付物 JSON、源素材、规格文件；
未生成图片／视频／音频，未合成 TTS，未提交 H3 付费生成，未投流上架。
"""

    # ---------- G. 自检 ----------
    for k in ("U02-R09", "U01-R20", "OPS-13", "Q52"):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S17_共享校验器单元作用域修复裁定" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S17；不写盘。")
    if "单元作用域（v2.4 · 强制）" not in charter or "v2.4 工具侧 · 校验器单元作用域修复" not in charter:
        sys.exit("[ABORT] 团队章程未写入 v2.4 条目；不写盘。")
    if idx.count(f"### 十·{idx_new}") != 1:
        sys.exit(f"[ABORT] 索引 §十·{idx_new} 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 v1.43→v1.44（U01-R19 核销 ＋ U01-R18 追加 ＋ U02-R09 ＋ U01-R20 ＋ OPS-13 ＋ Q52）；"
              f"project.json（+S17）；章程（§四·五 用法 + §九 v2.4）；索引 §二 1 处 ＋ §十·{idx_new}；交付说明 §{new_cn}")
        return

    write(p18, d18_out)
    write(p_prj, prj_out)
    write(p_charter, charter)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 本轮核销与新登记完成")
    print(f"   shared/D18.json：v1.43 → {d18['version']}（U01-R19 核销 ＋ U01-R18 追加 ＋ U02-R09 ＋ U01-R20 ＋ "
          f"OPS-13 ＋ Q52；gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：+S17_共享校验器单元作用域修复裁定；updated_at → {NOW}")
    print(f"   00_团队章程.md：§四·五 用法段 ＋ §九 v2.4 工具侧条目")
    print(f"   00_项目索引.md：§二 版本提法 ＋ §十·{idx_new}")
    print(f"   99_交付说明.md：新增 §{new_cn}")


if __name__ == "__main__":
    main()
