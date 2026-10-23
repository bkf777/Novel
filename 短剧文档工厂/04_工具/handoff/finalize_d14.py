#!/usr/bin/env python3
"""D14 逐镜终稿器：填装 → 校验 → 出提示词 → 落每镜包与单元索引。

对每个镜目录依次执行：
    1) fill_contract.py      填满 render_contract.json / appearance.json
    2) check-contract        H3 官方校验器，valid 必须为 true
    3) build-prompt          生成 h3_prompt.txt（预算 6500 字内）
    4) package.json          按工厂 schema 的 D14ShotPackage 落每镜交接包

最后写 units/<UNIT>/D14.json：shots 索引 + commands + check_results。

用法：
    python3 finalize_d14.py --project 02_项目/双相潮主 --unit U01 \
        --shots-root /path/到/各镜目录根 --skill-dir <blender-h3-dcc 路径>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILL_SCRIPT = os.path.join(HERE, "fill_contract.py")


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def run(cmd, label):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def finalize_one(shot_dir, project, unit, skill_dir, budget, repreflight=False,
                 shots_rel_prefix="D14_shots"):
    # 镜号以 shot_spec.json 为准（目录名只是约定，global_shot_no 才是真源）
    shot_spec = read_json(os.path.join(shot_dir, "shot_spec.json"))
    gno = int(shot_spec["global_shot_no"])
    workflow = os.path.join(skill_dir, "scripts", "m3_render_workflow.py")

    # 0) 可选：重跑 preflight 重建合同骨架（还原完整锚点集）
    # 白模视频不变，preflight 是确定性的；重跑只为把上轮被稀释掉的锚点还回来。
    if repreflight:
        rc, out = run([
            sys.executable, workflow, "preflight",
            "--source", os.path.join(shot_dir, "preview_video.mp4"),
            "--manifest", os.path.join(shot_dir, "manifest.json"),
            "--workdir", shot_dir,
            "--min-seconds", "4",
            "--max-seconds", "15",
        ], f"preflight G{gno:04d}")
        if rc != 0:
            return {"global_shot_no": gno, "status": "preflight_failed",
                    "error": out[-600:]}

    rc, out = run([
        sys.executable, FILL_SCRIPT,
        "--shot-dir", shot_dir,
        "--project", project,
        "--unit", unit,
        "--skill-dir", skill_dir,
    ], f"fill G{gno:04d}")
    if rc != 0:
        return {"global_shot_no": gno, "status": "fill_failed", "error": out[-600:]}

    contract_path = os.path.join(shot_dir, "render_contract.json")
    appearance_path = os.path.join(shot_dir, "appearance.json")
    prompt_path = os.path.join(shot_dir, "h3_prompt.txt")

    rc, out = run([
        sys.executable, workflow, "check-contract", "--contract", contract_path,
    ], f"check G{gno:04d}")
    try:
        check = json.loads(out)
    except Exception:
        check = {"valid": False, "errors": [out[-400:]]}
    if not check.get("valid"):
        return {"global_shot_no": gno, "status": "contract_invalid",
                "errors": check.get("errors", [])[:8]}

    rc, out = run([
        sys.executable, workflow, "build-prompt",
        "--contract", contract_path,
        "--appearance", appearance_path,
        "--output", prompt_path,
        "--max-characters", str(budget),
    ], f"prompt G{gno:04d}")
    budget_report = os.path.join(shot_dir, "h3_prompt_budget.json")
    report = read_json(budget_report) if os.path.exists(budget_report) else {}
    if not report.get("ready_to_submit"):
        return {"global_shot_no": gno, "status": "prompt_failed",
                "chars": report.get("prompt_characters"),
                "errors": report.get("invariant_errors", [])[:5]}

    contract = read_json(contract_path)
    appearance = read_json(appearance_path)
    preflight = read_json(os.path.join(shot_dir, "preflight.json"))

    # package_path 用**相对单元目录**的路径（章程 §六 / 字段规格表）：
    #   D14_shots/ep<NN>_shot<NN>/package.json
    dir_name = os.path.basename(shot_dir)
    package_rel = f"{shots_rel_prefix}/{dir_name}/package.json"
    package_path = os.path.join(shot_dir, "package.json")
    package = {
        "ep": int(shot_spec["ep"]),
        "global_shot_no": int(shot_spec["global_shot_no"]),
        "shot_id": int(shot_spec["shot_id"]),
        "scene_code": shot_spec["scene_code"],
        "duration_sec": float(shot_spec["duration_sec"]),
        "package_path": package_rel,
        "preflight": {
            "source": preflight.get("source", {}),
            "timeline_plan": preflight.get("timeline_plan", {}),
            "structure_evidence_available": preflight.get("structure_evidence_available"),
            "requires_m3_cut_review": preflight.get("requires_m3_cut_review"),
            "rule": preflight.get("rule"),
        },
        "render_contract": contract,
        "appearance": appearance,
        "h3_prompt": {
            "path": os.path.abspath(prompt_path),
            "char_count": int(report.get("prompt_characters", 0)),
            "within_budget": True,
            "protected_content_valid": True,
            "ready_to_submit": True,
        },
    }
    write_json(package_path, package)
    return {
        "global_shot_no": gno,
        "status": "ok",
        "anchors": len(contract.get("anchors", [])),
        "entities": len(contract.get("entities", [])),
        "prompt_chars": int(report.get("prompt_characters", 0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--shots-root", required=True)
    ap.add_argument("--skill-dir", required=True)
    ap.add_argument("--budget", type=int, default=6500)
    ap.add_argument("--repreflight", action="store_true",
                    help="填装前重跑 preflight 重建合同骨架（还原完整锚点集）")
    ap.add_argument("--write-index", action="store_true")
    ap.add_argument("--only", default="", help="只跑指定镜号，逗号分隔")
    args = ap.parse_args()

    shot_dirs = sorted(
        os.path.join(args.shots_root, d) for d in os.listdir(args.shots_root)
        if (d.startswith("G") or re.match(r"^ep\d+_shot\d+$", d))
        and os.path.isdir(os.path.join(args.shots_root, d))
    )
    results = []
    shot_dirs_by_no = {}
    for shot_dir in shot_dirs:
        res = finalize_one(shot_dir, args.project, args.unit, args.skill_dir,
                           args.budget, args.repreflight)
        results.append(res)
        if res.get("status") == "ok":
            shot_dirs_by_no[res["global_shot_no"]] = shot_dir
        print(json.dumps(res, ensure_ascii=False), flush=True)

    ok = [r for r in results if r.get("status") == "ok"]
    bad = [r for r in results if r.get("status") != "ok"]
    print(f"\n完成 {len(ok)}/{len(results)} 镜")
    for r in bad:
        print("  !!", json.dumps(r, ensure_ascii=False)[:300])

    if args.write_index and ok:
        if args.only:
            print("!! --only 指定了子集，索引会被写成不完整单元，本次不写 D14.json")
            return
        unit_dir = os.path.join(args.project, "units", args.unit)
        shots_index = []
        for r in sorted(ok, key=lambda x: x["global_shot_no"]):
            gno = r["global_shot_no"]
            shot_dir = shot_dirs_by_no[gno]
            # shots[] 必须是**完整的 D14ShotPackage**（schema additionalProperties=false），
            # 不是精简索引；精简索引只作单独索引文件，不进 shots[]。
            shots_index.append(read_json(os.path.join(shot_dir, "package.json")))
        index = {
            "doc_id": "D14",
            "unit": args.unit,
            "version": "v1.0",
            "status": "in_review",
            "shots": shots_index,
            "commands": [
                "白模：python3 04_工具/handoff/batch_build.py --plan <plan.json> --project 02_项目/双相潮主 --out <shots_root>",
                "填装：python3 04_工具/handoff/fill_contract.py --shot-dir <shot_dir> --project 02_项目/双相潮主 --unit U01 --skill-dir <blender-h3-dcc>",
                "校验：python3 <blender-h3-dcc>/scripts/m3_render_workflow.py check-contract --contract <shot_dir>/render_contract.json",
                "出稿：python3 <blender-h3-dcc>/scripts/m3_render_workflow.py build-prompt --contract <shot_dir>/render_contract.json --appearance <shot_dir>/appearance.json --output <shot_dir>/h3_prompt.txt --max-characters 6500",
                "重跑本单元：python3 04_工具/handoff/finalize_d14.py --project 02_项目/双相潮主 --unit U01 --shots-root <shots_root> --skill-dir <blender-h3-dcc> --write-index",
            ],
            "check_results": [
                {"check": "check-contract", "shots": len(ok), "result": "valid", "errors": 0},
                {"check": "build-prompt", "shots": len(ok), "result": "within_budget",
                 "budget": args.budget,
                 "max_observed": max((r.get("prompt_chars", 0) for r in ok), default=0)},
                {"check": "anchor_sampling", "shots": len(ok),
                 "result": "thinned_for_budget",
                 "note": "锚点为压缩提示词而按需均匀稀释（保首尾）；逐镜锚点数见 shots[].render_contract.anchors",
                 "min_observed": min((r.get("anchors", 0) for r in ok), default=0),
                 "max_observed": max((r.get("anchors", 0) for r in ok), default=0)},
                {"check": "factory_validator", "result": "pending_run",
                 "note": "由 04_工具/validate.mjs --unit U01 的 V11 覆盖校验复核"},
            ],
        }
        out = os.path.join(unit_dir, "D14.json")
        write_json(out, index)
        print(f"D14.json 已写出：{out}（{len(shots_index)} 镜）")

        # 自己跑一遍工厂校验，把真实结果写回 check_results（不留 pending）
        validator = os.path.join(os.path.dirname(HERE), "validate.mjs")
        if os.path.exists(validator):
            rc, vout = run(["node", validator, "--project", args.project,
                            "--unit", args.unit], "validate")
            passed = "通过 11/11" in vout or "11/11" in vout
            errors = 0
            for line in vout.splitlines():
                if "error" in line and "结果" in line:
                    digits = re.findall(r"error (\d+)", line)
                    if digits:
                        errors = int(digits[0])
            for item in index["check_results"]:
                if item["check"] == "factory_validator":
                    item["result"] = "pass" if (rc == 0 and errors == 0) else "fail"
                    item["note"] = (
                        f"validate.mjs --unit {args.unit} 退出码 {rc}；"
                        f"{'11/11 规则通过、error 0' if errors == 0 else f'error {errors}'}"
                    )
            write_json(out, index)
            print(f"factory_validator：{index['check_results'][-1]['result']}")


if __name__ == "__main__":
    main()
