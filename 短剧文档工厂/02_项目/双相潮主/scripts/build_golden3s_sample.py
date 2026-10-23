#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_golden3s_sample.py —— EP001「黄金 3 秒」分镜动效稿（45s，1080×1920）

为什么不用白模底片：白模是纯几何，看不出骨纹、面板与红光，做出来观众看不懂
（本项目的教训：交付物必须先过「人能不能看懂」这一关）。
本脚本用手写 SVG **矢量分镜**重画 EP001 四镜，字幕严格按 D16 新时码烧录，
音频用 preview/U01_tts 的实测配音（缺失处留静音，不臆造）。

硬边界：不生成图片/视频素材（这里只是矢量绘图 + 字幕烧录）、
不提交 H3 付费生成、不做美术终稿——这是**分镜动效稿**，不是成片。

用法
----
python3 scripts/build_golden3s_sample.py [--ep 1] [--out <dir>]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
FONT = "Hiragino Sans GB"
SUB_TOP = 1500
FPS = 24

# 配乐式底噪：D15 写明「低频嗡鸣铺底 40~60Hz」——用极低音量正弦近似，不做音乐
DRONE_HZ = 52
DRONE_DB = -34


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def wrap(text, per_line=15):
    t = str(text)
    out = []
    while len(t) > per_line:
        out.append(t[:per_line])
        t = t[per_line:]
    out.append(t)
    return out


def svg_doc(inner, w=W, h=H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n{inner}\n</svg>')


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
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# ═══════════════════ 矢量美术 ═══════════════════
# 骨纹：黑白双线交织的游龙纹（未激活态——只有纹路，没有光晕、没有读数）
BONE = (
    '<path d="M-150 0 C-108 -34 -66 34 -24 0 C18 -34 60 34 102 0 C126 -22 140 14 150 4" '
    'stroke="#F4F8FC" stroke-width="20" fill="none" stroke-linecap="round"/>'
    '<path d="M-150 26 C-108 60 -66 -8 -24 26 C18 60 60 -8 102 26 C126 48 140 12 150 22" '
    'stroke="#0B1016" stroke-width="20" fill="none" stroke-linecap="round"/>'
    '<path d="M-150 0 C-108 -34 -66 34 -24 0 C18 -34 60 34 102 0 C126 -22 140 14 150 4" '
    'stroke="#FFFFFF" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.85"/>'
)


def scene1():
    """镜1 0-13s：出租屋满地狼藉 + 门缝红光 + 前景手腕骨纹。"""
    return f"""
<defs>
  <linearGradient id="room" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0C1118"/><stop offset="0.62" stop-color="#151D27"/>
    <stop offset="1" stop-color="#080B10"/>
  </linearGradient>
  <radialGradient id="lamp" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#EAF4FF" stop-opacity="0.5"/>
    <stop offset="1" stop-color="#EAF4FF" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="redglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#FF3B30" stop-opacity="0.7"/>
    <stop offset="1" stop-color="#FF3B30" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="arm" x1="0" y1="1" x2="0.2" y2="0">
    <stop offset="0" stop-color="#4A3327"/><stop offset="0.5" stop-color="#8A6249"/>
    <stop offset="1" stop-color="#C79A78"/>
  </linearGradient>
  <linearGradient id="sleeve" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#1B2430"/><stop offset="1" stop-color="#0C1219"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#room)"/>
<!-- 冷白灯管 -->
<rect x="150" y="104" width="780" height="14" fill="#EAF4FF" opacity="0.9"/>
<ellipse cx="540" cy="176" rx="500" ry="180" fill="url(#lamp)"/>
<!-- 窗（城市夜色） -->
<rect x="856" y="320" width="160" height="420" fill="#0B1220" stroke="#253040" stroke-width="6"/>
<g fill="#5E7FA8" opacity="0.45">
  <rect x="874" y="360" width="12" height="8"/><rect x="926" y="392" width="10" height="8"/>
  <rect x="972" y="356" width="12" height="8"/><rect x="888" y="500" width="10" height="8"/>
  <rect x="954" y="540" width="12" height="8"/><rect x="900" y="620" width="10" height="8"/>
</g>
<!-- 门（虚掩）：门框 + 细门缝红光 -->
<rect x="620" y="290" width="200" height="720" fill="#161D26" stroke="#2B3644" stroke-width="5"/>
<rect x="614" y="290" width="7" height="720" fill="#FF4A3D" opacity="0.95"/>
<ellipse cx="618" cy="650" rx="120" ry="430" fill="url(#redglow)" opacity="0.45"/>
<!-- 翻倒的椅子 -->
<g stroke="#39485A" stroke-width="13" stroke-linecap="round" fill="none">
  <path d="M236 1180 L436 1104"/><path d="M300 1186 L262 1000"/><path d="M330 1176 L292 996"/>
  <path d="M236 1180 L214 1272"/><path d="M436 1104 L470 1180"/>
</g>
<!-- 散落工具 -->
<g fill="#48586C">
  <rect x="512" y="1300" width="150" height="15" rx="6" transform="rotate(-12 512 1300)"/>
  <rect x="716" y="1346" width="96" height="11" rx="5" transform="rotate(22 716 1346)"/>
  <rect x="300" y="1392" width="120" height="13" rx="6" transform="rotate(6 300 1392)"/>
</g>
<!-- 熄灭的屏幕 -->
<rect x="700" y="1360" width="200" height="124" rx="6" fill="#0A0E14" stroke="#2B3644" stroke-width="5"/>
<!-- 前景：抬起的小臂 + 握拳的手 + 腕侧未激活骨纹（第 0 帧的钩子） -->
<g transform="translate(452 966)">
  <!-- 小臂：自下而上收窄 -->
  <path d="M-152 980 C-150 700 -108 420 -78 190 C-72 140 -68 96 -70 66
           L70 66 C68 96 72 140 78 190 C108 420 150 700 152 980 Z"
        fill="url(#arm)"/>
  <!-- 袖口 -->
  <path d="M-152 980 C-150 860 -144 790 -132 730 L132 730 C144 790 150 860 152 980 Z"
        fill="url(#sleeve)"/>
  <path d="M-134 728 C-130 742 -128 752 -128 760 L128 760 C128 752 130 742 134 728 Z"
        fill="#33404F" opacity="0.9"/>
  <!-- 手：握拳 -->
  <path d="M-70 70 C-78 -10 -48 -74 4 -78 C58 -82 84 -34 78 34
           C74 70 60 86 4 88 C-48 88 -62 82 -70 70 Z" fill="url(#arm)"/>
  <g fill="#8A6249" opacity="0.75">
    <path d="M-58 6 C-18 24 30 26 72 12 L70 44 C26 58 -22 54 -60 38 Z"/>
  </g>
  <!-- 拇指 -->
  <path d="M64 -6 C92 -2 104 22 92 40 C82 54 60 54 54 40 C48 26 54 4 64 -6 Z"
        fill="url(#arm)"/>
  <!-- 腕侧骨纹：黑白双线游龙纹，未激活＝不发光、无读数 -->
  <g transform="translate(0 30) scale(0.62 0.62)">{BONE}</g>
</g>
<!-- 底部压暗 -->
<rect x="0" y="1600" width="{W}" height="320" fill="#05070A" opacity="0.5"/>
"""


def panel_overlay():
    """面板叠加层（2.3s 起出现在镜1）：灰框 + 红字倒计时。"""
    return """
<defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#C9D6E2" stop-opacity="0.16"/>
  <stop offset="1" stop-color="#8FA2B4" stop-opacity="0.07"/></linearGradient></defs>
<rect x="232" y="690" width="616" height="250" rx="10" fill="url(#pg)" stroke="#AFC2D4"
      stroke-width="3" stroke-opacity="0.75"/>
<g stroke="#AFC2D4" stroke-opacity="0.8" stroke-width="3">
  <path d="M232 716 L232 690 L268 690"/><path d="M848 716 L848 690 L812 690"/>
  <path d="M232 914 L232 940 L268 940"/><path d="M848 914 L848 940 L812 940"/></g>
<text x="540" y="790" font-family="Hiragino Sans GB" font-size="40" fill="#9FB4C6"
      text-anchor="middle" letter-spacing="6">距灰潮试炼降临</text>
<text x="540" y="886" font-family="Hiragino Sans GB" font-size="82" font-weight="bold"
      fill="#FF4B3E" text-anchor="middle" letter-spacing="2">2 小时 58 分</text>
"""


def scene2():
    """镜2 13-26s：面板特写，承载两处信息（归档回滚完成 / 上一趟存活）。"""
    return f"""
<defs><linearGradient id="bg2" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#0A0F15"/><stop offset="1" stop-color="#10161E"/></linearGradient>
  <linearGradient id="pan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#D6E3F0" stop-opacity="0.13"/>
    <stop offset="1" stop-color="#7F93A8" stop-opacity="0.05"/></linearGradient></defs>
<rect width="{W}" height="{H}" fill="url(#bg2)"/>
<rect x="80" y="300" width="920" height="980" rx="14" fill="url(#pan)" stroke="#B4C7D8"
      stroke-width="4" stroke-opacity="0.8"/>
<g stroke="#B4C7D8" stroke-opacity="0.9" stroke-width="5" fill="none">
  <path d="M80 350 L80 300 L140 300"/><path d="M1000 350 L1000 300 L940 300"/>
  <path d="M80 1230 L80 1280 L140 1280"/><path d="M1000 1230 L1000 1280 L940 1280"/></g>
<g stroke="#7F93A8" stroke-opacity="0.55" stroke-width="3">
  <path d="M96 440 L152 440"/><path d="M96 480 L152 480"/><path d="M928 440 L984 440"/>
  <path d="M928 480 L984 480"/><path d="M96 1200 L152 1200"/><path d="M928 1200 L984 1200"/></g>
<text x="140" y="404" font-family="Hiragino Sans GB" font-size="46" fill="#C7D6E4"
      letter-spacing="4">归档回滚完成。</text>
<text x="540" y="740" font-family="Hiragino Sans GB" font-size="44" fill="#93A8BC"
      text-anchor="middle" letter-spacing="6">距灰潮试炼降临</text>
<text x="540" y="868" font-family="Hiragino Sans GB" font-size="116" font-weight="bold"
      fill="#FF4B3E" text-anchor="middle">2 小时 58 分</text>
<rect x="140" y="1010" width="800" height="2" fill="#5E7286" opacity="0.7"/>
<text x="140" y="1080" font-family="Hiragino Sans GB" font-size="42" fill="#8FA2B4"
      letter-spacing="3">上一趟存活 3 小时 04 分</text>
<text x="940" y="1080" font-family="Hiragino Sans GB" font-size="42" fill="#8FA2B4"
      text-anchor="end" letter-spacing="3">本次窗口 2 小时 58 分</text>
<text x="540" y="1170" font-family="Hiragino Sans GB" font-size="52" font-weight="bold"
      fill="#FF4B3E" text-anchor="middle" letter-spacing="2">比上一趟少 6 分钟</text>
<g fill="#41505F">
  <rect x="140" y="1170" width="600" height="10" rx="5"/>
  <rect x="140" y="1206" width="470" height="10" rx="5"/>
  <rect x="140" y="1242" width="690" height="10" rx="5"/></g>
"""


def scene3():
    """镜3 26-38s：倒饼干、抓钢钎、膝软扶墙、门洞里全是红灯 + 面板爆点红字。"""
    return f"""
<defs>
  <linearGradient id="bg3" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#090D12"/><stop offset="1" stop-color="#0E141C"/></linearGradient>
  <linearGradient id="hall" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2E0B09"/><stop offset="1" stop-color="#7E1A13"/></linearGradient>
  <linearGradient id="floor3" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#151C25"/><stop offset="1" stop-color="#0A0E13"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg3)"/>
<!-- 地面 -->
<path d="M0 1240 L1080 1240 L1080 1920 L0 1920 Z" fill="url(#floor3)"/>
<!-- 左侧墙（陆沉撑着的那面） -->
<path d="M0 240 L232 300 L232 1240 L0 1240 Z" fill="#121924"/>
<g stroke="#212B37" stroke-width="4" opacity="0.9">
  <path d="M0 470 L232 510"/><path d="M0 720 L232 745"/><path d="M0 980 L232 990"/></g>
<!-- 门洞：门开着，洞里是楼道红光（透视梯形） -->
<path d="M742 300 L1010 300 L960 1240 L790 1240 Z" fill="url(#hall)"/>
<path d="M700 270 L1046 270 L1010 300 L742 300 Z" fill="#1B242F"/>
<path d="M756 1240 L980 1240 L1080 1420 L620 1420 Z" fill="#3A110E" opacity="0.55"/>
<g stroke="#3A0E0B" stroke-width="4" opacity="0.8">
  <path d="M760 300 L800 1240"/><path d="M995 300 L952 1240"/></g>
<!-- 楼道红灯（自上而下渐亮） -->
<g>
  <circle cx="876" cy="420" r="19" fill="#FF6A56" opacity="0.95"/>
  <circle cx="876" cy="420" r="66" fill="#FF3B30" opacity="0.20"/>
  <circle cx="872" cy="600" r="21" fill="#FF5A46" opacity="0.95"/>
  <circle cx="872" cy="600" r="72" fill="#FF3B30" opacity="0.22"/>
  <circle cx="868" cy="790" r="23" fill="#FF4B38" opacity="0.95"/>
  <circle cx="868" cy="790" r="78" fill="#FF3B30" opacity="0.24"/>
  <circle cx="864" cy="990" r="25" fill="#FF3B30" opacity="0.95"/>
  <circle cx="864" cy="990" r="86" fill="#FF3B30" opacity="0.26"/>
</g>
<!-- 陆沉剪影：侧身、一手撑墙、一手抓钢钎 -->
<g fill="#070A0E">
  <ellipse cx="392" cy="520" rx="58" ry="70"/>
  <path d="M338 590 q54 -24 108 2 l30 300 q-84 30 -168 2 z"/>
  <path d="M430 626 L560 700 L596 946 L512 956 L436 780 Z"/>
  <path d="M342 630 L262 690 L236 872 L312 890 L382 760 Z"/>
  <path d="M352 890 L318 1250 L402 1254 L424 896 Z"/>
  <path d="M432 892 L486 1248 L566 1232 L500 884 Z"/>
</g>
<!-- 钢钎（被抓在手里） -->
<g stroke="#8FA2B6" stroke-width="12" stroke-linecap="round">
  <path d="M596 940 L660 1120"/></g>
<!-- 地上的饼干碎块 + 工具箱 -->
<g fill="#6E5B3C">
  <rect x="180" y="1300" width="66" height="34" rx="5" transform="rotate(-18 180 1300)"/>
  <rect x="252" y="1330" width="62" height="32" rx="5" transform="rotate(24 252 1330)"/>
  <rect x="310" y="1302" width="58" height="30" rx="5" transform="rotate(6 310 1302)"/>
  <rect x="200" y="1372" width="50" height="26" rx="5" transform="rotate(-34 200 1372)"/></g>
<g fill="#1D2733" stroke="#4A5A6C" stroke-width="4">
  <rect x="556" y="1300" width="230" height="150" rx="8"/>
  <rect x="548" y="1256" width="244" height="48" rx="8" transform="rotate(-10 670 1280)"/></g>
<g stroke="#6B7C8F" stroke-width="11" stroke-linecap="round"><path d="M596 1368 L760 1368"/></g>
"""


def scene4():
    """镜4 38-45s：楼道走廊，感应灯由红转绿，人影上楼远去。"""
    vx, vy = 545, 880          # 灭点
    return f"""
<defs>
  <linearGradient id="bg4" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#070A0F"/><stop offset="1" stop-color="#0B1118"/></linearGradient>
  <linearGradient id="wallL" x1="1" y1="0" x2="0" y2="0">
    <stop offset="0" stop-color="#18212C"/><stop offset="1" stop-color="#090D12"/></linearGradient>
  <linearGradient id="wallR" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#18212C"/><stop offset="1" stop-color="#090D12"/></linearGradient>
  <linearGradient id="step" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#1B2530"/><stop offset="1" stop-color="#0F151D"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg4)"/>
<!-- 走廊两侧墙（向灭点收敛） -->
<path d="M0 0 L{vx-70} {vy-140} L{vx-70} {vy+120} L0 1920 Z" fill="url(#wallL)"/>
<path d="M1080 0 L{vx+70} {vy-140} L{vx+70} {vy+120} L1080 1920 Z" fill="url(#wallR)"/>
<!-- 天花 -->
<path d="M0 0 L1080 0 L{vx+70} {vy-140} L{vx-70} {vy-140} Z" fill="#0C1219"/>
<!-- 楼梯：向上的一串台阶 -->
<g fill="url(#step)" stroke="#070A0E" stroke-width="3">
  <path d="M-40 1920 L640 1920 L612 1790 L28 1790 Z"/>
  <path d="M28 1790 L612 1790 L586 1666 L64 1666 Z"/>
  <path d="M64 1666 L586 1666 L562 1548 L102 1548 Z"/>
  <path d="M102 1548 L562 1548 L540 1436 L140 1436 Z"/>
  <path d="M140 1436 L540 1436 L520 1330 L176 1330 Z"/>
  <path d="M176 1330 L520 1330 L502 1228 L210 1228 Z"/>
  <path d="M210 1228 L502 1228 L486 1130 L240 1130 Z"/>
  <path d="M240 1130 L486 1130 L472 1036 L268 1036 Z"/>
  <path d="M268 1036 L472 1036 L462 946 L292 946 Z"/>
</g>
<!-- 扶手 -->
<g stroke="#2A3746" stroke-width="9" fill="none" opacity="0.95">
  <path d="M60 1560 L520 1080"/><path d="M0 1720 L470 1240"/></g>
<!-- 感应灯：近处绿 → 远处红 -->
<g>
  <circle cx="205" cy="1330" r="20" fill="#2ECC71" opacity="0.96"/>
  <circle cx="205" cy="1330" r="62" fill="#2ECC71" opacity="0.17"/>
  <circle cx="270" cy="1180" r="18" fill="#7FD98F" opacity="0.95"/>
  <circle cx="270" cy="1180" r="56" fill="#2ECC71" opacity="0.15"/>
  <circle cx="330" cy="1046" r="16" fill="#B9B063" opacity="0.92"/>
  <circle cx="330" cy="1046" r="50" fill="#C0392B" opacity="0.15"/>
  <circle cx="382" cy="940" r="14" fill="#D25A4C" opacity="0.92"/>
  <circle cx="382" cy="940" r="44" fill="#C0392B" opacity="0.17"/>
  <circle cx="424" cy="862" r="12" fill="#E05A4C" opacity="0.9"/>
  <circle cx="424" cy="862" r="38" fill="#C0392B" opacity="0.19"/>
</g>
<!-- 上行的人影（远） -->
<g fill="#04070A">
  <ellipse cx="452" cy="1006" rx="30" ry="36"/>
  <path d="M424 1040 q28 -12 56 0 l16 176 q-44 16 -88 0 z"/>
  <path d="M426 1210 L404 1330 L436 1338 L470 1220 Z"/>
  <path d="M470 1210 L506 1324 L534 1310 L496 1200 Z"/></g>
<g fill="#04070A" opacity="0.5">
  <ellipse cx="392" cy="920" rx="18" ry="22"/>
  <path d="M374 942 q18 -8 36 0 l10 104 q-28 10 -56 0 z"/></g>
"""


SCENES = {1: scene1, 2: scene2, 3: scene3, 4: scene4}


def build(ep, d16, out_dir, tmpdir, tts_dir):
    ep16 = next(e for e in d16["episodes"] if e["ep"] == ep)
    lines = ep16["subtitle_style"]["lines"]
    shots = [(1, 0.0, 13.0), (2, 13.0, 26.0), (3, 26.0, 38.0), (4, 38.0, 45.0)]

    # ---------- 1) 底片：4 镜矢量场景 + 运镜 ----------
    segs = []
    for sid, t0, t1 in shots:
        png = os.path.join(tmpdir, f"scene{sid}.png")
        svg_to_png(svg_doc(SCENES[sid]()), png, tmpdir, f"scene{sid}")
        dur = t1 - t0
        nfr = int(round(dur * FPS))
        if sid in (1, 2):          # 推
            vf = (f"zoompan=z='min(1.0+0.00055*on,1.16)':d=1:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
        elif sid == 3:             # 移
            vf = (f"zoompan=z='1.10':d=1:x='(iw-iw/zoom)*on/{nfr}':"
                  f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
        else:                      # 跟
            vf = (f"zoompan=z='min(1.0+0.0004*on,1.08)':d=1:"
                  f"x='iw/2-(iw/zoom/2)+on*0.25':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
        seg = os.path.join(tmpdir, f"seg{sid}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS),
                        "-i", png, "-vf", vf, "-t", f"{dur}", "-r", str(FPS),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
                        seg], check=True)
        segs.append(seg)

    clist = os.path.join(tmpdir, "concat.txt")
    with open(clist, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    base = os.path.join(tmpdir, "base.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", clist, "-c", "copy", base], check=True)

    # ---------- 2) 叠加层：面板 / 字幕 / 角标 / 片尾 ----------
    overlays = []   # (png, t0, t1)
    ov_png = os.path.join(tmpdir, "panel.png")
    svg_to_png(svg_doc(panel_overlay()), ov_png, tmpdir, "panel")
    overlays.append((ov_png, 2.3, 13.0))

    for l in lines:
        if l.get("type") == "角标":
            continue
        if l.get("type") == "面板文字":
            continue          # 面板文字已画进画面里的面板，不重复烧底部字幕
        txt = l["text"]
        rows = wrap(txt, 15)
        parts = []
        for i, r in enumerate(rows):
            parts.append(
                f'<text x="{W//2}" y="{SUB_TOP + i*92}" font-family="{FONT}" font-size="72" '
                f'fill="#FFFFFF" stroke="#000000" stroke-width="5" text-anchor="middle">'
                f'{esc(r)}</text>')
        p = os.path.join(tmpdir, f"sub{l['seq']:02d}.png")
        svg_to_png(svg_doc("\n".join(parts)), p, tmpdir, f"sub{l['seq']:02d}")
        overlays.append((p, float(l["in_sec"]), float(l["out_sec"])))

    # 角标（常驻）
    badge = os.path.join(tmpdir, "badge.png")
    svg_to_png(svg_doc(
        f'<text x="1024" y="1430" font-family="{FONT}" font-size="30" fill="#FFFFFF" '
        f'fill-opacity="0.82" text-anchor="end">AI 生成</text>'), badge, tmpdir, "badge")
    overlays.append((badge, 0.0, 45.0))

    # ---------- 3) 滤镜链：逐个 overlay ----------
    # 每张 PNG 先 format=rgba,scale 归一成同尺寸视频流，再链式 overlay（末级即成片）
    filters, cur = [], "0:v"
    idx = 0
    for png, t0, t1 in overlays:
        idx += 1
        filters.append(f"[{idx}:v]format=rgba,scale={W}:{H}[s{idx}]")
        nxt = f"v{idx}"
        filters.append(
            f"[{cur}][s{idx}]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'[{nxt}]")
        cur = nxt
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", base]
    for png, _, _ in overlays:
        cmd += ["-i", png]
    cmd += ["-filter_complex", ";".join(filters), "-map", f"[{cur}]", "-r", str(FPS),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            os.path.join(tmpdir, "video.mp4")]
    subprocess.run(cmd, check=True)

    # ---------- 4) 音频：实测配音 + 低频底噪 ----------
    audio_inputs = []
    vo = {1: ("ep001_05", 10.4), 2: ("ep001_08", 31.4), 3: ("ep001_12", 39.2)}
    hook = os.path.join(tts_dir, "audio", "ep001_hook.mp3")
    if os.path.isfile(hook):
        vo = {0: ("ep001_hook", 0.5), **vo}
    used = []
    # 音频挂载改为**按 D16 对白行时码 + items.json 文本匹配**（不再硬编码），
    # 否则台词一改时码，音轨就与字幕对不上。
    import re as _re
    items_p = os.path.join(tts_dir, "items.json")
    if os.path.isfile(items_p):
        items = json.load(open(items_p, encoding="utf-8"))
        amap = {}
        for r in items:
            if r.get("ep") == ep and r.get("kind") == "dialogue":
                k = _re.sub(r"[「」『』\"\'（）()\s]", "", r.get("text", ""))
                amap[k] = r.get("audio")
        for l in lines:
            if l.get("type") != "对白":
                continue
            k = _re.sub(r"[「」『』\"\'（）()\s]", "", l.get("text", ""))
            src = amap.get(k)
            if src and os.path.isfile(src):
                used.append((src, float(l["in_sec"])))
            else:
                print(f"   ⚠️ 缺配音（按文本未匹配到）：{l.get('text')}——该处静音")
    else:
        for key, (fn, at) in sorted(vo.items()):
            src = os.path.join(tts_dir, "audio", f"{fn}.mp3")
            if os.path.isfile(src):
                used.append((src, at))
    cmd_audio = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                 "-i", f"sine=frequency={DRONE_HZ}:duration=45"]
    for src, at in used:
        cmd_audio += ["-i", src]
    n = len(used)
    mix = ["[0:a]volume={DB}dB[bed]".replace("{DB}", str(DRONE_DB))]
    if n:
        for i, (src, at) in enumerate(used, start=1):
            d = probe_dur(src)
            mix.append(f"[{i}:a]adelay={int(at*1000)}|{int(at*1000)},volume=1.0[v{i}]")
        labels = "".join(f"[v{i}]" for i in range(1, n + 1))
        mix.append(f"{labels}amix=inputs={n}:normalize=0:dropout_transition=0[mv]")
        mix.append("[bed][mv]amix=inputs=2:normalize=0:dropout_transition=0[aout]")
    else:
        mix.append("[bed]anull[aout]")
    cmd_audio += ["-filter_complex", ";".join(mix), "-map", "[aout]",
                  "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "1",
                  os.path.join(tmpdir, "audio.m4a")]
    subprocess.run(cmd_audio, check=True)

    # ---------- 5) 合成 ----------
    out_mp4 = os.path.join(out_dir, f"EP{ep:03d}_黄金3秒分镜稿.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmpdir, "video.mp4"),
                    "-i", os.path.join(tmpdir, "audio.m4a"),
                    "-c:v", "copy", "-c:a", "copy", "-shortest", out_mp4], check=True)
    dur = probe_dur(out_mp4)
    print(f"✅ {out_mp4}  ({dur:.1f}s, 配音 {n} 条)")
    return out_mp4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(ROOT, "preview", "golden3s"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    d16 = json.load(open(os.path.join(ROOT, "units", "U01", "D16.json"), encoding="utf-8"))
    tts = os.path.join(ROOT, "preview", "U01_tts")
    with tempfile.TemporaryDirectory() as td:
        build(a.ep, d16, a.out, td, tts)


if __name__ == "__main__":
    main()
