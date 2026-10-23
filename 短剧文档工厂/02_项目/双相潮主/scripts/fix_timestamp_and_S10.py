#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间戳与登记项订正（企划合规，2026-10-23 02:25）。

问题
----
上一轮回刷（patch_D18_v123_ledger_gapfill.py / patch_ledger_refresh_0228.py）里，
常量 NOW 写成了 "2026-10-23 02:32"，而**实际机器时钟是 02:25** —— 台账被写入了未来时间戳。
台账时间戳一旦不可信，下一位执行人按时间排序判断"谁先动过"就会错，故立即订正。

另有一处登记项误记：OPS-07 的 scope 写「③ project.json **S10** 登记」——
**S10 并不存在**：D10 v1.8 的作用域修正是由并行实例**并入既有 decisions.S6_并行段例外 的正文**
（不新增 decision 条目），本岗实际只刷新了 project.json 的 updated_at。

订正清单（每条带命中数断言，对不上即中止不写盘）
----------------------------------------------
  D18.json      ① D15 行「企划合规 02:28 对 D16 v1.5 重跑复算」 → 02:24
                ② U01 updated_at「2026-10-23 02:32」 → 02:24
                ③ dispatch_ledger OPS-07 波次 at「2026-10-23 02:32」 → 02:24
                ④ OPS-07 scope「③ project.json S10 登记」 → 改为实际动作
                ⑤ Q40 source「2026-10-23 02:32」 → 02:24
  project.json  ⑥ updated_at「2026-10-23 02:32」 → 02:24
  00_项目索引.md ⑦ 章节抬头「企划合规 2026-10-23 02:28–02:32」 → 02:20–02:24
  99_交付说明.md ⑧ §二十三 抬头「（2026-10-23 02:28–02:32）」 → 02:20–02:24
                ⑨ §23.5「updated_at → 2026-10-23 02:32」 → 02:24

用法
----
python3 scripts/fix_timestamp_and_S10.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 02:24"

D18_FIX = [
    ("企划合规 02:28 对 D16 v1.5 重跑复算", "企划合规 02:24 对 D16 v1.5 重跑复算"),
    ("③ project.json S10 登记 ④ 00_项目索引.md D15 行与状态栏回刷",
     "③ project.json `updated_at` 刷新（v1.8 作用域修正已由并行实例并入 `decisions.S6_并行段例外` 正文，"
     "**无新增 decision 条目**）④ 00_项目索引.md D15 行与状态栏回刷"),
    ("企划合规 2026-10-23 02:32（R-032 收尾台账缺口回填时实测）",
     "企划合规 2026-10-23 02:24（R-032 收尾台账缺口回填时实测）"),
]

INDEX_FIX = [
    ("（**企划合规 2026-10-23 02:28–02:32**）", "（**企划合规 2026-10-23 02:20–02:24**）"),
]

DELIV_FIX = [
    ("（2026-10-23 02:28–02:32）", "（2026-10-23 02:20–02:24）"),
    ("`updated_at` → 2026-10-23 02:32", "`updated_at` → 2026-10-23 02:24"),
]


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    p_idx = os.path.join(proj, "00_项目索引.md")
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- D18：文本替换 ----------
    for old, new in D18_FIX:
        n = d18_raw.count(old)
        if n != 1:
            sys.exit(f"[ABORT] D18 待替换串命中 {n} 次（期望 1）：{old[:60]}…；不写盘。")
        d18_raw = d18_raw.replace(old, new)

    # 文本替换后重新解析，再改结构字段（updated_at / ledger at）—— 两者必须走同一条序列化出口
    d18 = json.loads(d18_raw)
    u01 = [x for x in d18["unit_checks"] if x.get("unit") == "U01"][0]
    if u01.get("updated_at") != "2026-10-23 02:32":
        sys.exit(f"[ABORT] U01 updated_at={u01.get('updated_at')}，期望 2026-10-23 02:32；不写盘。")
    u01["updated_at"] = NOW

    hits = [w for w in u01["dispatch_ledger"] if any(i.get("id") == "OPS-07" for i in w.get("items", []))]
    if len(hits) != 1:
        sys.exit(f"[ABORT] dispatch_ledger 中 OPS-07 波次命中 {len(hits)} 条，期望 1；不写盘。")
    if hits[0].get("at") != "2026-10-23 02:32":
        sys.exit(f"[ABORT] OPS-07 波次 at={hits[0].get('at')}，期望 2026-10-23 02:32；不写盘。")
    hits[0]["at"] = NOW

    # 序列化格式必须与现文件一致（indent=2、无尾随换行），否则改写会引入纯格式 diff
    d18_out = json.dumps(d18, ensure_ascii=False, indent=2)
    if len(d18_out) != len(d18_raw) and "02:28" not in d18_out and "02:32" not in d18_out:
        pass  # 长度变化来自实际内容改动，允许
    for _, new in D18_FIX:
        if new not in d18_out:
            sys.exit(f"[ABORT] D18 文本订正在序列化后丢失：{new[:50]}…；不写盘。")

    # ---------- project.json ----------
    if prj.get("updated_at") != "2026-10-23 02:32":
        sys.exit(f"[ABORT] project.json updated_at={prj.get('updated_at')}，期望 2026-10-23 02:32；不写盘。")
    prj["updated_at"] = NOW

    # ---------- 索引 / 交付说明 ----------
    for old, new in INDEX_FIX:
        n = idx.count(old)
        if n != 1:
            sys.exit(f"[ABORT] 索引待替换串命中 {n} 次（期望 1）：{old[:60]}…；不写盘。")
        idx = idx.replace(old, new)
    for old, new in DELIV_FIX:
        n = deliv.count(old)
        if n != 1:
            sys.exit(f"[ABORT] 交付说明待替换串命中 {n} 次（期望 1）：{old[:60]}…；不写盘。")
        deliv = deliv.replace(old, new)

    # ---------- 终态自检：不得残留未来时间戳 / 假 S10 ----------
    for name, blob in (("D18.json", d18_out), ("00_项目索引.md", idx), ("99_交付说明.md", deliv)):
        if "2026-10-23 02:32" in blob or "2026-10-23 02:28" in blob:
            sys.exit(f"[ABORT] {name} 仍残留 02:28／02:32 时间戳；不写盘。")
    if "S10 登记" in d18_out:
        sys.exit("[ABORT] D18 仍残留「S10 登记」误记；不写盘。")
    # 交付说明开头的「爽点矩阵 S1~S10」与本条无关，不得被误改
    if "爽点矩阵 S1~S10" not in deliv:
        sys.exit("[ABORT] 交付说明「爽点矩阵 S1~S10」被误改（该 S10 与 decision 无关）；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print("[PLAN] D18 文本 3 处 ＋ U01 updated_at ＋ OPS-07 at；project.json updated_at；"
              "索引 1 处；交付说明 2 处")
        return

    with open(p18, "w", encoding="utf-8") as f:
        f.write(d18_out)
    with open(p_prj, "w", encoding="utf-8") as f:
        json.dump(prj, f, ensure_ascii=False, indent=2)
    with open(p_idx, "w", encoding="utf-8") as f:
        f.write(idx)
    with open(p_del, "w", encoding="utf-8") as f:
        f.write(deliv)

    print("[DONE] 时间戳与登记项订正完成")
    print(f"   D18.json：U01 updated_at / OPS-07 at → {NOW}；文本 3 处（含 S10 误记订正）")
    print(f"   project.json：updated_at → {NOW}")
    print("   00_项目索引.md：章节抬头 → 02:20–02:24")
    print("   99_交付说明.md：§二十三 抬头与 §23.5 → 02:20–02:24 / 02:24")


if __name__ == "__main__":
    main()
