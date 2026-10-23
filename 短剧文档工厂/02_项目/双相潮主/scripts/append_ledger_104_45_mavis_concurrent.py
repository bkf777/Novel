#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_45_mavis_concurrent.py —— 故事架构：**A15 错误消息文案订正落地（总控派单 12:53）
                                     ＋ ⭐ 派单事实三项独立复算全部成立
                                     ＋ ⭐ 文案改前改后逐字对照
                                     ＋ ⭐ 额外订正：第 829 行注释同一假陈述（逐处分类）
                                     ＋ ⭐ 产物零变更证据（六份 sha256＋mtime＋字节数）
                                     ＋ ⭐ 脚本指针四元组更新（Q30 追加式）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   幂等守卫锚在内容标记上；文件名沿用 `..._concurrent.py` 后缀。
用法：python3 scripts/append_ledger_104_45_mavis_concurrent.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

TEMPLATE = """__SUBHEAD__ **A15 错误消息文案订正落地（总控派单 2026-10-23 12:53）＋ ⭐ 派单事实三项独立复算全部成立 ＋ ⭐ 文案改前改后逐字对照 ＋ ⭐ 额外订正：第 829 行注释同一假陈述 ＋ ⭐ 产物零变更证据 ＋ ⭐ 脚本指针四元组更新（Q30 追加式）**｜标记 `__MARK__`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写」；**单写者纪律（本岗仅写 D04–D07 与本岗名下脚本）**；Q40「改内容源重跑」；派单第⑤条边界（⛔ 不改判据逻辑／⛔ 不改 U01／U02 产物／⛔ 不动 U03 产物／⛔ 不重跑脚本）。**复算与改稿时点 2026-10-23 12:50–12:58。**

**一、派单事项与核销方式**
- **派单**：总控／验收裁决人 12:53「A15 错误消息文案订正（不改判据逻辑、不改产物）」—— 本岗为 D07 属主。
- **核销方式**：按现盘独立复算派单的三项事实（**不采信转述**）⇒ 逐条复现后再动笔；改稿后**以 sha256＋mtime＋字节数三件套证明产物零变更**。

**二、⭐ 派单事实三项独立复算（全部成立 ✅）**
- **① 事实** —— 本岗现盘实测「D06 vs D07 的 `must_happen` **逐字相同集**」：

| 单元 | 逐字相同 | 不同集 |
|---|---|---|
| **U01** | 5 集 | **3 集（ep001／ep002／ep003）** |
| **U02** | 6 集 | **2 集（ep009／ep010）** |
| **U03** | **8 集** | **0 集（两表逐字相同）** |

  ⇒ **「U01／U02 惯例两表逐字相同」在 U01 与 U02 上都不成立**（不是只在 U01 不成立）；**逐字相同的只有 U03** ✅。
  ⇒ **定性②成立**：逐条比对显示各差异集的**条数与顺序完全一致**（U01 ep001＝4/4、ep002＝4/4、ep003＝6/6、U02 ep009＝6/6、ep010＝6/6），差异**仅在个别条目的措辞**（U01 ep001 仅 D06 2 条／仅 D07 2 条；ep002 1/1；ep003 1/1；U02 ep009 4/4；ep010 2/2）⇒ **大纲级（D06）vs 施工卡级（D07）的表述层级差异，实测无语义冲突，属既存差异、非本轮引入** ✅。
- **③ 关键澄清：A15 断言本身没有恒假** —— 本岗逐行核对 `scripts/build_D06_D07_U03.py`：**第 48 行 `UNIT = "U03"`**；**第 576–577 行** `eps6 = {e["ep"]: e for e in d06["episodes"]}`／`eps7 = {e["ep"]: e for e in d07["episodes"]}`，其 `d06`／`d07` 由**第 825／827 行以 `UNIT` 自建**、经**第 835 行** `assert_content(root, d06, d07, project, d05, rules)` 传入 ⇒ **A15 比的是 U03 自己的 D06 vs D07**，是**单元内一致性自检**，**在 U01／U02 上根本不执行、也不会因 U01 差异而失败** ✅。**缺陷只在失败消息的文案** ✔。
- **④ 处置面** —— 只订正文案、不动判据逻辑 ✅（见第三节）。

**三、⭐ 文案订正：改前改后逐字对照**

| 位置 | 改前 | 改后 |
|---|---|---|
| **L791**（`fail(...)` 失败消息） | `fail(f"A15 ep{ep} D07.must_happen 与 D06 不同表（U01／U02 惯例两表逐字相同）")` | `fail(f"A15 ep{ep} D07.must_happen 与 D06 不同表（U03 本单元约定两表逐字相同；U01／U02 为大纲级 vs 施工卡级表述差异，非逐字相同）")` |
| **L829**（同行注释，**额外订正**） | `# D07.must_happen 由 D06 派生（U01／U02 惯例两表逐字相同），不在脚本内手抄第二份` | `# D07.must_happen 由 D06 派生（U03 本单元约定两表逐字相同；U01／U02 为大纲级 vs 施工卡级表述差异，非逐字相同），不在脚本内手抄第二份` |

- ⚠️ **L829 属派单未点名的第二处同一假陈述** —— 本岗**一并订正**（**仅注释文本**，不涉判据、不涉产物、不涉他岗文件），理由：该注释与 L791 是**同一命题的两次表述**，只改其一则下一个读脚本的人仍会被误导，**正是本派单要消灭的问题**。**若总控要求严格只改 L791，L829 一行可即刻回退**（回退不影响任何行为）。
- ⭐ **同脚本另两处相关表述，本岗逐处分类后判定「不改」**（**同形异指须逐处分类，命中 ≠ 缺陷**）：
  - **L551**「并按 U01／U02 惯例把 D07 的 must_happen 与 D06 **同集同序对齐**（不在脚本里手抄两份）」⇒ **陈述为真**（实测各差异集条数与顺序完全一致）⇒ **不改**；
  - **L792** `print("  ✓ A15 D07 承接／回答／代价／时间／情绪／must_happen 逐集非空，且 must_happen ≡ D06")` ⇒ **断言成功输出**，陈述的是「**U03 单元内** must_happen ≡ D06」，在 U03 语境下为真；输出上下文已限定在 U03 ⇒ **不改**（派单「如需」项，本岗判为「不需要」；如总控要求加限定词，请明示，本岗可即刻补）。
- ⛔ **判据逻辑未动**：L790 `if mh != eps6[ep]["must_happen"]:` **逐字保持原样**。

**四、⭐ 产物零变更证据（本轮唯一写盘＝脚本；三行比对全等）**

| 文件 | 字节 | sha256 | mtime | 判定 |
|---|---|---|---|---|
| `units/U01/D06.json` | 10,936 B | `0626c76a335708ea534edc94cb92d187987a0ccd5dcec95addd9fc2b7a306357` | 2026-10-23 11:51:12 | ✅ 未变 |
| `units/U01/D07.json` | 25,598 B | `c487d8c7c36b3c2141e3fc197145369cebfa0a943659d71c5cfd23c97299d8be` | 2026-10-23 11:43:52 | ✅ 未变 |
| `units/U02/D06.json` | 12,630 B | `84a4f3191cf478e01ee0578c73cfac82b5c2997ec601fcd0f1238d59759db620` | 2026-10-23 11:51:12 | ✅ 未变 |
| `units/U02/D07.json` | 28,431 B | `4b35c5d0df9dc4071919dc721732a41328025912e8918513f2d567538fbab684` | 2026-10-23 07:06:33 | ✅ 未变 |
| `units/U03/D06.json` | 12,137 B | `08d028b6d2dfbb8dccc9480bfaeabad4441d7d382c679130a05adeeaf41d995f` | 2026-10-23 11:51:12 | ✅ 未变 |
| `units/U03/D07.json` | 25,608 B | `8be06f83a7a587f198ff5d37a0b7f34a0311ef0f8bd9a239e8aa4c4700eefc02` | 2026-10-23 11:43:26 | ✅ 未变 |

- ⇒ **六份产物字节／sha256／mtime 三项全等 ⇒ 产物零变更** ✅（**未重跑该脚本**；按派单第⑥(2) 条执行）。
- **语法校验**：`ast.parse` 通过（**只解析不执行、不写盘、不生成 `__pycache__`**）✅。

**五、⭐ 脚本指针四元组更新（Q30 追加式订正，旧登记不改写）**
- **旧值（台账 §一百零四 既有登记，保留）**：`scripts/build_D06_D07_U03.py`｜**53,629 B**｜sha256 前缀 `8c48b3301b2e0ca0`｜2026-10-23 11:43:16。
- **新值（本轮文案订正后）**：`scripts/build_D06_D07_U03.py`｜**53,777 B**｜sha256 `72ddf2dd0be48fbf5099d9ce2cead7a0bd3856d0339ea8b6c269803abe54debe`（前缀 `72ddf2dd0be48fb`）｜2026-10-23 12:53:44｜**改动＝L791 失败消息文案 ＋ L829 注释文案（判据逻辑与全部数据表零改动）**。
- ⇒ **本轮唯一写盘＝该脚本**；**本岗八件交付物（D04／D05／三单元 D06／D07）sha256 与 mtime 全部未变** ✔。

**六、⛔ 本轮明确未做（按派单第⑤条边界）**
- ⛔ **未改 A15 判据逻辑**（L790 逐字保持）｜⛔ **未改 U01／U02 的 D06／D07 产物**（未统一两表逐字相同）｜⛔ **未动 U03 的 D06／D07 产物**｜⛔ **未重跑该脚本**（未写盘）｜⛔ **未改 D18／project.json／索引／03_规格／04_工具／他岗章节与交付物**｜⛔ **未用 `--force`**（该脚本的版本守卫仍在：内容源落后于活盘，重跑仍会 `[ABORT]` 而非回退 —— 本岗**不争做**内容源回填，属并发实例作业面）。

**七、⭐ 请企划合规订正 D18 登记位的一处表述（他岗单写点，本岗不代改）**
- `shared/D18.json` 第 1769 行（及其 `render/D18.md` 对应行）载有：「③ **恒假的断言才是真缺陷** —— A15 写「U01／U02 惯例两表逐字相同」，而它在 U01 上**恒假**」—— 其中「**恒假**」与本轮第②节复算**不符**：A15 是 **U03 单元内自检**，**在 U01 上不执行**，**不构成恒假**；其缺陷是**失败消息文案里的假陈述**（已由本轮 L791／L829 订正闭合）。
- ⇒ **请企划合规按单写者纪律订正该登记位**（本岗**不代改 D18**）。本岗已把上述复算证据送达，请据以更新措辞；**重开条件可保留**（「U01 两表差异」仍是可逐处复算的活检查项）—— 本岗建议把该检查项的表述改为「**U01／U02 两表差异逐处复算（大纲级 vs 施工卡级表述差异，允许存在）**」，避免与「恒假」混为一谈。

**八、本轮闸现状与边界**
- **本岗自闸全绿**（未受本轮影响，因脚本未重跑、产物未动）：banmian 15/15｜G3 负测 13/13｜骨纹负测 4/4｜律条首用集 13/13｜roster U03 1,470／86／error 0｜D11↔D13 U01 exit 0｜覆盖轴① U03 62/62 rc=0｜段界对齐 `--all` 24 集／96 段零失配／59 硬切零失配／error 0。
- **边界**：本轮仅改**本岗名下脚本的两处文案文本**；未生成图片/视频、未合成 TTS/BGM、未提交 H3 付费生成、未投流上架（章程 §一 硬边界）。

**九、仍挂待回复（合并去重，不逐条重派）**
- **→ 企划合规／总控**：⭐ **第七节的 D18「恒假」表述订正请求**｜⭐ **L829 额外订正的确认（可否保留）**｜**L792 print 是否需加「U03 单元内」限定词（如需请明示，本岗可即刻补）**｜五件套母本收口清单（§104.43 第十节）｜⭐ **S19 是否升格为母本级通用条款**｜语速值是否登记进母本可查位置｜V12 三选一（62／103 双口径，现 e72）｜母本「受检面三类口径」统一｜「受检叶」钉为字符串叶｜词形治理盲区｜「影刃」是否立受控词条｜`term_first_use` 登记｜**本岗单写点 D05／D07 写入授权登记进章程**｜登记表五元组｜并发同岗实例编排｜D18 指针差集（批次在跑，冻结前不追刷）｜D03 B08 区间｜概述 ep018 阶位｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条｜口径字母收口＋口径D｜`audit-unit.py` 空集恒真｜本岗 `build_D06_D07_U03.py` **内容源回填**（并发实例作业面，不争做）。
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
    MARK = "A15-文案订正-派单12-53-产物零变更-2026-10-23"

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
                        "_bak_ledger_104_45_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
