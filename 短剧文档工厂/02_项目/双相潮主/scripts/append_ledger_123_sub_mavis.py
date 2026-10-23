#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账章内子节追加器（声音设计岗·通用版）—— 在本岗父章「一百二十三」内定点插入 `### 123.N`。

【为什么要通用版】
  `append_ledger_123_29_mavis.py` 的正文硬编码在脚本里 → 复用即分叉。
  本脚本：**正文一律由 `--body-file` 传入**，模块层只有纯函数，写盘全在
  `if __name__ == "__main__":` 之下 ⇒ import 无副作用（教训见 main 记忆：
  「取号脚本必须与写盘动作解耦：import 一个会写盘的取号器＝执行一次追加」）。

【为什么不能用 append_ledger_section_mavis.py / append_ledger_123_mavis.py】
  那两个都是「**新开顶级章**、追加到文件末尾」型；而本岗父章「一百二十三」位于
  文件**中部**（实测行 10418–11694，其后是「## 一百二十四、企划合规」）。
  追加到文件末尾 ⇒ 本节落进**他人章内** ⇒ 违反单写者纪律
  （2026-10-23 11:1x 已因同类错误做过一次带 CAS 的外科修复，见台账 §170.1）。
  ⇒ 本脚本：**在父章末尾（下一顶级章标题行之前）定点插入**，不新增顶级章。

【护栏（全部沿用已实跑验证过的规则）】
  · 父章号中文数字（Q85），子章号阿拉伯（123.N）。
  · 子节号动态取号：解析本岗父章内全部 `### 123.N` → max+1。
  · 幂等：按**内容特征签名**（`--fingerprint`）判定，章号无关。
  · 写前守卫：① 指纹必须逐字在正文里 ② 目标子节号不得已被占用
              ③ 现有子节号必须连续（不连续 ⇒ 拒写，交人工核）
  · 并发护栏：CAS —— 写盘前重读台账 SHA256，与读盘时不一致 ⇒ 中止不覆盖他人字节。
  · 内建备份 → reports/_bak_ledger_ch123_<子节号>_<时戳>/99_交付说明.md
  · 写后六轴自检：① 插入点前段逐字节一致 ② 后段逐字节一致 ③ `### 123.N` 行首计数＝1
                ④ 本岗子节 1..N 连续 ⑤ 文件增长 ⑥ 全库章号可解析且无重号
  · 写后自检不过：能安全回滚就回滚（他人已动过则不回滚，只报错并指认人工处理）。
  · 原子替换：os.replace。
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

PARENT_CN = "一百二十三"
PARENT_NO = 123


def cn2int(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    num = None
    for ch in s:
        if ch in "零一二三四五六七八九":
            num = "零一二三四五六七八九".index(ch)
        elif ch == "十":
            total += (num if num is not None else 1) * 10
            num = None
        elif ch == "百":
            total += (num if num is not None else 1) * 100
            num = None
        else:
            return None
    return total if num is None else total + num


def parse_chapters(text):
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        out.append((cn2int(raw), raw, text[:m.start()].count("\n") + 1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--body-file", required=True, help="正文文件（不含 `### ` 行，由本脚本加）")
    ap.add_argument("--fingerprint", action="append", default=[],
                    help="幂等指纹（可多次）；必须逐字出现在正文里")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")
    if not os.path.isfile(args.body_file):
        sys.exit(f"[ABORT] 找不到正文文件：{args.body_file}")

    with open(args.body_file, "r", encoding="utf-8") as f:
        body_text = f.read().strip("\n")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()
    sha_before_read = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ── 幂等：指纹逐字命中 ⇒ 已落 ────────────────────────────────
    if args.fingerprint:
        hits = [fp for fp in args.fingerprint if fp in text]
        if len(hits) == len(args.fingerprint):
            print(f"[NO-OP] 台账已含全部内容指纹（{len(hits)}/{len(args.fingerprint)} 命中），不重复追加")
            return 0

    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(f"## {PARENT_CN}、")), None)
    if start is None:
        sys.exit(f"[ABORT] 找不到本岗父章「## {PARENT_CN}、」")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))

    subs = []
    for i in range(start, end):
        m = re.match(rf"^###\s+{PARENT_NO}\.(\d+)\s", lines[i])
        if m:
            subs.append((int(m.group(1)), i))
    if not subs:
        sys.exit(f"[ABORT] 本岗父章内未解析到任何 `### {PARENT_NO}.N` 子节")
    nums = sorted(n for n, _ in subs)
    if nums != list(range(1, max(nums) + 1)):
        sys.exit(f"[ABORT] 本岗子节号不连续（{nums}）⇒ 需人工核，拒写")
    target_sub = max(nums) + 1

    if re.search(rf"(?m)^###\s+{PARENT_NO}\.{target_sub}\s", text):
        sys.exit(f"[ABORT] §{PARENT_NO}.{target_sub} 已存在 ⇒ 拒写")

    body = f"### {PARENT_NO}.{target_sub} " + body_text

    for fp in args.fingerprint:
        if fp not in body:
            sys.exit(f"[ABORT] 幂等指纹与正文脱钩：{fp!r} 不在正文中 ⇒ 幂等判定会恒不成立 ⇒ 拒写")

    ins = end
    if ins > 0 and lines[ins - 1].strip() == "":
        ins -= 1
    prefix = "\n".join(lines[:ins])
    suffix = "\n".join(lines[ins:])
    new_text = prefix.rstrip("\n") + "\n\n" + body.strip("\n") + "\n\n" + suffix.lstrip("\n")

    with open(ledger, "r", encoding="utf-8") as f:
        if hashlib.sha256(f.read().encode("utf-8")).hexdigest() != sha_before_read:
            print("[RETRY] 读盘后台账已被他人改动（SHA256 不一致）⇒ 本轮中止，请重跑")
            return 3

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_ledger_ch{PARENT_NO}_{target_sub}_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(ledger, bak)
    print(f"   · 备份 → reports/_bak_ledger_ch{PARENT_NO}_{target_sub}_{ts}/99_交付说明.md"
          f"（{os.path.getsize(bak)} B）")

    before_bytes = len(text.encode("utf-8"))
    tmp = ledger + ".tmp_sub"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)
    os.replace(tmp, ledger)

    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    alines = after.split("\n")
    a1 = after.startswith(prefix.rstrip("\n"))
    a2 = after.rstrip("\n").endswith(suffix.rstrip("\n"))
    a3 = sum(1 for l in alines if re.match(rf"^###\s+{PARENT_NO}\.{target_sub}\s", l)) == 1
    s2 = next(i for i, l in enumerate(alines) if l.startswith(f"## {PARENT_CN}、"))
    e2 = next((i for i in range(s2 + 1, len(alines)) if alines[i].startswith("## ")), len(alines))
    n2 = sorted(int(m.group(1)) for i in range(s2, e2)
                for m in [re.match(rf"^###\s+{PARENT_NO}\.(\d+)\s", alines[i])] if m)
    a4 = n2 == list(range(1, max(n2) + 1))
    a5 = len(after.encode("utf-8")) > before_bytes
    chaps = parse_chapters(after)
    parsed = [c[0] for c in chaps if c[0] is not None]
    a6 = (len(chaps) == len(parsed)) and (len(parsed) == len(set(parsed)))
    print(f"■ 台账章内定点插入自检：§{PARENT_NO}.{target_sub}（父章「{PARENT_CN}」行 {s2 + 1}–{e2}）")
    print(f"   ① 插入点前段逐字节一致：{a1}")
    print(f"   ② 插入点后段逐字节一致：{a2}")
    print(f"   ③ `### {PARENT_NO}.{target_sub}` 行首计数 ＝ 1：{a3}")
    print(f"   ④ 本岗子节 1..{max(n2)} 连续：{a4}（共 {len(n2)} 条）")
    print(f"   ⑤ 文件增长：{a5}（{before_bytes} → {len(after.encode('utf-8'))} B，"
          f"+{len(after.encode('utf-8')) - before_bytes}）")
    print(f"   ⑥ 全库章号可解析且无重号：{a6}（总章 {len(chaps)}｜可解析 {len(parsed)}｜"
          f"重复 {len(parsed) - len(set(parsed))}）")
    if not (a1 and a2 and a3 and a4 and a5 and a6):
        written = hashlib.sha256(after.encode("utf-8")).hexdigest()
        with open(ledger, "r", encoding="utf-8") as f:
            now = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
        if now == written:
            shutil.copy2(bak, ledger + ".tmp_rollback")
            os.replace(ledger + ".tmp_rollback", ledger)
            print("[ROLLBACK] 写后自检未过，且写后无人改动本文件 ⇒ 已从备份原子还原")
            return 3
        print("[ABORT] 写后自检未过，但写盘后本文件已被他人改动 ⇒ 不自动回滚（避免覆盖他人字节）")
        return 3
    print(f"✅ 台账 §{PARENT_NO}.{target_sub} 落盘并通过六轴自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
