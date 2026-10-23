#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U01「看得懂版」动态分镜样片 —— 白模画面 + 剧本字幕 + 集标题。

为什么有这个脚本
----------------
产线的交付物是 JSON（机器消费），用户看不了。本脚本把已有的**真素材**拼成人能看的东西：
  底片 = D14 逐镜白模预览视频（D14_shots/<shot>/preview_video.mp4，Blender 白模实拍，
         1080×1920，32 镜合计 360s ＝ 8 集 × 45s）
  字幕 = D16 剪辑节奏表里的 subtitle_style.lines（对白／字幕板／片头／片尾，带精确时码）
  标题 = D07 集标题或自动生成的「EP00N」
输出 = preview/U01_storyboard/EP001..EP008.mp4

技术要点
--------
· ffmpeg 8.1.1（homebrew）**未编译 libass/libfreetype** ⇒ subtitles / drawtext 滤镜不可用。
  故沿用产线既有做法：**SVG → PNG（sips，macOS 自带）→ ffmpeg 拼帧**。
· 字幕 PNG 走 RGBA 透明通道（sips 保留 alpha，已实测 pix_fmt=rgba），用 overlay 滤镜按时码贴在画面上。
· 白模视频无音轨（preview_video.mp4 只含画面）⇒ 样片默认静音；音频另走 TTS 预演片。
· 只读交付物，不改任何 JSON。

用法
----
python3 scripts/build_u01_storyboard.py --unit U01 [--ep 1] [--out <dir>]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

W, H = 1080, 1920
FONT = "Hiragino Sans GB"
SUB_TOP = 1500          # 成片字幕基线（竖屏底部上移）
TITLE_TOP = 150         # 片头四行带区（D16：画面高度 6%~20%）
ANNO_TOP = 1120         # 分镜说明带区（面板框与字幕带之间）
PANEL_TOP = 620         # 模拟面板框顶部
PANEL_H = 360


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def wrap(text, per_line=15):
    """按 D16 规定的 max_chars_per_line=15 折行。"""
    t = str(text)
    out = []
    while len(t) > per_line:
        out.append(t[:per_line])
        t = t[per_line:]
    out.append(t)
    return out


def svg_lines(lines, style="sub"):
    """生成字幕层的 SVG 片段（可多行）。lines 里可含 \n（片头多行合并用）。"""
    flat = []
    for ln in lines:
        flat.extend(ln.split("\n"))
    lines = flat
    parts = []
    for i, ln in enumerate(lines):
        if style == "title":
            parts.append(
                f'<text x="{W//2}" y="{TITLE_TOP + i*96}" font-family="{FONT}" font-size="84" '
                f'font-weight="bold" fill="#FFFFFF" stroke="#000000" stroke-width="6" '
                f'text-anchor="middle">{esc(ln)}</text>')
        elif style == "head":
            parts.append(
                f'<text x="{W//2}" y="{TITLE_TOP + i*84}" font-family="{FONT}" font-size="54" '
                f'fill="#E8E8E8" stroke="#000000" stroke-width="4" text-anchor="middle">{esc(ln)}</text>')
        else:
            parts.append(
                f'<text x="{W//2}" y="{SUB_TOP + i*92}" font-family="{FONT}" font-size="72" '
                f'fill="#FFFFFF" stroke="#000000" stroke-width="5" text-anchor="middle">{esc(ln)}</text>')
    return "\n".join(parts)


def svg_doc(inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">\n{inner}\n</svg>')


def svg_to_png(svg_text, out_png, tmpdir, tag):
    sp = os.path.join(tmpdir, f"{tag}.svg")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(svg_text)
    subprocess.run(["sips", "-s", "format", "png", sp, "--out", out_png],
                   check=True, capture_output=True)
    if not os.path.isfile(out_png):
        sys.exit(f"[ABORT] sips 未产出 {out_png}")


def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


# ── 分镜说明层（2026-10-23 新增）────────────────────────────────────────
# 病因：白模是纯几何，镜子里没有表情、没有动作，**一条字幕消失后画面就是一块灰板**。
# 实测 U01+U02 十六集：全集最长空窗 7.2~14.0s、平均每集空窗总 33.0s（体检脚本
# scripts/audit_dead_time.py）——观众看白模时看到的就是「什么也没有」。
# 修法：**把 D11 每镜的 visual_facts 拆成短句，按该镜时长铺开烧成"分镜说明"字幕**，
# 让每一镜每一小段时间都有信息在动。它是**分镜稿专用层**，不是成片字幕：
# 位置在上部带区、灰色小字、左对齐并带竖线标识，与底部成片字幕带完全分开。
ANNO_TOP = 1120
ANNO_MAX = 3          # 每镜最多 3 条说明
ANNO_MIN_LEN = 8      # 少于 8 个字的分句丢弃
ANNO_WRAP = 26        # 每行 26 字


def split_clauses(vf):
    """把 visual_facts 拆成可读的短句；剔除角标合规句与过碎的分句。"""
    t = str(vf or "")
    t = t.replace("右下角常驻白色角标：AI 生成。", "")
    t = re.sub(r"\s+", "", t)
    parts = re.split(r"[；;]", t)
    out = []
    for seg in parts:
        for c in re.split(r"[，,]", seg):
            c = c.strip("。、 ")
            if len(c) >= ANNO_MIN_LEN:
                out.append(c)
    return out[:ANNO_MAX]


def anno_svg(text):
    """分镜说明层：白模是浅灰几何，浅色字直接压上去会看不清（实测白墙处几乎消失）。
    ⇒ 文字改为「深色半透衬底 ＋ 亮字」，任何底色上都读得出来。"""
    rows = wrap(text, ANNO_WRAP)[:2]
    h = 40 + (len(rows) - 1) * 50
    parts = [f'<rect x="48" y="{ANNO_TOP - 58}" width="984" height="{h + 34}" rx="8" '
             f'fill="#0A1018" fill-opacity="0.58"/>',
             f'<rect x="62" y="{ANNO_TOP - 44}" width="5" height="{h}" '
             f'fill="#7FA6CC" opacity="0.95"/>']
    for i, r in enumerate(rows):
        parts.append(
            f'<text x="90" y="{ANNO_TOP + i * 50}" font-family="{FONT}" font-size="40" '
            f'fill="#E4EEF7" letter-spacing="1">{esc(r)}</text>')
    return "\n".join(parts)


def build_anno_clips(d11_ep, shots, tmpdir, ep):
    """产出 (png, t0, t1) 列表：每镜的 visual_facts 拆句后按镜时长均分。"""
    clips = []
    t = 0.0
    for s in shots:
        dur = float(s["duration_sec"])
        cls = split_clauses(s.get("visual_facts"))
        if cls:
            slot = dur / len(cls)
            for i, c in enumerate(cls):
                png = os.path.join(tmpdir, f"ep{ep}_anno{len(clips):02d}.png")
                svg_to_png(svg_doc(anno_svg(c)), png, tmpdir, f"ep{ep}_anno{len(clips):02d}")
                a = t + i * slot
                # 相邻说明**硬切**，不做重叠淡入：加了深色衬底后重叠窗会叠出两层文字。
                b = min(t + dur, a + slot)
                clips.append((png, round(a, 2), round(b, 2)))
        t += dur
    return clips


def panel_svg(text, danger=False):
    """模拟面板 UI：白模里没有面板，得给它一个样子，观众才知道面板是什么。"""
    col = "#FF5A4C" if danger else "#CFE0F0"
    rows = wrap(text, 16)
    parts = [f'<rect x="228" y="{PANEL_TOP}" width="624" height="{PANEL_H}" rx="10" '
             f'fill="#C9D6E2" fill-opacity="0.13" stroke="#AFC2D4" stroke-width="3" '
             f'stroke-opacity="0.8"/>']
    g = f'stroke="#AFC2D4" stroke-opacity="0.85" stroke-width="3"'
    parts += [
        f'<path d="M228 {PANEL_TOP+26} L228 {PANEL_TOP} L264 {PANEL_TOP}" {g}/>',
        f'<path d="M852 {PANEL_TOP+26} L852 {PANEL_TOP} L816 {PANEL_TOP}" {g}/>',
        f'<path d="M228 {PANEL_TOP+PANEL_H-26} L228 {PANEL_TOP+PANEL_H} L264 {PANEL_TOP+PANEL_H}" {g}/>',
        f'<path d="M852 {PANEL_TOP+PANEL_H-26} L852 {PANEL_TOP+PANEL_H} L816 {PANEL_TOP+PANEL_H}" {g}/>',
        f'<text x="540" y="{PANEL_TOP+54}" font-family="{FONT}" font-size="30" '
        f'fill="#8FA2B4" text-anchor="middle" letter-spacing="4">灰框面板</text>',
    ]
    for i, r in enumerate(rows):
        parts.append(
            f'<text x="540" y="{PANEL_TOP + 150 + i*64}" font-family="{FONT}" font-size="52" '
            f'font-weight="bold" fill="{col}" text-anchor="middle" letter-spacing="1">{esc(r)}</text>')
    parts.append(f'<g fill="#5E7286" opacity="0.8">'
                 f'<rect x="280" y="{PANEL_TOP+PANEL_H-46}" width="300" height="9" rx="4"/>'
                 f'<rect x="280" y="{PANEL_TOP+PANEL_H-46}" width="170" height="9" rx="4" fill="#9FB6CA"/>'
                 f'</g>')
    return "\n".join(parts)


def build_ep(ep, d11, d16, shots_root, out_dir, tmpdir, keep_audio=None):
    ep_d11 = next(e for e in d11["episodes"] if e["ep"] == ep)
    ep_d16 = next(e for e in d16["episodes"] if e["ep"] == ep)
    shots = sorted(ep_d11["shots"], key=lambda s: s["shot_id"])

    # ---- 1) 底片：concat 4 镜白模视频 ----
    seg_files = []
    for s in shots:
        d = os.path.join(shots_root, f"ep{ep:02d}_shot{s['shot_id']:02d}")
        pv = os.path.join(d, "preview_video.mp4")
        if not os.path.isfile(pv):
            sys.exit(f"[ABORT] 缺白模视频 {pv}")
        seg_files.append(pv)
    clist = os.path.join(tmpdir, f"ep{ep}_concat.txt")
    with open(clist, "w", encoding="utf-8") as f:
        for p in seg_files:
            f.write(f"file '{p}'\n")
    base = os.path.join(tmpdir, f"ep{ep}_base.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", clist, "-c", "copy", base], check=True)

    # ---- 2) 字幕层：按 D16 时码做透明 PNG，overlay 上去 ----
    # ① 片头多行合并成一张图（旧实现每行一张 PNG 且都落在同一 y，四行叠成一坨 —— 实测 bug）
    # ② 面板文字不进底部字幕带：它是**画面内文字**，改画进「模拟面板框」里（见 panel_svg）
    all_lines = [l for l in ep_d16["subtitle_style"]["lines"] if l.get("type") != "角标"]
    lines = []
    head_group = []
    for ln in all_lines:
        if ln.get("type") == "片头":
            head_group.append(ln)
            continue
        if head_group:
            lines.append({"type": "片头", "in_sec": head_group[0]["in_sec"],
                          "out_sec": head_group[-1]["out_sec"],
                          "text": "\n".join("\n".join(wrap(x["text"], 18)) for x in head_group)})
            head_group = []
        lines.append(ln)
    if head_group:
        lines.append({"type": "片头", "in_sec": head_group[0]["in_sec"],
                      "out_sec": head_group[-1]["out_sec"],
                      "text": "\n".join("\n".join(wrap(x["text"], 18)) for x in head_group)})

    filters = []
    inputs = []
    t0s, t1s = [], []
    vi = 1
    for idx, ln in enumerate(lines):
        txt = ln.get("text", "")
        if not txt:
            continue
        kind = ln.get("type")
        if kind == "面板文字":
            # 面板文字 → 画进画面里的模拟面板框
            danger = ("少" in txt) or ("比" in txt) or ("归一" in txt)
            png = os.path.join(tmpdir, f"ep{ep}_panel{idx:02d}.png")
            svg_to_png(svg_doc(panel_svg(txt, danger)), png, tmpdir, f"ep{ep}_panel{idx:02d}")
        else:
            rows = wrap(txt, 18 if kind == "片头" else 15)
            style = "head" if kind == "片头" else "sub"
            png = os.path.join(tmpdir, f"ep{ep}_sub{idx:02d}.png")
            svg_to_png(svg_doc(svg_lines(rows, style)), png, tmpdir, f"ep{ep}_sub{idx:02d}")
        inputs += ["-i", png]
        t0s.append(float(ln["in_sec"]))
        t1s.append(float(ln["out_sec"]))
        filters.append(f"[{vi}:v]format=rgba,scale={W}:{H}[s{vi}]")
        vi += 1

    # ---- 2b) 分镜说明层：把每镜 visual_facts 拆句铺开，补掉白模的空屏 ----
    anno_clips = build_anno_clips(ep_d11, shots, tmpdir, ep)
    for png, t0, t1 in anno_clips:
        idx = vi
        inputs += ["-i", png]
        filters.append(f"[{idx}:v]format=rgba,scale={W}:{H}[s{idx}]")
        t0s.append(t0)
        t1s.append(t1)
        vi += 1
    # 常驻角标说明（画面上永远有一行小字交代这是分镜稿）
    idx = vi
    inputs += ["-i", os.path.join(tmpdir, f"ep{ep}_annolabel.png")]
    filters.append(f"[{idx}:v]format=rgba,scale={W}:{H}[s{idx}]")
    t0s.append(0.0)
    t1s.append(45.0)
    vi += 1
    svg_to_png(svg_doc(
        f'<rect x="48" y="{ANNO_TOP - 128}" width="330" height="56" rx="8" '
        f'fill="#0A1018" fill-opacity="0.58"/>'
        f'<text x="62" y="{ANNO_TOP - 90}" font-family="{FONT}" font-size="30" '
        f'fill="#9FBBD6" letter-spacing="2">分镜说明 · 非成片字幕</text>'),
        os.path.join(tmpdir, f"ep{ep}_annolabel.png"), tmpdir, f"ep{ep}_annolabel")

    if not filters:
        filters.append("[0:v]null[v0]")
        last = "v0"
    else:
        # 链式 overlay：每层消费上一级输出，末级即最终画面
        # ⚠ 区间口径＝**左闭右开**（gte(t,t0)*lt(t,t1)），与 D16 subtitle_style 的
        #   「左闭右开」判定一致。原先用 ffmpeg 的 between(t,a,b)——它**双端闭区间**，
        #   在「上一行 out_sec ＝ 下一行 in_sec」的边界帧上两行同时渲染 → 1 帧文字重影
        #   （实测 EP001 @8.00s：两行叠字；@8.5s 干净）。抽帧审计会随机撞上这个假象。
        cur = "0:v"
        for k in range(1, vi):
            filters.append(f"[{cur}][s{k}]overlay=0:0:enable='gte(t,{t0s[k-1]:.2f})*lt(t,{t1s[k-1]:.2f})'[v{k}]")
            cur = f"v{k}"
        last = cur

    out = os.path.join(out_dir, f"EP{ep:03d}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", base] + inputs + \
          ["-filter_complex", ";".join(filters), "-map", f"[{last}]",
           "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20"]
    if keep_audio:
        cmd += ["-i", keep_audio, "-map", "0:v", "-map", f"{len(inputs)//2 + 1}:a" if False else "1:a",
                "-c:a", "aac", "-shortest"]
    else:
        cmd += ["-an"]
    cmd += [out]
    subprocess.run(cmd, check=True)

    dur = probe_dur(out)
    print(f"  EP{ep:03d} ✓ {os.path.getsize(out)//1024} KB  {dur:.1f}s  "
          f"({len(shots)} 镜 + {len(lines)} 条字幕 + {len(anno_clips)} 条分镜说明)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--ep", type=int, default=None, help="只做某一集")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # 脚本位于 <工厂根>/02_项目/双相潮主/scripts/ ⇒ 向上两级即项目根
    proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = args.unit
    d11 = json.load(open(os.path.join(proj, "units", unit, "D11.json"), encoding="utf-8"))
    d16 = json.load(open(os.path.join(proj, "units", unit, "D16.json"), encoding="utf-8"))
    shots_root = os.path.join(proj, "units", unit, "D14_shots")
    out_dir = args.out or os.path.join(proj, "preview", f"{unit}_storyboard")
    os.makedirs(out_dir, exist_ok=True)

    eps = [args.ep] if args.ep else [e["ep"] for e in d11["episodes"]]
    print(f"[BUILD] {unit} 动态分镜样片 → {out_dir}")
    with tempfile.TemporaryDirectory() as tmpdir:
        for ep in eps:
            build_ep(ep, d11, d16, shots_root, out_dir, tmpdir)
    print("[DONE]")


if __name__ == "__main__":
    main()
