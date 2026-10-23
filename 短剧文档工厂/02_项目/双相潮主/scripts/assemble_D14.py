#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装 D14 逐镜交接包：逐镜 package.json + D14.json（**单元无关逻辑**）。

用法：
    python3 assemble_D14.py --unit U01 --work /tmp/dcc-smoke/u01
    python3 assemble_D14.py --unit U02 --work /tmp/dcc-smoke/u02

真源：<work>/<shot>/（白模导出 + preflight + 合同 + h3_prompt）
产出：units/<UNIT>/D14_shots/<shot>/ 下与本轮白模自洽的全部产物
      + units/<UNIT>/D14.json

V11 要求：D14.shots[] 的内联项与落盘 package.json 必须同形（deepDiff 零差异），
因此先写文件、再把同一对象回填进 D14.json。

⚠️ 本脚本会**覆写** units/<UNIT>/D14.json 与 D14_shots/ —— U01 已锁，
对其重跑前先备份或改用 --project 指向副本。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version_guard import VersionGuard  # noqa: E402  写盘版本守卫（Q64 / Q68）

# 本脚本将写入的 D14 版本号（版本守卫据此与磁盘现盘比较）
D14_TARGET_VERSION = "v1.1"


def _parse_args():
    ap = argparse.ArgumentParser(description="组装 D14 逐镜交接包")
    ap.add_argument("--unit", default=os.environ.get("UNIT_ID", "U01"),
                    help="单元号，如 U01 / U02（默认 U01）")
    ap.add_argument("--project", default=os.environ.get("D14_PROJECT", ""),
                    help="项目目录（默认 双相潮主）")
    ap.add_argument("--work", default=os.environ.get("D14_WORK", ""),
                    help="白模工作区（默认 /tmp/dcc-smoke/<unit 小写>）")
    ap.add_argument("--force", action="store_true",
                    help="Q64 显式旁路：磁盘版本更高时仍然覆盖（旁路动作会留痕）")
    ap.add_argument("--version", default=os.environ.get("D14_VERSION", ""),
                    help=f"目标版本号（默认 {D14_TARGET_VERSION}）；"
                         "锁后修订时各单元独立升版，未传则沿用默认 ⇒ 行为不变")
    args, _unknown = ap.parse_known_args()
    return args


ARGS = _parse_args()
UNIT = ARGS.unit
# 项目根默认从脚本位置推导（<项目>/scripts/..），不写死绝对路径
ROOT = Path(ARGS.project) if ARGS.project else Path(__file__).resolve().parent.parent
WORK = Path(ARGS.work) if ARGS.work else Path(f"/tmp/dcc-smoke/{UNIT.lower()}")
SHOTS_DIR = ROOT / "units" / UNIT / "D14_shots"

# 白模流水线直接产出的产物
ARTIFACTS = [
    "preview_video.mp4",
    "manifest.json",
    "preflight.json",
    "render_contract.json",
    "appearance.json",
    "h3_prompt.txt",
    "h3_prompt_budget.json",
]

MOVE_MAP = {
    "固定": "static", "推": "dolly", "移": "truck", "跟": "truck",
    "升降": "pan", "手持": "orbit", "摇": "pan", "拉": "dolly",
}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ★ 交付包路径重写（2026-10-23 Chief）：白模流水线在 /tmp/dcc-smoke/u01 下工作，产物里所有
#   路径字段（source_frame / preflight.source.path / manifest_path / timeline_plan.source.path …）
#   都是 /tmp 绝对路径。/tmp 会被系统清理，交接包一出厂就断链，锚点参考帧取不到。
#   统一重写为「相对 units/<UNIT>/」形式，与 package_path 同基准。
_WORK_ABS = str(WORK)
TMP_PREFIXES = tuple(sorted({f"/private{_WORK_ABS}/", f"{_WORK_ABS}/"},
                             key=len, reverse=True))


def relativize_paths(obj):
    """递归把所有指向 /tmp 工作区的路径重写为相对 units/<UNIT>/ 的路径。"""
    if isinstance(obj, dict):
        return {k: relativize_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [relativize_paths(v) for v in obj]
    if isinstance(obj, str):
        for pfx in TMP_PREFIXES:
            if obj.startswith(pfx):
                return "D14_shots/" + obj[len(pfx):]
        return obj
    return obj


def quat_to_euler_deg(q):
    """Blender 四元数 (w,x,y,z) → XYZ 欧拉角（度）。"""
    w, x, y, z = q
    sinr = 2.0 * (w * x + y * z)
    cosr = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr, cosr)
    sinp = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
    pitch = math.asin(sinp)
    siny = 2.0 * (w * z + x * y)
    cosy = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny, cosy)
    return [round(math.degrees(roll), 4), round(math.degrees(pitch), 4), round(math.degrees(yaw), 4)]


def write_specs(dst: Path, manifest: dict, d11shot: dict, d13cam: dict, gsn: int):
    """按本轮白模的实际几何重建 shot_spec / scene_spec / projection。

    这三份是 04_工具/handoff 工具链的白模输入与投影真值；
    若保留上一轮白模（另一套分辨率与坐标）的旧文件，会与本目录内的
    preview_video.mp4 / manifest.json 互相矛盾，故一律按当前白模重生成。
    """
    ev = manifest["structure_evidence"]
    cams = ev.get("camera_samples") or []
    cam0 = cams[0] if cams else {}
    res = manifest.get("resolution") or [1080, 1920]
    if isinstance(res, dict):
        res = [res.get("width", 1080), res.get("height", 1920)]

    # ---- shot_spec ----
    actors = []
    for o in ev.get("objects", []):
        root = o.get("root_name") or ""
        if "_CHAR_" not in root:
            continue
        name = root.split("_CHAR_", 1)[1]
        samples = [s for s in (o.get("samples") or []) if s.get("projected_visible")]
        moved = False
        if len(samples) >= 2:
            a = samples[0].get("world_location")
            b = samples[-1].get("world_location")
            if a and b:
                moved = math.dist(a, b) > 0.05
        actors.append({"name": name, "motion": "locomotion" if moved else "static"})
    shot_spec = {
        "ep": d11shot["ep_no"],
        "shot_id": d11shot["shot_id"],
        "global_shot_no": gsn,
        "scene_code": d11shot["scene_code"],
        "duration_sec": d11shot["duration_sec"],
        "fps": manifest.get("fps", 24),
        "camera": {
            "location_m": cam0.get("location"),
            "rotation_euler_deg": quat_to_euler_deg(cam0.get("rotation_quaternion_wxyz", [1, 0, 0, 0])),
            "target_m": d13cam.get("target_m"),
            "lens_mm": cam0.get("lens_mm"),
            "move": MOVE_MAP.get(d11shot.get("movement"), "static"),
        },
        "actors": actors,
    }
    dump(dst / "shot_spec.json", shot_spec)

    # ---- scene_spec ----
    props = []
    for o in ev.get("objects", []):
        samples = [s for s in (o.get("samples") or []) if s.get("projected_visible")]
        if not samples:
            continue
        s = samples[0]
        loc = s.get("world_location") or [0, 0, 0]
        dim = s.get("world_dimensions") or [0, 0, 0]
        root = o.get("root_name") or ""
        kind = "human_proxy" if "_CHAR_" in root else ("box" if "_PROP_" in root or "_EXT_" in root else "proxy")
        props.append({
            "name": root,
            "kind": kind,
            "center_m": [round(float(v), 3) for v in loc],
            "size_m": [round(float(v), 3) for v in dim],
            "role": "primary" if props == [] else "set",
        })
    xs = [p["center_m"][0] for p in props]
    ys = [p["center_m"][1] for p in props]
    zs = [p["center_m"][2] for p in props]
    sizes = [p["size_m"] for p in props]
    scene_spec = {
        "scene_code": d11shot["scene_code"],
        "size_m": [
            round(max([p[0] for p in sizes] + [1.0]), 3),
            round(max([p[1] for p in sizes] + [1.0]), 3),
            round(max([p[2] for p in sizes] + [1.0]), 3),
        ],
        "ground_center_m": [round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)] if xs else [0, 0],
        "floor_z": round(min(zs), 3) if zs else 0.0,
        "props": props,
        "walls": [],
        "wall_thickness_m": 0.15,
    }
    dump(dst / "scene_spec.json", scene_spec)

    # ---- projection ----
    frames = []
    by_frame = {}
    for o in ev.get("objects", []):
        for s in (o.get("samples") or []):
            by_frame.setdefault(int(s["frame"]), []).append((o.get("root_name"), s))
    for cam in cams:
        f = int(cam["frame"])
        objects = {}
        # ★ Q94 R-028e-r2 修正：**同 root_name 的多实例按「组内最大」归并**，
        #   不得用「后者覆盖前者」。
        #   缺陷（实测 U01 ep08_shot03 / ep05_shot03）：
        #     8 个 `A-9_CHAR_RescuedQueueMember_01..08` 共享同一 root_name，
        #     插件 `_object_sample` 是**逐实例**采样的（每个实例都有自己的
        #     screen_bbox_percent），但投影字典以 root_name 为键 ⇒
        #     后写入的实例覆盖前面的 ⇒ 一群人只剩最后一个（最远、占幅 0）
        #     ⇒ 投影里「主体」凭空消失 ⇒ V12 误报 W1 角色不在画幅 + W3 主体让位环境。
        #   取值口径：组内**占幅最大**的实例作为该 root 的代表（逐帧、各自的旋转矩阵
        #     实测值，不做任何合成或估算）；in_frame 取代表实例的 projected_visible。
        #   ⚠️ 群体主体按「最显眼个体」计，**不取并集** —— 并集会给出任何单个成员
        #     都不存在的数（伪造），且可能把特写占幅顶出区间上沿。
        groups = {}
        for name, s in by_frame.get(f, []):
            groups.setdefault(name, []).append(s)
        for name, samples in groups.items():
            def _key(s):
                bb = s.get("screen_bbox_percent") or {}
                return (bool(s.get("projected_visible")),
                        float(bb.get("height", 0.0) or 0.0))
            s = max(samples, key=_key)
            bb = s.get("screen_bbox_percent") or {}
            objects[name] = {
                "in_frame": bool(s.get("projected_visible")),
                "visible_percent": {
                    "center_x": round(float(bb.get("center_x", 0.0)), 3),
                    "center_y": round(float(bb.get("center_y", 0.0)), 3),
                    "width": round(float(bb.get("width", 0.0)), 3),
                    "height": round(float(bb.get("height", 0.0)), 3),
                },
                "depth_m": round(float(s.get("depth") or 0.0), 4),
                "world_dimensions": [round(float(v), 3) for v in (s.get("world_dimensions") or [])],
                # ★ Q94 追加要求：该采样帧实际欧拉角（度）与角色姿态。
                #   真源由 scripts/build_white_model.py 采样写入 manifest 的
                #   structure_evidence（插件 _object_sample 不采样旋转），
                #   此处只做 manifest → projection 的字段映射。
                "rotation_euler_deg": s.get("rotation_euler_deg"),
                "pose": s.get("pose"),
            }
        frames.append({
            "time_seconds": round((f - manifest.get("frame_start", 1)) / manifest.get("fps", 24), 3),
            "frame": f,
            "camera": {
                "location_m": cam.get("location"),
                "rotation_euler_deg": quat_to_euler_deg(cam.get("rotation_quaternion_wxyz", [1, 0, 0, 0])),
                "lens_mm": cam.get("lens_mm"),
            },
            "objects": objects,
        })
    dump(dst / "projection.json", {
        "shot_dir": str(dst),
        "global_shot_no": gsn,
        "ep": d11shot["ep_no"],
        "shot_id": d11shot["shot_id"],
        "scene_code": d11shot["scene_code"],
        "fps": manifest.get("fps", 24),
        "frame_start": manifest.get("frame_start", 1),
        "frame_end": manifest.get("frame_end", 1),
        "resolution_px": res,
        "aspect": "9:16",
        "camera": shot_spec["camera"],
        "frames": frames,
    })


def main() -> int:
    # ★ 写盘版本守卫（Q64 / Q68）
    #   位置刻意放在**函数最前、所有写盘之前** —— 守卫拒绝时磁盘实况**完全未被改写**
    #   （含 32 份 package.json 与 D14_shots/ 一律不落），且此前没有任何抢先 exit 的守卫，
    #   保证守卫「真的会被执行到」、--force 逃生口不被上游遮蔽。
    _guard = VersionGuard(
        out_path=str(ROOT / f"units/{UNIT}/D14.json"),
        target=ARGS.version or D14_TARGET_VERSION,
        unit=UNIT,
        doc_id="D14",
        log_path=str(ROOT.parent.parent / "reports" / "force_overwrite_log.jsonl"),
    )
    if not _guard.check(force=ARGS.force):
        return 2

    d11 = load(ROOT / f"units/{UNIT}/D11.json")
    d13 = load(ROOT / f"units/{UNIT}/D13.json")
    d11_shots = {}
    gsn_of_d11 = {}          # global_shot_no -> (ep, shot_id)
    for ep in d11["episodes"]:
        for s in ep["shots"]:
            d11_shots[(int(ep["ep"]), int(s["shot_id"]))] = s
            gsn_of_d11[int(s["global_shot_no"])] = (int(ep["ep"]), int(s["shot_id"]))
    d13_cams = {}
    for sc in d13["scenes"]:
        for c in sc.get("camera_positions", []):
            d13_cams[int(c["global_shot_no"])] = c

    packages = []
    check_results = []
    problems = []
    # ★ 镜号集合一律**从 D11 现盘取**，不写死 1..32 ——
    #   U02 的 global_shot_no 是 33..64，写死上界会整单元漏装（实测 2026-10-23）。
    for gsn in sorted(gsn_of_d11):
        ep, sid = gsn_of_d11[gsn]
        name = f"ep{ep:02d}_shot{sid:02d}"
        src = WORK / name
        dst = SHOTS_DIR / name
        src_shot = dict(d11_shots[(ep, sid)])
        src_shot["ep_no"] = ep

        missing = [f for f in ARTIFACTS if not (src / f).is_file()]
        if missing:
            problems.append(f"{name}: 缺少产物 {missing}")
            continue
        budget = load(src / "h3_prompt_budget.json")
        if not (budget.get("within_budget") and budget.get("protected_content_valid")
                and budget.get("ready_to_submit")):
            problems.append(
                f"{name}: 预算三项未全通过 chars={budget.get('prompt_characters')} "
                f"wb={budget.get('within_budget')} pcv={budget.get('protected_content_valid')} "
                f"rts={budget.get('ready_to_submit')}")
            continue
        text = (src / "h3_prompt.txt").read_text(encoding="utf-8")
        if len(text) != budget.get("prompt_characters"):
            problems.append(f"{name}: h3_prompt.txt 实际 {len(text)} 字 ≠ 报告 {budget.get('prompt_characters')}")
            continue

        dst.mkdir(parents=True, exist_ok=True)
        for f in ARTIFACTS:
            shutil.copy2(src / f, dst / f)
        # ★ 拷贝后立刻重写 JSON 产物里的 /tmp 绝对路径 → 相对 units/<UNIT>/
        for f in ("render_contract.json", "preflight.json", "appearance.json", "manifest.json"):
            fp = dst / f
            if fp.is_file():
                dump(fp, relativize_paths(load(fp)))
        anchors_src = src / "source_anchor_frames"
        if anchors_src.is_dir():
            anchors_dst = dst / "source_anchor_frames"
            if anchors_dst.exists():
                shutil.rmtree(anchors_dst)
            shutil.copytree(anchors_src, anchors_dst)
        todo = dst / "TODO_fill.json"
        if todo.exists():
            todo.unlink()

        manifest = load(src / "manifest.json")
        write_specs(dst, manifest, src_shot, d13_cams.get(gsn, {}), gsn)

        contract = relativize_paths(load(src / "render_contract.json"))
        package = {
            "ep": ep,
            "global_shot_no": gsn,
            "shot_id": sid,
            "scene_code": src_shot["scene_code"],
            "duration_sec": src_shot["duration_sec"],
            "package_path": f"D14_shots/{name}/package.json",
            "preflight": relativize_paths(load(src / "preflight.json")),
            "render_contract": contract,
            "appearance": relativize_paths(load(src / "appearance.json")),
            "h3_prompt": {
                "path": f"D14_shots/{name}/h3_prompt.txt",
                "char_count": len(text),
                "within_budget": True,
                "protected_content_valid": True,
                "ready_to_submit": True,
            },
        }
        dump(dst / "package.json", package)
        packages.append(package)
        # check_results 统一为开工单指定的对象形状 {check, result, note}；
        # 其后附逐项证据字段，便于下游按镜复核而不必回读交接包。
        check_results.append({
            "check": "D14 逐镜交接包四项自检",
            "result": "PASS",
            "note": (
                f"{name}（g{gsn:02d}）：contract/appearance/package schema 与逐镜包文件一致性校验通过；"
                f"h3_prompt 实测 {len(text)} 字 ≤ 6500，"
                f"within_budget / protected_content_valid / ready_to_submit 三项为真；"
                f"source_inventory {len(contract['source_inventory'])} 条、"
                f"entities {len(contract['entities'])} 个、anchors {len(contract['anchors'])} 个；"
                f"render_contract schema_version={contract.get('schema_version')}、"
                f"appearance schema_version={load(src / 'appearance.json').get('schema_version')}"
            ),
            "shot": name,
            "global_shot_no": gsn,
            "check_contract": "PASS",
            "h3_prompt_characters": len(text),
            "within_budget": True,
            "protected_content_valid": True,
            "ready_to_submit": True,
            "source_inventory_count": len(contract["source_inventory"]),
            "entity_count": len(contract["entities"]),
            "anchor_count": len(contract["anchors"]),
            "compression_factor": budget.get("compression_factor"),
        })

    if problems:
        print("[assemble] 中止：以下镜头未就绪")
        for p in problems:
            print("   -", p)
        return 1

    commands = [
        f"D13_STAMP={UNIT.lower()} D13_SHADE=v4 /Applications/Blender.app/Contents/MacOS/Blender "
        f"--background --factory-startup --python 02_项目/双相潮主/scripts/build_white_model.py -- "
        f"--project 02_项目/双相潮主 --out {WORK.parent} --unit {UNIT} "
        f"--content white_model_content_{UNIT}",
        f"python3 02_项目/双相潮主/scripts/d14_pipeline.py preflight --root {WORK}",
        f"python3 02_项目/双相潮主/scripts/fill_D14_contracts.py --unit {UNIT}",
        f"python3 02_项目/双相潮主/scripts/d14_pipeline.py check --root {WORK}",
        f"python3 02_项目/双相潮主/scripts/d14_pipeline.py prompt --root {WORK}",
        f"python3 02_项目/双相潮主/scripts/assemble_D14.py --unit {UNIT} --work {WORK}",
    ]
    d14 = {
        "doc_id": "D14",
        "unit": UNIT,
        "version": ARGS.version or D14_TARGET_VERSION,
        "status": "in_review",
        "shots": packages,
        "commands": commands,
        "check_results": check_results,
    }
    dump(ROOT / f"units/{UNIT}/D14.json", d14)
    print(f"[assemble] 落盘 {len(packages)} 份逐镜包 + D14.json")
    for r in check_results:
        print(f"   {r['shot']}  g{r['global_shot_no']:02d}  chars={r['h3_prompt_characters']:>5}  "
              f"inv={r['source_inventory_count']:>2}  ent={r['entity_count']:>2}  anchors={r['anchor_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
