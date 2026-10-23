#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D14 逐镜 Render Contract / Appearance 填写器（U02 单元）。

原则：
- source_inventory 不删不改（preflight 依 Blender structure_evidence 生成）。
- 每个描述字段只写一个可见事实，且用英文（技能要求）。
- 锚点的可见性/包围盒取 Blender 实测证据；朝向/运动状态/空间关系由实测轨迹与
  投影框推导，不臆测。
- 运动合同按白模实测位移/形变判定；实测无位移者一律 static（不得自行动画化）。

U02 口径（与 U01 同构，差异只有三处）：
- 镜头号段 = 全局镜号 33..64（ep9–ep16，32 镜），不是 1..32。
- core_name() 正则放宽为 `^[A-Z]-\d+_(?:CHAR|PROP|EXT|FX|LGT)_(.+?)(?:[._]\d+)?$`，
  以便剥离 U02 场景码前缀（B-1…B-10）；U01 的 A-1…A-9 行为完全不变。
- 台词不进 D14：D14 只承载画面与环境音，台词由 D15/后期负责。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

# 注：本模块只提供**内容表**（语义/动作/交互/声音/风格）。
# 项目根与白模工作区一律由调用方（fill_D14_contracts.py）按 --project/--work 传入，
# 此处不写死任何绝对路径 —— 内容模块若自带路径，跨单元复用时会静默指向错误单元。

# ------------------------------------------------------------------ 实体语义
# core -> (entity_class, source_role, structural_constraints)
# 词汇表 = _U02_DESIGN_CONTRACT.md §3（角色 17 + 道具 50），一个不漏。
SEMANTIC = {
    # ---- 角色 ----
    "Luchen": ("articulated", "protagonist blockout in black tactical coat",
                "human height 1.80m; joint envelope fixed by source blockout"),
    "LuchenHand": ("articulated", "protagonist raised hand blockout",
                   "0.30m hand volume; stays attached to the protagonist forearm"),
    "Yehongyi": ("articulated", "female fighter character blockout in dark red outfit",
                 "human height 1.70m; carries the shadow blade at her side"),
    "Suqingci": ("articulated", "female scientist character blockout in white lab coat",
                 "human height 1.68m; holds the data tablet against the chest"),
    "Yechengjun": ("articulated", "male officer antagonist blockout in ivory short jacket",
                   "human height 1.81m; black shoulder boards keep their shape"),
    "Yechongyue": ("articulated", "family heir blockout seen from the back only",
                   "human height 1.78m; only shoulder and back enter the frame"),
    "GreySpottedPatient": ("articulated", "patient blockout with grey patched skin",
                            "human height 1.75m; the grey patch pattern stays on the skin surface"),
    "WelderWorker": ("articulated", "worker blockout welding the barrier gate",
                     "human height 1.76m; holds the welding torch against the door leaf"),
    "QueueMember": ("articulated", "queue member blockout in silhouette",
                    "0.60x0.60x1.75m body; no face is ever built or shown"),
    "GuardPostMember": ("articulated", "guard post member blockout in two columns",
                        "0.60x0.60x1.75m body; column order and count preserved"),
    "OrderSquadMember": ("articulated", "order squad member blockout clearing the line",
                         "0.60x0.60x1.75m body; moves with the squad column"),
    "CleanedPatient": ("articulated", "purified patient blockout with rolled sleeves",
                       "0.60x0.60x1.75m body; sleeves stay rolled up, skin clean"),
    "MarketTrader": ("articulated", "market stall trader blockout",
                     "human height 1.72m; no face is ever built or shown"),
    "MarketQueuer": ("articulated", "market queue member blockout in two columns",
                     "0.60x0.60x1.73m body; column order preserved, no face"),
    "RefugeeCrowdMember": ("articulated", "refugee crowd blockout in the dark",
                           "0.60x0.60x1.74m body; silhouette only, no face"),
    "AssassinLeader": ("articulated", "assassin group leader blockout across the junction",
                       "human height 1.79m; opposite silhouette, no face"),
    "Rescuee": ("articulated", "trapped person blockout crossing the gap",
                "0.60x0.60x1.73m body; outline only, no body detail"),
    # ★ 契约 §3.1 原词汇表只列了 17 个角色 core，但 D11 g47 明写「死士营的人站在门内
    #   看着门外，人影挤在门框里」—— 门框内这组人影无对应 core。
    #   处理：补登 DeathCampMember（死士营成员）作为第 18 个人形 core，
    #   与「秩序队」「岗哨」分属不同阵营，不可混用。
    "DeathCampMember": ("articulated", "death camp member blockout inside the door frame",
                        "0.60x0.60x1.75m body; packed inside the door frame, no face"),
    # ---- 建筑与场地 ----
    "ReinforcedCloister": ("environment", "reinforced lockable cell shell",
                           "steel lined room; encloses the safe and its door"),
    "PerimeterWall": ("environment", "perimeter wall of the factory yard",
                      "2.20m high steel plate run; carries the posted shadows"),
    "DarkJunction": ("environment", "unlit stretch outside the factory gate",
                     "no lamp inside the zone; stays dark for the whole shot"),
    # ---- 空间壳体（白模 SHELL 的 group 名直接作为 core，须逐个登记）----
    "FactoryYardGround": ("environment", "factory yard ground plate",
                          "one continuous plate from the outer yard into the hall; no seam"),
    "FactoryHallShell": ("environment", "factory hall walls and roof",
                         "26x18m hall; 12.00m clear height; carries the roof"),
    "FactorySouthFacade": ("environment", "factory south facade with the two openings",
                            "main gate opening 4.00x4.50m; side door opening 3.00x3.50m"),
    "WestPlantShell": ("environment", "combustible old steel frame of the west plant",
                       "X -22..-16 / Y -20..0; old frame columns only"),
    "MarketStreetGround": ("environment", "black market street ground plate",
                           "48x28m street; independent baseline at the street midpoint"),
    "MarketStreetBackdrop": ("environment", "black market street side building bands",
                             "far side bands; read as street depth only"),
    "MeetingRoomShell": ("environment", "meeting room shell in the factory east span",
                         "8x5m room; holds the defence map table"),
    "CommandCockpitShell": ("environment", "sealed command cockpit shell",
                            "6x5m room; lighting kept at the lowest level"),
    # ---- 道具 ----
    "MainRollerDoor": ("rigid", "roller door leaf of the factory south facade",
                       "4.00m wide; closed panels stack upward"),
    "WeldedGate": ("rigid", "welded barrier gate across the side door",
                   "3.00x0.12x2.20m; the weld seam grows across the leaf"),
    "SteelRack": ("rigid", "steel rack row used as cover and as a fire break",
                  "4.00x0.60x2.20m each; row order and count preserved"),
    "SteelStockPile": ("rigid", "stacked stainless steel stock pile",
                       "0.80x0.60x0.40m bundle; piled apart from the racks"),
    "WaterBucket": ("rigid", "well water bucket",
                    "0.34m diameter; stands on the ground"),
    "SideDoor": ("rigid", "side door leaf of the factory shell",
                 "1.10x2.05m leaf; pushed open and stays open"),
    "DataTablet": ("rigid", "handheld data tablet",
                   "0.30x0.22x0.02m; screen faces outward when held to the chest"),
    "WelderRig": ("rigid", "welding equipment beside the door",
                  "0.60x0.40x0.70m; the torch cable stays connected"),
    "SteelWorkbench": ("rigid", "steel work bench in the purification zone",
                       "2.00x0.80x0.90m; the patient lies on the top"),
    "ColdWhiteIndustrialLamp": ("rigid", "cold white industrial lamp over the bench",
                                "single overhead tube; the only light source in the zone"),
    "BlackWhiteTwinFlame": ("effect", "black and white twin flame on the treated arm",
                            "0.18x0.05x0.30m; clings to the contact patch of skin"),
    "WhiteSmoke": ("effect", "white smoke rising off the treated arm",
                   "0.05m puffs within 0.30m radius; dissipates upward"),
    "DefenseBlueprint": ("rigid", "defence blueprint sheet on the steel table",
                         "0.90x0.60m sheet; the four annotated categories stay legible"),
    "PlywoodWall": ("rigid", "plyboard wall carrying the pinned blueprint",
                    "3.00x2.40m panel run; keeps the pinned sheet flat"),
    "SteelTable": ("rigid", "steel table in the drawing and extraction zone",
                   "2.40x1.00x0.75m; carries the roster, the map and the seal"),
    "VapourExtractionLine": ("rigid", "vapour core extraction line",
                             "three stage run of 3.00m sections; carries the blocks along the run"),
    "PressSlot": ("rigid", "press slot on the extraction line",
                  "0.60x0.60x0.80m; compacts the vapour core into a block"),
    "OutfeedTable": ("rigid", "outfeed table at the end of the line",
                     "1.20x0.80x0.75m; the frosted blocks stack here"),
    "EnergyBlock": ("rigid", "frosted energy block",
                    "0.18x0.12x0.08m; white frost on the edges"),
    "DutyRoster": ("rigid", "duty roster sheet pinned to the plyboard wall",
                   "0.60x0.80m sheet; the column headings stay legible"),
    "GreyFramePanel": ("rigid", "floating grey frame interface panel",
                       "non solid overlay; never casts shadow or blocks the set"),
    "OldSheetMetalWall": ("rigid", "old sheet metal wall carrying the notice projection",
                          "4.00x2.60m panel run; carries the projected columns"),
    "CitywideNoticeProjection": ("rigid", "citywide notice projected on the sheet metal wall",
                                  "projected column text overlay; no speaker in the frame"),
    "GateQueue": ("articulated", "crowd blockout waiting at the factory gate",
                  "one distant line; bodies count preserved, no face is built"),
    "OrderSquad": ("articulated", "order squad blockout taking the line away",
                   "squad bodies keep their order; no face is built"),
    "MarketLedBoard": ("rigid", "led board over the market street",
                       "1.80x1.20m screen; the scrolling entries stay readable"),
    "MarketStalls": ("rigid", "market stall row along the street",
                     "2.40x1.80x2.10m each; the row order is preserved"),
    "CleanMarrowSignboard": ("rigid", "wooden board at the market stall front",
                             "0.90x0.60m board; the written rule stays legible"),
    "TradeCounter": ("rigid", "trade counter in front of the stalls",
                     "2.00x0.80x0.95m; the goods are laid out on its top"),
    "ShadowBlade": ("rigid", "shadow blade laid across the way",
                    "0.05x0.05x0.90m blade; edge stays unlit in every frame"),
    "LawStrip": ("rigid", "law strip metal bar",
                 "0.24x0.03x0.05m; engraved lines hold the cold light, never taken apart"),
    "SteelSafe": ("rigid", "steel safe built into the reinforced cell",
                  "0.90x0.80x1.20m; the door closes and stays closed"),
    "EmptyShelf": ("rigid", "empty stall shelf",
                   "1.80x0.40x1.60m; every shelf tier stays empty"),
    "SupplyCutNotice": ("rigid", "supply cut notice sheet on the bare counter",
                        "0.30x0.42m sheet; it stays pressed on the counter"),
    "SteelGatePost": ("rigid", "steel gate post at the factory gate",
                      "0.30x0.30x3.00m; the nailed board stays flat on its face"),
    "AppointmentBoard": ("rigid", "wooden appointment board on the gate post",
                         "0.80x0.50m board; the written rule stays legible"),
    "QuotaRoster": ("rigid", "quota roster sheet on the meeting table",
                    "0.60x0.84m sheet; the machine factory row keeps a blank signature"),
    "CommitteeScreen": ("rigid", "committee screen on the far side of the meeting table",
                        "1.60x0.90m screen; the last cost entry stays unclosed"),
    "CityDefenseMap": ("rigid", "city defence map sheet on the meeting table",
                       "1.20x0.80m sheet; the marked factory name stays readable"),
    "HeirSeal": ("rigid", "family heir seal pressed on the map",
                 "0.08x0.08x0.04m; stays pressed beside the marked name"),
    "EntryRoster": ("rigid", "entry roster and entry order on the command room table",
                    "0.60x0.84m sheet; the names stay illegible"),
    "OldCottonCoat": ("rigid", "old cotton coat worn inside the refugee crowd",
                      "worn over the body; the sleeve keeps covering the armour corner"),
    "StandardArmour": ("rigid", "standard armour corner under the sleeve",
                       "only a corner is exposed; never a full piece of armour"),
    "EmergencyLamp": ("rigid", "emergency lamp on the perimeter wall",
                      "0.20x0.12x0.16m; the only light source after the cut"),
    "UnexpectedShadow": ("rigid", "shadow shape cast on the perimeter wall",
                         "flat card on the wall face; count and spacing stay readable"),
    "FireHead": ("effect", "fire head flaring in the yard",
                 "three separate heads; each keeps its own position, none merges"),
    "FireLine": ("effect", "fire line running along the plant separation structure",
                 "low burning band; cuts the yard into separate blocks"),
    "PointerPen": ("rigid", "pointer pen resting on the defence map",
                   "pen tip lands on the plant name; the map stays under it"),
    "SteelPick": ("rigid", "long steel pick carried to the wall post",
                  "1.80m pick; separated from the ammunition crate"),
    "AmmunitionBox": ("rigid", "ammunition crate at the wall post",
                      "0.40x0.28x0.26m crate; kept apart from the pick"),
    "GapOpening": ("rigid", "gap left between two lifted steel racks",
                    "one person wide; the opening stays open for the whole shot"),
}

# ------------------------------------------------------------------ 镜头数据
# gsn -> (motion_type, subject_core, actions_en, forbidden_reinterpretations)
# gsn 为 U02 的全局镜号 33..64；motion_type 由 D11 movement 机械推出。

# ------------------------------------------------------------------ 人形实体集合
# 供消费方 fill_D14_contracts.py 的 orientation_of() 使用：这些 core 按**人形**代理
# 描述朝向（俯卧 / 直立 / 蹲伏），其余按通用体块描述。
# ⚠️ 必须**显式声明**：旧版消费方把名单写死 U01 的 7 个 core，U02 角色会落通用体积描述。
HUMAN_CORES = {
    "Luchen",
    "LuchenHand",
    "Yehongyi",
    "Suqingci",
    "Yechengjun",
    "Yechongyue",
    "GreySpottedPatient",
    "WelderWorker",
    "QueueMember",
    "GuardPostMember",
    "OrderSquadMember",
    "CleanedPatient",
    "MarketTrader",
    "MarketQueuer",
    "RefugeeCrowdMember",
    "AssassinLeader",
    "Rescuee",
    "DeathCampMember",
    # 群体人形（虽然由 MULTI 合成，仍按人形描述朝向）
    "GateQueue",
    "OrderSquad",
}

SHOT_DATA = {
    33: ("dolly", "WeldedGate",
         "a welding torch arcs against the rusted roller door leaf and the weld seam grows from nothing "
         "into one continuous gate bar; sparks fall on the cement floor leaving a momentary warm point "
         "only at the contact spot, the rest of the hall under cold industrial light; steel racks are "
         "lifted into a stacked cover and steel stock with the water bucket are piled to the inner ring",
         "do not split the weld into two separate steps; the seam must read as growing from nothing to a "
         "complete gate; do not let the arc light the whole hall"),
    34: ("tracking", "Suqingci",
         "at the inner face of the factory gate the fighter pushes the side door open and drags the "
         "scientist through it, the data tablet pressed flat to her chest with the screen facing out; a "
         "third person comes in with the arm and the back of the neck bare and covered in grey-white "
         "patches; the three bodies crowd into the door frame",
         "do not show any face; the grey patches stay a side view with their edges complete; do not turn "
         "the tablet screen away from camera"),
    35: ("static", "LuchenHand",
         "the protagonist takes the tablet without looking at any face and knocks twice on its back panel "
         "with his knuckles, the screen staying lit; a readout field in one corner shows the normalisation "
         "readout at 0.7%, and the bone pattern on his right wrist stays stopped at the wrist side "
         "without reaching the forearm",
         "do not show a face; do not let the bone pattern run past the wrist; do not change the readout value"),
    36: ("static", "Suqingci",
         "the scientist backs away behind the steel rack with the tablet held to the chest and turns the "
         "head from the welded gate to the silent queue holding steel rods; the queue stands still in the "
         "depth with the faces kept out of frame and only the outlines cut out by the hall light",
         "do not give any queue member a face; do not turn the step back into a camera move; do not light "
         "the depth enough for a face to read"),
    37: ("tracking", "Suqingci",
         "under the single cold white industrial lamp the scientist walks toward the door with the tablet "
         "against the chest, the hem of her white lab coat swinging with the steps; the protagonist does "
         "not stop her, he only shifts half a step aside; the two figures hold opposite sides of the frame "
         "with a clear aisle between them",
         "do not let the protagonist grab or hold her; do not close the aisle between the two figures; do "
         "not turn the follow into a frontal push"),
    38: ("static", "BlackWhiteTwinFlame",
         "a person lies on the steel work bench with grey patches covering the whole arm; the protagonist "
         "lays his right hand over it and the black and white twin flame ignites against the skin, the lit "
         "area confined to the patch under the palm; outside the flame the bench stays under cold hall "
         "light and the chest below rises and falls",
         "do not let the flame spread beyond the contact patch or cover the whole arm; do not add any "
         "broken skin or red liquid; keep the chest rise visible"),
    39: ("static", "WhiteSmoke",
         "white smoke rises from the edge of the grey patches and disperses upward until it is gone, the "
         "grey fading back to natural skin tone with the surface underneath intact; the chest on the bench "
         "slows its rise and fall and the fingers loosen; the hem of the white lab coat leaves the frame "
         "on the right",
         "do not leave any grey patch, broken skin or stain behind; do not let the smoke hang in the frame; "
         "do not bring the coat hem back into frame"),
    40: ("static", "LuchenHand",
         "the black and white bone pattern runs from the wrist bone across the forearm and climbs all the "
         "way to the elbow, the two colours surfacing flat against the skin; a readout field in one corner "
         "shows the normalisation readout at 1.0%; the scientist crouches and wipes the old conclusion "
         "off the tablet screen",
         "do not stop the pattern at the forearm; do not break the skin under the pattern; do not hide the "
         "corner readout"),
    41: ("static", "DefenseBlueprint",
         "a defence blueprint lies open on the steel table with four categories of Chinese annotation "
         "marked out on it, access positions, load bearing walls, evacuation routes and clean water "
         "sources; the scientist's fingertip travels over each annotation in turn; the ink is still wet "
         "with a water stain in one corner",
         "do not replace the four annotated categories with other labels; do not add a second sheet or "
         "extra drawings; do not let the finger cover the annotation text"),
    42: ("dolly", "VapourExtractionLine",
         "the blueprint is pinned to the plyboard wall and the steel racks are rearranged into two rows "
         "along its load bearing lines, leaving a walkway against the wall; the vapour core extraction line "
         "runs for the first time, the press slot compacts a core into an energy block and the frosted "
         "block is stacked on the outfeed table",
         "do not break the process into disconnected stages; do not add a separate view of the feed inlet; "
         "do not turn the lateral travel into an orbit"),
    43: ("static", "GuardPostMember",
         "a line of people stand in two columns against the duty roster on the wall, their steps landing "
         "on the same beat; the roster stays pinned above them with its column headings legible, and a grey "
         "frame panel pops up in one corner of the frame",
         "do not give any guard a face; do not merge the two columns into one; do not hide the roster sheet "
         "or the corner panel"),
    44: ("static", "MarketLedBoard",
         "the led board of the market street lights up and the first trading entry scrolls onto it with "
         "the Chinese item lines moving upward line by line; the stall fronts below the board light up one "
         "row after another in the depth, and street figures gather in front of the trading entry",
         "do not give the gathered figures a face; do not build the market as a full scene; do not stop the "
         "scroll with the first entry unreadable"),
    45: ("static", "CitywideNoticeProjection",
         "a citywide notice is projected on an old sheet metal wall, the Chinese body text laid out in "
         "columns with the ration grading table and the treatment sequence side by side; the second column "
         "counts civilians with grey patches as abandoned material outside the treatment sequence",
         "do not put a speaker in the frame; do not merge the columns or rewrite the second column; do not "
         "add a third table"),
    46: ("static", "GateQueue",
         "the road outside the factory is held as a distant band with the people waiting for medicine in "
         "one line; the order squad takes the tail away in batches and the crowd disperses into the grey "
         "fog, one figure turning the head back toward the gate",
         "do not show any face; do not bring the line close to camera; do not lose the single head turn "
         "back toward the gate"),
    47: ("static", "Luchen",
         "the people of the camp stand inside the gate looking out with their bodies crowded into the door "
         "frame; the protagonist stands in the foreground with the shoulder line cutting one corner of the "
         "frame and turns the head to look at the line outside the gate",
         "do not give a face in the door frame; do not turn the head turn into a camera move; do not widen "
         "the frame so the shoulder line stops covering the corner"),
    48: ("static", "CleanedPatient",
         "the protagonist turns and gathers the purified patients, and a few of them close into a half "
         "circle in the cold white light with their sleeves rolled up; a readout field in one corner shows "
         "the normalisation readout at 1.2% as he looks up toward the supply road outside the gate",
         "do not bring the grey patches back on the purified arms; do not close the half circle into a full "
         "ring; do not hide the corner readout"),
    49: ("static", "CleanMarrowSignboard",
         "the market stall is set up and four characters are pressed below the led board; on a wooden board "
         "at the front of the stall the exchange rule is written out, one purification in exchange for rare "
         "material with no vapour core taken; the people in the line walk around the end of the stall",
         "do not give the trader or the line a face; do not leave the board blank; do not turn the written "
         "rule into a spoken line"),
    50: ("static", "ShadowBlade",
         "vapour cores, steel stock and reagents are laid out on the counter one piece at a time and the "
         "line walks around the end of the stall into two columns; the fighter's shadow blade lies across "
         "the counter front with its edge kept unlit",
         "do not light the blade edge; do not swing or lift the blade; do not let a queue face enter the frame"),
    51: ("static", "LawStrip",
         "one law strip is pushed up onto the trade counter, the engraved lines holding the cold light with "
         "the face of the strip lying fully in frame; the hand of the scientist moves over the lines and the "
         "fingertip stops on them; the counter holds this single object and nothing else",
         "do not break the strip open or take it apart; do not put a second object on the counter; do not add "
         "a glow to the engraved lines"),
    52: ("static", "SteelSafe",
         "the safe door closes and the law strip is locked into the reinforced cloister, the last line of "
         "cold light in the door gap going out; a readout field in one corner shows the normalisation "
         "readout at 1.2% while the led board in the far market direction scrolls several price entries",
         "do not leave the safe door open or the strip in view; do not move the corner readout; do not show "
         "the strip taken apart"),
    53: ("static", "EmptyShelf",
         "the shelves of the market stall stand completely empty and the supply cut notice lies pressed on "
         "the bare counter; the people in the line look at the empty shelves and start to disperse while "
         "price increase entries roll on the led board behind them; only one wooden board is left at the stall",
         "do not put any goods back on the shelves; do not add a speaker or a committee figure; do not remove "
         "the supply cut notice"),
    54: ("static", "AppointmentBoard",
         "a wooden board is nailed to the steel gate post inside the factory gate, its face carrying the "
         "appointment numbering and the daily limit of twenty; the protagonist straightens it and his palm "
         "rests on the face, while a long line stands in the grey fog outside the gate",
         "do not let the palm cover the written rule; do not bring the line outside the gate into the "
         "foreground; do not take the board off the post"),
    55: ("static", "QuotaRoster",
         "a quota roster lies open on the meeting table and the row for the machine factory has nobody "
         "signing it, the blank signature space pressed into the paper; across the table the committee "
         "screen lights up in cold gold with a column of cost entries, the last entry left unclosed",
         "do not fill in the signature space; do not close the last cost entry; do not merge the roster and "
         "the screen into one surface"),
    56: ("static", "CityDefenseMap",
         "a city defence map lies open at the far end of the meeting table, the machine factory marked on "
         "it; the tip of a pen rests on that name and a family heir seal is pressed beside it, while the "
         "protagonist's shoulder and back fill one near side of the frame and a readout field in one corner "
         "shows the normalisation readout at 1.3%",
         "do not lift the pen tip off the marked name; do not turn the near shoulder into a full figure; do "
         "not move the corner readout"),
    57: ("static", "EntryRoster",
         "the entry roster and the entry order lie open on the steel table of the sealed command room with "
         "the lighting pressed to its lowest level; the officer stands behind the table, his ivory jacket "
         "and black shoulder boards reading as outline only, and his fingertip presses on the last few "
         "names on the roster",
         "do not raise the lighting; do not bring the officer's face into the light; do not make the names "
         "on the roster legible"),
    58: ("static", "RefugeeCrowdMember",
         "a crowd of refugees pours into the outer ring of the factory district with the old cotton coats "
         "mixed in among them; from under one sleeve a corner of standard armour shows and is covered again "
         "by the sleeve; everyone stays a silhouette in the dark",
         "do not show any face; do not push the armour corner into a close detail; do not put the armour "
         "outside the coat"),
    59: ("static", "DataTablet",
         "the data tablet is supported in the palm of the scientist and the spectrum on its screen jumps "
         "with uneven noise, the peaks spaced irregularly; her fingertips are reflected along the edge of "
         "the screen and press on the rim of the board",
         "do not bring the scientist's face into frame; do not smooth the noise into an even spectrum; do "
         "not add a second device"),
    60: ("static", "UnexpectedShadow",
         "after the lights are cut the factory yard keeps only the low level of the emergency lamps and an "
         "extra row of shadows that should not be there appears on the perimeter wall, countable at a "
         "glance; steel rods and ammunition are issued to the wall posts, and the fighter walks the wall "
         "alone with the shadow blade half drawn and pushed back; a corner readout shows the normalisation "
         "readout at 1.3%",
         "do not change the number or the spacing of the shadows on the wall; do not light the blade edge "
         "when it is pushed back; do not raise the ambient light"),
    61: ("static", "GreyFramePanel",
         "a panel floats in the centre of the protagonist's view and two lines of Chinese text light up one "
         "line after another, the archive deadline of fourteen days and the line stating that untreated grey "
         "patches begin to change; below the panel a corner of the factory hall sits and the first fire "
         "light rises in the far distance",
         "do not show any changed body; the second line stays as text on the panel only; do not move the "
         "panel out of the frame centre"),
    62: ("static", "FireHead",
         "three fire heads flare up at different positions across the yard, one beyond the perimeter wall "
         "and two in the west side workshop; the fire line runs along the dividing structure and cuts the "
         "yard into separate blocks, leaving one narrow way out while the factory gate stays lit on the right",
         "do not merge the three fire heads into one or change their count; do not show any burning body; "
         "keep the narrow way out visible"),
    63: ("tracking", "GapOpening",
         "two steel racks are lifted up across the front of the fire line and a gap is left between them; "
         "the trapped people pass through that gap one at a time, the line holding together in the smoke, "
         "while the protagonist pulls the last one out of the workshop",
         "do not close the gap between the racks; do not show any body detail in the smoke; keep the gap "
         "wide enough for one person at a time"),
    64: ("static", "ShadowBlade",
         "a stretch outside the factory gate has no light and the fighter stands at the junction, her dark "
         "red outfit reading as outline only; the shadow blade lies across the centre of the junction with "
         "its edge unlit and the assassin leader stands on the far side over trodden out fire sparks; "
         "daylight turns black and the grey fog sky presses down over the factory while a corner readout "
         "shows the normalisation readout at 1.4%",
         "do not light the blade edge; do not give the leader a face; do not light the junction with an "
         "artificial lamp"),
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
    33: [("IX_3301", ["WeldedGate", "WelderRig", "WelderWorker"], 0.00, 1.00,
         "the welding torch stays against the door leaf while the seam grows across the gate bar",
         "do not move the seam off the door leaf and do not add a second welding point")],
    34: [("IX_3401", ["Yehongyi", "Suqingci", "DataTablet", "SideDoor"], 0.00, 1.00,
         "the fighter drags the scientist through the side door with the data tablet pressed to her chest",
         "do not release the tablet and do not close the side door before the entry")],
    35: [("IX_3501", ["LuchenHand", "DataTablet"], 0.15, 0.55,
         "the knuckles knock twice on the back panel of the tablet while the screen stays lit",
         "do not knock on the screen face and do not drop the tablet")],
    36: [("IX_3601", ["Suqingci", "SteelRack", "QueueMember"], 0.10, 1.00,
         "the scientist backs behind the steel rack with the tablet held to the chest while the queue stands "
         "holding steel rods in the depth",
         "do not give any queue member a face and do not bring the queue forward out of the depth")],
    38: [("IX_3801", ["LuchenHand", "BlackWhiteTwinFlame", "GreySpottedPatient"], 0.00, 1.00,
         "the twin flame clings to the patch of skin under the palm on the patient's arm",
         "do not spread the flame beyond the contact patch and do not break the skin surface")],
    39: [("IX_3901", ["WhiteSmoke", "GreySpottedPatient"], 0.00, 0.70,
         "the white smoke rises off the grey patches and the skin underneath returns to its natural tone",
         "do not leave the patches on the skin and do not add any red liquid")],
    40: [("IX_4001", ["LuchenHand", "Suqingci", "DataTablet"], 0.30, 1.00,
         "the scientist crouches and picks the tablet up while the bone pattern reaches the elbow",
         "do not shorten the pattern and do not hide the corner readout")],
    42: [("IX_4201", ["VapourExtractionLine", "PressSlot", "EnergyBlock", "OutfeedTable"], 0.20, 1.00,
         "the press slot compacts a vapour core into a frosted energy block that is stacked on the outfeed table",
         "do not break the chain into separate stages and do not change the frosted edges")],
    43: [("IX_4301", ["GuardPostMember", "DutyRoster"], 0.00, 1.00,
         "the two columns stand against the pinned duty roster and keep their order",
         "do not merge the columns and do not take the roster off the wall")],
    44: [("IX_4401", ["MarketLedBoard", "MarketStalls"], 0.00, 1.00,
         "the led board lights up and the stall fronts below it light up one row after another in the depth",
         "do not build the market as a full scene and do not stop the scroll with the first entry unreadable")],
    46: [("IX_4601", ["GateQueue", "OrderSquad"], 0.25, 1.00,
         "the order squad takes the tail of the waiting line away in batches and the line disperses into the fog",
         "do not bring the line close to camera and do not show any face")],
    49: [("IX_4901", ["MarketTrader", "CleanMarrowSignboard", "MarketQueuer"], 0.10, 1.00,
         "the trader sets the stall up with the written board at the front and the line walks around its end",
         "do not give the trader or the line a face and do not blank the board")],
    50: [("IX_5001", ["ShadowBlade", "MarketQueuer", "TradeCounter"], 0.30, 1.00,
         "the shadow blade lies across the front of the counter and the queue is held in two columns behind it",
         "do not light the blade edge and do not let the queue cross the blade")],
    51: [("IX_5101", ["LawStrip", "TradeCounter", "Suqingci"], 0.10, 1.00,
         "the law strip is pushed up onto the counter and the scientist's fingertip stops on the engraved lines",
         "do not break the strip open and do not put a second object on the counter")],
    #   ⚠️ 不列 LawStrip：律条此刻**锁进小间**、按本行 forbidden 约束本就「不得可见」，
    #      故它不是 g52 的可见实例（不进 source_inventory）。「律条被锁进去」这一事实
    #      由 relation 文本承载；实例清单只挂**看得见的**柜体与小间。
    52: [("IX_5201", ["SteelSafe", "ReinforcedCloister"], 0.00, 0.80,
         "the law strip is locked into the reinforced cloister and the safe door closes on it",
         "do not leave the strip visible and do not open the safe door again")],
    53: [("IX_5301", ["EmptyShelf", "SupplyCutNotice"], 0.00, 1.00,
         "the supply cut notice stays pressed on the bare counter while every shelf tier of the stall stays empty",
         "do not put any goods back on the shelves and do not remove the notice")],
    54: [("IX_5401", ["AppointmentBoard", "SteelGatePost"], 0.15, 1.00,
         "the wooden board is nailed to the steel gate post and stays flat on the post face",
         "do not take the board off the post and do not cover the written rule")],
    55: [("IX_5501", ["QuotaRoster", "CommitteeScreen"], 0.00, 1.00,
         "the blank signature space of the machine factory row stays empty while the cost column on the "
         "screen stops at the last entry",
         "do not fill the signature space and do not close the last cost entry")],
    56: [("IX_5601", ["CityDefenseMap", "HeirSeal"], 0.20, 1.00,
         "the heir seal is pressed beside the marked factory name while the pen tip holds on that name",
         "do not lift the seal and do not add any other mark on the map")],
    57: [("IX_5701", ["Yechengjun", "EntryRoster"], 0.35, 1.00,
         "the officer's fingertip presses on the last few names of the roster lying on the steel table",
         "do not make the names legible and do not raise the lighting")],
    58: [("IX_5801", ["OldCottonCoat", "StandardArmour"], 0.30, 0.85,
         "a corner of standard armour shows under the sleeve of one old cotton coat and is covered again",
         "do not push the armour corner into a close detail and do not place it outside the coat")],
    60: [("IX_6001", ["Yehongyi", "ShadowBlade"], 0.40, 1.00,
         "the shadow blade is drawn half out and pushed back into its sheath at the wall",
         "do not light the blade edge and do not leave the blade drawn")],
    63: [("IX_6301", ["SteelRack", "GapOpening", "Rescuee"], 0.00, 1.00,
         "two steel racks are carried across the fire line and the people pass one at a time through the gap",
         "do not close the gap and do not crowd more than one person through it")],
    64: [("IX_6401", ["Yehongyi", "ShadowBlade", "AssassinLeader", "DarkJunction"], 0.00, 1.00,
         "the shadow blade lies across the centre of the unlit junction between the fighter and the leader "
         "standing on the far side",
         "do not light the blade edge and do not bring the leader's face into view")],
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
    33: "welding arc hum with a spitting crackle and sparks ticking on the cement floor under distant hall air",
    34: "distant engine noise coming closer, tyres over broken brick and one iron door pushed open",
    35: "two dull knocks of knuckles on the back of a tablet with the engine noise fading outside the door",
    36: "a distant engine fading away with a light touch of steel rod against a steel rack",
    37: "urgent footsteps on cement with the electric hum of a cold white tube lamp",
    38: "a short ignition hiss of the twin flame with breathing held in the throat",
    39: "a fine hiss of smoke dispersing and a tablet hitting a rack foot and bouncing twice",
    40: "paper turning with a low machine hum turning over in the distance",
    41: "paper friction with the scratch of a pencil point",
    42: "steel racks dragging across the floor and a dull drop from the press slot",
    43: "a row of feet landing on the same beat, a notice chime and a lamp strip flickering",
    44: "a scrolling chime from the led board with street noise swelling in the distance",
    45: "a notice chime over distant loudspeaker hiss and relay clicks",
    46: "a distant broadcast hum with the even footfalls of the order squad",
    47: "a distant broadcast swelling while the murmur inside the hall drops to a low level",
    48: "the distant broadcast pausing for a beat with feet shifting inside the hall",
    49: "the rattle of a stall frame being set up with street noise around it",
    50: "dull placement of vapour cores, steel and reagent on the counter with the line shifting its feet",
    51: "a metal piece pressed onto a wooden counter with a fingertip rubbing over the engraved lines",
    52: "a led board scrolling several notices and the metal sound of the safe door closing",
    53: "scrolling entries on the led board with an empty rack rattling",
    54: "two hammer blows of a nail into a steel post with a gate hinge turning",
    55: "a screen page turning with paper being pushed across the table",
    56: "a dull pen tip touching paper with fabric shifting",
    57: "a faint steel table sound with a pen tip running across paper",
    58: "many mixed footsteps with old cotton cloth rubbing together",
    59: "the electronic buzz of the tablet with the hall noise falling away",
    60: "one soft click of the light switch and the clatter of steel rods and ammunition being issued",
    61: "a citywide notice chime with a distant burst as the first fire lights",
    62: "fire bursting open with metal impacts as the steel racks are lifted",
    63: "many running feet with the strain call of people lifting the racks and a beam breaking",
    64: "distant fire bursts with a light metallic slide of a blade drawn half and pushed back",
}

# ------------------------------------------------------------------ 全局风格合同
# 来自共享 D10 风格合同（冷峻工业末世写实底 + 克制的能量风格化）+ U02 场景扩展
STYLE_BIBLE = {
    "world_and_era": (
        "post-collapse industrial city ruins; a walled factory district turned into a survival compound "
        "and the bone market street running beside it; ration queues, pinned duty rosters and projected "
        "notices govern daily life; human survivors and ceramic-pale altered beings share the same cold "
        "daylight and fog; no readable signage and no modern branding"),
    "visual_language": (
        "grounded industrial realism for humans and props with a separated stylisation layer for the bone "
        "pattern, the black and white twin flame, white smoke, fire heads and projected interface text; "
        "stylised elements never spill across into the human layer and every body surface stays intact"),
    "palette": (
        "grey fog cyan-grey #4A5A5C as the global base, ink shadow #171B1D with detail kept in the darks, "
        "plaster white #C6C2B8 for ceramic shells, pure-fire white #F5F7F8 and black #0B0B0C for the twin "
        "colour bone pattern, weld and fire orange #E07B39 as the only warm accent, dark red #7A2027 "
        "reserved for the fighter's outfit and never for any liquid"),
    "material_language": (
        "real skin with pores and slight oil sheen, matte technical fabric with wear and dust, oxidised "
        "steel with dull reflections, cold ceramic shells on altered bodies; every surface stays intact "
        "and no red liquid appears anywhere in the frame"),
    "environment_design": (
        "cement yard plates cut by fire lines, riveted steel frames and steel racks, sheet metal and "
        "plyboard walls carrying pinned drawings and duty rosters, a single cold ceiling tube over the "
        "purification bench, market stall rows under a led board along a fog covered street, and one "
        "unlit stretch of road outside the factory gate"),
    "prop_design": (
        "functional utilitarian tooling with real weight and thickness: welding rigs, steel racks, extraction "
        "lines and press slots, frosted energy blocks, duty rosters, nailed wooden boards, written notices, "
        "sealed safes and an unlit shadow blade; all carry visible use marks"),
    "lighting_and_atmosphere": (
        "one cold overhead key over the purification bench with shadow detail retained instead of crushed "
        "black, cold grey bounce from concrete and steel, the welding arc, the twin flame and the fire heads "
        "as the only moving light sources, and the emergency lamp as the sole light after the yard lights "
        "are cut"),
}


# ------------------------------------------------------------------ primary 主体指定
# importance=primary 的 entity，其每个实例都会进入 anchor 的 D= 明细段（含
# o/m/r 文本），人群级 entity 会把 6500 预算撑爆。故 primary 一律取单实例
# entity；群体主体仍由 shots[].camera_contract.tracked_target_entity 表达。
PRIMARY_PICK = {
    42: "DefenseBlueprint",   # 萃取线为三段式主体；画面锚点取钉在墙上的单张图纸
    43: "DutyRoster",         # 两列岗哨为群体；画面锚点取墙上的单张轮班表
    46: "GateQueue",           # 排队人群为群体；画面锚点取队列本身
                                  # ⚠️ 原写 MainRollerDoor 有误：g46 机位在 Y=-18、看向 Y=-29
                                  #    的厂外道路，卷帘门（Y=0）在机位**背后**，不入画 ⇒ 锚点落空。
                                  #    已改为与 subject_core 一致的 GateQueue（队列在 Y=-30，正入画）。
    48: "Luchen",             # 围成半圈者为群体；画面锚点取抬头看货源路的陆沉
    58: "OldCottonCoat",      # 逃难人流为群体；画面锚点取露出护具一角的那件旧棉衣
    60: "Yehongyi",           # 围墙上多排影子为群体件；画面锚点取独自巡墙的叶红衣
    62: "MainRollerDoor",     # 三处火头为三实例特效；画面锚点取亮着的厂门
}
