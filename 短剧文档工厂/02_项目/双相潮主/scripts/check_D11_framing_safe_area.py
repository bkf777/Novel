#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D11 取景安全区核验（只读 · 幂等 · exit 0 ＝ 无 error）

为什么有这个脚本
----------------
D14 的 `tracked_instances[].center_x_percent / bbox_width_percent` 是**白模实测**的画面占位，
但校验器 V1–V11 **不覆盖取景轴**（V11 只校 32 镜覆盖与逐镜包一致性）。2026-10-23 03:0x
白模场景师首次手工做 32 镜取景审计，报出「贴边」三镜（登记为 U02-R02）；手工审计不可复跑 →
本脚本把该轴固化为**可复跑、可审计的量化产出**。

判据定义（写死在脚本头部，复算须按此读；改动须同步改本段与 D18 登记）
----------------------------------------------------------------
- **主体实体**：逐镜包 `render_contract.entities[]` 中 `importance == "primary"` 的实体
  （即该镜的主角色）；回退条件：`entity_label` 含 `CHAR` 且**不含** `Hand`
  （手部／局部代理不是主体，出入画被画框切边的角色也不是缺陷）。
- **主体实例**：逐锚点 `tracked_instances[]` 中 `entity_label` 与主体实体一致者。
- **判据 E1「主体整镜缺席」**（**error**）：主体在**全部锚点**均无 `visibility == "visible"`
  的实例 → 主体整镜不在画内，属画面事故。
  ⚠️ 本条是**唯一有确定性的缺陷判定**；其余一律为提示级。
- **判据 W1「主体贴边」**（**warn · 提示级 · 不拦锁**）：主体在可见锚点中的最差净距
  `min(left, 100 − right)` < 5%，其中 `left = cx − w/2`、`right = cx + w/2`（画面宽百分比）。
- **判据 P1「主体出框」**（**信息 · 不判缺陷**）：可见锚点中存在 `left < 0` 或 `right > 100`。
  **角色出入画、近景切边是正常电影语言**，故不判 error；但必须量化列出供人工判读。
- **例外**：`visibility == "offscreen"` 的实例不参与净距计算（该帧主体不在画内是设计意图）；
  主体自画外入画（首锚点 offscreen、后续可见）按**可见锚点**判定。

**为什么把「贴边／出框」降为提示级**（方法论，与 D12 侧同源）：
D12 侧首版用「8 字连续子串」判覆盖，32 镜误报 18 条 —— 提示级判据**有固有假阳性，不得据以
单独判缺陷**。本脚本首版按「任何可见实例 + 宽度 ≤40%」判，误报 22 条（把手部代理、场景壳体、
出入画切边全算成主体）；改为「按 entities[].importance=primary 认主体」后误报清零，
并用**已知正确结论**（白模场景师「主体在画 32/32 通过」）反向验证口径一致。

归口原则（输出中的「归口建议」即按此判定，勿改）
----------------------------------------------
主体贴边/出框的**修法优先级**：
1. **D11 侧取景参数** —— 源码实测（`build_white_model_u01.py`）：
   白模链**真正消费**的 D11 字段只有 **`duration_sec`**（帧数）与 **`lens_mm`**（`cam_data.lens`）；
   `movement` 与 `visual_facts` **只进索引、零解析**，`shot_size`（景别）**零引用**。
   → D11 侧唯一真正改变主体在画框中占位的旋钮是**焦距**（更广焦距 → 主体更小、更靠中）；
     改景别／改画面文案只影响 **D12 卡头文字**，不改变白模几何。
2. **D13 侧机位与人物站位** —— 主体世界坐标与机位坐标属 D13（白模说明书）。
3. ⛔ **禁止**在 D14 白模侧单独挪主体 —— 白模只锁几何，单独挪主体会造成 D11↔D14 分叉
   （D14 声称的机位/站位与 D11/D13 不再对应），且 D14 是已核验产物，改它＝推翻既有核验。

用法
----
python3 scripts/check_D11_framing_safe_area.py --project 02_项目/双相潮主 --unit U01
exit 0 ＝ 无 error（可能有 warn/info，均为提示级、不拦锁）；exit 1 ＝ 有 error。

性质
----
**只读**：不写任何交付物。仅打印表格与统计。
"""
import argparse
import json
import os
import sys

EDGE_WARN = 5.0     # 主体贴边净距阈值（warn · 提示级）


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def primary_entities(rc):
    """本镜主体实体标签集合。"""
    prim = [e.get("label") for e in (rc.get("entities") or [])
            if e.get("importance") == "primary" and e.get("entity_label" if False else "label")]
    if prim:
        return prim
    # 回退：CHAR 且非手部代理
    labels = [e.get("label") for e in (rc.get("entities") or [])]
    fb = [l for l in labels if l and "CHAR" in l.upper() and "HAND" not in l.upper()]
    return fb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unit = args.unit
    cands = []
    if os.path.isabs(args.project):
        cands.append(args.project)
    else:
        cands.append(os.path.join(factory, args.project))
        cands.append(os.path.join(os.getcwd(), args.project))
        cands.append(os.path.abspath(args.project))
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "units", unit, "D11.json")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到含 units/{unit}/D11.json 的项目目录，候选：{cands}")

    d11 = load(os.path.join(proj, "units", unit, "D11.json"))
    # ── 前置条件：D14 白模包 ──
    #   本脚本核验的是 **D11 ↔ D14 白模包** 的取景一致性，**必须**有 D14 才谈得上复算。
    #   缺 D14 时**显式 exit 2 并说明前置条件**，不抛 traceback ——
    #   企划合规 §六十七 ②「U02 的 D14 产出后须用同一脚本复跑一次」，
    #   而 U02 的 D14 尚未产出（白模场景师未开工）→ 该轴**受检 0 条**，结论一律不成立（Q49）。
    d14_path = os.path.join(proj, "units", unit, "D14.json")
    if not os.path.isfile(d14_path):
        n_shots = sum(len(e["shots"]) for e in d11["episodes"])
        print(f"[前置条件缺失] {unit} 尚无 units/{unit}/D14.json —— "
              f"本脚本核验的是 D11 ↔ D14 白模包的取景一致性，D14 未产出 → "
              f"该轴受检 0 条，按 Q49 结论一律不成立。")
        print(f"  现况：{unit} D11 共 {n_shots} 镜在盘；D14 产出后请复跑本脚本。")
        sys.exit(2)
    d14 = load(d14_path)

    d11map = {}
    for e in d11["episodes"]:
        for s in e["shots"]:
            d11map[(e["ep"], s["shot_id"])] = s

    print(f"■ D11 取景安全区核验 · {os.path.basename(proj)} / {unit}")
    print(f"  主体＝entities[].importance=primary（回退：CHAR 且非手部代理）")
    print(f"  E1 主体整镜缺席→error；W1 主体贴边净距<{EDGE_WARN:.0f}%→warn（提示级）；"
          f"P1 主体出框→信息（角色出入画属正常电影语言，不判缺陷）")
    print()
    print(f"{'镜':<12}{'景别/角度':<13}{'焦距':>4}{'运动':<5}{'主体':<30}"
          f"{'可见锚点':>7}{'最差净距':>9}{'最差区间':>18}{'判定':<10}")
    print("-" * 118)

    err = warn = 0
    notes = []
    for s in d14["shots"]:
        key = (s["ep"], s["shot_id"])
        d = d11map.get(key)
        pkg_path = os.path.join(proj, "units", unit, s["package_path"])
        tag = f"ep{s['ep']:02d}/镜{s['shot_id']}"
        if not os.path.isfile(pkg_path):
            print(f"{tag:<12} 逐镜包缺失：{s['package_path']}")
            err += 1
            continue
        rc = load(pkg_path).get("render_contract") or {}
        prim = primary_entities(rc)
        anchors = rc.get("anchors") or []

        # 主体在逐锚点的占位（primary 实体用于 E1；全部角色实体用于 W1 贴边判定）
        per = {lbl: [] for lbl in prim}
        per_char = {}
        for an in anchors:
            for t in an.get("tracked_instances") or []:
                el = t.get("entity_label") or ""
                if el in per:
                    per[el].append(t)
                if "CHAR" in el.upper() and "HAND" not in el.upper():
                    per_char.setdefault(el, []).append(t)
        # 无 primary 实体标注时，用 CHAR 实体兜底
        if not prim:
            for an in anchors:
                for t in an.get("tracked_instances") or []:
                    el = t.get("entity_label") or ""
                    if "CHAR" in el.upper() and "HAND" not in el.upper():
                        per.setdefault(el, []).append(t)

        vis_n = 0
        gap_worst, range_worst, oob_flag, oob_txt = None, None, False, ""
        gap_owner = None
        cut_pct, cut_txt = 0.0, ""
        for lbl, ts in list(per.items()) + list(per_char.items()):
            vts = [t for t in ts if t.get("visibility") == "visible"
                   and t.get("center_x_percent") is not None
                   and t.get("bbox_width_percent") is not None]
            vis_n += len(vts)
            # 贴边/出框判定**只对角色实体**（CHAR 且非手部代理）：
            # ENV/PROP/FX 满幅壳体与特效本就是满幅，贴边是必然 → 不参与判定。
            # 注意：覆盖**所有**角色实体（不限于 primary）—— 白模场景师报的 ep07/镜4
            # 陆沉（@x=7）并非该镜 primary 实体，只看 primary 会漏掉。
            is_char = "CHAR" in (lbl or "").upper() and "HAND" not in (lbl or "").upper()
            if not is_char:
                continue
            for t in vts:
                cx, w = t["center_x_percent"], t["bbox_width_percent"]
                left, right = cx - w / 2.0, cx + w / 2.0
                gap = min(left, 100.0 - right)
                # 被裁比例：出框宽度 / 主体总宽（角色出入画的正常切边 → 比例小）
                cut = (max(0.0, -left) + max(0.0, right - 100.0)) / w * 100.0 if w else 0.0
                if cut > cut_pct:
                    cut_pct, cut_txt = cut, f"{lbl} 被裁 {cut:.0f}%"
                if gap_worst is None or gap < gap_worst:
                    gap_worst, range_worst, gap_owner = gap, (left, right), lbl
                if left < 0 or right > 100:
                    oob_flag = True
                    over = max(0.0, -left) + max(0.0, right - 100.0)
                    if over > 0.05:
                        oob_txt = f"{lbl} 出框 {over:.1f}%（占主体宽 {cut:.0f}%）"

        sz = f"{d['shot_size']}/{d['camera_angle']}" if d else "D11缺"
        lens = d["lens_mm"] if d else "-"
        mv = d["movement"] if d else "-"
        name = (gap_owner or "、".join(sorted(set(per))) or "（未标注主体实体）")
        name = name.replace("Entity ", "")

        verdict = "合规"
        if vis_n == 0:
            verdict = "主体缺席(error)"
            err += 1
        elif gap_worst is not None and gap_worst < EDGE_WARN:
            verdict = "主体贴边(warn)"
            warn += 1
        if oob_flag:
            verdict += "+出框(信息)"
        rw = f"[{range_worst[0]:.1f},{range_worst[1]:.1f}]" if range_worst else "-"
        gw = f"{gap_worst:.1f}%" if gap_worst is not None else "-"
        print(f"{tag:<12}{sz:<13}{str(lens):>4}{mv:<5}{name[:28]:<30}"
              f"{vis_n:>7}{gw:>9}{rw:>18}{verdict:<10}")
        if verdict != "合规":
            notes.append((tag, name, gw, rw, cut_txt or "被裁 0%"))
            # 提示级项：登记可复算的量（镜号 / 实体 / 净距 / 区间 / 出框量）

    print()
    print("── 汇总 ─────────────────────────────────────────────────────────────")
    print(f"  镜数：{len(d14['shots'])}　error：{err}（主体整镜缺席）　warn：{warn}（主体贴边 · 提示级）")
    for n in notes:
        print(f"    {n[0]}  {n[1]}  净距 {n[2]}  区间 {n[3]}  {n[4]}")
    print("  注：「被裁」＝出框宽度 ÷ 主体总宽。被裁 0% ＝bbox 端点恰落在画框线上、实际未裁切；")
    print("      被裁 >0 才是实质裁切（角色出入画的正常切边会被计入，故仍为提示级、需人工判读）。")
    print("  归口：① D11 侧取景参数（白模链真正消费 duration_sec 与 lens_mm；movement／visual_facts 零解析、"
          "shot_size 零引用 → 唯一几何旋钮是焦距）")
    print("        ② D13 侧机位与人物站位　③ ⛔禁止在 D14 白模侧单独挪主体（D11↔D14 分叉）")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
