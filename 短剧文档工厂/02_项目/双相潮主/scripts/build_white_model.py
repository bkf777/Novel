#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_white_model.py —— 《双相潮主》单元白模构建器（**单元无关逻辑**，Blender --background 运行）

在 Blender 内运行：按 D13.json 的空间规格为 32 个镜头各建一个独立 scene，
用代理几何体搭出该镜可见的道具/角色/空间壳体，按 D13 的机位坐标与 D11 的运镜
设置相机动画，逐镜导出 preview_video.mp4（white_model 模式）与 manifest.json
（schema v3，含 structure_evidence）。

用法：
  blender --background --factory-startup --python build_white_model.py -- \
      --project <项目目录> --out <输出根目录>

硬纪律：
  * 只用 --background，无窗口、不启动 GUI
  * 每个镜头一个 scene —— structure_evidence 只采该镜 scene 的对象，
    保证 source_inventory 与该镜可见实例一一对应
  * 代理体只做体量与占位（灰盒），不做任何成品材质与细节
  * 空间壳体（墙/地/顶/铺装）不在 D13 props 内，但必须建出来，
    否则镜头里只剩黑场浮盒，H3 合同无法描述空间关系
  * 坑洞/裂缝/沟槽在地面上真实开孔，角色与道具不会被盖板吞掉
  * 同一逻辑结构的多个体块合并为一个对象（join），避免可见实例膨胀
  * 重复实例（队列/车列/路灯）parent 到同一 Empty，
    使其 root_name 归并为一个 entity，实例数守恒且不撑爆 H3 提示词预算
"""

import bpy
import hashlib
import json
import math
import os
import sys

# 同目录模块（wm_framing 等）可被 import（Blender 的 sys.path 不含脚本目录）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ------------------------------------------------------------------ 参数

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def _arg(name, default=""):
    """取 --name value 形式的后续值（Blender 把参数放在 -- 之后）。"""
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            return argv[i + 1]
    return default


PROJECT = _arg("--project")
OUT_ROOT = _arg("--out")
UNIT_ID = _arg("--unit", os.environ.get("UNIT_ID", "U01"))
CONTENT_NAME = _arg("--content", os.environ.get("WM_CONTENT", "")) or f"white_model_content_{UNIT_ID}"

UNIT = os.path.join(PROJECT, "units", UNIT_ID)
D13 = json.load(open(os.path.join(UNIT, "D13.json"), encoding="utf-8"))
D11 = json.load(open(os.path.join(UNIT, "D11.json"), encoding="utf-8"))

FPS = 24
RES_X, RES_Y = 1080, 1920        # 9:16 竖屏（D10 竖屏标准，H3 参考源分辨率）
LENS_SENSOR = 36.0

# D11 真源索引
SHOT = {}
for _ep in D11["episodes"]:
    for _s in _ep["shots"]:
        SHOT[_s["global_shot_no"]] = {
            "ep": _ep["ep"], "shot_id": _s["shot_id"], "scene_code": _s["scene_code"],
            "duration_sec": _s["duration_sec"], "lens_mm": _s["lens_mm"],
            "movement": _s["movement"], "visual_facts": _s["visual_facts"],
            # ★ 相机角度（主观视角 / 过肩 / 俯视 …）—— clear_keys_from_camera 的
            #   避让策略要按角度分档（U02-R07 判定一），故必须进索引。
            "camera_angle": _s.get("camera_angle", ""),
            "shot_size": _s.get("shot_size", ""),
        }

# D13 场景索引
SCENES = {s["scene_code"]: s for s in D13["scenes"]}

# ---- 内容模块加载（几何表/位置表/角色表/机位动画表等全在内容层）----
import importlib.util as _ilu

_CPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONTENT_NAME + ".py")
if not os.path.exists(_CPATH):
    raise SystemExit(f"内容模块不存在：{_CPATH}")
_spec = _ilu.spec_from_file_location(CONTENT_NAME, _CPATH)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
for _k in dir(_mod):
    if _k.isupper():
        globals()[_k] = getattr(_mod, _k)
PROPS = {}
for s in D13["scenes"]:
    PROPS[s["scene_code"]] = s["props"]
CAMS = {}
for s in D13["scenes"]:
    CAMS[s["scene_code"]] = s["camera_positions"]

# name: (dx, dy, dz, shape, count, zmode, extra)
#   shape : box / cyl
#   zmode : 'base'（position_m.z 为底面）| 'center'（position_m.z 为中心）
#           | 'top'（position_m.z 为顶面）
#   extra : {'spread': 'x'|'y'|'z'|'x_center'|'y_center'|'queue'|'explicit', ...}

# 同名不同型的专属覆盖


# 内容模块可选提供 SHELL_OVERRIDE：{(scene_code, gsn): {"groups": {...}}}，
# 按镜覆盖空间壳体。用途：同一场内并存**两套独立坐标基线**时（如 U02 的 B-8 一场之内
# 既有骨市黑市基线、又有厂房区基线，两者原点重合、共用一块壳体会互相打架），
# 必须逐镜换壳。内容模块未声明时保持空表 ⇒ U01 行为逐字不变。
SHELL_OVERRIDE = {}


# 逐镜道具位置覆盖（白模布景层）
# 随身物与悬浮界面在同一场内随剧情换位，D13 只登记了单一场次坐标，
# 无法同时满足多个镜头的入画要求；此处按 (场景, 镜号, 道具名) 覆盖实际落位。
# 取值依据：D13 该镜 camera_positions 的视线方向与 sightline 的前景描述。

# 逐镜角色位置覆盖（白模布景层）
# 过肩镜里角色须在镜头侧后方、只让肩线入画；眼位主观镜由
# clear_keys_from_camera 统一把角色推到镜头之后。

# 同一逻辑结构由多个体块组成 → 合并为一个对象（join），
# 既保留真实体量关系，又不把可见实例数撑爆。
# key: (scene_code, name) 或 name
# parts: (shape, size, loc, rot_z)  —— 世界绝对坐标
# cuts : (shape, size, loc, rot_z)  —— 在合并结果上做布尔差集

# 地面开孔：在地面体块上做布尔差集

# 房间/厂房的墙、地、顶与场地铺装不在 D13 的 props（props 只登记画面成物），
# 但必须存在于白模，否则镜头里只剩黑场浮盒、H3 合同无法描述空间。
# 全部尺寸取自 D13 各场景 plan 与 scale_limits。




# ------------------------------------------------------------------ 工具函数


def geom_for(scene_code, name):
    return GEOM_OVERRIDE.get((scene_code, name)) or GEOM.get(name)


def multi_for(scene_code, name):
    return MULTI.get((scene_code, name)) or MULTI.get(name)


def cuts_for(scene_code, name):
    return CUTS.get((scene_code, name)) or []


def classify(t):
    """D13 道具 type → 白模对象类别（决定对象名前缀：CHAR/PROP/LGT/FX/EXT）。

    ★ 「人群/剪影」必须归 CHAR：
      D13 里「队列成员 / 岗哨成员 / 排队者 / 厂门队列 / 秩序队」等 **11 个
      人群道具的 type 是 `人群/剪影`**（U01 用的是 `人物占位`，U02 换了说法）。
      旧表不认识 `人群/剪影` ⇒ 全落到 PROP ⇒ 对象名里没有 `CHAR` ⇒
      V12 的 `wmKindOf`（按对象名判定主体）不认这些人是主体 ⇒
      U02 实测 13 镜 W1「角色完全不在画幅内」+ W3「画面最大对象是 PROP」。
      这些人按 D11 是在场的（只给远景剪影/不拍面部，不是「画面无人」），
      白模必须建成 CHAR 代理体，主体优先构图判据才有意义。
    """
    if t.startswith("建筑") or t in ("地面", "道路", "建筑面", "围护", "门洞", "建筑体", "工业构筑", "空间"):
        return "EXT"
    if t.startswith("人物") or "人群" in t or t in ("人物占位", "服装占位", "头发占位"):
        return "CHAR"
    if t.startswith("灯具") or t.startswith("显示") or t == "悬浮界面":
        return "LGT"
    if t.startswith("生物") or t in ("发光体", "能量体", "粒子表现", "体表标记", "体表色块", "碎块", "地面碎块"):
        return "FX"
    return "PROP"


def raw_box(shape, size, loc, rot_z=0.0):
    """创建一个未 link 的网格对象（世界坐标）。"""
    if shape == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=size[0] / 2.0, depth=size[2], location=loc)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        ob = bpy.context.object
        ob.scale = (size[0], size[1], size[2])
    ob = bpy.context.object
    if abs(rot_z) > 1e-9:
        if shape == "cyl":
            ob.rotation_euler = (math.pi / 2.0, 0.0, rot_z)
        else:
            ob.rotation_euler = (0.0, 0.0, rot_z)
    return ob


def link_to(ob, coll, name):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    ob.name = name
    return ob


def join_objects(objs, coll, name):
    """把多个体块合并为一个对象（join），保持世界坐标。"""
    if len(objs) == 1:
        return link_to(objs[0], coll, name)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    return link_to(joined, coll, name)


def raw_box_baked(shape, size, loc, rot_z=0.0):
    """建体块并把尺寸/位移/旋转全部烘进**网格数据**（对象变换保持单位）。

    与 raw_box 的世界效果逐位等价，但对象 scale/rotation 恒为单位 ——
    布尔运算（EXACT 求解器）对非均匀缩放不稳定，烘进网格后才可靠。
    """
    from mathutils import Matrix, Vector
    if shape == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=size[0] / 2.0, depth=size[2])
        ob = bpy.context.object
        ob.scale = (1.0, 1.0, 1.0)
        ob.data.transform(Matrix.Rotation(math.pi / 2.0, 4, "X"))   # 与 raw_box 同：躺倒
        if abs(rot_z) > 1e-9:
            ob.data.transform(Matrix.Rotation(rot_z, 4, "Z"))
    else:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ob = bpy.context.object
        ob.scale = (1.0, 1.0, 1.0)
        ob.data.transform(Matrix.Diagonal(Vector(size)).to_4x4())
        if abs(rot_z) > 1e-9:
            ob.data.transform(Matrix.Rotation(rot_z, 4, "Z"))
    ob.data.transform(Matrix.Translation(Vector(loc)))
    return ob


def _world_bbox(ob):
    """对象的世界包围盒 (lo, hi)。"""
    from mathutils import Vector
    mw = ob.matrix_world
    cs = [mw @ Vector(c) for c in ob.bound_box]
    return ([min(c[i] for c in cs) for i in range(3)],
            [max(c[i] for c in cs) for i in range(3)])


def _bbox_overlap(a, b, eps=1e-6):
    alo, ahi = a
    blo, bhi = b
    return all(alo[i] < bhi[i] - eps and blo[i] < ahi[i] - eps for i in range(3))


def apply_cuts(target, cutters):
    """在目标体块上做布尔差集（开孔 / 开槽）。

    ★ Q94：壳体构件逐个独立成对象后，布尔切割也逐构件执行：
      · 只对**包围盒相交**的构件下刀 —— 否则 EXACT 求解器在无交集时可能清空网格
      · 切割体与构件都把缩放烘进网格数据（布尔对非均匀缩放不稳定）
    """
    if not cutters:
        return
    cutter_objs = [raw_box_baked(shape, size, loc, rot_z) for shape, size, loc, rot_z in cutters]
    tb = _world_bbox(target)
    for cutter in cutter_objs:
        if not _bbox_overlap(tb, _world_bbox(cutter)):
            continue
        modifier = target.modifiers.new(name="cut", type="BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.object = cutter
        modifier.solver = "EXACT"
    if target.modifiers:
        bpy.ops.object.select_all(action="DESELECT")
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        for modifier in list(target.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
    for cutter in cutter_objs:
        bpy.data.objects.remove(cutter, do_unlink=True)


def make_empty(name, coll):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_size = 0.3
    empty.location = (0.0, 0.0, 0.0)
    coll.objects.link(empty)
    return empty


def prop_objects(coll, scene_code, prop, seq, gsn=None):
    """按 D13 道具规格铺出实体，返回生成的 object 列表。"""
    multi = multi_for(scene_code, prop["name"])
    g = geom_for(scene_code, prop["name"])
    if multi is None and g is None:
        return []
    pos = list(prop["position_m"])
    override = PROP_POS.get((scene_code, gsn, prop["name"])) if gsn is not None else None
    if override:
        pos = list(override)
    en = EN.get(prop["name"], prop["name"].replace("（", "_").replace("）", ""))
    kind = classify(prop["type"])

    if multi is not None:
        objs = [raw_box(shape, size, loc, rot_z) for shape, size, loc, rot_z in multi["parts"]]
        name = f"{scene_code}_{kind}_{en}_{seq:02d}"
        joined = join_objects(objs, coll, name)
        apply_cuts(joined, multi.get("cuts") or [])
        return [joined]

    dx, dy, dz, shape, count, zmode, extra = g
    objs = []
    group_empty = None
    if count > 1:
        group_empty = make_empty(f"{scene_code}_{kind}_{en}", coll)
    for i in range(count):
        px, py = pos[0], pos[1]
        pz = pos[2]
        if extra:
            spread = extra.get("spread")
            if spread == "x":
                px = pos[0] + extra["step"] * i
            elif spread == "y":
                py = pos[1] + extra["step"] * i
            elif spread == "z":
                pz = pos[2] + extra["step"] * i
            elif spread == "x_center":
                px = pos[0] + extra["step"] * (i - (count - 1) / 2.0)
            elif spread == "y_center":
                py = pos[1] + extra["step"] * (i - (count - 1) / 2.0)
            elif spread == "queue":
                px = pos[0] + extra["step"] * i
            elif spread == "explicit":
                off = extra["offsets"][i]
                px = pos[0] + off[0]
                py = pos[1] + off[1]
        if zmode == "center":
            z_center = pz
        elif zmode == "top":
            z_center = pz - dz / 2.0
        else:
            z_center = pz + dz / 2.0
        ob = raw_box(shape, (dx, dy, dz), (px, py, z_center))
        link_to(ob, coll, f"{scene_code}_{kind}_{en}_{i + 1:02d}")
        if group_empty is not None:
            ob.parent = group_empty
        objs.append(ob)
    if count == 1:
        apply_cuts(objs[0], cuts_for(scene_code, prop["name"]))
    return objs


def _shell_plane_key(shape, size, loc, rot_z):
    """把同一组壳体构件按**结构平面**归并（地板 / 顶棚 / 每一面墙 / 每个独立块）。

    ★ 为什么是「按平面」而不是「逐构件」：
      · 逐构件拆会让 D14 合同的 anchors 段（逐实例屏幕指标，受保护不可压缩）
        随对象数线性膨胀 —— 实测 ep01_shot03 的合同源文本 22.4K → 55.8K 字符，
        提示词 6097 → 6774 字，**突破 6500 预算上限**。
      · 而拆分的唯一作用是让「单个构件的包围盒不再包住相机」；按平面归并同样能
        达到该效果（每面墙是独立薄板，相机不在其包围盒内），对象数却只多几件。
      · 墙一旦整圈合并，包围盒又变回房间内体积 ⇒ 相机重新落入 ⇒ 回到「恒 100%」的老路，
        所以**墙必须按面分开**，这是归并粒度的下限。
    """
    sx, sy, sz = size
    if abs(rot_z) > 1e-9:
        return ("R", round(float(rot_z), 4))
    if sz <= 0.6 and sx >= 1.0 and sy >= 1.0:
        return ("H", round(float(loc[2]), 2))          # 地板 / 顶棚
    if sx <= 0.6:
        return ("X", round(float(loc[0]), 2))          # 东西向薄板（一面墙）
    if sy <= 0.6:
        return ("Y", round(float(loc[1]), 2))          # 南北向薄板（一面墙）
    return ("B", round(float(loc[0]), 2), round(float(loc[1]), 2), round(float(loc[2]), 2))


def _merge_identical(parts):
    """把**同尺寸、同朝向**的构件按「对齐轴」再归并一次（柱列、栏杆、阵列…）。

    例：WestPlantShell 的 8 根 0.3×0.3×6.0 立柱，散在两个 x 上 ⇒ 归并成 2 件
    （各按 x 对齐成一行），而不是 8 件。
    理由与代价：合同源文本里 `anchors` 段（逐实例屏幕指标，受保护不可压缩）随
    实例数线性膨胀 —— U02 ep16_shot02 实测 6558 字、突破 6500 预算上限。
    归并后每件仍是**细长薄板**（包围盒不含相机），W3 口径不受影响。
    返回：分组后的构件列表（每组一个对象）。
    """
    by_sig = {}
    for p in parts:
        sig = (p[0], tuple(round(float(v), 3) for v in p[1]), round(float(p[3]), 4))
        by_sig.setdefault(sig, []).append(p)
    groups = []
    for _sig, ps in by_sig.items():
        if len(ps) == 1:
            groups.append(ps)
            continue
        xs = [p[2][0] for p in ps]
        ys = [p[2][1] for p in ps]
        axis = 0 if (max(xs) - min(xs)) <= (max(ys) - min(ys)) else 1
        buckets = {}
        for p in ps:
            buckets.setdefault(round(float(p[2][axis]), 2), []).append(p)
        for k in sorted(buckets):
            groups.append(buckets[k])
    return groups


def _parts_bbox(parts):
    """一组壳体构件的整体世界包围盒 (lo, hi)（忽略 rot_z 的水平旋转，够用）。"""
    lo = [1e18, 1e18, 1e18]
    hi = [-1e18, -1e18, -1e18]
    for _shape, size, loc, _rot in parts:
        for i in range(3):
            lo[i] = min(lo[i], loc[i] - size[i] / 2.0)
            hi[i] = max(hi[i], loc[i] + size[i] / 2.0)
    return lo, hi


def _bbox_encloses(parts, point, margin=0.05):
    """整组包围盒是否**包住**该点（=机位在壳体内部体积里）。"""
    lo, hi = _parts_bbox(parts)
    return all(lo[i] - margin <= point[i] <= hi[i] + margin for i in range(3))


def shell_objects(coll, scene_code, gsn=None, cam_pos=None):
    """铺出空间壳体（墙/地/顶/铺装）。

    ★ Q94 C4-W3：壳体**逐构件独立成对象**，不再整组 join 成一个对象。
      原因：整组 join 后的包围盒**必然包住相机**（室内镜相机在壳体内），
      投影占幅恒为 100% ⇒ V12 W3「画面最大对象必须是角色」在结构上永远不可能通过，
      且白模渲出来就是一块灰板 —— 正是施工图 C4 规则 3 点名的缺陷。
      拆成构件后，每个构件的包围盒只反映**它自己**在画幅里的体量，
      「角色能否压过环境」才成为可判口径。

    命名：首个构件用 `{scene}_EXT_{group}`，其余加 `.NNN` 实例后缀。
      D14 合同的 core_name 会剥掉 `.NNN` ⇒ core 与实体分组保持不变，
      H3 提示词的 ENV/PROP 实体结构不受拆壳影响。
    """
    out = []
    conf = None
    if gsn is not None:
        conf = SHELL_OVERRIDE.get((scene_code, gsn))
    if conf is None:
        conf = SHELL.get(scene_code)
    if not conf:
        return out
    cutters = conf.get("cuts") or []
    for group_name, parts in conf["groups"].items():
        # ★ 拆分的**触发条件**：只有当「整组合并成一个对象」的包围盒会**包住机位**时
        #   才拆 —— 那时该对象的投影占幅恒 100%，W3 结构性不可判，必须拆开。
        #   若机位在壳体之外（室外镜、厂区镜），整组保持一个对象：
        #   实例数不涨 ⇒ D14 合同源文本不涨 ⇒ 提示词预算不被挤爆。
        if cam_pos is not None and not _bbox_encloses(parts, cam_pos):
            buckets = {"__whole__": parts}
        else:
            buckets = {}
            for p in parts:
                buckets.setdefault(_shell_plane_key(*p), []).append(p)
        merged = []
        for key, ps in buckets.items():
            # 只有「独立块」桶才做同尺寸归并；墙/地/顶按平面合并，
            # 其中带洞口的多段墙本就属于同一面墙（拆开反而多实例、无谓膨胀）。
            if key == "__whole__":
                merged.append(ps)
            elif key[0] == "B":
                merged.extend(_merge_identical(ps))
            else:
                merged.append(ps)
        for idx, ps in enumerate(merged, start=1):
            name = (f"{scene_code}_EXT_{group_name}" if idx == 1
                    else f"{scene_code}_EXT_{group_name}.{idx:03d}")
            objs = [raw_box_baked(shape, size, loc, rot_z) for shape, size, loc, rot_z in ps]
            ob = join_objects(objs, coll, name) if len(objs) > 1 else link_to(objs[0], coll, name)
            apply_cuts(ob, cutters)
            out.append(ob)
    return out


def clear_keys_from_camera(keys, cam_pos, view_dir, size, extra=0.0):
    """把角色关键帧从机位内推开。

    眼位 POV 镜与过肩镜里，机位本就落在角色体块中；白模会渲染出盒体内壁，
    整帧变成一块灰板。这里把角色沿「背离机位」方向挪到机位之外：
    与机位同点时推到镜头背后，否则沿径向外推，保证过肩镜仍保留前景肩线。

    ★ extra：额外退让距离（米）。**主观镜**（camera_angle=主观视角）里机位就是
      视点角色的眼睛，角色必须整只退到镜头背后，否则它会占满画幅 —— 白模要表达的
      是「视点角色看到的东西」，不是他自己的身体。
    """
    need = max(size[0], size[1]) / 2.0 + 0.10 + extra
    out = []
    for k in keys:
        ratio, x, y, zb, pose = k
        ox, oy = x - cam_pos[0], y - cam_pos[1]
        d = math.hypot(ox, oy)
        if d < need:
            if d < 1e-3:
                ux, uy = -view_dir[0], -view_dir[1]
            else:
                ux, uy = ox / d, oy / d
            x = cam_pos[0] + ux * need
            y = cam_pos[1] + uy * need
        out.append((ratio, x, y, zb, pose))
    return out


# ───────────────────────────────────────── 角色代理体（Q94 C1 三件套）

# 三件套常量（Q94 C1）：躯干盒 + 头 + 朝向楔
HEAD_R = 0.11                        # 头半径（16 边柱体近似）
# ★ 施工图 v3「C1' 几何口径」唯一权威（总控 11:05 收口）：
#   规则 2 头中心 = 躯干顶 + 0.09（略嵌入肩部，避免悬空缝）
#   规则 3 朝向楔 = 头中心 + 朝向(+Y) 0.14，z = 头中心 − 0.10
HEAD_DZ = 0.09                       # 头中心相对躯干顶的抬升
WEDGE_SIZE = (0.20, 0.10, 0.09)     # 朝向楔 宽×深×高
WEDGE_DY = 0.14                      # 朝向楔在头前方的距离（沿角色朝向 +Y）
WEDGE_DZ = -0.10                     # 朝向楔相对**头中心**的 z 偏移
ARM_DZ = -0.455                      # 举臂盒中心相对躯干顶的偏移（盒顶 z = 支撑面 + 1.35）

# 景别 → 主体占画幅高区间（真源：03_规格/rules.json → white_model_framing.shot_size_bands）
SHOT_SIZE_BANDS = {
    "远景": (8, 25), "全景": (5, 20), "中远景": (20, 40), "中景": (35, 65),
    "中近景": (45, 75), "近景": (55, 85), "特写": (70, 95), "大特写": (80, 98),
}

# 角色姿态随帧的可审计记录：{对象名: [(frame, pose), ...]}（供投影 pose 字段）
CHAR_POSE_TRACK = {}

# 投影 `pose` 字段的**报告口径**（施工图 v3「三、词表口径」）：
#   内容层用 `lieflat`，投影报告为 `lie`（两者语义同源，rules.json 词表两者都在）。
POSE_REPORT = {"lieflat": "lie"}


def pose_parts(pose):
    """该姿态的三件套体块描述（角色局部坐标：+Y 为正面、Z 向上）。

    返回 [(shape, size, center), ...]：
      躯干盒：body = (底面偏移, 顶面偏移, 截面W, 截面D) ⇒ 盒高 = 顶-底，盒心 z = (底+顶)/2
      头　　：16 边柱体近似球，位于躯干顶之上（躺姿时位于长轴端点，与躯干同高带）
      朝向楔：薄板，置于头前方，正对角色朝向
    """
    spec = POSE_SIZE[pose]
    b0, b1, W, D = spec["body"]
    axis = spec.get("axis")
    has_head = spec.get("head", True)
    parts = [("box", (W, D, b1 - b0), (0.0, 0.0, (b0 + b1) / 2.0))]
    if axis == "x":            # 躺姿：长轴沿 X，头在 +X 端（**不旋转**）
        hx = W / 2.0 - HEAD_R * 0.6
        if has_head:
            hz = (b0 + b1) / 2.0
            parts.append(("cyl", (HEAD_R * 2, HEAD_R * 2, HEAD_R * 2), (hx, 0.0, hz)))
            parts.append(("box", WEDGE_SIZE, (hx, WEDGE_DY, hz + WEDGE_DZ)))
    elif axis == "y":          # 躺姿：长轴沿 Y，头在 +Y 端（**不旋转**）
        hy = D / 2.0 - HEAD_R * 0.6
        if has_head:
            hz = (b0 + b1) / 2.0
            parts.append(("cyl", (HEAD_R * 2, HEAD_R * 2, HEAD_R * 2), (0.0, hy, hz)))
            parts.append(("box", WEDGE_SIZE, (0.0, hy + WEDGE_DY, hz + WEDGE_DZ)))
    else:                      # 站/坐/蹲/跪/跑：躯干盒 + 头 + 朝向楔
        if has_head:
            hz = b1 + HEAD_DZ
            parts.append(("cyl", (HEAD_R * 2, HEAD_R * 2, HEAD_R * 2), (0.0, 0.0, hz)))
            parts.append(("box", WEDGE_SIZE, (0.0, WEDGE_DY, hz + WEDGE_DZ)))
        arm = spec.get("arm")
        if arm:
            # C1' 规则 4：举臂盒 0.10×0.10×0.55，举至 z = 支撑面 + 1.35
            parts.append(("box", arm, (0.0, WEDGE_DY, b1 + ARM_DZ)))
    return parts


def raw_part(shape, size, center):
    """在**原点**建体块并把网格平移到 center（对象变换保持单位）。

    为什么不用 raw_box：raw_box 用对象 scale 表达尺寸，join 后各姿态的原点会随体块中心
    漂移，形状键就无从逐顶点对应。这里把尺寸/位移全部烘进**网格数据**，
    使所有姿态共享同一套局部坐标系 ⇒ 形状键可逐点形变。
    """
    from mathutils import Matrix, Vector
    if shape == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=size[0] / 2.0, depth=size[2])
    else:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.object
    ob.scale = (1.0, 1.0, 1.0)
    if shape != "cyl":
        ob.data.transform(Matrix.Diagonal(Vector(size)).to_4x4())
    ob.data.transform(Matrix.Translation(Vector(center)))
    return ob


def pose_vertex_coords(pose):
    """该姿态三件套 join 后的顶点坐标（角色局部坐标，顺序与实际对象一致）。"""
    parts = pose_parts(pose)
    objs = [raw_part(shape, size, center) for shape, size, center in parts]
    joined = join_objects(objs, bpy.context.scene.collection, "__pose_tmp__")
    coords = [tuple(v.co) for v in joined.data.vertices]
    bpy.data.objects.remove(joined, do_unlink=True)
    return coords


def char_yaw(cam_pos, view_dir, char_pos, explicit=None):
    """角色朝向（绕 Z 方位角，度）。

    · 显式朝向优先（CHAR_ANIM 关键帧第 6 位；方位角 0=+X、90=+Y）
    · 默认朝相机视线方向偏 **+40°**（三分之四侧身）⇒ **不会所有角色都正对镜头**
    · 角色与机位几乎同点（主观镜）时取视线方向本身
    """
    if explicit is not None:
        return math.radians(float(explicit))
    look = math.degrees(math.atan2(view_dir[1], view_dir[0]))
    d = math.hypot(char_pos[0] - cam_pos[0], char_pos[1] - cam_pos[1])
    if d < 0.5:
        return math.radians(look)
    return math.radians(look + 40.0)


def build_char_proxy(coll, scene_code, en, seq, x, y, zb, yaw, pose):
    """建角色代理体：躯干盒 + 头 + 朝向楔 三件套 join 成**单个对象**。

    · 对象名保持 `{scene}_CHAR_{en}_{seq:02d}` ⇒ 投影 / 合同 / 实体归并接口一律不变
    · 朝向用**静态** rotation_euler（**不插 rotation 关键帧**）⇒ W4「相邻帧旋转跳变」恒 0
    · 躺姿不带任何 rotation（Q94 R2：躺着的人不需要旋转）
    """
    parts = pose_parts(pose)
    objs = [raw_part(shape, size, center) for shape, size, center in parts]
    ob = join_objects(objs, coll, f"{scene_code}_CHAR_{en}_{seq:02d}")
    ob.location = (x, y, zb)
    lean = math.radians(float(POSE_SIZE[pose].get("lean", 0.0)))
    ob.rotation_euler = (lean, 0.0, yaw)
    return ob


def look_at(cam_obj, target):
    from mathutils import Vector
    d = Vector(target) - cam_obj.location
    cam_obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def face_panel_to_camera(ob, cam_loc):
    """悬浮面板占位板转向机位（板面法线为 ±Y）。"""
    dx = cam_loc[0] - ob.location.x
    dy = cam_loc[1] - ob.location.y
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return
    az = math.atan2(dy, dx)
    ob.rotation_euler = (0.0, 0.0, az - math.pi / 2.0)


def _cam_map_location(cam, fn):
    """按 fn(旧位置) → 新位置 改写相机的 location 关键帧与当前值（**朝向不动**）。

    Blender 5.x：`location` 是三条独立 fcurve（array_index 0/1/2），
    而关键帧点的 `co` 恒为二维 (帧, 值) —— 故必须按 array_index 分组处理。
    """
    ad = cam.animation_data
    if ad and ad.action:
        curves = [fc for fc in _all_fcurves(ad.action) if fc.data_path == "location"]
        if curves:
            by_idx = {fc.array_index: fc for fc in curves}
            frames = sorted({float(kp.co.x) for fc in curves for kp in fc.keyframe_points})
            for fr in frames:
                old = []
                for i in range(3):
                    fc = by_idx.get(i)
                    val = None
                    if fc is not None:
                        for kp in fc.keyframe_points:
                            if abs(kp.co.x - fr) < 1e-4:
                                val = kp.co.y
                                break
                    old.append(val)
                if any(v is None for v in old):
                    continue
                new = fn(tuple(old))
                for i in range(3):
                    fc = by_idx.get(i)
                    if fc is None:
                        continue
                    for kp in fc.keyframe_points:
                        if abs(kp.co.x - fr) < 1e-4:
                            kp.co = (kp.co.x, new[i])
                            break
            for fc in curves:
                fc.update()
    cur = tuple(cam.location)
    cam.location = tuple(fn(cur))


def _camera_inside_mesh(scene, cam, frames=(1,)):
    """相机是否落在某个网格体块内部（Q94 C4 规则 3：不得与外壳内表面重合）。

    返回 (对象名, 帧号)；未落入返回 (None, None)。
    """
    from mathutils import Vector
    for fr in frames:
        scene.frame_set(fr)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        cp = cam.evaluated_get(depsgraph).matrix_world.translation
        for ob in scene.objects:
            if ob.type != "MESH":
                continue
            # 角色代理体不参与「落进体块」判定：视点镜/过肩镜里机位本就贴着角色，
            # 那是合法的机位语义，不是把相机塞进墙里。
            if "_CHAR_" in ob.name:
                continue
            ev = ob.evaluated_get(depsgraph)
            m = ev.matrix_world
            corners = [m @ Vector(c) for c in ev.bound_box]
            lo = [min(c[i] for c in corners) for i in range(3)]
            hi = [max(c[i] for c in corners) for i in range(3)]
            if not all(lo[i] - 0.02 <= cp[i] <= hi[i] + 0.02 for i in range(3)):
                continue
            # ★ 精确判定：相机是否落在**实体内部**，而不是仅仅落在其包围盒里。
            #   大型钢架/厂房结构的包围盒必然包含相机（相机就在厂里），按包围盒判会
            #   把所有这类镜位都误判成「相机塞进墙里」⇒ 取景反推被无谓回滚。
            try:
                ok, loc, nor, _idx = ev.closest_point_on_mesh(m.inverted() @ cp)
            except Exception:
                continue
            if ok and (cp - loc).length < 0.08 and nor.dot(cp - loc) < 0.0:
                return ob.name, fr
    return None, None


# ───────────────────────────────────────── 取景反推（R-026c · 主体优先构图）

# ★ R-026c 重写：原实现用「推拉系数 × 居中微调」两参数粗网格，
#   且只解 W2 不解 W3 ⇒ 环境壳体常年压过主体（U01/U02 实测 52/64 镜 W3 失败）。
#   新实现（scripts/wm_framing.py）**联合求解 W1∧W2∧W3**，
#   口径与插件 scene_inspector._object_sample 逐项一致（见该模块头注释）。
# ★ 取景自由度不变（Q94 C4 规则 1/2）：**只平移机位**，不动朝向 / lens / 角色位置 /
#   D11 的 shot_size 与机位语义。平移量在相机系里表达：
#   dx＝画面右、dy＝画面上、dz＝机位后撤(+)／推进(−)。


def _apply_cam_offset(cam, delta_world):
    """把**世界系**平移量落到相机 location 关键帧上。

    相机旋转关键帧一律不动 ⇒ 视线方向严格不变（Q94 C4 规则 1）。
    """
    d = (float(delta_world[0]), float(delta_world[1]), float(delta_world[2]))
    _cam_map_location(cam, lambda v: (v[0] + d[0], v[1] + d[1], v[2] + d[2]))
    return d


def solve_framing(scene, cam, target, char_objs, other_objs, frames, shot_size, gsn,
                  base_delta_world=None):
    """C4 取景反推（R-026c）：联合求解 W1 主体在画幅 / W2 景别占幅 / W3 主体最大。

    `base_delta_world`：从**当前机位**回到 **D13 原始机位**所需的世界平移。
      求解器拿它当「原位基准」—— 第 2 轮之后当前机位已被挪过，若拿当前机位当
      基准，求解器就再也回不去 D13 原位（实测会把已经合格的镜改坏）。

    返回 dict；无可解时 moved=False 且带 reason。
    """
    import wm_framing
    band = SHOT_SIZE_BANDS.get(shot_size)
    if not band or not char_objs:
        return None
    orig_loc = tuple(cam.location)
    res = wm_framing.solve(scene, cam, char_objs, other_objs, frames, shot_size,
                            RES_X, RES_Y, base_delta_world=base_delta_world)
    if res is None:
        return {"shot_size": shot_size, "band": list(band), "moved": False,
                "reason": "角色不在任何采样帧的画幅内（占幅 0%）—— 取景反推无解",
                "h_before": 0.0, "other_max": 0.0}
    delta = _apply_cam_offset(cam, res["delta_world"])
    moved = tuple(cam.location) != orig_loc
    res.update({
        "moved": moved,
        "delta_m": [round(v, 3) for v in delta],
        "loc": [round(v, 3) for v in cam.location],
        "loc_d13": [round(v, 3) for v in orig_loc],
    })
    # 相机若落进网格体块 ⇒ 回滚到 D13 原机位（宁可不合格，也不把相机塞进墙里）
    inside, inside_frame = _camera_inside_mesh(scene, cam, wm_framing.v12_sample_frames(1, frames))
    if inside:
        _cam_map_location(cam, lambda v: orig_loc)
        res.update({"moved": False, "reverted": True,
                    "delta_m": [0.0, 0.0, 0.0],
                    "loc": [round(v, 3) for v in orig_loc],
                    "inside": inside, "inside_frame": inside_frame})
    scene.frame_set(1)
    return res


# ------------------------------------------------------------------ 主流程


def _pose_at(name, frame):
    """该帧生效的角色姿态（CHAR_POSE_TRACK＝CHAR_ANIM 的时序真源）。

    取「最后一个 frame ≤ 采样帧」的姿态；早于首个关键帧时取首个姿态。
    """
    track = CHAR_POSE_TRACK.get(name)
    if not track:
        return None
    cur = None
    for f, p in sorted(track):
        if f <= frame:
            cur = p
        else:
            break
    return cur if cur is not None else sorted(track)[0][1]


def enrich_projection_fields(scene, evidence):
    """给每个采样帧补 `rotation_euler_deg`（该采样帧实际欧拉角，度）与 `pose`。

    ★ 为什么必须由白模侧采：H3 插件 `scene_inspector._object_sample`
      **只测包围盒与深度，不采样旋转** ⇒ 投影里没有 rotation_euler_deg，
      V12 的 W4（相邻采样帧旋转跳变）就无从判定。
    ★ pose：CHAR 必填（角色代理体的当前姿态）；道具/环境可为 null。
    """
    if not evidence:
        return
    frames = evidence.get("sample_frames") or []
    objs_by_name = {o.name: o for o in scene.objects}
    for fr in frames:
        scene.frame_set(fr)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for entry in evidence.get("objects", []):
            ob = objs_by_name.get(entry.get("name"))
            if ob is None:
                continue
            try:
                ev = ob.evaluated_get(depsgraph)
            except RuntimeError:
                continue
            eul = ev.matrix_world.to_euler()
            rot = [round(math.degrees(v), 3) for v in eul]
            pose = _pose_at(entry.get("name"), int(fr))
            if pose is not None:
                pose = POSE_REPORT.get(pose, pose)
            for s in entry.get("samples", []):
                if int(s.get("frame", -1)) != int(fr):
                    continue
                s["rotation_euler_deg"] = rot
                s["pose"] = pose
    scene.frame_set(1)


def build_shot(gsn, out_dir):
    info = SHOT[gsn]
    scene_code = info["scene_code"]
    ep, shot_id = info["ep"], info["shot_id"]
    scene = bpy.data.scenes.new(f"S_ep{ep:02d}_sh{shot_id:02d}")
    bpy.context.window.scene = scene
    coll = scene.collection

    # ★ 逐镜清空姿态记录（修 pose 串镜）：
    #   本镜结束时会删除本镜对象（保持 Blender 命名空间干净、避免跨镜追加 .001
    #   后缀），于是**同一场景的同一角色在下一镜会复用同一个对象名**
    #   （如 A-1_CHAR_Luchen_01 同时出现在 A-1 的第 1/3/4 镜）。
    #   CHAR_POSE_TRACK 以对象名为键，若不清空，后一镜的关键帧会**追加**到前
    #   一镜的轨道上；`_pose_at` 取「最后一个 frame ≤ 采样帧」时就会跨镜取到
    #   别的镜的姿态 ⇒ 投影 pose 字段报错（U01 ep01_shot03 曾报 lie/situp，
    #   实为 ep01_shot01 的躺姿时序；U02 ep10_shot04 同理）。
    #   姿态真源是每镜独立的 CHAR_ANIM，故逐镜清空即可，不影响几何与取景求解。
    CHAR_POSE_TRACK.clear()

    # 1) 空间壳体（是否拆分取决于「整组包围盒会不会包住机位」）
    camp = next(c for c in CAMS[scene_code] if c["global_shot_no"] == gsn)
    shell_objects(coll, scene_code, gsn, cam_pos=list(camp["position_m"]))

    # 2) 道具代理（按 D13 props 的 shots 字段逐镜筛选）
    frames = max(2, int(round(info["duration_sec"] * FPS)))
    seq = 0
    panels = []
    for prop in PROPS[scene_code]:
        prop_shots = prop.get("shots")
        if prop_shots is not None and gsn not in prop_shots:
            continue
        seq += 1
        made = prop_objects(coll, scene_code, prop, seq, gsn)
        if prop["type"] == "悬浮界面":
            panels.extend(made)
        apply_prop_anim(scene_code, gsn, prop, made, frames)

    # 3) 角色代理（优先用动作关键帧表；无关键帧时回退到静态 CHARS）
    #    机位若落在角色代理体内，渲染出的是盒体内壁；先把角色让开机位。
    cam_pos = list(camp["position_m"])
    cam_tgt = list(camp.get("target_m") or camp["position_m"])
    vdx, vdy = cam_tgt[0] - cam_pos[0], cam_tgt[1] - cam_pos[1]
    vlen = math.hypot(vdx, vdy) or 1.0
    view_dir = (vdx / vlen, vdy / vlen)

    # 主观镜：机位＝视点角色的眼睛，角色必须退到镜头背后（见 clear_keys_from_camera）
    pov_extra = 1.20 if (info.get("camera_angle") or "") == "主观视角" else 0.0

    cseq = 0
    char_objs = []
    anim = CHAR_ANIM.get((scene_code, gsn))
    # ★ Q94 C3：CHAR_ANIM 优先于 CHARS，但**冲突必须显式告警**（不得再静默通过）
    static_specs = {s[0]: s for s in (CHARS.get((scene_code, gsn)) or [])}
    if anim:
        for en, keys in anim.items():
            cseq += 1
            pose0 = keys[0][4]
            spec = POSE_SIZE[pose0]
            body = spec["body"]
            override = CHAR_POS.get((scene_code, gsn, en))
            if override:
                keys = [(k[0], override[0], override[1], override[2], k[4]) for k in keys]
            else:
                keys = clear_keys_from_camera(keys, cam_pos, view_dir, (body[2], body[3]),
                                             extra=pov_extra)
            st = static_specs.get(en)
            if st and st[6] != pose0:
                print(f"[POSE-CONFLICT] {scene_code} g{gsn} {en}: "
                      f"CHAR_ANIM 首帧「{pose0}」 vs CHARS「{st[6]}」"
                      f"（ANIM 生效；CHARS 为静态兜底）", flush=True)
            x0, y0, zb0 = keys[0][1], keys[0][2], keys[0][3]
            yaw = char_yaw(cam_pos, view_dir, (x0, y0),
                           explicit=(keys[0][5] if len(keys[0]) > 5 else None))
            ob = build_char_proxy(coll, scene_code, en, cseq, x0, y0, zb0, yaw, pose0)
            char_objs.append(ob)
            # 姿态形变目标：把该镜涉及的所有姿态各建一份顶点坐标
            pose_targets = {}
            for k in keys:
                p = k[4]
                if p not in pose_targets:
                    pose_targets[p] = pose_vertex_coords(p)
            animate_char(ob, keys, frames, pose_targets)
    else:
        for spec in CHARS.get((scene_code, gsn), []):
            cseq += 1
            en, cn, x, y, z, h, pose = spec
            body = POSE_SIZE[pose]["body"]
            if (scene_code, gsn, en) not in CHAR_POS:
                keys = clear_keys_from_camera([(0.0, x, y, z, pose)], cam_pos, view_dir,
                                              (body[2], body[3]), extra=pov_extra)
                x, y, z = keys[0][1], keys[0][2], keys[0][3]
            yaw = char_yaw(cam_pos, view_dir, (x, y))
            ob = build_char_proxy(coll, scene_code, en, cseq, x, y, z, yaw, pose)
            char_objs.append(ob)
            animate_char(ob, [(0.0, x, y, z, pose)], frames,
                         {pose: pose_vertex_coords(pose)})

    # 4) 相机
    cam_data = bpy.data.cameras.new(f"CAM_g{gsn:02d}")
    cam_data.lens = float(info["lens_mm"])
    cam_data.sensor_width = LENS_SENSOR
    cam = bpy.data.objects.new(f"CAM_g{gsn:02d}", cam_data)
    coll.objects.link(cam)
    scene.camera = cam
    start = camp["position_m"]
    target = camp.get("target_m") or camp["position_m"]
    cam.location = start
    look_at(cam, target)

    for panel in panels:
        face_panel_to_camera(panel, start)

    # 5) 相机动画
    scene.frame_start = 1
    scene.frame_end = frames
    motion, end_pos, ratio = CAM_MOVE.get(gsn, ("static", None, None))
    if motion == "dolly" and end_pos is None and ratio:
        from mathutils import Vector
        s, t = Vector(start), Vector(target)
        cam.location = s
        cam.keyframe_insert("location", frame=1)
        cam.location = s + (t - s) * (1.0 - ratio)
        look_at(cam, t)
        cam.keyframe_insert("location", frame=frames)
    elif end_pos is not None:
        cam.keyframe_insert("location", frame=1)
        cam.location = tuple(end_pos)
        look_at(cam, target)
        cam.keyframe_insert("location", frame=frames)
    elif motion == "handheld":
        for f in range(1, frames + 1, max(1, frames // 8)):
            jitter = (math.sin(f * 1.7) * 0.04, math.cos(f * 2.3) * 0.04, math.sin(f * 3.1) * 0.02)
            cam.location = (start[0] + jitter[0], start[1] + jitter[1], start[2] + jitter[2])
            cam.keyframe_insert("location", frame=f)
        cam.location = start
    elif motion == "tracking":
        cam.keyframe_insert("location", frame=1)
        cam.location = tuple(end_pos) if end_pos else start
        cam.keyframe_insert("location", frame=frames)
    if motion in ("dolly", "crane", "tracking"):
        # ★ 分支归一（U01-R34 ep01_shot03 灰板根因修复）
        #   旋转只在首/尾帧打关键帧，中间按 **Euler 分量线性插值**。若首尾两个
        #   look_at 朝向落在不同的 ±180° 分支（如首 yaw=+125.8°、尾 yaw=-105.8°），
        #   线性插值会走 **远路**（+231.6° 而非 -128.4°），相机中途转向空处 ⇒
        #   整帧渲成纯色（unique=1 / std=0.00），且末段朝向与目标脱钩。
        #   修法：把尾端欧拉角折到与首端**同分支**（加/减 360° 的等价表示，
        #   末帧朝向逐位不变 ⇒ 未踩坑的镜位画面零变化），插值即走最短弧。
        start_eul = None
        for f in (1, frames):
            scene.frame_set(f)
            look_at(cam, target)
            if f == 1:
                start_eul = [math.degrees(v) for v in cam.rotation_euler]
            else:
                eul = [math.degrees(v) for v in cam.rotation_euler]
                for i in range(3):
                    while eul[i] - start_eul[i] > 180.0:
                        eul[i] -= 360.0
                    while eul[i] - start_eul[i] < -180.0:
                        eul[i] += 360.0
                cam.rotation_euler = [math.radians(v) for v in eul]
            cam.keyframe_insert("rotation_euler", frame=f)
    scene.frame_set(1)

    # 6) 渲染设置
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.film_transparent = False
    scene.render.use_simplify = True

    # 6b) ★ Q94 C4 / R-026c 取景反推 + 壳体剖切（主体优先构图）
    framing = None
    cuts = []
    # ★ 主体集合＝**所有**名字含 `_CHAR_` 的对象（与 V12 的 wmKindOf 同口径）：
    #   不只是 CHAR_ANIM/CHARS 建的姿态代理体，也包括 D13 里 type='人群/剪影'
    #   的人群道具（它们现在也被 classify 成 CHAR）。V12 认主体只看对象名，
    #   求解器必须用同一套口径，否则「主体」集合与判据不一致 ⇒ 求解目标错位。
    subject_objs = [o for o in scene.objects
                    if o.type == "MESH" and "_CHAR_" in o.name]
    if subject_objs:
        import wm_framing
        subj_set = {o.name for o in subject_objs}
        other_objs = [o for o in scene.objects
                      if o.type == "MESH" and o.name not in subj_set]
        shot_size = info.get("shot_size", "")
        # D13 原始机位（世界坐标）—— 求解器的「原位基准」，任何一轮都可回退到它
        d13_cam = tuple(start)
        # 累计施加的世界平移（相对 D13 原始机位）
        applied = [0.0, 0.0, 0.0]

        def _base_delta():
            """从当前机位回到 D13 原始机位所需的世界平移。"""
            return (-applied[0], -applied[1], -applied[2])

        for _round in range(4):
            framing = solve_framing(scene, cam, target, subject_objs, other_objs,
                                     frames, shot_size, gsn,
                                     base_delta_world=_base_delta())
            if framing and framing.get("moved"):
                dm = framing.get("delta_m") or [0.0, 0.0, 0.0]
                applied = [applied[i] + dm[i] for i in range(3)]
            if framing and framing.get("pass_all"):
                break
            new_cuts = wm_framing.cutaway(scene, cam, subject_objs, other_objs,
                                          frames, shot_size, RES_X, RES_Y)
            if not new_cuts:
                break
            cuts.extend(new_cuts)
        if cuts:
            # 剖切改变了几何 ⇒ 重解一次机位（基准仍是 D13 原始机位）
            framing = solve_framing(scene, cam, target, subject_objs, other_objs,
                                    frames, shot_size, gsn,
                                    base_delta_world=_base_delta())
        if framing:
            if "subject_max" in framing:
                print(f"[FRAMING] g{gsn:02d} {framing['shot_size']} "
                      f"主体占幅 {framing['subject_max']}% (带 {framing['band']}) "
                      f"环境最大 {framing['other_max']}% "
                      f"W2={'OK' if framing['w2_in_band'] else 'NG'} "
                      f"W3={'OK' if framing['w3_char_largest'] else 'NG'} "
                      f"压制项={framing.get('worst_other')}"
                      f"({framing.get('worst_other_h')}%) "
                      f"机位 {framing['loc_d13']}→{framing['loc']}"
                      f" Δ={framing.get('delta_m')}"
                      f" 剖切={len(cuts)}"
                      + ("  [回滚]" if framing.get("reverted") else ""), flush=True)
            else:
                print(f"[FRAMING] g{gsn:02d} {framing.get('shot_size')} 无解："
                      f"{framing.get('reason')}", flush=True)
            # 机位动了 ⇒ 悬浮面板要重新转向新机位
            for panel in panels:
                face_panel_to_camera(panel, cam.location)

    # 7) 导出
    from bl_ext.user_default.minimax_h3.services import preview_exporter
    from bl_ext.user_default.minimax_h3.services import scene_inspector
    from bl_ext.user_default.minimax_h3.models.manifest import ExportManifest, FileEntry

    shot_dir = os.path.join(out_dir, f"ep{ep:02d}_shot{shot_id:02d}")
    os.makedirs(shot_dir, exist_ok=True)
    video_path = os.path.join(shot_dir, "preview_video.mp4")
    apply_flat_view(scene)
    install_shade_variant()
    # WM_SKIP_RENDER=1 仅供**算法诊断**（跳过逐帧渲染，只算取景与投影）。
    # 正式重建不设该变量 —— 交付物必须含完整 preview_video.mp4。
    if not os.environ.get("WM_SKIP_RENDER"):
        preview_exporter.export_preview(
            scene=scene, camera=cam, frame_start=1, frame_end=frames,
            fps=FPS, resolution="original", export_mode="white_model",
            output_path=video_path,
        )
    scene.frame_set(1)
    evidence = scene_inspector.build_structure_evidence(
        scene, camera=cam, frame_start=1, frame_end=frames)
    # ★ Q94 追加要求：补 rotation_euler_deg / pose（插件 _object_sample 不采样旋转，
    #   旋转真源必须由白模侧补采；姿态取自 CHAR_ANIM 的时序真源）
    enrich_projection_fields(scene, evidence)
    if os.environ.get("WM_SKIP_RENDER"):
        # 诊断模式：写占位字节（manifest 校验要求 size>0），交付重建不走此分支
        with open(video_path, "wb") as f:
            f.write(b"WM_SKIP_RENDER_DIAGNOSTIC")
    raw = open(video_path, "rb").read()
    manifest = ExportManifest(
        addon_version="1.0.7",
        blender_version=info_scene()["blender_version"],
        os_name=info_scene()["os_name"],
        arch=info_scene()["arch"],
        scene_name=scene.name,
        camera_name=cam.name,
        frame_start=1, frame_end=frames, fps=FPS,
        resolution="original", export_mode="white_model",
        duration_seconds=frames / float(FPS),
        intent=f"{UNIT_ID} ep{ep:03d} shot{shot_id:02d} global_shot_no {gsn} scene {scene_code} white-model blockout",
        files=[FileEntry(role="preview_video", name="preview_video.mp4",
                         size_bytes=len(raw),
                         sha256=hashlib.sha256(raw).hexdigest(),
                         mime="video/mp4")],
        structure_evidence=evidence,
    )
    manifest.validate()
    with open(os.path.join(shot_dir, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(manifest.to_json_bytes().decode("utf-8"))
    visible = sum(1 for o in (evidence["objects"] if evidence else []) if o.get("ever_projected_visible"))
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
        apply_flat_view(scene)
        render_diag_views(scene, cam, shot_dir, gsn)
    except Exception as exc:
        print(f"[DIAG-SKIP] g{gsn:02d}: {exc}", flush=True)
    # 清理本镜对象：保持 Blender 命名空间干净，避免跨镜自动追加 .001 后缀，
    # 使每镜的 root_name / source_id 稳定可读。
    for ob in list(scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    try:
        bpy.data.scenes.remove(scene)
    except Exception:
        pass
    return {
        "global_shot_no": gsn, "ep": ep, "shot_id": shot_id, "scene_code": scene_code,
        "duration_sec": info["duration_sec"], "frames": frames, "fps": FPS,
        "dir": shot_dir, "video": video_path,
        "objects": len(evidence["objects"]) if evidence else 0,
        "visible_objects": visible,
        "framing": framing,
    }


def _all_fcurves(action):
    """取一个 Action 的全部 fcurve（Blender 5.x 为分层/分槽结构，须逐层遍历）。"""
    curves = []
    try:
        curves = list(action.fcurves)
    except AttributeError:
        for layer in getattr(action, "layers", []):
            for strip in getattr(layer, "strips", []):
                for bag in getattr(strip, "channelbags", []):
                    curves.extend(getattr(bag, "fcurves", []))
    return curves


def _set_linear(ob):
    """设关键帧为线性插值（Blender 5.x Action 为分槽结构，逐层遍历）。"""
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    for fc in _all_fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def animate_char(ob, keys, total, pose_targets=None):
    """按 CHAR_ANIM 关键帧驱动角色代理体（Q94 C1/C2）。

    · 位置：location 关键帧（z ＝ **支撑面**高，体块底偏移由 POSE_SIZE 决定）
    · 姿态：**形状键**逐姿态交叉淡入 ⇒ 躯干/头/朝向楔随姿态整体变形
    · **不插 rotation 关键帧** ⇒ 相邻采样帧旋转跳变恒 0（Q94 R2 / W4 上限 30°）
    """
    base_pose = keys[0][4]
    skeys = {}
    if pose_targets:
        ob.shape_key_add(name="basis", from_mix=False)
        nbase = len(ob.data.vertices)
        for pose, coords in pose_targets.items():
            if pose == base_pose:
                continue
            if len(coords) != nbase:
                print(f"[WARN] 姿态 {pose} 顶点数 {len(coords)} ≠ 基准 {nbase}，跳过该形状键",
                      flush=True)
                continue
            k = ob.shape_key_add(name=f"pose_{pose}", from_mix=False)
            for i, co in enumerate(coords):
                k.data[i].co = co
            skeys[pose] = k
    track = CHAR_POSE_TRACK.setdefault(ob.name, [])
    for ratio, x, y, zb, pose in keys:
        frame = max(1, min(total, int(round(ratio * total))))
        ob.location = (x, y, zb)
        # ★ 位置关键帧（漏了这一条，角色就会整镜钉在最后一个关键帧上不动 ——
        #   白模退化成静剪影，D11 的动作时序完全丢失）
        ob.keyframe_insert("location", frame=frame)
        for p, k in skeys.items():
            k.value = 1.0 if p == pose else 0.0
            k.keyframe_insert("value", frame=frame)
        track.append((frame, pose))
    _set_linear(ob)
    sk = getattr(ob.data, "shape_keys", None)
    if sk and sk.animation_data and sk.animation_data.action:
        for fc in _all_fcurves(sk.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def animate_prop(ob, keys, total):
    base_loc = ob.location.copy()
    base_scale = ob.scale.copy()
    for ratio, dx, dy, dz, sx, sy, sz in keys:
        frame = max(1, min(total, int(round(ratio * total))))
        ob.location = (base_loc.x + dx, base_loc.y + dy, base_loc.z + dz)
        ob.scale = (base_scale.x * sx, base_scale.y * sy, base_scale.z * sz)
        ob.keyframe_insert("location", frame=frame)
        ob.keyframe_insert("scale", frame=frame)
    _set_linear(ob)


def apply_prop_anim(scene_code, gsn, prop, made, frames):
    """按 PROP_ANIM 给道具加运动关键帧（队列入场、车灯扫过、触角顶出等）。"""
    if not made:
        return
    keys = PROP_ANIM.get((scene_code, gsn, prop["name"]))
    target = None
    if keys is not None:
        target = made[0].parent if made[0].parent is not None else made[0]
    else:
        prefix = prop["name"] + "#"
        for key, kk in PROP_ANIM.items():
            if key[0] == scene_code and key[1] == gsn and key[2].startswith(prefix):
                try:
                    n = int(key[2][len(prefix):])
                except ValueError:
                    continue
                if 1 <= n <= len(made):
                    keys = kk
                    target = made[n - 1]
                break
    if keys is None or target is None:
        return
    animate_prop(target, keys, frames)


def info_scene():
    import platform
    return {"blender_version": bpy.app.version_string, "os_name": platform.system(),
            "arch": platform.machine()}


def apply_flat_view(scene):
    """白模预览用平色：色彩变换走 Standard，避免 AgX 把灰压暗并染色。"""
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
    except Exception:
        pass
    shading = scene.display.shading
    try:
        shading.studiolight_rotate_z = 0.0
    except Exception:
        pass


def install_shade_variant():
    """扩展的 white_model 是 STUDIO 单灯 + 阴影，室内镜大面积死黑读不出结构。
    这里保留扩展的 export_preview 调用链，只在其 white_model 预设之后调整
    视口着色参数，使白模成为「可读灰模」：均匀底光 + 轮廓线 + 腔体线。
    D13_SHADE=v1 关闭本调整，完全使用扩展默认外观。
    """
    mode = os.environ.get("D13_SHADE", "v3")
    if mode == "v1":
        return
    from bl_ext.user_default.minimax_h3.services import preview_exporter
    orig = preview_exporter._apply_white_model

    def patched(scene):
        orig(scene)
        sh = scene.display.shading
        if mode == "v2":
            sh.studiolight_intensity = 1.15
            sh.studiolight_rotate_z = 0.7
            sh.background_type = "VIEWPORT"
            sh.background_color = (0.24, 0.24, 0.24)
        elif mode == "v4":
            # 保留 STUDIO 的面明暗（形体可读），关掉投影死黑，加轮廓线与腔体线
            sh.show_shadows = False
            sh.studiolight_intensity = 0.85
            sh.studiolight_rotate_z = 0.55
            sh.show_object_outline = True
            try:
                sh.object_outline_color = (0.10, 0.10, 0.11)
            except Exception:
                pass
            sh.show_cavity = True
            try:
                sh.cavity_type = "BOTH"
                sh.curvature_ridge_factor = 1.0
                sh.curvature_valley_factor = 1.0
            except Exception:
                pass
            sh.background_type = "VIEWPORT"
            sh.background_color = (0.22, 0.22, 0.24)
        else:  # v3
            sh.light = "FLAT"
            sh.show_shadows = False
            sh.show_object_outline = True
            sh.show_cavity = True
            try:
                sh.cavity_type = "BOTH"
            except Exception:
                pass
            sh.background_type = "VIEWPORT"
            sh.background_color = (0.16, 0.16, 0.16)

    preview_exporter._apply_white_model = patched
    try:
        scene.view_settings.view_transform = "Standard"
    except Exception:
        pass


def object_bounds(scene):
    """导出每对象世界包围盒，供诊断（不进入交付物）。"""
    from mathutils import Vector
    rows = []
    for ob in scene.objects:
        if ob.type != "MESH":
            continue
        corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = [round(min(c[i] for c in corners), 3) for i in range(3)]
        hi = [round(max(c[i] for c in corners), 3) for i in range(3)]
        rows.append({"name": ob.name, "parent": ob.parent.name if ob.parent else None,
                     "min": lo, "max": hi,
                     "size": [round(hi[i] - lo[i], 3) for i in range(3)]})
    return rows


def render_diag_views(scene, cam, shot_dir, gsn):
    """诊断用：正交俯视 / 正视 / 侧视 + 相机位，用于核对几何布局。"""
    if os.environ.get("D13_DIAG", "") in ("", "0"):
        return
    from mathutils import Vector
    pts = []
    for ob in scene.objects:
        if ob.type == "MESH":
            for c in ob.bound_box:
                pts.append(ob.matrix_world @ Vector(c))
    if not pts:
        return
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    cx = (lo[0] + hi[0]) / 2.0
    cy = (lo[1] + hi[1]) / 2.0
    span = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1.0) * 1.15
    views = {
        "top": ((cx, cy, hi[2] + span), (cx, cy, 0.0)),
        "front": ((cx, lo[1] - span, (lo[2] + hi[2]) / 2.0), (cx, cy, (lo[2] + hi[2]) / 2.0)),
        "side": ((hi[0] + span, cy, (lo[2] + hi[2]) / 2.0), (cx, cy, (lo[2] + hi[2]) / 2.0)),
    }
    orig_cam = scene.camera
    orig_loc = cam.location.copy()
    orig_rot = cam.rotation_euler.copy()
    for vname, (loc, tgt) in views.items():
        dcam_data = bpy.data.cameras.new(f"DIAG_{vname}")
        dcam_data.type = "ORTHO"
        dcam_data.ortho_scale = span
        dcam = bpy.data.objects.new(f"DIAG_{vname}", dcam_data)
        scene.collection.objects.link(dcam)
        dcam.location = loc
        look_at(dcam, tgt)
        scene.camera = dcam
        path = os.path.join(shot_dir, f"diag_{vname}.png")
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        scene.collection.objects.unlink(dcam)
        bpy.data.objects.remove(dcam)
    scene.camera = orig_cam
    cam.location = orig_loc
    cam.rotation_euler = orig_rot
    with open(os.path.join(shot_dir, "diag_bounds.json"), "w", encoding="utf-8") as f:
        json.dump({"camera": list(orig_loc), "objects": object_bounds(scene)},
                  f, ensure_ascii=False, indent=1)


def validate_tables():
    """启动自检：所有体块描述必须是 (shape, size, loc, rot_z) 四元组。"""
    bad = []
    for key, conf in MULTI.items():
        for item in (conf.get("parts") or []) + (conf.get("cuts") or []):
            if len(item) != 4:
                bad.append(f"MULTI {key}: {item}")
    for key, items in CUTS.items():
        for item in items or []:
            if len(item) != 4:
                bad.append(f"CUTS {key}: {item}")
    for key, conf in SHELL.items():
        for gname, parts in conf["groups"].items():
            for item in parts:
                if len(item) != 4:
                    bad.append(f"SHELL {key}.{gname}: {item}")
        for item in (conf.get("cuts") or []):
            if len(item) != 4:
                bad.append(f"SHELL {key}.cuts: {item}")
    if bad:
        raise ValueError("体块描述必须是四元组 (shape, size, loc, rot_z)：\n  " + "\n  ".join(bad))
    print(f"[TABLES-OK] MULTI={len(MULTI)} CUTS={len(CUTS)} SHELL={len(SHELL)}", flush=True)


def main():
    validate_tables()
    stamp = os.environ.get("D13_STAMP", f"{UNIT_ID.lower()}-white-model")
    out_root = os.path.join(OUT_ROOT, stamp)
    os.makedirs(out_root, exist_ok=True)
    limit = int(os.environ.get("D13_LIMIT", "0"))
    only = os.environ.get("D13_ONLY", "")
    targets = sorted(SHOT)
    if limit:
        targets = targets[:limit]
    if only:
        wanted = {int(x) for x in only.split(",") if x.strip()}
        targets = [g for g in targets if g in wanted]
    results = []
    for gsn in targets:
        try:
            r = build_shot(gsn, out_root)
            results.append(r)
            print(f"[OK] g{gsn:02d} {r['scene_code']} objs={r['objects']} "
                  f"visible={r['visible_objects']} frames={r['frames']} "
                  f"-> {os.path.basename(r['dir'])}", flush=True)
        except Exception as exc:
            print(f"[FAIL] g{gsn:02d}: {type(exc).__name__}: {exc}", flush=True)
            raise
    index = os.path.join(OUT_ROOT, "index.json")
    json.dump({"stamp": stamp, "root": out_root, "shots": results},
              open(index, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("DONE", out_root, flush=True)


if __name__ == "__main__":
    main()
