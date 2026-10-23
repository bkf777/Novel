#!/usr/bin/env python3
"""D14 逐镜交接包批量构建器。

对 U01 的 32 个镜头逐镜执行：
  1. Blender 后台按 scene_spec/shot_spec 搭白模 → preview_video.mp4 + manifest.json
  2. preflight → preflight.json / render_contract.json / appearance.json / source_anchor_frames/
  3. 输出**待填写清单**：把该镜需要人工实看视频后填写的 M3_FILL 字段列出来

第 4 步（填写合同 → check-contract → build-prompt）必须由 M3 实看视频后完成，脚本不代劳。

用法：
    python3 batch_build.py \
      --plan <plan.json> \
      --project <项目根> \
      --out <units/U01/handoff> \
      [--shots 1,2,3] [--dry-run]

plan.json 形状：
{
  "unit": "U01",
  "skill_dir": "/Users/ezreal/.minimax/v2/plugin-cache/official/sha256-tree-v1-.../skills/blender-h3-dcc",
  "resolution": "480P",
  "shots": [
    {"ep": 1, "shot_id": 1, "global_shot_no": 1, "scene_code": "A-1",
     "duration_sec": 13.0,
     "scene_spec": { ...见 build_white_model.py 的 scene_spec... },
     "shot_spec": { ...见 build_white_model.py 的 shot_spec... }},
    ...
  ]
}
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
BUILD_SCRIPT = os.path.join(SCRIPT_DIR, "build_white_model.py")
PROJECT_SCRIPT = os.path.join(SCRIPT_DIR, "project_bounds.py")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--shots", default="")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def run(cmd: list[str], label: str) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(cmd[-1])) if False else None,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(f"[{label}] FAILED rc={proc.returncode}")
        for line in out.splitlines()[-25:]:
            print("   ", line)
    return proc.returncode, out


def build_one_shot(shot: dict, out_root: str, skill_dir: str,
                   resolution: str, aspect: str = "9:16") -> dict:
    gno = int(shot["global_shot_no"])
    # 目录约定见 00_团队章程.md §六 与 03_规格/字段规格表.md：
    # units/<UNIT>/D14_shots/ep<NN>_shot<NN>/
    ep = int(shot.get("ep") or 0)
    sid = int(shot.get("shot_id") or 0)
    dirname = f"ep{ep:02d}_shot{sid:02d}" if ep and sid else f"G{gno:04d}"
    shot_dir = os.path.join(out_root, dirname)
    os.makedirs(shot_dir, exist_ok=True)

    scene_json = os.path.join(shot_dir, "scene_spec.json")
    shot_json = os.path.join(shot_dir, "shot_spec.json")
    video = os.path.join(shot_dir, "preview_video.mp4")
    manifest = os.path.join(shot_dir, "manifest.json")

    with open(scene_json, "w", encoding="utf-8") as fh:
        json.dump(shot["scene_spec"], fh, ensure_ascii=False, indent=2)
    with open(shot_json, "w", encoding="utf-8") as fh:
        json.dump(shot["shot_spec"], fh, ensure_ascii=False, indent=2)

    # 1) 白模导出
    cmd = [
        BLENDER, "--background", "--factory-startup",
        "--python", BUILD_SCRIPT, "--",
        "--shot-dir", shot_dir,
        "--scene-json", scene_json,
        "--shot-json", shot_json,
        "--out", video,
        "--manifest", manifest,
        "--resolution", resolution,
        "--aspect", aspect,
    ]
    rc, out = run(cmd, f"G{gno:04d} white-model")
    if rc != 0:
        return {"global_shot_no": gno, "status": "failed", "stage": "white_model",
                "error": out[-800:]}

    # 2) preflight
    script = os.path.join(skill_dir, "scripts", "m3_render_workflow.py")
    cmd = [
        sys.executable, script, "preflight",
        "--source", video,
        "--manifest", manifest,
        "--workdir", shot_dir,
        "--min-seconds", "4",
        "--max-seconds", "15",
    ]
    rc, out = run(cmd, f"G{gno:04d} preflight")
    if rc != 0:
        return {"global_shot_no": gno, "status": "failed", "stage": "preflight",
                "error": out[-800:]}

    # 3) 投影真值：按 preflight 选定的锚点帧，算每个物体的屏幕范围/遮挡/深度
    with open(os.path.join(shot_dir, "render_contract.json"), encoding="utf-8") as fh:
        contract = json.load(fh)
    anchor_times = ",".join(
        str(a["time_seconds"]) for a in contract.get("anchors", [])
    )
    projection = os.path.join(shot_dir, "projection.json")
    cmd = [
        BLENDER, "--background", "--factory-startup",
        "--python", PROJECT_SCRIPT, "--",
        "--shot-dir", shot_dir,
        "--scene-json", scene_json,
        "--shot-json", shot_json,
        "--anchor-times", anchor_times,
        "--out", projection,
        "--resolution", resolution,
        "--aspect", aspect,
    ]
    rc, out = run(cmd, f"G{gno:04d} projection")
    if rc != 0:
        return {"global_shot_no": gno, "status": "failed", "stage": "projection",
                "error": out[-800:]}

    # 4) 待填写清单
    todo = {
        "global_shot_no": gno,
        "ep": shot.get("ep"),
        "shot_id": shot.get("shot_id"),
        "scene_code": shot.get("scene_code"),
        "shot_dir": shot_dir,
        "source_inventory_count": len(contract.get("source_inventory", [])),
        "entities_count": len(contract.get("entities", [])),
        "anchors_count": len(contract.get("anchors", [])),
        "must_watch_video": video,
        "projection_json": projection,
        "must_fill": [
            "render_contract.watched_full_source -> true",
            "render_contract.source_inventory[*].source_name/source_type/"
            "root_name/identity_cues（不得删除条目）",
            "render_contract.entities[*].source_role/structural_constraints/motion_contract",
            "render_contract.shots[*].camera_contract（8 个子字段）/actions/"
            "layout_and_occlusion/lighting_spatial_logic",
            "render_contract.anchors[*].composition/camera_relation/"
            "key_layout_and_occlusion/tracked_instances[*]（含 4 个百分比数值与 3 个英文词字段）",
            "render_contract.m3_cut_review.confirmed_real_cuts",
            "appearance.watched_references -> true",
            "appearance.style_source_summary",
            "appearance.global_style_bible（7 个固定字段名）",
            "appearance.entity_appearances（键须与合同 entity labels 完全一致，每项 6 字段）",
            "appearance.sound",
        ],
        "then_run": [
            f'python3 "{skill_dir}/scripts/m3_render_workflow.py" check-contract '
            f'--contract "{shot_dir}/render_contract.json"',
            f'python3 "{skill_dir}/scripts/m3_render_workflow.py" build-prompt '
            f'--contract "{shot_dir}/render_contract.json" '
            f'--appearance "{shot_dir}/appearance.json" '
            f'--output "{shot_dir}/h3_prompt.txt"',
        ],
    }
    with open(os.path.join(shot_dir, "TODO_fill.json"), "w", encoding="utf-8") as fh:
        json.dump(todo, fh, ensure_ascii=False, indent=2)

    return {
        "global_shot_no": gno,
        "status": "awaiting_fill",
        "shot_dir": shot_dir,
        "video": video,
        "manifest": manifest,
        "source_inventory_count": todo["source_inventory_count"],
        "entities_count": todo["entities_count"],
        "anchors_count": todo["anchors_count"],
    }


def main() -> None:
    args = parse_args()
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)

    skill_dir = plan.get("skill_dir")
    resolution = plan.get("resolution", "480P")
    aspect = plan.get("aspect", "9:16")
    out_root = os.path.abspath(args.out)
    os.makedirs(out_root, exist_ok=True)

    wanted = None
    if args.shots:
        wanted = {int(x) for x in args.shots.split(",") if x.strip()}

    results = []
    for shot in plan["shots"]:
        gno = int(shot["global_shot_no"])
        if wanted is not None and gno not in wanted:
            continue
        if args.dry_run:
            print(f"[dry-run] G{gno:04d} ep{shot.get('ep')} "
                  f"{shot.get('duration_sec')}s scene {shot.get('scene_code')}")
            continue
        started = time.time()
        res = build_one_shot(shot, out_root, skill_dir, resolution, aspect)
        res["elapsed_sec"] = round(time.time() - started, 1)
        results.append(res)
        print(json.dumps(res, ensure_ascii=False))

    if results:
        index = os.path.join(out_root, "build_index.json")
        with open(index, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f"INDEX {index} ({len(results)} shots)")


if __name__ == "__main__":
    main()
