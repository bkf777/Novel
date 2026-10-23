#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1–W8 实测（口径严格对齐 04_工具/lib/rules.mjs 的 V12 与施工图 §4）。

用法：
  python3 scripts/measure_white_model_W.py --unit U01 [--unit U02] [--md out.md] [--json out.json]

判定口径（与 V12 同源）：
  · 主体占幅 subjectMax = 角色代理体 visible_percent.height 在**全部采样帧**上的最大值
  · 画面最大对象 largest = 全部 in_frame 对象 visible_percent.height 的最大值（首个并列者胜）
  · 空镜豁免：D11 visual_facts 命中 rules.json 的 empty_shot_pattern ⇒ 跳过 W1/W2/W3
  · W4：相邻采样帧 rotation_euler_deg 三分量最大角差（仅 in_frame 且带该字段的 CHAR 参与）
  · W5：in-frame CHAR 的 pose ∈ rules.json 的 pose_vocabulary
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # 短剧文档工厂/
PROJ = ROOT / "02_项目" / "双相潮主"
WM_KINDS = ["CHAR", "PROP", "LGT", "FX", "EXT"]


def wm_kind(name: str) -> str:
    for k in WM_KINDS:
        if k in name:
            return k
    return "OTHER"


def angle_delta(a: float, b: float) -> float:
    d = abs(float(a) - float(b)) % 360
    return 360 - d if d > 180 else d


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_content(unit: str):
    p = PROJ / "scripts" / f"white_model_content_{unit}.py"
    spec = importlib.util.spec_from_file_location(f"wm_{unit}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure_unit(unit: str, rules: dict):
    cfg = rules["white_model_framing"]
    bands = cfg["shot_size_bands"]
    max_jump = float(cfg.get("max_rotation_jump_deg", 30))
    require_largest = cfg.get("require_subject_is_largest", True) is not False
    vocab = cfg.get("pose_vocabulary") or []
    empty_re = re.compile(cfg["empty_shot_pattern"]) if cfg.get("empty_shot_pattern") else None

    d11 = load_json(PROJ / "units" / unit / "D11.json")
    shots = {}
    for ep in d11["episodes"]:
        for s in ep["shots"]:
            shots[f"ep{ep['ep']:02d}_shot{s['shot_id']:02d}"] = s
    shots_root = PROJ / "units" / unit / "D14_shots"

    content = load_content(unit)
    # W6：CHAR_ANIM 首帧 pose vs CHARS pose（静态兜底表）
    w6_conflicts = []
    for (sc, gsn), anim in (getattr(content, "CHAR_ANIM", {}) or {}).items():
        chars = {c[0]: c for c in (getattr(content, "CHARS", {}) or {}).get((sc, gsn), [])}
        for en, keys in anim.items():
            st = chars.get(en)
            if st and st[6] != keys[0][4]:
                w6_conflicts.append(f"{sc} g{gsn} {en}: ANIM「{keys[0][4]}」≠ CHARS「{st[6]}」")

    rows = []
    for d in sorted(os.listdir(shots_root)):
        sd = shots_root / d
        pj = sd / "projection.json"
        if not pj.is_file():
            continue
        proj = load_json(pj)
        src = shots.get(d)
        size = (src or {}).get("shot_size", "")
        facts = str((src or {}).get("visual_facts", "") or "")
        exempt = bool(empty_re and empty_re.search(facts))

        subject_max = 0.0
        largest = None
        rot_seq = {}
        poses = set()
        for fr in proj.get("frames", []):
            for name, o in (fr.get("objects") or {}).items():
                if not o or not o.get("in_frame"):
                    continue
                h = float((o.get("visible_percent") or {}).get("height", 0) or 0)
                if largest is None or h > largest["h"]:
                    largest = {"name": name, "h": h, "kind": wm_kind(name)}
                if wm_kind(name) != "CHAR":
                    continue
                subject_max = max(subject_max, h)
                rot = o.get("rotation_euler_deg")
                if isinstance(rot, list) and len(rot) == 3:
                    rot_seq.setdefault(name, []).append(rot)
                if isinstance(o.get("pose"), str):
                    poses.add(o["pose"])

        band = bands.get(size)
        w1 = subject_max > 0
        # V12 口径：subjectMax == 0 时**不判 W2**（角色没入画是 W1 的事）
        # V12 口径：subjectMax == 0 时**不判 W2**（角色没入画归 W1）⇒ 记 N/A
        w2_na = subject_max <= 0
        w2 = (None if w2_na else
              bool(band and subject_max >= band[0] and subject_max <= band[1]))
        w3 = bool(largest and largest["kind"] == "CHAR") if require_largest else True
        jump = 0.0
        jump_who = ""
        for name, seq in rot_seq.items():
            for i in range(1, len(seq)):
                j = max(angle_delta(seq[i][k], seq[i - 1][k]) for k in range(3))
                if j > jump:
                    jump, jump_who = j, name
        w4 = jump <= max_jump
        bad_pose = sorted(p for p in poses if vocab and p not in vocab)
        w5 = not bad_pose

        rows.append({
            "shot": d, "shot_size": size, "exempt": exempt,
            "subject_max": round(subject_max, 2),
            "band": band, "w1": w1, "w2": w2, "w2_na": w2_na,
            "w3": w3, "w4": w4, "w5": w5,
            "largest": largest, "jump": round(jump, 2), "jump_who": jump_who,
            "poses": sorted(poses), "bad_pose": bad_pose,
            "n_frames": len(proj.get("frames", [])),
            "n_objects": len((proj.get("frames") or [{}])[0].get("objects", {})) if proj.get("frames") else 0,
            "has_rot": bool(rot_seq), "has_pose": bool(poses),
        })
    return rows, w6_conflicts


def measure_w7_w8(unit: str):
    d14_path = PROJ / "units" / unit / "D14.json"
    shots_root = PROJ / "units" / unit / "D14_shots"
    d14 = load_json(d14_path) if d14_path.is_file() else {}
    disk = sorted(d for d in os.listdir(shots_root) if (shots_root / d).is_dir())
    expect = ["appearance.json", "h3_prompt.txt", "h3_prompt_budget.json", "manifest.json",
              "package.json", "preflight.json", "projection.json", "render_contract.json",
              "scene_spec.json", "shot_spec.json", "preview_video.mp4"]
    missing = {}
    for d in disk:
        miss = [f for f in expect if not (shots_root / d / f).is_file()]
        if miss:
            missing[d] = miss
    idx = {f"ep{s['ep']:02d}_shot{s['shot_id']:02d}" for s in d14.get("shots", [])}
    diff = sorted(set(idx) ^ set(disk))
    w7_ok = (not missing) and (not diff) and len(disk) == len(idx)
    checks = d14.get("check_results", [])
    # D14 的 check_contract 是字符串（PASS/FAIL），不是 dict
    w8_bad = [c for c in checks
              if str(c.get("check_contract", "")).upper() != "PASS"
              or not (c.get("within_budget") and c.get("protected_content_valid")
                      and c.get("ready_to_submit"))]
    return {
        "shots_on_disk": len(disk), "shots_in_index": len(idx),
        "missing_files": missing, "index_diff": diff,
        "w7_ok": bool(w7_ok),
        "w8_total": len(checks), "w8_bad": [c.get("shot") for c in w8_bad],
        "w8_ok": bool(not w8_bad and checks),
        "chars": [c.get("h3_prompt_characters") for c in checks],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", action="append", required=True)
    ap.add_argument("--md", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    rules = load_json(ROOT / "03_规格" / "rules.json")

    out = {}
    md = []
    md.append("# W1–W8 实测结果（Q94 白模重建）\n")
    md.append(f"判据真源：`03_规格/rules.json → white_model_framing`；"
              f"实现口径对齐 `04_工具/lib/rules.mjs` 的 V12。\n")
    for unit in args.unit:
        rows, w6 = measure_unit(unit, rules)
        w78 = measure_w7_w8(unit)
        out[unit] = {"shots": rows, "w6_conflicts": w6, "w78": w78}
        md.append(f"\n## {unit}\n")
        md.append("| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |")
        md.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            lg = r["largest"]
            lg_txt = f"{lg['name']} {round(lg['h'],1)}% {lg['kind']}" if lg else "—"
            md.append(
                f"| {r['shot']} | {r['shot_size'] or '—'}"
                f"{'（空镜豁免）' if r['exempt'] else ''} | {r['subject_max']}% | "
                f"{r['band'] if r['band'] else '—'} | "
                f"{'OK' if r['w1'] else 'NG'} | "
                f"{'—' if r['w2_na'] else ('OK' if r['w2'] else 'NG')} | "
                f"{'OK' if r['w3'] else 'NG'} | {r['jump']}° {'OK' if r['w4'] else 'NG'} | "
                f"{'OK' if r['w5'] else 'NG（' + '/'.join(r['bad_pose']) + '）'} | {lg_txt} |")
        n = len(rows)
        def cnt(k):
            if k == "w2":
                return sum(1 for r in rows if r["w2"] is True)
            return sum(1 for r in rows if r[k])
        na2 = sum(1 for r in rows if r["w2_na"])
        md.append(f"\n**W1 {cnt('w1')}/{n}｜W2 {cnt('w2')}/{n - na2}"
                  f"（另 {na2} 镜角色未入画，W2 不判）｜W3 {cnt('w3')}/{n}｜"
                  f"W4 {cnt('w4')}/{n}｜W5 {cnt('w5')}/{n}**")
        md.append(f"\n- W6 姿态冲突：**{len(w6)} 处** " +
                  ("（全部清零）" if not w6 else "→ " + "；".join(w6)))
        md.append(f"- W7 逐镜包：磁盘 {w78['shots_on_disk']} 镜 / 索引 {w78['shots_in_index']} 镜，"
                  f"缺文件 {sum(len(v) for v in w78['missing_files'].values())} 处，索引差异 {w78['index_diff'] or '无'} ⇒ "
                  f"**{'合格' if w78['w7_ok'] else '不合格'}**")
        md.append(f"- W8 合同有效：{w78['w8_total'] - len(w78['w8_bad'])}/{w78['w8_total']} ⇒ "
                  f"**{'合格' if w78['w8_ok'] else '不合格 ' + str(w78['w8_bad'])}**")
        md.append(f"- 投影字段：rotation_euler_deg 已提供={any(r['has_rot'] for r in rows)}，"
                  f"pose 已提供={any(r['has_pose'] for r in rows)}（V12 的两条 warning 应消失）")
        ng = {"W1": [r["shot"] for r in rows if not r["w1"] and not r["exempt"]],
              "W2": [r["shot"] for r in rows if r["w2"] is False and not r["exempt"]],
              "W3": [r["shot"] for r in rows if not r["w3"] and not r["exempt"]],
              "W4": [r["shot"] for r in rows if not r["w4"]],
              "W5": [r["shot"] for r in rows if not r["w5"]]}
        md.append(f"\n**不合格镜号**：W1 {ng['W1'] or '无'}；W2 {ng['W2'] or '无'}；"
                  f"W3 {ng['W3'] or '无'}；W4 {ng['W4'] or '无'}；W5 {ng['W5'] or '无'}")

    text = "\n".join(md)
    if args.md:
        Path(args.md).write_text(text + "\n", encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
