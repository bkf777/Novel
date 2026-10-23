#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U02 D12 内容模块 · 负向词组再分配补丁（补 REAL 洞）

发现：D10.negatives 共享池里的 REAL 组（现实国旗/徽章/企业 logo/军衔/货币符号/
民族宗教服饰/现实地标）在 U02 全单元**没有任何一张卡覆盖**——U02 有大量
委员会屏幕、公告投影、黑市电子屏、门牌木牌、城防图，是生成图最可能塞进
现实标识的地方。这是一条真洞，不是体例问题。

分配（保持 U01 的 17~35 条 / ≤700 字区间，不因 D12 不占 h3 预算而膨胀）：
  REAL  整组 7 条 → ep12/s1 公告投影、ep14/s3 委员会屏幕、ep14/s4 城防图
  REALX 精简 3 条 → ep11/s1 图纸、ep11/s4 电子屏、ep13/s4 电子屏、
                    ep14/s1 断供通知+电子屏、ep14/s2 木牌、ep15/s1 指挥舱名单
  ep16/s1 面板保留 CREATURE，另加卡专属「no real corporate logos」
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "d12_content_U02.py")

NEW_GROUPS = {
    (11, 1): ["REALX"],
    (11, 4): ["REALX"],
    (12, 1): ["REAL"],
    (13, 4): ["REALX"],
    (14, 1): ["REALX"],
    (14, 2): ["REALX"],
    (14, 3): ["REAL"],
    (14, 4): ["REAL"],
    (15, 1): ["REALX"],
}

EXTRA_PAIRS = [
    ('extras=["no transformed body", "no gray-skin transformation on screen", "no gore", "no blood", "no garbled text"],',
     'extras=["no transformed body", "no gray-skin transformation on screen", "no gore", "no blood",\n'
     '                "no garbled text", "no real corporate logos"],'),
]


def main():
    src = open(CONTENT, encoding="utf-8").read()
    applied, skipped = 0, 0

    for (ep, sid), groups in NEW_GROUPS.items():
        import re
        pat = re.compile(rf"dict\(ep={ep}, shot_id={sid}, groups=\[[^\]]*\]")
        found = pat.findall(src)
        if len(found) != 1:
            print(f"❌ 组标签定位异常（{len(found)} 次）：ep{ep} s{sid}")
            return 2
        new = f'dict(ep={ep}, shot_id={sid}, groups={groups!r}'.replace("'", '"')
        src = pat.sub(new, src, count=1)
        applied += 1

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
