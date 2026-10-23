#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账脚本（视觉设定岗）｜追加 §<max+1>：派活核销闭环 ＋ 投递失败事实登记 ＋ Q87 裁定回销 ＋ 指针终态核验

取号纪律（Q85／Q86）：父章中文 ＋ 子章阿拉伯；动态取 max+1；**中文／阿拉伯两种章号形态
都解析、取数值最大者**；**全库章号可解析率必须 100%，有一条解析不了即中止不写盘（禁止静默过滤）**。
写盘：写前备份 ＋ 落笔前并发守卫 ＋ 原子写 ＋ 落盘后回读断言（重复章号归一化后为 0、不可解析为 0）。

用法：python3 scripts/append_ledger_139_visual.py [--dry-run]
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
        if v is None:
            unparsable.append((i, raw))
        else:
            rows.append((i, raw, v))
    return rows, unparsable


SEC_TMPL = """
## {parent}、视觉设定（bot_db3fd3817800）：**分镜导演「ep016 镜3／C-131」派活核销闭环** ＋ **企划合规 Q87「锁后改动」裁定的回销（选项 A 成立·不回退）** ＋ ⚠️**三条私聊投递 BUSY／AGENT_UNAVAILABLE 的事实登记与「共享台账＝有效通道」处置** ＋ **索引／D18 指针终态核验（受检 8 组）** ＋ **一处新事实错误的证伪（negatives「95 条」）** ＋ **剩余 3 项挂账（附补丁文本）**（2026-10-23 09:5x–10:0x）

### {n}.1 派活核销闭环（分镜导演）

**派活原文要求**：「ep016 镜3／C-131 判定完成后，请回一条结论（改卡 or 判为「不适用」＋理由），本岗据以把 D12↔D11 U02 的 warn 1 核销为 0，并同步台账。」

**闭环状态：已闭合（三条独立通道互相印证）**：
① **本岗判定与处置**（§一百三十六）：判定＝**真实漏写**，已按 Q40 改内容源重跑 → D12 U02 **v1.1**（md5 `b92b5dfe28574c43bbb0640d0bca4f02`）。
② **企划合规独立复验并采纳**（§一百三十七.2／.3）：**L3 复审 6/6 全过、不采信转述**，md5 与本岗所报**逐字一致**；两处改卡的定性获确认（C-131 逐字承接 D11 原词；C-105 同族体例补齐）；并按 **Q87 A 路径**对 U02 D12 v1.1 做了**锁后修订复验**登记。
③ **判据实况**：`check_D12_D11_alignment.py --unit U02` → **error 0／warn 0**（32/32 覆盖率 1.000）——**派活要求的 warn 1 在共享台账层已归零**。

### {n}.2 ⚠️ 三条私聊投递失败的事实登记与处置（**BUSY／AGENT_UNAVAILABLE**）

**本岗本轮三次 `message_bot` 投递全部报 failed**（如实登记，不粉饰）：

| 批次 | 对象 | 内容 | 终态 |
|---|---|---|---|
| `batch_2839b22657f1` | 企划合规 | 三项请裁最终回执 | **failed · BUSY**（09:31:57 起跑 → 09:32:25 失败） |
| `batch_6d49bd70a9ff` | 企划合规 | U02 落锁冲突裁定请求 | **failed · BUSY** |
| `batch_b7ce7e3717a9` | 分镜导演 | ep016 镜3／C-131 核销结论 | **failed · AGENT_UNAVAILABLE**（09:36 起跑 → 09:40 失败） |

**但内容已全部抵达对方 —— 抵达路径不是私聊，而是共享台账**：
企划合规 §一百三十七.2 的标题即「**裁定视觉设定 §136.7 的二选一**」→ 其**明确引用本岗台账章节号**并据此裁定 Q87；其 §137.3 的 md5「与视觉设定所报**逐字一致**」亦说明比对对象是**共享台账与磁盘产物**。
⇒ **判定：私聊投递链在本时段不可靠；共享台账（`99_交付说明.md` ＋ `shared/D18.json`）才是各岗实读的有效通道**（各岗直接读盘，不经 bot 投递链）。

**本岗处置（与既有纪律一致）**：
① 所有交付事实（判定依据、证据链、处置与回退路径）**已写进台账**（§一百三十六）→ 裁定与核销均在共享 SSOT 留痕，不依赖任何一条私聊是否送达；
② **不改已落盘的 D12 v1.1**（企划合规已按 Q87 A 路径追认，**回退路径需用户／Chief 拍板**，非本岗可自决）；
③ 向分镜导演**补投一条短回条**（新 request_id），正文只作「结论已在 §一百三十六／§一百三十七 留痕」的指针，**不再重发长文**——避免通道再断时重复消耗；
④ **本节即为该回条的台账副本**：即使补投再失败，本岗的结论与证据仍在本节可查（**投递失败 ≠ 交付失败**）。

### {n}.3 企划合规 **Q87** 裁定的回销（**选项 A 成立，本岗无异议**）

**其裁定要点**（§一百三十七.2）：判据＝「**锁后修订 ≠ 重落锁**；以『真实缺陷 × 生产后果』为准，不以『锁的时点洁癖』为准」；**A 路径**＝补做 L3 人工审读 → D18 追加式记复验结论与新指纹 → `delivery_checks` 指针刷新 → 索引 §六 指针刷新 → `lock_conditions` 维持 pass；**`locked_at`／`locked_by`／`lock_state` 一律不重写**（沿用 U01 先例：锁后修订只增不减）；**B 路径（回退已修缺陷）才需用户／Chief 拍板**。

**本岗回销**：**选项 A 成立，本岗无异议**（判据与本岗 §一百三十六.7 提交的事实链同向；本岗提交的是「保留修正＋两个可一键执行的上游选项」，未自决、未改 `lock_state`、未改索引）。**D12 U02 v1.1 维持现状，不回退。**

**本岗侧独立复核（不采信转述）**：企划合规所报 md5 `b92b5dfe28574c43bbb0640d0bca4f02`（101,788 B／v1.1）与本岗所报**逐字一致**；L3 六项本岗侧亦全过 —— 卡↔D11 **1:1（32↔32）**／卡级必填 **8/8**／多余字段 **0**／`negatives` 空 **0**／`image_prompt` 焦距↔D11 `lens_mm` 不符 **0**／场景码↔D13 双向差集 **0**。

**时序事实（备核）**：派单述「D16 U02 已升 **v1.4**」，而落锁 L1 取证为 **D16 v1.5** → **派单成文早于 08:43 落锁**，执行时撞上已锁交付物。

### {n}.4 索引／D18 指针终态核验（**受检 8 组**，09:5x 实跑）

| # | 项 | 归属 | 现值（实测） | 判定 |
|---|---|---|---|---|
| 1 | 索引 §六 **D10 行**版本指针 | 企划合规 | **v1.11｜31,842 B｜08:32 落** | ✅ 已归位（§137.5 指针全刷） |
| 2 | 索引 §六 **D12（U02）行** | 企划合规 | **v1.1｜101,788 B｜09:17:34 落（09:3x 锁后修订复验通过，按 Q87，locked_at 仍 08:43 不重写）** | ✅ 已归位 |
| 3 | D18 `delivery_checks` U02 D12 | 企划合规 | `version`→v1.1／`size`→101,788 B／`state` 追加复验留痕 | ✅ 已归位（§137.10） |
| 4 | D18 `unit_checks[U02]` | 企划合规 | `lock_state=locked`／`locked_at=08:43`／L3.detail 追加式 | ✅ 已归位（Q87 A 路径） |
| 5 | 索引 §五 **视觉设定格** · U01 D10 版本/字节 | 企划合规 | 仍写「U01 D10 **v1.9（31,091 B）**」 | ❌ **仍待归位**（现 v1.11｜31,842 B） |
| 6 | 索引 §五 **视觉设定格** · negatives「**8 组 95 条**」 | 企划合规 | 仍写 95 条 | ❌ **事实错误（非旧版计数）**——见 §{n}.5 |
| 7 | 索引 §五 **视觉设定格** · U02 D12 | 企划合规 | 仍写「U02 D12 **v1.0（101,713 B／06:38）… `status=in_review` 待审读**」 | ❌ **仍待归位**（现 v1.1／已审读通过） |
| 8 | D18 `global_checks` 池下放口径／豁免说明／非血腥语义 | 本岗请登记 | **各 0 命中** | ❌ **本岗 D10 池下放口径未进 D18 登记**；且落点差异**全库无裁定**（见 §{n}.6） |

⇒ **受检 8 组：已归位 4／仍待归位 3／未登记 1**（第 8 项含两个子诉求）。

### {n}.5 一处新事实错误的证伪：**negatives「95 条」从来就不对**

本岗 §一百二十二.7 第 ② 项原写「『negatives 95 条全英文（8 组共 95 条）』→ **95 疑为旧版计数**，建议按盘核对后更新」——**本轮按盘核对后，「疑为旧版计数」这一表述被证伪**：

**实测**：以 v1.9 时期的备份 `reports/_bak_D10_v110_pool_exemption_20261023/D10.json.bak`（**version v1.9**）读取 → `negatives` **46 条**；现行 v1.11 亦 **46 条**。
⇒ **95 不是「旧版计数」，而是自 D10 收窄 negatives 之后就一直是错的**（§一百二十二.7 的措辞已按本节订正，Q30：本岗章节留痕不改写，**此处只作追加式订正**）。

**现值口径（建议直接采用）**：`negatives` **46 条**（全英文；D10 v1.9／v1.10／v1.11 三版**均 46**，自 v1.9 起未变）。

### {n}.6 剩余 3 项挂账（仍归企划合规，附补丁文本）

**① 索引 §五 视觉设定格 —— 三处归位（企划合规单点维护，本岗不代改）**

| 位置 | 现值 | 建议改为 |
|---|---|---|
| §五 视觉设定格 | 「**U01 D10 v1.9（31,091 B）**已审读通过（**negatives 8 组 95 条**全英文…」） | 「**U01 D10 v1.11（31,842 B）**已审读通过（**negatives 46 条**全英文…」） |
| §五 视觉设定格 | 「🔄 **U02 D12 v1.0（101,713 B／32 卡／06:38）已落盘，`status=in_review` 待审读**」 | 「✅ **U02 D12 v1.1（101,788 B／32 卡／09:17 落）已审读通过**（Q87 锁后修订复验通过，`locked_at` 仍 08:43 不重写）」 |
| §五 视觉设定格 | 无 D10 落点说明 | 补记「**豁免说明落 D10 `consistency_rules[17]`**（v1.10→v1.11）＋ 落点理由：D12 schema 无合法注记位，池的 owner 落池的定义处」 |

**② 落点差异仍无裁定（D18 `global_checks` 0 命中，全库无任何裁定期）** —— 请企划合规就 §一百二十二.2 的落点差异给一句结论：
- **本岗所提落点**＝`shared/D10.json` 的 `consistency_rules[17]`（v1.10→v1.11），理由：① **D12 装不下注记**（`03_规格/schema.json` 的 D12 顶层与 `cards[].items` 均 `additionalProperties: false`，无任何合法注记字段）② 共享池定义在 D10，豁免是「本池怎么用」的口径 ③ D10 `consistency_rules` 已有同体例（`[14]` 人物锚点闭合＝V7 的 D10 侧对应、`[16]` 净火照射范围＝ep010 镜头级约束）。
- **须一并补 D18 登记**：本岗的「非血腥语义条目须单元覆盖」口径目前只在本岗脚本 `verify_D12_independent.py` 的 **H9／H9b** 中机械实现，**D18 `global_checks` 内 0 命中** → 建议登记为一条 global_check（判据可机械复跑、负测已备）。
- **补强事实（供裁定参考）**：该口径的机械实现已随本岗 D12 v1.1 在 U02 侧实跑（受检 3,052 条断言 error 0）并有负测（抽掉 `real-world national flags` × 9 处 → H9 精确点名报错）→ **它已是可复跑的守卫，不只是文字规则**。

**③ U01 侧 3 条共享池缺项是否开返修单** —— 仍无裁定。按 D10 v1.11「适用范围」句：`net fire illuminating more than a small contact patch of skin` 是 **v1.9 才进池**、U01 D12 v1.5 成卡更早 → **不构成 U01 缺漏**；`religious processions`／`candle-lit shrines` 为本岗扩 RELIG 组后新增的逐卡下放项，U01 未回溯。**U01 D12 v1.5 已被 Q61 锁定，本岗不擅改** → 请裁定是否开返修单。

### {n}.7 出口闸终态复跑（对当前磁盘，09:5x 实跑）

| 闸 | 结果 |
|---|---|
| `validate.mjs` 全项目 | **22/22 通过｜error 0｜warning 4** |
| `validate.mjs --unit U01` | **11/11｜error 0｜warning 1** |
| `validate.mjs --unit U02` | **11/11｜error 0｜warning 3** |
| `check_D12_D11_alignment.py --unit U02` | **error 0／warn 0**（32/32 覆盖率 1.000） |
| `check_D12_D11_alignment.py --unit U01` | **error 0／warn 0／已核销 11** |
| `verify_D12_independent.py --unit U02` | **受检 3,052 条断言｜error 0｜warning 0** |
| `verify_D12_independent.py --unit U01` | **受检 2,583 条｜error 0｜warning 4**（适用性告警，零误报） |
| `build_D12.py --unit U02 --check-only` | **exit 0**（32 卡／negatives 894 条／最长 image 324／video 182／单卡正文 ≤1,131） |
| 交付物指纹 | D12 U02 **v1.1｜101,788 B｜md5 `b92b5dfe28574c43bbb0640d0bca4f02`**（本轮**零改动**）｜D10 **v1.11｜31,842 B｜negatives 46 条**（本轮**零改动**） |
| 台账归一化 | 标题 **137**（本节写入前）／max **138**／**重复 0**／**不可解析 0** |
| D18 | **v1.98**（企划合规 09:38 落；`global_checks` 88 条／`open_issues` 100 条） |

### {n}.8 边界

- **本岗本轮写盘面＝本台账一节 ＋ 本岗脚本 `scripts/append_ledger_139_visual.py`** —— **交付物 JSON 零改动**（D12 U02 v1.1／D10 v1.11 维持 §一百三十六 终态，未因投递失败而回退）。
- **未改** D08／D09／D11／D16／D15／D13／D14／D05／D06／D07／D10／D12／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／`project.json`；**未代改任何他岗台账章节正文**（§七·九 单写者纪律）。
- 派单与投递：**三次私聊投递均报 failed 的事实已如实登记**（§{n}.2），**不把「受理话术」当完成**；交付以**共享台账 + 磁盘产物**为准。
- MD 未手写／手改；**未生成任何图片／视频／音频；未合成 TTS／BGM；未提交 H3 付费生成；未投流上架**。
- **以上游合规裁决为准**（S7／S19–S25、D18 Q30–Q62／**Q85／Q86／Q87／Q88**、章程 §三·五 单元锁四条件、企划合规 2026-10-23 08:43 落锁与 09:14 Q85 裁定、企划合规 §一百三十七 Q87 A 路径裁定与 L3 复验 6/6）。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for attempt in range(5):
        base = open(REG, encoding="utf-8").read()
        rows, unp = chapters(base)
        if unp:
            raise SystemExit("❌ Q86 硬要求：全库章号可解析率须 100%%，当前 %d 条不可解析 %r → 中止不写盘"
                             % (len(unp), unp))
        vals = [v for _, _, v in rows]
        maxnum = max(vals)
        nxt = maxnum + 1
        parent = int2cn(nxt)
        assert cn2int(parent) == nxt, "int2cn 往返断言失败"
        sec = SEC_TMPL.replace("{parent}", parent).replace("{n}", str(nxt))
        print("=== 取号（Q85/Q86）===")
        print("  标题 %d｜max %d｜不可解析 0 ✅" % (len(rows), maxnum))
        print("  本节占号 = §%s（%d）" % (parent, nxt))
        if args.dry_run:
            print("🔍 --dry-run：未写盘")
            return 0

        now = open(REG, encoding="utf-8").read()
        if now != base:
            print("⚠️ 落笔前检测到文件已被他人改动 → 重算取号重来")
            continue

        bak_dir = os.path.join(ROOT, "reports",
                               "_bak_LEDGER_%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))

        out = base.rstrip("\n") + "\n" + sec.lstrip("\n")
        tmp = REG + ".tmp.%d" % os.getpid()
        st = os.stat(REG)
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(out)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, REG)

        after = open(REG, encoding="utf-8").read()
        rows2, unp2 = chapters(after)
        vals2 = [v for _, _, v in rows2]
        dup2 = {v: vals2.count(v) for v in set(vals2) if vals2.count(v) > 1}
        assert dup2 == {}, "❌ 落盘后重复章号 %r" % dup2
        assert unp2 == [], "❌ 落盘后不可解析章号 %r" % unp2
        assert ("## %s、视觉设定（bot_db3fd3817800）" % parent) in after
        print("=== 落盘后回读断言 ===")
        print("  标题 %d｜重复 %r｜不可解析 %d ✅" % (len(rows2), dup2 or "无", len(unp2)))
        print("  备份 → %s" % os.path.relpath(bak_dir, ROOT))
        print("  ✅ 新章 §%s（%d）已追加" % (parent, nxt))
        return 0

    print("❌ 连续 5 轮并发冲突，未写盘")
    return 2


if __name__ == "__main__":
    sys.exit(main())
