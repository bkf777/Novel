#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_ledger_round5_0745.py —— 自述落款时间改由时钟派生（Q48 同源订正）（企划合规 2026-10-23 07:4x）

起因：第四轮脚本把落款时间**手写成常量** `"2026-10-23 07:40"`，而实际落盘发生在 **07:33:50**
（`shared/D18.json` 磁盘 mtime 实测）—— **自报时间超前 mtime 6 分钟**，正是 D18 **Q48** 点名的失败形态
（「实测自报时间超前于 mtime 两例」）。本轮把这类时间戳**改为时钟派生**，并加**写盘后一致性断言**：
若写入时刻跨过分钟边界导致文本时间与磁盘 mtime 不一致，脚本**中止报错**，不留下新的偏差。

本轮改动（**只改时间戳与一处口径说明，不改任何实质内容**）：
  ① `shared/D18.json`  v1.72 → **v1.73**：OPS-17 resolution／detected_by 与 Q71 source 的时间戳；
  ② `project.json`：`updated_at` ＋ S28 正文时间戳；
  ③ `00_项目索引.md`：§十·五十八「订正留痕（07:40）」→ 时钟派生时间 ＋ §五/§六 D18 版本提法；
  ④ `99_交付说明.md`：§一百零二「订正留痕（07:40）」→ 时钟派生时间。

用法：python3 scripts/patch_ledger_round5_0745.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

OLD_HM = "07:40"
OLD_FULL = "2026-10-23 07:40"


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


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
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    # ⚠️ 时间戳**由时钟派生**，不再手写常量
    now = datetime.now()
    stamp_hm = now.strftime("%H:%M")
    stamp_full = f"{now.strftime('%Y-%m-%d')} {stamp_hm}"

    d18_raw = read(p18)
    d18_raw_orig = d18_raw          # ⚠️ CAS 比对必须用**未改动**的原始副本
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj_raw_orig = prj_raw
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检 ----------
    ver = d18.get("version", "")
    # ⚠️ 并行企划合规实例可能已推进版本（本轮实测：v1.72 → v1.73，gc/oi 未变）
    #    ⇒ 守卫用「≥现盘」，新版本**运行时取 max+1**，不写死
    if not (ver.startswith("v1.") and int(ver[3:]) >= 72):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.72；不写盘。")
    oi_ids = {o["id"] for o in d18["open_issues"]}
    gc_ids = {g["id"] for g in d18["global_checks"]}
    for k in ("OPS-17",):
        if k not in oi_ids:
            sys.exit(f"[ABORT] open_issues 无 {k}；不写盘。")
    for k in ("Q71",):
        if k not in gc_ids:
            sys.exit(f"[ABORT] global_checks 无 {k}；不写盘。")
    if "S28_校验器schema键遍历口径与title误报归零" not in prj["decisions"]:
        sys.exit("[ABORT] project.json 无 S28；不写盘。")
    # 待订正串必须在盘且命中数确定
    n18 = d18_raw.count(OLD_FULL)
    if n18 != 3:
        sys.exit(f"[ABORT] D18 中「{OLD_FULL}」命中数 {n18} ≠ 3；不写盘。")
    if prj_raw.count(OLD_FULL) != 2:
        sys.exit(f"[ABORT] project.json 中「{OLD_FULL}」命中数 {prj_raw.count(OLD_FULL)} ≠ 2；不写盘。")
    if idx.count(f"（{OLD_HM}）") != 1:
        sys.exit(f"[ABORT] 索引中「（{OLD_HM}）」命中数 {idx.count(f'（{OLD_HM}）')} ≠ 1；不写盘。")
    if deliv.count(f"（{OLD_HM}）") != 1:
        sys.exit(f"[ABORT] 交付说明中「（{OLD_HM}）」命中数 {deliv.count(f'（{OLD_HM}）')} ≠ 1；不写盘。")
    if stamp_hm == OLD_HM:
        sys.exit(f"[ABORT] 时钟派生时间与待订正值相同（{stamp_hm}）；不写盘。")

    # ---------- A. D18（只改时间戳，实质内容不动） ----------
    d18_raw = d18_raw.replace(OLD_FULL, stamp_full)
    d18 = json.loads(d18_raw)
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj_raw = prj_raw.replace(OLD_FULL, stamp_full)
    prj = json.loads(prj_raw)
    prj["updated_at"] = stamp_full
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引 ----------
    pat_a = r"D18 \*\*v1\.\d+\*\*（\*\*\d+\*\* 条 global_checks / \*\*\d+\*\* 条 open_issues"
    if len(re.findall(pat_a, idx)) != 1:
        sys.exit("[ABORT] 索引 §五 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_a,
                 f"D18 **{d18['version']}**（**{len(d18['global_checks'])}** 条 global_checks / "
                 f"**{len(d18['open_issues'])}** 条 open_issues",
                 idx, count=1)
    pat_c = (r"(\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*（字节数不钉，见 D18 \*\*Q34\*\*）。)"
             r"\*\*\d+ 条 global_checks\*\*")
    if len(re.findall(pat_c, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 计数锚点命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_c,
                 lambda m: m.group(1) + f"**{len(d18['global_checks'])} 条 global_checks**",
                 idx, count=1)
    pat_b = r"\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*"
    if len(re.findall(pat_b, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_b, f"**{d18['version']}｜«RUN_HM» 落｜approved**", idx, count=1)
    idx = idx.replace(f"（{OLD_HM}）", f"（{stamp_hm}）", 1)
    # 追加：时间戳口径订正说明
    idx = idx.rstrip("\n") + "\n" + f"""
**⑤ 落款时间口径订正（{stamp_hm}）**：第四轮脚本把落款时间**手写成常量**，实测**超前磁盘 mtime 数分钟**
（`shared/D18.json` mtime 为权威落盘事实）—— **Q48 同源形态，本岗自纠**。
本轮起**所有台账时间戳改由时钟派生**，并加**写盘后一致性断言**（文本时间与 D18.json 磁盘 mtime 不符即中止报错），
**不再手写常量**；历史章节的时间属当时实况，**留痕不改写**。
"""

    # ---------- D. 交付说明 ----------
    deliv = deliv.replace(f"（{OLD_HM}）", f"（{stamp_hm}）", 1)
    deliv = deliv.rstrip("\n") + "\n" + f"""
### 一百零二.6 落款时间口径订正（{stamp_hm}）

第四轮脚本把落款时间**手写成常量**，实测**超前磁盘 mtime 数分钟** → **Q48 同源，本岗自纠**。
本轮起台账时间戳**改由时钟派生** ＋ **写盘后一致性断言**（文本时间与 D18.json 磁盘 mtime 不符即中止）；
历史章节时间属当时实况，**留痕不改写**。
"""

    # ---------- E. 自检 ----------
    if "OPS-17" not in d18_out or "Q71" not in d18_out:
        sys.exit("[ABORT] D18 序列化后丢失 OPS-17/Q71；不写盘。")
    if "S28_校验器schema键遍历口径与title误报归零" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S28；不写盘。")
    for name, txt in (("索引", idx), ("交付说明", deliv)):
        if OLD_FULL in txt:
            sys.exit(f"[ABORT] {name} 仍残留「{OLD_FULL}」；不写盘。")
        if f"（{OLD_HM}）" in txt:
            sys.exit(f"[ABORT] {name} 仍残留「（{OLD_HM}）」；不写盘。")
        if txt.count(f"（{stamp_hm}）") < 1:
            sys.exit(f"[ABORT] {name} 未写入新时间戳；不写盘。")
    if prj["updated_at"] != stamp_full:
        sys.exit("[ABORT] project.json updated_at 未按时钟派生；不写盘。")

    # ---------- F. 并发写盘竞态守卫（compare-and-swap） ----------
    # ⚠️ 比对基准必须是**读入时的原始字节**（上面的 d18_raw_orig / prj_raw_orig），
    #    不能用已做时间戳替换的版本 —— 否则守卫恒不成立。
    for path, raw0, label in ((p18, d18_raw_orig, "shared/D18.json"),
                               (p_prj, prj_raw_orig, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] 时钟派生时间 {stamp_full}；D18 {ver}→{d18['version']}（仅时间戳）；"
              f"project.json updated_at ＋ S28 正文；索引 §五/§六 版本提法 ＋ 订正段；交付说明 §一百零二")
        return

    bak = os.path.join(proj, "reports", "_bak_0745_patch_round5")
    os.makedirs(bak, exist_ok=True)
    for path, name in ((p18, "D18.json"), (p_prj, "project.json"),
                       (p_idx, "00_项目索引.md"), (p_del, "99_交付说明.md")):
        with open(os.path.join(bak, name), "wb") as f:
            f.write(open(path, "rb").read())

    write(p18, d18_out)
    write(p_prj, prj_out)

    # ⚠️ 写入若跨分钟边界，文本时间会与磁盘 mtime 不符 —— **收敛重写**：
    #    以 D18.json 自身 mtime 为准重写文本（重写耗时 <1s，必然落在同一分钟内）
    run_hm = datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M")
    for _ in range(3):
        if run_hm == stamp_hm:
            break
        print(f"[REWRITE] 写入跨分钟边界（文本 {stamp_hm} vs mtime {run_hm}），按 mtime 重写收敛", file=sys.stderr)
        stamp_hm = run_hm
        stamp_full = f"{now.strftime('%Y-%m-%d')} {stamp_hm}"
        d18_raw2 = d18_raw_orig.replace(OLD_FULL, stamp_full)
        d18_out = serialize_like(json.loads(d18_raw2), d18_raw2)
        prj_raw2 = prj_raw_orig.replace(OLD_FULL, stamp_full)
        prj["updated_at"] = stamp_full
        prj_out = serialize_like(json.loads(prj_raw2), prj_raw2)
        write(p18, d18_out)
        write(p_prj, prj_out)
        run_hm = datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M")
    if run_hm != stamp_hm:
        sys.exit(f"[ABORT] 文本时间 {stamp_hm} 与 D18.json mtime {run_hm} 仍不一致；请重跑。")

    idx = idx.replace("«RUN_HM»", run_hm)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 落款时间改由时钟派生 ＋ 时间戳订正落盘")
    print(f"   时钟派生时间：{stamp_full}（与 D18.json 磁盘 mtime 一致性已断言）")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：updated_at → {stamp_full}")
    print(f"   00_项目索引.md：§五/§六 版本提法 ＋ 订正段（落款 {run_hm}）")
    print("   99_交付说明.md：§一百零二.6")


if __name__ == "__main__":
    main()
