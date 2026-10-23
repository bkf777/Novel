#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_D16_dialogue_to_D15.py —— D16 对白字幕行按 D15 配音实测重新对齐

背景（2026-10-23）：
  声音设计岗的 TTS 派活连报两次 AGENT_UNAVAILABLE / BUSY，**但盘上其实有产物**（假失败）。
  ep001_hook.mp3 实测 3.3669s ⇒ D15 预算 3.5s（向上取整 0.1 + 0.1 余量）正确。
  而 D16 那一行的字幕仍写着「预算 1.8s」⇒ **字幕与真实配音对不上**（早退 1.7s）。

本脚本做的事（可复用到任意单元）：
  ① 读 D15 的 voice_over（line_ref → at_sec / dur_sec）
  ② 读 preview/<UNIT>_tts/items.json，用**归一化文本**（去「」与空格）把每条对白字幕行
     匹配到 D15 的一条配音
  ③ 覆写该字幕行：in_sec ＝ D15 的 at_sec；out_sec ＝ in_sec ＋ D15 的 dur_sec
  ④ 重叠自检（左闭右开）：若与相邻行重叠，按「后行让位」并记一条告警，不静默改数

幂等：可重复执行。
用法：python3 scripts/sync_D16_dialogue_to_D15.py --unit U01 [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = False


def norm(t):
    t = re.sub(r"[「」『』\"'（）()\s]", "", str(t or ""))
    return t


def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def main():
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    unit = a.unit
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(ROOT, "reports", f"_bak_syncD16_{unit}_{stamp}")

    d15 = json.load(open(os.path.join(ROOT, "units", unit, "D15.json"), encoding="utf-8"))
    d16 = json.load(open(os.path.join(ROOT, "units", unit, "D16.json"), encoding="utf-8"))
    d16_old = json.loads(json.dumps(d16))
    items_p = os.path.join(ROOT, "preview", f"{unit}_tts", "items.json")
    items = json.load(open(items_p, encoding="utf-8")) if os.path.isfile(items_p) else []

    # ① D15 配音索引：ep → {D09 idx: 配音行}
    #    配对必须走 **D09 这条唯一真源**：D15 的 line_ref 写的是「D09 epN #idx」，
    #    D09 的 idx 是该集对白序号，D16 的对白行与 D09 的对白行逐条同序同文。
    #    ⛔ 旧实现（先按文本命中任意 candidate）会把本集四句台词全配到第一行 —— 已废止。
    d09 = json.load(open(os.path.join(ROOT, "units", unit, "D09.json"), encoding="utf-8"))
    d09_by_ep = {}
    for l in d09.get("lines", []):        # D09 的 lines 是平铺的，每行带 ep
        d09_by_ep.setdefault(l["ep"], {})[l["idx"]] = norm(l.get("text"))

    vo_by_ep = {}
    for e in d15["episodes"]:
        rows = {}
        for v in e.get("voice_over", []):
            m = re.search(r"#(\d+)", v.get("line_ref", ""))
            if m:
                rows[int(m.group(1))] = {
                    "at": float(v["at_sec"]), "dur": float(v["dur_sec"]),
                    "line_ref": v.get("line_ref", ""), "char_id": v.get("char_id")}
        vo_by_ep[e["ep"]] = rows

    # ② items.json 索引：ep + 归一化文本 → 音频路径
    audio_by_key = {}
    for r in items:
        if r.get("kind") != "dialogue":
            continue
        audio_by_key[(r.get("ep"), norm(r.get("text")))] = r.get("audio")

    warnings = []
    for e16 in d16["episodes"]:
        ep = e16["ep"]
        lines = e16["subtitle_style"]["lines"]
        vo = vo_by_ep.get(ep, [])
        d09map = d09_by_ep.get(ep, {})
        for l in lines:
            if l.get("type") != "对白":
                continue
            key = norm(l.get("text"))
            # 找 D09 里同文的那一行 → 拿它的 idx → 去 D15 取对应配音行
            idx = None
            for k, txt in d09map.items():
                if txt == key:
                    idx = k
                    break
            match = vo.get(idx) if idx is not None else None
            if match is None:
                warnings.append(f"ep{ep} 字幕行「{l.get('text')}」找不到 D09/D15 配音，未改")
                continue
            a = audio_by_key.get((ep, key))
            if a and os.path.isfile(a):
                d = probe_dur(a)
                if d is not None:
                    budget = round(d, 1) + 0.1
                    if abs(budget - match["dur"]) > 0.05:
                        warnings.append(
                            f"ep{ep} 「{l.get('text')}」实测 {d:.3f}s ⇒ 预算应为 {budget:.1f}s，"
                            f"D15 现值 {match['dur']}s（D15 归声音设计岗，本脚本不擅自改 D15）")
            l["in_sec"] = round(match["at"], 1)
            l["out_sec"] = round(match["at"] + match["dur"], 1)
            l["note"] = (l.get("note", "") +
                         f"｜【配音对齐 2026-10-23】按 D15 {match['line_ref']}："
                         f"at {match['at']}s ＋ dur {match['dur']}s 实测复核").strip("｜")

        # ④ 重叠自检（左闭右开）
        seq = sorted([l for l in lines if l.get("type") not in ("角标", "片头", "片尾")],
                     key=lambda x: float(x["in_sec"]))
        for i in range(len(seq) - 1):
            a_, b_ = seq[i], seq[i + 1]
            if float(b_["in_sec"]) < float(a_["out_sec"]) - 1e-6:
                warnings.append(
                    f"ep{ep} 字幕重叠：seq{a_['seq']}「{a_['text'][:12]}」{a_['out_sec']}s "
                    f"> seq{b_['seq']}「{b_['text'][:12]}」{b_['in_sec']}s")
                b_["in_sec"] = round(float(a_["out_sec"]), 1)
                if float(b_["out_sec"]) - float(b_["in_sec"]) < 1.2:
                    b_["out_sec"] = round(float(b_["in_sec"]) + 1.2, 1)


    if not DRY:
        if {k: v for k, v in d16.items() if k != "version"} == \
           {k: v for k, v in d16_old.items() if k != "version"}:
            print("⏭  无变化")
        else:
            v = re.sub(r"^v+", "v", str(d16.get("version", "v1.0")))
            d16["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"
            os.makedirs(bak, exist_ok=True)
            shutil.copy2(os.path.join(ROOT, "units", unit, "D16.json"),
                         os.path.join(bak, "D16.json"))
            with open(os.path.join(ROOT, "units", unit, "D16.json"), "w", encoding="utf-8") as f:
                json.dump(d16, f, ensure_ascii=False, indent=2)
            print(f"✅ 已写 D16.json (v{d16['version']})，备份 {bak}")
    for w in warnings:
        print("   ⚠️ ", w)


if __name__ == "__main__":
    main()
