#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_D13.py —— 《双相潮主》单元 D13 场景白模说明书 生成器（**单元无关逻辑**）

用法：
    python3 build_D13.py --unit U01 --content d13_content_U01
    python3 build_D13.py --unit U02 --content d13_content_U02

SSOT：本脚本是 D13 的**逻辑**真源；**内容**在同目录 `d13_content_<UNIT>.py`。
改需求 → 改对应的那一份 → 重跑 → 再跑 validate.mjs。
产出：短剧文档工厂/02_项目/双相潮主/units/<UNIT>/D13.json

**严禁复制本脚本成 `_u02` 副本**（S12 裁决 / U02-R01）：副本即第二套实现，必然分叉。
新单元一律用 `--unit` + `--content` 两参数复用本逻辑。

硬纪律（自检内置，违反即抛错）：
  1. 场景数与内容模块声明一致，scene_code 集合必须与 D11 实际值完全相等（不多不少）
  2. 每个场景的 camera_positions / sightlines 必须恰好覆盖 D11 属于该场的全部 global_shot_no
  3. 坐标单位统一为米；方位角由目标点反算（正北=0°，顺时针为正）
  4. D13 不写镜头设计（景别/焦距/运镜/机位角度词一律不出现）
  5. D13 不写美术风格（色板名/材质/氛围形容词不出现）
  6. V5 禁用同义词：全文扫描 D05.glossary.forbidden_synonyms，命中即报错
  7. V6 血腥禁词：全文扫描 rules.forbidden_words，命中即报错
"""

import argparse
import importlib.util
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version_guard import VersionGuard  # noqa: E402  写盘版本守卫（Q64 / Q68）

ROOT = os.path.dirname(os.path.abspath(__file__))


def _parse_args():
    ap = argparse.ArgumentParser(description="D13 场景白模说明书生成器")
    ap.add_argument("--unit", default=os.environ.get("UNIT_ID", "U01"),
                    help="单元号，如 U01 / U02（默认 U01）")
    ap.add_argument("--content", default=os.environ.get("D13_CONTENT", ""),
                    help="内容模块名（不带 .py），默认按单元自动推断 d13_content_<UNIT>")
    ap.add_argument("--project", default=os.environ.get("D13_PROJECT", ""),
                    help="项目目录（默认脚本所在的上级目录）")
    ap.add_argument("--force", action="store_true",
                    help="Q64 显式旁路：磁盘版本更高时仍然覆盖（旁路动作会留痕）")
    args, _unknown = ap.parse_known_args()
    return args


ARGS = _parse_args()
UNIT_ID = ARGS.unit
PROJ = ARGS.project or os.path.dirname(ROOT)          # 02_项目/双相潮主
FACTORY = os.path.dirname(os.path.dirname(PROJ))     # 短剧文档工厂
CONTENT_NAME = ARGS.content or f"d13_content_{UNIT_ID}"
UNIT = os.path.join(PROJ, "units", UNIT_ID)

D11_PATH = os.path.join(UNIT, "D11.json")
D05_PATH = os.path.join(PROJ, "shared", "D05.json")
RULES_PATH = os.path.join(FACTORY, "03_规格", "rules.json")
OUT_PATH = os.path.join(UNIT, "D13.json")


def _load_content(name):
    """加载内容模块（内容模块不依赖本脚本，避免循环导入）。"""
    path = os.path.join(ROOT, name + ".py")
    if not os.path.exists(path):
        raise SystemExit(f"内容模块不存在：{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bearing(x1, y1, x2, y2):
    """正北=0°，顺时针为正。"""
    return round(math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360)


def compass(b):
    b %= 360
    names = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    return names[int((b + 22.5) % 360 // 45)]


def facing(pos, target, label):
    b = bearing(pos[0], pos[1], target[0], target[1])
    return f"方位角 {b}°（{compass(b)}），指向{label} ({target[0]:.2f},{target[1]:.2f})"


def cam(gsn, cid, pos, target, label, notes):
    return {
        "global_shot_no": gsn,
        "camera_id": cid,
        "position_m": [round(v, 2) for v in pos],
        "height_m": round(pos[2], 2),
        "facing": facing(pos, target, label),
        "target_m": [round(v, 2) for v in target],
        "notes": notes,
    }


def sight(gsn, cid, pos, target, label, blocked, foreground):
    return {
        "global_shot_no": gsn,
        "camera_id": cid,
        "position_m": [round(v, 2) for v in pos],
        "target_m": [round(v, 2) for v in target],
        "target_label": label,
        "occlusion": blocked,
        "foreground": foreground,
    }


def prop(name, kind, size, pos, state, note, shots=None):
    """道具条目。shots = 该道具实际入画的 global_shot_no 列表。

    省略 shots 表示"本场各镜均在位"（空间壳体、常驻陈设）；
    给出 shots 表示该道具只属于这些镜头，白模按此逐镜筛选，
    避免把别的镜头的剧情道具搬进本镜画面。
    """
    item = {
        "name": name,
        "type": kind,
        "size_or_extent": size,
        "position_m": pos,
        "state": state,
        "note": note,
    }
    if shots is not None:
        item["shots"] = sorted(shots)
    return item


def light(lid, kind, pos, kelvin, beam, note):
    return {
        "id": lid,
        "type": kind,
        "position_m": [round(v, 2) for v in pos],
        "color_temp_K": kelvin,
        "beam": beam,
        "note": note,
    }


# ---------------------------------------------------------------- 坐标系常量

# 街区基线：O = 地面破口中心 (0,0,0)，+X 东 / +Y 北 / +Z 上，Z=0 为厂区地坪面
ROAD_W = "X +12.00..+18.00"

# 出租屋独立局部基线：O = 床尾中心地面点 (0,0,0)
ROOM = "X -2.10..+02.10 / Y -1.80..+01.80"


# ---------------------------------------------------------------- 场景定义


# ---------------------------------------------------------------- 组装 + 自检

def main():
    content = _load_content(CONTENT_NAME)
    scenes = content.build_scenes({
        "bearing": bearing, "compass": compass, "facing": facing,
        "cam": cam, "sight": sight, "prop": prop, "light": light,
    })
    NEEDS_KEYWORDS = content.NEEDS_KEYWORDS
    # 版本号由**内容模块**声明（单元无关逻辑）：锁后修订时由内容层升版，
    # 内容模块未声明 VERSION 时保持 v1.0（⇒ 未声明单元行为逐字不变）。
    DOC_VERSION = getattr(content, "VERSION", "v1.0")
    d11 = json.load(open(D11_PATH, encoding="utf-8"))
    d05 = json.load(open(os.path.join(PROJ, "shared", "D05.json"), encoding="utf-8"))
    rules = json.load(open(RULES_PATH, encoding="utf-8"))

    # D11 真源：每镜的 scene_code / global_shot_no
    d11_shots = {}          # global_shot_no -> {ep, shot_id, scene_code}
    scene_of_shot = {}      # scene_code -> [global_shot_no...]
    for ep in d11["episodes"]:
        for s in ep["shots"]:
            d11_shots[s["global_shot_no"]] = {
                "ep": ep["ep"], "shot_id": s["shot_id"], "scene_code": s["scene_code"],
                "visual_facts": s.get("visual_facts", "") or "",
            }
            scene_of_shot.setdefault(s["scene_code"], []).append(s["global_shot_no"])

    errs = []

    # ① 场景数 = 9，集合与 D11 完全一致
    my_codes = [s["scene_code"] for s in scenes]
    if len(scenes) != content.SCENE_COUNT:
        errs.append(f"场景数应为 {content.SCENE_COUNT}（内容模块声明），实际 {len(scenes)}")
    if len(set(my_codes)) != len(my_codes):
        errs.append("scene_code 存在重复")
    if set(my_codes) != set(scene_of_shot):
        errs.append(f"scene_code 集合与 D11 不一致："
                    f"缺 {sorted(set(scene_of_shot) - set(my_codes))}，"
                    f"多 {sorted(set(my_codes) - set(scene_of_shot))}")

    # ② 每场机位与视线恰好覆盖 D11 属于该场的镜头
    for sc in scenes:
        code = sc["scene_code"]
        want = sorted(scene_of_shot.get(code, []))
        got_cam = sorted(c["global_shot_no"] for c in sc["camera_positions"])
        got_sig = sorted(s["global_shot_no"] for s in sc["sightlines"])
        if got_cam != want:
            errs.append(f"{code} 机位覆盖不符：D11={want} D13={got_cam}")
        if got_sig != want:
            errs.append(f"{code} 视线覆盖不符：D11={want} D13={got_sig}")
        # ep 必须与 D11 该场镜号所属集一致
        eps = {d11_shots[g]["ep"] for g in want}
        if eps and sc["ep"] not in eps:
            errs.append(f"{code} 的 ep={sc['ep']} 与 D11 所属集 {sorted(eps)} 不符")
        # 机位与视线一一对应
        if {c["camera_id"] for c in sc["camera_positions"]} != {s["camera_id"] for s in sc["sightlines"]}:
            errs.append(f"{code} 机位与视线未一一对应")
        # 坐标单位与量纲
        for c in sc["camera_positions"]:
            if len(c["position_m"]) != 3 or len(c["target_m"]) != 3:
                errs.append(f"{code}/{c['camera_id']} 坐标维度不为 3")
            if abs(c["position_m"][2] - c["height_m"]) > 0.01:
                errs.append(f"{code}/{c['camera_id']} height_m 与 position_m.z 不一致")
        for s in sc["sightlines"]:
            if len(s["position_m"]) != 3 or len(s["target_m"]) != 3:
                errs.append(f"{code}/{s['camera_id']} 坐标维度不为 3")
        # 每场景必填字段非空
        for f in ("plan", "props", "entrances", "camera_positions", "sightlines", "scale_limits"):
            if not sc.get(f):
                errs.append(f"{code} 字段 {f} 为空")
        for sl in sc["scale_limits"]:
            if not isinstance(sl, str) or not sl.strip():
                errs.append(f"{code} scale_limits 含空串")

    # ③ 悬浮界面道具与 D11 画面事实交叉核对（面板只在该镜确有界面元素时才登记）
    UI_KEYS = ("面板", "进度条", "读数栏", "通报条", "读数暴涨")
    for sc in scenes:
        code = sc["scene_code"]
        ui_shots = set()
        for g in scene_of_shot.get(code, []):
            blob_shot = d11_shots[g]["visual_facts"]
            if any(k in blob_shot for k in UI_KEYS):
                ui_shots.add(g)
        has_panel = any(p["name"] == "灰框面板" for p in sc["props"])
        if ui_shots and not has_panel:
            errs.append(f"{code} D11 镜 {sorted(ui_shots)} 有界面元素，但 D13 未登记灰框面板")
        if has_panel and not ui_shots:
            errs.append(f"{code} 登记了灰框面板，但 D11 该场各镜画面事实无界面元素")

    # ④ D07.scene_needs → D13 场景逐条落地核对（按 ep 定位空间，再核对要素词）
    scene_blob = {sc["scene_code"]: json.dumps(sc, ensure_ascii=False) for sc in scenes}
    d07 = json.load(open(os.path.join(UNIT, "D07.json"), encoding="utf-8"))
    for ep in d07["episodes"]:
        for need in ep.get("scene_needs", []) or []:
            # D07 U02 v1.3 的 scene_needs 键名不统一：ep9~ep11 用「空间」，
            # ep12~ep16 用「space」。本岗不改他岗产物，此处只做**读取兼容**。
            space = need.get("空间") or need.get("space") or ""
            key = (ep["ep"], space)
            if key not in NEEDS_KEYWORDS:
                errs.append(f"D07 ep{ep['ep']} scene_needs「{space}」未登记要素核对表")
                continue
            targets, kws = NEEDS_KEYWORDS[key]
            for code in targets.split("/"):
                blob = scene_blob.get(code, "")
                for kw in kws:
                    if kw not in blob:
                        errs.append(f"D07 ep{ep['ep']}「{space}」要素「{kw}」未在 D13 {code} 落地")
    # D07 的 scene_needs 空间名必须都能对上 D13 的某个场景
    covered = {t for tg, _ in NEEDS_KEYWORDS.values() for t in tg.split("/")}
    for sc in scenes:
        if sc["scene_code"] not in covered:
            errs.append(f"D13 {sc['scene_code']} 未被任何 D07 scene_needs 覆盖")

    # ⑤ 全文禁用词扫描（V5 / V6）
    doc = {
        "doc_id": "D13", "unit": UNIT_ID, "version": DOC_VERSION, "status": "in_review",
        "scenes": scenes,
    }
    blob = json.dumps(doc, ensure_ascii=False)
    for g in d05.get("glossary", []):
        for bad in g.get("forbidden_synonyms") or []:
            if bad and bad in blob:
                errs.append(f"命中禁用同义写法「{bad}」（术语 {g['term']}）")
    for bad in rules.get("forbidden_words", []):
        if bad and bad in blob:
            errs.append(f"命中血腥禁词「{bad}」")
    # 派活单 R-016 指定的字面 grep 口径（连否定句也不允许出现该词）
    for bad in ["血液", "血肉", "喷溅", "器官", "创口", "创面", "十字", "光环", "念珠", "法衣", "祭坛"]:
        if bad in blob:
            errs.append(f"命中 R-016 字面禁用词「{bad}」")

    # ④ D13 不得出现镜头设计词汇（D11 职责）
    cam_vocab = ["景别", "焦距", "毫米", "运镜", "构图", "画幅", "中景", "近景", "特写",
                 "远景", "全景", "中远景", "中近景", "过肩", "主观视角", "客观跟拍",
                 "仰视", "俯视", "顶视", "平视", "手持", "变焦", "环绕", "跟拍"]
    for w in cam_vocab:
        if w in blob:
            errs.append(f"D13 出现镜头设计词汇「{w}」（属 D11 职责）")

    if errs:
        print("❌ 自检未通过：")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    # ★ 写盘版本守卫（Q64 / Q68）
    #   位置刻意放在**内容自检之后、写盘之前**，且**此前没有任何会抢先 exit 的守卫** ——
    #   保证守卫「真的会被执行到」（Q68 可达性），且 --force 逃生口不被上游遮蔽。
    guard = VersionGuard(
        out_path=OUT_PATH,
        target=doc["version"],
        unit=UNIT_ID,
        doc_id="D13",
        log_path=os.path.join(FACTORY, "reports", "force_overwrite_log.jsonl"),
    )
    if not guard.check(force=ARGS.force):
        sys.exit(2)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    total_props = sum(len(s["props"]) for s in scenes)
    print("✅ D13 生成并自检通过")
    print(f"   场景数 {len(scenes)}｜镜头覆盖 {sum(len(v) for v in scene_of_shot.values())}/"
          f"{len(d11_shots)}｜props 合计 {total_props}")
    for sc in scenes:
        gs = sorted(c["global_shot_no"] for c in sc["camera_positions"])
        print(f"   {sc['scene_code']}  ep{sc['ep']}  镜 {gs}  props {len(sc['props'])}")


if __name__ == "__main__":
    main()
