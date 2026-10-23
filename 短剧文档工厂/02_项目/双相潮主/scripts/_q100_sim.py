#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_q100_sim.py —— Q100 填充方案的离线校验＋空窗预演（只读，不写盘）

口径与 scripts/densify_subtitles.py 一致：
  · 锚点必须逐字出现在该集该镜的 D11 visual_facts 中
  · 挂载区间必须落在该镜的真实可见区间（D16 cuts 推导）
  · 停留 ≥1.2s；单行 ≤15 字；与既有行（左闭右开）不重叠
空窗口径与总控一致（scripts/audit_dead_time.py 的「空窗总」口径）：
  · AI 角标行不计入覆盖
  · 「最长空窗」取**全局**最长空窗（比逐镜裁剪口径更严，逐镜口径随之必然达标）
  · 「空窗总」＝ 45s − 字幕覆盖时长
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _q100_plan import PLAN, OWNED  # noqa: E402

spec = importlib.util.spec_from_file_location("ds", os.path.join(HERE, "densify_subtitles.py"))
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)


def gap_stats(lines, total=45.0):
    iv = sorted((float(l["in_sec"]), float(l["out_sec"]))
                for l in lines if l.get("type") != "角标")
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    gaps, cur = [], 0.0
    for a, b in merged:
        if a - cur > 1e-9:
            gaps.append((cur, a))
        cur = max(cur, b)
    if total - cur > 1e-9:
        gaps.append((cur, total))
    lens = [round(b - a, 1) for a, b in gaps]
    return (max(lens) if lens else 0.0), round(sum(lens), 1), gaps


def per_shot_max(lines, bounds):
    worst = 0.0
    for (a, b, _s) in bounds:
        iv = sorted((float(l["in_sec"]), float(l["out_sec"]))
                    for l in lines if l.get("type") != "角标")
        merged = []
        for x, y in iv:
            if merged and x <= merged[-1][1] + 1e-9:
                merged[-1][1] = max(merged[-1][1], y)
            else:
                merged.append([x, y])
        cur, g = a, []
        for x, y in merged:
            if x > cur:
                g.append(min(x, b) - cur)
            cur = max(cur, y)
        if cur < b:
            g.append(b - cur)
        worst = max(worst, max([v for v in g if v > 0.05] or [0.0]))
    return round(worst, 1)


def main():
    problems = []
    summary = []
    for unit in ("U01", "U02"):
        d11 = json.load(open(os.path.join(ROOT, "units", unit, "D11.json"), encoding="utf-8"))
        d16 = json.load(open(os.path.join(ROOT, "units", unit, "D16.json"), encoding="utf-8"))
        m11 = {e["ep"]: e for e in d11["episodes"]}
        for ep in d16["episodes"]:
            e11 = m11[ep["ep"]]
            ss = ep["subtitle_style"]
            lines = ss["lines"]
            shots = sorted(e11["shots"], key=lambda s: s["shot_id"])
            vis = ds.shot_visibility(ep.get("cuts") or [], shots)
            facts = {int(s["shot_id"]): str(s.get("visual_facts") or "") for s in shots}
            min_dwell = float(ss.get("min_dwell_sec", 1.2))
            max_chars = int(ss.get("max_chars_per_line", 15))
            bounds = []
            t = 0.0
            for s in shots:
                bounds.append((t, t + float(s["duration_sec"]), int(s["shot_id"])))
                t += float(s["duration_sec"])

            before_max, before_tot, _ = gap_stats(lines)
            new_lines = list(lines)
            plan = PLAN.get(unit, {}).get(str(ep["ep"])) if str(ep["ep"]) in OWNED.get(unit, []) else None
            if plan:
                for (txt, typ, i0, o0, sid, anchor, note) in plan:
                    tag = f"{unit} ep{ep['ep']:03d} 「{txt}」"
                    if anchor not in facts.get(sid, ""):
                        problems.append(f"{tag} 锚点「{anchor}」不在 D11 镜{sid} visual_facts 中")
                    if not any(a <= i0 and o0 <= b and s == sid for a, b, s in vis):
                        problems.append(f"{tag} 区间 {i0}~{o0} 不在镜{sid} 可见区间 "
                                        f"{[(a, b) for a, b, s in vis if s == sid]}")
                    if round(o0 - i0, 2) < min_dwell - 1e-9:
                        problems.append(f"{tag} 停留 {round(o0 - i0, 2)}s < {min_dwell}s")
                    if len(txt) > max_chars:
                        problems.append(f"{tag} {len(txt)} 字 > {max_chars} 字上限")
                    if any(l.get("text") == txt for l in lines):
                        problems.append(f"{tag} 文案与既有行重复")
                    clash = next((l for l in lines
                                  if l.get("type") != "角标"
                                  and ds.overlaps(i0, o0, float(l["in_sec"]), float(l["out_sec"]))), None)
                    if clash:
                        problems.append(f"{tag} 与既有行「{clash.get('text')}」"
                                        f"{clash['in_sec']}~{clash['out_sec']}s 重叠")
                    # 术语首用集前禁用（D05：ep013–ep040 字幕面不得出现「律条」）
                    if 13 <= ep["ep"] <= 40 and "律条" in txt:
                        problems.append(f"{tag} 命中 D05 术语首用集前禁用词「律条」")
                    # 禁词/贬称
                    for w in ("血肉模糊", "血肉横飞", "断肢", "残肢", "内脏", "器官",
                              "喷溅", "血浆", "废物", "垃圾", "蠢货", "贱", "杂种"):
                        if w in txt:
                            problems.append(f"{tag} 命中禁词/贬称「{w}」")
                    new_lines.append({"type": typ, "text": txt, "in_sec": i0, "out_sec": o0,
                                      "shot_id": sid})
            after_max, after_tot, gaps = gap_stats(new_lines)
            ps = per_shot_max(new_lines, bounds)
            n_new = len(new_lines) - len(lines)
            summary.append((unit, ep["ep"], before_max, before_tot, after_max, after_tot, ps, n_new))
            if after_max > 4.0:
                problems.append(f"{unit} ep{ep['ep']:03d} 改后全局最长空窗 {after_max}s > 4.0s")
            if after_tot > 12.0:
                problems.append(f"{unit} ep{ep['ep']:03d} 改后空窗总 {after_tot}s > 12.0s")
            if ps > 4.0:
                problems.append(f"{unit} ep{ep['ep']:03d} 改后逐镜最长空窗 {ps}s > 4.0s")

    print(f"{'集':>10} {'改前最长':>8} {'改前总':>7} | {'改后最长':>8} {'改后总':>7} "
          f"{'逐镜最长':>8} {'新增行':>6}  判定")
    for (unit, ep, bm, bt, am, at, ps, n) in summary:
        ok = "✅ 达标" if (am <= 4.0 and at <= 12.0 and ps <= 4.0) else "❌ NG"
        print(f"{unit}-EP{ep:<4} {bm:>8.1f} {bt:>7.1f} | {am:>8.1f} {at:>7.1f} "
              f"{ps:>8.1f} {n:>6}  {ok}")
    print()
    if problems:
        print(f"❌ {len(problems)} 条问题：")
        for p in problems:
            print("   -", p)
        return 1
    print("✅ 全部校验通过（锚点 / 可见区间 / 停留 / 字数 / 重叠 / 术语 / 禁词 / 空窗判据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
