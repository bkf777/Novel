#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U01 有声预演 —— 音频生成（macOS say 引擎，零配额、离线）。

角色差异化（macOS 仅 Tingting 一款中文音色，用 [[pbas]] 音高 + 语速 + 音量做区分）：
  LC   陆沉   → 音高下压 -20，语速慢（低沉磁性）
  YHY  叶红衣 → 音高 +25，语速偏快（清冷锋利）
  YJ-ES 叶承钧 → 音高 +5，语速最慢（宣读式平稳）
  NARR 旁白   → 基准音高 +12，语速略快
  PANEL 系统  → 音高 +40，语速快（面板播报）
"""
import json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "preview", "U01_tts")
AUDIO = os.path.join(OUT, "audio")

# role → (音高偏移, 语速 wpm, 音量 0-1)
VOICE = {
    "LC":    (-20, 168, 1.00),
    "YHY":   (+25, 186, 0.95),
    "YJ-ES": (+5,  160, 1.00),
    "NARR":  (+12, 178, 0.85),
    "PANEL": (+40, 192, 0.80),
}


def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    os.makedirs(AUDIO, exist_ok=True)
    items = json.load(open(os.path.join(OUT, "items.json"), encoding="utf-8"))
    d08 = json.load(open(os.path.join(ROOT, "units", "U01", "D08.json"), encoding="utf-8"))

    # 角色反查 + 面板判定
    role_map, panel_map = {}, {}
    PANEL_HINT = ("等级", "新手福利期", "归档回滚完成", "全区首杀", "求救信号",
                  "面板", "倒计时", "归一度", "LV")
    for e in d08["episodes"]:
        for b in e["body"]:
            if b["type"] == "dialogue":
                role_map[(e["ep"], b["text"])] = b["char_id"]
            elif b["type"] in ("action", "subtitle"):
                panel_map[(e["ep"], b["text"])] = any(k in b["text"] for k in PANEL_HINT)

    made, failed = 0, 0
    for it in items:
        aiff = os.path.join(AUDIO, it["id"] + ".aiff")
        mp3 = os.path.join(AUDIO, it["id"] + ".mp3")
        if os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
            it["audio"] = mp3
            it["dur"] = dur_of(mp3)
            made += 1
            continue

        if it["kind"] == "dialogue":
            # D08 的 dialogue.text 本身已含「」，直接用原文匹配
            role = role_map.get((it["ep"], it["text"]), "NARR")
        else:
            role = "PANEL" if panel_map.get((it["ep"], it["text"])) else "NARR"
        it["role"] = role
        pb, rate, vol = VOICE[role]

        # 去掉引号，读文本本身
        txt = it["text"].strip().strip("「」")
        # 面板/系统播报加轻微停顿感
        if role == "PANEL":
            spoken = txt.replace("：", "，").replace("、", "，")
        else:
            spoken = txt

        # say 不接受 [[pbas]] 以外的复杂标记；用 [[pbas N]] 包裹整句
        markup = f"[[pbas {pb}]]{spoken}"
        cmd = ["say", "-v", "Tingting", "-r", str(rate), "-o", aiff, markup]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(aiff):
            print(f"  ✗ {it['id']} say 失败: {r.stderr[:120]}")
            failed += 1
            continue
        # 转 mp3
        r2 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff,
                             "-ar", "44100", "-ac", "1", "-b:a", "128k", mp3],
                            capture_output=True, text=True)
        if r2.returncode != 0 or not os.path.exists(mp3):
            print(f"  ✗ {it['id']} ffmpeg 失败: {r2.stderr[:120]}")
            failed += 1
            continue
        os.remove(aiff)
        it["audio"] = mp3
        it["dur"] = dur_of(mp3)
        made += 1
        if made % 20 == 0:
            print(f"  ... {made}/{len(items)}", flush=True)

    with open(os.path.join(OUT, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f"音频完成 {made} 条 / 共 {len(items)}，失败 {failed}")


if __name__ == "__main__":
    main()
