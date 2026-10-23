#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》D12 AI 提示词卡库 · 参数化生成引擎

用法：
    python3 scripts/build_D12.py --unit U02
    python3 scripts/build_D12.py --unit U02 --check-only

设计要点（对应 D12 交付纪律）：
- **不复制 _u02 副本（S12）**：本引擎按 --unit 参数化；单元专属内容放 scripts/d12_content_<UNIT>.py，
  内容模块只需提供 CARDS（32 镜卡数据）与 SCENE_APPEARANCE（每个场景码一份 appearance）。
- **卡头不手写**：景别／机位／焦距／运镜／时长一律从 units/<UNIT>/D11.json 读取后由引擎拼装，
  结构上不可能与 D11 打架（零手抄 = 零冲突）。
- **取景声明不手写**：从 D11 visual_facts 末段机械抽取「主体…留白」取景句，原样落进 image_prompt。
- **台词与音效不手写**：取 D11 shot.dialogue / shot.sfx，并断言台词在 D09 对白表里逐字存在。
- **否定／状态表述正面化（轴②）**：内容模块可给每卡 state_keys，引擎断言这些状态短语在
  image_prompt 与 video_prompt 中都逐字出现——避免把「没有合上」写成「滚过」这类方向错误。
- **体量纪律**：image_prompt / video_prompt 长度设上限，超限即报错，避免把下游 H3 提示词预算吃穿。
- 内建自检：JSON 合法性 / D11 镜号覆盖 / 卡头一致 / 取景落地 / 台词↔D09 / V7 锚点闭合 /
  V5 禁用同义词（negatives 按 rules.json.term_scan_exempt 豁免）/ 母题色板存在性 / 零血腥词自查。
- 重建脚本即 SSOT：status 固定 in_review，重跑不会把状态打回 draft。
"""

import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
SPEC = os.path.abspath(os.path.join(HERE, "..", "..", "..", "03_规格"))

# ---------------------------------------------------------------- 体量上限（防吃 H3 预算）
MAX_IMAGE_CHARS = 330
MAX_VIDEO_CHARS = 260
MAX_NEG_CHARS = 700

# ---------------------------------------------------------------- 固定块
STYLE = "写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
BADGE_POS = "右下角 72%~78% 画面高度留净空供 AI 角标，底部 15% 留字幕带。"
BADGE_NEG = (
    "AI 生成角标须常驻：基线落在画面高 72%~78%、右对齐、距画面右缘 ≥6% 画面宽、"
    "字号 ≥画面高 1.5%、不透明度 ≥50%，黑场镜亦保留，角标文字「AI 生成」，"
    "不得被主体、字幕或特效遮挡、裁切或变形"
)
TEXT_NEG = "画面内文字一律中文并逐字可读；出现外文或字母缩写时同屏必须配中文；不得出现乱码字形"
DEROG_NEG = "画面内不得出现任何贬称、侮辱性或宗教化文字"

GORE = ["gore", "blood", "blood splatter", "red liquid", "open wounds", "internal organs",
        "dismembered limbs", "corpse piles", "rotting flesh", "exposed bone", "eyes and eyeballs"]
RELIG = ["religious iconography", "crosses and crucifixes", "halos", "rosaries and prayer beads",
         "altars", "ritual robes and priestly vestments", "prayer gestures", "chanting",
         "religious processions", "candle-lit shrines", "sacred statuary"]
REAL = ["real-world national flags", "real-world country emblems", "real corporate logos",
        "real-world military insignia", "real-world currency symbols", "real-world ethnic or religious dress",
        "recognizable real-world landmark"]
# REAL 精简组：屏幕/标牌类镜位用，控条数不超 U01 基线上限
REALX = ["real corporate logos", "real-world country emblems", "real-world national flags"]
CREATURE = ["photorealistic flesh decay", "realistic animal anatomy for creatures", "facial features on creatures",
             "skin and muscle detail on creatures", "creature eyes"]
FLAME = ["third flame color", "red flame", "orange flame", "multi-colored fire", "any fire color other than black and white"]
# 实景火光（薪火橙）专用：禁其它焰色，不禁橙
FIRE = ["blue-green flame", "green fire", "purple flame", "magenta flame", "violet fire", "rainbow flame"]
UI = ["garbled text", "fake random glyphs", "English-only text", "red alert overlay", "handwritten text on the interface"]
NO_TEXT = ["no visible text of any kind in frame", "no sign board", "no screen with content"]
SCREEN_TEXT = ["no garbled text", "no English-only text", "no fake random glyphs",
               "red alert overlay", "handwritten text on the interface"]
# 断言 5.9 用：**image_prompt 中声明「画面里有可读文字」的特征**（同屏中文引文／中文可读措辞）。
# 只认「声明」不认「提及」——卡片正文里出现「屏上」二字不等于画面里有字，必须命中下列强特征。
INFRAME_TEXT_RE = re.compile(
    r"(同屏中文「|显示同屏中文|屏上文字|文字层一律中文|中文正写|逐字可读"
    r"|纸面正文保持|条款栏位为|名单板上的名字与数字|告示为中文|字为中文正写)")

# 分级禁项（L1 突发惊吓 / L2 血腥特写）——全卡通用，来源 D03.red_lines L1/L2
UNIVERSAL = ["jump scares", "extreme close-up of a screaming face"]

# 内容模块按镜位指定的负向词组（组名 → 词表）
NEG_GROUPS = {
    "GORE": GORE, "RELIG": RELIG, "REAL": REAL, "REALX": REALX, "CREATURE": CREATURE,
    "FLAME": FLAME, "FIRE": FIRE, "UI": UI, "NOTEKST": NO_TEXT,
}

# 焦距 → 构图意图（防止文案与焦距矛盾：广角主体小而居中，长焦主体大而靠前）
LENS_PHRASE = {
    24: "24mm 广角，主体在画框中占比小、居中，环境占满上下画面",
    35: "35mm，主体占画面中段，四周留出环境纵深",
    50: "50mm 中焦，主体放大居中，纵深压缩",
    85: "85mm 长焦，主体放大靠前，背景压平",
}

# seed 域：角色跨单元同族（跨集同角色必须同一 seed 家族），场景域按单元分段
SEED_ROLE = {"LC": "110101", "YHY": "110201", "SQC": "110301", "YJ-ES": "110301",
             "YJ-JZ": "110401", "YD-GC": "110501", "WM-SZ": "110601"}
SEED_SCENE_U01 = {"A-1": "110401", "A-2": "110402", "A-3": "110403", "A-4": "110404", "A-5": "110405",
                  "A-6": "110406", "A-7": "110407", "A-8": "110408", "A-9": "110409"}
SEED_SCENE_U02 = {"B-1": "110511", "B-2": "110512", "B-3": "110513", "B-4": "110514", "B-5": "110515",
                  "B-6": "110516", "B-7": "110517", "B-8": "110518", "B-9": "110519", "B-10": "110520"}
# U03（ep017–024，场景码 B-11…B-19）—— 沿用 B 族连续段，不与 U02 重号
SEED_SCENE_U03 = {"B-11": "110521", "B-12": "110522", "B-13": "110523", "B-14": "110524", "B-15": "110525",
                  "B-16": "110526", "B-17": "110527", "B-18": "110528", "B-19": "110529"}
SEED_UI = "110501"
MODEL = "H3（图生视频；首帧＝本卡 image_prompt 产出图）"

# ---------------------------------------------------------------- Q107 拼接边界纪律
# 依据：D18 global_checks Q107 —— 模板拼接的每个片段边界必须自带标点，或由拼接器显式补分隔符。
#   ① 片段 A 末尾无句读终止符（。／；／：／！／？）且片段 B 以文字开头 ⇒ 拼接器必须补分隔符，
#      禁止把两个完整句首尾相接（典型症状：「…只留下一道暗色右下角 72%~78%…」）；
#   ② 抽取型片段（从 D11 visual_facts 机械抽取的取景句）默认不带尾标点，不得假设源文本自带；
#   ③ 片段内容已被前文逐小句覆盖 ⇒ 判为重复并整段丢弃（禁止同卡出现重复句）。
SENT_END_CHARS = "。；：！？"
CLAUSE_SPLIT_RE = re.compile(r"[。；，]")
SENT_SPLIT_RE = re.compile(r"[。；]")
RUNON_RE = re.compile(r"[^\s，。；]{6,}右下角")
DUP_MIN_SENT_LEN = 12


def _clauses(text):
    """按「。」「；」「，」切成小句（判重复的最小单位）。"""
    return [c.strip() for c in CLAUSE_SPLIT_RE.split(text or "") if c.strip()]


def _sentences(text):
    """按「。」「；」切成句子（与 D18 Q107 验收口径一致）。"""
    return [s.strip() for s in SENT_SPLIT_RE.split(text or "") if s.strip()]


def join_fragments(fragments):
    """把若干片段拼成一段可读文本 —— Q107 边界纪律的唯一实现点。

    - 片段为空 ⇒ 直接跳过（既不产生多余标点，也不会出现「。。」或悬空分隔）；
    - 前文末尾无句读终止符 ⇒ 显式补「。」（禁止两个完整句黏成一句）；
    - 片段的每个小句都已在前文出现 ⇒ 判为重复，整段丢弃（禁止同卡出现重复句）。
    """
    out = ""
    seen_clauses = set()
    for frag in fragments:
        f = (frag or "").strip()
        if not f:
            continue
        fc = _clauses(f)
        if fc and all(c in seen_clauses for c in fc):
            continue                      # 重复片段 → 丢弃
        if out and out[-1] not in SENT_END_CHARS:
            out += "。"                   # 边界补句读分隔
        out += f
        seen_clauses.update(fc)
    return out


def dup_sentences(text):
    """同卡重复句检测（口径：按「。」「；」切分取长度 ≥12 的句子；
    句 A 被同卡另一句 B 完整包含亦判重复 —— 黏连会把重复句的尾标点吞掉，
    只判完全相等会漏判，故取更严口径）。"""
    sents = [s for s in _sentences(text) if len(s) >= DUP_MIN_SENT_LEN]
    out = []
    for i, a in enumerate(sents):
        for j, b in enumerate(sents):
            if i != j and a != b and a in b and a not in out:
                out.append(a)
                break
    return out


def negs(*groups, extra=None):
    out = []
    for g in groups:
        out.extend(g)
    if extra:
        out.extend(extra)
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def load_module(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_text(node, acc):
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, list):
        for x in node:
            all_text(x, acc)
    elif isinstance(node, dict):
        for v in node.values():
            all_text(v, acc)
    return acc


def framing_of(visual_facts):
    """从 D11 visual_facts 末段机械抽取取景声明（末段恒为角标句，倒数第二段为取景句）。"""
    segs = [x.strip() for x in visual_facts.split("；") if x.strip()]
    if len(segs) >= 2 and segs[-1] == "右下角常驻白色角标：AI 生成。":
        return segs[-2]
    for s in reversed(segs):
        if any(k in s for k in ("画面", "留白", "留一段", "居中", "正中", "充满")):
            return s
    return ""


def build(unit, check_only=False, verbose=False):
    proj_dir = os.path.join(PROJ, "units", unit)
    D10 = json.load(open(os.path.join(PROJ, "shared", "D10.json"), encoding="utf-8"))
    D05 = json.load(open(os.path.join(PROJ, "shared", "D05.json"), encoding="utf-8"))
    D11 = json.load(open(os.path.join(proj_dir, "D11.json"), encoding="utf-8"))
    D09 = json.load(open(os.path.join(proj_dir, "D09.json"), encoding="utf-8"))
    RULES = json.load(open(os.path.join(SPEC, "rules.json"), encoding="utf-8"))

    content = load_module(os.path.join(HERE, f"d12_content_{unit}.py"))

    ANCHORS = {a["char_id"]: a for a in D10["character_anchors"]}
    MOTIFS = {m["motif_id"] for m in D10["motifs"]}
    PALETTE = {p["name"] for p in D10["palette"]}
    SHOTS = {}
    for e in D11["episodes"]:
        for s in e["shots"]:
            SHOTS[(e["ep"], s["shot_id"])] = s
    D09_TEXTS = {l["text"] for l in D09.get("lines", [])}
    BANNED = sorted({b for g in D05["glossary"] for b in (g.get("forbidden_synonyms") or [])})
    GORE_WORDS = RULES.get("forbidden_words", [])
    SEED_SCENE = dict(SEED_SCENE_U01)
    SEED_SCENE.update(SEED_SCENE_U02)
    SEED_SCENE.update(SEED_SCENE_U03)
    APPEAR = content.SCENE_APPEARANCE
    OPPOSITES = getattr(content, "OPPOSITES", {})

    cards = []
    idx0 = 0 if unit == "U01" else int(unit[1:]) * 100 - 100
    for n, item in enumerate(content.CARDS, start=1):
        ep, sid = item["ep"], item["shot_id"]
        descs = list(item.get("descs", []))
        motifs = list(item.get("motifs", []))
        palette = list(item.get("palette", []))
        body_image = item["body_image"]
        body_video = item["body_video"]
        extra = list(item.get("extras", []))
        steps = item.get("steps", 30)
        state_keys = list(item.get("state_keys", []))
        has_text = bool(item.get("text", False))

        shot = SHOTS[(ep, sid)]
        scene = shot["scene_code"]
        scene_appear = APPEAR[scene]
        frame = framing_of(shot["visual_facts"])

        header = (f"{shot['shot_size']}，{shot['camera_angle']}，{shot['lens_mm']}mm，{shot['movement']}，9:16 竖屏。")
        lens_phrase = LENS_PHRASE[int(shot["lens_mm"])]

        # Q107 拼接边界：改走 join_fragments —— 由拼接器统一处理边界标点与重复片段，
        # 不再由本行裸拼（裸拼时 frame 无尾标点会与 BADGE_POS 黏成一句）。
        image_prompt = join_fragments([header, lens_phrase, scene_appear,
                                       body_image, frame, BADGE_POS, STYLE])
        # 台词与音效取自 D11，避免手抄不一致
        dialogue = (shot.get("dialogue") or "").strip()
        sfx = (shot.get("sfx") or "").strip()
        video_prompt = (f"{shot['duration_sec']} 秒单镜：" + body_video
                        + (f"；台词：{dialogue}" if dialogue else "；本镜无台词")
                        + (f"；音效：{sfx}" if sfx else "")
                        + "；右下角 AI 生成角标常驻不遮挡。")

        # negatives 组装（对齐 U01 体例）：GORE + 按镜位指定的组 + 本卡专属 + 文字类 + 三条固定块
        neg_list = list(GORE) + list(UNIVERSAL)
        for g in item.get("groups", []):
            if g not in NEG_GROUPS:
                raise KeyError(f"未定义的负向词组：{g}（ep{ep} 镜{sid}）")
            neg_list += NEG_GROUPS[g]
        neg_list += list(extra)
        neg_list += (SCREEN_TEXT if has_text else NO_TEXT)
        neg_list += [BADGE_NEG, TEXT_NEG, DEROG_NEG]

        chars = item.get("chars")
        if chars is None:
            chars = []
            for cid in descs:
                if cid not in chars:
                    chars.append(cid)
        # char_ids 由 descs 反查：只登记「本卡画框内出现的编号角色」
        chars = item.get("char_ids", chars)

        parts = []
        if chars:
            parts.append("角色域 seed 固定 " + "／".join(f"{c}:{SEED_ROLE.get(c, '110999')}" for c in chars))
        else:
            parts.append("无角色域 seed")
        parts.append(f"场景光效域 seed {SEED_SCENE[scene]}")
        if has_text:
            parts.append(f"面板与界面域 seed {SEED_UI}")
        parts.append("同角色跨集复用同一 seed 家族；换 seed 必须重述全部锚点句")

        cards.append({
            "card_id": f"C-{idx0 + n:03d}",
            "ep": ep,
            "shot_id": sid,
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "negatives": negs(*[[x for x in neg_list]]),
            "params": {
                "model": MODEL,
                "aspect": "9:16",
                "seed_strategy": "；".join(parts),
                "steps": steps,
                "guidance": 6.5,
                "duration_sec": shot["duration_sec"],
            },
            "consistency_refs": {
                "char_ids": chars,
                "motifs": motifs,
                "palette": palette,
            },
            "char_descriptions": descs,
            "source": "both",
        })

    doc = {
        "doc_id": "D12",
        "unit": unit,
        "version": content.VERSION,
        "status": "in_review",
        "cards": cards,
    }

    # ---------------------------------------------------------------- 自检
    errs, warns = [], []
    if set(SHOTS.keys()) != {(c["ep"], c["shot_id"]) for c in cards}:
        errs.append("卡集合与 D11 镜集合不一致")
    if len(cards) != len(content.CARDS):
        errs.append("卡数与内容模块不一致")

    for c in cards:
        cid = c["card_id"]
        shot = SHOTS[(c["ep"], c["shot_id"])]
        ip, vp = c["image_prompt"], c["video_prompt"]

        # 卡头与 D11 逐镜一致（卡头由引擎生成，这里做回归断言）
        for token in (f"{shot['shot_size']}，{shot['camera_angle']}，{shot['lens_mm']}mm，{shot['movement']}"):
            if token not in ip:
                errs.append(f"{cid}: 卡头与 D11 不一致（缺 {token}）")
        if f"{shot['duration_sec']} 秒单镜" not in vp:
            errs.append(f"{cid}: video_prompt 缺 D11 镜时")
        # 焦距意图与焦距值一致
        if LENS_PHRASE[int(shot["lens_mm"])] not in ip:
            errs.append(f"{cid}: 缺焦距构图短语")
        # 取景声明落地
        frame = framing_of(shot["visual_facts"])
        if frame and frame not in ip:
            # Q107：取景句若被判为重复而整段丢弃，改判「逐小句语义落地」——
            # 内容必须仍在 image_prompt 里，但不要求与源句逐字同构（源句的「，」在正文里可能是「；」）。
            ip_clauses = set(_clauses(ip))
            if not all(c in ip_clauses for c in _clauses(frame)):
                errs.append(f"{cid}: 取景声明未落进 image_prompt")
        # 场景 appearance 落地
        if APPEAR[shot["scene_code"]] not in ip:
            errs.append(f"{cid}: 场景 appearance 未落进 image_prompt")
        # Q107 边界自检（防静默回退：拼接器改动后必须仍然成立）
        if RUNON_RE.search(ip):
            errs.append(f"{cid}: image_prompt 存在片段黏连（边界未补句读分隔）："
                        f"{RUNON_RE.search(ip).group(0)[-20:]}")
        if "。。" in ip:
            errs.append(f"{cid}: image_prompt 出现多余标点「。。」")
        dups = dup_sentences(ip)
        if dups:
            errs.append(f"{cid}: image_prompt 出现同卡重复句：{dups[0]}")
        # 台词与音效取自 D11
        d = (shot.get("dialogue") or "").strip()
        if d and f"台词：{d}" not in vp:
            errs.append(f"{cid}: video_prompt 台词与 D11 不一致")
        if d:
            for part in [x.strip() for x in d.split("／") if x.strip()]:
                core = re.sub(r"^[^「]*", "", part).strip()
                if core and core not in D09_TEXTS:
                    errs.append(f"{cid}: 台词「{core}」不在 D09 对白表")
        s = (shot.get("sfx") or "").strip()
        if s and f"音效：{s}" not in vp:
            errs.append(f"{cid}: video_prompt 音效与 D11 不一致")
        # 轴②：否定／状态表述必须正面出现在两张 prompt 里
        item = next(x for x in content.CARDS if x["ep"] == c["ep"] and x["shot_id"] == c["shot_id"])
        for key in item.get("state_keys", []):
            if key not in ip:
                errs.append(f"{cid}: 状态短语未在 image_prompt 正面出现：{key}")
            if key not in vp:
                errs.append(f"{cid}: 状态短语未在 video_prompt 正面出现：{key}")
        # 轴②反向守卫：相反过程词不得出现在任一 prompt（不得写成与状态相反的过程）
        for bad in OPPOSITES.get(f"ep{c['ep']}_s{c['shot_id']}", []):
            if bad in ip:
                errs.append(f"{cid}: image_prompt 出现与状态相反的过程词「{bad}」")
            if bad in vp:
                errs.append(f"{cid}: video_prompt 出现与状态相反的过程词「{bad}」")
        # V7 锚点闭合：每条 char_descriptions 必须原样出自「本卡已声明角色」的 anchor_text / markers
        declared = c["consistency_refs"]["char_ids"]
        descs_c = c["char_descriptions"]
        if not declared and descs_c:
            errs.append(f"{cid}: 未声明角色却填了 char_descriptions（画面无编号角色时不得用锚点声明服装）：{descs_c}")
        if declared and not descs_c:
            warns.append(f"{cid}: 声明了角色 {declared} 但未填 char_descriptions（手部-only 镜位可接受，无法验证锚点闭合）")
        allowed = []
        for cid2 in declared:
            a = ANCHORS.get(cid2)
            if not a:
                errs.append(f"{cid}: D10 无角色锚点 {cid2}")
                continue
            allowed.append((cid2, f"{a['anchor_text']} {' '.join(a['markers'])}"))
        for d in descs_c:
            if allowed and not any(d in hay for _, hay in allowed):
                errs.append(f"{cid}: char_descriptions「{d}」未原样出自已声明角色的 D10 锚点/markers")
        for cid2, hay in allowed:
            # 官方 V7 口径：descs 为空 → 只 warning（手部-only 镜位可接受）；descs 非空但无一匹配 → error
            if not descs_c:
                continue
            related = [x for x in descs_c if x in hay or any(m in x for m in ANCHORS[cid2]["markers"])]
            if not related:
                errs.append(f"{cid}: 角色 {cid2} 的描述未匹配 D10 锚点表")
        # 母题 / 色板存在性
        for m in c["consistency_refs"]["motifs"]:
            if m not in MOTIFS:
                errs.append(f"{cid}: 母题 {m} 不在 D10")
        for p in c["consistency_refs"]["palette"]:
            if p not in PALETTE:
                errs.append(f"{cid}: 色板 {p} 不在 D10")
        # 体量
        if len(ip) > MAX_IMAGE_CHARS:
            errs.append(f"{cid}: image_prompt {len(ip)} 字 > 上限 {MAX_IMAGE_CHARS}")
        if len(vp) > MAX_VIDEO_CHARS:
            errs.append(f"{cid}: video_prompt {len(vp)} 字 > 上限 {MAX_VIDEO_CHARS}")
        if sum(len(x) for x in c["negatives"]) > MAX_NEG_CHARS:
            errs.append(f"{cid}: negatives 合计 {sum(len(x) for x in c['negatives'])} 字 > 上限 {MAX_NEG_CHARS}")
        # 零血腥词自查（V6 表）
        for w in GORE_WORDS:
            if w in ip or w in vp:
                errs.append(f"{cid}: 画面文案命中零血腥词「{w}」")
        # 断言 5.9（2026-10-23 视觉设定岗）：**画内文字声明 ⇄ negatives 文字组不得自相矛盾**
        #   缺陷成因：负词组由内容源的 `text` 标志二选一派生（SCREEN_TEXT vs NO_TEXT），
        #   而 image_prompt 的正文与取景句会**机械抽取** D11 末段（含「同屏中文「…」」读数栏）。
        #   ⇒ 若某镜 `text=False` 但 D11 该镜有画内可读文字，卡会出现
        #     「image_prompt 声明画内中文文字」×「negatives 禁一切画内文字」的自相矛盾。
        #   实测本条曾漏标 1 张（U03 C-224 / ep22镜4），故固化守卫防复发。
        #   判据：若 image_prompt 声明了画内可读文字，则 negatives 不得含 NO_TEXT 任一条。
        if INFRAME_TEXT_RE.search(ip):
            for bad in NO_TEXT:
                if bad in c["negatives"]:
                    errs.append(f"{cid}: image_prompt 声明画内可读文字，但 negatives 含互斥负词「{bad}」"
                                f"（text 标志与 D11 画内文字事实不符）")

    # V5 术语扫描（negatives 按 rules.json.term_scan_exempt 的 cards[].negatives 豁免）
    exempt = set(RULES.get("term_scan_exempt", {}).get("D12", []))
    scan = []
    for c in cards:
        scan.append(c["image_prompt"])
        scan.append(c["video_prompt"])
        scan.append(json.dumps(c["params"], ensure_ascii=False))
        scan.append(json.dumps(c["consistency_refs"], ensure_ascii=False))
        scan.extend(c["char_descriptions"])
    joined = "\n".join(scan)
    hits = sorted({w for w in BANNED if w in joined})
    if hits:
        errs.append(f"V5 命中禁用同义词：{hits}")
    neg_join = "\n".join(x for c in cards for x in c["negatives"])
    neg_hits = sorted({w for w in BANNED if w in neg_join})
    if neg_hits and "cards[].negatives" not in exempt:
        errs.append(f"V5 命中禁用同义词（negatives 未豁免）：{neg_hits}")

    stats = {
        "cards": len(cards),
        "scenes": sorted({SHOTS[(c["ep"], c["shot_id"])] ["scene_code"] for c in cards}),
        "negatives_total": sum(len(c["negatives"]) for c in cards),
        "negatives_per_card": (min(len(c["negatives"]) for c in cards),
                               max(len(c["negatives"]) for c in cards)),
        "max_image_chars": max(len(c["image_prompt"]) for c in cards),
        "max_video_chars": max(len(c["video_prompt"]) for c in cards),
        "max_neg_chars": sum(len(x) for x in max(cards, key=lambda c: sum(len(x) for x in c["negatives"]))["negatives"]),
        "max_card_total": max(len(c["image_prompt"]) + len(c["video_prompt"])
                              + sum(len(x) for x in c["negatives"]) for c in cards),
        "motifs_used": sorted({m for c in cards for m in c["consistency_refs"]["motifs"]}),
        "chars_used": sorted({x for c in cards for x in c["consistency_refs"]["char_ids"]}),
    }

    if errs:
        print("❌ 自检未通过：")
        for e in errs:
            print("   -", e)
        if verbose:
            print("   ── 逐卡体量与 state_keys 命中 ──")
            for c in cards:
                item = next(x for x in content.CARDS
                            if x["ep"] == c["ep"] and x["shot_id"] == c["shot_id"])
                miss = [k for k in item.get("state_keys", [])
                        if k not in c["image_prompt"] or k not in c["video_prompt"]]
                print(f"   {c['card_id']} ep{c['ep']:02d}/S{c['shot_id']} "
                      f"img={len(c['image_prompt']):>3} vid={len(c['video_prompt']):>3} "
                      f"neg={sum(len(x) for x in c['negatives']):>3} "
                      f"keys={len(item.get('state_keys', []))} miss={len(miss)}")
                for k in miss:
                    print(f"        × {k}")
        return 1, stats

    if not check_only:
        out = os.path.join(proj_dir, "D12.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✅ 写出 {out}")

    print(f"   卡数 {stats['cards']}（D11 镜数 {len(SHOTS)}）｜场景码 {stats['scenes']}")
    print(f"   negatives：{stats['negatives_total']} 条（每卡 {stats['negatives_per_card'][0]}~{stats['negatives_per_card'][1]}）")
    print(f"   最长 image_prompt {stats['max_image_chars']} 字｜最长 video_prompt {stats['max_video_chars']} 字｜"
          f"单卡 negatives 最长 {stats['max_neg_chars']} 字｜单卡正文最大 {stats['max_card_total']} 字")
    print(f"   使用母题 {stats['motifs_used']}｜使用角色 {stats['chars_used']}")
    print(f"   V5 禁用同义词命中 0（negatives 豁免：{'cards[].negatives' if 'cards[].negatives' in exempt else '无'}）")
    for w in warns:
        print("   !", w)
    return 0, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True, help="单元号，如 U01 / U02")
    ap.add_argument("--check-only", action="store_true", help="只自检不写盘")
    ap.add_argument("--verbose", action="store_true", help="自检失败时打印逐卡体量与 state_keys 命中明细")
    args = ap.parse_args()
    code, _ = build(args.unit.upper(), check_only=args.check_only, verbose=args.verbose)
    sys.exit(code)


if __name__ == "__main__":
    main()
