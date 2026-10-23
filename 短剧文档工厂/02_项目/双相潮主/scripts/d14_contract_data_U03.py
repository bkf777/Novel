#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D14 逐镜 Render Contract / Appearance 填写器（U03 单元）。

原则（与 U01/U02 同构）：
- source_inventory 不删不改（preflight 依 Blender structure_evidence 生成）。
- 每个描述字段只写一个可见事实，且用英文（技能要求）。
- 锚点的可见性/包围盒取 Blender 实测证据；朝向/运动状态/空间关系由实测轨迹与
  投影框推导，不臆测。
- 运动合同按白模实测位移/形变判定；实测无位移者一律 static（不得自行动画化）。
- 台词不进 D14：D14 只承载画面与环境音，台词由 D15/后期负责。

U03 口径：
- 镜头号段 = 全局镜号 65..96（ep17–ep24，32 镜），不是 1..32。
- core_name() 正则放宽为 `^[A-Z]-\d+_(?:CHAR|PROP|EXT|FX|LGT)_(.+?)(?:[._]\d+)?$`，
  以便剥离 U03 场景码前缀（B-11…B-19）。
- 零血腥口径：敌人消散一律写 ash motes / silhouette；不给人体细节、不给面部特写、
  不出现任何创口与红色液体；异化者只作遮挡。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# 注：本模块只提供**内容表**（语义/动作/交互/声音/风格）。
# 项目根与白模工作区一律由调用方（fill_D14_contracts.py）按 --project/--work 传入，
# 此处不写死任何绝对路径 —— 内容模块若自带路径，跨单元复用时会静默指向错误单元。

# ------------------------------------------------------------------ 实体语义
# core -> (entity_class, source_role, structural_constraints)
# 词汇表 = white_model_content_U03.py 的 EN 表（值集合一一对应，一个不漏）。
SEMANTIC = {
    # ---- 角色 ----
    "Luchen": ("articulated", "protagonist blockout in black tactical coat",
                "human height 1.80m; bone pattern stays flat on the skin surface, never breaks the body"),
    "LuchenHand": ("articulated", "protagonist raised hand blockout",
                   "0.30m hand volume; stays attached to the protagonist forearm"),
    "Yehongyi": ("articulated", "female fighter character blockout in dark red outfit",
                 "human height 1.70m; carries the shadow blade at her side"),
    "Suqingci": ("articulated", "female scientist character blockout in white lab coat",
                 "human height 1.68m; holds the data tablet against the chest"),
    "Yechengjun": ("articulated", "male officer antagonist blockout in ivory short jacket",
                   "human height 1.79m; pushed to the junction as a silhouette, no face is ever built"),
    "MessengerHand": ("articulated", "captured messenger hand blockout",
                      "0.30m hand volume; only the hand and the terminal enter the frame"),
    # ---- 群体人形（白模层由 MULTI 合成，按人形描述朝向）----
    "EncroachingShadowCrowd": ("articulated", "closing shadow crowd blockout in a half circle",
                               "thirteen bodies on a 5.50m radius arc; no face is ever built"),
    "RetreatingShadow": ("articulated", "retreating shadow blockout heading for the junction",
                         "three bodies; no face is ever built"),
    "SuppressedCrowd": ("articulated", "suppressed crowd blockout in two columns along the street",
                        "eight bodies; silhouettes only, no face"),
    "QueueColumns": ("articulated", "queue column blockout at the triage table",
                     "fourteen bodies in two columns; column order preserved, no face"),
    "GateGuard": ("articulated", "gate guard blockout on the two queue lanes",
                  "two bodies; silhouettes only, no face"),
    "RutQueue": ("articulated", "queue blockout along the wheel ruts outside the gate",
                 "twelve bodies; silhouettes only, no face"),
    "LongQueue": ("articulated", "long queue blockout bending twice before the triage table",
                  "sixteen bodies; silhouettes only, no face"),
    "OverduePatient": ("articulated", "overdue patient blockout slowing down",
                       "three bodies; only outline and sleeve are readable, no face"),
    "AlteredPatient": ("articulated", "altered patient blockout used as foreground occlusion",
                       "two bodies; occlusion only, no body detail and no face"),
    "PassingPatient": ("articulated", "passing patient blockout walking around the overdue ones",
                       "three bodies; silhouettes only, no face"),
    "GeometryBadgeColumn": ("articulated", "badge column blockout walking through the street corner",
                            "six bodies in step; abstract geometric cuff badges only"),
    "WorkSilhouette": ("articulated", "well site worker blockout on the far side of the rig",
                       "three bodies; outline only, no body detail"),
    # ---- 建筑与场地 ----
    "StreetGround": ("environment", "brick street and inner yard ground plate",
                     "40x36m single plate; street and inner yard share one level"),
    "FactoryGateWall": ("environment", "factory gate wall with the main opening",
                        "4.80m high wall; main opening 4.00x3.80m; lintel above"),
    "StreetSideWall": ("environment", "side perimeter wall of the street",
                       "4.80m high steel plate run on both sides of the street"),
    "JunctionBlock": ("environment", "building band across the street end",
                      "8.00m high band split by a 10.00m cross street opening"),
    "WellGround": ("environment", "well site ground plate",
                   "36x28m rammed earth; one level, no steps"),
    "WellFarBank": ("environment", "far earth bank at the well site edge",
                    "1.20m high far boundary band; reads as distance only"),
    "FactoryInnerFloor": ("environment", "inner factory floor plate",
                          "24x18m plate; carries the steel table and the name board wall"),
    "FactoryInnerWall": ("environment", "inner factory room walls",
                         "6.00m clear height; the north wall carries the name board"),
    "FactoryInnerRoof": ("environment", "inner factory room roof",
                         "roof slab at 6.00m clear height"),
    "FactoryInnerCeilingLamp": ("environment", "cold white ceiling lamp over the steel table",
                                "single tube fixture; the only overhead source in the room"),
    # ---- 道具 ----
    "SteelGatePost": ("rigid", "steel gate post of the factory main gate",
                      "0.46x0.46x6.20m post; two posts symmetric about the opening"),
    "EmergencyLamp": ("rigid", "emergency lamp on the gate post face",
                      "0.26x0.20x0.18m fixture; two units aimed at the street"),
    "ResidualFireHead": ("effect", "residual fire head still burning on the street",
                         "1.20x1.20m footprint; flame height 2.40m; three separate heads"),
    "WallShadowBand": ("rigid", "shadow band along the foot of the gate wall",
                       "2.20x0.60m band on each side of the opening"),
    "AshDeposit": ("rigid", "ash settled into the brick seams",
                   "0.02m thin patches pushed into lines by the wind"),
    "SteelCrate": ("rigid", "steel crate on the street used as a tablet stand",
                   "1.10x0.70x0.62m; only the data tablet rests on its top"),
    "DataTablet": ("rigid", "handheld data tablet",
                   "0.30x0.03x0.22m; screen carries Chinese text only"),
    "IdentityPlate": ("rigid", "identity metal plate",
                      "0.22x0.16x0.03m; abstract geometric pattern; no signature"),
    "EnemyChiefEmblem": ("rigid", "enemy chief emblem metal piece",
                          "0.24x0.24x0.03m square plate; abstract geometric pattern"),
    "ThresholdStone": ("rigid", "threshold stone at the factory gate",
                       "7.60m run with a 0.66m open seam; seam takes the flagpole"),
    "Flagpole": ("rigid", "flagpole planted in the threshold seam",
                 "0.50x0.50x7.20m; two people can reach around it"),
    "FlagCloth": ("rigid", "flag cloth raised on the pole",
                  "1.60x0.04x1.05m; one line of Chinese, written once"),
    "PointerPen": ("rigid", "pointer pen used on the roster and the tablet",
                   "0.18m long; tip stays on the writing surface"),
    "RegistrationDesk": ("rigid", "registration desk inside the gate",
                         "2.40x0.90m top at 0.78m; holds the roster only"),
    "NameRoster": ("rigid", "name roster sheet on the registration desk",
                   "0.42x0.30m sheet; columns written in Chinese"),
    "TriageTable": ("rigid", "triage table inside the gate",
                    "3.20x0.90m top at 0.80m; two columns form in front of it"),
    "MedicineCrate": ("rigid", "medicine crate beside the triage table",
                      "0.70x0.50x0.40m; stands on the floor east of the table"),
    "NetFireSlot": ("rigid", "marked net fire slot at the head of the queue",
                    "1.20x1.20m marked ground slot; kept clear"),
    "WheelRut": ("rigid", "wheel rut tracks pressed into the brick street",
                 "0.28m wide tracks running in from all sides"),
    "DistantShedBand": ("environment", "distant shed band at the street end",
                        "26.00m long band; reads as distance only, never a full scene"),
    "NoticeWall": ("rigid", "gate wall face covered with notices",
                   "6.00x2.40m face; notices packed with no large gap"),
    "NewNotice": ("rigid", "newly posted notice sheet",
                  "0.60x0.90m sheet; Chinese text only"),
    "WellDerrick": ("rigid", "wooden derrick over the bone well",
                    "9.00m tall frame on four columns; reads as outline in the fog"),
    "Winch": ("rigid", "winch drum on the derrick head",
              "0.90m drum on a 1.60m axle; rope winds deeper on the drum"),
    "WinchRope": ("rigid", "winch rope dropping into the well mouth",
                  "0.10m rope running 7.60m from the drum into the mouth"),
    "WellMouth": ("rigid", "square stone lined mouth of the bone well",
                  "3.20x3.20m opening with a 1.20m shaft; rim stands 0.40m proud"),
    "FreshChiselMark": ("rigid", "fresh chisel mark on the shaft wall",
                        "1.20m long notch; edges still shedding dust"),
    "WellMist": ("effect", "grey mist rising out of the well mouth",
                 "2.60m wide column above the opening; contains no body"),
    "DerrickLamp": ("rigid", "lamp on the derrick head",
                    "single fixture at 8.60m; the only light on the well site"),
    "ToolBox": ("rigid", "tool box on the well site",
                "0.70x0.50x0.45m; the data tablet rests on its top"),
    "MessengerSilhouette": ("articulated", "captured messenger blockout lying on the floor",
                            "prone outline only; the face is never built"),
    "Terminal": ("rigid", "handheld terminal of the captured messenger",
                 "0.22x0.14x0.04m unit; the screen stays lit"),
    "SealedLetter": ("rigid", "unopened sealed letter",
                     "0.21x0.30m folded sheet; seal intact, no signature on the paper"),
    "SteelTable": ("rigid", "steel table inside the factory",
                   "2.40x1.10m top at 0.76m; the document area is the only lit patch"),
    "OpenLetter": ("rigid", "contract letter spread open on the steel table",
                   "two 0.42x0.30m pages side by side; clauses in columns, no signature"),
    "DeliveryLastPage": ("rigid", "last page of the delivery column",
                          "0.21x0.30m sheet; only a batch number and four characters on it"),
    "TreatmentRoster": ("rigid", "treatment duty roster sheet",
                         "0.42x0.30m sheet; laid beside the letter"),
    "TradeClauseSheet": ("rigid", "trade clause sheet on the steel table",
                         "0.60x0.42m sheet; Chinese text only"),
    "WellProgressSheet": ("rigid", "well drilling progress sheet on the steel table",
                          "0.60x0.42m sheet; laid side by side with the clauses"),
    "NameBoard": ("rigid", "name board fixed on the north wall",
                  "2.60x1.80m board; names in columns, one number line at the bottom"),
    "NameBoardFrame": ("rigid", "leaning frame under the name board",
                       "two posts and one rail; supports the board edge only"),
    "PurifyStation": ("rigid", "marked purification work station on the floor",
                      "2.20x1.00m marked bay; one person can lie down in it"),
    "PurifyFirePit": ("effect", "purification fire pit of the net fire",
                      "1.10x1.10m pit; black and white twin flame only"),
    "VapourCore": ("rigid", "vapour core pressed against the name board",
                   "0.10x0.10x0.10m cube; the contact patch stays clean"),
    "BlackWhiteTwinFlame": ("effect", "black and white twin flame on the contact patch",
                            "0.18m contact patch; only two colours, black and white"),
    "WhiteSmoke": ("effect", "white smoke rising off the purified hand",
                   "0.06m puffs rising within 0.30m radius"),
    "ShadowBlade": ("rigid", "shadow blade held across the body",
                    "1.60m blade; the edge stays unlit in every frame"),
    "GreyFramePanel": ("rigid", "floating grey frame interface panel",
                       "non solid overlay; never casts shadow or blocks the set"),
    "AshMoteBurst": ("effect", "glowing ash motes left where a figure dispersed",
                     "0.55m clusters; reads as motes and drifting ash, never as a body"),
}

# 人形实体集合：内容模块显式声明 ⇒ 白模层所有人形 core 都拿到朝向描述。
HUMAN_CORES = {
    "Luchen", "LuchenHand", "Yehongyi", "Suqingci", "Yechengjun", "MessengerHand",
    # 群体人形（虽由 MULTI 合成，仍按人形描述朝向）
    "EncroachingShadowCrowd", "RetreatingShadow", "SuppressedCrowd", "QueueColumns",
    "GateGuard", "RutQueue", "LongQueue", "OverduePatient", "AlteredPatient",
    "PassingPatient", "GeometryBadgeColumn", "WorkSilhouette", "MessengerSilhouette",
}

# 逐镜合同：(motion, subject_core, actions, forbidden)
SHOT_DATA = {
    65: ("dolly", "EncroachingShadowCrowd",
         "the residual fire still burns on the street and thirteen shadow figures press in out of the "
         "grey fog, closing the street into a half circle around the one person standing in the gap; "
         "she holds the shadow blade flat across her front and the blade edge stays unlit; the "
         "attacking figures are silhouettes and no face is ever built",
         "do not give any shadow figure a face; do not light the blade edge; do not break the "
         "half circle open; do not add a second figure in the gap"),
    66: ("static", "AshMoteBurst",
         "the blade sweeps across the brick street and the front row of the half circle disperses one "
         "by one into glowing ash motes; the ash settles into the brick seams and only a single dark "
         "band is left on the street; the blade stays unlit and no body detail is shown",
         "do not leave any body detail in the dispersal; do not add broken skin or any red liquid; "
         "do not light the blade edge; do not turn the sweep into a camera move"),
    67: ("static", "Yechengjun",
         "the remaining shadows retreat toward the unlit crossing and the leader is pushed onto the "
         "junction where the road is cut off; the crossing holds nothing but darkness and the "
         "severed way out; the leader reads as a silhouette and no face is shown",
         "do not give the leader a face; do not light the crossing with a lamp; do not bring the "
         "retreating figures forward into the near ground"),
    68: ("crane", "Luchen",
         "one figure walks out of the gate shadow and the black and white bone pattern on the right "
         "wrist bone lights up all the way along the forearm; the whole street is held down under it "
         "and a readout field in one corner shows the normalisation readout at 1.4%; the pattern stays "
         "flat on the skin surface and never breaks the body",
         "do not break the skin under the bone pattern; do not hide the corner readout; do not stop "
         "the vertical travel of the camera; do not build a face for the figure"),
    69: ("dolly", "LuchenHand",
         "the bone will is fully open and the pattern runs from the right wrist bone up along the "
         "forearm while a band of white light spreads along the street and the grey fog is pushed down; "
         "loose stones on the street jump in the vibration; only the wrist and forearm segment is in "
         "frame and no mouth, face or identity marker is shown",
         "do not put a face or a mouth of the protagonist in frame; do not let the pattern run past "
         "the forearm; do not break the skin surface"),
    70: ("static", "AshMoteBurst",
         "inside the pressed down range the people who came forward disperse one by one into glowing "
         "ash motes; the dispersal runs from near to far and the human outlines come apart into "
         "lit dots; only motes and outlines come apart, no body detail is shown",
         "do not show any body detail while the outlines come apart; do not change the near to far "
         "order of the dispersal; do not turn the fixed camera into a pan"),
    71: ("static", "DataTablet",
         "the scientist rests the data tablet on a steel crate and the spectrum on the screen flattens "
         "line by line until no extra heartbeat signal is left; the street goes quiet and the settled "
         "ash is pushed into streaks by the wind; the text layer on the screen is Chinese only",
         "do not turn the tablet screen away from the camera; do not leave any waveform running; do "
         "not add a second object on the crate top"),
    72: ("static", "IdentityPlate",
         "where the ash settled only two metal pieces are left, an identity plate and an enemy chief "
         "emblem, each lying alone on the brick face; the protagonist bends down and takes the two "
         "pieces one by one into his hand; a readout field in one corner shows the normalisation "
         "readout at 1.4%",
         "do not put anything else on the brick face; do not add a body, a face or any red liquid; "
         "do not hide the corner readout"),
    73: ("static", "IdentityPlate",
         "the identity plate and the enemy chief emblem are hung on the steel gate post, only these "
         "two metal pieces hang there and nothing else is on the post; the post reads as outline only "
         "in the grey fog; the pattern on the metal is abstract geometry with no readable emblem",
         "do not hang a third object on the post; do not put a readable badge on the metal pieces; do "
         "not light the post fully"),
    74: ("crane", "FlagCloth",
         "the fighter presses the flagpole down into the seam of the threshold stone, the shaft comes "
         "up straight and the flag cloth opens out in the grey fog; one line of Chinese is written on "
         "the cloth, read straight and character by character",
         "do not bend the flagpole once it is planted; do not repeat the written line; do not write "
         "the line in any other script; do not stop the vertical travel of the camera"),
    75: ("static", "DataTablet",
         "the scientist copies the plate number into the data tablet and checks it once more; the "
         "protagonist stands on the inner side of the gate looking at the flag cloth and says nothing; "
         "the number on the tablet screen is written straight in Chinese",
         "do not turn the tablet screen away; do not build a face for the protagonist in the near "
         "ground; do not let the foreground shoulder cover the tablet"),
    76: ("dolly", "RutQueue",
         "in the grey fog outside the factory gate the wheel ruts press in from all sides and a queue "
         "has already formed along them up to the gate; the queued people are silhouettes all the way; "
         "a readout field in one corner shows the normalisation readout at 1.4%",
         "do not give any queued person a face; do not remove the wheel ruts; do not turn the push "
         "into an orbit"),
    77: ("static", "QueueColumns",
         "the queue runs from the factory gate all the way to the crossing and the wheel ruts are "
         "pressed into the grey fog with one set of prints laid over another; the queued people are "
         "silhouettes and the line turns deeper into the fog; a queue lane is kept on each side of the "
         "gate and the caller never enters the frame",
         "do not give any queued person a face; do not build the shed area as a full scene; do not "
         "close the queue lanes on either side of the gate"),
    78: ("static", "TriageTable",
         "at the triage table the scientist splits the line into two columns by the weight of the grey "
         "patch and the net fire position is placed at the head of the line; one aisle is kept open "
         "between the two columns; the grey patch is only visible on the cuffs and the backs of hands",
         "do not merge the two columns; do not close the aisle between them; do not let the grey patch "
         "spread past the cuffs and hands"),
    79: ("static", "NameRoster",
         "the death camp calls the names off the roster for the first time and the pen tip runs down "
         "the columns one after another; the protagonist walks to the registration position, takes the "
         "roster over and turns it to the last page; the roster columns are written straight in Chinese",
         "do not make the names legible; do not raise the lighting; do not add a second sheet to the "
         "desk"),
    80: ("static", "Yehongyi",
         "the gate watch is changed to two shifts and the blade never leaves the fighter's hand; when "
         "it gets light the grey fog has not lifted and the street is still grey; a readout field in "
         "one corner shows the normalisation readout at 1.4%",
         "do not light the blade edge; do not let the blade leave the hand; do not clear the fog; do "
         "not hide the corner readout"),
    81: ("static", "LongQueue",
         "the queue in front of the triage table bends twice and the grey patches have doubled since "
         "two days ago; the grey patch is only visible on the cuffs and the backs of hands and the "
         "queued people are silhouettes all the way",
         "do not give any queued person a face; do not let the grey patch spread past the cuffs and "
         "hands; do not straighten the two bends in the queue"),
    82: ("static", "OverduePatient",
         "the people who were treated late slow down and the grey patch spreads outward from its "
         "edge while the others on the street walk around them; the altered ones are used only as "
         "occlusion and no face is shown; the edge of the patch stays complete",
         "do not give an altered figure a face; do not show body detail on the altered ones; do not "
         "let the patch edge break apart"),
    83: ("static", "NewNotice",
         "a new notice is posted on the factory gate, the medicine is issued by measure and the safe "
         "house quota is suspended; the protagonist puts the net fire purification first and the "
         "scientist sorts by the remaining medicine; the notice is written straight in Chinese",
         "do not blank the notice text; do not let the notice read in any other script; do not add a "
         "second poster on the same patch of wall"),
    84: ("static", "GeometryBadgeColumn",
         "a column of people walks through the street corner with steps in time like a column; the "
         "badges on their cuffs are abstract geometry and no religious symbol can be read in them; a "
         "readout field in one corner shows the normalisation readout at 1.4%",
         "do not put any religious symbol on the badges; do not break the column order; do not give "
         "any of them a face; do not hide the corner readout"),
    85: ("static", "WellDerrick",
         "the winch on the derrick over the bone well turns and grey mist starts to come back up out "
         "of the well mouth; the derrick reads as outline only in the grey fog; the workers on the site "
         "are silhouettes and the mist out of the mouth carries no body at all",
         "do not build the well site as a full scene; do not show any body in the mist; do not light "
         "the site with anything but the derrick lamp"),
    86: ("static", "DataTablet",
         "a sustained low frequency comes up on the data tablet and the direction marker points to the "
         "outskirts of the city; one stretch of the waveform on the screen holds without falling; the "
         "text and the symbols on the screen are written straight in Chinese",
         "do not let the waveform fall; do not move the direction marker off the outskirts; do not "
         "turn the tablet screen away from the camera"),
    87: ("static", "WellMouth",
         "the well is empty and only the derrick and the mist coming back up out of the mouth are left; "
         "a fresh chisel mark on the shaft wall is still shedding dust and the rope on the winch has "
         "been wound one layer deeper; the people are only outlines at a distance",
         "do not put workers back at the shaft; do not clean the fresh chisel mark; do not unwind the "
         "winch rope"),
    88: ("static", "Terminal",
         "inside the factory a messenger dragged back from the west side still has his terminal lit; "
         "the death camp takes an unopened letter out of the terminal and the paper carries no "
         "signature; only the hand and the terminal enter the frame and no face is shown; a readout "
         "field in one corner shows the normalisation readout at 1.4%",
         "do not open the letter; do not show the content of the letter; do not give the messenger a "
         "face; do not put a signature on the paper"),
    89: ("static", "OpenLetter",
         "one letter lies spread open on the steel table and the layout is the layout of a contract "
         "with the clauses set in columns; the paper carries no signature; the clause columns are "
         "written straight in Chinese and read character by character",
         "do not add a signature; do not add a handwritten note; do not add any ritual element to the "
         "paper; do not put a second sheet on the table"),
    90: ("static", "OpenLetter",
         "the clauses state that one side issues the safe house quota and the medicine by batch and "
         "the other side delivers the high grade vapour cores by batch; the two clause lines fall on "
         "the paper line by line and the body text stays written straight in Chinese",
         "do not change the two clause lines; do not rewrite them in any other script; do not add a "
         "third clause"),
    91: ("static", "DeliveryLastPage",
         "the delivery column is turned to its last page and only a batch number and four characters "
         "are on it; the whole page carries no name of any person because the column holds areas and "
         "not people; the scientist has laid her own treatment duty roster beside it and the areas on "
         "the two sheets match",
         "do not write a name on the last page; do not add a fifth character; do not let the roster "
         "cover the last page"),
    92: ("static", "OpenLetter",
         "the protagonist lays the letter on the panel and reads it line by line until his fingertip "
         "stops on the last line; a readout field in one corner shows the normalisation readout at "
         "1.4% and the bone pattern stays flat on the skin surface",
         "do not let the fingertip leave the last line; do not hide the corner readout; do not break "
         "the skin under the bone pattern"),
    93: ("static", "TradeClauseSheet",
         "two things lie side by side on the steel table, the trade clauses and the progress of the "
         "well drilling; the two of them fill the middle of the frame; the paper text stays written "
         "straight in Chinese",
         "do not add a third object to the table; do not let the two sheets overlap; do not change the "
         "paper text"),
    94: ("static", "NameBoard",
         "the scientist works out one line of numbers in front of the name board and it is the limit "
         "of what the net fire can cover; the names on the board run in several columns and the "
         "numbers are written on the bottom line; the names and the numbers are written straight in "
         "Chinese",
         "do not put a second set of numbers on the board; do not cover the bottom line; do not build "
         "a face for the scientist"),
    95: ("static", "NameBoard",
         "the protagonist presses one vapour core against the name board and the grey patch retreats "
         "from the edge of the knuckles back to a pale tone; the black and white twin flame burns "
         "across and the result is one thread of white smoke and the normal skin tone of the back of "
         "the hand; the flame is only black and white",
         "do not add a third flame colour; do not leave a broken surface on the hand; do not spread "
         "the flame past the contact patch"),
    96: ("static", "NameBoard",
         "the protagonist does not argue back and looks at the last line of the name board for a long "
         "time; the fire in the purification zone burns until it is light and the list has grown by "
         "another stretch; a readout field in one corner shows the normalisation readout at 1.4%",
         "do not hide the corner readout; do not put the fire out; do not clear the last line of the "
         "board"),
}

# D11 景别 -> anchor shot_scale
SHOT_SCALE = {
    "远景": "wide", "全景": "full", "中远景": "medium_full",
    "中景": "medium", "近景": "close", "特写": "extreme_close",
}

# D11 movement -> camera motion_type
MOTION_TYPE = {
    "固定": "static", "推": "dolly", "拉": "dolly", "摇": "pan_tilt",
    "移": "dolly", "跟": "tracking", "升降": "crane", "环绕": "orbit",
    "手持": "handheld", "变焦": "dolly",
}

# 镜头运动类型 -> 禁止的改写
FORBIDDEN_MOTION = {
    "static": "do not add any camera move, zoom or handheld shake",
    "dolly": "do not convert the linear camera move into an orbit or a zoom",
    "tracking": "do not swap the follow move for an orbit or a frontal push",
    "crane": "do not hold a fixed high angle; the vertical travel must remain",
    "handheld": "do not stabilise the handheld rig or move onto the face",
    "orbit": "do not reduce the orbit to a static frame",
    "pan_tilt": "do not replace the pan with a dolly move",
}

# 每镜的交互合同：(interaction_id, [core names], start, end, relation, forbidden)
INTERACTIONS = {
    65: [("IX_6501", ["EncroachingShadowCrowd", "Yehongyi", "ShadowBlade"], 0.00, 1.00,
          "the shadow figures hold the half circle and the fighter stands in the gap with the blade "
          "across her front",
          "do not open the gap and do not light the blade edge")],
    66: [("IX_6601", ["ShadowBlade", "AshMoteBurst", "AshDeposit"], 0.10, 0.80,
          "the blade sweeps the street and the front row of the circle breaks into motes that settle "
          "into the brick seams",
          "do not leave a body in the dispersal and do not clear the settled ash")],
    67: [("IX_6701", ["RetreatingShadow", "Yechengjun", "JunctionBlock"], 0.00, 1.00,
          "the remaining shadows retreat into the unlit crossing and the leader is pushed onto the "
          "junction where the way out is cut",
          "do not light the crossing and do not bring the leader's face into view")],
    68: [("IX_6801", ["Luchen", "GreyFramePanel", "SteelGatePost"], 0.00, 1.00,
          "the figure walks out of the gate shadow and the corner readout stays legible beside him",
          "do not hide the corner readout and do not build a face for the figure")],
    69: [("IX_6901", ["LuchenHand", "StreetGround", "WellMist"], 0.00, 1.00,
          "the white band spreads along the street and presses the fog down while the wrist segment "
          "stays in frame",
          "do not show a mouth or a face and do not break the skin surface")],
    70: [("IX_7001", ["SuppressedCrowd", "AshMoteBurst"], 0.00, 1.00,
          "the people inside the pressed down range come apart into lit motes from near to far",
          "do not change the near to far order and do not show any body detail")],
    71: [("IX_7101", ["DataTablet", "SteelCrate", "Suqingci"], 0.15, 1.00,
          "the scientist rests the tablet on the crate top and the spectrum on the screen flattens",
          "do not turn the screen away and do not put a second object on the crate")],
    72: [("IX_7201", ["IdentityPlate", "EnemyChiefEmblem", "LuchenHand"], 0.20, 0.90,
          "the hand takes the two metal pieces off the brick face one by one",
          "do not put a third object on the brick face and do not add any red liquid")],
    73: [("IX_7301", ["IdentityPlate", "EnemyChiefEmblem", "SteelGatePost"], 0.00, 1.00,
          "the two metal pieces hang flat on the gate post face and nothing else is hung there",
          "do not hang a third object and do not put a readable badge on the metal")],
    74: [("IX_7401", ["Flagpole", "ThresholdStone", "Yehongyi"], 0.00, 0.70,
          "the fighter presses the pole into the seam of the threshold stone and the shaft comes up "
          "straight",
          "do not close the seam and do not bend the shaft once it is planted")],
    75: [("IX_7501", ["DataTablet", "PointerPen", "Suqingci", "Luchen"], 0.10, 0.85,
          "the scientist copies the plate number onto the tablet while the protagonist watches the flag "
          "from the inner side of the gate",
          "do not let the foreground shoulder cover the tablet and do not give the protagonist a face")],
    76: [("IX_7601", ["WheelRut", "RutQueue", "GreyFramePanel"], 0.00, 1.00,
          "the queue holds along the wheel ruts that press in from all sides while the corner readout "
          "stays lit",
          "do not give any queued person a face and do not remove the ruts")],
    77: [("IX_7701", ["QueueColumns", "WheelRut", "GateGuard"], 0.00, 1.00,
          "the line runs from the gate to the crossing along the ruts and the guards hold the two "
          "queue lanes beside the gate",
          "do not close the queue lanes and do not build the shed area")],
    78: [("IX_7801", ["TriageTable", "Suqingci", "NetFireSlot"], 0.20, 1.00,
          "the scientist splits the line into two columns at the triage table and the net fire slot "
          "stays at the head of the line",
          "do not merge the columns and do not close the aisle between them")],
    79: [("IX_7901", ["NameRoster", "PointerPen", "LuchenHand"], 0.10, 0.90,
          "the pen runs down the roster columns and then the protagonist takes the roster over and "
          "turns it to the last page",
          "do not make the names legible and do not add a second sheet")],
    80: [("IX_8001", ["Yehongyi", "ShadowBlade", "GreyFramePanel"], 0.00, 1.00,
          "the blade stays in the fighter's hand while the watch changes and the corner readout stays "
          "lit",
          "do not let the blade leave the hand and do not clear the fog")],
    81: [("IX_8101", ["LongQueue", "TriageTable", "NetFireSlot"], 0.00, 1.00,
          "the queue bends twice before it reaches the triage table and the net fire slot stays at the "
          "head",
          "do not straighten the bends and do not give any queued person a face")],
    82: [("IX_8201", ["OverduePatient", "AlteredPatient", "PassingPatient"], 0.00, 1.00,
          "the late ones slow down and the others walk around them while the altered ones hold the "
          "near ground as occlusion",
          "do not give an altered figure a face and do not let the patch edge break")],
    83: [("IX_8301", ["NewNotice", "NoticeWall", "MedicineCrate"], 0.00, 1.00,
          "the new notice stays flat on the notice wall while the medicine crate stands beside the "
          "triage table",
          "do not blank the notice and do not add a second poster")],
    84: [("IX_8401", ["GeometryBadgeColumn", "GreyFramePanel"], 0.00, 1.00,
          "the column walks through the corner in step while the corner readout stays lit",
          "do not put a religious symbol on the badges and do not break the column order")],
    85: [("IX_8501", ["WellDerrick", "Winch", "WellMist", "DerrickLamp"], 0.00, 1.00,
          "the winch turns on the derrick head and mist comes back up out of the well mouth under the "
          "single derrick lamp",
          "do not light the site otherwise and do not put a body in the mist")],
    86: [("IX_8601", ["DataTablet", "ToolBox"], 0.10, 1.00,
          "the tablet rests on the tool box top and the direction marker on the screen points to the "
          "outskirts",
          "do not turn the screen away and do not let the waveform fall")],
    87: [("IX_8701", ["WellMouth", "FreshChiselMark", "WinchRope"], 0.00, 1.00,
          "the well mouth stands empty with the fresh chisel mark still shedding dust and the winch "
          "rope wound one layer deeper",
          "do not put workers back and do not unwind the rope")],
    88: [("IX_8801", ["Terminal", "SealedLetter", "MessengerHand", "GreyFramePanel"], 0.00, 1.00,
          "the lit terminal lies by the messenger's hand and the sealed letter comes out of it while "
          "the corner readout stays lit",
          "do not open the letter and do not give the messenger a face")],
    89: [("IX_8901", ["OpenLetter", "SteelTable"], 0.00, 1.00,
          "the letter lies spread open on the steel table with the clauses in columns",
          "do not add a signature and do not add a second sheet")],
    90: [("IX_9001", ["OpenLetter", "SteelTable"], 0.00, 1.00,
          "the two clause lines fall on the paper while the rest of the table stays dark",
          "do not add a third clause and do not light the whole table")],
    91: [("IX_9101", ["DeliveryLastPage", "TreatmentRoster", "OpenLetter"], 0.05, 1.00,
          "the last page of the delivery column lies beside the treatment duty roster and the areas on "
          "the two sheets match",
          "do not write a name on the page and do not let the roster cover it")],
    92: [("IX_9201", ["OpenLetter", "LuchenHand", "GreyFramePanel"], 0.15, 1.00,
          "the fingertip stops on the last line of the letter while the corner readout stays legible",
          "do not let the fingertip leave the last line and do not hide the readout")],
    93: [("IX_9301", ["TradeClauseSheet", "WellProgressSheet", "SteelTable"], 0.00, 1.00,
          "the trade clauses and the well drilling progress lie side by side on the steel table",
          "do not add a third object and do not let the two sheets overlap")],
    94: [("IX_9401", ["NameBoard", "Suqingci", "NameBoardFrame"], 0.00, 1.00,
          "the scientist stands at the name board and the bottom line of numbers stays readable under "
          "the board frame",
          "do not cover the bottom line and do not build a face")],
    95: [("IX_9501", ["VapourCore", "BlackWhiteTwinFlame", "WhiteSmoke", "NameBoard"], 0.00, 0.75,
          "the vapour core is pressed against the board and the twin flame burns over the contact patch "
          "while one thread of white smoke rises",
          "do not add a third flame colour and do not leave a broken surface on the hand")],
    96: [("IX_9601", ["NameBoard", "PurifyFirePit", "Luchen", "GreyFramePanel"], 0.00, 1.00,
          "the fire in the purification zone burns on while the protagonist stays at the board and the "
          "corner readout stays lit",
          "do not put the fire out and do not hide the corner readout")],
}


def core_name(root: str) -> str:
    m = re.match(r"^[A-Z]-\d+_(?:CHAR|PROP|EXT|FX|LGT)_(.+?)(?:[._]\d+)?$", root)
    if m:
        return m.group(1)
    return re.sub(r"[._]\d+$", "", root)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ 声音
# 逐镜环境与动作音（英文，仅自然环境与动作音，不含对白与配乐）
SOUND = {
    65: "crushed brick under a boot step with wind running through the gap in the factory gate",
    66: "a run of breaking sounds that thins out and then goes quiet",
    67: "distant footsteps spreading out with wind through the street crossing",
    68: "a low hum with loose stones hopping on the street",
    69: "a low hum deepening with stones jumping in the vibration of the street",
    70: "a run of breaking sounds going from near to far and then no voice left",
    71: "a tablet prompt tone with a fine hiss of ash being pushed by the wind",
    72: "a light metal sound of the pieces lifting off the brick",
    73: "metal pieces settling against a steel post with wind across the gate",
    74: "the pole settling into the stone seam with cloth opening out in the wind",
    75: "paper and a stylus tip on a screen with the pen tapping twice",
    76: "a distant broadcast hum with many footsteps on a packed street",
    77: "many feet on brick with a low crowd murmur kept far off",
    78: "a crate being moved on cement with a tablet prompt tone",
    79: "a pen tip running down a page with pages being turned over",
    80: "one soft click of a shift change with distant footsteps on the road",
    81: "a long line of feet on brick with the queue turning twice",
    82: "slow dragging footsteps with the others stepping around them",
    83: "a poster being pressed flat on a metal wall with wind across the street",
    84: "a column of steps keeping time on the road with a distant broadcast",
    85: "a winch turning under load with a deep hum rising out of the shaft",
    86: "a tablet prompt tone with a sustained low note under it",
    87: "dust falling off the shaft wall with the winch rope creaking",
    88: "a terminal prompt tone with paper friction on a hard floor",
    89: "paper pages turning over on a steel table",
    90: "paper pages turning with a pen tip touching the sheet",
    91: "paper turning with a pen tip pointing at a sheet",
    92: "paper friction with a fingertip stopping on the sheet and wind outside the roof",
    93: "paper pages turning with the fire of the purification zone in the distance",
    94: "a piece of chalk writing on a board with pages being turned over",
    95: "a low breath of the twin flame with a fine hiss of smoke dispersing",
    96: "fire in the purification zone with footsteps of a shift change far off",
}

# ------------------------------------------------------------------ 全局风格合同
# 来自共享 D10 风格合同（冷峻工业末世写实底 + 克制的能量风格化）+ U03 场景扩展
STYLE_BIBLE = {
    "world_and_era": (
        "post-collapse industrial city ruins; a walled mechanical factory compound with one gate, a "
        "brick street in front of it and an outskirts bone well being sunk outside the city; ration "
        "queues, name rosters and posted notices govern daily life; survivors and ceramic-pale "
        "altered ones share the same cold daylight and fog; no readable signage and no modern branding"),
    "visual_language": (
        "grounded industrial realism for humans and props with a separated stylisation layer for the "
        "bone pattern, the ash motes, the twin flame, the white smoke and the projected interface "
        "text; stylised elements never spill across into the human layer and every body surface "
        "stays intact"),
    "palette": (
        "grey fog cyan-grey #4A5A5C as the global base, ink shadow #171B1D with detail kept in the "
        "darks, plaster white #C6C2B8 for ceramic shells, pure-fire white #F5F7F8 and black #0B0B0C "
        "for the twin colour bone pattern and the twin flame, weld and fire orange #E07B39 as the "
        "only warm accent, dark red #7A2027 reserved for the fighter's outfit and never for any liquid"),
    "material_language": (
        "real skin with pores and slight oil sheen, matte technical fabric with wear and dust, "
        "oxidised steel with dull reflections, cold ceramic shells on altered bodies; every surface "
        "stays intact and no red liquid appears anywhere in the frame"),
    "environment_design": (
        "a brick street cut by wheel ruts in front of a single gate with two steel posts, a gate wall "
        "with one open cross street at the far end, a registration desk and a triage table inside "
        "the gate, one steel table in the inner factory room with a name board on its north wall, and "
        "one wooden derrick over a square well mouth on the outskirts"),
    "prop_design": (
        "functional utilitarian tooling with real weight and thickness: gate posts, threshold stone, "
        "a flagpole and its cloth, steel crates and tables, rosters and notices, a data tablet, a "
        "terminal, a sealed letter, a winch and its rope, a name board and vapour cores; all carry "
        "visible use marks"),
    "lighting_and_atmosphere": (
        "one cold overhead key over the steel table with shadow detail retained instead of crushed "
        "black, cold grey bounce from concrete and steel, the emergency lamps on the gate posts, the "
        "residual fire heads, the twin flame and the derrick lamp as the only moving light sources, "
        "and the grey fog pressing down over the street with the unlit crossing kept dark"),
}


# ------------------------------------------------------------------ primary 主体指定
# importance=primary 的 entity，其每个实例都会进入 anchor 的 D= 明细段（含 o/m/r 文本），
# 人群级 entity 会把 6500 预算撑爆。故 primary 一律取单实例 entity；
# 群体主体仍由 shots[].camera_contract.tracked_target_entity 表达。
PRIMARY_PICK = {
    65: "Yehongyi",        # 包围者为群体；画面锚点取缺口处持刃的叶红衣
    76: "GreyFramePanel",   # 沿辙排开的队伍为群体；画面锚点取视野一角的读数栏
    77: "WheelRut",         # 排队区为群体；画面锚点取压在砖面上的车辙
    81: "TriageTable",      # 长队为群体；画面锚点取分诊台
    82: "AlteredPatient",   # 逾期者为群体；画面锚点取作遮挡的异化者
    84: "GreyFramePanel",   # 徽记队列为群体；画面锚点取视野一角的读数栏
}
