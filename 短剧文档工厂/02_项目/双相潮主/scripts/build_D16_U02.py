#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U02 D16 剪辑节奏表构建器（分镜导演岗 · 2026-10-23 第三波单 `sxcz-u02-w3-d08fix-d11d16-0350`）

设计原则（与 U01 D16 v1.7 同源）：

  ① **JSON 是唯一真源，MD 只由 render-md.mjs 单向渲染** —— 本脚本只写 JSON。
  ② **切点预算**：D17 对 U02 的 `D16_切点` 预算是 **20**（全季 400 / 20 单元）。
     U02 全单元不设并行段（D07 各段 mode=串行）→ 每集 3 个段间边界 × 8 集 = **24 个段间切点**；
     其中 **4 个取叠化**（`counted_in_d17_cut_count: false`，不计入 D17 切点口径），
     → **计入 D17 ＝ 20**，正好满额、零余量（同 U01 的 20/26 口径）。
  ③ **S9 纪律**：若需增切点，**先调 D17 再改 D16**；本轮不动 D17。
  ④ **余量数值必须带口径名**（D18 Q46）：镜尾余量／起音间隙／镜首余量三者分列，不写裸值。
  ⑤ **字幕行口径**：本表对白字幕行时码**由 D15 U02 配音锚点驱动** ——
     in_sec ＝ 配音 at_sec，out_sec ＝ 配音 at_sec＋dur_sec（按 D15 条目的 `line_ref` 硬锚配对）；
     D15 缺失则脚本**直接中止**，不退化为「按字数估算」的排布稿口径
     （Q49「受检 0 条的结论一律不成立」，没有锚点就不许产出任何配音一致性结论）。

用法：python3 scripts/build_D16_U02.py          # 落盘（已存在则先备份）
      python3 scripts/build_D16_U02.py --check  # 只校验，不写盘
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

D06 = json.load(open(P("units", "U02", "D06.json"), encoding="utf-8"))
D07 = json.load(open(P("units", "U02", "D07.json"), encoding="utf-8"))
D09 = json.load(open(P("units", "U02", "D09.json"), encoding="utf-8"))
D11 = json.load(open(P("units", "U02", "D11.json"), encoding="utf-8"))
PROJ = json.load(open(P("project.json"), encoding="utf-8"))

# ── D15 U02（声音设计岗，2026-10-23 05:18:19 落盘 v1.0） ──
#   本表的字幕行时码与 `subtitle_sync_audit` **全部由 D15 配音锚点驱动**：
#   in_sec ＝ 配音 at_sec；out_sec ＝ 配音 at_sec＋dur_sec。
#   ⚠️ D15 缺失 → **直接中止**，不得退化为「按台词字数估算时长」的排布稿口径 ——
#      没有配音锚点就不许产出任何「与配音一致」或余量结论（Q49：受检 0 条的结论一律不成立）。
D15_PATH = P("units", "U02", "D15.json")
if not os.path.exists(D15_PATH):
    print("❌ 中止：units/U02/D15.json 不存在 —— 字幕时码须由 D15 配音锚点驱动，"
          "不得退化为字数估算（Q49：受检 0 条的结论一律不成立）。")
    sys.exit(2)
D15 = json.load(open(D15_PATH, encoding="utf-8"))
D15_VERSION = D15.get("version", "（未标版本）")

# ─────────────────────────────────────────────────────────────────────────────
# 【Q56 断言清单】—— 本脚本**跑了哪些断言**，逐条写死，禁「跑到什么算什么」。
#   ① 本清单是**单元级副本**：跨单元复用本脚本时，清单必须随脚本一起复制（Q56 ②）。
#   ② 新增/删除任一断言点，**必须同步更新本清单** —— 构建时的机械守卫会核对
#      「清单条数 == 实际断言点数」，对不上即 exit 2 中止（Q56 ③ 的可执行形式）。
#   ③ 每条断言都做过**负测**（把违规数据塞回去，确认精确报出并 exit 1 不写盘）。
#   ④ 来源标注：U01-R19 ＝ U01 侧已立的关（**必须跨单元复制**）；U02-自检 ＝ 本岗自查新增。
# ─────────────────────────────────────────────────────────────────────────────
ASSERT_MANIFEST = [
    ("A01", "D11 dialogue 片段缺引号即中止", "U02-自检"),
    ("A02", "D11 dialogue 未知角色名即中止", "U02-自检"),
    ("A03", "D11 dialogue 条数 == D09 台词条数", "S18 台词轴"),
    ("A04", "角色 char_id 与 D09 逐条一致", "S18 台词轴"),
    ("A05", "台词文本与 D09 逐字一致", "S18 台词轴"),
    ("A06", "D15 配音条数 == 台词条数", "S18 闭合腿"),
    ("A07", "D15 配音角色与台词一致", "S18 闭合腿"),
    ("A08", "D15 配音所属镜号与 D11 一致", "S18 闭合腿"),
    ("A09", "D15 line_ref == D09 epN #N（硬锚配对）", "S18 闭合腿"),
    ("A10", "配音时长 >= 1.2s", "S22 停留口径"),
    ("A11", "字幕行落在所在镜时间窗内", "U01-R19 跨单元复制"),
    ("A12", "同镜对白行不重叠", "U01-R19 跨单元复制"),
    ("A13", "D07 每集 4 段", "U01-R19 跨单元复制"),
    ("A14", "D07 全部段 mode=串行（1 镜/段假设成立）", "U01-R19 跨单元复制"),
    ("A15", "D11 每集镜数 == 4", "U01-R19 跨单元复制"),
    ("A16", "面板字幕行顺延后仍在本镜时间窗内", "U02-自检"),
    ("A17", "字幕行停留 >= 1.2s", "S22 停留口径"),
    ("A18", "字幕行限 0~45s", "U01-R19 跨单元复制"),
    ("A19", "字幕行不越所在镜时间窗", "U01-R19 跨单元复制"),
    ("A20", "字幕行不跨段间切点", "U01-R19 跨单元复制"),
    ("A21", "正文行 out_sec 不越过片尾标题卡 in_sec（43.0s）", "U01-R19 跨单元复制 ★ 本轮补入"),
    ("A22", "同镜内任意两行零重叠（对白/面板文字混排）", "U01-R19 跨单元复制"),
    ("A23", "next_ep_hook 引文确实在上游钩子原文内", "U02-自检"),
    ("A24", "引文是上游起始钩子句（非中途截取）", "U02-自检"),
    ("A25", "钩子链闭合：本集 hook_out == 下一集 hook_in", "U01-R19 跨单元复制"),
    ("A26", "跨单元钩子链：U02 last_hook == U03 first_hook == D06 hook_out", "U01-R19 跨单元复制"),
    ("A27", "计入 D17 的切点数 <= 预算（S9：先调 D17 再改 D16）", "S9"),
    ("A28", "段间切点总数 == 24（8 集 × 3 边界）", "U01-R19 跨单元复制"),
    ("A29", "对白字幕行逐集条数 == D09 台词条数", "S18 台词轴"),
    ("A30", "每集计入 D17 的切点数落在「每集 2~3 个」", "D17 口径"),
    ("A31", "audit_field_scope 全部 4 个计数字段/明细的 row_filter+predicate 复算值 == 落盘值（口径与数值自洽；8 集 × 4 字段 = 32 项复算）", "D18 U02-R29"),
    ("A32", "「实际音频轴未测（受检 0 条）」声明在位且未改写", "D18 U02-R29 ⑤"),
    ("A33", "产物↔盘上无未声明差异（漂移守卫，只允许已声明版本变更/新增键之差）", "分镜导演 A36 2026-10-23"),
]

VERSION = "v1.5"


def _vkey(v):
    """版本号 → 可比较的 (主, 次) 元组；非 vX.Y 形式一律按 (0, 0) 视作最低。"""
    m = re.match(r"^v?(\d+)\.(\d+)$", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

# ─────────────────────────────────────────────────────────────────────────────
# 切点方案：每集 3 个段间边界；指定集的第 3 个（或第 2 个）边界取叠化（不计入 D17）。
#   叠化理由逐集登记在 transitions[].basis。
# ─────────────────────────────────────────────────────────────────────────────
DISSOLVE_AT = {11: 3, 12: 2, 13: 3, 16: 3}

DISSOLVE_BASIS = {
    11: "切点落在 D07 段3 与段4 的场景切换处（D07 scenes：B-3 机械厂 → B-4 骨市黑市）："
        "厂房里成制的节拍与黑市电子屏的第一条交易信息叠化 0.5s，把「刚立住编制」与「市面已经开张」"
        "压成同一件事，同时消掉等长镜头的机械感。",
    12: "切点落在 D07 段1 与段2 的场所切换处（厂房内旧铁皮墙的公告投影 → 厂外道路远景）："
        "公告文字的冷光与灰雾里排队的人影叠化 0.5s，让「口径」直接落到「被清走的人」身上，"
        "不切断这条因果。不计入 D17 切点口径。",
    13: "切点落在 D07 段3 与段4 的场景切换处（D07 scenes：B-6 骨市黑市 → B-7 机械厂保险柜位）："
        "交易台上律条的冷光与锁柜小间门缝里收掉的一线冷光叠化 0.5s，把「成交」与「上锁」压成一次动作。"
        "不计入 D17 切点口径。",
    16: "切点落在 D07 段3 与段4 的情绪转折处（扑火撤人 → 厂门暗处影刃封路与全城入夜）："
        "钢架残骸的火光与天幕压下的转黑叠化 0.5s，把这一夜的账一次性收束。不计入 D17 切点口径。",
}

# ─────────────────────────────────────────────────────────────────────────────
# 声音预铺：各集在哪个切点做声音预铺、提前多少秒。
#   提前量逐集声明，**不是全局常量**（U01 ep8 的 0.3s 口径教训）。
#
# ⚠️ 措辞口径（2026-10-23 修）：必须与 **U01 D16 v1.9 逐字同构**，三要素齐全 ——
#   ① 含「**声音预铺位**」二字 ② 含切点秒数「（NN.0s）」 ③ 含提前量「提前 X.Xs」。
#   缺 ① 会让下游脚本（`reconcile_D15_D16_timing.mjs` 按「预铺」关键词解析预铺切点）**解析失败**
#   → 合法预铺被误判成「越窗／跨切点」。本轮 U02 首跑实测：**8 条伪越窗 ＋ 9 条伪跨切点**，
#   根因即 U02 措辞漏了「预铺」二字（U01 写「唯一一次声音预铺位在切点 3（38.0s）：…」）。
#   本表在 `transitions[0].audio_lead`（总体口径项）与各条 `sound_handling` 两处写明，与 U01 一致。
# ─────────────────────────────────────────────────────────────────────────────
AUDIO_LEAD = {
    9:  (3, 0.2, "唯一一次声音预铺位在切点 3（38.0s）：厂外引擎声由远及近，提前 0.2s 侵入，"
                 "切点后引擎声退到厂外、厂内钢钎轻碰钢架接管声底。"),
    10: (2, 0.2, "唯一一次声音预铺位在切点 2（24.0s）：火焰起燃的短促声提前 0.2s 侵入，"
                 "切点后白烟散尽的细响接管声底，让净火与白烟在听觉上连成一次动作。"),
    11: (2, 0.2, "唯一一次声音预铺位在切点 2（24.0s）：压制槽落料的闷响提前 0.2s 侵入，"
                 "切点后脚步声踩在同一节拍上接管声底。"),
    12: (1, 0.2, "唯一一次声音预铺位在切点 1（13.0s）：公告提示音提前 0.2s 侵入，"
                 "切点后广播逐条接力接管声底。"),
    13: (2, 0.2, "唯一一次声音预铺位在切点 2（26.0s）：金属压上木台的闷响提前 0.2s 侵入，"
                 "切点后队伍挪动声接管声底。"),
    14: (2, 0.2, "唯一一次声音预铺位在切点 2（25.0s）：钉子敲进钢柱的两声提前 0.2s 侵入，"
                 "切点后门轴转动声接管声底。"),
    15: (1, 0.2, "唯一一次声音预铺位在切点 1（13.0s）：数据板的电子蜂鸣提前 0.2s 侵入，"
                 "切点后混杂脚步声压上来接管声底。"),
    16: (2, 0.3, "唯一一次声音预铺位在切点 2（26.0s）：远处第一处火光亮起的爆响提前 0.3s 侵入，"
                 "切点后火焰爆开声接管声底。"
                 "本集提前量取 0.3s（比其余各集的 0.2s 多 0.1s），用于把「大限提醒到点火」的时距拉出来——"
                 "逐集声明，不作全局常量。"),
}

# ─────────────────────────────────────────────────────────────────────────────
# 面板文字字幕行：来自 D11 visual_facts 里的**面板本体弹出的提示/通报文字**。
#   key = ep → [(镜号, 文字, 镜内起点, 时长)]
#
# ⚠️ 口径收口（2026-10-23，U02 v1.2 修正）—— 与 **U01 D16 现行做法同构**：
#     进字幕层 ＝ **面板本体弹出的提示/通报文字**
#              （视野正中浮出的面板、面板底部通报条、面板顶部栏位）
#     留画面    ＝ **读数栏的数值读数**（视野一角读数栏／面板读数栏）
#   U01 先例：ep4 镜4「面板**一角读数栏**仍停在同屏中文「归一度 0.5%」」**未进字幕层**，
#   而同镜「面板底部滚出全区首杀通报条」**进了字幕层** —— 同一面面板上，两类文字分开处置。
#
#   本轮 U02 首版（v1.0／v1.1）把 8 条「归一度 X%」**读数栏**误作面板文字进了字幕层，
#   后果：ep10 seq9（42.5~43.9）与 ep15 seq10（42.3~43.7）**伸进片尾标题卡带**
#   （43.0~45.0，与对白同在底部字幕区＝真实视觉冲突）。故按上述口径改正。
# ─────────────────────────────────────────────────────────────────────────────
PANEL_LINES = {
    11: [(3, "新手福利期结束", 0.8, 1.6)],
    16: [(1, "归档大限日：十四天大限", 1.0, 1.8), (1, "逾期未处理的灰斑开始异化", 2.8, 1.8)],
}

# 读数栏（**留画面、不进字幕层**）：登记在 D16 供审读与追溯 —— 每条注明所在镜与原文出处。
READOUT_IN_FRAME = {
    9:  [(3, "归一度 0.7%")],
    10: [(4, "归一度 1.0%")],
    11: [(3, "归一度 1.1%")],
    12: [(4, "归一度 1.2%")],
    13: [(4, "归一度 1.2%")],
    14: [(4, "归一度 1.3%")],
    15: [(4, "归一度 1.3%")],
    16: [(4, "归一度 1.4%")],
}

# v1.2 改正**之前**的旧版式面板行全集（含读数栏曾被当作面板文字的那些行）——
#   仅用于**忠实复现旧版式排布**并生成序号迁移对照表，不参与现行字幕层的任何时码排定。
LEGACY_PANEL_LINES = {
    9:  [(3, "归一度 0.7%", 1.2, 1.4)],
    10: [(4, "归一度 1.0%", 0.8, 1.4)],
    11: [(3, "新手福利期结束", 0.8, 1.6), (3, "归一度 1.1%", 3.0, 1.4)],
    12: [(4, "归一度 1.2%", 0.8, 1.4)],
    13: [(4, "归一度 1.2%", 0.8, 1.4)],
    14: [(4, "归一度 1.3%", 0.8, 1.4)],
    15: [(4, "归一度 1.3%", 0.8, 1.4)],
    16: [(1, "归档大限日：十四天大限", 1.0, 1.8), (1, "逾期未处理的灰斑开始异化", 2.8, 1.8),
         (4, "归一度 1.4%", 0.8, 1.4)],
}

# 片头（每集相同）
HEAD_LINES = [
    {"type": "片头", "text": "《双相潮主》", "in_sec": 0, "out_sec": 2,
     "position": "上部带区（画面高度 6%~20%）第 1 行，大字"},
    {"type": "片头", "text": "节目编号：〔待平台给出〕", "in_sec": 0, "out_sec": 2,
     "position": "上部带区第 2 行",
     "note": "⛔ 不可自编；编号由播出单位出具（D03 §7.3／D18 Q4 一票否决项）"},
    {"type": "片头", "text": "编剧：〔待定〕　导演：〔待定〕", "in_sec": 0, "out_sec": 2,
     "position": "上部带区第 3 行"},
    {"type": "片头", "text": "本片由人工智能生成", "in_sec": 0, "out_sec": 2,
     "position": "上部带区第 4 行，与序 1~3 并列呈现"},
]

TAIL_LINE = {
    "type": "片尾", "text": "编剧：〔待定〕　导演：〔待定〕　《双相潮主》　本片由人工智能生成",
    "in_sec": 43, "out_sec": 45, "position": "底部字幕区（画面高度 80%~90%），叠在最后一镜末段上",
}

BADGE_LINE = {
    "type": "角标", "text": "AI 生成", "in_sec": 0, "out_sec": 45,
    "position": "右下角，基线 72%~78% 画面高度，右对齐，距右 ≥6% 画面宽",
}

# 字幕样式（与 U01 D16 v1.7 统一口径逐字一致：可计算口径 + 像素换算）
SUBTITLE_STYLE_BASE = {
    "font": "思源黑体 Medium（规范汉字，不生造词、不用谐音）",
    "size": "画面宽度 6%~7%（1080×1920 竖屏下约 65~76px）",
    "color_stroke": "文字 #FFFFFF，描边 #000000 2px，不透明度 100%，无半透明底板",
    "position": "底部上移 ≥15% 画面高度（1080×1920 下字幕基线距底 ≥288px），水平居中",
    "max_chars_per_line": 15,
    "min_dwell_sec": 1.2,
    # ⚠️ dwell_calc_convention 与 sync_rule **逐集生成**（见 main() 内赋值）——
    #   余量三口径的最小值随集不同，必须现算；此处不写死，避免留下过期口径文案。
    "dwell_calc_convention": "（逐集生成，见 main()）",
    "sync_rule": "（逐集生成，见 main()；区间口径按左闭右开判定，片尾标题卡单独检查）",
    "badge_avoid": "对白字幕区＝字幕文字顶以下区域（基线距底 ≥15% 画面高 → 基线自顶 85%；"
                   "字号 65~76px → 文字顶约 81%~81.6% 自顶）；AI 角标带＝72%~78% 自顶；"
                   "两区间须留 ≥2% 画面高间距（U01 实测 3.0%~3.6%）。角标在字幕行上方。",
    "ai_badge": {
        "text": "AI 生成",
        "position": "右下角，基线画面高 72%~78%，右对齐，距右缘 ≥6% 画面宽",
        "size_opacity": "字号 ≥画面高 1.5%，不透明度 ≥50%",
        "duration": "00.0~45.0s 全集常驻（含黑场镜，本单元无黑场镜）",
    },
    "terminology_rule": "本集字幕只出现中文界面文字与角色台词，不出现任何世界观名词作解释性字幕；"
                        "术语只作内部称呼，不进画面字幕。",
}

# 每集切点的依据（basis）文本：按集手写，每条指明「切在哪两个镜之间、为什么在此切」。
CUT_BASIS = {
    9: [
        "镜1 的焊缝从无到有收在叶红衣「门焊死了」的尾音上，镜2 客观跟拍接住引擎声逼近与把人拽进门；"
        "切换点落在台词尾音结束、厂外引擎声由远及近处，观众注意力由「封门」转到「有人来了」。",
        "镜2 的门框拥挤与拖人动作收在叶红衣「先进来。」的尾音上，镜3 近景切到陆沉的手与数据板；"
        "切换点落在台词尾音结束、陆沉伸手接板处，注意力由「进人」转到「验人」。",
        "镜3 的「板子里的东西，比你这条命值钱」落定、面板读数 0.7% 停在视野一角，镜4 切到苏清辞退到钢架后；"
        "切换点落在台词落定与读数停住处，属本集收钩起跳——误认从这一退步开始。",
    ],
    10: [
        "镜1 侧身让开半步的停顿收在陆沉「看完这一样，再走」的尾音上，镜2 近景切到工作台上的手臂；"
        "切换点落在台词尾音结束、观众视线被引向台上那一条手臂处。",
        "镜2 黑白双焰贴身起燃与接触处的亮区收在火焰起燃的短促声后，镜3 近景切到白烟自下而上散尽；"
        "切换点落在起燃动作完成、白烟尚未散尽处，净化过程在两镜之间连成一条完整可见的过程。",
        "镜3 白烟散尽与胸口起伏缓过来、板上旧结论被抹掉，镜4 近景切到腕骨纹路延到手肘与读数 1.0%；"
        "切换点落在世界观碎掉与代价落地的接缝处，属本集收钩起跳。",
    ],
    11: [
        "镜1 的指尖点过四类标注收在苏清辞「厂子能活人」的尾音上，镜2 横移镜头接住图纸上墙与钢架重排；"
        "切换点落在台词尾音结束、图纸被钉上墙处，注意力由「定方案」转到「开工」。",
        "镜2 的萃取线跑通与能量块上出料台收在落料闷响后，镜3 切到按岗表站成两列的队伍；"
        "切换点落在工序完成、编制开始成形处。",
        "镜3 面板弹出「新手福利期结束」与岗表贴在墙上的画面收在面板提示音后，镜4 切到骨市黑市电子屏；"
        "切换点落在全服提示音落定处，用叠化 0.5s 把「厂里刚立住编制」与「市面已经开张」压成同一刻。",
    ],
    12: [
        "镜1 公告第二栏原文停在「不计入救治序列」上，镜2 切到厂外排队的远景；"
        "切换点落在投影文字读完、观众被交到厂外的人群处，用叠化 0.5s 让口径直接落到被清走的人身上。",
        "镜2 队尾散进灰雾、有人回头看厂门的动作收在广播声的接力里，镜3 过肩切到门内的人影与陆沉的侧影；"
        "切换点落在广播接力停拍、门内视角接住处，注意力由「他们被清走」转到「我们也在这栏」。",
        "镜3 陆沉「……我们也在那一栏」的尾音落定，镜4 切到他转身把被净化过的灰斑者叫到一起；"
        "切换点落在台词落定、转身起势处，属本集收钩起跳。",
    ],
    13: [
        "镜1 木牌上的交换规则与陆沉「谁也带不走」的承诺收在台词尾音上，镜2 切到台面上的物资与两列队伍；"
        "切换点落在台词尾音结束、队伍绕过摊位尾处。",
        "镜2 叶红衣的影刃把队伍隔成两列收在「谁插队，退出去」的尾音上，镜3 特写切到交易台上的律条；"
        "切换点落在台词尾音结束、金属压上木台处，注意力由「秩序」转到「货」。",
        "镜3 苏清辞确认律条真伪并划下不能拆用的红线，镜4 切到厂内锁柜小间；"
        "切换点落在红线划完、陆沉点头推过律条之后，用叠化 0.5s 把「成交」与「上锁」压成一次动作。",
    ],
    14: [
        "镜1 空货架与断供通知停在电子屏滚动条目上，镜2 切到厂门钢柱上被钉上的预约牌；"
        "切换点落在条目滚完、陆沉钉牌的手起势处，注意力由「被掐」转到「改规」。",
        "镜2 陆沉「从这道门进来的，才能排上号」的尾音落定，镜3 切到会议桌上的配额名单与委员会屏幕；"
        "切换点落在台词尾音结束、名单被摊开处。",
        "镜3 成本模型最后一栏没有合上停住，镜4 过肩切到城防图与笔尖落在机械厂的名字上；"
        "切换点落在成本条目滚停、笔尖落纸处，属本集收钩起跳——财阀第一次算不过这条路。",
    ],
    15: [
        "镜1 名单与进场顺序核对完、笔尖停在最后几个名字上，镜2 切到涌进外圈的逃难人流；"
        "切换点落在笔尖停住处，观众注意力由「谁在核对」转到「谁混进来了」。",
        "镜2 旧棉衣底下的护具一角被袖子盖住、混流继续，镜3 特写切到数据板上的频谱；"
        "切换点落在护具一角被盖住处——线索先出现，证据后到。",
        "镜3 苏清辞「三个心跳不在厂区」落定，镜4 切到熄灯后围墙上那排不该在的影子；"
        "切换点落在台词落定、切灯声后，属本集收钩起跳。",
    ],
    16: [
        "镜1 面板上两行大限中文逐行亮起、远处第一处火光亮起，镜2 远景切到三处火头与退路；"
        "切换点落在第二行中文亮定、火头声起处，期限与后果在同一切点交接。",
        "镜2 三处火头与只剩一条的退路收在陆沉「钢架抬起来」的吼声里，镜3 切到钢架被抬起的缺口；"
        "切换点落在命令尾音结束、钢架离地起势处。",
        "镜3 钢架残骸与撤出的人流收在梁木断裂声后，镜4 切到厂门暗处的影刃与天幕压下的转黑；"
        "切换点落在火光与转黑之间，用叠化 0.5s 把这一夜的账一次性收束。",
    ],
}

# 每集首帧描述（片头 first_frame），以及片尾沿用的末帧描述
FIRST_FRAME = {
    9:  "0.0s 首帧即为锈蚀卷帘门内侧的焊接起弧，不是黑场",
    10: "0.0s 首帧即为冷白工业灯下抱着数据板往门口走的苏清辞，不是黑场",
    11: "0.0s 首帧即为钢桌上摊开的防御图纸，不是黑场",
    12: "0.0s 首帧即为旧铁皮墙上刚亮起的全服公告投影，不是黑场",
    13: "0.0s 首帧即为黑市摊位电子屏下压着的「无垢净髓」，不是黑场",
    14: "0.0s 首帧即为黑市摊位的空货架与压在台面上的断供通知，不是黑场",
    15: "0.0s 首帧即为指挥舱钢桌上摊开的名单与进场顺序，不是黑场",
    16: "0.0s 首帧即为视野正中浮出的面板第一行中文，不是黑场",
}

TAIL_FORM = {
    9:  "不切黑、不新增静止无信息镜（D10.camera_language.banned「长时间静止无信息镜」）；"
        "画面保持镜4 末帧（苏清辞退到钢架后、目光扫过持钎队列），片尾字幕层叠在其上",
    10: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（腕骨纹路延到手肘、读数停在 1.0%），片尾字幕层叠在其上",
    11: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（黑市电子屏滚出第一条交易信息），片尾字幕层叠在其上",
    12: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（陆沉抬头看向门外被掐断的货源路），片尾字幕层叠在其上",
    13: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（锁柜门缝里最后一线冷光收掉），片尾字幕层叠在其上",
    14: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（笔尖点在城防图上机械厂的名字上），片尾字幕层叠在其上",
    15: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（熄灯后围墙上那排不该在的影子），片尾字幕层叠在其上",
    16: "不切黑、不新增静止无信息镜；画面保持镜4 末帧（影刃横在路口、天幕压下、全城入夜），片尾字幕层叠在其上",
}

# 下一集钩子：引文片段**逐字取自下一集的钩子原文**，冒号后为本岗补的一句承接说明。
#   ep009–ep015 → 下一集 D06 的 hook_in（U02 内，ep010–ep016）。
#   ep016 → 下一集是 **U03 首集 ep017**，U02 内无 ep017 的 D06；
#     取 project.json `units[U03].first_hook`（＝「叶红衣迎战，大限夜灰雾待爆」，
#     与 U02 的 last_hook、U02 D06 ep016 的 hook_out 三者逐字一致）。
#     ⚠️ 「陆沉日夜焚斑救人数万」是 U03 的 **last_hook（ep024 钩）**，不是 U03 首钩，不可混用。
#   断言会校验引文确为上游原文，杜绝改述失配。
NEXT_HOOK = {
    9:  ("苏清辞初见陆沉，以为这是一支军阀",
         "他抱紧数据板，眼前的钢钎、焊门与一排排沉默的灰斑者，比身后的追兵更像威胁"),
    10: ("苏清辞通宵画图", "他把净火焚斑的每一道热流抄进数据板，画出一张陆沉自己都看不懂的防御图"),
    11: ("新手期结束，黑市开启", "骨市黑市的电子屏亮起第一行交易信息"),
    12: ("陆沉准备反制", "他要拿什么去反？财阀手里握着药物和安全的门"),
    13: ("世家物价崩塌，恼羞成怒", "他们要掐的是哪一只手？陆沉能不能顶住这一掐"),
    14: ("叶家决定派暗杀组", "他们有多少人、从哪进？陆沉还能不能提前察觉"),
    15: ("杀机逼近", "熄灯后的厂区，围墙上多了一排不该在的影子"),
    16: ("叶红衣迎战，大限夜灰雾待爆",
         "围墙上的影子没等到第二个人，来的是叶红衣——这一夜的账由她先开"),
}

errors = []
def chk(cond, msg):
    if not cond:
        errors.append(msg)

CHAR_NAME = {
    "LC": "陆沉", "YHY": "叶红衣", "SQC": "苏清辞",
    "YD-GC": "商既衡", "YJ-JZ": "叶崇岳", "YJ-ES": "叶承钧",
}
NAME2ID = {v: k for k, v in CHAR_NAME.items()}


def d15_voice_over(ep):
    """取 D15 U02 本集的配音条目（voice_over）。

    D15 的条目带 `char_id / shot_id / at_sec / dur_sec / line_ref`，
    其中 `line_ref`（如 `D09 ep9 #1`）是回指 D09 台词序号的**硬锚** ——
    本表用它把配音与字幕行**逐条**配对，不靠顺序猜。
    """
    e15 = next(e for e in D15["episodes"] if e["ep"] == ep)
    return e15.get("voice_over", [])


def legacy_seq_map(ep, drows, shots_start, d11):
    """计算 v1.2 面板口径改正**之前**的旧版式 seq 编号 → 现 seq 的迁移对照。

    旧版式里，读数栏行被当作面板文字进字幕层并参与排序 → 排在它之后的正文行 seq 更大；
    且**存留面板行本身的位置也会变**（例：ep11「新手福利期结束」旧位 30.7s，移走读数栏后前移到 29.0s）。
    故此处**忠实复现旧版式的排布算法**（面板行按 (镜号, 文字) 排序、逐条顺延消解），
    再算旧 seq，写进 D16 的 `subtitle_sync_audit.seq_number_migration`，
    供「点名到 seq」的引用可追溯。定位一律以「内容＋时码」为准，seq 只是当前盘上值。
    """
    occupied = {}
    for r in drows:
        occupied.setdefault(r["shot_id"], []).append((r["in_sec"], r["out_sec"]))
    merged = [(r["in_sec"], "对白", r["text"]) for r in drows]
    for (sid, text, off, dur) in sorted(LEGACY_PANEL_LINES.get(ep, []), key=lambda x: (x[0], x[1])):
        t = shots_start[sid - 1] + off
        for _ in range(24):
            ce = None
            for (a, b) in occupied.get(sid, []):
                if t < b - 1e-9 and t + dur > a + 1e-9:
                    ce = b if ce is None else max(ce, b)
            if ce is None:
                break
            t = round(ce + 0.3, 1)
        occupied.setdefault(sid, []).append((t, t + dur))
        merged.append((t, "面板文字", text))
    merged.sort(key=lambda x: (x[0], x[1] != "对白"))
    # seq 1~4 为片头行，正文行从 5 起
    seq_map = {}
    for i, (t, typ, txt) in enumerate(merged, start=5):
        seq_map[txt] = {"seq": i, "in_sec": t, "type": typ}
    return seq_map


def legacy_layout_rows(ep, drows, shots_start):
    """复现旧版式里**面板文字行**的时码（用于迁移表里「时码也变了」的那几行）。"""
    occupied = {}
    for r in drows:
        occupied.setdefault(r["shot_id"], []).append((r["in_sec"], r["out_sec"]))
    out = {}
    for (sid, text, off, dur) in sorted(LEGACY_PANEL_LINES.get(ep, []), key=lambda x: (x[0], x[1])):
        t = shots_start[sid - 1] + off
        for _ in range(24):
            ce = None
            for (a, b) in occupied.get(sid, []):
                if t < b - 1e-9 and t + dur > a + 1e-9:
                    ce = b if ce is None else max(ce, b)
            if ce is None:
                break
            t = round(ce + 0.3, 1)
        occupied.setdefault(sid, []).append((t, t + dur))
        out[text] = (t, round(t + dur, 1))
    return out


def build_sync_audit(ep, lines, vo_by_seq, shots_start, d11, cuts):
    """由 D15 U02 配音锚点**自动计算**本集的「字幕 ↔ 配音」核对结果。

    不手写 rows／余量：全部从 D15 配音条目 × D16 字幕行 × D11 镜窗 × D16 切点现算，
    保证脚本可重跑、不会算错；任何结论都随附**受检条数**（Q49）。

    三口径定义与 `scripts/reconcile_D15_D16_timing.mjs` **逐字同口径**：
      口径1「镜尾余量」＝ 镜窗结束 − 配音结束
      口径2「起音间隙」＝ 配音起音 − 本镜起始硬切点（本集若无起始硬切点则不参与取最小）
      口径3「镜首余量」＝ 配音起音 − 镜窗开始
    三个数测的是不同的东西，不可互相替代；数值一律带口径名（D18 Q46）。
    """
    vo = sorted(d15_voice_over(ep), key=lambda v: int(str(v["line_ref"]).split("#")[-1]))
    cut_at = sorted(c["at_sec"] for c in cuts)

    # ── 逐条核对：对白字幕行 vs D15 配音锚点 ──
    rows = []
    for r in lines:
        if r["type"] != "对白":
            continue
        meta = vo_by_seq.get(r["seq"])
        if meta is None:
            continue
        fl = r["out_sec"] - r["in_sec"]
        rows.append({
            "seq": r["seq"],
            "type": "对白",
            "text": r["text"],
            "char_id": r["char_id"],
            "shot_id": r["shot_id"],
            "in_sec": r["in_sec"],
            "out_sec": r["out_sec"],
            "nominal_dwell_sec": round(fl, 1),
            "float_dwell_sec": fl,
            "d15_vo_at_sec": meta["at_sec"],
            "d15_vo_dur_sec": meta["dur_sec"],
            "d15_line_ref": meta["line_ref"],
            "action": "不动",
            "verdict": "合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）",
            "note": "本行时码直接取自 D15 配音锚点，非按字数估算；"
                    "标称 dwell 与浮点 dwell 的差异仅为二进制表示尾差，不作判定依据。",
        })

    # ── 三口径最小值（**带口径名**） ──
    marg = []
    for v in vo:
        sid = v["shot_id"]
        st = shots_start[sid - 1]
        en = st + d11["shots"][sid - 1]["duration_sec"]
        at = round(float(v["at_sec"]), 1)
        du = round(float(v["dur_sec"]), 1)
        sc = [c for c in cut_at if c <= st + 1e-9]
        marg.append({
            "shot": sid, "at": at, "dur": du, "win": f"{round(st,1)}–{round(en,1)}",
            "tail": round(en - (at + du), 1),
            "gap": None if not sc else round(at - max(sc), 1),
            "head": round(at - st, 1),
        })
    min_tail = min(marg, key=lambda m: m["tail"])
    with_gap = [m for m in marg if m["gap"] is not None]
    min_gap = min(with_gap, key=lambda m: m["gap"]) if with_gap else None
    min_head = min(marg, key=lambda m: m["head"])

    def _loc(m):
        return f"ep{ep} 镜{m['shot']}"

    margin_min_by_caliber = {
        "镜尾余量": {
            "定义": "镜窗结束 − 配音结束",
            "最小值_sec": min_tail["tail"],
            "出现位置": _loc(min_tail),
            "明细": f"配音 {min_tail['at']}+{min_tail['dur']}，镜窗 {min_tail['win']}",
        },
        "起音间隙": {
            "定义": "配音起音 − 本镜起始硬切点",
            "最小值_sec": None if min_gap is None else min_gap["gap"],
            "出现位置": "（本集无起始硬切点，不参与取最小）" if min_gap is None else _loc(min_gap),
            "明细": "（无）" if min_gap is None
                    else f"配音起音 {min_gap['at']}，本镜起始硬切 {min_gap['at'] - min_gap['gap']}",
        },
        "镜首余量": {
            "定义": "配音起音 − 镜窗开始",
            "最小值_sec": min_head["head"],
            "出现位置": _loc(min_head),
            "明细": f"配音起音 {min_head['at']}，镜窗 {min_head['win']}",
        },
    }

    n_panel = sum(1 for r in lines if r["type"] == "面板文字")
    floor_rows = [r for r in rows if r["nominal_dwell_sec"] == 1.2]
    tail_rows = [r for r in rows if abs(r["float_dwell_sec"] - r["nominal_dwell_sec"]) > 0]

    # ── 结构化口径字段（U02-R29 · 企划合规 05:4x 登记并派单）────────────────
    #   缺陷：此前这些计数字段的**口径只写在自然语言正文里**，复算方必须自行反推 ——
    #   企划合规第一次独立复算即因用通用容差 1e-12 而得 0 条，**险些误判为造数**（D18 Q57）。
    #   本块把口径落成**机器可读定义**：`row_filter` ＋ `predicate` ＋ 覆盖范围/判定说明，
    #   脚本可直接消费，不必反推。
    #   ⚠️ **数值本身不动** —— 独立复算已确认 ft 21／dwell 2／synced 28／no_vo 3 全部吻合。
    audit_field_scope = {
        "_说明": (
            "本块是 `subtitle_sync_audit` 各计数字段的**机器可读口径定义**（D18 U02-R29）。"
            "此前口径只写在自然语言正文里，复算方须自行反推；本轮补为结构化定义，**数值一律不动**。"
        ),
        "synced_row_count": {
            "口径": "本集**对白字幕行**条数（逐条有 D15 配音锚点，逐条严格相等）",
            "覆盖范围": "仅对白行",
            "row_filter": {"line_type": "对白", "require_d15_vo_anchor": True},
            "predicate": "in_sec == d15_vo_at_sec and out_sec == d15_vo_at_sec + d15_vo_dur_sec（严格相等，不用容差）",
            "name_semantics_mismatch": False,
        },
        "float_tail_row_count": {
            "口径": "本集**对白字幕行**中浮点表示尾差不为零的条数",
            "覆盖范围": "仅对白行（**不是全部字幕行** —— 面板文字行无 dwell 字段，不参与；"
                        "按全部字幕行复算会得 24，差 3 条来自面板文字行）",
            "row_filter": {"line_type": "对白", "require_d15_vo_anchor": True},
            "predicate": "float_dwell_sec != nominal_dwell_sec（**严格非零，不用 1e-12 容差**；"
                          "用容差会把本项算成 0 条 —— 这正是企划合规第一次复算踩的坑）",
            "name_semantics_mismatch": False,
        },
        "no_vo_anchor_rows": {
            "口径": "本集**面板文字行**条数",
            "覆盖范围": "仅面板文字行",
            "row_filter": {"line_type": "面板文字"},
            "predicate": "count_all（面板本体弹出的提示/通报文字进字幕、声音层不承载，故无 D15 配音锚点；"
                          "**读数栏数值**留画面、不进字幕层，各集清单见 readout_in_frame）",
            "字段名字面义与实际口径": "**不一致** —— 字段名字面义是「无配音锚点的行数」，"
                                    "实际口径是「**面板文字行数**」。**下游请按本块 `read_as` 消费，勿按字段名推断**",
            "name_semantics_mismatch": True,
            "read_as": "面板文字行数",
            "改名决定": "**保留字段名不改**（分镜导演决定，U02-R29 ②③）：该键名被 U01 侧 "
                        "`patch_D16_v17_badge_avoid.mjs`、`patch_D16_dwell_convention.py` 按**键名**消费，"
                        "且 U01 D16 落盘结构有同名字段 8 处 → 改名会波及 U01 落盘结构与两个补丁脚本，"
                        "改动面远大于收益；故按「优先在结构化口径字段里写明」办，并给出 `read_as` 供脚本直接消费",
        },
        "dwell_floor_rows": {
            "口径": "标称停留＝1.2s（合规下沿）的对白行**明细列表**（非计数）",
            "覆盖范围": "仅对白行",
            "row_filter": {"line_type": "对白", "require_d15_vo_anchor": True},
            "predicate": "nominal_dwell_sec == 1.2（**按 0.1s 标称网格判定**，浮点尾差不作不合格依据）",
            "name_semantics_mismatch": False,
        },
        "actual_audio_axis": {
            "已测": False,
            "说明": "U02 无预演音频资产（`preview/` 下仅 `U01_tts`／`U01_video`）→ "
                    "「实测音频时长 vs D15 预算」这一轴**受检 0 条**，按 Q49「受检 0 条的结论一律不成立」，"
                    "本表**不作任何「实际音频已核」声明**；本表的「与配音一致」仅指与 **D15 配音锚点**一致",
        },
    }
    audit = {
        "synced_row_count": len(rows),
        "no_vo_anchor_rows": n_panel,
        "dwell_floor_rows": [
            {"seq": r["seq"], "text": r["text"], "in_sec": r["in_sec"], "out_sec": r["out_sec"],
             "nominal_dwell_sec": r["nominal_dwell_sec"], "float_dwell_sec": r["float_dwell_sec"]}
            for r in floor_rows
        ],
        "float_tail_row_count": len(tail_rows),
        "audit_field_scope": audit_field_scope,
        "sync_basis": (f"D15 U02 {D15_VERSION} 配音锚点逐条驱动：本集对白字幕行 in_sec ＝ 配音 at_sec、"
                       f"out_sec ＝ 配音 at_sec＋dur_sec，配对依据为 D15 条目的 `line_ref`"
                       f"（如 D09 ep{ep} #N）**硬锚**，不靠顺序猜；"
                       f"受检 {len(rows)} 条（对白行数），逐条严格相等。"),
        "verified_against_d15": f"{D15_VERSION}（D15 U02 落盘后现算复核；数值带版本号，D18 Q39）",
        "verified_note": (
            f"本次核对受检 {len(rows)} 条对白行（本集对白行全部有配音锚点），"
            f"逐条相等、无一条不符；另有 {n_panel} 条面板文字行无配音锚点"
            "（**面板本体弹出的提示/通报文字**进字幕、声音层不承载；"
            "**读数栏数值**留画面不进字幕层，各集清单见 readout_in_frame），"
            "按「镜内锚点＋同镜顺排消解」排定，已逐行登记 note。"
            "余量三口径的最小值见 `margin_min_by_caliber`（三个数测的是不同的东西，不可互相替代）。"
            "本轮 D16 升级 v1.0→v1.1 的实质变更：字幕行时码由「按字数估算的排布稿」改为「D15 锚点驱动」，"
            "同时取消首版「受检 0 条／不宣称与配音一致」的保留声明。"
            "⚠️ **实际音频轴未测**：U02 无预演音频资产（`preview/` 下仅 `U01_tts`／`U01_video`）→ "
            "「实测音频时长 vs D15 预算」这一轴**受检 0 条**，按 Q49「受检 0 条的结论一律不成立」，"
            "本表**不作任何「实际音频已核」声明**；本表的「与配音一致」仅指与 **D15 配音锚点**一致。"),
        "margin_min_by_caliber": margin_min_by_caliber,
        "rows": rows,
    }

    # ── A31（U02-R29）：口径字段与落盘数值**自洽** ──
    #   判据：把 `audit_field_scope` 里**声明的** row_filter ＋ predicate 套回实际字幕行集合，
    #   独立复算出的计数必须等于落盘计数值 —— 口径不是写给人看的说明，而是
    #   **脚本可直接消费的定义**（复算方不必再自行反推，也就不会再踩「容差 1e-12 → 0 条」的坑）。
    for _field in ("synced_row_count", "float_tail_row_count", "no_vo_anchor_rows", "dwell_floor_rows"):
        _sc = audit_field_scope.get(_field, {})
        _f = _sc.get("row_filter", {})
        _sub = []
        for _r in lines:
            if _r.get("type") != _f.get("line_type"):
                continue
            if _f.get("require_d15_vo_anchor") and vo_by_seq.get(_r["seq"]) is None:
                continue
            _sub.append(_r)
        if _field == "float_tail_row_count":
            _got = sum(1 for _r in _sub
                       if abs((_r["out_sec"] - _r["in_sec"]) - round(_r["out_sec"] - _r["in_sec"], 1)) > 0)
        elif _field == "dwell_floor_rows":
            _got = [{"seq": r["seq"], "text": r["text"], "in_sec": r["in_sec"], "out_sec": r["out_sec"],
                     "nominal_dwell_sec": round(r["out_sec"] - r["in_sec"], 1),
                     "float_dwell_sec": r["out_sec"] - r["in_sec"]}
                    for r in _sub if round(r["out_sec"] - r["in_sec"], 1) == 1.2]
        else:
            _got = len(_sub)
        chk(_got == audit[_field],
            f"ep{ep}: audit_field_scope.{_field} 声明的覆盖范围/判定复算得 {_got} 条 "
            f"≠ 落盘 {audit[_field]} 条（口径与数值不自洽）")
    chk(audit_field_scope["actual_audio_axis"]["已测"] is False
        and "受检 0 条" in audit_field_scope["actual_audio_axis"]["说明"],
        f"ep{ep}: 「实际音频轴未测（受检 0 条）」声明缺失或被改写（U02-R29 ⑤）")

    return audit


def dialogue_rows(ep):
    """把 D11 每镜的 dialogue 字段拆成字幕行（按镜内顺序排布）。

    D11 的 dialogue 写的是**中文角色名**（如 `叶红衣「门焊死了。」`），不是 char_id；
    本函数把角色名反查为 D09 的 char_id，并把拆出的条目与 D09 `lines` **逐条对齐**：
    条数、角色、台词文本三者必须逐字一致（任一不一致即中止写盘）。
    """
    e11 = next(e for e in D11["episodes"] if e["ep"] == ep)
    d09 = sorted([l for l in D09["lines"] if l["ep"] == ep], key=lambda l: l["idx"])

    # ── 第一步：从 D11 逐镜拆出 (角色名, 台词, 镜号) ──
    parsed = []
    for s in e11["shots"]:
        d = (s.get("dialogue") or "").strip()
        if not d:
            continue
        for p in [x for x in d.split("／") if x.strip()]:
            if "「" not in p:
                chk(False, f"ep{ep} 镜{s['shot_id']}: dialogue 片段缺引号 → {p!r}")
                continue
            head, tail = p.split("「", 1)
            name = head.strip()
            text = tail.rstrip("」").strip()
            cid = NAME2ID.get(name)
            if cid is None:
                chk(False, f"ep{ep} 镜{s['shot_id']}: 未知角色名 {name!r}")
                continue
            parsed.append({"char_id": cid, "name": name, "text": text,
                           "shot_id": s["shot_id"], "shot_dur": s["duration_sec"]})

    # ── 第二步：与 D09 台词逐条对齐（条数／角色／文本） ──
    chk(len(parsed) == len(d09),
        f"ep{ep}: D11 dialogue 拆出 {len(parsed)} 条 ≠ D09 台词 {len(d09)} 条")
    for i, (a, b) in enumerate(zip(parsed, d09)):
        chk(a["char_id"] == b["char_id"],
            f"ep{ep} 第 {i+1} 条: D11 角色 {a['name']}({a['char_id']}) ≠ D09 角色 {b['char_id']}")
        chk(a["text"] == b["text"].strip("「」").strip(),
            f"ep{ep} 第 {i+1} 条: D11 台词 ≠ D09 台词｜D11: {a['text']}｜D09: {b['text']}")

    # ── 第三步：字幕行时码**由 D15 配音锚点驱动**（D15 U02 已落盘） ──
    #   in_sec ＝ 配音 at_sec；out_sec ＝ 配音 at_sec＋dur_sec（标称 0.1s 网格）。
    #   ⚠️ 不再使用「按台词字数估算时长」的排布稿口径 —— 该口径只适用于 D15 未落盘的首版；
    #      沿用它会让字幕行与真实配音错位（首版实测：配音 28 条虽逐条相符，但行位是估算的）。
    d15vo = sorted(d15_voice_over(ep), key=lambda v: int(str(v["line_ref"]).split("#")[-1]))
    chk(len(d15vo) == len(parsed),
        f"ep{ep}: D15 配音 {len(d15vo)} 条 ≠ D11/D09 台词 {len(parsed)} 条")
    out = []
    cursor = 0.0
    shot_bounds = {}
    for s in e11["shots"]:
        shot_bounds[s["shot_id"]] = (cursor, cursor + s["duration_sec"])
        cursor += s["duration_sec"]
    for i, (a, v) in enumerate(zip(parsed, d15vo)):
        start, end = shot_bounds[a["shot_id"]]
        chk(v["char_id"] == a["char_id"],
            f"ep{ep} 第 {i+1} 条: D15 配音角色 {v['char_id']} ≠ D11/D09 角色 {a['char_id']}")
        chk(v["shot_id"] == a["shot_id"],
            f"ep{ep} 第 {i+1} 条: D15 配音所属镜 {v['shot_id']} ≠ D11 镜 {a['shot_id']}")
        chk(v["line_ref"] == f"D09 ep{ep} #{i+1}",
            f"ep{ep} 第 {i+1} 条: D15 line_ref {v['line_ref']} ≠ D09 ep{ep} #{i+1}")
        t = round(float(v["at_sec"]), 1)
        dur = round(float(v["dur_sec"]), 1)
        chk(dur >= 1.2 - 1e-9, f"ep{ep} 第 {i+1} 条: 配音时长 {dur}s < 1.2s")
        chk(t >= start - 1e-6 and t + dur <= end + 1e-6,
            f"ep{ep} 镜{a['shot_id']}: 字幕行 {t}–{round(t+dur,1)} 超出本镜时间窗 "
            f"{round(start,1)}–{round(end,1)}")
        out.append({
            "type": "对白", "char_id": a["char_id"], "text": a["text"],
            "in_sec": t, "out_sec": round(t + dur, 1),
            "shot_id": a["shot_id"],
            "note": f"时码由 D15 U02 {D15_VERSION} 配音锚点驱动：in_sec ＝ 配音 at_sec，"
                    f"out_sec ＝ 配音 at_sec＋dur_sec（{v['line_ref']}）；"
                    f"本行与配音逐条一致，字幕不早于起音、不早于收音。",
            # 内部字段：供 subtitle_sync_audit 逐条配对用，落盘前剥离
            "_vo": {"line_ref": v["line_ref"], "at_sec": t, "dur_sec": dur,
                    "char_id": v["char_id"], "shot_id": v["shot_id"]},
        })
    # 同镜内字幕行不得重叠（逐镜、逐行顺推）
    for sid in sorted({r["shot_id"] for r in out}):
        rows = [r for r in out if r["shot_id"] == sid]
        for i in range(1, len(rows)):
            chk(rows[i]["in_sec"] >= rows[i - 1]["out_sec"] - 1e-9,
                f"ep{ep} 镜{sid}: 对白字幕行重叠（第 {i} 行 in {rows[i]['in_sec']} "
                f"< 上一行 out {rows[i-1]['out_sec']}）")
    return out


def next_hook_source(ep):
    """返回 (下一集集号, 钩子原文, 出处标签)。

    ep009–ep015：下一集在 U02 内 → 取 D06 下一集的 hook_in。
    ep016：下一集是 U03 首集 ep017，U02 内无 ep017 的 D06
            → 取 project.json `units[U03].first_hook`（SSOT 级单元钩子链）。
    """
    nxt = ep + 1
    if nxt <= 16:
        e = next(x for x in D06["episodes"] if x["ep"] == nxt)
        return nxt, e["hook_in"], f"U02 D06 ep{nxt:03d} hook_in"
    u3 = next(u for u in PROJ["units"] if u["id"] == "U03")
    return nxt, u3["first_hook"], "project.json units[U03].first_hook"


def assert_manifest_guard():
    """Q56 ①③：断言清单与**实际断言点数**机械一致 —— 对不上即中止。

    计数刻意避开在源码里出现连续的断言函数名（用拼接），否则本函数自己会被数进去。
    """
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    token = "ch" + "k("
    n_call = src.count(token) - 1      # 减去函数定义那一处
    n_decl = len(ASSERT_MANIFEST)
    if n_call != n_decl:
        print(f"❌ 中止：断言清单 {n_decl} 条 ≠ 实际断言点 {n_call} 处 —— "
              "Q56：新增/删除断言必须同步更新 ASSERT_MANIFEST（禁「跑到什么算什么」）。")
        sys.exit(2)
    return n_decl, n_call


def main():
    assert_manifest_guard()
    d07map = {e["ep"]: e for e in D07["episodes"]}
    d11map = {e["ep"]: e for e in D11["episodes"]}
    d06map = {e["ep"]: e for e in D06["episodes"]}
    d09count = {}
    for l in D09["lines"]:
        d09count[l["ep"]] = d09count.get(l["ep"], 0) + 1

    episodes = []
    total_counted = 0
    total_cuts = 0
    for ep in sorted(d11map):
        d07 = d07map[ep]
        d11 = d11map[ep]
        segs = d07["quad_segments"]
        bounds = [(s["start_sec"], s["end_sec"]) for s in segs]
        chk(len(segs) == 4, f"ep{ep}: D07 段数 ≠ 4")
        chk(all(s.get("mode") == "串行" for s in segs),
            f"ep{ep}: 存在并行段 → 1 镜/段假设不成立，切点方案须重算")
        chk(len(d11["shots"]) == 4, f"ep{ep}: D11 镜数 ≠ 4")

        cuts = []
        transitions = []
        for i in range(3):
            at = bounds[i][1]
            is_dis = (ep in DISSOLVE_AT and DISSOLVE_AT[ep] == i + 1)
            tech = "叠化" if is_dis else "硬切"
            counted = not is_dis
            basis = CUT_BASIS[ep][i]
            if is_dis:
                basis = basis + "（" + DISSOLVE_BASIS[ep] + "）"
            cuts.append({
                "index": i + 1,
                "at_sec": at,
                "from_shot": i + 1,
                "to_shot": i + 2,
                "from_segment": i + 1,
                "to_segment": i + 2,
                "technique": tech,
                "dissolve_sec": 0.5 if is_dis else 0,
                "counted_in_d17_cut_count": counted,
                "basis": basis,
            })
            al_idx, al_lead, al_text = AUDIO_LEAD.get(ep, (None, None, None))
            sh = "无声音预铺位，直接随画面切换"
            if al_idx == i + 1:
                sh = al_text
            transitions.append({
                "type": "段间转场",
                "index": i + 1,
                "at_sec": at,
                "from_shot": i + 1,
                "to_shot": i + 2,
                "technique": tech,
                "dissolve_sec": 0.5 if is_dis else 0,
                "sound_handling": sh,
                "cut_basis": basis,
                "counted_in_d17_cut_count": counted,
            })
        total_cuts += len(cuts)
        total_counted += sum(1 for c in cuts if c["counted_in_d17_cut_count"])

        al_idx, al_lead, al_text = AUDIO_LEAD.get(ep, (None, None, None))
        al_summary = al_text if al_text else "本集无声音预铺位：三个段间边界均直接随画面切换。"
        overall = {
            "type": "总体口径",
            "overall": (f"本集 3 个段间边界："
                        f"{'、'.join(c['technique'] + '（' + ('计入 D17' if c['counted_in_d17_cut_count'] else '不计入 D17') + '）' for c in cuts)}；"
                        f"无淡入淡出、无闪白与故障效果。"),
            "boundary_count": 3,
            "hard_cut_count": sum(1 for c in cuts if c["technique"] == "硬切"),
            "dissolve_count": sum(1 for c in cuts if c["technique"] == "叠化"),
            "d17_counted_cut_count": sum(1 for c in cuts if c["counted_in_d17_cut_count"]),
            "d17_count_basis": "D17 totals「每集 2–3 个切点」，U02 单元预算 D16_切点＝20；"
                               "本集 3 个段间边界中计入 D17 的为 "
                               f"{sum(1 for c in cuts if c['counted_in_d17_cut_count'])} 个"
                               f"（叠化 {sum(1 for c in cuts if c['technique'] == '叠化')} 个按 D16 既有口径不计入）。",
            "dissolves": [{"index": c["index"], "at_sec": c["at_sec"], "dissolve_sec": c["dissolve_sec"],
                           "basis": c["basis"]} for c in cuts if c["technique"] == "叠化"],
            "audio_lead": al_summary,
            "banned": "禁闪白、频闪、故障转场；禁任何暗示异化或疯狂的视觉特效转场。",
            "segment_alignment": "／".join(f"{a:.1f}–{b:.1f}" for a, b in bounds)
                                 + f"，与 D07 ep{ep:03d} quad_segments 逐段对齐，合计 {bounds[-1][1]:.1f}s。",
        }
        transitions = [overall] + transitions

        # ── 字幕行 ──
        lines = []
        seq = 1
        for hl in HEAD_LINES:
            r = dict(hl); r["seq"] = seq; seq += 1
            lines.append(r)
        # 面板文字行（按镜号）
        drows = dialogue_rows(ep)
        panel = PANEL_LINES.get(ep, [])
        shots_start = []
        c = 0.0
        for s in d11["shots"]:
            shots_start.append(c); c += s["duration_sec"]
        merged = []
        # ── 同镜内字幕行顺排消解：**对白优先，面板文字行顺延** ──
        #   面板行的镜内偏移是「最早可显示位置（锚点）」；实际时码由本步排定，
        #   保证同镜内任意两行零重叠（U01 D16 v1.7 同口径：同镜并存各行顺排不重叠）。
        occupied = {}          # shot_id → [(in, out)]
        for r in drows:
            occupied.setdefault(r["shot_id"], []).append((r["in_sec"], r["out_sec"]))
        for (sid, text, off, dur) in sorted(panel, key=lambda x: (x[0], x[1])):
            anchor = shots_start[sid - 1] + off
            t = anchor
            for _ in range(24):
                conflict_end = None
                for (a, b) in occupied.get(sid, []):
                    if t < b - 1e-9 and t + dur > a + 1e-9:
                        conflict_end = b if conflict_end is None else max(conflict_end, b)
                if conflict_end is None:
                    break
                t = round(conflict_end + 0.3, 1)
            sh_start = shots_start[sid - 1]
            sh_end = sh_start + d11["shots"][sid - 1]["duration_sec"]
            chk(sh_start - 1e-6 <= t and t + dur <= sh_end + 1e-6,
                f"ep{ep} 镜{sid}: 面板字幕行顺延后越出本镜时间窗"
                f"（{round(t,1)}–{round(t+dur,1)}，镜 {sh_start}–{sh_end}）")
            occupied.setdefault(sid, []).append((t, t + dur))
            note = None
            if abs(t - anchor) > 1e-6:
                note = (f"锚点：镜内 {off}s 起可显示；因与同镜字幕行重叠，"
                        f"实际时码顺延至 {round(t,1)}s 起（对白优先，面板让位）。")
            merged.append((t, t + dur, "面板文字", None, text, sid, note, None))
        for r in drows:
            merged.append((r["in_sec"], r["out_sec"], "对白", r["char_id"], r["text"],
                           r["shot_id"], r.get("note"), r.get("_vo")))
        merged.sort(key=lambda x: (x[0], x[2] != "对白"))
        vo_by_seq = {}
        for (ins, outs, typ, cid, text, sid, mnote, vometa) in merged:
            row = {"seq": seq, "type": typ, "text": text,
                   "in_sec": round(ins, 1), "out_sec": round(outs, 1)}
            if cid:
                row["char_id"] = cid
            row["shot_id"] = sid
            if mnote:
                row["note"] = mnote
            lines.append(row)
            if vometa:
                vo_by_seq[seq] = vometa
            seq += 1
        bl = dict(BADGE_LINE); bl["seq"] = seq; seq += 1
        lines.append(bl)
        tl = dict(TAIL_LINE); tl["seq"] = seq; seq += 1
        lines.append(tl)

        # 字幕行断言
        for r in lines:
            dwell = round(r["out_sec"] - r["in_sec"], 1)
            chk(dwell >= 1.2 - 1e-9, f"ep{ep} seq{r['seq']}: 停留 {dwell}s < 1.2s")
            chk(r["in_sec"] >= 0 and r["out_sec"] <= 45.0 + 1e-6,
                f"ep{ep} seq{r['seq']}: 字幕行越出 0~45s")
            if "shot_id" in r:
                sid = r["shot_id"]
                s = d11["shots"][sid - 1]
                st = shots_start[sid - 1]
                chk(r["in_sec"] >= st - 1e-6 and r["out_sec"] <= st + s["duration_sec"] + 1e-6,
                    f"ep{ep} seq{r['seq']}: 字幕行越出所在镜时间窗")
        # 字幕行不跨切点 —— **只判台词字幕行（对白／面板文字）**。
        #   角标为全集常驻版式层（0~45s，跨全部切点是设计使然）、片头片尾为整集版式层，
        #   二者与镜切换无关，不参与该判定（与 U01 D16 v1.7 同口径：角标行同样跨全集切点）。
        cut_at = [c["at_sec"] for c in cuts]
        for r in lines:
            if r["type"] not in ("对白", "面板文字"):
                continue
            for ca in cut_at:
                chk(not (r["in_sec"] < ca < r["out_sec"]),
                    f"ep{ep} seq{r['seq']}: 字幕行跨切点 {ca}")
        # 正文行不得伸进**片尾标题卡带**（43.0~45.0s；与对白同在底部字幕区 → 同刻即真实视觉冲突）。
        #   ← U01-R19 已立过「片尾标题卡单独检查」这条关；**本岗 U02 构建脚本首版漏了它**，
        #     致 ep10 seq9（42.5~43.9）／ep15 seq10（42.3~43.7）两条面板文字行伸进片尾带。
        #   区间口径沿用左闭右开：out_sec ＝ 片尾 in_sec 视为相接，不算重叠。
        tail_in = TAIL_LINE["in_sec"]
        for r in lines:
            if r["type"] not in ("对白", "面板文字"):
                continue
            chk(r["out_sec"] <= tail_in + 1e-9,
                f"ep{ep} seq{r['seq']}: 正文行 out_sec {r['out_sec']} 伸进片尾标题卡带"
                f"（片尾 in {tail_in}，同在底部字幕区＝真实视觉冲突）")

        # 同镜内任意两条字幕行不得重叠（对白／面板文字混排后的全局判据；
        #   U01 D16 v1.7 同镜并存各行亦为顺排零重叠）
        by_shot = {}
        for r in lines:
            if "shot_id" not in r:
                continue
            by_shot.setdefault(r["shot_id"], []).append(r)
        for sid in sorted(by_shot):
            rs = sorted(by_shot[sid], key=lambda x: x["in_sec"])
            for i in range(1, len(rs)):
                chk(rs[i]["in_sec"] >= rs[i - 1]["out_sec"] - 1e-9,
                    f"ep{ep} 镜{sid}: 字幕行重叠（seq{rs[i-1]['seq']}({rs[i-1]['type']}) "
                    f"out {rs[i-1]['out_sec']} → seq{rs[i]['seq']}({rs[i]['type']}) in {rs[i]['in_sec']}）")

        ss = dict(SUBTITLE_STYLE_BASE)
        ss["lines"] = lines
        audit = build_sync_audit(ep, lines, vo_by_seq, shots_start, d11, cuts)
        # S22 口径要点的行（标称 1.2s＝合规下沿）—— 逐条点名，内容＋时码为准
        floor_rows = audit["dwell_floor_rows"]
        if floor_rows:
            floor_txt = "；".join(
                f"seq{r['seq']}「{r['text']}」{r['in_sec']}~{r['out_sec']}"
                f"（标称 {r['nominal_dwell_sec']}s，实算 {r['float_dwell_sec']!r}）"
                for r in floor_rows)
        else:
            floor_txt = "（本集无标称 1.2s 的行）"
        ss["subtitle_sync_audit"] = audit
        # 口径文本逐集生成（余量数值必须带口径名，D18 Q46）
        ss["dwell_calc_convention"] = (
            "停留按标称时码计（in_sec/out_sec 均为 0.1s 精度时间码），标称 ≥1.2s 即合规；"
            "二进制浮点表示尾差（如 37.4−36.2 实算 1.1999999999999957）不是时码精度问题，"
            "不构成不合格依据，判定基准一律取 0.1s 标称网格。"
            f"本集对白字幕行与 D15 U02 {D15_VERSION} 配音**逐条对应**（受检 "
            f"{audit['synced_row_count']} 条）：in_sec ＝ 配音 at_sec，out_sec ＝ 配音 at_sec＋dur_sec，"
            "逐条严格相等，本表不含任何按字数估算的排布稿时码。"
            f"面板文字行 {audit['no_vo_anchor_rows']} 条无配音锚点"
            "（**面板本体弹出的提示/通报文字**进字幕、声音层不承载；"
            "**读数栏数值**留画面不进字幕层，各集清单见 readout_in_frame），"
            "其时码按「镜内锚点＋同镜顺排消解」排定，已在本表 note 中登记顺延原因。"
            "【本表口径 · 2026-10-23 U02 v1.1】D15 U02 已落盘，故本表**取消**首版"
            "「受检 0 条／未与配音核对」的保留声明，改为按 D15 锚点逐条核对并登记实测值；"
            "余量三口径（**镜尾余量／起音间隙／镜首余量**）的最小值见 "
            "`subtitle_sync_audit.margin_min_by_caliber`，三个数测的是不同的东西，不可互相替代。"
            "【本表口径 · 2026-10-23 U02 v1.2】面板文字口径收口：读数栏数值不再进字幕层，"
            "正文行 out_sec 一律不得越过片尾标题卡 in_sec（43.0s）。"
            "【本表口径 · 2026-10-23 U02 v1.3 · 落地企划合规 S22】停留**按 0.1s 标称网格判定，"
            "不做浮点位相等 / 严格比较**；**标称 1.2s 为合规下沿**（等于下沿即合规，"
            "不因二进制浮点尾差判不合格）。"
            f"本集标称 1.2s 的行：{floor_txt}；"
            f"本集存在浮点表示尾差的对白行 {audit['float_tail_row_count']} 条，一律以标称网格判定。"
        )
        ss["sync_rule"] = (
            "字幕不得早于配音起音，出点不早于配音收音；"
            "区间口径按**左闭右开**判定（out_sec 等于下一条 in_sec 视为相接，不算重叠）；"
            "重叠检查须覆盖**全部正文行**（对白／字幕／面板文字），"
            "**片尾标题卡单独检查**（其位置与对白同在底部字幕带，与对白同刻即构成真实视觉冲突）——"
            "本表正文行的 out_sec 一律不得越过片尾标题卡的 in_sec（43.0s）。"
        )
        ss["panel_subtitle_rule"] = (
            "面板文字分两类处置：**面板本体弹出的提示/通报文字**进字幕层"
            "（如 ep11「新手福利期结束」、ep16 视野正中面板的两行）；"
            "**读数栏的数值读数**留画面、不进字幕层（各集清单见 readout_in_frame；"
            "U01 ep4 镜4「面板一角读数栏…归一度 0.5%」为同类先例，同样未进字幕层）。"
            "理由：读数栏已在画面内可读，再叠一条底部字幕只会与对白／片尾标题卡抢同一条字幕带。"
        )
        ss["readout_in_frame"] = [
            {"shot_id": sid, "text": txt,
             "basis": "D11 原文为「视野一角读数栏／面板读数栏显示同屏中文「…」」——"
                      "属读数栏数值，已在画面内可读，不进字幕层。"}
            for (sid, txt) in READOUT_IN_FRAME.get(ep, [])
        ]
        # ── 序号迁移对照（v1.2 移除读数栏面板行 → 排在之后的正文行 seq 前移；存留面板行时码亦变） ──
        legacy_map = legacy_seq_map(ep, drows, shots_start, d11)
        legacy_panel_pos = legacy_layout_rows(ep, drows, shots_start)
        migration = []
        for l in lines:
            if l["type"] not in ("对白", "面板文字"):
                continue
            old = legacy_map.get(l["text"])
            if old is None:
                continue
            old_in, old_out = (legacy_panel_pos.get(l["text"], (None, None))
                               if l["type"] == "面板文字" else (l["in_sec"], l["out_sec"]))
            changed = (old["seq"] != l["seq"]) or (old_in is not None and abs(old_in - l["in_sec"]) > 1e-9)
            if not changed:
                continue
            migration.append({
                "text": l["text"],
                "type": l["type"],
                "seq_before_v1_2": old["seq"],
                "seq_now": l["seq"],
                "old_in_sec": old_in,
                "old_out_sec": old_out,
                "now_in_sec": l["in_sec"],
                "now_out_sec": l["out_sec"],
            })
        if migration:
            ss["subtitle_sync_audit"]["seq_number_migration"] = {
                "cause": "v1.2 面板口径收口：读数栏数值退出字幕层 → 各集排在这些行之后的正文行 seq 前移；"
                         "且存留面板行的时码因「同镜顺排消解」的占用集变化而改变。",
                "rows": migration,
                "note": "定位一律以「内容＋时码」为准，seq 只是当前盘上值。"
                        "企划合规 §六十七 S22 点名的 ep9「……军阀。」旧称 seq10，现为 seq9。",
            }
        ss["subtitle_sync_audit"]["sync_records"] = [
            {
                "date": "2026-10-23",
                "event": "U02 D16 v1.1 → v1.3",
                "basis": "企划合规第六波派单（S21 预铺明文 ＋ S22 停留口径）＋ 本岗自查发现的片尾带冲突",
                "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
                "changes": [
                    "v1.1：字幕行时码由「D09 字数估算」改为 D15 配音锚点驱动"
                    "（in_sec ＝ at_sec、out_sec ＝ at_sec＋dur_sec）；subtitle_sync_audit 8 集回填；"
                    "sync_rule 补区间口径；audio_lead 补「声音预铺位」明文",
                    "v1.2：面板口径收口 —— 读数栏数值退出字幕层（改留画面并登记 readout_in_frame），"
                    "面板字幕行 11→3；消除片尾带冲突 2 条",
                    "v1.3：落地 S22 停留口径（标称网格判定、标称 1.2s 为合规下沿、下沿行逐条点名）；"
                    "补记「实际音频轴未测（受检 0 条）」声明",
                ],
                "applied_by": "分镜导演",
            }
        ]

        # ── 下一集钩子：引文逐字取自上游钩子原文（断言校验，杜绝改述失配） ──
        hook_quote, hook_bridge = NEXT_HOOK[ep]
        nxt_ep, hook_src, hook_src_label = next_hook_source(ep)
        chk(hook_quote in hook_src,
            f"ep{ep}: next_ep_hook 引文「{hook_quote}」不在 {hook_src_label} 原文内")
        chk(hook_src.startswith(hook_quote),
            f"ep{ep}: next_ep_hook 引文非 {hook_src_label} 的起始钩子句｜原文: {hook_src}")
        # 钩子链一致性：下一集 hook_in 必须等于本集 hook_out
        if nxt_ep <= 16:
            prev_out = next(x for x in D06["episodes"] if x["ep"] == ep)["hook_out"]
            chk(prev_out == hook_src,
                f"ep{ep}: 钩子链断裂 —— 本集 hook_out ≠ 下一集 hook_in")
        else:
            u2 = next(u for u in PROJ["units"] if u["id"] == "U02")
            d06_out = next(x for x in D06["episodes"] if x["ep"] == ep)["hook_out"]
            chk(u2["last_hook"] == hook_src == d06_out,
                f"ep{ep}: 跨单元钩子链断裂 —— U02 last_hook／U03 first_hook／D06 hook_out 三者不一致")
        next_hook_str = f"ep{nxt_ep:03d} 承接「{hook_quote}」：{hook_bridge}"

        title_card = {
            "head": {
                "in_sec": 0, "out_sec": 2,
                "form": "文字层叠加在镜1 的起幅段，不设独立黑场、不做片头动画——"
                        "独立片头会吃掉 0~3s 的钩子预算（D10 §5.2）",
                "layout": "画面上部带区（画面高度 6%~20%）四行：剧名／编号位／署名／AI 标识",
                "fade": "文字层淡入 0.2s（0.0~0.2s）、淡出 0.3s（1.7~2.0s）；画面本身无淡入淡出",
                "first_frame": FIRST_FRAME[ep],
            },
            "tail": {
                "in_sec": 43, "out_sec": 45,
                "form": TAIL_FORM[ep],
                "audio": "43.0~45.0s 音乐收尾，环境声保留至 45.0s，不做绝对静音",
                "next_ep_hook": next_hook_str,
            },
            "compliance": {
                "ai_disclosure": "片头第 4 行「本片由人工智能生成」＋全片右下角常驻角标「AI 生成」，"
                                 "二者并列呈现（D03 §6.5／R09）",
                "title_items_checklist": "剧名／编号位／署名／AI 标识 四项齐备",
                "pending_fill": "剧名定稿（D03 §7.1）、节目编号（平台出具，不可自编）、编剧与导演署名",
            },
        }

        paywall_point = {
            "status": "待用户确认",
            "conclusion": "本集不自行指定付费卡点集数与位置；商业模式与卡点集数未获用户确认前，"
                          "本集不落任何付费相关元素。",
            "basis": "D01 commercial.confirmed_by_user=false；gaps G-02（商业模式）、"
                     "G-03（付费卡点集数与位置）、G-11（卡点与发行平台侧算法合规对齐）",
            "zero_elements": ["无卡点提示条",
                              "无「解锁」「付费」「VIP」「充值」「开通」等字样（画面与声音均无）",
                              "无「下集付费解锁」引导",
                              "无「试看结束」「会员抢先看」角标",
                              "无充值按钮、礼物入口、价格、优惠文案"],
            "revision_condition": "待用户确认商业模式与卡点集数后，由本岗在本表 revisions 中补写卡点集数与位置，"
                                  "不在本轮预支任何卡点铺垫。",
        }

        episodes.append({
            "ep": ep,
            "cuts": cuts,
            "transitions": transitions,
            "subtitle_style": ss,
            "title_card": title_card,
            "paywall_point": paywall_point,
        })

    doc = {"doc_id": "D16", "unit": "U02", "version": VERSION, "status": "in_review",
           "episodes": episodes}

    # ── 预算断言：D17 对 U02 的 D16_切点 = 20 ──
    D17 = json.load(open(P("shared", "D17.json"), encoding="utf-8"))
    u02 = next(u for u in D17["units"] if u["unit"] == "U02")
    budget = u02["workload"]["D16_切点"]
    chk(total_counted <= budget,
        f"计入 D17 的切点 {total_counted} > D17 对 U02 的预算 {budget}（S9：须先调 D17 再改 D16）")
    chk(total_cuts == 24, f"段间切点总数 {total_cuts} ≠ 24（8 集 × 3 个段间边界）")
    # 台词条数核对：字幕行里的对白条数必须等于 D09 本集台词条数
    for e in episodes:
        ep = e["ep"]
        n_vo = sum(1 for r in e["subtitle_style"]["lines"] if r["type"] == "对白")
        chk(n_vo == d09count.get(ep, 0),
            f"ep{ep}: 对白字幕行 {n_vo} 条 ≠ D09 台词 {d09count.get(ep, 0)} 条")
    # 每集切点数落在 D17 的「每集 2–3 个切点」
    for e in episodes:
        c = sum(1 for x in e["cuts"] if x["counted_in_d17_cut_count"])
        chk(2 <= c <= 3, f"ep{e['ep']}: 计入 D17 的切点 {c} 不在「每集 2–3 个」区间")

    # ── 漂移守卫（A36 · 2026-10-23 分镜导演立）────────────────────────────
    #   产物 ↔ 盘上**只允许**下列已声明差异；任何未声明差异即中止写盘
    #   （防绕过构建器手改交付物、或脚本与盘上悄悄分叉）。
    #   ⚠️ 本守卫必须位于 `if errors:` **之前** —— 否则它的断言产生的 error
    #      不会触发中止，断言形同虚设（第一版就踩了这个坑，靠结构化 diff 抓到 52 处漏声明差异）。
    #      ⚠️ 另注：本文件里**不得在注释/字符串中写字面断言函数名**（守卫按 token 计数，见下）。
    DECLARED_VERSION_CHANGE = ("v1.4", "v1.5")
    DECLARED_INSERTS = [
        (("episodes", i, "subtitle_style", "subtitle_sync_audit"), "audit_field_scope")
        for i in range(8)
    ]
    #   随上游 D15 U02 升版（v1.0→v1.1）而带的**版本戳同步**：逐条落在
    #   sync_basis／verified_against_d15／lines[].note／dwell_calc_convention。
    #   写成**精确 token 替换**（不写裸 "v1.0"→"v1.1"：裸替换会误伤 verified_note 里
    #   「本轮 D16 升级 v1.0→v1.1 的实质变更」这类**历史留痕陈述**，按 S11 不得改写）。
    #   ⚠️ 2026-10-23 07:45 声音设计把 D15 U02 升到 **v1.2** → 本表版本戳随之过期
    #      （`build_D16_U02.py` 第 50 行 D15_VERSION 是**动态**取 D15.get("version")，
    #      故产物自动戳 v1.2、盘上仍为 v1.1 → A36 漂移守卫如实拦截，--check exit 1）。
    #      本轮追加 v1.1→v1.2 一对 token；**保留** v1.0→v1.1 那对（链式幂等，防倒退）。
    #      实测：盘上 52 处版本戳全为**当前态引用**（lines[].note 28 ＋ sync_basis 8
    #      ＋ dwell_calc_convention 8 ＋ verified_against_d15 8），**无一处落在
    #      「升版／本轮／留痕／历史」附近** → 该 token 替换不误伤 S11 历史留痕。
    #      ⚠️ 本轮**只同步版本戳**：D15 v1.2 未改任何配音锚点 —— 由两道独立机制证明：
    #         ① 本守卫的判定是**整份文档相等性**（exp != doc 才判失败，8 条截断只影响报错文案）
    #            → --check 放行即等于穷尽证明「除版本戳与版本号外零差异」；
    #         ② reconcile_D15_D16_timing.mjs --unit U02 判据 D1「字幕 out_sec == 配音
    #            (at_sec+dur_sec)」对现盘 D15 v1.2 逐条核对 0 条不符。
    DECLARED_TEXT_REPLACES = [
        ("D15 U02 v1.0", "D15 U02 v1.1"),
        ("D15 U02 v1.1", "D15 U02 v1.2"),
        ("v1.0（D15 U02 落盘后现算复核", "v1.1（D15 U02 落盘后现算复核"),
        ("v1.1（D15 U02 落盘后现算复核", "v1.2（D15 U02 落盘后现算复核"),
    ]

    def _getp(d, path):
        cur = d
        for p in path:
            cur = cur[p]
        return cur

    def _diff(a, b, path=""):
        if type(a) is not type(b):
            return [f"{path}: 类型不同"]
        if isinstance(a, dict):
            out = []
            for k in sorted(set(a) | set(b)):
                if k not in a:
                    out.append(f"{path}.{k}: 仅在产物")
                elif k not in b:
                    out.append(f"{path}.{k}: 仅在盘上")
                else:
                    out += _diff(a[k], b[k], f"{path}.{k}")
                if len(out) > 8:
                    return out
            return out
        if isinstance(a, list):
            out = []
            for i in range(max(len(a), len(b))):
                if i >= len(a):
                    out.append(f"{path}[{i}]: 仅在盘上")
                elif i >= len(b):
                    out.append(f"{path}[{i}]: 仅在产物")
                else:
                    out += _diff(a[i], b[i], f"{path}[{i}]")
                if len(out) > 8:
                    return out
            return out
        return [] if a == b else [f"{path}: 产物={a!r} 盘上={b!r}"]

    def _apply_text_repl(obj):
        if isinstance(obj, str):
            for _o, _n in DECLARED_TEXT_REPLACES:
                obj = obj.replace(_o, _n)
            return obj
        if isinstance(obj, dict):
            return {k: _apply_text_repl(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_apply_text_repl(v) for v in obj]
        return obj

    _d16_disk = P("units", "U02", "D16.json")
    drift_msgs = []
    drift_ok = True
    if os.path.exists(_d16_disk):
        disk_doc = json.load(open(_d16_disk, encoding="utf-8"))
        exp = _apply_text_repl(json.loads(json.dumps(disk_doc)))
        _old_v, _new_v = DECLARED_VERSION_CHANGE
        _disk_v = exp.get("version")
        if _disk_v == _new_v:
            pass                                  # 已应用（幂等重跑）
        elif _disk_v == _old_v:
            exp["version"] = _new_v
        elif _vkey(_disk_v) > _vkey(VERSION):
            # 盘上版本**高于**本脚本 → 这是「版本回退」场景，**不是内容漂移**：
            # 交由 Q64 版本守卫判定（它带 --force 逃生口），本守卫不抢它的活。
            #   ⚠️ 本守卫**只管内容差异**：内容层的未声明差异一律拒绝，--force 也不放行
            #      （否则等于允许静默吞掉他人手改 —— 那才是本守卫要防的事）。
            drift_msgs.append(f"盘上版本 {_disk_v} 高于脚本版本 {VERSION} → 版本回退场景，交 Q64 版本守卫判定")
            exp["version"] = doc.get("version")   # 版本差不计入内容漂移
        else:
            drift_msgs.append(f"版本：盘上 {_disk_v} 既非 {_old_v} 也非 {_new_v} —— 盘上可能已被他人改动")
            drift_ok = False
        for _path, _key in DECLARED_INSERTS:
            try:
                _tgt = _getp(exp, _path)
            except (KeyError, IndexError, TypeError):
                drift_msgs.append(f"声明插入路径不存在：{'.'.join(map(str, _path))}")
                drift_ok = False
                continue
            _want = _getp(doc, _path)[_key]
            if _key in _tgt:
                if _tgt[_key] != _want:
                    drift_msgs.append(f"声明新增键 {'.'.join(map(str, _path))}.{_key} 盘上值与产物不同 —— 盘上可能已被他人改动")
                    drift_ok = False
            else:
                _tgt[_key] = _want
        if drift_ok and exp != doc:
            drift_ok = False
            for d in _diff(doc, exp)[:8]:
                drift_msgs.append("未声明差异 → " + d)
    else:
        drift_msgs.append("盘上交付物不存在（首建，无可比对基线）")
    chk(drift_ok, "产物↔盘上存在未声明差异（A36 漂移守卫）："
        + ("；".join(drift_msgs) if drift_msgs else "结构不符"))

    if errors:
        print(f"\n❌ 中止（{len(errors)} 项断言未过，不写盘）：")
        for e in errors:
            print("   ·", e)
        sys.exit(1)

    print("✅ 全部断言通过：")
    print(f"   · 8 集 × 3 个段间切点 = {total_cuts} 条；其中叠化 {total_cuts - total_counted} 条（不计入 D17）")
    print(f"   · 计入 D17 的切点 = {total_counted}，D17 对 U02 的预算 = {budget} → 满额、零余量（未动 D17，S9 合规）")
    print(f"   · 对白字幕行逐集条数与 D09 台词一一对应（合计 {sum(d09count.values())} 条）")
    print(f"   · 字幕行：停留 ≥1.2s、不越本镜时间窗、不跨切点、同镜零重叠、限 0~45s")
    total_synced = sum(e["subtitle_style"]["subtitle_sync_audit"]["synced_row_count"] for e in episodes)
    print(f"   · D15 U02 {D15_VERSION} 锚点驱动：对白字幕行 {total_synced} 条逐条核对"
          f"（in_sec ＝ at_sec、out_sec ＝ at_sec＋dur_sec），0 条不符")
    print(f"   · 余量三口径最小值（带口径名）已写入各集 subtitle_sync_audit.margin_min_by_caliber")
    print(f"   · Q56 断言清单 {len(ASSERT_MANIFEST)} 条 —— 机械守卫已核对「清单条数 == 实际断言点数」")

    if "--check" in sys.argv:
        print("（--check：只校验，不写盘）")
        return

    out = P("units", "U02", "D16.json")
    # ── 版本守卫（Q64 · 2026-10-23 企划合规立规；范式取自台本编剧 build_D08.py）──
    #   判据：磁盘产物的 version **高于**本脚本要写的 version → 拒绝覆盖、中止、不写盘。
    #   正常升版（磁盘 v1.3 → 脚本 v1.4）与幂等重跑（版本相同）**必须放行**（不得做成「一律拒绝」）。
    #   需要故意回退时用 --force 显式放行（人工确认过再动）。
    #   ⚠️ _vkey 已提到**模块级** —— 首版把它定义在调用点之后，NameError 恰被上游漂移守卫的
    #      exit 2 挡住，本守卫实际**从未执行过**；删除漂移守卫副本后才暴露。
    #   ⚠️ 与 A36 漂移守卫的分工：内容差异 → A36 一律拒绝（--force 也不放行）；
    #      版本回退 → 本守卫判定，带 --force 逃生口。两守卫不再互相遮蔽。
    if os.path.exists(out):
        try:
            cur = json.load(open(out, encoding="utf-8"))
            cur_v = cur.get("version")
            if _vkey(cur_v) > _vkey(VERSION) and "--force" not in sys.argv:
                print(f"❌ 版本守卫：磁盘 {os.path.relpath(out, ROOT)} 已是 **{cur_v}**，"
                      f"高于本脚本要写的 **{VERSION}** → 拒绝覆盖，未写盘。")
                print("   可能原因：另一个写者已用更新版本落盘，或本脚本用的是旧内容源。")
                print("   确认确需回退时，加 --force 显式放行。")
                sys.exit(1)
        except json.JSONDecodeError:
            pass  # 磁盘文件损坏 → 照常覆盖，交由自检与 validate 兜底

    # A36 漂移守卫唯一实例在 `if errors:` 之前（上方已 chk 并中止）；
    # 此处不得再放第二份副本 —— 副本能通过 chk 但不会触发中止，且不套文本替换会误报未声明差异。
    if os.path.exists(out):
        # 本岗备份纪律（U02-R10）：**不在 units/ 交付目录内写备份**，统一落 reports/_bak_*。
        bak_dir = P("reports", "_bak_U02_D11_D16_" + time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        bak = os.path.join(bak_dir, "D16.json")
        shutil.copy2(out, bak)
        print(f"   · 备份旧文件 → {os.path.relpath(bak, ROOT)}")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"✅ 落盘：units/U02/D16.json  {VERSION}  {os.path.getsize(out)} B")


if __name__ == "__main__":
    main()
