# W1–W8 实测结果（Q94 白模重建）

判据真源：`03_规格/rules.json → white_model_framing`；实现口径对齐 `04_工具/lib/rules.mjs` 的 V12。


## U01

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep01_shot01 | 中景 | 49.97% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-1_CHAR_Luchen_01 50.0% CHAR |
| ep01_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-1_EXT_Corridor 100.0% EXT |
| ep01_shot03 | 中景 | 49.92% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-1_CHAR_Luchen_01 49.9% CHAR |
| ep01_shot04 | 全景 | 12.52% | [5, 20] | OK | OK | OK | 0.0° OK | OK | A-1_CHAR_Luchen_01 12.5% CHAR |
| ep02_shot01 | 中远景 | 29.67% | [20, 40] | OK | OK | OK | 0.0° OK | OK | A-2_CHAR_Luchen_01 29.7% CHAR |
| ep02_shot02 | 中景 | 49.96% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-2_CHAR_Luchen_01 50.0% CHAR |
| ep02_shot03 | 中远景 | 30.02% | [20, 40] | OK | OK | OK | 0.0° OK | OK | A-3_CHAR_Luchen_01 30.0% CHAR |
| ep02_shot04 | 远景 | 16.58% | [8, 25] | OK | OK | OK | 0.0° OK | OK | A-3_CHAR_LuchenHand_02 16.6% CHAR |
| ep03_shot01 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | A-4_EXT_FactorySouthWall_01 100.0% EXT |
| ep03_shot02 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | A-4_LGT_GreyFramePanel_01 100.0% LGT |
| ep03_shot03 | 近景 | 70.0% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-4_CHAR_LuchenHand_02 70.0% CHAR |
| ep03_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-4_LGT_StreetLamp_06 100.0% LGT |
| ep04_shot01 | 中景 | 49.99% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-5_CHAR_Luchen_01 50.0% CHAR |
| ep04_shot02 | 特写 | 81.81% | [70, 95] | OK | OK | OK | 0.0° OK | OK | A-5_CHAR_LuchenHand_01 81.8% CHAR |
| ep04_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | A-5_LGT_GreyFramePanel_01 91.4% LGT |
| ep04_shot04 | 中景 | 50.71% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-5_CHAR_Luchen_01 50.7% CHAR |
| ep05_shot01 | 中远景 | 29.1% | [20, 40] | OK | OK | OK | 0.0° OK | OK | A-6_CHAR_EscortQueueMember 29.1% CHAR |
| ep05_shot02 | 近景 | 67.97% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-6_CHAR_Yechengjun_01 68.0% CHAR |
| ep05_shot03 | 远景 | 11.3% | [8, 25] | OK | OK | NG | 0.0° OK | OK | A-6_EXT_InnerYard 12.6% EXT |
| ep05_shot04 | 近景 | 70.04% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-6_CHAR_Yechengjun_01 70.0% CHAR |
| ep06_shot01 | 中景 | 49.97% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 50.0% CHAR |
| ep06_shot02 | 中景 | 50.1% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_GuardCaptain_02 50.1% CHAR |
| ep06_shot03 | 中景 | 49.47% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 49.5% CHAR |
| ep06_shot04 | 中景 | 49.99% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-7_CHAR_Luchen_01 50.0% CHAR |
| ep07_shot01 | 中景 | 50.0% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Yehongyi_02 50.0% CHAR |
| ep07_shot02 | 近景 | 69.97% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Luchen_01 70.0% CHAR |
| ep07_shot03 | 近景 | 78.6% | [55, 85] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Luchen_01 78.6% CHAR |
| ep07_shot04 | 中景 | 50.03% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-8_CHAR_Yehongyi_02 50.0% CHAR |
| ep08_shot01 | 中景 | 50.57% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_DarkRedOutfit_01 50.6% CHAR |
| ep08_shot02 | 中远景 | 30.13% | [20, 40] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_Luchen_01 30.1% CHAR |
| ep08_shot03 | 远景 | 6.8% | [8, 25] | OK | NG | NG | 0.0° OK | OK | A-9_EXT_SteelPlateWall_01 7.7% EXT |
| ep08_shot04 | 中景 | 49.75% | [35, 65] | OK | OK | OK | 0.0° OK | OK | A-9_CHAR_Luchen_01 49.8% CHAR |

**W1 27/32｜W2 26/27（另 5 镜角色未入画，W2 不判）｜W3 25/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep01_shot02', 'ep03_shot01', 'ep03_shot02', 'ep03_shot04', 'ep04_shot03']；W2 ['ep08_shot03']；W3 ['ep01_shot02', 'ep03_shot01', 'ep03_shot02', 'ep03_shot04', 'ep04_shot03', 'ep05_shot03', 'ep08_shot03']；W4 无；W5 无

## U02

| 镜位 | 景别 | 主体占幅 | 区间 | W1 | W2 | W3 | W4 跳变 | W5 | 画面最大对象 |
|---|---|---|---|---|---|---|---|---|---|
| ep09_shot01 | 中远景 | 30.0% | [20, 40] | OK | OK | OK | 0.0° OK | OK | B-1_CHAR_WelderWorker_01 30.0% CHAR |
| ep09_shot02 | 中远景 | 30.0% | [20, 40] | OK | OK | OK | 0.0° OK | OK | B-1_CHAR_Yehongyi_01 30.0% CHAR |
| ep09_shot03 | 近景 | 62.96% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-1_CHAR_LuchenHand_01 63.0% CHAR |
| ep09_shot04 | 中景 | 50.49% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-1_CHAR_Suqingci_01 50.5% CHAR |
| ep10_shot01 | 中景 | 50.0% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-2_CHAR_Suqingci_01 50.0% CHAR |
| ep10_shot02 | 近景 | 70.3% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-2_CHAR_GreySpottedPatient_01 70.3% CHAR |
| ep10_shot03 | 近景 | 69.76% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-2_CHAR_GreySpottedPatient_01 69.8% CHAR |
| ep10_shot04 | 近景 | 70.01% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-2_CHAR_Suqingci_02 70.0% CHAR |
| ep11_shot01 | 特写 | 81.94% | [70, 95] | OK | OK | OK | 0.0° OK | OK | B-3_CHAR_Suqingci_01 81.9% CHAR |
| ep11_shot02 | 中远景 | 0.0% | [20, 40] | NG | — | NG | 0.0° OK | OK | B-3_EXT_FactoryHallShell.002 50.3% EXT |
| ep11_shot03 | 中景 | 49.77% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-3_CHAR_GuardPostMember_03 49.8% CHAR |
| ep11_shot04 | 中景 | 49.59% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-4_CHAR_MarketQueuer_04 49.6% CHAR |
| ep12_shot01 | 特写 | 0.0% | [70, 95] | NG | — | NG | 0.0° OK | OK | B-5_EXT_OldSheetMetalWall_01 100.0% EXT |
| ep12_shot02 | 远景 | 16.49% | [8, 25] | OK | OK | OK | 0.0° OK | OK | B-5_CHAR_GateQueue_03 16.5% CHAR |
| ep12_shot03 | 中景 | 48.75% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-5_CHAR_DeathCampMember_02 48.8% CHAR |
| ep12_shot04 | 中景 | 50.1% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-5_CHAR_CleanedPatient_03 50.1% CHAR |
| ep13_shot01 | 中景 | 53.14% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-6_CHAR_MarketQueuer_06 53.1% CHAR |
| ep13_shot02 | 中远景 | 30.0% | [20, 40] | OK | OK | OK | 0.0° OK | OK | B-6_CHAR_MarketQueuer_06 30.0% CHAR |
| ep13_shot03 | 特写 | 83.03% | [70, 95] | OK | OK | OK | 0.0° OK | OK | B-6_CHAR_MarketQueuer_06 83.0% CHAR |
| ep13_shot04 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-7_EXT_ReinforcedCloister_01 100.0% EXT |
| ep14_shot01 | 中景 | 49.86% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-8_CHAR_MarketQueuer_05 49.9% CHAR |
| ep14_shot02 | 中景 | 50.35% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-8_CHAR_QueueMember_02 50.4% CHAR |
| ep14_shot03 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-8_EXT_FactoryHallShell 100.0% EXT |
| ep14_shot04 | 近景 | 69.97% | [55, 85] | OK | OK | OK | 0.0° OK | OK | B-8_CHAR_Luchen_01 70.0% CHAR |
| ep15_shot01 | 中景 | 50.09% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Yechengjun_01 50.1% CHAR |
| ep15_shot02 | 远景 | 16.82% | [8, 25] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_RefugeeCrowdMember_02 16.8% CHAR |
| ep15_shot03 | 特写 | 82.27% | [70, 95] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Suqingci_01 82.3% CHAR |
| ep15_shot04 | 中景 | 41.59% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-9_CHAR_Yehongyi_01 41.6% CHAR |
| ep16_shot01 | 中景 | 0.0% | [35, 65] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 98.7% EXT |
| ep16_shot02 | 远景 | 0.0% | [8, 25] | NG | — | NG | 0.0° OK | OK | B-10_EXT_WestPlantShell 66.4% EXT |
| ep16_shot03 | 中景 | 50.01% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-10_CHAR_QueueMember_03 50.0% CHAR |
| ep16_shot04 | 中景 | 50.6% | [35, 65] | OK | OK | OK | 0.0° OK | OK | B-10_CHAR_Yehongyi_01 50.6% CHAR |

**W1 26/32｜W2 26/26（另 6 镜角色未入画，W2 不判）｜W3 26/32｜W4 32/32｜W5 32/32**

- W6 姿态冲突：**0 处** （全部清零）
- W7 逐镜包：磁盘 32 镜 / 索引 32 镜，缺文件 0 处，索引差异 无 ⇒ **合格**
- W8 合同有效：32/32 ⇒ **合格**
- 投影字段：rotation_euler_deg 已提供=True，pose 已提供=True（V12 的两条 warning 应消失）

**不合格镜号**：W1 ['ep11_shot02', 'ep12_shot01', 'ep13_shot04', 'ep14_shot03', 'ep16_shot01', 'ep16_shot02']；W2 无；W3 ['ep11_shot02', 'ep12_shot01', 'ep13_shot04', 'ep14_shot03', 'ep16_shot01', 'ep16_shot02']；W4 无；W5 无
