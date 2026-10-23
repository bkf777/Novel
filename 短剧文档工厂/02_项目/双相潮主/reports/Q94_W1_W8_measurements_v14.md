# W1–W8 实测结果（Q94 白模重建）

判据真源：`03_规格/rules.json → white_model_framing`；实现口径对齐 `04_工具/lib/rules.mjs` 的 V12。


## U01

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep01_shot01 | 中景 | 38.08% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-1_PROP_CardboardColumn_01 60.0% PROP |
| ep01_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-1_EXT_Corridor 100.0% EXT |
| ep01_shot03 | 中景 | 40.38% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-1_PROP_CardboardColumn_01 71.3% PROP |
| ep01_shot04 | 全景 | 12.5% | [5, 20] | OK | OK | NG | 0.0° OK | OK | A-1_PROP_CardboardColumn_01 31.9% PROP |
| ep02_shot01 | 中远景 | 26.39% | [20, 40] | OK | OK | NG | 0.0° OK | OK | A-2_EXT_FactoryHall.003 40.2% EXT |
| ep02_shot02 | 中景 | 55.66% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-2_PROP_SideRollerDoor_01 77.3% PROP |
| ep02_shot03 | 中远景 | 30.01% | [20, 40] | OK | OK | NG | 0.0° OK | OK | A-3_EXT_InnerYard 84.8% EXT |
| ep02_shot04 | 远景 | 18.18% | [8, 25] | OK | OK | OK | 0.0° OK | OK | A-3_CHAR_Luchen_01 18.2% CHAR |
| ep03_shot01 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | A-4_EXT_FactorySouthWall_01 100.0% EXT |
| ep03_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-4_LGT_GreyFramePanel_01 100.0% LGT |
| ep03_shot03 | 近景 | 61.53% | [55, 85] | OK | OK | NG | 0.0° OK | OK | A-4_EXT_FactoryGround_01 100.0% EXT |
| ep03_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-4_LGT_StreetLamp_06 100.0% LGT |
| ep04_shot01 | 中景 | 43.32% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-5_CHAR_Luchen_01 43.3% CHAR |
| ep04_shot02 | 特写 | 33.26% | [70, 95] | OK | NG | NG | 0.0° OK | OK | A-5_EXT_BattleGround_01 100.0% EXT |
| ep04_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-5_LGT_GreyFramePanel_01 91.4% LGT |
| ep04_shot04 | 中景 | 41.41% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-5_LGT_RoadsideLamp_09 63.2% LGT |
| ep05_shot01 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | A-6_EXT_PipeRack_10 100.0% EXT |
| ep05_shot02 | 近景 | 97.06% | [55, 85] | OK | NG | OK | 0.0° OK | OK | A-6_CHAR_Yechengjun_01 97.1% CHAR |
| ep05_shot03 | 远景 | 8.15% | [8, 25] | OK | OK | NG | 0.0° OK | OK | A-6_EXT_InnerYard 18.3% EXT |
| ep05_shot04 | 近景 | 56.83% | [55, 85] | OK | OK | NG | 0.0° OK | OK | A-6_PROP_Bulldozer_01 100.0% PROP |
| ep06_shot01 | 中景 | 64.41% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 64.4% CHAR |
| ep06_shot02 | 中景 | 42.38% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 42.4% CHAR |
| ep06_shot03 | 中景 | 43.53% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-7_PROP_Bulldozer_01 57.8% PROP |
| ep06_shot04 | 中景 | 48.34% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-7_EXT_InnerYard 100.0% EXT |
| ep07_shot01 | 中景 | 58.29% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Luchen_01 58.3% CHAR |
| ep07_shot02 | 近景 | 100.0% | [55, 85] | OK | NG | OK | 0.0° OK | OK | A-8_CHAR_Yehongyi_03 100.0% CHAR |
| ep07_shot03 | 近景 | 70.05% | [55, 85] | OK | OK | NG | 0.0° OK | OK | A-8_EXT_InnerYard 100.0% EXT |
| ep07_shot04 | 中景 | 47.24% | [35, 65] | OK | OK | NG | 0.0° OK | OK | A-8_EXT_InnerYard 51.4% EXT |
| ep08_shot01 | 中景 | 48.89% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_Yehongyi_01 48.9% CHAR |
| ep08_shot02 | 中远景 | 42.24% | [20, 40] | OK | NG | NG | 0.0° OK | OK | A-9_PROP_TransverseSteelRack_01 63.7% PROP |
| ep08_shot03 | 远景 | 16.51% | [8, 25] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_Luchen_01 16.5% CHAR |
| ep08_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-9_LGT_RegionalRoadLamp_05 17.9% LGT |

**W1 25/32｜W2 21/25（另 7 镜角色未入画，W2 不判）｜W3 9/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep01_shot02', 'ep03_shot01', 'ep03_shot02', 'ep03_shot04', 'ep04_shot03', 'ep05_shot01', 'ep08_shot04']；W2 ['ep04_shot02', 'ep05_shot02', 'ep07_shot02', 'ep08_shot02']；W3 ['ep01_shot01', 'ep01_shot02', 'ep01_shot03', 'ep01_shot04', 'ep02_shot01', 'ep02_shot02', 'ep02_shot03', 'ep03_shot01', 'ep03_shot02', 'ep03_shot03', 'ep03_shot04', 'ep04_shot02', 'ep04_shot03', 'ep04_shot04', 'ep05_shot01', 'ep05_shot03', 'ep05_shot04', 'ep06_shot03', 'ep06_shot04', 'ep07_shot03', 'ep07_shot04', 'ep08_shot02', 'ep08_shot04']；W4 无；W5 无

## U02

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep09_shot01 | 中远景 | 30.0% | [20, 40] | OK | OK | NG | 0.0° OK | OK | B-1_PROP_MainRollerDoor_01 100.0% PROP |
| ep09_shot02 | 中远景 | 30.0% | [20, 40] | OK | OK | NG | 0.0° OK | OK | B-1_PROP_SideDoor_01 70.2% PROP |
| ep09_shot03 | 近景 | 20.78% | [55, 85] | OK | NG | NG | 0.0° OK | OK | B-1_EXT_FactoryYardGround 43.7% EXT |
| ep09_shot04 | 中景 | 39.46% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-1_PROP_MainRollerDoor_01 51.7% PROP |
| ep10_shot01 | 中景 | 46.98% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactoryYardGround 55.9% EXT |
| ep10_shot02 | 近景 | 51.45% | [55, 85] | OK | NG | NG | 0.0° OK | OK | B-2_EXT_FactoryHallShell 74.0% EXT |
| ep10_shot03 | 近景 | 64.92% | [55, 85] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactorySouthFacade 84.0% EXT |
| ep10_shot04 | 近景 | 64.4% | [55, 85] | OK | OK | NG | 0.0° OK | OK | B-2_EXT_FactoryYardGround 84.7% EXT |
| ep11_shot01 | 特写 | 45.06% | [70, 95] | OK | NG | NG | 0.0° OK | OK | B-3_PROP_SteelTable_01 90.1% PROP |
| ep11_shot02 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | B-3_EXT_FactoryHallShell.002 50.3% EXT |
| ep11_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-3_PROP_GuardPostMember_03 67.5% PROP |
| ep11_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-4_LGT_MarketLedBoard_01 98.7% LGT |
| ep12_shot01 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | B-5_EXT_OldSheetMetalWall_01 100.0% EXT |
| ep12_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-5_PROP_GateQueue_03 14.3% PROP |
| ep12_shot03 | 中景 | 39.66% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-5_PROP_MainRollerDoor_03 100.0% PROP |
| ep12_shot04 | 中景 | 45.04% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-5_LGT_CitywideNoticeProjection_01 53.0% LGT |
| ep13_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-6_EXT_MarketStreetBackdrop.004 100.0% EXT |
| ep13_shot02 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | B-6_LGT_MarketLedBoard_01 62.5% LGT |
| ep13_shot03 | 特写 | 60.48% | [70, 95] | OK | NG | NG | 0.0° OK | OK | B-6_PROP_TradeCounter_01 87.1% PROP |
| ep13_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-7_EXT_ReinforcedCloister_01 100.0% EXT |
| ep14_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-8_PROP_EmptyShelf_01 69.1% PROP |
| ep14_shot02 | 中景 | 40.37% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-8_CHAR_QueueMember_02 40.4% CHAR |
| ep14_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-8_EXT_FactoryHallShell 100.0% EXT |
| ep14_shot04 | 近景 | 70.04% | [55, 85] | OK | OK | NG | 0.0° OK | OK | B-8_EXT_FactoryHallShell.002 98.0% EXT |
| ep15_shot01 | 中景 | 48.2% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Yechengjun_01 48.2% CHAR |
| ep15_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-9_PROP_RefugeeCrowdMember_02 44.5% PROP |
| ep15_shot03 | 特写 | 47.1% | [70, 95] | OK | NG | OK | 0.0° OK | OK | B-9_CHAR_Suqingci_01 47.1% CHAR |
| ep15_shot04 | 中景 | 57.84% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Yehongyi_01 57.8% CHAR |
| ep16_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 98.7% EXT |
| ep16_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 66.4% EXT |
| ep16_shot03 | 中景 | 43.62% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-10_PROP_GapOpening_06 54.7% PROP |
| ep16_shot04 | 中景 | 42.09% | [35, 65] | OK | OK | NG | 0.0° OK | OK | B-10_PROP_DarkJunction_02 100.0% PROP |

**W1 19/32｜W2 14/19（另 13 镜角色未入画，W2 不判）｜W3 4/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep11_shot02', 'ep11_shot03', 'ep11_shot04', 'ep12_shot01', 'ep12_shot02', 'ep13_shot01', 'ep13_shot02', 'ep13_shot04', 'ep14_shot01', 'ep14_shot03', 'ep15_shot02', 'ep16_shot01', 'ep16_shot02']；W2 ['ep09_shot03', 'ep10_shot02', 'ep11_shot01', 'ep13_shot03', 'ep15_shot03']；W3 ['ep09_shot01', 'ep09_shot02', 'ep09_shot03', 'ep09_shot04', 'ep10_shot01', 'ep10_shot02', 'ep10_shot03', 'ep10_shot04', 'ep11_shot01', 'ep11_shot02', 'ep11_shot03', 'ep11_shot04', 'ep12_shot01', 'ep12_shot02', 'ep12_shot03', 'ep12_shot04', 'ep13_shot01', 'ep13_shot02', 'ep13_shot03', 'ep13_shot04', 'ep14_shot01', 'ep14_shot03', 'ep14_shot04', 'ep15_shot02', 'ep16_shot01', 'ep16_shot02', 'ep16_shot03', 'ep16_shot04']；W4 无；W5 无
