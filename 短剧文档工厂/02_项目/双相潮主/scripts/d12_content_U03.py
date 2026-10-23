#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U03 单元 · D12 AI 提示词卡库 · 内容数据

由 scripts/build_D12.py --unit U03 调用；**改内容必须改本文件后重跑引擎，禁直接改 JSON**。

- CARDS：32 镜卡数据（ep017–024 × 每集 4 镜），逐镜对应 units/U03/D11.json 的 (ep, shot_id)。
  景别／机位／焦距／运镜／时长／取景声明／台词／音效**一律由引擎从 D11 读取**，本文件只写：
    ep, shot_id            —— 镜位
    char_ids              —— 本卡画框内出现的编号角色（只登记有编号角色，群演不入）
    descs                 —— D10 锚点表 markers 里的原样片段（V7 溯源用，逐字）
    motifs / palette      —— D10 的 motif_id 与色板名
    body_image            —— 画面主体与构图要点（≤130 字，防吃下游 H3 预算）
    body_video            —— 动作与过程要点（≤130 字）
    extras                —— 本卡专属负向词（全英文）
    state_keys            —— 否定／状态表述的关键短语，必须在 image_prompt 与 video_prompt 中都正面出现（轴②）
    text                  —— 画面内是否有可读中文（决定负向词组与 UI seed）
    steps                 —— 采样步数（奇观镜 32，其余 30）

**V7 铁律**：descs 里的每一项都必须是 D10 `character_anchors[].markers` 的**原样片段**（逐字）。
**画外音纪律（分镜导演 10:3x 派活）**：台词为画外音的镜位，角色**不入画** ⇒ char_ids 不得挂该角色。
"""

VERSION = "v1.4"

# ---------------------------------------------------------------- 每个场景码一份 appearance
SCENE_APPEARANCE = {
    "B-11": "废弃军工机械厂厂门外街面与门禁区：厂门与门柱、门外一段被烧过的街面、应急灯与残余火光；工业冷光加青灰雾气。",
    "B-12": "废弃军工机械厂厂门外街面与门禁区：厂门阴影、贴墙阴影带、厂内应急灯自门缝漏出；冷调低照度，街面留出影刃穿行的空当。",
    "B-13": "废弃军工机械厂门柱与旗位：门柱、贴上门柱的两件金属件、一面立起的旗；灰雾里只剩轮廓，照明压到最低。",
    "B-14": "废弃军工机械厂门禁与分诊区：门柱两侧的通道、分诊台、两列排队区；工业冷光加青灰雾气，排队的人一律作剪影。",
    "B-15": "废弃军工机械厂告示位与街口：门边贴出的告示、贴满布告的墙面、街口通道；冷调低照度，灰雾压在街面。",
    "B-16": "城郊骨井井口：井架、转动绞盘、井口返出的灰雾；照明只靠井架顶灯，井架在灰雾里只剩轮廓。",
    "B-17": "废弃军工机械厂厂内拖回位：厂内地面、拖回的人形轮廓、摊开的终端与密信；冷白工业灯低照度。",
    "B-18": "废弃军工机械厂内一张钢桌：钢桌面、摊开的合同与名单板；冷白工业灯自高位落下，桌面文件区为唯一亮面。",
    "B-19": "废弃军工机械厂净化区与名单板：净化区地面、名单板与其立架、净化用火堆位置；工业冷光加净化处白光，背景压暗。",
}

# ---------------------------------------------------------------- 32 镜
CARDS = [
    # ============================== ep017 ==============================
    dict(ep=17, shot_id=1, groups=[], char_ids=["YHY"], descs=["影刃", "暗红衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="厂门外的余火还在烧，十几条影子从灰雾里压过来，把街面围成半圈；叶红衣独自站在半圈缺口处，影刃横在身前，刃面不反光，街面上只留下一道暗色；排队与包围者一律作剪影，面部不入画。",
         body_video="镜头自远景缓慢推进；厂门外余火还在烧，十几条影子从灰雾里压过来围成半圈；叶红衣独自站在半圈缺口处，影刃横在身前不动，刃面不反光；包围者只作剪影，面部一律不入镜。",
         extras=["no face of the crowd", "no close-up of the crowd", "no weapon raised against the protagonist", "no gore", "no blood"],
         state_keys=["影刃横在身前", "刃面不反光"], text=False, steps=30),
    dict(ep=17, shot_id=2, groups=["FLAME"], char_ids=["YHY"], descs=["影刃"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "石膏灰白"],
         body_image="影刃切过街面，最前排的影子一个个溃散为灰烬光尘，落灰积在砖缝里；街面上只留下一道暗色，刃身不反光；溃散只作光尘与落灰，不给人体细节。",
         body_video="影刃切过街面，最前排的影子逐个溃散为灰烬光尘；落灰积在砖缝里；落灰自半空沉下、积进砖缝；街面只留下一道暗色，刃身全程不反光；不给人体细节。",
         extras=["no flesh disintegration close-up", "no bone fragments", "no blood", "no gore", "no third flame color"],
         state_keys=["溃散为灰烬光尘", "落灰积在砖缝里"], text=False, steps=32),
    dict(ep=17, shot_id=3, groups=[], char_ids=["YHY"], descs=["暗红衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="剩下的影子退向街口暗处，主谋被逼到路口，退路一寸寸断掉；街口只剩暗处与被截断的路；主谋只作剪影，不给面部。",
         body_video="剩下的影子逐个退向街口暗处；主谋被逼到路口、退路一寸寸断掉；街口只剩暗处与被截断的路；主谋只作剪影，面部一律不入镜。",
         extras=["no face of the retreating crowd", "no close-up of the leader", "no gore", "no blood"],
         state_keys=["主谋只作剪影", "退路一寸寸断掉"], text=False, steps=30),
    dict(ep=17, shot_id=4, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹"], motifs=["M02"], palette=["净火白", "净火黑", "灰雾青灰", "墨灰暗部"],
         body_image="厂门阴影里走出一个人，右腕骨上的黑白骨纹一路亮起来，整条街面被压住；视野一角的读数栏显示同屏中文「归一度 1.4%」；骨纹只走体表发光与轮廓光，不破体。",
         body_video="镜头自中景随人物抬升；厂门阴影里走出一个人，右腕骨上的黑白骨纹一路亮起来；整条街面被压住，读数栏保持「归一度 1.4%」可读；骨纹只走体表发光与轮廓光、不破体。",
         extras=["no skin breakage", "no bone protruding through skin", "no blood", "no gore", "no third flame color"],
         state_keys=["黑白骨纹一路亮起来", "归一度 1.4%"], text=True, steps=32),

    # ============================== ep018 ==============================
    dict(ep=18, shot_id=1, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹"], motifs=["M01", "M02"], palette=["净火白", "净火黑", "灰雾青灰", "墨灰暗部"],
         body_image="骨威全开，骨纹自右腕骨一路亮到小臂，白光顺着街面铺开，灰雾被压得下沉；街面碎石在震动里跳起；骨纹只走体表发光，不破体不见皮下骨骼。",
         body_video="镜头自全景缓慢推进；骨纹自右腕骨一路亮到小臂，白光顺着街面铺开，灰雾被压得下沉；街面碎石在震动里跳起；骨纹全程贴附皮肤表面发光、不破体；本句为画外音／主观声，画幅内只有腕骨纹路这一局部，无面部、无口型、无身份锚点。",
         extras=["no skin puncture", "no bone under the skin", "no third flame color", "no blood", "no gore"],
         state_keys=["骨纹自右腕骨一路亮到小臂", "灰雾被压得下沉"], text=False, steps=32),
    dict(ep=18, shot_id=2, groups=["FLAME"], char_ids=[], descs=[], motifs=[], palette=["石膏灰白", "灰雾青灰", "墨灰暗部"],
         body_image="压下来的范围内，围上来的人一个个溃散为灰烬光尘；消解由近及远，人形轮廓逐个散成发亮的灰点；只作光尘与轮廓散解，不给人体细节。",
         body_video="消解由近及远推进，围上来的人逐个散成发亮的灰点；人形轮廓一路散成灰烬光尘并向上飘散；全程不给人体细节与残骸。",
         extras=["no flesh disintegration close-up", "no bone fragments", "no blood", "no gore"],
         state_keys=["消解由近及远", "散成发亮的灰点"], text=False, steps=32),
    dict(ep=18, shot_id=3, groups=[], char_ids=["SQC"], descs=["数据板", "白色科研风衣"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="苏清辞把数据板架在钢箱上，屏上频谱一条条平下去，多余的心跳信号全部消失；街面安静下来，落灰被风推成一道一道；数据板屏上文字层一律中文。",
         body_video="苏清辞把数据板架稳在钢箱上，屏上频谱一条条平下去，多余的心跳信号全部消失；街面安静下来，落灰被风推成一道一道；屏上文字保持中文正写、逐字可读。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no face in frame", "no gore"],
         state_keys=["频谱一条条平下去", "多余的心跳信号全部消失"], text=True, steps=30),
    dict(ep=18, shot_id=4, groups=[], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="灰烬落定处只剩两件金属件：身份铭牌与敌酋纹章，单独落在砖面上；陆沉弯腰把两件一件件取下握在手里；视野一角的读数栏显示同屏中文「归一度 1.4%」。",
         body_video="灰烬落定后砖面上只剩两件金属件；陆沉弯腰把身份铭牌与敌酋纹章一件件取下、握在手里；读数栏保持「归一度 1.4%」可读；不给金属件上的可辨徽记。",
         extras=["no readable real-world insignia", "no real-world national flags", "no real corporate logos", "no gore", "no blood"],
         state_keys=["只剩两件金属件", "归一度 1.4%"], text=True, steps=30),

    # ============================== ep019 ==============================
    dict(ep=19, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="身份铭牌与敌酋纹章被挂上门柱，只挂两件金属件，门柱上没有别的东西；门柱在灰雾里只剩轮廓；金属件上的纹样为抽象几何，不带任何可辨徽记。",
         body_video="镜头固定不动；身份铭牌与敌酋纹章被挂上门柱，只挂两件金属件；门柱在灰雾里只剩轮廓；金属件纹样保持抽象几何，不出现可辨徽记；本句为画外音／主观声，画面内只有门柱与两件金属件，不出现该角色、不给口型与面部。",
         extras=["no readable real-world insignia", "no real-world national flags", "no real corporate logos", "no sign board with text", "no gore"],
         state_keys=["只挂两件金属件", "门柱在灰雾里只剩轮廓"], text=False, steps=30),
    dict(ep=19, shot_id=2, groups=["REAL"], char_ids=["YHY"], descs=["暗红色劲装", "黑长直发"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "暗红"],
         body_image="叶红衣把旗杆压进门槛石缝，杆身立直，旗面在灰雾里展开；旗面上一行字：踏入此线者死；字为中文正写、逐字可读。",
         body_video="镜头自中景随旗杆抬升；叶红衣把旗杆压进门槛石缝，杆身立直，旗面在灰雾里展开；旗面上一行字：踏入此线者死；旗面那行中文「踏入此线者死」保持正写、逐字可读；旗面不作飘飞乱动。",
         extras=["no garbled text", "no English-only text", "no religious iconography", "no gore", "no blood"],
         state_keys=["旗面上一行字：踏入此线者死"], text=True, steps=30),
    dict(ep=19, shot_id=3, groups=[], char_ids=["SQC", "LC"], descs=["数据板", "白色科研风衣", "黑色战术风衣"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="苏清辞把铭牌编号抄进数据板，抄完又核了一遍；陆沉站在门内一侧看着旗面，没有接话；数据板屏上编号为中文正写、逐字可读。",
         body_video="苏清辞把铭牌编号一笔笔抄进数据板，抄完又核了一遍；陆沉站在门内一侧看着旗面、没有接话；屏上编号保持中文正写、逐字可读；不给面部特写。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no close-up of any face", "no gore"],
         state_keys=["抄完又核了一遍", "没有接话"], text=True, steps=30),
    dict(ep=19, shot_id=4, groups=[], char_ids=["LC"], descs=["右手腕黑白游龙骨纹"], motifs=["M02"], palette=["灰雾青灰", "墨灰暗部"],
         body_image="厂门外的灰雾里车辙从四面压过来，天还没亮，队伍已经沿着车辙排到厂门外；排队的人一律作剪影；视野一角的读数栏显示同屏中文「归一度 1.4%」。",
         body_video="镜头自远景推近厂门；灰雾里车辙从四面压过来，队伍已经沿着车辙排到厂门外；排队者一律作剪影，面部不入镜；读数栏保持「归一度 1.4%」可读。",
         extras=["no face of the queue", "no close-up of the crowd", "no gore", "no blood"],
         state_keys=["队伍已经沿着车辙排到厂门外", "归一度 1.4%"], text=True, steps=30),

    # ============================== ep020 ==============================
    dict(ep=20, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="队伍从厂门一直排到路口，车辙压进灰雾里，轮印叠着轮印；排队的人一律作剪影，队形一路拐进灰雾深处；门两边各留一列排队通道位，喊话者不入画。",
         body_video="镜头自远景俯视；队伍从厂门一直排到路口，车辙压进灰雾里、轮印叠着轮印；排队的人一律作剪影，队形一路拐进灰雾深处；门两边各留一列排队通道位，喊话者不入画；本句为画外音／主观声，画面内只有队伍与剪影，不出现喊话者、不给口型与面部。",
         extras=["no face of the queue", "no close-up of the crowd", "no gore", "no blood"],
         state_keys=["排队的人一律作剪影", "门两边各留一列排队通道位"], text=False, steps=30),
    dict(ep=20, shot_id=2, groups=[], char_ids=["SQC"], descs=["白色科研风衣", "数据板"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="苏清辞在分诊台前按灰斑轻重分出两列，净火排在最前面；两列之间留出一条通道，队头是净火位；灰斑只在袖口与手背上可见。",
         body_video="苏清辞在分诊台前按灰斑轻重把队伍分出两列，净火排在最前面；两列之间留出一条通道，队头始终是净火位；灰斑只在袖口与手背上可见；不给面部特写。",
         extras=["no visible open skin lesion", "no gore", "no blood", "no close-up of any face"],
         state_keys=["净火排在最前面", "两列之间留出一条通道"], text=False, steps=30),
    dict(ep=20, shot_id=3, groups=[], char_ids=["LC", "YHY"], descs=["黑色战术风衣", "暗红衣"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="死士营第一次按名册点人，笔尖一列列往下走；陆沉走到登记位前把名册接过来翻到最后一页；名册栏位一律中文正写、逐字可读。",
         body_video="死士营第一次按名册点人，笔尖一列列往下走；陆沉走到登记位前把名册接过来、翻到最后一页；名册栏位保持中文正写、逐字可读；不给面部特写。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no close-up of any face", "no gore"],
         state_keys=["笔尖一列列往下走", "翻到最后一页"], text=True, steps=30),
    dict(ep=20, shot_id=4, groups=[], char_ids=["YHY"], descs=["影刃"], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="门禁改成两班，叶红衣的刃没有离手；天亮时灰雾没有散，街面上还是灰的；视野一角的读数栏显示同屏中文「归一度 1.4%」。",
         body_video="门禁改成两班，叶红衣的刃没有离手；天亮时灰雾没有散，街面上还是灰的；读数栏保持「归度 1.4%」可读；刃身不反光。",
         extras=["no third flame color", "no blood", "no gore", "no daylight", "no warm sunlight"],
         state_keys=["刃没有离手", "天亮时灰雾没有散"], text=True, steps=30),

    # ============================== ep021 ==============================
    dict(ep=21, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "病态青"],
         body_image="分诊台前的队伍拐了两个弯，灰斑比两天前多了一倍；灰斑只在袖口与手背上可见，排队的人一律作剪影；灰斑边缘清晰，不扩散到衣物之外。",
         body_video="分诊台前的队伍拐过两个弯；灰斑比两天前多了一倍，只在袖口与手背上可见；排队的人一律作剪影，面部不入镜；灰斑只在袖口与手背上可见；灰斑边缘清晰，不扩散到衣物之外；本句为画外音／主观声，画面内只有拐弯的长队与剪影，不出现该角色、不给口型与面部。",
         extras=["no visible open skin lesion", "no face of the queue", "no close-up of the crowd", "no gore", "no blood"],
         state_keys=["灰斑只在袖口与手背上可见", "排队的人一律作剪影"], text=False, steps=30),
    dict(ep=21, shot_id=2, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "病态青"],
         body_image="逾期的人动作变慢，灰斑从边缘往外扩，街上的人绕着他们走；异化者只作遮挡，不给面部；灰斑以霜灰与白烟收边，边缘保持完整。",
         body_video="逾期的人动作变慢，灰斑自边缘往外扩；街上的人绕着他们走；异化者只作遮挡，不给面部；灰斑以霜灰与白烟收边，边缘保持完整。",
         extras=["no open wounds", "no blood", "no gore", "no face of the mutated", "no skin decay close-up"],
         state_keys=["异化者只作遮挡", "不给面部"], text=False, steps=30),
    dict(ep=21, shot_id=3, groups=[], char_ids=["LC", "SQC"], descs=["白色科研风衣", "数据板", "黑色战术风衣"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="厂门贴出新的告示：药剂按量分配，安全屋名额暂停发放；陆沉把净火净化排到最前，苏清辞按剩余药剂分诊；告示为中文正写、逐字可读。",
         body_video="厂门贴出新的告示：药剂按量分配，安全屋名额暂停发放；告示正文保持中文正写、逐字可读；陆沉把净火净化排到最前，苏清辞按剩余药剂分诊；两人动作幅度小，不给面部特写。",
         extras=["no garbled text", "no English-only text", "no religious iconography", "no close-up of any face", "no gore"],
         state_keys=["药剂按量分配，安全屋名额暂停发放", "把净火净化排到最前"], text=True, steps=30),
    dict(ep=21, shot_id=4, groups=["RELIG"], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "叶家青灰"],
         body_image="街口走过一列人，步子齐得像一列，袖口上是几何徽记；徽记是抽象几何，看不出任何宗教符号；视野一角的读数栏显示同屏中文「归一度 1.4%」。",
         body_video="街口走过一列人，步子齐整；袖口上的徽记是抽象几何，看不出任何宗教符号；读数栏保持「归一度 1.4%」可读；不给面部特写。",
         extras=["no face of the marching column", "no gore"],
         state_keys=["徽记是抽象几何", "看不出任何宗教符号"], text=True, steps=30),

    # ============================== ep022 ==============================
    dict(ep=22, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="城郊骨井的井架上绞盘在转，井口开始返出灰雾，作业的人只余剪影；井架在灰雾里只剩轮廓；井口返雾不含任何人体。",
         body_video="井架上的绞盘持续转动，井口开始返出灰雾；作业的人只余剪影，面部不入镜；井架在灰雾里只剩轮廓；井口返雾只有雾体；本句为画外音／主观声，画面内只有井架、绞盘与返雾，不出现该角色、不给口型与面部。",
         extras=["no face of the workers", "no close-up of the workers", "no body in the well", "no gore", "no blood"],
         state_keys=["作业的人只余剪影", "井架在灰雾里只剩轮廓"], text=False, steps=30),
    dict(ep=22, shot_id=2, groups=[], char_ids=["SQC"], descs=["数据板"], motifs=[], palette=["骨白", "云顶冷白", "墨灰暗部"],
         body_image="数据板上跳出一段持续低频，方向标指向城郊；屏幕上一段波形保持不落；屏上文字与符号一律中文正写、逐字可读。",
         body_video="数据板上跳出一段持续低频，方向标指向城郊；屏幕上一段波形保持不落、幅度稳定；屏上文字与符号保持中文正写、逐字可读；不拍持有者的面部。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no face in frame", "no gore"],
         state_keys=["跳出一段持续低频", "方向标指向城郊"], text=True, steps=30),
    dict(ep=22, shot_id=3, groups=[], char_ids=["YHY"], descs=["暗红色劲装", "黑长直发"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "暗红"],
         body_image="叶红衣带人出城查过一趟，只找到空井架和返上来的灰雾；井壁上一道新的凿痕还在掉灰，绞盘的绳缠得更深了一层；人一律只作远景轮廓。",
         body_video="镜头固定不动；井壁上一道新的凿痕还在掉灰，绞盘的绳缠得更深了一层；返上来的灰雾贴着井口；同行的人只作远景轮廓，不给面部。",
         extras=["no face of the party", "no close-up of any face", "no body in the well", "no gore", "no blood"],
         state_keys=["一道新的凿痕还在掉灰", "绳缠得更深了一层"], text=False, steps=30),
    dict(ep=22, shot_id=4, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "冷银"],
         body_image="厂内，城西方向拖回一名信使，终端还亮着；死士营从终端里取出一封未拆的密信，纸面没有署名；信纸内容不外露，只给未拆状态。",
         body_video="镜头自特写起；城西方向拖回一名信使、终端还亮着；死士营从终端里取出一封未拆的密信；信纸保持未拆状态，纸面没有署名；不给拖回者的面部。",
         extras=["no face of the messenger", "no readable private document text", "no gore", "no blood"],
         state_keys=["取出一封未拆的密信", "纸面没有署名"], text=True, steps=30),

    # ============================== ep023 ==============================
    dict(ep=23, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["骨白", "冷银", "墨灰暗部"],
         body_image="一封密信在钢桌上摊开，排版是合同的样子，条款分栏排列；纸面没有署名；条款栏位为中文正写、逐字可读。",
         body_video="镜头固定不动；一封密信摊开在桌上，排版是合同的样子，条款分栏排列；纸面没有署名；条款栏位为中文正写、逐字可读；不出现手与面部。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no readable real-world insignia", "no gore"],
         state_keys=["排版是合同的样子", "纸面没有署名"], text=True, steps=30),
    dict(ep=23, shot_id=2, groups=[], char_ids=[], descs=[], motifs=[], palette=["骨白", "云顶冷白", "墨灰暗部"],
         body_image="条款写着：云顶财阀按批次拨付安全屋配额与药剂，雾盟按批次交付高阶雾核；两行条款逐行落在纸面上；纸面正文保持中文正写、逐字可读。",
         body_video="镜头固定不动；云顶财阀按批次拨付安全屋配额与药剂、雾盟按批次交付高阶雾核两行条款逐行落在纸面上；纸面正文保持中文正写、逐字可读；不出现手与面部。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no real corporate logos", "no gore"],
         state_keys=["两行条款逐行落在纸面上"], text=True, steps=30),
    dict(ep=23, shot_id=3, groups=[], char_ids=[], descs=[], motifs=[], palette=["骨白", "冷银", "墨灰暗部"],
         body_image="交付栏翻到最后一页，只有批次编号和四个字：清退区域；整页没有一个人的名字，栏位是区域，不是人；苏清辞把自己的救治排班表摊在旁边，两张纸上的区域对上了。",
         body_video="交付栏翻到最后一页，交付栏翻到最后一页，只有批次编号和四个字：清退区域；整页没有一个人的名字，栏位是区域，不是人；救治排班表摊在旁边，两张纸上的区域对上；纸面保持中文正写、逐字可读。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no personal names on the document", "no gore"],
         state_keys=["只有批次编号和四个字：清退区域", "栏位是区域，不是人"], text=True, steps=30),
    dict(ep=23, shot_id=4, groups=[], char_ids=["LC"], descs=["右手腕黑白游龙骨纹"], motifs=["M02"], palette=["灰雾青灰", "墨灰暗部", "冷银"],
         body_image="陆沉把密信摊在面板上逐行读完，指腹在最后一行停住；视野一角的读数栏显示同屏中文「归一度 1.4%」；骨纹只走体表发光，不破体。",
         body_video="陆沉把密信摊在面板上逐行读完，指腹在最后一行停住；读数栏保持「归一度 1.4%」可读；骨纹只走体表发光、不破体；不给面部特写。",
         extras=["no skin breakage", "no bone protruding through skin", "no garbled text", "no close-up of any face", "no gore"],
         state_keys=["指腹在最后一行停住", "归一度 1.4%"], text=True, steps=30),

    # ============================== ep024 ==============================
    dict(ep=24, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["骨白", "冷银", "墨灰暗部"],
         body_image="钢桌上并排摊着两样东西：交易条款，和骨井凿进的进度；两样东西并排占满画面中部；纸面文字保持中文正写、逐字可读。",
         body_video="镜头固定不动；钢桌上并排摊着交易条款与骨井凿进的进度两样东西；两样东西并排占满画面中部；纸面文字保持中文正写、逐字可读；不出现手与面部；本句为画外音／主观声，画面内只有钢桌上的两份单据，不出现该角色、不给口型与面部。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no real corporate logos", "no gore"],
         state_keys=["两样东西并排占满画面中部"], text=True, steps=30),
    dict(ep=24, shot_id=2, groups=[], char_ids=["SQC"], descs=["数据板"], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="苏清辞在名单板前算出一行数字，是净火能覆盖的极限；名单板上的名字排成几列，数字写在最下一行；名单板上的名字与数字保持中文正写、逐字可读。",
         body_video="苏清辞在名单板前算出一行数字；名单板上的名字排成几列，数字写在最下一行；名字与数字保持中文正写、逐字可读；不拍面部。",
         extras=["no garbled text", "no English-only text", "no fake random glyphs", "no face in frame", "no gore"],
         state_keys=["算出一行数字", "数字写在最下一行"], text=True, steps=30),
    dict(ep=24, shot_id=3, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹", "双相净火(黑白火焰)"], motifs=["M01", "M02"], palette=["净火白", "净火黑", "骨白", "墨灰暗部"],
         body_image="陆沉把一枚雾核按在名单板上，灰斑从指节边缘退成浅色；黑白双焰烧过，净化结果是一缕白烟和恢复正常的手背颜色；火焰只有黑与白两色。",
         body_video="陆沉把一枚雾核按在名单板上；黑白双焰自指节边缘烧过，灰斑从指节边缘退成浅色；净化结果是一缕白烟和恢复正常的手背颜色；火焰只有黑与白两色，不出现第三种颜色。",
         extras=["no burn wound", "no blister", "no charred skin", "no blood", "no gore", "net fire illuminating more than a small contact patch of skin"],
         state_keys=["灰斑从指节边缘退成浅色", "恢复正常的手背颜色"], text=False, steps=32),
    dict(ep=24, shot_id=4, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹"], motifs=["M02"], palette=["净火白", "净火黑", "灰雾青灰", "墨灰暗部"],
         body_image="陆沉没有反驳，把名单板上的最后一行看了很久；净化区的火一直烧到天亮，名单又长了一截；视野一角的读数栏显示同屏中文「归一度 1.4%」。",
         body_video="陆沉没有反驳，把名单板上的最后一行看了很久；净化区的火一直烧到天亮，名单又长了一截；读数栏保持「归一度 1.4%」可读；火焰只有黑与白两色。",
         extras=["no third flame color", "no red flame", "no skin breakage", "no gore", "no blood"],
         state_keys=["把名单板上的最后一行看了很久", "名单又长了一截"], text=True, steps=32),
]
