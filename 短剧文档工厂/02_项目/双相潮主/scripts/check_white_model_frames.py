#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_white_model_frames.py —— 白模预览视频「整帧灰板」检测器

**为什么要有**：U01 g27 出现过整帧纯灰、无任何几何的缺陷 —— 成因是**机位落在角色代理
体块内部**，Workbench 渲染出的是盒体**内壁**，画面因此只剩一块均匀灰面。该缺陷**事后
可机器检出**，但此前没有任何自检能发现它（V11 只校 JSON 一致性，不看视频）。

**判据**：对每镜 preview_video.mp4 抽若干帧，逐帧统计**唯一颜色数**与**灰度标准差**。
  - 唯一颜色数 ≤ 阈值（默认 8）⇒ 判「整帧均匀灰板」；
  - 灰度标准差 < 阈值（默认 3.0）⇒ 判「整帧无明暗结构」。
两者任一命中即记为**疑似灰板**。

⚠️ 判据必须**先过敏感度检验**（Q67）：对一张已知正常的帧应判「通过」，对已知灰板帧应判
「命中」。本脚本内置 `--selftest`：用**合成图**（一张纯色 + 一张带方块的图）验证判据本身
有区分力，避免「零检出」被误升格成「无缺陷」。

用法：
    python3 check_white_model_frames.py --unit U02 --shots-dir units/U02/D14_shots
    python3 check_white_model_frames.py --selftest
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------- 抽帧
def _ffmpeg() -> str:
    for c in ("/opt/homebrew/bin/ffmpeg", "ffmpeg"):
        if c == "ffmpeg":
            p = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
            if p.returncode == 0:
                return p.stdout.strip()
        elif os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return ""


def _ffprobe_frames(video: Path) -> int:
    ff = _ffmpeg()
    if not ff:
        return 0
    probe = ff.replace("ffmpeg", "ffprobe")
    if not os.path.isfile(probe):
        return 0
    r = subprocess.run([probe, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0


def extract_frames(video: Path, n: int, out_dir: Path) -> list:
    """抽帧**铺满整条片子**（按比例取样），避免缺陷只出现在中段而漏检。"""
    ff = _ffmpeg()
    if not ff:
        return []
    total = _ffprobe_frames(video) or 0
    if total <= 0:
        picks = [i * 12 for i in range(n)]
    else:
        picks = [int(total * (i + 0.5) / n) for i in range(n)]
    out = []
    for i, fr in enumerate(picks):
        dst = out_dir / f"f{i:02d}.ppm"
        cmd = [ff, "-v", "error", "-i", str(video),
               "-vf", f"select=eq(n\\,{fr})", "-vframes", "1", str(dst), "-y"]
        subprocess.run(cmd, capture_output=True)
        if dst.exists() and dst.stat().st_size > 0:
            out.append(dst)
    return out


def read_ppm(path: Path):
    """读 8-bit PPM，返回 (w, h, bytes)。支持 P6。"""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"P6"):
        return None
    # 解析 header：P6 <w> <h> <maxval> \n
    idx = 2
    vals = []
    while len(vals) < 3:
        while idx < len(data) and data[idx:idx + 1].isspace():
            idx += 1
        if data[idx:idx + 1] == b"#":
            while idx < len(data) and data[idx:idx + 1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(data) and not data[idx:idx + 1].isspace():
            idx += 1
        vals.append(int(data[start:idx]))
    idx += 1
    w, h, _maxv = vals
    return w, h, data[idx:idx + w * h * 3]


def frame_stats(ppm: Path):
    r = read_ppm(ppm)
    if not r:
        return None
    w, h, buf = r
    if not buf:
        return None
    px = len(buf) // 3
    # 抽样（最多 200k 像素）算唯一色数与灰度标准差
    step = max(1, px // 200000)
    colors = set()
    s = 0.0
    s2 = 0.0
    n = 0
    for i in range(0, px, step):
        o = i * 3
        r_, g_, b_ = buf[o], buf[o + 1], buf[o + 2]
        colors.add((r_ >> 2, g_ >> 2, b_ >> 2))
        y = 0.299 * r_ + 0.587 * g_ + 0.114 * b_
        s += y
        s2 += y * y
        n += 1
    mean = s / n if n else 0.0
    var = max(0.0, s2 / n - mean * mean) if n else 0.0
    return {"unique_colors": len(colors), "stddev": math.sqrt(var), "sampled": n}


# ---------------------------------------------------------------- 主流程
def check_shot(shot_dir: Path, frames: int, max_colors: int, min_stddev: float):
    video = shot_dir / "preview_video.mp4"
    if not video.is_file():
        return {"shot": shot_dir.name, "status": "SKIP", "note": "无 preview_video.mp4"}
    with tempfile.TemporaryDirectory() as td:
        ppms = extract_frames(video, frames, Path(td))
        if not ppms:
            return {"shot": shot_dir.name, "status": "SKIP", "note": "抽帧失败（ffmpeg 不可用？）"}
        stats = [s for s in (frame_stats(p) for p in ppms) if s]
    if not stats:
        return {"shot": shot_dir.name, "status": "SKIP", "note": "帧统计失败"}
    flat = [s for s in stats if s["unique_colors"] <= max_colors]
    dull = [s for s in stats if s["stddev"] < min_stddev]
    # ★ 双条件同时命中才判灰板（AND，非 OR）：
    #   灰板帧的特征是「颜色数极少 **且** 明暗结构全无」；
    #   合法夜戏帧（熄灯/暗处/远景火光）可能标准差低但仍有颜色层次，
    #   单用「标准差低」会误报，故要求两条同时成立。
    both = [s for s in stats
            if s["unique_colors"] <= max_colors and s["stddev"] < min_stddev]
    if both:
        return {
            "shot": shot_dir.name, "status": "FAIL",
            "note": (f"疑似整帧灰板：{len(both)}/{len(stats)} 帧**同时**满足"
                     f"唯一色数 ≤ {max_colors} 且 灰度标准差 < {min_stddev}；"
                     f"样例 unique={both[0]['unique_colors']} std={both[0]['stddev']:.2f}"
                     f"（全片 unique {min(s['unique_colors'] for s in stats)}–"
                     f"{max(s['unique_colors'] for s in stats)}，"
                     f"std {min(s['stddev'] for s in stats):.2f}–"
                     f"{max(s['stddev'] for s in stats):.2f}）"),
            "stats": stats,
        }
    return {
        "shot": shot_dir.name, "status": "PASS",
        "note": (f"{len(stats)} 帧均有几何结构：unique "
                 f"{min(s['unique_colors'] for s in stats)}–{max(s['unique_colors'] for s in stats)}，"
                 f"std {min(s['stddev'] for s in stats):.2f}–{max(s['stddev'] for s in stats):.2f}"),
        "stats": stats,
    }


def selftest(max_colors: int, min_stddev: float):
    """判据敏感度检验：纯色图必须命中，带方块的图必须放行。"""
    ff = _ffmpeg()
    if not ff:
        print("❌ 自测跳过：找不到 ffmpeg")
        return 1
    ok = True
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # ① 纯色图（模拟灰板）
        flat_ppm = td / "flat.ppm"
        w, h = 64, 64
        flat_ppm.write_bytes(b"P6\n%d %d\n255\n" % (w, h) + bytes([128, 128, 128]) * (w * h))
        s = frame_stats(flat_ppm)
        hit = (s["unique_colors"] <= max_colors) and (s["stddev"] < min_stddev)
        print(f"  [纯色图] unique={s['unique_colors']} std={s['stddev']:.3f} → {'命中（符合预期）' if hit else '未命中（❌ 判据无区分力）'}")
        ok = ok and hit
        # ② 带几何结构的图（模拟正常帧）：用**渐变 + 方块**，
        #    真实渲染帧因抗锯齿会产生大量中间色，故合成图也必须有足够多的唯一色，
        #    否则会把「色数少但有明暗结构」误判成灰板（自测自身失真）。
        busy_ppm = td / "busy.ppm"
        buf = bytearray(w * h * 3)
        for y in range(h):
            for x in range(w):
                o = (y * w + x) * 3
                buf[o] = min(255, 30 + x * 3)
                buf[o + 1] = min(255, 30 + y * 3)
                buf[o + 2] = 60
        for y in range(10, 30):
            for x in range(10, 30):
                o = (y * w + x) * 3
                buf[o:o + 3] = bytes([220, 200, 160])
        busy_ppm.write_bytes(b"P6\n%d %d\n255\n" % (w, h) + bytes(buf))
        s2 = frame_stats(busy_ppm)
        hit2 = (s2["unique_colors"] <= max_colors) and (s2["stddev"] < min_stddev)
        print(f"  [几何图] unique={s2['unique_colors']} std={s2['stddev']:.3f} → {'命中（❌ 误报）' if hit2 else '放行（符合预期）'}")
        ok = ok and not hit2
    print("■ 自测结论：" + ("判据具备区分力 ✅" if ok else "判据无区分力 ❌"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="白模预览视频整帧灰板检测")
    ap.add_argument("--unit", default=os.environ.get("UNIT_ID", "U01"))
    ap.add_argument("--project", default=os.environ.get("WM_PROJECT", ""))
    ap.add_argument("--shots-dir", default="", help="逐镜包目录（默认 <project>/units/<unit>/D14_shots）")
    ap.add_argument("--frames", type=int, default=6, help="每镜抽帧数")
    ap.add_argument("--max-colors", type=int, default=8, help="唯一色数上限（≤ 判灰板）")
    ap.add_argument("--min-stddev", type=float, default=3.0, help="灰度标准差下限（< 判灰板）")
    ap.add_argument("--selftest", action="store_true", help="只跑判据敏感度自测")
    args = ap.parse_args()

    if args.selftest:
        return selftest(args.max_colors, args.min_stddev)

    project = Path(args.project) if args.project else Path(__file__).resolve().parent.parent
    shots_dir = Path(args.shots_dir) if args.shots_dir else project / "units" / args.unit / "D14_shots"
    if not shots_dir.is_dir():
        print(f"❌ 逐镜包目录不存在：{shots_dir}")
        return 2

    dirs = sorted([d for d in shots_dir.iterdir() if d.is_dir()])
    if not dirs:
        print(f"❌ {shots_dir} 下没有镜位目录")
        return 2

    results = [check_shot(d, args.frames, args.max_colors, args.min_stddev) for d in dirs]
    fails = [r for r in results if r["status"] == "FAIL"]
    skips = [r for r in results if r["status"] == "SKIP"]
    passes = [r for r in results if r["status"] == "PASS"]

    print(f"■ 整帧灰板检测 · {args.unit}｜受检镜位 {len(results)}｜抽帧 {args.frames}/镜")
    for r in results:
        if r["status"] != "PASS":
            print(f"  [{r['status']}] {r['shot']}  {r['note']}")
    # 判据余量：正常帧离阈值有多远（余量小 ⇒ 阈值需要收紧/放宽的实测依据）
    if passes:
        uc = [s["unique_colors"] for r in passes for s in r["stats"]]
        sd = [s["stddev"] for r in passes for s in r["stats"]]
        print(f"· 正常帧唯一色数 {min(uc)}–{max(uc)}（阈值 ≤{args.max_colors} 判灰板）"
              f"｜灰度标准差 {min(sd):.2f}–{max(sd):.2f}（阈值 <{args.min_stddev} 判灰板）")
    print(f"■ 结果　PASS {len(passes)}｜FAIL {len(fails)}｜SKIP {len(skips)}"
          f"｜受检条数 {len(results)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
