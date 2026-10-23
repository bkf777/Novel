#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V12 白模构图命中归属诊断（**只读 · 幂等**）。

用途：把 `validate.mjs` 的 V12 error 逐条拆成「**判据口径缺陷**」与「**白模侧实缺陷**」，
让企划合规按数字改口径、白模场景师按数字改取景 —— 避免两边各猜。

读入（只读）：
  <project>/units/<UNIT>/D11.json          景别标签 / 画面事实
  <project>/units/<UNIT>/D14_shots/*/projection.json   逐帧投影占幅
  <project>/units/<UNIT>/D14_shots/*/manifest.json     结构证据（世界坐标）
  <project>/units/<UNIT>/D13.json          机位（position_m / target_m）
  <factory>/03_规格/rules.json            white_model_framing 阈值

输出：每单元一条汇总 + 逐镜归属明细。**不写任何文件。**

用法：
  python3 scripts/check_D14_projection_composition.py --project 02_项目/双相潮主 [--unit U01]

退出码：0＝诊断完成（不判合规，判定归 validate.mjs）；2＝输入缺失。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

KINDS = ["CHAR", "PROP", "LGT", "FX", "EXT"]


def kind_of(name: str) -> str:
    for k in KINDS:
        if k in name:
            return k
    return "OTHER"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def shot_index(d11):
    out = {}
    for ep in d11.get("episodes", []):
        for s in ep.get("shots", []):
            out[(ep["ep"], s["shot_id"])] = s
    return out


def cam_index(d13):
    out = {}
    for sc in d13.get("scenes", []):
        for c in sc.get("camera_positions", []):
            out[int(c["global_shot_no"])] = c
    return out


def char_world(shot_dir: Path):
    """从 manifest 取角色代理的世界坐标（取首个 CHAR 实体）。"""
    mf = shot_dir / "manifest.json"
    if not mf.is_file():
        return None
    m = load(mf)
    for o in (m.get("structure_evidence") or {}).get("objects", []):
        if kind_of(o.get("name", "")) != "CHAR":
            continue
        for s in o.get("samples", []) or []:
            wl = s.get("world_location")
            if wl:
                return [float(v) for v in wl]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="V12 白模构图命中归属诊断（只读）")
    ap.add_argument("--project", default="02_项目/双相潮主")
    ap.add_argument("--unit", default="")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    factory = proj.parent.parent
    rules_path = factory / "03_规格" / "rules.json"
    if not rules_path.is_file():
        print(f"[ABORT] 找不到阈值真源：{rules_path}", file=sys.stderr)
        return 2
    cfg = load(rules_path).get("white_model_framing", {})
    bands = cfg.get("shot_size_bands", {})

    units = [args.unit] if args.unit else sorted(
        u.name for u in (proj / "units").iterdir() if u.is_dir())
    grand = {}
    for unit in units:
        shots_root = proj / "units" / unit / "D14_shots"
        d11p = proj / "units" / unit / "D11.json"
        if not shots_root.is_dir() or not d11p.is_file():
            print(f"[SKIP] {unit}：无 D14_shots 或无 D11.json")
            continue
        d11 = load(d11p)
        src = shot_index(d11)
        d13p = proj / "units" / unit / "D13.json"
        cams = cam_index(load(d13p)) if d13p.is_file() else {}

        buckets = {"A_EXT计入最大对象": 0, "B_并列同值误判": 0,
                   "C_角色本非该镜主体": 0, "D_白模取景实缺陷": 0}
        details = []
        for d in sorted(os.listdir(shots_root)):
            sd = shots_root / d
            pj = sd / "projection.json"
            if not pj.is_file():
                continue
            p = load(pj)
            shot = src.get((p.get("ep"), p.get("shot_id")))
            if shot is None:
                continue

            per = {}
            for fr in p.get("frames", []) or []:
                for name, o in (fr.get("objects") or {}).items():
                    if not o or not o.get("in_frame"):
                        continue
                    h = float((o.get("visible_percent") or {}).get("height") or 0)
                    k = kind_of(name)
                    if h > per.get(k, (0.0, ""))[0]:
                        per[k] = (h, name)
            charmax = per.get("CHAR", (0.0, ""))[0]

            size = shot.get("shot_size")
            band = bands.get(size)
            facts = str(shot.get("visual_facts") or "")

            # W1：角色不在画幅
            if charmax <= 0:
                buckets["C_角色本非该镜主体"] += 1
                details.append((d, size, "C", f"角色占幅 0%（D11 主体线索：{facts[:28]}…）"))

            # W2：占幅超景别区间（白模侧取景）
            if band and charmax > 0 and not (band[0] <= charmax <= band[1]):
                buckets["D_白模取景实缺陷"] += 1
                gsn = int(shot.get("global_shot_no") or 0)
                cam = cams.get(gsn) or {}
                cpos = cam.get("position_m") or []
                cw = char_world(sd)
                dist = ""
                if cpos and cw:
                    dist = f"机位→角色 {math.dist([float(v) for v in cpos[:2]], cw[:2]):.2f}m"
                lens = shot.get("lens_mm")
                details.append((d, size, "D",
                                f"占幅 {charmax:.1f}% 应 [{band[0]},{band[1]}]"
                                f"｜{dist}｜lens {lens}mm｜机位 {cam.get('camera_id', '?')}"))

            # W3：最大对象非角色
            nonchar = {k: v for k, v in per.items() if k != "CHAR" and v[0] > 0}
            if nonchar:
                mx = max(v[0] for v in nonchar.values())
                mk = max(nonchar, key=lambda k: nonchar[k][0])
                if mx > charmax:
                    if mk == "EXT":
                        buckets["A_EXT计入最大对象"] += 1
                        details.append((d, size, "A",
                                        f"最大对象是 EXT「{nonchar['EXT'][1]}」占 {mx:.1f}%"
                                        f"（角色 {charmax:.1f}%）"))
                    else:
                        buckets["D_白模取景实缺陷"] += 1
                        details.append((d, size, "D",
                                        f"最大对象是 {mk}「{nonchar[mk][1]}」占 {mx:.1f}%"
                                        f"（角色 {charmax:.1f}%）"))
                elif mx == charmax and charmax > 0:
                    buckets["B_并列同值误判"] += 1
                    details.append((d, size, "B",
                                    f"角色 {charmax:.1f}% 与 {mk}「{nonchar[mk][1]}」"
                                    f"同值 {mx:.1f}% → 规则严格 > 判为失败"))

        print(f"\n===== {unit}｜V12 命中归属 =====")
        tot = 0
        for k in sorted(buckets):
            print(f"   {k}: {buckets[k]}")
            tot += buckets[k]
        print(f"   （命中条目合计 {tot}；校验器按**镜**合并为一条 error，故条数 ≤ 明细条数）")
        for d, size, b, txt in details:
            print(f"     [{b}] {d}（{size}）{txt}")
        grand[unit] = buckets

    print("\n===== 汇总 =====")
    for unit, b in grand.items():
        rule_side = b["A_EXT计入最大对象"] + b["B_并列同值误判"] + b["C_角色本非该镜主体"]
        print(f"   {unit}：判据口径侧 {rule_side} 条（需改 rules.mjs/rules.json）"
              f"｜白模侧实缺陷 {b['D_白模取景实缺陷']} 条（需改白模取景）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
