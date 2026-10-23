#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D14 逐镜 Render Contract / Appearance 填写器。

原则：
- source_inventory 不删不改（preflight 依 Blender structure_evidence 生成）。
- 每个描述字段只写一个可见事实，且用英文（技能要求）。
- 锚点的可见性/包围盒取 Blender 实测证据；朝向/运动状态/空间关系由实测轨迹与
  投影框推导，不臆测。
- 运动合同按白模实测位移/形变判定；实测无位移者一律 static（不得自行动画化）。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

# 注：本模块只提供**内容表**（语义/动作/交互/声音/风格）。
# 项目根与白模工作区一律由调用方（fill_D14_contracts.py）按 --project/--work 传入，
# 此处不写死任何绝对路径 —— 内容模块若自带路径，U02 复用时会静默指向 U01。

# ------------------------------------------------------------------ 实体语义
# core -> (entity_class, source_role, structural_constraints)
SEMANTIC = {
    # ---- 角色 ----
    "Luchen": ("articulated", "male protagonist blockout",
                "human height 1.80m; silhouette and joint envelope fixed by source blockout"),
    "LuchenHand": ("articulated", "protagonist raised hand blockout",
                   "0.30m hand volume; stays attached to protagonist forearm"),
    "Yechengjun": ("articulated", "male officer antagonist blockout",
                   "human height 1.81m; pinned to steel plate after impact"),
    "Yehongyi": ("articulated", "female captive character blockout",
                 "human height 1.70m; wrist restraint position fixed"),
    "GuardCaptain": ("articulated", "guard captain blockout",
                     "human height 1.80m; kneels after impact, armour stays on body"),
    "EscortQueueMember": ("articulated", "escort officer marching in column",
                          "0.60x0.60x1.75m body; column spacing and order preserved"),
    "RescuedQueueMember": ("articulated", "rescued captive standing in column",
                            "0.60x0.60x1.75m body; no facial detail readable at this scale"),
    "DarkRedOutfit": ("rigid", "dark red tactical outfit blockout",
                      "worn on kneeling female captive; colour reads dark under cold light"),
    "LongStraightHair": ("rigid", "long straight hair blockout",
                         "hangs behind shoulders; length below shoulder line"),
    # ---- 建筑与场地 ----
    "RentalRoom": ("environment", "rental room shell with walls floor ceiling",
                   "net 4.20x3.60x2.60m; encloses every A-1 interior element"),
    "Corridor": ("environment", "stairwell corridor shell",
                 "2.40m wide x 6.20m long x 2.50m high; encloses stair approach"),
    "StairFlight": ("environment", "stair flight shell with eleven treads",
                    "rises to +1.87m; treads 0.28m deep 0.17m rise"),
    "FactoryFrame": ("environment", "factory structural frame shell",
                     "26x18m footprint, 12.00m clear height; carries roof and walls"),
    "FactoryHall": ("environment", "factory hall floor and enclosure",
                    "26x18m footprint, 12.00m clear height"),
    "InnerYard": ("environment", "inner yard ground plate",
                  "36x28m ground plate; carries pit and disposal platform"),
    "OuterGravelGround": ("environment", "outer gravel ground band",
                          "6x22m gravel band outside the wire fence"),
    "RoadShoulder": ("environment", "regional road shoulder band",
                     "6x20m shoulder band at yard edge"),
    "PipeRack": ("environment", "elevated pipe rack structure",
                 "raised +3.50m, 1.20m wide, four parallel pipes"),
    "SteelFenceWest": ("environment", "west steel fence run",
                       "at X=+24.00m; gap left for west gate at Y+4..+10"),
    "SteelFenceNorth": ("environment", "north steel fence run",
                        "at Y=+14.00m; carries north gate opening"),
    "WestGatePost": ("environment", "west gate post",
                     "0.40x0.40x4.20m post flanking the west gate opening"),
    "NorthGatePost": ("environment", "north gate post",
                      "0.40x0.40x4.20m post flanking the north gate opening"),
    "RoadAndGravelStrip": ("environment", "road and gravel strip ground",
                            "12x22m strip along the yard edge"),
    "FactoryGround": ("environment", "factory yard ground plate",
                      "32x24m cement plate; carries fissure and break hole"),
    "FactorySouthWall": ("environment", "factory south facade wall",
                         "26m wide x 12m high; carries catwalk above"),
    "BattleGround": ("environment", "battle zone ground plate",
                     "20x20m ground shared with factory yard plane"),
    "FactoryEastWall": ("environment", "factory east facade wall",
                        "18m long x 12m high; carries two high window openings"),
    "ServiceRoad": ("environment", "service road band outside factory",
                    "6x30m road band behind the east facade"),
    "EastHighWindow": ("environment", "east facade high window opening",
                       "1.60x2.40m opening cut into the east wall"),
    "SteelPlateFloor": ("environment", "steel plate floor of the queue yard",
                        "10x6m plate; kneeling point at its centre"),
    "SteelPlateWall": ("environment", "steel plate wall behind the column",
                       "22m long x 2.40m high; column backs onto it"),
    "RegionalRoad": ("environment", "regional road north of the gate",
                     "60x6m road band 59.60m beyond the north gate"),
    # ---- 道具 ----
    "Bed": ("rigid", "single bed frame",
            "1.00x2.00x0.45m; protagonist sits and rises on it"),
    "UnderBedBox": ("rigid", "storage box under the bed",
                    "0.70x0.50x0.35m; lid opens and ration crates return inside"),
    "RationCrate": ("rigid", "ration crate stack",
                    "0.40x0.30x0.25m each; four crates stacked, count preserved"),
    "Wardrobe": ("rigid", "wardrobe against the east wall",
                 "1.00x0.60x2.00m; door faces into the room"),
    "CardboardColumn": ("rigid", "stacked cardboard column",
                        "0.80x0.80x2.50m; stands beside the bed"),
    "Toolbox": ("rigid", "open toolbox",
                "0.50x0.30x0.25m; holds one wrench and one tape roll"),
    "Wrench": ("rigid", "single wrench inside the toolbox",
               "0.32m long; lies inside the open toolbox"),
    "TapeRoll": ("rigid", "half roll of tape",
                 "0.12m diameter; lies inside the open toolbox"),
    "SteelCrowbar": ("rigid", "modified heavy steel crowbar",
                     "1.20-1.50m long bar; carried by hand, never dropped"),
    "Crowbar": ("rigid", "crowbar used to pry the roller door",
                "1.50m long bar; pries the main roller door open"),
    "Window": ("rigid", "window opening in the east wall",
               "1.20x1.40m opening; night city visible through it"),
    "RoomDoor": ("rigid", "room door leaf swung inward",
                 "0.90x2.05m leaf; opens into the room and stays open"),
    "StairRail": ("rigid", "slanted stair handrail",
                  "runs along the stair flight, 0.79m above treads"),
    "StairwellWindow": ("rigid", "stairwell high window",
                        "1.20x1.20m opening at stair landing level"),
    "CeilingTubeLight": ("rigid", "cold white ceiling tube light",
                         "1.20m tube; only light source in the rental room"),
    "CorridorSensorLight": ("rigid", "corridor sensor lamp",
                             "0.16x0.10x0.20m; lights the stairwell floor"),
    "GreyFramePanel": ("rigid", "floating grey frame interface panel",
                       "non solid overlay; never casts shadow or blocks set"),
    "MainRollerDoor": ("rigid", "main roller door of the factory",
                       "4.00m wide; lifted to 2.60m clear passage"),
    "SideRollerDoor": ("rigid", "side roller door of the factory",
                       "3.00m wide x 3.50m high; protagonist enters here"),
    "WeldedGate": ("rigid", "welded barrier gate inside side door",
                   "3.00x0.12x2.20m; welded seam leaves warm spark mark"),
    "WestHighWindow": ("rigid", "west facade high window",
                       "1.60x2.40m opening; cold sky light enters"),
    "SteelRack": ("rigid", "steel rack row",
                  "4.00x0.60x2.20m each; four racks in a row"),
    "StackedSteelRack": ("rigid", "stacked steel rack under window",
                         "4.00x0.60x2.20m each; two racks stacked"),
    "HalfRationBox": ("rigid", "half filled ration box",
                      "0.50x0.35x0.30m; pressed onto the toolbox lid"),
    "Bulldozer": ("rigid", "bulldozer parked in the yard",
                  "3.80x2.40x2.70m; steel plate on its flank is the pinning face"),
    "Wristwatch": ("rigid", "wristwatch on the protagonist wrist",
                   "0.045m dial; face lights up against the night"),
    "DeepPit": ("environment", "deep pit cut into the yard ground",
                "4.40x3.00m opening, 2.20m deep; character stands inside"),
    "GroundBreakHole": ("environment", "circular break hole in concrete",
                        "0.50m diameter opening; tentacle emerges from it"),
    "GroundFissure": ("environment", "diagonal fissure band in the yard",
                      "18.30m long x 0.30m wide crack across the ground"),
    "ArmouredVehicle": ("rigid", "armoured vehicle body line",
                        "6.80x2.60x2.90m each; four vehicles parked in row"),
    "ApprovalConsole": ("rigid", "approval console table",
                        "2.40x0.80x1.05m; antagonist leans on its edge"),
    "ApprovalTerminal": ("rigid", "approval terminal screen unit",
                         "1.00x0.20x0.70m screen with one red reject key"),
    "DisposalPlatform": ("environment", "disposal platform deck",
                         "6.00x3.00x0.30m deck beside the pit"),
    "PitLadder": ("environment", "inspection ladder in the pit wall niche",
                  "rises from pit floor to rim, 1.90m niche in the wall"),
    "ShadowBlade": ("rigid", "shadow blade carried by the captive",
                   "0.05x0.05x0.90m blade; reversed into the ground, no edge glow"),
    "WristRestraint": ("rigid", "wrist restraint cuff on the captive",
                       "0.075m cuff; buckle opens and the hand pulls free"),
    "TransverseSteelRack": ("environment", "transverse steel rack at the yard",
                            "4.00x1.50x2.20m; protagonist stands on its top"),
    "DistantArmourColumn": ("effect", "distant armour column light spots",
                             "four light spots only; vehicle bodies stay unseen"),
    "RecoverySignboard": ("rigid", "waste core recovery direction sign",
                          "2.40x1.40m screen on a 6.00m post at the yard edge"),
    "StreetLamp": ("rigid", "street lamp over the yard",
                   "8.00m pole with lamp head; reads as a diffuse glow disc"),
    "RoadsideLamp": ("rigid", "roadside lamp along the service road",
                     "8.00m pole at the road shoulder"),
    "RegionalRoadLamp": ("rigid", "distant roadside lamp on the regional road",
                         "8.00m pole 59m beyond the north gate"),
    # ---- 特效 ----
    "ChitinTentacle": ("effect", "chitin tentacle of the burrow insect",
                       "segmented limb, 0.24m diameter tapering to 0.08m"),
    "ConcreteDebris": ("effect", "concrete debris chunks",
                       "0.12m chips; ejected upward then settle"),
    "TwinFlame": ("effect", "black and white twin flame on the wrist",
                  "0.18x0.05x0.30m; clings to skin, no body glow"),
    "TwinGreyVapour": ("effect", "twin grey-blue vapour mass over the fissure",
                       "two flat low volumes along the fissure band; spreads flat and pushes outward"),
    "DisposalLightRing": ("rigid", "white lamp ring on the disposal platform rim",
                          "eight lamps on a 3.00m radius at +0.50m; the only grouped light source in frame"),
    "DisposalSilhouette": ("articulated", "processed person silhouette on the platform",
                           "0.60x0.60x1.75m standing blockout; no face or skin detail, rim lit only"),
    "WristBoneMark": ("effect", "black and white bone pattern on the wrist",
                      "0.075m marking; lies flat on skin surface only"),
    "AshDust": ("effect", "grey ash dust cloud",
                 "sparse particles within 1.80m radius, no solid occlusion"),
    "MistCore": ("effect", "cold white mist core grain",
                 "0.12m grain; sinks into the palm and vanishes"),
    "LooseGravel": ("effect", "loose gravel on the factory floor",
                    "0.08m stones; draggable underfoot"),
    "AshPatch": ("effect", "grey white patch on the captive forearm",
                 "0.12x0.10m patch; expands along the forearm"),
    "WhiteSmoke": ("effect", "white smoke rising off the forearm",
                   "0.05m puffs within 0.25m radius, dissipates upward"),
}

# ------------------------------------------------------------------ 镜头数据
# gsn -> (motion_type, subject_core, actions_en, forbidden_reinterpretations)
SHOT_DATA = {
    1: ("dolly", "Luchen",
        "protagonist wakes prone on the bed, presses the mattress and sits up; "
        "grey frame panel brightens column by column at frame centre",
        "do not turn the push into an orbit or a zoom; keep the bed below frame centre"),
    2: ("dolly", "GreyFramePanel",
        "grey frame panel fills the frame, corner tick marks stay fixed, bottom ticker scrolls upward",
        "do not pull the camera back to reveal the room; panel stays frame filling"),
    3: ("dolly", "Luchen",
        "protagonist crouches, opens the under-bed lid, pushes ration crates back into the wardrobe, "
        "lifts the toolbox and lays a crowbar on it, then stands up unsteadily",
        "do not re-stage the crouch as a running move; the camera keeps a single lateral slide"),
    4: ("tracking", "Luchen",
        "room door leaf swings open, protagonist rushes out into the corridor, "
        "corridor lamps light one by one, figure climbs the stairs and recedes to the landing",
        "do not keep the protagonist large; the wide framing must end with a receding figure"),
    5: ("static", "Luchen",
        "protagonist squeezes sideways through the pried roller door gap, hauls steel racks and cable "
        "reels across the floor, then cranks the well winch and stacks two water drums at the wall base",
        "do not let the camera follow; the fixed wide frame must keep the whole hall visible"),
    6: ("static", "Luchen",
        "protagonist carries a steel rack sideways and stacks it under the window, "
        "then presses a half ration box onto the toolbox lid and closes it",
        "do not add a dolly; keep the welding spark at the contact point as the only warm accent"),
    7: ("tracking", "Luchen",
        "protagonist walks along the fence line once, pauses at the pipe rack and the gate "
        "to note the position, gravel kicked up by the boots",
        "do not reveal the pit interior; the camera stays outside the fence"),
    8: ("static", "Wristwatch",
        "protagonist raises the wrist, the watch dial lights against the night, "
        "distant clock tower silhouette stands against the cold sky",
        "do not zoom toward the tower; it stays a small distant silhouette"),
    9: ("static", "TwinGreyVapour",
        "twin grey vapour rises out of the ground fissure and spreads flat across the yard, "
        "street lamps reduce to diffuse glow discs, vapour keeps pushing outward",
        "do not move the camera; the ground geometry itself carries the change"),
    10: ("static", "GreyFramePanel",
         "grey frame panel holds frame centre, bottom ticker scrolls, four numeric readouts appear one after another",
         "do not reveal the yard behind the panel"),
    11: ("static", "LuchenHand",
         "first black and white bone line creeps from wrist toward the back of the hand, "
         "twin flame ignites at the wrist, raised wrist tilts and the flame leans sideways",
         "do not turn this into a hand close-up beyond the source framing"),
    12: ("crane", "ChitinTentacle",
         "cement ground cracks open, one chitin tentacle pushes up out of the gap and debris jumps, "
         "the camera descends and finally settles on the crack edge",
         "do not keep the high angle; the crane must end low on the fissure edge"),
    13: ("tracking", "Luchen",
         "tentacle whips out of the break hole and drags gravel, cutting a long gouge, "
         "protagonist sidesteps clear and grips the crowbar",
         "do not swap the sidestep for a charge forward"),
    14: ("handheld", "SteelCrowbar",
         "crowbar bar crosses the tentacle limb, first contact throws sparks, "
         "second contact breaks the tip off, third contact drops the limb whole",
         "do not add any wound detail; only the contact point is shown"),
    15: ("static", "MistCore",
         "insect body breaks into grey ash dust, the dust hangs and settles, "
         "one mist core lifts out of the ash and sinks into the open palm",
         "do not let the camera move; the ash cloud carries the change"),
    16: ("static", "GreyFramePanel",
         "panel bottom rolls out a kill notification bar with the protagonist name on top, "
         "vehicle headlamps sweep in through the factory window and cross the frame",
         "do not turn the passing headlamps into visible vehicle bodies"),
    17: ("static", "EscortQueueMember",
         "armour column headlamps sweep the steel fence, escorts march a column in through the west gate, "
         "the last few captives hold stiff arms under grey white patches",
         "do not cut to any single face; the column must stay a group"),
    18: ("static", "ApprovalTerminal",
         "over the shoulder of the officer toward the approval terminal, one red reject key lit, "
         "a column of numbers on the screen with the last line pressed by the red key",
         "do not show the officer face frontally; keep the over the shoulder framing"),
    19: ("static", "DisposalLightRing",
         "the disposal platform far in frame lights a ring of white lamps, "
         "only silhouettes of the processed remain, rim light edges them",
         "do not reveal any face or body surface; the platform ring is the only change"),
    20: ("static", "Yechengjun",
         "profile of the officer at the terminal, collar buttoned, one eye silver single lens catching cold light, "
         "a hand in the dark grips the crowbar and tightens",
         "do not widen the frame; the officer face stays the only subject"),
    21: ("handheld", "Luchen",
         "a silhouette in the dark plant bursts out and charges, tactical coat hem swinging, "
         "the crowbar drags a spark line across the concrete",
         "do not push the camera onto the face; handheld must stay off the subject"),
    22: ("handheld", "GuardCaptain",
         "one strike knocks the guard captain back half a metre, he slides and drops to one knee, "
         "the crowbar is swept out of hand and bounces on the concrete",
         "do not show injury detail; no wound and no red"),
    23: ("static", "SteelCrowbar",
         "protagonist lunges half a step, swings the crowbar sideways and pins the officer to the "
         "steel plate on the bulldozer flank, approval terminal red key flashes",
         "do not let the bar pass through the body; it stops at the plate"),
    24: ("crane", "WristRestraint",
         "crowbar strikes the cuff buckle on the captive wrist, the buckle pops, her hand pulls free, "
         "protagonist flips off the platform into the pit and lands on one hand",
         "do not keep the high camera; the crane must descend with the fall"),
    25: ("tracking", "Luchen",
         "protagonist lands at the pit floor and walks along the platform side wall to the captive, "
         "she raises her head and props herself up on one hand",
         "do not cut to a close-up; keep both figures in the mid frame"),
    26: ("static", "LuchenHand",
         "protagonist presses the right wrist close to her forearm, twin flame touches the skin, "
         "white smoke rises along the arm and clears, the skin underneath stays intact",
         "do not add any wound or red liquid; the surface must stay unbroken"),
    27: ("static", "WristBoneMark",
         "ordered embers in the smoke flow back into the protagonist wrist, the bone pattern bar "
         "advances one step, the black and white pattern brightens and extends half an inch up the forearm",
         "do not widen beyond the wrist close-up framing"),
    28: ("static", "Yehongyi",
         "the captive forearm returns to normal skin tone, she grips the shadow blade and stands up, "
         "moves half a step behind the protagonist, the blade stays unlit at her side",
         "do not let the blade emit any edge glow"),
    29: ("static", "Yehongyi",
         "the captive kneels on one knee on the steel plate, dark red outfit reads dark under cold light, "
         "the shadow blade is reversed into the ground with no edge glow",
         "do not add any motion; the kneeling pose must stay fixed"),
    30: ("crane", "Luchen",
         "protagonist steps onto the transverse steel rack and stands high, coat hem lifted by airflow, "
         "the column below tilts heads up but no face enters frame",
         "do not end on the column; the crane must rise to the standing figure"),
    31: ("static", "RescuedQueueMember",
         "rescued captives stand in a column along the steel plate wall receding into depth, "
         "the last one pulls a sleeve over the wrist, the protagonist lifts the right wrist "
         "and the bone pattern flares once",
        "do not render any face; the column must stay unreadable at this scale"),
    32: ("static", "DistantArmourColumn",
         "a row of moving headlamp spots travels along the far regional road, vehicle bodies never resolve, "
         "a panel pops up in view with a distress signal bar pointing west",
         "do not bring the vehicles into the frame; only light spots are allowed"),
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
    3: [("IX_0301", ["Luchen", "SteelCrowbar", "Toolbox"], 0.30, 0.75,
         "protagonist hand grips crowbar resting on the open toolbox",
         "do not separate the crowbar from the hand or add new held items")],
    8: [("IX_0801", ["Luchen", "Wristwatch"], 0.10, 1.00,
         "watch dial stays mounted on the raised wrist",
         "do not detach the watch or place it on the ground")],
    11: [("IX_1101", ["Luchen", "WristBoneMark", "TwinFlame"], 0.00, 1.00,
         "bone pattern and twin flame stay bound to the right wrist skin",
         "do not move the pattern off the wrist or add flame to the body")],
    13: [("IX_1301", ["Luchen", "SteelCrowbar"], 0.45, 1.00,
         "crowbar held in the protagonist hand during the sidestep",
         "do not drop the crowbar or move it to another hand")],
    14: [("IX_1401", ["SteelCrowbar", "ChitinTentacle"], 0.00, 1.00,
         "crowbar bar crosses the tentacle limb at one contact point",
         "do not show wound detail or extra contact points")],
    15: [("IX_1501", ["MistCore", "Luchen"], 0.35, 1.00,
         "mist core lifts from the ash and sinks into the open palm",
         "do not leave the core floating or add extra cores")],
    20: [("IX_2001", ["LuchenHand", "SteelCrowbar"], 0.00, 1.00,
         "hand in shadow holds the crowbar shaft",
         "do not release the grip or add a second hand")],
    22: [("IX_2201", ["GuardCaptain", "SteelCrowbar"], 0.00, 0.45,
         "crowbar swept out of the captain's hand and bounced on the concrete",
         "do not keep the crowbar in the hand after the sweep")],
    23: [("IX_2301", ["SteelCrowbar", "Yechengjun", "Bulldozer"], 0.30, 1.00,
         "crowbar pinned through the steel plate holding the officer beside it",
         "do not let the bar pass through the body or move the officer")],
    24: [("IX_2401", ["Luchen", "WristRestraint", "Yehongyi"], 0.00, 0.55,
         "crowbar strikes the cuff buckle until the captive hand pulls free",
         "do not keep the cuff closed or add injury detail")],
    25: [("IX_2501", ["Luchen", "Yehongyi"], 0.00, 1.00,
         "protagonist walks up to the kneeling captive at the pit floor",
         "do not move the captive out of the pit or swap their positions")],
    26: [("IX_2601", ["Luchen", "Yehongyi", "TwinFlame"], 0.00, 1.00,
         "protagonist wrist held against the captive forearm surface",
         "do not break the skin surface or add red liquid")],
    27: [("IX_2701", ["Luchen", "WristBoneMark"], 0.00, 1.00,
         "ordered embers flow back into the wrist bone pattern",
         "do not detach the pattern from the wrist")],
    28: [("IX_2801", ["Yehongyi", "ShadowBlade"], 0.00, 1.00,
         "shadow blade gripped in the captive hand with no edge glow",
         "do not add blade glow or extra blades")],
    29: [("IX_2901", ["Yehongyi", "ShadowBlade"], 0.00, 1.00,
         "shadow blade reversed into the steel plate ground",
         "do not lift the blade or light its edge")],
    30: [("IX_3001", ["Luchen", "TransverseSteelRack"], 0.00, 0.60,
         "protagonist feet stand on the transverse steel rack top",
         "do not place the protagonist back on the ground")],
    31: [("IX_3101", ["Luchen", "WristBoneMark", "TwinFlame"], 0.50, 1.00,
         "bone pattern flares once on the raised wrist",
         "do not move the flare to another body part")],
}


def core_name(root: str) -> str:
    m = re.match(r"^A-\d+_(?:CHAR|PROP|EXT|FX|LGT)_(.+?)(?:[._]\d+)?$", root)
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
    1: "current switch-on click with a continuous low frequency hum underneath",
    2: "low frequency hum continues with one short panel refresh beep",
    3: "dull cardboard drag against a wooden cabinet, then a metal toolbox latch closing",
    4: "door hinge creak, then footsteps on the stair running from near to far",
    5: "metal scraping friction with distant wind",
    6: "short welding arc burst and steel dragging over concrete",
    7: "fine crunch of gravel under boots with distant machine rumble",
    8: "eleven bell strikes with the tail echoing across the open ground",
    9: "low rumble with the hissing rush of spreading vapour",
    10: "two short panel beeps over a continuing low rumble",
    11: "low breath of the twin flame igniting and thin night wind over the bone pattern",
    12: "dull cement fracture with debris bouncing on concrete",
    13: "hard whipping impact with gravel rolling away",
    14: "three short metal impacts plus the fine hiss of scattered sparks",
    15: "fine hiss of ash dispersing and one low resonance as the mist core sinks in",
    16: "one short notification beep with distant engine rumble approaching",
    17: "diesel engine growl with an iron gate sliding on its rail",
    18: "short electronic confirm from the terminal over a continuing diesel growl",
    19: "white lamp hum and low mechanical operation under the line reading",
    20: "metal squeak of a tightened crowbar grip with one low heartbeat",
    21: "metal dragging on concrete and footsteps closing in",
    22: "dull armour impact then a sharp metal bounce of the dropped crowbar",
    23: "burst of the bar striking steel with terminal alarm buzzing",
    24: "sharp click of the buckle popping open then a dull landing thud",
    25: "fine crunch of footfalls on debris over distant machine rumble",
    26: "low breath of the twin flame with a thin airflow of rising white smoke",
    27: "dense hum of embers flowing back and one low pulse as the bone pattern brightens",
    28: "soft metal click of the blade entering the hand and a settled footstep",
    29: "short metallic sound of the blade entering the steel plate",
    30: "dull metallic thud of a boot on the steel rack with a light rack sway",
    31: "one footstep after another on steel plate and one low pulse as the bone pattern lights",
    32: "armour engine sound approaching from far away with one short panel beep",
}

# ------------------------------------------------------------------ 全局风格合同
# 来自共享 D10 风格合同（冷峻工业末世写实底 + 克制的能量风格化）
STYLE_BIBLE = {
    "world_and_era": (
        "post-collapse industrial city ruins; concrete yards, sheet metal fences, disused "
        "military machine shops and a walled disposal line; human survivors and ceramic-pale "
        "altered beings share the same night; no readable signage and no modern branding"),
    "visual_language": (
        "grounded industrial realism for humans and props with a separated stylisation layer for "
        "bone pattern, twin flame, grey fog and altered bodies; stylised elements never bleed into "
        "the human layer and no graphic injury detail anywhere"),
    "palette": (
        "grey fog cyan-grey #4A5A5C as the global base, ink shadow #171B1D with detail kept in "
        "the darks, plaster white #C6C2B8 for ceramic shells, pure-fire white #F5F7F8 and black "
        "#0B0B0C for the twin colour bone pattern, ember orange #E07B39 as the only warm accent"),
    "material_language": (
        "real skin with pores and slight oil sheen, matte technical fabric with wear and dust, "
        "oxidised steel with dull reflections, cold ceramic shells on altered bodies; no wet "
        "gore surface and no red liquid in the whole frame"),
    "environment_design": (
        "cement yard plates cut by fissures and pit openings, riveted steel frames, sheet metal "
        "fence runs with gate gaps, overhead pipe racks, stairwells and a single cold ceiling tube "
        "as the only interior light"),
    "prop_design": (
        "functional utilitarian tooling with real weight and thickness: crowbars, ration crates, "
        "steel racks, cable reels, console terminals, rolled roller doors, restraint cuffs and "
        "an unlit shadow blade; all carry visible use marks"),
    "lighting_and_atmosphere": (
        "one cold overhead key with shadow detail retained instead of crushed black, cold grey "
        "bounce from concrete and steel, the black and white twin flame as the only moving light "
        "source, and industrial weld sparks as the only warm light in the frame"),
}


# ------------------------------------------------------------------ primary 主体指定
# importance=primary 的 entity，其每个实例都会进入 anchor 的 D= 明细段（含
# o/m/r 文本），人群级 entity 会把 6500 预算撑爆。故 primary 一律取单实例
# entity；群体主体仍由 shots[].camera_contract.tracked_target_entity 表达。
PRIMARY_PICK = {
    17: "Bulldozer",      # 队列为 11 人群体；画面锚点取推土机深色轮廓
    31: "Luchen",        # 队列为 20 人群体；画面锚点取抬腕的陆沉
}
