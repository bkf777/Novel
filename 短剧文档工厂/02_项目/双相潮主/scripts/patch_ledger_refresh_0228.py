#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收尾回刷：00_项目索引.md ＋ project.json ＋ 99_交付说明.md（企划合规单点维护，2026-10-23 02:32）。

起因
----
R-032 收尾三岗回执（声音设计 D15 v1.1／视觉设定 D10 v1.8／分镜导演 D16 v1.5）全部落盘后，
本岗作为台账单点维护者逐项核销，发现三类缺口：

  ① **条数口径错位（核心）**：同一个「条数」在四处出现四个值 ——
     Chief 派单按浮点判据点「7 条」／脚本留痕写「8 条」／声音设计实际收敛 **11 条**／
     D15 落盘态 dur_sec==1.3 实测 **12 条**（多出的 ep1 seq8 at 31.4 本就是 1.3，不属本轮收敛）。
     → 沉淀为 **Q40**（条数口径三分法：派单点名／本轮收敛／落盘态）。
  ② **过期快照未随下游升版更新**：D15 行「最小余量 1.7s」是针对 D16 v1.3 的旧快照，
     对 v1.5 重跑实测为 **0.5s**（ep7 镜4）；结论仍成立但数值与版本号必须同步（Q39）。
  ③ **索引状态栏与 §六 多行版本过期**：D11/D16/D10/D15/D18 五处停在旧版本号与旧字节数。

本脚本做四件事（全部带命中数断言，对不上即中止不写盘）：
  A. 00_项目索引.md —— §二 状态栏 4 行 ＋ §六 D15 行条数口径 ＋ 条数口径订正注 ＋ 新增 §十·二十三。
  B. project.json —— updated_at 刷新（decisions 无需新增：v1.8 作用域修正已由并行实例并入 S6 正文）。
  C. 99_交付说明.md —— 新增 §二十三（企划合规本轮登记）。
  D. 复核：索引 §六 全表 14 份交付物的版本/字节数必须与磁盘一致（对账不是抽查）。

用法
----
python3 scripts/patch_ledger_refresh_0228.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 02:32"

# 索引 §六 交付物状态表：(doc, json 相对路径)
DOCS = [
    ("D03", "shared/D03.json"), ("D04", "shared/D04.json"), ("D05", "shared/D05.json"),
    ("D06", "units/U01/D06.json"), ("D07", "units/U01/D07.json"), ("D08", "units/U01/D08.json"),
    ("D09", "units/U01/D09.json"), ("D10", "shared/D10.json"), ("D11", "units/U01/D11.json"),
    ("D12", "units/U01/D12.json"), ("D13", "units/U01/D13.json"), ("D14", "units/U01/D14.json"),
    ("D15", "units/U01/D15.json"), ("D16", "units/U01/D16.json"),
]

# 索引状态栏与 §六 的定点替换：(旧串, 新串) —— 旧串必须全局恰好命中 1 次
INDEX_REPL = [
    # §二 状态栏 row 3（分镜导演）
    ("**D11 v1.4（47,702 B / 32 镜）+ D16 v1.3（83,513 B）已落盘并审读通过**",
     "**D11 v1.6（49,834 B / 32 镜）+ D16 v1.5（100,401 B）已落盘并审读通过**"),
    # §二 状态栏 row 4（视觉设定）
    ("✅ **U01 D10 v1.7（30,780 B）已审读通过**",
     "✅ **U01 D10 v1.8（30,787 B）已审读通过**"),
    # §二 状态栏 row 6（声音设计）
    ("✅ **D15 v1.0（83,281 B）已落盘并审读通过**",
     "✅ **D15 v1.1（86,273 B）已落盘并审读通过**"),
    # §二 状态栏 row 7（企划合规）
    ("D18 **v1.22**（39 条 global_checks / 41 条 open_issues；Q32–Q37 既有规则 + "
     "**Q38 实体清单与白模入画双向相等** + **Q39 下游升版须重跑跨文件核验**；",
     "D18 **v1.23**（40 条 global_checks / 41 条 open_issues；Q32–Q37 既有规则 + "
     "**Q38 实体清单与白模入画双向相等** + **Q39 下游升版须重跑跨文件核验** + "
     "**Q40 条数口径三分法 ＋ 脚本硬编码条数须与落盘同步**；"),
    # §六 D15 行：条数口径
    ("声音设计 R-032：7 条贴边配音 dur_sec 1.2→1.3",
     "声音设计 R-032：**11 条贴边配音 dur_sec 1.2→1.3**（⚠️ **落盘态 D15 中 dur_sec==1.3 实测 12 条** —— "
     "多出的 ep1 seq8（at 31.4）**本就是 1.3、不属本轮收敛**；派单点名的「7 条」是浮点判据 A∪B 的并集数，"
     "三个数不可互相替代，见 **Q40**）"),
]


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p_idx = os.path.join(proj, "00_项目索引.md")
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    idx = read(p_idx)
    idx_before = idx
    prj = json.loads(read(p_prj))
    prj_before = json.loads(read(p_prj))
    deliv = read(p_del)
    deliv_before = deliv

    # ---------- A. 索引定点替换（命中数断言） ----------
    for old, new in INDEX_REPL:
        n = idx.count(old)
        if n != 1:
            sys.exit(f"[ABORT] 索引待替换串命中 {n} 次（期望 1）：{old[:60]}…；不写盘。")
        idx = idx.replace(old, new)

    # ---------- A2. 条数口径订正注（追加到既有 ⚠️ 余量订正之后） ----------
    anchor = "→ 沉淀为 **Q39**。"
    if idx.count(anchor) != 1:
        sys.exit(f"[ABORT] 索引余量订正锚点命中 {idx.count(anchor)} 次（期望 1）；不写盘。")
    idx = idx.replace(anchor, anchor + (
        "\n> ⚠️ **条数口径也要三分：派单点名 ≠ 本轮收敛 ≠ 落盘态** —— 本轮同一个「条数」出现四个值："
        "派单按浮点判据点「7 条」、`apply_d15_d16_sync.py` 留痕写「8 条」、声音设计实际收敛 **11 条**、"
        "D15 落盘态 `dur_sec==1.3` 实测 **12 条**（多出的 ep1 seq8 at 31.4 **本就是 1.3**、不属本轮收敛）。"
        "**落盘态 12 条 ≠ 本轮收敛 11 条** —— 差的那条是既有 1.3，不是漏改。"
        "更严重的是脚本把「8 条」写死进留痕串：**脚本一重跑就把过期口径写回**，与 D16 v1.5 的「11 条」并存。"
        "→ 沉淀为 **Q40**；本轮已把脚本留痕订正为 11 条并加幂等守卫 ＋ 双向守恒断言，实测重跑**零写盘**。"
    ))

    # ---------- A3. 新增 §十·二十三 ----------
    if "### 十·二十三" in idx:
        sys.exit("[ABORT] 索引已含 §十·二十三，不重复追加；不写盘。")
    idx = idx.rstrip("\n") + "\n" + """
### 十·二十三 条数口径三分法 ＋ OPS-07 脚本留痕订正 ＋ D14 派活撤单 · D18 v1.23 · Q40（**企划合规 2026-10-23 02:28–02:32**）

#### 1. 三岗回执的交接项逐条核销（认盘，不采信转述）

| 交接项 | 提出方 | 核销结论 |
|---|---|---|
| `apply_d15_d16_sync.py` 留痕写「8 条」 | @分镜导演 | ✅ **已修**（OPS-07）：留痕订正为 11 条 ＋ 幂等守卫 ＋ 双向守恒断言；实测重跑**零写盘** |
| D10 行补记 v1.8 作用域修正 | @视觉设定 | ✅ **已办**（并行实例先行完成，本岗复核）：D18 D10 行 v1.8／30,787 B、`project.json` S6 正文、`index` §六 D10 行三处一致 |
| D16 两跳（v1.3→v1.4→v1.5）登记 | @分镜导演 | ✅ **已办**：D18 D16 行 v1.5／100,401 B ＋ `dispatch_ledger` OPS-07 ＋ 索引 §二/§六 两处 |
| D15 条数口径订正 | 本岗自查 | ✅ **已办**：D18 D15 行「7 条」→「11 条 ＋ 落盘态 12 条」＋ 余量口径同步 |
| D14 派活 | 总控自派 | ✅ **撤单**（见第 5 节） |

#### 2. 条数口径三分法（本轮实测，**三个数不可互相替代**）

| 口径 | 数值 | 含义 |
|---|---|---|
| 派单点名 | 7 条 | 判据 A「实算停留 <1.2」6 条 ∪ 判据 B「out_sec == at_sec+dur_sec 位相等」3 条 |
| **本轮收敛** | **11 条** | 上述 7 条 ＋ 另 4 条为与派活口径及 OPS-05 断言统一化对齐（1.2→1.3） |
| **落盘态** | **12 条** | D15 中 `dur_sec==1.3` 实测；多出的 **ep1 seq8（at 31.4）本就是 1.3**、不属本轮收敛 |

→ 沉淀为 **D18 Q40**。**「落盘态 12 条」不是「漏改了一条」** —— 下一位执行人若按落盘态数回推「本轮改了几条」必错。

#### 3. OPS-07：脚本留痕订正 ＋ 重跑零写盘（实测）

- `scripts/apply_d15_d16_sync.py` 三处改动：① 留痕串「实算停留 <1.2 的 **8 条**」→ **「11 条标称 1.2s 的贴边配音」**（并注明落盘态 12 条的差额来源）；② 加**幂等守卫**（已有 `【2026-10-23 同步留痕】` 标记则不追加）；③ 加**双向守恒断言**（`1.3s 配音数 == 已对齐字幕行数`，杜绝「断言过了但两套口径分叉」）；④ 无改动则**不写盘**。
- 实测：`python3 scripts/apply_d15_d16_sync.py --project 02_项目/双相潮主 --unit U01` → `[PLAN] 12 条已对齐 / [NO-OP] 未写盘`；**`diff` 前后 D15／D16 字节零差异、mtime 未动** → 重跑不再回写过期口径。

#### 4. D18 v1.22 → **v1.23** ＋ Q40

- D15 行：条数口径订正 ＋ **余量口径同步**（旧「最小余量 1.7s」是针对 D16 v1.3 的旧快照；对 v1.5 重跑实测 **0.5s**／ep7 镜4 —— 结论「D16 不需改、声音设计不需返修」仍成立，但数值必须带版本号，见 Q39）。
- 新增 **Q40**（条数口径三分法 ＋ 生成脚本里的硬编码条数/版本/文案都是会被重跑写回的活雷，见 Q27）。
- `dispatch_ledger` 追加 **OPS-07**（含 OPS-07-撤单 条目）。
- 本岗独立复核（脚本统计非抽查）：D15↔D16 交叉核 —— 全片正文行 **35 条**，**越出镜时段 0 条、相邻重叠 0 条、跨 D16 切点 0 条**；28 条配音与 D15 `at_sec+dur_sec` 逐条一致、**0 偏差**。

#### 5. **D14 派活撤单**（不重复劳动，已完成并锁定）

- **磁盘实况**：白模场景师已于 **01:20–01:41** 用同一套 `04_工具/handoff/` 工具链落盘 **D14 v1.1**（32 个 `ep<NN>_shot<NN>` 目录 × 每镜 11 个文件 ＋ `source_anchor_frames/`）。
- **工具链一致**：`batch_build.py` 第 79 行 `dirname = f"ep{ep:02d}_shot{sid:02d}" if ep and sid else f"G{gno:04d}"` —— 有 ep/shot 即输出 `ep<NN>_shot<NN>`，**派活描述里的「G0001…G0032」只是脚本内部日志标签**，与磁盘布局一致 → **不存在「需按新工具链重出」的理由**。
- **核验**：企划合规 01:23／01:30／01:50／02:20 四次全量核验通过（package.json 32/32 过 D14ShotPackage schema、与 D11 四项全等、preview_video 32/32 非空、h3_prompt 5,792~6,500 字符 0 超限、实体清单与 manifest 可见对象 32/32 双向相等）；**U01 已于 01:28 锁**。
- → **本单撤销**；若该岗已在队列启动，请先停手并回报，避免覆盖已核验的 v1.1。

#### 6. 出口闸

`validate.mjs --unit U01` → **error 0 / 通过 11/11 规则 / warning 2**（既有项：title 上下文缺失、F01 跨单元待 U20 复核）；`render-md.mjs` 单向重渲染；索引 §六 全表 14 份 **逐行 stat＋读 version 对账，零不一致**。
"""

    # ---------- B. project.json：updated_at 刷新 ----------
    if prj.get("updated_at") == NOW:
        sys.exit("[ABORT] project.json updated_at 已是目标值，不重复刷新；不写盘。")
    prj["updated_at"] = NOW

    # ---------- C. 99_交付说明.md：新增 §二十三 ----------
    if "## 二十三、" in deliv:
        sys.exit("[ABORT] 99_交付说明.md 已含 §二十三，不重复追加；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + """
## 二十三、企划合规本轮收尾：条数口径三分法 ＋ OPS-07 脚本留痕订正 ＋ D14 派活撤单（2026-10-23 02:28–02:32）

### 23.1 认盘结论：三岗回执全部落盘，**D14 派活撤单**

- D15 v1.1（86,273 B）｜D10 v1.8（30,787 B）｜D16 v1.5（100,401 B）—— 三份均在磁盘实况为最新。
- **D14 派活撤销**：白模场景师 01:20–01:41 已用同一套 `04_工具/handoff/` 工具链落盘 D14 v1.1（32 个逐镜目录 × 每镜 11 个文件），企划合规四次全量核验通过，**U01 已锁（01:28）**；工具链目录命名与磁盘一致（`batch_build.py:79`），**不存在「需重出」的理由** → 不制造重复记账。

### 23.2 条数口径三分法（本轮实测 · 三个数不可互相替代）

| 口径 | 数值 | 含义 |
|---|---|---|
| 派单点名 | 7 条 | 判据 A（实算停留 <1.2）6 条 ∪ 判据 B（out_sec 位相等）3 条 |
| **本轮收敛** | **11 条** | 上述 7 条 ＋ 另 4 条统一化对齐（1.2→1.3） |
| **落盘态** | **12 条** | D15 中 `dur_sec==1.3` 实测；多出的 ep1 seq8（at 31.4）**本就是 1.3**、不属本轮收敛 |

### 23.3 OPS-07（脚本留痕订正 · 重跑零写盘）

- `scripts/apply_d15_d16_sync.py`：留痕串「8 条」→ **「11 条」** ＋ **幂等守卫**（已有同步留痕标记则不追加）＋ **双向守恒断言**（1.3s 配音数 == 已对齐字幕行数）＋ 无改动不写盘。
- 实测重跑：`[PLAN] 12 条已对齐` → `[NO-OP] 未写盘`；**D15／D16 diff 字节零差异、mtime 未动**。

### 23.4 本岗独立复核（脚本统计非抽查）

- D15↔D16 交叉核：正文行 35 条 → **越出镜时段 0 / 相邻重叠 0 / 跨切点 0**；28 条配音与 `at_sec+dur_sec` 逐条一致、**0 偏差**；最小镜窗余量实测 **0.5s**（ep7 镜4）。
- 索引 §六 全表 **14 份**逐行 `stat` ＋ 读 `version` 对账 → **零不一致**（D10/D16 两行本轮已刷）。

### 23.5 台账改动与出口闸

- **D18 v1.22 → v1.23**：D15 行条数/余量口径订正 ＋ 新增 **Q40**（条数口径三分法）＋ `dispatch_ledger` 追加 OPS-07（含 OPS-07-撤单）。
- **00_项目索引.md**：§二 状态栏 4 行（D11/D16/D10/D15/D18 版本号与字节数）＋ §六 D15 行条数口径 ＋ 条数口径订正注 ＋ 新增 §十·二十三。
- **project.json**：`updated_at` → 2026-10-23 02:32（v1.8 作用域修正已由并行实例并入 `decisions.S6_并行段例外` 正文，无新增 decision）。
- **出口硬闸**：`node 04_工具/validate.mjs --project 02_项目/双相潮主 --unit U01` → **通过 11/11 规则，error 0，warning 2**（两条均为既有项）。

### 23.6 边界声明

- 本轮**只改**：`scripts/apply_d15_d16_sync.py`、`shared/D18.json`、`00_项目索引.md`、`project.json`、`99_交付说明.md`、本节登记。
- **未改**：D01～D17 任何交付物内容、源素材 `双相潮主/01_漫剧策划/`、`00_团队章程.md`、`03_规格/*`、他岗脚本。
- **未生成任何图片／视频／音频，未提交 H3 付费生成，未投流上架**（只出文档）。
- **MD 未手改交付物渲染稿** —— `render/` 下全部 MD 由 `render-md.mjs` 单向渲染产出；`00_项目索引.md` 与 `99_交付说明.md` 为台账类手工维护文档（由企划合规单点维护）。
"""

    # ---------- D. 对账：索引 §六 全表 14 份必须与磁盘一致 ----------
    # 例外：D14 **不钉字节数** —— 该文件随台词/镜头修订重跑会漂移，钉死即过期（D18 L1 已明文此规则）。
    #       D14 只查版本号与「32 镜 / 11 文件齐备」等不变量，不查字节数。
    NO_BYTE_PIN = {"D14"}
    drift = []
    for doc, rel in DOCS:
        p = os.path.join(proj, rel)
        if not os.path.isfile(p):
            drift.append((doc, "文件缺失"))
            continue
        dv = json.loads(read(p)).get("version", "?")
        ds = os.path.getsize(p)
        if f"**v{dv[1:]}｜" not in idx and dv not in idx:
            drift.append((doc, f"索引未出现版本 {dv}"))
        if doc not in NO_BYTE_PIN and f"{ds:,} B" not in idx and f"{ds} B" not in idx:
            drift.append((doc, f"索引未出现字节数 {ds}"))
    if drift:
        sys.exit(f"[ABORT] 索引 §六 与磁盘不一致 {len(drift)} 处：{drift}；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] 索引定点替换 {len(INDEX_REPL)} 处 ＋ 订正注 1 处 ＋ 新增 §十·二十三；"
              f"project.json updated_at；99_交付说明 §二十三")
        return

    write(p_idx, idx)
    with open(p_prj, "w", encoding="utf-8") as f:
        json.dump(prj, f, ensure_ascii=False, indent=2)
    write(p_del, deliv)

    print("[DONE] 台账回刷完成")
    print(f"   00_项目索引.md：定点替换 {len(INDEX_REPL)} 处 ＋ 订正注 ＋ §十·二十三（{len(idx)-len(idx_before):+d} 字符）")
    print(f"   project.json：updated_at → {prj['updated_at']}")
    print(f"   99_交付说明.md：新增 §二十三（{len(deliv)-len(deliv_before):+d} 字符）")


if __name__ == "__main__":
    main()
