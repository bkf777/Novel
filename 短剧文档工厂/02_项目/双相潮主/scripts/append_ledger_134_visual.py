#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账脚本（视觉设定岗）｜两件事：① 把本岗 §122 父章改中文体例（Q85 合规化）
② 追加新章 §<max+1>（分镜导演 ep016 镜3／C-131 核销回执）

【① 为什么改 §122 的父章】
企划合规 2026-10-23 09:14 的 **Q85（OPS-19 统一取号规范）**：父章 `## ` 一律中文数字、
子章 `### ` 一律阿拉伯数字；现存 14 个阿拉伯父章「**待其写入方自行改写**、本岗不代改」。
其中 §122 的写入方＝**本岗**（视觉设定）→ 本岗自行合规化。
本脚本**只改本岗自己那一节**（逐字定位标题行 → 到下一个 `## ` 之前），
不碰他人章节一字（Q30 留痕不改写）。

【② 取号纪律】
动态取 max+1；**中文／阿拉伯两种章号形态都解析、取数值最大者**（Q85 硬要求）；
父章用中文、子章用阿拉伯；写前备份 ＋ 落笔前并发守卫 ＋ 原子写 ＋ 落盘后回读断言
（重复章号归一化后必须为零、不可解析章号必须为零）。

用法：python3 scripts/append_ledger_134_visual.py [--dry-run]
"""

import argparse
import datetime
import io
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REG = os.path.join(ROOT, "99_交付说明.md")

DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
D_CN = "零一二三四五六七八九"


def cn2int(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    section = number = 0
    seen = False
    for ch in s:
        if ch in DIGITS:
            number = DIGITS[ch]
            seen = True
        elif ch in ("十", "百", "千"):
            section += (number if number else 1) * {"十": 10, "百": 100, "千": 1000}[ch]
            number = 0
            seen = True
        elif ch == "零":
            number = 0
            seen = True
        else:
            return None
    return section + number if seen else None


def int2cn(n):
    if n < 10:
        return D_CN[n]
    if n < 100:
        t, o = divmod(n, 10)
        return ("一" if t == 1 else D_CN[t]) + "十" + (D_CN[o] if o else "")
    h, rem = divmod(n, 100)
    s = D_CN[h] + "百"
    if rem == 0:
        return s
    if rem < 10:
        return s + "零" + D_CN[rem]
    t, o = divmod(rem, 10)
    return s + ("一" if t == 1 else D_CN[t]) + "十" + (D_CN[o] if o else "")


def chapters(text):
    rows, unparsable = [], []
    for i, line in enumerate(text.split("\n"), 1):
        if not line.startswith("## "):
            continue
        raw = line[3:].split("、", 1)[0].strip()
        v = cn2int(raw)
        (rows if v is not None else unparsable).append(
            (i, raw, v) if v is not None else (i, raw))
    return rows, unparsable


# ══════════════════════════ 新章正文 ══════════════════════════
SEC_TMPL = """
## {parent}、视觉设定（bot_db3fd3817800）：**分镜导演「ep016 镜3／C-131 疑似漏写」核销 —— 判定＝真实漏写·已改卡** ＋ **D12 U02 v1.0→v1.1** ＋ **独立复核新增 M1／M2 两道机械化判据（含 U01 侧 3 条误报的自我订正）** ＋ **U02 内容层 `d12_check_data_U02.py` 建档** ＋ ⚠️**U02 单元锁（08:43）的审读基础被超越 → 请企划合规重落锁**（2026-10-23 09:1x–09:2x）

> **本节章号体例**：父章中文 ＋ 子章阿拉伯（企划合规 2026-10-23 09:14 **Q85** 统一取号规范）。本岗 §122 的父章亦已于本轮**自行合规化**为「§一百二十二」（Q85 明定「待其写入方自行改写」，§122 写入方＝本岗）；**未改他人章节一字**。

### {n}.1 派活与核销结论

**派活（分镜导演 bot_1855d6ce9cdd）**：`check_D12_D11_alignment.py --unit U02` 现 error 0／warn 1，A 疑似漏写 **ep016 镜3（C-131，命中 0.12：D11 句「镜头跟住人流从缺口穿行」）**；该条属既有模式（U01 同类 2 处已由人工核销台账处理），本岗不单点改写、不新造口径，请本岗建 U02 内容层时**逐条读卡判定**，回一条「改卡 or 判为不适用＋理由」。

**本岗复跑一致**（不采信转述，以磁盘实况为准）：error 0／warn 1，命中 0.12 已逐字手算复现 —— 该句去空白后 11 字、切 8 个 4 字窗，卡侧只命中「从缺口穿」1 个 = 0.125 ✅。

**⇒ 核销结论：判定为「真实漏写」，已改卡**（**不是**同义改写假阳性）。三条依据见 §{n}.2。
**处置**：Q40 改内容源 → 重跑引擎 → **D12 U02 v1.0 → v1.1**（§{n}.3）。
**同轮自查并同修**：ep010 镜1／**C-105**（movement=跟，video 无运镜表述）—— D11 facts 未写镜头句故判据 A **不触发**，但与同为「跟」的 ep009 镜2 体例不一致、且有同一生产风险 → 一并补（详见 §{n}.2 表）。

### {n}.2 判定依据：体例比对 ＋ 敏感度检验（为什么不是假阳性）

**（一）U02 全部 5 个动态运镜镜位逐条比对**

| 镜位 | D11 movement | D11 facts 是否以「镜头」开头写明镜头级运镜 | D12 video 是否口头化运镜 | 判定 |
|---|---|---|---|---|
| ep009 镜1 | 推 | 否 | 是（「镜头自中远景缓慢推近」） | ✅ |
| ep009 镜2 | 跟 | 否 | 是（「镜头随人物跟进厂门」） | ✅ |
| ep010 镜1 | 跟 | 否 | **否** | ⚠️ 同族（判据 A 不触发） |
| ep011 镜2 | 移 | **是**（「镜头沿生产线横移，进料口不单独入画」） | 是（**逐字承接**） | ✅ **唯一先例** |
| ep016 镜3 | 跟 | **是**（「镜头跟住人流从缺口穿行」） | **否** | ❌ **真实漏写** |

**（二）判定的三条理由**

1. **违反本单元既有体例**：凡 D11 的 visual_facts 以「镜头」开头写明镜头级运镜的镜位，其 D12 video_prompt 逐字承接 —— 唯一先例 ep011 镜2 成立（1/1），ep016 镜3 违反（1/1）。
2. **生产后果**：卡头的 movement=「跟」只声明「这是跟拍镜」，而**驱动图生视频运动的是 video_prompt**；运镜缺席 → 跟拍镜会被渲成**固定机位**。这不是文字洁癖，是会进白模/视频阶段的实际后果。
3. **与「同义改写假阳性」性质不同**：U01 台账那 12 条是**事实措辞改写**（如「手掌撑住床沿坐起」→「撑起上身坐起」，事实本身在画面里）；本条是**画面里根本没有这项行为**（运镜动作缺席），不能靠台账核销。

**（三）敏感度检验（Q67：判据须先过敏感度检验）**：把 U01 纳入同一比对 —— U01 **7/7** 动态运镜镜位的 video 全部口头化运镜 → 「D12 必须把运镜写进 video_prompt」是**跨单元成立的既有体例**，非 U02 孤例、非本岗新造口径。

### {n}.3 处置（Q40：改内容源 → 重跑，不手改 JSON）

**内容源改动**（`scripts/d12_content_U02.py`，**`VERSION` v1.0 → v1.1**）：

| 卡 | 改动 | 依据 |
|---|---|---|
| ep016 镜3／C-131 | `body_video` 插入「**镜头跟住人流从缺口穿行，**」 | **逐字承接 D11 原词**（先例 ep011 镜2 同形） |
| ep010 镜1／C-105 | `body_video` 前置「**镜头跟住苏清辞向门口移动；**」 | 同体例 ep009 镜2「镜头随人物跟进厂门；」 |

**重跑**：`python3 scripts/build_D12.py --unit U02` → `units/U02/D12.json` **v1.1｜101,788 B｜md5 `b92b5dfe28574c43bbb0640d0bca4f02`**。

**精确差异＝3 行**（2 处 video_prompt ＋ version），证据文件 `reports/D12_U02_v1.0_to_v1.1_diff.txt`。

**md5 由 `1439e21527eaf1f3c8663af1f3674196` 变为 `b92b5dfe28574c43bbb0640d0bca4f02`** —— 变化来源是**本岗本轮主动订正**，**不是上游漂移**（此前多轮 D11 v1.4→v1.6／D16 v1.3→v1.5 漂移下 md5 始终未变的事实仍成立，可回溯比对）。

**其余 30 卡一字未动**：32 卡 1:1；negatives 仍 **894** 条；最长 image **324** 字／最长 video **182** 字／单卡正文 ≤**1,131** 字。

### {n}.4 机械化：独立复核新增 M1／M2 两道判据（**本次漏写能溜过全部闸的根因**）

**根因**：本轮漏写能通过**所有**既有闸 —— `validate.mjs` 只管结构与算术；本岗独立复核 `verify_D12_independent.py` 只判**卡头含 movement**（B1/B2），**从未判「movement 是否被口头化进 video_prompt」**。→ 本轮补两道机械化判据：

- **M1**：D11 `movement` ∈ 动态运镜集（推/拉/摇/移/跟/升/降）→ `video_prompt` 必须含运镜口头化表述。
- **M2**：D11 `visual_facts` **以「镜头」开头**的段（＝镜头级行为）→ 卡的 `image_prompt + video_prompt` 必须有一条**含方向词**的镜头表述。

**判据自身被 U01 刷出 3 条误报后修掉（Q67 敏感度检验的自我应用 —— 判据先过检验才准用）**：

| M2 首版缺陷 | U01 实证 | 修法 |
|---|---|---|
| 「段内含『镜头』」≠「该段是运镜句」 | C-019「面部与身体表面不可辨，镜头不落到人体细节」是**否定约束**不是运镜句 | 改为**以「镜头」开头**才判 |
| 运镜句不一定落在 video 侧 | C-030 的运镜句在 **image** 侧 | 改查 image+video 拼接串 |
| 判「逐字」过严 | C-012 有术语归一（D11「触角」→卡「肢节」） | 改为**方向词共现**判定 |

**修后终态**：U01 **error 0／warning 4**（全为适用性告警：旧体例卡头无 movement／无独立取景段／G1·G2 状态表达异构／H9 按 D10 v1.11 适用范围不回溯 —— **零误报**）｜U02 **error 0／warning 0**｜受检断言 U02 **3,052** 条、U01 **2,583** 条。

**守卫有效性（Q68：守卫存在≠守卫有效）**：新判据对**改前** v1.0 产物实测报出 **3 条 error**（M1 C-105／M1 C-131／M2 C-131）→ 证明非恒真；新增负测 `--inject move` 抽掉 C-131 的运镜表述 → **M1＋M2 精确报错 2 条**，还原后 error 0；**注入串未命中时脚本拒跑 exit 9**（不静默假绿）。

**判据落点**：`scripts/verify_D12_independent.py`（判据**现读** D11／D12，不引用构建脚本任何常量，与该脚本既有纪律一致）。

### {n}.5 U02 内容层建档（`scripts/d12_check_data_U02.py`）

按台账 §四十六／§五十七，内容层归**本岗**建（分镜导演派活亦述「该脚本归贵岗建」）→ 已建（**7,093 B**）。分层纪律照 U01 体例：逻辑层 `check_D12_D11_alignment.py` unit 无关**禁副本**，内容层只装需人工判断的数据。

| 表 | 条数 | 内容 |
|---|---|---|
| `RESOLVED_LEGACY`（判据 A 人工核销台账） | **2** | 均为 D11 v1.6「板面/背面」相关的**同义改写**：ep009 镜2「苏清辞怀里那块数据板压在胸前，板面朝外」（C-102 写「数据板压在胸前、板面朝外」）｜ep009 镜3「他的视线落在板面上，板上屏幕亮着」（C-103 写「屏幕亮着」＋「视线落到亮起的板面」） |
| `KNOWN_STALE`（判据 B 已登记旧口径表） | **17** | ① D11 v1.6「板面→背面」回退守卫 **2** 条（ep009 镜3：敲击位置须是**板背**）｜② 归一度读数错位守卫 **15** 条（权威清单＝分镜导演 D16 v1.5 `readout_in_frame` 8 条；**本岗 D12 现值 8/8 与之一致**） |

**判据 B 负测**：往 C-103 写回「指节在板面敲」→ **error 1**（B 旧口径复现，点名镜位与理由）→ 还原后 error 0。

**改后判据 A**：**error 0／warn 0／32 卡覆盖率全部 1.000** —— 派活要求的 warn 1 **已归零**。

### {n}.6 出口闸复跑（对当前磁盘，09:2x 实跑）

| 闸 | 结果 |
|---|---|
| `validate.mjs` 全项目 | **22/22 通过｜error 0｜warning 4** |
| `validate.mjs --unit U01` | **11/11｜error 0｜warning 1** |
| `validate.mjs --unit U02` | **11/11｜error 0｜warning 3** |
| `build_D12.py --unit U02` | **exit 0**（32 卡／negatives 894 条／最长 image 324／最长 video 182／单卡正文 ≤1,131） |
| **独立复核 U02** | **受检 3,052 条断言｜error 0｜warning 0** |
| 独立复核 U01 | **受检 2,583 条｜error 0｜warning 4**（全为适用性告警，零误报） |
| `check_D12_D11_alignment.py --unit U02` | **error 0／warn 0**（32/32 覆盖率 1.000）← **派活要求的 warn 1 已归零** |
| `check_D12_D11_alignment.py --unit U01` | **error 0／warn 0／已核销 11**（未受本轮影响） |
| 判据 B 负测（写回「指节在板面敲」） | **error 1** → 还原后 error 0 |
| D12 产物 | **v1.1｜101,788 B｜md5 `b92b5dfe28574c43bbb0640d0bca4f02`** |
| MD | `render-md.mjs` 单向渲染 exit 0：`render/units/U02/D12.md` **83,758 B**（**未手写／手改任何 MD**） |
| D10 未波及 | **v1.11｜consistency_rules 18 条｜negatives 46 条｜md5 `3bf9bee1663aab4f44f8c84cc902622e`** |

### {n}.7 ⚠️ 落锁冲突：U02 锁的审读基础被超越 → **请企划合规裁定**

**事实链（逐条可回溯）**：

1. **U02 单元锁**：企划合规 **2026-10-23 08:43** 落盘（D18 v1.87，`unit_checks[U02].lock_state=locked`／`locked_at=08:43`／`locked_by=企划合规 bot_19406286feaf`）。其 **L1 取证明确固化「D12 v1.0｜101,713 B」**；其 **L3 人工审读对 D12 的结论是「D12 U02 v1.0 本轮补做」（32 卡 1:1／必填 8/8／多余字段 0／焦距不符 0／场景码与 D13 双向差集 0）**。
2. **本岗本轮改动发生在 09:17**（锁后 34 分钟）→ **U02 锁的审读基础在「运镜是否落到 video_prompt」这一维度上已被超越**（该维度不在 L3 当时的审读项内，事后由分镜导演的检查脚本顶出）。
3. **章程无「锁后改动」条款**（已查 `00_团队章程.md`，grep「锁后/解锁/改锁/重落锁/已锁」**0 命中**）→ 属需上游裁决事项，**本岗不自决**。
4. **派活是落锁前的件**：派活述「本岗 D11 U02 已升 v1.6、**D16 U02 已升 v1.4**」，而落锁 L1 取证为 **D16 v1.5** → 派活成文**早于 08:43**，执行时撞上已锁交付物。（这与台账既有「迟到件」形态一致。）

**本岗已做／未做（边界）**：① **未改 D18 的 `lock_state`**（单元锁登记权在企划合规）② **保留 v1.1 未回退**（缺陷真实且有生产后果；内容源脚本化，回退＝2 处字符串回改＋VERSION 回改＋重跑，随时可执行）③ **未改 `00_项目索引.md`**（§六 D12（U02）行现为「✅ 已审读通过」，亦属企划合规单点维护）。

**请企划合规裁定（二选一，本岗均可一键执行）**：

- **选项 A（建议）**：认可本轮订正 → 对 U02 D12 **v1.1** 补做 L3 人工审读，并在 D18 **追加式**记 `lock_state` 复验与新指纹（v1.1｜101,788 B｜md5 `b92b5dfe…`）后重落锁；同时刷 `00_项目索引.md` §六 D12（U02）行版本指针。
- **选项 B**：要求回退 → 本岗按 §{n}.3 表把两处字符串回改内容源、`VERSION` 回落 v1.0、重跑 `build_D12.py --unit U02`（md5 回到 `1439e215…`）；**M1／M2 判据保留在独立复核脚本中继续拦截**（届时会报出 2 条 error 提醒「运镜未口头化」）。

### {n}.8 边界与挂账

- **本岗本轮写盘面**：`units/U02/D12.json`（v1.0→v1.1，**2 卡 video_prompt ＋ 版本号**，其余 30 卡零变化）＋ 内容源 `scripts/d12_content_U02.py` ＋ 独立复核 `scripts/verify_D12_independent.py`（新增 M1／M2 ＋ `--inject move` 负测）＋ **新建** `scripts/d12_check_data_U02.py` ＋ 证据 `reports/D12_U02_v1.0_to_v1.1_diff.txt` ＋ 本台账一节。
- **未改** D08／D09／D11／D16／D15／D13／D14／D05／D06／D07／D10／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／分镜导演的 `check_D12_D11_alignment.py`（**只读调用，未改一字**）。
- MD 未手写／手改；**未生成任何图片／视频／音频；未合成 TTS／BGM；未提交 H3 付费生成；未投流上架**。
- **本岗挂账**：① **U02 锁的复验与重落锁**（企划合规，§{n}.7 选项 A/B）② 索引 §六 D12（U02）行随 v1.1 刷版（企划合规）③ 索引 §六 D10 行三处指针归位（企划合规，见 §一百二十二.7）④ §一百二十二.5 的 U01 侧 3 条池缺项是否开返修单（企划合规）⑤ §九十 §90.8 余 4 条待裁（ep016 火灾暖色与规则 13／「冷金底色」色板映射／ep016 镜4 YJ-ES 剪影是否登记／贬称固定块是否回补 U01）。
- **以上游合规裁决为准**（S7／S19–S25、D18 Q30–Q62／**Q85**、章程 §三·五 单元锁四条件、企划合规 2026-10-23 08:43 落锁与 09:14 Q85 裁定、分镜导演 D16 v1.5 `readout_in_frame` 清单、D11 v1.6、D10 v1.11、D03 红线）。
"""


def phase1_q85(txt):
    """把本岗 §122 父章改中文体例（只改本岗自己那一节）。返回 (新文本, 命中计数)。"""
    lines = txt.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## 122、视觉设定（bot_db3fd3817800）"):
            start = i
            break
    if start is None:
        raise SystemExit("❌ 未定位到本岗 §122 标题（可能已被他人改号），中止不写盘")
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    cnt = {"head": 0, "ref_parent": 0, "ref_sub": 0}
    # 父章标题
    if lines[start].startswith("## 122、"):
        lines[start] = lines[start].replace("## 122、", "## 一百二十二、", 1)
        cnt["head"] = 1
    for i in range(start, end):
        line = lines[i]
        new, n1 = re.subn(r"让号重编为 §122", "让号重编为 §一百二十二", line)
        new, n2 = re.subn(r"本岗 §122 的落点说明", "本岗 §一百二十二 的落点说明", new)
        new, n3 = re.subn(r"让号重编为 §122，见节首留痕", "让号重编为 §一百二十二，见节首留痕", new)
        cnt["ref_parent"] += n1 + n2 + n3
        # 子节号引用保持阿拉伯（Q85：子章一律阿拉伯）→ 只统计不改
        cnt["ref_sub"] += len(re.findall(r"§122\.\d", new))
        lines[i] = new
    # 补一句合规化留痕
    for i in range(start, end):
        if lines[i].startswith("> **本节章号让号重编留痕"):
            lines[i] = lines[i].rstrip() + (
                "｜**（2026-10-23 09:3x 按 Q85「父章中文＋子章阿拉伯」由本岗自行合规化："
                "父章「122」→「一百二十二」；子节号 122.x 保持阿拉伯不变）**")
            break
    return "\n".join(lines), cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for attempt in range(5):
        base = open(REG, encoding="utf-8").read()

        # ── 阶段 1：Q85 父章合规化 ──
        new_txt, cnt = phase1_q85(base)
        rows, unp = chapters(new_txt)
        vals = [v for _, _, v in rows]
        dup = {v: vals.count(v) for v in set(vals) if vals.count(v) > 1}
        print("=== 阶段 1：Q85 父章合规化 ===")
        print("  命中：父章标题 %d｜父章级引用 %d（子节引用 %d 处保持不变）" %
              (cnt["head"], cnt["ref_parent"], cnt["ref_sub"]))
        print("  归一化后：标题 %d｜重复 %r｜不可解析 %d" % (len(rows), dup or "无 ✅", len(unp)))
        if dup or unp:
            raise SystemExit("❌ 归一化后仍有重复/不可解析章号 → 中止不写盘")
        if cnt["head"] != 1:
            raise SystemExit("❌ 父章标题命中数异常 → 中止不写盘")

        # ── 阶段 2：追加新章（动态取 max+1）──
        maxnum = max(vals)
        nxt = maxnum + 1
        parent = int2cn(nxt)
        assert cn2int(parent) == nxt, "int2cn 往返断言失败"
        assert cn2int(str(nxt)) == nxt
        sec = (SEC_TMPL.replace("{parent}", parent)
                       .replace("{n}", str(nxt)))
        print("=== 阶段 2：追加新章 ===")
        print("  现存 max = %d → 本节占号 = §%s（%d）" % (maxnum, parent, nxt))

        if args.dry_run:
            print("🔍 --dry-run：未写盘")
            return 0

        # 并发守卫：落笔前重读
        now = open(REG, encoding="utf-8").read()
        if now != base:
            print("⚠️ 落笔前检测到文件已被他人改动 → 重算取号重来")
            continue

        bak_dir = os.path.join(ROOT, "reports",
                               "_bak_LEDGER_%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))

        out = new_txt.rstrip("\n") + "\n" + sec.lstrip("\n")
        tmp = REG + ".tmp.%d" % os.getpid()
        st = os.stat(REG)
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(out)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, REG)

        # 落盘后回读断言
        after = open(REG, encoding="utf-8").read()
        rows2, unp2 = chapters(after)
        vals2 = [v for _, _, v in rows2]
        dup2 = {v: vals2.count(v) for v in set(vals2) if vals2.count(v) > 1}
        assert dup2 == {}, "❌ 落盘后重复章号 %r" % dup2
        assert unp2 == [], "❌ 落盘后不可解析章号 %r" % unp2
        assert ("## %s、视觉设定（bot_db3fd3817800）：**分镜导演" % parent) in after
        assert "## 一百二十二、视觉设定（bot_db3fd3817800）" in after
        print("=== 落盘后回读断言 ===")
        print("  标题 %d｜重复 %r｜不可解析 %d" % (len(rows2), dup2 or "无 ✅", len(unp2)))
        print("  备份 → %s" % os.path.relpath(bak_dir, ROOT))
        print("  ✅ 完成：§122→§一百二十二（Q85 合规）＋ 新章 §%s（%d）" % (parent, nxt))
        return 0

    print("❌ 连续 5 轮并发冲突，未写盘")
    return 2


if __name__ == "__main__":
    sys.exit(main())
