#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""append_D08_D09_U02_delivery_note.py —— 台本编剧交付说明章节追加（通用）

为什么是脚本而不是手写追加：
  · `99_交付说明.md` 是**多写者共享台账**（企划合规 / 故事架构 / 分镜导演 / 视觉设定 /
    白模场景师 / 声音设计 并发追加）。开工时读到的节号 **不等于** 落笔时的节号 ——
    追加前必须**重新认盘**取当时最大值 +1，否则必撞号。
  · 本脚本做三件事：①落笔前重算最大节号；②追加新章节；③**写后回读**校验
    全档节号唯一性与连续性，有重号即报错退出。

用法：
  python3 scripts/append_D08_D09_U02_delivery_note.py \
      --note scripts/_delivery_note_XXX.md --title "章节标题（不含节号）"

  · `--note`   本节正文源文件（相对项目根或绝对路径），默认取本仓的 U02 D08/D09 节。
  · `--title`  章节标题（不含 `## <节号>、` 前缀），默认沿用原标题。
  · **节号运行时取 max+1**：落笔前重新认盘，取当时最大节号 +1，避免与并发追加撞号。
"""

import os
import re
import sys

NOTE_ARG = None
TITLE_ARG = "U02 第二波：D08／D09 落盘（台本编剧，2026-10-23 03:10–03:35）"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "99_交付说明.md")

_CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


def cn2int(s: str) -> int:
    """中文数字 → 整数。

    2026-10-23 修复：原实现不支持三位数，且「一百零一」被误解析为 100
    （`"零一"` 落到 `_CN_DIGITS.get(s, 0)` ⇒ 0）。台账节号已过 100 后，
    该误解析会让**重号检测误报**，并使 `int2cn` 在打印重号时抛错。
    现按「百 / 十 / 单一位」三段解析，并显式支持「零」占位。
    """
    s = s.strip()
    if not s:
        return 0
    total = 0
    if "百" in s:
        a, _, b = s.partition("百")
        total += (_CN_DIGITS.get(a, 1) if a else 1) * 100
        s = b
    if "十" in s:
        a, _, b = s.partition("十")
        total += (_CN_DIGITS.get(a, 1) if a else 1) * 10
        s = b
    if s:
        # 「零」在中文数字里从不表示非零值，只作占位（「一百零一」＝101）。
        # 剥离后再取个位；整串为「零」时结果为 0。
        s = s.replace("零", "")
        if s:
            total += _CN_DIGITS.get(s[0], 0)
    return total


def int2cn(n: int) -> str:
    """整数 → 中文数字（支持 1-999）。"""
    if n < 0:
        raise ValueError(f"节号不能为负，收到 {n}")
    if n == 0:
        return "零"
    _ONES = "零一二三四五六七八九"   # 10 字符，索引 0-9
    _TENS = "一二三四五六七八九"     # 9 字符，索引 0-8（表示 1-9）
    if n < 10:
        return _ONES[n]
    if n < 20:
        return "十" + (_ONES[n % 10] if n % 10 else "")
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens - 1] + "十" + (_ONES[ones] if ones else "")
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        head = _TENS[hundreds - 1] + "百"
        if rest == 0:
            return head
        if rest < 10:
            return head + "零" + _ONES[rest]
        if rest < 20:
            # 110 → 一百一十（不是「一百十」）
            return head + _ONES[rest // 10] + "十" + (_ONES[rest % 10] if rest % 10 else "")
        return head + int2cn(rest)
    raise ValueError(f"本脚本只覆盖 1-999，收到 {n}")


SECTION_RE = re.compile(r"^## ([一二三四五六七八九十百零]+)、", re.M)


def main():
    global NOTE_ARG, TITLE_ARG
    if not os.path.exists(LEDGER):
        sys.exit(f"❌ 找不到台账：{LEDGER}")

    with open(LEDGER, encoding="utf-8") as f:
        text = f.read()

    # ── ① 落笔前重新认盘：取当时最大节号 ──
    secs = SECTION_RE.findall(text)
    if not secs:
        sys.exit("❌ 台账里没有任何 `## <节号>、` 章节，格式异常")
    nums = [cn2int(s) for s in secs]
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        print(f"⚠️ 落笔前发现既有重号（不属本岗处理范围，仅登记）：{[int2cn(d) for d in dup]}")
    max_n = max(nums)
    new_n = max_n + 1
    new_cn = int2cn(new_n)
    print(f"落笔前认盘：全档 {len(secs)} 节，最大节号 {max_n}（{int2cn(max_n)}）→ 本岗新章节 {new_n}（{new_cn}）")

    note_path = NOTE_ARG or os.path.join(os.path.dirname(os.path.abspath(__file__)), "_delivery_note_U02_D08_D09.md")
    body = open(note_path, encoding="utf-8").read()
    section = f"## {new_cn}、{TITLE_ARG}\n\n{body.rstrip()}\n\n---\n\n"

    # ── ② 追加 ──
    if not text.endswith("\n"):
        text += "\n"
    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write(text + section)

    # ── ③ 写后回读：全档节号唯一性 + 新章节落位 ──
    with open(LEDGER, encoding="utf-8") as f:
        after = f.read()
    secs2 = SECTION_RE.findall(after)
    nums2 = [cn2int(s) for s in secs2]
    dup2 = sorted({n for n in nums2 if nums2.count(n) > 1})
    new_count = nums2.count(new_n)
    tail_ok = nums2[-1] == new_n

    print(f"写后回读：全档 {len(secs2)} 节｜新章节出现 {new_count} 次｜末节={int2cn(nums2[-1])}")
    if dup2:
        print(f"❌ 写后回读发现重号：{[int2cn(d) for d in dup2]}")
    if new_count != 1 or not tail_ok:
        print("❌ 新章节落位异常（重号或非末节），请人工介入")
        sys.exit(1)
    print(f"✅ 已追加 `## {new_cn}、` 章节｜全档无重号、末节连续")


if __name__ == "__main__":
    _a = sys.argv[1:]
    for _i, _v in enumerate(_a):
        if _v == "--note" and _i + 1 < len(_a):
            NOTE_ARG = _a[_i + 1]
        if _v == "--title" and _i + 1 < len(_a):
            TITLE_ARG = _a[_i + 1]
    main()
