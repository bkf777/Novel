#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D14 逐镜流水线驱动：对每镜跑 preflight / check-contract / build-prompt。

用法：
  python3 scripts/d14_pipeline.py preflight   --root /tmp/dcc-smoke/u01
  python3 scripts/d14_pipeline.py prompt      --root /tmp/dcc-smoke/u01
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = "/Users/ezreal/.minimax/v2/plugin-cache/official/sha256-tree-v1-3162973b011325e70d646e947487a03b0e47524b01b650d4cdab313321e37631/skills/blender-h3-dcc"
WF = f"{SKILL}/scripts/m3_render_workflow.py"


def shot_dirs(root):
    root = Path(root)
    out = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "manifest.json").is_file() and (d / "preview_video.mp4").is_file():
            out.append(d)
    return out


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def cmd_preflight(root):
    dirs = shot_dirs(root)
    print(f"[preflight] {len(dirs)} shots")
    fails = []
    for d in dirs:
        rc, so, se = run([sys.executable, WF, "preflight",
                          "--source", str(d / "preview_video.mp4"),
                          "--manifest", str(d / "manifest.json"),
                          "--workdir", str(d)])
        if rc != 0:
            fails.append((d.name, se.strip()[:200]))
            print(f"  [FAIL] {d.name}: {se.strip()[:200]}", flush=True)
        else:
            pf = json.loads((d / "preflight.json").read_text(encoding="utf-8"))
            ev = pf.get("blender_structure_evidence") or {}
            inv = len(ev.get("objects") or []) if isinstance(ev, dict) else 0
            anchors = len(json.loads((d / "render_contract.json").read_text(encoding="utf-8"))["anchors"])
            print(f"  [OK] {d.name} anchors={anchors} ev_objs={inv}", flush=True)
    print(f"[preflight] done, fails={len(fails)}")
    return 1 if fails else 0


def cmd_prompt(root):
    dirs = shot_dirs(root)
    print(f"[prompt] {len(dirs)} shots")
    summary = []
    for d in dirs:
        rc, so, se = run([sys.executable, WF, "build-prompt",
                          "--contract", str(d / "render_contract.json"),
                          "--appearance", str(d / "appearance.json"),
                          "--output", str(d / "h3_prompt.txt")])
        report = d / "h3_prompt_budget.json"
        rep = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
        row = {
            "shot": d.name,
            "rc": rc,
            "char_count": rep.get("prompt_characters"),
            "within_budget": rep.get("within_budget"),
            "protected_content_valid": rep.get("protected_content_valid"),
            "ready_to_submit": rep.get("ready_to_submit"),
            "compression_factor": rep.get("compression_factor"),
            "invariant_errors": rep.get("invariant_errors"),
            "stderr": se.strip()[:300],
        }
        summary.append(row)
        flag = "OK " if rc == 0 else "FAIL"
        print(f"  [{flag}] {d.name} chars={row['char_count']} wb={row['within_budget']} "
              f"pcv={row['protected_content_valid']} rts={row['ready_to_submit']} "
              f"f={row['compression_factor']}", flush=True)
        if rc != 0:
            print(f"        {row['stderr']}", flush=True)
    (Path(root).parent / "prompt_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in summary if r["rc"] != 0]
    print(f"[prompt] done, fails={len(bad)}")
    return 1 if bad else 0


def cmd_check(root):
    dirs = shot_dirs(root)
    fails = []
    for d in dirs:
        rc, so, se = run([sys.executable, WF, "check-contract",
                          "--contract", str(d / "render_contract.json")])
        if rc != 0:
            fails.append((d.name, so.strip()[:400]))
            print(f"  [FAIL] {d.name}: {so.strip()[:400]}", flush=True)
    print(f"[check] done, fails={len(fails)}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["preflight", "prompt", "check"])
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    return {"preflight": cmd_preflight, "prompt": cmd_prompt, "check": cmd_check}[args.cmd](args.root)


if __name__ == "__main__":
    raise SystemExit(main())
