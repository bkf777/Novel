#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
refresh_D16_U01_audit_mavis.py —— 分镜导演：**D16 U01 审计块刷新（rows 行号对位 ＋ 活戳追版）**

起因
----
Chief 12:1x 来件列「D16 审计块 4 项待刷」；本岗**按现盘逐项实测**后，4 项里 **3 项已被并发实例修掉**，
**唯一真待办**是活戳落后一版。本脚本只做这两件，**不碰**其余：

① `subtitle_sync_audit.rows[].seq` **行号对位**：
   D16 的 `subtitle_style.lines` 在每次插入字幕行后按 `in_sec` **重排并重编 seq**；
   而 `rows[]` 是「事件溯源留痕」，**不跟着重排** ⇒ 每次字幕密度填充后必然行号错位。
   实证：本轮 densify 落盘后 ep003/ep004/ep007 共 **10 条** row 行号错位（时码全部仍命中，数据未失）。
   ⇒ 刷新方式：按 **(in_sec, out_sec)** 对位到活 lines，取活行 seq 覆写 row.seq
     （**不按行序猜、不改任何数值字段**）。

② `verified_against_d15` **活戳追版**：v1.12 → **v1.13**（D15 U01 现值）。
   依据：`node scripts/reconcile_D15_D16_timing.mjs --unit U01` 实跑 EXIT 0 ——
   对白字幕 30 条 / D15 配音 30 条，`out_sec ≠ 配音(at_sec+dur_sec)` **0 条**，
   配对距离 >0.05s **0 条** ⇒ D16 现盘数值对 D15 v1.13 全部成立。

**不动的字段（有意为之）**
-------------------------
` synced_row_count` / `no_vo_anchor_rows` / `sync_basis` / `verified_note` / `sync_records`：
` sync_basis` 自述「本字段是**事件溯源陈述**，不是活链接」⇒ 这两个计数字段是**历史留痕常量**
（实测：ep01 3+1=4、ep03 3+2=5≠rows 3、ep08 4+1=5≠rows 4 ⇒ 各集口径本就不同源），
**改它们会破坏溯源**，故一律不动。

守卫（缺一不可）
----------------
① **版本守卫**：盘面 D16 U01 必须等于读盘时的版本；被他人升版 → `[NO-OP]` exit 0（不回退、不抢写）。
② **内容幂等**：rows 已全部对位 且 活戳已是 v1.13 → `[IDEMPOTENT]` exit 0（不写盘、不动版本）。
③ **对位断言**：每条 row 必须按 (in_sec,out_sec) 在活 lines 中**唯一命中**，否则中止。
④ **写前并发守卫**：size/mtime/sha256 三锚 CAS（读盘后被他人改动即中止）。
⑤ **备份先行**：整份复制到 `reports/_bak_d16_audit_refresh_*`。
⑥ **写后回读**：行号对位与活戳复验；失败自动回滚。

用法：python3 scripts/refresh_D16_U01_audit_mavis.py [--dry-run]
"""
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "units", "U01", "D16.json")
D15 = os.path.join(ROOT, "units", "U01", "D15.json")
MARK = "refresh_D16_U01_audit_mavis_v1"


def fingerprint(p):
    b = open(p, "rb").read()
    o = json.loads(b.decode("utf-8"))
    return {"version": o.get("version"), "size": len(b),
            "sha16": hashlib.sha256(b).hexdigest()[:16],
            "mtime": os.path.getmtime(p)}


def main():
    dry = "--dry-run" in sys.argv
    fp0 = fingerprint(TARGET)
    d15v = json.load(open(D15, encoding="utf-8")).get("version")
    d16 = json.load(open(TARGET, encoding="utf-8"))
    print("📌 基线：D16 %s sha16=%s ｜ D15 %s" % (fp0["version"], fp0["sha16"], d15v))

    n_seq = 0
    n_ver = 0
    plan = []
    for e in d16["episodes"]:
        ep = e["ep"]
        ss = e["subtitle_style"]
        a = ss.get("subtitle_sync_audit")
        if not isinstance(a, dict):
            continue
        lines = ss.get("lines", [])
        by_iv = {}
        for l in lines:
            by_iv.setdefault((l["in_sec"], l["out_sec"]), []).append(l)
        for r in a.get("rows", []):
            key = (r["in_sec"], r["out_sec"])
            hit = by_iv.get(key, [])
            if len(hit) != 1:
                print("[ABORT] ep%s row seq=%s (%s~%s) 在活 lines 中命中 %d 次（要求唯一）"
                      % (ep, r.get("seq"), r["in_sec"], r["out_sec"], len(hit)))
                return 2
            live = hit[0]
            if live["seq"] != r.get("seq"):
                plan.append((ep, r.get("seq"), live["seq"], r["in_sec"], r["out_sec"]))
                n_seq += 1
        # 活戳
        cur = a.get("verified_against_d15", "")
        if d15v and d15v not in cur:
            n_ver += 1
        else:
            a["verified_against_d15"] = cur

    if n_seq == 0 and n_ver == 0:
        print("[IDEMPOTENT] rows 行号已全部对位 且 活戳已含 %s；未改动 D16。" % d15v)
        return 0

    # 应用 seq 对位
    for e in d16["episodes"]:
        ss = e["subtitle_style"]
        a = ss.get("subtitle_sync_audit")
        if not isinstance(a, dict):
            continue
        by_iv = {(l["in_sec"], l["out_sec"]): l for l in ss.get("lines", [])}
        for r in a.get("rows", []):
            live = by_iv[(r["in_sec"], r["out_sec"])]
            r["seq"] = live["seq"]
        if d15v:
            a["verified_against_d15"] = "%s（黄金 3 秒判据落点见 golden3s_first_line；秒级真值回 D15 at_sec 取）" % d15v

    print("📊 将刷新：行号对位 %d 条 ｜ 活戳追版 %d 集（→ %s）" % (n_seq, n_ver, d15v))
    for p in plan[:20]:
        print("   ep%s row.seq %s → %s（%s~%s）" % p)
    if len(plan) > 20:
        print("   … 共 %d 条" % len(plan))

    if dry:
        print("（--dry-run：未写盘）")
        return 0

    # 版本守卫：盘面版本必须仍等于读盘时版本
    now = fingerprint(TARGET)
    if now != fp0:
        print("[NO-OP] 盘面 D16 已演进（读盘时 %s → 现在 %s）；不写盘，请重新核对基线。"
              % (fp0["version"], now["version"]))
        return 0

    # 备份
    bak_dir = os.path.join(ROOT, "reports", "_bak_d16_audit_refresh_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "D16.json")
    shutil.copy2(TARGET, bak)

    # 自持升版（Q80：落盘方自持自增版本，不回退）
    v = str(d16.get("version", "v1.0"))
    major, minor = v.replace("v", "").split(".")[:2]
    d16["version"] = "v%s.%d" % (major, int(minor) + 1)

    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)

    # 写后回读
    back = json.load(open(TARGET, encoding="utf-8"))
    bad = 0
    for e in back["episodes"]:
        ss = e["subtitle_style"]
        a = ss.get("subtitle_sync_audit")
        if not isinstance(a, dict):
            continue
        by_iv = {(l["in_sec"], l["out_sec"]): l for l in ss.get("lines", [])}
        for r in a.get("rows", []):
            live = by_iv.get((r["in_sec"], r["out_sec"]))
            if live is None or live["seq"] != r.get("seq"):
                bad += 1
        if d15v and d15v not in a.get("verified_against_d15", ""):
            bad += 1
    if bad:
        shutil.copy2(bak, TARGET)
        print("[ROLLBACK] 写后复验失败 %d 处，已回滚。" % bad)
        return 4
    print("✅ D16 U01 → %s ｜ 刷新行号 %d 条、活戳 %d 集 ｜ 备份 %s"
          % (d16["version"], n_seq, n_ver, os.path.relpath(bak, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
