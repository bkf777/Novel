#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_52_mavis_concurrent.py —— 故事架构：**U03 D06「1 字节变化」定性（末尾换行，内容等价）
                                     ＋ ⭐⭐ 字节差三档分流判据（细化 §104.49 的两档分流）
                                     ＋ ⭐ 全项目末尾换行惯例实测（38 件＝20 带／18 不带）
                                     ＋ 处置口径：不追改（登记不追刷）**
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

TEMPLATE = """__SUBHEAD__ **U03 D06「1 字节变化」定性（末尾换行、内容等价 189/189）＋ ⭐⭐ 字节差三档分流判据（细化 §104.49 两档分流）＋ ⭐ 全项目末尾换行惯例实测（38 件＝20 带／18 不带）＋ 处置口径＝不追改**｜标记 `__MARK__`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写」；Q42 配套「登记不追刷」；**单写者纪律**；**并发同岗实例规程（不争写）**。**复算时点 2026-10-23 14:15–14:25。**

**一、本节性质**
- **触发**：§104.51 落盘后的交付物终检发现，**本岗单写点 `units/U03/D06.json` 的 sha256 与登记基线不一致** ⇒ 本节做定性并落处置口径。
- **注意**：**该文件已由并发同岗实例改动**（本岗 §104.50 相邻节「U03 D06 静默回退雷闭合＋A17 反静默回退守卫」即该实例的作品）⇒ **本岗不争写、不回改、不追改**，只做**只读取证与口径澄清**。

**二、⭐ 定性：内容零变更，差异＝文件末尾多一个换行符**
- **登记基线**（`_bak_director_r026f_u03d16_20261023-121743/units/U03/D06.json`）：**12,137 B｜sha16 `08d028b6d2dfbb8d`｜v1.1**。
- **现盘**：`units/U03/D06.json` ＝ **12,138 B｜sha16 `97196925784b92cb`｜v1.1**｜mtime 14:0x 之后。
- ⭐ **结构化逐键 diff（自写 walker，扁平化为「键路径 → 值」后比集合）**：**叶数 189 → 189（相等）｜同路径值不同 ＝ 0 条｜键集合增删 ＝ 0** ⇒ **JSON 内容完全等价**。
- ⭐ **字节级定位**：**首个差异字节位置＝12,137**（＝旧文件长度，即文件末尾）—— 旧尾 `…是命在烧。"\n    }\n  ]\n}` vs 新尾 `…是命在烧。"\n    }\n  ]\n}\n` ⇒ **差异＝新文件末尾多一个 `\\n`（1 字节）**。
- ⇒ **结论**：**「字节数 +1」不是内容变更，是格式变更（末尾换行）**；**版本号仍为 v1.1（同版本号不同字节，本项目第三类实证，且本次字节差为 1）**。

**三、⭐⭐ 字节差三档分流判据（细化 §104.49 的两档分流，建议入母本）**
- §104.49 已立两档分流（**sha 一致＝指针未刷新**；**sha 不同＝产物真变更**）。本轮实测证明**两档不够** —— **sha 不同既可能是内容变更，也可能是纯格式差异**。
- ⇒ **三档判据（按序判定，每档都要给证据）**：
　· **第 1 档：sha256 相同** ⇒ **字节完全一致** ＝ **指针未刷新**（owner 岗无改动义务，指针待刷新；按 §104.49 判据转 owner 岗自查）。
　· **第 2 档：sha256 不同 ＋ 结构化逐键 diff 零差异**（叶数相等、同路径值全同、键集合无增删）⇒ **格式差异**（典型＝**文件末尾换行**；亦可能是缩进/键序/换行符风格）⇒ **内容等价，产物无需改动**，仅需登记现状；**若差异仅在文件末尾，则「字节数不一致」这一现象本身就不足以支撑「产物变更」结论**。
　· **第 3 档：sha256 不同 ＋ 结构化逐键 diff 有差异**（叶数差 / 同路径值差 / 键增删）⇒ **内容真变更** ＝ owner 岗需回函并刷新指针。
- ⇒ **配套纪律**：**凡报「字节不一致」者，必须同时给出「结构化 diff 结论」**（零差异 / 有差异）—— **只报字节数差而不报 diff 结论，等于没定性**（本岗 §104.46「受检 29｜不一致 13」与本节 U03 D06 均属「未做此分层」的教训）。
- ⇒ **配套纪律**：**差异定位应做字节级首差定位**（首个差异字节位置 ＋ 两侧上下文）—— 只看总字节差 **无法区分「尾部 1 字节」与「中段改写」**。

**四、⭐ 全项目末尾换行惯例实测（14:2x，38 件交付物全覆盖）**
- **带末尾换行 20 件**：`shared/D01.json`｜`shared/D02.json`｜`shared/D18.json`｜`units/U01/D11.json`｜`units/U01/D12.json`｜`units/U01/D13.json`｜`units/U01/D14.json`｜`units/U01/D16.json`｜`units/U02/D07.json`｜`units/U02/D11.json`｜`units/U02/D12.json`｜`units/U02/D13.json`｜`units/U02/D14.json`｜`units/U02/D16.json`｜`units/U03/D06.json`｜`units/U03/D07.json`｜`units/U03/D11.json`｜`units/U03/D12.json`｜`units/U03/D13.json`｜`units/U03/D14.json`。
- **不带末尾换行 18 件**（含本岗 `shared/D04.json`｜`shared/D05.json`｜`units/U01/D06.json`｜`units/U01/D07.json`｜`units/U02/D06.json`）。
- ⭐ **结论：全项目存在两种末尾换行惯例且已混存（20／18），无统一规范** ⇒ **「末尾换行差异」在本项目是常态性噪声源**，任何以字节数为锚的指针/对账**天然会被这一项污染** ⇒ 这是 §104.49「差集条目必须分流」的**第二个二义来源**（第一个是「指针未刷新」）。
- ⇒ **建议母本**：① **指针比对以 sha256 为主锚、字节数为辅锚**（已在 §104.49 建议补 sha256，此处再补一层理由）；② **或统一末尾换行规范**（二选一即可，建议由总控裁定后一次性统一，避免各岗继续混写）。

**五、处置口径（本岗）**
- **不追改、不回改**：本岗**不**为「恢复原字节」去重写 `units/U03/D06.json` —— ① 内容等价，重写只会制造无意义的 sha 抖动并可能覆盖并发实例的成果；② 按 §104.42 已立口径「**登记不追刷**」，登记**现状陈述**（现盘 v1.1｜12,138 B｜sha16 `97196925784b92cb`｜内容等价）即可。
- **本岗八件交付物现状（14:2x 实测）**：内容层面**八件全部零变更**（U03 D06 除外，且其变更经结构化 diff 证为**纯格式**）；本岗台账登记的 sha16 基线仍对 U03 D06 有效但**字节数已过期** ⇒ **本岗自报的八件 sha16 中，U03 D06 一项需按现盘更新为 `97196925784b92cb`**（内容不变，仅字节/sha 变）。
- ⚠️ **本岗不代改他岗产物**：其余 7 条字节不一致条目仍按 §104.49 第三节判据转各 owner 岗自查（视觉设定 2／白模场景师 2／声音设计 2／分镜导演 2）；**本岗不作任何处置判断**。

**六、本轮闸现状与边界**
- **本岗自闸全绿**（本轮为纯只读取证＋台账登记，未动任何产物）：banmian 15/15｜G3 负测 13/13｜骨纹负测 4/4｜律条首用集 13/13｜roster U03 1,470／86／error 0｜D11↔D13 U01 exit 0｜覆盖轴① U03 62/62 rc=0｜段界对齐 `--all` 24 集／96 段零失配／59 硬切零失配／error 0。
- **台账现值**：`99_交付说明.md` **2,893,333 B**｜全库 U+FFFD **0**｜本岗 `104.1–104.51` 连续 51 节、缺号 0、重号 0（落本节后为 52 节）。
- **边界**：本岗**未改**任何交付物（本节零写盘，除本台账）；**未改** D08／D09／D11／D12／D14／D15／D16／`shared/D18.json`（只读不代改）／`00_项目索引.md`／project.json／03_规格／04_工具／源素材／他岗交付物与章节；**未生成图片／视频、未合成 TTS／BGM、未提交 H3 付费生成、未投流上架**（章程 §一 硬边界）；**本岗不做 TTS 实测**。

**七、仍挂待回复（合并去重，不逐条重派）**
- **→ 企划合规／总控**：⭐⭐ **字节差三档分流判据（sha 一致／sha 不同＋diff 零差异＝格式差异／sha 不同＋diff 有差异＝内容变更）—— 请裁是否入母本；配套要求「报字节不一致必须同时报 diff 结论」**｜⭐ **全项目末尾换行惯例混存（38 件＝20 带／18 不带）⇒ 请裁「统一末尾换行规范」或「指针以 sha256 为主锚」**｜⭐⭐ **V12 双口径现值＝失败镜次 16／判据条数 32，16 镜全部同型 ⇒ 请裁「V12 三选一」**｜⭐ **官方闸现值 36/39｜e16｜w14｜U03 缺件已归零**｜⭐⭐ **词形治理盲区裁「裁决甲」**｜⚠️ **U01 D08 ep001 字数余量 0（裁 A／B）**｜⭐ **基线对象须取冻结时点现盘（新立，§104.51）｜差集判据三段式｜指针补 sha256／mtime｜size 字段格式统一｜四元组／五元组｜追加型入口三件套｜官方闸读数带时点｜S19 升格｜D18「恒假」订正｜L829／L792｜语速值登记｜五件套收口｜受检面三类口径｜受检叶钉字符串叶｜影刃词条｜`term_first_use`｜单写点写入授权登记｜并发实例编排｜D03 B08 区间｜ep018 阶位｜城郊骨井｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜数据板词条｜口径字母收口＋口径D｜`audit-unit.py` 空集恒真｜本岗 `build_D06_D07_U03.py` 内容源回填**。
- **→ 分镜导演**：⭐⭐⭐ **D11 U01 ep002 三镜台词与 D08 v1.18／D09 v1.9 不一致（真实缺口，已取证；详见 §104.51 与本岗去函）**｜⭐ **V12 的 16 镜请评估 D11 侧景别可否一次性覆盖**。
- **→ 台本编剧**：④ **`d08_content_U02/U03.py` 的 Q64 守卫请在安全窗口自行补装**｜⭐⭐ **词形治理盲区待总控裁「裁决甲」（执行方即本岗）**｜⚠️ **U01 D08 ep001 字数余量 0（若 ep001 有改动请同步本岗）**。
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
    MARK = "MVS-104-52-U03D06末尾换行定性-字节差三档分流判据-末尾换行惯例全库实测-2026-10-23"

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
                        "_bak_ledger_104_52_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
