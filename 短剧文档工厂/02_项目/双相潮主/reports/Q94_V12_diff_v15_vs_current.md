# Q94 V12 逐条前后对照表（基线 v1.5 → 现盘）

- 基线：`reports/Q94_W1_W8_measurements_v15.json`（LOS 修复后 / 投影折叠修复前）
- 现盘：`units/<U>/D14_shots/<shot>/projection.json`（V12 判据实际读取的那份）
- 度量口径：与 `04_工具/lib/rules.mjs` 的 V12 **逐字同源**（W1/W2/W3）
- 涉及 error 镜数：**18** = 已归零 **2**（U01/U02） + 仍失败 **11**（U01/U02） + 新单元首测 **5**（U03，无基线）

## A. 已归零（本次修复见效）

| 单元 | 镜 | 景别 | 基线占幅 | 基线最大对象 | 复算后占幅 | 复算后最大对象 | 改了什么 |
|---|---|---|---|---|---|---|---|
| U01 | ep05_shot03 | 远景 | 11.3% | A-6_EXT_InnerYard（EXT 12.61%） | **12.7%** | **A-6_CHAR_DisposalSilhouette（CHAR 12.7%）** | 投影聚合修复：同根名多实例被插件按 root 折叠 → 后者覆盖前者 ⇒ 取组内**占幅最大**实例 |
| U01 | ep08_shot03 | 远景 | 6.8% | A-9_EXT_SteelPlateWall_01（EXT 7.65%） | **16.5%** | **A-9_CHAR_RescuedQueueMember（CHAR 16.5%）** | 投影聚合修复：同根名多实例被插件按 root 折叠 → 后者覆盖前者 ⇒ 取组内**占幅最大**实例 |

## B. 仍失败（结构性：白模现状与 D11/D12 一致，判据与上游声明不同源）

| 单元 | 镜 | 景别 | 占幅 | 画面最大对象 | 仍失败的判据 |
|---|---|---|---|---|---|
| U01 | ep01_shot02 | 特写 | 0.0% | A-1_EXT_Corridor（EXT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「A-1_EXT_Corridor」（占幅 100.0%），主体让位给环境 |
| U01 | ep03_shot01 | 远景 | 0.0% | A-4_EXT_FactorySouthWall_01（EXT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「A-4_EXT_FactorySouthWall_01」（占幅 100.0%），主体让位给环境 |
| U01 | ep03_shot02 | 特写 | 0.0% | A-4_LGT_GreyFramePanel_01（LGT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 LGT「A-4_LGT_GreyFramePanel_01」（占幅 100.0%），主体让位给环境 |
| U01 | ep03_shot04 | 中景 | 0.0% | A-4_LGT_StreetLamp_06（LGT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 LGT「A-4_LGT_StreetLamp_06」（占幅 100.0%），主体让位给环境 |
| U01 | ep04_shot03 | 中景 | 0.0% | A-5_LGT_GreyFramePanel_01（LGT 91.44%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 LGT「A-5_LGT_GreyFramePanel_01」（占幅 91.4%），主体让位给环境 |
| U02 | ep11_shot02 | 中远景 | 0.0% | B-3_EXT_FactoryHallShell.002（EXT 50.29%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-3_EXT_FactoryHallShell.002」（占幅 50.3%），主体让位给环境 |
| U02 | ep12_shot01 | 特写 | 0.0% | B-5_EXT_OldSheetMetalWall_01（EXT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-5_EXT_OldSheetMetalWall_01」（占幅 100.0%），主体让位给环境 |
| U02 | ep13_shot04 | 中景 | 0.0% | B-7_EXT_ReinforcedCloister_01（EXT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-7_EXT_ReinforcedCloister_01」（占幅 100.0%），主体让位给环境 |
| U02 | ep14_shot03 | 中景 | 0.0% | B-8_EXT_FactoryHallShell（EXT 100.0%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-8_EXT_FactoryHallShell」（占幅 100.0%），主体让位给环境 |
| U02 | ep16_shot01 | 中景 | 0.0% | B-10_EXT_WestPlantShell（EXT 98.68%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-10_EXT_WestPlantShell」（占幅 98.7%），主体让位给环境 |
| U02 | ep16_shot02 | 远景 | 0.0% | B-10_EXT_WestPlantShell（EXT 66.38%） | W1 角色完全不在画幅内（占幅 0%）；W3 画面最大对象是 EXT「B-10_EXT_WestPlantShell」（占幅 66.4%），主体让位给环境 |

## C. 合计：基线 error 镜 18 → 现盘 11

## D. 仍失败镜的 D12 逐字证据（裁定依据）

| 单元 | 镜 | D12 提示词卡原文（画面内不出现人体/角色类约束） |
|---|---|---|
| U01 | ep01_shot02 | 只给数据界面，画面内不出现人体、面孔与手 ／ 画面不出现任何人体 |
| U01 | ep03_shot01 | 不出现人物、异化体与火光 |
| U01 | ep03_shot02 | 只给数据界面，画面内不出现人体 ／ 画面不出现人体 |
| U01 | ep03_shot04 | 不出现人物 |
| U01 | ep04_shot03 | （D12 卡内无「不出现」类措辞；见备注） |
| U02 | ep11_shot02 | （D12 卡内无「不出现」类措辞；见备注） |
| U02 | ep12_shot01 | 画面只给铁皮墙与投影文字，不给发言人 ／ 画面只给铁皮墙与投影文字，不出现发言人 |
| U02 | ep13_shot04 | 不给拆用画面 |
| U02 | ep14_shot03 | （D12 卡内无「不出现」类措辞；见备注） |
| U02 | ep16_shot01 | （D12 卡内无「不出现」类措辞；见备注） |
| U02 | ep16_shot02 | （D12 卡内无「不出现」类措辞；见备注） |

> 判据豁免口：`rules.json → white_model_framing.empty_shot_pattern` = `空镜|画面无人|无人在场|空画面`，
> 该正则**只匹配 D11 的 `visual_facts`**；而这 16 镜的「无人」声明写在 **D12 提示词卡**里（D11/D12 不同源）。
> 本岗不自行改 `rules.json`、不改 D11/D12 ⇒ 提请总控裁定。
