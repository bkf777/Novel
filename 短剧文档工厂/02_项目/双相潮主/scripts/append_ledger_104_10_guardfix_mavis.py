#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_10_guardfix_mavis.py —— 故事架构：**台账追加脚本幂等守卫写错 → 重复块已删
                                            并重写守卫**的自纠留痕（2026-10-23）

**事故**：`scripts/append_ledger_104_9_delivery_mavis.py` 首版的**幂等守卫**用
「动态子节号（`### 104.max+1`）」做存在性检查 —— **恒不命中**（子节号由 max+1 推出，
永远取不到自己）→ 守卫形同虚设 → 幂等复跑**重复写入**了同一份「外发投递留痕」两块：
`### 104.9`（第 7501 行）与 `### 104.10`（第 7515 行），正文逐字相同。

**处置**：`scripts/fix_ledger_104_dup_mavis.py`（新增，本岗名下）精确定位并删除 §104.10
的插入跨度（14 行，含前置空行、至下一个 `## ` 同级标题之前）；断言「被删块与保留块正文
逐字相同（去尾空行后）」否则中止不写盘；CAS 守卫（size+mtime+SHA256）＋写后回读
（前段/后段逐字节不变、104.9 恰 1 处、104.10 恰 0 处）。
**实删：868,601 → 866,397 B ＝ 首次正确落盘后的字节数 → 重复块彻底清除。**
两端幂等复验：修复脚本报 `[NOOP]`、追加脚本报 `[IDEMPOTENT]`，均不再写盘。

⚠️ 本脚本**锚点＝「本岗章节之后的第一个同级标题之前」**（Q72／OPS-20），
   子节号在 §一百零四 下动态取 max+1，**幂等守卫锚在内容标记上**（不是动态编号）。
用法：python3 scripts/append_ledger_104_10_guardfix_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import sys
from datetime import datetime


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


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
    # 标记取**无粗体包裹**的稳定子串：标题里 `**` 包住整句，带 `**` 的串匹配不到（已栽过一次）
    MARK = "本岗自纠：台账追加脚本的幂等守卫写错"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    # A1 本岗章节命中数恰为 1
    mine = [i for i, l in enumerate(lines) if l.startswith(MY_HEADER)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    i0 = mine[0]

    # A4 追加点＝本岗章节之后的第一个同级标题
    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    # A3 幂等：**内容标记**判定（动态编号恒不命中，已是本岗第二次栽在同一处）
    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK}；未改动台账。")
        return 0

    # A2 动态子节号
    used = set()
    for l in lines[i0:ins]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    sub_max = max([n for (a, n) in used if a == 104], default=0)
    n = sub_max + 1
    sub_head = f"### 104.{n}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""{sub_head} **本岗自纠：台账追加脚本的幂等守卫写错 → 重复块已删并重写守卫**（{now}）

**事故**：`scripts/append_ledger_104_9_delivery_mavis.py` 首版的**幂等守卫**用「动态子节号（`### 104.max+1`）」做存在性检查 —— **恒不命中**（子节号由 max+1 推出，永远取不到自己）→ **守卫形同虚设** → 幂等复跑**重复写入**了同一份「外发投递留痕」两块：`### 104.9`（第 7501 行）与 `### 104.10`（第 7515 行），正文逐字相同。

**处置**（`scripts/fix_ledger_104_dup_mavis.py`，新增、本岗名下）：
① 精确定位重复块 `### 104.10`（必须恰 1 处）与其插入跨度（14 行，含前置空行、至下一个 `## ` 同级标题之前）；
② 断言「被删块与保留块正文逐字相同（去尾空行后）」—— 不同即**中止不写盘**（防止误删非本岗自写内容）；
③ **CAS 守卫**（size+mtime+SHA256）＋**写后回读**（前段/后段逐字节不变、`### 104.9` 恰 1 处、`### 104.10` 恰 0 处）。
**实删：868,601 → 866,397 B ＝ 首次正确落盘后的字节数 → 重复块已彻底清除**（字节数回到正确态是"删干净了"的独立佐证）。
**两端幂等复验**：修复脚本报 `[NOOP]`、追加脚本报 `[IDEMPOTENT]`，均**不再写盘**。

**教训（可复用）**：**幂等／存在性守卫必须锚在「内容标记」上，不能锚在「运行时生成的编号」上** —— 凡「编号运行时取 max+1」的追加逻辑，用编号判存在＝**恒不命中**＝守卫无效；这与 **Q68「守卫存在≠守卫有效」**同族，但更隐蔽：守卫**被执行到了**（有输出、有断言），只是**判据选错**而永远放行。**守卫改完必须实跑复验它的「拒绝路径」**，不能只看它"跑通了"。
本岗同轮另修两处同类缺陷：`fix_ledger_104_dup_mavis.py` 的 `body_of()` 从标题行本身起算导致空正文（已改为从标题**下一行**起算）；去尾空行前比对导致误判两块不一致（已改为去尾后比对）。

**边界**：本节仅追加台账本岗章节，**未改任何交付物 JSON**（D05 v1.3／D06 v1.2／D07 v1.3 本轮一字未动）；**他岗章节（§一百零五／§一百零六）逐字节未变**（已由脚本的前段/后段不变断言覆盖）。本岗名下脚本本轮新增 2 支（`append_ledger_104_9_delivery_mavis.py`、`fix_ledger_104_dup_mavis.py`），均为本岗单写者。未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架。"""
    block = [""] + body.split("\n") + [""]

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

    # A5 CAS 守卫
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # A6 结构性断言：前段与后段逐字节不变
    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(MARK) == 1, "A6 标记重复"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    back = open(ledp, "rb").read().decode("utf-8")
    assert back.count(MARK) == 1, "A7 写后标记计数异常"
    assert back.startswith(pre), "A7 写后前段不一致"
    assert back.endswith(post), "A7 写后后段不一致"
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back.encode('utf-8'))} B；"
          f"追加点＝原第 {ins + 1} 行（下一个同级标题之前）。落盘时间 {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
