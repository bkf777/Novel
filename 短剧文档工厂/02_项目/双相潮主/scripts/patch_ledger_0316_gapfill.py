#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台账缺口回填（企划合规单点维护，2026-10-23 03:1x）。

起因
----
R-032 收尾后的五份回执（声音设计 D15 v1.2／分镜导演 D16 v1.6／视觉设定 D12 v1.4／
白模场景师 D14 取景审计／故事架构 U02 D06+D07）已由并行实例登记到 D18 v1.32。
本岗逐项回盘后，发现**五处真实缺口**（其余均已登记，**不重复记账**）：

  ① **白模场景师的两条 U02 前置未登记** —— 现役脚本 `build_white_model_u01.py`／
     `assemble_D14.py` 硬编码 U01 路径；`04_工具/handoff/README.md` 仍记旧 plan 流程，
     未记现役新链与两条新场景规格约定（`pose` × 底面 z × 时间比例布轨；道具
     `center_m[2]` ＝ 几何体心）；`make_plan.py` 归档与否待裁。
  ② **视觉设定提请的 `check_D12_D11_alignment.py` 硬编码 U01 路径** —— 同属工具链单测参数化。
  ③ **D14 逐镜取景审计的两类提示级发现未登记** —— 两处构图贴边（ep05_shot02 叶承钧
     12%×100% @x=94；ep06_shot03／ep07_shot04 陆沉 @x=3／x=7）＋ 六处提示词预算零余量
     （g29=6500 恰好顶格、g22=6498、g6=6475、g7=6452、g26=6441、g21=6415，上限 6,500）。
     **两者都不违规，但都直接影响 U02** —— U02 同密度场景任何内容增补都会顶破预算。
  ④ **`project.json` decisions.S1 末句是过期时点快照** —— 「D12 两卡原处置与新口径一致、
     无需返修」是 2026-10-22 的 D12 状态；C-006 已在 D12 v1.3 重建时口径回退、
     v1.4 已恢复 S1 口径。project.json 是跨 20 单元共享真源，同一颗时点雷。
  ⑤ **索引 §二 状态栏 D18 版本提法停在 v1.28（42/44）**、**§六 无 U02 两行**。

本脚本做五件事（全部带命中数断言，对不上即中止不写盘；落盘后写后回读）：
  A. D18 v1.32 → v1.33：新增 open_issues **U02-R01**（工具链单测参数化＋README 新链）
     与 **U02-R02**（取景贴边＋预算零余量）；新增 global_check **Q45**（提示级发现必须登记）。
  B. project.json：S1 末句补时点限定；新增 decisions **S12_白模工具链参数化与归档裁定**。
  C. 00_项目索引.md：§二 状态栏版本提法刷到 v1.33（45/48）＋ 补 Q42–Q45／S12／新未结项；
     §六 补 U02 两行并改表头计数；新增 §十·三十一。
  D. 99_交付说明.md：新增 **§三十四**（节号按运行时最大节号＋1 计算，不写死）。
  E. 出口硬闸与写后回读由调用方执行。

用法
----
python3 scripts/patch_ledger_0316_gapfill.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 03:18"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
    """中文数字 → int（覆盖 一 ~ 九十九）。"""
    if "十" in s:
        head, tail = s.split("十", 1)
        return (CN[head] if head else 1) * 10 + (CN[tail] if tail else 0)
    return CN[s]


def int_to_cn(n):
    """int → 中文数字（一 ~ 九十九）。"""
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
    """按原文件的序列化约定回写：indent=2；尾随换行与否跟随原文件。

    必须跟随原文件而不是写死 —— D18.json（并行实例维护，尾随换行）与
    project.json（本岗维护，无尾随换行）约定不同，写死会造成纯格式 diff。
    """
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


def replace_once(text, old, new, where):
    n = text.count(old)
    if n != 1:
        sys.exit(f"[ABORT] {where} 待替换串命中 {n} 次（期望 1）：{old[:70]}…；不写盘。")
    return text.replace(old, new)


def replace_idempotent(text, old, new, where, skipped):
    """台账文本替换（幂等）：旧串命中 1 次 → 替换；新串已在 → 跳过（并行实例已做）；
    两者都不在 → 中止（说明落盘态与预期不符，不可盲写）。"""
    if old in text:
        n = text.count(old)
        if n != 1:
            sys.exit(f"[ABORT] {where} 待替换串命中 {n} 次（期望 1）：{old[:70]}…；不写盘。")
        return text.replace(old, new)
    if new in text:
        skipped.append(where)
        return text
    sys.exit(f"[ABORT] {where} 旧串与新串均未命中（落盘态与预期不符）：{old[:70]}…；不写盘。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    p_idx = os.path.join(proj, "00_项目索引.md")
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ================= A. D18 =================
    if d18.get("version") != "v1.32":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.32；不写盘。")

    oi_ids = [o.get("id") for o in d18["open_issues"]]
    for oid in ("U02-R01", "U02-R02"):
        if oid in oi_ids:
            sys.exit(f"[ABORT] open_issues 已含 {oid}，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if "Q45" in gc_ids:
        sys.exit("[ABORT] global_checks 已含 Q45，不重复登记；不写盘。")
    if gc_ids[-1] != "Q44":
        sys.exit(f"[ABORT] global_checks 末条为 {gc_ids[-1]}，期望 Q44；不写盘。")

    d18["open_issues"].append({
        "id": "U02-R01",
        "issue": "**U02 开工前置（工具链侧）：现役脚本按 U01 硬编码，且 handoff README 未记现役新链** —— "
                 "白模场景师 02:4x 与视觉设定 02:4x 分别报出：① `scripts/build_white_model_u01.py`／"
                 "`scripts/assemble_D14.py` **硬编码 U01 路径**，U02 需先参数化，否则 U02 的 D13/D14 无法复用"
                 "（U02 需覆盖场景码 **B-1…B-10**，比 U01 的 A-1…A-9 多一个场景）；"
                 "② `04_工具/handoff/README.md`（23:26）**仍记旧 plan 流程**，未记现役新链"
                 "（`build_white_model_u01.py` 01:34 → `assemble_D14.py` 01:41），也未记两条新场景规格约定 —— "
                 "**角色代理按 `pose` × 底面 z × 时间比例布轨**、**道具 `center_m[2]` 为几何体心（不是底面高）**；"
                 "③ 视觉设定新增的只读核验脚本 `scripts/check_D12_D11_alignment.py` **同样硬编码 U01 路径**，"
                 "U02 的 D12 画面文案轴将无覆盖。",
        "owner": "白模场景师（①②）＋ 视觉设定（③）＋ 企划合规（参数化口径与验收）",
        "blocks": "拦 U02 的 **D13／D14** 产出（D13 须覆盖 B-1…B-10）；**不拦** U02 的 D08／D09／D11／D16／D12／D15"
                  "（与工具链无关，可正常推进）",
        "priority": "中",
        "status": "已登记·待排期",
        "resolution": "2026-10-23 03:18 企划合规裁决 **S12_白模工具链参数化与归档裁定**："
                      "① **三个脚本一律按 `--unit` 参数化，禁止复制 `_u02` 副本** —— 副本即第二套实现，"
                      "U02 与 U01 必然分叉；② **`04_工具/handoff/README.md` 补记现役新链 ＋ 两条场景规格约定** —— "
                      "该 README 是下一位执行人的第一入口，留旧流程＝必然按旧流程重跑；"
                      "**边界**：工具改动不在企划合规单写者范围，本岗只裁口径与排期，由各岗执行并回报。",
        "detected_by": "白模场景师 2026-10-23 02:4x（§28.4）＋ 视觉设定 2026-10-23 02:4x（§27.5）",
    })
    d18["open_issues"].append({
        "id": "U02-R02",
        "issue": "**D14 逐镜取景审计的两类提示级发现未消除，将直接影响 U02** —— 白模场景师 02:4x 在撤单同时做了 "
                 "32 镜逐镜取景审计（V11 只校覆盖与一致性、不校白模取景，此项此前无人做）："
                 "**主体在画 32/32 通过**（腕部特写、触角交击、终端前过肩、暗处冲锋剪影、坑底跟拍、双人对峙等易错镜次均正确）；"
                 "但报出 **① 两处构图贴边**（`ep05_shot02` 叶承钧 **12%×100% @x=94**，贴右缘几乎被裁；"
                 "`ep06_shot03`／`ep07_shot04` 陆沉 **@x=3／x=7**，贴左缘）—— **不违规，但 H3 阶段可能被裁**；"
                 "**② 六处提示词预算零余量**（上限 6,500）：`g29=6500`（**恰好顶格**）、`g22=6498`、`g6=6475`、"
                 "`g7=6452`、`g26=6441`、`g21=6415` —— **不违规（单镜未超限），但 U02 同密度场景任何内容增补都会顶破**。",
        "owner": "白模场景师（出判定）＋ 分镜导演（D11 visual_facts 改动会连带改变取景）＋ 企划合规（U02 开工前复核）",
        "blocks": "**不拦 U01 单元锁**（U01 已锁、已全量核验通过）；**U02 开工前须复核** —— "
                  "预算余量随文案增补只会更紧，贴边构图会随 D11 visual_facts 改写而变化",
        "priority": "中",
        "status": "已登记·待复核",
        "resolution": "2026-10-23 03:18 企划合规登记（**只登记不代改**）：① 贴边三镜"
                      "（ep05_shot02／ep06_shot03／ep07_shot04）**列入 U02 的 D11 视角落位复核清单** —— "
                      "若 U02 复用同类构图，须先在 **D11 侧**把主体中心拉离画面边缘，"
                      "**不得在 D14 白模侧单独移动主体**（白模只锁几何，挪主体＝与 D11 分叉）；"
                      "② 六处零余量镜 **g21／g22／g26／g6／g7／g29** 列入 U02 的 D12 预算前置清单 —— "
                      "**余量 <100 字符的镜位禁止增补**；③ 两类**均不拦 U01 单元锁**（不违规、已核验通过）。",
        "detected_by": "白模场景师 2026-10-23 02:4x（D14 撤单时同步做的 32 镜取景审计）",
    })
    d18["global_checks"].append({
        "id": "Q45",
        "item": "**提示级发现（非违规但会影响下游）必须单独登记为 open_issue —— 「不违规」不等于「对下一单元无影响」** —— "
                "本轮实证：白模场景师在 D14 撤单同时做了 32 镜逐镜取景审计，结论是「主体在画 32/32 通过」，"
                "但同时报出 **两处构图贴边**（ep05_shot02 叶承钧 12%×100% @x=94 几乎被裁；"
                "ep06_shot03／ep07_shot04 陆沉 @x=3／x=7 贴左缘）与 **六处提示词预算零余量**"
                "（g29=6500 恰好顶格、g22=6498、g6=6475、g7=6452、g26=6441、g21=6415，上限 6,500）。"
                "这两类都**不违规**（V11 不校取景；预算校验只看单镜上限、不看余量），但都**直接影响 U02**："
                "U02 同密度场景任何内容增补都会顶破 6,500 预算，贴边构图会在 H3 阶段被裁。"
                "**做法**：① 回执里的「提示级发现」必须单独登记为 open_issue，"
                "**不能因为它「不违规」就只留在回执里**；② 登记要带**可复算的量**（镜号／坐标／字符数），"
                "不能只写「有贴边」；③ 下一个单元开工前逐条回核这些量是否已被上游改动消除 —— "
                "贴边构图会随 D11 visual_facts 改写而消失，预算余量会随文案增补而更紧；"
                "④ 审计类结论与「合规违规」分开列：前者不拦锁、后者才拦，但**两者都要进台账**。",
        "method": "审计类回执逐条分类（合规违规／提示级发现），后者逐条登记为 open_issue 并带可复算的量",
        "source": "企划合规 2026-10-23 03:18（白模场景师 D14 取景审计回报回盘时）",
        "severity": "中",
    })
    d18["version"] = "v1.33"
    u02 = [x for x in d18["unit_checks"] if x.get("unit") == "U02"][0]
    u02["updated_at"] = NOW
    # 序列化必须复现原文件约定（indent=2；尾随换行跟随原文件），否则引入纯格式 diff
    if serialize_like(json.loads(d18_raw), d18_raw) != d18_raw:
        sys.exit("[ABORT] D18.json 序列化格式与 indent=2 不一致；不写盘。")
    d18_out = serialize_like(d18, d18_raw)

    # ================= B. project.json =================
    s1 = prj["decisions"].get("S1_色板暖源口径")
    if not s1 or "D12 两卡原处置与新口径一致，无需返修" not in s1:
        sys.exit("[ABORT] project.json S1 决策未命中待订正的末句；不写盘。")
    if "S12_白模工具链参数化与归档裁定" in prj["decisions"]:
        sys.exit("[ABORT] project.json decisions 已含 S12，不重复登记；不写盘。")
    prj["decisions"]["S1_色板暖源口径"] = s1.replace(
        "D10/D11 已改，D12 两卡原处置与新口径一致，无需返修。",
        "D10/D11 已改，**（2026-10-22 当时的 D12 处置）两卡原处置与新口径一致、无需返修** —— "
        "⚠️ **该结论为时点快照，已于 2026-10-23 02:40 失效并被订正**：D12 v1.3（01:56 重建产物）的 C-006 "
        "把本裁决③明确允许的「金属局部暖反光」一并排除（写成「暖色只出现在弧光本身」），属**重建时口径回退**；"
        "已由视觉设定在 **D12 v1.4** 恢复为 S1 口径（「焊花瞬时溅落卷帘门、仅在接触处留下局部暖色亮点"
        "（取色板 薪火橙）＋ 周围仍由工业冷光照明」），**negatives 一条未动**，"
        "并在 `build_D12_U01.py` 内加 S1 口径断言防再次回退。"
        "**Apply when**：共享层决策里写「无需返修／无需重出」的时点结论，一律视为快照，"
        "须在下游重建后重核（与 Q39 同型）。",
    )
    prj["decisions"]["S12_白模工具链参数化与归档裁定"] = (
        "企划合规裁决（2026-10-23 03:18，白模场景师 §28.4 与视觉设定 §27.5 请裁工具链口径）："
        "**① 现役脚本一律按 `--unit` 参数化，禁止复制 `_u02` 副本** —— 副本即第二套实现，U02 与 U01 必然分叉；"
        "参数化后 U02 复用同一实现。**② `04_工具/handoff/README.md` 必须补记现役新链 ＋ 两条新场景规格约定**"
        "（角色代理按 `pose` × 底面 z × **时间比例**布轨；道具 `center_m[2]` 为**几何体心**而非底面高）—— "
        "该 README 是下一位执行人的第一入口，留旧 plan 流程＝必然按旧流程重跑；"
        "**注意与 2026-10-23 01:34–01:41 的工具语义变更同源**（坐标语义改一次，下游必须同步换算，"
        "否则只半高下沉、不报错）。**③ `04_工具/handoff/make_plan.py` 归档（可恢复退役）** —— "
        "现役新链（`build_white_model_u01.py` 01:34 → `assemble_D14.py` 01:41）已绕开它；"
        "**留着比没有更坏**：谁重跑一次就会把已核验的 D14 打回旧结构。"
        "**④ 边界**：工具改动不在企划合规单写者范围，本岗只裁口径与排期，由各岗执行并回报；"
        "D18／索引／交付说明由本岗单点维护。"
    )
    prj["updated_at"] = NOW
    if serialize_like(json.loads(prj_raw), prj_raw) != prj_raw:
        sys.exit("[ABORT] project.json 序列化格式与 indent=2 不一致；不写盘。")
    prj_out = serialize_like(prj, prj_raw)

    # ================= C. 00_项目索引.md =================
    skipped = []
    idx = replace_idempotent(
        idx,
        "D18 **v1.28**（42 条 global_checks / 44 条 open_issues",
        "D18 **v1.33**（45 条 global_checks / 48 条 open_issues",
        "索引 §二 状态栏", skipped,
    )
    idx = replace_idempotent(
        idx,
        "**Q41 派活「grep＝0」只对内容面生效**；",
        "**Q41 派活「grep＝0」只对内容面生效** ＋ **Q42 迟到回执按磁盘核销** ＋ "
        "**Q43 回执数字以磁盘实测为准** ＋ **Q44 台账节号唯一连续 ＋ 写后回读** ＋ "
        "**Q45 提示级发现必须单独登记（非违规≠无影响）**；",
        "索引 §二 状态栏 Q 清单", skipped,
    )
    idx = replace_idempotent(
        idx,
        "；新增 U01-R14 D13 props Z 语义待收口 · B16 D01 gaps 11 项待用户拍板）；",
        "；新增 U01-R14 D13 props Z 语义待收口 · U01-R15／R16／R17 · U02-F01 伏笔编号 · "
        "**U02-R01 工具链单测参数化 ＋ handoff README 记新链** · **U02-R02 D14 取景贴边与预算零余量** · "
        "B16 D01 gaps 11 项待用户拍板）；",
        "索引 §二 状态栏 未结项", skipped,
    )
    idx = replace_idempotent(
        idx,
        "**S11 版本戳语义**（`synced_with_d15_vXX` 是同步当时的溯源陈述，不得改写为活链接）|",
        "**S11 版本戳语义**（`synced_with_d15_vXX` 是同步当时的溯源陈述，不得改写为活链接）＋ "
        "**S12 白模工具链参数化与 make_plan.py 归档裁定**（U02 开工前置）|",
        "索引 §二 状态栏 裁决", skipped,
    )
    # §六：表头计数 + 补 U02 两行
    idx = replace_idempotent(
        idx,
        "## 六、交付物状态表（18 份 · **JSON 真源制式**）",
        "## 六、交付物状态表（20 份 ＝ U01 18 ＋ U02 2 · **JSON 真源制式**）",
        "索引 §六 表头", skipped,
    )
    u02_rows = (
        "| D06 分集大纲（U02） | unit | 故事架构 | ✅ **已交付（JSON）** | "
        "`units/U02/D06.json` → `render/units/U02/D06.md` | **v1.0｜11,281 B｜03:03 落**。"
        "ep009–016 八集逐集落位源素材《逐集内容概述》U02 段；钩链 **7/7 逐字咬合**"
        "（ep009 hook_in ＝ U02 first_hook，ep016 hook_out ＝ U03 first_hook 逐字）；"
        "归一度锚点 **0.7→1.0→1.1→1.2→1.2→1.3→1.3→1.4%**（ep010 精确命中 12 锚点表）单调不减；"
        "伏笔 **F02**（ep010→U04）／**F04**（ep013→U05）／**F03**（ep016→U03）已登记为 **U02-F01**；"
        "ep012「按废弃物资口径处理」＝源素材「按垃圾处理」的**贬称方向合规收敛**，采纳不回退。**L1 仍 pending** |\n"
        "| D07 逐集施工卡（U02） | unit | 故事架构 | ✅ **已交付（JSON）** | "
        "`units/U02/D07.json` → `render/units/U02/D07.md` | **v1.0｜28,398 B｜03:03 落**。"
        "8 集 × 四段制，段界连续无缝、各 **45s**；代价 **8/8 具体**；"
        "**场景码 B-1…B-10**（U01 用 A-1…A-9，U02 顺延字母 B 避免单元撞码）；"
        "**全单元 8 集「串行」不设并行段**（理由：D17 切点预算零余量 ＋ 无叙事需求；"
        "若后续要并行段，须 **D07 先改并显式标 `mode=并行`** → D11／D16 据改后段界重刷）。"
        "术语禁用首跑命中 1 处（「烧掉」→ 改为「陷进火里只剩钢架残骸」）已闭合 ✅ |\n"
    )
    lines = idx.split("\n")
    if "| D06 分集大纲（U02） |" in idx:
        skipped.append("索引 §六 U02 两行（已存在）")
    else:
        hit = [i for i, l in enumerate(lines) if l.startswith("| D18 交付与质检清单 |")]
        if len(hit) != 1:
            sys.exit(f"[ABORT] 索引 §六 D18 行命中 {len(hit)} 次（期望 1）；不写盘。")
        lines.insert(hit[0] + 1, u02_rows.rstrip("\n"))
        idx = "\n".join(lines)
    # §十·三十一
    if "### 十·三十一" in idx:
        sys.exit("[ABORT] 索引已含 §十·三十一，不重复追加；不写盘。")
    if not idx.rstrip().endswith("|"):
        pass  # 末行可能是表格，追加在文末即可
    idx = idx.rstrip("\n") + "\n" + """
### 十·三十一 U02 开工前置两条登记 ＋ S1 时点快照订正 ＋ D18 v1.33（**企划合规 2026-10-23 03:08–03:18**）

#### 1. 认盘：五份回执已由并行实例登记到 D18 v1.32，本岗只补**五处真实缺口**

| 回执 | 提出方 | 并行实例已办 | 本岗补办 |
|---|---|---|---|
| D15 v1.1 → v1.2 登记 | @声音设计 | ✅ D18 D15 行 v1.2／91,657 B ＋ 索引 §六 | — |
| D16 v1.5 → v1.6 登记 ＋ 键名消歧自纠 | @分镜导演 | ✅ D18 D16 行 v1.6／107,609 B ＋ S11 裁决 | — |
| D12 v1.3 → v1.4 登记 | @视觉设定 | ✅ D18 D12 行 v1.4／86,404 B ＋ 索引 §六 | — |
| D06／D07 v1.0 ＋ F02/F03/F04 ＋ 场景码 B ＋ 不设并行段 | @故事架构 | ✅ D18 U02 条目两行 ＋ **U02-F01** | 索引 §六补 U02 两行 |
| TTS 实际时长 vs `dur_sec` 校验 | @声音设计 | ✅ **TOOL-04** 已登记（含实现路径） | 本岗补排期归属（见第 4 节） |
| **工具链 U01 硬编码 ＋ README 未记新链** | @白模场景师 | ❌ 未登记 | ✅ **U02-R01** ＋ **S12** |
| **D14 取景贴边 ＋ 预算零余量** | @白模场景师 | ❌ 未登记 | ✅ **U02-R02** |
| **S1 末句「无需返修」是过期快照** | @视觉设定 | ❌ 未订正 | ✅ **S1 补时点限定** ＋ 记 C-006 回退已订正 |
| `check_D12_D11_alignment.py` 硬编码 U01 | @视觉设定 | ❌ 未登记 | ✅ 并入 **U02-R01** |

#### 2. **U02-R01 —— 工具链单测参数化 ＋ handoff README 记新链**（S12 裁决）

- **三个脚本按 `--unit` 参数化**，**禁止复制 `_u02` 副本** —— 副本即第二套实现，U02 与 U01 必然分叉。
- **`04_工具/handoff/README.md` 补记现役新链**（`build_white_model_u01.py` 01:34 → `assemble_D14.py` 01:41）
  ＋ 两条场景规格约定：**角色代理按 `pose` × 底面 z × 时间比例布轨**、**道具 `center_m[2]` ＝ 几何体心（不是底面高）**。
  该 README 是下一位执行人的第一入口，**留旧 plan 流程＝必然按旧流程重跑**。
- **`04_工具/handoff/make_plan.py` 归档（可恢复退役）** —— 现役新链已绕开它，留着会被重跑打回已核验的 D14。
- 拦 U02 的 **D13／D14**；**不拦** D08／D09／D11／D16／D12／D15。

#### 3. **U02-R02 —— D14 取景审计两类提示级发现**

- **两处构图贴边**：`ep05_shot02` 叶承钧 **12%×100% @x=94**（贴右缘几乎被裁）；`ep06_shot03`／`ep07_shot04` 陆沉 **@x=3／x=7**（贴左缘）。
- **六处提示词预算零余量**（上限 6,500）：`g29=6500`（**恰好顶格**）、`g22=6498`、`g6=6475`、`g7=6452`、`g26=6441`、`g21=6415`。
- **两者都不违规，但都直接影响 U02**：预算余量随文案增补只会更紧；贴边构图会随 D11 visual_facts 改写而变化。
- 处置：**贴边须在 D11 侧拉离边缘**，不得在 D14 白模侧单独挪主体（白模只锁几何，挪主体＝与 D11 分叉）；
  **余量 <100 字符的镜位禁止增补**。**均不拦 U01 锁**（U01 已锁、已全量核验）。

#### 4. **S1 时点快照订正 ＋ TOOL-04 排期归属 ＋ 新判据 Q45**

- **S1 末句订正**：`project.json` `decisions.S1_色板暖源口径` 末句「D12 两卡原处置与新口径一致，无需返修」
  ＝ **2026-10-22 的 D12 状态**，且 **C-006 已在 D12 v1.3 重建时口径回退、v1.4 已恢复 S1 口径** →
  补时点限定并记订正结果。**project.json 是跨 20 单元共享真源，同一颗时点雷**（与 S6 的处理同款）。
- **TOOL-04 排期归属（总控裁决）**：**归口「出片阶段」，文档工厂侧不排期、不做** —— 该比对一旦要跑就会触及实际音频产物，
  超出本产线硬边界（只出文档与白模、不合成 TTS/BGM/音频、不提交 H3 付费生成）。
  实现路径沿用 TOOL-04 已记的四条（复用 `build_audio_u01.py` 的 `dur_of`、以 `at_sec+dur_sec` 为上限、
  **按 0.1s 标称网格判**、结果不得改 D16 时码）。**U02 开工不需要它**。
- **新增 Q45**：**提示级发现（非违规但会影响下游）必须单独登记为 open_issue** ——
  「不违规」不等于「对下一单元无影响」；登记要带**可复算的量**（镜号／坐标／字符数），
  下一个单元开工前逐条回核是否已被上游改动消除；审计类结论与合规违规分列（前者不拦锁、后者才拦），**但两者都要进台账**。

#### 5. 出口闸

`validate.mjs --unit U01` → **error 0 / 通过 11/11 规则 / warning 2**（既有项）；`--unit U02` → **error 0 / warning 14**（基线）；
`render-md.mjs` 单向重渲染；**U01 单元锁未动**（`locked` @ 2026-10-23 01:28，L1–L4 全 pass）。
"""

    # ================= D. 99_交付说明.md =================
    heads = [l for l in deliv.split("\n") if l.startswith("## ")]
    nums = []
    for h in heads:
        body = h[3:].split("、", 1)[0].strip()
        try:
            nums.append((cn_to_int(body), h))
        except KeyError:
            pass
    if not nums:
        sys.exit("[ABORT] 交付说明未解析到任何中文节号；不写盘。")
    max_n = max(n for n, _ in nums)
    new_n = max_n + 1
    new_cn = int_to_cn(new_n)
    if f"## {new_cn}、" in deliv:
        sys.exit(f"[ABORT] 交付说明已含 §{new_cn}；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + f"""
## {new_cn}、U02 开工前置两条登记 ＋ S1 时点快照订正 ＋ D18 v1.33（**企划合规 2026-10-23 03:08–03:18**）

### {new_cn}.1 认盘结论：五份回执已登记，本岗只补五处缺口

D15 v1.2／D16 v1.6／D12 v1.4／U02 D06＋D07／U02-F01／TOOL-04／S10／S11／Q40–Q44 **均已由并行实例登记**（D18 v1.32），
本岗**不重复记账**。补办五项：**U02-R01**（工具链单测参数化 ＋ handoff README 记新链 ＋ `make_plan.py` 归档裁定 ＝ **S12**）、
**U02-R02**（D14 取景贴边 ＋ 提示词预算零余量）、**S1 末句时点快照订正**、索引 §二/§六 回刷、本节登记。

### {new_cn}.2 U02-R01：工具链单测参数化 ＋ README 记新链（S12 裁决）

- 三个脚本按 `--unit` 参数化，**禁止 `_u02` 副本**（副本＝第二套实现，必然分叉）。
- `04_工具/handoff/README.md` 补记现役新链 ＋ 两条场景规格约定（`pose` × 底面 z × 时间比例布轨；道具 `center_m[2]` ＝ 几何体心）。
- `04_工具/handoff/make_plan.py` **归档（可恢复退役）** —— 新链已绕开它，留着会被重跑打回已核验的 D14。
- 拦 U02 的 D13／D14；**不拦** D08／D09／D11／D16／D12／D15。工具改动不在本岗单写者范围，**只裁口径与排期**。

### {new_cn}.3 U02-R02：D14 取景审计两类提示级发现（只登记不代改）

- 贴边：`ep05_shot02` 叶承钧 12%×100% @x=94；`ep06_shot03`／`ep07_shot04` 陆沉 @x=3／x=7。
- 预算零余量：`g29=6500`（顶格）、`g22=6498`、`g6=6475`、`g7=6452`、`g26=6441`、`g21=6415`（上限 6,500）。
- 处置：贴边**须在 D11 侧**拉离边缘，不得在白模侧挪主体；余量 <100 字符的镜位**禁止增补**；**均不拦 U01 锁**。

### {new_cn}.4 S1 末句订正 ＋ TOOL-04 排期归属 ＋ 新判据 Q45

- **S1 末句**「D12 两卡原处置与新口径一致，无需返修」＝ 2026-10-22 的时点快照；
  C-006 已于 D12 v1.3 重建时回退、**v1.4 已恢复 S1 口径** → 补时点限定并记订正结果。
- **TOOL-04 排期归属**：**归口出片阶段，文档工厂侧不排期**（比对要触及实际音频产物，超硬边界）；
  U02 开工不需要它。
- **Q45**：提示级发现（非违规但影响下游）必须单独登记 ＋ 带可复算的量；审计结论与合规违规分列，但**都要进台账**。

### {new_cn}.5 出口闸与边界

- `validate.mjs --unit U01` → **通过 11/11 规则，error 0，warning 2**（既有项）；`--unit U02` → error 0（基线）；
  `render-md.mjs` 单向重渲染；**U01 锁态未动**。
- 本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）、本岗补丁脚本。
- **未改**任何交付物内容（D01–D17）、源素材、章程、规格、工具；未生成图片／视频／音频，未合成 TTS，
  未提交 H3 付费生成，未投流上架。**以上游合规裁决为准。**
"""

    # ================= E. 终态自检 =================
    for name, blob in (("D18.json", d18_out), ("project.json", prj_out)):
        if "2026-10-23 03:32" in blob:
            sys.exit(f"[ABORT] {name} 残留未来时间戳；不写盘。")
    if "U02-R01" not in d18_out or "U02-R02" not in d18_out or "Q45" not in d18_out:
        sys.exit("[ABORT] D18 序列化后丢失新增条目；不写盘。")
    if "S12_白模工具链参数化与归档裁定" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S12；不写盘。")
    if "时点快照" not in prj_out:
        sys.exit("[ABORT] project.json S1 时点限定未写入；不写盘。")
    if idx.count("### 十·三十一") != 1:
        sys.exit("[ABORT] 索引 §十·三十一 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 v1.32→v1.33（+open_issues U02-R01/U02-R02 ＋ global_checks Q45）；"
              f"project.json（S1 末句订正 ＋ S12）；索引（§二 4 处 ＋ §六 表头与 U02 两行 ＋ §十·三十一）；"
              f"交付说明 §{new_cn}（运行时最大节号 {max_n}＋1）")
        return

    write(p18, d18_out)
    write(p_prj, prj_out)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 台账缺口回填完成")
    print(f"   shared/D18.json：v1.32 → {d18['version']}（+U02-R01 +U02-R02 +Q45；global_checks {len(d18['global_checks'])}）")
    print(f"   project.json：S1 末句补时点限定 ＋ 新增 S12；updated_at → {NOW}")
    print(f"   00_项目索引.md：§二 4 处 ＋ §六 表头与 U02 两行 ＋ §十·三十一")
    print(f"   99_交付说明.md：新增 §{new_cn}（运行时取最大节号 {max_n}＋1）")


if __name__ == "__main__":
    main()
