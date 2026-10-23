#!/usr/bin/env python3
"""D14 逐镜投影真值导出器（Blender 后台，无窗口）。

重建 build_white_model.py 的同一场景，在**每个锚点帧**上计算每个物体的
真实屏幕空间量，写入 projection.json：

    visible_percent : {center_x, center_y, width, height}   画幅内可见范围（已按 0-100 截断）
    raw_percent     : 未截断的投影延展（几何真值，可超 100）
    depth_m         : 相机到物体最近可见点的距离
    occlusion_ratio : 画面采样点中被其它物体挡住的占比
    screen_axis_deg : 物体长轴在屏幕上的角度（度，0=水平向右，Y 向下为正）
    occluders       : 遮挡者名字 + 遮挡占比

用法（必须在 Blender 内运行）：
    blender --background --factory-startup --python project_bounds.py -- \
        --shot-dir <dir> \
        --scene-json <dir>/scene_spec.json \
        --shot-json <dir>/shot_spec.json \
        --anchor-times "0.0,1.62,3.24" \
        --out <dir>/projection.json

为什么必须有这一步：
    preflight 自动填的 screen_bbox_percent 是**投影总延展**（地面可以横跨 18 个画幅，
    出现 center_x=-876 / width=1870 这类值），而 check-contract 要求 0-100。
    二者不是"错与对"，而是两种表达：总延展 vs 画幅内可见范围。
    本脚本同时给出两者，由填装器按"画幅内可见范围"口径写合同。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_white_model as bwm  # noqa: E402  (必须复用同一套建场逻辑)


# ---------------------------------------------------------------- argparse


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot-dir", required=True)
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--shot-json", required=True)
    parser.add_argument("--anchor-times", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    parser.add_argument("--resolution", default="480P")
    parser.add_argument("--grid", type=int, default=5)
    return parser.parse_args(argv)


# ---------------------------------------------------------------- 投影工具


def _frustum_map(camera, scene):
    """返回 (u, v) -> 相机世界方向向量 的映射。

    u=0 画面最左，u=1 最右；v=0 画面最下，v=1 最上。
    用 view_frame 拿到相机局部视框四角，因此自动兼容 sensor_fit / shift。

    注意：basis @ local 是**世界方向**（相机前方），不能减 origin——
    origin 是世界点，方向减点会得到错误的射线方向。
    """
    corners = camera.data.view_frame(scene=scene)
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    z = sum(zs) / len(zs)
    basis = camera.matrix_world.to_3x3()
    x_axis = basis @ Vector((1.0, 0.0, 0.0))
    y_axis = basis @ Vector((0.0, 1.0, 0.0))
    z_axis = basis @ Vector((0.0, 0.0, 1.0))

    def pixel_dir(u: float, v: float) -> Vector:
        local = x_axis * (x0 + u * (x1 - x0)) + y_axis * (y0 + v * (y1 - y0)) + z_axis * z
        return local.normalized()

    return pixel_dir


def _project(scene, camera, point: Vector):
    """世界点 -> 归一化画面坐标 (u, v, depth)。depth<=0 表示在相机背后。"""
    from bpy_extras.object_utils import world_to_camera_view

    co = world_to_camera_view(scene, camera, point)
    return co.x, co.y, co.z


def _clamp_extent(us, vs):
    """把投影范围裁到画幅内。返回 (cx, cy, w, h) 或 None（完全在画幅外）。"""
    if not us or not vs:
        return None
    x0, x1 = min(us), max(us)
    y0, y1 = min(vs), max(vs)
    ix0, ix1 = max(x0, 0.0), min(x1, 1.0)
    iy0, iy1 = max(y0, 0.0), min(y1, 1.0)
    if ix1 - ix0 <= 1e-6 or iy1 - iy0 <= 1e-6:
        return None
    return (
        (ix0 + ix1) / 2.0 * 100.0,
        (iy0 + iy1) / 2.0 * 100.0,
        (ix1 - ix0) * 100.0,
        (iy1 - iy0) * 100.0,
    )


def _longest_axis(obj):
    """物体最长本地轴（用于算屏幕上的朝向）。"""
    dims = obj.dimensions
    axes = [Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))]
    idx = max(range(3), key=lambda i: dims[i])
    return axes[idx], float(dims[idx])


# ---------------------------------------------------------------- 主计算


def analyse_frame(scene, camera, objects, frame: int, grid: int):
    """在指定帧上计算所有物体的屏幕空间真值。"""
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pixel_dir = _frustum_map(camera, scene)
    origin = camera.matrix_world.translation

    raw = {}
    for name, obj in objects.items():
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        us, vs, depths, dists = [], [], [], []
        for corner in corners:
            u, v, d = _project(scene, camera, corner)
            if d <= 0:
                continue
            us.append(u)
            vs.append(v)
            depths.append(d)
            dists.append((corner - origin).length)
        if not us:
            raw[name] = None
            continue
        centre = obj.matrix_world.translation
        cu, cv, cd = _project(scene, camera, centre)
        raw[name] = {
            "us": us,
            "vs": vs,
            "depths": depths,
            "dists": dists,
            "centre": (cu, cv, cd),
        }

    results = {}
    for name, obj in objects.items():
        info = raw[name]
        if info is None:
            results[name] = {"in_frame": False}
            continue

        clamped = _clamp_extent(info["us"], info["vs"])
        if clamped is None:
            results[name] = {
                "in_frame": False,
                "raw_percent": {
                    "center_x": (min(info["us"]) + max(info["us"])) / 2.0 * 100.0,
                    "center_y": 100.0 - (min(info["vs"]) + max(info["vs"])) / 2.0 * 100.0,
                    "width": (max(info["us"]) - min(info["us"])) * 100.0,
                    "height": (max(info["vs"]) - min(info["vs"])) * 100.0,
                },
            }
            continue

        cx, cy, w, h = clamped
        # 深度：相机到该物体最近可见角点的欧氏距离（并列取中位更稳）
        ordered = sorted(info["dists"])
        depth_m = ordered[len(ordered) // 2]

        # 遮挡：只在**该物体自身的画幅内范围**上采样，避免用整幅画面误判
        occluders = {}
        samples = 0
        hit_self = 0
        misses = 0
        u_lo, u_hi = cx / 100.0 - w / 200.0, cx / 100.0 + w / 200.0
        v_lo, v_hi = cy / 100.0 - h / 200.0, cy / 100.0 + h / 200.0
        for i in range(grid):
            for j in range(grid):
                u = u_lo + (i + 0.5) / grid * (u_hi - u_lo)
                v = v_lo + (j + 0.5) / grid * (v_hi - v_lo)
                samples += 1
                direction = pixel_dir(u, v)
                hit, _loc, _nrm, _idx, hit_obj, _mat = scene.ray_cast(
                    depsgraph, origin, direction
                )
                if not hit or hit_obj is None:
                    misses += 1
                    continue
                if hit_obj.name == name:
                    hit_self += 1
                    continue
                occluders[hit_obj.name] = occluders.get(hit_obj.name, 0) + 1

        blocked = sum(occluders.values())
        # 打空（射线没碰到任何物体）＝ 背景，不算被遮挡
        occluded_ratio = blocked / samples if samples else 0.0
        visible_ratio = hit_self / samples if samples else 0.0

        # 屏幕长轴角度：把物体长轴投影到相机像平面（不依赖角点是否可见）
        axis, axis_len = _longest_axis(obj)
        axis_world = (obj.matrix_world.to_3x3() @ axis).normalized()
        cam_basis = camera.matrix_world.to_3x3()
        cam_right = cam_basis @ Vector((1.0, 0.0, 0.0))
        cam_up = cam_basis @ Vector((0.0, 1.0, 0.0))
        dx = axis_world.dot(cam_right)
        dy = axis_world.dot(cam_up)
        angle = math.degrees(math.atan2(-dy, dx))

        results[name] = {
            "in_frame": True,
            # 对外口径与 preflight/manifest 一致：**自上而下**（y=0 是画面顶边）
            "visible_percent": {
                "center_x": round(cx, 3),
                "center_y": round(100.0 - cy, 3),
                "width": round(w, 3),
                "height": round(h, 3),
            },
            "raw_percent": {
                "center_x": round((min(info["us"]) + max(info["us"])) / 2.0 * 100.0, 3),
                "center_y": round(
                    100.0 - (min(info["vs"]) + max(info["vs"])) / 2.0 * 100.0, 3
                ),
                "width": round((max(info["us"]) - min(info["us"])) * 100.0, 3),
                "height": round((max(info["vs"]) - min(info["vs"])) * 100.0, 3),
            },
            "depth_m": round(float(depth_m), 4),
            "centre_depth_m": round(float(info["centre"][2]), 4),
            "occlusion_ratio": round(occluded_ratio, 4),
            "visible_ratio": round(visible_ratio, 4),
            "background_ratio": round(misses / samples if samples else 0.0, 4),
            "occluders": {k: round(v / samples, 4) for k, v in sorted(occluders.items())},
            "screen_axis_deg": round(angle, 2) if angle is not None else None,
            "world_dimensions": [round(float(v), 4) for v in obj.dimensions],
        }

    return results


def main() -> None:
    args = parse_args()
    with open(args.scene_json, encoding="utf-8") as fh:
        scene_spec = json.load(fh)
    with open(args.shot_json, encoding="utf-8") as fh:
        shot_spec = json.load(fh)
    anchor_times = [
        float(v) for v in args.anchor_times.split(",") if v.strip()
    ]

    bwm.clear_scene()
    scene = bpy.context.scene
    fps = int(shot_spec.get("fps", 24))
    duration = float(shot_spec.get("duration_sec", 10.0))
    frame_start = 1
    frame_end = max(frame_start + 1, int(round(duration * fps)))
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.fps = fps
    # 画幅必须与 build_white_model.py 完全一致，否则视锥算错、投影全偏
    width, height = bwm.apply_resolution(scene, args.resolution, args.aspect)

    _collection, objects = bwm.build_scene(scene_spec)
    camera = bwm.build_camera(shot_spec)
    bwm.animate_camera(camera, shot_spec, frame_start, frame_end)

    frames = []
    for t in anchor_times:
        frame = frame_start + int(round(t * fps))
        frame = max(frame_start, min(frame_end, frame))
        frames.append({"time_seconds": t, "frame": frame})

    payload = {
        "shot_dir": os.path.abspath(args.shot_dir),
        "global_shot_no": shot_spec.get("global_shot_no"),
        "ep": shot_spec.get("ep"),
        "shot_id": shot_spec.get("shot_id"),
        "scene_code": shot_spec.get("scene_code"),
        "fps": fps,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "resolution_px": [width, height],
        "aspect": args.aspect,
        "camera": {
            "lens_mm": float(shot_spec.get("camera", {}).get("lens_mm", 35)),
            "move": shot_spec.get("camera", {}).get("move", "static"),
            "location_m": shot_spec.get("camera", {}).get("location_m"),
            "target_m": shot_spec.get("camera", {}).get("target_m"),
            "rotation_euler_deg": shot_spec.get("camera", {}).get("rotation_euler_deg"),
        },
        "frames": [],
    }

    for entry in frames:
        frame = entry["frame"]
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        cam_state = {
            "location_m": [round(float(v), 4) for v in camera.matrix_world.translation],
            "rotation_euler_deg": [
                round(math.degrees(float(v)), 4) for v in camera.rotation_euler
            ],
            "lens_mm": round(float(camera.data.lens), 3),
        }
        objects_data = analyse_frame(scene, camera, objects, frame, args.grid)
        payload["frames"].append(
            {
                "time_seconds": entry["time_seconds"],
                "frame": frame,
                "camera": cam_state,
                "objects": objects_data,
            }
        )

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print("PROJECTION_OK", json.dumps({"out": args.out, "frames": len(payload["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
