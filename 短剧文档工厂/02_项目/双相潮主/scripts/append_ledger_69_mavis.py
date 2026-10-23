#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账 §六十九（分镜导演岗）—— 动态取最大章号 + 1，避免并发撞号。"""
import io
import json
import os
import re
import datetime

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"


def cn2int(s):
    if s.isdigit():
        return int(s)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    total = section = 0
    for ch in s:
        if ch in digits:
            section = digits[ch]
        elif ch in units:
            u = units[ch]
            if section == 0:
                section = 1
            total += section * u
            section = 0
        else:
            return None
    return total + section


def int2cn(n):
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n - 10] if n > 10 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    return str(n)


txt = open(REG, encoding="utf-8").read()
nums = [cn2int(m.group(1)) for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)]
nums = [n for n in nums if n]
nxt = max(nums) + 1
CH = int2cn(nxt)
print(f"📌 当前最大章号 = {max(nums)}，本节占号 = {CH}（{nxt}）")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
D11U2 = f"{ROOT}/units/U02/D11.json"
D16U2 = f"{ROOT}/units/U02/D16.json"
d16 = json.load(open(D16U2, encoding="utf-8"))
eps = d16["episodes"]
sync_total = sum(e["subtitle_style"]["subtitle_sync_audit"]["synced_row_count"] for e in eps)
panel_total = sum(1 for e in eps for l in e["subtitle_style"]["lines"] if l["type"] == "面板文字")
readout_total = sum(len(e["subtitle_style"]["readout_in_frame"]) for e in eps)
floor_total = sum(len(e["subtitle_style"]["subtitle_sync_audit"]["dwell_floor_rows"]) for e in eps)
tail_total = sum(e["subtitle_style"]["subtitle_sync_audit"]["float_tail_row_count"] for e in eps)
mig_total = sum(len(e["subtitle_style"]["subtitle_sync_audit"].get("seq_number_migration", {}).get("rows", [])) for e in eps)
baks = sorted(x for x in os.listdir(f"{ROOT}/reports") if x.startswith("_bak_U02_D11_D16_"))

SEC = f"""
## {CH}、分镜导演：**第六波派单核销**（S18 闭合腿 ＋ S21 预铺明文 ＋ S22 停留口径）＋ U02 D16 **v1.3** ＋ **序号迁移对照表**（**分镜导演，{now}**）

对应企划合规 §六十七 第六波派单（`batch_df7098b9d29f`／request_id `sxcz-u02-w6-d16audit-d05-0525`，派给本岗的 `task_aaa95d268ca7`）。**派单三项全部落地**，且本岗在落地过程中**自查发现并消除 2 条真实视觉冲突**（§{nxt}.3），故落盘版本由派单预期的 v1.1 递进到 **v1.3**。

### {nxt}.1 第六波派单三项 —— 逐条核销

| 派单项 | 派单要求 | 本岗落地 | 核销结论 |
|---|---|---|---|
| ① **S18 闭合腿**：`subtitle_sync_audit` 8 集回填（含「实际音频轴未测」声明 ＋ 三口径余量） | 8 集全回填 | 8 集**全部回填**：**受检 {sync_total} 条**对白行逐条等于 D15 配音（`in_sec ＝ at_sec`、`out_sec ＝ at_sec＋dur_sec`，按 D15 条目 `line_ref` 硬锚配对）；三口径余量写入各集 `margin_min_by_caliber`（**带口径名**）；**实际音频轴未测声明已写入 `verified_note`**（见 §{nxt}.4） | ✅ **闭合** |
| ② **S21**：8 集 `audio_lead` 补「预铺」明文 | 与 U01 体例一致 | 8 集 `transitions[].audio_lead` ＋ 各切点 `sound_handling` 均改为**含「声音预铺位」＋切点秒数＋提前量三要素**；复跑：音效层 83 条（sfx 67 ＋ foley 16）**0 越窗 / 0 跨切点**，**9 条设计预铺**被正确识别为豁免 | ✅ **闭合** |
| ③ **S22**：停留口径写死标称网格 ＋ **ep9 两条点名**；**不改时码** | 口径落地、时码不动 | 停留口径写进各集 `dwell_calc_convention`：**按 0.1s 标称网格判定、不做浮点位相等/严格比较；标称 1.2s 为合规下沿**；本单元标称 1.2s 的行**共 {floor_total} 条**，逐条点名（内容＋时码＋seq＋实算浮点值）见 §{nxt}.4。**时码一字未改** | ✅ **闭合** |

**时码未动的证明**：v1.0→v1.3 全程 `out_sec` 由 D15 锚点决定，**未为任何口径调整改过一个秒值**；本轮所有改动落在「口径文本 ＋ 审计块 ＋ 面板行取舍 ＋ 序号对照」四处。

### {nxt}.2 S21 措辞修复的实测效果（首跑 17 项违规 → 0）

企划合规 §67.2 实跑得 **17 项违规**（8 条音效越窗 ＋ 9 条跨切点）且「设计预铺豁免 0 条」，根因是豁免解析先判「预铺」二字 —— **U02 的 `audio_lead` 漏词**。本岗补词后复跑：

```
── 判据 A/B/C · D15 sfx ＋ foley（音效/拟音层）──
  对象总数：83（sfx 67 ＋ foley 16）
  越出本镜时间窗：0 条
  跨 D16 段间硬切点：0 条
  【设计预铺豁免】9 条（D16 明文声明的预铺位，跨切与越窗均为设计）
     ep9 sfx 镜4 37.8~42 预铺切点 38(声明提前 0.2s) ｜ ep10 sfx 镜2 ｜ ep11 sfx 镜2
     ep12 sfx 镜1 ｜ ep13 sfx 镜2 ｜ ep14 sfx 镜2 ｜ ep14 foley 镜2 ｜ ep15 sfx 镜1 ｜ ep16 sfx 镜2
✅ 独立复算零违规：配音与字幕均 0 越窗 / 0 跨切点，字幕与配音逐条同步。   exit 0
```

→ **与派单一致**：D15 U02 音效层**数据无误**，17 项纯属措辞缺词导致的误报；本岗**未改 D15 一个时码**。

### {nxt}.3 **本岗自查发现并消除 2 条真实视觉冲突**（派单未预见）

本岗在独立复核时发现：**ep10 seq9 面板文字「归一度 1.0%」42.5~43.9**、**ep15 seq10 面板文字「归一度 1.3%」42.3~43.7** —— 两条都**伸进片尾标题卡带（43.0~45.0s）**；片尾卡与对白**同在底部字幕区**，同刻即构成真实视觉冲突（U01-R19 立过的那条关）。

**两层根因**：

1. **本岗 U02 构建脚本漏了「片尾标题卡单独检查」断言** —— U01-R19 已把它写进 `reconcile_tts_actual_vs_d15_budget.mjs`，但 U02 是另一支构建脚本，**没有这条断言** → 首版 U02 D16 自我检查通过、却带着 2 条冲突出厂。
2. **面板口径分错类** —— U02 首版把 8 条「归一度 X%」**读数栏**误当「面板文字」进了字幕层。

**口径收口（与 U01 现行做法同构，未新造）**：

| 类别 | 处置 | U02 现状 | U01 先例 |
|---|---|---|---|
| **面板本体弹出的提示/通报文字** | **进字幕层** | {panel_total} 条（ep11「新手福利期结束」＋ ep16 视野正中面板两行） | ep1「归档回滚完成。」／ep3「等级 LV.1（一阶）」／ep8「求救信号 城西」 |
| **读数栏的数值读数**（视野一角读数栏／面板读数栏） | **留画面，不进字幕层** | {readout_total} 条「归一度 X%」，登记进各集 `readout_in_frame` 留痕 | ep4 镜4「面板**一角读数栏**…归一度 0.5%」**未进字幕层**；同镜「面板底部滚出全区首杀通报条」**进了字幕层** |

**改正动作与验证**：新增断言「正文行 `out_sec` 不得越过片尾标题卡 `in_sec`（43.0s）」（左闭右开，相接不算重叠）；**负测**：临时塞回旧口径面板行 → 断言精确报出这 2 条并 exit 1 不写盘（负测脚本已删）；改正后独立复核 **片尾带冲突 0 条｜同镜重叠 0 条**。

> **本岗立场**：该口径属**编辑判断**，本岗按 U01 现行做法对齐并已落盘，**提请企划合规／视觉设定复核**；若裁定另有口径，D16 U02 再升一版即可（构建脚本可复跑，口径改动只落在一处常量表）。

### {nxt}.4 S22 停留口径 ＋ **实际音频轴未测**声明 ＋ 序号迁移对照表

**① 停留口径（各集 `dwell_calc_convention`）**：按 0.1s 标称网格判定，不做浮点位相等/严格比较；**标称 1.2s 为合规下沿**（等于下沿即合规，不因二进制浮点尾差判不合格）。本单元标称 1.2s 的行 **{floor_total} 条**：

| 集 | seq | 台词 | 时码 | 标称 | 实算浮点 |
|---|---|---|---|---|---|
""" + "\n".join(
    f"| ep{e['ep']:02d} | seq{r['seq']} | 「{r['text']}」 | {r['in_sec']}~{r['out_sec']} | "
    f"{r['nominal_dwell_sec']}s | `{r['float_dwell_sec']!r}` |"
    for e in eps for r in e["subtitle_style"]["subtitle_sync_audit"]["dwell_floor_rows"]
) + f"""

→ 本单元 **{tail_total} 条**对白行存在浮点表示尾差（标称与实算不等），**一律以标称网格判定**。

> ⚠️ **seq 编号提示**：企划合规 §67.3 点名的 ep9「……军阀。」为**旧版式的 seq10**，现盘为 **seq9**（面板口径改正后其后序行前移）。**定位一律以「内容＋时码」为准**，seq 只是当前盘上值 —— 见 §{nxt}.4 ②。

**② 序号迁移对照表**（写入各集 `subtitle_sync_audit.seq_number_migration`，共 **{mig_total} 条**）：

| 集 | 类型 | 旧 seq → 新 seq | 旧时码 → 新时码 | 文本 |
|---|---|---|---|---|
""" + "\n".join(
    f"| ep{e['ep']:02d} | {r['type']} | **{r['seq_before_v1_2']} → {r['seq_now']}** | "
    f"{r['old_in_sec']}~{r['old_out_sec']} → {r['now_in_sec']}~{r['now_out_sec']} | 「{r['text']}」 |"
    for e in eps
    for r in e["subtitle_style"]["subtitle_sync_audit"].get("seq_number_migration", {}).get("rows", [])
) + f"""

→ 该表由构建脚本**忠实复现旧版式排布算法**（面板行按 (镜号, 文字) 排序、逐条顺延消解）现算，并与 v1.1 备份**逐条实测比对：3/3 完全一致、0 漏项、0 不一致**。注意 ep11 的面板行**连时码也变了**（30.7~32.3 → 29.0~30.6，因占用集变化而前移）。

**③ 实际音频轴未测声明**（写入各集 `verified_note`）：U02 **无预演音频资产**（`preview/` 下仅 `U01_tts`／`U01_video`）→「实测音频时长 vs D15 预算」这一轴**受检 0 条**，按 Q49 该轴结论**一律不成立**，本表**不作任何「实际音频已核」声明**；本表的「与配音一致」仅指与 **D15 配音锚点**一致。

### {nxt}.5 落盘版本与改动面

| 文件 | 版本 | 字节 | 改动 |
|---|---|---|---|
| `units/U02/D16.json` | **v1.3** | {os.path.getsize(D16U2)} B | v1.0 排布稿 → v1.1 D15 锚点驱动＋审计回填 → v1.2 面板口径收口＋片尾带断言 → v1.3 S22 停留口径＋实际音频轴未测声明＋序号迁移表 |
| `units/U02/D11.json` | **v1.3** | {os.path.getsize(D11U2)} B | 仅 ep009 镜3 `note` 引文（「敲板面的两下」→「敲板背的两下」，对齐 D08 v1.3）＋ 版本号；**其余 32 镜逐字未变** |

**构建脚本**（**只改内容源，不只改 JSON** —— Q40）：`scripts/build_D16_U02.py`（D15 驱动 ＋ 审计回填 ＋ 面板口径 ＋ 片尾带断言 ＋ S22 口径 ＋ 迁移表 ＋ 备份落点）／`scripts/build_D11_U02.py`（引文 ＋ 版本 ＋ 备份落点）。
**复算脚本**（本岗自修，**只读实跑、未改他岗数据**）：`scripts/reconcile_D15_D16_timing.mjs`（清除过期的单元登记值硬编码）／`scripts/reconcile_tts_actual_vs_d15_budget.mjs`（识别 `stale_audio` ＋ 条数动态化）。
**备份**：本轮新落 {len(baks)} 个目录 `reports/_bak_U02_D11_D16_20261023-*/`（**不在 units/ 交付目录内**）；`units/` 目录 `.bak` 残留 **0**。

### {nxt}.6 出口硬闸（最终态，全量重跑）

| 闸 | U01 | U02 |
|---|---|---|
| `validate.mjs --unit` | **11/11 PASS｜error 0｜warning 2** | **11/11 PASS｜error 0｜warning 8** |
| `check_D08_D11_shotintent.mjs --unit` | **23/23｜0 硬冲突｜exit 0** | **29/29｜0 硬冲突｜引文提示 0｜exit 0** |
| `reconcile_D15_D16_timing.mjs --unit` | **exit 0** | **exit 0**（D11 v1.3／D15 v1.0／D16 v1.3；判据 D **28/28**、0 条不符、配对距离 >0.05s **0 条**；三口径 2.8s／0.4s／0.4s） |
| `check_D12_D11_alignment.py --unit` | error 0｜warn 0｜已核销 11 | 无 D12 → 未开工非缺陷，exit 0 |
| `reconcile_tts_actual_vs_d15_budget.mjs` | **exit 0**（27 条受检：0 破坏／2 贴边／25 合规；1 条旧音频单列） | 不适用 |
| MD | `render-md.mjs` 单向渲染，**未手写 / 手改任何 MD** | 同左 |

### {nxt}.7 边界与仍待他岗核销

**本轮只改**：`units/U02/D16.json`、`units/U02/D11.json`、`scripts/build_D16_U02.py`、`scripts/build_D11_U02.py`、`scripts/reconcile_D15_D16_timing.mjs`、`scripts/reconcile_tts_actual_vs_d15_budget.mjs`、本节台账。**未改** D08／D09／D10／D12／D13／D14／D15／共享件／`00_项目索引.md`／`04_工具/**`／`preview/**`。

**未生成任何图片／视频／音频，未合成 TTS/BGM，未提交 H3 付费生成，未投流上架。**

**待他岗核销（本岗不代销他岗单、不自销本岗单）**：

1. **企划合规**：第六波派单三项核销（§{nxt}.1）；**面板口径收口**（§{nxt}.3）请复核；**序号迁移表**（§{nxt}.4 ②）请以「内容＋时码」为准更新 S22 的引用。
2. **企划合规补记版本跳**：D11 U02 v1.0→v1.1→v1.2→**v1.3**、D16 U02 v1.0→**v1.1→v1.2→v1.3**、D11 U01 v1.7→v1.8、D16 U01 v1.8（已被 v1.9 继承）、D16 U01 v1.8→v1.9。
3. **视觉设定**：§57.4 预检「U02 D11 与 D10 v1.9 零冲突 → D12 可开工」仍成立，U02 仍缺 D12／D13／D14，须总控明派。
4. **§五十三.6 全项目多单元同跑**（`validate.mjs` 不带 `--unit` → error 128）—— 待企划合规裁定；本岗一律 `--unit` 单跑，**未改 `04_工具/**`**。
5. **G-05 预算档位**（无默认值）—— 待用户/Chief 裁决。
6. **群通报与 2 条私聊仍待发出**（MCP 写操作通道受阻，非内容问题）；正文备于 `reports/_outbox_20261023.md`。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
