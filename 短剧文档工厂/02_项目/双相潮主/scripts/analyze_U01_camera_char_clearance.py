#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U01 机位—角色代理体几何间距分析（只读）

用途：定位「机位落进角色代理体 ⇒ 整帧灰板」的完整病灶集。
判据（与企划合规 2026-10-23 U02-R07 裁定同源）：
  角色代理体最大截面半径 0.25 m（stand 0.50×0.35×1.80）
  机位须与角色轴的水平间距 ≥ 0.35 m（= 0.25 半径 + 0.10 余量）

输出：逐镜「机位↔最近角色」的水平间距、是否达 0.35m、机位是否落在代理体包围盒内。
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)

W = 0.50   # stand 体宽（X）
D = 0.35   # 体深（Y）
H = 1.80   # 体高
R_MAX = 0.25
CLEAR = 0.35


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    d13 = json.load(open(os.path.join(PROJ, "units", "U01", "D13.json"), encoding="utf-8"))
    wm = load_module("white_model_content_U01", os.path.join(HERE, "white_model_content_U01.py"))

    CHARS = wm.CHARS
    CHAR_ANIM = wm.CHAR_ANIM
    CAM_MOVE = wm.CAM_MOVE
    POSE_SIZE = wm.POSE_SIZE

    # (scene_code, gsn) -> [(core, 中文名, x, y, z底, height, pose)]
    def chars_of(sc, gsn):
        if (sc, gsn) in CHARS:
            return CHARS[(sc, gsn)]
        if (sc, gsn) in CHAR_ANIM:
            out = []
            for core, seq in CHAR_ANIM[(sc, gsn)].items():
                for item in seq:
                    ratio, x, y, z, pose = item
                    out.append((core, core, x, y, z, 1.80, pose))
            return out
        return []

    rows = []
    for sc in d13["scenes"]:
        sc_code = sc["scene_code"]
        for cp in sc.get("camera_positions", []):
            gsn = cp["global_shot_no"]
            cam = list(cp["position_m"])
            cands = chars_of(sc_code, gsn)
            best = None
            for core, nm, x, y, z, height, pose in cands:
                psize = POSE_SIZE.get(pose, (W, D, H))
                dx = cam[0] - x
                dy = cam[1] - y
                horiz = (dx * dx + dy * dy) ** 0.5
                # 代理体包围盒（stand/crouch 等为底置盒）
                bx = psize[0] / 2.0
                by = psize[1] / 2.0
                inside = (abs(dx) <= bx and abs(dy) <= by and z <= cam[2] <= z + psize[2])
                rec = (horiz, core, nm, x, y, z, psize, inside)
                if best is None or horiz < best[0]:
                    best = rec
            if best is None:
                rows.append((gsn, sc_code, cam, None))
                continue
            rows.append((gsn, sc_code, cam, best))

    print("=" * 104)
    print("U01 机位↔角色代理体几何间距（离轴水平距离，阈值 0.35 m = 0.25 截面半径 + 0.10 余量）")
    print("=" * 104)
    print(f'{"gsn":<5}{"场景":<6}{"机位":<26}{"最近角色":<16}{"角色轴":<20}{"离轴":<9}{"包围盒内":<10}判定')
    print("-" * 104)
    bad = []
    for gsn, sc_code, cam, b in sorted(rows):
        if b is None:
            print(f"{gsn:<5}{sc_code:<6}{str(cam):<26}{'—':<16}{'—':<20}{'—':<9}{'—':<10}本镜无角色")
            continue
        horiz, core, nm, x, y, z, psize, inside = b
        if inside:
            verdict = "⛔ 机位在代理体内"
            bad.append((gsn, sc_code, cam, b, "inside"))
        elif horiz < CLEAR:
            verdict = f"⚠ 离轴 {horiz:.3f} < 0.35（余量不足）"
            bad.append((gsn, sc_code, cam, b, "near"))
        else:
            verdict = "合规"
        print(f"{gsn:<5}{sc_code:<6}{str(cam):<26}{core:<16}{f'({x},{y},{z})':<20}"
              f"{horiz:<9.3f}{str(inside):<10}{verdict}")
    print("-" * 104)
    print(f"病灶镜位 {len(bad)} 个：")
    for gsn, sc_code, cam, b, kind in bad:
        horiz, core, nm, x, y, z, psize, inside = b
        print(f"   gsn{gsn} {sc_code}  {kind}  离轴 {horiz:.3f}  角色 {core}@({x},{y},{z}) pose={psize}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
