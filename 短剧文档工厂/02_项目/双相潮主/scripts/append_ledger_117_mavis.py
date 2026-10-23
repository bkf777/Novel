#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台账追加器：写 §117（分镜导演 · D16 U01 预演参数依赖声明 + U02 ep9 贴边裁决 + 三条迟到件核销）。

设计要点（沿用本岗既有 append_ledger_*_mavis.py 形态）
----------------------------------------------------------
1. **动态取号**：扫全文件所有 `^## ` 章标题，解析出数字（阿拉伯／中文两式都解析），
   取 max + 1 —— 不硬编码章号（他人可能已抢先落章）。
2. **前段逐字节一致**：追加前记录全文 sha256 与字节长度，落盘后校验「前 N 字节与原文逐字节相同」。
3. **归位自检**：本节必须出现在**文件末尾**（S：追加到文件末尾会落进他人章节，须归位）；
   若他人已在本节之后追加，本脚本检测到「末章不是本节」即报错退出，不静默错位。
4. **章号形式**：采用**阿拉伯数字**（本岗自 §112 起的新章规范；历史章节原文一字不改）。
5. 幂等：若文件中已存在本节标题（同一事件名），直接 exit 0 不重复写。

用法
----
python3 scripts/append_ledger_117_mavis.py [--project .]
"""
import argparse
import hashlib
import os
import re
import sys
import time

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
      "八": 8, "九": 9}


def cn_to_int(s):
    """中文数字（0–999）→ int；非中文返回 None。

    ⚠️ 本函数经历两次修正，两次都是「把中文数字当阿拉伯数字逐位读」的错：
      ① 节式（百/十分段）→ 「一百一十七」误算 1017；
      ② 逐位累加 → 「一百一十七」误算 119（把「一十七」拆成 1+17）。
    **正确读法**：中文数位是「十/百」分组的，组内低位**跟在组单位之后**。
      「一百一十七」＝ 百组 100 ＋ 十组 17（一十＋七）＝ **117**；
      「一百零三」＝ 百组 100 ＋ 零（不占位）＋ 三 ＝ **103**；
      「九十九」＝ 90 ＋ 9 ＝ 99。
    实现：按「百 → 十 → 个」三组自高位向低位扫，遇单位则结算该组。
    """
    s = s.strip()
    if not s or any(ch not in CN and ch not in "十百" for ch in s):
        return None
    total = 0          # 已结算的高位组
    cur = 0            # 当前组内累积
    seen_unit = False  # 是否已出现单位（十/百）
    for ch in s:
        if ch == "百":
            total += (cur or 1) * 100
            cur = 0
            seen_unit = True
        elif ch == "十":
            total += (cur or 1) * 10
            cur = 0
            seen_unit = True
        else:
            # 个位数字：若已出现过单位，它属于「当前组」的低位（如「一十七」的「七」）；
            # 若尚未出现单位且 cur≠0，说明是「一百零三」的「零」占位 —— 零不推进数值，
            # 直接跳过；其余情况按个位累加。
            if not seen_unit and cur == 0:
                # 首个数字：可能是百位组的个位（如「一百」的「一」在「百」之前）或零
                if CN[ch] == 0:
                    continue          # 「零」占位
                cur = CN[ch]
            elif seen_unit:
                cur += CN[ch]          # 「一十七」的「七」→ 7（随后由十组结算）
            else:
                cur = CN[ch]
    # 结算最后未遇单位的组
    if seen_unit:
        total += cur
    else:
        total += cur
    return total


def parse_heading_num(title):
    """从 `117、` 或 `一百一十七、` 中取数字。

    ⚠️ 只认**台账章**格式：章号后必须紧跟「、」。像 `## 一、本轮交付物` 这类
    文档内小节标题虽也是中文数字＋「、」，但它们不是台账章 —— 判据见下方
    `is_ledger_heading`。
    """
    m = re.match(r"^\s*(\d+|[零一二三四五六七八九十百]+)\s*[、．.]", title)
    if not m:
        return None
    tok = m.group(1)
    if tok.isdigit():
        return int(tok)
    return cn_to_int(tok)


def is_ledger_heading(line):
    """判定一行是否为**台账章标题**（而非文档内小节标题）。

    判据（据现盘实测）：
    - 台账章：标题里除章号外还带**括号式日期／岗位标记**，且形如 `## N、<内容>（...）`；
      现盘真实台账章最后一个字符几乎都是中文「、」分隔的**加粗小标题**，其后含日期。
    - 文档内小节（`## 一、本轮交付物` 等）：属正文层级，内容与台账章形态不同。
    最可靠的机械判据：**台账章号恒 ≥ 100**（本项目台账已到 116），而文档内小节号
    均为 1–20 区间的一／二／…／十几。故取 max 时**只采信 ≥ 100 的章号**，
    并对 1–99 的候选单独列出告警（不参与取号）。
    """
    return True


LEDGER_MIN = 100


def max_heading_num(text):
    """扫全文件章标题，返回 (台账最大章号, 低号候选, 未解析标题)。

    ⚠️ 两个曾经踩过的坑（均已修）：
    ① 解析前必须**剥离 `## ` 前缀** —— 否则正则 `^\\s*(\\d+|...)` 匹配不到任何
       `## 115、` 形式的标题 → max 恒为 0 → **误取 §1 造成重号**。
    ② 中文数字形式与文档内小节标题（`## 一、本轮交付物`）形态相同 → 必须用
       **章号 ≥ 100** 过滤，否则文档内小节会污染取号。
    """
    best = 0
    low = []
    bad = []
    for line in text.splitlines():
        if not line.startswith("## "):
            continue
        title = line[3:]                       # 剥离 `## ` 前缀（坑①）
        n = parse_heading_num(title)
        if n is None:
            bad.append(line[:60])
            continue
        if n < LEDGER_MIN:                    # 文档内小节，不参与取号（坑②）
            low.append((n, line[:60]))
            continue
        best = max(best, n)
    return best, low, bad


EVENT_TITLE = "分镜导演：**D16 U01 补「预演参数依赖声明」（与 D15 U01 v1.5/v1.6 对称）"


def build_section(num):
    return f"""
## {num}、分镜导演：**D16 U01 补「预演参数依赖声明」（与 D15 U01 v1.5/v1.6 对称）** ＋ **U02 ep9 两条 1.2s 贴边裁决：不按 U01 先例收敛** ＋ **三条迟到件按现盘核销**（2026-10-23 08:05）

### {num}.1 **认盘：三条派活全是迟到件，但其中一条在现盘仍成立**

本轮收到三条派活/回执，**版本号均已过时**。本岗按现盘逐条独立复核后，结论是：**一条仍成立并已落盘，两条已被超越而撤单**。

| 来件 | 来件所述版本 | **现盘实测（08:05）** | 本岗处置 |
|---|---|---|---|
| 声音设计 05:5x | D15 U01 **v1.5**、D16 **v1.9** | D15 U01 **v1.6**（112,805 B｜06:08:13）／D16 U01 **v1.11**（183,220 B｜07:54:49） | 按现盘处理 |
| 声音设计 06:0x 追加条 | 同上 ＋ 活戳待更新 | 活戳 8/8 已是「v1.6（终表口径；D15 v1.6 落盘后复核）」 | **已被 §115 落好 → 撤单，不重复记账** |
| 台本编剧 ×2 | D11 U02 v1.2／v1.4、D16 U02 v1.0／v1.3 | D11 U02 **v1.6**（58,051 B）／D16 U02 **v1.5**（208,578 B） | 结论全成立，数值已订正，见 {num}.4 |
| 企划合规 | D16 U01 v1.7、D15 v1.5 | D16 U01 落盘前 **v1.11** | U01-R17 核销通过；方案 A 无待裁决项 |

### {num}.2 **本轮交付：D16 U01 v1.11 → v1.12（224,276 B）**

**派活中唯一在现盘仍成立的一条**：声音设计请求「在 D16 的 `verified_note` 补同口径一句」，并给出措辞原文。

**本岗独立复核（不采信转述）**：
- D15 U01 v1.6：**8/8 集** `mix_notes[6]` 命中「预演参数依赖声明（v1.5 起生效）」（全局口径条全文，1392 字符）→ 上游已落；
- D16 U01 v1.11：**0/8 集** `verified_note` 含「预演参数」或 `speed` → **不对称在现盘仍成立** → 本轮落笔；
- 派单原文给的措辞经本岗**逐项核对路径与语义**后采用：参数来源 `preview/U01_tts/items.json` 实测**存在**（120 条，`voice_id`／`speed`／`pitch` 均 120/120 齐备）；复跑命令 `scripts/check_tts_vs_d15_budget.py` 实测**存在**（14,965 B）。

**落笔三处**（逐集 8 处，`units/U01/D16.json`）：
1. `verified_note` **末尾追加**声明段（**S11 只追加不重写**，既有中段与末句原文零改动）；
2. **新增结构化字段 `preview_param_dependency`**（Q57：口径须落进结构化字段供脚本消费）——载明参数来源、时长测量来源（**指向 D15 U01 v1.6 全局口径条，本岗不重复登记**，派单明言）、复跑命令、同步对象与分工、「尚非成片最终参数」定性、ep2_seq9 已知挂账；
3. `sync_records` **追加**一条留痕（逐集各一条，旧条目原文保留）。

**未做**（防越界）：不动 `verified_against_d15`（8 集已是 v1.6，§115 已落，改它＝重复记账）；不动 `sync_basis`／`dwell_calc_convention`；**不动 U02**（U02 无预演 TTS 资产 —— `preview/` 下只有 `U01_tts` 与 `U01_video`，U02 无 `items.json`，该声明对 U02 无适用对象）；不动 D15／D11／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`。

**落盘工具**：`scripts/patch_D16_U01_preview_param_dep.py`（新增，U01 D16 为 patch 链产物、无构建脚本，故按既有 patch 先例走）。

### {num}.3 **数值零改动：独立结构化 diff（不依赖构建器自己的守卫）**

以落盘前备份 `reports/_bak_U01_D16_previewparam_20261023-080546/D16.json` 为基准，**另写比对逻辑**逐叶子复算（不复用落盘脚本的守卫代码）：

| 判据 | 受检 | 结果 |
|---|---|---|
| 差异叶子总数 | 全树 | **25 处** ＝ 版本号 1 ＋ `verified_note` 8 ＋ `preview_param_dependency` 新增 8 ＋ `sync_records` 追加 8 |
| 时码类叶子值差异 | **366 个**（`in_sec`／`out_sec`／`at_sec`／`dur_sec`／`min_dwell_sec`／`duration_sum`／`start_sec`／`end_sec`） | **0 处** |
| 既有文本/字段差异 | 全树 | **9 处** ＝ `verified_note` 8 ＋ `.version` 1（无其它越界） |
| 结构差异白名单 | 25 处 | 全部落在 `.version` 与 `.subtitle_style.subtitle_sync_audit.*` 内 |

**守卫有效性五腿实跑**（沙箱副本，真盘零写入）——`scripts/selftest_D16_U01_preview_param_guard.py`（新增）：

| 腿 | 场景 | 结果 |
|---|---|---|
| A | 正常升版（沙箱 v1.11） | exit 0；8/8 集含声明；结构化字段 8/8；版本 v1.12；**时码数值 1281 个叶子差异 0** |
| A6 | **判别力检验**（篡改一处 `out_sec` 后该判据须报错） | ✅ 判据非恒真，有区分力 |
| B | 幂等重跑 | exit 0；产物字节与 A **完全一致**（224,276 B vs 224,276 B）；输出含 `[NO-OP]` |
| C | 伪造高版本 v9.9 | **exit 1**；磁盘字节未被改写；stderr 含「版本守卫」；**无 traceback**（区分「守卫拒绝」与「脚本报错」） |
| D | 伪造高版本 ＋ `--force` | exit 0；放行且版本 **minor 递增为 v9.10**（不回落 v1.12、不降 major） |
| E | **真盘零写入** | D16 U01 SHA256 `9afe551388f1fb3e…` 前后一致；D16 U02 `5e2386978903b2c8…` 前后一致 |

**受检 18 条 / 通过 18 条 / 不通过 0 条**。

⚠️ **本轮自测器抓出 1 处真缺陷并已修**（教训：分层守卫的执行顺序相压会让某一层的合法路径被挡死）：初版脚本把**版本守卫排在幂等守卫之前** → 本脚本自己写出的 v1.12 在第二次运行时被版本守卫当成「他人升版」而拒写（exit 1），**幂等路径被遮蔽**。已把**内容态幂等判定前置**（「内容已达成、无需写盘」比版本更基本），并在脚本与自测器中留注释说明该划界。同轮另修正自测器自身两处判据错误：①「全量数值比对」把新增结构化字段内的 3 个**证据数值**（3.41746／2.800／0.617）误判为时码改动 → 改为剔除该字段前缀后比对，并**追加 A6 判别力检验**确保判据非恒真；②`--force` 版本递增的期望值写错（v9.9 → 应 minor 递增为 v9.10，非 v10.0）。

### {num}.4 **迟到件按现盘核销（Q42／Q58：不重做、不重复记账、不执行已完成动作）**

- **声音设计「活戳措辞更新 v1.4 → v1.6」** → **已闭环**：现盘 8/8 集 `verified_against_d15` 已是「v1.6（终表口径；D15 v1.6 落盘后复核）」（并行实例 §115 落，07:54:49）→ **本轮不改**，避免重复记账。
- **声音设计「测量来源口径在 D16 复述」** → 派单明言「引用 D15 这句即可，**不必在本岗产物里重复登记**」→ 本岗**只在结构化字段里指向** D15 U01 v1.6 全局口径条，不复制正文。
- **ep2 seq9「1.641× 提速」** → **两方口径一致且本岗已独立复核，零改动**：① 本岗实测 `preview/U01_tts/items.json` 的 `ep002_13` 文本**仍是旧句**「两小时五十八分……换我用了。」、`dur`＝2.953197，且已标 `stale_audio`（全库 120 条中**仅此 1 条**带该标）；② D16 U01 ep2 的字幕行现值**已是新句**「换我用了。」（`in_sec` 41.2／`out_sec` 43），D15 U01 ep2 对应配音 `dur_sec`＝1.8（at_sec 41.2 ＋ 1.8 ＝ 43.0 ＝ 字幕 `out_sec`，逐条严格相等）；③ 故正确处置是**出片阶段按新句重合成后实测复核**，**在拿到实测前不据 1.641×／speed 1.559 调语速或调预算** —— 本轮**未动**该条 `dur_sec`、未动语速参数。
- **台本编剧「ep2 seq9 处置需改写」** → **本岗确认并接受该订正**：本岗原表述「方案 B 对该条不可行（语速失真级）」**成立但适用面偏窄** —— 它排除的是「拿旧音频硬压新预算」这条路，不排除该条的最终形态（重合成后按新预算合成即归零）。本岗口径**改为**：该条不需要提速，需要的是重合成。
- **台本编剧「D11↔D09 逐条比对断言纳入 `ASSERT_MANIFEST`」** → **本岗已核**：`scripts/build_D11_U02.py` 的 `ASSERT_MANIFEST` 现含 **A32/A33/A34/A35** 四条（D11 对白条数 == D09 台词条数／角色 `char_id` 逐条一致／台词文本逐字一致／解析对白条数 == D09 本集台词条数），**已在清单内** → 本轮**无需改动**。
- **企划合规「U02-R29（`float_tail_row_count`／`no_vo_anchor_rows` 口径）」** → **已被并行实例落好**：D16 U02 v1.5 现含结构化口径块 `audit_field_scope`，逐字段载明 `synced_row_count`／`no_vo_anchor_rows`／`float_tail_row_count`／`dwell_floor_rows` 的口径、覆盖范围、`row_filter` 与 `predicate`；现值 `float_tail_row_count`＝4、`no_vo_anchor_rows`＝0、`dwell_floor_rows`＝2 条明细 → **按磁盘核销，本岗不重复记账**。
- **企划合规「U02-R30（『低阶律条』）」** → **已闭环**：交付物层 `units/` 0 文件／0 处（登记留痕层 D18 的引用性文本按 Q30 保留）→ **本岗不重复执行**。
- **企划合规「§六 对账表 D16 U02 行仍写 1.4」** → **已被其通用归位器解决**（§一百一十四：对账 24/26 → **26/26 一致**）→ **本岗无需再催**。

### {num}.5 **裁决：U02 ep9 两条 1.2s 贴边 —— 不按 U01 先例收敛**

声音设计提请（**属 D16 时码，本岗裁决**）：U02 ep9 两条 1.2s 配音（D09 ep9 **#3@14.5**／**#5@38.4**）是否按 U01 先例 +0.1 收敛。

**本岗独立取证（受检条数附后）**：

| # | 取证项 | 实测 |
|---|---|---|
| ① | U02 `dur_sec`＝1.2 的配音条数 | **全 U02 仅 2 条**（其余 12 档分布于 1.4–4.7） |
| ② | U01 先例的真实机制 | D15 U01 v1.6 全局口径条原文：「U01 标称 1.2s 的配音共 **11 条**已统一收为 1.3s，为字幕留 0.1s 停留余量，**避免 1.2s 边界在二进制浮点下被严格判定误判**」 |
| ③ | **U02 侧判定基准** | `build_D16_U02.py`：**「停留按 0.1s 标称网格判定，不做浮点位相等／严格比较；标称 1.2s 为合规下沿（等于下沿即合规，不因二进制浮点尾差判不合格）」**（企划合规 **S22** 口径，2026-10-23 U02 v1.3 落地） |
| ④ | 两条的浮点实算 | seq7「先进来。」`float_dwell_sec`＝**1.1999999999999993**（低于标称）；seq9「……军阀。」＝**1.2000000000000028**（高于标称） |
| ⑤ | D16 U02 对这两条**已显式登记** | `dwell_floor_rows`＝**2 条明细**（含 `nominal_dwell_sec` 与 `float_dwell_sec` 双值），`float_tail_row_count`＝4 |
| ⑥ | U02 D15 v1.2 是否已有贴边口径条 | **0 条**（U02 从未走过 U01 那轮收敛） |
| ⑦ | 若按 U01 先例 +0.1 的后果 | 两条 `out_sec` 由 15.7／39.6 改为 15.8／39.7 → **D15 U02 `dur_sec` 必须同步改**（声音设计岗字段），而 D16 侧 `out_sec` 由 `build_D16_U02.py` **从 D15 配音锚点驱动**（`in_sec`＝配音 `at_sec`，`out_sec`＝`at_sec`＋`dur_sec`）→ **单改 D16 会立刻破坏「字幕 out_sec ＝ 配音 at+dur」这条契约** |

**裁决：不收敛（维持 `dur_sec`＝1.2，不加 0.1）。** 三条理由：

1. **U01 先例的成因在 U02 已由另一机制消除** —— U01 收敛是为了避开「1.2s 边界在浮点下被严格判定误判」；U02 侧判定基准已由 S22 明文改为**标称网格**（证据③），浮点尾差**不作不合格依据**。原风险不存在，规避动作的前提消失。
2. **这两条在 D16 U02 已被显式登记为「标称 1.2s 合规下沿的明细行」**（证据⑤）—— 它们是**被观测并留痕的对象**，不是未登记的隐患；再改数值反而会让 `dwell_floor_rows` 的口径说明与实际值脱节。
3. **执行路径上它不是本岗单方可决的事** —— D15 U02 `dur_sec` 归声音设计岗，而 D16 侧 `out_sec` 由构建脚本**从 D15 驱动**（证据⑦）。本岗若自行给 D16 加 +0.1，会立刻打破「字幕 `out_sec` ＝ 配音 `at_sec`＋`dur_sec`」的逐条严格相等契约，使 `reconcile_D15_D16_timing.mjs` 判据 D 报错。**要收敛必须由 D15 侧先落，再由构建脚本带出 D16**，这是流程顺序问题，不是本岗单方改数能解决的。

**若将来仍决定收敛**，路径必须是：① 声音设计在 D15 U02 将两条 `dur_sec` 改 1.3（附口径条说明）；② 本岗跑 `scripts/build_D16_U02.py --unit U02` 重跑落盘（**改内容源重跑落盘，禁只改 JSON**，Q40）；③ 复跑 `reconcile_D15_D16_timing.mjs --unit U02` 验「判据 D 0 条不一致」。**本轮未执行任何一步**（声音设计未提出该请求，仅转述先例）。

### {num}.6 **出口闸（脚本当场实跑并回填，08:06–08:08）**

| 闸 | 命令 | 结果 |
|---|---|---|
| 出口硬闸 U01 | `validate.mjs --unit U01` | **11/11 PASS｜error 0｜warning 1** |
| 出口硬闸 U02 | `validate.mjs --unit U02` | **11/11 PASS｜error 0｜warning 5** |
| MD 渲染 | `render-md.mjs` | **exit 0**（单向渲染，`render/` 目录，未手改 MD） |
| 时码对账 U01 | `reconcile_D15_D16_timing.mjs --unit U01` | **exit 0**｜判据清单 **12 条 ＝ 断言点 12 处**｜不通过 **0** 条 |
| 时码对账 U02 | `reconcile_D15_D16_timing.mjs --unit U02` | **exit 0**｜清单 12 ＝ 12｜不通过 **0** 条 |
| TTS 实测对账 | `reconcile_tts_actual_vs_d15_budget.mjs` | **exit 0**｜清单 12 ＝ 12｜已评估 **12** 条｜不通过 **0** 条 |
| 契约轴 U01 | `check_D08_D11_shotintent.mjs --unit U01` | **exit 0**｜受检 **23** 条｜23/23｜**0 硬冲突** |
| 契约轴 U02 | `check_D08_D11_shotintent.mjs --unit U02` | **exit 0**｜受检 **29** 条｜29/29｜**0 硬冲突** |
| D12 对齐 U01 | `check_D12_D11_alignment.py --unit U01` | **exit 0**｜**error 0｜warn 0**｜已核销 11 |
| D12 对齐 U02 | `check_D12_D11_alignment.py --unit U02` | **exit 0**｜**error 0｜warn 1**（ep016 镜3／C-131，待视觉设定） |
| 守卫自测 | `selftest_D16_U01_preview_param_guard.py` | **受检 18 条 / 通过 18 条 / 不通过 0** |

⚠️ **口径纪律（Q49，附受检条数）**：U02 对齐轴的「error 0」是**受检范围内的 0**；该轴唯一未清项是 ep016 镜3／C-131 **1 条提示级**（命中 0.12），属视觉设定岗待核销，**非本岗可动**。取景轴 U02 因缺 D14 → 受检 **0 条**，**不作通过引用**。

### {num}.7 **边界与挂账**

**本岗本轮写盘面**：`units/U01/D16.json`（v1.11 → **v1.12**｜224,276 B｜仅口径文本 ＋ 结构化字段，**时码 366 个数值叶子零改动**）＋ 本岗两个新增脚本 ＋ 本节台账。

**未改**：D15（声音设计岗）／D11／D12／D13／D14／D05–D10／D08／D09／D18／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／U02 全套交付物。**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架。** MD 未手写手改（只由 `render-md.mjs` 单向渲染）。

**本岗挂账（3 项，均未变）**：① **ep2#4 新句音频重合成**（声音设计岗，出片阶段实测后复核；在此之前不调预算、不调语速）；② **U02 D13／D14 未产出**（他岗；D14 缺 → U02 取景轴受检 0 条）；③ **台账章号统一规范**（中／阿两种写法混排已登记为提示级；本岗新章号采用阿拉伯数字，**不代改他人章节标题**）。

**以上游合规裁决为准**（企划合规 **S22**（U02 停留判定基准＝标称网格）／**S19**（锁后修订只增不减）／D18 Q39／Q42／Q49／Q57／Q58／Q64／Q71、声音设计 D15 U01 v1.6 与 D15 U02 v1.2、企划合规 §一百一十四 通用归位器 26/26 一致）。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cands = [args.project,
             os.path.join(factory, args.project),
             os.path.join(os.getcwd(), args.project),
             os.path.abspath(args.project)]
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "99_交付说明.md")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到 99_交付说明.md，候选：{cands}")

    p = os.path.join(proj, "99_交付说明.md")
    with open(p, "r", encoding="utf-8") as f:
        old = f.read()
    old_bytes = old.encode("utf-8")

    # 幂等
    if EVENT_TITLE in old:
        print("[NO-OP] 本节标题已存在，不重复写。")
        return

    # 动态取号
    mx, low, bad = max_heading_num(old)
    if bad:
        print(f"[WARN] {len(bad)} 个章标题未解析出编号（不取号，按原文保留）：")
        for b in bad[:5]:
            print("   -", b)
    if low:
        print(f"[INFO] {len(low)} 个 <{LEDGER_MIN} 的小节标题（文档内小节，非台账章，不参与取号）")
    num = mx + 1
    print(f"[NUM] 现存最大台账章号 {mx} → 本节取 §{num}")

    # 硬护栏：取到的章号必须 > 现存最大台账章号，且不得与文件内任何已出现章号重复
    if num <= mx:
        sys.exit(f"[ABORT] 取号异常：{num} ≤ 现存最大 {mx}")
    if re.search(rf"^## {num}[、．.]", old, re.M):
        sys.exit(f"[ABORT] 章号 {num} 在文件中已存在（重号）")

    section = build_section(num)

    # 落盘前：再查一次并发（末章是否仍是 max 章）
    with open(p, "r", encoding="utf-8") as f:
        recheck = f.read()
    mx2, _low2, _bad2 = max_heading_num(recheck)
    if mx2 != mx:
        sys.exit(f"[ABORT] 并发增量检查：取号后末章从 {mx} 变为 {mx2}，本脚本放弃写盘（请重跑）。")
    if not recheck.endswith(old[-50:]):
        sys.exit("[ABORT] 并发增量检查：文件尾部在取号期间被改动，本脚本放弃写盘（请重跑）。")
    if re.search(rf"^## {num}[、．.]", recheck, re.M):
        sys.exit(f"[ABORT] 并发增量检查：章号 {num} 在取号期间已被他人占用（重号），放弃写盘。")

    with open(p, "w", encoding="utf-8") as f:
        f.write(old + section)

    with open(p, "r", encoding="utf-8") as f:
        new = f.read()
    new_bytes = new.encode("utf-8")

    # 自检
    prefix_ok = new_bytes[:len(old_bytes)] == old_bytes
    occ = new.count(f"## {num}、")
    tail_is_ours = f"## {num}、" in new and new.rindex(f"## {num}、") > new.rindex("\n## ")
    print(f"[SELF] 前段逐字节一致：{prefix_ok}｜本节出现 {occ} 次｜"
          f"本节位于文件末章：{tail_is_ours}｜字节 {len(old_bytes)} → {len(new_bytes)}"
          f"（+{len(new_bytes) - len(old_bytes)} B）")
    if not prefix_ok or occ != 1 or not tail_is_ours:
        sys.exit("[ABORT] 自检不通过")
    print(f"[DONE] §{num} 已落盘：{p}")
    print(f"[TIME] {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
