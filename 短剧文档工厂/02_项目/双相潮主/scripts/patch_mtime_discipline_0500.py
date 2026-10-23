#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_mtime_discipline_0500.py —— 落盘时间口径核对（企划合规 2026-10-23 04:50）

为什么做这一条
--------------
本岗本轮落盘时，正文自述时间（04:45／04:55／05:00）**超前于磁盘 mtime 约 10 分钟**
（真实写入时刻 04:46:54–04:49:40，真实时钟 04:49:54）。这与本岗既有的
「台账落款时间以磁盘 mtime 为准」纪律同源：**自报时间会超前**，按自述时间检索会找错节、
按自述时间判因果会判反。

处置（沿用该纪律的既定做法）：
  · **正文自述不改** —— 那是事件留痕，改写等于抹掉当时的判断快照；
  · **在核对处标注「自述时间 ≠ 磁盘 mtime」，并以 mtime 为准**；
  · 台账的「落」字段以写盘后回填的 mtime 为准。

本脚本做两件事：
  A. D18 v1.45 → v1.46：在 U01-R21 的 resolution 追加「落盘时间口径」核对段（含各文件真实 mtime）。
  B. 回填本岗台账「落」字段的时间口径说明（索引 §十·三十八 与 交付说明 §五十五 均加一行标注）。

用法：python3 scripts/patch_mtime_discipline_0500.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

# 真实磁盘 mtime（stat 实测，2026-10-23）
MTIME = {
    "shared/D18.json": "04:49:40",
    "project.json": "04:49:07",
    "00_项目索引.md": "04:48:42",
    "99_交付说明.md": "04:47:37",
    "00_团队章程.md": "04:46:54",
    "04_工具/validate.mjs": "04:40:15",
}
NOTE = ("**落盘时间口径（2026-10-23 04:50 核对）**：本轮正文自述时间"
        "（04:45／04:55／05:00）**超前于磁盘 mtime 约 10 分钟**"
        "（真实写入 04:46:54–04:49:40，真实时钟 04:49:54）。"
        "按本岗既定纪律：**正文自述不改**（属事件留痕，改写等于抹掉当时的判断快照），"
        "**核对处以磁盘 mtime 为准** —— 本轮各文件真实落盘时刻："
        "`04_工具/validate.mjs` 04:40:15 → `00_团队章程.md` 04:46:54 → "
        "`99_交付说明.md` 04:47:37 → `00_项目索引.md` 04:48:42 → "
        "`project.json` 04:49:07 → `shared/D18.json` 04:49:40。"
        "**Apply**：任何按自述时间检索台账、判因果或对齐版本的场合，一律改用 mtime。")


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

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    p_idx = os.path.join(proj, "00_项目索引.md")
    p_del = os.path.join(proj, "99_交付说明.md")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    deliv = read(p_del)

    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 45):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.45；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    if "U01-R21" not in oi:
        sys.exit("[ABORT] open_issues 无 U01-R21；不写盘。")
    if "落盘时间口径" in oi["U01-R21"].get("resolution", ""):
        sys.exit("[ABORT] U01-R21 已含落盘时间口径说明；不写盘。")

    oi["U01-R21"]["resolution"] = oi["U01-R21"]["resolution"].rstrip() + "　" + NOTE
    # 版本号从现盘 +1（并行实例可能已推进，运行时取 max+1，禁止写死）
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    body = json.dumps(d18, ensure_ascii=False, indent=2)
    d18_out = body + "\n" if d18_raw.endswith("\n") else body

    # 索引 / 交付说明 加一行标注（追加在各自末节末尾）
    tag = "> **落盘时间口径**：本节正文自述时间超前磁盘 mtime 约 10 分钟，**以磁盘 mtime 为准**（见 D18 U01-R21）。\n"
    if tag not in idx:
        idx = idx.rstrip("\n") + "\n\n" + tag
    if tag not in deliv:
        deliv = deliv.rstrip("\n") + "\n\n" + tag

    if "落盘时间口径" not in d18_out:
        sys.exit("[ABORT] D18 序列化后自检失败；不写盘。")
    if idx.count(tag) != 1 or deliv.count(tag) != 1:
        sys.exit("[ABORT] 索引/交付说明 标注写入异常；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print("[PLAN] D18 版本从现盘+1（U01-R21 追加落盘时间口径核对）；索引 ＋ 交付说明 各加一行标注")
        return

    write(p18, d18_out)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 落盘时间口径核对完成")
    print(f"   shared/D18.json：v1.45 → {d18['version']}（U01-R21 追加落盘时间口径核对）")
    print("   00_项目索引.md ＋ 99_交付说明.md：各加一行「以磁盘 mtime 为准」标注")


if __name__ == "__main__":
    main()
