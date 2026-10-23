#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账让号重编补丁：视觉设定 §一百零一 → §122

背景
----
本岗 08:3x 写入台账的「## 一百零一、视觉设定（bot_db3fd3817800）…」
与**企划合规 07:2x 的「## 一百零一、企划合规：…」** 撞号
（企划合规节＝U02-R33 订正 ＋ Q67/Q68/Q69 登记；本岗节＝三项请裁回销）。

处置原则（照既有先例，不新造规矩）
--------------------------------
1. **不改他人章节一字**：只重编本岗自己那一节的标题与子节号。
   先例：声音设计「§一百零七 → §一百零九」让号重编（台账 §一百零九 节末留痕）。
2. **不占用 §108**：台本编剧 §111.4 已把 108 登记为**真空缺号**并明确「**不回填**」
   （理由：回填会虚构历史留痕，节内容实际写在 109/110 之后）。
   本节内容同样写在 §一百二十一 之后 → 占用 108 属同类问题 → **取 122 而非 108**。
3. **取号＝落笔前实时 max+1**，且**两种章号形态都解析、取数值最大者**
   （阿拉伯／中文混排，取单一形态必然取错——台账 §117 已登记此教训）。
   追加**往返断言**（int→中文→int 与 int→阿拉伯→int 双向往返）。
4. **章号用阿拉伯数字**（OPS-19 统一规范建议 1；`isdigit` 分支最易被所有实现识别）。
5. **子节号同步**：101.1–101.8 → 122.1–122.8；节内 §101.x 引用同步。
6. **并发守卫**：写盘前重读，若文件已被他人追加 → 重算取号重来（最多 5 轮）；
   原子写（tmp + os.replace）＋ 写前备份 ＋ 落盘后回读断言。

用法：python3 scripts/patch_ledger_renumber_visual.py [--dry-run]
"""

import argparse
import os
import re
import shutil
import sys
import time

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "99_交付说明.md")
LEDGER = os.path.abspath(LEDGER)
BACKUP_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports",
                 "_bak_ledger_renumber_20261023")
)

MY_HEAD_OLD = "## 一百零一、视觉设定（bot_db3fd3817800）"
MY_HEAD_OLD_FULL = (
    "## 一百零一、视觉设定（bot_db3fd3817800）：**企划合规三项请裁全部回销（成立·不改）**"
    " ＋ **豁免说明入 D10（v1.10→v1.11）** ＋ **复核工具单元参数化 ＋ 判据适用性自检**"
    " ＋ **U01 侧 3 条池缺项发现上报**（2026-10-23 08:2x–08:3x）"
)

DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s: str):
    """中文数字 → int（支持 一/十/百/千 与 零 占位）；不可解析返回 None。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    section = 0
    number = 0
    seen = False
    for ch in s:
        if ch in DIGITS:
            number = DIGITS[ch]
            seen = True
        elif ch == "十":
            section += (number if number else 1) * 10
            number = 0
            seen = True
        elif ch == "百":
            section += (number if number else 1) * 100
            number = 0
            seen = True
        elif ch == "千":
            section += (number if number else 1) * 1000
            number = 0
            seen = True
        elif ch == "零":
            number = 0
            seen = True
        else:
            return None
    return section + number if seen else None


def int2cn(n: int) -> str:
    """int → 中文数字（仅用于往返断言；100 以上须正确，不能输出「一百零一」给 111）。"""
    if n < 10:
        return "零一二三四五六七八九"[n]
    if n < 100:
        t, o = divmod(n, 10)
        s = ("一" if t == 1 else DIGITS_CN[t]) + "十"
        return s + (DIGITS_CN[o] if o else "")
    if n < 1000:
        h, rem = divmod(n, 100)
        s = DIGITS_CN[h] + "百"
        if rem == 0:
            return s
        if rem < 10:
            return s + "零" + DIGITS_CN[rem]
        t, o = divmod(rem, 10)
        return s + ("一" if t == 1 else DIGITS_CN[t]) + "十" + (DIGITS_CN[o] if o else "")
    return str(n)


DIGITS_CN = "零一二三四五六七八九"


def parse_chapters(text: str):
    """返回 [(行号, 章号原文, 数值)]；数值不可解析者单列（静默过滤是跳号直接成因）。"""
    rows = []
    unparsable = []
    for i, line in enumerate(text.split("\n"), 1):
        if not line.startswith("## "):
            continue
        raw = line[3:].split("、", 1)[0].strip()
        val = cn2int(raw)
        if val is None:
            unparsable.append((i, raw))
        else:
            rows.append((i, raw, val))
    return rows, unparsable


def build_new_section(text: str, target: int):
    """把本岗那一节的标题/子节号/节内引用改成 target 号；返回 (新全文, 命中计数)。"""
    lines = text.split("\n")
    # 定位本岗那一节的起始行（标题原文必须精确命中）
    start = None
    for i, line in enumerate(lines):
        if line.startswith(MY_HEAD_OLD):
            start = i
            break
    if start is None:
        raise SystemExit("❌ 未定位到本岗那一节的标题（可能已改号或被人改动），中止不写盘")

    head_old = lines[start]
    head_new = head_old.replace(MY_HEAD_OLD, "## %d、视觉设定（bot_db3fd3817800）" % target, 1)
    lines[start] = head_new

    cnt = {"subhead": 0, "inline": 0, "ref": 0}

    # 子节标题 + 节内 §引用（只在本岗这一节范围内改）
    for i in range(start, len(lines)):
        line = lines[i]
        new, n1 = re.subn(r"^### 101\.", "### %d." % target, line)
        cnt["subhead"] += n1
        new, n2 = re.subn(r"§101\.", "§%d." % target, new)
        cnt["inline"] += n2
        new, n3 = re.subn(r"本岗 §一百零一 的落点说明", "本岗 §%d 的落点说明" % target, new)
        cnt["ref"] += n3
        lines[i] = new

    if cnt["subhead"] != 8 or cnt["inline"] != 3 or cnt["ref"] != 1:
        raise SystemExit("❌ 命中数不符，期望 subhead=8 inline=3 ref=1，实得 %r —— 中止不写盘" % cnt)

    # 节首留痕（让号重编的审计说明）
    note = [
        "",
        "> **本节章号让号重编留痕（2026-10-23 08:4x）**：本节初稿写为「§一百零一」，与"
        "**企划合规 07:2x 的 §一百零一**（U02-R33 订正 ＋ Q67/Q68/Q69 登记）**撞号** → 本岗按"
        "「**不改他人章节一字、只重编自己那一节**」的先例（声音设计「§一百零七 → §一百零九」"
        "让号重编见该节末留痕）**让号重编为 §%d**。取号＝**落笔前实时 max+1**（两种章号形态都解析、"
        "取数值最大者，含双向往返断言），**章号用阿拉伯数字**（OPS-19 统一规范建议 1）。"
        % target,
        "> **刻意不占用 §108**：台本编剧 §111.4 已把 108 登记为**真空缺号**并明确「**不回填**」"
        "（理由：回填会虚构历史留痕，节内容实际写在 109/110 之后）—— 本节内容同样写在"
        "§一百二十一 之后，占用 108 属同类问题，故**取 %d 而非 108**。" % target,
    ]
    lines[start + 1:start + 1] = note

    # 边界条目补一句写盘面说明
    for i in range(start, len(lines)):
        if "本岗本轮写盘面" in lines[i]:
            lines[i] = lines[i].replace(
                "＋ 本台账一节。",
                "＋ 本台账一节（初稿 §一百零一 → 撞号 → 让号重编为 §%d，见节首留痕）。" % target,
            )
            break

    return "\n".join(lines), cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for attempt in range(5):
        with open(LEDGER, "r", encoding="utf-8") as f:
            base = f.read()
        if MY_HEAD_OLD_FULL not in base and MY_HEAD_OLD not in base:
            print("ℹ️  本岗那一节标题已不在原样（可能已被改号/被人动过）→ 退出，不写盘")
            return 1

        rows, unparsable = parse_chapters(base)
        vals = [v for _, _, v in rows]
        maxnum = max(vals)
        used = set(vals)
        target = maxnum + 1
        if target in used:
            print("❌ 目标号 %d 已被占用 → 换轮次重算" % target)
            time.sleep(1)
            continue

        # 往返断言：目标号的阿拉伯写法与中文写法都要能解析回同一数值
        assert cn2int(str(target)) == target
        assert cn2int(int2cn(target)) == target

        print("=== 取号 ===")
        print("  标题总数        : %d" % len(rows))
        print("  不可解析章号    : %d %r" % (len(unparsable), unparsable))
        print("  现存 max        : %d（按数值）" % maxnum)
        print("  取号结果        : %d（= max+1，未占用）" % target)
        print("  int2cn(%d)      : %s" % (target, int2cn(target)))

        new_text, cnt = build_new_section(base, target)
        print("=== 命中数 ===")
        print("  子节标题 101.x→%d.x : %d" % (target, cnt["subhead"]))
        print("  节内 §101.x 引用    : %d" % cnt["inline"])
        print("  §一百零一 引用      : %d" % cnt["ref"])
        print("  字节数 %d → %d" % (len(base.encode()), len(new_text.encode())))

        if args.dry_run:
            print("🔍 --dry-run：未写盘")
            return 0

        # 并发守卫：写盘前重读，若他人已追加 → 重算取号重来
        with open(LEDGER, "r", encoding="utf-8") as f:
            now = f.read()
        if now != base:
            print("⚠️  写盘前检测到文件已被他人改动（%d → %d B）→ 重算取号重来" %
                  (len(base.encode()), len(now.encode())))
            time.sleep(1)
            continue

        os.makedirs(BACKUP_DIR, exist_ok=True)
        bak = os.path.join(BACKUP_DIR, "99_交付说明.md.bak")
        shutil.copy2(LEDGER, bak)

        tmp = LEDGER + ".tmp.%d" % os.getpid()
        st = os.stat(LEDGER)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, LEDGER)

        # 落盘后回读断言
        with open(LEDGER, "r", encoding="utf-8") as f:
            after = f.read()
        rows2, unparsable2 = parse_chapters(after)
        vals2 = [v for _, _, v in rows2]
        dup = sorted({v for v in vals2 if vals2.count(v) > 1})
        assert dup == [], "❌ 落盘后仍有重复章号 %r" % dup
        new_head = "## %d、视觉设定（bot_db3fd3817800）" % target
        assert new_head in after
        # 只在本岗这一节范围内断言（企划合规 §一百零一 节的 101.1–101.12 属他人章节，不动）
        my_part = after[after.index(new_head):]
        assert "### 101." not in my_part, "❌ 本岗节内仍残留 101.x 子节号"
        assert "§101." not in my_part, "❌ 本岗节内仍残留 §101.x 引用"
        assert "本岗 §%d 的落点说明" % target in my_part
        print("=== 落盘后回读断言 ===")
        print("  标题总数        : %d" % len(rows2))
        print("  重复章号        : %r ✅" % dup)
        print("  不可解析章号    : %d %r" % (len(unparsable2), unparsable2))
        print("  备份            : %s" % bak)
        print("  ✅ 改号完成 → §%d" % target)
        return 0

    print("❌ 连续 5 轮并发冲突，未写盘")
    return 2


if __name__ == "__main__":
    sys.exit(main())
