#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3 镜代表锚点帧拼图（Q94 交付物 4）。

用法：
  python3 scripts/make_anchor_collage.py --out /tmp/wm_probe/anchor_collage.jpg

每镜取 3 张锚点帧，排成 3 行 × 3 列（行＝镜位，列＝该镜的三个采样时刻）。
要求：一眼能看出「是人、头在哪、朝哪」—— 白模角色是「躯干盒＋头＋朝向楔」三件套，
头与朝向楔必须在画面里可辨。

前置：units/<UNIT>/D14_shots/<shot>/source_anchor_frames/anchor_*.jpg 已由
D14 preflight 生成。
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
SHOTS = [
    ("U01", "ep01_shot01", "U01 ep01_shot01（原最差）"),
    ("U02", "ep13_shot02", "U02 ep13_shot02（原无角色）"),
    ("U01", "ep06_shot01", "U01 ep06_shot01（原仅两个方块）"),
]


def pick_frames(shot_dir: Path, n: int = 3):
    """从该镜的锚点帧里挑 n 张：优先分散在序列首/中/尾，便于看出姿态与朝向。"""
    files = sorted(glob.glob(str(shot_dir / "source_anchor_frames" / "anchor_*.jpg")))
    if not files:
        return []
    if len(files) <= n:
        return files
    idx = [round(i * (len(files) - 1) / (n - 1)) for i in range(n)]
    return [files[i] for i in idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/wm_probe/anchor_collage.jpg")
    ap.add_argument("--work", default="/tmp/wm_probe/collage_work")
    args = ap.parse_args()
    if not shutil.which("ffmpeg"):
        print("[FAIL] ffmpeg 不在 PATH", file=sys.stderr)
        return 2
    work = Path(args.work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    picked = []
    for unit, shot, label in SHOTS:
        sd = PROJ / "units" / unit / "D14_shots" / shot
        fs = pick_frames(sd)
        if not fs:
            print(f"[WARN] {unit}/{shot} 没有锚点帧", file=sys.stderr)
            continue
        for i, f in enumerate(fs):
            dst = work / f"{unit}_{shot}_{i:02d}.jpg"
            shutil.copy2(f, dst)
            picked.append((dst, label))
        print(f"[OK] {unit}/{shot}: {len(fs)} 帧")

    if not picked:
        print("[FAIL] 没有任何锚点帧", file=sys.stderr)
        return 2

    n = len(picked)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for f, _ in picked:
        cmd += ["-i", str(f)]
    # 3 行 × 3 列：每行 hstack，三行再 vstack。
    # （xstack 的 layout 串在本机 ffmpeg 上解析异常 —— canvas 只到 1088×4080，
    #   故改用 hstack/vstack 组合，实测尺寸正确。）
    rows = []
    for r in range(3):
        cells = picked[r * 3:(r + 1) * 3]
        if not cells:
            continue
        idx = [i for i in range(n) if r * 3 <= i < r * 3 + 3]
        chain = "".join(f"[{i}:v]" for i in idx)
        rows.append(f"{chain}hstack=inputs={len(idx)}[r{r}]")
    vchain = "".join(f"[r{r}]" for r in range(len(rows)))
    rows.append(f"{vchain}vstack=inputs={len(rows)}[stk]")
    W, H = 1080, 1920
    scale = min(1.0, 1500.0 / (3 * W))
    rows.append(f"[stk]scale=iw*{scale:.4f}:ih*{scale:.4f}[out]")
    cmd += ["-filter_complex", ";".join(rows), "-map", "[out]", "-frames:v", "1", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[:800], file=sys.stderr)
        return 1
    # 自检：拼图必须是 3 列 × 3 行（不是单帧）
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", args.out],
        capture_output=True, text=True)
    print(f"[DONE] {args.out}  ({n} 帧，{len(picked)//3} 行，尺寸 {probe.stdout.strip()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
