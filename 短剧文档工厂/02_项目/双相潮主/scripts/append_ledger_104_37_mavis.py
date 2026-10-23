#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_37_mavis.py —— 故事架构：**声音设计 10:4x 回执⑤ 闭环（本岗自闸 G3/G7 漏检修复 ＋ 两项判据边界裁定
                                     ＋ 负测 13 腿全绿）＋ 台本编剧 10:5x 复销核销（9 项一致 ＋ 5 处状态更正）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_37_mavis.py --project 02_项目/双相潮主 [--dry-run]
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
    MARK = "TBZ-10-5x-banmian-修复-台本编剧复销-2026-10-23"

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
    body = f"""{sub_head} **声音设计 10:4x 回执⑤ 闭环（本岗自闸 G3/G7 漏检修复 ＋ 两项判据边界裁定 ＋ 负测 13 腿全绿）＋ 台本编剧 10:5x 复销核销（9 项一致 ＋ 5 处状态更正）**｜标记 `{MARK}`

**本节处置原则**：Q42「不采信回报自述、以磁盘实况为准」——**全部数字由本岗独立复算**（复算时点 **2026-10-23 11:02–11:30**）；**判据放宽/改边界必须配负测**（Q62）；**豁免精确到子树、不整份排除**。

**一、声音设计 10:4x 回执⑤ —— 本岗三项处置（裁定 ×2 ＋ 漏检修复）**

**（1）裁定①：`sync_records` 纳入留痕面（精确到该子树，不豁免父键）**
- **实际结构**（本岗实读）：`episodes[].subtitle_style.subtitle_sync_audit.sync_records`，**D16 U01 ep0 len=3／U02 ep0 len=1**；字段＝`date` ＋ `event` ＋ `basis`（事件溯源）＋ `interval_rule` ＋ `rows`（old→new 时码对照）＋ `changes`（逐版本变更记录，**逐字引述旧写法**）。
- **裁定理由**：① 语义同族（记录「改了什么」而非「现在是什么」）；② 现状**无雷**（除已豁免的 8 处外「板面」命中全为 0）⇒ 纳入豁免**不掩盖现存违规**；③ 不纳入则将来一次「板面→板背」同步会在 `changes` 里逐字写下旧写法 ⇒ **重演今天这次假红**。
- ⚠️ **豁免精确到 `sync_records` 这一层**，**不豁免父键 `subtitle_sync_audit`**（父键下还有 `d16_out_matches_contract` 等活跃字段必须照查；实测父键有 **12 个兄弟键**）。

**（2）裁定②：`gaps_resolved` ＋ `decisions` 纳入登记台账语境（精确到 `project.json` 两个子树）**
- **实测结构**：`project.json` 顶层键 **12 个**；`decisions`＝dict **68 条**（值全为 str＝裁定正文字符串）｜`gaps_resolved`＝list **25 条**（元素键＝`id`／`gap`／`resolution`／`status`／`decided_by`）。
- **命中分布（本岗实读定位）**：「低阶律条」**3 处**＝`decisions/S31_术语首用集机器闸与律条四层锚点落地裁定`、`decisions/S32_G12双条目合并裁定与迟到回执核销口径`、`gaps_resolved/22/resolution`；「板面」**8 处**（含 G25 登记引述）⇒ 两者都是**逐字引述被裁定的旧写法或被裁词条本身**，与 D18 的 `open_issues`／`global_checks` 同性质 ⇒ 登记语境。
- **裁定**：按登记台账语境豁免这两个子树，**不整份排除 `project.json`**（`project`／`source_of_truth`／`terminology`／`characters`／`units`／`files` 等仍是活跃面）。
- ⭐ **豁免面按文件名精确到 `project.json`**（取证：**31 份交付物中 0 处**出现 `gaps_resolved`／`decisions` 键 ⇒ 豁免面**不触及任何交付物内容**；将来若某交付物引入同名键，本闸**仍照查不豁免**，负测腿10 锁死这一条）。

**（3）⭐ 本岗自闸缺陷修复：受检面硬编码单元名单 ⇒ U03 漏检（自证并修复）**
- **缺陷**（本岗自认）：`scan_files` 原硬编码 `("shared","units/U01","units/U02")` ⇒ **U03 的 2 份交付物完全不在受检面** ⇒ 对 G3／G7 **两条规则同时无感**（声音设计以沙箱注入实测确证：向 U03 D07 注入违规，闸仍「命中 0｜全绿｜exit 0」）。
- **方向说明**：这是**漏检（漏报）**，与同轮修掉的假红（误报）**方向相反**；两者**同源**（都是受检面定义没跟着产线走）。
- **修复**：① `scan_files` 改**遍历 `units/*` 全部单元目录**（不硬编码）；② 新增 **G3c 覆盖度自证断言**（受检交付物数 == 磁盘实况，**漏扫 0／多扫 0**）⇒ **防再犯**（不可能再悄悄漏掉下一个单元）；③ 另加独立于 `scan_files` 的 `delivery_inventory()` 盘点，两种算法必须一致。
- ⚠️ **代价透明**：新增单元进受检面后若报出旧写法，属**既有数据的真实状态**、不是新缺陷；「**命中 ≠ 缺陷**」，须按「同形异指」逐处分类（引述/登记留痕 vs 活跃违规）。

**二、⭐ G7 判据第四次精确化（与 G3 统一到同一活跃面）—— 负测腿7a 失败定位与修复**
- **触发**：负测腿7a（`project.json` 进受检面时其 `gaps_resolved` 内既有引述不得触发）**rc=1**；逐条拆断言后定位：**G3 已是绿的**（登记台账豁免 **1 个**｜命中 **0**）⇒ 失败来自**另一条断言 G7**。
- **根因**：**G3 走结构化遍历（吃留痕/登记豁免），G7 走原文全文计数（不吃任何豁免）** ⇒ 二者活跃面不一致 ⇒ `project.json` 的登记台账引述在 G7 上必然命中 ⇒ **G7 恒红**（沙箱实测：G7 命中 1｜`project.json` 3 处）。
- **修复**：**G7 改为结构化遍历**，与 G3 共用留痕子树 ＋ 登记台账子树豁免；另保留 D05 侧两项既有豁免（`forbidden_synonyms` 注册位 ＋ 词条自身 `definition` 自引述），**G7 语义不变、只是换了取文本的方式**。
- ⭐ **G3 判据保持不动**：「板面」**不在**任何词条的 `forbidden_synonyms`（唯一注册位是 `glossary[律条].forbidden_synonyms` 里的「低阶律条」）⇒ G3 **无注册位可豁免** ⇒ 不动它，避免无负测支撑的判据放宽（Q62）。
- ⚠️ **已知边界（G7 登记台账豁免的语义边界）**：登记语境按「如实引述」豁免 ⇒ 若将来出现「**把被裁的违规写法登记为现行口径**」的记录，本闸不会拦；**触发条件**＝出现此类记录 ⇒ 须由企划合规/总控**显式裁决**后再收口豁免面或改判据。

**三、负测 13 腿全绿（Q62；腿形 == 真盘真实落盘形态；`/tmp` 沙箱、真盘零写入）**
- **规模**：由 3 腿扩到 **13 条断言腿**（G3 侧八腿 ＋ G7 侧三腿 ＋ 两自证）；每腿**独立沙箱**，互不污染。
- **实跑结果（11:2x）**：**13 腿｜通过 13｜失败 0**。
- 腿0 **夹具基线自证**（沙箱交付物文件集与 sha256 与真盘逐份全等，含 U03）｜腿1 基线放行（G3/G3b/G3c 全绿 ＋ 覆盖单元含 U03）｜腿2 活跃面注入必拦（U02 D16 字幕行）｜腿3 `d15_version_history` 注入放行｜腿4 ⭐ **U03 漏检自证**（向 U03 D07 ep0 `story_time` 注入必拦 —— **直接锁死「不得硬编码单元名单」**）｜腿5 ⭐ `sync_records` 注入放行｜腿6 ⭐ 父键兄弟键 `verified_note` 注入必拦（证豁免精确到子树）｜腿7a ⭐ `project.json gaps_resolved` 登记语境放行（rc=0｜登记台账豁免 2 个｜命中 0）｜腿7b ⭐ `project.json project.title` 注入必拦（证不整份排除）｜腿8 ⭐ **G7 登记语境放行**（`project.json → decisions` 注入「低阶律条」⇒ G7 ✅）｜腿9 ⭐ **G7 同文件兄弟键必拦**（`project.json → source_of_truth` 注入 ⇒ G7 ❌）｜腿10 ⭐ **G7 豁免不外溢到交付物**（交付物内 `decisions` 键注入 ⇒ G7 ❌）｜**真盘零写入**（`units/U02/D16.json`／`units/U03/D07.json`／`project.json` 三份 sha256 前后全等）。

**四、全闸回归与官方闸现状（11:2x 实跑；含 V12 状态更正）**

| 闸 | 结果 | 口径／范围／时点 |
|---|---|---|
| 本岗 banmian 自闸 | **断言 15｜通过 15｜失败 0** | G3 受检文件 **33**（＝31 交付物 ＋ 2 源素材 json：`setting_db.json`／`story_spine.json`）｜活跃面受检 **1,802,848 字符**｜留痕子树豁免 **24** 个（`d15_version_history` **8** ＋ `sync_records` **16**）｜登记台账豁免 **0**｜命中 **0**｜时点 11:2x |
| G3c 覆盖度自证 | ✅ | 磁盘交付物 **31** 份（`shared` 去 D18 **7** ＋ `units/*` **22**）｜受检 **31**｜漏扫 **0**｜多扫 **0**｜覆盖单元 `['U01','U02','U03']` |
| G7 | ✅ | 受检 **33** 个文件｜活跃面受检 **1,802,443 字符**｜留痕豁免 **24**｜登记台账豁免 **0**｜注册位豁免 **42**｜命中 **0**｜注册位自引述豁免 **1** 处 |
| 本岗负测 | **13 腿｜通过 13｜失败 0** | 见第三节；真盘零写入已校验 |
| 本岗 lutiao naming | **10/10** | 已落台词/字幕面 3 单元：U01(165 行)／U02(157 行)／U03(50 行)｜受检台词/字幕行合计 **372** 条 |
| 本岗 lutiao firstuse | **13/13** | D05「律条」首用锚点回读 |
| 本岗 roster | ✅ | U01 受检 **1,498** 条命中 **93**；U03 受检 **1,470** 条命中 **86**（口径：姓名精确匹配，存在别名/称号/代称盲区，PASS 只缩小人工审读范围，不得当作内容合格依据） |
| 幂等 | ✅ | `build_D06_D07_U03.py`＝[IDEMPOTENT]｜`patch_source_ep020_xinhuocheng.py`＝[IDEMPOTENT]｜`patch_D05_firstuse_shadow_bone.py`＝[IDEMPOTENT]（**幂等判据改锚词条现值**，见第六节） |
| **官方闸 全项目** | **34/36｜error 62｜warning 20** | 11:2x 实跑；**U01 30 error／U02 32 error／U03 0 error**；**红灯按规则归类只有 V12**（白模构图一致性） |
| 官方闸 U03 | **12/12｜error 0｜warning 10** | 本岗单元（U01／U02 为 11/11＋V12＝12/12，本岗单元 U03 无 D11→V12 跳过提示） |

- ⚠️ **V12 红灯状态更正（相对来件快照）**：V12 红灯**仍未解**（62 error），归属与裁法不变（**改数据／改规则／解锁重跑**三选一，裁决权＝企划合规/总控；产物方＝白模场景师 `D14_shots/*/projection.json`，对端＝分镜导演 D11 `shot_size`，规则与锁态＝企划合规）；`rules.mjs` V12 规则 mtime＝**10:51:40** ⇒ **新规撞存量数据**（D14 投影 mtime：U01 10:08:20／U02 08:32:28，均早于规则）。**本岗不代改 `04_工具/*`／`03_规格/*`／D11／D13／D14。**

**五、台本编剧 10:5x 复销核销（9 项一致 ✅ ＋ 5 处状态更正 ＋ 两条 D05 冲突已闭环）**
- **逐条核销**（本岗现盘独立复算，时点 11:2x）：① 三口径 321／225／112 —— 属 §104.35 已复算项，**结论不变** ✅；② 指针全表 24 条 —— 属 §104.35 已复算项，**不一致 2 条坐标不变** ✅；③ 官方闸 —— **数字已过期**（见第六节状态更正③）；④ 台账 U+FFFD —— **已归零**（见状态更正②）；⑤ 腿3 双岗互证 ✅；⑥ 两条 BUSY 不重投 ✅；⑦ §104 合规 —— 本岗现为 **104.1–104.36 连续 36 节、缺号 0／重号 0**（本岗 10:57 落 §104.36 后）✅；⑧ 口径D ＋ 字母分配权收口已转母本 ✅；⑨ 七项交付物指纹 —— **5 项一致、2 项已变**（见状态更正①）。
- ⭐ **来件第六节「D05 两条首用集/definition 冲突待贵岗裁」—— 本岗答复：已闭环，贵岗可开写**：
  - 影刃封路 `first_use_ep` **37 → 36**（源《逐集内容概述》ep036 字面首现；原值疑取「斩叶家族长」beat 〔B13〕标记集 ep037 ⇒ **beat 锚点 ≠ 词形首现集**）；
  - 骨龙贯穿／骨龙威压 **17 → 26**（源 ep026〔B09〕「三纹破境，黑白双生骨龙威震全场」；原值疑为「骨威」首现集 ep017 串位；「骨威」是**另一词形**、不在本词条范围）；
  - **definition 已同步写入首用口径**（因 `D05.md` 渲染表**不渲染 `first_use_ep`**，首用集口径须写进 `definition` 才可人工审读）：三层＝① 词形首用集（台词面/字幕面自 ep036 起）② 形态规约自 ep016 起适用（禁写面与首用集**正交、始终生效**）③ **形态可先于定名出现**（画面描述面不受词形首用集约束，沿用「律条」先例「机制先、名字晚」）。
  - ⇒ **U03 D08 v1.0（ep017–024）可直接照「骨威」＋ 36/26 口径落，不必再等裁**；母本机器口径（`rules.json` `_term_first_use_note`）：首用集**只查台词面与字幕面，画面描述面不查** ⇒ 存量「影刃封路」**14 处全在画面描述面** ⇒ **零回改**。

**六、⚠️ 现状更正（三处状态漂移 ＋ 外部写入登记）**

**（更正①）七项指纹：5 项一致 ＋ 2 项已变（来件报的是 10:4x/10:5x 快照）**

| 产物 | 来件报（10:4x 快照） | 本岗现盘（11:2x） | 判定 |
|---|---|---|---|
| D04 | v1.2／15,722 B／sha `ddbe0ddf2408dd0a` | 同 | ✅ 一致 |
| D05 | v1.5／38,574 B／sha `bed73e0b9a6de809` | **v1.7／41,166 B／sha `b4cfa4b40020d526`** | ⚠️ **已被写入**（见下） |
| U01 D07 | v1.1／25,559 B | **v1.2／25,580 B／sha `4e669b387244d02b`** | ⚠️ **已被写入**（见下） |
| U02 D06 | v1.2／11,320 B | 同 | ✅ 一致 |
| U02 D07 | v1.3／28,431 B | 同 | ✅ 一致 |
| U03 D06 | v1.0／10,874 B／sha `b9b441d56ce30947` | 同 | ✅ 一致 |
| U03 D07 | v1.0／25,609 B／sha `e8d17b61ed8a9165` | 同 | ✅ 一致 |

**（更正②）台账 U+FFFD：由 3 → 0** —— 本岗 11:2x 现盘实测 **U+FFFD ＝ 0**（全库）⇒ 企划合规 §一百四十四 三个损坏字符**已修**（owner 侧闭环）⇒ **该条从本岗待回复清单移除，不再挂**；台账现 **2,010,260 B｜175 个二级标题**（他岗并发追加中，行号与字节数随时漂移，引用前须回盘重取）。

**（更正③）官方闸：由 33/33｜e0｜w15 → 34/36｜e62｜w20** —— 成因见第四节（V12 新规撞存量数据，**与本岗本轮改动无关**）；本岗单元 U03 仍 **12/12｜e0｜w10**。

**（外部写入登记 ⚠️）本岗单写点 D05／U01 D07 出现并发写入**
- `shared/D05.json`：本岗 **10:54:51** 落 v1.6（40,625 B｜sha `0088a44796b63c0c`）→ **11:03:46 他岗写入 v1.7**（41,166 B｜sha `b4cfa4b40020d526`），新增三处**「骨纹未激活态」口径**（`glossary[16].definition`＝骨纹自 ep001 可见但未激活、ep003 首次亮起并显示 0.5%；`motifs[1].desc`；`power_system.gauge_readings[0].event`）；⭐ **本岗两条首用集订正（影刃封路=36／骨龙=26 ＋ definition 首用口径）完整保留**（结构化 diff 逐路径核过：无删改、无新增路径、仅 8 处路径值变）。
- `units/U01/D07.json`：本岗 v1.1（25,559 B）→ **11:03:46**「golden3s_ep001」批次写入 v1.2 → **11:24:22**「retime_ep001」批次再次写入（备份目录 `reports/_bak_golden3s_ep001_20261023-110346/`、`reports/_bak_retime_ep001_20261023-112422/`）；⭐ **11:24–11:26 之间版本号出现 v1.2 → v1.3 → v1.2 抖动**（本岗两次读盘实测，中间态已不可复现）⇒ **本岗单写点存在并发写入**。
- **内容侧影响（本岗 v1.1 → 现盘 v1.2 结构化 diff）**：**唯一实质差异**＝`episodes/0/quad_segments/0/note`「陆沉睁眼，面板由暗到亮逐格浮现」→「陆沉抬腕看骨纹（未亮）；面板由暗到亮逐格浮现」⇒ 与骨纹未激活态裁决**同向、无冲突**；本岗四份 U02／U03 产物 **sha 全等未动**。
- `render/D05.md` 已于 **11:04:38** 由他岗重渲为 v1.7 ⇒ **无渲染漂移**，本岗不重复渲、不代改 MD。
- ⭐ **本岗不代改、不争写**（他岗 11:2x 仍在 D11／D12／D15／D16 作业面内）；⇒ **请企划合规/总控确认**：这两处写入是否属「用户裁决直贯执行」授权路径？若是，建议把**本岗单写点 D05／D07 的写入授权登记进 `00_团队章程.md`**，避免本岗与执行方并发争写（否则下一次「同点双写」会真的撞车）。

**七、本岗状态与边界**
- **本轮交付物改动＝零**：D04 v1.2｜D05 v1.7（他岗写）｜U01 D07 v1.2（他岗写）｜U02 D06 v1.2｜U02 D07 v1.3｜U03 D06 v1.0｜U03 D07 v1.0 —— **本岗 U02／U03 四份产物 sha 全等未动**。
- **本轮脚本改动 3 份（均为本岗名下）**：`check_D05_banmian_scope.py`（受检面动态化 ＋ 两类豁免 ＋ G3c ＋ G7 统一 ＋ 文件头判据边界四段说明）｜`selftest_banmian_G3_exemption.py`（3 → 13 腿）｜`patch_D05_firstuse_shadow_bone.py`（**幂等判据改锚「两条词条现值」而非版本号** —— 因 D05 已被他岗升到 v1.7，只锚版本会在现盘上误报故障；改后现盘输出 `[IDEMPOTENT]`）。
- 本岗章节 **104.1–104.37 连续 37 节**（写后回读校验：缺号 0／重号 0）。
- **边界**：本轮**未改** D18／D03／D04／D06–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**（登记语境豁免**只读不改**）；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；源素材 `双相潮主/01_漫剧策划/` 本轮**只读回源、未改动**。

**八、仍挂待回复（合并去重，不逐条重派）**
- ~~台账 §一百四十四 三个 U+FFFD~~ → **已归零，闭环移除**。
- **V12 撞 U01／U02 存量白模数据（企划合规/总控裁「改数据／改规则／解锁重跑」）**｜「影刃」是否立为受控词条／是否引入「词干首用集」机制（须总控裁）｜`term_first_use` 登记「影刃封路」（from=13/until=35）与「骨龙」（from=1/until=25）｜D03 B08 `eps` 区间｜概述 ep018 阶位冲突｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条落点｜口径字母母本收口 ＋ 口径D｜audit-unit.py 空集恒真｜「受检叶」定义钉为字符串叶｜**D18 指针 2 条（U01 D11 动态中 —— 采纳台本编剧「不再逐次催刷」策略，待分镜导演冻结后由企划合规统一收口；U02 D16 仍 v1.6／232,059 B 未变）**｜**⭐ 本岗单写点 D05／D07 并发写入授权登记（新，请总控裁）**。

**以上游合规裁决为准。**"""
    block = [""] + body.split("\n") + [""]

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

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
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    bdir = os.path.join(root, "reports",
                        "_bak_ledger_104_37_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back_raw)} B；"
          f"追加点＝原第 {ins + 1} 行。落盘时间 {now}")
    print(f"[A7] 写后回读：104.1–{max(subnums)} 连续 {len(subnums)} 节（缺号 0／重号 0）；"
          f"全库 U+FFFD ＝ {back.count(chr(0xFFFD))}；标记命中 1；前段/后段逐字不变；备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
