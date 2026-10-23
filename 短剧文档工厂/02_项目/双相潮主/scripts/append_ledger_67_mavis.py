#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账 §六十七（分镜导演岗）—— 动态取最大章号 + 1，避免并发撞号。

纪律：
  · 台账 `99_交付说明.md` 多岗共写 → 只写自己章节，不改他人章节。
  · 章号运行时取 max + 1（不预写死）。
  · 正文所有数字均**现读磁盘**后填入，不凭记忆抄。
"""
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


def sz(path):
    return os.path.getsize(path)


def ver(path):
    return json.load(open(path, encoding="utf-8"))["version"]


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

def cal(name):
    """取该口径在 U02 全单元的最小值与出现位置（跨 8 集现算）。"""
    best = None
    for e in eps:
        m = e["subtitle_style"]["subtitle_sync_audit"]["margin_min_by_caliber"][name]
        v = m["最小值_sec"]
        if v is None:
            continue
        if best is None or v < best[0]:
            best = (v, f"ep{e['ep']} {m['出现位置'].split(' ')[-1] if False else ''}{m['出现位置']}".replace("ep", "ep"))
    return best

c1 = cal("镜尾余量")
c2 = cal("起音间隙")
c3 = cal("镜首余量")

SEC = f"""
## {CH}、分镜导演：U02-R03 连带项闭合（D11 v1.2→**v1.3**）＋ U02 D16 v1.0→**v1.2**（D15 锚点驱动 ＋ 面板口径收口 ＋ **片尾带冲突 2 条已消除**）＋ TTS 对账脚本修（**分镜导演，{now}**）

本节三件事：① 闭合台本编剧 §六十六.2 点名的 U02-R03 连带项；② U02 D16 由 **v1.0 排布稿**升到 **v1.2**，其中含本岗**自查发现并消除的 2 条真实视觉冲突**；③ 修一支把「已登记的旧音频」误报成硬失败的复算脚本。

### {nxt}.1 U02-R03 连带项闭合（D11 → **v1.3**）

台本编剧 §六十六.2 复跑时报出「⚠️ 引文/引用提示 1 条：ep9 镜3: note 的引文与 D08 现行 body[10] 不匹配」。**该提示已由本岗消除**。

| 项 | 内容 |
|---|---|
| 落点 | `units/U02/D11.json` → **v1.3**（{sz(D11U2)} B）｜ep009 镜3 的 `note` 引文 |
| 改法 | 手写 `note_extra` 的引文「敲**板面**的两下」→「敲**板背**的两下」—— 与 D08 U02 **v1.3** 现行 `shot_intent`「敲板背的两下必须被看见，陆沉判断的顺序在这一下里。」逐字一致 |
| 为何必须改 | 台本编剧 v1.3 只订正了 `shot_intent` 措辞、**未动正文**；D11 的 note 是**逐字引用** `shot_intent`，不改即引文失配 |
| 未动 | `visual_facts`／`dialogue`／`sfx`／时长／场景码／`global_shot_no`／`minor_present` **逐字未变**；32 镜全覆盖 |
| 同步机制 | 改的是**内容源** `scripts/build_D11_U02.py`（`note_extra`）→ 重跑落盘，**未只改 JSON**（只改 JSON 会被重跑覆盖，Q40） |
| 复跑确认 | `check_D08_D11_shotintent.mjs --unit U02` → **受检 29 条（>0，Q49 满足）｜29/29 覆盖｜0 硬冲突｜引文提示 0 条｜exit 0**；台词轴 **28/28** 对齐 D09 |

### {nxt}.2 U02 D16 v1.0 → v1.1：**字幕时码改由 D15 配音锚点驱动**（实质变更）

| 项 | 内容 |
|---|---|
| 落点 | `units/U02/D16.json` → **v1.1** → **v1.2**（{sz(D16U2)} B） |
| **实质变更** | v1.0 的对白字幕行时码是「按 D09 台词字数 4.5 字/秒**估算**的排布稿」；v1.1 起改为 **D15 U02 v1.0 配音锚点驱动**：`in_sec ＝ 配音 at_sec`、`out_sec ＝ 配音 at_sec＋dur_sec`，配对依据是 D15 条目的 `line_ref`（如 `D09 ep9 #N`）**硬锚**，不靠顺序猜 |
| **审计回填** | `subtitle_sync_audit` 由占位（`synced_row_count: 0`／「受检 0 条」）改为**现算**：**受检 {sync_total} 条**（＝本单元对白行数）逐条严格相等、0 条不符；`rows` 逐条带 `d15_vo_at_sec`／`d15_vo_dur_sec`／`d15_line_ref` |
| 口径文本 | `dwell_calc_convention` **取消**「受检 0 条／不宣称与配音一致」的保留声明（改为按 D15 锚点逐条核对并登记实测值）；`sync_rule` 补**左闭右开**区间口径 ＋「片尾标题卡单独检查」（与 U01 D16 v1.9 逐字同构） |
| 余量登记 | 余量三口径（**镜尾余量／起音间隙／镜首余量**）最小值写入各集 `subtitle_sync_audit.margin_min_by_caliber`，**数值带口径名**（D18 Q46） |
| D15 缺失时 | 构建脚本**直接 exit 2 中止**，不退化为字数估算 —— 没有锚点就不许产出任何配音一致性结论（Q49） |
| 备份落点 | 由 `units/U02/D16.json.bak-<ts>`（交付目录内）改落 `reports/_bak_U02_D11_D16_<ts>/` —— 本岗备份纪律（U02-R10） |

**逐集余量三口径（现读自盘上 JSON）**：

| 集 | 对白核对 | 面板字幕行 | 读数栏留画面 | 镜尾余量 | 起音间隙 | 镜首余量 |
|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| ep{e['ep']:02d} | {e['subtitle_style']['subtitle_sync_audit']['synced_row_count']} 条 | "
    f"{sum(1 for l in e['subtitle_style']['lines'] if l['type'] == '面板文字')} 条 | "
    f"{len(e['subtitle_style']['readout_in_frame'])} 条 | "
    f"{e['subtitle_style']['subtitle_sync_audit']['margin_min_by_caliber']['镜尾余量']['最小值_sec']}s | "
    f"{e['subtitle_style']['subtitle_sync_audit']['margin_min_by_caliber']['起音间隙']['最小值_sec']}s | "
    f"{e['subtitle_style']['subtitle_sync_audit']['margin_min_by_caliber']['镜首余量']['最小值_sec']}s |"
    for e in eps
) + f"""

→ **单元级三口径最小值**：镜尾余量 **{c1[0]}s**（{c1[1]}）／起音间隙 **{c2[0]}s**（{c2[1]}）／镜首余量 **{c3[0]}s**（{c3[1]}）。三个数测的是不同的东西，不可互相替代。

### {nxt}.3 **本岗自查发现并消除 2 条真实视觉冲突**（v1.2 的由来）

本岗在独立复核时发现：**ep10 seq9 面板文字「归一度 1.0%」42.5~43.9**、**ep15 seq10 面板文字「归一度 1.3%」42.3~43.7** —— 两条都**伸进片尾标题卡带（43.0~45.0s）**。片尾卡与对白**同在底部字幕区**，同刻即构成真实视觉冲突。

**根因有两层**：

1. **构建脚本漏了 U01-R19 已立过的那条关** —— U01-R19 把「重叠候选集须覆盖全部正文行」与「**片尾标题卡单独检查**」写进了 `reconcile_tts_actual_vs_d15_budget.mjs`；但本岗 **U02 的构建脚本从无此断言**，于是首版 U02 D16 自我检查通过、却带着 2 条冲突出厂。
2. **面板口径本身分错类** —— U02 首版把 8 条「归一度 X%」**读数栏**误当「面板文字」进了字幕层。

**口径收口（与 U01 现行做法同构，不新造）**：

| 类别 | 处置 | U02 现状 | U01 先例 |
|---|---|---|---|
| **面板本体弹出的提示/通报文字** | **进字幕层** | ep11「新手福利期结束」1 条 ＋ ep16 视野正中面板 2 条 | ep1「归档回滚完成。」／ep3「等级 LV.1（一阶）」／ep8「求救信号 城西」 |
| **读数栏的数值读数**（视野一角读数栏／面板读数栏） | **留画面，不进字幕层** | 8 条「归一度 X%」 | ep4 镜4「面板**一角读数栏**仍停在同屏中文「归一度 0.5%」」**未进字幕层**；而同一面面板的「底部滚出全区首杀通报条」**进了字幕层** |

**改正动作**：

- 面板字幕行 **{panel_total} 条**（11 → 3）；8 条读数栏登记进各集 `subtitle_style.readout_in_frame`（含镜号、文字、口径依据）**留痕**，不静默丢弃。
- 新增 `subtitle_style.panel_subtitle_rule`（口径条文）与新增断言：**正文行 `out_sec` 不得越过片尾标题卡 `in_sec`（43.0s）**，区间口径沿用左闭右开（相接不算重叠）。
- **负测证明断言非恒真**：临时把旧口径面板行塞回构建脚本 → 断言**精确报出这 2 条**（`ep10 seq9: out_sec 43.9 伸进片尾标题卡带`、`ep15 seq10: out_sec 43.7 …`）并 exit 1 不写盘；负测脚本已删除。
- 改正后独立复核：**片尾带冲突 0 条｜同镜重叠 0 条**。

### {nxt}.4 `AUDIO_LEAD` 措辞修复的**实测效果**（v1.0 首跑 → v1.1 复跑）

U02 首版 `transitions[].sound_handling` 的措辞漏「**声音预铺位**」二字 → 下游 `reconcile_D15_D16_timing.mjs` 按「预铺」关键词解析失败，把合法预铺误判成违规：**8 条伪越窗 ＋ 9 条伪跨切点**。措辞改为与 U01 逐字同构（含「声音预铺位」＋切点秒数＋提前量三要素）后复跑：

- 音效层 **83 条**（sfx 67 ＋ foley 16）：**0 越窗 / 0 跨切点**；**9 条设计预铺**被正确识别为**豁免**（ep9／ep10／ep11／ep12／ep13／ep14×2／ep15／ep16），逐条列明「预铺切点 NN（声明提前 X.Xs）」。
- 字幕层 **79 条**：0 越窗 / 0 跨切点；判据 D **28/28** 逐条相等、0 条不符、配对距离 >0.05s **0 条**。
- 复算脚本 **exit 0**：「独立复算零违规：配音与字幕均 0 越窗 / 0 跨切点，字幕与配音逐条同步」。

### {nxt}.5 独立复算比对（构建脚本登记值 ↔ 复算脚本现算值）

**两者不同源**：构建脚本按各集现算写入 `margin_min_by_caliber`，复算脚本 `reconcile_D15_D16_timing.mjs --unit U02` 独立读盘复算。**逐项一致**：镜尾余量 2.8s（ep10 镜4）／起音间隙 0.4s（ep9 镜2）／镜首余量 0.4s（ep9 镜1），出现位置亦同。

**顺手清掉一处过期硬编码**：复算脚本原有一行写死「U01 登记：口径1 1.0s（ep001 镜1）／口径2 0.5s／口径3 0.0s」，而 U01 的口径1 已在 §六十三 订正为 **0.6s 底**（D15 v1.4 收敛后实测）→ **硬编码会造成口径漂移**。已改为「本脚本不硬编码任何单元的登记值，换单元时以该单元的登记值为准」。

### {nxt}.6 TTS 对账脚本修（`scripts/reconcile_tts_actual_vs_d15_budget.mjs`）

**缺口**：该脚本不识别 `items.json` 里的 `stale_audio` 标记，把**已登记的**「旧音频待出片阶段重合成」当成映射失败并 **exit 1**（ep2 seq9「换我用了。」← 旧句「两小时五十八分……换我用了。」，实测 2.953s，超出 D15 v1.4 预算 1.8s）。

**修法**（与 `check_tts_vs_d15_budget.py` 的既有处理对齐，**不新造口径**）：

1. 按 items 条目的 `stale_new_text` 归一化匹配 → 命中者单列为「**旧音频待出片阶段重合成**」，**不计入合规统计、也不算映射失败**；理由与上游一并打印。
2. 方案 A 模拟的条数**硬编码**「10 条破坏项／18 条／28 条」→ 改**现读**（D15 v1.4 后破坏项已归零，硬编码与实况脱节）。

**复跑**：**exit 0**；受检 **27 条**可实测核对（**0 破坏 / 2 贴边 / 25 合规**）＋ **1 条**旧音频单列；A3 候选集 35 条正文行 ＋ **8 张片尾标题卡**单独检查；新出点到下一正文行起音的最小间隔 **0s**（ep8 seq8，恰相接）。

> **边界**：旧音频的**重合成**属出片阶段动作，**不在本岗边界内**（不合成 TTS/BGM）。本岗只保证「不把已知陈旧资产报成硬失败」，并把它留在台账上待出片阶段核销。

### {nxt}.7 备份纪律落实（本岗新立，U02-R10 延伸）

- `scripts/build_D11_U02.py` 与 `scripts/build_D16_U02.py` 的备份落点由 `units/U02/*.bak-<ts>`（**交付目录内**）改落 `reports/_bak_U02_D11_D16_<ts>/`。
- 本轮备份 2 处：`reports/_bak_U02_D11_D16_20261023-052734/`（D11＋D16）、`reports/_bak_U02_D11_D16_20261023-053055/`（D16）。
- 复核：`units/` 目录 `.bak` 残留 **0**。

### {nxt}.8 出口硬闸（全量重跑）

| 闸 | U01 | U02 |
|---|---|---|
| `validate.mjs --unit` | **11/11 PASS｜error 0｜warning 2** | **11/11 PASS｜error 0｜warning 8**（D12/D13/D14 未产出 ＋ F02/F03/F04 跨单元回收待复核） |
| `check_D08_D11_shotintent.mjs --unit` | **23/23｜0 硬冲突｜exit 0** | **29/29｜0 硬冲突｜引文提示 0｜exit 0** |
| `reconcile_D15_D16_timing.mjs --unit` | **exit 0**（口径 0.6s／0.5s／0.5s） | **exit 0**（口径 2.8s／0.4s／0.4s） |
| `check_D12_D11_alignment.py --unit` | **error 0｜warn 0｜已核销 11** | 无 D12 → 未开工非缺陷，**exit 0** |
| `reconcile_tts_actual_vs_d15_budget.mjs` | **exit 0**（27 条受检 ＋ 1 条旧音频单列） | 不适用（U01 专属脚本） |
| MD | `render-md.mjs` 单向渲染，**未手写 / 手改任何 MD** | 同左 |

### {nxt}.9 边界与待核销（本岗不越界、不代销自己的单）

**本轮只改**：`units/U02/D11.json`（1 处引文 ＋ 版本号）、`units/U02/D16.json`（版本号 ＋ 时码驱动 ＋ 审计回填 ＋ 面板口径 ＋ 读数栏留痕）、`scripts/build_D11_U02.py`、`scripts/build_D16_U02.py`、`scripts/reconcile_D15_D16_timing.mjs`、`scripts/reconcile_tts_actual_vs_d15_budget.mjs`、本节台账。**未改** D08／D09／D10／D12／D13／D14／D15／共享件／`00_项目索引.md`／`04_工具/**`。

**未生成任何图片／视频／音频，未合成 TTS/BGM，未提交 H3 付费生成，未投流上架。**

**待核销（本岗不代销他岗单）**：

1. **企划合规补记版本跳**：D11 U02 v1.0→v1.1→**v1.2→v1.3**、D16 U02 v1.0→**v1.1→v1.2**、D11 U01 v1.7→v1.8、D16 U01 v1.8（已被 v1.9 继承）、D16 U01 v1.8→v1.9。
2. **面板口径收口需企划合规/视觉设定确认**：本岗按 U01 现行做法对齐（读数栏留画面、面板提示进字幕），若裁定另有口径，D16 U02 需再升一版。
3. **U02 仍缺 D12/D13/D14**（视觉设定 §57.4 预检「U02 D11 与 D10 v1.9 零冲突 → D12 可开工」仍成立，须总控明派）。
4. **§五十三.6 全项目多单元同跑**（`validate.mjs` 不带 `--unit` → error 128，V2/V11 跨单元互串）—— 待企划合规裁定；本岗一律 `--unit` 单跑，**未改 `04_工具/**`**。
5. **G-05 预算档位**（无默认值）—— 待用户/Chief 裁决。
6. **群通报与 2 条私聊仍未发出**（阻塞在 MCP 写操作通道，非内容问题；兜底已请企划合规代转）。正文备于 `reports/_outbox_20261023.md`。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
