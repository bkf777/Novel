#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U01 有声预演片合成：TTS 音频 + 字幕卡画面 → 每集一个 mp4。

画面：SVG → PNG（sips，macOS 自带）→ ffmpeg 拼帧；无 drawtext/libass 依赖。
每集一条：按 items.json 的 ep 分组，逐条生成字幕卡，帧时长 = 该条 TTS 实际时长。
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "preview", "U01_tts")
VID = os.path.join(ROOT, "preview", "U01_video")
FRM = os.path.join(VID, "_frames")
AUDIO = os.path.join(OUT, "audio")

W, H = 1080, 1920
FPS = 30

# 角色配色（呼应 D10 色板：冷白 + 深蓝 + 琥珀）
ROLE_COLOR = {
    "LC":   "#E8EEF7",   # 陆沉 —— 冷白
    "YHY":  "#F0C88A",   # 叶红衣 —— 琥珀
    "YJ-ES":"#8FA8C8",   # 叶承钧 —— 冷蓝
    "NARR": "#9AA3AE",   # 旁白 —— 灰
    "PANEL":"#7FD4C8",   # 面板 —— 青
}
BG = "#0B0E13"
SPEAKER_LABEL = {"LC": "陆沉", "YHY": "叶红衣", "YJ-ES": "叶承钧",
                 "NARR": "旁白", "PANEL": "系统"}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def wrap(text: str, per_line: int = 16):
    """按标点优先断行，竖屏每行约 16 字。"""
    lines, cur = [], ""
    i = 0
    while i < len(text):
        ch = text[i]
        cur += ch
        if ch in "。？！，；：、…—" and len(cur) >= per_line * 0.6:
            lines.append(cur)
            cur = ""
        elif len(cur) >= per_line:
            lines.append(cur)
            cur = ""
        i += 1
    if cur:
        lines.append(cur)
    return lines


def svg_for(item, ep_title, ep_no):
    txt = item["text"].strip().strip("「」")
    kind = item["kind"]
    role = item.get("role", "NARR")
    if kind == "dialogue":
        color = ROLE_COLOR.get(role, "#E8EEF7")
        tag = SPEAKER_LABEL.get(role, "")
        fs = 62
    elif role == "PANEL":
        color = ROLE_COLOR["PANEL"]
        tag = "系统"
        fs = 60
    else:
        color = ROLE_COLOR["NARR"]
        tag = "旁白"
        fs = 46
    lines = wrap(txt, 15 if kind == "dialogue" else 19)
    lh = int(fs * 1.55)
    total = lh * len(lines)
    y0 = H * 0.52 - total / 2 + fs

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        # 顶部集数条
        f'<rect x="0" y="0" width="{W}" height="120" fill="#111722"/>',
        f'<text x="70" y="78" font-size="40" fill="#7C8794" font-family="PingFang SC,Heiti SC">'
        f'《双相潮主》 EP{ep_no:03d} · {esc(ep_title)}</text>',
        # 角色标签
        f'<text x="{W//2}" y="{int(y0 - fs*1.9)}" font-size="34" fill="{color}" text-anchor="middle" '
        f'font-family="PingFang SC,Heiti SC" opacity="0.9">{esc(tag)}</text>',
    ]
    for i, ln in enumerate(lines):
        parts.append(
            f'<text x="{W//2}" y="{int(y0 + i*lh)}" font-size="{fs}" fill="{color}" text-anchor="middle" '
            f'font-family="PingFang SC,Heiti SC">{esc(ln)}</text>')
    # 底部 AI 角标（D03 R09 常驻）
    parts.append(
        f'<text x="{W-50}" y="{int(H*0.75)}" font-size="28" fill="#FFFFFF" text-anchor="end" '
        f'opacity="0.55" font-family="PingFang SC,Heiti SC">AI 生成</text>')
    parts.append("</svg>")
    return "".join(parts)


def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    os.makedirs(FRM, exist_ok=True)
    os.makedirs(AUDIO, exist_ok=True)
    os.makedirs(VID, exist_ok=True)

    items = json.load(open(os.path.join(OUT, "items.json"), encoding="utf-8"))
    results = json.load(open(os.path.join(OUT, "results.json"), encoding="utf-8"))

    d08 = json.load(open(os.path.join(ROOT, "units", "U01", "D08.json"), encoding="utf-8"))
    titles = {e["ep"]: e["title"] for e in d08["episodes"]}

    # 角色标注：从 D08 dialogue 反查
    role_map = {}
    for e in d08["episodes"]:
        for b in e["body"]:
            if b["type"] == "dialogue":
                role_map[(e["ep"], b["text"])] = b["char_id"]

    # 逐条取音频（本地已下载或从 node_id 拉取）
    ready = []
    missing = []
    for it in items:
        fn = it["id"] + ".mp3"
        p = os.path.join(AUDIO, fn)
        if not os.path.exists(p):
            r = results.get(fn, {})
            if not r.get("node_id"):
                missing.append(it["id"])
                continue
            url = subprocess.run(["mcode-tools", "get_asset_url", r["node_id"]],
                                 capture_output=True, text=True).stdout
            try:
                u = json.loads(url[url.find("{"):])["download_url"]
            except Exception:
                missing.append(it["id"])
                continue
            subprocess.run(["curl", "-sL", "-o", p, u], check=False)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            it["audio"] = p
            it["dur"] = dur_of(p)
            it["role"] = it.get("role") or role_map.get((it["ep"], it["text"]), "NARR")
            it["panel"] = bool(it.get("panel"))
            ready.append(it)
        else:
            missing.append(it["id"])

    print(f"可用音频 {len(ready)} 条 / 缺失 {len(missing)} 条")
    if missing:
        print("缺失示例:", missing[:8])

    by_ep = {}
    for it in ready:
        by_ep.setdefault(it["ep"], []).append(it)

    made = []
    for ep in sorted(by_ep):
        rows = by_ep[ep]
        epdir = os.path.join(FRM, f"ep{ep:03d}")
        os.makedirs(epdir, exist_ok=True)
        flist = []
        for i, it in enumerate(rows):
            svgp = os.path.join(epdir, f"{i:03d}.svg")
            pngp = os.path.join(epdir, f"{i:03d}.png")
            with open(svgp, "w", encoding="utf-8") as f:
                f.write(svg_for(it, titles.get(ep, ""), ep))
            subprocess.run(["sips", "-s", "format", "png", svgp, "--out", pngp],
                           capture_output=True, check=False)
            if not os.path.exists(pngp):
                continue
            d = max(it["dur"], 0.4)
            flist.append((pngp, d))
        if not flist:
            continue

        # 写 concat 清单，用 image2 demuxer + duration
        lst = os.path.join(epdir, "concat.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for pngp, d in flist:
                f.write(f"file '{pngp}'\nduration {d:.3f}\n")
            f.write(f"file '{flist[-1][0]}'\n")

        # 音频：每条转统一 m4a 后用 concat demuxer 拼接（段间 0.1s 静音更稳）
        m4as = []
        for i, it in enumerate(rows):
            m4 = os.path.join(epdir, f"{i:03d}.m4a")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", it["audio"],
                            "-ar", "44100", "-ac", "1", "-c:a", "aac", "-b:a", "128k", m4],
                           capture_output=True, check=False)
            if os.path.exists(m4):
                m4as.append(m4)
        alist = os.path.join(epdir, "audio_concat.txt")
        with open(alist, "w", encoding="utf-8") as f:
            for m in m4as:
                f.write(f"file '{m}'\n")

        c = ["ffmpeg", "-y", "-loglevel", "error",
             "-f", "concat", "-safe", "0", "-i", lst,
             "-f", "concat", "-safe", "0", "-i", alist,
             "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "128k", "-shortest",
             "-movflags", "+faststart",
             os.path.join(VID, f"EP{ep:03d}.mp4")]
        r = subprocess.run(c, capture_output=True, text=True)
        outp = os.path.join(VID, f"EP{ep:03d}.mp4")
        if os.path.exists(outp):
            sz = os.path.getsize(outp)
            made.append((ep, outp, sz))
            print(f"  EP{ep:03d} ✓ {sz//1024} KB  ({len(rows)} 条音频)")
        else:
            print(f"  EP{ep:03d} ✗ 失败: {r.stderr[-400:]}")
    print(f"\n完成 {len(made)} 个 mp4 → {VID}")


if __name__ == "__main__":
    main()
