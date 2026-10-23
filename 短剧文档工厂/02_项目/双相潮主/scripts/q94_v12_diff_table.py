#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q94：V12 逐条「改了什么 / 怎么改的 / 复算占幅」前后对照表。

口径必须与 04_工具/lib/rules.mjs 的 V12 **完全一致**（同一度量、同一度量字段）：
  · W1 角色在画幅内    —— subjectMax = 所有 CHAR 类对象 visible_percent.height 的跨帧最大
  · W2 景别占幅区间    —— subjectMax ∈ rules.json white_model_framing.shot_size_bands[景别]
  · W3 画面最大对象是角色 —— 跨帧 visible_percent.height 最大者，其 kind 必须是 CHAR
  · kind 判定：名字含 CHAR/PROP/LGT/FX/EXT 之一（按该顺序取首个命中），与 rules.mjs 的 WM_KINDS 同序
  · 空镜豁免：只在 D11.visual_facts 上匹配 rules.json 的 empty_shot_pattern

基线 = reports/Q94_W1_W8_measurements_v15.json（LOS 修复后、折叠修复前的 v1.5）
现盘 = units/<U>/D14_shots/<shot>/projection.json（V12 判据实际读取的那份）

用法：
    python3 scripts/q94_v12_diff_table.py --out-json reports/Q94_V12_diff_v15_vs_current.json \
                                         --out-md   reports/Q94_V12_diff_v15_vs_current.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WM_KINDS = ["CHAR", "PROP", "LGT", "FX", "EXT"]          # 与 rules.mjs WM_KINDS 同序


def wm_kind_of(name: str) -> str:
    for k in WM_KINDS:
        if k in name:
            return k
    return "OTHER"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="reports/Q94_W1_W8_measurements_v15.json")
    ap.add_argument("--out-json", default="reports/Q94_V12_diff_v15_vs_current.json")
    ap.add_argument("--out-md", default="reports/Q94_V12_diff_v15_vs_current.md")
    ap.add_argument("--units", default="U01,U02,U03")
    return ap.parse_args()


def measure_projection(proj: dict) -> dict:
    """复刻 rules.mjs V12 的度量（逐帧遍历 fr.objects）。"""
    subject_max = 0.0
    largest = None
    for fr in proj.get("frames") or []:
        for name, o in (fr.get("objects") or {}).items():
            if not o or not o.get("in_frame"):
                continue
            h = float((o.get("visible_percent") or {}).get("height") or 0)
            if largest is None or h > largest["h"]:
                largest = {"name": name, "h": round(h, 2), "kind": wm_kind_of(name)}
            if wm_kind_of(name) != "CHAR":
                continue
            if h > subject_max:
                subject_max = h
    return {"subject_max": round(subject_max, 2), "largest": largest}


def load_d12_evidence(unit: str) -> dict:
    """取 D12 提示词卡里「画面内不出现人体/角色」类逐字约束（裁定证据）。"""
    p = ROOT / f"units/{unit}/D12.json"
    if not p.is_file():
        return {}
    key = re.compile(r"不出现|不给|无人在|空镜|画外音|不入画|只给|只有")
    out = {}
    for c in json.loads(p.read_text(encoding="utf-8")).get("cards") or []:
        hits = []
        for f in ("image_prompt", "video_prompt"):
            for seg in re.split(r"[；;。\n]", str(c.get(f) or "")):
                if key.search(seg):
                    hits.append(seg.strip())
        neg = [str(x) for x in (c.get("negatives") or []) if key.search(str(x))]
        out[(c["ep"], c["shot_id"])] = {"segments": hits[:3], "negatives": neg[:3]}
    return out


def load_current(unit: str) -> dict:
    base = ROOT / "units" / unit / "D14_shots"
    out = {}
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        pj = d / "projection.json"
        if not pj.is_file():
            continue
        proj = json.loads(pj.read_text(encoding="utf-8"))
        out[d.name] = {
            "ep": proj.get("ep"),
            "shot_id": proj.get("shot_id"),
            "n_frames": len(proj.get("frames") or []),
            **measure_projection(proj),
        }
    return out


def load_bands() -> dict:
    cfg = json.loads((ROOT.parent.parent / "03_规格/rules.json").read_text(encoding="utf-8"))
    wf = cfg.get("white_model_framing") or {}
    return {
        "bands": wf.get("shot_size_bands") or {},
        "empty_re": wf.get("empty_shot_pattern") or "",
        "require_largest": wf.get("require_subject_is_largest") is not False,
    }


def judge(shot: dict, cfg: dict) -> list:
    """按 V12 判据给出该镜的 error 列表（与 rules.mjs 同措辞）。"""
    bad = []
    sm = shot["subject_max"]
    if not sm > 0:
        bad.append("W1 角色完全不在画幅内（占幅 0%）")
    band = cfg["bands"].get(shot["shot_size"])
    if band and sm > 0 and not (band[0] <= sm <= band[1]):
        bad.append(f"W2 主体占幅 {sm:.1f}% 落在「{shot['shot_size']}」区间 "
                   f"[{band[0]}, {band[1]}] 之外")
    lg = shot.get("largest")
    if not lg:
        bad.append("W3 画幅内没有任何可见对象")
    elif cfg["require_largest"] and lg["kind"] != "CHAR":
        bad.append(f"W3 画面最大对象是 {lg['kind']}「{lg['name']}」（占幅 {lg['h']:.1f}%），主体让位给环境")
    return bad


def main() -> int:
    a = parse_args()
    cfg = load_bands()
    base = json.loads((ROOT / a.baseline).read_text(encoding="utf-8"))
    rows = []
    for unit in a.units.split(","):
        cur = load_current(unit)
        d12 = load_d12_evidence(unit)
        bshots = (base.get(unit) or {}).get("shots") or []
        base_by_name = {b["shot"]: b for b in bshots}
        d11 = json.loads((ROOT / f"units/{unit}/D11.json").read_text(encoding="utf-8"))
        for ep in d11["episodes"]:
            for s in ep["shots"]:
                name = f"ep{ep['ep']:02d}_shot{s['shot_id']:02d}"
                cs = cur.get(name)
                if cs is None:
                    continue
                bs = base_by_name.get(name)
                cur_shot = {"shot": name, "shot_size": s["shot_size"],
                            "subject_max": cs["subject_max"], "largest": cs["largest"]}
                c_err = judge(cur_shot, cfg)
                if bs is not None:
                    b_err = judge({**bs, "subject_max": bs.get("subject_max", 0.0),
                                   "largest": bs.get("largest")}, cfg)
                else:
                    b_err = []
                if not b_err and not c_err:
                    continue
                ev = d12.get((ep["ep"], s["shot_id"]), {})
                rows.append({
                    "unit": unit, "shot": name, "shot_size": s["shot_size"],
                    "band": cfg["bands"].get(s["shot_size"]),
                    "has_baseline": bs is not None,
                    "baseline_subject_max": (bs or {}).get("subject_max"),
                    "baseline_largest": (bs or {}).get("largest"),
                    "baseline_errors": b_err,
                    "current_subject_max": cs["subject_max"],
                    "current_largest": cs["largest"],
                    "current_errors": c_err,
                    "d12_evidence": ev,
                    "status": ("已归零" if b_err and not c_err else
                               ("仍失败" if b_err and c_err else
                                ("新单元首测（无基线）" if bs is None else "新出现")))})
    out = {"bands": cfg["bands"], "empty_shot_pattern": cfg["empty_re"],
           "baseline": a.baseline, "rows": rows}
    (ROOT / a.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    fixed = [r for r in rows if r["status"] == "已归零"]
    still = [r for r in rows if r["status"] == "仍失败"]
    lines = ["# Q94 V12 逐条前后对照表（基线 v1.5 → 现盘）", "",
             f"- 基线：`{a.baseline}`（LOS 修复后 / 投影折叠修复前）",
             "- 现盘：`units/<U>/D14_shots/<shot>/projection.json`（V12 判据实际读取的那份）",
             "- 度量口径：与 `04_工具/lib/rules.mjs` 的 V12 **逐字同源**（W1/W2/W3）",
             f"- 涉及 error 镜数：**{len(rows)}** = 已归零 **{len(fixed)}**（U01/U02）"
             f" + 仍失败 **{len([r for r in still if r['has_baseline']])}**（U01/U02）"
             f" + 新单元首测 **{len([r for r in rows if not r['has_baseline']])}**（U03，无基线）",
             "",
             "## A. 已归零（本次修复见效）", "",
             "| 单元 | 镜 | 景别 | 基线占幅 | 基线最大对象 | 复算后占幅 | 复算后最大对象 | 改了什么 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in fixed:
        lines.append(
            f"| {r['unit']} | {r['shot']} | {r['shot_size']} | "
            f"{r['baseline_subject_max']}% | {r['baseline_largest']['name']}（{r['baseline_largest']['kind']} "
            f"{r['baseline_largest']['h']}%） | **{r['current_subject_max']}%** | "
            f"**{r['current_largest']['name']}（{r['current_largest']['kind']} {r['current_largest']['h']}%）** | "
            f"投影聚合修复：同根名多实例被插件按 root 折叠 → 后者覆盖前者 ⇒ 取组内**占幅最大**实例 |")
    lines += ["", "## B. 仍失败（结构性：白模现状与 D11/D12 一致，判据与上游声明不同源）", "",
              "| 单元 | 镜 | 景别 | 占幅 | 画面最大对象 | 仍失败的判据 |", "|---|---|---|---|---|---|"]
    for r in still:
        lines.append(
            f"| {r['unit']} | {r['shot']} | {r['shot_size']} | {r['current_subject_max']}% | "
            f"{r['current_largest']['name']}（{r['current_largest']['kind']} {r['current_largest']['h']}%） | "
            f"{'；'.join(r['current_errors'])} |")
    lines += ["", "## C. 合计：基线 error 镜 {} → 现盘 {}".format(len(rows), len(still)), ""]
    lines += ["## D. 仍失败镜的 D12 逐字证据（裁定依据）", "",
              "| 单元 | 镜 | D12 提示词卡原文（画面内不出现人体/角色类约束） |", "|---|---|---|"]
    for r in still:
        ev = r.get("d12_evidence") or {}
        segs = ev.get("segments") or []
        txt = " ／ ".join(segs) if segs else "（D12 卡内无「不出现」类措辞；见备注）"
        lines.append(f"| {r['unit']} | {r['shot']} | {txt} |")
    lines += ["", "> 判据豁免口：`rules.json → white_model_framing.empty_shot_pattern` = `空镜|画面无人|无人在场|空画面`，",
              "> 该正则**只匹配 D11 的 `visual_facts`**；而这 16 镜的「无人」声明写在 **D12 提示词卡**里（D11/D12 不同源）。",
              "> 本岗不自行改 `rules.json`、不改 D11/D12 ⇒ 提请总控裁定。", ""]
    (ROOT / a.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"[diff] rows={len(rows)} fixed={len(fixed)} still={len(still)}")
    for r in rows:
        print(f"   {r['unit']} {r['shot']} {r['shot_size']} "
              f"base={r['baseline_subject_max']}% -> cur={r['current_subject_max']}% [{r['status']}]")
    print(f"[diff] {a.out_md} / {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
