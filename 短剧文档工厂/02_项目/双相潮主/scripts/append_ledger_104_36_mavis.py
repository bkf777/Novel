#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_36_mavis.py —— 故事架构：**台本编剧 10:4x U03 开工前置来件核销 ＋ D05 v1.6 两处首用集订正落地**
                                     （6 条必守口径独立复算全成立 ＋ ⭐ ep023 跨岗口径决断确认
                                      ＋ ⭐⭐ 影刃封路 37→36／骨龙 17→26，零级联
                                      ＋ ⚠️ V12 新规撞存量数据红灯转报 ＋ ⚠️「影刃」专名提前用待裁）

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_36_mavis.py --project 02_项目/双相潮主 [--dry-run]
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
    MARK = "TBZ-10-4x-核销-D05v16-2026-10-23"

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
    body = f"""{sub_head} **台本编剧 10:4x U03 开工前置来件 · 独立复算与核销**（6 条必守口径**全部成立 ✅** ＋ ⭐ ep023 跨岗口径决断**确认接收** ＋ ⭐⭐ **D05 v1.6 两处首用集订正已落地**（影刃封路 37→36／骨龙 17→26，**零级联**）＋ ⚠️ **V12 新规撞存量数据红灯转报** ＋ ⚠️「影刃」专名提前用**待裁**）｜标记 `{MARK}`

**来件**：台本编剧 10:4x 送达的《U03 开工前置口径核销》，含六条必守口径逐条复核、ep023 跨岗口径决断、两处 D05 母本级冲突、D03 B08 区间、U04 提示。
**本岗处置原则**：Q42「不采信回报自述、以磁盘实况为准」——**全部数字由本岗独立复算**（检索时点 **2026-10-23 10:50–10:56**）；**D05 单写点范围内的母本冲突，本岗直接裁定并落地**（不空转上呈）。

**一、① 六条必守口径 —— 本岗独立复算，全部成立 ✅**

| # | 口径 | 本岗实测（U03 D06／D07） | 判定 |
|---|---|---|---|
| ① | 归一度 ep017–024 恒 **1.4%** | 「1.4%」**D06 8 + D07 8 = 16 处**；「1.5%」**命中 0** | ✅ 成立 |
| ② | 「影刃封路」禁用于 ep037 前 | U03 两文件**命中 0**（仅作「影刃」） | ✅ 字面成立（语义层见第三节裁定） |
| ③ | 「骨龙」ep026 首现，U03 用「骨威」 | U03 两文件「骨龙」**命中 0**；「骨威」14 处 | ✅ 字面成立（母本冲突见第三节） |
| ④ | 「阎王」及民间信仰五词 0 处 | 阎王／阴曹／地府／鬼差／投胎**各 0** | ✅ 成立 |
| ⑤ | ep019 立旗台词＝叶红衣口头禅 | D04 `YHY.catchphrase`＝「谁敢对陆沉露獠牙，我必先摘下他的身份铭牌」，**与 U03 ep019 逐字一致**；旗面「踏入此线者死」D06 1 + D07 2 = 3 处 | ✅ 成立 |
| ⑥ | ep023 密信＝商业合同 | D07 ep023 落「云顶财阀拨付安全屋配额与药剂，雾盟按批次交付高阶雾核」＋「交付栏只写批次编号与「清退区域」四个字，没有一个姓名」；**「商既衡」字面 0**、「云顶财阀」4 处 | ✅ 成立 |

- 伏笔复核：**ep021 `payoff=F09`**（`pending_unit=null`）✅｜**ep023 `plant=F02`**（`pending_unit=U05`）✅；其余 6 集三字段均 null ✅。
- 官方闸复跑：`validate --unit U03` ＝ **11/11｜error 0｜warning 11** —— 与来件自报**逐字一致** ✅（落盘实测 D06 v1.0／10,874 B／10:30、D07 v1.0／25,609 B／10:31）。

⭐ **叶数口径钉死（来件与本岗两数均成立，差在「叶」的定义）**
- 来件报 **591 叶**（D06 **173** ＋ D07 **418**）＝ **标量叶口径**（字符串＋数字＋布尔全部标量）。
- 本岗复算用 **字符串叶口径** ＝ D06 **136** ＋ D07 **273** ＝ **409**。
- 差额 182 个为**非字符串标量**（409 + 182 = 591），**不可能含任何词形** ⇒ **禁词／词形扫描的有效受检面＝字符串叶**。
- ⇒ **两数均成立，不是错数**；但按 §104.35 的四件套规则，「受检叶」属**范围口径**，报数时必须写明统计对象。⭐ **母本级建议已随回报上呈**：把「受检叶」定义钉为**字符串叶**，避免数字/布尔稀释分母。

**二、⭐ ep023 跨岗口径 —— 本岗正式接收贵岗决断：**
- **本岗答复（单一结论）**：**接受** —— **D07 ep023 `present_characters` 维持 `["LC","SQC"]`，不增列 `YD-GC`**；本岗 U03 D06／D07 **零改动**。
- 复算佐证：D06 ep023 `characters`＝`["LC","SQC"]`；D07 ep023 `present_characters`＝`["LC","SQC"]`；**两侧一致且均无 YD-GC** ⇒ 不增列即不触发 V2 ✅；U03 全部交付物「商既衡」字面 **0** 命中 ✅。
- 本岗回加一条写法口径（供贵岗 D08 照执行）：密信内容**以面板／终端可见文本呈现**，行动行只写可见事实 —— **不出现姓名、不出现宗教仪式与誓词**；面板归一度照写 **1.4%**；台词层只用「云顶财阀／拨付／批次／清退区域」等**指示性表述**指称机构层级。

**三、⭐⭐ 两处 D05 母本级冲突 —— 本岗（D05 单写点）裁定并已落地：`**D05 v1.5 → v1.6**`

（1）**回源依据（唯一真源＝《逐集内容概述》｜16,731 B｜sha256 `7627f1381c4c6b81`｜检索时点 10:52）**
- ⭐ **《脉络确认》§三 术语首用表只收 8 词（灰潮试炼／灰雾·灰斑／灰奴／归档·重生／雾核·配额／律条·天律／潮主／神骸），不含「影刃封路」「骨龙」** ⇒ **原值 37 与 17 在母本内无出处**。
- 「**影刃封路**」字面首现＝**ep036**（「叶红衣影刃封路叶家族长退路」），全集**仅 1 处**。
- 「**骨龙**」字面首现＝**ep026**〔B09〕（「三纹破境，黑白双生骨龙威震全场」），全集 ep026／037／091／099。
- 「**骨龙贯穿**」字面首现＝**ep091**；「**骨龙威压**」字面首现＝**ep099**；「**骨威**」首现＝**ep017**，全集 ep017／018／052／098。
- 源素材本轮**只读回源，未改动**。

（2）**裁定**

| 词条 | 原值 | 裁定 | 依据与原值疑因 |
|---|---|---|---|
| 影刃封路 | 37 | **36** | 源 ep036 字面首现；**原值疑取「斩叶家族长」beat 的〔B13〕标记集 ep037 —— beat 锚点 ≠ 词形首现集** |
| 骨龙贯穿 / 骨龙威压 | 17 | **26** | 源 ep026「骨龙」字面首现；**原值疑为「骨威」首现集 ep017 的串位**；「骨龙贯穿」ep091、「骨龙威压」ep099 均在 26 之后 |

（3）**definition 同步写入首用口径**（**必要**：`D05.md` 的渲染表只有「术语／收口定义／禁用同义写法」三列、**不渲染 `first_use_ep`** ⇒ 首用集口径写进 `definition` 才可被人工审读）
- **影刃封路**三层：① **词形首用集＝ep036**；② **形态规约自 ep016 起适用**（源 ep016〔归档大限日〕暗杀组夜袭，叶红衣封退路 ⇒ 该形态一出现即须以影刃呈现、禁枪械与射杀；**禁写面＝`forbidden_synonyms`，与首用集正交、始终生效**）；③ **形态可先于定名出现**（沿用「律条」词条已确立的先例「机制先、名字晚」）——**画面描述面不受词形首用集约束**；**台词面与字幕面自 ep036 起方可出现「影刃封路」四字**。
- **骨龙贯穿 / 骨龙威压**：本词条 `first_use_ep` 取**「骨龙」形态的源素材字面首现集 ep026**；「骨威」是**另一词形**（ep017／018／052／098），**不在本词条范围**、不受本词条首用集约束；**ep026 之前不得使用「骨龙」这一名称及其派生词形**。

（4）**零级联实测（改前先证，改后回读）**
- ⭐ **母本机器口径**（`03_规格/rules.json` `_term_first_use_note`）：首用集**只约束台词面**（D11 `shots[].dialogue` ＋ D08 `body[type=dialogue]`）**与字幕面**（D16 `subtitle_style.lines[].text`）；**画面描述面不查 —— D05 明文允许**。
- 实扫 U01／U02／U03 全部 D08／D09／D11／D16 的上述四类面：「影刃封路」「骨龙」命中 **0** ✅。
- 「骨龙」在 `units/` 全部已落交付物命中 **0** ✅ ⇒ **17→26 无任何回改需求**。
- 存量「影刃封路」命中 **14 处**（U02 D06 1／D07 3／D08 1／D11 4／D13 2／D16 3）**全部落在画面描述面**（`must_happen`／`scene_needs`／`quad_segments[].note`／`compliance_notes`／`shots[].note`／`continuity`／`cuts`／`transitions` `basis`）⇒ 按母本口径不受词形首用集约束 ⇒ **零回改**。
- 官方闸 V5 **不检查 D05 glossary 的 `first_use_ep`**（只跑 `rules.json` 的 `term_first_use` 轴，当前仅「律条」一条）⇒ 本次变更**结构上不可能**产生新 error（已实跑验证：改动后官方闸 error 全部来自 V12，见第五节）。

（5）**落盘与副作用控制**
- `shared/D05.json` **v1.5 → v1.6**｜**38,574 → 40,625 B**｜sha256 `bed73e0b9a6de809` → `0088a44796b63c0c`｜**10:54:51**。
- 脚本 `scripts/patch_D05_firstuse_shadow_bone.py`（17,929 B）：断言 A1 版本／A2 词条定位／A3 原值逐字／**A4 回源首现集必须与裁定目标值一致**（源素材变了就拒绝写盘）／A5 台词面零命中／A6「骨龙」全库零命中／A7 schema 键集合白名单＋非目标 40 条词条逐字不变＋禁写面未动／A8 CAS／A9 写后回读；**幂等守卫锚内容**；备份 `reports/_bak_D05_firstuse_20261023-105451/D05.json`。
- MD 同步：`render/D05.md` 由 `render-md.mjs` 重新生成（v1.6｜含 2 处「首用口径」）—— **只同步本岗这一份**；**其余 28 份 MD 逐字节与渲染产物一致（零代改他岗产物）**。
- ⭐ **边界（本岗刻意不做的事）**：**不新增 glossary 词条**（新立词条＝新增母本收口，须总控/企划合规裁）｜**不动 `terminology_basis`**（其 T 编号与 glossary 序**不对应** —— T12=云顶财阀、T13=叶家，追加会错位）｜**不动 `forbidden_synonyms`**（禁写面与首用集正交，改它会波及 V5 全文扫描面）｜**不动 `03_规格/rules.json`**（企划合规单写点）。

**四、⚠️ 附带发现（不自行处置，已登记待裁）：「影刃」作为专名在源素材首现 ep036，而本岗 U03 ep017 与 U02 ep016 已用**
- **事实**：源《逐集内容概述》「影刃」字面首现＝**ep036**；本岗 U03 D06 ep017 `hook_out`「影刃切断了最后一个退路」／`logline`「影刃过处刺客溃散为灰烬光尘」／`must_happen[1]`「影刃切过」已用；U02 D07 ep013／ep016 亦用（画面层 14 处「影刃封路」见第三节）。
- ⭐ **本岗不处置的三条理由**：① **「影刃」未在 D05 glossary 登记为词条** ⇒ 无母本依据判定其「首用集前禁用」；② 若把「影刃」立为受控词条（`first_use_ep=36`），**等于本岗新立一条母本收口、同时回溯判自己已落的 U03 违规** ⇒ 属**新增母本口径**，须总控/企划合规裁；③ 「影刃」是**词干**，D05 现无「词干首用集」机制（现机制只管整词），新立机制影响面 42 词条。
- ⇒ **本岗默认执行口径不变**：已落 D06/D07 不动；**D08 若落 ep017，同步沿用 D07 的「影刃」写法**（D08 须与 D07 施工卡逐字一致，单方改会造新分叉）。
- ⇒ **已随回报上呈总控/企划合规**，请裁：是否新立「影刃」词条、是否引入「词干首用集」机制。

**五、⚠️ V12 新规撞存量数据 —— 红灯转报（与本岗本轮改动无关，已逐条取证）**
- **现象**：官方闸由 10:44 的 **33/33｜error 0｜warning 15** 变为 10:55 的 **34/36｜error 62｜warning 22**（U01 30 error／U02 32 error／U03 **0** error）。
- ⭐ **根因取证（四条，逐条可核）**：
 ① **V12 是新规则**：`04_工具/lib/rules.mjs` mtime＝**2026-10-23 10:51:40**，V12＝「白模构图一致性（D11 景别 ↔ 投影占幅）」（`scope=unit`）；10:44 时全项目 11 规则/单元、现 12 规则/单元 ⇒ **规则集在本岗改动之前已变更**；**`04_工具` 属主＝企划合规**。
 ② **V12 不读 D05**：V12 函数体内 `D05｜glossary｜first_use` 命中 **0** ⇒ **本岗 D05 变更在结构上不可能触发 V12**。
 ③ **命中面全在白模投影数据**：62 条 error 全部形如「V12 epXX_shotYY：W1 角色完全不在画幅内（占幅 0%）／W2 主体占幅 X% 落在「〈景别〉」区间 [a,b] 之外／W3 画面最大对象是 EXT／LGT「…」（占幅 100.0%），主体让位给环境」；分类：**U01 W1 9／W2 14／W3 23**｜**U02 W1 15／W2 11／W3 31**。
 ④ **数据早于规则**：`units/U01/D14_shots/*/projection.json` mtime＝**10:08:20**、`units/U02/D14_shots/*/projection.json` mtime＝**08:32:28** ⇒ 属**新规则撞存量数据**，不是新数据不合规。
- **归属**：命中数据＝`units/U0X/D14_shots/*/projection.json`（**产物方＝白模场景师**）；对端＝D11 `shot_size`（**分镜导演**）；规则与锁态＝**企划合规**（U01 locked 01:28／U02 locked 08:43）⇒ **新规则与已锁单元的存量数据冲突**，需总控裁「改数据／改规则／解锁重跑」三选一。
- ⭐ **不重复派工**：白模场景师 **10:55 正在 `04_工具/check_white_model_poses.py`（W6 白模姿态数据自洽检查）** 作业面内（V12 判输出、W6 判输入，同源于 `rules.json` → `white_model_framing`）⇒ **已在处理面，本岗不另发件**；本节只作**归属指认 ＋ 转报**。
- 本岗**不代改** `04_工具/*`／`03_规格/*`／D11／D13／D14。

**六、附两条来件转来的口径（本岗采纳，登记备查）**
- ⭐ **U04 提示（贵岗提供，本岗采纳）**：`gauge_locked` 另锁 **ep028＝1.5%**（源《逐集内容概述》ep028〔B10〕「系统警告『潮主归一度达 1.5%』」）⇒ ep026 锚点（1.5%）把区间抬到 **[1.5%, 1.5%]** ⇒ **ep027 起读数下限即 1.5%**；**U04（ep025–ep032）写 ep025–ep028 时勿按 ep024 的 1.4% 顺延**。⇒ 本岗 U04 落盘时按此执行。
- **D03 B08 区间（归企划合规，D03 单写点）**：B08 `eps`＝「ep025-032」不含 ep023，而 U03 ep023 密信已按 B08 口径落成 ⇒ 区间与实际首用集冲突。**贵岗已一并转报企划合规，本岗不重复派单**；本岗 D08 若落 ep023，按**已落 D07 的商业合同口径**写，**不因待核改写**。

**七、本岗状态与边界**
- 本轮**唯一交付物改动**：`shared/D05.json` **v1.5 → v1.6**（本岗单写点）＋ `render/D05.md` 同步；**D04 v1.2｜15,722 B｜U01 D07｜U02 D06｜U02 D07｜U03 D06｜U03 D07 全部零改动**。
- 本岗章节 **104.1–104.36 连续 36 节**（写后回读校验：缺号 0／重号 0）。
- **边界**：本轮**未改** D18／D03／D04／D06／D07／D08–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；源素材 `双相潮主/01_漫剧策划/` 本轮**只读回源、未改动**。

**八、仍挂待回复（合并去重，不逐条重派）**
audit-unit.py 空集恒真（企划合规）｜台账 §一百四十四 三个 U+FFFD（企划合规，owner 已订正）｜D03 B08 区间（企划合规）｜概述 ep018 阶位冲突｜**D05「影刃」是否立为受控词条（新立母本收口，须总控裁）**｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条｜口径字母母本收口 ＋ 口径D｜D18 指针 2 条｜**V12 撞 U01／U02 存量白模数据（企划合规/总控裁）**｜**「受检叶」定义钉为字符串叶（母本级）**。

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
                        "_bak_ledger_104_36_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
