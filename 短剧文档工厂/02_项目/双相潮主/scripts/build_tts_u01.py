#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U01 有声预演 —— 从 D08 抽取台词/动作，分配角色音色，产出 TTS 批次。

- 对白 → 角色音色（voice 锁定见 D04）
- 动作/字幕 → 旁白音色（漫剧解说式预演）
- 音效行不朗读（属 D15 声音设计范畴）
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D08 = os.path.join(ROOT, "units", "U01", "D08.json")
OUT = os.path.join(ROOT, "preview", "U01_tts")
CHUNK_DIR = os.path.join(OUT, "_chunks")

# ── 角色音色映射（依据 D04 voice 锁定 + 音色库语义） ──────────────
VOICE = {
    "LC":   ("male-qn-badao",                    -1, 0.95),  # 陆沉 低沉磁性语带狂傲 → 霸道青年
    "YHY":  ("Chinese (Mandarin)_Crisp_Girl",    +1, 0.95),  # 叶红衣 清冷锋利 → 清脆少女
    "YJ-ES":("Chinese (Mandarin)_Male_Announcer", 0, 0.92),  # 叶承钧 清晰平稳像宣读 → 播报男声
}
NARRATOR = ("Chinese (Mandarin)_Gentleman", 0, 1.02)  # 旁白：温润男声
PANEL    = ("Chinese (Mandarin)_Male_Announcer", 0, 1.0)  # 面板/系统播报

# 系统/面板字幕关键词 → 面板音
PANEL_HINT = ("等级", "新手福利期", "归档回滚完成", "全区首杀", "求救信号",
              "面板", "倒计时", "读数", "归一度", "LV")

# 情绪映射（TTS emotion 枚举）
EMOTION = {
    "低吼": "angry", "砸": "angry", "牙关咬紧": "angry", "字音": "angry",
    "带笑": "happy", "尾音提": "happy",
    "气声": "neutral", "气音": "neutral", "压低": "neutral",
    "放慢": "neutral", "上扬": "surprised", "发紧": "fearful",
}


def pick_emotion(tone: str) -> str:
    if not tone:
        return "neutral"
    for k, v in EMOTION.items():
        if k in tone:
            return v
    return "neutral"


def is_panel(text: str) -> bool:
    return any(k in text for k in PANEL_HINT)


def main():
    os.makedirs(CHUNK_DIR, exist_ok=True)
    d08 = json.load(open(D08, encoding="utf-8"))

    items = []   # {id, ep, kind, text, voice_id, emotion, speed, pitch}
    for e in d08["episodes"]:
        ep = e["ep"]
        n = 0
        for b in e["body"]:
            t = b["type"]
            if t == "sfx":
                continue
            n += 1
            if t == "dialogue":
                cid = b["char_id"]
                vid, pit, spd = VOICE.get(cid, NARRATOR)
                emo = pick_emotion(b.get("emotion", ""))
                if "放慢" in (b.get("emotion") or ""):
                    spd = max(0.8, spd - 0.06)
            else:  # action / subtitle
                if is_panel(b["text"]):
                    vid, pit, spd = PANEL
                else:
                    vid, pit, spd = NARRATOR
                emo = "neutral"
            items.append({
                "id": f"ep{ep:03d}_{n:02d}",
                "ep": ep,
                "kind": t,
                "text": b["text"],
                "voice_id": vid,
                "emotion": emo,
                "speed": spd,
                "pitch": pit,
            })

    # 写批（每批 ≤10 条）
    chunks = [items[i:i + 10] for i in range(0, len(items), 10)]
    for i, ch in enumerate(chunks):
        reqs = []
        for it in ch:
            r = {
                "text": it["text"],
                "voice_id": it["voice_id"],
                "emotion": it["emotion"],
                "speed": it["speed"],
                "pitch": it["pitch"],
                "output_file": f"{it['id']}.mp3",
            }
            reqs.append(r)
        with open(os.path.join(CHUNK_DIR, f"batch_{i:02d}.json"), "w", encoding="utf-8") as f:
            json.dump({"requests": reqs}, f, ensure_ascii=False, indent=1)

    with open(os.path.join(OUT, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

    per_ep = {}
    for it in items:
        per_ep.setdefault(it["ep"], []).append(it["id"])
    print(f"items={len(items)}  chunks={len(chunks)}")
    for ep in sorted(per_ep):
        print(f"  ep{ep:03d}: {len(per_ep[ep])} lines")
    print("chars:", {c: sum(1 for i in items if i['kind'] == 'dialogue' and i['text'] and c in i['text']) for c in []} or "")


if __name__ == "__main__":
    main()
