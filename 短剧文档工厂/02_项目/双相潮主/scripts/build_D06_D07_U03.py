#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
build_D06_D07_U03.py —— 故事架构：U03 单元 D06（章节结构）+ D07（逐集梗概）落盘脚本

为什么是脚本而不是手写 JSON（Q40 同型 · 本岗纪律）：
  「version 字面量写在脚本里，JSON 随之变；**禁手写 JSON**（手改会被重跑覆盖，且 diff 工具
   会把 version 当派生量静默放过 —— D18 Q82 已踩坑）」。
  U01／U02 的 D06／D07 为手写 JSON（`scripts/` 内**无** D06／D07 现役构建脚本，已回盘确认），
  故本岗自建带断言的落盘脚本，作为 U03 起的唯一落盘通道。

落盘范围（本岗交付物）：units/U03/D06.json ＋ units/U03/D07.json（ep017–024）。
**不写** project.json／00_项目索引.md／D18／03_规格／04_工具／他岗交付物。

内容真源（脚本内逐条断言，不靠自觉）：
  ① 集级 SSOT：《逐集内容概述.md》U03 段（L30–L38）—— 每集标题钩子逐字回源核对；
  ② 单元钩子链：project.json units[] —— U03.first_hook＝U02.last_hook、U03.last_hook＝U04.first_hook；
     **边界逐字相等**（不只是 V8 的「前 6 字包含」判据）；
  ③ 伏笔：《脉络确认.md》§五 伏笔表 —— F09 埋 ep016 → 收 ep021；F02 埋 ep023 → 收 ep037(U05)；
  ④ 归一度：D05 power_system.gauge_rule 三真规则 —— 锚点集精确命中／非锚点集落相邻锚点闭区间／
     逐集单调不减；**ep024 及以前不得出现 1.5%**（ep026 才是 1.5% 锚点）；
  ⑤ 术语：D05.glossary[].forbidden_synonyms（全 126 条）＋ 03_规格/rules.json forbidden_words（27 条）
     ＋ 未命名期（ep013–ep040）专名禁写 ＋ 「阎王」及同义写法；
  ⑥ 合规：D03 red_lines R01（去宗教化）／R02（暴力表达）／R08（零血腥）—— 唯一暴力出口＝
     「溃散为灰烬光尘」（D05 first_use_ep=17，本单元正是首用集）；
  ⑦ 节拍：Bxx 标注以《逐集内容概述》为准（B07@ep018、B08@ep023），与 D03 beat_risk_map 的
     粗粒度 eps 窗口不一致 → **按概述执行并登记为发现项**（见台账 §104.33）。

用法：
  python3 scripts/build_D06_D07_U03.py --project 02_项目/双相潮主 [--dry-run] [--force]
退出码：0 = 已落盘或幂等无操作；1 = 断言失败／中止（不写盘）。
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────
D06_VERSION = "v1.1"
D07_VERSION = "v1.1"
STATUS = "in_review"
UNIT = "U03"
EPS = list(range(17, 25))            # ep017–ep024
GAUGE = "1.4%"                       # 归一度读数（见口径说明）
SOURCE_EPISODES = "/Users/ezreal/projects/小说创作/双相潮主/01_漫剧策划/逐集内容概述.md"

# D04 角色 id（仅用于断言角色存在）
D04_IDS = ["LC", "YHY", "SQC", "YJ-JZ", "YJ-ES", "WM-SZ", "YD-GC"]
ROLE = {
    "LC": "主角",
    "YHY": "盟友·死士营头领",
    "SQC": "盟友·逃亡科学家",
    "YJ-JZ": "反派·叶家之主",
    "YJ-ES": "反派·叶家指定继承人",
    "WM-SZ": "反派·雾盟首座",
    "YD-GC": "反派·云顶财阀资源配置委员会负责人",
}

# 未命名期（ep013–ep040）该物件只有画面特征、没有名称 —— 台词面与字幕面禁其专名写法
UNNAMED_PERIOD_FORBIDDEN = ["律条", "骨签", "规则石", "低阶律条", "普通律条", "天律"]

# 「阎王」及同义写法（D05/D04 口径：统一为「我救下的人，谁也带不走。」）
YANWANG_FORBIDDEN = ["阎王", "阎君", "阎罗", "冥王", "死神", "死灵", "阴曹", "地府", "鬼差",
                     "投胎", "黄泉", "阴间", "勾魂", "索命", "判官"]

# 民间信仰／邪教化词（D03 R01 禁词）
R01_FORBIDDEN = ["教皇", "教主", "教义", "教众", "狂信徒", "飞升", "神恩", "归一之眼",
                 "祷告", "洗礼", "皈依", "圣光", "法衣", "念珠", "祭坛", "教宗",
                 "大主教", "主教", "布道", "传道", "诵读"]

# 本单元专属禁写（含首用集地板与档位口径）
UNIT_SPECIFIC_FORBIDDEN = [
    "薪火城",      # D05 first_use_ep=33，ep024 及以前不得出现
    "基地",        # 薪火城 的 forbidden_synonym
    "据点城",      # 薪火城 的 forbidden_synonym
    "影刃封路",    # D05 first_use_ep=37，ep037 才是首用集（U02 ep016 的用法属既有缺陷，见台账）
    "叶家二少",    # project.json N_naming三处 ②：统一为「叶承钧」
    "叶二少",      # 同上
]

# ─────────────────────────────────────────────────────────────
# 内容数据（唯一真源在本脚本内；JSON 由脚本生成）
# ─────────────────────────────────────────────────────────────
D06_EPISODES = [
    {
        "ep": 17,
        "title": "暗夜修罗",
        "beats": ["爽点", "转折"],
        "hook_in": "叶红衣迎战，大限夜灰雾待爆",
        "hook_out": "陆沉骨威全开：影刃切断了最后一个退路，陆沉从厂门阴影里走出来",
        "emotion_goal": "狠·反杀",
        "logline": "大限夜的火还没灭，暗杀组已经围住机械厂；叶红衣独自迎上去，影刃过处刺客溃散为灰烬光尘，最后一步，陆沉从厂门阴影里走出来",
        "must_happen": [
            "大限夜的火还没灭，暗杀组在机械厂门外合围，叶红衣独自迎上",
            "影刃切过，围上来的刺客逐个溃散为灰烬光尘，不呈现人体与创口",
            "叶承钧被震退到街口暗处，退路被封死",
            "陆沉从厂门阴影里走出来，骨威全开压住整条街面",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["YHY", "YJ-ES", "LC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "情绪",
        "hook_type_reason": "hook_out 落在**燃点**：骨威全开、切断退路、从阴影里走出来——爽感兑现。",
    },
    {
        "ep": 18,
        "title": "骨威",
        "beat_ids": ["B07"],
        "beats": ["爽点"],
        "hook_in": "陆沉骨威全开：影刃切断了最后一个退路，陆沉从厂门阴影里走出来",
        "hook_out": "陆沉取下叶家暗杀组主谋的那枚身份铭牌：最后一个刺客散成灰烬光尘，灰烬落定处留下两件金属件——主谋的身份铭牌与敌酋纹章",
        "emotion_goal": "碾压·立威",
        "logline": "陆沉骨威全开，围上来的刺客在厂门外尽数溃散为灰烬光尘；灰烬落定，他从主谋留下的身份铭牌与敌酋纹章上取下那枚身份铭牌",
        "must_happen": [
            "陆沉骨威全开，骨纹自右腕骨一路亮到小臂，整条街面被压住",
            "围攻的刺客逐个溃散为灰烬光尘，叶承钧也散在灰烬光尘里，不呈现人体与创口",
            "灰烬落定后只剩两件金属件：主谋的身份铭牌与敌酋纹章，被陆沉取下",
            "苏清辞在数据板上核对频谱：厂区外已经找不到多余的心跳信号",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "YJ-ES", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "信息",
        "hook_type_reason": "hook_out 落在**新线索**：留下主谋身份铭牌**与敌酋纹章**，敌酋第一次有了可查的符号。",
    },
    {
        "ep": 19,
        "title": "悬铭立旗",
        "beats": ["爽点", "转折"],
        "hook_in": "陆沉取下叶家暗杀组主谋的那枚身份铭牌：最后一个刺客散成灰烬光尘，灰烬落定处留下两件金属件——主谋的身份铭牌与敌酋纹章",
        "hook_out": "四方流民涌来：天还没亮，四面八方的流民已经沿着灰雾里的车辙往机械厂方向涌",
        "emotion_goal": "立威·震动",
        "logline": "陆沉把主谋的身份铭牌与敌酋纹章悬上机械厂大门，立起一面铁血战旗；旗杆刚压进石缝，四方的流民已经沿着车辙涌来",
        "must_happen": [
            "身份铭牌与敌酋纹章被悬上机械厂大门，只挂铭牌与纹章，不呈现人体",
            "死士营立起铁血战旗，旗面写「踏入此线者死」",
            "叶红衣把旗杆压进门槛石缝，在旗边立下那句话：谁敢对陆沉露獠牙，我必先摘下他的身份铭牌",
            "苏清辞把铭牌编号抄进数据板：这一夜之后，这块牌子的编号会传遍全城",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "情绪",
        "hook_type_reason": "hook_out 落在**人心向附**：四面流民涌向机械厂，是被认可的情绪兑现。",
    },
    {
        "ep": 20,
        "title": "人潮",
        "beats": ["爽点", "转折"],
        "hook_in": "四方流民涌来：天还没亮，四面八方的流民已经沿着灰雾里的车辙往机械厂方向涌",
        "hook_out": "大限夜已过，全城仍未脱离灰雾：灰雾压了一整夜没有散，街面上还是灰的",
        "emotion_goal": "涌·膨胀",
        "logline": "立旗之后第一批流民涌到机械厂门口，四面八方的人跟着车辙找来；人越来越多，口粮、棚子与守门的规矩同时压到陆沉身上",
        "must_happen": [
            "流民沿灰雾里的车辙涌向机械厂，队伍从厂门一直排到路口",
            "陆沉开门收人，苏清辞按灰斑轻重分诊，净火净化排在最前面",
            "死士营第一次按名册点人，棚区不够，口粮与弹药按人头见底",
            "叶红衣把门禁改成两班，刃不离手",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "危机",
        "hook_type_reason": "hook_out 落在**规则失效**：大限夜已过而灰雾不散，靠山塌了，威胁升级。",
    },
    {
        "ep": 21,
        "title": "善后",
        "beats": ["回收", "转折"],
        "hook_in": "大限夜已过，全城仍未脱离灰雾：灰雾压了一整夜没有散，街面上还是灰的",
        "hook_out": "雾盟现身：灰雾里第一次浮出同心潮纹的标记，一行人从街口走过，步子齐得像一列",
        "emotion_goal": "压·恐慌",
        "logline": "大限已过，逾期没管的灰斑在一夜之间暴增，恐慌从街上漫进机械厂；同一刻，灰雾里第一次浮出同心潮纹的标记",
        "must_happen": [
            "大限过去两天，逾期未处理的灰斑成批暴增，苏清辞的分诊台前排起长队",
            "逾期的人开始异化：动作变慢，灰斑从边缘往外扩，街上的人绕着他们走",
            "全城恐慌：药价与安全屋的门槛一起抬高，机械厂门口贴出新的告示",
            "陆沉把净火净化排到最前，苏清辞按剩余药剂分诊",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": "F09", "pending_unit": None},
        "hook_type": "信息",
        "hook_type_reason": "hook_out 落在**新势力亮相**：同心潮纹标记浮出，第三方第一次现身。",
    },
    {
        "ep": 22,
        "title": "凿井",
        "beats": ["铺垫", "转折"],
        "hook_in": "雾盟现身：灰雾里第一次浮出同心潮纹的标记，一行人从街口走过，步子齐得像一列",
        "hook_out": "陆沉截获密信：死士营在城西截下一名雾盟信使，苏清辞从他的终端里读出一封未拆的密信",
        "emotion_goal": "阴·蓄势",
        "logline": "大限的余波还没散，雾盟已经在城郊的骨井上凿开新的口子，蓄积的灰雾顺着井壁往上返；同一夜，陆沉截下一封写着交易条款的密信",
        "must_happen": [
            "远景：城郊骨井的井架上，雾盟的人正往下凿，井口开始返出灰雾",
            "苏清辞在数据板上发现一段持续低频：方向在城郊，节律与凿进灰雾层一致",
            "叶红衣带人出城查过一趟，只找到空井架和返上来的灰雾，人已经撤走",
            "死士营在城西截下一名雾盟信使，他的终端里存着一封未拆的密信",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "悬念",
        "hook_type_reason": "hook_out 落在**未拆的信**：读出来但没说是写了什么。",
    },
    {
        "ep": 23,
        "title": "密信",
        "beat_ids": ["B08"],
        "beats": ["转折", "伏笔"],
        "hook_in": "陆沉截获密信：死士营在城西截下一名雾盟信使，苏清辞从他的终端里读出一封未拆的密信",
        "hook_out": "密信内容触目惊心：条款里没有一句是关于救人，只有一行一行的高阶雾核数目",
        "emotion_goal": "寒·背叛",
        "logline": "密信是一份交易条款：云顶财阀按批次拨付安全屋配额与药剂，换雾盟按批次交付高阶雾核；而雾盟交付的方式，是把平民从名单上清出去",
        "must_happen": [
            "密信按商业合同的口径写成：云顶财阀拨付安全屋配额与药剂，雾盟按批次交付高阶雾核",
            "交付栏只写批次编号与「清退区域」四个字，没有一个姓名",
            "苏清辞把自己的救治排班表摊在旁边对照：被清退的区域，正是机械厂要接的那一片",
            "陆沉把密信摊在面板上逐行读完，指腹在最后一行停住",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": "F02", "payoff": None, "pending_unit": "U05"},
        "hook_type": "反转",
        "hook_type_reason": "hook_out 落在**信仰被推翻**：条款里没有一句救人，只有雾核数目——他救人，对方牟利，认知整个翻面。",
    },
    {
        "ep": 24,
        "title": "双潮",
        "beats": ["转折", "铺垫"],
        "hook_in": "密信内容触目惊心：条款里没有一句是关于救人，只有一行一行的高阶雾核数目",
        "hook_out": "陆沉日夜焚斑救人数万",
        "emotion_goal": "决·沉重",
        "logline": "交易条款把两件事并成一件：财阀拿药换雾核，雾盟拿平民换雾核，而骨井里蓄的灰雾只等第二次引爆；陆沉决定先救人——从今夜起不熄净火，一个一个把名单上的人划掉",
        "must_happen": [
            "陆沉把交易条款和骨井的进度并排看：第二次引爆只是时间问题",
            "苏清辞算出净火能覆盖的极限：按现在的净化速度，全城的灰斑要净到什么时候",
            "陆沉下令：从今夜起不熄净火，优先净名单上最重的那一批",
            "叶红衣把大门的门禁再压一遍：从今夜起，进来的每一个名字都算在陆沉头上",
            "面板归一度读数 1.4%",
        ],
        "locations": ["废弃军工机械厂"],
        "characters": ["LC", "YHY", "SQC"],
        "duration_sec": 45,
        "foreshadow": {"plant": None, "payoff": None, "pending_unit": None},
        "hook_type": "情绪",
        "hook_type_reason": "hook_out 落在**代价的重量**：日夜焚斑救人数万，代价是命在烧。",
    },
]

D07_EPISODES = [
    {
        "ep": 17,
        "story_time": "灾变第 14 日 21:45（大限夜·暗杀组合围）",
        "present_characters": ["YHY", "YJ-ES", "LC"],
        "carry_over": "承接上集钩子：叶红衣迎战、大限夜灰雾待爆——她一个人能不能扛住整支暗杀组？陆沉什么时候出手？",
        "answer": "扛住了，但只是半程：叶红衣以影刃切路，围上来的刺客逐个溃散为灰烬光尘，叶承钧被震退到街口暗处、退路被封死；陆沉在最后一步从厂门阴影里走出来，骨威全开压住整条街面。",
        "cost": "出手就是亮底牌：陆沉一走出厂门，全城都知道这厂里有能压住整条街的人——叶家的下一次不会只派一支暗杀组；而被震退的叶承钧还活着站在暗处，这笔账没有结清。",
        "emotion_goal": "狠·反杀",
        "scenes": [
            {"code": "B-11", "location": "废弃军工机械厂", "time": "21:45-22:30", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·合围", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "厂门外火光未灭，十几条影子从灰雾里压过来，影刃横在身前"},
            {"index": 2, "name": "推进·穿行", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "影刃切过，围上来的影子一个个散成灰烬光尘，街面上只剩落灰"},
            {"index": 3, "name": "转折·震退", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "主谋被震退到街口暗处，退路一寸寸封死"},
            {"index": 4, "name": "收钩·骨威", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "厂门阴影里走出一个人，骨纹自右腕骨亮起，整条街面被压住"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（夜·厂门外街面与门禁区）",
             "要点": "厂门外一段可供十来人合围的街面；照明只靠厂内应急灯与残余火光；"
                     "街面留出影刃穿行的空当；敌人消散统一为灰烬光尘，不呈现人体细节与残骸"},
        ],
        "open_questions": [],
    },
    {
        "ep": 18,
        "story_time": "灾变第 14 日 22:30（骨威全开）",
        "present_characters": ["LC", "YHY", "YJ-ES", "SQC"],
        "carry_over": "承接上集钩子：陆沉骨威全开——这一下能不能把整条街压住？压住之后，暗杀组还剩谁？",
        "answer": "压住了：围攻的刺客逐个溃散为灰烬光尘，主谋也散在灰烬光尘里；灰烬落定处只剩两件金属件——身份铭牌与敌酋纹章，被陆沉取下；数据板上的多余心跳信号同时全部消失。",
        "cost": "全歼换来的是一次暴露：骨威全开让整个城都看见了机械厂的底牌，也把陆沉的骨纹推进了所有人眼里——下一次来的不会再是刺客，是带着配额和武装的整支队伍。",
        "emotion_goal": "碾压·立威",
        "scenes": [
            {"code": "B-12", "location": "废弃军工机械厂", "time": "22:30-23:15", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·压街", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "骨纹自右腕骨一路亮到小臂，压在街面上，灰雾被压得下沉"},
            {"index": 2, "name": "推进·溃散", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "围上来的人一个个散成灰烬光尘，街面只剩落灰与安静"},
            {"index": 3, "name": "转折·数据板", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "数据板上的频谱一条条平下去，多余的心跳信号全部消失"},
            {"index": 4, "name": "收钩·取牌", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "灰烬落定，两件金属件被取下：身份铭牌与敌酋纹章"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（夜·厂门外街面与铭牌落点）",
             "要点": "街面留出骨威压制的纵深；敌人消散为灰烬光尘、地面积灰不呈现残骸；"
                     "身份铭牌与敌酋纹章为可近拍的金属件，单独出现、不带人体"},
        ],
        "open_questions": [],
    },
    {
        "ep": 19,
        "story_time": "灾变第 14 日 23:15（悬铭立旗）",
        "present_characters": ["LC", "YHY", "SQC"],
        "carry_over": "承接上集钩子：陆沉取下主谋的身份铭牌——一枚铭牌能做什么？",
        "answer": "做成一面旗：身份铭牌与敌酋纹章被挂上机械厂大门，铁血战旗同时立起，旗面八个字——踏入此线者死。",
        "cost": "立威是把所有视线都招到自己门口的买卖：铭牌挂出去的第二天，全城都知道这厂里有人敢把叶家的东西当战利品；牌挂得越高，树敌越多，下一场来的就不是一支暗杀组。",
        "emotion_goal": "立威·震动",
        "scenes": [
            {"code": "B-13", "location": "废弃军工机械厂", "time": "23:15-24:00", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·挂牌", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "两件金属件被挂上门柱，只挂铭牌与纹章"},
            {"index": 2, "name": "推进·立旗", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "旗杆压进门槛石缝，旗面在灰雾里立住"},
            {"index": 3, "name": "转折·立话", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "她在旗边立下那句话，声音压过厂外的风"},
            {"index": 4, "name": "收钩·人潮", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "天还没亮，四方的车辙从灰雾里压向机械厂"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（夜·大门门柱与旗杆位）",
             "要点": "门柱可挂金属铭牌与纹章；旗杆需两人合抱、底部有石缝可插；"
                     "大门内外两侧留出可站岗的宽度；旗面文字为中文、只出现一次"},
        ],
        "open_questions": [],
    },
    {
        "ep": 20,
        "story_time": "灾变第 15 日 06:30（流民涌到）",
        "present_characters": ["LC", "YHY", "SQC"],
        "carry_over": "承接上集钩子：四方流民涌来——开门还是不开？开门的代价谁来付？",
        "answer": "开：陆沉开门收人，苏清辞按灰斑轻重分诊、净火排在最前；死士营第一次按名册点人，棚区、口粮与弹药同时见底。",
        "cost": "收人就是收账：棚区不够住、口粮按人头见底、守门的规矩刚立就被人数压弯；陆沉从这天起欠下的不是雾核，是几千张嘴和一整套他还没学会的治理。",
        "emotion_goal": "涌·膨胀",
        "scenes": [
            {"code": "B-14", "location": "废弃军工机械厂", "time": "06:30-07:15", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·排队", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "队伍从厂门一直排到路口，车辙压进灰雾里"},
            {"index": 2, "name": "推进·分诊", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "分诊台前按灰斑轻重分出两列，净火排在最前面"},
            {"index": 3, "name": "转折·见底", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "名册点到最后一行，棚区不够，口粮和弹药按人头见底"},
            {"index": 4, "name": "收钩·灰雾", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "天亮时灰雾没有散，街面上还是灰的"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（晨·厂门登记位与分诊台）",
             "要点": "厂门内侧一处可站人登记的宽位；分诊台按轻重分两列；"
                     "棚区只作远景，不建立完整场景；人多为远景剪影，不给面部特写"},
        ],
        "open_questions": [],
    },
    {
        "ep": 21,
        "story_time": "灾变第 16 日 08:00（大限善后·灰斑暴增）",
        "present_characters": ["LC", "YHY", "SQC"],
        "carry_over": "承接上集钩子：大限夜已过，全城仍未脱离灰雾——大限过了，城里的人就安全了吗？",
        "answer": "没有安全：逾期未处理的灰斑成批暴增，街上开始有人异化，药价与安全屋的门槛一起抬高；恐慌从街上漫进机械厂，分诊台前的队越排越长。",
        "cost": "大限是替所有人设的期限，过了这条线，没被救下的人开始异化，而能救命的净火只够排最前面的一批——陆沉第一次要当着流民的面决定，谁排在前面、谁排在后面。",
        "emotion_goal": "压·恐慌",
        "scenes": [
            {"code": "B-15", "location": "废弃军工机械厂", "time": "08:00-08:45", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·长队", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "分诊台前的队伍拐了两个弯，灰斑比两天前多了一倍"},
            {"index": 2, "name": "推进·异变", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "逾期的人动作变慢，街上的人绕着他们走"},
            {"index": 3, "name": "转折·涨价", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "药价与安全屋的门槛一起抬高，告示贴上厂门"},
            {"index": 4, "name": "收钩·潮纹", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "街口走过一列人，步子齐得像一列，袖口上是几何徽记"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（晨·分诊台与门禁区）",
             "要点": "分诊台前可排长队；街面只作远景；"
                     "异化者一律远景、遮挡，不呈现人体细节；徽记为抽象几何、无宗教符号"},
        ],
        "open_questions": [],
    },
    {
        "ep": 22,
        "story_time": "灾变第 17 日 21:00（城郊凿井）",
        "present_characters": ["LC", "YHY", "SQC"],
        "carry_over": "承接上集钩子：雾盟现身——他们要干什么？",
        "answer": "凿井：城郊骨井上，雾盟借大限余波往下凿，井口开始返出灰雾；叶红衣出城查过一趟，只找到空井架和返上来的灰雾。苏清辞在数据板那段持续低频里确认了凿井的节律；同一夜，死士营在城西截下一名雾盟信使，终端里存着一封未拆的密信。",
        "cost": "查得到位置、追不上人：雾盟每一步都留一半，苏清辞只能算出方向和节律；等死士营把信使截下，井已经凿到第三层，而他们连凿井的人长什么样都没看见。",
        "emotion_goal": "阴·蓄势",
        # 场景边界必须落在四段制段界上（0/12/25/38/45），否则某一段会横跨两个场景、
        # 下游 D11「镜时严格等于段界、镜内内容全归单一 scene_code」无法落位。
        # ep022 段界 12/13/13/7 ⇒ B-16 = 12+13+13 = 38s（镜1–3）、B-17 = 7s（镜4）。
        # 2026-10-23 修正：原写 32s/13s（B-16 收在 32.0s，落在镜3 的 25–38s 之内）。
        "scenes": [
            {"code": "B-16", "location": "城郊骨井", "time": "21:00-21:38", "duration_sec": 38},
            {"code": "B-17", "location": "废弃军工机械厂", "time": "21:38-21:45", "duration_sec": 7},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·凿井", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "远景：井架上的绞盘在转，井口开始返出灰雾"},
            {"index": 2, "name": "推进·低频", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "数据板上有一段持续低频，方向在城郊，节律对上了"},
            {"index": 3, "name": "转折·空架", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "出城查到的是空井架和返上来的灰雾，人已经撤走"},
            {"index": 4, "name": "收钩·密信", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "城西截下一名信使，终端里存着一封未拆的密信"},
        ],
        "scene_needs": [
            {"空间": "城郊骨井（远景·凿井作业点）",
             "要点": "井架与绞盘只作远景轮廓；井口返出的灰雾为唯一可读元素；"
                     "作业者一律远景剪影，不呈现人体细节"},
            {"空间": "废弃军工机械厂（夜·数据板与信使）",
             "要点": "数据板屏与终端为主光源；信使只作局部（终端、手），不给面部特写"},
        ],
        "open_questions": [],
    },
    {
        "ep": 23,
        "story_time": "灾变第 18 日 10:30（密信摊开）",
        "present_characters": ["LC", "SQC"],
        "carry_over": "承接上集钩子：陆沉截获密信——密信上写的是什么？",
        "answer": "是一份交易条款：云顶财阀按批次拨付安全屋配额与药剂，雾盟按批次交付高阶雾核；交付栏只写批次编号与「清退区域」四个字。苏清辞把自己的救治排班表摊在旁边对照，被清退的区域正是机械厂要接的那一片。",
        "cost": "真相是有价的：陆沉知道了财阀在卖、雾盟在收，可知道之后他什么都还没变——名单上的人还在等下一炉净火，而能付钱的那一方已经在加码。",
        "emotion_goal": "寒·背叛",
        "scenes": [
            {"code": "B-18", "location": "废弃军工机械厂", "time": "10:30-11:15", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·摊开", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "一封密信在钢桌上摊开，排版是合同的样子"},
            {"index": 2, "name": "推进·对表", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "救治排班表摊在旁边，两张纸上的区域对上了"},
            {"index": 3, "name": "转折·清退栏", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "交付栏翻到最后一页，只有批次编号和四个字"},
            {"index": 4, "name": "收钩·停手", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "面板上密信一行行读完，指腹在最后一行停住"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（日·数据板与摊开的密信）",
             "要点": "数据板屏与一张摊开的纸质密信为主视觉；密信为可读的条款排版，"
                     "不出现签名与手写体；纸面不出现宗教符号与仪式元素"},
        ],
        "open_questions": [],
    },
    {
        "ep": 24,
        "story_time": "灾变第 19 日 19:00（真相并排）",
        "present_characters": ["LC", "YHY", "SQC"],
        "carry_over": "承接上集钩子：密信内容触目惊心——触目惊心在哪？陆沉打算怎么办？",
        "answer": "在两笔账并成了一笔：财阀拿药换雾核，雾盟拿平民换雾核，骨井里蓄的灰雾只等第二次引爆。陆沉把条款和凿井进度并排看了一遍，下令从今夜起不熄净火，优先净名单上最重的那一批。",
        "cost": "救人的代价是明码的：净火每净一个人都往骨纹里添一笔余烬，归一度只会往上走；陆沉拿自己的额度去填全城排不上队的那张名单，而对面已经在准备第二次引爆。",
        "emotion_goal": "决·沉重",
        "scenes": [
            {"code": "B-19", "location": "废弃军工机械厂", "time": "19:00-19:45", "duration_sec": 45},
        ],
        "duration_sum_sec": 45,
        "quad_segments": [
            {"index": 1, "name": "开场·并排", "start_sec": 0, "end_sec": 12, "mode": "串行",
             "note": "条款与凿井进度并排摊在钢桌上"},
            {"index": 2, "name": "推进·算账", "start_sec": 12, "end_sec": 25, "mode": "串行",
             "note": "净火能覆盖的极限被算成一行数字"},
            {"index": 3, "name": "转折·下令", "start_sec": 25, "end_sec": 38, "mode": "串行",
             "note": "从今夜起不熄净火，名单上最重的那一批先来"},
            {"index": 4, "name": "收钩·不熄", "start_sec": 38, "end_sec": 45, "mode": "串行",
             "note": "净化区的火一直烧到天亮，名单又长了一截"},
        ],
        "scene_needs": [
            {"空间": "废弃军工机械厂（夜·净化区与名单板）",
             "要点": "净化区留出可躺下的工位与净火空当；名单板固定在墙上、只作中景；"
                     "不呈现人体创口，净化结果为白烟与正常肤色；火为黑白双焰，不出现第三种火焰色"},
        ],
        "open_questions": [],
    },
]

# 源素材《逐集内容概述》U03 段的集级钩子（逐字，用于回源核对）
SOURCE_HOOKS = {
    17: "陆沉骨威全开",
    18: "陆沉取下叶家暗杀组主谋的那枚身份铭牌",
    19: "四方流民涌来",
    20: "大限夜已过，全城仍未脱离灰雾",
    21: "雾盟现身",
    22: "陆沉截获密信",
    23: "密信内容触目惊心",
    24: "陆沉日夜焚斑救人数万",
}
# 源素材的集级事件摘要（逐字，用于回源核对）
SOURCE_EVENTS = {
    17: "叶红衣化身暗夜修罗，反杀刺客",
    18: "陆沉一纹巅峰骨威全歼刺客",
    19: "悬身份铭牌于据点大门，立铁血战旗「踏入此线者死」",
    20: "流民疯涌归附，据点人口暴涨，治理压力骤增",
    21: "大限善后，灰雾余波致灰斑暴增，全城恐慌",
    22: "雾盟借大限余波凿穿骨井，欲二次引爆蓄积灰雾",
    23: "截获密信，财阀默许雾盟清洗平民换高阶雾核",
    24: "财阀与雾盟交易真相浮出，陆沉决意阻止人造双潮",
}

# 《脉络确认》§五 伏笔表（埋点 → 回收点）
FORESHADOW_TABLE = {
    "F01": ("ep001", "ep156"), "F02": ("ep023", "ep037"), "F03": ("ep028", "ep094"),
    "F04": ("ep047", "ep102"), "F05": ("ep067", "ep094"), "F06": ("ep074", "卷三灰海"),
    "F07": ("ep010", "ep028"), "F08": ("ep013", "ep035"), "F09": ("ep016", "ep021"),
}

# ─────────────────────────────────────────────────────────────
# 工具
# ─────────────────────────────────────────────────────────────
def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def all_text(node):
    """全量取文本（V5 同口径：所有字符串值）。"""
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for n in node:
            out.extend(all_text(n))
    elif isinstance(node, dict):
        for v in node.values():
            out.extend(all_text(v))
    return out


def materialize_d07(d07):
    """把 present_characters 的 char_id 列表展开成 schema 要求的对象数组，
    并按 U01／U02 惯例把 D07 的 must_happen 与 D06 同集同序对齐（**不在脚本里手抄两份**）。

    schema D07.episodes[].present_characters[] = {char_id, role, minor(, voice_only)}；
    本岗脚本内只维护 char_id 列表（避免手抄 role/minor 造成口径漂移），落盘前统一展开。
    schema D07.episodes[].must_happen 为必填（V1 会拦），口径与 D06 逐字相同 —— 由 D06 派生，
    保证两表不会出现「改了 D06 忘了改 D07」的分叉。
    """
    for ep in d07["episodes"]:
        ids = ep["present_characters"]
        ep["present_characters"] = [
            {"char_id": cid, "role": ROLE[cid], "minor": False} for cid in ids
        ]
    return d07


def fail(msg):
    print(f"  ✗ {msg}")
    raise AssertionError(msg)


# ─────────────────────────────────────────────────────────────
# 断言组
# ─────────────────────────────────────────────────────────────
def assert_content(root, d06, d07, project, d05, rules):
    print("■ 断言组（内容口径）")
    eps6 = {e["ep"]: e for e in d06["episodes"]}
    eps7 = {e["ep"]: e for e in d07["episodes"]}

    # A1 集号连续且等于 EPS
    if sorted(eps6) != EPS:
        fail(f"A1 D06 集号 {sorted(eps6)} ≠ {EPS}")
    if sorted(eps7) != EPS:
        fail(f"A1 D07 集号 {sorted(eps7)} ≠ {EPS}")
    print("  ✓ A1 集号连续 ep017–ep024，D06／D07 各 8 集")

    # A2 单元内钩子链逐字咬合
    for ep in EPS[1:]:
        if eps6[ep]["hook_in"] != eps6[ep - 1]["hook_out"]:
            fail(f"A2 ep{ep} hook_in 与 ep{ep-1} hook_out 不逐字相等")
    print("  ✓ A2 单元内钩子链逐字咬合（7 处）")

    # A3 单元边界：ep017.hook_in ＝ U02 ep016.hook_out（逐字，读盘）
    u02 = load_json(os.path.join(root, "units", "U02", "D06.json"))
    u02_last = next(e for e in u02["episodes"] if e["ep"] == 16)["hook_out"]
    if eps6[17]["hook_in"] != u02_last:
        fail(f"A3 ep017 hook_in ≠ U02 ep016 hook_out（逐字）\n     本岗：{eps6[17]['hook_in']}\n     U02：{u02_last}")
    u3 = next(u for u in project["units"] if u["id"] == "U03")
    u4 = next(u for u in project["units"] if u["id"] == "U04")
    u2 = next(u for u in project["units"] if u["id"] == "U02")
    if u3["first_hook"] != u2["last_hook"]:
        fail(f"A3 project.json U03.first_hook ≠ U02.last_hook：{u3['first_hook']} / {u2['last_hook']}")
    if u3["first_hook"] != eps6[17]["hook_in"]:
        fail("A3 ep017 hook_in ≠ project.json U03.first_hook（逐字）")
    if u3["last_hook"] != u4["first_hook"]:
        fail(f"A3 U03.last_hook ≠ U04.first_hook：{u3['last_hook']} / {u4['first_hook']}")
    if eps6[24]["hook_out"] != u3["last_hook"]:
        fail("A3 ep024 hook_out ≠ U03.last_hook（逐字）")
    print(f"  ✓ A3 单元边界逐字：ep017.hook_in ＝ U02 ep016.hook_out ＝ {u3['first_hook']}")
    print(f"  ✓ A3 单元边界逐字：ep024.hook_out ＝ U03.last_hook ＝ U04.first_hook ＝ {u3['last_hook']}")

    # A4 集级钩子回源核对（《逐集内容概述》U03 段）
    for ep in EPS:
        h = SOURCE_HOOKS[ep]
        if ep == 24:
            if eps6[ep]["hook_out"] != h:
                fail(f"A4 ep024 hook_out ≠ 概述钩子逐字：{eps6[ep]['hook_out']}")
        else:
            if not eps6[ep]["hook_out"].startswith(h):
                fail(f"A4 ep{ep} hook_out 未以概述钩子「{h}」开头：{eps6[ep]['hook_out']}")
        if not eps6[ep]["hook_in"].startswith(SOURCE_HOOKS.get(ep - 1, "")) and ep != 17:
            fail(f"A4 ep{ep} hook_in 未以概述钩子「{SOURCE_HOOKS[ep-1]}」开头")
    print("  ✓ A4 集级钩子回源核对（《逐集内容概述》U03 段 8 行逐字命中）")

    # A5 归一度：读数恒 1.4%、单调不减、落在相邻锚点闭区间、ep024 及以前不出现 1.5%
    gauge = []
    for e in d05["power_system"]["gauge_readings"]:
        m = re.search(r"(\d+(?:\.\d+)?)%", str(e.get("reading", "")))
        if m:
            gauge.append((int(re.search(r"\d+", str(e["ep"])).group(0)), float(m.group(1))))
    anchors = sorted(gauge, key=lambda x: x[0])
    avals = [v for _, v in anchors]
    prev_ep, prev_v = 16, 1.4
    for e in d06["episodes"]:
        # 注：本岗 D06／D07 写作「面板归一度读数 1.4%」，比 audit-unit.py 的
        #     `归一度\s*(\d+)%` 多一个「读数」限定词，故此处放宽到「归一度 + ≤4 个非数字字符 + 数值」。
        vals = [float(m.group(1)) for m in
                re.finditer(r"归一度[^\d%]{0,4}(\d+(?:\.\d+)?)%", json.dumps(e, ensure_ascii=False))]
        if not vals:
            fail(f"A5 ep{e['ep']} 缺归一度读数")
        v = max(vals)
        if v != 1.4:
            fail(f"A5 ep{e['ep']} 归一度读数 {v} ≠ 1.4%（本单元口径）")
        if v < prev_v:
            fail(f"A5 ep{e['ep']} 归一度非单调不减：{prev_v} → {v}")
        lo = max([a for a in avals if a <= v], default=None)
        hi = min([a for a in avals if a >= v], default=None)
        if lo is None or hi is None or not (lo <= v <= hi):
            fail(f"A5 ep{e['ep']} 读数 {v} 越出锚点区间 [{lo},{hi}]")
        if v == 1.5 and e["ep"] <= 24:
            fail(f"A5 ep{e['ep']} 出现 1.5%（该值为 ep026 锚点，ep024 及以前禁）")
        prev_v = v
        gauge.append(v)
    print(f"  ✓ A5 归一度：8 集恒 1.4%，单调不减，落在锚点区间 [1.0, 1.5]，未出现 1.5%")

    # A6 伏笔：F09 收在 ep021、F02 埋在 ep023 → U05
    fs = {e["ep"]: e["foreshadow"] for e in d06["episodes"]}
    if fs[21]["payoff"] != "F09" or fs[21]["plant"] is not None:
        fail("A6 ep021 必须为 F09 回收（脉络确认 §五：F09 埋 ep016 → 收 ep021）")
    if fs[23]["plant"] != "F02" or fs[23]["pending_unit"] != "U05":
        fail("A6 ep023 必须埋 F02，pending_unit=U05（脉络确认 §五：F02 埋 ep023 → 收 ep037 ∈ U05）")
    for ep in EPS:
        f = fs[ep]
        if f["plant"] and f["payoff"]:
            fail(f"A6 ep{ep} 不得同时埋与收")
    # 与 U02 已埋伏笔不重号
    u02_fs = {}
    for e in u02["episodes"]:
        f = e.get("foreshadow") or {}
        if f.get("plant"):
            u02_fs[f["plant"]] = e["ep"]
    for ep in EPS:
        p = fs[ep].get("plant")
        if p and p in u02_fs:
            fail(f"A6 F 编号重号：{p} 已在 U02 ep{u02_fs[p]} 埋过")
    print(f"  ✓ A6 伏笔：F09 收于 ep021；F02 埋于 ep023（pending U05）；与 U02 已埋 {sorted(u02_fs)} 不重号")

    # A7 名单一致：D06.characters == D07.present_characters，且 ⊆ D04
    for ep in EPS:
        r6 = set(eps6[ep]["characters"])
        r7 = set(p["char_id"] for p in eps7[ep]["present_characters"])
        if r6 != r7:
            fail(f"A7 ep{ep} D06.characters {sorted(r6)} ≠ D07.present_characters {sorted(r7)}")
        for cid in r6:
            if cid not in D04_IDS:
                fail(f"A7 ep{ep} 角色 {cid} 不在 D04")
    print("  ✓ A7 名单：D06.characters ≡ D07.present_characters（8 集）且角色 id 均在 D04")

    # A8 节拍：Bxx 标注以概述为准；爽点密度 ≥3；单元内须有转折
    for ep, bids in ((18, ["B07"]), (23, ["B08"])):
        if eps6[ep].get("beat_ids") != bids:
            fail(f"A8 ep{ep} beat_ids {eps6[ep].get('beat_ids')} ≠ {bids}（概述〔Bxx〕）")
    shock = sum(1 for e in d06["episodes"] if "爽点" in e["beats"])
    if shock < rules.get("density", {}).get("min_shock_points_per_unit", 3):
        fail(f"A8 爽点仅 {shock} 个 < 下限")
    if not any("转折" in e["beats"] for e in d06["episodes"]):
        fail("A8 单元内无「转折」beat")
    print(f"  ✓ A8 节拍：B07@ep018、B08@ep023；爽点 {shock} 个（下限 3）；含转折 beat")

    # A9 四段制与场景时长
    codes = []
    for ep in EPS:
        segs = eps7[ep]["quad_segments"]
        if len(segs) != 4:
            fail(f"A9 ep{ep} 四段数 {len(segs)} ≠ 4")
        cur = 0
        for i, s in enumerate(segs):
            if s["index"] != i + 1:
                fail(f"A9 ep{ep} 段序号应为 {i+1}")
            if s["start_sec"] != cur:
                fail(f"A9 ep{ep} 段{i+1} 起点 {s['start_sec']} 与上一段终点 {cur} 不接续")
            if s["end_sec"] <= s["start_sec"]:
                fail(f"A9 ep{ep} 段{i+1} 区间非法")
            cur = s["end_sec"]
        if cur != 45:
            fail(f"A9 ep{ep} 四段合计 {cur}s ≠ 45")
        ssum = sum(s["duration_sec"] for s in eps7[ep]["scenes"])
        if abs(ssum - eps7[ep]["duration_sum_sec"]) > 1e-6:
            fail(f"A9 ep{ep} 场景时长合计 {ssum} ≠ duration_sum_sec {eps7[ep]['duration_sum_sec']}")
        if abs(eps7[ep]["duration_sum_sec"] - eps6[ep]["duration_sec"]) > 1e-6:
            fail(f"A9 ep{ep} D06.duration_sec ≠ D07.duration_sum_sec")
        for s in eps7[ep]["scenes"]:
            codes.append(s["code"])
    if codes != sorted(codes, key=lambda c: int(c.split("-")[1])):
        fail(f"A9 场景编码未按序：{codes}")
    if len(set(codes)) != len(codes):
        fail(f"A9 场景编码重复：{codes}")
    print(f"  ✓ A9 四段制与时长：8 集段界连续、合计 45s；场景编码 {codes[0]}–{codes[-1]}（{len(codes)} 个）连续不重")

    # A10 禁词扫描：D05 禁用同义写法 ＋ rules.forbidden_words ＋ 未命名期专名 ＋ 阎王同义 ＋ R01
    forbidden = set()
    for g in d05["glossary"]:
        forbidden.update(g.get("forbidden_synonyms") or [])
    forbidden.update(rules.get("forbidden_words") or [])
    forbidden.update(UNNAMED_PERIOD_FORBIDDEN)
    forbidden.update(YANWANG_FORBIDDEN)
    forbidden.update(R01_FORBIDDEN)
    forbidden.update(UNIT_SPECIFIC_FORBIDDEN)
    for doc, name in ((d06, "D06"), (d07, "D07")):
        txt = "\n".join(all_text(doc))
        hits = sorted({w for w in forbidden if w and w in txt})
        if hits:
            fail(f"A10 {name} 命中禁写词 {hits}")
    print(f"  ✓ A10 禁词扫描：D06／D07 命中 0（禁写集合 {len(forbidden)} 条）")

    # A11 地点：只允许 D05.locations 中的名字出现在 D06.locations
    d05_locs = {l["name"] for l in d05["locations"]}
    for e in d06["episodes"]:
        for loc in e["locations"]:
            if loc not in d05_locs:
                fail(f"A11 ep{e['ep']} 地点「{loc}」不在 D05 地点表（会产生 V2 warning）")
    print(f"  ✓ A11 D06.locations 全部在 D05.locations（{sorted(d05_locs)}）")

    # A12 未命名期：本单元不出现该物件的任何专名写法（额外独立复核）
    for doc, name in ((d06, "D06"), (d07, "D07")):
        txt = "\n".join(all_text(doc))
        for w in UNNAMED_PERIOD_FORBIDDEN:
            if w in txt:
                fail(f"A12 {name} 出现未命名期专名写法「{w}」")
    print("  ✓ A12 未命名期（ep013–ep040）专名写法 0 处")

    # A13 零血腥 / 去宗教化：D03 R02、R08 禁词
    gore = ["斩首", "悬首", "悬头颅", "竖首级", "手撕", "徒手撕开", "撕开", "刀斩", "碾碎",
            "轰碎喉骨", "钉在人身上", "血肉", "喷溅", "血浆", "脑浆", "白骨露", "尸体堆",
            "肢解", "掏心", "开膛", "残肢", "断肢", "内脏", "器官", "焚烧人体", "献祭", "血祭"]
    for doc, name in ((d06, "D06"), (d07, "D07")):
        txt = "\n".join(all_text(doc))
        hits = sorted({w for w in gore if w and w in txt})
        if hits:
            fail(f"A13 {name} 命中暴力/血腥禁词 {hits}")
    print("  ✓ A13 零血腥与去宗教化禁词 0 命中（唯一暴力出口＝溃散为灰烬光尘）")

    # A14 首用集地板：薪火城(33)、影刃封路(37)、律条名(41) 均不得出现
    floors = {"薪火城": 33, "影刃封路": 37, "律条": 41, "天律": 65, "骨窖": 49, "供位": 49,
              "境外基因财阀": 85, "雾盟副座": 90, "神骸": 120}
    for doc, name in ((d06, "D06"), (d07, "D07")):
        txt = "\n".join(all_text(doc))
        for term, floor_ep in floors.items():
            if term in txt and floor_ep > 24:
                fail(f"A14 {name} 出现首用集未到的术语「{term}」（first_use_ep={floor_ep}）")
    print("  ✓ A14 首用集地板：薪火城／影刃封路／律条／天律／骨窖／供位 等均 0 出现")

    # A15 D07 逐集必备字段非空（承接/回答/代价）＋ must_happen 与 D06 逐字相同
    for ep in EPS:
        for k in ("carry_over", "answer", "cost", "story_time", "emotion_goal"):
            if not str(eps7[ep].get(k, "")).strip():
                fail(f"A15 ep{ep} D07.{k} 为空")
        mh = eps7[ep].get("must_happen")
        if not mh:
            fail(f"A15 ep{ep} D07.must_happen 缺失（schema 必填，V1 会拦）")
        if mh != eps6[ep]["must_happen"]:
            fail(f"A15 ep{ep} D07.must_happen 与 D06 不同表（U03 本单元约定两表逐字相同；U01／U02 为大纲级 vs 施工卡级表述差异，非逐字相同）")
    print("  ✓ A15 D07 承接／回答／代价／时间／情绪／must_happen 逐集非空，且 must_happen ≡ D06")

    # A16 集级事件回源：《逐集内容概述》U03 段 8 行逐字存在
    if os.path.exists(SOURCE_EPISODES):
        src = open(SOURCE_EPISODES, encoding="utf-8").read()
        for ep in EPS:
            if f"**ep{ep:03d}**" not in src:
                fail(f"A16 源素材缺 ep{ep:03d} 行")
        for ep in EPS:
            if SOURCE_EVENTS[ep] not in src:
                fail(f"A16 源素材事件摘要不匹配 ep{ep}：{SOURCE_EVENTS[ep]}")
        print("  ✓ A16 集级事件回源：《逐集内容概述》U03 段 8 行事件摘要逐字命中")
    else:
        print(f"  ! A16 源素材不可达（{SOURCE_EPISODES}），跳过回源核对")

    # A17 钩子类型字段在位 ＋ **反静默回退守卫**
    #  背景（2026-10-23 13:4x 实锤）：本脚本曾是 U03 D06 的唯一生成通道，而现盘 D06 被并发加上了
    #  8 集的 hook_type／hook_type_reason（schema D06.episodes 可选字段），**脚本内命中 0** ⇒
    #  重跑生成器 = 这 8 集的 hook 字段被整份抹掉（静默回退，且抹的是「钩子类型」这一节奏判据输入）。
    #  ⇒ 守卫口径：**现盘若含生成器产不出的字段 ⇒ 源脚本已落后，此刻必须拦下（先回并内容源）**，
    #     而不是照写不误把现盘覆盖回旧形态。
    HOOK_ENUM = ["悬念", "反转", "情绪", "信息", "危机"]
    for e in d06["episodes"]:
        if e.get("hook_type") not in HOOK_ENUM:
            fail(f"A17 ep{e['ep']} D06.hook_type={e.get('hook_type')!r} 不在 schema 枚举 {HOOK_ENUM}")
        if not str(e.get("hook_type_reason") or "").strip():
            fail(f"A17 ep{e['ep']} D06.hook_type_reason 缺失或为空")
    for fname, gen in (("D06.json", d06), ("D07.json", d07)):
        p = os.path.join(root, "units", UNIT, fname)
        if not os.path.exists(p):
            continue
        try:
            disk_obj = load_json(p)
        except Exception as ex:
            fail(f"A17 现盘 {fname} 不可解析：{ex}")
        gen_eps = {e["ep"]: e for e in gen["episodes"]}
        for e in disk_obj.get("episodes", []):
            ge = gen_eps.get(e.get("ep"))
            if ge is None:
                continue
            extra = set(e.keys()) - set(ge.keys())
            if extra:
                fail(f"A17 现盘 {fname} ep{e.get('ep')} 多出生成器产不出的字段 {sorted(extra)}"
                     " ⇒ 源脚本已落后，重跑会静默抹掉该字段 ⇒ 拒绝写盘，请先回并内容源")
    print("  ✓ A17 hook_type 枚举合规 + 反静默回退守卫：现盘无生成器产不出的字段")


# ─────────────────────────────────────────────────────────────
# 落盘
# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    factory = os.path.abspath(os.path.join(root, "..", ".."))
    rules_p = os.path.join(factory, "03_规格", "rules.json")
    rules = load_json(rules_p) if os.path.exists(rules_p) else {}
    project = load_json(os.path.join(root, "project.json"))
    d05 = load_json(os.path.join(root, "shared", "D05.json"))

    d06 = {"doc_id": "D06", "unit": UNIT, "version": D06_VERSION, "status": STATUS,
           "episodes": D06_EPISODES}
    d07 = {"doc_id": "D07", "unit": UNIT, "version": D07_VERSION, "status": STATUS,
           "episodes": D07_EPISODES}
    # D07.must_happen 由 D06 派生（U03 本单元约定两表逐字相同；U01／U02 为大纲级 vs 施工卡级表述差异，非逐字相同），不在脚本内手抄第二份
    d06_mh = {e["ep"]: e["must_happen"] for e in d06["episodes"]}
    for e in d07["episodes"]:
        e["must_happen"] = list(d06_mh[e["ep"]])
    materialize_d07(d07)

    assert_content(root, d06, d07, project, d05, rules)

    unit_dir = os.path.join(root, "units", UNIT)
    os.makedirs(unit_dir, exist_ok=True)
    targets = [(os.path.join(unit_dir, "D06.json"), d06),
               (os.path.join(unit_dir, "D07.json"), d07)]

    payload = []
    for path, obj in targets:
        blob = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        payload.append((path, blob))

    # 幂等：内容逐字节一致则不动盘
    changed = []
    for path, blob in payload:
        if os.path.exists(path):
            cur = open(path, "rb").read()
            if cur == blob:
                print(f"[IDEMPOTENT] {os.path.relpath(path, root)} 已存在且逐字节一致；未改动。")
                continue
            if not args.force:
                print(f"[ABORT] {os.path.relpath(path, root)} 已存在且内容不同；"
                      f"如确需覆盖请加 --force（本次未写盘）。")
                sys.exit(1)
        changed.append((path, blob))

    if not changed:
        print("[OK] 无需改动。")
        return 0

    if args.dry_run:
        for path, blob in changed:
            print(f"[DRY-RUN] 将写 {os.path.relpath(path, root)}｜{len(blob)} B｜"
                  f"sha256 {hashlib.sha256(blob).hexdigest()[:16]}")
        return 0

    for path, blob in changed:
        with open(path, "wb") as f:
            f.write(blob)
        print(f"[OK] 已写入 {os.path.relpath(path, root)}｜{len(blob)} B｜"
              f"sha256 {hashlib.sha256(blob).hexdigest()[:16]}｜"
              f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 写后回读：版本/字节/集号
    for path, blob in changed:
        back = open(path, "rb").read()
        if back != blob:
            sys.exit("[ABORT] 写后回读不一致。")
        obj = json.loads(back.decode("utf-8"))
        print(f"[VERIFY] {os.path.relpath(path, root)}：version={obj['version']}｜"
              f"{len(back)} B｜{len(obj['episodes'])} 集｜ep{obj['episodes'][0]['ep']}–ep{obj['episodes'][-1]['ep']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
