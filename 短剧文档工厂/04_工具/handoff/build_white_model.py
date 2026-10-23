#!/usr/bin/env python3
"""D14 逐镜白模构建器（Blender 后台，无窗口）。

按 D13 场景说明书 + D11 镜头参数搭白模，导出 preview_video.mp4 与 manifest.json。

用法（必须在 Blender 内运行）：
    blender --background --factory-startup --python build_white_model.py -- \
        --shot-dir <dir> \
        --scene-json <scene_spec.json> \
        --shot-json <shot_spec.json> \
        --out <output.mp4> \
        --manifest <manifest.json>

scene_spec.json 形状（白模场景师按 D13 生成）：
{
  "scene_code": "A-1",
  "size_m": [8.0, 6.0, 2.8],          // X宽 Y深 Z高
  "floor_z": 0.0,
  "props": [
    {"name": "Bed", "kind": "box", "center_m": [-1.2, 0.4, 0.25],
     "size_m": [1.6, 2.0, 0.5], "role": "set"},
    {"name": "ActorA", "kind": "human_proxy", "center_m": [-0.8, 0.0, 0.0],
     "height_m": 1.75, "role": "primary"},
    {"name": "ActorB", "kind": "human_proxy", "center_m": [1.1, 0.3, 0.0],
     "height_m": 1.68, "role": "secondary"}
  ],
  "walls": ["-X", "+X", "+Y"],        // 需要围合的墙：-X/-X/+Y/+Y/-Y/+Y
  "wall_thickness_m": 0.15
}

shot_spec.json 形状（白模场景师按 D11 生成）：
{
  "ep": 1, "shot_id": 1, "global_shot_no": 1, "scene_code": "A-1",
  "duration_sec": 13.0,
  "fps": 24,
  "camera": {
    "location_m": [0.0, -5.2, 1.6],
    "rotation_euler_deg": [69.0, 0.0, 0.0],
    "lens_mm": 35,
    "move": "static"                   // static | dolly | pan | orbit | truck | push_in
  },
  "actors": [                          // 演员在镜头内的运动（可为 null）
    {"name": "ActorA", "motion": "static"},
    {"name": "ActorB", "motion": "static"}
  ]
}

输出：
  preview_video.mp4   白模渲染（Workbench 单色 + 影棚光）
  manifest.json       导出侧车（schema v3，含 structure_evidence）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

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
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--resolution", default="480P")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    parser.add_argument("--fps", type=int, default=24)
    return parser.parse_args(argv)


# ---------------------------------------------------------------- 分辨率


def apply_resolution(scene, resolution: str, aspect: str) -> tuple[int, int]:
    """设置输出画幅。

    本项目是**竖屏 9:16** 漫剧（D12 每张卡 aspect 均为 9:16，H3 也按 9:16 出），
    白模必须用同一画幅，否则视锥与取景全错——16:9 的水平/垂直视野与 9:16 互换了 90°，
    会出现"人物头顶出画"这类假缺陷。

    返回 (width, height)。
    """
    if aspect == "9:16":
        long_side = 1080 if resolution == "1080P" else 540
        width, height = long_side, int(round(long_side * 16 / 9))
    else:
        width, height = (1920, 1080) if resolution == "1080P" else (854, 480)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    return width, height


# ---------------------------------------------------------------- geometry


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_box(name, center, size, collection):
    """size 为 (x, y, z) 全尺寸。返回对象。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def make_plane(name, size, collection):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0], size[1], 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def make_cylinder(name, center, radius, height, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, location=center
    )
    obj = bpy.context.object
    obj.name = name
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def make_human_proxy(name, cx, cy, base_z, height, facing, pose, collection):
    """建一个人物白模代理。

    pose:
      standing —— 直立：躯干 + 腿 + 头
      seated  —— 坐在承载面上：躯干坐在面上、大腿前伸、小腿垂地
      kneeling —— 单膝跪：一腿膝触地、另一腿脚掌撑地、躯干直立

    facing: (fx, fy) 单位向量，角色面朝方向（一般面朝相机）。
    代理只是空间占位；成片由 H3 依据 D08/D11 生成真实人物。
    姿态必须与 D11 的 visual_facts 一致，否则注视点高度与取景全错。
    """
    width = 0.45
    depth = 0.30
    parts = []

    if pose == "seated":
        # 坐姿比例（以身高 h 为基准）：坐面即髋，肩在坐面上 0.29h，头顶 0.45h
        hip_z = base_z
        parts.append((f"{name}_Torso", (cx, cy, hip_z + height * 0.19),
                      (width, depth, height * 0.28)))
        parts.append((f"{name}_Head", (cx, cy, hip_z + height * 0.42),
                      ("cyl", height * 0.075, height * 0.16)))
        thigh_len = height * 0.22
        tx = cx + facing[0] * thigh_len * 0.5
        ty = cy + facing[1] * thigh_len * 0.5
        parts.append((f"{name}_Thigh", (tx, ty, hip_z + height * 0.07),
                      (width * 0.9, thigh_len, height * 0.14)))
        shin_h = max(hip_z, 0.05) + height * 0.07
        parts.append((f"{name}_Shin", (tx, ty, shin_h / 2.0),
                      (width * 0.75, height * 0.10, shin_h)))
    elif pose == "kneeling":
        hip_z = height * 0.40
        parts.append((f"{name}_Torso", (cx, cy, hip_z + height * 0.11),
                      (width, depth, height * 0.24)))
        parts.append((f"{name}_Head", (cx, cy, hip_z + height * 0.28),
                      ("cyl", height * 0.075, height * 0.16)))
        parts.append((f"{name}_Thigh", (cx, cy, hip_z * 0.5),
                      (width * 0.9, height * 0.10, hip_z)))
        shin_len = height * 0.24
        parts.append((f"{name}_Shin",
                      (cx - facing[0] * shin_len * 0.5,
                       cy - facing[1] * shin_len * 0.5, height * 0.06),
                      (width * 0.75, shin_len, height * 0.12)))
        fx = cx + facing[0] * height * 0.18
        fy = cy + facing[1] * height * 0.18
        parts.append((f"{name}_Legs", (fx, fy, hip_z * 0.5),
                      (width * 0.75, height * 0.09, hip_z)))
    else:
        parts.append((f"{name}_Torso", (cx, cy, base_z + height * 0.55),
                      (width, depth, height * 0.45)))
        parts.append((f"{name}_Legs", (cx, cy, base_z + height * 0.25),
                      (width * 0.8, depth * 0.85, height * 0.5)))
        parts.append((f"{name}_Head", (cx, cy, base_z + height * 0.88),
                      ("cyl", height * 0.075, height * 0.16)))

    objects = {}
    for part_name, centre, dims in parts:
        if dims[0] == "cyl":
            obj = make_cylinder(part_name, centre, radius=dims[1], height=dims[2],
                                collection=collection)
        else:
            obj = make_box(part_name, centre, dims, collection)
        objects[obj.name] = obj
    return objects


def _split_rect(rects, hole):
    """用矩形洞把若干矩形切成互不重叠的小矩形。"""
    hx0, hx1, hy0, hy1 = hole
    out = []
    for (x0, x1, y0, y1) in rects:
        ix0, ix1 = max(x0, hx0), min(x1, hx1)
        iy0, iy1 = max(y0, hy0), min(y1, hy1)
        if ix0 >= ix1 or iy0 >= iy1:
            out.append((x0, x1, y0, y1))
            continue
        if iy0 > y0:
            out.append((x0, x1, y0, iy0))
        if iy1 < y1:
            out.append((x0, x1, iy1, y1))
        if ix0 > x0:
            out.append((x0, ix0, iy0, iy1))
        if ix1 < x1:
            out.append((ix1, x1, iy0, iy1))
    return out


def build_floor(scene_spec, collection, objects):
    """建地面。若 scene_spec 有 floor_holes（深坑），地面必须开口，
    否则坑底机位（z<0）会被地面整块挡住，画面全黑。"""
    size_x, size_y, _z = scene_spec.get("size_m", [8.0, 6.0, 2.8])
    floor_z = float(scene_spec.get("floor_z", 0.0))
    gcx, gcy = scene_spec.get("ground_center_m", [0.0, 0.0])
    x0, x1 = gcx - size_x / 2, gcx + size_x / 2
    y0, y1 = gcy - size_y / 2, gcy + size_y / 2
    holes = scene_spec.get("floor_holes", []) or []

    rects = [(x0, x1, y0, y1)]
    for h in holes:
        hc = h["center_m"]
        hs = h["size_m"]
        hole = (hc[0] - hs[0] / 2, hc[0] + hs[0] / 2,
                hc[1] - hs[1] / 2, hc[1] + hs[1] / 2)
        rects = _split_rect(rects, hole)

    piece = 0
    for (rx0, rx1, ry0, ry1) in rects:
        if rx1 - rx0 < 1e-3 or ry1 - ry0 < 1e-3:
            continue
        name = "Floor" if piece == 0 else f"Floor_{piece}"
        obj = make_plane(name, (rx1 - rx0, ry1 - ry0), collection)
        obj.location = ((rx0 + rx1) / 2, (ry0 + ry1) / 2, floor_z)
        objects[obj.name] = obj
        piece += 1

    # 深坑：坑壁 + 坑底
    for idx, h in enumerate(holes, start=1):
        hc = h["center_m"]
        hs = h["size_m"]
        depth = float(h.get("depth_m", 0.0))
        if depth <= 0:
            continue
        cx, cy = float(hc[0]), float(hc[1])
        hx, hy = float(hs[0]) / 2, float(hs[1]) / 2
        t = 0.12
        walls = [
            (f"Pit_WallNegX", (cx - hx - t / 2, cy, floor_z - depth / 2),
             (t, hy * 2 + t * 2, depth)),
            (f"Pit_WallPosX", (cx + hx + t / 2, cy, floor_z - depth / 2),
             (t, hy * 2 + t * 2, depth)),
            (f"Pit_WallNegY", (cx, cy - hy - t / 2, floor_z - depth / 2),
             (hx * 2, t, depth)),
            (f"Pit_WallPosY", (cx, cy + hy + t / 2, floor_z - depth / 2),
             (hx * 2, t, depth)),
        ]
        for name, centre, dims in walls:
            obj = make_box(name, centre, dims, collection)
            objects[obj.name] = obj
        bottom = make_plane(f"Pit_Bottom{idx}", (hx * 2, hy * 2), collection)
        bottom.location = (cx, cy, floor_z - depth)
        objects[bottom.name] = bottom


def build_scene(scene_spec: dict):
    """按 scene_spec 搭出白模。返回 (collection, objects_by_name)。

    约定：道具的 center_m 是**底面中心**（Z=0 表示落在地面），
    与 D13 的 position_m 语义一致（D13 里所有道具 position_m 的 Z 均为 0）。
    几何体按底面中心落位，再按自身高度抬升，避免道具悬空或埋入地面。
    """
    scene = bpy.context.scene
    collection = bpy.data.collections.new("WhiteModel")
    scene.collection.children.link(collection)

    size_x, size_y, size_z = scene_spec.get("size_m", [8.0, 6.0, 2.8])
    floor_z = float(scene_spec.get("floor_z", 0.0))
    thickness = float(scene_spec.get("wall_thickness_m", 0.15))
    # 地面矩形中心：场景可能用绝对街区坐标（原点不在几何中心）
    gcx, gcy = scene_spec.get("ground_center_m", [0.0, 0.0])

    objects: dict[str, bpy.types.Object] = {}

    # 地面（带深坑开口）
    build_floor(scene_spec, collection, objects)

    # 墙（只建指定朝向）——墙心在 Z = floor + 层高/2
    wall_specs = {
        "-X": ((gcx - size_x / 2, gcy, floor_z + size_z / 2),
               (thickness, size_y, size_z), "WallNegX"),
        "+X": ((gcx + size_x / 2, gcy, floor_z + size_z / 2),
               (thickness, size_y, size_z), "WallPosX"),
        "-Y": ((gcx, gcy - size_y / 2, floor_z + size_z / 2),
               (size_x, thickness, size_z), "WallNegY"),
        "+Y": ((gcx, gcy + size_y / 2, floor_z + size_z / 2),
               (size_x, thickness, size_z), "WallPosY"),
    }
    for wall in scene_spec.get("walls", []) or []:
        if wall not in wall_specs:
            continue
        center, dims, obj_name = wall_specs[wall]
        obj = make_box(obj_name, center, dims, collection)
        objects[obj.name] = obj

    # 道具与人物代理
    for prop in scene_spec.get("props", []) or []:
        name = prop.get("name")
        kind = prop.get("kind", "box")
        pos = prop.get("center_m", [0.0, 0.0, 0.0])
        cx, cy = float(pos[0]), float(pos[1])
        role = prop.get("role", "set")
        if kind == "human_proxy":
            height = float(prop.get("height_m", 1.75))
            # center_m 的 Z 是**站立/坐落基准面**（0=地面，>0=床面/台面）
            base_z = floor_z + float(pos[2]) if len(pos) > 2 else floor_z
            facing = prop.get("facing_m", [0.0, -1.0])
            pose = prop.get("pose", "standing")
            objects.update(
                make_human_proxy(name, cx, cy, base_z, height, facing, pose, collection)
            )
        elif kind == "cylinder":
            height = float(prop.get("height_m", 1.0))
            obj = make_cylinder(
                name,
                (cx, cy, floor_z + height / 2),
                radius=float(prop.get("radius_m", 0.3)),
                height=height,
                collection=collection,
            )
            objects[obj.name] = obj
        else:
            dims = prop.get("size_m", [1.0, 1.0, 1.0])
            # center_m 已在 make_plan 阶段换算成**几何体心**（含底面/体心语义判读），
            # 这里直接按体心落位，不再擅自按半高抬升。
            obj = make_box(
                name,
                (cx, cy, floor_z + float(pos[2]) if len(pos) > 2 else floor_z),
                dims,
                collection,
            )
            objects[obj.name] = obj

    return collection, objects


# ---------------------------------------------------------------- camera


def build_camera(shot_spec: dict):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("ShotCam")
    cam = bpy.data.objects.new("ShotCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    cam_spec = shot_spec.get("camera", {})
    location = cam_spec.get("location_m", [0.0, -5.0, 1.6])
    cam.location = tuple(location)
    target = cam_spec.get("target_m")
    if target:
        # 用 look-at 直接求朝向：Blender 相机默认沿 -Z 看
        # （纯欧拉角公式的 rz 符号易错，这里用 Blender 自己的向量运算）
        direction = Vector(target) - Vector(location)
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    else:
        rotation = cam_spec.get("rotation_euler_deg", [69.0, 0.0, 0.0])
        cam.rotation_euler = tuple(math.radians(v) for v in rotation)
    cam_data.lens = float(cam_spec.get("lens_mm", 35))
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200.0

    return cam


def _pseudo(seed: float) -> float:
    """确定性伪随机 [-1, 1]。不用 random，保证同一 plan 重跑结果完全一致。"""
    v = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return (v - math.floor(v)) * 2.0 - 1.0


def _look_at(cam, loc, target):
    """把相机指向 target（Blender 相机沿 -Z 看）。"""
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _derive_end(base, target, move, amount):
    """按运镜类型推导终点机位与终点注视点。

    - dolly/push_in/tracking：沿视线轴**朝注视点**推进（不是朝原点缩放，
      绝对坐标场景下朝原点缩放会把机位甩到场景另一侧）
    - pull_out：沿视线轴后退
    - truck：垂直于视线轴横向平移，注视点不动（主体在画面里横移）
    - pan / pan_tilt：机位不动，注视点绕机位旋转
    - orbit：机位绕注视点公转
    - crane / crane_up / crane_down：垂直升降
    """
    base_v = Vector(base)
    tgt_v = Vector(target) if target else base_v + Vector((0.0, -1.0, 0.0))
    axis = tgt_v - base_v
    if axis.length < 1e-6:
        axis = Vector((0.0, -1.0, 0.0))
    axis.normalize()

    if move in ("dolly", "push_in", "tracking"):
        return base_v + axis * amount, tgt_v
    if move == "pull_out":
        return base_v - axis * amount, tgt_v
    if move == "truck":
        lateral = Vector((axis.y, -axis.x, 0.0))
        if lateral.length < 1e-6:
            lateral = Vector((1.0, 0.0, 0.0))
        lateral.normalize()
        return base_v + lateral * amount, tgt_v
    if move in ("pan", "pan_tilt"):
        # 注视点绕机位水平旋转 amount 度
        rel = tgt_v - base_v
        a = math.radians(amount)
        cos_a, sin_a = math.cos(a), math.sin(a)
        rel = Vector((rel.x * cos_a + rel.y * sin_a,
                      -rel.x * sin_a + rel.y * cos_a,
                      rel.z))
        return base_v, base_v + rel
    if move == "orbit":
        rel = base_v - tgt_v
        a = math.radians(amount)
        cos_a, sin_a = math.cos(a), math.sin(a)
        rel = Vector((rel.x * cos_a - rel.y * sin_a,
                      rel.x * sin_a + rel.y * cos_a,
                      rel.z))
        return tgt_v + rel, tgt_v
    if move in ("crane", "crane_up"):
        return base_v + Vector((0.0, 0.0, amount)), tgt_v
    if move == "crane_down":
        return base_v + Vector((0.0, 0.0, -amount)), tgt_v
    return base_v, tgt_v


def animate_camera(cam, shot_spec: dict, frame_start: int, frame_end: int) -> None:
    """按 D11 的 movement 字段给相机做关键帧。

    两种输入：
      ① 显式路径：shot_spec.camera.end_location_m / end_target_m（D13 的机位说明
         逐镜写死了起止机位时用这个，路径以 D13 为准）
      ② 运镜类型：move ∈ static/dolly/push_in/pull_out/truck/pan/pan_tilt/orbit/
         tracking/crane/crane_up/crane_down/handheld/compound，按类型推导位移。

    关键帧同时写 location 与 rotation_euler：每帧都朝当前注视点重新瞄准，
    否则跟拍/环绕会被拍成"主体自己动了"，那是结构失败。
    """
    cam_spec = shot_spec.get("camera", {}) or {}
    move = (cam_spec.get("move", "static") or "static").strip()
    end_loc_spec = cam_spec.get("end_location_m")
    end_tgt_spec = cam_spec.get("end_target_m")
    if move == "static" and not end_loc_spec:
        return

    base = tuple(cam.location)
    target = cam_spec.get("target_m")
    amount = float(cam_spec.get("move_amount_m", 1.2))

    if end_loc_spec:
        end_loc = Vector(tuple(end_loc_spec))
    else:
        end_loc, _ = _derive_end(base, target, move, amount)
    if end_tgt_spec:
        end_target = Vector(tuple(end_tgt_spec))
    elif target:
        end_target = Vector(tuple(target))
    else:
        end_target = Vector(base) + Vector((0.0, -1.0, 0.0))

    start_target = Vector(tuple(target)) if target else end_target

    def key(frame, loc, tgt):
        cam.location = tuple(loc)
        _look_at(cam, loc, tgt)
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 手持：机位基本不动，但有确定性的轻微抖动与竖向起伏
    if move == "handheld":
        amp = float(cam_spec.get("shake_amp_m", 0.035))
        bob = float(cam_spec.get("shake_bob_m", 0.055))
        span = max(1, frame_end - frame_start)
        step = max(1, span // 6)
        for frame in range(frame_start, frame_end + 1, step):
            t = (frame - frame_start) / span
            loc = Vector(base) + Vector((
                _pseudo(frame * 3.1) * amp,
                _pseudo(frame * 5.7) * amp,
                _pseudo(frame * 7.3) * bob,
            ))
            tgt = start_target.lerp(end_target, t)
            key(frame, loc, tgt)
        key(frame_end, Vector(base), end_target)
    else:
        key(frame_start, Vector(base), start_target)
        key(frame_end, end_loc, end_target)

    _set_bezier_interpolation(cam)


def _iter_fcurves(action) -> list:
    """Blender 4.4+ 的 Action 是分层结构，fcurves 可能在 layer/strip/channelbag 里。"""
    if action is None:
        return []
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        try:
            return list(fcurves)
        except Exception:
            pass
    collected = []
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for channelbag in getattr(strip, "channelbags", []) or []:
                collected.extend(list(getattr(channelbag, "fcurves", []) or []))
    return collected


def _set_bezier_interpolation(obj) -> None:
    anim = getattr(obj, "animation_data", None)
    if anim is None or anim.action is None:
        return
    for fc in _iter_fcurves(anim.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"


# ---------------------------------------------------------------- manifest


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(scene, objects, shot_spec, out_path, video_path, resolution):
    """产出 manifest v3（含 structure_evidence）。"""
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    fps = int(scene.render.fps)
    duration = (frame_end - frame_start + 1) / fps

    # 结构证据：每个可渲染对象的屏幕包围盒采样。
    # 采样要覆盖整条片子（不只首/中/尾三帧），否则中途入画的物件会漏登记；
    # 判据是**投影与画幅相交**，不是"相机前方有角点"——
    # 后者会把完全在画外的墙/道具也登记成可见，污染 H3 合同的一对一守恒清单。
    total_frames = frame_end - frame_start + 1
    stride = max(1, total_frames // 24)
    sample_frames = sorted(
        set(range(frame_start, frame_end + 1, stride))
        | {frame_start, (frame_start + frame_end) // 2, frame_end}
    )
    camera = scene.camera
    bpy.context.view_layer.update()

    from bpy_extras.object_utils import world_to_camera_view

    objects_evidence = []
    for name in sorted(objects.keys()):
        obj = objects[name]
        samples = []
        ever_visible = False
        for frame in sample_frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
            xs, ys = [], []
            for corner in corners:
                co = world_to_camera_view(scene, camera, corner)
                if co.z <= 0:
                    continue
                xs.append(co.x * 100.0)
                ys.append((1.0 - co.y) * 100.0)
            if not xs:
                samples.append({
                    "frame": frame,
                    "projected_visible": False,
                    "screen_bbox_percent": None,
                })
                continue
            in_frame = (max(xs) > 0.0 and min(xs) < 100.0
                        and max(ys) > 0.0 and min(ys) < 100.0)
            if in_frame:
                ever_visible = True
            samples.append({
                "frame": frame,
                "projected_visible": bool(in_frame),
                "screen_bbox_percent": {
                    "center_x": round((min(xs) + max(xs)) / 2.0, 3),
                    "center_y": round((min(ys) + max(ys)) / 2.0, 3),
                    "width": round(max(xs) - min(xs), 3),
                    "height": round(max(ys) - min(ys), 3),
                },
            })
        # 根节点名：同一角色的躯干/腿/头归到同一个 root，便于语义分组
        root_name = name.split("_")[0] if "_" in name else name
        if name.startswith("Wall") or name in ("Floor",):
            root_name = name
        world_dims = [round(v, 4) for v in obj.dimensions]
        objects_evidence.append({
            "source_id": f"{shot_spec['global_shot_no']:04d}_{name}",
            "name": name,
            "object_type": obj.type,
            "root_name": root_name,
            "ever_projected_visible": ever_visible,
            "world_dimensions": world_dims,
            "samples": samples,
        })

    camera_samples = []
    for frame in sample_frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        camera_samples.append({
            "frame": frame,
            "location_m": [round(v, 4) for v in camera.matrix_world.translation],
            "rotation_euler_deg": [
                round(math.degrees(v), 4) for v in camera.rotation_euler
            ],
            "lens_mm": round(camera.data.lens, 3),
            "shift_x": round(camera.data.shift_x, 5),
            "shift_y": round(camera.data.shift_y, 5),
        })

    size_bytes = os.path.getsize(video_path)
    manifest = {
        "addon_version": "1.0.7",
        "blender_version": bpy.app.version_string,
        "os_name": os.name,
        "arch": bpy.app.build_platform.decode() if isinstance(
            bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        "scene_name": f"{shot_spec.get('scene_code', 'SC')}_G{shot_spec['global_shot_no']:04d}",
        "camera_name": camera.name,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "fps": fps,
        "resolution": resolution,
        "export_mode": "white_model",
        "duration_seconds": round(duration, 4),
        "intent": (
            f"U01 ep{shot_spec.get('ep')} shot{shot_spec.get('shot_id')} "
            f"scene {shot_spec.get('scene_code')} white model blockout"
        ),
        "files": [
            {
                "role": "preview_video",
                "name": os.path.basename(video_path),
                "size_bytes": size_bytes,
                "sha256": sha256_of(video_path),
                "mime": "video/mp4",
            }
        ],
        "schema_version": 3,
        "structure_evidence": {
            "schema_version": 1,
            "sample_frames": sample_frames,
            "camera_samples": camera_samples,
            "objects": objects_evidence,
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


# ---------------------------------------------------------------- main


def main() -> None:
    args = parse_args()
    with open(args.scene_json, encoding="utf-8") as fh:
        scene_spec = json.load(fh)
    with open(args.shot_json, encoding="utf-8") as fh:
        shot_spec = json.load(fh)

    os.makedirs(args.shot_dir, exist_ok=True)

    clear_scene()
    scene = bpy.context.scene
    fps = int(shot_spec.get("fps", args.fps))
    duration = float(shot_spec.get("duration_sec", 10.0))
    frame_start = 1
    frame_end = max(frame_start + 1, int(round(duration * fps)))

    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.fps = fps
    width, height = apply_resolution(scene, args.resolution, args.aspect)

    collection, objects = build_scene(scene_spec)
    camera = build_camera(shot_spec)
    animate_camera(camera, shot_spec, frame_start, frame_end)

    from bl_ext.user_default.minimax_h3.services import preview_exporter

    video_path = preview_exporter.export_preview(
        scene=scene,
        camera=camera,
        frame_start=frame_start,
        frame_end=frame_end,
        fps=fps,
        resolution="original",
        export_mode="white_model",
        output_path=args.out,
    )

    manifest = build_manifest(
        scene, objects, shot_spec, args.manifest, video_path,
        f"{width}x{height}",
    )
    print(
        "WHITEMODEL_OK",
        json.dumps({
            "video": video_path,
            "manifest": args.manifest,
            "frames": [frame_start, frame_end],
            "fps": fps,
            "duration_sec": manifest["duration_seconds"],
            "source_ids": [o["source_id"] for o in manifest["structure_evidence"]["objects"]],
        }, ensure_ascii=False),
    )


if __name__ == "__main__":
    main()
