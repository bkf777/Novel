#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机位旋转关键帧「Euler 分支远路插值」影响面量化（只读）

根因（U01-R34 ep01_shot03 1/6 灰板）：
  build_white_model.py 只在首/尾帧给 rotation_euler 打关键帧，中间按 **Euler 分量线性插值**。
  首尾两个 look_at 朝向若落在不同的 ±180° 分支（如 首 yaw=-35.8°、尾 yaw=+195.8°），
  线性插值会走 **远路**（+231.6°），中途相机转向空处 → 整帧平场（unique=1, std=0.00）。

本脚本对每个单元的每镜算出首尾朝向差，标出「走了远路」的镜位。
判据：Euler 分量差 > 180° ⇒ 该镜的插值路径与最短弧不一致（潜在灰板/朝向错）。
"""
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quat_to_euler_xyz(w, x, y, z):
    """Blender XYZ 序欧拉角（弧度）。"""
    m00 = 1 - 2 * (y * y + z * z)
    m01 = 2 * (x * y - z * w)
    m02 = 2 * (x * z + y * w)
    m10 = 2 * (x * y + z * w)
    m11 = 1 - 2 * (x * x + z * z)
    m12 = 2 * (y * z - x * w)
    m20 = 2 * (x * z - y * w)
    m21 = 2 * (y * z + x * w)
    m22 = 1 - 2 * (x * x + y * y)
    # R = Rz(rz) Ry(ry) Rx(rx) ⇒ r = atan2(m21, m22), p = asin(-m20), y = atan2(-m10, m00)
    ry = math.asin(max(-1.0, min(1.0, -m20)))
    rx = math.atan2(-m21, m22)
    rz = math.atan2(-m10, m00)
    return rx, ry, rz


def look_at_quat(loc, tgt):
    """复刻 Blender 的 look_at：d.to_track_quat('-Z','Y')。"""
    dx, dy, dz = (tgt[0] - loc[0], tgt[1] - loc[1], tgt[2] - loc[2])
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    d = (dx / n, dy / n, dz / n)
    # 相机 -Z 轴指向 d，Y 轴尽量朝世界 +Z
    zc = (-d[0], -d[1], -d[2])
    up = (0.0, 0.0, 1.0)
    xc = (up[1] * zc[2] - up[2] * zc[1],
          up[2] * zc[0] - up[0] * zc[2],
          up[0] * zc[1] - up[1] * zc[0])
    n2 = math.sqrt(sum(v * v for v in xc)) or 1.0
    xc = tuple(v / n2 for v in xc)
    yc = (zc[1] * xc[2] - zc[2] * xc[1],
          zc[2] * xc[0] - zc[0] * xc[2],
          zc[0] * xc[1] - zc[1] * xc[0])
    # 旋转矩阵列 = (xc, yc, zc) → 转四元数
    m00, m01, m02 = xc[0], yc[0], zc[0]
    m10, m11, m12 = xc[1], yc[1], zc[1]
    m20, m21, m22 = xc[2], yc[2], zc[2]
    tr = m00 + m11 + m22
    if tr > 0:
        S = math.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (m21 - m12) / S
        y = (m02 - m20) / S
        z = (m10 - m01) / S
    elif (m00 > m11) and (m00 > m22):
        S = math.sqrt(1.0 + m00 - m11 - m22) * 2
        w = (m21 - m12) / S
        x = 0.25 * S
        y = (m01 + m10) / S
        z = (m02 + m20) / S
    elif m11 > m22:
        S = math.sqrt(1.0 + m11 - m00 - m22) * 2
        w = (m02 - m20) / S
        x = (m01 + m10) / S
        y = 0.25 * S
        z = (m12 + m21) / S
    else:
        S = math.sqrt(1.0 + m22 - m00 - m11) * 2
        w = (m10 - m01) / S
        x = (m02 + m20) / S
        y = (m12 + m21) / S
        z = 0.25 * S
    return (w, x, y, z)


def aim_azimuth(loc, tgt):
    dx, dy = tgt[0] - loc[0], tgt[1] - loc[1]
    return math.degrees(math.atan2(dy, dx))


def main():
    print("=" * 104)
    print("机位旋转关键帧「Euler 分支远路插值」影响面（只读）")
    print("=" * 104)
    for unit in ("U01", "U02"):
        d13 = json.load(open(os.path.join(PROJ, "units", unit, "D13.json"), encoding="utf-8"))
        wm = load_module(f"white_model_content_{unit}",
                         os.path.join(HERE, f"white_model_content_{unit}.py"))
        CAM_MOVE = wm.CAM_MOVE
        cams = {}
        for sc in d13["scenes"]:
            for cp in sc.get("camera_positions", []):
                cams[cp["global_shot_no"]] = cp
        print(f"\n──── {unit} ────")
        print(f'{"gsn":<5}{"运镜":<12}{"首端yaw":<10}{"尾端yaw":<10}{"Δyaw(分量)":<14}{"方位首":<10}{"方位尾":<10}判定')
        print("-" * 104)
        bad = []
        for gsn in sorted(cams):
            cp = cams[gsn]
            mv = CAM_MOVE.get(gsn, ("static", None, None))
            motion, end_pos, ratio = mv
            start = list(cp["position_m"])
            tgt = list(cp.get("target_m") or cp["position_m"])
            if motion == "static" or (end_pos is None and not ratio):
                continue
            if end_pos is not None:
                end = list(end_pos)
            else:  # dolly+ratio：朝 target 走 (1-ratio) 段
                end = [start[i] + (tgt[i] - start[i]) * (1.0 - ratio) for i in range(3)]
            e1 = quat_to_euler_xyz(*look_at_quat(start, tgt))
            e2 = quat_to_euler_xyz(*look_at_quat(end, tgt))
            d = [(e2[i] - e1[i]) for i in range(3)]
            dz_deg = math.degrees(d[2])
            long_way = any(abs(math.degrees(v)) > 180.0 for v in d)
            az1, az2 = aim_azimuth(start, tgt), aim_azimuth(end, tgt)
            verdict = "⛔ 远路插值" if long_way else "OK"
            if long_way:
                bad.append(gsn)
            print(f"{gsn:<5}{motion:<12}{math.degrees(e1[2]):<10.1f}{math.degrees(e2[2]):<10.1f}"
                  f"{dz_deg:<14.1f}{az1:<10.1f}{az2:<10.1f}{verdict}")
        print(f"  ⇒ 远路插值镜位：{bad if bad else '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
