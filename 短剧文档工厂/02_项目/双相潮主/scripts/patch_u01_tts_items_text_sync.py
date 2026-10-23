#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R-028a-r2 · U01 预演 TTS 清单（`preview/U01_tts/items.json`）台词层同步器

背景
  台本编剧 12:47／12:51 改写了 D09 U01 ep001／ep002 台词（D09 v1.8 → v1.9），
  D16 侧由分镜导演同步；本岗负责把**预演 TTS 清单的台词层与本岗 D15 预算口径对齐**。

两种结局（由 TTS 是否重出成功决定，数据源＝/tmp/tts_r028a_manifest.json）
  ① 已重出 → 该条 `text` 同步为新台词、`dur` ＝ ffprobe 实测（不取缓存字段）、
     `audio` 指向新音频、清掉 stale 标注（音频已与台词一致 ⇒ 不再是旧音频）。
  ② 未重出（上游 429 限流）→ **保留旧台词与旧音频**，并按仓内既有机制打 stale 标注
     （`stale_audio=true` + `stale_new_text`＝新台词 + 理由/上游/待办），
     ⇒ `reconcile_tts_actual_vs_d15_budget.mjs` 归类为「旧音频待出片阶段重合成」，
     **不算映射失败、也不混入合规统计**；音频仍与旧台词一致，不制造「用旧音频测新台词」的假通过。

边界
  只改 `preview/<unit>_tts/items.json`；不碰任何交付物 JSON（D15/D16/…）、不碰音频文件、
  不合成音频、不改 D15 预算。

幂等
  已达目标态则逐条 no-op（不产生字节变化）。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

NORM = lambda s: re.sub(r"[「」“”]", "", str(s or "")).strip()

# 目标槽位 → (ep, d09_idx, kind)；d09_idx=None 表示台词不从 D09 取（钟声口径行）
TARGETS = [
    ("ep001_hook", 1, 1, "dialogue"),
    ("ep001_05",   1, 2, "dialogue"),
    ("ep001_08",   1, 3, "dialogue"),
    ("ep001_12",   1, 4, "dialogue"),
    ("ep002_03",   2, 1, "dialogue"),
    ("ep002_06",   2, 2, "dialogue"),
    ("ep002_10",   2, 3, "dialogue"),
    ("ep002_13",   2, 4, "dialogue"),
    ("ep003_hook", 3, 1, "dialogue"),
    ("ep002_12",   2, None, "subtitle"),
]

# 未重出时的 stale 标注口径
UPSTREAM = "D08 U01 v1.17 ／ D09 U01 v1.9（台本编剧 2026-10-23 12:47／12:51 台词改稿波次）"
ACTION = "音频待出片阶段重合成"
REASON = "台词已被上游改写，本条音频仍为旧台词版本（上游 TTS 429 限流，未能重出）"


def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None


def load_manifest(path):
    if not os.path.exists(path):
        return {}
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--manifest", default="/tmp/tts_r028a_manifest.json")
    ap.add_argument("--check", action="store_true", help="只打印将要发生的改动，不写盘")
    args = ap.parse_args()

    P = os.path.abspath(args.project)
    u = args.unit
    items_path = os.path.join(P, "preview", "%s_tts" % u, "items.json")
    d09_path = os.path.join(P, "units", u, "D09.json")
    if not os.path.exists(items_path):
        print("[FATAL] 缺 %s" % items_path, file=sys.stderr)
        return 2
    raw = io.open(items_path, encoding="utf-8").read()
    items = json.loads(raw)
    by_id = {it["id"]: it for it in items}
    d09 = json.load(io.open(d09_path, encoding="utf-8"))
    d09_line = {(l["ep"], l["idx"]): l for l in d09["lines"]}
    manifest = load_manifest(args.manifest)

    notes = []
    changed = 0

    for slot, ep, idx, kind in TARGETS:
        m = manifest.get(slot) or {}
        # 新台词
        if slot == "ep002_12":
            new_text = "全城钟楼敲响十一下。"
            ep_key = 2
        else:
            new_text = d09_line[(ep, idx)]["text"]
            ep_key = ep
        it = by_id.get(slot)

        if m.get("ok") and os.path.exists(m.get("file", "")):
            # ── ① 已重出 ──
            actual = dur_of(m["file"])
            if actual is None:
                notes.append("[SKIP] %s ffprobe 未读出时长，跳过" % slot)
                continue
            if it is None:
                # 新增条目（ep003_hook）
                src = by_id.get("ep001_hook") or {}
                it = {"id": slot, "ep": ep_key, "kind": kind, "text": new_text,
                      "voice_id": src.get("voice_id"), "emotion": src.get("emotion", "neutral"),
                      "speed": src.get("speed", 0.95), "pitch": src.get("pitch", -1),
                      "role": src.get("role", "LC"), "audio": m["file"], "dur": round(actual, 6)}
                items.append(it)
                by_id[slot] = it
                changed += 1
                notes.append("新增条目 %s（text=%s dur=%.6f）" % (slot, new_text, actual))
                continue
            before = (it.get("text"), it.get("dur"), it.get("audio"),
                      tuple(sorted(k for k in it if k.startswith("stale_"))))
            it["text"] = new_text
            it["audio"] = m["file"]
            it["dur"] = round(actual, 6)
            for k in ("stale_audio", "stale_reason", "stale_new_text", "stale_upstream", "stale_action"):
                it.pop(k, None)
            after = (it.get("text"), it.get("dur"), it.get("audio"),
                     tuple(sorted(k for k in it if k.startswith("stale_"))))
            if before != after:
                changed += 1
                notes.append("同步 %s：text %r → %r；dur → %.6f（ffprobe 实测）；stale 标注清除"
                             % (slot, before[0], new_text, actual))
            else:
                notes.append("[NO-OP] %s 已是目标态" % slot)
        else:
            # ── ② 未重出 ──：保留旧台词与旧音频，打 stale 标注
            if it is None:
                # 从未合成的条目（钩子行）—— 建占位条目：旧台词位留空壳，标注待合成
                src = by_id.get("ep001_hook") or {}
                it = {"id": slot, "ep": ep_key, "kind": kind,
                      "text": "（未合成·待出片阶段）",
                      "voice_id": src.get("voice_id"), "emotion": src.get("emotion", "neutral"),
                      "speed": src.get("speed", 0.95), "pitch": src.get("pitch", -1),
                      "role": src.get("role", "LC"),
                      "audio": os.path.join(P, "preview", "%s_tts" % u, "audio", slot + ".mp3"),
                      "dur": None}
                items.append(it)
                by_id[slot] = it
                changed += 1
                notes.append("新增占位条目 %s（音频尚未存在，待出片阶段合成）" % slot)
            if it.get("stale_audio") and it.get("stale_new_text") == new_text:
                notes.append("[NO-OP] %s 已标注 stale（new_text 一致）" % slot)
                continue
            it["stale_audio"] = True
            it["stale_reason"] = REASON
            it["stale_new_text"] = new_text
            it["stale_upstream"] = UPSTREAM
            it["stale_action"] = ACTION
            changed += 1
            notes.append("标注 %s：旧台词 %r → 新台词 %r（音频未重出，保留旧音频与旧 dur）"
                         % (slot, it.get("text"), new_text))

    for n in notes:
        print(n)
    print("---- 合计改动 %d 处 ----" % changed)
    if not changed:
        print("清单未变化（no-op）")
        return 0
    if args.check:
        print("（--check：将改动 %d 处，未写盘）" % changed)
        return 0

    # 格式保真：沿用原文件的缩进与末尾换行组合
    def dumps(obj):
        for indent in (2, 1, 4, None):
            for tail in ("", "\n"):
                cand = json.dumps(obj, ensure_ascii=False, indent=indent) + tail
                if cand == raw:
                    return cand
        return json.dumps(obj, ensure_ascii=False, indent=2)

    out = dumps(items)
    tmp = items_path + ".tmp.%d" % os.getpid()
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, items_path)
    print("已写盘 %s（%d bytes）" % (items_path, len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
