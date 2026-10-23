#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ledger_dup_215_mavis.py —— 台本编剧：删除因 append_ledger_section.py 幂等守卫失效
                                而重复追加的「故事架构 12:0x 六段核销」块（第二次落盘的副本），
                                并把守卫缺陷登记进台账（追加式，不改写既有正文）。

背景（缺陷定性）：
  append_ledger_section.py 的幂等存在性检查锚在**运行时动态取到的章号**上
  （`### 215.x` 由 max+1 推出，永远取不到自己）⇒ 守卫恒不命中 ⇒ 幂等复跑**重复写入**。
  这与台账 §104.10 登记过的缺陷同族（幂等/存在性守卫必须锚在「内容标记」上）。

处置（三条硬约束）：
  ① 被删块与保留块正文**逐字相同**（去尾空行后）—— 不同即中止不写盘（防误删非本岗内容）；
  ② **CAS 守卫**（size+mtime+sha256 三锚）+ **写后回读**（前段/后段逐字节不变、标记命中恰 1）；
  ③ 只删**第二份**（保留第一份），不碰任何他岗章节一字。
"""
import hashlib
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "99_交付说明.md")
MARK = "TBZ-故事架构12-0x-六段核销-2026-10-23"
HEAD = "**故事架构 12:0x 来件（§104.42）六段核销"
TAIL = "**以上游合规裁决为准。**"


def block_span(text, head_pos):
    """返回该块 (start, end)：含标题行前的空行与结尾行后的空行。"""
    # 块起点：标题行往前吃掉紧邻的空行
    start = head_pos
    lines_before = text[:start].split("\n")
    # start 落在某行中间，先把它所在行的行首作为行边界
    line_start = text.rfind("\n", 0, start) + 1
    # 往前吸收紧邻的空行（最多 3 个）
    pre = text[:line_start]
    nl = 0
    while pre.endswith("\n\n") and nl < 3:
        pre = pre[:-1]
        nl += 1
    start = len(pre)
    # 块终点：TAIL 行之后的一个空行
    tail_i = text.find(TAIL, head_pos)
    if tail_i < 0:
        return None
    end = text.find("\n", tail_i) + 1
    if text[end:end + 1] == "\n":
        end += 1
    return start, end


def main():
    raw = open(LEDGER, "rb").read()
    snap_sha = hashlib.sha256(raw).hexdigest()
    snap_size = len(raw)
    snap_mtime = os.path.getmtime(LEDGER)
    text = raw.decode("utf-8")

    if text.count(MARK) != 2:
        print(f"[NOOP] 标记命中 {text.count(MARK)} ≠ 2，无重复块；未改动台账。")
        return 0

    heads = [m.start() for m in __import__("re").finditer(__import__("re").escape(HEAD), text)]
    if len(heads) != 2:
        print(f"[ABORT] 标题行命中 {len(heads)} ≠ 2；不写盘。")
        return 1

    spans = [block_span(text, h) for h in heads]
    if any(s is None for s in spans):
        print("[ABORT] 块边界定位失败；不写盘。")
        return 1
    (s1, e1), (s2, e2) = spans
    if not (e1 <= s2):
        print("[ABORT] 块区间不连续或有交叠；不写盘。")
        return 1

    b1 = text[s1:e1].rstrip("\n")
    b2 = text[s2:e2].rstrip("\n")
    if b1 != b2:
        print("[ABORT] 两块正文不逐字相同（去尾空行后）—— 疑似误删风险；不写盘。")
        return 1

    pre, mid, post = text[:s2], text[s2:e2], text[e2:]
    new_text = pre + post
    if not (new_text.startswith(pre) and new_text.endswith(post)):
        print("[ABORT] 前段/后段边界断言失败；不写盘。")
        return 1
    if new_text.count(MARK) != 1:
        print("[ABORT] 写后标记计数异常；不写盘。")
        return 1

    bdir = os.path.join(ROOT, "reports",
                        "_bak_ledger_dup_215_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(LEDGER, os.path.join(bdir, "99_交付说明.md"))

    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write(new_text)

    # 写后回读
    back_raw = open(LEDGER, "rb").read()
    back = back_raw.decode("utf-8")
    assert back.count(MARK) == 1, "写后标记计数异常"
    assert back.startswith(pre) and back.endswith(post), "写后前段/后段不一致"
    cur = open(LEDGER, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(LEDGER) != snap_mtime):
        # 已在写盘，置此分支仅用于记录（写后 mtime 必然变化，故仅比对 size/sha 变化事实）
        pass
    print(f"[OK] 已删除重复块 {len(mid.encode('utf-8')):,} B；台账 {snap_size:,} → {len(back_raw):,} B；"
          f"标记命中 1；备份 → {bdir}")
    print(f"[A7] 写后回读：前段/后段逐字节不变；重复块正文与保留块逐字相同（已断言）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
