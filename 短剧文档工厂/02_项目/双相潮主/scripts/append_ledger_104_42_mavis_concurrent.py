#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_42_mavis_concurrent.py —— 故事架构：**台本编剧 11:5x 回件核销（6 段）＋ ⭐ ① 验收逐字复现
                                     ＋ ⭐ ② 「版本号不是唯一坐标」实证 ＋ ⭐ ③ 登记不追刷
                                     ＋ ⚠️⭐ 并发同岗实例登记（本岗单写点与台账命名空间被同写）
                                     ＋ ⚠️ 本岗产物现值变更（追加式订正）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
⚠️ **文件名不沿用 `append_ledger_104_NN_mavis.py` 约定** —— 2026-10-23 11:45 起该命名空间被**并发同岗实例**占用
   （见第九节），改用 `..._concurrent.py` 后缀以避免同名路径互覆。
用法：python3 scripts/append_ledger_104_42_mavis_concurrent.py --project 02_项目/双相潮主 [--dry-run]
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
    MARK = "TBZ-11-5x-台本编剧回件核销-并发实例登记-2026-10-23"

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
    body = f"""{sub_head} **台本编剧 11:5x 回件核销（6 段）＋ ⭐ ① 两条首用集订正的验收逐字复现 ＋ ⭐ ② 「版本号不是唯一坐标」实证 ＋ ⭐ ③ 登记不追刷 ＋ ⚠️⭐ 并发同岗实例登记 ＋ ⚠️ 本岗产物现值变更（追加式订正）**｜标记 `{MARK}`

**处置原则**：Q42「以磁盘实况为准」；**Q30 留痕不改写**——对既有登记只作**追加式订正**；复算时点 **2026-10-23 11:56–12:07**。

**一、来件 6 段核销（全部成立 ✅）**
① **两条首用集订正对已落产物零回改、零返修** —— 本岗独立复算见第二节，**逐字复现** ✅。
　⚠️ 来件「U03 D08 可开写」对本岗**已过期**：U03 D08 v1.4 已于 11:30:26 落盘（ep017–024 早已完成），内容源↔产物 6/6 一致 ⇒ **无需重开写** ✅。
② **两处状态更正再过期一版** —— 见第三节 ✅。
③ **指针策略「登记不追刷」** —— 本岗**支持** ✅，并补一条**差集同向实测**（第三节）。
④ **外部写入登记：支持把「单写点写入授权」登记进 `00_团队章程.md`** —— 本岗**支持** ✅，并附本岗侧守卫体检（第五节）。
⑤ **其余项**：① 三口径 321／225／112 无异议 ✅｜⑤ 腿3 双岗互证 ✅｜⑥ 两条 BUSY 不重投 ✅｜⑦ §104 连续节号无异议 ✅｜⑧ 口径D ＋ 字母分配权收口已转母本无异议 ✅｜④ 台账 U+FFFD ＝ **0** ✅（来件报台账 2,244,043 B｜父章 188｜最大 189｜缺号仅 108）｜③ 官方闸 **34/36｜e55｜w13** —— 本岗 12:0x 复跑**逐字一致** ✅（U01 e27 w2／U02 e28 w4／U03 e0 w7）。
⑥ **边界**：与本岗同口径 ✅。

**二、⭐ ① 验收逐字复现 —— 本岗两条首用集订正「零回改」获独立互证**
- **受检面（有效位）＝ D08 `body[].text` ＋ D09 `lines[].text`**（与贵岗同口径）。
- **词形命中（三单元全量）**：「骨龙」**0**｜「骨龙贯穿」**0**｜「骨龙威压」**0**｜「骨龙威」**0**｜「影刃封路」**0** ⇒ **全部 ✅**。
- **「影刃」（另一词形·形态/器物名）出现集**：U01 D08 ep7 body[13]／ep8 body[0]｜U02 D08 ep13 body[4]／ep15 body[10]／ep16 body[9]｜U03 D08 ep17 body[3]／body[4] ⇒ **与贵岗所报（U01 ep007·ep008｜U02 ep013·ep015·ep016｜U03 ep017）逐字一致**；**D09 台词面 0 命中** ⇒ 落在母本机器口径（首用集只查台词面＋字幕面）之外 ✅。
- **禁写面全量**：D05 `forbidden_synonyms` **126 条**（去重 124）× 三单元有效位 ⇒ **各 0 命中** ✅（与贵岗所报条数逐字一致）。
- **D09 语气卡 `forbidden_words`**：**U01 38／U02 87／U03 67 条** × 台词面 ⇒ **各 0 命中** ✅（条数逐字一致）。
- **灰烬光尘词形**：「散成灰烬光尘」全库有效位 **0**；「溃散为灰烬光尘」分布＝U01 D08 3／D09 1、U02 D09 1、U03 D08 7／D09 1 ✅。
- ⇒ **本岗裁定（「影刃封路 37→36／骨龙 17→26」）在已落产物上零回改、零返修，成立** ✅。

**三、⭐ ② 「版本号不是唯一坐标」—— 实证成立，本岗采纳为规程**
- **贵岗实测**：U01 D11 **同一版本号 v1.13** 下，字节在 8 分钟内从 **55,539 B** 变为 **56,478 B**（11:32:48）。
- **本岗复现**：本岗 11:3x 读到 U01 D11 ＝ **v1.13｜56,478 B｜sha `4ff2cc57b4926b98`｜11:32:48**；贵岗 11:3x 读到同版本号 **55,539 B** ⇒ **同版本号、不同字节、不同内容** ⇒ **版本号不能唯一定位一次写入** ✅。
- ⭐ **本岗采纳的指针登记四元组**（已用于本节与后续回执）：**版本 ＋ 字节 ＋ sha256 前缀 ＋ 时点**（版本号单独不可作坐标）。
- **D18 指针差集（本岗 12:0x 独立复算，24 条受检）＝ 不一致 10 条**：U01 `D06`/`D07`/`D12`/`D14`/`D15`/`D16`（6）＋ U02 `D06`/`D12`/`D14`/`D15`（4）⇒ **比贵岗 11:56 的 9 条多 1 条（U02 D12 登记 v1.1 ≠ 盘 v1.2，12:0x 刚升）** ⇒ **同向、差集在漂**，与贵岗「2→6→9」的轨迹一致 ⇒ **差集条数不是稳定值、不是可一次性闭合的缺陷清单**，**冻结前不追刷、只报「批次在跑 ＋ 差集现值/时点」** ✅。
  ⭐ **本岗复算方法留档（供他岗复用）**：D18 `unit_checks[].delivery_checks[]` 行结构＝`doc`/`json`(**相对路径**)/`md`/`owner`/`size`/`state`/`version`；**必须按 `json` 字段解析路径**（不可按 `units/{{unit}}/{{doc}}.json` 猜，否则 `shared/` 级文件会被误判「缺产物」）；`size` 两种格式（`21012 B`／`38,574 B`）须分别归一。

**四、⭐ ③ 登记不追刷 —— 本岗支持并补充**
- 本岗支持「**冻结前不再报具体条数**，只报「批次在跑 ＋ 差集现值/时点」」；**请勿按 2／5／6／9／10 任一历史值开单** ✅。
- 补充一条判据：**差集条数与差集成员都会随批次推进而变** ⇒ 判据应写成「**在冻结时点重取差集**」，而不是「某时点的差集清单」。

**五、⭐ ④ 章程登记 —— 本岗支持，并附本岗侧守卫体检**
- **本岗支持**把「单写点写入授权」登记进 `00_团队章程.md`，并**同意**贵岗五步规程（① 照常接受他岗字节与内容、不夺回不二次污染 ② **把内容源全量回填到现盘**（否则重跑会静默回退）③ 台账登记 ④ 去函请求授权源登记 ⑤ **给所有写盘入口补装版本守卫**）✅ —— 本岗第二节的 U01 D07/D06 措辞收口与 U03 ep022 段界对齐，正是按此规程由**同岗并发实例**完成的（见第九节）。
- **本岗四个写盘入口守卫体检（12:05 实测）**：`build_D06_D07_U03.py`（含 sha 校验＋幂等守卫）｜`patch_source_ep020_xinhuocheng.py`（含 sha 校验＋幂等守卫）｜`patch_D05_firstuse_shadow_bone.py`（含 sha 校验＋幂等守卫＋A4 回源断言）｜台账追加脚本（**含 sha256 CAS（size/mtime/sha256 三锚）＋ 标记幂等 ＋ 写后回读**）⇒ **本岗写盘入口均已带守卫** ✅。
- ⭐ **登记表字段建议（承接贵岗 ② 的实证，钉为四元组）**：**版本 ＋ 字节 ＋ sha256 前缀 ＋ 写入时点**（版本号单独不可作坐标，见第三节）；**授权登记**另加「**是否属用户裁决直贯**」字段。

**六、⚠️⭐ 并发同岗实例登记（新事实，本岗首次记录）**
- **事实**：本项目内**存在并发运行的同岗实例（故事架构）**。实证三条：
  ① **11:45** 本岗一次性脚本 `scripts/append_ledger_104_40_mavis.py`（14,739 B）**被另一并发实例以同路径写入覆盖**，原文件内容不可恢复（现为 1,250 B 的「作废占位」文件，其自述：原脚本属「故事架构另一并发实例的 §104.40 台账追加」）。
  ② 该并发实例**已落台账 §104.41**（骨纹措辞收口 ＋ U03 ep022 场景边界对齐段界），并在 **11:43:26／11:43:52／11:51:12** 重写本岗单写点产物：**U03 D07 v1.1、U01 D07 v1.3、U01 D06 v1.4、U02 D06 v1.3、U03 D06 v1.1**。
  ③ **§104.40 的台账正文未受影响**（落盘 11:43:06，备份 `reports/_bak_ledger_104_40_20261023-114306/99_交付说明.md` 可证；本岗写后回读：104.1–104.40 连续、标记命中 1、U+FFFD＝0）✅。
- ⭐ **风险判定**：两实例**同写同一批单写点**（D06／D07）＋ **共享台账节号命名空间**（`### 104.N` 由 max+1 动态取号，节号本身不冲突）＋ **共享脚本文件名约定**（`append_ledger_104_NN_mavis.py`）⇒ **同名路径互覆**已实际发生一次（本岗 14,739 B 脚本被覆盖）；**内容回退**风险见第七节。
- **本岗处置（本节即为规程化）**：① **不争写**（本岗本轮未对 D06／D07 任何一件落盘）；② **节号沿用 max+1 动态**（本节＝**{sub_head}**）；③ **脚本文件名避开既有约定**（本脚本用 `..._concurrent.py` 后缀）；④ **台账内登记并发事实**（本节）；⑤ **上报总控定编排**（见第八节）。

**七、⚠️ 本岗产物现值变更（追加式订正，按 Q30 不改写原节）**
- 本岗此前台账登记的指纹**已被并发实例更新**（现盘实测 12:05）：`units/U01/D06` **v1.4｜10,936 B｜sha `0626c76a335708ea`｜11:51:12**｜`units/U01/D07` **v1.3｜25,598 B｜sha `c487d8c7c36b3c21`｜11:43:52**｜`units/U02/D06` **v1.3｜12,630 B｜sha `84a4f3191cf478e0`｜11:51:12**｜`units/U03/D06` **v1.1｜12,137 B｜sha `08d028b6d2dfbb8d`｜11:51:12**｜`units/U03/D07` **v1.1｜25,608 B｜sha `8be06f83a7a587f1`｜11:43:26**。D04 v1.2（`ddbe0ddf2408dd0a`）与 D05 v1.7（`b4cfa4b40020d526`）未变。
- ⚠️ **回退风险（已实测拦截 ✅）**：本岗 `build_D06_D07_U03.py` 的**内容源已落后于活盘**（并发实例改了 U03 D06 v1.1／D07 v1.1，而本岗脚本仍按旧内容源生成）⇒ 12:05 实跑该脚本 ⇒ **`[ABORT] units/U03/D06.json 已存在且内容不同；如确需覆盖请加 --force（本次未写盘）`** ⇒ **幂等守卫正确拦下，未回退** ✅。
  ⇒ ⭐ **处置**：**本岗本轮不用 `--force` 重跑**（会回退并发实例成果）⇒ 需**把内容源全量回填到现盘**（贵岗规程②）后再重跑；该回填属并发实例同一作业面，**本岗不争做**，已在第八节并入总控编排请求。
- **闸复跑（12:05，全部绿 ✅）**：banmian **15/15**｜负测 **13/13** ＋ **4/4**｜lutiao firstuse **13/13**｜lutiao naming **10/10**｜roster U03 **1,470/86** ✅；**官方闸** U01 11/12 e27 w2｜U02 11/12 e28 w4｜**U03 12/12 e0 w7（V12 现为 PASS）**｜全项目 34/36 **e55 w13**。

**八、⭐ 覆盖轴① 对 U03 的挂项 —— 已部分消解**
- **分镜导演 U03 D11 已落盘**（`units/U03/D11.json` 现存在）⇒ 官方闸 U03 的 V12 由「**D11 不存在，无法对账**」转为「**PASS（V12: 本单元尚无 D14_shots 白模投影，跳过构图检查）**」⇒ **「D11 未落盘 ⇒ 覆盖轴① 对 U03 受检 0 条」这一条已消解** ✅。
- **余项**：U03 尚无 `D14_shots` 白模投影 ⇒ V12 在 U03 暂跳过 ⇒ **属白模场景师后续产物**（本岗不代做、不重复派单）。
- ⭐ **本岗 U03 产物（D06／D07）不受此影响**：本岗闸覆盖 U03 全部已落交付物，且 §104.36 的六条必守口径在 ep022 段界对齐后**仍全绿**（roster 1,470/86、lutiao firstuse 13/13）。

**九、仍挂待回复（合并去重，不逐条重派）**
- ⚠️ **（新）并发同岗实例的编排与命名空间**：建议总控明确 ① 同一岗是否允许多实例并发；② 若允许，**单写点（交付物）应串行**、**台账节号可并行但需带实例标识**；③ **脚本文件名须加实例后缀**（本岗已用 `..._concurrent.py` 自保）；④ 登记表字段＝**版本＋字节＋sha256 前缀＋时点＋是否用户裁决直贯**（本节第五、六节）。
- **V12 撞 U01／U02 存量白模数据三选一**（现 e55／w13，失败镜次 62→判据条数 103 的双口径见 §104.38）｜母本「受检面三类口径」统一｜受检叶＝字符串叶＋报数三件套｜词形治理盲区（「溃散为灰烬光尘」等）｜「影刃」是否立受控词条／词干首用集机制｜`term_first_use` 登记「影刃封路」「骨龙」｜本岗单写点 D05／D07 写入授权登记｜D18 指针差集（**批次在跑，冻结前不追刷**）｜D03 B08 区间｜概述 ep018 阶位｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条｜口径字母母本收口 ＋ 口径D｜audit-unit.py 空集恒真｜**本岗 `build_D06_D07_U03.py` 内容源回填到现盘（并发实例作业面，本岗不争做）**。

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
                        "_bak_ledger_104_42_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
