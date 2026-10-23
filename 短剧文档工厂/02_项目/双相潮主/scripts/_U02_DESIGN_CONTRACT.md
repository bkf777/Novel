# U02 白模与交接包 · 共享设计契约（唯一基准）

> 维护方：白模场景师（bot_e3df82ceee20）｜基线时点：2026-10-23 07:3x
> 适用单元：**U02**（ep9–ep16，32 镜，场景码 **B-1…B-10**）
> 上游真源：`units/U02/D11.json` v1.6｜`units/U02/D07.json` v1.3｜`units/U02/D12.json` v1.0
> 模板：`scripts/d13_content_U01.py`（1094 行）｜`scripts/white_model_content_U01.py`（759 行）｜`scripts/d14_contract_data_U01.py`（510 行）

---

## 〇、三层命名链路（**必须严格一致，错了整链失效**）

```
D13 prop.name（中文）
   ├─→ GEOM / MULTI / PROP_POS / PROP_ANIM 的键（中文）
   └─→ EN[中文] → 英文 core 名
                    └─→ 白模对象名 "{scene_code}_{CLASS}_{英文}" （如 B-1_CHAR_Luchen）
                              └─→ core_name() 剥离前缀 → 英文 core 名
                                                    └─→ SEMANTIC 的键
```

**铁律**：`EN` 的**值**集合 ⊆ `SEMANTIC` 的**键**集合（SEMANTIC 必须覆盖每一个 EN 值，一个不漏）。
`core_name()` 必须单元无关：正则为 `^[A-Z]-\d+_(?:CHAR|PROP|EXT|FX|LGT)_(.+?)(?:[._]\d+)?$`
（U01 版写死 `^A-\d+_`，**U02 必须放宽**，否则 `B-1_CHAR_Luchen` 不会被剥离 → SEMANTIC 全查不到 → 实体全落 `other`）。

---

## 一、坐标基线

### 1.1 厂房区基线（**延续 U01 同一座厂**）
- **O = 厂房正门门槛地面点 (0,0,0)**；+X 东 / +Y 北 / +Z 上；Z=0 为厂区地坪面。

| 区域 | 范围 | 说明 |
|---|---|---|
| 厂房外壳 | X −16.00..+14.00 / Y +00.00..+24.00 | 净高 12.00m；南立面即正门所在 |
| 厂区地坪（门禁区） | X −22.00..+14.00 / Y −20.00..+00.00 | 门禁区在正门内侧与门外两侧 |
| 西侧厂房 | X −22.00..−16.00 / Y −20.00..+00.00 | 可燃旧钢架结构（火线沿此延伸） |
| 围墙 | 厂区外缘：X=−22.00（西）、Y=+24.00（北）、X=+14.00（东） | 高 2.20m，钢板 |
| 净化区（内圈西跨） | X −14.00..−2.00 / Y +04.00..+16.00 | 钢制工作台 + 冷白工业灯 |
| 图纸墙与萃取线（内圈东跨） | X +00.00..+12.00 / Y +06.00..+20.00 | 钢桌、木板墙、萃取线 |
| 会议室 | X −10.00..−2.00 / Y +18.00..+23.00 | 可摊开城防图；冷金照明 |
| 指挥舱 | X −13.00..−07.00 / Y +18.00..+23.00 | 密闭；照明压到最低 |
| 保险柜位（小间） | X +06.00..+11.00 / Y +19.00..+23.00 | 钢板内嵌锁柜 |
| 厂区外道路（远景） | Y −34.00..−28.00 | 厂外灰雾天幕下的道路，只作远景 |
| 区域道路 | Y +70.00..+76.00 | 承接 U01（可选） |

### 1.2 骨市黑市基线（**独立局部基线**，不与厂房区共用）
- **O = 黑市街道中段地面点 (0,0,0)**；+X 东 / +Y 北 / +Z 上。

| 区域 | 范围 | 说明 |
|---|---|---|
| 黑市街道 | X −24.00..+24.00 / Y −14.00..+14.00 | 摊位排面沿街道两侧 |
| 电子屏位 | X −06.00..+00.00 / Y +06.00..+12.00 | 屏下压木牌 |

> ⚠️ 每镜独立 Blender scene 渲染并清场，**不同基线之间不会几何打架**（U01 出租屋独立基线同此理）。
>
> ⚠️ **但同一场内并存两套基线时会打架**：B-8 一场之内既有骨市黑市基线（g53）
> 又有厂房区基线（g54–g56），两者**原点重合**（都是 0,0,0）⇒ 共用一块壳体必然互穿。
> 处理：逻辑层 `build_white_model.py` 支持 `SHELL_OVERRIDE[(scene_code, gsn)]` **按镜换壳**
> （内容模块未声明时为空表 ⇒ U01 行为逐字不变），U02 用它把 g53 换成黑市壳体。

---

## 二、场景 ↔ 镜号 ↔ 空间 对照（D11 v1.6 实测）

| 场景 | 镜号 | ep | 空间（D07） | 机位组数 |
|---|---|---|---|---|
| B-1 | 33–36 | ep9 | 厂房外圈·门禁区 | 4 |
| B-2 | 37–40 | ep10 | 厂房内圈·净化区 | 4 |
| B-3 | 41–43 | ep11 | 厂房内圈·图纸墙与萃取线 | 3 |
| B-4 | 44 | ep11 | 骨市黑市（远景·开市瞬间） | 1 |
| B-5 | 45–48 | ep12 | 门禁区与公告投影位 | 4 |
| B-6 | 49–51 | ep13 | 骨市黑市（交易区） | 3 |
| B-7 | 52 | ep13 | 废弃军工机械厂（保险柜位） | 1 |
| B-8 | 53–56 | ep14 | 厂门预约位与会议室（**含黑市一镜**） | 4 |
| B-9 | 57–60 | ep15 | 指挥舱·名单位（**含夜围墙一镜**） | 4 |
| B-10 | 61–64 | ep16 | 夜·西侧厂房与厂门 | 4 |

> **B-8 / B-9 / B-10 各自含多个子空间** —— D13 的 `plan` 必须把该场**全部子空间**写全，`props` 必须覆盖各子空间的成物。

---

## 三、规范英文 core 名（**三个模块共用，不得另起名**）

### 3.1 角色（CHARS 键 / SEMANTIC 键）

| core | 中文 | 身高 | 特征 |
|---|---|---|---|
| `Luchen` | 陆沉 | 1.80 | 黑色战术风衣；本单元主要视角人物 |
| `LuchenHand` | 陆沉的手 | 0.30 | 敲数据板背面的手 |
| `Yehongyi` | 叶红衣 | 1.70 | 暗红劲装；携影刃 |
| `Suqingci` | 苏清辞 | 1.68 | 白色科研风衣 |
| `Yechengjun` | 叶承钧 | 1.81 | 象牙白短外套 + 黑色硬质肩章 |
| `Yechongyue` | 叶崇岳 | 1.78 | 叶家继承人；仅肩背入画 |
| `GreySpottedPatient` | 灰斑者 | 1.75 | 净化台上；灰斑覆满整条手臂 |
| `WelderWorker` | 焊接工 | 1.76 | g33 焊闸门 |
| `QueueMember` | 队列成员 | 1.75 | 持钎队列，剪影，不入面部 |
| `GuardPostMember` | 岗哨成员 | 1.75 | 两列岗哨 |
| `OrderSquadMember` | 秩序队成员 | 1.75 | 带离排队人群 |
| `CleanedPatient` | 被净化过的灰斑者 | 1.75 | 围成半圈，袖口卷起 |
| `MarketTrader` | 摊主 | 1.72 | 黑市摊位 |
| `MarketQueuer` | 排队者 | 1.73 | 黑市队伍两列 |
| `RefugeeCrowdMember` | 逃难者 | 1.74 | 暗处剪影 |
| `AssassinLeader` | 暗杀组领头人 | 1.79 | 对面剪影，不给面部 |
| `Rescuee` | 被救出的人 | 1.73 | g63 穿过缺口 |
| `DeathCampMember` | 死士营成员 | 1.75 | g47 门框内挤着的人影 |

> **§3.1 增补（2026-10-23）**：D11 g47 明写「死士营的人站在门内看着门外，人影挤在门框里」，
> 原 17 个角色 core 无对应项 ⇒ 补登 `DeathCampMember` 为第 18 个人形 core。
> 它与「秩序队」「岗哨」分属不同阵营，**不可互相顶替**。

### 3.1b 环境壳体 core（白模 `SHELL` 的 group 名直接当 core，须逐个登记）

| core | 用途 |
|---|---|
| `FactoryYardGround` | 厂区/厂房地坪整板（不分门禁区与厂房内部，避免共面 z-fighting） |
| `FactoryHallShell` | 厂房四壁与屋面（净高 12.00） |
| `FactorySouthFacade` | 南立面（含正门洞 X-2..+2 / 侧门洞 X-10..-7） |
| `WestPlantShell` | 西侧厂房可燃旧钢架结构 |
| `MarketStreetGround` | 黑市街面（独立基线） |
| `MarketStreetBackdrop` | 黑市两侧与尽头的建筑背景带 |
| `MeetingRoomShell` | 会议室壳体 |
| `CommandCockpitShell` | 密闭指挥舱壳体 |
| `PerimeterWall` | 厂区外缘围墙（既在 SEMANTIC，也在 D13 道具里） |

### 3.2 主要道具（GEOM/MULTI 键＝中文；EN 值＝下表英文）

| 中文 D13 名 | EN | 说明 |
|---|---|---|
| 正门卷帘门 | `MainRollerDoor` | B-1/B-5/B-8/B-10 |
| 简易闸门 | `WeldedGate` | B-1 焊成 |
| 钢架（成排） | `SteelRack` | 掩体 / 隔火两用 |
| 锈钢材堆 | `SteelStockPile` | B-1 |
| 井水桶 | `WaterBucket` | B-1 |
| 侧门 | `SideDoor` | B-1 |
| 数据板 | `DataTablet` | B-1/B-2/B-9 |
| 焊接设备 | `WelderRig` | B-1 |
| 钢制工作台 | `SteelWorkbench` | B-2 |
| 冷白工业灯 | `ColdWhiteIndustrialLamp` | B-2 头顶一盏 |
| 黑白双焰 | `BlackWhiteTwinFlame` | B-2 特效 |
| 白烟 | `WhiteSmoke` | B-2 特效 |
| 防御图纸 | `DefenseBlueprint` | B-3 |
| 木板墙 | `PlywoodWall` | B-3 |
| 钢桌 | `SteelTable` | B-3/B-9 |
| 雾核萃取线 | `VapourExtractionLine` | B-3 三段 |
| 压制槽 | `PressSlot` | B-3 |
| 出料台 | `OutfeedTable` | B-3 |
| 能量块 | `EnergyBlock` | B-3 带白霜 |
| 轮班表 | `DutyRoster` | B-3 贴墙 |
| 灰框面板 | `GreyFramePanel` | 悬浮界面（仅 D11 画面事实有界面元素的镜） |
| 旧铁皮墙 | `OldSheetMetalWall` | B-5 公告投影面 |
| 全服公告投影 | `CitywideNoticeProjection` | B-5 |
| 厂门队列 | `GateQueue` | B-5 剪影人群 |
| 秩序队 | `OrderSquad` | B-5 |
| 电子屏 | `MarketLedBoard` | B-4/B-6/B-8 |
| 摊位排面 | `MarketStalls` | B-4/B-6 |
| 无垢净髓木牌 | `CleanMarrowSignboard` | B-6 |
| 交易台 | `TradeCounter` | B-6 |
| 影刃 | `ShadowBlade` | B-6/B-10 |
| 律条 | `LawStrip` | B-6 |
| 加固小间 | `ReinforcedCloister` | B-7 |
| 保险柜 | `SteelSafe` | B-7 |
| 空货架 | `EmptyShelf` | B-8 |
| 断供通知 | `SupplyCutNotice` | B-8 |
| 钢门柱 | `SteelGatePost` | B-8 |
| 预约木牌 | `AppointmentBoard` | B-8 |
| 配额名单 | `QuotaRoster` | B-8 |
| 委员会屏幕 | `CommitteeScreen` | B-8 |
| 城防图 | `CityDefenseMap` | B-8 |
| 继承人印 | `HeirSeal` | B-8 |
| 名单 | `EntryRoster` | B-9 |
| 旧棉衣 | `OldCottonCoat` | B-9 |
| 制式护具 | `StandardArmour` | B-9 |
| 围墙 | `PerimeterWall` | B-9 |
| 应急灯 | `EmergencyLamp` | B-9 |
| 墙位影子 | `UnexpectedShadow` | B-9 |
| 火头 | `FireHead` | B-10 特效，三处 |
| 缺口 | `GapOpening` | B-10 |
| 暗处路口 | `DarkJunction` | B-10 |
| 笔 | `PointerPen` | B-8 会议室城防图上的笔 |
| 钢钎 | `SteelPick` | B-9 墙位（与弹药拆开） |
| 弹药 | `AmmunitionBox` | B-9 墙位（与钢钎拆开） |
| 火线 | `FireLine` | B-10 火线（沿分隔结构延伸） |

> 新增道具时：**中文名进 D13，英文名进 EN，英文名必须同时进 SEMANTIC**。

---

## 四、机位推导规则（从 D11 的景别/角度/运镜机械推出）

| D11 景别 | 机位距主体 | 镜头高度 |
|---|---|---|
| 远景 / 全景 | 8.0–14.0 m | 1.6–2.2 m（地面以上） |
| 中远景 | 5.0–8.0 m | 1.5–1.9 m |
| 中景 | 3.0–5.0 m | 1.4–1.8 m |
| 近景 | 1.6–2.6 m | 1.3–1.7 m |
| 特写 | 0.9–1.8 m | 1.0–1.6 m |

- **俯视**：机位高度 > 主体头顶 1.0 m 以上（俯角 ≥ 35°）。
- **仰视**：机位高度 ≤ 1.0 m，且主体在画面上方。
- **过肩**：机位在主体**侧后方**，肩线入画（主体距机位 1.2–2.0 m，侧偏 0.4–0.7 m）。
- **主观视角**：机位＝主体眼位，**主体不建实体**（白模里该角色不出画）。
- **运镜**：`推/拉` → 机位沿视线轴前后；`移` → 沿垂直于视线轴横移（**D14 的 motion_type 枚举无 truck，用 dolly 兜底，但 world_path 必须写清横向坐标**）；`跟` → tracking；`升降` → crane；`手持` → handheld；`固定` → static。
- **主体不入画的镜**：队列/人群/剪影类，**只建剪影体块，不建面部**。

### 4.1 机位落进体积 ⇒ 整帧灰板（U02 实测两条，血的教训）

- `clear_keys_from_camera` **只避让角色**（`CHARS`/`CHAR_ANIM`），**避让不了道具**。
  道具体积大、又常按 D13 登记点摆 ⇒ 机位很容易落进**道具体积内部**，
  Workbench 渲出的是盒体内壁 ⇒ **整帧纯灰、零几何**（与 U01 g27 同根因、但走的是道具路径）。
- **U02 实测命中 2 例**（均被「整帧平场」与「机位穿入实体」双判据同时抓到）：
  - g39：机位 (-9.50, 9.00, 1.38) 落在 B-2 第二架钢架体内（深陷 0.30m）⇒ 修法：钢架改**沿 X 并排**。
  - g51：机位 (-3.00, 4.94, 1.60) 落在 B-6 摊主体内（深陷 0.12m）⇒ 修法：摊主移到**台后西端**（X=-3.90 / Y=+6.30），既出画幅又不遮主体。
- **纪律**：白模出片后**必须**跑两个检测器（`check_white_model_frames.py` 整帧平场、
  `check_camera_inside_geometry.py` 机位穿入实体）；只跑 validate 过不了这一类问题。
- **同材质同法向 ⇒ 读不出**：俯视特写里，小物平放大平面上时，顶面同色 ⇒ 主体读不出来
  （g51 的律条 0.02 薄板实测 unique=5 / std=0.45）。修法：**给足厚度**让侧壁入画
  （律条改 0.10 后 unique=180 / std=18.8），或改机位使小面不与平面同法向。

---

## 五、预算与硬约束

1. **h3_prompt ≤ 6500 字符**（schema `char_count` 上限）。
   - 经验杠杆：**运动实例数** 每个 ≈ 495 字符；**实体数** 每个 ≈ 205 字符。
   - 群体主体（队列/人群/岗哨）用 `MULTI` 合成**单对象**以压实例数，但**人数要在 D11 画面事实里可数**的镜（g60 影子数量一眼可数）例外处理。
2. **D13 禁镜头设计词**：景别/焦距/毫米/运镜/构图/画幅/中景/近景/特写/远景/全景/中远景/中近景/过肩/主观视角/客观跟拍/仰视/俯视/顶视/平视/手持/变焦/环绕/跟拍 —— **D13 的 props/plan/notes 一律不得出现**（D11 职责）。
3. **禁血腥词**（连否定句也不许出现）：血液/血肉/喷溅/器官/创口/创面/十字/光环/念珠/法衣/祭坛。
4. **禁术语同义写法**：以 `shared/D05.json` 的 `glossary[].forbidden_synonyms` 为准（D13 自检会扫）。
5. **`灰框面板` 只登记在该场 D11 `visual_facts` 出现界面元素（面板/进度条/读数栏/通报条/读数暴涨）的场景**，否则自检报错。
6. **D07 `scene_needs` 键名不统一**（ep9–11 用「空间」，ep12–16 用「space」）→ `build_D13.py` 已做**读取兼容**；`NEEDS_KEYWORDS` 的键用**空间名原文**（不含括号内的细分说明）。
7. **`NEEDS_KEYWORDS` 必须覆盖 D07 的每一条 (ep, 空间)**，且**每个 D13 场景码都要被至少一条 NEEDS_KEYWORDS 的 targets 覆盖**（否则自检报错「D13 X 未被任何 D07 scene_needs 覆盖」）。
8. **交接包内不得出现 `/tmp` 绝对路径** —— 相对 `units/<UNIT>/`。
9. **零创口、零红色液体、零人体异化画面**（D03 R08）——异化只作面板文字。

---

## 六、自检与出口

```bash
cd /Users/ezreal/projects/小说创作/短剧文档工厂
python3 02_项目/双相潮主/scripts/build_D13.py --unit U02            # 内部 9 项自检
python3 02_项目/双相潮主/scripts/build_white_model.py --unit U02 --out /tmp/dcc-smoke
python3 02_项目/双相潮主/scripts/d14_pipeline.py preflight --root /tmp/dcc-smoke/u02
python3 02_项目/双相潮主/scripts/fill_D14_contracts.py --unit U02
python3 02_项目/双相潮主/scripts/d14_pipeline.py check   --root /tmp/dcc-smoke/u02
python3 02_项目/双相潮主/scripts/d14_pipeline.py prompt  --root /tmp/dcc-smoke/u02
python3 02_项目/双相潮主/scripts/assemble_D14.py --unit U02 --work /tmp/dcc-smoke/u02
node 04_工具/validate.mjs --project 02_项目/双相潮主 --unit U02    # error 必须 0
node 04_工具/validate.mjs --project 02_项目/双相潮主              # 全项目 error 必须 0
```
