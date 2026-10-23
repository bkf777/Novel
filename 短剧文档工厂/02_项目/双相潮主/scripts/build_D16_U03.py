#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U03 D16 剪辑节奏表构建器（分镜导演岗 · 2026-10-23 R-026f 任务三）

设计原则（与 U02 `scripts/build_D16_U02.py` 同源）：

  ① **JSON 是唯一真源，MD 只由 render-md.mjs 单向渲染** —— 本脚本只写 JSON。
  ② **切点预算**：D17 对 U03 的 `D16_切点` 预算是 **20**（全季 400 / 20 单元）。
     U03 全单元不设并行段（D07 各段 mode=串行）→ 每集 3 个段间边界 × 8 集 = **24 个段间切点**；
     其中 **4 个取叠化**（`counted_in_d17_cut_count: false`，不计入 D17 切点口径），
     → **计入 D17 ＝ 20**，正好满额、零余量（同 U01 的 20/26、U02 的 20/24 口径）。
  ③ **S9 纪律**：若需增切点，**先调 D17 再改 D16**；本轮不动 D17。
  ④ **余量数值必须带口径名**（D18 Q46）：镜尾余量／起音间隙／镜首余量三者分列，不写裸值。
  ⑤ **字幕行时码口径 —— 本轮是「排布稿」**：**D15 U03 整份缺件**（单元 10 件交付物现 6/10，
     缺 D13/D14/D15/D16），因此本表的时码**没有配音锚点**，按 **U02 D16 v1.0 首版**（本项目
     自己的「D15 未落盘」先例）的口径处理：
       · out_sec 由 **D09 台词字数 ÷ 4.5 字/秒**估算、下限 **1.2s**（标称 0.1s 网格）；
       · in_sec ＝ 该行所属镜的起点（全集首行取 **0.5s**＝黄金 3 秒目标；其余各镜取 镜起点＋0.4s），
         同镜第二行起取 前一行 out_sec＋0.3s；
       · 每行 note 标「排布稿」；**本表不宣称与 D15 配音一致，也不宣称任何余量结论**
         （Q49「受检 0 条的结论一律不成立」）。
     D15 U03 落盘后须按「out_sec ＝ 配音 at_sec＋dur_sec」重跑对齐并回填
     `subtitle_style.subtitle_sync_audit` 与各行 `note` —— 本脚本检测到 D15 U03 存在时
     会自动切到「配音锚点驱动」路径重跑。

用法：python3 scripts/build_D16_U03.py          # 落盘（已存在则先备份）
      python3 scripts/build_D16_U03.py --check  # 只校验，不写盘
"""
import json
import math
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

D06 = json.load(open(P("units", "U03", "D06.json"), encoding="utf-8"))
D07 = json.load(open(P("units", "U03", "D07.json"), encoding="utf-8"))
D08 = json.load(open(P("units", "U03", "D08.json"), encoding="utf-8"))
D09 = json.load(open(P("units", "U03", "D09.json"), encoding="utf-8"))
D11 = json.load(open(P("units", "U03", "D11.json"), encoding="utf-8"))
D17 = json.load(open(P("shared", "D17.json"), encoding="utf-8"))

D15_PATH = P("units", "U03", "D15.json")
D15 = json.load(open(D15_PATH, encoding="utf-8")) if os.path.exists(D15_PATH) else None
MODE = "d15_anchored" if D15 is not None else "budget_draft"

VERSION = "v1.0"

# ─────────────────────────────────────────────────────────────────────────────
# 【Q56 断言清单】—— 本脚本**跑了哪些断言**，逐条写死，禁「跑到什么算什么」。
#   本清单是**单元级副本**（承 U02 `build_D16_U02.py` 的同名清单，随脚本一起复制）。
# ─────────────────────────────────────────────────────────────────────────────
ASSERT_MANIFEST = [
    ("A01", "D11 每集镜数 == 4（U03 全单元四段制 1 镜/段）"),
    ("A02", "D11 每集镜时求和 == 45.0s"),
    ("A03", "D11 镜时逐镜等于 D07 四段边界（12／13／13／7 严格等于段界）"),
    ("A04", "D07 每集 4 段"),
    ("A05", "D07 全部段 mode=串行（1 镜/段假设成立）"),
    ("A06", "D11 dialogue 片段缺引号即中止"),
    ("A07", "D11 dialogue 未知台词即中止（D09 U03 内查无此句）"),
    ("A08", "D11 台词条数 == D09 U03 台词条数（S18 台词轴）"),
    ("A09", "D11 台词文本与 D09 逐字一致（按集按序）"),
    ("A10", "字幕行落在所在镜时间窗内"),
    ("A11", "同镜对白行不重叠"),
    ("A12", "字幕行停留 >= 1.2s（标称网格）"),
    ("A13", "字幕行限 0~45s"),
    ("A14", "字幕行不跨段间切点"),
    ("A15", "正文行 out_sec 不越过片尾标题卡 in_sec（43.0s）"),
    ("A16", "计入 D17 的切点数 <= 预算（S9：先调 D17 再改 D16）"),
    ("A17", "段间切点总数 == 24（8 集 × 3 边界）"),
    ("A18", "每集计入 D17 的切点数落在「每集 2~3 个」"),
    ("A19", "跨单元钩子链：U03 各集 hook_out == 下一集 hook_in == D06 逐字相等"),
    ("A20", "黄金 3 秒闸位：8 集逐集登记，秒码待 D15 落锚、首句文本取 D08 v1.5 原文"),
    ("A21", "画外音 delivery 三档字面与 D11 现盘画幅事实一致（Q104）"),
]

# ── 叠化方案：4 集各取 1 个段间边界取叠化（不计入 D17 切点口径）──
DISSOLVE_AT = {18: 1, 19: 3, 21: 1, 24: 2}

DISSOLVE_BASIS = {
    (18, 1): "切点落在 D07 段1 与段2 的动作交接处（骨威全开的白光铺开 → 压制范围内的人溃散为灰烬光尘）："
             "骨纹亮起的白光与随之散开的光尘叠化 0.5s，把「骨威第一次全开」与「代价第一次生效」"
             "压成同一件事，不切断这条因果。不计入 D17 切点口径。",
    (19, 3): "切点落在 D07 段3 与段4 的场景切换处（门内旗面与编号 → 厂门外灰雾里四面压来的车辙）："
             "旗面「踏入此线者死」的字与灰雾里的车辙叠化 0.5s，让威胁在旗还立着的时候就到门口。"
             "不计入 D17 切点口径。",
    (21, 1): "切点落在 D07 段1 与段2 的同一画面内（长队拐两个弯 → 逾期的人动作变慢、灰斑外扩）："
             "长队与逾期者的灰斑叠化 0.5s，把「队伍在涨」与「涨的是什么」压成一次。"
             "不计入 D17 切点口径。",
    (24, 2): "切点落在 D07 段2 与段3 的动作交接处（名单板前算出净火覆盖极限 → 雾核按在名单板上净化）："
             "算出来的那行极限数字与黑白双焰的净化叠化 0.5s，把「算不出来」与「照做」压成同一拍。"
             "不计入 D17 切点口径。",
}

# ── 各集首句的画外音分档（Q104 三档；判据＝角色身份在画幅内是否可辨识）──
#   tier1 「人物不出画」＝ 角色完全无任何形象出现在画幅内；
#   tier2 「身份不出画」＝ 角色在画幅内以可辨识形象出现、但身份不可辨识；
#   tier3 「主观声」＝ 角色以内心声出现且画幅内无其任何形象。
#   「首帧给最强符号」独立于三档，不随档位变。
#   None ＝ 说话人在画幅内（非画外音），不写 delivery。
DELIVERY_BY_EP = {
    17: None,                                                  # 叶红衣在镜1 画幅内（独自站在半圈缺口处）
    18: "画外音（身份不出画，首帧给最强符号）",                 # 陆沉腕骨纹路在画幅内、无面部/无口型/无身份锚点
    19: "画外音（人物不出画，首帧给最强符号）",                 # 陆沉不在镜1 画幅内
    20: "画外音（人物不出画，首帧给最强符号）",                 # 叶红衣不在镜1 画幅内（画幅为队伍）
    21: "画外音（人物不出画，首帧给最强符号）",                 # 陆沉不在镜1 画幅内
    22: "画外音（人物不出画，首帧给最强符号）",                 # 叶红衣不在镜1 画幅内
    23: "画外音（人物不出画，首帧给最强符号）",                 # 陆沉不在镜1 画幅内
    24: "画外音（人物不出画，首帧给最强符号）",                 # 陆沉不在镜1 画幅内
}

DELIVERY_BASIS = {
    17: "镜1 的 visual_facts 写明「叶红衣独自站在半圈缺口处，影刃横在身前」——说话人在画幅内且身份可辨识，"
        "非画外音，故不写 delivery。",
    18: "镜1 的最强符号是**陆沉的腕骨纹路**（骨纹自右腕骨一路亮到小臂）——角色以不可辨识局部在画幅内，"
        "但画面内无该角色口型、无面部、无身份锚点 ⇒ 按 Q104① 属第二档「**身份不出画**」。"
        "（D11 U03 v1.1 该镜 note 已落同一口径「身份不出画／先声后人」。）",
    19: "镜1 的 visual_facts 内无该角色、无该角色锚点（门柱与两件金属件占满画面）⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
    20: "镜1 的画幅是排队的人群（排队的人一律作剪影），门禁喊话的叶红衣不在本镜画幅内 ⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
    21: "镜1 的 visual_facts 内无该角色、无该角色锚点（长队与灰斑占满画面）⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
    22: "镜1 的 visual_facts 内无该角色、无该角色锚点（井架绞盘与返雾，作业的人只余剪影）⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
    23: "镜1 的 visual_facts 内无该角色、无该角色锚点（密信摊开，排版是合同的样子）⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
    24: "镜1 的 visual_facts 内无该角色、无该角色锚点（钢桌上并排摊着的两样东西）⇒ 按 Q104① 属第一档"
        "「人物不出画」。",
}

# ── 字幕样式（承 U01/U02 既有口径，逐字沿用，不另起写法）──
FONT = "思源黑体 Medium（规范汉字，不生造词、不用谐音）"
SIZE = "画面宽度 6%~7%（1080×1920 竖屏下约 65~76px）"
COLOR_STROKE = "文字 #FFFFFF，描边 #000000 2px，不透明度 100%，无半透明底板"
POSITION = "底部上移 ≥15% 画面高度（1080×1920 下字幕基线距底 ≥288px），水平居中"
MAX_CHARS = 15
MIN_DWELL = 1.2
BADGE_AVOID = ("对白字幕区＝字幕文字顶以下区域（基线距底 ≥15% 画面高 → 基线自顶 85%；"
               "字号 65~76px → 文字顶约 81%~81.6% 自顶）；AI 角标带＝72%~78% 自顶；"
               "两区间须留 ≥2% 画面高间距（U01 实测 3.0%~3.6%）。角标在字幕行上方。")
AI_BADGE = {
    "text": "AI 生成",
    "position": "右下角，基线画面高 72%~78%，右对齐，距右缘 ≥6% 画面宽",
    "size_opacity": "字号 ≥画面高 1.5%，不透明度 ≥50%",
    "duration": "00.0~45.0s 全集常驻（含黑场镜，本单元无黑场镜）",
}
TERMINOLOGY = ("本集字幕只出现中文界面文字与角色台词，不出现任何世界观名词作解释性字幕；"
               "术语只作内部称呼，不进画面字幕。")
SYNC_RULE = ("字幕不得早于配音起音，出点不早于配音收音；区间口径按**左闭右开**判定"
             "（out_sec 等于下一条 in_sec 视为相接，不算重叠）；重叠检查须覆盖**全部正文行**"
             "（对白／字幕／面板文字），**片尾标题卡单独检查**（其位置与对白同在底部字幕带，"
             "与对白同刻即构成真实视觉冲突）——本表正文行的 out_sec 一律不得越过片尾标题卡的 in_sec（43.0s）。")
PANEL_SUBTITLE_RULE = ("面板文字分两类处置：**面板本体弹出的提示/通报文字**进字幕层；"
                       "**读数栏的数值读数**留画面、不进字幕层（各集清单见 readout_in_frame）。"
                       "理由：读数栏已在画面内可读，再叠一条底部字幕只会与对白／片尾标题卡抢同一条字幕带。")
TAIL_CONTENT = "节目编号：〔待平台给出〕　编剧：〔待定〕　导演：〔待定〕　《双相潮主》　本片由人工智能生成"

PAYWALL = {
    "status": "待用户确认",
    "conclusion": "本集不自行指定付费卡点集数与位置；商业模式与卡点集数未获用户确认前，本集不落任何付费相关元素。",
    "basis": "D01 commercial.confirmed_by_user=false；gaps G-02（商业模式）、G-03（付费卡点集数与位置）、"
             "G-11（卡点与发行平台侧算法合规对齐）",
    "zero_elements": [
        "无卡点提示条",
        "无「解锁」「付费」「VIP」「充值」「开通」等字样（画面与声音均无）",
        "无「下集付费解锁」引导",
        "无「试看结束」「会员抢先看」角标",
        "无充值按钮、礼物入口、价格、优惠文案",
    ],
    "revision_condition": "待用户确认商业模式与卡点集数后，由本岗在本表 revisions 中补写卡点集数与位置，"
                          "不在本轮预支任何卡点铺垫。",
}

PUNCT = set("。，、；：？！“”‘’（）()《》〈〉—…·「」『』【】〔〕-—~,.!?;:'\"[]{} \t")


# ─────────────────────────────────────────────────────────────────────────────
# 取数辅助
# ─────────────────────────────────────────────────────────────────────────────
def by_ep(doc, key="episodes"):
    return {e["ep"]: e for e in doc[key]}


def d07(ep):
    return by_ep(D07)[ep]


def d06(ep):
    return by_ep(D06)[ep]


def d08(ep):
    return by_ep(D08)[ep]


def d11(ep):
    return by_ep(D11)[ep]


def d09_lines(ep):
    return [l for l in D09["lines"] if l["ep"] == ep]


def nominal(x):
    return round(x + 1e-9, 1)


def estimate_dur(text):
    """排布稿口径：out_sec 由 D09 台词字数按 4.5 字/秒估算（向上取整到 0.1s 标称网格）、下限 1.2s。"""
    n = len([c for c in text if c not in PUNCT])
    return max(MIN_DWELL, nominal(math.ceil(n / 4.5 * 10) / 10))


def clause(vf):
    """visual_facts 的首个分句（作为切点/片头的画面锚点，逐字取自 D11，不改写）。"""
    parts = [p for p in re.split(r"[；;]", vf) if p.strip()]
    return parts[0].strip() if parts else vf.strip()


def parse_dialogue(raw):
    """D11 dialogue 形如 `角色「台词」／角色「台词」`。返回 [(角色, 台词)]。"""
    out = []
    for seg in raw.split("／"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"^([^「」]+)「([^」]+)」$", seg)
        if not m:
            raise AssertionError(f"A06 D11 dialogue 片段缺引号或格式异常：{seg!r}")
        out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def first_line_of_ep(ep):
    """D08 v1.5 现盘首句原文（第一个 dialogue body 条目）。"""
    for b in d08(ep)["body"]:
        if b.get("type") == "dialogue":
            return b["text"], b.get("char_id"), b.get("shot_intent")
    raise AssertionError(f"A20 ep{ep}：D08 body 内无 dialogue 条目")


def shot_windows(ep):
    """D11 镜窗（按镜时累加）。返回 [(shot_id, start, end, shot)]。"""
    out = []
    t = 0.0
    for s in d11(ep)["shots"]:
        out.append((s["shot_id"], nominal(t), nominal(t + s["duration_sec"]), s))
        t += s["duration_sec"]
    return out


def cut_at(ep):
    """段间切点（D07 四段边界）。"""
    segs = d07(ep)["quad_segments"]
    return [(nominal(segs[i]["end_sec"]), segs[i], segs[i + 1]) for i in range(len(segs) - 1)]


def d17_budget(unit):
    for u in D17["units"]:
        if u.get("unit") == unit:
            return u["workload"]["D16_切点"]
    raise AssertionError(f"D17 无 {unit} 的 D16_切点 预算")


# ─────────────────────────────────────────────────────────────────────────────
# 构建
# ─────────────────────────────────────────────────────────────────────────────
def build_episode(ep):
    e11 = d11(ep)
    e07 = d07(ep)
    e06 = d06(ep)
    wins = shot_windows(ep)
    segs = e07["quad_segments"]

    # ---- A01/A02/A03/A04/A05 ----
    assert len(e11["shots"]) == 4, f"A01 ep{ep}：镜数 {len(e11['shots'])} ≠ 4"
    assert nominal(e11["duration_sum_sec"]) == 45.0, f"A02 ep{ep}：镜时求和 ≠ 45.0s"
    assert len(segs) == 4, f"A04 ep{ep}：D07 段数 ≠ 4"
    assert all(s.get("mode") == "串行" for s in segs), f"A05 ep{ep}：D07 存在非串行段"
    for i, (sid, a, b, s) in enumerate(wins):
        assert nominal(b - a) == nominal(segs[i]["end_sec"] - segs[i]["start_sec"]), \
            f"A03 ep{ep}：镜{sid} 镜时 {nominal(b - a)} ≠ 段界 {nominal(segs[i]['end_sec'] - segs[i]['start_sec'])}"

    # ---- 台词收集（D11 镜位 → D09 锚点）----
    d09_by_text = {}
    for l in d09_lines(ep):
        d09_by_text[l["text"].strip("「」")] = l
    rows = []
    for sid, a, b, s in wins:
        raw = s.get("dialogue") or ""
        if not raw.strip():
            continue
        for name, text in parse_dialogue(raw):
            if text not in d09_by_text:
                raise AssertionError(f"A07 ep{ep}：D11 镜{sid} 台词「{text}」在 D09 U03 内查无此句")
            l9 = d09_by_text[text]
            rows.append({
                "char_id": l9["char_id"],
                "char_name": name,
                "text": text,
                "shot_id": sid,
                "shot_start": a,
                "shot_end": b,
                "line_ref": f"D09 ep{ep} #{l9['idx']}",
                "d09_idx": l9["idx"],
            })
    # ---- A08/A09：条数与逐字一致 ----
    assert len(rows) == len(d09_lines(ep)), \
        f"A08 ep{ep}：D11 台词 {len(rows)} 条 ≠ D09 台词 {len(d09_lines(ep))} 条"
    for r, l9 in zip(rows, d09_lines(ep)):
        assert r["text"] == l9["text"].strip("「」"), \
            f"A09 ep{ep}：D11 台词「{r['text']}」与 D09「{l9['text']}」不逐字一致"

    # ---- 字幕行时码（排布稿 / 配音锚点两路）----
    lines = []
    seq = 0
    prev_out_in_shot = {}
    for r in rows:
        seq += 1
        if MODE == "d15_anchored":
            vo = [v for v in D15["episodes"] if v["ep"] == ep][0]["voice_over"]
            hit = [v for v in vo if v["line_ref"] == r["line_ref"]]
            assert hit, f"D15 U03 无 {r['line_ref']} 的配音条目"
            v = hit[0]
            in_sec, dur = nominal(v["at_sec"]), nominal(v["dur_sec"])
            note = (f"时码由 D15 U03 配音锚点驱动：in_sec ＝ 配音 at_sec，out_sec ＝ 配音 at_sec＋dur_sec"
                    f"（{r['line_ref']}）；本行与配音逐条一致。")
            extra = {"d15_vo_at_sec": in_sec, "d15_vo_dur_sec": dur, "d15_line_ref": r["line_ref"]}
        else:
            if r["shot_id"] not in prev_out_in_shot:
                in_sec = 0.5 if r["shot_id"] == 1 else nominal(r["shot_start"] + 0.4)
            else:
                in_sec = nominal(prev_out_in_shot[r["shot_id"]] + 0.3)
            dur = estimate_dur(r["text"])
            out_sec = nominal(in_sec + dur)
            note = ("排布稿：out_sec 由 D09 台词字数按 4.5 字/秒估算、下限 1.2s（标称 0.1s 网格）；"
                    "D15 U03 落盘后须改为「配音 at_sec＋dur_sec」并重跑核对。")
            extra = {"d15_pending": True}
        out_sec = nominal(in_sec + dur)
        prev_out_in_shot[r["shot_id"]] = out_sec
        row = {
            "seq": seq,
            "type": "对白",
            "char_id": r["char_id"],
            "text": r["text"],
            "in_sec": in_sec,
            "out_sec": out_sec,
            "shot_id": r["shot_id"],
            "note": note,
        }
        row.update(extra)
        lines.append(row)

        # ---- A10/A11/A12/A13/A14/A15 ----
        assert r["shot_start"] <= in_sec and out_sec <= r["shot_end"] + 1e-9, \
            f"A10 ep{ep}：行「{r['text']}」({in_sec}~{out_sec}) 越出镜{r['shot_id']} 窗 " \
            f"({r['shot_start']}~{r['shot_end']})"
        assert nominal(out_sec - in_sec) >= MIN_DWELL, f"A12 ep{ep}：行「{r['text']}」停留 < 1.2s"
        assert 0 <= in_sec and out_sec <= 45.0, f"A13 ep{ep}：行「{r['text']}」越出 0~45s"
        for ca, _s1, _s2 in cut_at(ep):
            assert not (in_sec < ca < out_sec), f"A14 ep{ep}：行「{r['text']}」跨段间切点 {ca}s"
        assert out_sec <= 43.0 + 1e-9, f"A15 ep{ep}：行「{r['text']}」越过片尾标题卡 43.0s"

    # 同镜零重叠
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a1, a2 = lines[i]["in_sec"], lines[i]["out_sec"]
            b1, b2 = lines[j]["in_sec"], lines[j]["out_sec"]
            assert not (a1 < b2 and b1 < a2), f"A11 ep{ep}：两行重叠"

    # ---- 角标行 + 片尾行 ----
    seq += 1
    badge = {
        "type": "角标",
        "text": "AI 生成",
        "in_sec": 0,
        "out_sec": 45,
        "position": "右下角，基线 72%~78% 画面高度，右对齐，距右 ≥6% 画面宽",
        "seq": seq,
    }
    seq += 1
    tail = {
        "type": "片尾",
        "text": TAIL_CONTENT,
        "in_sec": 43,
        "out_sec": 45,
        "position": "底部字幕区（画面高度 80%~90%），叠在最后一镜末段上",
        "seq": seq,
        "note": "片头四行（剧名／节目编号／署名／AI 标识）自本版起统一移至片尾；编号不可自编（D03 §7.3）",
    }
    lines.extend([badge, tail])

    # ---- cuts / transitions ----
    cuts = []
    transitions = []
    dissolve_idx = DISSOLVE_AT.get(ep)
    counted = 0
    for i, (ca, s1, s2) in enumerate(cut_at(ep), start=1):
        from_shot = i
        to_shot = i + 1
        is_dissolve = (dissolve_idx == i)
        technique = "叠化" if is_dissolve else "硬切"
        basis = (f"镜{from_shot} 的{clause(wins[i - 1][3]['visual_facts'])}收在段界（{s1['name']}）；"
                 f"镜{to_shot} 的{clause(wins[i][3]['visual_facts'])}接住（{s2['name']}）；"
                 f"切换点落在两段动作的交接处，观众注意力由「{s1['name']}」转到「{s2['name']}」。")
        if is_dissolve:
            basis = DISSOLVE_BASIS[(ep, i)]
        cuts.append({
            "index": i,
            "at_sec": ca,
            "from_shot": from_shot,
            "to_shot": to_shot,
            "from_segment": i,
            "to_segment": i + 1,
            "technique": technique,
            "dissolve_sec": 0.5 if is_dissolve else 0,
            "counted_in_d17_cut_count": not is_dissolve,
            "basis": basis,
        })
        transitions.append({
            "type": "段间转场",
            "index": i,
            "at_sec": ca,
            "from_shot": from_shot,
            "to_shot": to_shot,
            "technique": technique,
            "dissolve_sec": 0.5 if is_dissolve else 0,
            "sound_handling": "无声音预铺位，直接随画面切换",
            "cut_basis": basis,
            "counted_in_d17_cut_count": not is_dissolve,
        })
        if not is_dissolve:
            counted += 1
    n_hard = sum(1 for c in cuts if c["technique"] == "硬切")
    n_diss = sum(1 for c in cuts if c["technique"] == "叠化")
    order_txt = "、".join(
        ("叠化 0.5s（不计入 D17）" if c["technique"] == "叠化" else "硬切（计入 D17）")
        for c in cuts)
    overall = f"本集 3 个段间边界：{order_txt}；无淡入淡出、无闪白与故障效果。"
    seg_bounds = "／".join(f"{s['start_sec']:.1f}–{s['end_sec']:.1f}" for s in segs)
    transitions.insert(0, {
        "type": "总体口径",
        "overall": overall,
        "boundary_count": len(cuts),
        "hard_cut_count": n_hard,
        "dissolve_count": n_diss,
        "d17_counted_cut_count": counted,
        "d17_count_basis": f"D17 totals「每集 2–3 个切点」，U03 单元预算 D16_切点＝{d17_budget('U03')}；"
                           f"本集 3 个段间边界中计入 D17 的为 {counted} 个（叠化 {n_diss} 个按 D16 既有口径不计入）。",
        "dissolves": [{"index": c["index"], "at_sec": c["at_sec"], "basis": c["basis"]}
                      for c in cuts if c["technique"] == "叠化"],
        "audio_lead": "本集无声音预铺位：三个段间切点均随画面切换，不做提前侵入。",
        "banned": "禁闪白、频闪、故障转场；禁任何暗示异化或疯狂的视觉特效转场。",
        "segment_alignment": f"{seg_bounds}，与 D07 ep{ep:03d} quad_segments 逐段对齐，合计 45.0s。",
    })

    # ---- readout_in_frame（读数栏数值留画面，不进字幕层）----
    readout = []
    for sid, a, b, s in wins:
        for m in re.finditer(r"读数栏显示同屏中文「([^」]+)」", s.get("visual_facts", "")):
            readout.append({
                "shot_id": sid,
                "text": m.group(1),
                "basis": "D11 原文为「视野一角的读数栏显示同屏中文「…」」——属读数栏数值，"
                         "已在画面内可读，不进字幕层。",
            })

    # ---- golden3s_first_line ----
    first_text, first_char, first_intent = first_line_of_ep(ep)
    gate = {
        "target": "首句台词 ≤1.5s 入画（短剧黄金 3 秒）",
        "status": "待 D15 落锚",
        "text": first_text,
    }
    gate_row = rows[0]
    gate["planned_in_sec"] = 0.5
    gate["budget_dur_sec"] = estimate_dur(gate_row["text"])
    gate["planned_out_sec"] = nominal(0.5 + gate["budget_dur_sec"])
    if DELIVERY_BY_EP[ep]:
        gate["delivery"] = DELIVERY_BY_EP[ep]
    gate["d15_pending"] = ("声音设计岗需为该句新增 voice_over（at_sec 0.5、dur_sec 按实测）；"
                            "D15 U03 整份缺件，本岗随后按实测同步本表该行。")
    gate["note"] = (
        f"首句取 D08 U03 v1.5 现盘原文 {first_text}（说话人 {first_char}）。"
        f"秒码**待 D15 落锚**：本集预算时码为 0.5~{gate['planned_out_sec']}s"
        f"（预算停留 {gate['budget_dur_sec']}s，按 4.5 字/秒估算、下限 1.2s），"
        "D15 U03 落盘后须按实测复核并回填 `d15_vo_at_sec`／`d15_vo_dur_sec`。"
        f"画幅口径：{DELIVERY_BASIS[ep]}")

    # ---- subtitle_sync_audit ----
    dialogue_rows = [r for r in lines if r.get("type") == "对白"]
    if MODE == "d15_anchored":
        audit = {
            "synced_row_count": len(dialogue_rows),
            "no_vo_anchor_rows": 0,
            "sync_basis": "本集对白字幕行与 D15 U03 配音**逐条对应**：in_sec ＝ 配音 at_sec，"
                          "out_sec ＝ 配音 at_sec＋dur_sec，逐条严格相等。",
            "verified_against_d15": D15.get("version"),
            "verified_note": "待 D15 U03 落盘后按实测复算并刷新本字段。",
            "rows": [],
        }
    else:
        audit = {
            "synced_row_count": 0,
            "no_vo_anchor_rows": len(dialogue_rows),
            "sync_basis": "【本表口径 · U03 首版】本集对白字幕行按 D09 台词与 D11 镜位**排布**，"
                          "尚未与 D15 U03 配音锚点核对。D15 U03 未落盘 → **受检 0 条**；"
                          "按 Q49「受检 0 条的结论一律不成立」，本表**不宣称**与配音一致、也不宣称任何余量结论。"
                          "D15 U03 落盘后须重跑核对并回填本字段与 rows。",
            "verified_against_d15": "（未核对）D15 U03 尚未落盘",
            "verified_note": "本轮**未执行** D15↔D16 时码复算（受检 0 条），因此本表不含任何余量数值结论。"
                              "待 D15 U03 落盘后，复算须覆盖：本集对白字幕行与配音 out_sec 逐条比对、"
                              "越出本镜时间窗、跨段间切点、停留 <1.2s、以及镜尾余量／起音间隙／镜首余量"
                              "三口径最小值（D18 Q46：余量数值必须带口径名）。",
            "rows": [],
        }

    # ---- 字幕样式 ----
    if MODE == "d15_anchored":
        dwell_extra = ""
    else:
        dwell_extra = ("【本表口径 · 2026-10-23 U03 首版】本集对白字幕行为**排布稿**："
                       "D15 U03 尚未落盘，本表**未与配音锚点核对**（受检 0 条）。"
                       "按 Q49「受检 0 条的结论一律不成立」，本表**不宣称**与 D15 配音一致；"
                       "D15 U03 落盘后须按「out_sec ＝ 配音 at_sec＋dur_sec」重跑对齐并回填本字段与 "
                       "subtitle_sync_audit.rows。预算口径：out_sec 由 D09 台词字数按 4.5 字/秒估算、"
                       "下限 1.2s（标称 0.1s 网格）；in_sec ＝ 该行所属镜的起点（全集首行取 0.5s＝黄金 3 秒目标，"
                       "其余各镜取 镜起点＋0.4s），同镜第二行起取 前一行 out_sec＋0.3s。")

    subtitle_style = {
        "font": FONT,
        "size": SIZE,
        "color_stroke": COLOR_STROKE,
        "position": POSITION,
        "max_chars_per_line": MAX_CHARS,
        "min_dwell_sec": MIN_DWELL,
        "dwell_calc_convention": (
            "停留按标称时码计（in_sec/out_sec 均为 0.1s 精度时间码），标称 ≥1.2s 即合规；"
            "二进制浮点表示尾差（如 37.4−36.2 实算 1.1999999999999957）不是时码精度问题，"
            "不构成不合格依据，判定基准一律取 0.1s 标称网格。" + dwell_extra),
        "sync_rule": SYNC_RULE,
        "badge_avoid": BADGE_AVOID,
        "ai_badge": AI_BADGE,
        "terminology_rule": TERMINOLOGY,
        "lines": lines,
        "subtitle_sync_audit": audit,
        "panel_subtitle_rule": PANEL_SUBTITLE_RULE,
        "readout_in_frame": readout,
        "golden3s_first_line": gate,
    }

    # ---- title_card ----
    first_frame = clause(wins[0][3]["visual_facts"])
    last_shot = wins[-1][3]
    nxt = ep + 1
    if nxt in by_ep(D06):
        gloss = d07(nxt).get("carry_over", "")
        gloss = gloss.split("——", 1)[1] if "——" in gloss else ""
        next_hook = f"ep{nxt:03d} 承接「{e06['hook_out']}」——{gloss}"
    else:
        next_hook = (f"U04 承接「{e06['hook_out']}」（D06 U03 v1.1 出钩）；"
                     "U04 的入钩与承接句待 D06 U04 落盘后由本岗回填 —— "
                     "跨单元钩子链跨不过缺件，本岗不自造 U04 正文。")
    title_card = {
        "head": {
            "in_sec": 0,
            "out_sec": 0,
            "form": "**不做片头文字层**——剧名／节目编号／编剧导演署名／AI 标识四行全部撤出正文区，"
                    "改由片尾 43~45s 标题层承担；第 0 帧直接给画面本身",
            "layout": "无。画面上部带区（画面高度 6%~20%）在本集不承载任何文字",
            "fade": "无文字层，故无淡入淡出；画面本身无淡入淡出",
            "first_frame": f"0.0s 首帧即为{first_frame}，非黑场、无文字层",
            "basis": "短剧黄金 3 秒：第 0 帧必须是「已经出事的画面」，不能是环境铺陈，也不能是字幕板；"
                     "四行片头原本占掉 0~2s，且含「〔待平台给出〕」「〔待定〕」等半成品信息，劝退观众。",
        },
        "tail": {
            "in_sec": 43,
            "out_sec": 45,
            "form": f"不切黑、不新增静止无信息镜（D10.camera_language.banned「长时间静止无信息镜」）；"
                    f"画面保持镜{last_shot['shot_id']} 末帧（{clause(last_shot['visual_facts'])}），"
                    "片尾字幕层叠在其上",
            "audio": "43.0~45.0s 音乐收尾，环境声保留至 45.0s，不做绝对静音",
            "next_ep_hook": next_hook,
            "content": TAIL_CONTENT,
        },
        "compliance": {
            "ai_disclosure": "AI 生成标识义务由**全片右下角常驻角标「AI 生成」**"
                              "（本集各镜 visual_facts 逐镜声明、D12 对应卡 negatives 逐卡声明）＋"
                              "**片尾字幕「本片由人工智能生成」**承担；片头不再重复大字"
                              "（D03 R09 要求的是常驻明显位置标识，角标已在；片头大字既重复又占掉最贵的 2 秒）",
            "title_items_checklist": "剧名／编号位／署名／AI 标识 四项**齐备但统一在片尾 43~45s 呈现**",
            "pending_fill": "剧名定稿（D03 §7.1）、节目编号（平台出具，不可自编）、编剧与导演署名",
        },
    }

    return {
        "ep": ep,
        "cuts": cuts,
        "transitions": transitions,
        "subtitle_style": subtitle_style,
        "title_card": title_card,
        "paywall_point": json.loads(json.dumps(PAYWALL)),
    }, counted


def main():
    check_only = "--check" in sys.argv
    errors = []

    # ---- 单元级断言 ----
    # A16/A17/A18：切点预算
    budget = d17_budget("U03")
    eps = sorted(d11(e)["ep"] for e in by_ep(D11))
    total_counted = 0
    per_ep_counted = {}
    for ep in eps:
        cuts = cut_at(ep)
        if len(cuts) != 3:
            errors.append(f"A17 ep{ep}：段间边界 {len(cuts)} 个 ≠ 3")
    total_boundaries = sum(len(cut_at(ep)) for ep in eps)
    if total_boundaries != 24:
        errors.append(f"A17：段间切点总数 {total_boundaries} ≠ 24（8 集 × 3 边界）")
    n_dissolve = len(DISSOLVE_AT)
    counted_total = total_boundaries - n_dissolve
    if counted_total > budget:
        errors.append(f"A16：计入 D17 的切点数 {counted_total} > 预算 {budget}（S9：先调 D17 再改 D16）")
    for ep in eps:
        c = len(cut_at(ep)) - (1 if ep in DISSOLVE_AT else 0)
        per_ep_counted[ep] = c
        if not (2 <= c <= 3):
            errors.append(f"A18 ep{ep}：计入 D17 的切点数 {c} 不落在「每集 2~3 个」")
    if len(DISSOLVE_AT) != 4:
        errors.append(f"A16/A18：叠化集数 {len(DISSOLVE_AT)} ≠ 4（{total_boundaries} 边界 − 4 叠化 ＝ {counted_total}）")

    # A19：跨集钩子链
    for ep in eps[:-1]:
        if d06(ep)["hook_out"] != d06(ep + 1)["hook_in"]:
            errors.append(f"A19 ep{ep}：hook_out ≠ ep{ep + 1} hook_in")

    # A20/A21：闸位与分档
    for ep in eps:
        try:
            ft, fc, fi = first_line_of_ep(ep)
        except AssertionError as e:
            errors.append(f"A20 {e}")
            continue
        if ft.strip("「」") != rows_first_text(d11(ep)):
            errors.append(f"A20 ep{ep}：D08 首句与 D11 镜1 首句不一致")
        if DELIVERY_BY_EP[ep] and "画外音" not in DELIVERY_BY_EP[ep]:
            errors.append(f"A21 ep{ep}：delivery 字面异常")
        if DELIVERY_BY_EP[ep] and "首帧给最强符号" not in DELIVERY_BY_EP[ep]:
            errors.append(f"A21 ep{ep}：delivery 丢失「首帧给最强符号」（Q104③）")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # ---- 逐集构建 ----
    episodes = []
    for ep in eps:
        e, counted = build_episode(ep)
        episodes.append(e)

    total_counted = sum(per_ep_counted.values())
    print(f"ℹ️ 模式：{MODE}"
          + ("（D15 U03 已落盘，走配音锚点驱动）" if MODE == "d15_anchored"
             else "（D15 U03 缺件，走排布稿口径；所有 D15 锚点字段标「待 D15 落锚」）"))
    print(f"ℹ️ 切点：段间边界 {total_boundaries} 个，叠化 {len(DISSOLVE_AT)} 个，"
          f"计入 D17 {total_counted} 个（预算 {budget}）")

    doc = {
        "doc_id": "D16",
        "unit": "U03",
        "version": VERSION,
        "status": "in_review",
        "episodes": episodes,
    }

    if check_only:
        print("✅ --check 通过；未写盘。")
        return 0

    out = P("units", "U03", "D16.json")
    if os.path.exists(out):
        ts = time.strftime("%Y%m%d-%H%M%S")
        bakdir = P("reports", f"_bak_D16_U03_{ts}")
        os.makedirs(bakdir, exist_ok=True)
        shutil.copy2(out, os.path.join(bakdir, "D16.json"))
        print(f"ℹ️ 旧版已备份：{os.path.relpath(bakdir, ROOT)}")

    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, out)

    print(f"✅ 已落盘：{os.path.relpath(out, ROOT)}  {VERSION}")
    for e in episodes:
        g = e["subtitle_style"]["golden3s_first_line"]
        print(f"   ep{e['ep']:03d} 闸位 {g['status']}｜首句 {g['text']}｜"
              f"0.5~{g['planned_out_sec']}s（待 D15 落锚）"
              f"｜delivery {g.get('delivery', '（无：说话人在画内）')}")
    return 0


def rows_first_text(e11):
    """D11 镜1 的首句台词原文（用于与 D08 首句交叉核对）。"""
    for s in e11["shots"]:
        raw = s.get("dialogue") or ""
        if raw.strip():
            return parse_dialogue(raw)[0][1]
    raise AssertionError("D11 镜1 无台词")


if __name__ == "__main__":
    sys.exit(main())
