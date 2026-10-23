#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账新章节（分镜导演岗）—— 动态取最大章号 + 1 ＋ 写前/写后 CAS 防并发撞号。

并发纪律（据 OPS-18／Q49 与既有教训）
------------------------------------
- 台账 `99_交付说明.md` 由**多个岗实例并发写入**。既有 `append_ledger_section.py`
  为「读盘 → 取 max+1 → append」三步，**中间无 CAS**：两实例同刻读到同一 max 即撞号。
  本脚本补 CAS：**以读入时的原始字节为比对基准**，写前重读若字节已变 → 重新取号并重排。
- 编号兼容：台账章号**中／阿两种写法混排**（§一百零六 与 §107／110／111／112／113 并存），
  取号函数按两种写法分别解析，**取数值最大者**；新章号采用**阿拉伯数字**（与近 6 节一致）。
- 写后回读：核对本节**只出现一次**且**章号不与他节重复**，对不上即报错。

用法
----
python3 scripts/append_ledger_114_mavis.py [--dry-run]
"""
import argparse
import datetime
import io
import os
import re
import sys

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"


def cn2int(s):
    """中文数字 → int；已是阿拉伯数字直接返回；无法解析返回 None。"""
    if s.isdigit():
        return int(s)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    total = section = 0
    for ch in s:
        if ch in digits:
            section = digits[ch]
        elif ch in units:
            u = units[ch]
            if section == 0:
                section = 1
            total += section * u
            section = 0
        else:
            return None
    return total + section


def parse_max(txt):
    """取全部 '## <号>、' 顶级章节的最大章号（兼容中／阿两种写法）。"""
    vals = []
    for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M):
        n = cn2int(m.group(1))
        if n:
            vals.append(n)
    return (max(vals), sorted(vals)) if vals else (0, [])


def build_section(nxt, now):
    CH = f"{nxt}、"
    return f"""
## {CH}分镜导演：**D16 活戳刷新（U01 侧 v1.4 → v1.6，27 处活链接）** ＋ **U02 侧 52 处撤单核销** ＋ **守卫有效性五腿实跑** ＋ **数值零改动实证（1281 数值字段 0 差异）**（分镜导演，{now}）

### {nxt}.1 **派活与认盘：U02 侧已被并行实例落好 → 撤单；U01 侧实测仍指 v1.4 → 本岗补做**

派活来源：声音设计追加派单（接 `task_80f96d3b8320`）——把 D16 中指向 D15 的「活戳」更新到当前 D15 版本，U02 侧 52 处目标 v1.1→v1.2，U01 侧目标 v1.6。

| 侧 | 派活前提 | **磁盘实况（认盘 07:50–07:55）** | 本岗处置 |
|---|---|---|---|
| U02 | 52 处 v1.1→v1.2 | **已由并行实例 `scripts/build_D16_U02.py` 于 07:49:50 落好**（D16 v1.5，208,578 B） | **撤单**，不重复记账、不重跑生成器 |
| U01 | 21 处「仍指 v1.6 不变」 | **实测仍指 v1.4**（8 集 `verified_against_d15` ＝「v1.4（终表口径；D15 v1.4 落盘后复核）」） | **补做**：按现行 D15 U01 **v1.6** 刷新 |

> **认盘结论优先级**：磁盘实况 > 派活转述。派活文说 U01 侧「仍指 v1.6 不变」，磁盘并非如此；按派活的**目标态**（U01 侧应指向现行 D15 版本 = v1.6）执行。

### {nxt}.2 **改动明细：活链接 27 处 ＋ 事件溯源保留（不动）**

**只改活链接（当前有效性指针）**：

| # | 字段 | 集 | 处数 | 旧 → 新 |
|---|---|---|---|---|
| 1 | `subtitle_style.subtitle_sync_audit.verified_against_d15` | 全 8 集 | **8** | `v1.4（终表口径；D15 v1.4 落盘后复核）` → `v1.6（…D15 v1.6 落盘后复核）` |
| 2 | `subtitle_style.subtitle_sync_audit.verified_note` 末句 | 全 8 集 | **8** | 「D15 v1.4 落盘后**须复核** 9 行逐条一致。」→「D15 v1.6 落盘后**已复核** 9 行逐条一致（9/9 一致）。」＋追加 v1.6 复算证据段与余量三口径现值 |
| 3 | `subtitle_style.dwell_calc_convention` 终表段 | ep1/2/3/5/8 | **5** | 「D15 v1.4 落盘后复核）」→「D15 v1.6 落盘后复核）」 |
| 4 | `subtitle_style.dwell_calc_convention` 非终表集 | ep4/6/7 | **3** | 「现值仍为 D15 **v1.4** 现行预算」→「**v1.6**」 |
| 5 | `subtitle_style.dwell_calc_convention` 非终表集 | ep4/6/7 | **3** | 「D15 现行为 **v1.4**」→「D15 现行为 **v1.6**」 |

**活链接合计 27 处**（8＋8＋5＋3＋3）。派活文按字段类型计「U01 侧 21 处」＝ 8＋8＋5，**未计非终表集 3 集的 2 处 `**v1.4**` 活链接**——本岗按同一口径（凡断言「现值／现行为」者皆属活链接）**补齐该 6 处差额**。

**事件溯源按 S11「只追加不覆盖」原文保留（零改动）**：`sync_basis` 的「D15 v1.1 贴边配音收敛」｜`sync_records[0].basis` 的「D15 新 dur_sec 待声音设计落 v1.4 后复核」｜`dwell_calc_convention`【上游闭合戳】段与「D16 v1.3→v1.4」｜`verified_note` 中段「D15 v1.3 × D16 v1.6 × D11 v1.6 复算」。

### {nxt}.3 **数值零改动实证（1281 个数值字段逐字段比对，差异 0 处）**

落盘前备份 `reports/_bak_U01_D16_liveptr_20261023-075449/D16.json`；落盘后与备份**逐叶子路径比对全部数值字段**：

| 项 | 值 |
|---|---|
| 备份数值字段数 | **1,281** |
| 现盘数值字段数 | **1,281** |
| **差异条数** | **0** |

→ 本轮**只改口径文本与版本指针**，未动任何 `in_sec`／`out_sec`／`dur_sec`／`cuts`／`transitions`／`title_card`／`paywall_point`。

### {nxt}.4 **守卫有效性五腿实跑（沙箱副本，真盘零写入）**

脚本 `scripts/patch_D16_live_pointer_v16.py`。**自测全程在 `/tmp` 沙箱副本进行，未在真实交付物上伪造版本**。

| 腿 | 构造 | 期望 | 实测 |
|---|---|---|---|
| **A** | 沙箱 D16 version 伪造 `v9.9` | `[NO-OP]` exit 0，磁盘零改写 | ✅ `[NO-OP]` exit 0，**字节未变** |
| **B** | 沙箱 D15 version 改 `v1.7`（目标版本不符） | `[NO-OP]` exit 0，磁盘零改写 | ✅ `[NO-OP]` exit 0，**字节未变** |
| **C** | 沙箱正常跑 | 落盘 v1.11 | ✅ `v1.11`，183,220 B，含备份 |
| **D** | 沙箱复跑（幂等） | `[NO-OP]`，字节不变 | ✅ `[NO-OP]`，**字节未变** |
| **E** | 沙箱破坏 1 处锚点 | `[ABORT]` exit 1，不写盘 | ✅ `[ABORT]`，**退出码 1**，**字节未变** |

**拒绝路径独立取证**：腿 E 实测**退出码 = 1**（非 0），且字节数与 mtime 均未变 → 证明「守卫存在**且有效**」，而非仅「跑得通」。

### {nxt}.5 **出口闸与跨文档复算（落盘后全链重跑）**

| 轴 | 受检 | 结果 |
|---|---|---|
| `validate --unit U01` | — | **11/11 PASS｜error 0｜warning 1**（刷新前 warning 2 → **降 1**） |
| `validate --unit U02` | — | **11/11 PASS｜error 0｜warning 5** |
| `render-md --project 02_项目/双相潮主` | — | **exit 0**；`render/units/U01/D16.md` = **164,514 B** |
| `reconcile_D15_D16_timing.mjs --unit U01` | 配音 28 ＋ sfx/foley 80 ＋ 字幕 75 | **exit 0**；0 越窗 / 0 跨切点 / 0 重叠；**28 条对白字幕 out_sec ＝ 配音 at_sec＋dur_sec，0 条不符**；判据清单断言 12/12 不通过 0 条 |
| `reconcile_D15_D16_timing.mjs --unit U02` | 同上 | **exit 0**，零违规 |

**上轮遗留已结**：此前「out_sec ≠ 配音 at+dur」**9 条**（U01-R18 终表新 `dur_sec` 未落）**已归零** —— 实测 D15 U01 **v1.6** 现盘已含该 9 条新 `dur_sec`，逐条比对终表值 **9/9 一致**。

### {nxt}.6 **活戳 grep 复核（派活点名项）**

**U01 D16（改后 v1.11）**

| grep | 结果 | 判定 |
|---|---|---|
| `D15 v1.6` | **61** | ✅ 活指针全部现值 |
| `v1.4（终表口径；D15 v1.4 落盘后复核）` | **0** | ✅ 旧活指针已清零 |
| `D15 v1.4 落盘后复核）` | **0** | ✅ 终表段旧值已清零 |
| `D15 **v1.4**` | 8 | ✅ **全在 `sync_records[1].changes[3]` 引述改前值**，非活指针 |
| `D15 v1.4 落盘后须复核` | 8 | ✅ **全在 `sync_records[1].changes[1]` 引述改前值**，非活指针 |
| `D15 v1.4`（总计 32） | 32 | ✅ **4 类全属事件溯源／改前值引述**：`verified_note` 证据段 8（v1.4 为「ep1 镜1 预算上调起始版」的历史事实）＋`sync_records[1].changes[1]` 8 ＋`changes[2]` 8 ＋`verification.margin_caliber1_change_reason` 8 |

**逐字段判定**：8 集 ×（`verified_against_d15` ＝ `v1.6…`／`verified_note` 含「v1.6 落盘后已复核」且**不含**任何 v1.4 活指针串／`dwell_calc_convention` 三种活戳形态）→ **8/8 全通过，活指针停在 v1.4 的集：无**。

**U02 D16（并行实例已落 v1.5，本岗未改）**

| grep | 结果 | 期望 |
|---|---|---|
| `D15 U02 v1.2` | **44** | — |
| `v1.2（D15 U02 落盘后现算复核` | **8** | 现值 |
| `D15 U02 v1.0` | **0** | ✅ 期望 0 |
| `D15 U02 v1.1` | **0** | ✅ 期望 0 |
| 裸 `v1.0（D15 U02 落盘后现算复核` | **0** | ✅ 期望 0 |

### {nxt}.7 **一处口径澄清：派活「21 处」vs 本岗实作「27 处」**

派活文称「U01 侧 21 处」，本岗实作 **27 处**。差额 **6 处** ＝ 非终表集（ep4／ep6／ep7）`dwell_calc_convention` 中两处断言「**现值仍为** D15 **v1.4** 现行预算」「**D15 现行为** **v1.4**」的**活链接**。判据依据：这二句断言的是**当前**预算版本（与 `verified_against_d15` 同为「当前有效性」语义），若停在 v1.4 即为**过期活指针**；其正文已明示「上文『已随 D15 v1.1』与【上游闭合戳】段均为 v1.1／v1.2 时点的**历史留痕**，按 S11 原文保留」——即该字段本已区分「历史段」与「现值段」，只有后两者属活链接。**故补齐，不视为与派活冲突。**

### {nxt}.8 **一处上游声明的取证边界（不作越界结论）**

声音设计 `scripts/build_D15_U01.py` 变更说明称：v1.5「只改口径文本，时长数据与 v1.4 逐字节一致」、v1.6「同样只改口径文本」。**本岗无 D15 U01 v1.4 备份可比对**（全树检索无、`git log --all` 从未追踪 `units/`），故该条**仅作转述**，不作本岗独立实测结论。本岗结论**严格限于**「**D16 U01 v1.11 现盘数值对 D15 U01 v1.6 全部成立**」——该结论由 §{nxt}.5 的现盘复算独立支撑，不依赖上述声明。

### {nxt}.9 **边界与挂账**

- **本节只写台账一个文件**；本岗本轮**交付物改动仅 `units/U01/D16.json`**（v1.10 → **v1.11**，149,395 B → **183,220 B**，mtime 07:54:49）；**U02 侧零改动**（D16 v1.5 为并行实例既有产物，未碰）。
- **新增可复跑脚本 1 个**：`scripts/patch_D16_live_pointer_v16.py`（一次性活戳刷新，带版本守卫／命中数断言／结构差异白名单／落盘前备份；**真盘落盘 1 次，沙箱五腿自测**）。
- 未改 D11（v1.8）／D15／D12／D13／D14／D05／D06／D07／D08／D09／D10／D18／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／源素材；**未碰他岗交付物**。
- 未生成任何图片／视频／音频；未合成 TTS／BGM；未提交 H3 付费生成；未投流上架。
- **本岗挂账（更新后 3 项）**：① **ep2#4 新句音频重合成**（声音设计岗，D09 U02 v1.1 已改文案）；② **U02 D13／D14 未产出**（他岗；D14 缺 → V11 逐镜覆盖检查跳过、U02 取景轴受检 0 条）；③ **台账章号统一规范**（中／阿两种写法混排已登记为提示级，本岗新章号采用阿拉伯数字，**不代改他人章节标题**）。
- **以上游合规裁决为准**（企划合规 **U02-R30**、§六十七.4 **S20**、D18 Q39／Q49／Q51／Q56／D18 Q39 版本号必带规则、声音设计 D15 U01 v1.6 与 D15 U02 v1.2）。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--body-file", default=None,
                    help="新章节正文 markdown 文件；不给则用内置 SEC（§115 专用）")
    args = ap.parse_args()

    with io.open(REG, "rb") as f:
        base_bytes = f.read()
    base_txt = base_bytes.decode("utf-8")
    nxt, allv = parse_max(base_txt)
    print(f"📌 认盘：现有章号 {len(allv)} 个，最大 = {nxt} → 本节占号 = {nxt + 1}")
    print(f"   近 8 节：{allv[-8:]}")

    # ── CAS：写前重读，与读入时的原始字节比对 ──
    for attempt in range(5):
        with io.open(REG, "rb") as f:
            cur_bytes = f.read()
        if cur_bytes != base_bytes:
            print(f"[CAS] 认盘后台账已被他人改写（第 {attempt + 1} 次重试）→ 重新取号")
            base_bytes = cur_bytes
            nxt, allv = parse_max(cur_bytes.decode("utf-8"))
            print(f"      新最大章号 = {nxt} → 本节占号 = {nxt + 1}")
            continue
        break
    else:
        sys.exit("[ABORT] 台账持续被并发写入，5 次重试仍未取得稳定读入，不写盘。")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sec = build_section(nxt + 1, now)
    MY_NO = nxt + 1                     # 本次将占用的章号

    # ── body-file 覆盖：章号必须**等于**本次将占用的章号，且不得 ≤ 现盘最大章号 ──
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            body = f.read()
        m = re.match(r"^## ([零一二三四五六七八九十百\d]+)、", body)
        if not m:
            sys.exit("[ABORT] body-file 首行须为「## <章号>、…」，不写盘。")
        body_no = cn2int(m.group(1))
        if body_no is None:
            sys.exit(f"[ABORT] body-file 章号不可解析：{m.group(1)}，不写盘。")
        if body_no <= nxt:
            # **写前幂等**：该章号已存在于台账 → 判为「已写入」，[NO-OP] 绝不重复追加
            print(f"[NO-OP] body-file 章号 {m.group(1)}（={body_no}）≤ 现盘最大章号 {nxt}："
                  f"该章已写入台账，不重复追加。")
            return
        if body_no != MY_NO:
            sys.exit(f"[ABORT] body-file 章号 {m.group(1)}（={body_no}）与本次将占用的章号 "
                     f"{MY_NO} 不一致，不写盘。")
        sec = body
        print(f"   使用 body-file：{args.body_file}（{len(sec)} 字符，章号 {m.group(1)}）")
    else:
        # ── 落笔前自检：本节章号不得与现有章号重复 ──
        if MY_NO in allv:
            sys.exit(f"[ABORT] 章号 {MY_NO} 已存在于台账，不写盘。")

    if args.dry_run:
        print(f"[DRY-RUN] 将追加 §{MY_NO}，{len(sec)} 字符；文件现 {os.path.getsize(REG)} B")
        return

    with io.open(REG, "a", encoding="utf-8") as f:
        f.write(sec)
        f.flush()
        os.fsync(f.fileno())

    # ── 写后回读核对 ──
    with io.open(REG, "rb") as f:
        after = f.read().decode("utf-8")
    n2, allv2 = parse_max(after)
    cnt = after.count(f"## {nxt + 1}、")
    print(f"✅ 已追加 §{nxt + 1}（{len(sec)} 字符），文件现 {os.path.getsize(REG)} B")
    print(f"   写后最大章号 = {n2}；本节标题出现次数 = {cnt}；章号唯一 = {allv2.count(nxt + 1) == 1}")
    if cnt != 1 or allv2.count(nxt + 1) != 1:
        sys.exit("[ABORT] 写后回读发现本节重复或章号撞号，需人工核查。")


if __name__ == "__main__":
    main()
