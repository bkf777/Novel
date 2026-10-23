#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_golden3s_ep001.py —— 「黄金 3 秒」改版落盘（U01 ep001）

Chief 补位执行（D08/D09 走各自生成脚本，本脚本只碰画面层与台账层）：
  · D11 U01 ep001 —— 四镜 visual_facts / dialogue / note + continuity 增补
  · D12 U01 C-001..C-004 —— 图像/视频提示词同步（骨纹未激活、门缝红光、面板爆点）
  · D05 shared —— 骨纹 glossary / motifs / gauge_readings 首现口径
  · D07 U01 ep001 —— 四段制第 1 段 note 同步
  · D16 U01 ep001 —— 字幕时码重排 + 片头四行处置 + title_card + 同步留痕
  · D18 shared —— 登记本轮口径变更（Q98 / U01-R37）

幂等：可重复执行；每次只改目标字段，其余字段逐字保留。
用法：python3 scripts/patch_golden3s_ep001.py [--dry-run]
"""
import json, os, sys, shutil, datetime, re

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = f"{ROOT}/reports/_bak_golden3s_ep001_{STAMP}"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj, old=None):
    """内容无变化 → 不写盘、不动版本号（幂等：重复执行不产生版本漂移）。"""
    if old is not None:
        a = {k: v for k, v in obj.items() if k != "version"}
        b = {k: v for k, v in old.items() if k != "version"}
        if a == b:
            print(f"   ⏭  无变化，跳过 {os.path.relpath(p, ROOT)} (版本 {obj.get("version")})")
            return
    if DRY:
        print(f"   [dry-run] 不写盘 {os.path.relpath(p, ROOT)}")
        return
    os.makedirs(BAK, exist_ok=True)
    b = os.path.join(BAK, os.path.basename(p))
    if not os.path.exists(b):
        shutil.copy2(p, b)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 写 {os.path.relpath(p, ROOT)}  (版本 {obj.get("version")})")


def bump(obj, key="version"):
    v = str(obj.get(key, "v1.0"))
    v = re.sub(r"^v+", "v", v)          # 归一：任何 v/vv/vvv 一律视作 v
    obj[key] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def ep_of(doc, n):
    for it in doc["episodes"]:
        if it.get("ep") == n:
            return it
    raise SystemExit(f"❌ 找不到 ep{n}")


def card_of(doc, cid):
    for it in doc["cards"]:
        if it.get("card_id") == cid:
            return it
    raise SystemExit(f"❌ 找不到 {cid}")


# ═══════════════════════ D11 ═══════════════════════
D11 = f"{ROOT}/units/U01/D11.json"
d11 = load(D11)
d11_old = json.loads(json.dumps(d11))
e1 = ep_of(d11, 1)
sh = {s["shot_id"]: s for s in e1["shots"]}

sh[1]["visual_facts"] = (
    "陆沉抬起右手腕占住画面前景，腕侧皮肤上有一道极淡的黑白游龙纹，没亮，像旧印；"
    "背景是满地狼藉的出租屋——翻倒的椅子、散落的工具、熄灭的屏幕；"
    "房门虚掩，门缝下透进一道红光；"
    "灰框面板浮到视野正中，栏目自上而下逐格亮起，中央倒计时数字跳动，"
    "面板顶部同屏中文「距灰潮试炼降临 2 小时 58 分」；"
    "右下角常驻白色角标：AI 生成。"
)
sh[1]["dialogue"] = "陆沉「上一趟我死在第三个小时。」／陆沉「两小时五十八分。」"
sh[1]["sfx"] = "电流接通声；低频嗡鸣持续铺底。"
sh[1]["note"] = (
    "【黄金 3 秒改版 · 2026-10-23】D07 段1 由「陆沉睁眼，面板由暗到亮逐格浮现」改为"
    "「陆沉抬腕看骨纹（未亮）→ 面板由暗到亮逐格浮现」：第 0 帧即为全剧最强符号。"
    "骨纹在本集**可见但未激活**——不发光、不显示归一度读数。"
    "镜头用推：压迫感由推镜承担（D10.camera_language.movement_rule）。"
    "面板文字全部中文同屏（D03 R12）。"
)

sh[2]["visual_facts"] = (
    "灰框面板占满画面，四角有细刻度线，底部滚动播报栏持续上滚；"
    "面板顶部同屏中文「归档回滚完成。」；"
    "面板中央倒计时读数稳定为同屏中文「距灰潮试炼降临 2 小时 58 分」；"
    "面板角落一行同屏中文「上一趟存活 3 小时 04 分」；"
    "右下角常驻白色角标：AI 生成。"
)
sh[2]["note"] = (
    "D07 段2「倒计时与归档回滚提示占满画面，镜头推近提示框」。"
    "特写只给数据界面，不给人体（D10.shot_size_rule）。"
    "本镜承担本集第一处信息爆点：上一趟存活 3 小时 04 分 与本趟 2 小时 58 分 同屏，"
    "观众自己算出少 6 分钟。"
)

sh[3]["visual_facts"] = (
    "陆沉把半箱压缩饼干倒在地上，只抓走一把钢钎；"
    "工具箱敞口处只有一把扳手和半卷胶布；"
    "他站起时膝软，一只手撑住墙；"
    "房门被拉开，楼道感应灯逐层亮起，全是红的；"
    "面板底部一行红字同屏中文「比上一趟少 6 分钟」；"
    "右下角常驻白色角标：AI 生成。"
)
sh[3]["note"] = (
    "D07 段3「他把成箱物资推回柜子，只留下工具箱与钢钎」。"
    "代价落点（膝软扶墙）以可见动作呈现，不写情绪形容词。"
    "面板底部红字是本集第二处爆点，必须在画面上读得清，不得被底部字幕带压住。"
)

sh[4]["visual_facts"] = (
    "陆沉夺门而出，楼道感应灯在他身后一盏盏由红转绿；"
    "感应灯逐层亮起形成向上的光带，人影在转角处远去；"
    "右下角常驻白色角标：AI 生成。"
)
sh[4]["note"] = (
    "D07 段4「他拉开门冲进楼道，脚步声由近及远」。"
    "楼道仅作运动通道，不建立完整场景（D07 scene_needs）。"
    "24mm 用于空间交代（D10.camera_language.lens）。"
)

cont = e1["continuity"]
for c in cont:
    if c.get("id") == "C-U01-EP01-04":
        c["type"] = "口径声明·骨纹与归一度读数"
        c["content"] = (
            "ep001 骨纹**可见但未激活**：腕侧一道极淡的黑白游龙纹，不发光、"
            "全片不出现归一度读数画面（D05 T20／gauge_readings：ep001-002 未解锁骨纹，"
            "ep003 骨纹第一次亮起并首次读 0.5%）。"
        )
cont.append({
    "id": "C-U01-EP01-05",
    "type": "口径声明·黄金 3 秒",
    "content": (
        "本集第 0 帧即为「手腕上的未激活骨纹」，首句台词在 0.5s 入画"
        "（D08 body[0]／D09 ep1 #1／D16 seq1 三处对齐）；"
        "面板与前史后置到 1.5s 之后，片头文字层不在正文区出现——"
        "剧名、节目编号、署名与 AI 标识四行全部移至片尾 43~45s 字幕层，"
        "AI 标识义务由**每镜常驻角标**（本集 4 镜 visual_facts 均声明）承担。"
    ),
})
cont.append({
    "id": "C-U01-EP01-06",
    "type": "口径声明·零血腥代价表达",
    "content": (
        "本集代价一律用物证表达：满地狼藉、吃了一半的压缩饼干、"
        "倒地的工具与熄灭的屏幕、站起时膝软、一只手撑住墙；"
        "全镜无创口、无体液、无喷溅、无器官特写（D03 R08／L1~L5）。"
        "骨纹是体表纹路不破体（D05 T18），与创口不同层。"
    ),
})
bump(d11)
save(D11, d11, d11_old)

# ═══════════════════════ D12 ═══════════════════════
D12 = f"{ROOT}/units/U01/D12.json"
d12 = load(D12)
d12_old = json.loads(json.dumps(d12))
c1 = card_of(d12, "C-001")
c1["image_prompt"] = (
    "中景，平视，35mm，9:16 竖屏。单间出租屋：床、衣柜、堆到天花板的纸箱、一扇窗；"
    "冷白灯管是室内唯一光源，暗部保留细节不做死黑。"
    "利落短发的青年抬起右手腕，手腕占住画面前景，"
    "腕侧皮肤上有一道极淡的黑白游龙纹，像旧印，**纹路不发光**、纹路周围无任何光晕或读数；"
    "背景是翻倒的椅子、散落的工具、熄灭的屏幕；房门虚掩，门缝下透进一道红光；"
    "视野正中浮出灰框面板，栏目自上而下逐格亮起，中央倒计时数字跳动，"
    "面板顶部同屏中文「距灰潮试炼降临 2 小时 58 分」。"
    "右下角 72%~78% 画面高度留净空供 AI 生成角标，底部 15% 留字幕带，"
    "主体居中偏上、头顶留白 8%。写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
)
c1["video_prompt"] = (
    "13 秒单镜：镜头自中景极缓推进，前景手腕保持稳定，"
    "皮肤上那道极淡的黑白游龙纹全程**不发光**、不变形、不出现读数；"
    "人物只做抬腕、眨眼与呼吸三组小幅动作；"
    "面板在视野正中逐格亮起，倒计时数字跳动后落定，"
    "顶部中文「距灰潮试炼降临 2 小时 58 分」始终可读；"
    "不做大幅肢体动作，不做贴脸；右下角 AI 生成角标常驻不遮挡。"
)

c2 = card_of(d12, "C-002")
c2["image_prompt"] = (
    "特写，平视，50mm，9:16 竖屏。半透明灰框面板占满画面，四角有细刻度线，灰框冷白发光，"
    "底部滚动播报栏持续上滚；面板顶部同屏中文「归档回滚完成。」；"
    "面板中央倒计时读数为同屏中文「距灰潮试炼降临 2 小时 58 分」；"
    "面板角落一行同屏中文「上一趟存活 3 小时 04 分」。"
    "只给数据界面，画面内不出现人体、面孔与手。"
    "右下角 72%~78% 画面高度留净空供 AI 生成角标，底部 15% 留字幕带，"
    "主体居中偏上、头顶留白 8%。写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
)
c2["video_prompt"] = (
    "13 秒单镜：镜头极缓推近面板；播报栏持续上滚；"
    "顶部中文「归档回滚完成。」、中央读数「距灰潮试炼降临 2 小时 58 分」、"
    "角落一行「上一趟存活 3 小时 04 分」三处文字保持可读；"
    "界面发光轻微呼吸，不做闪烁抖动；画面不出现任何人体。"
)

c3 = card_of(d12, "C-003")
c3["image_prompt"] = (
    "中景，平视，35mm 横向平移，9:16 竖屏。出租屋："
    "半箱压缩饼干被倒在地上，人物只抓走一把钢钎；"
    "工具箱敞口里只有一把扳手和半卷胶布；"
    "利落短发的青年侧身发力，站起时膝软、一只手撑住墙面借力；"
    "房门被拉开，楼道感应灯逐层亮起，灯色全是红的；"
    "视野下缘浮出面板，面板底部一行红字同屏中文「比上一趟少 6 分钟」。"
    "右下角 72%~78% 画面高度留净空供 AI 生成角标，底部 15% 留字幕带，"
    "主体居中偏上、头顶留白 8%。写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
)
c3["video_prompt"] = (
    "12 秒单镜：镜头横向平移跟住倒饼干动作，饼干箱被推倒，人物只抓走一把钢钎；"
    "手部把工具箱盖扣上；人物站起时膝盖一软、一只手扶墙借力；"
    "房门拉开，门外楼道感应灯逐层亮起且灯色全为红；"
    "面板底部红字「比上一趟少 6 分钟」保持可读。"
    "动作连贯、幅度克制，箱体与手部不出现破损或污渍；右下角 AI 生成角标常驻。"
)

c4 = card_of(d12, "C-004")
c4["image_prompt"] = (
    "全景，客观跟拍，24mm，9:16 竖屏。狭窄楼道与转角应急灯："
    "人物冲出房门进入楼道，感应灯逐层亮起形成向上的光带，灯色由红转绿；"
    "窗外是城市夜色，楼道只作运动通道、不建立完整场景；人物沿楼梯向上，身影在转角处远去。"
    "冷青灰夜景，暗部保留细节。右下角 72%~78% 画面高度留净空供 AI 生成角标，"
    "底部 15% 留字幕带，主体居中偏上、头顶留白 8%。"
    "写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。"
)
c4["video_prompt"] = (
    "7 秒单镜：跟拍人物冲出房门、沿楼梯向上，感应灯随经过逐层亮起，灯色由红转绿，"
    "脚步声由近及远；镜头保持客观跟拍、不追进转角，人物在转角处远去；"
    "不出现其他住户与日光；右下角 AI 生成角标常驻。"
)
bump(d12)
save(D12, d12, d12_old)

# ═══════════════════════ D05 ═══════════════════════
D05 = f"{ROOT}/shared/D05.json"
d05 = load(D05)
d05_old = json.loads(json.dumps(d05))
for g in d05["glossary"]:
    if g.get("term") == "骨纹":
        M = "【首现口径 · 2026-10-23 用户裁决】"
        if M in g["definition"]:
            g["definition"] = g["definition"].split(M)[0].rstrip()
        g["definition"] += (
            M + "骨纹自 ep001 即可见，但**只作未激活态**——"
            "黑白游龙纹路，不发光、不显示归一度读数；ep002 同 ep001；"
            "ep003 骨纹**第一次亮起**（发光）并首次显示归一度读数 0.5%。"
            "未激活态 ≠ 已解锁阶位：ep001-002 陆沉仍未解锁骨纹，阶位与读数口径不变。"
        )
for m in d05.get("motifs", []):
    if m.get("name") == "灰白与漆黑交织骨纹":
        M = "；ep001-002 以未激活态（纹路不发光）出现，ep003 起点亮"
        if M in m["desc"]:
            m["desc"] = m["desc"].split(M)[0].rstrip()
        m["desc"] += M
for gr in d05["power_system"].get("gauge_readings", []):
    if gr.get("ep") == 3:
        M = "（ep001-002 骨纹可见但未激活、不显示读数；本行 0.5% 自 ep003 首次亮起时起读）"
        if M in gr["event"]:
            gr["event"] = gr["event"].split(M)[0].rstrip()
        gr["event"] += M
bump(d05)
save(D05, d05, d05_old)

# ═══════════════════════ D07 ═══════════════════════
D07 = f"{ROOT}/units/U01/D07.json"
d07 = load(D07)
d07_old = json.loads(json.dumps(d07))
e7 = ep_of(d07, 1)
e7["quad_segments"][0]["note"] = "陆沉抬腕看骨纹（未亮）；面板由暗到亮逐格浮现"
bump(d07)
save(D07, d07, d07_old)

# ═══════════════════════ D16 ═══════════════════════
D16 = f"{ROOT}/units/U01/D16.json"
d16 = load(D16)
d16_old = json.loads(json.dumps(d16))
e16 = ep_of(d16, 1)
ss = e16["subtitle_style"]

DMARK = "【黄金 3 秒改版 · 2026-10-23】"
if DMARK in ss["dwell_calc_convention"]:
    ss["dwell_calc_convention"] = ss["dwell_calc_convention"].split(DMARK)[0].rstrip()
ss["dwell_calc_convention"] += (
    DMARK + "本集字幕表重排：片头四行（剧名／节目编号／署名／AI 标识）"
    "从 0.0~2.0s 正文区**全部撤出**，改由片尾 43~45s 标题层承担；"
    "首句台词提前到 0.5s 入画（seq1），为全库首个「前 3 秒有台词」的集。"
    "新增行 seq1（hook 句）当前为**预算时长 1.8s**，待声音设计岗合成实测后按"
    "「out_sec ＝ 配音 at_sec＋dur_sec」复核；其余 3 条对白行沿用 D15 v1.6 现行配音预算，未改数值。"
)

ss["lines"] = [
    {"seq": 1, "type": "对白", "char_id": "LC", "text": "上一趟我死在第三个小时。",
     "in_sec": 0.5, "out_sec": 2.3, "shot_id": 1,
     "note": "【黄金 3 秒】第 0.5s 入画的第一句台词；预算时长 1.8s，待 TTS 实测复核"},
    {"seq": 2, "type": "面板文字", "text": "距灰潮试炼降临 2 小时 58 分",
     "in_sec": 2.3, "out_sec": 4.3, "shot_id": 1},
    {"seq": 3, "type": "对白", "char_id": "LC", "text": "两小时五十八分。",
     "in_sec": 10.4, "out_sec": 12.4, "shot_id": 1},
    {"seq": 4, "type": "面板文字", "text": "归档回滚完成。",
     "in_sec": 13.4, "out_sec": 15.2, "shot_id": 2},
    {"seq": 5, "type": "面板文字", "text": "上一趟存活 3 小时 04 分",
     "in_sec": 15.6, "out_sec": 17.8, "shot_id": 2},
    {"seq": 6, "type": "对白", "char_id": "LC", "text": "东西不带。",
     "in_sec": 31.4, "out_sec": 32.7, "shot_id": 3},
    {"seq": 7, "type": "面板文字", "text": "比上一趟少 6 分钟",
     "in_sec": 33.2, "out_sec": 35.4, "shot_id": 3},
    {"seq": 8, "type": "对白", "char_id": "LC", "text": "机械厂。",
     "in_sec": 39.2, "out_sec": 40.5, "shot_id": 4},
    {"seq": 9, "type": "角标", "text": "AI 生成",
     "in_sec": 0, "out_sec": 45,
     "position": "右下角，基线 72%~78% 画面高度，右对齐，距右 ≥6% 画面宽"},
    {"seq": 10, "type": "片尾", "text": "节目编号：〔待平台给出〕　编剧：〔待定〕　导演：〔待定〕　《双相潮主》　本片由人工智能生成",
     "in_sec": 43, "out_sec": 45,
     "position": "底部字幕区（画面高度 80%~90%），叠在最后一镜末段上",
     "note": "片头四行（剧名／编号位／署名／AI 标识）自本版起统一移至片尾；编号不可自编（D03 §7.3）"},
]

aud = ss["subtitle_sync_audit"]
aud["synced_row_count"] = 3
aud["no_vo_anchor_rows"] = 1
aud["verified_against_d15"] = ("v1.6（终表口径；D15 v1.6 落盘后复核）｜"
                                "黄金 3 秒改版新增的 seq1 hook 句待 D15 v1.7 落盘后按实测复核")
aud["rows"] = [
    {"seq": 1, "type": "对白", "in_sec": 0.5, "out_sec": 2.3,
     "nominal_dwell_sec": 1.8, "float_dwell_sec": 1.7999999999999998,
     "d15_vo_at_sec": 0.5, "d15_vo_dur_sec": 1.8,
     "action": "新增行（预算值，待实测）",
     "verdict": "待复核——TTS 尚未合成，dur_sec 为预算；实测落盘后按 D15 v1.7 重算 out_sec",
     "note": "本行是本集新增的 hook 句，也是全库第一条「前 3 秒入画」的台词。"},
    {"seq": 3, "type": "对白", "in_sec": 10.4, "out_sec": 12.4,
     "nominal_dwell_sec": 2.0, "float_dwell_sec": 2.0,
     "d15_vo_at_sec": 10.4, "d15_vo_dur_sec": 2.0,
     "action": "不动（沿用 D15 v1.6 终表）",
     "verdict": "合规"},
    {"seq": 6, "type": "对白", "in_sec": 31.4, "out_sec": 32.7,
     "nominal_dwell_sec": 1.3, "float_dwell_sec": 1.3000000000000043,
     "d15_vo_at_sec": 31.4, "d15_vo_dur_sec": 1.3,
     "action": "不动（沿用 D15 v1.6 终表）",
     "verdict": "合规（标称网格与 D15 配音逐条一致；浮点尾差仅存在于二进制表示）"},
    {"seq": 8, "type": "对白", "in_sec": 39.2, "out_sec": 40.5,
     "nominal_dwell_sec": 1.3, "float_dwell_sec": 1.2999999999999972,
     "d15_vo_at_sec": 39.2, "d15_vo_dur_sec": 1.3,
     "action": "不动（沿用 D15 v1.6 终表）",
     "verdict": "合规"},
]
_rec = {
    "date": "2026-10-23",
    "event": "黄金 3 秒改版（Chief 补位 · U01 ep001）",
    "basis": "用户三条裁决：①短剧要有黄金 3 秒、不能像小说铺陈 ②不要有血 ③可以有骨纹。"
             "改动面＝D08 正文 / D09 台词 / D11 四镜 / D12 四卡 / D05 骨纹口径 / D07 段1 note / D16 字幕表。",
    "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
    "changes": [
        "字幕行 11 行 → 10 行：片头四行（seq1~4）撤出正文区，合并进片尾 seq10",
        "新增 seq1 对白（hook 句，0.5s 入画）、seq2 面板文字、seq4/seq5 面板文字、seq7 面板文字",
        "seq 重排：原 seq6→seq3、原 seq8→seq6、原 seq9→seq8",
        "title_card.head 由「四行片头」改为「无片头文字层」；片尾承担剧名／编号／署名／AI 标识",
        "synced_row_count 1 → 3；no_vo_anchor_rows 0 → 1（seq1 待实测）",
    ],
    "not_changed": [
        "3 条既有对白字幕的 in_sec／out_sec 数值零改动（沿用 D15 v1.6 终表）",
        "subtitle_style 的字号／描边／位置／min_dwell_sec／sync_rule／badge_avoid／ai_badge／terminology_rule 全部未动",
        "cuts 与 transitions（3 个段间硬切、镜时 13/13/12/7）零改动 —— 四段制未动",
    ],
    "applied_by": "Chief（bot_6da791c7f983）",
}
_srs = aud.setdefault("sync_records", [])
_srs[:] = [r for r in _srs if not (r.get("date") == _rec["date"] and r.get("event") == _rec["event"])]
_srs.append(_rec)

e16["title_card"] = {
    "head": {
        "in_sec": 0,
        "out_sec": 0,
        "form": "**不做片头文字层**——剧名／节目编号／编剧导演署名／AI 标识四行全部撤出正文区，"
                "改由片尾 43~45s 标题层承担；第 0 帧直接给画面本身（手腕上的未激活骨纹）",
        "layout": "无。画面上部带区（画面高度 6%~20%）在本集不承载任何文字",
        "fade": "无文字层，故无淡入淡出；画面本身无淡入淡出",
        "first_frame": "0.0s 首帧即为陆沉抬起的手腕与那道极淡的黑白游龙纹，非黑场、无文字层",
        "basis": "短剧黄金 3 秒：第 0 帧必须是「已经出事的画面」，不能是环境铺陈，也不能是字幕板；"
                 "四行片头原本占掉 0~2s，且含「〔待平台给出〕」「〔待定〕」等半成品信息，劝退观众。",
    },
    "tail": {
        "in_sec": 43,
        "out_sec": 45,
        "form": "不切黑、不新增静止无信息镜（D10.camera_language.banned「长时间静止无信息镜」）；"
                "画面保持镜4 末帧（楼道感应灯由红转绿、身影向上远去），片尾字幕层叠在其上",
        "audio": "43.0~45.0s 音乐收尾，环境声保留至 45.0s，不做绝对静音",
        "content": "节目编号：〔待平台给出〕　编剧：〔待定〕　导演：〔待定〕　《双相潮主》　本片由人工智能生成",
        "next_ep_hook": "ep002 承接「先去哪、抢什么」：陆沉选择废弃军工机械厂",
    },
    "compliance": {
        "ai_disclosure": "AI 生成标识义务由**全片右下角常驻角标「AI 生成」**（本集 4 镜 visual_facts 逐镜声明、"
                         "D12 四张卡 negatives 逐卡声明）＋**片尾字幕「本片由人工智能生成」**承担；"
                         "片头不再重复大字（D03 R09 要求的是常驻明显位置标识，角标已在；"
                         "片头大字既重复又占掉最贵的 2 秒）",
        "title_items_checklist": "剧名／编号位／署名／AI 标识 四项**齐备但统一在片尾 43~45s 呈现**",
        "pending_fill": "剧名定稿（D03 §7.1）、节目编号（平台出具，不可自编）、编剧与导演署名",
    },
}
bump(d16)
save(D16, d16, d16_old)

# ═══════════════════════ D18 ═══════════════════════
D18 = f"{ROOT}/shared/D18.json"
d18 = load(D18)
d18_old = json.loads(json.dumps(d18))
_gc = {
    "id": "Q98",
    "id": "Q98",
    "rule": "**「黄金 3 秒」是硬结构约束，不是写作建议**：每集第 0 帧必须是「已经出事的画面」（不得为环境铺陈），"
            "首句台词须在 **1.5s 内**入画且台词条数 ≥3；片头文字层（剧名／编号／署名／AI 标识）"
            "**不得占用 0~3s 正文区**；每集正文末条**不得是合规备注**；正文零创口／零体液／零喷溅。",
    "detail": "**依据**＝用户 2026-10-23 三条裁决（短剧要有黄金 3 秒、不要有血、可以有骨纹）"
              "＋ Chief 对 U01/U02 的实测取证：16 集里 8 集前 3 秒一句台词都没有（最晚 ep003 首句在 16.4s）、"
              "11 集正文末条是合规句（每集最强 30 秒在念「AI 生成角标常驻」）、"
              "每集 0~2s 被片头四行占满且含「〔待平台给出〕」「〔待定〕」。"
              "**首轮落点**＝U01 ep001 单集改造（D08 v1.10／D09 v1.6／D11 v1.11／D12 v1.6／D16 v1.13／D05／D07），"
              "四段制 4 镜 45 秒与 D14 白模几何**零改动**（镜时 13/13/12/7、景别中景/特写/中景/全景均不变）。"
              "**骨纹口径**＝ep001 可见但未激活（不发光、无归一度读数），ep003 第一次亮起并首次读 0.5%。"
              "**代价表达**＝一律用物证（满地狼藉、吃了一半的压缩饼干、还冒着热气的速溶咖啡、膝软、扶墙），不用血。"
              "**合规口径**＝AI 标识由常驻角标＋片尾字幕满足，片头不再重复大字。",
    "status": "生效（U01 ep001 已改造）",
    "scope": "U01 ep001 起逐集推行；U01 其余 7 集、U02 8 集、U03+ 全部 160 集待改造",
}
_gcs = d18["global_checks"]
_gcs[:] = [g for g in _gcs if g.get("id") != "Q98"]
_gcs.append(_gc)
_oi = {
    "id": "U01-R37",
    "id": "U01-R37",
    "status": "已登记·待总控裁定（黄金 3 秒改造未铺开）",
    "note": "**本轮只改了 U01 ep001 一集**，U01 其余 7 集与 U02 8 集仍是「小说式铺陈」写法："
            "前 3 秒无台词、正文末条为合规备注、片头四行占满 0~2s。"
            "**未铺开的原因**＝① 需要用户在看过 ep001 样片后确认黄金 3 秒的具体版本；"
            "② 改造会连带 D08 正文 → D09 台词 → D11 四镜 → D12 四卡 → D15 配音 → D16 字幕 全链重做，"
            "且新增台词需 TTS 合成（上游 429 限流）。"
            "**待裁定**：(a) 直接按 ep001 口径铺 U01 八集＋U02 八集；"
            "(b) 先只铺 U01；(c) 暂停改造、回退 ep001。"
            "**附带**＝ep001 新增的 hook 句尚无实测音频（D16 seq1 dur_sec 1.8 为预算值），"
            "已挂 U01-R37 随声音设计岗 TTS 合成一并闭合。",
}
_ois = d18["open_issues"]
_ois[:] = [o for o in _ois if o.get("id") != "U01-R37"]
_ois.append(_oi)
bump(d18)
save(D18, d18, d18_old)

print(f"\n{'[dry-run] ' if DRY else ''}✅ 黄金 3 秒改版落盘完成；备份目录 {BAK}")
