#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U01 单元 · D12 AI 提示词卡库 · 生成脚本

- 真源：本脚本 → units/U01/D12.json（JSON 唯一真源；MD 由 04_工具/render-md.mjs 单向渲染）
- 上游只读：shared/D10.json（锚点/母题/色板）、shared/D04.json、units/U01/D11.json（32 镜）、units/U01/D08.json
- 一镜一卡：U01 32 镜 → 32 张卡，每卡同时含 image_prompt 与 video_prompt（D12 schema 两项均为必填）
- 内建自检：JSON 合法性 / V7 锚点闭合 / V5 禁用同义词 / D11 镜号引用 / 母题与色板存在性
- 重建脚本即 SSOT：status 固定 in_review，重跑不会把状态打回 draft
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
SHARED = os.path.join(PROJ, "shared")
UNIT = os.path.join(PROJ, "units", "U01")
OUT = os.path.join(UNIT, "D12.json")

D10 = json.load(open(os.path.join(SHARED, "D10.json"), encoding="utf-8"))
D05 = json.load(open(os.path.join(SHARED, "D05.json"), encoding="utf-8"))
D11 = json.load(open(os.path.join(UNIT, "D11.json"), encoding="utf-8"))
RULES = json.load(open(os.path.abspath(os.path.join(HERE, "..", "..", "..", "03_规格", "rules.json")), encoding="utf-8"))

ANCHORS = {a["char_id"]: a for a in D10["character_anchors"]}
MOTIFS = {m["motif_id"] for m in D10["motifs"]}
PALETTE = {p["name"] for p in D10["palette"]}
SHOT_KEYS = {(e["ep"], s["shot_id"]) for e in D11["episodes"] for s in e["shots"]}
BANNED = sorted({b for g in D05["glossary"] for b in (g.get("forbidden_synonyms") or [])})

# ---------------------------------------------------------------- 固定块

STYLE = "写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
BADGE_POS = "右下角 72%~78% 画面高度留净空供 AI 生成角标，底部 15% 留字幕带，主体居中偏上、头顶留白 8%。"
BADGE_NEG = (
    "AI 生成角标须常驻：基线落在画面高 72%~78%、右对齐、距画面右缘 ≥6% 画面宽、"
    "字号 ≥画面高 1.5%、不透明度 ≥50%，黑场镜亦保留，角标文字「AI 生成」，"
    "不得被主体、字幕或特效遮挡、裁切或变形"
)
TEXT_NEG = "画面内文字一律中文并逐字可读；出现外文或字母缩写时同屏必须配中文；不得出现乱码字形"

GORE = ["gore", "blood", "blood splatter", "red liquid", "open wounds", "internal organs",
        "dismembered limbs", "corpse piles", "rotting flesh", "exposed bone", "eyes and eyeballs"]
RELIG = ["religious iconography", "crosses and crucifixes", "halos", "rosaries and prayer beads",
         "altars", "ritual robes and priestly vestments", "prayer gestures", "chanting", "sacred statuary"]
REAL = ["real-world national flags", "real-world country emblems", "real corporate logos",
        "real-world military insignia", "real-world currency symbols", "real-world ethnic or religious dress",
        "recognizable real-world landmark"]
CREATURE = ["photorealistic flesh decay", "realistic animal anatomy for creatures", "facial features on creatures",
             "skin and muscle detail on creatures", "creature eyes", "insect mandibles biting"]
FLAME = ["third flame color", "red flame", "orange flame", "multi-colored fire", "any fire color other than black and white"]
UI = ["garbled text", "fake random glyphs", "English-only text", "red alert overlay", "handwritten text on the interface"]


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


MODEL = "H3（图生视频；首帧＝本卡 image_prompt 产出图）"
SEED_ROLE = {"LC": "110101", "YHY": "110201", "YJ-ES": "110301"}
SEED_SCENE = {"A-1": "110401", "A-2": "110402", "A-3": "110403", "A-4": "110404", "A-5": "110405",
              "A-6": "110406", "A-7": "110407", "A-8": "110408", "A-9": "110409"}
SEED_UI = "110501"

# 「面板与界面域 seed」显式白名单（v1.7 起）
# ⚠️ 此前用 `("面板" in image or "播报栏" in image)` 自动判定 → 「黄金 3 秒改造」给 C-003 的
#    image 追加了「视野下缘浮出面板」一行后，C-003 被**误判**为 UI 卡、seed 策略多出
#    「面板与界面域 seed 110501」→ 与改造基线（v1.6）字节不一致。
#    基线是权威：C-003 画面虽含底缘面板字，但 seed 策略**保持原样（无 UI 域）**。
#    ⇒ 改为显式白名单，新增/改写文案不再自动改 seed 策略。
SEED_UI_CARDS = {"C-001", "C-002", "C-010", "C-015", "C-016", "C-032"}


def params(scene, dur, chars, steps=30, ui=False):
    parts = []
    if chars:
        parts.append("角色域 seed 固定 " + "／".join(f"{c}:{SEED_ROLE[c]}" for c in chars))
    else:
        parts.append("无角色域 seed")
    parts.append(f"场景光效域 seed {SEED_SCENE[scene]}")
    if ui:
        parts.append(f"面板与界面域 seed {SEED_UI}")
    parts.append("同角色跨集复用同一 seed 家族；换 seed 必须重述全部锚点句")
    return {
        "model": MODEL,
        "aspect": "9:16",
        "seed_strategy": "；".join(parts),
        "steps": steps,
        "guidance": 6.5,
        "duration_sec": dur,
    }


# ---------------------------------------------------------------- 32 镜卡数据
# (ep, shot_id, scene, dur, steps, chars, descs, motifs, palette, image, video, negatives)

CARDS = [
    # ============================ ep001 ============================
    (1, 1, "A-1", 13, 30, ["LC"], ["剑眉冷目", "利落短发"], [], ["灰雾青灰", "墨灰暗部"],
     "中景，平视，35mm，9:16 竖屏。单间出租屋：床、衣柜、堆到天花板的纸箱、一扇窗；冷白灯管是室内唯一光源。利落短发的青年抬起右手腕占住画面前景，指腹用力按在腕侧骨纹上，青筋暴起；腕侧皮肤上有一道极淡的黑白游龙纹，像旧印，**纹路不发光**、纹路周围无任何光晕或读数；背景是翻倒的椅子、散落的工具、熄灭的屏幕；房门虚掩，门缝下透进一道红光；视野正中浮出灰框面板，栏目自上而下逐格亮起，中央倒计时数字跳动，面板顶部同屏中文「距灰潮试炼降临 2 小时 58 分」。" + BADGE_POS + STYLE,
     "13 秒单镜：镜头自中景极缓推进，人物抬腕后用指腹按住腕侧骨纹，按压处青筋暴起，而皮肤上那道极淡的黑白游龙纹全程**不发光**、不变形、不出现读数；人物只做抬腕、指腹按压、眨眼与呼吸四组小幅动作；面板在视野正中逐格亮起，倒计时数字跳动后落定，顶部中文「距灰潮试炼降临 2 小时 58 分」始终可读；不做大幅肢体动作，不做贴脸；右下角 AI 生成角标常驻不遮挡。",
     negs(GORE, extra=["no other people in the room", "no daylight", "no warm sunlight", "no clutter of readable documents"])),

    (1, 2, "A-1", 13, 30, [], [], [], ["灰雾青灰", "云顶冷白", "墨灰暗部"],
     "特写，平视，50mm，9:16 竖屏。半透明灰框面板占满画面，四角有细刻度线，灰框冷白发光，底部滚动播报栏持续上滚；面板顶部同屏中文「归档回滚完成。」；面板中央倒计时读数为同屏中文「距灰潮试炼降临 2 小时 58 分」；面板角落一行同屏中文「上一趟存活 3 小时 04 分」。只给数据界面，画面内不出现人体、面孔与手。" + BADGE_POS + STYLE,
     "13 秒单镜：镜头极缓推近面板；播报栏持续上滚；顶部中文「归档回滚完成。」、中央读数「距灰潮试炼降临 2 小时 58 分」、角落一行「上一趟存活 3 小时 04 分」三处文字保持可读；界面发光轻微呼吸，不做闪烁抖动；画面不出现任何人体。",
     negs(UI, GORE, extra=["no human body in frame", "no face", "no hands", "no bed", "no room interior"])),

    (1, 3, "A-1", 12, 30, ["LC"], ["利落短发"], [], ["灰雾青灰", "墨灰暗部"],
     "中景，平视，35mm 横向平移，9:16 竖屏。出租屋：利落短发的青年掀翻储物箱，把压缩饼干倒在地上，只抓出一柄半米长的实心重钢钎；工具箱敞口处只有一把扳手和半卷胶布，他迅速用胶布将钢钎死死捆在右腕骨纹之上；他侧身发力，站起时膝软、一只手死死撑住墙面、指节发白；房门被拉开，楼道感应灯逐层亮起，灯色全是红的；视野下缘浮出面板，面板底部一行红字同屏中文「比上一趟少 6 分钟」。" + BADGE_POS + STYLE,
     "12 秒单镜：镜头横向平移跟住倒饼干动作，储物箱被掀翻、压缩饼干倒在地上，人物只抓出一柄半米长的实心重钢钎；手部取半卷胶布把钢钎死死捆在右腕骨纹之上；人物站起时膝盖一软、一只手扶墙借力、指节发白；房门拉开，门外楼道感应灯逐层亮起且灯色全为红；面板底部红字「比上一趟少 6 分钟」保持可读。动作连贯、幅度克制，箱体与手部不出现破损或污渍；右下角 AI 生成角标常驻。",
     negs(GORE, extra=["no other people", "no weapon raised", "no visible wounds", "no daylight"])),

    (1, 4, "A-1", 7, 30, ["LC"], ["利落短发"], [], ["灰雾青灰", "墨灰暗部", "骨白"],
     "全景，客观跟拍，24mm，9:16 竖屏。狭窄楼道与转角应急灯：人物夺门而出、翻过楼道扶手纵身下跃，楼道感应灯在他身后一盏盏由红转绿；感应灯逐层亮起形成向上的光带，人影在转角处远去；窗外是城市夜色，楼道只作运动通道、不建立完整场景。冷青灰夜景，暗部保留细节。" + BADGE_POS + STYLE,
     "7 秒单镜：跟拍人物夺门而出、翻过楼道扶手纵身下跃，感应灯在身后一盏盏由红转绿、随经过逐层亮起形成向上的光带，脚步声由近及远；镜头保持客观跟拍、不追进转角，人物在转角处远去；不出现其他住户与日光；右下角 AI 生成角标常驻。",
     negs(GORE, extra=["no other residents", "no daylight", "no warm hallway light", "no crowd"])),

    # ============================ ep002 ============================
    (2, 1, "A-2", 13, 30, ["LC"], ["利落短发", "黑色战术风衣"], [], ["灰雾青灰", "墨灰暗部", "石膏灰白"],
     "中远景，平视，35mm 固定机位，9:16 竖屏。暴雨夜的废弃军工机械厂大门外，卷帘门底槽被实心重钢钎顶起一人宽缝隙，门轴酸涩长响；门缝里露出厂房内部锈蚀车床与钢架的轮廓。黑色战术风衣的青年提着两桶净水敏捷侧身滑入厂房内部，反手把两桶水按在门后墙根码齐；工业冷光自高位钢架灯带落下，湿地面反着冷光，阴影边缘锐利。" + BADGE_POS + STYLE,
     "13 秒固定机位单镜：卷帘门底槽被实心重钢钎顶起一人宽缝隙，门轴酸涩长响；人物提着两桶净水敏捷侧身滑入厂房内部，反手把两桶水按在门后墙根码齐。全程机位不动；暴雨在厂区外落幕，湿地面反光；无其他人物与车辆。",
     negs(GORE, extra=["no forklift", "no other workers", "no daylight", "no green vegetation", "no warm sunlight", "no readable brand marks"])),

    (2, 2, "A-2", 15, 32, ["LC"], ["黑色战术风衣", "利落短发"], [], ["灰雾青灰", "墨灰暗部", "薪火橙"],
     "中景，平视，50mm 固定机位，9:16 竖屏。大跨厂房内侧，卷帘门彻底轰然下坠锁死；侧门内侧焊起简易闸门，焊花瞬时溅落卷帘门、仅在接触处留下局部暖色亮点（取色板 薪火橙）；焊接弧光是画面里唯一的暖源，周围仍由工业冷光照明，场景整体保持工业冷光、不做整体暖调偏移；黑色战术风衣的青年把钢架横推到窗下、架面留出射击口，半箱压缩饼干与工具箱扣实封好；厂房底部的检修铁闸被他单手拉开，身形敏捷钻入通往后山的地下排渣管廊。工业冷光与灰白钢构质感。" + BADGE_POS + STYLE,
     "15 秒固定机位单镜：卷帘门彻底轰然下坠锁死，焊接弧光短促爆响，焊花瞬时溅落卷帘门并只留局部暖色亮点（取色板 薪火橙），闸门焊缝逐渐成形；暖色不形成持续主光，周围仍工业冷光；人物把钢架横推到窗下、架面留出射击口，随后把半箱压缩饼干与工具箱扣实封好；末段他单手拉开厂房底部的检修铁闸，身形敏捷钻入通往后山的地下排渣管廊；镜头不动，不给面部特写。",
     negs(GORE, RELIG, extra=["no fire beyond the welding arc", "no warm ambient color grading", "no orange glow filling the frame",
                              "no sparks showering onto the character", "no other people", "no daylight"])),

    (2, 3, "A-3", 12, 30, ["LC"], ["黑色战术风衣"], [], ["灰雾青灰", "墨灰暗部", "石膏灰白"],
     "中远景，客观跟拍，24mm，9:16 竖屏。归废处置线外圈：黑色战术风衣的青年推开管廊尽头的排气栅栏翻出暗道，贴着钢板围栏疾行；推土机与高压指示屏沿视线排开，远处是深坑边缘；工业冷光下金属表面反射冷灰。他在排渣闸口与管廊暗扣处停步丈量记下，鞋底带起碎石。画面内严守底线绝不呈现坑内作业与人体。" + BADGE_POS + STYLE,
     "12 秒跟拍单镜：镜头随人物沿钢板围栏平行移动，人物自管廊尽头的排气栅栏翻出暗道后贴着钢板围栏疾行，边走边观察，在排渣闸口与管廊暗扣处停步、丈量记下，随后继续前行；鞋底与碎石互动清晰。始终不越过围栏、不俯视坑内、不出现任何作业人员。",
     negs(GORE, extra=["no workers in frame", "no pit interior", "no human bodies", "no visible wounds", "no fire", "no smoke"])),

    (2, 4, "A-3", 5, 30, ["LC"], ["黑色战术风衣"], [], ["灰雾青灰", "墨灰暗部"],
     "远景，仰视，24mm 固定机位，9:16 竖屏。夜色天幕为冷青灰，城市钟楼轮廓立在远处天幕下，压迫感由仰视构图给出；黑色战术风衣的青年顺着检修铁梯登上天台制高点，抬腕看表，腕表面在夜色里亮起微冷光；空场留白承载钟声。画面不拍人物痛苦表情，不给面部特写。底部字幕「全城钟楼敲响十一下。」" + BADGE_POS + STYLE,
     "5 秒固定仰视单镜：钟楼轮廓静立冷青灰天幕下，人物顺着检修铁梯登上天台制高点后在画面下缘抬腕看表，腕表面亮起微冷光；镜头保持不动、不推近面部；钟声由远及近再散开。",
     negs(GORE, extra=["no close-up of the clock face", "no daylight", "no warm sky", "no crowd", "no facial expression"])),

    # ============================ ep003 ============================
    (3, 1, "A-4", 12, 30, [], [], [], ["灰雾青灰", "墨灰暗部"],
     "远景，俯视，24mm 固定机位，9:16 竖屏。厂区地缝冒出青灰双生雾气，贴着地面向四周铺开；天幕被灰雾压过，路灯只剩一圈圈散光；雾气整体向画面外推进，机位不动。灰雾为青灰双色半透明介质，无红色、无火光。" + BADGE_POS + STYLE,
     "12 秒固定俯视单镜：地缝持续涌出青灰双生雾气，贴地铺开并向画面外推进，路灯光圈被雾气吞没成散光；机位完全不动，让雾体自身运动；不出现人物、异化体与火光。",
     negs(GORE, extra=["no red fog", "no orange glow", "no fire", "no creatures in frame", "no horizon glow", "no warm light"])),

    (3, 2, "A-4", 12, 30, [], [], [], ["灰雾青灰", "云顶冷白"],
     "特写，主观视角，50mm 固定机位，9:16 竖屏。半透明灰框面板浮在视野正中，灰框冷白发光，底部滚动播报栏持续上滚；面板顶部同屏中文「等级 LV.1（一阶）」，其下同屏中文「新手福利期 9 小时」；面板四维数值同时浮现并依次跳动。只给数据界面，画面内不出现人体。" + BADGE_POS + STYLE,
     "12 秒固定单镜：面板播报栏持续上滚，顶部「等级 LV.1（一阶）」与「新手福利期 9 小时」保持可读，四维数值依次跳动归位；面板随呼吸轻微浮动，不做旋转与位移；画面不出现人体。",
     negs(UI, GORE, extra=["no human body in frame", "no hands", "no red UI theme"])),

    (3, 3, "A-4", 12, 32, ["LC"], ["右手腕黑白游龙骨纹", "双相净火(黑白火焰)"], ["M01", "M02"],
     ["净火白", "净火黑", "灰雾青灰", "墨灰暗部"],
     "近景，主观视角，85mm 固定机位，9:16 竖屏。右腕特写：皮肤表面第一次亮起一道黑白游龙纹，纹路由腕侧向手背延开，只贴在皮肤表面，纹路下方皮肤完好无破口；腕侧燃起黑白双焰，黑焰在内、白焰在外，沿掌缘翻卷，夜风把火焰吹偏一侧。火焰只有黑与白两色，不出现第三种颜色。视野一角读数栏为同屏中文「归一度 0.5%」。" + BADGE_POS + STYLE,
     "12 秒固定单镜：黑白游龙纹自腕侧向手背缓慢延开并稳定，纹路贴附皮肤表面不破体；黑白双焰沿掌缘翻卷、被夜风带向一侧，火焰不换色、不分裂成第三色；读数栏保持「归一度 0.5%」可读；镜头不移动。",
     negs(GORE, FLAME, CREATURE, extra=["no skin breakage", "no bone protruding through skin", "no tattoo-like flat art",
                                        "no ink on the wrist", "no blood"])),

    (3, 4, "A-4", 9, 32, [], [], ["M14"], ["石膏灰白", "灰雾青灰", "墨灰暗部"],
     "中景，俯视，35mm，9:16 竖屏。厂区水泥地面被顶开一道直径约半米的裂缝，灰白石膏质感的多节几何肢节自裂口中顶出，碎屑弹起；节段为抽象几何、无五官、不取现实动物形态、无人体内部结构。镜头随肢节抬升而下压，最后落在裂缝边缘。工业冷光，无红色、无火光。" + BADGE_POS + STYLE,
     "9 秒单镜：镜头自中景随肢节抬升缓慢下压并落向裂缝边缘；多节几何肢节一节一节顶出裂口，节段间开合有节律，碎屑弹起后落回地面；外壳始终为灰白石膏质感、无五官、无人体内部结构；不出现人物。",
     negs(GORE, CREATURE, FLAME, extra=["no realistic insect anatomy", "no eyes on the creature", "no gore", "no blood", "no fire", "no warm light"])),

    # ============================ ep004 ============================
    (4, 1, "A-5", 12, 30, ["LC"], ["黑色战术风衣", "利落短发"], ["M14"], ["石膏灰白", "灰雾青灰", "墨灰暗部"],
     "中景，客观跟拍，35mm，9:16 竖屏。机械厂战斗区：灰白石膏质感的多节几何肢节自破口抽出，卷起碎石抽打，地面被拉出一道长沟；黑色战术风衣的青年侧身避开肢节、反手握住改装重钢钎，风衣下摆在抽打的气流里翻起；碎屑弹起。地面积水反冷光，画面不出现人体内部结构。" + BADGE_POS + STYLE,
     "12 秒跟拍单镜：几何肢节自破口抽出抽打地面、卷起碎石，镜头平行跟住人物侧移避让并反手握住改装重钢钎，风衣下摆被气流掀起；动作节奏短促有力，肢节与人物不接触、不出现伤害细节；右下角 AI 生成角标常驻。",
     negs(GORE, CREATURE, extra=["no blood", "no gore", "no creature eyes", "no realistic insect anatomy", "no crowd", "no warm light"])),

    (4, 2, "A-5", 12, 32, ["LC"], ["右手腕黑白游龙骨纹", "利落短发"], ["M14"], ["石膏灰白", "墨灰暗部"],
     "特写，俯视，85mm 手持轻微晃动，9:16 竖屏。改装重钢钎的钎身与灰白石膏质感的多节几何肢节相交：第一次接触溅出金属火星，第二次接触肢节尖端断开并落在水泥地上，第三次接触整根垂落。画面只拍手部、钎身与壳体，接触点之外无任何创口；壳体无五官、无人体内部结构。" + BADGE_POS + STYLE,
     "12 秒手持有界单镜：钎身与几何肢节三次交击，每次接触迸出金属火星，肢节自尖端依次断开并垂落至水泥地；镜头只跟随手部与钎身，交击点不出现人体伤害、不出现红色液体；手持晃动幅度小。",
     negs(GORE, CREATURE, extra=["no blood on the hand", "no skin puncture", "no face", "no realistic insect anatomy",
                                 "no sparks on skin", "no gore"])),

    (4, 3, "A-5", 12, 32, ["LC"], ["右手腕黑白游龙骨纹"], ["M02", "M09"], ["石膏灰白", "净火白", "墨灰暗部"],
     "中景，平视，50mm 固定机位，9:16 竖屏。几何肢节虫体自接触点整体溃散为灰烬光尘，灰烬悬在半空缓落，无碎块、无人体内部结构；一枚雾核自灰烬中浮起，呈冷白粒状微光（取色板 净火白，不作金色），贴着掌心没入；视野中的面板四维读数同时暴涨、右腕骨纹进度条推进一格，骨纹仍贴附皮肤表面；面板一角读数栏为同屏中文「归一度 0.5%」。" + BADGE_POS + STYLE,
     "12 秒固定单镜：几何肢节整体化为灰烬光尘并缓落，雾核以冷白粒状微光自灰烬中浮起、贴着掌心没入；面板四维读数逐项跳升、右腕骨纹进度条推过一格（贴合皮肤表面、不破体）；读数栏保持「归一度 0.5%」；镜头不动。",
     negs(GORE, CREATURE, UI, extra=["no body fragments", "no flesh chunks", "no red glow", "no golden glow",
                                     "no photorealistic decay", "no red liquid"])),

    (4, 4, "A-5", 9, 30, [], [], [], ["灰雾青灰", "墨灰暗部", "云顶冷白"],
     "中景，主观视角，50mm 固定机位，9:16 竖屏。面板底部滚出全区首杀通报条，同屏中文「全区首杀」，角色名置顶；面板一角读数栏为同屏中文「归一度 0.5%」；厂区窗外的车灯扫进窗框，围栏外停着一排装甲车，车体只以轮廓与车灯存在、不显形。画面内不出现人体面孔。" + BADGE_POS + STYLE,
     "9 秒固定单镜：面板底部通报条自下滚出，「全区首杀」与角色名保持可读，读数栏维持「归一度 0.5%」；窗外车灯缓慢扫过窗框，围栏外车列只作光斑与轮廓，不推进、不显形；画面不出现人体。",
     negs(UI, GORE, REAL, extra=["no armored vehicle detail", "no vehicle plate", "no soldier close-up", "no gore"])),

    # ============================ ep005 ============================
    (5, 1, "A-6", 12, 30, [], [], [], ["灰雾青灰", "墨灰暗部"],
     "中远景，平视，35mm 固定机位，9:16 竖屏。归废处置线：装甲车灯扫过钢板围栏，护卫队押着一列队列走进厂区；钢板围栏与推土机的深色轮廓在工业冷光里显形；队列末端几人的手臂上覆着灰白斑块、走路时手臂僵直。队列全程远景，不出现任何单人面部特写、不给人体细节。" + BADGE_POS + STYLE,
     "12 秒固定机位单镜：装甲车灯自画面一侧扫过钢板围栏，队列在护卫队押送下自远处走进厂区，末端几人手臂僵直；队列始终保持远景与遮挡，面部不入镜、不给特写；镜头不动。",
     negs(GORE, REAL, extra=["no close-up of any face", "no visible wounds", "no detail on arms or skin",
                             "no crowd close-up", "no blood"])),

    (5, 2, "A-6", 13, 30, ["YJ-ES"], ["象牙白短外套与黑色硬质肩章", "右手灰色薄手套，腕口两道黑线"], [], ["云顶冷白", "墨灰暗部", "骨白"],
     "近景，过肩，50mm 固定机位，9:16 竖屏。过肩看向长方形审批终端：终端外壳亮着一枚红色拒绝键，屏幕亮起一列编号，最后一行被红色拒绝键压住，屏幕文字全部中文；叶承钧站在终端前，象牙白短外套配黑色硬质肩章、领口扣齐，右手灰色薄手套搭在台沿，左眼一片银框单片信息镜反着冷光。工业冷光。" + BADGE_POS + STYLE,
     "13 秒固定单镜：终端屏幕文字逐行亮起，最后一行被红色拒绝键压住并保持常亮；戴灰色薄手套的手在台沿轻敲一次后停住，肩线不动、领口始终扣齐；镜头不动，不给正面特写；右下角 AI 生成角标常驻。",
     negs(UI, GORE, RELIG, extra=["no weapon aimed at anyone", "no real corporate logos", "no gore", "no blood"])),

    (5, 3, "A-6", 12, 30, ["YHY"], ["暗红衣"], [], ["骨白", "灰雾青灰", "墨灰暗部"],
     "远景，平视，35mm 固定机位，9:16 竖屏。归废处置线处置台：处置台在远景里亮起一圈白灯，处置区只余被处置者的剪影，轮廓被白灯边缘光勾出，剪影是被束具缚住的形状；剪影周身覆着一层霜白，霜白自肩部向下漫开、边缘浮起一层冷白雾气，在远景里成块可辨；霜白里不见斑痕形状，霜白只作轮廓上的成块色块；面部与身体表面不可辨，镜头不落到人体细节；处置区之外是钢板围栏与推土机的深色轮廓。工业冷光加白灯边缘光，无红色。" + BADGE_POS + STYLE,
     "12 秒固定单镜：白灯圈在远景中常亮并轻微起伏，被处置者的剪影在光圈边缘缓慢移动，剪影周身覆着一层霜白、霜白自肩部向下漫开，在远景里成块可辨，镜头始终保持远景与遮挡；不推近、不落到人体细节、不给面部；白灯不转为暖色。",
     negs(GORE, RELIG, extra=["no body details", "no face", "no visible wounds", "no blood", "no fire", "no burning, no smoke", "no visible skin texture",
                              "frost-layer cold white mist preserved", "no warm tint on the work lamp"])),

    (5, 4, "A-6", 8, 30, ["YJ-ES"], ["象牙白短外套与黑色硬质肩章", "左眼银框单片信息镜"], [], ["云顶冷白", "墨灰暗部", "骨白"],
     "近景，主观视角，85mm 固定机位，9:16 竖屏。视线穿过厂房阴影的深色边缘，落在大跨度厂区里终端前的那张侧脸：象牙白短外套领口扣齐，左眼一片银框单片信息镜反着冷光；画面暗处有一只手握住钢钎，指节收紧。冲击由声音承担，不拍痛苦表情、不贴脸。工业冷光。" + BADGE_POS + STYLE,
     "8 秒固定单镜：镜头保持主观视线不移动，终端前的侧脸在冷光中一动不动，信息镜反光一闪即收；暗处握钎的手指节缓慢收紧；不推近、不给正面、不出现任何伤害细节。",
     negs(GORE, extra=["no frontal portrait", "no blood", "no weapon in frame", "no crowd", "no warm light"])),

    # ============================ ep006 ============================
    (6, 1, "A-7", 11, 30, ["LC"], ["黑色战术风衣"], [], ["墨灰暗部", "灰雾青灰"],
     "中景，平视，35mm 手持轻微晃动，9:16 竖屏。厂房暗处：一道剪影暴起冲出，黑色战术风衣下摆甩开；重钢钎拖过水泥地划出一道金属火星；机位随冲势起伏但不贴近人物面部。工业冷光，画面不出现创口与红色。" + BADGE_POS + STYLE,
     "11 秒手持单镜：剪影自厂房暗处暴起冲出、风衣下摆甩开，重钢钎拖地划出金属火星；机位随冲势起伏但不贴近面部、不给特写；火星只落在地面，不溅到人身。",
     negs(GORE, extra=["no sparks on skin", "no visible wounds", "no crowd", "no warm light", "no gore"])),

    (6, 2, "A-7", 13, 30, ["LC"], ["黑色战术风衣"], [], ["灰雾青灰", "墨灰暗部"],
     "中景，平视，35mm 手持轻微晃动，9:16 竖屏。一击震退：一名无名护卫队员向后滑出半米、单膝落地，护具与地面擦出一道灰痕；重钢钎被横扫脱手、落在水泥地上弹起。画面不呈现任何伤害细节，不见创口、不见红色，队员面部不入镜。工业冷光。" + BADGE_POS + STYLE,
     "13 秒手持单镜：一击震退使护卫队员向后滑出半米、单膝落地并在地面擦出灰痕，重钢钎脱手落地弹起后静止；机位随动势轻微起伏，不给面部、不给伤害细节；画面无红色液体。",
     negs(GORE, extra=["no injury detail", "no bruise", "no broken limb", "no weapon piercing flesh", "no gore", "no face"])),

    (6, 3, "A-7", 13, 30, ["LC", "YJ-ES"], ["右手腕黑白游龙骨纹", "象牙白短外套与黑色硬质肩章", "左眼银框单片信息镜"], [],
     ["云顶冷白", "骨白", "墨灰暗部"],
     "中景，平视，50mm 固定机位，9:16 竖屏。推土机侧板前：改装重钢钎的钎身横甩出去，贯穿叶承钧身侧的钢板并把他固定在推土机钢板上，钎身与人身之间没有穿透；叶承钧的象牙白短外套领口仍扣齐，左眼银框单片信息镜仍亮着；审批终端的红灯连闪、警报条已经发出。打击只落在钎身、钢板与束具扣上。" + BADGE_POS + STYLE,
     "13 秒固定单镜：钎身横甩出去、贯穿身侧钢板并把他固定在推土机侧板上，钎身与人身之间始终无穿透；终端红灯连闪、警报条保持；人物只有呼吸与眼神变化，不做挣扎；画面无创口、无红色液体。",
     negs(GORE, UI, extra=["no penetration of the body", "no wound", "no broken bone", "no red liquid", "no gore",
                           "no impact on skin"])),

    (6, 4, "A-7", 8, 30, ["LC", "YHY"], ["黑色战术风衣", "暗红衣"], [], ["暗红", "墨灰暗部", "灰雾青灰"],
     "中景，俯视，35mm 升降，9:16 竖屏。处置台边沿：陆沉用钎身砸在叶红衣腕上的束具扣上，扣件弹开；暗红色劲装的小臂从束具里抽出，灰斑沿小臂爬到中段，以表皮色块形态呈现、无创口无创面；陆沉翻身跃下处置台深坑，落地时单手撑地。工业冷光，无红色液体。" + BADGE_POS + STYLE,
     "8 秒升降单镜：钎身砸中束具扣、扣件弹开，小臂自束具中抽出，灰斑沿小臂向上爬行（只作表皮色块推进，无创面细节）；陆沉翻身跃下处置台边沿、落地单手撑地；镜头随动作短促升降，不落进坑内。",
     negs(GORE, extra=["no blood", "no wound", "no visible skin lesion detail", "no red liquid", "no gore",
                       "no deep pit interior", "no burning"])),

    # ============================ ep007 ============================
    (7, 1, "A-8", 12, 30, ["LC", "YHY"], ["黑色战术风衣", "暗红衣"], ["M01"], ["净火白", "净火黑", "灰雾青灰", "墨灰暗部"],
     "中景，平视，35mm 跟拍，9:16 竖屏。归废处置线处置台：陆沉从深坑底落地，沿处置台侧壁走到叶红衣面前；叶红衣抬头、右手撑地要起身，灰白斑块沿小臂扩了一圈；黑白双焰的余光把两人的轮廓边缘勾亮，火焰只有黑与白两色。工业冷光加双焰边缘光，无红色。" + BADGE_POS + STYLE,
     "12 秒跟拍单镜：镜头随人物自深坑底向上跟行，他沿处置台侧壁走到叶红衣面前停住；叶红衣抬头、右手撑地欲起身，斑块边缘再扩一圈；黑白双焰余光在两人轮廓上跳动，火焰不换色。",
     negs(GORE, FLAME, extra=["no visible wound", "no red flame", "no third flame color", "no crowd", "no warm ambient light"])),

    (7, 2, "A-8", 13, 32, ["LC", "YHY"], ["右手腕黑白游龙骨纹", "双相净火(黑白火焰)", "暗红衣"], ["M01"],
     ["净火白", "净火黑", "骨白", "墨灰暗部"],
     "近景，平视，85mm 固定机位，9:16 竖屏。右手腕贴近小臂：黑白双焰贴上皮肤表面，灰斑边缘泛起白烟，白烟自下而上散尽；霜灰褪去后露出的皮肤完好如初，无创口、无创面、无红色液体。火焰只有黑与白两色，白烟为冷白半透明。" + BADGE_POS + STYLE,
     "13 秒固定单镜：黑白双焰贴住小臂表面并沿皮肤推移，灰斑边缘泛起白烟并自下而上散尽；霜灰褪去后露出完好皮肤，全程不出现创面与红色；火焰不换色、不分裂，白烟上升方向恒定向上。",
     negs(GORE, FLAME, extra=["no burn wound", "no blister", "no charred skin", "no red flame", "no flesh damage", "no warm flame"])),

    (7, 3, "A-8", 12, 32, ["LC"], ["右手腕黑白游龙骨纹"], ["M02"], ["净火白", "净火黑", "墨灰暗部"],
     "近景，主观视角，85mm 固定机位，9:16 竖屏。白烟中的规则余烬回流入右腕，腕侧黑白游龙纹的进度条被推过一格，黑白两色更亮，纹路向小臂延伸半寸并只贴在皮肤表面、不破体、不见皮下骨骼；视野一角读数栏仍停在同屏中文「归一度 0.5%」。工业冷光加纹路自发光。" + BADGE_POS + STYLE,
     "12 秒固定单镜：灰白余烬自白烟中回流向右腕，骨纹进度条推过一格，黑白两色亮度提升，纹路向小臂延伸半寸后停住（贴合皮肤表面、不破体）；读数栏保持「归一度 0.5%」不变；镜头不移动。",
     negs(GORE, FLAME, extra=["no skin puncture", "no blood", "no red flame", "no third flame color", "no tattoo",
                              "no bone under the skin"])),

    (7, 4, "A-8", 8, 30, ["LC", "YHY"], ["黑色战术风衣", "影刃", "暗红衣"], [], ["暗红", "墨灰暗部", "骨白"],
     "中景，平视，50mm 固定机位，9:16 竖屏。叶红衣的小臂恢复成正常肤色，她握紧随身影刃站起、站到陆沉侧后方半步，影刃收在身侧不显刃光；陆沉侧身让出半步。工业冷光，画面无创口与红色。" + BADGE_POS + STYLE,
     "8 秒固定单镜：叶红衣小臂肤色恢复，她握紧影刃起身、走到陆沉侧后方半步站定，刃身始终收着不显刃光；陆沉侧身让出半步，两人同时停住；镜头不动。",
     negs(GORE, FLAME, extra=["no blood", "no gore", "no wound", "no glowing blade edge", "no combat pose", "no crowd"])),

    # ============================ ep008 ============================
    (8, 1, "A-9", 12, 30, ["YHY"], ["暗红衣", "影刃", "黑长直发"], [], ["暗红", "墨灰暗部", "灰雾青灰"],
     "中景，平视，50mm 固定机位，9:16 竖屏。钢板地上：叶红衣单膝跪地，暗红色劲装在冷光里偏暗，黑长直发垂在肩后；影刃反手插进地面，刃身收着不显刃光；钢板上留一道浅浅刃痕。军礼为单膝跪地，非双膝跪伏。工业冷光。" + BADGE_POS + STYLE,
     "12 秒固定单镜：叶红衣自站立改为单膝跪地、影刃反手插进钢板，刃身收着不显刃光；发丝与衣摆有一次轻微落定；全程保持单膝，不出现双膝跪伏；镜头不动。",
     negs(GORE, extra=["no blood", "no gore", "no both knees kneeling", "no blade glow", "no crowd close-up", "no warm light"])),

    (8, 2, "A-9", 14, 30, ["LC"], ["黑色战术风衣"], [], ["灰雾青灰", "墨灰暗部"],
     "中远景，仰视，35mm 升降，9:16 竖屏。归废处置线纵深：陆沉踩上横置的钢架立于高处，黑色战术风衣下摆被气流带起；下方队列仰头看向他，队列的脸一律不入特写；镜头自队列高度向上抬到他的站位，形成竖屏友好的仰视构图。工业冷光，钢架轻微晃动。" + BADGE_POS + STYLE,
     "14 秒升降单镜：镜头自队列高度缓慢向上抬起，最终停在高处站位；人物踩上横置钢架站定，风衣下摆被气流带起并轻摆，钢架轻微晃动；下方队列始终保持远景，脸不入镜；不推近面部。",
     negs(GORE, extra=["no crowd close-up", "no faces in close-up", "no blood", "no gore", "no daylight", "no warm rim light"])),

    (8, 3, "A-9", 12, 32, ["LC"], ["右手腕黑白游龙骨纹", "双相净火(黑白火焰)"], ["M01", "M02"],
     ["净火白", "净火黑", "灰雾青灰"],
     "远景，平视，24mm 固定机位，9:16 竖屏。获救队列沿钢板墙自画面纵深排成长队，队列末尾有人把袖子拉过手腕，腕上褪尽的斑痕褪成一小块浅色，在远景里可辨，是队伍已被救下的可见证据；看不到任何人的面部，队列的脸一律不入镜；队列里没人说话，钢板上的脚步一前一后；陆沉抬起右腕，黑白游龙纹在腕侧亮起，双色火焰贴着骨纹翻了一下，火焰只有黑与白两色。工业冷光。" + BADGE_POS + STYLE,
     "12 秒固定单镜：队列自画面纵深缓慢向前挪动，钢板上的脚步一前一后，末端有人把袖子拉过手腕，腕上褪尽的斑痕褪成一小块浅色，在远景里可辨；陆沉在画面一侧抬起右腕，黑白双焰贴着骨纹翻动一次后收住；队列脸一律不入镜、不给伤处特写。",
     negs(GORE, FLAME, extra=["no close-up of faces", "no visible wounds", "no scar close-up", "no blood", "no gore",
                              "no red flame", "no third flame color"])),

    (8, 4, "A-9", 7, 30, [], [], [], ["云顶冷白", "墨灰暗部"],
     "中景，平视，50mm 固定机位，9:16 竖屏。远处公路方向：装甲车引擎声逼近，画面只见公路上一排移动的车灯光斑，车体不显形、不出现标识；陆沉视野中弹出灰框面板，面板底部浮出一条求救信号条，同屏中文「求救信号 城西」，定位点落在城西方向；面板灰框冷白发光。" + BADGE_POS + STYLE,
     "7 秒固定单镜：远处公路上的车灯光斑缓慢横移，车体始终不显形；面板自视野下方浮起，底部求救信号条与「求救信号 城西」保持可读；镜头不动，不给人物面部。",
     negs(UI, GORE, REAL, extra=["no armored vehicle detail", "no vehicle plate", "no real-world insignia", "no gore"])),
]

# ---------------------------------------------------------------- 组装 + 自检

cards = []
for idx, (ep, sid, scene, dur, steps, chars, descs, motifs, palette, image, video, negatives) in enumerate(CARDS, start=1):
    card = {
        "card_id": f"C-{idx:03d}",
        "ep": ep,
        "shot_id": sid,
        "image_prompt": image,
        "video_prompt": video,
        "negatives": negatives + [BADGE_NEG, TEXT_NEG],
        "params": params(scene, dur, chars, steps=steps, ui=(f"C-{idx:03d}" in SEED_UI_CARDS)),
        "consistency_refs": {
            "char_ids": chars,
            "motifs": motifs,
            "palette": palette,
        },
        "char_descriptions": descs,
        "source": "both",
    }
    cards.append(card)

errs = []

# 1) D11 镜号引用
for c in cards:
    if (c["ep"], c["shot_id"]) not in SHOT_KEYS:
        errs.append(f"{c['card_id']}: ep{c['ep']} 镜{c['shot_id']} 在 D11 不存在")

# 2) 32 镜全覆盖、无重复
seen = [(c["ep"], c["shot_id"]) for c in cards]
if len(set(seen)) != len(seen):
    errs.append("存在重复镜号卡")
if set(seen) != SHOT_KEYS:
    errs.append(f"卡与 D11 镜集合不一致：缺 {sorted(SHOT_KEYS - set(seen))}，多 {sorted(set(seen) - SHOT_KEYS)}")

# 3) V7 锚点闭合（逐卡逐角色模拟）
v7_ok = 0
for c in cards:
    descs = c["char_descriptions"]
    ok = True
    for cid in c["consistency_refs"]["char_ids"]:
        a = ANCHORS.get(cid)
        if not a:
            errs.append(f"{c['card_id']}: D10 无角色锚点 {cid}")
            ok = False
            continue
        hay = f"{a['anchor_text']} {' '.join(a['markers'])}"
        related = [d for d in descs if d in hay or any(m in d for m in a["markers"])]
        if not related:
            errs.append(f"{c['card_id']}: 角色 {cid} 的描述未匹配 D10 锚点表")
            ok = False
    if ok:
        v7_ok += 1

# 4) 母题 / 色板存在性
for c in cards:
    for m in c["consistency_refs"]["motifs"]:
        if m not in MOTIFS:
            errs.append(f"{c['card_id']}: 母题 {m} 不在 D10")
    for p in c["consistency_refs"]["palette"]:
        if p not in PALETTE:
            errs.append(f"{c['card_id']}: 色板 {p} 不在 D10")

# 5) V5 禁用同义词全文扫描
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

doc = {
    "doc_id": "D12",
    "unit": "U01",
    "version": "v1.11",
    # v1.11（2026-10-23 13:1x 视觉设定）：**体量守卫补位 ＋ C-001 修剪重复句**（本版只改 1 张卡 ＋ 加 1 条断言）
    #   起因：v1.10 产物经独立复核（`verify_D12_independent.py`）报 **H5 C-001 prompt 超体量上限**（image 333 字 > 330）。
    #   根因：C-001 的场景句尾部「，暗部保留细节不做死黑」与尾部 STYLE 里的同一句**重复了一次** ⇒ 多占 12 字；
    #   该约束由尾部 STYLE 承载，删去场景句中的重复**不改变任何画面事实**（语义不变，仅去冗余）。
    #   ⚠️ 治本：**本脚本此前无任何体量断言** ⇒ 该超长只有独立复核能发现、构建链自身拦不住（守卫缺位）。
    #   本版新增 **断言 5.8 体量守卫**（image ≤330／video ≤260，超限 exit 1 **不写盘**），
    #   上限与独立复核 H5 **同口径**（两处必须一致，否则一条绿一条红）。
    #   ⚠️ 本版**未改动任何台词**：ep001 镜1 等镜位的台词分叉属 **D11↔D09 上游矛盾**（D11 台词 ≠ D09 对白表），
    #   D12 层**无论跟哪一边都会与另一边分叉** ⇒ 由分镜导演／台本编剧在上游对齐，本岗不代改（详见台账）。
    # v1.10（2026-10-23 12:3x 视觉设定）：D11 U01 ep002 四镜在 12:33:43 被上游整段改稿（视觉圣经级重写：
    #   镜1 改「暴雨夜废弃军工机械厂大门外」＋实心重钢钎顶起卷帘门＋两桶净水；镜2 改「卷帘门彻底轰然下坠锁死」
    #   ＋钢架横推＋检修铁闸→地下排渣管廊；镜3 改「排气栅栏翻出暗道」＋高压指示屏＋排渣闸口与管廊暗扣丈量；
    #   镜4 改「顺着检修铁梯登上天台制高点」；四镜 dialogue 一并改写），
    #   而 D12 U01 的 C-005～C-008 仍停在旧口径（新口径关键词在 D12 命中 0）⇒ 本岗必须同步，否则出图与分镜分叉。
    #   本版把 C-005～C-008 的 image_prompt / video_prompt 全部对齐新 D11，
    #   并把断言 5.7 的守卫键由「仅 ep001」扩为 (ep, shot_id) 全表，覆盖 ep001 三镜 + ep002 四镜。
    #   ⚠️ C-006 的「仅在接触处留下局部暖色亮点」按 S1 裁决 + D10 consistency_rules[13] 保留
    #      （新 D11 文本略去该局部限定，属上游简化，不构成下游可省略的依据）。
    # v1.9（2026-10-23 12:3x 视觉设定）：黄金 3 秒批次在 D11 U01 v1.15 改写 ep001 三镜动作后，D12 U01 三张卡未跟，
    #   按 D12×D11 同口径轴（check_D12_D11_alignment.py 判据 A）逐条人工裁定后补齐：
    #   ① C-001（ep001 镜1）：补「指腹用力按在腕侧骨纹上，青筋暴起」——D11 明写「指腹用力按上去，青筋暴起」，
    #      而旧卡只有「抬起右手腕」；触碰是「骨纹可见但未激活」这一第 0 帧核心符号的因由，漏则出图画成「举腕看纹」。
    #      video 原句「人物只做抬腕、眨眼与呼吸三组小幅动作」补按压后自相矛盾 → 改为四组。
    #   ② C-003（ep001 镜3）：补「掀翻储物箱／半米长的实心重钢钎／用胶布将钢钎死死捆在右腕骨纹之上／指节发白」——
    #      旧卡「人物只抓走一把钢钎」与 D11「捆在右腕骨纹之上」是**两种终态**；video「手部把工具箱盖扣上」替换为胶布动作。
    #   ③ 断言 5.7 由「只守镜4」泛化为按镜位的动态守卫 D11_SYNC_SHOTS＝{镜1,镜3,镜4}，
    #      并保留「D11 写纵身下跃 ⇒ D12 禁反向词沿楼梯向上」的条件性反证分支。
    # v1.8（2026-10-23 12:3x 视觉设定）：① C-004（ep001 镜4）动作方向修正——旧「人物冲出房门进入楼道…人物沿楼梯向上」
    #   与 D11 U01 v1.15「夺门而出翻过扶手纵身下跃」、D08 U01 v1.10「他翻过扶手纵身下跃」方向相反，
    #   且漏「扶手」道具与「下跃」动作；改为「夺门而出、翻过楼道扶手纵身下跃…感应灯在他身后一盏盏由红转绿」。
    #   ② 新增自检断言 5.7「D11 同步守卫」：动态同口径（D11 该镜 visual_facts 里的动作关键词 D12 必须携带；
    #   D11 写「纵身下跃」时 D12 禁反向词「沿楼梯向上」）——不写死单一口径，D11 再改词也拦得住。
    # v1.7（2026-10-23 11:4x 视觉设定）：① C-011 image_prompt 措辞「浮出第一道」→「第一次亮起」（对齐 D08 U01 v1.13 body[9]／D05 T20／D11 U01 v1.13 ep003 镜3 visual_facts）；② 补回填「黄金 3 秒改造」曾只改 JSON 未同步脚本的 C-001～C-004（否则重跑会静默回退这 4 张卡）；③ 留痕：本岗曾出现同一 v1.6 标签对应两份不同字节（改造后 87,127 B 与重跑产物 86,410 B），已于 11:4x 补正——脚本与产物自此一致。
    "status": "in_review",
    "cards": cards,
}
joined = "\n".join(all_text(doc, []))
hits = sorted({w for w in BANNED if w in joined})
if hits:
    errs.append(f"V5 命中禁用同义词：{hits}")

# 5.5) S1 裁决口径闭合（电焊火花暖色落点）—— 防止重建时口径回退
# 依据：project.json decisions.S1_色板暖源口径（codex 裁定 2026-10-22）
#   ① D11 ep002 镜2 焊花 =「薪火橙 #E07B39 瞬时溅落，仅接触处局部暖色亮点，周围仍工业冷光」
#   ③ D10 consistency_rules[13]：电焊火花复用薪火橙，金属暖反光复用薪火橙／薪火暖白
# D12 正面描述若收窄为「暖色只出现在弧光本身」，即与 S1 裁决及 D11 v1.6 分叉
# （D12 v1.3 重建时曾回退过一次，本断言锁死）
S1_REQUIRED = "焊花瞬时溅落卷帘门"
S1_FORBIDDEN = "暖色只出现在弧光本身"
_c006 = next((c for c in cards if (c.get("ep"), c.get("shot_id")) == (2, 2)), None)
if _c006 is None:
    errs.append("S1 断言：找不到 ep002 镜2 的卡")
else:
    _b = (_c006.get("image_prompt") or "") + " " + (_c006.get("video_prompt") or "")
    if S1_REQUIRED not in _b:
        errs.append("S1 口径缺失：ep002 镜2 须含「%s」" % S1_REQUIRED)
    if S1_FORBIDDEN in _b:
        errs.append("S1 口径回退：ep002 镜2 出现旧表述「%s」" % S1_FORBIDDEN)

# 5.6) ep5 镜3 霜层雾气负向词闭合 —— 防止重建时回退（U01-R18 终表）
# 依据：D18 U01-R18 终表（企划合规 2026-10-23 04:45 明派）
#   问题：C-019 的 negatives 原含 `no smoke from humans`，而该镜的冷白雾气**长在被缚人形剪影上**，
#        「from humans」正好命中该载体 → 模型极可能把冷白雾气判成「人体冒烟」而压制，
#        **ep5 镜3 的霜白合规改动会在出图环节静默落空**。
#   处置：`no smoke from humans` → `no burning, no smoke`（去掉命中载体的限定），
#        并保留 `frost-layer cold white mist preserved`（明确要求保留霜层冷白雾气）。
FROST_REQUIRED = ["no burning, no smoke", "frost-layer cold white mist preserved"]
FROST_FORBIDDEN = "no smoke from humans"
_c019 = next((c for c in cards if (c.get("ep"), c.get("shot_id")) == (5, 3)), None)
if _c019 is None:
    errs.append("霜层断言：找不到 ep005 镜3 的卡")
else:
    _ng = _c019.get("negatives") or []
    for _need in FROST_REQUIRED:
        if _need not in _ng:
            errs.append("霜层负向词缺失：ep005 镜3 须含「%s」" % _need)
    if FROST_FORBIDDEN in _ng:
        errs.append("霜层负向词回退：ep005 镜3 出现旧项「%s」"
                    "（该限定会命中「雾气长在人形剪影上」，压制霜白）" % FROST_FORBIDDEN)

# 5.7) D11 同步守卫（黄金 3 秒批次 · ep001 镜1/镜3/镜4）—— 防止 D11 改口径而 D12 不跟
# 依据：D11 U01 v1.15 ep001 三镜的 visual_facts
#   镜1「陆沉抬起右手腕占住画面前景…指腹用力按上去，青筋暴起」
#   镜3「陆沉掀翻储物箱把压缩饼干倒在地上，只抓出一柄半米长的实心重钢钎；
#        工具箱敞口处只有一把扳手和半卷胶布，他迅速用胶布将钢钎死死捆在右腕骨纹之上；
#        他站起时膝软，一只手死死撑住墙指节发白」
#   镜4「陆沉夺门而出翻过扶手纵身下跃，楼道感应灯在他身后一盏盏由红转绿」
#   与上游真源 D08 U01 v1.10 action 条「他翻过扶手纵身下跃，楼道灯在身后一盏盏由红转绿。」
# 问题：「黄金 3 秒批次」改写了 ep001 镜1/镜3/镜4 的动作细节，而 D12 C-001/C-003/C-004 未跟：
#   ① C-004「人物沿楼梯向上」与 D11「纵身下跃」**方向相反**，且漏「扶手」道具与「下跃」动作；
#   ② C-001 只写「抬起右手腕」，漏 D11 的「指腹用力按上去，青筋暴起」——
#      **触碰骨纹是「可见但未激活」这一第 0 帧核心符号的因由**，漏了出图会画成「举腕看纹」；
#      且 video 原写「人物只做抬腕、眨眼与呼吸三组小幅动作」，补按压后该「三组」会自相矛盾。
#   ③ C-003 只写「人物只抓走一把钢钎」，漏 D11 的「用胶布将钢钎死死捆在右腕骨纹之上」——
#      「抓走」与「捆在腕上」是**两种终态**，出图会与 D11 分叉；另漏「指节发白」。
# 处置：C-001/C-003/C-004 的 image_prompt 与 video_prompt 全部对齐 D11 v1.15。
# 本断言做成**动态同口径**（不写死单一口径，D11 再改词也拦得住）：
#   ① 凡 D11 对应镜 visual_facts 里出现的动作关键词，D12 同镜卡必须携带；
#   ② 当 D11 写「纵身下跃」时，D12 不得再出现反向词「沿楼梯向上」。
D11_SYNC_SHOTS = {
    (1, 1): ["指腹", "青筋"],
    (1, 3): ["腕骨纹", "指节发白"],
    (1, 4): ["夺门而出", "扶手", "纵身下跃", "由红转绿"],
    (2, 1): ["暴雨夜", "实心重钢钎", "两桶净水"],
    (2, 2): ["轰然下坠", "检修铁闸", "排渣管廊"],
    (2, 3): ["排气栅栏", "暗道", "高压指示屏", "丈量"],
    (2, 4): ["检修铁梯", "天台制高点"],
}
D11_SYNC_CONTRADICT = {(1, 4): ("纵身下跃", "沿楼梯向上")}


def _d11_shot(ep, sid):
    for _e in D11.get("episodes", []):
        if _e.get("ep") == ep:
            for _s in _e.get("shots", []):
                if _s.get("shot_id") == sid:
                    return _s
    return None


for (_ep, _sid), _tokens in sorted(D11_SYNC_SHOTS.items()):
    _ds = _d11_shot(_ep, _sid)
    _dc = next((c for c in cards if (c.get("ep"), c.get("shot_id")) == (_ep, _sid)), None)
    if _ds is None:
        errs.append("D11 同步守卫：D11 U01 找不到 ep%03d 镜%d" % (_ep, _sid))
        continue
    if _dc is None:
        errs.append("D11 同步守卫：找不到 ep%03d 镜%d 的卡" % (_ep, _sid))
        continue
    _d11_txt = _ds.get("visual_facts") or ""
    _img = _dc.get("image_prompt") or ""
    _vid = _dc.get("video_prompt") or ""
    for _tk in _tokens:
        # 关键词必须出现在 **image_prompt**（静帧＝画面真相）：只写在 video_prompt 里，
        # 首帧出图仍然缺该事实 ⇒ 与「D12 未跟上 D11 口径」等价。
        if _tk in _d11_txt and _tk not in _img:
            errs.append("D11 同步守卫：D11 ep%03d 镜%d 含「%s」但 D12 同镜卡 image_prompt 缺失"
                        "（D12 未跟上 D11 口径）" % (_ep, _sid, _tk))
    if (_ep, _sid) in D11_SYNC_CONTRADICT:
        _anchor, _anti = D11_SYNC_CONTRADICT[(_ep, _sid)]
        # 反向词在 image 或 video 任一字段出现即判错（动作方向错＝画面事实错）
        if _anchor in _d11_txt and (_anti in _img or _anti in _vid):
            errs.append("D11 同步守卫：D11 ep%03d 镜%d 为「%s」，D12 不得出现反向词「%s」"
                        % (_ep, _sid, _anchor, _anti))

if errs:
    print("❌ 自检未通过：")
    for e in errs:
        print("   -", e)
    sys.exit(1)

# 5.8) 体量守卫（2026-10-23 13:1x 视觉设定新增）——**本脚本此前无任何体量断言**
#   起因：C-001 的 image_prompt 因「暗部保留细节不做死黑」在场景句与 STYLE 里重复一次而达 333 字
#   ⇒ 超出 image ≤330 上限；**该超长只有独立复核脚本能发现**，本脚本自身拦不住 ⇒ 属「守卫缺位」。
#   处置：① 修剪重复句（该约束仍由尾部 STYLE 承载，语义不变）；② 把上限写进脚本，**超限即 exit 1 不写盘**。
#   上限口径＝与独立复核 `verify_D12_independent.py` 的 H5 一致（image ≤330／video ≤260），两处必须同口径。
MAX_IMAGE_CHARS_U01 = 330
MAX_VIDEO_CHARS_U01 = 260
for _c in cards:
    _ci = len(_c.get("image_prompt") or "")
    _cv = len(_c.get("video_prompt") or "")
    if _ci > MAX_IMAGE_CHARS_U01:
        errs.append("体量守卫：%s image_prompt %d 字 > 上限 %d" % (_c["card_id"], _ci, MAX_IMAGE_CHARS_U01))
    if _cv > MAX_VIDEO_CHARS_U01:
        errs.append("体量守卫：%s video_prompt %d 字 > 上限 %d" % (_c["card_id"], _cv, MAX_VIDEO_CHARS_U01))
if errs:
    print("❌ 体量守卫未通过：")
    for e in errs:
        print("   -", e)
    sys.exit(1)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"✅ 写出 {OUT}")
print(f"   卡数 {len(cards)}（D11 镜数 {len(SHOT_KEYS)}）｜V7 逐卡通过 {v7_ok}/{len(cards)}")
used = sorted({m for c in cards for m in c["consistency_refs"]["motifs"]})
print(f"   使用母题 {used}（D10 共 {len(MOTIFS)} 条）")
print(f"   V5 禁用同义词命中 0")
