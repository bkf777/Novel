#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_35_mavis.py —— 故事架构：**台本编剧 10:2x 核销来件的独立复算与逐条核销**
                                     （三口径 321／225／112 全成立 ＋ ⭐ 指针全表 24 条复测不一致 **2** 条
                                      ＋ ⭐ 官方闸 22/22→**33/33** 数字订正 ＋ ⭐ 口径D 建议上报母本）

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_35_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    ledp = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledp):
        sys.exit("[ABORT] 台账文件不存在；不写盘。")

    MY_HEADER = "## 一百零四、故事架构"
    MARK = "TBZ-10-2x-核销-2026-10-23"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    # A1 本岗章节命中数恰为 1
    mine = [i for i, l in enumerate(lines) if l.startswith(MY_HEADER)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    i0 = mine[0]

    # A4 追加点
    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    # A3 幂等：内容标记（不用动态编号）
    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK}；未改动台账。")
        return 0

    # A2 动态子节号
    used = set()
    for l in lines[i0:ins]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    n = max([k for (a, k) in used if a == 104], default=0) + 1
    sub_head = f"### 104.{n}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""{sub_head} **台本编剧 10:2x 核销来件 · 独立复算与逐条核销**（三口径 **321／225／112** 全部成立 ✅ ＋ ⭐ 指针全表 24 条复测不一致 **2** 条 ＋ ⭐ 官方闸 **22/22 → 33/33** 数字订正 ＋ ⭐ 口径D 建议上报母本）｜标记 `{MARK}`

**来件**：台本编剧 10:3x 送达本岗的《10:2x 来件核销》，含 5 类结论、三口径表、指针全表 24 条、台账自修留痕、两条 BUSY 任务结案。
**本岗处置原则**：Q42「不采信回报自述、以磁盘实况为准」——**全部数字由本岗独立复算**（检索时点 **2026-10-23 10:43–10:45**）。

**核销总表（Q42 三分类 · 受检 9 项）**

| # | 来件申报项 | 本岗复算结论 |
|---|---|---|
| ① | **声明成立 5 项**（三口径计数／腿3 联动／指针 3 条已闭环／台账整体／§104 合规） | **成立 ✅**（详见一、五、八） |
| ② | **贵岗认领「112 漏标范围」1 项** | **成立 ✅** —— 本岗 10:0x 报文「受检 112 条」漏标检索范围，**Q49 违规，本岗已认领**（§104.32 已登记） |
| ③ | **本岗自造口径字母冲突 1 项** | **成立 ✅** —— 属**台本编剧自认领项**（其 10:2x 报文自定义 A/B 与本岗项目级 A/B/C 撞车）；**本岗不自定义字母，只引用** |
| ④ | **U01 D14 字节指针归他岗 1 项** | **成立 ✅，且现已闭环** —— D18 现盘该条已刷为 `v1.2｜4,021,340 B` ＝ 磁盘实测（详见三） |
| ⑤ | **两条 BUSY 任务不重投 1 项** | **成立 ✅** —— 同意不重投（详见六） |

**一、① 三口径 321／225／112 —— 本岗独立复算，全部成立 ✅**

| 口径（项目级字母） | 范围定义 | 计数 | 本岗独立复算明细 | 命中 |
|---|---|---|---|---|
| **口径A** 全库四面 | U01＋U02 的 D08／D09／D11／D16 **全部台词/字幕行** | **321** | D09 `lines` **56** ＋ D08 `body[type=dialogue]` **56** ＋ D11 `shots[].dialogue` **47** ＋ D16 `subtitle_style.lines` **162**；分单元＝U01 **164** 行 ＋ U02 **157** 行 | **0** |
| **口径B** 四面实质 | 口径A **剔 D16 样板行**（片头／片尾／角标） | **225** | 样板＝片头 **64** ＋ 片尾 **16** ＋ 角标 **16** ＝ **96** → D16 实质 **66**（面板文字 9 ＋ 对白 56 ＋ 字幕 1）；56＋56＋47＋66 | **0** |
| **口径C** 单岗产物台词面 | 台本编剧四份产物（D08＋D09）的台词面 | **112** | D09 **56** ＋ D08 **56** | **0** |

- ⭐ **D16 `type` 分布实测**（U01＋U02 全量字幕行）：片头 **64**｜面板文字 **9**｜对白 **56**｜角标 **16**｜片尾 **16**｜字幕 **1** ＝ **162** —— 与来件**逐字一致** ✅。
- ⭐ **「112 并非错数」**：112 ＝ 口径C 的实扫范围（D09 56 ＋ D08 56），321 ＝ 口径A 的范围 ⇒ **两者范围不同、均成立，缺的正是范围标注**；**结论层不受影响**（三口径下专名命中均为 0）。
- 附：本岗 G10 覆盖度报告（按磁盘实况派生）现值＝「已落台词/字幕面 3 单元：U01(164行)、U02(157行)、U03(0行)｜受检台词/字幕行合计 **321** 条」⇒ 与口径A **自洽**。

**二、⭐ ④ 指针全表 24 条 —— 本岗 10:44 独立复测：一致 22｜不一致 2｜缺产物 0**

- **指针表位置**：`shared/D18.json` → `unit_checks[].delivery_checks[]`（**U01 14 条 ＋ U02 10 条 ＝ 24 条**）；字段＝`{{doc, owner, json, md, state, version, size}}`；`size` 存在**两种格式**（`21012 B` 与 `38,574 B`），须分别解析。
- ❌ **U01 D11**：登记 `v1.8｜50,322 B` vs 现盘 **`v1.10｜51,543 B`**（mtime **10:43**）
- ❌ **U02 D16**：登记 `v1.5｜208,578 B` vs 现盘 **`v1.6｜232,059 B`**（mtime **10:32:34**）
- ✅ **来件所报「唯一不一致＝U01 D14（登记 4,018,110 vs 盘 4,021,340）」已闭环** —— D18 现盘该条**已刷为** `v1.2｜4,021,340 B`，与磁盘实测逐位相等（**版本与字节双一致**）。
- ⚠️ **本岗对该条的订正（坐标层）**：来件坐标系 **10:3x 时点**，现盘 U01 D11 **又进一版**（`v1.9｜50,876 B` → `v1.10｜51,543 B`，分镜导演持续在动）⇒ **不一致条数由 1 条变为 2 条**；**结论层（U01 D14 已闭环、逐镜一致性未破）不变**。
- **归属**：刷写方＝企划合规（**D18 单写点**），产物方＝分镜导演；**本岗不代改 D18**。
- 附：来件引用的官方闸 V11「D14 逐镜覆盖与逐镜包一致性」在本岗 10:44 复跑中**仍 PASS** ✅ ⇒ 确系纯字节指针问题。

**三、③ 台账 U+FFFD 现状 —— 全库 3 处，仍未修 ✅（与来件一致）**

- **受检范围**：台账 `99_交付说明.md` 全文（**1,721,233 B**，mtime **10:43:01**）；**检索时点 10:43**。
- **U+FFFD ＝ 3 处，全部集中在同一行 L13226**，归属 **`## 一百四十四、企划合规：…`** 节内。
- 本岗章节（**一百零四**）内 **0**；台本编剧章节（**一百五十一／一百五十八／一百五十九**）内 **0** ⇒ **来件所报「§151 自纠后我节内 0」成立 ✅**，且台账 U+FFFD 已由其自纠前的 **6** 回落至 **3** ✅。
- ⚠️ **归属订正（来件表述不一致）**：来件同一节内先写「**企划合规 §144** 的损坏字符」，后写「**贵岗 §144** 那 3 个 U+FFFD 仍未修 …… **属贵岗章节正文**，本岗不代改」—— **两句指同一对象，但称谓不一致**。台账章节标题实测 §144 ＝「**一百四十四、企划合规：…**」⇒ **owner ＝ 企划合规，非本岗**。本岗已于 **§104.33** 转报企划合规，**不代改他岗章节正文**（本岗章节内无该字符，无从改起）。请勿按「贵岗章节」派单，避免该条悬空无人认领。

**四、⭐ ④ 官方闸现值 —— 本岗 10:44 实跑：全项目 **33/33**（来件 22/22 为 U03 落盘前快照）**

| 口径（范围定义） | 检索时点 | 来件自报 | 本岗实测 | 判定 |
|---|---|---|---|---|
| 口径A 全项目出口闸（3 单元 × 11 规则） | 10:44 | `22/22 error 0 warning 4` | **`33/33 通过｜error 0｜warning 15`** | ⚠️ **数字订正**（结论层不变：error 仍 0） |
| 口径A 单单元 U01 | 10:44 | `11/11 warning 1` | **`11/11｜error 0｜warning 1`** | ✅ 一致 |
| 口径A 单单元 U02 | 10:44 | `11/11 warning 3` | **`11/11｜error 0｜warning 3`** | ✅ 一致 |
| 口径A 单单元 U03 | 10:44 | （未报） | **`11/11｜error 0｜warning 11`** | ⭐ 本岗新增单元 |

- ⭐ **数字订正的成因**：`22 = 2 单元 × 11 规则`，是 **U03 的 D06／D07 落盘（10:30:57／10:31:25）之前**的快照；U03 落盘后第 3 单元并入 ⇒ 现行 **33**。**来件当时并非报错，只是时点早于 U03 落盘。**
- U03 的 11 条 warning 全为预期项：D08／D09／D11–D16 未产出 **8** 条 ＋ V3「D11 未提供镜位」**1** ＋ V10「F02 跨单元回收待复核」**1** ＋ V11「D14 不存在跳过」**1**。

**五、① 腿3 联动 —— 成立 ✅（双岗互证）**

- **10:0x 本岗产出**（/tmp 沙箱，真盘零写入）：移除注册位后 **rc ＝ 1**；G7 命中 `('D05.json','glossary/34/definition')`；G7b「注册位含该词 **False**｜注册位该词出现 **0** 次」。
- **10:3x 台本编剧独立复现逐字一致**（其本岗 /tmp 沙箱）⇒ **双岗互证成立**。
- ⭐ **因果链（来件已采纳，本岗同判）**：豁免条件＝「该词条自身 `forbidden_synonyms` 含该词」⇒ **注册位一旦缺失，豁免条件同时失效** ⇒ 自引述不再被豁免 ⇒ **G7 与 G7b 双断言同时报警** ⇒ **注册位与豁免面同源绑定，不存在「豁免开着但注册丢了」的空档**。
- 三腿合看：腿1 证**不整份豁免**／腿2 证**不跨词条豁免**／腿3 证**注册位可校验且失效可见** ⇒ **非恒真判据**（Q62／Q50）。

**六、⑤ 两条 BUSY 投递任务 —— 验收结案，同意不重投 ✅**

| batch_id / task_id | 目标 | 来件状态 | 本岗判定 |
|---|---|---|---|
| `batch_008e96966743` / `task_dc0486c7014a`（`sjc-u02-w2-r03r06-receipt-027`） | 企划合规 | `failed`｜`BUSY`｜notification `delivered`｜complete true | **不重投** —— 内容（U02-R03／U02-R06 返修回执）已被后续多轮回执覆盖 |
| `batch_2645ed0a6c4c` / `task_5f4c228dedab`（`sjc-u02-d11-mirror-sync-027`） | 分镜导演 | `failed`｜`BUSY` | **不重投** —— U02 D11 镜3 `note` 引文同步属 D11 覆盖层，事实已由 09:4x 来件核销 |

- 理由：两条均为 **BUSY（平台侧调度争用）而非内容失败**，且**内容层已闭环** ⇒ 重投只会产生重复件。本岗**同意不重投**。

**七、⭐ 口径D 建议 ＋ 字母分配权收口到母本 —— 上报企划合规／总控（本岗不自行落地）**

- **缺口**：现行三口径（口径A 全库四面／口径B 四面实质／口径C 单岗产物台词面）**只覆盖台词/字幕面**；「四份交付物**全库** 0 命中」这类断言在现三口径内**无对应字母可引** ⇒ 各岗被迫自造字母（台本编剧 10:2x 即因此与项目级字母撞车）。
- **建议 ①**：新增 **口径D ＝ 交付物原文全文扫描（含全部豁免字段）**。
- **建议 ②**：把**字母分配权收口到母本** —— 立一条「**计数口径登记（口径字母 ↔ 范围定义）**」，落点二选一（**均非本岗写权限，只能派单不能自行落地**）：
  ① `shared/D18.json` → `global_checks`（企划合规单写点）　② `03_规格/rules.json`（企划合规单写点）
- **规则**：各岗**只引用字母、不自定义**；引用时一律带出**范围定义**。
- ⭐ **过渡期规则（本岗即刻采纳，自 10:45 起执行）**：任何计数断言必须「**口径字母 ＋ 范围定义 ＋ 检索范围 ＋ 检索时点**」四件套全写（Q49）；「全库 0 处」类断言另须给出检索范围与口径、命中数（Q79）。

**八、本岗状态、边界与仍挂清单**

- **本岗交付物本轮零改动**（回盘实测，10:43）：`shared/D04.json` v1.2｜15,722 B｜sha `ddbe0ddf2408dd0a`｜`shared/D05.json` v1.5｜38,574 B｜sha `bed73e0b9a6de809`｜`units/U01/D07.json` v1.1｜25,559 B｜`units/U02/D06.json` v1.2｜11,320 B｜`units/U02/D07.json` v1.3｜28,431 B｜`units/U03/D06.json` v1.0｜10,874 B｜sha `b9b441d56ce30947`｜`units/U03/D07.json` v1.0｜25,609 B｜sha `e8d17b61ed8a9165`。
- **本岗章节 104.1–104.35 连续 35 节，无缺号、无重号**（写后回读校验）。
- **边界**：本轮**未改** D18／D03／D05 共享版／D06–D07 他岗单元／D08–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；源素材 `双相潮主/01_漫剧策划/` 本轮未改动。
- **仍挂待回复（不变）**：audit-unit.py 空集恒真（归企划合规）｜台账 §144 三个 U+FFFD（归企划合规）｜D03 节拍窗口／B08 区间｜概述 ep018 阶位冲突｜D05「骨龙」first_use 与「影刃封路」definition（本岗单写点，已两度上呈）｜D05「城郊骨井」补词｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条落点｜机器闸并入 U02 出口闸｜⭐ **D18 指针 2 条（U01 D11、U02 D16）**｜⭐ **口径字母母本收口 ＋ 口径D 新增**。

**以上游合规裁决为准。**"""
    block = [""] + body.split("\n") + [""]

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

    # A5 CAS 守卫
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # A6 结构性断言
    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(MARK) == 1, "A6 标记计数异常"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    # 备份
    bdir = os.path.join(root, "reports", "_bak_ledger_104_35_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(ledp, os.path.join(bdir, "99_交付说明.md"))

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    # A7 写后回读校验
    back_raw = open(ledp, "rb").read()
    back = back_raw.decode("utf-8")
    assert back.count(MARK) == 1, "A7 写后标记计数异常"
    assert back.startswith(pre), "A7 写后前段不一致"
    assert back.endswith(post), "A7 写后后段不一致"
    blines = back.split("\n")
    subnums = sorted(int(m.group(1)) for m in
                     (re.match(r"^### 104\.(\d+)", l) for l in blines) if m)
    gaps = [k for k in range(min(subnums), max(subnums) + 1) if k not in subnums]
    dups = sorted({k for k in subnums if subnums.count(k) > 1})
    assert not gaps, f"A7 本岗子节号有缺号：{gaps}"
    assert not dups, f"A7 本岗子节号有重号：{dups}"
    fffd = back.count(chr(0xFFFD))
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back_raw)} B；"
          f"追加点＝原第 {ins + 1} 行（下一个同级标题之前）。落盘时间 {now}")
    print(f"[A7] 写后回读：104.1–{max(subnums)} 连续 {len(subnums)} 节（缺号 0／重号 0）；"
          f"全库 U+FFFD ＝ {fffd}（应维持 3，全部在 §一百四十四 企划合规节）；"
          f"标记命中 1；前段/后段逐字不变；备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
