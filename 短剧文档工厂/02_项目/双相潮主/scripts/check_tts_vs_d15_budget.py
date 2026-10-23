#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_tts_vs_d15_budget.py —— 「实际 TTS 时长 vs D15 dur_sec 预算」只读比对

派活来源
  企划合规 2026-10-23 03:35（batch_647000ba9193 / request_id sxcz-u02-w2-status-d15tts-0335）
  边界三条（逐条遵守）：
    ① 只读比对，**不合成 TTS/BGM/音频、不调用任何付费生成** —— 本脚本只跑 ffprobe 读既有文件；
    ② **不改 D15/D16**（跨岗改动须上游裁决）—— 本脚本只出报告，不写任何交付物；
    ③ `--unit` 参数化、**禁单元专属副本**（S12）—— 见下方 _guard_no_unit_copy()。

  ⚠️ 与 TOOL-04 裁决的关系：TOOL-04 于 03:30 裁「归口成片阶段、文档工厂侧不排期不做」，
    其**理由**是「比对一旦要跑就会触及实际音频产物」。该前提已变化：U01 预演音频 120 条
    已于 2026-10-23 02:30–03:16 落盘（preview/{unit}_tts/audio/），比对因此是**纯只读**，
    不触及合成环节。故本轮按总控 03:35 派活执行，不新增合成排期。

判定基准（唯一口径，写在报告 basis 字段里，便于第三方复算）
  * 预算      = D15 voice_over[].dur_sec（标称 0.1s 网格）
  * 契约上限  = D15 voice_over[].at_sec + dur_sec（该值同时是 D16 对白字幕 out_sec）
  * 实测      = ffprobe format=duration（毫秒级精度，**只信实测、不信 items.json 的 dur 字段**
                 —— 实测已发现两者不一致，故 items.json 的 dur 一律不作判定输入）
  * 归一      = actual_nominal = ceil(actual × 10) / 10（0.1s 标称网格**向上**取整）
                 理由：浮点尾差不是时码精度问题（31.4+1.3 实算 ≠ 32.7），任何按浮点位相等的
                 写法都会误报；向上取整保证「实际超出预算」不会被网格吸收掉。
  * 判定      = actual_nominal > 预算 → **契约破坏（ERROR）**：配音将晚于 D16 字幕出点结束
                 actual_nominal == 预算 → 贴边零余量（WARN）
                 actual_nominal < 预算 → 合规，余量 = 预算 − actual_nominal
  * 处置边界  = 本脚本只报告；**不得改 D16 时码**（字幕时码由分镜导演定）。
                 修法二选一须上游裁定：① 缩短该句配音使实测 ≤ 预算；② 上调 D15 预算并同步
                 D16 对应行 out_sec（跨岗改动走裁决流程）。

退出码
  0 = 无超预算（含仅 WARN）｜1 = 存在契约破坏（超预算）｜2 = 参数／IO／前置条件错误

用法
  python3 scripts/check_tts_vs_d15_budget.py --project . --unit U01 [--out report.json]
"""

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys

GRID = 0.1          # 标称网格精度（秒）
MIN_DWELL_SEC = 1.2  # D16 字幕最小停留（秒），用于契约影响判定


# ── 工具 ─────────────────────────────────────────────────────────────────────
def grid_ceil(x):
    """向上取整到 0.1s 标称网格（消除浮点尾差，且不吞掉真实超支）。"""
    return round(math.ceil(round(float(x) / GRID, 6)) * GRID, 1)


def grid_round(x):
    """就近取整到 0.1s 标称网格。"""
    return round(round(float(x) / GRID) * GRID, 1)


def dur_of(path):
    """实测音频时长（秒）。复用 build_audio_u01.py 的 ffprobe 调用方式。"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 守卫：禁单元专属副本（S12）────────────────────────────────────────────────
def _guard_no_unit_copy(script_dir):
    """S12：同一脚本只留一份，跨单元靠 --unit 参数化，禁止 _u02 这类单元专属副本。"""
    copies = []
    for p in glob.glob(os.path.join(script_dir, "check_tts_vs_d15_budget_*.py")):
        copies.append(os.path.basename(p))
    if copies:
        print("[FATAL] 检出单元专属副本，违反 S12（须用 --unit 参数化）：%s" % ", ".join(copies),
              file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="项目目录（含 units/ 与 preview/）")
    ap.add_argument("--unit", required=True, help="单元号，如 U01")
    ap.add_argument("--out", default=None, help="报告 JSON 落盘路径（可选）")
    args = ap.parse_args()

    P = os.path.abspath(args.project)
    u = args.unit

    if not _guard_no_unit_copy(os.path.dirname(os.path.abspath(__file__))):
        return 2

    d15_path = os.path.join(P, "units", u, "D15.json")
    d09_path = os.path.join(P, "units", u, "D09.json")
    d16_path = os.path.join(P, "units", u, "D16.json")
    items_path = os.path.join(P, "preview", "%s_tts" % u, "items.json")

    for p in (d15_path, d09_path, d16_path):
        if not os.path.exists(p):
            print("[FATAL] 缺文件：%s（该单元是否已开工？）" % p, file=sys.stderr)
            return 2
    if not os.path.exists(items_path):
        print("[FATAL] 缺预演音频清单：%s —— 该单元尚无预演音频，无法做「实测时长」比对"
              % items_path, file=sys.stderr)
        return 2

    d15 = load(d15_path)
    d09 = load(d09_path)
    d16 = load(d16_path)
    items = load(items_path)

    # ── 映射：D15 voice_over.line_ref → D09 lines → 预演音频条目 ──────────────
    d09_lines = {(l["ep"], l["idx"]): l for l in d09.get("lines", [])}
    audio_by_text = {}
    stale_items = []
    for it in items:
        if it.get("kind") == "dialogue":
            audio_by_text[(it["ep"], it["text"])] = it
        if it.get("stale_audio"):
            stale_items.append(it)
    # 旧音频条目：台词已被上游改写，items.json 里留着旧句音频 → 按新句反查
    stale_by_new_text = {(it["ep"], it.get("stale_new_text")): it for it in stale_items}

    # D16 对白字幕行（用于契约影响判定）
    sub_by_key = {}
    for ep in d16["episodes"]:
        for ln in ep["subtitle_style"].get("lines", []):
            if ln.get("type") == "对白":
                sub_by_key[(ep["ep"], ln.get("shot_id"), ln.get("char_id"),
                            grid_round(ln["in_sec"]))] = ln

    rows = []
    missing_audio = []
    for ep in d15["episodes"]:
        e = ep["ep"]
        for v in ep.get("voice_over", []):
            m = re.match(r"D09 ep(\d+) #(\d+)", v.get("line_ref", ""))
            if not m:
                missing_audio.append({"ep": e, "line_ref": v.get("line_ref"),
                                      "reason": "line_ref 格式不可解析"})
                continue
            ep_idx, idx = int(m.group(1)), int(m.group(2))
            line = d09_lines.get((ep_idx, idx))
            if line is None:
                missing_audio.append({"ep": e, "line_ref": v.get("line_ref"),
                                      "reason": "D09 无对应 lines 条目"})
                continue
            it = audio_by_text.get((ep_idx, line["text"]))
            if it is None:
                stale = stale_by_new_text.get((ep_idx, line["text"]))
                if stale is not None:
                    missing_audio.append({
                        "ep": e, "line_ref": v.get("line_ref"),
                        "reason": "旧音频待出片阶段重合成（items.json 旧句条目已标注 stale_audio）",
                        "text": line["text"],
                        "stale_item_id": stale.get("id"),
                        "stale_old_text": stale.get("text"),
                        "stale_reason": stale.get("stale_reason"),
                        "stale_upstream": stale.get("stale_upstream"),
                    })
                else:
                    missing_audio.append({"ep": e, "line_ref": v.get("line_ref"),
                                          "reason": "预演音频无对应 dialogue 条目",
                                          "text": line["text"]})
                continue

            apath = it.get("audio") or os.path.join(P, "preview", "%s_tts" % u,
                                                     "audio", it["id"] + ".mp3")
            if not os.path.exists(apath):
                missing_audio.append({"ep": e, "line_ref": v.get("line_ref"),
                                      "reason": "音频文件不存在：%s" % apath})
                continue

            actual = dur_of(apath)
            if actual is None:
                missing_audio.append({"ep": e, "line_ref": v.get("line_ref"),
                                      "reason": "ffprobe 未能读取时长：%s" % apath})
                continue

            budget = grid_round(v["dur_sec"])
            at = grid_round(v["at_sec"])
            nominal = grid_ceil(actual)
            slack = round(budget - nominal, 1)
            items_dur = it.get("dur")
            items_dur_delta = (round(float(items_dur) - actual, 3)
                               if items_dur is not None else None)

            if nominal > budget:
                verdict = "契约破坏"
                level = "ERROR"
            elif nominal == budget:
                verdict = "贴边零余量"
                level = "WARN"
            else:
                verdict = "合规"
                level = "OK"

            # D16 契约影响：字幕 out_sec ＝ 配音 at_sec＋dur_sec；实际配音结束 = at_sec＋actual
            sub = sub_by_key.get((e, v.get("shot_id"), v.get("char_id"), at))
            sub_out = grid_round(sub["out_sec"]) if sub else None
            sub_out_matches = (sub_out is not None
                               and abs(sub_out - grid_round(at + budget)) < 1e-6)
            actual_end = round(at + actual, 3)
            sub_end = grid_round(at + budget)
            gap = round(actual_end - sub_end, 3) if sub_out is not None else None

            rows.append({
                "ep": e, "line_ref": v.get("line_ref"), "char_id": v.get("char_id"),
                "shot_id": v.get("shot_id"), "text": line["text"],
                "at_sec": at, "budget_sec": budget,
                "contract_limit_sec": grid_round(at + budget),
                "actual_sec": round(actual, 3),
                "actual_nominal_sec": nominal,
                "slack_sec": slack,
                "items_json_dur": items_dur,
                "items_json_vs_ffprobe_delta": items_dur_delta,
                "d16_subtitle_out_sec": sub_out,
                "d16_out_matches_contract": sub_out_matches,
                "actual_voice_end_sec": actual_end,
                "subtitle_end_sec": sub_end,
                "subtitle_cut_shortfall_sec": gap,
                "verdict": verdict, "level": level,
                "audio": os.path.relpath(apath, P),
            })

    errs = [r for r in rows if r["level"] == "ERROR"]
    warns = [r for r in rows if r["level"] == "WARN"]
    ok = [r for r in rows if r["level"] == "OK"]

    report = {
        "unit": u,
        "task": "实际 TTS 时长 vs D15 dur_sec 预算（只读比对）",
        "dispatch": {
            "batch_id": "batch_647000ba9193",
            "request_id": "sxcz-u02-w2-status-d15tts-0335",
            "task_id": "task_f4cf5b81380c",
            "dispatched_at": "2026-10-23 03:35",
        },
        "inputs": {
            "d15": os.path.relpath(d15_path, P), "d15_version": d15.get("version"),
            "d09": os.path.relpath(d09_path, P), "d09_version": d09.get("version"),
            "d16": os.path.relpath(d16_path, P), "d16_version": d16.get("version"),
            "preview_items": os.path.relpath(items_path, P),
            "audio_dir": os.path.relpath(os.path.join(P, "preview", "%s_tts" % u, "audio"), P),
        },
        "basis": {
            "grid_sec": GRID,
            "measure": "ffprobe format=duration（只信实测；items.json 的 dur 字段不作判定输入）",
            "normalize": "actual_nominal = ceil(actual × 10) / 10（0.1s 标称网格向上取整）",
            "budget": "D15 voice_over[].dur_sec",
            "contract_limit": "D15 voice_over[].at_sec + dur_sec（＝ D16 对白字幕 out_sec）",
            "verdict_rule": "actual_nominal > 预算 → 契约破坏(ERROR)；== 预算 → 贴边零余量(WARN)；< 预算 → 合规",
            "float_rule": "浮点尾差不是时码精度问题，任何按浮点位相等的写法都会误判；判定一律走标称网格。",
            "mutation_rule": "本脚本不写任何交付物；不得改 D16 时码（字幕时码由分镜导演定）。",
        },
        "summary": {
            "vo_total": len(rows),
            "measured": len(rows),
            "no_audio": len(missing_audio),
            "error_count": len(errs),
            "warn_count": len(warns),
            "ok_count": len(ok),
            "d16_contract_rows_checked": sum(1 for r in rows if r["d16_subtitle_out_sec"] is not None),
            "d16_out_mismatch_count": sum(1 for r in rows
                                          if r["d16_subtitle_out_sec"] is not None
                                          and not r["d16_out_matches_contract"]),
            "items_json_dur_mismatch_count": sum(1 for r in rows
                                                if r["items_json_vs_ffprobe_delta"] is not None
                                                and abs(r["items_json_vs_ffprobe_delta"]) > 0.05),
        },
        "verdict": "FAIL" if errs else ("WARN" if warns else "PASS"),
        "errors": errs,
        "warnings": warns,
        "missing_audio": missing_audio,
        "stale_audio_items": [{
            "id": it.get("id"), "ep": it.get("ep"), "old_text": it.get("text"),
            "new_text": it.get("stale_new_text"), "upstream": it.get("stale_upstream"),
            "reason": it.get("stale_reason"), "action": it.get("stale_action"),
            "dur": it.get("dur"),
        } for it in stale_items],
        "rows": rows,
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        outp = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with open(outp, "w", encoding="utf-8") as f:
            f.write(text)
        print("\n[OK] 报告已写出：%s" % outp, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
