#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fix_ledger_104_dup_mavis.py —— 故事架构：**删除台账重复块**（本岗自纠工具，现已加固）

**事故经过**：本岗 `scripts/append_ledger_104_9_delivery_mavis.py` 的首版**幂等守卫写错** ——
用「动态子节号（`### 104.max+1`）」做存在性检查，**恒不命中**（子节号由 max+1 推出，永远
取不到自己）→ 守卫形同虚设 → 幂等复跑**重复写入**了同一份「外发投递留痕」两块：
`### 104.9` 与 `### 104.10`，正文逐字相同。

**⚠️ 本脚本已加固（第二轮）**：初版按**硬编码编号 `### 104.10`** 识别重复块 ——
但本岗随后**合法地**新增了 `### 104.10`（自纠章「幂等守卫写错」），于是初版会把
**合法章节**误判为重复块（实测触发 A3 中止、未写盘，属守卫正确拦下；但若两块正文
恰好相同则可能**误删合法章节**）。→ **改为按「内容标记 + 正文逐字相同」识别**：
重复块 ＝ **正文与 `### 104.9`「外发投递留痕」块逐字相同**的其它 `### 104.N` 节。
**不再按编号判定**，故不会误伤 `### 104.10`（自纠章，正文不同）。

**处置要点**：
  ① 定位 `### 104.9`（必须恰 1 处，含内容标记）→ 取其正文（去尾空行）；
  ② 在其后逐节扫描，找出**正文与之一致**的节 ＝ 重复块（命中须恰 1 处，0 处＝已修复；
     ≥2 处＝中止，须人工核）；
  ③ 断言重复块与保留块正文**逐字相同**（去尾空行后）—— 不同即中止不写盘；
  ④ CAS 守卫（size+mtime+SHA256）＋写后回读（前段/后段逐字节不变、标记恰 1 处、
     **所有 `### 104.N` 正文两两互异**）；
  ⑤ 幂等：重复运行报「已修复，无重复块」且**不再写盘**。

用法：python3 scripts/fix_ledger_104_dup_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    ledp = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledp):
        sys.exit("[ABORT] 台账文件不存在；不写盘。")

    MARK = "外发投递留痕"          # 保留块的内容标记（「外发投递留痕」块）
    KEEP_HEAD = "### 104.9 "      # 保留块的首个子节（投递留痕）

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    def rstrip_blank(ls):
        out = list(ls)
        while out and out[-1].strip() == "":
            out = out[:-1]
        return out

    def body_of(i):
        """从标题**下一行**起算的正文（到下一个 `## ` 或 `### ` 标题之前）。"""
        out = []
        for l in lines[i + 1:]:
            if l.startswith("## ") or l.startswith("### "):
                break
            out.append(l)
        return rstrip_blank(out)

    # A1 保留块：必须恰 1 处，且其正文含内容标记
    keep = [i for i, l in enumerate(lines) if l.startswith(KEEP_HEAD)]
    if len(keep) != 1:
        sys.exit(f"[ABORT] A1 保留块 `{KEEP_HEAD}` 命中 {len(keep)} ≠ 1；不写盘。")
    i9 = keep[0]
    b_keep = body_of(i9)
    if not any(MARK in l for l in lines[i9:i9 + 4]) or len(b_keep) == 0:
        sys.exit(f"[ABORT] A1 保留块正文为空或缺内容标记 `{MARK}`；不写盘。")

    # A2 扫描重复块：正文与保留块**逐字相同**的其它 `### 104.N` 节（不按编号判定）
    secs = [(i, l) for i, l in enumerate(lines) if re.match(r"^### 104\.\d+ ", l)]
    dups = [(i, l) for (i, l) in secs if i != i9 and body_of(i) == b_keep]
    if len(dups) == 0:
        print(f"[NOOP] 未发现与 `{KEEP_HEAD}` 正文逐字相同的重复节；"
              f"已扫描 {len(secs)} 个 `### 104.N` 节，无需修复。")
        return 0
    if len(dups) > 1:
        sys.exit(f"[ABORT] A2 发现 {len(dups)} 个疑似重复节 {[l for _, l in dups]}；不写盘，须人工核。")
    i10, dup_head = dups[0]

    # A3 重复块的删除跨度：**只吃它自己这一节**（前置空行 + 本节正文）
    #    ⚠️ 不得按「下一个 `## `」取跨度 —— 那样会连带吞掉其后的 `### 104.N` 子节。
    start = i10 - 1 if i10 > 0 and lines[i10 - 1].strip() == "" else i10
    nxt = [i for i, l in enumerate(lines)
           if i > i10 and (l.startswith("## ") or l.startswith("### "))]
    if not nxt:
        sys.exit("[ABORT] A3 重复节之后无标题（无法确定删除跨度）；不写盘。")
    end = nxt[0]

    removed = lines[start:end]
    new_lines = lines[:start] + lines[end:]
    new_text = "\n".join(new_lines)

    # A4 CAS 守卫
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A4 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # A5 结构性断言：前段/后段逐字节不变
    pre = "\n".join(lines[:start])
    post = "\n".join(lines[end:])
    assert new_text.startswith(pre), "A5 前段被改动"
    assert new_text.endswith(post), "A5 后段被改动"

    if args.dry_run:
        print(f"[DRY-RUN] 将删除重复节 `{dup_head.strip()}`（第 {start + 1}–{end} 行，"
              f"{len(removed)} 行）；未写盘。")
        return 0

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    # A6 写后回读：标记恰 1 处；所有 `### 104.N` 正文两两互异（无重复块残留）
    back = open(ledp, "rb").read().decode("utf-8")
    blines = back.split("\n")

    def body_of_back(i):
        out = []
        for l in blines[i + 1:]:
            if l.startswith("## ") or l.startswith("### "):
                break
            out.append(l)
        return rstrip_blank(out)

    bsec = [(i, l) for i, l in enumerate(blines) if re.match(r"^### 104\.\d+ ", l)]
    bodies = [body_of_back(i) for i, _ in bsec]
    assert len(bodies) == len(set(map(tuple, bodies))), "A6 写后仍有正文重复的子节"
    # 标记计数按**含标记的节数**算（裸子串在块内可出现多次，不能用 count(MARK)==1）
    marked = [l for (i, l) in bsec if any(MARK in x for x in body_of_back(i))]
    assert len(marked) == 1, f"A6 写后含标记的节数 {len(marked)} ≠ 1"
    assert back.startswith(pre), "A6 写后前段不一致"
    assert back.endswith(post), "A6 写后后段不一致"
    print(f"[OK] 已删除重复节 `{dup_head.strip()}`（第 {start + 1}–{end} 行，{len(removed)} 行）；"
          f"台账 {snap_size} → {len(back.encode('utf-8'))} B；"
          f"§104 子节 {len(bsec)} 个，正文两两互异 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
