#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》U02 单元 · D12 AI 提示词卡库 · 内容数据

由 scripts/build_D12.py --unit U02 调用；**改内容必须改本文件后重跑引擎，禁直接改 JSON**。

- CARDS：32 镜卡数据，逐镜对应 units/U02/D11.json 的 (ep, shot_id)。
  景别／机位／焦距／运镜／时长／取景声明／台词／音效**一律由引擎从 D11 读取**，本文件只写：
    ep, shot_id            —— 镜位
    char_ids              —— 本卡画框内出现的编号角色（只登记有编号角色，群演不入）
    descs                 —— D10 锚点表里的原样片段（V7 溯源用）
    motifs / palette      —— D10 的 motif_id 与色板名
    body_image            —— 画面主体与构图要点（≤130 字，防吃下游 H3 预算）
    body_video            —— 动作与过程要点（≤130 字）
    extras                —— 本卡专属负向词（全英文）
    state_keys            —— 否定／状态表述的关键短语，必须在 image_prompt 与 video_prompt 中都正面出现（轴②）
    text                  —— 画面内是否有可读中文（决定负向词组）
    steps                 —— 采样步数（奇观镜 32，其余 30）
"""

VERSION = "v1.4"

# ---------------------------------------------------------------- 每个场景码一份 appearance
SCENE_APPEARANCE = {
    "B-1": "废弃军工机械厂门禁区：锈蚀卷帘门与加焊闸门、垒成掩体的内侧钢架、分堆的钢材与井水桶；工业冷光，暗部保留细节。",
    "B-2": "废弃军工机械厂内圈净化区：可躺下的钢制工作台、头顶一盏冷白工业灯、地面留出白烟上浮的净空。",
    "B-3": "废弃军工机械厂内圈图纸墙与萃取线：钢桌、钉图纸的木板墙、连续运转的雾核萃取线与出料台、地面留出轮班队列与通道。",
    "B-4": "骨市黑市远景开市瞬间：电子屏与一排排摊位排面，霓虹冷色，只作开市一瞥。",
    "B-5": "废弃军工机械厂门禁区与公告投影位：可投影的旧铁皮墙、门内通道、门外远景道路；工业冷光加投影冷白。",
    "B-6": "骨市黑市交易区：摊位排面与电子屏、台面与排队区之间留出的通道宽度；霓虹冷色。",
    "B-7": "废弃军工机械厂保险柜位：可上锁的加固小间、墙面钢板与内嵌锁柜；冷白低照度。",
    "B-8": "废弃军工机械厂厂门预约位与会议室：钢门柱、可摊开大尺寸城防图的会议桌、委员会屏幕的冷金底色。",
    "B-9": "废弃军工机械厂夜场围墙与墙位、指挥舱名单位：熄灯后围墙只留应急灯低照度与贴墙阴影带；指挥舱为摊开名单的钢桌、照明压到最低。",
    "B-10": "废弃军工机械厂夜场西侧厂房与厂门：可燃的旧钢架分隔结构、可被两人抬起的隔火钢架、厂门外一段无照明暗处。",
}

# ---------------------------------------------------------------- 32 镜
CARDS = [
    # ============================== ep009 ==============================
    dict(ep=9, shot_id=1, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "薪火橙"],
         body_image="锈蚀卷帘门内侧，蓝白弧光沿门板逐寸熔接，焊缝从无到有连成一道简易闸门，火星落在水泥地上；焊花只在焊点与门板接触处留下瞬时暖色亮点，周围仍由工业冷光照明；内侧钢架被抬上架垒成掩体，钢材与井水桶分堆到内圈。",
         body_video="镜头自中远景缓慢推近；焊枪起弧，蓝白弧光逐寸推进，焊缝从无到有连成一道简易闸门，火星落在水泥地上；内侧钢架被抬上架垒成掩体，钢材与井水桶分堆到内圈；焊缝成形过程完整可见，不切成两个动作。",
         extras=["no other people in frame", "no fire beyond the welding arc", "no warm ambient color grading", "no gore", "no daylight"],
         state_keys=["焊缝从无到有连成一道简易闸门", "火星落在水泥地上"], text=False, steps=30),
    dict(ep=9, shot_id=2, groups=["CREATURE"], char_ids=["YHY", "SQC"], descs=["暗红衣", "数据板"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="厂门内侧，叶红衣一手推开侧门、一手把苏清辞连人带板拽进厂门；苏清辞怀里的数据板压在胸前、板面朝外；来人裸露的手臂与后颈覆着灰白斑块、边缘清晰；三人挤在门框内。",
         body_video="镜头随人物跟进厂门；侧门被推开，叶红衣把苏清辞连人带板拽进门内，数据板始终压在胸前、板面朝外；来人手臂与后颈的灰白斑块只在侧面露出、边缘完整；不给面部特写。",
         extras=["no close-up of any face", "no visible wounds", "no open skin lesion", "no blood", "no gore", "no crowd"],
         state_keys=["板面朝外", "灰白斑块"], text=False, steps=30),
    dict(ep=9, shot_id=3, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹", "利落短发"], motifs=["M02"], palette=["云顶冷白", "净火白", "净火黑", "墨灰暗部"],
         body_image="陆沉没看人脸，先接过数据板，指节在板背面敲了两下，视线落在板面、板上屏幕亮着；视野一角读数栏显示同屏中文「归一度 0.7%」；他右手腕的黑白游龙骨纹停在腕侧，纹路未向小臂延开。",
         body_video="先接板，指节在板背面敲了两下，视线落到亮起的板面；读数栏保持「归一度 0.7%」可读，腕侧骨纹停在原处、纹路未向小臂延开；不拍人脸。",
         extras=["no face of the rescued person", "no skin breakage", "no blood", "no gore", "no third flame color"],
         state_keys=["指节在板背面敲了两下", "归一度 0.7%", "纹路未向小臂延开"], text=True, steps=30),
    dict(ep=9, shot_id=4, groups=[], char_ids=["SQC"], descs=["数据板", "白色科研风衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="苏清辞抱着数据板退到钢架后，目光从焊门扫过持钎的队列；那排人影沉默站立，队列的脸一律不入镜；厂房纵深里的光只压出人轮廓。",
         body_video="苏清辞抱着数据板退到钢架后停住，目光自焊门扫向持钎的队列；纵深里那排人影保持沉默站立、只余轮廓，面部一律不入镜。",
         extras=["no faces in the queue", "no close-up of the crowd", "no weapon raised", "no gore", "no blood"],
         state_keys=["抱着数据板退到钢架后"], text=False, steps=30),

    # ============================== ep010 ==============================
    dict(ep=10, shot_id=1, groups=[], char_ids=["LC", "SQC"], descs=["黑色战术风衣", "数据板", "白色科研风衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="冷白工业灯下，苏清辞抱着数据板往门口走，白色科研风衣的衣摆随步子摆动；陆沉没拦也没解释，只侧身让开半步，黑色战术风衣的下摆不动；两人分列画面两侧，中间留出通道。",
         body_video="镜头跟住苏清辞向门口移动；苏清辞抱板快步走向门口、衣摆随步摆动；陆沉不拦不解释，只侧身让开半步、下摆不动；两人始终分列画面两侧，中间留出通道。",
         extras=["no confrontation pose", "no raised hand", "no other people", "no gore", "no daylight"],
         state_keys=["侧身让开半步", "中间留出通道"], text=False, steps=30),
    dict(ep=10, shot_id=2, groups=["FLAME"], char_ids=["LC"], descs=["右手腕黑白游龙骨纹", "双相净火(黑白火焰)"], motifs=["M01"], palette=["净火白", "净火黑", "骨白", "墨灰暗部"],
         body_image="钢制工作台上躺着一个人，灰斑覆满整条手臂；陆沉右手覆上那条手臂，黑白双焰贴着皮肤烧，亮区只收在掌心与手臂接触的一小片皮肤上；火焰之外的部分仍是厂房冷光；台下灰斑者的胸口起伏。",
         body_video="陆沉右手覆上灰斑手臂，黑白双焰贴着皮肤烧，亮区只收在掌心与手臂接触的一小片皮肤上，不扩散到整条手臂；周围仍是工业冷光；台下胸口起伏可见；火焰只有黑与白两色。",
         extras=["no burn wound", "no blister", "no charred skin", "no red flame", "no third flame color", "no flesh damage", "no blood", "net fire illuminating more than a small contact patch of skin"],
         state_keys=["黑白双焰贴着皮肤烧", "亮区只收在掌心与手臂接触的一小片皮肤上"], text=False, steps=32),
    dict(ep=10, shot_id=3, groups=["FLAME"], char_ids=["SQC"], descs=["白色科研风衣"], motifs=["M01"], palette=["骨白", "净火白", "墨灰暗部"],
         body_image="灰斑边缘泛起白烟，白烟自下而上散尽，灰斑退成皮肤本色；白烟散尽处露出完好的皮肤；台上的人胸口起伏缓过来，手指松开；白色科研风衣的下摆从画面右侧退出。",
         body_video="灰斑边缘泛起白烟，白烟自下而上散尽，灰斑退成皮肤本色，露出完好的皮肤；净化过程从起到尽完整可见；台上的人胸口起伏缓过来、手指松开；白色科研风衣的下摆从画面右侧退出。",
         extras=["no burn wound", "no red liquid", "no scar", "no blood", "no smoke from the person's body"],
         state_keys=["白烟自下而上散尽", "灰斑退成皮肤本色", "露出完好的皮肤"], text=False, steps=32),
    dict(ep=10, shot_id=4, groups=["FLAME"], char_ids=["LC", "SQC"], descs=["右手腕黑白游龙骨纹", "数据板"], motifs=["M02"], palette=["净火白", "净火黑", "云顶冷白"],
         body_image="陆沉的右腕骨纹从腕骨延过小臂，一路爬到手肘，黑白两色贴着皮肤表面浮出；视野一角读数栏显示同屏中文「归一度 1.0%」；苏清辞蹲下捡起数据板，抹掉屏上的旧结论。",
         body_video="骨纹从腕骨延过小臂，一路爬到手肘，走向可读；读数栏保持「归一度 1.0%」可读；苏清辞蹲下捡起数据板，抹掉屏上的旧结论。",
         extras=["no skin puncture", "no bone under the skin", "no tattoo", "no blood", "no third flame color"],
         state_keys=["从腕骨延过小臂，一路爬到手肘", "归一度 1.0%"], text=True, steps=32),

    # ============================== ep011 ==============================
    dict(ep=11, shot_id=1, groups=["REALX"], char_ids=["SQC"], descs=[], motifs=[], palette=["骨白", "灰雾青灰", "墨灰暗部"],
         body_image="钢桌上摊开一张防御图纸，图上用中文逐项标出四类标注：门禁位、承重墙、撤离通道、净水源；苏清辞的指尖点过每一项标注；纸面墨迹未干，角落有一块水渍。",
         body_video="指尖逐项点过四类中文标注——门禁位、承重墙、撤离通道、净水源，四项都要读得出；纸面墨迹未干、角落有水渍；标注保持中文正写、逐字可读。",
         extras=["no garbled text", "no English-only text", "no readable foreign script",
                "no sleeve or clothing in frame", "no face in frame", "no gore"],
         state_keys=["门禁位、承重墙、撤离通道、净水源"], text=True, steps=30),
    dict(ep=11, shot_id=2, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="图纸被钉上木板墙，钢架按图上的承重线重排成两列，墙边留出通行宽度；雾核萃取线第一次跑通，压制槽把雾核压成能量块，能量块边缘带着白霜被码上出料台。",
         body_video="镜头沿生产线横移，从压制槽一气移到出料台，压制槽把雾核压成能量块，能量块边缘带着白霜，随后码上出料台；钢架按承重线重排成两列，墙边留出通行宽度；进料口不单独入画。",
         extras=["no people in frame", "no fire", "no gore", "no readable brand marks", "no daylight"],
         state_keys=["压制槽把雾核压成能量块", "能量块边缘带着白霜"], text=False, steps=30),
    dict(ep=11, shot_id=3, groups=["RELIG"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "灰雾青灰", "墨灰暗部"],
         body_image="一排人按墙上的岗表站成两列，脚步落在同一节拍上；轮班表贴在木板墙上，栏位写着门禁、淬火、净水；视野一角的面板弹出同屏中文「新手福利期结束」；面板读数栏显示同屏中文「归一度 1.1%」。",
         body_video="一排人按岗表站成两列、脚步落在同一节拍上；轮班表上「门禁、淬火、净水」三栏中文可读；面板弹出「新手福利期结束」，读数栏保持「归一度 1.1%」；人脸不入镜。",
         extras=["no faces in frame", "no garbled text", "no English-only text", "no gore"],
         state_keys=["门禁、淬火、净水", "新手福利期结束", "归一度 1.1%"], text=True, steps=30),
    dict(ep=11, shot_id=4, groups=["REALX"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "灰雾青灰", "墨灰暗部"],
         body_image="骨市黑市的电子屏亮起，屏上滚出第一条交易信息，中文条目逐行上移；摊位排面在屏下一排排亮开，只作远景；街上人影在交易信息前聚拢。",
         body_video="电子屏逐行上移滚出第一条交易信息，中文条目保持可读；屏下摊位排面一排排亮开并只作远景，街上人影在屏前聚拢、面部不入镜。",
         extras=["no faces in the crowd", "no garbled text", "no English-only text", "no real corporate logos", "no gore"],
         state_keys=["滚出第一条交易信息"], text=True, steps=30),

    # ============================== ep012 ==============================
    dict(ep=12, shot_id=1, groups=["REAL"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "墨灰暗部", "灰雾青灰"],
         body_image="厂房内一块旧铁皮墙上投出全服公告，中文正文分栏排布，配给分级表与救治序列并排出现；公告第二栏写明生灰斑平民按废弃物资口径处理、不计入救治序列；画面只给铁皮墙与投影文字，不给发言人。",
         body_video="投影文字分栏逐行亮起，第二栏「生灰斑平民按废弃物资口径处理、不计入救治序列」保持中文正写、逐字可读；配给分级表与救治序列并排出现；画面只给铁皮墙与投影文字，不出现发言人。",
         extras=["no speaker in frame", "no garbled text", "no English-only text", "no real corporate logos", "no gore"],
         state_keys=["生灰斑平民按废弃物资口径处理、不计入救治序列"], text=True, steps=30),
    dict(ep=12, shot_id=2, groups=[], char_ids=[], descs=[], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="厂门外的道路只作远景，等药的人排成一条队；秩序队的人把队尾一批批带离，队伍散进灰雾；散开的人群里有人回头看厂门方向；所有人只作剪影，面部不入镜。",
         body_video="等药队伍在远景里被一批批带离、散进灰雾；其中有人回头看厂门方向——这一下必须清楚可见；所有人只作剪影，面部不入镜。",
         extras=["no faces in frame", "no visible wounds", "no blood", "no gore", "no conflict detail"],
         state_keys=["有人回头看厂门方向", "所有人只作剪影"], text=False, steps=30),
    dict(ep=12, shot_id=3, groups=[], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部"],
         body_image="死士营的人站在门内看着门外，人影挤在门框里；陆沉的侧影在前景，肩线压住画面一角；陆沉转头看门外的队伍。",
         body_video="门内人影挤在门框里看向门外；陆沉的前景侧影压住画面一角，随后转头看门外的队伍；人群不给面部。",
         extras=["no faces in the crowd", "no gore", "no blood"],
         state_keys=["转头看门外的队伍"], text=False, steps=30),
    dict(ep=12, shot_id=4, groups=[], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["骨白", "云顶冷白", "墨灰暗部"],
         body_image="陆沉转身把厂里被净火净化过的灰斑者叫到一起，几个人在冷白光里围成半圈，袖口都卷着；视野一角读数栏显示同屏中文「归一度 1.2%」；陆沉抬头看向门外那条被掐断的货源路。",
         body_video="几个人在冷白光里围成半圈、袖口卷起；读数栏保持「归一度 1.2%」可读；陆沉抬头看向门外那条被掐断的货源路，动作收在抬头这一下，不补名单、不给名单特写。",
         extras=["no list of names on screen", "no close-up of faces", "no scar close-up", "no blood", "no gore"],
         state_keys=["围成半圈", "归一度 1.2%", "抬头看向门外那条被掐断的货源路"], text=True, steps=30),

    # ============================== ep013 ==============================
    dict(ep=13, shot_id=1, groups=["RELIG"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "灰雾青灰", "墨灰暗部"],
         body_image="黑市摊位支起，电子屏下压着四个字「无垢净髓」；摊位前的木牌上写着以稀有材料换一次净化不收雾核；排队的人绕过摊位尾。",
         body_video="摊位支起，电子屏下方的「无垢净髓」四字与木牌上的「以稀有材料换一次净化不收雾核」保持正写可读；排队的人绕过摊位尾，摊主与排队者都不给面部特写。",
         extras=["no faces in the crowd", "no garbled text", "no English-only text", "no real corporate logos", "no gore"],
         state_keys=["无垢净髓", "以稀有材料换一次净化不收雾核"], text=True, steps=30),
    dict(ep=13, shot_id=2, groups=[], char_ids=["YHY"], descs=["影刃", "暗红衣"], motifs=[], palette=["暗红", "灰雾青灰", "墨灰暗部"],
         body_image="雾核、钢材与药剂在台面上一件件摆开，摊前的队伍绕过摊位尾排成两列；叶红衣的影刃横在台面前，刃身收着，队伍被隔成两列。",
         body_video="雾核、钢材与药剂在台面上一件件摆开；影刃横陈在台面前封住通道，刃身收着不显刃光；队伍被隔成两列，叶片与人脸不入镜。",
         extras=["no glowing blade edge", "no swinging blade", "no faces in the queue", "no gore"],
         state_keys=["刃身收着", "队伍被隔成两列"], text=False, steps=30),
    dict(ep=13, shot_id=3, groups=[], char_ids=["SQC"], descs=[], motifs=[], palette=["云顶冷白", "墨灰暗部", "骨白"],
         body_image="一枚律条被推上交易台，纹路压着冷光，条面朝上完整入画；苏清辞的手摸过纹路，指腹在纹路上停住；台面上只有这一枚实物。",
         body_video="律条被推上台、条面朝上完整入画，纹路压着冷光；苏清辞的指腹沿纹路摸过并停住；台面上只有这一枚实物，不拆用、不拆解。",
         extras=["no real-world emblem", "no readable foreign script", "no second object on the table",
                "no sleeve or clothing in frame", "no face in frame", "no gore"],
         state_keys=["条面朝上完整入画", "台面上只有这一枚实物"], text=False, steps=32),
    dict(ep=13, shot_id=4, groups=["REALX"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "墨灰暗部", "灰雾青灰"],
         body_image="厂内的保险柜门合上，律条锁进加固小间，柜门缝里最后一线冷光收掉；视野一角读数栏显示同屏中文「归一度 1.2%」；电子屏在远处的黑市方向连刷数条涨价条目。",
         body_video="保险柜门合上，柜门缝里最后一线冷光收掉；读数栏保持「归一度 1.2%」可读；远处黑市方向的电子屏连刷数条涨价条目；不给拆用画面。",
         extras=["no lockpicking detail", "no garbled text", "no weapon", "no real corporate logos", "no gore"],
         state_keys=["柜门缝里最后一线冷光收掉", "归一度 1.2%"], text=True, steps=30),

    # ============================== ep014 ==============================
    dict(ep=14, shot_id=1, groups=["REALX"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "灰雾青灰", "墨灰暗部"],
         body_image="黑市摊位的货架全空，断供通知压在空台面上；排队的人看着空架散开，电子屏上滚着涨价条目；陆沉的摊位只剩一张木牌。",
         body_video="摊前的货架全空，断供通知压在空台面上；排队的人看着空架散开；后方电子屏滚着涨价条目（只作远景）；陆沉的摊位只剩一张木牌。",
         extras=["no faces in the crowd", "no garbled text", "no real corporate logos", "no gore"],
         state_keys=["货架全空", "断供通知压在空台面上"], text=True, steps=30),
    dict(ep=14, shot_id=2, groups=["REALX"], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["灰雾青灰", "墨灰暗部", "骨白"],
         body_image="厂门内侧的钢门柱上被钉上一块木牌，牌面写着预约排号、每日限二十；陆沉把木牌按正，手掌在牌面上停了一下；门外灰雾里排着长队。",
         body_video="木牌被钉上钢门柱，陆沉把木牌按正并停住一拍；牌面中文「预约排号、每日限二十」保持正写可读；门外灰雾里的长队只作远景剪影。",
         extras=["no faces in the queue", "no garbled text", "no blood", "no gore"],
         state_keys=["预约排号、每日限二十", "把木牌按正"], text=True, steps=30),
    dict(ep=14, shot_id=3, groups=["REAL"], char_ids=[], descs=[], motifs=[], palette=["琥珀", "云顶深蓝", "云顶冷白", "墨灰暗部"],
         body_image="会议桌上摊开一张配额名单，机械厂那一行后面没有人落笔，空白的签名位压着纸面；委员会屏幕在另一侧亮起，冷金底色上一列成本条目停在最后一栏，最后一栏数字没有合上。",
         body_video="配额名单摊在桌面，机械厂那一行的空白签名位压着纸面、没有人落笔；另一侧委员会屏幕亮起，冷金底色上一列成本条目停在最后一栏，最后一栏数字没有合上——这一状态必须完整可见。",
         extras=["no scrolling cost entries", "no garbled text", "no English-only text", "no faces in frame", "no gore"],
         state_keys=["最后一栏数字没有合上", "没有人落笔"], text=True, steps=30),
    dict(ep=14, shot_id=4, groups=["REAL"], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["骨白", "墨灰暗部", "云顶深蓝"],
         body_image="会议桌另一头摊开一张城防图，图上标着机械厂的名字；一支笔的笔尖点在那个名字上，旁边按着一枚继承人的印；陆沉的肩背在画面近处；视野一角读数栏显示同屏中文「归一度 1.3%」。",
         body_video="一支笔的笔尖点在那个名字上、点住不移开，旁边压着一枚继承人的印；陆沉的肩背只占画面近处一侧、不压主体；读数栏保持「归一度 1.3%」可读；不出现现实机构标识与外文字样。",
         extras=["no real-world insignia", "no garbled text", "no English-only text", "no gore"],
         state_keys=["笔尖点在那个名字上", "归一度 1.3%"], text=True, steps=30),

    # ============================== ep015 ==============================
    dict(ep=15, shot_id=1, groups=["REALX"], char_ids=["YJ-ES"], descs=["象牙白短外套与黑色硬质肩章"], motifs=[], palette=["云顶深蓝", "琥珀", "墨灰暗部"],
         body_image="指挥舱的钢桌上摊开名单与进场顺序，照明压到最低；叶承钧立在桌后，象牙白短外套与黑色硬质肩章在暗光里只剩轮廓；他的指尖压在名单最后几个名字上。",
         body_video="照明压到最低，名单与进场顺序摊在钢桌上；叶承钧立在桌后只剩轮廓，指尖压在名单最后几个名字上；名单上的名字不作特写、不给可辨字迹。",
         extras=["no readable names on the list", "no garbled text", "no frontal portrait",
                "no real corporate logos", "no gore"],
         state_keys=["指尖压在名单最后几个名字上"], text=True, steps=30),
    dict(ep=15, shot_id=2, groups=[], char_ids=[], descs=[], motifs=[], palette=["墨灰暗部", "灰雾青灰"],
         body_image="逃难人流涌进厂区外圈，旧棉衣混在人流里；一件旧棉衣的袖口下露出一角制式护具，很快被袖子盖住；所有人只作暗处剪影，不给面部与护具细节特写。",
         body_video="逃难人流涌进厂区外圈，旧棉衣混在其中；其中一件旧棉衣的袖口下露出一角制式护具，很快被袖子盖住；所有人只作暗处剪影，面部与护具都不给特写。",
         extras=["no faces in the crowd", "no close-up of the armor", "no weapon detail", "no gore", "no blood"],
         state_keys=["袖口下露出一角制式护具，很快被袖子盖住", "所有人只作暗处剪影"], text=False, steps=30),
    dict(ep=15, shot_id=3, groups=[], char_ids=["SQC"], descs=["数据板"], motifs=[], palette=["云顶冷白", "墨灰暗部"],
         body_image="数据板被苏清辞托在掌心，屏上的频谱跳出不齐的噪声，波峰疏密不匀；屏边映出她的指尖，指尖压着板沿。",
         body_video="数据板频谱跳出不齐的噪声，波峰疏密不匀，噪声形状必须看得清；屏边映出指尖、指尖压着板沿；苏清辞的面部不入镜。",
         extras=["no regular waveform", "no garbled text", "no face in frame",
                "no sleeve or clothing in frame", "no gore"],
         state_keys=["频谱跳出不齐的噪声，波峰疏密不匀"], text=True, steps=30),
    dict(ep=15, shot_id=4, groups=[], char_ids=["LC", "YHY"], descs=["黑色战术风衣", "影刃", "暗红衣"], motifs=[], palette=["墨灰暗部", "暗红", "灰雾青灰"],
         body_image="熄灯后的厂区只留应急灯的低照度，围墙上多出一排不该在的影子，影子的数量与站位在墙上一眼可数；钢钎与弹药沿墙位拆开分到岗上；叶红衣独自巡墙，影刃出鞘一半又按了回去；视野一角读数栏显示同屏中文「归一度 1.3%」。",
         body_video="熄灯后厂区只剩应急灯低照度，围墙上那排不该在的影子数量与站位一眼可数；钢钎与弹药沿墙位分发到位；叶红衣独自巡墙，影刃出鞘一半又按了回去、刃身不显刃光；读数栏保持「归一度 1.3%」可读。",
         extras=["no glowing blade edge", "no faces of the shadow figures", "no gore", "no blood", "no warm ambient light"],
         state_keys=["一眼可数", "影刃出鞘一半又按了回去", "归一度 1.3%"], text=True, steps=30),

    # ============================== ep016 ==============================
    dict(ep=16, shot_id=1, groups=["CREATURE"], char_ids=[], descs=[], motifs=[], palette=["云顶冷白", "墨灰暗部", "灰雾青灰"],
         body_image="视野正中浮出面板，同屏中文「归档大限日：十四天大限」与「逾期未处理的灰斑开始异化」两行字逐行亮起；面板下方是厂房的一角，远处第一处火光亮起。",
         body_video="面板在视野正中逐行亮起，「归档大限日：十四天大限」与「逾期未处理的灰斑开始异化」两行中文保持可读；面板下方是厂房一角，远处第一处火光亮起；不拍任何人体异化画面。",
         extras=["no transformed body", "no gray-skin transformation on screen", "no gore", "no blood",
                "no garbled text", "no real corporate logos"],
         state_keys=["归档大限日：十四天大限", "逾期未处理的灰斑开始异化"], text=True, steps=30),
    dict(ep=16, shot_id=2, groups=["FIRE"], char_ids=[], descs=[], motifs=[], palette=["薪火橙", "墨灰暗部", "灰雾青灰"],
         body_image="三处火头在厂区不同位置窜起，围墙外一处、西侧厂房两处；火线沿厂房的分隔结构延伸，把厂区切成几块；退路只剩一条窄道；厂门在画面右侧亮着。",
         body_video="三处火头同时窜起——围墙外一处、西侧厂房两处，数量与位置在远景里可数；火线沿厂房分隔结构延伸、把厂区切成几块，退路只剩一条窄道，厂门在画面右侧亮着；火场只以火光、烟与钢架残骸呈现。",
         extras=["no human body burning", "no burning person", "no gore", "no blood", "no red liquid", "no crowd close-up"],
         state_keys=["三处火头", "退路只剩一条窄道"], text=False, steps=30),
    dict(ep=16, shot_id=3, groups=["FIRE"], char_ids=["LC"], descs=["黑色战术风衣"], motifs=[], palette=["薪火橙", "墨灰暗部", "灰雾青灰"],
         body_image="两副钢架被抬起来横在火线前，两架之间留出一道缺口；被围的人从缺口穿过去，队伍在烟里排成一线；陆沉带人把最后一个被围的人拽出厂房。",
         body_video="两副钢架被抬起横在火线前、两架之间留出一道缺口，缺口够人一个一个过；镜头跟住人流从缺口穿行，被围的人从缺口穿过、队伍在烟里排成一线；陆沉带人把最后一个被围的人拽出厂房；人一律作远景轮廓，不拍人体细节。",
         extras=["no human body burning", "no gore", "no blood", "no red liquid", "no faces in the crowd"],
         state_keys=["两架之间留出一道缺口", "队伍在烟里排成一线"], text=False, steps=30),
    dict(ep=16, shot_id=4, groups=["FIRE"], char_ids=["YHY"], descs=["影刃", "暗红衣"], motifs=[], palette=["暗红", "灰雾青灰", "墨灰暗部"],
         body_image="厂门外一段暗处没有灯，叶红衣站在路口，暗红劲装在暗光里只剩轮廓；影刃横在路口中央，刃身不显刃光；暗杀组领头人停在路口对面，脚下是压灭的火星；白日忽然转黑，灰雾天幕压到厂房上方；视野一角读数栏显示同屏中文「归一度 1.4%」。",
         body_video="叶红衣站在无照明的厂门外暗处，暗红劲装只剩轮廓，影刃横在路口中央、刃身不显刃光；对面领头人只作剪影、脚下是压灭的火星；白日忽然转黑，灰雾天幕压到厂房上方；读数栏保持「归一度 1.4%」可读。",
         extras=["no glowing blade edge", "no face of the assassin", "no gore", "no blood", "no warm ambient light"],
         state_keys=["影刃横在路口中央", "白日忽然转黑，灰雾天幕压到厂房上方", "归一度 1.4%"], text=True, steps=30),
]

# ---------------------------------------------------------------- 轴②反向守卫：相反过程词
OPPOSITES = {
    "ep11_s1": ["墨迹已干", "墨迹干透", "字迹干透"],
    "ep10_s2": ["整条手臂燃烧", "整条手臂烧起", "全身燃起", "火势蔓延"],
    "ep13_s2": ["刃身出鞘", "完全出鞘", "刃光显露"],
    "ep13_s3": ["第二枚", "多枚律条", "几枚实物"],
    "ep14_s1": ["货架摆满", "堆满货物", "货架空置"],
    "ep14_s3": ["滚过", "划过", "掠过", "翻过去"],
    "ep15_s4": ["完全出鞘", "刃身出鞘", "整柄出鞘"],
    "ep16_s2": ["退路宽敞", "多条退路", "退路畅通"],
    "ep16_s3": ["严丝合缝", "完全封死", "没有缺口"],
    "ep12_s2": ["始终面朝前方", "没有回头"],
}
