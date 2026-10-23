#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_anchor_quality.py —— 白模锚点帧「纯色板/白板」度实测（新增工具脚本）。

用法（单盘）：
  python3 scripts/measure_anchor_quality.py --root units/U01/D14_shots --unit U01 \
      --md reports/Q94_anchor_quality_U01_v15.md

用法（两盘对比）：
  python3 scripts/measure_anchor_quality.py --unit U01 \
      --root-a /tmp/q94_v14_snapshot/U01 --root-b units/U01/D14_shots \
      --label-a v1.4 --label-b v1.5 \
      --md reports/Q94_anchor_quality_U01_cmp.md

原理：白模渲坏时不是「主体不见了」，而是**整帧渲成一块白墙/灰板**。
这类画面的灰度标准差（std）极小 —— 纯色板 std≈0，正常白模画面（人＋地板＋墙＋阴影）
std 明显大于 0。故用**逐帧灰度 std** 作「画面是否有内容」的客观指纹。

⚠️ ffmpeg 的 `signalstats` 在本机返回 YSTD=-1（不可用），故改为：
  `ffmpeg -i <img> -vf scale=64:114 -f rawvideo -pix_fmt gray -` → Python 直算 std。
  缩到 64×114 是为了快（64 锚点帧 × 64 镜），且不影响「是否纯色」的判定。
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
W, H = 64, 114
PURE_STD = 2.0        # 灰度 std 低于此值 ⇒ 判「近纯色（白板/灰板）」


def frame_std(path: str):
    """返回该图的灰度 std（None = 解码失败）。"""
    try:
        r = subprocess.run(
            [FFMPEG, "-v", "error", "-i", path, "-vf", f"scale={W}:{H}",
             "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, timeout=60)
    except Exception:
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    buf = r.stdout
    n = len(buf)
    mean = sum(buf) / n
    var = sum((b - mean) ** 2 for b in buf) / n
    return math.sqrt(var)


def scan(root: str, unit: str):
    """扫一个根目录，返回 {shot_name: {...}}。

    支持四种目录形态：
      · <root>/D14_shots/ep*_shot*        （root = units/U01 或 快照根）
      · <root>/<unit>/D14_shots/ep*_shot*  （root = 上层目录）
      · <root>/<unit>/ep*_shot*
      · <root>/ep*_shot*
    """
    out = {}
    r = Path(root)
    cands = [r / "D14_shots", r / unit / "D14_shots", r / unit, r]
    base = None
    for c in cands:
        if c.is_dir() and any(c.glob("ep*_shot*")):
            base = c
            break
    if base is None:
        return out
    for shot_dir in sorted(base.glob("ep*_shot*")):
        frames = sorted(glob.glob(str(shot_dir / "source_anchor_frames" / "anchor_*.jpg")))
        if not frames:
            continue
        stds = []
        for fp in frames:
            s = frame_std(fp)
            if s is not None:
                stds.append(s)
        if not stds:
            continue
        out[shot_dir.name] = {
            "frames": len(frames),
            "std_max": round(max(stds), 3),
            "std_mean": round(sum(stds) / len(stds), 3),
            "std_min": round(min(stds), 3),
            # 镜级「全纯色」＝该镜**每一帧**都是纯色
            "pure": bool(max(stds) < PURE_STD),
            # 镜级「含纯色帧」＝该镜**至少一帧**是纯色（机位越界只发生在部分时刻时，
            #   全部帧判据会漏掉 ⇒ 必须两档并列看）
            "has_pure_frame": bool(any(s < PURE_STD for s in stds)),
            "pure_frames": sum(1 for s in stds if s < PURE_STD),
            "stds": [round(s, 3) for s in stds],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--root", help="单盘模式：含 D14_shots 的根")
    ap.add_argument("--root-a", help="对比模式 A 根")
    ap.add_argument("--root-b", help="对比模式 B 根")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--md", required=True)
    args = ap.parse_args()

    if args.root_a and args.root_b:
        A = scan(args.root_a, args.unit)
        B = scan(args.root_b, args.unit)
    elif args.root:
        A = scan(args.root, args.unit)
        B = {}
    else:
        print("❌ 需给 --root 或 --root-a/--root-b")
        return 2

    common = sorted(set(A) & set(B))
    improved, regressed = [], []
    for k in common:
        a, b = A[k], B[k]
        if a["pure"] and not b["pure"]:
            improved.append(k)
        elif (not a["pure"]) and b["pure"]:
            regressed.append(k)

    lines = [f"# 锚点帧画面内容度实测 —— {args.unit}", ""]
    lines.append(f"判据：逐帧灰度 std < {PURE_STD} ⇒ 判「近纯色（白板/灰板）」。")
    lines.append("")
    if B:
        lines.append(f"| 指标 | {args.label_a} | {args.label_b} |")
        lines.append("|---|---|---|")
        lines.append(f"| 有锚点帧的镜数 | {len(A)} | {len(B)} |")
        lines.append(f"| 近纯色镜数（**全部帧**皆纯色） | {sum(1 for v in A.values() if v['pure'])} | "
                     f"{sum(1 for v in B.values() if v['pure'])} |")
        lines.append(f"| 含纯色帧的镜数（**至少一帧**纯色） | "
                     f"{sum(1 for v in A.values() if v['has_pure_frame'])} | "
                     f"{sum(1 for v in B.values() if v['has_pure_frame'])} |")
        lines.append(f"| 纯色帧总数 | {sum(v['pure_frames'] for v in A.values())} | "
                     f"{sum(v['pure_frames'] for v in B.values())} |")
        lines.append(f"| 逐镜 std 最大值的中位 | "
                     f"{sorted(v['std_max'] for v in A.values())[len(A)//2] if A else 0} | "
                     f"{sorted(v['std_max'] for v in B.values())[len(B)//2] if B else 0} |")
        lines.append("")
        lines.append(f"**改善镜（{args.label_a} 含纯色帧 → {args.label_b} 无纯色帧）："
                     f"{sum(1 for k in common if A[k]['has_pure_frame'] and not B[k]['has_pure_frame'])}**")
        lines.append("")
        lines.append(f"**退步镜（{args.label_a} 无纯色帧 → {args.label_b} 含纯色帧）："
                     f"{sum(1 for k in common if (not A[k]['has_pure_frame']) and B[k]['has_pure_frame'])}**")
        lines.append("")
        lines.append("| 镜 | " + f"{args.label_a} std_max | {args.label_b} std_max | "
                     f"{args.label_a} 纯色帧 | {args.label_b} 纯色帧 |")
        lines.append("|---|---|---|---|---|")
        for k in common:
            lines.append(f"| {k} | {A[k]['std_max']} | {B[k]['std_max']} | "
                         f"{A[k]['pure_frames']}/{A[k]['frames']} | {B[k]['pure_frames']}/{B[k]['frames']} |")
    else:
        lines.append("| 镜 | 帧数 | std_max | std_mean | std_min | 近纯色 |")
        lines.append("|---|---|---|---|---|---|")
        for k in sorted(A):
            v = A[k]
            lines.append(f"| {k} | {v['frames']} | {v['std_max']} | {v['std_mean']} | "
                         f"{v['std_min']} | {'是' if v['pure'] else '否'} |")
    lines.append("")

    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    with open(args.md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 已写 {args.md}")
    if B:
        print(f"  {args.label_a}: 纯色镜 {sum(1 for v in A.values() if v['pure'])}/{len(A)}")
        print(f"  {args.label_b}: 纯色镜 {sum(1 for v in B.values() if v['pure'])}/{len(B)}")
        print(f"  改善 {len(improved)}｜退步 {len(regressed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
