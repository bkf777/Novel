#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账父章号合规化脚本（分镜导演岗）—— 阿拉伯父章 → 中文父章（Q85）。

【触发】企划合规 2026-10-23 10:3x 在 D18 `open_issues` **OPS-24** 中登记：
  「**非规范「零前缀」中文式** ＋ **阿拉伯父章 5 处**（`## 112、／## 115、／## 117、／## 120、／## 125、`，
   **全部属分镜导演**）—— 百位后接两位数时不应加「零」（规范写法＝一百五十六／一百五十七）；
   `cn2int()` 实测值仍解析为 156／157 ⇒ **值无误、无撞号**，属**写法偏离 Q85「父章中文」规范**；
   ⇒ **请分镜导演修本岗 `int2cn()` 的 100–199 段写法（值不变，仅改字面）**」

【本脚本做什么】
  · 把**本岗名下**仍用阿拉伯写的父章标题行（`## 112、` 之类）改写为规范中文式；
  · **数值不变**（112 → 一百一十二、115 → 一百一十五、117 → 一百一十七、120 → 一百二十、125 → 一百二十五）；
  · **只改标题行**，正文与子章号（`### 112.1` 等阿拉伯子章）**一字不动**（Q85：父章中文／子章阿拉伯）；
  · **不改写任何他岗章节**（不在目标清单内的一律不动）。

【并发护栏】台账是多岗并发追加的共享文件 ⇒ 本脚本：
  ① 读 → 改 → **写前再次校验文件未被他人改动**（SHA256 比对）→ 不一致即中止退出 3；
  ② 写后回读复核：目标标题命中 1 次、原阿拉伯标题 0 次、**其余字节逐字节未变**（与备份做前缀/后缀比对）；
  ③ 写前备份到 `reports/_bak_ledger_cnfix_<本地时间戳>/99_交付说明.md`。

【幂等】目标阿拉伯标题不存在时输出 `[NO-OP]`，不重复改写。
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

# 本岗名下仍用阿拉伯写的父章号 → 规范中文式（数值一一对应）
TARGETS = {
    "112": "一百一十二",
    "115": "一百一十五",
    "117": "一百一十七",
    "120": "一百二十",
    "125": "一百二十五",
}

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    num = None
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == "十":
            total += (num if num is not None else 1) * 10
            num = None
        elif ch == "百":
            total += (num if num is not None else 1) * 100
            num = None
        else:
            return None
    return total if num is None else total + num


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()
    h0 = sha256_text(text)

    # ── 目标校验：只改存在的、且确属本岗名下（阿拉伯父章）的标题行 ──
    plan = []
    for arabic, cn in TARGETS.items():
        pat = re.compile(rf"^##\s+{arabic}、", re.M)
        hits = pat.findall(text)
        if not hits:
            continue
        if len(hits) > 1:
            sys.exit(f"[ABORT] 「## {arabic}、」出现 {len(hits)} 次，拒绝自动改写")
        # 数值一致性自证：中文式必须与阿拉伯号同值
        if cn2int(cn) != int(arabic):
            sys.exit(f"[ABORT] 数值不一致：{arabic} vs {cn}（{cn2int(cn)}）")
        plan.append((arabic, cn, pat))

    if not plan:
        print(f"[NO-OP] 未发现需合规化的阿拉伯父章（目标 {len(TARGETS)} 个）—— 已全部为中文式")
        return 0

    print("■ 改写计划（只改标题行，正文与子章号一字不动）")
    for arabic, cn, _ in plan:
        print(f"   ## {arabic}、  →  ## {cn}、")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return 0

    new_text = text
    for arabic, cn, pat in plan:
        new_text = pat.sub(f"## {cn}、", new_text, count=1)

    # ── 并发护栏：写前复检文件未被他人改动 ──
    with open(ledger, "r", encoding="utf-8") as f:
        cur = f.read()
    if sha256_text(cur) != h0:
        print("[RETRY] 读改期间台账被他人改动，本轮中止（不写盘），请重跑")
        return 3

    # ── 备份 ──
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_ledger_cnfix_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(ledger, bak)
    print(f"   · 备份 → reports/_bak_ledger_cnfix_{ts}/99_交付说明.md（{os.path.getsize(bak)} B）")

    with open(ledger, "w", encoding="utf-8") as f:
        f.write(new_text)

    # ── 写后回读复核 ──
    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    ok = True
    for arabic, cn, _ in plan:
        a = len(re.findall(rf"^##\s+{arabic}、", after, re.M))
        b = len(re.findall(rf"^##\s+{cn}、", after, re.M))
        print(f"   · 「## {arabic}、」现 {a} 次（应为 0）｜「## {cn}、」现 {b} 次（应为 1）")
        ok = ok and a == 0 and b == 1
    # 其余字节未变：把新文本里的本次改动还原，应与原文本逐字相同
    restored = after
    for arabic, cn, _ in plan:
        restored = re.sub(rf"^##\s+{cn}、", f"## {arabic}、", restored, count=1, flags=re.M)
    same = restored == text
    print(f"   · 除本次标题改写外，其余内容逐字未变：{same}")
    ok = ok and same

    if not ok:
        sys.exit("[ABORT] 写后复核未通过")
    print(f"✅ 父章号合规化完成：{len(plan)} 处；字节 {len(text.encode('utf-8'))} → {len(after.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
