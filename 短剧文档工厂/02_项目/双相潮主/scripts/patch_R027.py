#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-027 一次性补丁（2026-10-23 台本编剧岗）。

做四件事，全部带**命中数断言**（对不上即中止，不写盘）—— OPS-05 纪律：
  ① build_D08_U01.py：ep8 compliance_notes[4] 由旧 P1/C4 口径同步为 R-024 口径
     （Chief 代执行时改了 JSON 漏了脚本 → 脚本一跑即回退，Q27 教训）；
  ② build_D08_U01.py：脚本自检面与机器闸对齐（豁免 term_scan_exempt.D08 登记的留痕面）
     + body 字段白名单放行 shot_intent + 新增 shot_intent 护栏自检；
  ③ build_D08_U01.py：回填每集 ≥2 条 shot_intent（镜头意图层），版本 v1.6 → v1.7；
  ④ build_D09_U01.py：SUBTEXT(8,4) 与新句自洽微调，版本 v1.3 → v1.4。

跑完本脚本即可删除；build_*.py 仍是唯一 SSOT。
"""
import json, os, sys

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
D08S = f"{ROOT}/scripts/build_D08_U01.py"
D09S = f"{ROOT}/scripts/build_D09_U01.py"

# ─────────────────────────────────────────────────────────────
# ① ② ③ build_D08_U01.py
# ─────────────────────────────────────────────────────────────
src = open(D08S, encoding="utf-8").read()
orig = src
edits = []          # (说明, 旧串, 新串, 期望命中数)


def E(tag, old, new, n=1):
    edits.append((tag, old, new, n))


# ── ① ep8 compliance_notes[4]：旧 P1/C4 口径 → R-024 口径 ──
# 新文案直接从当前 D08.json 取出，避免手抄走样。
_cur = json.load(open(f"{ROOT}/units/U01/D08.json", encoding="utf-8"))
_ep8_notes = _cur["episodes"][7]["compliance_notes"]
_r024 = None
for n in _ep8_notes:
    if n.startswith("R-024 结掉"):
        _r024 = n
if _r024 is None:
    sys.exit("❌ 当前 D08.json 找不到 R-024 口径留痕，中止")
# 旧口径（C4）在脚本里的原文
_old_c4 = ('        "P1 结掉（总控 C4 裁决）：ep008「阎王」为 D04 登记的陆沉口头禅原句，D03 R01 禁用清单与 D05 '
           '术语表均未收录，**保留不改**；附加约束——D11/D12/D16 不得将其做成画面可见文字或字幕板眼，D10 不得设信仰'
           '符号化视觉锚点。本集不出现信仰符号化视觉。",')
E("ep8 note[4] C4→R-024", _old_c4, '        ' + json.dumps(_r024, ensure_ascii=False) + ',')

# ── ② 脚本自检面与机器闸对齐：豁免留痕面 ──
E("自检·豁免留痕面",
  """    for i, note in enumerate(ep.get("compliance_notes", [])):
        for w in BANS:
            if w and w in note:
                errs.append(f"ep{ep['ep']} compliance_notes[{i}] 命中禁用写法「{w}」:: {note[:70]}")""",
  """    # compliance_notes / compliance_reason 是**裁决与规则留痕**面（逐字引用 D03 红线原文以说明
    # 「当时查到什么」），机器闸 V6 已在 rules.json 的 term_scan_exempt.D08 登记豁免
    # （D18 L3 审读结论：留痕面逐字引用属正当留痕）。此处与机器闸保持同一扫描面，
    # 否则脚本无法自建 R-024 留痕 → 脚本与产物漂移（Q27 教训）。
    # 扫描面＝V6 口径：body[].text / body[].emotion。""")

# ── ② body 字段白名单放行 shot_intent ──
E("白名单+shot_intent",
  """        for k in b:
            if k not in {"type", "char_id", "text", "emotion", "sfx", "compliance_added", "compliance_reason"}:
                errs.append(f"ep{ep['ep']} body 非法字段 {k}")""",
  """        for k in b:
            if k not in {"type", "char_id", "text", "emotion", "sfx", "compliance_added", "compliance_reason", "shot_intent"}:
                errs.append(f"ep{ep['ep']} body 非法字段 {k}")
        si = b.get("shot_intent")
        if si is not None:
            if not isinstance(si, str) or not si.strip():
                errs.append(f"ep{ep['ep']} shot_intent 非空字符串")
            elif len(si) > 60:
                errs.append(f"ep{ep['ep']} shot_intent 超 60 字（{len(si)}）:: {si[:40]}")
            for w in CAMERA_BAN:
                if w in si:
                    errs.append(f"ep{ep['ep']} shot_intent 越权写了镜头语言「{w}」:: {si[:40]}")
            for w in BANS:
                if w and w in si:
                    errs.append(f"ep{ep['ep']} shot_intent 命中禁用写法「{w}」:: {si[:40]}")""")

# ── ② shot_intent 数量护栏 + 运镜词表 ──
E("CAMERA_BAN 表",
  """def A(t, **kw):""",
  """# 镜头语言词表：shot_intent 属剧本层「镜头意图」，**不得**越权写景别/焦距/机位/运镜
# （那归 D10 camera_language 与 D11）。下列词一旦出现在 shot_intent 即判越权。
CAMERA_BAN = ["特写", "近景", "中景", "全景", "远景", "远镜头", "景深", "焦距", "机位", "运镜",
              "镜头", "视角", "构图", "长焦", "广角", "主观镜", "过肩", "俯拍", "仰拍", "平拍",
              "跟拍", "轨道", "摇臂", "镜头运动", "画面角度"]


def A(t, **kw):""")

E("每集≥2条护栏",
  """    for k in ep:
        if k not in {"ep", "title", "duration_sec", "scene_heading", "present_characters", "body", "word_count", "compliance_notes"}:
            errs.append(f"ep{ep['ep']} 非法字段 {k}")""",
  """    for k in ep:
        if k not in {"ep", "title", "duration_sec", "scene_heading", "present_characters", "body", "word_count", "compliance_notes"}:
            errs.append(f"ep{ep['ep']} 非法字段 {k}")
    n_si = sum(1 for b in ep["body"] if b.get("shot_intent"))
    if n_si < 2:
        errs.append(f"ep{ep['ep']} shot_intent 回填 {n_si} 条，少于每集最低 2 条")""")

# ── ③ shot_intent 回填（每集 ≥2 条，≤60 字，不含运镜/景别词）──
SI = [
    # ── EP1 归档回滚 ──
    ('A("视野正中浮出灰框面板，栏目自上而下逐格亮起。"),',
     'A("视野正中浮出灰框面板，栏目自上而下逐格亮起。", shot_intent="面板由暗到亮逐格浮现的过程必须被完整看见，不能只给最终画面。"),'),
    ('A("面板中央的倒计时数字跳动：距灰潮试炼降临 2 小时 58 分。"),',
     'A("面板中央的倒计时数字跳动：距灰潮试炼降临 2 小时 58 分。", shot_intent="倒计时数字必须可读，观众要能看清「2 小时 58 分」这个具体数值。"),'),
    ('A("工具箱里只有一把扳手和半卷胶布。"),',
     'A("工具箱里只有一把扳手和半卷胶布。", shot_intent="工具箱里的空缺必须被看见——只有一把扳手和半卷胶布，物资见底是本集前提。"),'),
    # ── EP2 抢点 ──
    ('A("侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。"),',
     'A("侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。", shot_intent="侧门焊死这一步必须被看见：从焊缝成形到闸门合拢，这道门是本集「占位」的关键。"),'),
    ('A("归废处置线外圈，他贴着围栏走了一圈，记下管廊与闸口的位置。"),',
     'A("归废处置线外圈，他贴着围栏走了一圈，记下管廊与闸口的位置。", shot_intent="归废处置线的管廊与闸口必须被看清，这是本集唯一留存的退路信息。"),'),
    ('A("他抬腕看表，钟楼方向传来第一声钟响。"),',
     'A("他抬腕看表，钟楼方向传来第一声钟响。", shot_intent="钟楼方向与第一声钟响必须在画面里有出处，观众要能确认「十一下」不是凭空响起。"),'),
    # ── EP3 面板 ──
    ('A("半透明灰框面板浮到视野正中，底部滚动播报栏。"),',
     'A("半透明灰框面板浮到视野正中，底部滚动播报栏。", shot_intent="面板等级「LV.1」与中文「一阶」必须同屏出现，两个信息缺一不可。"),'),
    ('A("陆沉右手腕骨浮出第一道黑白游龙纹，纹路由腕侧向手背延开。"),',
     'A("陆沉右手腕骨浮出第一道黑白游龙纹，纹路由腕侧向手背延开。", shot_intent="骨纹第一次亮起必须给到独立可辨的视觉呈现，不与人体同框混作。"),'),
    ('A("面板一角读数栏刷新：归一度 0.5%。"),',
     'A("面板一角读数栏刷新：归一度 0.5%。", shot_intent="归一度读数「0.5%」必须能被读出来，这是全片第一次出现读数。"),'),
    # ── EP4 首杀 ──
    ('A("面板四维读数同时暴涨，骨纹进度条推进一格。"),',
     'A("面板四维读数同时暴涨，骨纹进度条推进一格。", shot_intent="首杀后四维读数暴涨与骨纹进度推进必须被看见，这是能力第一次有回报。"),'),
    ('T("全区首杀"),',
     'T("全区首杀", shot_intent="「全区首杀」必须作为面板上的可见信息出现，公开性是本集的后果。"),'),
    ('A("厂区窗外的车灯扫进窗框，一排装甲车停在围栏外。"),',
     'A("厂区窗外的车灯扫进窗框，一排装甲车停在围栏外。", shot_intent="围栏外的装甲车必须被看见，威胁要在拿到雾核之前就压到画面上。"),'),
    # ── EP5 规程 ──
    ('A("终端屏幕亮起一列编号，最后一行被红色拒绝键压住。"),',
     'A("终端屏幕亮起一列编号，最后一行被红色拒绝键压住。", shot_intent="终端上「最后一行被红色拒绝键压住」必须被看见，这是她被判定逾期的直接原因。"),'),
    ('A("处置台在远景里亮起一圈白灯，被处置者只余剪影。"),',
     'A("处置台在远景里亮起一圈白灯，被处置者只余剪影。", shot_intent="处置台的白灯与被处置者的剪影必须同时在画面里，冲击由声音承担。"),'),
    ('A("处置台底下，叶红衣被束具缚住，周身覆着一层霜白，远景只见轮廓。"),',
     'A("处置台底下，叶红衣被束具缚住，周身覆着一层霜白，远景只见轮廓。", shot_intent="叶红衣周身的霜白必须被看见，观众要认出她，但只到轮廓为止。"),'),
    # ── EP6 束具 ──
    ('A("叶承钧被贯穿身侧钢板的钎身别在推土机钢板上，人与钢板之间没有穿透。"),',
     'A("叶承钧被贯穿身侧钢板的钎身别在推土机钢板上，人与钢板之间没有穿透。", shot_intent="钎身与叶承钧之间「别住」的关系必须被看清，不能呈现为刺入人体的效果。"),'),
    ('A("陆沉用钎身砸在叶红衣腕上的束具扣上，扣件弹开。"),',
     'A("陆沉用钎身砸在叶红衣腕上的束具扣上，扣件弹开。", shot_intent="束具扣被砸开的那一下必须被看见，这是叶红衣第一次被救下来。"),'),
    # ── EP7 焚斑 ──
    ('A("灰斑边缘泛起白烟，白烟自下而上散尽。"),',
     'A("灰斑边缘泛起白烟，白烟自下而上散尽。", shot_intent="净火焚斑只以白烟散尽呈现，必须看见烟起与烟尽，不能出现创口。"),'),
    ('A("白烟里的规则余烬回流入陆沉右腕，骨纹进度条被推过一格。"),',
     'A("白烟里的规则余烬回流入陆沉右腕，骨纹进度条被推过一格。", shot_intent="余烬回流与骨纹进度推进必须被看见——救一个人就用掉三十秒上限。"),'),
    # 注：EP4 与 EP7 同有一行「面板一角读数栏仍停在归一度 0.5%。」，故用双行锚点（带下一行台词）消歧。
    ('        A("面板一角读数栏仍停在归一度 0.5%。"),\n        D("YHY", "「你叫什么。」", "清冷，问得直接"),',
     '        A("面板一角读数栏仍停在归一度 0.5%。", shot_intent="归一度读数仍停在 0.5% 必须可读，骨纹更亮不等于归一化在涨。"),\n        D("YHY", "「你叫什么。」", "清冷，问得直接"),'),
    # ── EP8 军令状 ──
    ('A("获救的灰斑者沿钢板墙排成长队，队伍向画面纵深排开。"),',
     'A("获救的灰斑者沿钢板墙排成长队，队伍向画面纵深排开。", shot_intent="获救队列的规模与纵深必须被看见，人数是这一集的全部说服力。"),'),
    ('A("队列末尾有人把袖子拉过手腕，露出褪尽的斑痕。"),',
     'A("队列末尾有人把袖子拉过手腕，露出褪尽的斑痕。", shot_intent="褪尽的斑痕必须被看见，这是「救下来」的可见证据。"),'),
    ('A("面板底部弹出一条求救信号，定位点在城西。"),',
     'A("面板底部弹出一条求救信号，定位点在城西。", shot_intent="求救信号条必须可读，定位点落在城西。"),'),
]
for old, new in SI:
    E("shot_intent", old, new)

# ── ③ 版本号 ──
E("D08 版本号", '"version": "v1.6"', '"version": "v1.7"')

# ── 执行（带命中数断言）──
fails = []
for tag, old, new, n in edits:
    c = src.count(old)
    if c != n:
        fails.append(f"{tag}：期望命中 {n}，实际 {c} :: {old[:60]}")
if fails:
    print("❌ 补丁中止（命中数对不上，不写盘）：")
    for f in fails:
        print("   -", f)
    sys.exit(1)
for tag, old, new, n in edits:
    src = src.replace(old, new, n)
open(D08S, "w", encoding="utf-8").write(src)
print(f"✅ build_D08_U01.py 已打补丁（{len(edits)} 处）")

# ─────────────────────────────────────────────────────────────
# ④ build_D09_U01.py
# ─────────────────────────────────────────────────────────────
src9 = open(D09S, encoding="utf-8").read()
e9 = []
E9 = lambda tag, old, new, n=1: e9.append((tag, old, new, n))

E9("SUBTEXT(8,4) 微调",
   '    (8, 4): "他的口头禅，是给这句军令状压舱——他认下自己要挡的那一整夜。",',
   '    (8, 4): "口头禅，也是军令状的压舱石——他不指望谁来兜底，「带不走」三个字靠的是他自己担下来的话。",')
E9("D09 版本号", '"version": "v1.3"', '"version": "v1.4"')

fails = []
for tag, old, new, n in e9:
    c = src9.count(old)
    if c != n:
        fails.append(f"{tag}：期望命中 {n}，实际 {c} :: {old[:60]}")
if fails:
    print("❌ D09 补丁中止（命中数对不上，不写盘）：")
    for f in fails:
        print("   -", f)
    sys.exit(1)
for tag, old, new, n in e9:
    src9 = src9.replace(old, new, n)
open(D09S, "w", encoding="utf-8").write(src9)
print(f"✅ build_D09_U01.py 已打补丁（{len(e9)} 处）")
