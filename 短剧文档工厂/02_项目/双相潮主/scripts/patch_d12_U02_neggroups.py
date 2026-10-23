#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U02 D12 内容模块 · negatives 组装补丁

对齐 U01 体例：每卡固定带 GORE（零血腥）+ 文字类负向词 + 角标/文字/贬称三条固定块；
按镜位加主题组（D03 红线口径）：
  RELIG    —— R01 邪教化/宗教符号（一票否决）
  CREATURE —— R04/R05 异化体解剖感
  FLAME    —— 净火只能黑白双色，不得出现第三色焰
  FIRE     —— 实景火光只能薪火橙，禁其它焰色（ep16 火灾）
每条替换断言恰好命中 1 次。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "d12_content_U02.py")

GROUPS = {
    1: ([], "ep9"), 2: (["CREATURE"], "ep9"), 3: (["FLAME"], "ep9"), 4: ([], "ep9"),
    1: ([], "ep10"), 2: (["FLAME"], "ep10"), 3: (["FLAME"], "ep10"), 4: (["FLAME"], "ep10"),
    1: ([], "ep11"), 2: ([], "ep11"), 3: (["RELIG"], "ep11"), 4: ([], "ep11"),
    1: (["RELIG"], "ep12"), 2: ([], "ep12"), 3: ([], "ep12"), 4: ([], "ep12"),
    1: (["RELIG"], "ep13"), 2: ([], "ep13"), 3: ([], "ep13"), 4: ([], "ep13"),
    1: ([], "ep14"), 2: ([], "ep14"), 3: ([], "ep14"), 4: ([], "ep14"),
    1: ([], "ep15"), 2: ([], "ep15"), 3: ([], "ep15"), 4: ([], "ep15"),
    1: (["CREATURE"], "ep16"), 2: (["FIRE"], "ep16"), 3: (["FIRE"], "ep16"), 4: (["FIRE"], "ep16"),
}

# (ep, shot_id) → 组名列表（覆盖上面的粗表，用精确键）
BY_KEY = {
    (9, 1): [], (9, 2): ["CREATURE"], (9, 3): ["FLAME"], (9, 4): [],
    (10, 1): [], (10, 2): ["FLAME"], (10, 3): ["FLAME"], (10, 4): ["FLAME"],
    (11, 1): [], (11, 2): [], (11, 3): ["RELIG"], (11, 4): [],
    (12, 1): ["RELIG"], (12, 2): [], (12, 3): [], (12, 4): [],
    (13, 1): ["RELIG"], (13, 2): [], (13, 3): [], (13, 4): [],
    (14, 1): [], (14, 2): [], (14, 3): [], (14, 4): [],
    (15, 1): [], (15, 2): [], (15, 3): [], (15, 4): [],
    (16, 1): ["CREATURE"], (16, 2): ["FIRE"], (16, 3): ["FIRE"], (16, 4): ["FIRE"],
}

EXTRA_PAIRS = [
    ('extras=["no lockpicking detail", "no garbled text", "no weapon", "no gore"],',
     'extras=["no lockpicking detail", "no garbled text", "no weapon", "no real corporate logos", "no gore"],'),
    ('extras=["no readable names on the list", "no garbled text", "no frontal portrait", "no gore"],',
     'extras=["no readable names on the list", "no garbled text", "no frontal portrait",\n'
     '                "no real corporate logos", "no gore"],'),
]


def main():
    src = open(CONTENT, encoding="utf-8").read()
    applied, skipped = 0, 0

    for (ep, sid), groups in BY_KEY.items():
        old = f"dict(ep={ep}, shot_id={sid}, "
        new = f"dict(ep={ep}, shot_id={sid}, groups={groups!r}, ".replace("'", '"')
        n = src.count(old)
        if n == 1:
            src = src.replace(old, new)
            applied += 1
        elif n == 0 and src.count(new) >= 1:
            skipped += 1
        else:
            print(f"❌ 组标签注入命中异常（{n} 次）：{old}")
            return 2

    for old, new in EXTRA_PAIRS:
        n = src.count(old)
        if n == 1:
            src = src.replace(old, new)
            applied += 1
        elif n == 0 and src.count(new) >= 1:
            skipped += 1
        else:
            print(f"❌ extras 替换命中异常（{n} 次）：{old[:50]}")
            return 2

    open(CONTENT, "w", encoding="utf-8").write(src)
    print(f"✅ 应用 {applied} 条，跳过（已生效）{skipped} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
