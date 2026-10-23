#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fix_ledger_trailing_newlines_mavis.py —— 分镜导演：清理台账末尾多余空行（**定点尾改，os.replace 原子替换**）

起因
----
2026-10-23 12:4x，追加器 v1/v2 的失败回滚/定点摘除各在台账末尾留下一枚多余换行
（追加体以 "\n" 起首，摘除时只裁正文未裁掉分隔换行 ⇒ 每轮净增 1 个 "\n"），
6 轮空转后末尾累积到 7 个空行。

本脚本只做一件事：**把文件末尾的连续换行收敛为恰好 1 个**，其余字节逐字不动。

安全措施
--------
  · 写前 sha256 三锚 CAS（size/mtime/sha256）⇒ 并发者在窗口内改过台账即中止；
  · 备份先行（reports/_bak_ledger_tail_YYYYmmdd-HHMMSS/）；
  · **用 os.replace 原子替换**（不是 shutil.copy2 的「截断＋写」窗口）⇒ 不会产生半截文件；
  · 写后回读校验：字节长度变化 == 被裁掉的字节数，且正文前 4096 字节逐字不变。

用法：python3 scripts/fix_ledger_trailing_newlines_mavis.py [--dry-run]
"""
import hashlib
import os
import shutil
import sys
import time

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")


def main():
    dry = "--dry-run" in sys.argv
    b = open(LEDGER, "rb").read()
    sha = hashlib.sha256(b).hexdigest()
    size = len(b)
    mtime = os.path.getmtime(LEDGER)
    txt = b.decode("utf-8")
    n = len(txt) - len(txt.rstrip("\n"))
    print("🔍 现状：%d B｜末尾连续换行 %d 个" % (size, n))
    if n <= 1:
        print("✅ 末尾换行已规范（≤1），无需处理。")
        return 0
    cut = n - 1
    new = (txt[: len(txt) - cut]).encode("utf-8")
    print("✂️ 将裁掉末尾 %d 个多余换行 ⇒ 新长度 %d B（%+d）" % (cut, len(new), len(new) - size))
    if dry:
        print("（--dry-run：未写盘）")
        return 0

    cur = open(LEDGER, "rb").read()
    if (len(cur) != size or os.path.getmtime(LEDGER) != mtime
            or hashlib.sha256(cur).hexdigest() != sha):
        print("[ABORT] 并发改动守卫触发；不写盘，请重跑。")
        return 3

    bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_tail_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    shutil.copy2(LEDGER, os.path.join(bak_dir, "99_交付说明.md"))

    tmp = LEDGER + ".tmp_tail"
    with open(tmp, "wb") as f:
        f.write(new)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LEDGER)  # 原子替换

    back = open(LEDGER, "rb").read()
    bt = back.decode("utf-8")
    ok = (len(back) == len(new)
          and len(bt) - len(bt.rstrip("\n")) == 1
          and bt[:4096] == txt[:4096]
          and bt == txt[: len(txt) - cut])          # 逐字节：裁掉末尾多余换行后应与预期完全相等
    if not ok:
        shutil.copy2(os.path.join(bak_dir, "99_交付说明.md"), LEDGER)
        print("[ROLLBACK] 写后校验失败，已回滚。")
        return 4
    print("✅ 末尾换行已收敛为 1 个｜文件现 %d B（%+d）｜备份 %s"
          % (len(back), len(back) - size, os.path.relpath(bak_dir, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
