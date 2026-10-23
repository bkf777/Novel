# W1–W8 实测结果（Q94 白模重建）

判据真源：`03_规格/rules.json → white_model_framing`；实现口径对齐 `04_工具/lib/rules.mjs` 的 V12。


## U01

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep01_shot01 | 中景 | 48.01% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-1_EXT_RentalRoom.003 100.0% EXT |
| ep01_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-1_EXT_Corridor 100.0% EXT |
| ep01_shot03 | 中景 | 53.61% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-1_EXT_RentalRoom.003 100.0% EXT |
| ep01_shot04 | 全景 | 100.0% | [5, 20] | OK | NG | NG | 0.0° OK | OK | A-1_PROP_RoomDoor_11 100.0% PROP |
| ep02_shot01 | 中远景 | 31.02% | [20, 40] | OK | OK | NG | 0.0° OK | OK | A-2_EXT_FactoryFrame_01 100.0% EXT |
| ep02_shot02 | 中景 | 47.87% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-2_EXT_FactoryHall.005 82.0% EXT |
| ep02_shot03 | 中远景 | 43.0% | [20, 40] | OK | NG | NG | 0.0° OK | OK | A-3_EXT_PipeRack_07 100.0% EXT |
| ep02_shot04 | 远景 | 35.67% | [8, 25] | OK | NG | OK | 0.0° OK | OK | A-3_CHAR_LuchenHand_02 35.7% CHAR |
| ep03_shot01 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | A-4_EXT_FactorySouthWall_01 100.0% EXT |
| ep03_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-4_LGT_GreyFramePanel_01 100.0% LGT |
| ep03_shot03 | 近景 | 57.88% | [55, 85] | OK | OK | NG | 0.0° OK | OK | A-4_FX_TwinFlame_01 88.2% FX |
| ep03_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-4_LGT_StreetLamp_06 100.0% LGT |
| ep04_shot01 | 中景 | 51.2% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-5_CHAR_Luchen_01 51.2% CHAR |
| ep04_shot02 | 特写 | 37.29% | [70, 95] | OK | NG | NG | 0.0° OK | OK | A-5_EXT_BattleGround_01 100.0% EXT |
| ep04_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-5_LGT_GreyFramePanel_01 91.4% LGT |
| ep04_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-5_EXT_FactoryEastWall_01 100.0% EXT |
| ep05_shot01 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | A-6_EXT_PipeRack_10 100.0% EXT |
| ep05_shot02 | 近景 | 96.98% | [55, 85] | OK | NG | NG | 0.0° OK | OK | A-6_EXT_SteelFenceWest_01 100.0% EXT |
| ep05_shot03 | 远景 | 8.15% | [8, 25] | OK | OK | NG | 0.0° OK | OK | A-6_EXT_InnerYard 18.3% EXT |
| ep05_shot04 | 近景 | 90.46% | [55, 85] | OK | NG | NG | 0.0° OK | OK | A-6_EXT_PipeRack_05 100.0% EXT |
| ep06_shot01 | 中景 | 93.69% | [35, 65] | OK | NG | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 93.7% CHAR |
| ep06_shot02 | 中景 | 60.09% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_GuardCaptain_02 60.1% CHAR |
| ep06_shot03 | 中景 | 48.58% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-7_PROP_Bulldozer_01 68.6% PROP |
| ep06_shot04 | 中景 | 57.78% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-7_EXT_InnerYard 100.0% EXT |
| ep07_shot01 | 中景 | 50.38% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Yehongyi_02 50.4% CHAR |
| ep07_shot02 | 近景 | 100.0% | [55, 85] | OK | NG | OK | 0.0° OK | OK | A-8_CHAR_Yehongyi_03 100.0% CHAR |
| ep07_shot03 | 近景 | 71.24% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Luchen_01 71.2% CHAR |
| ep07_shot04 | 中景 | 48.37% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-8_EXT_InnerYard 59.3% EXT |
| ep08_shot01 | 中景 | 55.5% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-9_EXT_SteelPlateFloor_01 58.7% EXT |
| ep08_shot02 | 中远景 | 30.99% | [20, 40] | OK | OK | NG | 0.0° OK | OK | A-9_PROP_TransverseSteelRack_01 39.0% PROP |
| ep08_shot03 | 远景 | 15.29% | [8, 25] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_Luchen_01 15.3% CHAR |
| ep08_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-9_LGT_RegionalRoadLamp_05 17.9% LGT |

**W1 24/32｜W2 16/24（另 8 镜角色未入画，W2 不判）｜W3 8/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep01_shot02', 'ep03_shot01', 'ep03_shot02', 'ep03_shot04', 'ep04_shot03', 'ep04_shot04', 'ep05_shot01', 'ep08_shot04']；W2 ['ep01_shot04', 'ep02_shot03', 'ep02_shot04', 'ep04_shot02', 'ep05_shot02', 'ep05_shot04', 'ep06_shot01', 'ep07_shot02']；W3 ['ep01_shot01', 'ep01_shot02', 'ep01_shot03', 'ep01_shot04', 'ep02_shot01', 'ep02_shot02', 'ep02_shot03', 'ep03_shot01', 'ep03_shot02', 'ep03_shot03', 'ep03_shot04', 'ep04_shot02', 'ep04_shot03', 'ep04_shot04', 'ep05_shot01', 'ep05_shot02', 'ep05_shot03', 'ep05_shot04', 'ep06_shot03', 'ep06_shot04', 'ep07_shot04', 'ep08_shot01', 'ep08_shot02', 'ep08_shot04']；W4 无；W5 无

## U02

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep09_shot01 | 中远景 | 30.31% | [20, 40] | OK | OK | NG | 0.0° OK | OK | B-1_EXT_FactorySouthFacade 100.0% EXT |
| ep09_shot02 | 中远景 | 28.36% | [20, 40] | OK | OK | NG | 0.0° OK | OK | B-1_EXT_FactorySouthFacade 100.0% EXT |
| ep09_shot03 | 近景 | 50.75% | [55, 85] | OK | NG | NG | 0.0° OK | OK | B-1_EXT_FactoryYardGround 55.3% EXT |
| ep09_shot04 | 中景 | 61.52% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-1_CHAR_Suqingci_01 61.5% CHAR |
| ep10_shot01 | 中景 | 53.79% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactoryHallShell 94.5% EXT |
| ep10_shot02 | 近景 | 84.36% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-2_CHAR_GreySpottedPatient_01 84.4% CHAR |
| ep10_shot03 | 近景 | 71.71% | [55, 85] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactorySouthFacade 100.0% EXT |
| ep10_shot04 | 近景 | 76.23% | [55, 85] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactoryHallShell 100.0% EXT |
| ep11_shot01 | 特写 | 64.18% | [70, 95] | OK | NG | NG | 0.0° OK | OK | B-3_PROP_SteelTable_01 90.3% PROP |
| ep11_shot02 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | B-3_EXT_FactoryHallShell.002 50.3% EXT |
| ep11_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-3_PROP_GuardPostMember_03 67.5% PROP |
| ep11_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-4_LGT_MarketLedBoard_01 98.7% LGT |
| ep12_shot01 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | B-5_EXT_OldSheetMetalWall_01 100.0% EXT |
| ep12_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-5_PROP_GateQueue_03 14.3% PROP |
| ep12_shot03 | 中景 | 61.09% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-5_PROP_MainRollerDoor_03 84.1% PROP |
| ep12_shot04 | 中景 | 47.0% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-5_EXT_OldSheetMetalWall_01 68.7% EXT |
| ep13_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-6_EXT_MarketStreetBackdrop.004 100.0% EXT |
| ep13_shot02 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | B-6_LGT_MarketLedBoard_01 62.5% LGT |
| ep13_shot03 | 特写 | 88.03% | [70, 95] | OK | OK | OK | 0.0° OK | OK | B-6_CHAR_Suqingci_01 88.0% CHAR |
| ep13_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-7_EXT_ReinforcedCloister_01 100.0% EXT |
| ep14_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-8_PROP_EmptyShelf_01 69.1% PROP |
| ep14_shot02 | 中景 | 31.91% | [35, 65] | OK | NG | NG | 0.0° OK | OK | B-8_PROP_SteelGatePost_01 100.0% PROP |
| ep14_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-8_EXT_FactoryHallShell 100.0% EXT |
| ep14_shot04 | 近景 | 0.0% | [55, 85] | NG | — | NG | 0.0° OK | OK | B-8_EXT_MeetingRoomShell.006 100.0% EXT |
| ep15_shot01 | 中景 | 53.2% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-9_EXT_CommandCockpitShell.005 100.0% EXT |
| ep15_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-9_PROP_RefugeeCrowdMember_02 44.5% PROP |
| ep15_shot03 | 特写 | 75.75% | [70, 95] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Suqingci_01 75.8% CHAR |
| ep15_shot04 | 中景 | 47.55% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-9_EXT_FactoryHallShell.002 63.0% EXT |
| ep16_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 98.7% EXT |
| ep16_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 66.4% EXT |
| ep16_shot03 | 中景 | 53.73% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-10_PROP_SteelRack_01.001 100.0% PROP |
| ep16_shot04 | 中景 | 52.22% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-10_PROP_DarkJunction_02 100.0% PROP |

**W1 18/32｜W2 15/18（另 14 镜角色未入画，W2 不判）｜W3 4/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep11_shot02', 'ep11_shot03', 'ep11_shot04', 'ep12_shot01', 'ep12_shot02', 'ep13_shot01', 'ep13_shot02', 'ep13_shot04', 'ep14_shot01', 'ep14_shot03', 'ep14_shot04', 'ep15_shot02', 'ep16_shot01', 'ep16_shot02']；W2 ['ep09_shot03', 'ep11_shot01', 'ep14_shot02']；W3 ['ep09_shot01', 'ep09_shot02', 'ep09_shot03', 'ep10_shot01', 'ep10_shot03', 'ep10_shot04', 'ep11_shot01', 'ep11_shot02', 'ep11_shot03', 'ep11_shot04', 'ep12_shot01', 'ep12_shot02', 'ep12_shot03', 'ep12_shot04', 'ep13_shot01', 'ep13_shot02', 'ep13_shot04', 'ep14_shot01', 'ep14_shot02', 'ep14_shot03', 'ep14_shot04', 'ep15_shot01', 'ep15_shot02', 'ep15_shot04', 'ep16_shot01', 'ep16_shot02', 'ep16_shot03', 'ep16_shot04']；W4 无；W5 无
