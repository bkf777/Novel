#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_53_mavis_concurrent.py —— 故事架构：**核销台本编剧对 §104.48 的复函（D18 指针差集口径）
                                     ＋ ⭐⭐ D18 现址刷新（v1.152）
                                     ＋ ⭐⭐ pointer 引入时点追溯（v1.149｜13:36:43｜上游先行落地）
                                     ＋ ⭐⭐ 两口径现盘独立复算（口径 A＝0｜口径 D＝2）
                                     ＋ ⭐⭐⭐ 口径 D 的 2 条＝「仅 mtime 不符」＝指针噪声（三档分流第 2.5 档）
                                     ＋ ⭐ 台本编剧第四点订正成立 → 本岗「补 sha256＋mtime」建议销号
                                     ＋ ⚠️ 本岗报数缺失一环（差集报数六件套）
                                     ＋ ⭐ 本岗 pointer 缺口自查 3 行**
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

TEMPLATE = """__SUBHEAD__ **核销台本编剧对 §104.48 的复函（D18 指针差集口径）＋ ⭐⭐ D18 现址刷新（v1.152）＋ ⭐⭐ pointer 引入时点追溯（v1.149｜13:36:43｜上游先行落地）＋ ⭐⭐ 两口径现盘独立复算（A＝0｜D＝2）＋ ⭐⭐⭐ 口径 D 的 2 条＝「仅 mtime 不符」＝指针噪声（三档分流第 2.5 档）＋ ⭐ 贵岗第四点订正成立 → 本岗「补 sha256＋mtime」建议销号 ＋ ⚠️ 本岗报数缺失一环 ＋ ⭐ 本岗 pointer 缺口自查 3 行**｜标记 `__MARK__`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写，现状陈述随现盘刷新」；Q49「受检面为空不得据以推论」；**单写者纪律**；**并发同岗实例规程**。**复算时点 2026-10-23 14:10–14:20。**

**一、本节性质**
- **来件**：台本编剧《复函 · §104.48 核销件 · D18 指针差集口径（贵岗报 11 vs 本岗实测 4）》，登记于其本岗章节 **§二百三十一**（本岗**只引用、不改写**）。
- **核销方式**：按现盘独立复算，**不采信转述**。
- **结论先行**：**贵岗五点整体成立 ✅**；⭐⭐ **贵岗第四点订正成立**（D18 指针已有 pointer 四锚）⇒ **本岗 §104.48「建议母本补 sha256＋mtime」一条建议项销号**（上游已自行实现，方向一致）；⭐⭐⭐ **贵岗口径 D 的 2 条「不一致」经本岗独立复算为「仅 mtime 不符」＝指针噪声，非产物变更** ⇒ **现盘两口径交叉互证：产物内容变更 0 条**；⚠️ **本岗同时认领一处报数缺失（差集报数未带口径定义与 D18 版本号）**。

**二、⭐⭐ D18 现址刷新（Q30：现状陈述随现盘更新；历史坐标保留不改写）**
- **本岗先前记录（13:3x–14:0x，各节原文保留）**：`shared/D18.json` ＝ **v1.147｜936,520 B｜sha16 `cdebbf4f2b10ee93`｜13:16:48**｜`unit_checks` 2／`global_checks` **130**／`open_issues` **147**。
- **现盘（14:1x）**：`shared/D18.json` ＝ **v1.152｜1,050,514 B｜sha16 `f4159ab5d35ee0eb`｜14:06:23**｜`unit_checks` 2／`global_checks` **138**／`open_issues` **158**｜**受检 24**。
- ⇒ **本岗 §104.48／§104.49／§104.51／§104.52 各节引用的 D18 坐标，一律按现盘理解**；历史坐标为**落盘时点属实**的留痕，不改写（Q30）。

**三、⭐⭐ pointer 引入时点追溯（本岗独立复算，备份链全遍历）**
- **全谱结论**：**v1.54 起至 v1.147，全部 `delivery_checks` 行的 `pointer` 子对象计数 ＝ 0**；**v1.148（`_bak_d18_vv1148_20261023-133514`｜954,712 B）仍为 0**；⭐ **v1.149（`_bak_d18_renum_20261023-133643`｜988,695 B｜13:36:43）首次出现 pointer ＝ 11 行**；v1.150（14:00）11；v1.151（14:01）11；**v1.152（14:06:23 现盘）＝ 12 行**。
- ⇒ ⭐ **本岗 §104.48 第七节「含 `sha256` 字段者 ＝ 0 条、含 `mtime` 字段者 ＝ 0 条」在落盘时点（13:27，D18＝v1.147）完全属实** ⇒ **非本岗误判**；pointer 由**上游于 13:36（v1.149）**引入，**比本岗建议晚约 9 分钟** ⇒ **本岗建议方向与上游实现一致** ⇒ **该建议项销号**（详见第六节）。
- ⇒ **现盘字段级事实复核**：顶层含 `sha256` 键的行 **0**、含 `mtime` 键的行 **0**（**sha16／mtime 嵌在 `pointer` 子对象内，不在顶层**）⇒ **本岗原结论「顶层无 sha／mtime 字段」在现盘仍成立**，但**「指针无 sha 锚」已不成立** ⇒ **二者须严格区分，不得混用**。

**四、⭐⭐ 两口径现盘独立复算（14:1x 现盘 v1.152）**
- **受检 24** ✅（三段式第①段：受检面有效）｜**含 pointer 12 行**。
- **口径 A（顶层 `version` ＋ `size` 双锚 vs 现盘）：不一致 0 条** —— 顶层 `version` 与 `size` 也已被上游随 pointer 一并刷新。
- **口径 D（`pointer` 四锚 `version`＋`bytes`＋`sha16`＋`mtime` vs 现盘）：不一致 2 条** ＝ `units/U01/D08.json`｜`units/U01/D12.json`。
- **顶层 ↔ `pointer` 自洽性（24 行逐条比 `version`／`bytes`）：不一致 0 条** ✅ **与贵岗结论逐字一致**。
- ⭐ **与贵岗报数的时点关系**：贵岗 **14:0x 冻结 A＝4／D＝4**、**14:05 复取 A＝5／D＝4** ⇒ **现盘 A＝0／D＝2** ⇒ **口径 A：4 → 5 → 0；口径 D：4 → 2** ⇒ **同一小时内两口径均漂移且趋于收敛**（上游 14:01–14:06 连刷 v1.150／v1.151／v1.152 刷新指针）⇒ **贵岗「该数只作时点快照、不作开单依据」的结论成立且被本岗加强 ✅**。

**五、⭐⭐⭐ 口径 D 的 2 条「不一致」定性＝指针噪声，非产物变更（§104.52 三档分流判据补第 2.5 档）**
- **`units/U01/D08.json`**：`pointer.version` v1.18 **✔**／`bytes` 40,546 **✔**／**`sha16` `2026b168cfc3da0f` ✔**／**`mtime` ✘**（pointer 记「2026-10-23 13:51:49」vs 现盘 **14:08:03**）。
- **`units/U01/D12.json`**：`pointer.version` v1.11 **✔**／`bytes` 87,954 **✔**／**`sha16` `dbe84bf9ce9f094b` ✔**／**`mtime` ✘**（pointer 记「2026-10-23 13:19:48」vs 现盘 **13:59:22**）。
- ⇒ **两行的 version／bytes／sha16 三锚全部一致，仅 `mtime` 单项不符** ⇒ **内容完全等价** ⇒ **是「同内容重写／touch 导致 mtime 变动」造成的指针噪声，不是产物变更**。
- ⚠️ **可观测事实（值得上游注意）**：**U01 D08 现盘 mtime 14:08:03，而其 sha16 与本岗 13:5x 实测完全相同** ⇒ **有实例重写了同内容**（或并发脚本重跑）⇒ **在本项目，`mtime` 不是可靠的变更信号**。
- ⇒ ⭐⭐ **本岗 §104.52 三档分流判据补第 2.5 档**：**「四锚中仅 `mtime` 不符，而 `version`／`bytes`／`sha16` 三锚全符」⇒ 判指针噪声，不判产物变更，不开单**（须与第 2 档「sha 不同但 diff 零差异＝格式差异」并列）。
- ⇒ ⭐⭐ **据此：口径 D 现盘真实「产物内容变更」条数 ＝ 0**，**与口径 A 的 0 条交叉互证** ⇒ **现盘 24 行无任何「内容变更未登记」的交付物**。

**六、⭐ 贵岗第四点订正 —— 成立；本岗「建议补 sha256＋mtime」销号**
- **贵岗订正**：本岗「D18 指针只有版本＋字节两锚、无 sha 锚」的现状陈述需订正 —— 实测 11/24 行已有 pointer 子对象且含 sha16＋mtime。**本岗接受该订正 ✅**。
- ⚠️ **但须带时点限定（Q30）**：本岗 §104.48 该陈述**落盘于 13:27，当时 D18＝v1.147（pointer 0 行）**，落盘时**属实**；pointer 于 **13:36（v1.149）**由上游引入 ⇒ **本岗建议与上游实现方向一致、上游先行落地 ⇒ 该建议项销号，不作本岗误判记账**。
- **贵岗建议的新动作（把余下行补齐 pointer 四锚、差集判据统一走 pointer）—— 本岗支持 ✅**（理由：`pointer` 具备 `sha16` 锚，可发现「同版本号同字节不同 sha」，这是顶层 `size` 双锚做不到的）。
- ⭐ **本岗已自查本岗名下 pointer 缺口 ＝ 3 行**：`shared/D04.json`｜`shared/D05.json`｜`units/U02/D07.json`（本岗 `units/U01/D06.json`／`units/U01/D07.json`／`units/U02/D06.json` **已具 pointer 四锚且四锚全一致 ✅**）。
- ⚠️ **本岗不代改 D18**（属企划合规／总控侧登记位，**只读不代改**）⇒ **缺口清单交总控转各 owner 岗**。

**七、⚠️ 本岗认领一处报数缺失：差集报数须带「口径定义 ＋ D18 版本号」**
- 本岗 §104.49／§104.51 所报「不一致 11」＝ **在 v1.147 上按「顶层 `size` 字段 vs 现盘字节」计算**；贵岗所报 4／5 ＝ **在 v1.149+ 上按 `pointer` 四锚计算**。
- ⇒ **两个数既不是同一集合、也不是同一时点** ⇒ **跨版本不可比**；**本岗该轮报数缺「口径定义」与「所依据的 D18 版本号」两要素，属本岗报数缺失，本岗认领**。
- ⇒ ⭐ **新立（建议入母本）**：**差集报数六件套 ＝ 范围 ＋ 口径 ＋ 统计方式 ＋ 统计对象 ＋ 时点 ＋ 「所依据的 D18 版本号 ＋ 所用口径定义（顶层 size 双锚 / pointer 四锚）」**。
- ⇒ 配套：**同一个「不一致 N」在不同 D18 版本上不可比**，引用时必须带 D18 版本号。

**八、贵岗第五点 —— 本岗核销 ✅**
- **U03 ep018 改档已结**：本岗实测 `units/U03/D08.json` ＝ **v1.6｜46,802 B｜sha16 `bd6b87096a416718`｜13:57:54** ⇒ **与贵岗所报逐字一致 ✅**；台账 §231 已在盘 ✅。
- ⭐ **「U03 在 D18 指针表内 0 行」—— 本岗独立复算确认 ✅**（24 行中 U03 计数 ＝ 0）⇒ **本次改档不产生 D18 义务 ✅**。
- **贵岗所报 U01 D08 四锚现值**：version v1.18／bytes 40,546／sha16 `2026b168cfc3da0f` —— 本岗实测**三项逐字一致 ✅**（mtime 因 14:08 同内容重写而变，见第五节）。

**九、本轮闸现状与边界**
- **本岗自闸全绿**（本轮为纯核销＋只读复算，未动任何产物）：banmian 15/15｜G3 负测 13/13｜骨纹负测 4/4｜律条首用集 13/13｜roster U03 1,470／86／error 0｜D11↔D13 U01 exit 0｜覆盖轴① U03 62/62 rc=0｜段界对齐 `--all` 24 集／96 段零失配／59 硬切零失配／error 0。
- **台账现值**：`99_交付说明.md` **2,911,314 B**｜全库 U+FFFD **0**｜本岗 `104.1–104.52` 连续 52 节、缺号 0、重号 0（落本节后为 53 节）。
- **边界**：本岗**未改**任何交付物；**未改** `shared/D18.json`（**只读不代改**）／`00_项目索引.md`／project.json／03_规格／04_工具／源素材／他岗交付物与章节（含台本编剧 §二百一十五／§二百一十七／§二百一十八／§二百二十／§二百二十二／§二百三十一）；**未生成图片／视频、未合成 TTS／BGM、未提交 H3 付费生成、未投流上架**（章程 §一 硬边界）；**本岗不做 TTS 实测**。

**十、仍挂待回复（合并去重，不逐条重派）**
- **→ 台本编剧**：⭐⭐⭐ **贵岗 §231 五点核销成立；本岗 §104.48「补 sha256＋mtime」建议项销号（上游 v1.149 已先行落地 pointer 四锚）**｜⭐⭐ **本岗 §104.52 三档分流判据补第 2.5 档「仅 mtime 不符 ⇒ 指针噪声」；现盘口径 D 的 2 条即属此档，真实产物内容变更 ＝ 0**｜⭐ **本岗 pointer 缺口 3 行（`shared/D04.json`／`shared/D05.json`／`units/U02/D07.json`）—— 属 D18 登记位，本岗不代改，请转总控/owner 岗**｜⭐⭐ **差集报数六件套（新增「口径定义 ＋ D18 版本号」）**｜⚠️ **U01 D08 在 14:08 被同内容重写（sha16 未变、mtime 变）⇒ 请留意 `mtime` 不可作变更信号**｜④ **`d08_content_U02/U03.py` 的 Q64 守卫请在安全窗口自行补装**｜⭐⭐ **词形治理盲区待总控裁「裁决甲」（执行方即本岗）**｜⚠️ **U01 D08 ep001 字数余量 0（若 ep001 有改动请同步本岗）**。
- **→ 企划合规／总控**：⭐⭐ **D18 指针现址刷新：v1.152｜1,050,514 B｜sha16 `f4159ab5d35ee0eb`｜14:06:23｜global_checks 138｜open_issues 158｜受检 24｜含 pointer 12 行**｜⭐⭐ **本岗「补 sha256＋mtime」建议项销号（上游 v1.149｜13:36:43 已先行落地 pointer 四锚）⇒ 请改裁「补齐余下 12 行 pointer 并统一走 pointer」**｜⭐ **pointer 缺口 12 行清单：`shared/D03`／`shared/D04`／`shared/D05`／`shared/D10`／`units/U01/D09`／`units/U01/D11`／`units/U01/D13`／`units/U02/D07`／`units/U02/D08`／`units/U02/D09`／`units/U02/D11`／`units/U02/D13`**｜⭐⭐ **三档分流判据补第 2.5 档「仅 mtime 不符 ⇒ 指针噪声」**｜⭐ **差集报数六件套**｜⭐⭐ **V12 双口径现值＝失败镜次 16／判据条数 32，16 镜全部同型 ⇒ 请裁「V12 三选一」**｜⭐ **官方闸现值 36/39｜e16｜w14｜U03 缺件已归零**｜⭐⭐ **词形治理盲区裁「裁决甲」**｜⚠️ **U01 D08 ep001 字数余量 0（裁 A／B，建议 215–235）**｜⭐ **基线对象须取冻结时点现盘｜字节差三档分流｜末尾换行规范二选一｜差集判据三段式｜size 字段格式统一｜四元组／五元组｜追加型入口三件套｜官方闸读数带时点｜S19 升格｜D18「恒假」订正｜L829／L792｜语速值登记｜五件套收口｜受检面三类口径｜受检叶钉字符串叶｜影刃词条｜`term_first_use`｜单写点写入授权登记｜并发实例编排｜D03 B08 区间｜ep018 阶位｜城郊骨井｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜数据板词条｜口径字母收口＋口径D｜`audit-unit.py` 空集恒真｜本岗 `build_D06_D07_U03.py` 内容源回填**。
- **→ 分镜导演**：⭐⭐⭐ **D11 U01 ep002 三镜台词与 D08 v1.18／D09 v1.9 不一致（真实缺口，已取证；详见 §104.51 与本岗去函）**｜⭐ **V12 的 16 镜请评估 D11 侧景别可否一次性覆盖**。
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
    MARK = "TBZ-§231复函-核销§104.48-D18指针口径-pointer于v1.149引入-两口径现盘A0D2-仅mtime不符判噪声-建议销号-2026-10-23"

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
                        "_bak_ledger_104_53_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
