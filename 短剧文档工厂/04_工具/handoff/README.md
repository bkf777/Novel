# D14 逐镜交接包基础设施

每镜一个独立交接包（U01 = 32 镜 = 32 份），D14.json 是它们的索引 + 汇总。
原因：blender-h3-dcc 技能是**逐镜**流程，H3 单次生成受帧数格点 `17n+5` 限制，
45 秒单元不可能一次生成；单份单元合同无法表达逐镜状态。

> **2026-10-23 01:34 起本文件记的是「现役新链」。**
> 早先记的 `make_plan.py → batch_build.py → finalize_d14.py`（旧 plan 链）已**归档**，
> 见文末「旧 plan 链（已归档，非生产路径）」。
> 留旧流程＝必然按旧流程重跑，谁重跑一次就会把已核验的 D14 打回旧结构。

## 目录布局

```
units/<UNIT>/
  D14.json                       ← 单元索引（shots[] + commands + check_results）
  D14_shots/                     ← 逐镜交接包（目录名 ep<NN>_shot<NN>，见字段规格表）
    ep01_shot01/
      preview_video.mp4          ← Blender 白模导出（真实素材，540×960 竖屏 9:16）
      manifest.json              ← 导出侧车（结构证据 = 逐镜可见实例清单的来源）
      preflight.json             ← 脚本产出
      render_contract.json       ← 脚本产出 + 填装（M3_FILL 全字段）
      appearance.json            ← 脚本产出 + 填装
      h3_prompt.txt              ← build-prompt 脚本产出（禁手写）
      h3_prompt_budget.json      ← 预算报告
      package.json               ← 该镜交接包（D14ShotPackage，与 D14 内联项同形）
      projection.json            ← 逐锚点帧投影真值（屏幕范围/遮挡/深度）
      scene_spec.json / shot_spec.json
      source_anchor_frames/      ← 锚点帧（喂 H3 的源画面）
```

`D14.json` 的 `shots[]` 每项是**完整 D14ShotPackage**（schema `additionalProperties=false`），
不是精简索引；`shots[].package_path` = `D14_shots/ep<NN>_shot<NN>/package.json`（相对 `units/<UNIT>/`）。

## 硬纪律

1. `h3_prompt.txt` **只由** `m3_render_workflow.py build-prompt` 产出，禁手写、禁裁剪、禁二次优化。
2. `render_contract.json` 的 `M3_FILL` 字段必须**实看完整源视频**后填写，不得靠缩略图猜。
3. `source_inventory` 条目**不得删除**；每个可见源实例一对一守恒
   （`one_to_one_no_merge_split_delete_or_replace`）。
   —— 章程 §六 与 blender-h3-dcc `SKILL.md` 同款禁令。**因此可见实例清单必须在生产端正确**
   （见下「可见性证据」），填装阶段不做任何增删。
4. 描述字段只写一个可见事实；anchor 的 `orientation/motion_state/spatial_relations` 各 3–8 个英文词。
5. 美术质量不能抵消结构失败：新增切镜 / 跳轴 / 动作改写一律失败。
6. **只交到交接包，绝不提交 H3 付费生成**。付费提交与结果 QA 属用户执行端。

## 现役新链（6 步 + 1 步前置）

全部脚本在 `02_项目/双相潮主/scripts/`。`<UNIT>` 形如 `U01`／`U02`，`<WORK>` 形如 `/tmp/dcc-smoke/u01`。

```bash
cd 短剧文档工厂
PROJ=02_项目/双相潮主
UNIT=U01
WORK=/tmp/dcc-smoke/$(echo $UNIT | tr 'A-Z' 'a-z')

# ⓪ 前置：D13 场景白模说明书（内容层出数据，逻辑层组装）
python3 $PROJ/scripts/build_D13.py --unit $UNIT --content d13_content_$UNIT

# ① 白模：Blender --background，逐镜建 scene 并导出 preview_video.mp4 + manifest.json
D13_STAMP=$(echo $UNIT | tr 'A-Z' 'a-z') D13_SHADE=v4 \
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python $PROJ/scripts/build_white_model.py -- \
  --project $PROJ --out $(dirname $WORK) --unit $UNIT --content white_model_content_$UNIT

# ② preflight：产 preflight.json + render_contract/appearance 骨架
python3 $PROJ/scripts/d14_pipeline.py preflight --root $WORK

# ③ 填装：把骨架里的 M3_FILL 换成实测描述（内容层取语义表）
python3 $PROJ/scripts/fill_D14_contracts.py --unit $UNIT --work $WORK

# ④ 合同自检：check-contract
python3 $PROJ/scripts/d14_pipeline.py check --root $WORK

# ⑤ 提示词：build-prompt（禁手写）
python3 $PROJ/scripts/d14_pipeline.py prompt --root $WORK

# ⑥ 组装：逐镜 package.json + D14.json 单元索引
python3 $PROJ/scripts/assemble_D14.py --unit $UNIT --work $WORK

# 出口硬闸 + 渲染
node 04_工具/validate.mjs --project $PROJ --unit $UNIT
node 04_工具/render-md.mjs --project $PROJ
```

### 参数面

| 脚本 | 参数 | 默认 |
|---|---|---|
| `build_D13.py` | `--unit` / `--content` / `--project` | `U01` / `d13_content_<UNIT>` / 脚本位置推导 |
| `build_white_model.py` | `--project` / `--out` / `--unit` / `--content`（须在 Blender `--` 之后） | 无默认（必给） / `white_model_content_<UNIT>` |
| `fill_D14_contracts.py` | `--unit` / `--project` / `--work` / `--content` | `U01` / 脚本位置推导 / `/tmp/dcc-smoke/<unit小写>` / `d14_contract_data_<UNIT>` |
| `assemble_D14.py` | `--unit` / `--project` / `--work` | `U01` / 脚本位置推导 / `/tmp/dcc-smoke/<unit小写>` |
| `d14_pipeline.py` | 子命令 `preflight`｜`check`｜`prompt` + `--root` | `--root` 必给 |

环境变量同义：`UNIT_ID` / `D14_PROJECT` / `D14_WORK` / `D14_CONTENT` / `D13_CONTENT` / `WM_CONTENT`。

## 逻辑层 / 内容层分工（**禁止 `_u02` 副本**）

现役脚本一律按 `--unit` 参数化。**新单元不许复制一份 `xxx_u02.py`** ——
副本即第二套实现，U02 与 U01 必然分叉；参数化后 U02 复用同一实现。

| 层 | 文件 | 装什么 |
|---|---|---|
| 逻辑（单元无关） | `build_D13.py` | 组装 + 落盘；场景数据由内容模块给 |
| 逻辑（单元无关） | `build_white_model.py` | Blender 建场/相机/导出/结构证据采集；**不含任何内容表** |
| 逻辑（单元无关） | `fill_D14_contracts.py` | 合同填装算法；语义/动作/交互/声音取内容模块 |
| 逻辑（单元无关） | `assemble_D14.py` | 逐镜 package.json + D14.json 组装 |
| 逻辑（单元无关） | `d14_pipeline.py` | preflight / check / prompt 驱动 |
| 内容（每单元一份） | `d13_content_<UNIT>.py` | `SCENE_COUNT` / `NEEDS_KEYWORDS` / `build_scenes(h)` |
| 内容（每单元一份） | `white_model_content_<UNIT>.py` | 13 张表：`GEOM` `GEOM_OVERRIDE` `PROP_POS` `CHAR_POS` `MULTI` `CUTS` `SHELL` `EN` `CHARS` `CAM_MOVE` `POSE_SIZE` `CHAR_ANIM` `PROP_ANIM` |
| 内容（每单元一份） | `d14_contract_data_<UNIT>.py` | 实体语义表 / 镜头动作表 / 交互表 / 声音表 / 风格圣经 |

规矩：

1. 内容模块用 `importlib` 按名加载，**不得自带绝对路径**（项目根与工作区由调用方按
   `--project` / `--work` 传入）；内容模块若写死路径，U02 复用时会静默指向 U01。
2. **不得设跨单元兜底**：找不到 `d14_contract_data_<UNIT>` 就报错，
   回落到别的单元的内容＝静默用错数据。
3. 内容模块缺失时链会**响亮失败**，不是静默出半成品。
4. 改名即退役旧脚本（可恢复删除），避免两套实现并存漂移。

## 两条场景规格约定

### ① 角色代理：`pose` × 底面 z × 时间比例

角色代理的体量、落位与运动由三个量共同决定，缺一不可：

- **`pose`** —— 姿态枚举，决定代理体量（`POSE_SIZE`）：
  `stand`(0.50×0.35×1.80) / `crouch`(0.45×0.35×1.08) / `kneel`(0.45×0.35×0.99) /
  `seated`(0.45×0.35×0.99) / `situp`(0.50×0.35×0.75) / `hand`(0.10×0.10×0.30) /
  `lie`(1.80×0.45×0.35)。
- **底面 z** —— `CHAR_ANIM` 键元组第 4 位是**底面高**（不是体心高）：
  `(scene_code, gsn) -> {英文名: [(时间比例, x, y, 底面z, pose), ...]}`。
  代理按体量往上长，落位用底面 z + 体高/2 求体心。
- **时间比例** —— 键元组第 1 位是 **0.00–1.00 的归一化时间比例**（不是秒）。
  同一镜内多关键帧按比例插值；`0.00` 与 `1.00` 是首末态。

⚠️ 三者任一换算错都**不报错**：代理会静默半高、沉地或穿模。
改动这三个量的语义时，必须同步改下游读法并回算一镜实查。

### ② 道具：`center_m[2]` 是几何体心（**不是底面高**）

D14 `scene_spec.props[].center_m` 取自白模 manifest 的 `world_location`，
即 Blender 物体的**原点（几何体心）**。因此：

- `center_m[2]` **不是**该道具的底面高，**不能**再拿它当底面叠加体高。
- 构建器对 D13 `position_m[2]` 的语义判读，由内容表 `GEOM`/`GEOM_OVERRIDE` 的
  **`zmode`** 字段**静态声明**（不再靠运行时启发式猜）：

  | zmode | D13 `position_m[2]` 的含义 | 体心换算 |
  |---|---|---|
  | `base`（缺省） | 底面高（落在支撑面上：窗台高／台面高／落地件） | `pos_z + dz/2` |
  | `center` | 体心高（贴附人体表面或悬浮：套环／腕环／表盘／体表） | `pos_z` |
  | `top` | 顶面高（标高／顶板） | `pos_z - dz/2` |

- 两处语义变更必须同源同步：**上游改了坐标语义，下游必须同步换算**，
  否则只半高下沉、不报错（只出图不报错＝最难查的一类）。

> **codex 深审判定：启发式只作迁移工具，不是最终空间真源。**
> 正确终局是 D13 的 props 上带显式语义字段（`z_basis: bottom|center|top` + 依据），
> 由 `scripts/build_D13.py` 落盘。当前 U01 有 52 条 props 的 `pos_z ≠ 0` 待人工收口
> （D18 `U01-R14`），重点：钢钎「斜靠…约 70°」、撬棍「斜顶于…下缘」、
> 楼道感应灯「中心 Z=+2.20」、冷白灯管「底面 Z=+2.55」、A-6 审批终端台「台面高 +0.30」。

## 可见性证据：清单必须在生产端正确

`manifest.json` 的 `structure_evidence[].samples[].projected_visible` 曾以
→「物体有角点在相机前方」为判据，导致**完全在画外的墙/道具也被登记成可见**，
下游再去删就成了「删 source_inventory」（违反硬纪律 3）。

现在：判据是**投影包围盒与画幅相交**，且采样从首/中/尾 3 帧加密到覆盖全片
（每 ~12 帧一采，共约 24 帧），避免中途入画的物件漏登记。
`ever_projected_visible` 与 `projected_visible` 随之变成「该实例在本镜某帧真的入画」。

后果：填装器**不做任何裁剪**；`source_inventory` 天然只含本镜真实可见的实例。

### POV 镜补前臂占位体

主观视角下手腕高度有骨纹/束具/双焰时，内容表的 `MULTI` 会补一段「右前臂占位」，
让腕饰有身体依托；机位离腕饰 <0.35m 时不补（否则前臂会糊住画面）。

## 已实测基准（2026-10-23，总控实跑）

- 环境：Blender 5.2.2 LTS + minimax_h3 1.0.7，24fps，**540×960 竖屏（9:16）**。
  画幅必须与 D12 的 aspect=9:16 一致，否则 16:9 的窄垂直视锥会把 1.75m 人物裁成「头顶出画」的假缺陷。
- 耗时：白模导出 + preflight + 投影真值 约 **3–5 秒/镜**，32 镜整批约 2.5 分钟。
- U01 终稿：**32/32 镜** `check-contract` valid 且 `build-prompt` 三布尔全 true，
  提示词 **3,961–6,483 字**（预算 6,500 / H3 硬上限 7,000）。
- 工厂校验：`validate.mjs --unit U01` → **11/11 规则通过 / error 0 / warning 2**
  （warning 为设计内：V1 title 跳过、V10 的 F01 跨 U20 回收）。
- 内容层审读：`audit-unit.py --unit U01` → **0 项待确认**。
- V11 现含「落盘包 vs D14 内联项」结构深比较 + 「落盘包身份 vs D11」比对；
  已做反向测试（篡改落盘包 → V11 报错；恢复 → 绿）。

## 已知踩坑记录

- manifest v3 的 structure_evidence 必须包含 `ever_projected_visible` / `root_name` /
  `world_dimensions`，缺一个 preflight 会退回占位清单（inventory 只剩 1 条 `V001`）。
- 角色躯干/腿/头必须归到同一 `root_name`，否则 preflight 会把一个人拆成 3 个实体。
- 白模渲染用 Workbench 单色 + 影棚光，**不含材质**，这是预期：白模只锁时空合同。
- 提示词超预算时的合规压缩杠杆：非主体实体 `motion_contract.mode=static`（走紧凑列表）、
  主体角色标 `importance=primary`、锚点自适应稀释（保首尾，最薄 2 个）。
  **不可用**删实例的方式压预算（见硬纪律 3）。
- **D11 的 `movement` / `visual_facts` / `shot_size` 不进白模**：白模只消费 `duration_sec`
  与 `lens_mm`。改焦距会改构图意图，**禁止在 D14 白模侧单独挪主体**（＝与 D11 分叉）；
  取景旋钮在 D11 侧。

## 旧 plan 链（已归档，非生产路径）

`04_工具/handoff/` 下的旧 plan 链**不是生产路径**，现役新链已完全绕开：

| 文件 | 状态 |
|---|---|
| `make_plan.py` | **已退役**（可恢复删除，2026-10-23）。它把 D13 空间 + D11 镜头编成 `plan.json`，其 `position_m[2]` 语义判读已下沉进内容表 `zmode` 字段。 |
| `batch_build.py` | 归档。消费 `plan.json` 的批量构建器，现役链不用。 |
| `build_white_model.py` | 归档。与 `scripts/build_white_model.py` **同名不同物**，容易混；现役链用 `scripts/` 下那份。 |
| `fill_contract.py` | 归档。中文描述版单镜填装器；现役用 `scripts/fill_D14_contracts.py`（英文描述版）。 |
| `finalize_d14.py` | 归档。旧终稿编排器。 |
| `project_bounds.py` | 归档。旧包围盒工具。 |

⚠️ 归档件**只作历史参考，不得当作现役入口**：重跑它们会产出与现役链结构不同、
且与已核验 D14 不自洽的结果。`00_团队章程.md` L289 与 `00_项目索引.md` 仍记旧链，
属上游台账归口，已报企划合规处置（工具改动不越权改共享层）。
