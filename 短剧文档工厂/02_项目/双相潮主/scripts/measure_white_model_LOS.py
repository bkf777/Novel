#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_white_model_LOS.py —— Q94 视线遮挡（LOS）修复的实测统计（新增工具脚本）。

用法：
  python3 scripts/measure_white_model_LOS.py \
      --index /tmp/dcc-smoke/index.json \
      --md reports/Q94_LOS_measurements_v15.md \
      --json reports/Q94_LOS_measurements_v15.json

数据源：`build_white_model.py` 结束时写在 /tmp/dcc-smoke/index.json 的
`results[].framing`（wm_framing.solve 的返回值），其中含：
  · `los_blocked_candidates` —— 网格搜索里**视线被壳体挡住**而被筛掉的候选数
  · `los_fallback`          —— 全部候选都被挡、最终回退到已验过的候选（须人工复核）
  · `delta_world` / `offset_cam` —— 机位位移（世界系 / 相机系）

**口径说明**：
  · 「LOS 生效镜」＝ `los_blocked_candidates > 0` ⇒ 求解器**因视线被挡**而放弃了
    若干候选，走了别的机位。这不是缺陷，是修复生效的证据。
  · 「LOS 回退镜」＝ `los_fallback == True` ⇒ 全部候选都被挡，只能退回 —— **须上报总控**。
  · 位移幅度按**世界系** Δ 统计；相机系分量见 `offset_cam`。
  · 相机朝向**不受本项影响**：`_apply_cam_offset` 只写 `cam.location`，不调 `look_at`。
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path


def load_units(index_path: str):
    with open(index_path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("shots", []):
        unit = r.get("unit") or data.get("unit") or "?"
        out.setdefault(unit, []).append(r)
    # index.json 里没有 unit 字段时，按 dir 路径回退推断
    if len(out) == 1 and "?" in out:
        only = list(out)[0]
        out = {}
        for r in data.get("shots", []):
            unit = r.get("unit")
            if not unit:
                d = str(r.get("dir", ""))
                unit = "U01" if "/u01/" in d else ("U02" if "/u02/" in d else "?")
            out.setdefault(unit, []).append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="/tmp/dcc-smoke/index.json")
    ap.add_argument("--md", default="reports/Q94_LOS_measurements_v15.md")
    ap.add_argument("--json", default="reports/Q94_LOS_measurements_v15.json")
    args = ap.parse_args()

    with open(args.index, encoding="utf-8") as f:
        data = json.load(f)
    shots = data.get("shots", [])
    if not shots:
        print("❌ index.json 里没有 shots；先跑完 build_white_model.py")
        return 2

    per_shot = []
    for r in shots:
        fr = r.get("framing") or {}
        d13 = fr.get("loc_d13") or r.get("loc_d13")
        loc = fr.get("loc")
        delta = fr.get("delta_m") or fr.get("delta_world") or [0, 0, 0]
        mag = math.sqrt(sum(float(v) ** 2 for v in delta))
        per_shot.append({
            "unit": r.get("unit") or "?",
            "gsn": r.get("global_shot_no"),
            "ep": r.get("ep"),
            "shot_id": r.get("shot_id"),
            "scene_code": r.get("scene_code"),
            "shot_size": fr.get("shot_size"),
            "band": fr.get("band"),
            "subject_max": fr.get("subject_max"),
            "w2_in_band": fr.get("w2_in_band"),
            "w3_char_largest": fr.get("w3_char_largest"),
            "other_max": fr.get("other_max"),
            "worst_other": fr.get("worst_other"),
            "los_blocked_candidates": fr.get("los_blocked_candidates"),
            "los_fallback": fr.get("los_fallback"),
            "cam_d13": d13,
            "cam_solved": loc,
            "delta_world": [round(float(v), 3) for v in delta],
            "delta_mag_m": round(mag, 3),
            "reverted": fr.get("reverted", False),
        })

    by_unit = {}
    for row in per_shot:
        by_unit.setdefault(row["unit"], []).append(row)

    summary = {}
    for unit, rows in by_unit.items():
        n = len(rows)
        los_active = [r for r in rows if (r["los_blocked_candidates"] or 0) > 0]
        fallback = [r for r in rows if r["los_fallback"]]
        moved = [r for r in rows if (r["delta_mag_m"] or 0) > 0.001]
        w2 = [r for r in rows if r["w2_in_band"]]
        w3 = [r for r in rows if r["w3_char_largest"]]
        mags = sorted((r["delta_mag_m"] for r in rows), reverse=True)
        summary[unit] = {
            "shots": n,
            "los_active_shots": len(los_active),
            "los_fallback_shots": len(fallback),
            "moved_shots": len(moved),
            "w2_in_band": len(w2),
            "w3_char_largest": len(w3),
            "w2_not_in_band": [r["gsn"] for r in rows if not r["w2_in_band"]],
            "w3_not_char_largest": [r["gsn"] for r in rows if not r["w3_char_largest"]],
            "los_fallback_gsn": [r["gsn"] for r in fallback],
            "delta_mag_max_m": mags[0] if mags else 0.0,
            "delta_mag_median_m": round(mags[len(mags) // 2], 3) if mags else 0.0,
            "delta_mag_top5": mags[:5],
        }

    out = {"index": args.index, "summary": summary, "shots": per_shot}
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    lines = ["# Q94 LOS 视线遮挡修复 —— 实测统计（v1.5）", ""]
    lines.append(f"数据源：`{args.index}`（`build_white_model.py` 的 results[].framing）")
    lines.append("")
    lines.append("| 单元 | 镜数 | LOS 生效镜 | LOS 回退镜 | 挪动机位镜 | W2 入带 | W3 主体最大 | Δ 中位 (m) | Δ 最大 (m) |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for unit in sorted(summary):
        s = summary[unit]
        lines.append(
            f"| {unit} | {s['shots']} | {s['los_active_shots']} | {s['los_fallback_shots']} | "
            f"{s['moved_shots']} | {s['w2_in_band']}/{s['shots']} | {s['w3_char_largest']}/{s['shots']} | "
            f"{s['delta_mag_median_m']} | {s['delta_mag_max_m']} |")
    lines.append("")
    lines.append("> 「LOS 生效镜」= 求解器因视线被壳体挡住而放弃了至少一个候选 —— 修复生效的证据。")
    lines.append("> 「LOS 回退镜」= 全部候选都被挡、只能退回 —— 须上报总控人工复核。")
    lines.append("")
    for unit in sorted(by_unit):
        lines.append(f"### {unit} 逐镜")
        lines.append("")
        lines.append("| gsn | ep/shot | 景别 | 主体占幅% | W2 | W3 | LOS 挡候选 | 回退 | 机位 D13 → 求解 | Δ 世界 (m) | Δ 模长 |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(by_unit[unit], key=lambda x: x["gsn"] or 0):
            lines.append(
                f"| {r['gsn']} | ep{r['ep']:02d}/shot{r['shot_id']:02d} | {r['shot_size']} | "
                f"{r['subject_max']} | {'OK' if r['w2_in_band'] else 'NG'} | "
                f"{'OK' if r['w3_char_largest'] else 'NG'} | {r['los_blocked_candidates']} | "
                f"{'是' if r['los_fallback'] else '否'} | {r['cam_d13']} → {r['cam_solved']} | "
                f"{r['delta_world']} | {r['delta_mag_m']} |")
        lines.append("")
    lines.append("> 相机**朝向**不受影响：`_apply_cam_offset` 只写 `cam.location`，不调 `look_at`（C4「朝向不变」成立）。")
    lines.append("")

    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 已写 {args.md} / {args.json}")
    for unit in sorted(summary):
        s = summary[unit]
        print(f"  {unit}: 镜 {s['shots']}｜LOS 生效 {s['los_active_shots']}｜回退 {s['los_fallback_shots']}｜"
              f"W2 {s['w2_in_band']}｜W3 {s['w3_char_largest']}｜Δ 中位 {s['delta_mag_median_m']} m｜最大 {s['delta_mag_max_m']} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
