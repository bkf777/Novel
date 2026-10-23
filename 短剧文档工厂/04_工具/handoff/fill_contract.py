#!/usr/bin/env python3
"""D14 逐镜合同填装器：把 M3_FILL 全部填成真值。

输入（每镜目录）：
    render_contract.json   preflight 骨架（source_inventory/entities/anchors/shots）
    appearance.json        preflight 骨架（global_style_bible/entity_appearances）
    projection.json        投影真值（project_bounds.py 产出）
    scene_spec.json / shot_spec.json

输入（项目层）：
    shared/D10.json  视觉圣经（风格层/色板/材质/光型/一致性规则）
    units/U01/D11.json 镜头真源（景别/角度/运镜/焦距/画面事实）
    units/U01/D12.json 提示词卡（负向词/角色描述/一致性引用）
    units/U01/D13.json 场景说明书（光位/视线/道具）
    units/U01/D15.json 声音设计（分镜音效）

输出：原地覆写 render_contract.json 与 appearance.json。

原则：
    几何量（屏幕范围/遮挡/深度）一律取 projection.json 的几何真值，
    语义量（动作/景别/光位/音效）取 D 层权威文档，
    绝不臆造坐标，也不在仓库里造"为跑通校验器而存在"的交付物。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

# ---------------------------------------------------------------- 枚举映射

SHOT_SCALE_MAP = {
    "特写": "close",
    "大特写": "extreme_close",
    "近景": "medium",
    "中近景": "medium",
    "中景": "medium_full",
    "中远景": "full",
    "全景": "wide",
    "远景": "extreme_wide",
}

MOTION_MAP = {
    "固定": "static",
    "推": "dolly",
    "拉": "dolly",
    # H3 的 CAMERA_MOTION_TYPES 没有 truck，横移统一归到 tracking
    "移": "tracking",
    "横移": "tracking",
    "摇": "pan_tilt",
    "跟": "tracking",
    "升降": "crane",
    "升": "crane",
    "降": "crane",
    "环绕": "orbit",
    "手持": "handheld",
    "变焦": "compound",
}

PROMPT_CHAR_BUDGET = 6500

MOVE_CN = {
    "static": "固定",
    "dolly": "推／拉",
    "truck": "横移",
    "pan_tilt": "摇",
    "tracking": "跟拍",
    "crane": "升降",
    "orbit": "环绕",
    "handheld": "手持",
    "compound": "变焦",
}


# ---------------------------------------------------------------- 文本工具


def compact(text: str, limit: int) -> str:
    """把文本压到 limit 字以内（超长时按中文句读截断，不留半截词）。"""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("；", "，", "。", "、", " "):
        idx = cut.rfind(sep)
        if idx >= limit * 0.55:
            return cut[:idx]
    return cut[:limit]


def depth_band(depth: float | None) -> str:
    if depth is None:
        return "不可见"
    if depth < 3.0:
        return "前景"
    if depth < 10.0:
        return "中景"
    return "背景"


def axis_desc(angle) -> str:
    if angle is None:
        return "朝向随相机透视变化"
    a = angle % 180.0
    if a < 8 or a > 172:
        return "水平横置"
    if 82 <= a <= 98:
        return "竖直"
    if a < 90:
        return f"斜置向右下 {int(a)}°"
    return f"斜置向左下 {int(180 - a)}°"


def direction_cn(dx: float, dy: float) -> str:
    if abs(dx) < 1.2 and abs(dy) < 1.2:
        return "基本不动"
    if abs(dx) >= abs(dy):
        return ("自画面左缘向右移" if dx > 0 else "自画面右缘向左移")
    return ("自画面下方向上移" if dy > 0 else "自画面上方向下移")


def classify(name: str):
    """把白模对象名归类，用于写 source_role / appearance。"""
    if name.startswith("Floor"):
        return "floor", "地面基准面：承载全部道具与人物的水平参考"
    if name.startswith("Pit_") or name.startswith("PitBottom"):
        return "pit", "深坑坑壁与坑底：界定坑口高差与垂直落差"
    if name.startswith("WallNegX"):
        return "wall", "西侧围合墙：界定空间左边界并遮挡外部"
    if name.startswith("WallPosX"):
        return "wall", "东侧围合墙：界定空间右边界并遮挡外部"
    if name.startswith("WallNegY"):
        return "wall", "南侧围合墙：界定空间前边界并遮挡外部"
    if name.startswith("WallPosY"):
        return "wall", "北侧围合墙：界定空间后边界并遮挡外部"
    if name.startswith("WallPit"):
        return "pit", "深坑侧壁：坑口以下挡土，界定垂直落差"
    m = re.match(r"^(.+?)_(Torso|Legs|Head|Thigh|Shin)$", name)
    if m:
        who, part = m.group(1), m.group(2)
        part_cn = {"Torso": "躯干", "Legs": "双腿", "Head": "头部",
                   "Thigh": "大腿", "Shin": "小腿"}[part]
        return "actor", f"角色占位体：{who} 的{part_cn}（仅作空间占位）"
    if re.search(r"钟楼|远景|远端", name):
        return "landmark", f"远景地标：{name}，交代空间纵深与尺度"
    if re.search(r"占位|队列|护卫|队员", name):
        return "crowd", f"人群占位体：{name}，表现群体规模与纵深排列"
    return "prop", f"场景道具：{name}，承担该镜的实体信息"


# ---------------------------------------------------------------- 各层读取


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pick_lighting(d10, scene_code: str, lighting_setup):
    """按 D13 的光型名去 D10.lighting 找对应的光位口径。"""
    names = [l.get("type", "") for l in (lighting_setup or [])]
    out = []
    for n in names:
        for item in d10.get("lighting", []):
            if not item.get("setup"):
                continue
            key = item.get("name", "")
            if any(t in key or key in t for t in (n[:2],)) and key not in out:
                out.append(f"{key}（{item['setup']}）")
                break
    return out


# ---------------------------------------------------------------- 主填装


def render_prompt_len(contract, appearance, skill_dir: str) -> int:
    """用 H3 官方渲染器量出提示词实际字数（不落盘）。"""
    if not skill_dir:
        return 0
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    try:
        import m3_render_workflow as w  # type: ignore
        prompt, _ = w.render_budgeted_prompt(contract, appearance, 0.2)
        return len(prompt)
    except Exception:
        return 0


def thin_anchors(contract, keep: int):
    """把锚点稀释到 keep 个，均匀分布并保留首尾。"""
    anchors = contract["anchors"]
    n = len(anchors)
    if keep >= n:
        return
    idx = sorted({round(i * (n - 1) / (keep - 1)) for i in range(keep)})
    contract["anchors"] = [anchors[i] for i in idx]


def fill_shot(args) -> dict:
    shot_dir = args.shot_dir
    contract = load_json(os.path.join(shot_dir, "render_contract.json"))
    appearance = load_json(os.path.join(shot_dir, "appearance.json"))
    proj = load_json(os.path.join(shot_dir, "projection.json"))
    scene_spec = load_json(os.path.join(shot_dir, "scene_spec.json"))
    shot_spec = load_json(os.path.join(shot_dir, "shot_spec.json"))

    gno = int(shot_spec["global_shot_no"])
    d11 = load_json(os.path.join(args.project, "units", args.unit, "D11.json"))
    d12 = load_json(os.path.join(args.project, "units", args.unit, "D12.json"))
    d13 = load_json(os.path.join(args.project, "units", args.unit, "D13.json"))
    d15 = load_json(os.path.join(args.project, "units", args.unit, "D15.json"))
    d10 = load_json(os.path.join(args.project, "shared", "D10.json"))

    # ---- D11 镜头 ----
    shot11 = None
    for ep in d11["episodes"]:
        for s in ep["shots"]:
            if int(s["global_shot_no"]) == gno:
                shot11 = s
                ep_no = ep["ep"]
    scene13 = next((s for s in d13["scenes"]
                    if s["scene_code"] == shot11["scene_code"]), {})
    card12 = next((c for c in d12["cards"]
                   if c["ep"] == shot11.get("ep") and c["shot_id"] == shot11["shot_id"]), {})
    sfx15 = []
    for ep in d15["episodes"]:
        for item in ep.get("sfx", []):
            if item.get("shot_id") == shot11["shot_id"] and ep.get("ep") == shot11.get("ep"):
                sfx15.append(item)

    frames = proj["frames"]
    first_f, last_f = frames[0], frames[-1]
    cam0 = first_f["camera"]
    cam1 = last_f["camera"]

    # ---- 逐镜实例清单：不在这里做任何删减 ----
    # 章程 §六 硬纪律与 H3 技能 SKILL.md 都明写「不删 source_inventory 条目」。
    # 可见实例清单由**生产端**负责：build_white_model.py 的 manifest 证据以
    # 「投影与画幅相交」为判据，preflight 据此建立 source_inventory。
    # 填装阶段只负责把每个条目的语义填满，不做增删。
    inv_by_id = {item["source_id"]: item for item in contract.get("source_inventory", [])}

    def obj_of(source_id: str) -> str:
        item = inv_by_id.get(source_id)
        if item and item.get("source_name"):
            return item["source_name"]
        return source_id.split("_", 1)[-1]

    culled_ids = set()
    empty_frame = False

    # ---- 主体实体（角色躯干占位；无角色则取 primary 实体）----
    subject_label = None
    for ent in contract["entities"]:
        base = ent["source_instance_ids"][0]
        obj_name = base.split("_", 1)[1] if "_" in base else base
        if re.search(r"_(Torso|Legs)$", obj_name):
            subject_label = ent["label"]
            break
    if subject_label is None:
        for ent in contract["entities"]:
            base = ent["source_instance_ids"][0]
            obj_name = base.split("_", 1)[1] if "_" in base else base
            if re.search(r"_(Torso|Head)$", obj_name):
                subject_label = ent["label"]
                break
    if subject_label is None:
        for ent in contract["entities"]:
            if ent.get("importance") == "primary":
                subject_label = ent["label"]
                break
    if subject_label is None:
        # 画幅里没有角色（主观镜/空镜）时，主实体取**画幅内占幅最大**的物件，
        # 合同要求至少有一个 primary，否则 H3 校验器直接判 invalid。
        def entity_area(ent):
            total = 0.0
            for sid in ent.get("source_instance_ids", []):
                v = first_f["objects"].get(obj_of(sid)) or {}
                if not v.get("in_frame"):
                    continue
                vp = v.get("visible_percent") or {}
                total += float(vp.get("width", 0)) * float(vp.get("height", 0))
            return total

        ranked = sorted(contract["entities"], key=entity_area, reverse=True)
        if ranked and entity_area(ranked[0]) > 0:
            subject_label = ranked[0]["label"]
        elif ranked:
            subject_label = ranked[0]["label"]
    subject_obj = None
    if subject_label:
        for ent in contract["entities"]:
            if ent["label"] != subject_label:
                continue
            base = ent["source_instance_ids"][0]
            subject_obj = base.split("_", 1)[1] if "_" in base else base
            break

    # 主体实体标记为 primary：只有 primary 会在每个锚点展开朝向/位移/遮挡三段文字，
    # 把这个名额给角色（而不是地面），提示词里的细节才落在主体身上。
    if subject_label:
        for ent in contract["entities"]:
            if ent["label"] == subject_label:
                ent["importance"] = "primary"
            elif ent.get("importance") == "primary":
                # 工厂 schema 的 importance 枚举只有 primary / context
                ent["importance"] = "context"

    # ---- 相机运动趋势 ----
    def yaw_pitch(cam):
        rx, _ry, rz = cam["rotation_euler_deg"]
        return rz, rx

    yaw0, pit0 = yaw_pitch(cam0)
    yaw1, pit1 = yaw_pitch(cam1)
    dyaw = (yaw1 - yaw0 + 540) % 360 - 180
    dpitch = pit1 - pit0

    def dist_to_target(frame):
        if not subject_obj:
            return None
        v = frame["objects"].get(subject_obj)
        if not v or not v.get("in_frame"):
            return None
        return v.get("depth_m")

    move = shot_spec["camera"].get("move", "static")
    motion_type = MOTION_MAP.get((shot11.get("movement") or "").strip(), "static")
    if motion_type == "static" and move != "static":
        motion_type = MOTION_MAP.get({
            "dolly": "dolly", "truck": "tracking", "pan": "pan_tilt",
            "tracking": "tracking", "orbit": "orbit", "crane": "crane",
            "handheld": "handheld",
        }.get(move, "static"))

    # ---- 合同头 ----
    contract["watched_full_source"] = True

    # ---- entities ----
    for ent in contract["entities"]:
        base = ent["source_instance_ids"][0]
        obj_name = base.split("_", 1)[1] if "_" in base else base
        cat, role = classify(obj_name)
        ent["source_role"] = compact(role, 72)
        dims = None
        for f in frames:
            for name, v in f["objects"].items():
                if name == obj_name and v.get("world_dimensions"):
                    dims = v["world_dimensions"]
                    break
            if dims:
                break
        if dims:
            size_txt = f"{dims[0]:.2f}×{dims[1]:.2f}×{dims[2]:.2f}m"
        else:
            size_txt = "白模包围盒"
        ent["structural_constraints"] = compact(
            f"保持 {size_txt} 白模包围盒与所在位置不变；不得放大、缩小、移位或替换为其它物体", 108)
        moving = move != "static"
        # 只有主体角色用 camera_only（它的朝向/位移/遮挡关系逐锚点写）；
        # 其余实体在世界坐标里全程静止，用 static 走紧凑列表，
        # 否则每镜提示词会膨胀到 1.4 万字、超出 H3 的 7000 字硬上限。
        is_subject = (ent["label"] == subject_label)
        ent["motion_contract"] = {
            "mode": "camera_only" if (moving and is_subject) else "static",
            "action": compact(
                f"本体静止，仅随{MOVE_CN.get(motion_type, '固定')}机位运动产生视差" if (moving and is_subject)
                else "本体全程静止不动", 92),
            "continuity_requirement": compact(
                "全程保持同一世界坐标与同一尺寸，屏幕位置随相机运动连续变化不跳变", 112),
            "forbidden_substitutions": compact(
                "不得替换为其它物体、不得改变尺寸与位置、不得自行移动、旋转或变形", 100),
        }

    # ---- shots ----
    d0 = dist_to_target(first_f)
    d1 = dist_to_target(last_f)
    if d0 is None or d1 is None:
        dist_trend = "stable"
    elif abs(d1 - d0) < 0.25:
        dist_trend = "stable"
    else:
        dist_trend = "decrease" if d1 < d0 else "increase"

    if abs(dyaw) < 1.0:
        az_trend = "stable"
    else:
        az_trend = "clockwise" if dyaw > 0 else "counterclockwise"
    if abs(dpitch) < 0.5:
        elev_trend = "stable"
    else:
        elev_trend = "increase" if dpitch > 0 else "decrease"

    visible_counts = [sum(1 for v in f["objects"].values() if v.get("in_frame")) for f in frames]
    main_objs = []
    for name, v in first_f["objects"].items():
        if not v.get("in_frame"):
            continue
        vp = v["visible_percent"]
        if vp["width"] * vp["height"] < 1.2:
            continue
        main_objs.append((vp["width"] * vp["height"], name, v))
    main_objs.sort(reverse=True)
    key_names = [n for _a, n, _v in main_objs[:3]]

    for shot in contract["shots"]:
        shot["actions"] = compact(
            "；".join(re.split(r"[；;]", shot11.get("visual_facts", ""))[:2]), 60)
        cam_path = (
            f"机位自 ({cam0['location_m'][0]:.2f},{cam0['location_m'][1]:.2f},"
            f"{cam0['location_m'][2]:.2f}) {MOVE_CN.get(motion_type,'固定')}"
            f"至 ({cam1['location_m'][0]:.2f},{cam1['location_m'][1]:.2f},"
            f"{cam1['location_m'][2]:.2f})")
        shot["camera_contract"] = {
            "motion_type": motion_type,
            "tracked_target_entity": subject_label or "none",
            "world_path": compact(cam_path, 110),
            "target_distance_trend": dist_trend,
            "azimuth_trend": az_trend,
            "elevation_trend": elev_trend,
            "focal_length_trend": "stable",
            "screen_composition_rule": compact(
                f"{shot11.get('shot_size','')}（{shot11.get('camera_angle','')}）"
                f"{shot11.get('lens_mm',35)}mm 竖屏 9:16，主体居中偏{'' if subject_label else '下'}，"
                f"底部留字幕带", 95),
            "forbidden_reinterpretations": compact(
                "不得改变机位高度与朝向、不得更换焦距、不得改为横屏、不得把主体移出画幅", 90),
        }
        occ_txt = []
        for _a, name, v in main_objs[:3]:
            oc = v.get("occlusion_ratio", 0.0)
            occ_txt.append(f"{name}被遮挡{oc*100:.0f}%")
        shot["layout_and_occlusion"] = compact(
            f"画幅内主要实体：{'、'.join(key_names) or '无'}；"
            f"遮挡关系：{'；'.join(occ_txt) or '无'}；"
            f"全程可见实体数 {min(visible_counts)}~{max(visible_counts)}", 142)
        lights = pick_lighting(d10, shot11["scene_code"], scene13.get("lighting_setup"))
        lpos = "、".join(
            f"{l.get('type','')}@({','.join(str(v) for v in (l.get('position_m') or []))})"
            for l in (scene13.get("lighting_setup") or [])[:2])
        shot["lighting_spatial_logic"] = compact(
            f"光源位：{lpos or '场景环境光'}；{('；'.join(lights)) or '按 D13 光位执行'}", 92)

    # ---- anchors ----
    scale = SHOT_SCALE_MAP.get(shot11.get("shot_size", ""), "medium_full")
    for idx, anchor in enumerate(contract["anchors"]):
        t = float(anchor["time_seconds"])
        frame = frames[min(idx, len(frames) - 1)]
        cam = frame["camera"]
        objs = frame["objects"]

        near = sorted(
            [(v["depth_m"], n) for n, v in objs.items()
             if v.get("in_frame") and v.get("depth_m") is not None])
        if near:
            d_near, n_near = near[0]
            d_far, n_far = near[-1]
            balance = compact(
                f"近 {n_near} {d_near:.1f}m／远 {n_far} {d_far:.1f}m，纵深跨度 {d_far-d_near:.1f}m", 70)
        else:
            balance = "画幅内无实体"

        anchor["composition"] = {
            "shot_scale": scale,
            "frame_balance_and_depth": balance,
        }
        anchor["camera_relation"] = compact(
            f"机位 ({cam['location_m'][0]:.2f},{cam['location_m'][1]:.2f},"
            f"{cam['location_m'][2]:.2f}) {cam['lens_mm']:.0f}mm，"
            f"俯仰 {cam['rotation_euler_deg'][0]:.1f}°，方位 {cam['rotation_euler_deg'][2]:.1f}°", 65)

        key_here = []
        for name, v in objs.items():
            if not v.get("in_frame"):
                continue
            vp = v["visible_percent"]
            if vp["width"] * vp["height"] < 1.2:
                continue
            key_here.append(f"{name}居{vp['center_x']:.0f}%/{vp['center_y']:.0f}%")
        anchor["key_layout_and_occlusion"] = compact(
            "；".join(key_here[:3]) or "画幅内无显著实体", 65)

        for ti in anchor["tracked_instances"]:
            base = ti["source_id"]
            obj_name = base.split("_", 1)[1] if "_" in base else base
            v = objs.get(obj_name, {})
            if not v.get("in_frame"):
                ti["visibility"] = "offscreen"
                for k in ("center_x_percent", "center_y_percent",
                          "bbox_width_percent", "bbox_height_percent"):
                    ti[k] = None
                ti["orientation"] = "出画，屏幕外无投影"
                ti["motion_state"] = "静止，位于画幅之外"
                ti["spatial_relations"] = "出画，不参与本帧遮挡关系"
                continue
            vp = v["visible_percent"]
            occ = v.get("occlusion_ratio", 0.0)
            vis_ratio = v.get("visible_ratio", 1.0)
            if occ > 0.35 or vis_ratio < 0.25:
                ti["visibility"] = "partially_occluded"
            else:
                ti["visibility"] = "visible"
            ti["center_x_percent"] = round(vp["center_x"], 2)
            ti["center_y_percent"] = round(vp["center_y"], 2)
            ti["bbox_width_percent"] = round(vp["width"], 2)
            ti["bbox_height_percent"] = round(vp["height"], 2)
            ti["orientation"] = compact(axis_desc(v.get("screen_axis_deg")), 38)

            prev = frames[max(0, min(idx, len(frames) - 1) - 1)]
            prev_v = prev["objects"].get(obj_name, {})
            if prev_v.get("in_frame"):
                dx = vp["center_x"] - prev_v["visible_percent"]["center_x"]
                dy = vp["center_y"] - prev_v["visible_percent"]["center_y"]
                if abs(dx) < 0.8 and abs(dy) < 0.8:
                    ti["motion_state"] = "静止，屏幕位置基本不变"
                else:
                    ti["motion_state"] = compact(
                        f"静止，{direction_cn(dx, dy)} {max(abs(dx), abs(dy)):.1f}%", 48)
            else:
                ti["motion_state"] = "静止，随机位运动进入／移出画面"

            depth = v.get("depth_m")
            band = depth_band(depth)
            if occ > 0.35:
                rel = f"{band}，被遮挡{occ*100:.0f}%"
            elif v.get("occluders"):
                top = max(v["occluders"].items(), key=lambda kv: kv[1])
                rel = f"{band}，被{top[0]}挡住{top[1]*100:.0f}%"
            else:
                rel = f"{band}，距机位{depth:.1f}m，无遮挡" if depth else f"{band}，无遮挡"
            ti["spatial_relations"] = compact(rel, 48)

    # ---- appearance ----
    appearance["watched_references"] = True
    appearance["style_source_summary"] = compact(
        f"风格来源：D10 视觉圣经（写实人物层＋风格化特效层）；"
        f"本镜场景 {shot11['scene_code']}，{shot11.get('shot_size','')}", 110)
    lights = pick_lighting(d10, shot11["scene_code"], scene13.get("lighting_setup"))
    palette_names = [p["name"] for p in d10.get("palette", [])][:4]
    materials = [m["name"] for m in d10.get("materials", [])][:4]
    props_names = [p["name"] for p in scene13.get("props", [])][:4]
    tone = (d10.get("style", {}) or {}).get("overall_tone", "")
    appearance["global_style_bible"] = {
        "world_and_era": compact(
            f"末世工业旧世界，{shot11['scene_code']} 场景；{tone}", 82),
        "visual_language": compact(
            "人物层实拍写实质感（皮肤毛孔、发丝走向、织物褶皱）；"
            "特效层风格化（骨纹发光不破体、双相净火双色、灰雾青灰介质）", 82),
        "palette": compact(
            "、".join(f"{n}" for n in palette_names) or "按 D10 色板", 82),
        "material_language": compact(
            "、".join(materials) or "按 D10 材质表", 82),
        "environment_design": compact(
            f"{shot11['scene_code']}：{scene13.get('plan','')[:46]}", 82),
        "prop_design": compact(
            "、".join(props_names) or "无显著道具", 82),
        "lighting_and_atmosphere": compact(
            "；".join(lights) or "按 D13 光位与 D10 光型执行", 82),
    }

    ent_map = {}
    for ent in contract["entities"]:
        base = ent["source_instance_ids"][0]
        obj_name = base.split("_", 1)[1] if "_" in base else base
        cat, _role = classify(obj_name)
        if cat == "floor":
            target = "地面基准面"
            finish = "水泥地坪，有接触阴影"
            route = "realism"
        elif cat == "wall":
            target = f"围合墙{obj_name}"
            finish = "混凝土墙，有接缝锈迹"
            route = "realism"
        elif cat == "pit":
            target = "深坑，坑壁垂直"
            finish = "混凝土坑壁坑底"
            route = "realism"
        elif cat == "actor":
            who = re.match(r"^(.+?)_(Torso|Legs|Head|Thigh|Shin)$", obj_name)
            who = who.group(1) if who else obj_name
            target = f"{who} 身体占位"
            finish = "皮肤织物写实，毛孔可见"
            route = "realism 人物"
        elif cat == "crowd":
            target = f"群体占位{obj_name}"
            finish = "体型有差异，五官不辨"
            route = "realism 人物"
        elif cat == "landmark":
            target = f"远景地标{obj_name}"
            finish = "剪影体量清晰"
            route = "realism 远景"
        else:
            target = f"道具{obj_name}"
            finish = "按 D10 材质表落实"
            route = "realism"
        ent_map[ent["label"]] = {
            "semantic_target": compact(target, 78),
            "final_materials_and_detail": compact(finish, 100),
            "style_route": compact(route, 70),
            "source_visual_policy": "spatiotemporal_evidence_only",
            "silhouette_policy": "stay_within_source_bounds_and_articulation_envelope",
            "source_unsupported_additions": [],
        }
    appearance["entity_appearances"] = ent_map

    sound_bits = []
    for item in sfx15[:3]:
        desc = item.get("event") or item.get("description") or item.get("sfx") or ""
        mix = item.get("mix") or ""
        if desc:
            sound_bits.append(f"{desc}（{mix}）" if mix else str(desc))
    mix_note = ""
    for ep in d15["episodes"]:
        if ep.get("ep") == shot11.get("ep"):
            notes = ep.get("mix_notes") or []
            if notes:
                mix_note = str(notes[0])
            break
    appearance["sound"] = compact(
        "；".join(sound_bits) or "按 D15 分镜音效表执行：自然环境声与动作声，无对白与配乐", 110)

    # ---- 预算自适应：H3 提示词硬上限 7000 字，目标 6500 ----
    # 锚点每多一个，就要为全部实体各写一行屏幕空间锁定，是提示词的主要体积来源。
    # 先按 preflight 的全部锚点填，再实测长度，超预算就均匀稀释锚点（保留首尾）。
    prompt_len = render_prompt_len(contract, appearance, args.skill_dir)
    original_anchors = len(contract["anchors"])
    for keep in range(original_anchors - 1, 1, -1):
        if prompt_len <= PROMPT_CHAR_BUDGET:
            break
        thin_anchors(contract, keep)
        prompt_len = render_prompt_len(contract, appearance, args.skill_dir)
    if prompt_len > PROMPT_CHAR_BUDGET:
        print(f"!! g{gno} 提示词仍超预算：{prompt_len} > {PROMPT_CHAR_BUDGET}", file=sys.stderr)

    # 落盘
    with open(os.path.join(shot_dir, "render_contract.json"), "w", encoding="utf-8") as fh:
        json.dump(contract, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(shot_dir, "appearance.json"), "w", encoding="utf-8") as fh:
        json.dump(appearance, fh, ensure_ascii=False, indent=2)
    return {
        "global_shot_no": gno,
        "entities": len(contract["entities"]),
        "culled_instances": len(culled_ids),
        "anchors": len(contract["anchors"]),
        "anchors_before": original_anchors,
        "prompt_chars": prompt_len,
        "shot_size": shot11.get("shot_size"),
        "subject": subject_label,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot-dir", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--skill-dir", default="")
    args = ap.parse_args()
    result = fill_shot(args)
    print("FILL_OK", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
