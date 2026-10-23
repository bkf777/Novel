#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_source_ep020_xinhuocheng.py —— 源素材《逐集内容概述》ep020 术语首用冲突订正（单行）

发现（2026-10-23 U03 开工，独立复算）：
  《逐集内容概述.md》ep020 行写「流民疯涌归附，**薪火城**人口暴涨，治理压力骤增」，
  而 D05 术语表 `glossary[薪火城].first_use_ep = 33`（定义：「第一卷末建立的唯一庇护所」）。
  ⇒ ep020 使用「薪火城」比首用集**早 13 集**，且同一份源素材的 ep040 才写「薪火城成立」
  （U05＝薪火城建立，ep033–040）——**源素材自身前后矛盾**。
  风险：该行是 D08／D09／D11／D16 的直接上游，一旦被下游读成「薪火城」写进台词／字幕，
  就构成**首用集前用名**；而官方机器闸**没有覆盖这一条**（`term_first_use` 轴只登记「律条」，
  V5 只查 `forbidden_synonyms`）⇒ **静默通过、无人拦截**。

处置（派活已授权写 U03 段源素材；单一真源，不在工厂侧另建覆盖表）：
  ep020「薪火城人口暴涨」→「**据点**人口暴涨」。
  选词依据：① 「据点」是本项目对「废弃军工机械厂」的既有称法（D05.locations 该地点 desc：
  「陆沉抢占的战略据点」），且同一份源素材 ep019 已用「据点大门」；② 「据点」**不在** D05
  `glossary[薪火城].forbidden_synonyms`（＝基地／据点城／不灭薪火城）之列；③ 与本岗 U03
  D06／D07 的写法一致（U03 全单元未出现「薪火城」）。

**未改动**：《脉络确认.md》§二 纹阶解锁表与 D05 `gauge_readings`（二纹＝ep010 ⇒ ep017–024 为二纹）；
《逐集内容概述》ep018 的「一纹巅峰」**不属本脚本管辖** —— 那是《概述》与《脉络确认》两份源素材
之间的设定事实冲突，须由总控／企划合规裁定取哪一份为准（本岗 U03 正文不写任何阶位数字，
已在台账 §104.33 登记为发现项）。

用法：
  python3 scripts/patch_source_ep020_xinhuocheng.py --source "<01_漫剧策划目录>" [--dry-run]
退出码：0 = 已订正或幂等无操作；1 = 断言失败／中止（不写盘）。
"""

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime

OLD = "- **ep020** 流民疯涌归附，薪火城人口暴涨，治理压力骤增 ｜ 钩：大限夜已过，全城仍未脱离灰雾"
NEW = "- **ep020** 流民疯涌归附，据点人口暴涨，治理压力骤增 ｜ 钩：大限夜已过，全城仍未脱离灰雾"


def fail(msg):
    print(f"  ✗ {msg}")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="01_漫剧策划 目录")
    ap.add_argument("--project", default=None, help="工厂项目目录（用于回读 D05 断言）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    f = os.path.join(src, "逐集内容概述.md")
    if not os.path.isfile(f):
        fail(f"源文件不存在：{f}")

    raw = open(f, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    size = len(raw)
    mtime = os.path.getmtime(f)
    text = raw.decode("utf-8")
    lines = text.split("\n")

    # A1 目标行存在且唯一
    idx = [i for i, l in enumerate(lines) if l.startswith("- **ep020**")]
    if len(idx) != 1:
        fail(f"A1 ep020 行命中 {len(idx)} 条（应恰 1 条）")
    i = idx[0]
    print(f"■ 源素材订正：{os.path.basename(f)}")
    print(f"  行号 {i+1}｜原文：{lines[i]}")

    # A2 幂等：已是新写法则不动盘
    if lines[i] == NEW:
        print("[IDEMPOTENT] ep020 已是「据点人口暴涨」；未改动。")
        return 0
    if lines[i] != OLD:
        fail(f"A2 ep020 行内容与预期旧值不符，未改动：{lines[i]}")

    # A3 首用集地板：D05.glossary[薪火城].first_use_ep 必须 == 33
    if args.project:
        import json
        d05p = os.path.join(os.path.abspath(args.project), "shared", "D05.json")
        if os.path.isfile(d05p):
            d05 = json.load(open(d05p, encoding="utf-8"))
            fue = next((g.get("first_use_ep") for g in d05["glossary"]
                        if g.get("term") == "薪火城"), None)
            if fue != 33:
                fail(f"A3 D05 薪火城 first_use_ep={fue} ≠ 33，口径已变，本脚本不适用")
            print("  ✓ A3 D05.glossary[薪火城].first_use_ep == 33（与本订正依据一致）")

    # A4 全文扫描：ep033 之前不得再出现「薪火城」（ep040 的「薪火城成立」是建立点，保留）
    early = []
    for i2, l in enumerate(lines):
        m = l.find("**ep")
        if "薪火城" in l:
            em = None
            import re
            mm = re.search(r"\*\*ep(\d{3})\*\*", l)
            if mm:
                em = int(mm.group(1))
            if em is not None and em < 33:
                early.append((i2 + 1, em, l[:70]))
    if len(early) != 1 or early[0][0] != i + 1:
        fail(f"A4 ep033 之前的「薪火城」命中 {len(early)} 处（应恰 1 处＝ep020）：{early}")
    print(f"  ✓ A4 ep033 之前「薪火城」恰 1 处（ep020，第 {early[0][0]} 行）")

    new_lines = list(lines)
    new_lines[i] = NEW
    new_text = "\n".join(new_lines)

    # A5 结构断言：只改这一行
    pre = "\n".join(lines[:i])
    post = "\n".join(lines[i + 1:])
    assert new_text.startswith(pre), "A5 前段被改动"
    assert new_text.endswith(post), "A5 后段被改动"
    assert new_text.count(OLD) == 0, "A5 旧值仍有残留"

    if args.dry_run:
        print(f"[DRY-RUN] 将改第 {i+1} 行：{OLD}\n           → {NEW}")
        return 0

    # A6 CAS 守卫
    cur = open(f, "rb").read()
    if (len(cur) != size or hashlib.sha256(cur).hexdigest() != sha
            or os.path.getmtime(f) != mtime):
        fail("A6 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # 备份
    bdir = os.path.join(os.path.abspath(args.project), "reports",
                        "_bak_source_ep020_" + datetime.now().strftime("%Y%m%d-%H%M%S")) \
        if args.project else None
    if bdir:
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(f, os.path.join(bdir, "逐集内容概述.md"))
        print(f"[BAK] 备份 → {bdir}")

    with open(f, "w", encoding="utf-8") as fh:
        fh.write(new_text)

    # A7 写后回读
    back = open(f, "rb").read().decode("utf-8")
    blines = back.split("\n")
    hits = [j for j, l in enumerate(blines) if l.startswith("- **ep020**")]
    if len(hits) != 1 or blines[hits[0]] != NEW:
        fail("A7 写后回读不一致")
    assert back.startswith(pre), "A7 前段不一致"
    assert back.endswith(post), "A7 后段不一致"
    if "薪火城人口暴涨" in back:
        fail("A7 旧写法仍有残留")
    print(f"[OK] 已订正 {os.path.basename(f)} 第 {i+1} 行：")
    print(f"     − {OLD}")
    print(f"     + {NEW}")
    print(f"     {size} → {len(back.encode('utf-8'))} B｜sha256 {sha[:16]} → "
          f"{hashlib.sha256(back.encode('utf-8')).hexdigest()[:16]}｜"
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
