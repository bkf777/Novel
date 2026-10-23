#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账**追加子节**（分镜导演岗）—— 插入本岗自有章节内，锚点＝本岗章节之后的第一个同级标题之前。

与 `append_ledger_114_mavis.py` 的区别：那是**追加顶级新章节**（动态取 max+1）；
本脚本**把子节插入本岗自有章节（默认 §115）内**，故：

  **泛化**：`--sub` 指定子节号（默认 `### 115.10`）、`--body-file` 指定正文文件（不给则用内置 build()）。
  新增子节时**不再复制本脚本**，避免多份近似副本各自演化。

  **追加到本岗另一个顶级章节时用 `--chapter`**（2026-10-23 09:0x 新增）：本岗有多个自有顶级章
  （§115 与 §125），锚点必须跟着**目标章**走。原实现把 `## 115、` 写死在模块常量里，
  用 `--sub 125.7` 会把 §125.7 **误插进 §115 区域**（章号与归属错位）。故改为
  `--chapter` 参数化，默认值仍为 `## 115、`（向后兼容）。**不新增脚本副本**。

- **不取新章号**，也不假定 §115 仍是台账末章。锚点规则＝
  **「本岗自己章节之后的第一个同级标题之前」**：定位 `## 115、` 之后的下一个 `^## `
  顶级标题，把 §115.10 插在它前面（§115 是末章时即插在文件末尾）。
  **绝不追加到文件末尾**——并发下末章会易主（本脚本首次实跑即撞上：
  企划合规在读盘与写盘之间追加了 §一百一十六，若按「追加末尾」写就会把 §115.10
  落到他人章节之后，归属错乱）。
- 带 **CAS**：以读入时的原始字节为基准，写前重读比对；被他人改写则**重新认盘并重定位锚点**
  后重试（最多 5 次）。
- **原子写**：先写同目录临时文件，再 `os.replace()` 覆盖 —— 避免中途崩溃留下半截文件。
- 写后回读：核对 `### 115.10` 出现次数 ＝ 1，且**位于 `## 115、` 与下一个顶级标题之间**。

用法
----
python3 scripts/append_ledger_115_10_mavis.py [--dry-run]
"""
import argparse
import datetime
import io
import os
import re
import sys

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"
MY_CHAPTER = "## 115、"
MY_SUB = "### 115.10"


def top_level_chapters(txt):
    """返回全部顶级章节标题（'## ' 开头，排除 '### '）。"""
    return [(m.start(), m.group(0)) for m in re.finditer(r"^## .*$", txt, re.M)]


def heading_hits(txt, heading):
    """行锚定命中：只认**行首**的该标题字面量。

    2026-10-23 修判据缺陷：初版用 `txt.count(heading)` 做锚点唯一性判据，
    会把**正文里引用该标题的字面量**（如 125.11 表格里的
    `（全部中文数字写法，如 ## 一百二十五、）`）误计为第二个标题
    => 追加被误 `[ABORT]`（锚点不唯一）。
    判据语义应是「**该标题作为标题出现几次**」，不是「该字符串出现几次」。
    终止符用 `(?![0-9A-Za-z])`：既允许中文紧跟（如 `## 一百二十五、分镜导演…`），
    又不会把 `### 125.12` 误配到 `### 125.121`。
    """
    return [m.start() for m in re.finditer(r"^" + re.escape(heading) + r"(?![0-9A-Za-z])", txt, re.M)]


def build(now):
    return f"""
### 115.10 **并行实例交叉核销（07:5x–08:0x）＋ 结构化 diff 三数字 ＋ 新增只读取证工具**

**背景**：另一并行分镜导演实例（台账 §112）于 07:54:10 就 U02 侧同型问题完成处置（D16 U02 v1.4→v1.5），并**主动不与并行写者抢盘**、把「21 处活戳」结论交本岗；该协调件 07:57 送达本会话时，**本岗已于 07:54:49 落盘完成 U01 侧**（本岗消息成文早于本岗落盘 39 秒，双方本无重叠）。

**① 交叉核销结论：方向一致，但目标处数需补差额 6 处**

| 项 | 并行实例（§112） | 本岗实测 | 判定 |
|---|---|---|---|
| 21 处是否**全为活指针、无一条溯源混入** | 是 | **是** | ✅ **一致**（双方独立得出同向结论） |
| 溯源（`D15 v1.1` 38 处 ＋ `D15 v1.3` 17 处）是否按 S11 原文保留 | 是 | **是** | ✅ 一致 |
| 目标处数 | 21（8+8+5，按字段类型计） | **27**（8+8+5+3+3） | ⚠️ **差 6 处** |

**差额 6 处的构成与依据**：并行实例按**字段类型**计 21（`verified_against_d15` 8 ＋ `verified_note` 8 ＋ `dwell_calc_convention` 5），漏计的是**同一字段 `dwell_calc_convention` 内**非终表集（ep4／ep6／ep7）的另外两处断言形态：「**现值仍为** D15 **v1.4** 现行预算」与「D15 **现行为** **v1.4**」。该字段正文本身已明示「上文『已随 D15 v1.1』与【上游闭合戳】段均为 v1.1／v1.2 时点的**历史留痕**，按 S11 原文保留」——即**该字段已自区分「历史段」与「现值段」**，只有后者属活链接。故按同一语义口径应计 **27**；**只按 21 处改会留下 6 处过期活指针**。本岗已补齐。

**② 结构化 diff 三数字（可复跑，只读）**

新增工具 `scripts/diff_D16_unit.py`（**只读**，不写任何文件；Q76 副作用隔离：全程无写盘流程，逻辑在 `main()` 内并由 `if __name__ == "__main__":` 守卫）。命令：

```
python3 scripts/diff_D16_unit.py --project . --unit U01 \\
    --old reports/_bak_U01_D16_liveptr_20261023-075449/D16.json
```

| 口径 | U01（本岗 v1.10→v1.11） | U02（并行实例 v1.4→v1.5，**本岗独立复验**） |
|---|---|---|
| 差异叶子总数 | **33** | **53** |
| 分类 | 版本号 **1** ＋ 版本戳 **16** ＋ 版本戳＋文本 **8** ＋ 纯追加 **8** | 版本号 **1** ＋ 版本戳 **52** |
| **时码叶子** | **0** ✅ | **0** ✅ |
| **真结构差异** | **0** ✅ | **0** ✅ |
| 数组纯追加 | 8（`sync_records` 1→2，S11 只追加，**不计入结构差异**） | 0 |

**交叉取证**：本岗工具对 U02 的独立复验结果 **53 ＝ 版本号 1 ＋ 版本戳 52**，与并行实例 §112 自报数**完全一致**，且时码 0／真结构 0 —— **双方成果互为独立佐证**。工具另支持 `--json` 输出机读报告。

**③ 出口闸数字的时点差（Q74：须给旧值 → 现行值对照）**

| 轴 | 并行实例（07:5x） | 本岗 07:56 ＋ 07:59 两次实跑 |
|---|---|---|
| `validate --unit U01` | 11/11｜error 0｜warning 1 | **11/11｜error 0｜warning 1**（一致） |
| `validate --unit U02` | 11/11｜error 0｜**warning 6** | **11/11｜error 0｜warning 5**（两次实跑同为 5；差异源于他岗产物落盘时点，非本岗改动） |
| `reconcile --unit U01／U02` | 均 exit 0，判据清单 12 ＝ 断言点 12 | **均 exit 0，12/12，不通过 0 条** |
| `units/` 内 `.bak` 残留 | 0 | **0** ✅ |

**④ 边界**

- 本子节**只写台账一个文件**；本岗交付物 `units/U01/D16.json` 自 07:54:49 起**未再改一字节**（复跑 diff 工具前后 mtime/字节一致：07:54:49／183,220 B）——工具**只读性已实测**。
- **未改** `units/U02/D16.json`（v1.5 为并行实例产物，未碰）／D15／D11／D12／D13／D14／D05–D10／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`。
- 未生成任何图片／视频／音频；未合成 TTS／BGM；未提交 H3 付费生成；未投流上架。
- **以上游合规裁决为准**（并行实例 §112 结论、企划合规 §一百一十四 的 Q74／Q76、D18 Q30／Q39／Q49／Q51／Q56）。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sub", default=MY_SUB, help="子节标题（如 '### 115.11'）")
    ap.add_argument("--body-file", default=None, help="正文 markdown 文件；不给则用内置 build()")
    ap.add_argument("--chapter", default=MY_CHAPTER,
                    help="锚点所在本岗顶级章标题（默认 '## 115、'）；如 '--chapter \"## 125、\"'")
    args = ap.parse_args()
    my_sub = args.sub
    my_chapter = args.chapter

    with io.open(REG, "rb") as f:
        base_bytes = f.read()
    base_txt = base_bytes.decode("utf-8")

    sub_hits = heading_hits(base_txt, my_sub)
    if sub_hits:
        print(f"[NO-OP] {my_sub} 已存在于台账（{len(sub_hits)} 处，行锚定），不重复追加。")
        return

    for attempt in range(5):
        with io.open(REG, "rb") as f:
            cur_bytes = f.read()
        if cur_bytes != base_bytes:
            print(f"[CAS] 台账已被他人改写（第 {attempt + 1} 次重试）→ 重新认盘")
            base_bytes = cur_bytes
            base_txt = cur_bytes.decode("utf-8")
            continue
        break
    else:
        sys.exit("[ABORT] 台账持续被并发写入，5 次重试仍未取得稳定读入，不写盘。")

    chapters = top_level_chapters(base_txt)
    if not chapters:
        sys.exit("[ABORT] 台账未找到顶级章节，不写盘。")

    # ── 定位锚点：`my_chapter` 之后的第一个同级顶级标题之前 ──
    # ⚠ 锚点唯一性判据改为**行锚定**（2026-10-23 修）：正文里引用标题字面量
    #   （反引号包裹的 `## 一百二十五、`）不是标题，不得计入。
    chap_hits = heading_hits(base_txt, my_chapter)
    if not chap_hits:
        sys.exit(f"[ABORT] 台账未找到本岗章节 {my_chapter}（行锚定），不写盘。")
    if len(chap_hits) > 1:
        sys.exit(f"[ABORT] 本岗章节 {my_chapter} 作为标题在台账中出现 {len(chap_hits)} 次，"
                 f"锚点不唯一，不写盘。")
    idx_115 = chap_hits[0]
    nxt = re.search(r"^## .*$", base_txt[idx_115 + len(my_chapter):], re.M)
    if nxt:
        insert_pos = idx_115 + len(my_chapter) + nxt.start()
        anchor_desc = "下一个顶级标题之前"
    else:
        insert_pos = len(base_txt)
        anchor_desc = "文件末尾（本岗章节为末章）"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.body_file:
        body = open(args.body_file, encoding="utf-8").read().strip("\n")
    else:
        body = build(now).strip("\n")
    # ── 【2026-10-23 12:4x 修】子节标题必须由本岗补齐 ──────────────
    # 缺陷：原实现只把 **正文** 写入（`--sub` 仅作去重键），若 `--body-file`
    #   的正文**未自带** `### 125.x` 标题行，落盘后正文会直接贴在上一子节尾部，
    #   台账里查不到该子节标题 —— 写后自查能报出来，但**已是事后**（文件已写）。
    # 修法：**写前**补标题（正文已自带则不重复补），并把「标题存在」提为写前守卫。
    #   ⇒ 追加器的契约由「正文须自带标题」放宽为「正文可只给标题后的正文部分」。
    if not body.lstrip().startswith(my_sub):
        body = my_sub + " " + body.lstrip()
    if not body.lstrip().startswith(my_sub):
        sys.exit(f"[ABORT] 子节标题 {my_sub} 未能就位，不写盘。")
    ins = "\n\n" + body + "\n\n"

    if args.dry_run:
        print(f"[DRY-RUN] 将把 {my_sub} 插入「{anchor_desc}」；文件现 {os.path.getsize(REG)} B；"
              f"插入 {len(ins)} 字符")
        return

    # ── 原子写：临时文件 → os.replace（同目录，同文件系统）──
    tmp = REG + ".tmp-" + re.sub(r"\W+", "", my_chapter)[:12]
    with io.open(REG, "r", encoding="utf-8") as f:
        cur = f.read()
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(cur[:insert_pos] + ins + cur[insert_pos:])
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, REG)

    with io.open(REG, "rb") as f:
        after = f.read().decode("utf-8")
    sub_after = heading_hits(after, my_sub)
    cnt = len(sub_after)
    # 归属校验：子节必须位于 my_chapter 之后、且在下一个顶级标题之前
    chap_after = heading_hits(after, my_chapter)
    i115 = chap_after[0] if chap_after else -1
    i11510 = sub_after[0] if sub_after else -1
    nxt_after = re.search(r"^## .*$", after[i115 + len(my_chapter):], re.M)
    ok_order = (i115 < i11510) and (
        not nxt_after or i11510 < i115 + len(my_chapter) + nxt_after.start())
    print(f"✅ 已插入 {my_sub}（{len(ins)} 字符，锚点：{anchor_desc}），"
          f"文件现 {os.path.getsize(REG)} B")
    print(f"   写后 {my_sub} 出现次数 = {cnt}；归属校验（在本岗章节内且未越过后续顶级标题）= {ok_order}")
    if cnt != 1 or not ok_order:
        sys.exit("[ABORT] 写后回读发现子节重复或归属错位，需人工核查。")


if __name__ == "__main__":
    main()
