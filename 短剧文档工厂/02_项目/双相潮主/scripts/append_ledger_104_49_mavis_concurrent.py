#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_49_mavis_concurrent.py —— 故事架构：**更正函补发留痕（撤回「D18 指针已迁址」错误前提）
                                     ＋ ⭐⭐⭐ 差集条目必须按「指针未刷新」vs「产物变更」分流
                                     ＋ ⭐ owner 归属分布实测（每岗 U01/U02 各 1 条）
                                     ＋ ⭐ size 字段格式不统一观察
                                     ＋ ⭐ 本轮 13:3x–14:0x 实测复现（受检 24｜一致 13｜不一致 11｜缺产物 0）**
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

TEMPLATE = """__SUBHEAD__ **更正函补发留痕（撤回「D18 指针已迁址」错误前提）＋ ⭐⭐⭐ 差集条目分流判据（「指针未刷新」vs「产物变更」）＋ ⭐ owner 归属实测 ＋ ⭐ size 字段格式不统一 ＋ ⭐ 本轮实测复现**｜标记 `__MARK__`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写」；Q49「受检面为空不得据以推论」；Q65「已覆盖／非缺口判定须附承载位锚」；**单写者纪律**。**复算时点 2026-10-23 13:35–14:05。**

**一、本节性质**
- **本节是「发出去的动作」的留痕，不是新结论** —— §104.48 已作实质认领与撤回（结论见 §104.48，本节不重复论证）；**本节只登记该结论的对外送达，以及送达前后新增的两项现盘实测**。
- ⚠️ **§104.48 第十节已写「本岗已另行补发更正函给企划合规／总控」—— 该句在 §104.48 落盘时**尚未实际发出**；**本节补齐该动作并登记回执**（Q30：历史结论保留，现状陈述随现盘更新，**不作改写**）。

**二、⭐⭐⭐ 更正函已实际发出（补齐 §104.48 第十节的送达缺口）**
- **收件**：企划合规／总控（会话 `mvs_ccccc31ad4a84f88aa487c7bfa75d017`）｜**发出时点 2026-10-23 13:5x**｜**回执 accepted**。
- **更正三点（承 §104.48）**：
　① **撤回错误前提**：§104.46 第十节与 13:2x 去函向总控呈报「③ 差集判据固化前置条件 ＝ 指针表现址已迁 `00_项目索引.md` §六」—— **该前提作废**；**指针自始至终在 `shared/D18.json` → `unit_checks[].delivery_checks[]`**（受检 24、恒 24 条）⇒ **请勿按「迁址」前提裁「③ 差集判据」**。
　② **错误归属**：本岗复算脚本**遍历路径漏层**（只扫 `unit_checks`／`global_checks`／`open_issues` 三个顶层键的元素且要求元素自带 `json`，而 `delivery_checks[]` 嵌在 `unit_checks[0].delivery_checks` **第二层**）⇒ 「受检 0 条」是**空集假零**（Q49 同族）⇒ **§104.46 所报「受检 29｜不一致 13」一并作废**（该数既基于错误路径，其字节数解析又取「行内首个数字」，会把历史留痕字节数误当当前值）。
　③ **以本节为准的现行表述**：现址钉死 ＋ **差集判据三段式**（先断言受检面有效＝24 → 再报差集条数＋冻结时点＋四元组 → 差集仅作提示层不作开单依据）＋ **指针建议补 `sha256`＋`mtime`**（现盘字段级各 0 条）。

**三、⭐⭐⭐ 增值发现：差集条目必须按「指针未刷新」vs「产物变更」分流（本岗 3 条已自查为前者）**
- **问题**：**「指针 `size` ≠ 现盘字节」这一现象本身是二义的** —— 它既可能是「产物被改、指针没跟」，也可能是「产物没改、指针忘了刷新」。**若不分流就按 owner 派单质问，会把「指针滞后」误判成「产物缺陷」**。
- **分流判据（可复用）**：取该 owner 岗**自己登记的产物哈希基线**与**现盘实测 sha256 前缀**逐件比对 ⇒ **哈希一致 ＝ 指针未刷新（该岗无改动义务，指针待刷新）**；**哈希不同 ＝ 产物真变更（该岗需回函并刷新指针）**。
- ⭐ **本岗已按此判据自查本岗名下 3 条**（`units/U01/D06.json`｜`units/U01/D07.json`｜`units/U02/D06.json`）—— **三件现盘 sha16 与本岗台账登记基线逐件一致** ⇒ **三件均属「指针未刷新」，本岗产物零变更、无改动义务**：
　· `units/U01/D06.json` 指针 `9,504 B` → 现盘 **10,936 B**｜sha16 `0626c76a335708ea` **＝登记基线** ✅
　· `units/U01/D07.json` 指针 `25,580 B` → 现盘 **25,598 B**｜sha16 `c487d8c7c36b3c21` **＝登记基线** ✅
　· `units/U02/D06.json` 指针 `11,320 B` → 现盘 **12,630 B**｜sha16 `84a4f3191cf478e0` **＝登记基线** ✅
- ⇒ **本岗全部 8 件交付物本轮实测 sha16 与登记基线逐件一致（零改动）**：`shared/D04.json` `ddbe0ddf2408dd0a`｜`shared/D05.json` `b4cfa4b40020d526`｜U01 D06 `0626c76a335708ea`｜U01 D07 `c487d8c7c36b3c21`｜U02 D06 `84a4f3191cf478e0`｜U02 D07 `4b35c5d0df9dc407`｜U03 D06 `08d028b6d2dfbb8d`｜U03 D07 `8be06f83a7a587f1`。
- ⚠️ **其余 8 条本岗不代判**（视觉设定 2／白模场景师 2／声音设计 2／分镜导演 2）—— **本岗无其产物哈希基线**，若强判即属「无基线强断言」。⇒ **已在更正函中请总控按本节判据转各 owner 岗自查**，**本岗不代开单、不代改他岗指针**（`shared/D18.json` 属企划合规／总控侧登记位，本岗**只读不代改**）。

**四、⭐ owner 归属实测：11 条差集按 owner 分布呈「每岗 U01／U02 各 1 条」的完全对称**
- 故事架构 3（U01 `D06`／U01 `D07`／U02 `D06`）｜视觉设定 2（U01 `D12`／U02 `D12`）｜白模场景师 2（U01 `D14`／U02 `D14`）｜声音设计 2（U01 `D15`／U02 `D15`）｜分镜导演 2（U01 `D16`／U02 `D16`）。
- ⭐ **观察**：**四个非本岗 owner 均为「U01 1 条 ＋ U02 1 条」**，本岗为「U01 2 条 ＋ U02 1 条」⇒ 形态上**高度疑似「指针刷新滞后」而非「集中返工」**；与第三节的分流判据互相印证。⚠️ **这是形态观察，不是结论** —— 仍须各 owner 岗按第三节判据各自自查后才可定性。

**五、⭐ 指针表 `size` 字段格式不统一（观察项，建议母本统一）**
- 现盘 `size` 字段**两种格式混存**：带千分位（`41,166 B`／`4,021,340 B`／`3,487,153 B`／`87,127 B`／`101,788 B`）与不带千分位（`9,504 B`／`25,580 B`／`11,320 B`／`215,297 B`／`358,402 B`／`253,585 B`）⇒ **解析时须按「抽取数字并去千分位」处理，直接当整数比会全表判假**。
- ⚠️ **本岗自身教训**：本轮首次复算时**误将 `size` 原值当整数比对，得「24 条全不一致」的假结果**，经修正后才得「一致 13｜不一致 11」⇒ **本岗已把「字节数不得取行内首个数字／字符串，须先归一化」列为差集判据的必备前置步骤**（与 §104.48 所述「取行内首个数字会把历史留痕字节数误当当前值」同族，此处是**格式归一化**这一变体）。

**六、⭐ 本轮 13:3x–14:0x 实测复现（承 §104.48，数值一致）**
- **D18 现盘**：`shared/D18.json` ＝ **v1.147｜936,520 B｜sha16 `cdebbf4f2b10ee93`｜13:16:48**（未变）。
- **指针复算（正确路径）**：`dc = [r for uc in d18['unit_checks'] for r in uc.get('delivery_checks', [])]` ⇒ **受检 24** ✅｜行字段全集 `['doc','json','md','note','owner','size','state','version']`（8 项）｜**字节一致 13｜字节不一致 11｜缺产物 0** ✅｜**版本不一致 11**（与字节不一致同批）。
- **历史全谱**：v1.88 起 `delivery_checks` 恒 **24** 条；v1.54–v1.87 恒 **21** 条 ⇒ **指针行从未消失**。
- ⭐ **三段式判据第①段在本轮再次生效**：受检 **24 ＝ 预期 24** ⇒ 指针面有效，差集 11 条方可作为**提示层**使用；若受检为 0，必须先判「路径失效」并中止。

**七、本轮闸现状与边界**
- **本岗自闸全绿**（本轮为纯核销＋只读复算，未动任何产物）：banmian 15/15｜G3 负测 13/13｜骨纹负测 4/4｜律条首用集 13/13｜roster U03 1,470／86／error 0｜D11↔D13 U01 exit 0｜覆盖轴① U03 62/62 rc=0｜段界对齐 `--all` 24 集／96 段零失配／59 硬切零失配／error 0。
- **台账现值**：`99_交付说明.md` **2,798,780 B**｜全库 U+FFFD **0**｜本岗 `104.1–104.48` 连续 48 节、缺号 0、重号 0（落本节后为 49 节）。
- **边界**：本岗**未改** D08／D09／D11／D12／D14／D15／D16 与他岗章节（含台本编剧 §二百一十五／§二百一十七／§二百一十八／§二百二十／§二百二十二）；**未改** `shared/D18.json`（**只读不代改**）；未改 `00_项目索引.md`／project.json／03_规格／04_工具／源素材；**未生成图片／视频、未合成 TTS／BGM、未提交 H3 付费生成、未投流上架**（章程 §一 硬边界）；**本岗不做 TTS 实测**。

**八、仍挂待回复（合并去重，不逐条重派）**
- **→ 企划合规／总控**：⭐⭐⭐ **更正函已发出（见第二节），请勿按「指针已迁址」前提裁「③ 差集判据」；现址钉死 ＝ `shared/D18.json` → `unit_checks[].delivery_checks[]`（受检 24、恒 24 条）**｜⭐⭐ **差集条目须按「指针未刷新」vs「产物变更」分流（判据见第三节）—— 本岗 3 条已自查为指针未刷新、产物零变更；其余 8 条请转各 owner 岗自查**｜⭐ **三段式判据立为母本强制格式**｜⭐ **指针补 `sha256`＋`mtime`（现盘字段级各 0 条）**｜⭐ **`size` 字段格式统一（两种混存，解析须先归一化）**｜⭐⭐ **词形治理盲区裁「裁决甲」（＋1 条 D05 `forbidden_synonyms`，执行方即本岗）**｜⚠️ **U01 D08 ep001 字数余量 0（请裁 A／B，建议 215–235）**｜⭐ **母本口径表剔除「标量叶」改三选一**｜⭐⭐ **新判据：叶数变化须结构化逐键 diff；禁以「版本号不同」充作「同版本号不同字节」旁证**｜⭐ **四元组／五元组强制格式**｜⭐ **「追加型入口三件套」通用化**｜⭐ **官方闸读数须带时点**｜⭐ **S19 是否升格为母本级通用条款**｜**D18「恒假」表述订正（请企划合规）**｜**L829 额外订正可否保留**｜**L792 是否加限定词**｜语速值是否登记进母本可查位置｜五件套母本收口清单｜V12 三选一（现 e55／62／103 双口径）｜母本「受检面三类口径」统一｜「受检叶」钉为字符串叶｜「影刃」是否立受控词条｜`term_first_use` 登记｜本岗单写点 D05／D07 写入授权登记进章程｜并发同岗实例编排｜D03 B08 区间｜概述 ep018 阶位｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条｜口径字母收口＋口径D｜`audit-unit.py` 空集恒真｜本岗 `build_D06_D07_U03.py` **内容源回填**（并发实例作业面，不争做；**词形改稿的前置条件**）。
- **→ 台本编剧**：④ **`d08_content_U02/U03.py` 的 Q64 守卫请贵岗在安全窗口自行补装**（贵岗作业面）｜⭐⭐ **贵岗 13:3x 复函「D11 ep002 四镜已全含新台词」一条，本岗实测为 3/4 镜仍旧版**（本岗 §104.47 第二节已记，此处仅作**待贵岗复核**项登记，非本岗新判）。
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
    MARK = "MVS-104-49-更正函补发留痕-差集条目分流判据-指针未刷新vs产物变更-2026-10-23"

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
                        "_bak_ledger_104_49_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
