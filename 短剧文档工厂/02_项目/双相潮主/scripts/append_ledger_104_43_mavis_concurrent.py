#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_43_mavis_concurrent.py —— 故事架构：**台本编剧 11:4x 来件核销回执（六段）核销
                                     ＋ ⭐⭐ 「591／409」出处硬证（在 v1.0 备份上逐字复现）
                                     ＋ ⭐ 差额 16 的归因（钩型批次 8×2 键）
                                     ＋ 两条订正接受 ＋ 承载位锚判据
                                     ＋ ⭐ 五件套母本收口清单
                                     ＋ ⚠️ 官方闸 V9 新增 FAIL 定位（U01 D08 word_count 未回填）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
⚠️ **文件名不沿用 `append_ledger_104_NN_mavis.py` 约定** —— 该命名空间被**并发同岗实例**占用
   （见 §104.42），改用 `..._concurrent.py` 后缀以避免同名路径互覆。
用法：python3 scripts/append_ledger_104_43_mavis_concurrent.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

TEMPLATE = """__SUBHEAD__ **台本编剧 11:4x 来件核销回执（六段）＋ ⭐⭐ 「591／409」出处硬证（在 v1.0 备份上逐字复现）＋ ⭐ 差额 16 的归因（钩型批次 8×2 键）＋ 两条订正接受 ＋ 承载位锚判据 ＋ ⭐ 五件套母本收口清单 ＋ ⚠️ 官方闸 V9 新增 FAIL 定位（U01 D08 `word_count` 未回填）**｜标记 `__MARK__`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写」（对既有登记只作**追加式订正**）；Q49「受检面为空不得据以推论」；Q65 同族「非缺口判定须附承载位锚」；Q59 同型「报数须注明口径」。**复算时点 2026-10-23 12:22–12:52。**

**一、来件性质与核销方式**
- **来件**：《故事架构 → 台本编剧 · 2026-10-23 11:4x》核销回执（六段）。**该件的台账留痕见父章 §199.1–§199.8（台本编剧自写，本岗只引用、不改写）**。
- **核销方式**：按现盘独立复算，**不采信转述**；一切字面值按「版本＋字节＋sha256 前缀＋时点」**四元组**标注；每条结论附**受检面**与**受检条数**。
- **本轮结论先行**：来件对本岗的**两条订正全部成立，本岗接受**；且本岗在核销中把 **「591／409」的出处定位到具体备份文件并逐字复现**，把此前「不可复现」的成因由推测升级为**硬证**；另定位官方闸 **V9 新增 FAIL** 的根因并给出可执行处方。

**二、⭐⭐ 硬证：「591／409」＝ U03 D06＋D07 @ v1.0，在旧版备份上逐字复现**

| 文件 | 版本 | 字节 | sha256 前缀 | 标量叶 | 字符串叶 |
|---|---|---|---|---|---|
| `reports/_bak_storyarch_ep022_bone_20261023-114250/U03_D06.json` | v1.0 | 10,874 B | `b9b441d56ce30947` | **173** | **136** |
| `reports/_bak_storyarch_ep022_bone_20261023-114250/U03_D07.json` | v1.0 | 25,609 B | `e8d17b61ed8a9165` | **418** | **273** |
| **合计** | — | — | — | **591** | **409** |

- ⇒ **来件 591／409 属「U03 D06＋D07 @ v1.0」范围，可完整复现**；它**不是无据推论，也不是数字失效**。
- **现盘（12:47）对照**：U03 D06 **v1.1**｜12,137 B｜sha `08d028b6d2dfbb8d`＝标量 **189**／字符串 **152**；U03 D07 **v1.1**｜25,608 B｜sha `8be06f83a7a587f1`＝标量 **418**／字符串 **273** ⇒ 合计 **607／425**。

**三、⭐ 差额 16 的归因（递归逐键 diff，v1.0 → v1.1，非推测）**
- 对 `U03_D06.json` v1.0 与现盘 v1.1 做**全量递归逐键 diff**：**新增 16 个键位 ＝ 8 集 × 2 键**（`episodes[i].hook_type` ＋ `episodes[i].hook_type_reason`，i＝0..7）；**删除 0**；**同路径值不同 1**（仅 `version`：v1.0 → v1.1）；顶层键与集数不变（8 集）。
- ⇒ **非字符串标量叶恒为 182**（607−425 ＝ 591−409），**差额 16 全部落在字符串叶** ⇒ 成因为**「钩型标注」批次**（另有 `reports/_bak_hooktype_U03_20261023-115112/D06.json`＝10,874 B，与改写前同尺寸）。
- ⇒ **写盘方＝并发同岗实例**（已登记于 §104.42）：11:43–11:51 改写 U03 D07 v1.1、U03 D06 v1.1、U01 D06 v1.4、U01 D07 v1.3、U02 D06 v1.3。

**四、⭐ Q30 追加式订正：本岗 §104.40 的「不是版本漂移」前提已失效（原文保留，不改写）**
- **原文（保留供追溯）**：§104.40 第二节：「⇒ **八组数全部成立**；分歧点只有一个＝**统计范围**……**不是数字失效、不是版本漂移**（U03 D06 sha `b9b441d56ce30947`／D07 sha `e8d17b61ed8a9165` 至今未变）」。
- **订正（追加式）**：该括注依据的「sha 至今未变」在 **11:43–11:51 失效**（上述两项 sha 现均为 v1.1 值）⇒ **来件第①条订正成立，本岗接受**。带时点表述：**11:42 时点**「不是版本漂移」成立（当刻现盘确为 v1.0，591／409 逐字复现）；**12:47 时点**现盘已为 v1.1，591／409 **只在 v1.0 备份上**成立。
- ⚠️ **两条订正并存，不得互相顶替**：① **§199.2 认领的「591／409 在 D08＋D09 范围不可复现」**（Q49 受检面为空）——本岗 11:3x 结论**作废**，已由 §199.2 追加式订正；② **「现盘已漂」**——本节新增。⇒ **同一句话的两个否定理由都成立，但分别指向不同范围与不同时点。**

**五、八组叶子数现盘逐字复现（v1.1，时点 12:47）**

| 范围 | 标量叶 | 字符串叶 | 差（非字符串标量） |
|---|---|---|---|
| U03 **D06+D07** | **607** | **425** | 182 |
| U03 **D08+D09** | **802** | **700** | 102 |
| U03 **D08** 单件 | **513** | **473** | 40 |
| 三单元 **D08+D09** 合计 | **2299** | **1997** | 302 |
| 三单元 **D06+D07** 合计 | **1822** | **1288** | 534 |
| U02 **D06+D07** | **628** | **449** | 179 |
| U01 **D07** 单件 | **409** | **274** | 135 |
| U01 **D06** 单件 | **178** | **140** | 38 |

- ⇒ **八组全部可复现**；与来件所报逐字一致；**分歧点只剩统计范围与统计方式**（见第六节）。

**六、⭐ 条目数 vs 出现次数（双口径）—— 母本报数第 4／5 项的实测依据**

| 范围 | 词 | 命中**条目数** | 出现**次数** |
|---|---|---|---|
| U03 D08 | 骨龙 | **8** | **10** |
| U03 D08 | 影刃封路 | **2** | **3** |
| U03 D08 | **合计** | **10** | **13** |
| U03 D09 | 骨龙 | 4 | 4 |
| U03 D09 | 影刃封路 | 4 | 4 |
| U03 D09 | **合计** | **8** | **8** |
| U02 D08 | 影刃封路 | 1 | 1 |

- ⇒ **来件用「出现次数」口径、本岗此前用「条目数」口径，两数不矛盾但必须带口径报数**（同词同文件：条目 8 vs 出现 10）。
- ⇒ **全部命中位＝留痕位**：U03 D08 命中位全在 `episodes[*].compliance_notes[*]`；U03 D09 全在 `voice_cards[*].forbidden_words[*]`；U02 D08 在 `episodes[7].compliance_notes[3]` ⇒ **禁词／词形扫描的有效受检面＝字符串叶**（母本「受检叶钉为字符串叶」的再实测支持）。

**七、⭐「商既衡」逐处定位 —— 来件第②条订正（字面不精确）成立，本岗接受**
- **U03 D08 全件 1 处**：`episodes[6].compliance_notes[6]`（**留痕位**），原文「……ep023 密信**不点名任何具体反派**（含云顶财阀的实名人商既衡）」。
- **ep023 正文 body 11 段内命中 0** ✅ ⇒「ep023 正文无商既衡」成立；但「**D08 无商既衡字样**」按字面**不成立** ⇒ **来件订正成立，本岗接受并按 Q30 追加式订正原措辞（不改写其原表述）**。
- **同形异指提示（命中 ≠ 缺陷）**：**U02 D11 命中 4 处**（`episodes[3].shots[0].dialogue`／`.note`、`episodes[5].shots[0].dialogue`／`.note`）——**属台词面**，与 U03 的留痕位**不同面**；请贵岗与分镜导演**按面分类**，勿一刀切判缺陷。

**八、覆盖轴① U03 复跑（现盘 rc=0）**
- `node scripts/check_D08_D11_shotintent.mjs --project . --unit U03` → D08 **v1.5**／D11 **v1.1**／受检 shot_intent **62 条**／覆盖核验 **62/62**／**零硬冲突**／镜头语言越权 **0**／**rc=0** ✅。
- U03 D11 现值：**v1.1**｜**58,424 B**｜sha `e91b931cb2ecab08`｜12:10:00。

**九、承载位锚判据（Q65 同族）—— 已采纳并当场补齐**
- 本岗自此**不再以「已覆盖／非缺口」三字收口**；每次判定须附**承载位锚**（字面锚／角色锚 char_id／在场锚 present_characters）。本节第六、七节均按此格式给出（路径级锚已逐条列出）。

**十、⭐ 五件套母本收口清单（并入既有「受检面三类口径」议题，**不另开派单源**）**

| # | 件 | 收口内容 | 本轮实证 |
|---|---|---|---|
| 1 | **范围** | 同一名词在不同文件／单元下**必须显式写范围** | 591／409 与 607／425 分属 D06＋D07 范围且可同刻并存 |
| 2 | **口径** | 「受检叶」定义钉为**字符串叶**（标量叶另列） | 差额 182 ＝ 非字符串标量，跨版本恒定 |
| 3 | **统计方式** | 必须写**条目数 vs 出现次数** | U03 D08 骨龙：条目 **8** ／ 出现 **10** |
| 4 | **统计对象** | 必须写**受检条目数 vs 命中条数**（分母单列） | `selftest_banmian_G3_exemption.py` 报「受检 34 个交付物文件｜活跃面受检 2,031,708 字符｜命中 1」⇒ 分母与命中必须分列 |
| 5 | **时点** | 必带**版本＋字节＋sha256 前缀＋时点** | 本轮 6 次同版本号不同字节实证（§104.42） |

**十一、⚠️ 官方闸 V9 新增 FAIL 定位（12:52 实测，全项目 error 55 → 72）**
- **现值（12:52 实测）**：全项目 **33/36 通过｜error 72｜warning 12**；U01 **10/12｜e44｜w2**｜U02 **11/12｜e28｜w4**｜U03 **12/12｜e0｜w6**。
- **增量归因**：本岗 12:0x 复跑为 **34/36｜e55｜w13**；本轮 **通过规则 −1、error +17** ⇒ 全部来自**新增 FAIL「V9 字数基础档与合规增量档（U01）」**。
- **根因（现盘实测）**：**U01 D08 v1.13**（12:23:19 落盘｜37,422 B｜sha `25288745ab63ed6f`）**8 集的 `word_count` 全部声明为 0**（`base`／`compliance_add`／`total`）；U02 D08 v1.7、U03 D08 v1.5 均已正确回填实算值 ⇒ **属台本编剧单写点（D08）的未回填批次，本岗不代改**。
- **17 error 拆解（官方 `countWords` 口径：汉字数＋英文/数字单词数，标点空白不计）**：**16 条**为 `base`／`total` 声明不符（8 集 × 2）＋ **1 条**为 `ep01` 基础字数 **312 > 上限 240**（其余 7 集实算 196–231，均在 [180,240] 内）⇒ **回填后可清零 16 条，ep01 需在内容源侧压缩 ≥72 字**才能清掉第 17 条。
- ⭐ **处方（按 `rules.json` `_derived_note` 权威口径，不手改 JSON）**：`word_count` 是**派生量**，权威来源＝生成脚本 `scripts/build_D08.py` 的 `count_words()`；**D08 JSON 内的 `word_count` 禁手工改动**（手改会被重跑覆盖，且会静默逃过内容 diff）⇒ **正确改法＝改生成脚本后重跑（Q40 同型）**；`ep01` 的 312 字须在**生成脚本／内容源**侧压缩至 ≤240。

**十二、本轮闸现状（现盘复跑，OPS-18 ＋ Q102 三件套）**

| 脚本 | 规则/断言数 | 通过 | 失败 | error | rc |
|---|---|---|---|---|---|
| `check_D05_banmian_scope.py` | 15 | 15 | 0 | 0 | 0 |
| `selftest_banmian_G3_exemption.py` | 13 | 13 | 0 | 0 | 0 |
| `selftest_D05_bone_scopes.py` | 4 | 4 | 0 | 0 | 0 |
| `check_D05_lutiao_firstuse.py` | 13 | 13 | 0 | 0 | 0 |
| `check_D06_D07_roster_consistency.py --unit U03` | 受检 1,470 条 | 命中 86 | 0 | 0 | 0 |
| `check_D11_D13_camera_alignment.py --unit U01` | — | — | 0 | 0 | 0（无硬失败且无待同步项） |
| `check_D08_D11_shotintent.mjs --unit U03` | 受检 62 | 62/62 | 0 | 0 | 0 |
| 官方闸 `validate.mjs` U03 | 12/12 | 12 | 0 | 0 | 0（w6，V12 因 U03 无 `D14_shots` 跳过） |
| 官方闸 `validate.mjs` 全项目 | 33/36 | 33 | — | **72** | 1 |

- **缺件/被跳过规则（点名）**：U03 **V12 跳过**（本单元尚无 `D14_shots` 白模投影，属白模场景师后续，本岗不代做、不重复派单）；U01／U02 **V11 跳过**（缺 `D14`，同属白模场景师作业面）。
- ⚠️ **V12 红灯仍挂**（U01／U02 合计 72 error；**失败镜次 62／判据条数 103 双口径**见 §104.38）⇒ 仍待总控裁「改数据／改规则／解锁重跑」三选一，**本岗不代裁**。

**十三、本轮改动范围与边界**
- **交付物零改动**：本岗单写点八件（D04／D05／U01–U03 的 D06／D07）**一字未动**；源素材 `双相潮主/01_漫剧策划/` **只读回源**；**未改** D18／`project.json`／`00_项目索引.md`／`03_规格`／`04_工具`／**他岗章节与交付物**（含台本编剧父章 §199）。
- **本轮唯一写盘**：台账本节 ＋ 脚本 `scripts/append_ledger_104_43_mavis_concurrent.py`（文件名避开并发实例占用的 `append_ledger_104_NN_mavis.py` 命名空间）。
- **硬边界**：未生成图片/视频、未合成 TTS/BGM、未提交 H3 付费生成、未投流上架（章程 §一）。

**十四、仍挂待回复（合并去重，不逐条重派）**
- **→ 台本编剧（本轮随函回执）**：U01 D08 v1.13 `word_count` 未回填导致 V9 FAIL 17 error（**其单写点**，处方见第十一节）；U02 D11「商既衡」4 处**台词面**请按面分类。
- **→ 企划合规／总控**：⭐ **五件套母本收口清单**（第十节）｜**V12 三选一**（62／103 双口径，现 e72）｜**母本「受检面三类口径」统一**｜**「受检叶」钉为字符串叶**｜**词形治理盲区**（「溃散为灰烬光尘」等）｜**「影刃」是否立受控词条／是否引入「词干首用集」机制**｜`term_first_use` 登记「影刃封路」「骨龙」｜**本岗单写点 D05／D07 写入授权登记进 `00_团队章程.md`**｜**登记表五元组**（版本＋字节＋sha＋时点＋是否用户裁决直贯）｜**并发同岗实例编排**（多实例是否允许／单写点是否串行／脚本名是否须带实例标识／写前是否须读最新状态）｜D18 指针差集（**批次在跑，冻结前不追刷**）｜D03 B08 `eps` 区间｜概述 ep018 阶位冲突｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条落点｜口径字母母本收口＋口径D｜`audit-unit.py` 空集恒真｜**本岗 `build_D06_D07_U03.py` 内容源回填**（并发实例作业面，不争做）。
- **以上游合规裁决为准。**
"""


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
    MARK = "TBZ-11-4x-来件核销回执-591-409出处硬证-五件套-2026-10-23"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    mine = [i for i, l in enumerate(lines) if l.startswith(MY_HEADER)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    i0 = mine[0]

    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK}；未改动台账。")
        return 0

    used = set()
    for l in lines[i0:ins]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    n = max([k for (a, k) in used if a == 104], default=0) + 1
    sub_head = f"### 104.{n}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = (TEMPLATE
             .replace("__SUBHEAD__", sub_head)
             .replace("__MARK__", MARK)
             .replace("__NOW__", now))
    new_text = "\n".join(lines[:ins]) + "\n\n" + block + "\n" + "\n".join(lines[ins:])

    # A5 并发改动守卫：size/mtime/sha256 三锚
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(MARK) == 1, "A6 标记计数异常"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block.splitlines())} 行）；未写盘。")
        return 0

    bdir = os.path.join(root, "reports",
                        "_bak_ledger_104_43_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(ledp, os.path.join(bdir, "99_交付说明.md"))

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

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
    print(f"[OK] 已写入 {sub_head}（{len(block.splitlines())} 行）；台账 {snap_size} → {len(back_raw)} B；"
          f"追加点＝原第 {ins + 1} 行。落盘时间 {now}")
    print(f"[A7] 写后回读：104.1–{max(subnums)} 连续 {len(subnums)} 节（缺号 0／重号 0）；"
          f"全库 U+FFFD ＝ {back.count(chr(0xFFFD))}；标记命中 1；前段/后段逐字不变；备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
