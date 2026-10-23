#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_q100_report.py —— Q100 交付报表生成器（只读）

产出两份交付件：
  reports/Q100_densify_metrics_U01_U02.json  —— 逐集「改前/改后」空窗指标
  reports/Q100_densify_anchor_table_U01_U02.md —— 新增字幕行 → D11 镜号 + visual_facts 原文 对照表

口径：
  · 「最长空窗」＝**全局**最长无字幕空窗（AI 角标行不计入），比逐镜裁剪口径更严；
  · 「空窗总」＝ 45s − 字幕覆盖时长（与 scripts/audit_dead_time.py 的 gap_total 同值）；
  · 「新增行」＝ 本岗本轮落盘的新增/改期字幕行（按 texts 清单逐条回指 D11）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _q100_plan import PLAN, OWNED  # noqa: E402

# 本岗作业开始时（2026-10-23 12:16~12:18）实测的「改前」基线（全局最长空窗/空窗总）
BEFORE = {
    "U01": {1: (7.4, 24.7), 2: (2.4, 7.8), 3: (12.8, 34.7), 4: (19.2, 37.9),
            5: (14.1, 34.4), 6: (24.2, 36.6), 7: (22.2, 37.2), 8: (13.8, 33.2)},
    "U02": {9: (10.1, 33.9), 10: (31.7, 33.5), 11: (21.5, 32.3), 12: (19.3, 35.2),
            13: (11.7, 33.2), 14: (23.3, 34.4), 15: (21.0, 30.6), 16: (22.6, 32.5)},
}
# 归属：mine=本岗本轮落盘；other=同岗另一实例本轮落盘
OWNER = {ep: "other" for ep in (2, 3, 4, 7)}


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
    return (max(lens) if lens else 0.0), round(sum(lens), 1)


def main():
    metrics = {}
    md = ["# Q100 字幕密度填充 · 新增行 → D11 镜号 + visual_facts 原文 对照表",
          "",
          "生成：2026-10-23（分镜导演岗 bot_1855d6ce9cdd）",
          "",
          "口径：每条新增字幕行都必须能指回**该镜 D11 `visual_facts` 里逐字存在**的一句；",
          "指不回去的行一律不许加（`scripts/densify_subtitles.py` 按此硬校验，写盘前中止）。",
          "",
          "新增行取自 D11 已写明的事实，**不加台词、不新增画面物件、不编数字**；",
          "对白行一条未加、时码一字未动（D09「每集不超过 4 句」不受突破）。",
          ""]

    for unit in ("U01", "U02"):
        d11 = json.load(open(os.path.join(ROOT, "units", unit, "D11.json"), encoding="utf-8"))
        d16 = json.load(open(os.path.join(ROOT, "units", unit, "D16.json"), encoding="utf-8"))
        m11 = {e["ep"]: e for e in d11["episodes"]}
        metrics[unit] = {"version": d16["version"], "episodes": {}}
        md.append(f"## {unit}（D16 {d16['version']}）")
        md.append("")
        for ep in d16["episodes"]:
            e11 = m11[ep["ep"]]
            lines = ep["subtitle_style"]["lines"]
            mx, tot = gap_stats(lines)
            bm, bt = BEFORE[unit][ep["ep"]]
            metrics[unit]["episodes"][str(ep["ep"])] = {
                "before_max_gap": bm, "before_gap_total": bt,
                "after_max_gap": mx, "after_gap_total": tot,
                "pass": (mx <= 4.0 and tot <= 12.0),
                "line_count": len(lines),
            }
            # 本岗本轮新增行（按 PLAN 逐条回指 D11）
            mine = []
            if str(ep["ep"]) in OWNED.get(unit, []):
                for (txt, typ, i0, o0, sid, anchor, note) in PLAN[unit][str(ep["ep"])]:
                    shot = next(s for s in e11["shots"] if int(s["shot_id"]) == sid)
                    vf = str(shot["visual_facts"])
                    assert anchor in vf, (unit, ep["ep"], txt, anchor)
                    # 该行在盘上的现值
                    row = next((l for l in lines if l.get("text") == txt), None)
                    mine.append({
                        "text": txt, "type": typ, "shot_id": sid,
                        "in_sec": row["in_sec"] if row else i0,
                        "out_sec": row["out_sec"] if row else o0,
                        "anchor": anchor,
                        "d11_visual_facts": vf,
                    })
            if not mine:
                continue
            md.append(f"### ep{ep['ep']:03d}")
            md.append("")
            md.append("| # | 新增字幕行 | 类型 | 挂镜 | 区间 | D11 visual_facts 原文（锚点句以 **加粗** 标出） |")
            md.append("|---|---|---|---|---|---|")
            for i, m in enumerate(mine, 1):
                vf = m["d11_visual_facts"]
                a = m["anchor"]
                k = vf.find(a)
                if k >= 0:
                    vf_mark = vf[:k] + "**" + a + "**" + vf[k + len(a):]
                else:
                    vf_mark = vf
                vf_mark = vf_mark.replace("|", "｜")
                md.append(f"| {i} | {m['text']} | {m['type']} | 镜{m['shot_id']} | "
                          f"{m['in_sec']}~{m['out_sec']}s | {vf_mark} |")
            md.append("")

    mp = os.path.join(ROOT, "reports", "Q100_densify_metrics_U01_U02.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ap = os.path.join(ROOT, "reports", "Q100_densify_anchor_table_U01_U02.md")
    with open(ap, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"✅ 写 {mp}")
    print(f"✅ 写 {ap}")
    for unit in ("U01", "U02"):
        for ep, v in metrics[unit]["episodes"].items():
            print(f"   {unit}-EP{int(ep):03d}  {v['before_max_gap']:.1f}/{v['before_gap_total']:.1f}"
                  f"  →  {v['after_max_gap']:.1f}/{v['after_gap_total']:.1f}"
                  f"   {'✅' if v['pass'] else '❌'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
