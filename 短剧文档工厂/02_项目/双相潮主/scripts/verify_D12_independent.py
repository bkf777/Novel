#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D12 · 独立复核（另立判据，不引用任何构建脚本）｜单元参数化

复核原则（对应「构建脚本自检不能自证」）：
① 判据现读源文件重建：卡头/取景句从 D11 现解析，禁词从 rules.json 现读，
   锚点从 D10 现读，禁词组从 D10.negatives 现读——不抄构建脚本里的任何常量。
② 至少覆盖构建脚本自检**没有覆盖**的项：
   - 焦距↔构图一致性（按焦距分段独立推导主体大小措辞）
   - 轴②反向：自行现读 D11 的否定/状态段，判定「末句必须被正面拍出」
   - negatives 英文语体（除三条固定中文块外必须全 ASCII）
   - D10.negatives 共享池的覆盖度
   - D04 角色表存在性
③ 负测：--inject 故意注入一条故障，确认复核脚本报错（证明断言非恒真）。
④ 单元参数化（--unit，默认 U02）：D10 v1.10「共享池下放口径」要求「非血腥语义条目须单元覆盖」，
   本脚本的 H9 即该口径的可机械判定实现，下一单元可直接复用（U03+ 沿用同一判据）。
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
SPEC = os.path.abspath(os.path.join(HERE, "..", "..", "..", "03_规格"))

errs = []
warns = []
checks = 0


def ck(cond, msg):
    global checks
    checks += 1
    if not cond:
        errs.append(msg)
    return cond


def J(path):
    return json.load(open(path, encoding="utf-8"))


def _norm(s):
    """归一化：去掉标点与空白，用于「合句/分句」形态差异下的事实比对（不改变字词）。"""
    return re.sub(r"[，。；、！？：\s,.!?;:]", "", s or "")


def main(unit, inject=None):
    D12 = J(os.path.join(PROJ, "units", unit, "D12.json"))
    D11 = J(os.path.join(PROJ, "units", unit, "D11.json"))
    D09 = J(os.path.join(PROJ, "units", unit, "D09.json"))
    D10 = J(os.path.join(PROJ, "shared", "D10.json"))
    D04 = J(os.path.join(PROJ, "shared", "D04.json"))
    D05 = J(os.path.join(PROJ, "shared", "D05.json"))
    RULES = J(os.path.join(SPEC, "rules.json"))

    if inject == "header":
        D12["cards"][0]["image_prompt"] = "特写，平视，35mm，固定机位，9:16 竖屏。" + D12["cards"][0]["image_prompt"]
    if inject == "axis2":
        D12["cards"][22]["image_prompt"] = D12["cards"][22]["image_prompt"].replace(
            "最后一栏数字没有合上", "最后一栏数字已经合上")
    if inject == "negcn":
        D12["cards"][3]["negatives"].append("画面内禁止出现贬称文字与外文")
    if inject == "fire":
        D12["cards"][5]["negatives"] = [n for n in D12["cards"][5]["negatives"]
                                        if n != "net fire illuminating more than a small contact patch of skin"]
    if inject == "move":
        # 负测：抽掉 C-131 的运镜口头化表述 → M1/M2 必须报错
        _b = D12["cards"][30]["video_prompt"]
        _a = _b.replace("镜头跟住人流从缺口穿行，", "")
        if _a == _b:
            print("⛔ 注入失败：目标串「镜头跟住人流从缺口穿行，」未命中 → 负测无效（拒跑）")
            return 9
        D12["cards"][30]["video_prompt"] = _a
    if inject == "m1c":
        # 负测（2026-10-23）：抽掉复合/单字运镜镜位 C-205 的运镜口头化 → M1 必须报错
        _c = D12["cards"][4]
        _a = _c["video_prompt"].replace("镜头自全景缓慢推进；", "")
        if _a == _c["video_prompt"]:
            print("⛔ 注入失败：目标串「镜头自全景缓慢推进；」未命中 → 负测无效（拒跑）")
            return 9
        _c["video_prompt"] = _a
    if inject == "m3":
        # 负测（2026-10-23）：把固定机位卡 C-209 的「镜头固定不动」改成运镜表述 → M3 必须报错
        _c = D12["cards"][8]
        _a = _c["video_prompt"].replace("镜头固定不动；", "镜头自中景推近门柱；")
        if _a == _c["video_prompt"]:
            print("⛔ 注入失败：目标串「镜头固定不动；」未命中 → 负测无效（拒跑）")
            return 9
        _c["video_prompt"] = _a
    if inject == "d2":
        # 负测（2026-10-23 13:2x）：把 U03 C-203 的取景声明整段抽掉 → D2 必须报错
        #   （证明「同义表述核销」放宽后，**事实缺失仍然拦得住**，不是恒真放行）
        _c = D12["cards"][2]
        _a = _c["image_prompt"].replace("街口只剩暗处与被截断的路；主谋只作剪影，不给面部。", "")
        if _a == _c["image_prompt"]:
            print("⛔ 注入失败：目标串未命中 → 负测无效（拒跑）")
            return 9
        _c["image_prompt"] = _a

    cards = D12["cards"]
    shots = {}
    for e in D11["episodes"]:
        for s in e["shots"]:
            shots[(e["ep"], s["shot_id"])] = s

    # ---------- 体例探测（判据须先确认自己适用）----------
    # 本岗参数化引擎 build_D12.py 的卡头体例含 movement：
    #   「{shot_size}，{camera_angle}，{lens_mm}mm，{movement}，9:16 竖屏。」
    # 旧脚本 build_D12_U01.py 产出的 U01 D12 卡头**不含 movement**（体例不同），
    # 若直接套用会刷出大量「卡头不一致」误报 → 工具误报比工具缺位更危险。
    # 故先探测；体例不符则跳过 B1/B2 两项判据并显式告警，其余判据照常。
    _s0 = shots[(cards[0]["ep"], cards[0]["shot_id"])]
    _h_new = f"{_s0['shot_size']}，{_s0['camera_angle']}，{_s0['lens_mm']}mm，{_s0['movement']}，9:16 竖屏。"
    _h_old = f"{_s0['shot_size']}，{_s0['camera_angle']}，{_s0['lens_mm']}mm，9:16 竖屏。"
    _head0 = cards[0]["image_prompt"]
    LEGACY_HEADER = _head0.startswith(_h_old) and not _head0.startswith(_h_new)
    anchors = {a["char_id"]: a for a in D10["character_anchors"]}
    char_ids = {c["id"] for c in D04["characters"]}
    motifs = {m["motif_id"] for m in D10["motifs"]}
    palettes = {p["name"] for p in D10["palette"]}
    d09_texts = {l["text"] for l in D09.get("lines", [])}
    pool = list(D10["negatives"])

    # ---------- A 结构与覆盖 ----------
    ck(len(cards) == len(shots), f"A1 卡数 {len(cards)} ≠ D11 镜数 {len(shots)}")
    ck({(c["ep"], c["shot_id"]) for c in cards} == set(shots), "A2 卡与 D11 镜集合不一致")
    ck(len({(c["ep"], c["shot_id"]) for c in cards}) == len(cards), "A2b 存在重复镜（合并/拆分）")
    ck(len({c["card_id"] for c in cards}) == len(cards), "A3 card_id 不唯一")
    for c in cards:
        ck(re.fullmatch(r"[A-Z]+-[0-9]+", c["card_id"]) is not None, f"A3b {c['card_id']} 不符 card_id 模式")
        ck(c["consistency_refs"]["char_ids"] is not None, f"A3c {c['card_id']} 缺 consistency_refs")

    # ---------- B 卡头与 D11 逐镜一致（独立解析，不复用构建脚本） ----------
    if LEGACY_HEADER:
        warns.append(f"B1/B2 已跳过：本单元 D12 卡头体例不含 movement（与本岗参数化引擎 build_D12.py 不同体例），"
                     f"卡头判据不适用；其余判据照常执行")
    for c in cards:
        s = shots[(c["ep"], c["shot_id"])]
        if LEGACY_HEADER:
            continue
        head = f"{s['shot_size']}，{s['camera_angle']}，{s['lens_mm']}mm，{s['movement']}，9:16 竖屏。"
        ck(c["image_prompt"].startswith(head), f"B1 {c['card_id']} 卡头与 D11 不一致：{head}")
        ck(c["video_prompt"].startswith(f"{s['duration_sec']} 秒单镜："),
           f"B2 {c['card_id']} video_prompt 未以 D11 镜时开头")
        ck(f"{s['duration_sec']} 秒单镜" in c["video_prompt"], f"B2b {c['card_id']} 缺 D11 镜时")

    # ---------- C 焦距↔构图一致（按焦距分段独立推导） ----------
    for c in cards:
        if LEGACY_HEADER:
            break
        s = shots[(c["ep"], c["shot_id"])]
        lens = int(s["lens_mm"])
        head = f"{s['shot_size']}，{s['camera_angle']}，{s['lens_mm']}mm，{s['movement']}，9:16 竖屏。"
        rest = c["image_prompt"][len(head):]
        m = re.search(r"[^。]*\d+\s*mm[^。]*。", rest)
        ck(m is not None, f"C1 {c['card_id']} 找不到焦距构图句")
        if not m:
            continue
        clause = m.group(0)
        # 主体大小措辞（从文本判定，不查表）
        small = any(k in clause for k in ("占比小", "主体小", "占画面中段", "中段"))
        large = any(k in clause for k in ("放大", "主体大", "靠前"))
        if lens <= 35:
            ck(not large, f"C2 {c['card_id']} 广角 {lens}mm 用了长焦构图措辞：{clause}")
            ck(small, f"C3 {c['card_id']} 广角 {lens}mm 缺「主体小/居中」措辞：{clause}")
        elif lens >= 85:
            ck(large, f"C4 {c['card_id']} 长焦 {lens}mm 缺「主体大/靠前」措辞：{clause}")
            ck(not (small and "占画面中段" in clause), f"C5 {c['card_id']} 长焦 {lens}mm 用了广角构图措辞：{clause}")
        else:
            ck(large or small, f"C6 {c['card_id']} 中焦 {lens}mm 缺主体占比措辞：{clause}")

    # ---------- D 取景声明落地（独立解析 D11 visual_facts） ----------
    # 只判「独立取景声明段」：**D11 的可见事实散文被 D12 改写成画面语言，用词必然不同**
    # （例：D11「锈蚀门板被焊枪起弧的蓝白弧光逐寸熔接」→ D12「锈蚀卷帘门内侧，蓝白弧光沿门板逐寸熔接」），
    # 故「逐字落地」对可见事实**不成立**、不得作为判据；事实不丢由轴② G1（否定/状态末句必须被正面拍出）承担。
    # 取景声明是 D11 明确给出的硬约束（「主体（…）在画面中部偏上…头顶留白」），故**逐字**判据成立。
    # U01 体例的 D11 v1.8 无独立取景段 → 按 LEGACY_HEADER 跳过（避免刷出误报）。
    if LEGACY_HEADER:
        warns.append("D2 已跳过：本单元 D11 无独立取景声明段（旧体例），取景判据不适用；事实不丢由 G1 承担")
    for c in cards:
        if LEGACY_HEADER:
            break
        s = shots[(c["ep"], c["shot_id"])]
        segs = [x.strip() for x in s["visual_facts"].split("；") if x.strip()]
        framing = ""
        if segs and segs[-1].endswith("角标：AI 生成。"):
            framing = segs[-2] if len(segs) >= 2 else ""
        else:
            for x in reversed(segs):
                if any(k in x for k in ("画面", "留白", "居中", "留一段")):
                    framing = x
                    break
        ck(bool(framing), f"D2 {c['card_id']} 无法从 D11 解析取景声明")
        if framing:
            # D2 取景声明落地 —— 按 **Q77 判据方法**（命中低先回查原文、逐要素判「缺失／同义」）：
            #   ① 逐字命中 → 通过；
            #   ② 逐字未命中但**归一后命中**（仅合句↔分句／标点差异，事实完整）→ **判同义表述，人工核销留痕（warning）**，
            #      **不因此改动交付物**；
            #   ③ 归一后仍不命中 → 事实缺失 ⇒ error。
            #   实测触发例（U03 C-203）：D11 取景句为合句「街口只剩暗处与被截断的路，主谋只作剪影，不给面部」，
            #   D12 写成两句「街口只剩暗处与被截断的路；主谋只作剪影，不给面部。」⇒ 事实逐要素齐全，仅标点分句不同。
            if framing in c["image_prompt"]:
                pass
            elif _norm(framing) in _norm(c["image_prompt"]):
                warns.append(f"D2 {c['card_id']} 取景声明为**同义表述**（仅合句/分句与标点差异，事实逐要素齐全）"
                             f"⇒ 按 Q77 人工核销留痕，不改动交付物：{framing[:40]}")
            else:
                ck(False, f"D2 {c['card_id']} 取景声明未落进 image_prompt：{framing[:40]}")

    # ---------- E 台词 / 音效 ----------
    # E1/E3/E4 判的是「本引擎约定的承载写法」（台词：X／音效：X／本镜无台词标记）→ 旧体例不适用；
    # E2 判的是「D11 台词是否逐字存在于 D09 对白表」→ 与承载写法无关，两体例均适用。
    for c in cards:
        s = shots[(c["ep"], c["shot_id"])]
        d = (s.get("dialogue") or "").strip()
        fx = (s.get("sfx") or "").strip()
        if d:
            if not LEGACY_HEADER:
                ck(f"台词：{d}" in c["video_prompt"], f"E1 {c['card_id']} 台词与 D11 不一致")
            for part in [x.strip() for x in d.split("／") if x.strip()]:
                core = re.sub(r"^[^「]*", "", part).strip()
                if core:
                    ck(core in d09_texts, f"E2 {c['card_id']} 台词「{core[:24]}」不在 D09 对白表")
        else:
            if not LEGACY_HEADER:
                ck("本镜无台词" in c["video_prompt"], f"E3 {c['card_id']} 无台词镜未标「本镜无台词」")
        if fx and not LEGACY_HEADER:
            ck(f"音效：{fx}" in c["video_prompt"], f"E4 {c['card_id']} 音效与 D11 不一致")

    # ---------- F V7 锚点闭合（现读 D10） ----------
    for c in cards:
        decl = c["consistency_refs"]["char_ids"]
        descs = c.get("char_descriptions") or []
        hays = {}
        for cid in decl:
            ck(cid in char_ids, f"F1 {c['card_id']} 角色 {cid} 不在 D04 角色表")
            a = anchors.get(cid)
            ck(a is not None, f"F2 {c['card_id']} D10 无角色锚点 {cid}")
            if a:
                hays[cid] = f"{a['anchor_text']} {' '.join(a['markers'])}"
        # 每条 desc 必须归属于「已声明角色」中的至少一位
        for d in descs:
            ck(any(d in hay or any(m in d for m in anchors[cid]["markers"])
                   for cid, hay in hays.items()),
               f"F3 {c['card_id']} char_descriptions「{d}」未原样出自任何已声明角色的 D10 锚点")
        # 每位已声明角色至少拥有一条匹配的 desc
        for cid, hay in hays.items():
            if not descs:
                continue
            own = [d for d in descs if d in hay or any(m in d for m in anchors[cid]["markers"])]
            ck(bool(own), f"F4 {c['card_id']} 角色 {cid} 没有属于自己的 char_descriptions")

    # ---------- G 轴②：否定/状态必须正面拍出（独立判据） ----------
    # 判据：从 D11 visual_facts 现读否定/状态段，取末句（状态主体）。
    #   G1 末句必须出现在 image_prompt（画面层必须能正面拍出该状态）；
    #      「入画」类属取景规则（镜头约束而非可见状态），允许只在 video。
    #   G2 相反过程词不得出现在任一 prompt（自撰清单）。
    NEGPAT = re.compile(r"没有|未|仍|停住|不|无|最后|只|停")
    if LEGACY_HEADER:
        warns.append("G1/G2 已跳过：旧体例的状态表达方式与本判据集不同（其「只有…和…」类事实以 negatives 表达），"
                     "判据不适用；其余适用判据照常执行")
    OPPOSITE = {
        "最后一栏数字没有合上": ["滚过", "划过", "掠过", "已经合上", "数字合上"],
        "没有人落笔": ["有人落笔", "已签字", "签名已落"],
        "台面上只有这一枚实物": ["第二枚", "多枚", "几枚"],
        "货架全空": ["摆满", "堆满", "货架空置"],
        "刃身收着": ["刃身出鞘", "完全出鞘"],
        "影刃出鞘一半又按了回去": ["完全出鞘", "整柄出鞘"],
        "柜门缝里最后一线冷光收掉": ["冷光仍在", "缝隙透光", "柜缝透光"],
        "退路只剩一条窄道": ["退路宽敞", "多条退路"],
        "两架之间留出一道缺口": ["严丝合缝", "完全封死", "没有缺口"],
        "白烟自下而上散尽": ["浓烟弥漫", "白烟不散"],
        "灰斑退成皮肤本色": ["灰斑仍在", "灰斑不退"],
        "露出完好的皮肤": ["创口", "伤口", "血口"],
        "纹路未向小臂延开": ["骨纹蔓延", "延至小臂", "爬向小臂"],
        "纸面墨迹未干": ["墨迹已干", "字迹干透"],
        "指腹在纹路上停住": ["指腹继续划过", "指腹划过纹路"],
        "周围仍由工业冷光照明": ["暖光照明", "橙色环境光", "暖色照明"],
        "火焰之外的部分仍是厂房冷光": ["整条手臂燃起", "全身燃起", "火势蔓延"],
        "白日忽然转黑，灰雾天幕压到厂房上方": ["天色渐亮", "白日重现", "天幕散开"],
        "队伍被隔成两列": ["队伍排成一列", "队伍散开"],
    }
    for c in cards:
        s = shots[(c["ep"], c["shot_id"])]
        for seg in [x.strip() for x in s["visual_facts"].split("；") if x.strip()]:
            if not NEGPAT.search(seg):
                continue
            core = seg.split("，")[-1].strip()
            if len(core) < 3:
                continue
            if LEGACY_HEADER:
                # 旧体例（U01 由 build_D12_U01.py 产出，已验收）：其「只有…和…」类事实
                # 常以 negatives 表达而非正面散文，本判据集不适用 → 跳过，不产误报。
                continue
            elif "入画" in core:
                ok = core in c["image_prompt"] or core in c["video_prompt"]
            else:
                # 本引擎体例：状态必须落在 image_prompt（首帧即可拍出该状态）——此为引擎级更严标准
                ok = core in c["image_prompt"]
            ck(ok, f"G1 {c['card_id']} D11 否定/状态段末句未在 image_prompt 正面出现：{core[:40]}")
            for bad in OPPOSITE.get(core, []):
                ck(bad not in c["image_prompt"],
                   f"G2 {c['card_id']} image_prompt 出现与状态相反的过程词「{bad}」（{core[:20]}）")
                ck(bad not in c["video_prompt"],
                   f"G2 {c['card_id']} video_prompt 出现与状态相反的过程词「{bad}」（{core[:20]}）")

    # ---------- M 运镜口头化（video_prompt 必须承载镜头运动） ----------
    # 为什么补这道闸（2026-10-23 由 ep016 镜3／C-131 漏写事件驱动）：
    #   卡头里的 movement 字段只声明「这是跟拍/横移镜」，而**驱动图生视频运动的是
    #   video_prompt** —— 运镜不写进 video_prompt，跟拍镜会被渲成固定机位。
    #   D12 侧历来把运镜写进 video_prompt 句首（ep009 镜1「镜头自中远景缓慢推近」／
    #   ep009 镜2「镜头随人物跟进厂门」／ep011 镜2「镜头沿生产线横移」），本判据把该体例机械化。
    # M1：D11 movement ∈ 动态运镜集 → video_prompt 必须含运镜口头化表述。
    # M2：D11 visual_facts **以「镜头」开头**的段（＝镜头级行为）→ 卡的 image+video 必须有一条
    #     **含方向词**的镜头表述。
    #     ⚠️ M2 首版曾有三个设计缺陷，已被 U01 复跑刷出 3 条误报后修掉（敏感度检验 Q67）：
    #       ①「段内含『镜头』」不等于「该段是运镜句」——C-019「面部与身体表面不可辨，镜头不落到
    #         人体细节」是**否定约束**不是运镜句 → 改为**以「镜头」开头**才判；
    #       ② 运镜句不一定落在 video 侧——C-030 的运镜句在 **image** 侧 → 改为查 image+video 拼接串；
    #       ③ 判「逐字」过严——C-012 有术语归一（D11「触角」→ 卡「肢节」）→ 改为**方向词共现**判定。
    # 敏感度检验：U01＋U02 共 12 个动态运镜镜位，U01 7/7 全部口头化、
    #   U02 改前 3/5（缺 ep010 镜1、ep016 镜3）→ 两判据零假阳性且能精确点名漏写镜位。
    DYN_MOVE = ("推", "拉", "摇", "移", "跟", "升", "降")
    DIR_WORDS = ("推", "拉", "摇", "移", "跟", "升", "抬", "降", "压")
    # M1′ 复合运镜值补漏（2026-10-23）：旧判据 `mv in DYN_MOVE` **精确匹配单字值**，
    #   D11 写「升降」「横移」「平移」等复合值时**从不触发** ⇒ 守卫存在≠守卫有效。
    #   实测 U03 C-210（mv=升降）video 无任何运镜口头化，旧判据零告警放行。
    #   同时旧判据只查 CAM_VERB **词面**（含「镜头」二字即算通过）⇒「镜头不动」也算
    #   口头化。两处一并收紧为：**卡内须出现「镜头窗口＋方向词」**。
    #   ⚠️「手持」是**技法**不是方向运镜，且已验收 U01 手持卡的口头化形态是
    #   「机位随…起伏」（非「镜头+方向词」形态）⇒ **不纳入**动态集，
    #   否则对 U01 C-014/C-021/C-022 产假阳性（敏感度检验实测）。
    # M3 固定机位规则（2026-10-23 新增）：D11 movement=固定 的卡，卡内不得出现运镜表述
    #   ——卡头已声明「固定机位」，卡内再写「推近/横移/下压」＝与 D11 自相矛盾。
    #   否定式豁免：「镜头不动/不移动/保持主观视线不移动/固定不动」不算运镜。
    #   ⚠️ 窗口用正则「镜头[^；。，、]{0,14}」而非分句锚定：U01 C-005 的
    #   「人物自画面深处走向镜头再走开」是**主语带镜头**（非镜头句），分句锚定会误判；
    #   窗口+方向词判定对同一句正确判为「无方向词」。
    NEG_CAM = ("不移动", "不动", "不推", "不拉", "不摇", "不移", "不跟", "不升", "不降",
               "不压", "不抬", "固定", "静止", "锁死")

    def _cam_motion(blob):
        """返回卡内「镜头窗口＋方向词」的运镜表述；否定式（不动/不移动/固定…）不算运镜。"""
        out = []
        for m in re.finditer(r"镜头[^；。，、]{0,14}", blob):
            w = m.group(0)
            for n in NEG_CAM:
                w = w.replace(n, "")
            if any(x in w for x in DIR_WORDS):
                out.append(m.group(0))
        return out

    for c in cards:
        s = shots[(c["ep"], c["shot_id"])]
        mv = (s.get("movement") or "").strip()
        vp = c["video_prompt"]
        blob = c["image_prompt"] + " " + vp
        is_dyn = mv in DYN_MOVE or any(ch in mv for ch in DYN_MOVE)
        if is_dyn:
            ck(bool(_cam_motion(vp)),
               f"M1 {c['card_id']} D11 movement=「{mv}」但 video_prompt 未口头化运镜")
        elif mv in ("固定", "固定机位", "静止"):
            bad = _cam_motion(blob)
            ck(not bad, f"M3 {c['card_id']} D11 movement=固定 但卡内出现运镜表述：{bad[0] if bad else ''}")
        blob = c["image_prompt"] + " " + c["video_prompt"]
        card_cam = [m.group(0) for m in re.finditer(r"镜头[^；。，、]{0,14}", blob)]
        for seg in [x.strip().rstrip("。") for x in (s.get("visual_facts") or "").split("；") if x.strip()]:
            if not seg.startswith("镜头"):
                continue
            dirs = {w for w in DIR_WORDS if w in seg}
            if not dirs:
                ck(bool(card_cam),
                   f"M2 {c['card_id']} D11 镜头级句未在卡内承接：{seg[:30]}")
            else:
                ck(any(any(w in cc for w in dirs) for cc in card_cam),
                   f"M2 {c['card_id']} D11 镜头级运镜（{'/'.join(sorted(dirs))}）"
                   f"未在卡内任何镜头表述中出现：{seg[:30]}")

    # ---------- H negatives 质量 ----------
    GORE_MIN = ["gore", "blood", "red liquid", "open wounds", "internal organs",
                "dismembered limbs", "corpse piles", "rotting flesh", "exposed bone", "eyes and eyeballs"]
    CN_FIXED = ("AI 生成角标须常驻", "画面内文字一律中文", "画面内不得出现任何贬称")
    for c in cards:
        negs = c["negatives"]
        for g in GORE_MIN:
            ck(g in negs, f"H1 {c['card_id']} 缺零血腥负向词「{g}」")
        for n in negs:
            if n.startswith(CN_FIXED):
                continue
            ck(all(ord(ch) < 128 for ch in n), f"H2 {c['card_id']} 非固定块的 negative 含非 ASCII：{n[:40]}")
        ck(17 <= len(negs) <= 35, f"H3 {c['card_id']} negatives 条数 {len(negs)} 偏离基线 17~35")
        ck(sum(len(n) for n in negs) <= 700, f"H4 {c['card_id']} negatives 合计超 700 字")
        ck(len(c["image_prompt"]) <= 330 and len(c["video_prompt"]) <= 260,
           f"H5 {c['card_id']} prompt 超体量上限")
        for w in RULES.get("forbidden_words", []):
            ck(w not in c["image_prompt"] and w not in c["video_prompt"],
               f"H6 {c['card_id']} 命中零血腥禁词「{w}」")
        for w in RULES.get("derogatory_terms", []):
            ck(w not in c["image_prompt"] and w not in c["video_prompt"],
               f"H7 {c['card_id']} 命中贬称「{w}」")
        hits = [p for p in pool if p in negs]
        ck(len(hits) >= 10, f"H8 {c['card_id']} 只命中 D10 共享池 {len(hits)} 条，覆盖不足")

    # 共享池整体覆盖：池中「非血腥/非分级语义」条目必须单元级全覆盖
    # （血腥变体由每卡固定的 GORE 块语义覆盖，逐卡全带会使负向列表膨胀、稀释 H3 负向提示）
    allneg = set()
    for c in cards:
        allneg.update(c["negatives"])
    GORE_SEM = re.compile(r"gore|blood|wound|laceration|bone|organ|limb|corpse|flesh|skinned|behead|decap|"
                          r"severed|spatter|fluid|stain|pool|scream|jump|skull|decay|rott|mutilat")
    must = [p for p in pool if not GORE_SEM.search(p)]
    if LEGACY_HEADER:
        # D10 v1.11「共享池下放口径」适用范围条款：自 v1.10 起适用，
        # 此前已验收单元按其验收时的池口径、不回溯要求 → 对旧体例跳过本项。
        warns.append("H9/H9b 已跳过：本单元为 v1.10 前已验收单元，按 D10 v1.11 适用范围条款不回溯要求")
    else:
        uncovered = [p for p in must if p not in allneg]
        ck(not uncovered, f"H9 D10 共享池非血腥条目未被单元覆盖：{uncovered}")
        covered = [p for p in pool if p in allneg]
        ck(len(covered) >= 30, f"H9b D10 共享池整体覆盖 {len(covered)}/46，覆盖不足 30")

    # ---------- I 母题 / 色板 ----------
    for c in cards:
        for m in c["consistency_refs"]["motifs"]:
            ck(m in motifs, f"I1 {c['card_id']} 母题 {m} 不在 D10")
        for p in c["consistency_refs"]["palette"]:
            ck(p in palettes, f"I2 {c['card_id']} 色板 {p} 不在 D10")

    # ---------- J 术语收口（D05 禁用同义词，negatives 豁免） ----------
    banned = sorted({b for g in D05["glossary"] for b in (g.get("forbidden_synonyms") or [])})
    exempt = set(RULES.get("term_scan_exempt", {}).get("D12", []))
    scan = []
    for c in cards:
        scan.append(c["image_prompt"])
        scan.append(c["video_prompt"])
        scan.append(json.dumps(c["params"], ensure_ascii=False))
        scan.append(json.dumps(c["consistency_refs"], ensure_ascii=False))
        scan.extend(c.get("char_descriptions") or [])
    joined = "\n".join(scan)
    hits = sorted({w for w in banned if w in joined})
    ck(not hits, f"J1 D12 正文命中 D05 禁用同义词：{hits}")
    neg_join = "\n".join(n for c in cards for n in c["negatives"])
    if "cards[].negatives" not in exempt:
        hits2 = sorted({w for w in banned if w in neg_join})
        ck(not hits2, f"J2 negatives 命中 D05 禁用同义词：{hits2}")

    # ---------- 汇总 ----------
    print(f"独立复核（{unit}）：受检断言 {checks} 条｜error {len(errs)}｜warning {len(warns)}")
    for e in errs[:40]:
        print("   ❌", e)
    if len(errs) > 40:
        print(f"   …另有 {len(errs)-40} 条")
    for w in warns:
        print("   !", w)
    return 1 if errs else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default="U02", help="单元号，如 U01 / U02（默认 U02）")
    ap.add_argument("--inject", default=None,
                    help="负测：注入一条故障以证明断言非恒真（header/axis2/negcn/fire/move/m1c/m3）")
    a = ap.parse_args()
    sys.exit(main(a.unit.upper(), a.inject))
