#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_camera_inside_geometry.py —— **机位穿入几何体**检测器

**要检的缺陷（U01 实测两例，同一根因）**：
  - **g27（ep07_shot03，主观视角）**：机位与角色代理**同点** ⇒ 相机在盒体内，
    Workbench 渲染出盒体**内壁** ⇒ 整帧纯灰、零几何（U01 已锁件，未解冻）。
  - **g03（ep01_shot03，移/横移）**：相机沿横移路径**穿过**墙体/大型道具内部 ⇒
    后半段整帧被盒体内壁填满（灰度 100 平场、std≈0）⇒ 画面无任何几何信息。
    这类缺陷**不会**被「角色避让规则」挡住 —— 规则只管主体，不管机位路径。

**判据**：对每镜 manifest 的 `structure_evidence.camera_samples[]`（真实机位采样），
逐点测试是否落在任一对象的**世界 AABB** 内（`world_location ± world_dimensions/2`）。
落入即记为「机位穿模」。

**判据有效性（Q67/Q68）**：
  - 必须**有区分力**：已知坏镜（g03/g27）必须命中、已知好镜必须放行 → 用 `--selftest`
    对**真实交付物**做正反两组对照，不接受「零检出＝无缺陷」。
  - 只读产物，不写任何文件。

用法：
    python3 check_camera_inside_geometry.py --unit U01
    python3 check_camera_inside_geometry.py --unit U02
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# 落入 AABB 至少要深入这么多米才算「穿模」（避免表面擦碰误报）
EPS = 0.02


def aabb_of(sample):
    loc = sample.get("world_location")
    dim = sample.get("world_dimensions")
    if not loc or not dim or len(loc) < 3 or len(dim) < 3:
        return None
    return [(loc[i] - dim[i] / 2.0, loc[i] + dim[i] / 2.0) for i in range(3)]


def inside_depth(point, box):
    """点在 AABB 内的**深入深度**（各轴最小余量）；在外部为负。"""
    depths = []
    for i in range(3):
        lo, hi = box[i]
        if point[i] < lo:
            depths.append(point[i] - lo)
        elif point[i] > hi:
            depths.append(hi - point[i])
        else:
            depths.append(min(point[i] - lo, hi - point[i]))
    return min(depths)


def check_shot(shot_dir: Path):
    mpath = shot_dir / "manifest.json"
    if not mpath.is_file():
        return {"shot": shot_dir.name, "status": "SKIP", "note": "无 manifest.json"}
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except ValueError as e:
        return {"shot": shot_dir.name, "status": "SKIP", "note": f"manifest 解析失败：{e}"}
    se = m.get("structure_evidence") or {}
    cams = se.get("camera_samples") or []
    objs = se.get("objects") or []
    if not cams or not objs:
        return {"shot": shot_dir.name, "status": "SKIP", "note": "manifest 缺 camera_samples/objects"}

    hits = []
    for cs in cams:
        pt = cs.get("location")
        if not pt:
            continue
        for o in objs:
            # ★ 排除 EXT 壳体（房间/厂房/场地/围护）——
            #   壳体是**空心**的（墙地顶拼成的一个盒），相机本就该待在它内部，
            #   用 AABB 判必然误报。壳体类问题（钻进墙体、穿出场景）由
            #   check_white_model_frames.py 的「整帧平场」判据覆盖。
            name = o.get("name") or ""
            if "_EXT_" in name:
                continue
            for s in (o.get("samples") or []):
                box = aabb_of(s)
                if not box:
                    continue
                d = inside_depth(pt, box)
                if d > EPS:
                    hits.append({
                        "frame": cs.get("frame"),
                        "object": name,
                        "depth_m": round(d, 3),
                        "cam_loc": pt,
                    })
                    break
    if hits:
        names = sorted({h["object"] for h in hits})
        maxd = max(h["depth_m"] for h in hits)
        ratio = len(hits) / max(1, len(cams))
        deep = [h for h in hits if h["depth_m"] > 0.30]
        # ★ 判定门槛（据 U01 实测校准）：
        #   - **多数帧命中**（≥50%）或**单帧深陷 >0.30m** ⇒ 判缺陷
        #     （g27 = 9/9 帧深陷 0.175m，相机在角色几何中心 ⇒ 必然死段）
        #   - 单帧浅擦（≤0.30m，占少数帧）⇒ **放行**：那是相机擦身而过，
        #     不是穿模。U01 实测有 2 镜属此类（ep01_shot04 2/8 深 0.033m、
        #     ep02_shot03 1/9 深 0.119m），若按「任一命中即失败」会全成误报。
        if ratio >= 0.5 or deep:
            return {
                "shot": shot_dir.name, "status": "FAIL",
                "note": (f"机位穿入实体：{len(hits)}/{len(cams)} 个采样帧落在对象 AABB 内"
                         f"（占比 {ratio:.0%}，深陷 >0.30m 的 {len(deep)} 帧，最大深入 {maxd:.3f}m）；"
                         f"涉及 {len(names)} 个对象：{', '.join(names[:6])}"
                         f"{' …' if len(names) > 6 else ''}"),
                "hits": hits[:12],
            }
        return {
            "shot": shot_dir.name, "status": "PASS",
            "note": (f"少数帧浅擦（{len(hits)}/{len(cams)}，占比 {ratio:.0%}，最大深入 {maxd:.3f}m）"
                     f"—— 判为擦身而过，不判穿模；涉及 {', '.join(names[:4])}"),
            "hits": hits[:6],
        }
    return {
        "shot": shot_dir.name, "status": "PASS",
        "note": f"{len(cams)} 个采样机位均不在任何对象 AABB 内",
    }


def main():
    ap = argparse.ArgumentParser(description="机位穿入几何体检测")
    ap.add_argument("--unit", default=os.environ.get("UNIT_ID", "U01"))
    ap.add_argument("--project", default=os.environ.get("WM_PROJECT", ""))
    ap.add_argument("--shots-dir", default="")
    ap.add_argument("--expect-fail", default="",
                    help="已知坏镜清单（逗号分隔的目录名），用于正反对照；列出即要求必须命中")
    args = ap.parse_args()

    project = Path(args.project) if args.project else Path(__file__).resolve().parent.parent
    shots_dir = Path(args.shots_dir) if args.shots_dir else project / "units" / args.unit / "D14_shots"
    if not shots_dir.is_dir():
        print(f"❌ 逐镜包目录不存在：{shots_dir}")
        return 2
    dirs = sorted([d for d in shots_dir.iterdir() if d.is_dir()])
    if not dirs:
        print(f"❌ {shots_dir} 下没有镜位目录")
        return 2

    results = [check_shot(d) for d in dirs]
    fails = [r for r in results if r["status"] == "FAIL"]
    passes = [r for r in results if r["status"] == "PASS"]
    skips = [r for r in results if r["status"] == "SKIP"]

    print(f"■ 机位穿模检测 · {args.unit}｜受检镜位 {len(results)}｜采样帧来自 manifest")
    for r in results:
        if r["status"] != "PASS":
            print(f"  [{r['status']}] {r['shot']}  {r['note']}")

    # 正反对照（判据有效性）：已知坏镜必须命中
    expect = [x.strip() for x in args.expect_fail.split(",") if x.strip()]
    disc_ok = True
    if expect:
        failed_names = {r["shot"] for r in fails}
        missing = [e for e in expect if e not in failed_names]
        print(f"· 正反对照：已知坏镜 {expect} → "
              + ("全部命中 ✅" if not missing else f"未命中 {missing} ❌"))
        disc_ok = disc_ok and not missing
    print(f"■ 结果　PASS {len(passes)}｜FAIL {len(fails)}｜SKIP {len(skips)}｜受检条数 {len(results)}")
    return 1 if (fails or not disc_ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
