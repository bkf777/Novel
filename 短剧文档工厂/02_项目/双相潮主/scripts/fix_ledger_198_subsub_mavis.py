#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fix_ledger_198_subsub_mavis.py —— 定点修复台账 §一百九十八 内**子节号占位符未替换**的字面缺陷。

背景
----
本岗 12:1x 追加 §一百九十八 时，追加器正文模板误用 `{n}`（正确应为 `{nxt}`）⇒ 实跑后
台账内留下 8 行字面量 `### {n}.1 …` 形式的子标题（父章号取号正确，子节号未渲染）。
**已实测确认**：父章 `## 一百九十八、` 正确、Markdown 结构完好，仅子节号是字面量。

处置
----
**不做整文件回滚**（备份回滚会连带覆盖他岗并发写入）⇒ 只对本岗本节做**定点替换**：
把本节内 `### {n}.` 逐条换成 `### 198.`（共 8 条，节号连续 1–8）。

守卫（缺一不可）
----------------
① **作用域限缩**：只在「本节起始行（`## 一百九十八、`）→ 文件末」这一段内替换，
   段外一律不动（台账 2.3 MB，别的章节若含同名字面量不误伤）。
② **数量断言**：段内 `### {n}.` 命中数必须**恰为 8**，且替换后段内不得残留 `{n}.`。
③ **写前并发守卫**：size/mtime/sha256 三锚 CAS（读后被他人改动即中止，不写盘）。
④ **备份先行**：整份复制到 `reports/_bak_ledger_fix_*`。
⑤ **写后回读**：标记计数与子节号连续性复验。

用法：python3 scripts/fix_ledger_198_subsub_mavis.py [--dry-run]
"""
import hashlib
import os
import shutil
import sys
import time

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")
SEC_HEAD = "## 一百九十八、分镜导演"
MARK = "TBZ-12-1x-D11U02内容源同步-守卫四件套-2026-10-23"
EXPECT = 8          # 本节子节数（.1–.8）
SUB = "198"         # 本节子章号


def main():
    dry = "--dry-run" in sys.argv
    snap = open(LEDGER, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(LEDGER)
    txt = snap.decode("utf-8")

    if MARK not in txt:
        print("[ABORT] 台账内未找到本岗标记 %s；不写盘。" % MARK)
        return 2
    lines = txt.split("\n")
    heads = [i for i, l in enumerate(lines) if l.startswith(SEC_HEAD)]
    if len(heads) != 1:
        print("[ABORT] 本节父章命中数 %d ≠ 1；不写盘。" % len(heads))
        return 2
    i0 = heads[0]

    seg = lines[i0:]
    bad = [l for l in seg if l.startswith("### {n}.")]
    if len(bad) != EXPECT:
        print("[IDEMPOTENT/ABORT] 段内 `### {n}.` 命中数 %d ≠ 预期 %d；不写盘。"
              % (len(bad), EXPECT))
        return 0 if not bad else 2

    # 逐条替换为连续子节号（按段内出现顺序 1..8）
    k = 0
    for i in range(i0, len(lines)):
        if lines[i].startswith("### {n}."):
            k += 1
            lines[i] = lines[i].replace("### {n}", "### %s" % SUB, 1)
    if k != EXPECT:
        print("[ABORT] 替换计数 %d ≠ %d；不写盘。" % (k, EXPECT))
        return 2
    out = "\n".join(lines)
    if "{n}." in "\n".join(lines[i0:]):
        print("[ABORT] 段内仍残留占位符；不写盘。")
        return 2
    # 子节号连续性复验
    got = [l.split(".")[1].split(" ")[0] for l in lines[i0:] if l.startswith("### 198.")]
    if got != [str(i) for i in range(1, EXPECT + 1)]:
        print("[ABORT] 子节号不连续：%s；不写盘。" % got)
        return 2

    print("📌 将替换 %d 条子节号：### {n}.x → ### %s.x（1–%d）" % (k, SUB, EXPECT))
    if dry:
        print("（--dry-run：未写盘）")
        for l in lines[i0:i0 + 40]:
            if l.startswith("### "):
                print("   " + l[:80])
        return 0

    cur = open(LEDGER, "rb").read()
    if (len(cur) != snap_size or os.path.getmtime(LEDGER) != snap_mtime
            or hashlib.sha256(cur).hexdigest() != snap_sha):
        print("[ABORT] 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")
        return 3

    bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_fix_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(LEDGER, bak)

    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write(out)

    back = open(LEDGER, encoding="utf-8").read()
    blines = back.split("\n")
    b0 = [i for i, l in enumerate(blines) if l.startswith(SEC_HEAD)]
    if len(b0) != 1 or "{n}." in "\n".join(blines[b0[0]:]):
        shutil.copy2(bak, LEDGER)
        print("[ROLLBACK] 写后复验失败，已回滚。")
        return 4
    print("✅ 已修复 %d 条子节号｜文件现 %d B（%+d）｜备份 %s"
          % (EXPECT, os.path.getsize(LEDGER), os.path.getsize(LEDGER) - snap_size,
             os.path.relpath(bak, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
