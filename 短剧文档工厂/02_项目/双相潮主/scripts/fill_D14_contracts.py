#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D14 逐镜合同填写器：把 preflight 模板里的 M3_FILL 换成实测描述（**单元无关逻辑**）。

用法：
    python3 fill_D14_contracts.py --unit U01 --work /tmp/dcc-smoke/u01
    python3 fill_D14_contracts.py --unit U02 --work /tmp/dcc-smoke/u02

数据来源（全部为真实证据，不臆测）：
  manifest.json      → Blender structure_evidence（实例、投影框、相机位姿）
  D11.json           → 镜头语义（景别、运镜、画面事实）
  D13.json           → 空间真源（机位、灯位）
  D10.json           → 全场景风格合同
  d14_contract_data  → 实体语义表 / 镜头动作表 / 交互表 / 声音表
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

def _parse_args():
    ap = argparse.ArgumentParser(description="D14 逐镜合同填写器")
    ap.add_argument("--unit", default=os.environ.get("UNIT_ID", "U01"),
                    help="单元号，如 U01 / U02（默认 U01）")
    ap.add_argument("--project", default=os.environ.get("D14_PROJECT", ""),
                    help="项目目录（默认 双相潮主）")
    ap.add_argument("--work", default=os.environ.get("D14_WORK", ""),
                    help="白模工作区（默认 /tmp/dcc-smoke/<unit 小写>）")
    ap.add_argument("--content", default=os.environ.get("D14_CONTENT", ""),
                    help="合同内容模块（默认 d14_contract_data_<UNIT>）")
    args, _unknown = ap.parse_known_args()
    return args


ARGS = _parse_args()
UNIT = ARGS.unit
# 项目根默认从脚本位置推导（<项目>/scripts/..），不写死绝对路径
ROOT = Path(ARGS.project) if ARGS.project else Path(__file__).resolve().parent.parent
WORK = Path(ARGS.work) if ARGS.work else Path(f"/tmp/dcc-smoke/{UNIT.lower()}")
FPS = 24.0

def _load_content(name):
    """加载合同内容模块（实体语义表 / 镜头动作表 / 交互表 / 声音表）。

    ⚠️ 不设任何跨单元兜底：找不到就报错。回落到别的单元的内容＝静默用错数据。
    """
    import importlib
    last = None
    for c in (name, f"d14_contract_data_{name}"):
        try:
            return importlib.import_module(c)
        except ModuleNotFoundError as e:
            last = e
    raise SystemExit(f"合同内容模块不存在：{name}（{last}）")


_CONTENT = _load_content(ARGS.content) if ARGS.content else _load_content(f"d14_contract_data_{UNIT}")
FORBIDDEN_MOTION = _CONTENT.FORBIDDEN_MOTION
INTERACTIONS = _CONTENT.INTERACTIONS
MOTION_TYPE = _CONTENT.MOTION_TYPE
PRIMARY_PICK = _CONTENT.PRIMARY_PICK
SEMANTIC = _CONTENT.SEMANTIC
SHOT_DATA = _CONTENT.SHOT_DATA
SHOT_SCALE = _CONTENT.SHOT_SCALE
SOUND = _CONTENT.SOUND
STYLE_BIBLE = _CONTENT.STYLE_BIBLE
core_name = _CONTENT.core_name
load = _CONTENT.load
write = _CONTENT.write

# ★ 人形实体集合：**优先由内容模块显式声明**（`HUMAN_CORES`）。
#   - U02 模块已声明 ⇒ Suqingci / Yechongjun / GreySpottedPatient 等得到人形朝向描述；
#     旧版把名单写死 U01 的 7 个 core，U02 角色全落「通用体积」描述（实测遗留问题）。
#   - 内容模块**未声明**时 → **回落到历史行为（U01 的 7 个 core）**，
#     保证 U01 的重建输出**逐字不变**（U01 已锁，不得因本改动而漂移）。
#     ⚠️ 曾试过「从 SEMANTIC 的 articulated/living 推导」：U01 的 DisposalSilhouette
#     也是 articulated，会让 U01 重建输出漂移 —— 故不采用该派生式。
HUMAN_CORES = getattr(_CONTENT, "HUMAN_CORES", None) or {
    "Luchen", "LuchenHand", "Yechengjun", "Yehongyi",
    "GuardCaptain", "EscortQueueMember", "RescuedQueueMember",
}

D11 = load(ROOT / f"units/{UNIT}/D11.json")
D13 = load(ROOT / f"units/{UNIT}/D13.json")
D11_SHOTS = {}
for _epi in D11["episodes"]:
    for s in _epi["shots"]:
        # 集号在 D11 里挂在 episode 上，不在 shot 上 —— 补进镜条目，
        # 逐镜目录名 ep<NN>_shot<NN> 依赖它（漏注入会 KeyError: 'ep'）
        s = dict(s)
        s["ep"] = _epi["ep"]
        D11_SHOTS[int(s["global_shot_no"])] = s
D13_SCENES = {s["scene_code"]: s for s in D13["scenes"]}


# ------------------------------------------------------------------ 数学工具

def quat_rotate(q, v):
    w, x, y, z = q
    ux, uy, uz = x * v[0] + y * v[1] + z * v[2]
    cx = y * v[2] - z * v[1]
    cy = z * v[0] - x * v[2]
    cz = x * v[1] - y * v[0]
    return (v[0] + 2.0 * (w * cx + y * cz - z * cy),
            v[1] + 2.0 * (w * cy + z * cx - x * cz),
            v[2] + 2.0 * (w * cz + x * cy - y * cx))


def cam_axes(cam):
    q = cam["rotation_quaternion_wxyz"]
    return (quat_rotate(q, (1.0, 0.0, 0.0)),
            quat_rotate(q, (0.0, 1.0, 0.0)),
            quat_rotate(q, (0.0, 0.0, -1.0)))


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def fmt(v, n=2):
    return "(" + ", ".join(f"{x:.{n}f}" for x in v) + ")"


def pick(samples, t):
    if not samples:
        return None
    target = 1 + t * FPS
    return min(samples, key=lambda s: abs(float(s.get("frame") or 0) - target))


def azimuth_to(cam_loc, target):
    """相机指向目标的平面方位角（度，北 0 顺时针）。"""
    dx = target[0] - cam_loc[0]
    dy = target[1] - cam_loc[1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def angle_diff(a, b):
    d = (a - b + 540.0) % 360.0 - 180.0
    return d


# ------------------------------------------------------------------ 描述生成

def orientation_of(core, dims):
    if not dims:
        return "proxy volume, orientation unresolved"
    dx, dy, dz = dims
    human = core in HUMAN_CORES
    if human:
        if dx > max(dy, dz) * 1.6:
            return "prone body proxy, long axis lying across frame"
        if dz > max(dx, dy) * 1.4:
            return "upright body proxy, head end up"
        return "compact body proxy, crouched volume"
    if dz > max(dx, dy) * 1.4:
        return "vertical volume proxy, long axis standing up"
    if dx > max(dy, dz) * 1.5:
        return "horizontal volume proxy, long axis running across frame"
    if dy > max(dx, dz) * 1.5:
        return "horizontal volume proxy, long axis running into depth"
    return "compact block proxy, near cubic volume"


def motion_state_of(dv):
    if dv is None:
        return "stationary across this interval"
    mag = math.sqrt(sum(c * c for c in dv))
    if mag < 0.012:
        return "stationary across this interval"
    dx, dy, dz = dv
    parts = []
    if abs(dx) > 0.02:
        parts.append("drifting frame right" if dx > 0 else "drifting frame left")
    if abs(dz) > 0.02:
        parts.append("rising" if dz > 0 else "sinking")
    if not parts and abs(dy) > 0.02:
        parts.append("drifting up frame" if dy > 0 else "drifting down frame")
    if not parts:
        parts.append("shifting laterally")
    return ", ".join(parts) + " in this interval"


def spatial_relations_of(core, sample, peers):
    if not peers:
        return "only visible instance in this frame"
    cx = sample["screen_bbox_percent"]["center_x"]
    cy = sample["screen_bbox_percent"]["center_y"]
    depth = sample.get("depth") or 0.0
    left = [p for p in peers if p["screen_bbox_percent"]["center_x"] < cx]
    right = [p for p in peers if p["screen_bbox_percent"]["center_x"] > cx]
    near = [p for p in peers if (p.get("depth") or 0.0) < depth]
    bits = []
    if left:
        p = max(left, key=lambda q: q["screen_bbox_percent"]["center_x"])
        bits.append(f"right of {core_name(p['root_name'])}")
    if right:
        p = min(right, key=lambda q: q["screen_bbox_percent"]["center_x"])
        bits.append(f"left of {core_name(p['root_name'])}")
    bits.append("in front of nearer elements" if near else "behind all nearer elements")
    bits.append("upper frame band" if cy < 40 else
                ("lower frame band" if cy > 62 else "middle frame height"))
    return ", ".join(bits[:4])


def visible_peers(objs, t, exclude_id):
    peers = []
    for oid, other in objs.items():
        if oid == exclude_id:
            continue
        s = pick(other.get("samples") or [], t)
        if s and s.get("projected_visible") and s.get("screen_bbox_percent"):
            peers.append({"root_name": other.get("root_name"), **s})
    return peers


def describe_layout(anchor, objs):
    vis = []
    for tr in anchor["tracked_instances"]:
        if tr["visibility"] != "offscreen":
            vis.append(tr)
    if not vis:
        return "no instance visible in this anchor"
    dom = max(vis, key=lambda t: t["bbox_width_percent"] * t["bbox_height_percent"])
    ordered = sorted(vis, key=lambda t: t["center_x_percent"])

    def core_of(tr):
        obj = objs.get(tr["source_id"])
        return core_name(obj.get("root_name") or "") if obj else "element"

    names = ", ".join(core_of(x) for x in ordered[:5])
    return (f"{len(vis)} visible instances. Dominant {core_of(dom)} "
            f"covers {dom['bbox_width_percent']:.0f}x{dom['bbox_height_percent']:.0f} percent at "
            f"frame {dom['center_x_percent']:.0f}/{dom['center_y_percent']:.0f}. "
            f"Left to right: {names}.")


def describe_depth(anchor, objs):
    rows = []
    for tr in anchor["tracked_instances"]:
        if tr["visibility"] == "offscreen":
            continue
        obj = objs.get(tr["source_id"])
        s = pick(obj.get("samples") or [], anchor["time_seconds"]) if obj else None
        if s and s.get("depth") is not None:
            rows.append((s["depth"], tr))
    if not rows:
        return "single depth layer visible"
    rows.sort(key=lambda r: r[0])

    def core_of(tr):
        obj = objs.get(tr["source_id"])
        return core_name(obj.get("root_name") or "") if obj else "element"

    fore = core_of(rows[0][1])
    back = core_of(rows[-1][1])
    return (f"depth spans {rows[0][0]:.2f}m to {rows[-1][0]:.2f}m across {len(rows)} layers; "
            f"nearest is {fore}, furthest is {back}")


# ------------------------------------------------------------------ 实体

def instance_motion(samples):
    """单实例的运动判定：返回 (位移, 形变量)。多实例必须逐实例算，不能跨实例混算。"""
    vis = [s for s in samples if s.get("projected_visible") and s.get("world_location")]
    if len(vis) < 2:
        return 0.0, 0.0, None, None
    d = dist(vis[0]["world_location"], vis[-1]["world_location"])
    da, db = vis[0].get("world_dimensions"), vis[-1].get("world_dimensions")
    shape = max(abs(a - b) for a, b in zip(da, db)) if da and db else 0.0
    return d, shape, da, db


GROUP_CONSTRAINTS = {
    "CHAR": "keep the source joint envelope and floor contact; the body stays inside the blocked volume",
    "FX": "keep the source volume and the attachment point; the effect never detaches from its source surface",
    "ENV": "all shell geometry keeps the blocked set footprint and clear height",
    "PROP": "each member keeps its own source footprint, size and placement",
}


def group_entities(contract, inv_by_id, animated_cores):
    """按语义/风格重新分组 entity：分组是语义组织，不是删减源实例。

    - 角色逐个成组（运动合同不同，不可合并）
    - 特效逐个成组（形变合同不同）
    - 该镜内发生运动的道具单独成组
    - 其余环境体与道具按场景合并成一组

    分组只依据 source_inventory（唯一真源），不读上一轮写回的 entities，
    因此本函数可重复执行而不会把已合并的组再塌成一个组。
    """
    by_core = {}
    for it in contract["source_inventory"]:
        core = core_name(it["root_name"])
        by_core.setdefault(core, []).append(it["source_id"])

    groups = {}
    for core, ids in by_core.items():
        cls = SEMANTIC.get(core, ("other",))[0]
        scene = inv_by_id[ids[0]]["root_name"].split("_")[0]
        if cls == "articulated":
            key = ("CHAR", core)
        elif cls == "effect":
            key = ("FX", core)
        elif core in animated_cores:
            key = ("PROP", core)
        elif cls == "environment":
            key = ("ENV", scene)
        else:
            key = ("PROP", scene)
        groups.setdefault(key, []).append({"core": core, "cls": cls, "ids": ids, "scene": scene})

    rebuilt = []
    for index, (key, members) in enumerate(groups.items(), start=1):
        ids = []
        for m in members:
            ids.extend(m["ids"])
        kind = key[0]
        if kind in ("CHAR", "FX"):
            group_cls = "articulated" if kind == "CHAR" else "effect"
        elif kind == "ENV":
            group_cls = "environment"
        else:
            group_cls = "rigid"
        rebuilt.append({
            "label": f"Entity {index:02d} {kind} {key[1]}",
            "kind": kind,
            "group_class": group_cls,
            "members": members,
            "source_ids": ids,
        })
    return rebuilt


def fill_entities(contract, objs, subject_core, primary_core=None):
    inv_by_id = {it["source_id"]: it for it in contract["source_inventory"]}

    # 逐实例运动判定，并找出该镜内发生运动的 core（依据 source_inventory，不读上一轮 entities）
    per_core = {}
    for it in contract["source_inventory"]:
        core = core_name(it["root_name"])
        obj = objs.get(it["source_id"])
        if not obj:
            continue
        d, shape, da, db = instance_motion(obj.get("samples") or [])
        cur = per_core.get(core)
        if cur is None:
            per_core[core] = (d, shape, da, db)
        else:
            per_core[core] = (
                max(cur[0], d), max(cur[1], shape), cur[2] or da, cur[3] or db)
    animated_cores = {c for c, v in per_core.items() if v[0] > 0.25 or v[1] > 0.15}
    # 特效类即使位移很小也视为演化（形变合同），单独成组
    for core, v in per_core.items():
        if SEMANTIC.get(core, ("",))[0] == "effect" and v[0] > 0.01:
            animated_cores.add(core)

    rebuilt = group_entities(contract, inv_by_id, animated_cores)

    new_entities = []
    label_by_id = {}
    for item in rebuilt:
        members = item["members"]
        ids = item["source_ids"]
        kind = item["kind"]
        cls = item["group_class"]
        scene = members[0]["scene"]
        roles = []
        for m in members:
            if m["core"] not in roles:
                roles.append(m["core"])
        sem_desc = [SEMANTIC.get(m["core"], ("", m["core"], ""))[1] for m in members]
        if kind == "CHAR":
            role = sem_desc[0] if len(sem_desc) == 1 else (
                f"repeated {sem_desc[0]} blockout, {len(ids)} copies")
        elif kind == "FX":
            role = sem_desc[0] if len(sem_desc) == 1 else (
                f"{sem_desc[0]} set, {len(ids)} pieces")
        elif kind == "ENV":
            role = (f"{scene} built environment shell enclosing the set: " +
                    ", ".join(roles[:6]))
        else:
            role = (f"{scene} set pieces and fittings: " + ", ".join(roles[:8]))
        constraints = GROUP_CONSTRAINTS[kind]

        # 组内运动取最动态成员
        d = 0.0
        shape = 0.0
        da = db = None
        for s in ids:
            obj = objs.get(s)
            if not obj:
                continue
            sd, ss, sda, sdb = instance_motion(obj.get("samples") or [])
            if sd > d:
                d, da, db = sd, sda, sdb
            shape = max(shape, ss)
        multi = len(ids) > 1
        if cls == "articulated":
            mode = "articulation" if shape > 0.15 else ("locomotion" if d > 0.25 else "static")
        elif cls == "effect":
            mode = "effect_evolution" if (d > 0.05 or shape > 0.05) else "static"
        elif cls in ("rigid", "environment"):
            mode = "rigid_travel" if d > 0.25 else "static"
        else:
            mode = "static"

        if mode == "articulation":
            if da and db and da[0] > da[2] and db[2] > db[0]:
                action = "rises from a prone posture to an upright posture"
            elif da and db and db[2] < da[2]:
                action = "lowers from a standing posture into a crouch or kneel"
            else:
                action = "changes body pose while keeping floor contact"
        elif mode == "locomotion":
            action = f"travels {d:.2f}m across the set during the shot"
        elif mode == "rigid_travel":
            action = f"translates {d:.2f}m across the set without changing form"
        elif mode == "effect_evolution":
            action = "develops and drifts as the effect unfolds"
        else:
            action = "holds its source position for the whole shot"

        if multi:
            cont = "keep every instance and the column order exactly as in the source"
            forbid = "do not merge, split, drop or reorder the instances"
        else:
            cont = "stay inside the source blockout bounds for the full shot"
            forbid = "do not replace, duplicate or remove this instance"

        ent = {
            "label": item["label"],
            "entity_class": cls,
            "importance": "context",
            "source_instance_ids": ids,
            "instance_count": len(ids),
            "conservation_rule": "one_to_one_no_merge_split_delete_or_replace",
            "source_role": role,
            "structural_constraints": constraints,
            "motion_contract": {
                "mode": mode,
                "action": action,
                "continuity_requirement": cont,
                "forbidden_substitutions": forbid,
            },
        }
        new_entities.append(ent)
        for s in ids:
            label_by_id[s] = item["label"]

    # primary：取单实例 entity，避免整个群体进入 anchor 明细段
    primary_done = False
    wanted = primary_core or subject_core
    for ent in new_entities:
        if ent["source_instance_ids"]:
            c = core_name(inv_by_id[ent["source_instance_ids"][0]]["root_name"])
            if c == wanted and ent["instance_count"] == 1:
                ent["importance"] = "primary"
                primary_done = True
                break
    if not primary_done:
        for ent in new_entities:
            if ent["instance_count"] == 1:
                ent["importance"] = "primary"
                primary_done = True
                break
    if not primary_done and new_entities:
        new_entities[0]["importance"] = "primary"

    contract["entities"] = new_entities
    return label_by_id


# ------------------------------------------------------------------ 镜头

def subject_area_trend(contract, objs, subject_core):
    areas = []
    for anchor in contract["anchors"]:
        best = 0.0
        for tr in anchor["tracked_instances"]:
            if tr["visibility"] == "offscreen":
                continue
            obj = objs.get(tr["source_id"])
            if not obj:
                continue
            if core_name(obj.get("root_name") or "") != subject_core:
                continue
            best = max(best, tr["bbox_width_percent"] * tr["bbox_height_percent"])
        areas.append(best)
    if len(areas) < 2 or areas[0] <= 0:
        return "stable"
    ratio = areas[-1] / areas[0]
    if ratio > 1.12:
        return "decrease"
    if ratio < 0.89:
        return "increase"
    return "stable"


def fill_shot(contract, ev, objs, d11shot, subject_core, label_by_id):
    shot = contract["shots"][0]
    cams = ev.get("camera_samples") or []
    motion_type = MOTION_TYPE.get(d11shot["movement"], "static")
    shot["camera_contract"]["motion_type"] = motion_type

    target_label = "none"
    for it in contract["source_inventory"]:
        if core_name(it["root_name"]) == subject_core:
            target_label = label_by_id.get(it["source_id"], "none")
            break
    shot["camera_contract"]["tracked_target_entity"] = target_label

    c0, cN = (cams[0] if cams else None), (cams[-1] if cams else None)
    if c0 and cN:
        p0, pN = c0["location"], cN["location"]
        moved = dist(p0, pN)
        shot["camera_contract"]["world_path"] = (
            f"camera travels from {fmt(p0)} to {fmt(pN)} on a {d11shot['lens_mm']}mm lens, "
            f"total path length {moved:.2f}m inside the blocked set")
        shot["camera_contract"]["target_distance_trend"] = subject_area_trend(
            contract, objs, subject_core)
        if moved < 0.05:
            shot["camera_contract"]["azimuth_trend"] = "stable"
            shot["camera_contract"]["elevation_trend"] = "stable"
        else:
            az = []
            for cam in cams:
                subj = None
                for tr in contract["anchors"][0]["tracked_instances"]:
                    obj = objs.get(tr["source_id"])
                    if obj and core_name(obj.get("root_name") or "") == subject_core:
                        s = pick(obj.get("samples") or [], 0.0)
                        subj = s.get("world_location") if s else None
                        break
                if subj:
                    a = azimuth_to(cam["location"], subj)
                    if a is not None:
                        az.append(a)
            if len(az) >= 2:
                delta = angle_diff(az[-1], az[0])
                shot["camera_contract"]["azimuth_trend"] = (
                    "clockwise" if delta > 1.5 else
                    ("counterclockwise" if delta < -1.5 else "stable"))
            else:
                shot["camera_contract"]["azimuth_trend"] = "variable"
            dz = pN[2] - p0[2]
            shot["camera_contract"]["elevation_trend"] = (
                "increase" if dz > 0.05 else ("decrease" if dz < -0.05 else "stable"))
    shot["camera_contract"]["focal_length_trend"] = "stable"
    shot["camera_contract"]["screen_composition_rule"] = (
        f"{d11shot['shot_size']} framing in 9:16 vertical, subject held in the frame centre band "
        f"with head room above, foreground occlusion kept under one third of frame, "
        f"and the AI badge corner left clear of the subject")
    forbidden = FORBIDDEN_MOTION.get(motion_type, "do not change the source camera path")
    shot["camera_contract"]["forbidden_reinterpretations"] = (
        f"{forbidden}; keep the {d11shot['shot_size']} framing and the {d11shot['movement']} "
        f"move exactly as blocked out")
    shot["actions"] = SHOT_DATA[int(d11shot["global_shot_no"])][2]
    shot["layout_and_occlusion"] = describe_layout(contract["anchors"][0], objs)
    shot["lighting_spatial_logic"] = STYLE_BIBLE["lighting_and_atmosphere"]


# ------------------------------------------------------------------ 锚点

def fill_anchors(contract, ev, objs, d11shot):
    cams = ev.get("camera_samples") or []
    for anchor in contract["anchors"]:
        t = anchor["time_seconds"]
        cam = pick(cams, t)
        for tr in anchor["tracked_instances"]:
            obj = objs.get(tr["source_id"])
            sample = pick(obj.get("samples") or [], t) if obj else None
            if not sample or not sample.get("projected_visible"):
                tr["visibility"] = "offscreen"
                for k in ("center_x_percent", "center_y_percent",
                          "bbox_width_percent", "bbox_height_percent"):
                    tr[k] = None
                tr["orientation"] = "off screen at this anchor"
                tr["motion_state"] = "offscreen at this anchor"
                tr["spatial_relations"] = "leaves the frame before this anchor"
                continue
            # ★ 退化投影兜底（边看边对象）：
            #   插件把「包围盒与画幅相交」记为 visible，但对**侧看成一条线**的对象
            #   （0.04m 厚的旗布、掠射角下的地坪），投影包围盒在某一轴上的厚度恒为 0
            #   ⇒ 打破合同 schema 的不变量「visible 时 bbox 宽高必须 > 0」
            #   （实测 U03 ep19_shot02「旗布高 0.0」/ ep21_shot02「地坪宽 0.0」
            #     ⇒ check-contract 与 build-prompt 双双失败，整镜无法进 D14）。
            #   这里把 0 抬到**最小可见值 0.01**：对象确实在画幅内，只是侧看成线，
            #   合同必须如实记「几乎不可见」而不是「不在画内」。
            for _k in ("bbox_width_percent", "bbox_height_percent"):
                _v = tr.get(_k)
                if isinstance(_v, (int, float)) and _v <= 0:
                    tr[_k] = 0.01
            core = core_name(obj.get("root_name") or "")
            tr["orientation"] = orientation_of(core, sample.get("world_dimensions"))
            nxt = pick(obj.get("samples") or [], t + 0.5)
            dv = None
            if nxt and sample.get("world_location") and nxt.get("world_location"):
                dv = tuple(b - a for a, b in zip(sample["world_location"], nxt["world_location"]))
            tr["motion_state"] = motion_state_of(dv)
            tr["spatial_relations"] = spatial_relations_of(
                core, sample, visible_peers(objs, t, tr["source_id"]))
        anchor["composition"]["shot_scale"] = SHOT_SCALE.get(d11shot["shot_size"], "medium")
        anchor["composition"]["frame_balance_and_depth"] = describe_depth(anchor, objs)
        if cam:
            anchor["camera_relation"] = (
                f"camera at {fmt(cam['location'])} on a {cam.get('lens_mm')}mm lens, "
                f"frame {cam.get('frame')} of {cams[-1].get('frame')}")
        else:
            anchor["camera_relation"] = "camera pose not sampled at this anchor"
        anchor["key_layout_and_occlusion"] = describe_layout(anchor, objs)


# ------------------------------------------------------------------ 交互

def fill_interactions(contract, gsn):
    inv_by_id = {it["source_id"]: it for it in contract["source_inventory"]}
    by_core = {}
    for it in contract["source_inventory"]:
        by_core.setdefault(core_name(it["root_name"]), []).append(it["source_id"])
    rows = []
    for iid, cores, start, end, relation, forbidden in INTERACTIONS.get(gsn, []):
        ids = []
        for c in cores:
            ids.extend(by_core.get(c, []))
        if not ids:
            continue
        rows.append({
            "interaction_id": iid,
            "source_instance_ids": sorted(set(ids)),
            "start_seconds": start,
            "end_seconds": end,
            "relation": relation,
            "forbidden_change": forbidden,
        })
    contract["interaction_contracts"] = rows


# ------------------------------------------------------------------ 外观

def fill_appearance(appearance, contract, gsn, d11shot):
    appearance["watched_references"] = True
    appearance["style_source_summary"] = (
        "World style is taken from the shared unit style contract: cold industrial post-collapse "
        "realism for humans and props with a separated stylisation layer for bone pattern, twin flame, "
        "grey fog and altered bodies. No external appearance reference image was supplied for this unit, "
        "so no reference route is registered and every entity is styled from the world style alone.")
    appearance["reference_routes"] = []
    appearance["global_style_bible"] = dict(STYLE_BIBLE)
    mapping = {}
    for ent in contract["entities"]:
        label = ent["label"]
        core = core_name(label.split(" ", 2)[-1])
        role, cls = ent["source_role"], ent["entity_class"]
        if cls == "articulated":
            finish = ("real skin with pores and fine hair, fabric with real drape and wear, "
                      "matte metal fittings, contact shadow under the body")
        elif cls == "effect":
            finish = ("stylised energy surface in the two permitted flame colours, or grey-white "
                      "ceramic shell for altered bodies, never wet gore")
        elif cls == "environment":
            finish = ("worn cement, oxidised steel and sheet metal with cold grey reflections, "
                      "shadow detail kept readable in the dark areas")
        else:
            finish = ("utilitarian material with visible weight, thickness and use marks, "
                      "cold grey metal and dull plastic, no gloss hero finish")
        mapping[label] = {
            "semantic_target": role,
            "final_materials_and_detail": finish,
            "style_route": "world_style_unit_contract",
            "source_visual_policy": "spatiotemporal_evidence_only",
            "silhouette_policy": "stay_within_source_bounds_and_articulation_envelope",
            "source_unsupported_additions": [],
        }
    appearance["entity_appearances"] = mapping
    appearance["sound"] = SOUND[int(d11shot["global_shot_no"])]


# ------------------------------------------------------------------ 主流程

def process(shot_dir: Path, gsn: int):
    manifest = load(shot_dir / "manifest.json")
    contract = load(shot_dir / "render_contract.json")
    appearance = load(shot_dir / "appearance.json")
    ev = manifest["structure_evidence"]
    objs = {o["source_id"]: o for o in ev.get("objects", [])}
    d11shot = D11_SHOTS[gsn]
    subject_core = SHOT_DATA[gsn][1]

    contract["watched_full_source"] = True
    label_by_id = fill_entities(contract, objs, subject_core,
                                PRIMARY_PICK.get(gsn, subject_core))
    for anchor in contract["anchors"]:
        for tr in anchor["tracked_instances"]:
            tr["entity_label"] = label_by_id.get(tr["source_id"], tr["entity_label"])
    fill_shot(contract, ev, objs, d11shot, subject_core, label_by_id)
    fill_anchors(contract, ev, objs, d11shot)
    fill_interactions(contract, gsn)
    fill_appearance(appearance, contract, gsn, d11shot)
    write(shot_dir / "render_contract.json", contract)
    write(shot_dir / "appearance.json", appearance)
    return len(contract["source_inventory"]), len(contract["entities"]), len(contract["anchors"])


def main():
    total = 0
    for gsn in sorted(D11_SHOTS):
        ep = D11_SHOTS[gsn]["ep"]
        sid = D11_SHOTS[gsn]["shot_id"]
        d = WORK / f"ep{ep:02d}_shot{sid:02d}"
        if not (d / "render_contract.json").is_file():
            print(f"  [SKIP] g{gsn:02d} missing contract")
            continue
        inv, ent, anc = process(d, gsn)
        total += 1
        print(f"  [OK] g{gsn:02d} inv={inv} entities={ent} anchors={anc}", flush=True)
    print(f"[fill] done, shots={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
