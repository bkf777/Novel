#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_ledger_chapnum.py —— 台账取号函数的**单元测试**（可复跑）

为什么必须有这个文件：
  2026-10-23 本岗在重写 `append_ledger_section.py` 时，把中文数字表里的
  「七」手误写成 `8-3`（= 5）——**一个静默的取号错误**。若未被发现，台账
  章号会算错 → **撞号**（前 106 章都是中文数字，「七十七」「六十七」等
  章节都会被读成别的值）。
  → **取号函数必须有单测**，这与本岗向企划合规建议的「取号前断言全库章号
  可解析率 == 100%」是同一条纪律的两端：**函数要对，改函数的人也要被测。**

用法：python3 scripts/test_ledger_chapnum.py
退出码：0＝全通过；1＝有失败项。
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "append_ledger_section.py")

spec = importlib.util.spec_from_file_location("ledger_chapnum", TARGET)
mod = importlib.util.module_from_spec(spec)
# 该模块在 import 时会执行「读台账 + 追加章节」的副作用 → 必须先拦掉 argv 解析
sys.argv = [sys.argv[0]]
_orig_open = open
_src_guarded = False
try:
    # 用源码级方式只取函数，避免执行模块顶层副作用
    src = open(TARGET, encoding="utf-8").read()
    ns = {}
    # 截取到 SEC 定义之前（函数区）
    head = src.split("txt = open(REG", 1)[0]
    exec(compile(head, TARGET, "exec"), ns)
    cn2int = ns["cn2int"]
    int2cn = ns["int2cn"]
finally:
    pass

fails = []
def eq(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")
    print(f"  {'✅' if got == want else '❌'} {name}: {got!r}")

print("=== cn2int：中文数字 → 整数 ===")
for s, want in [
    ("零", 0), ("一", 1), ("七", 7), ("八", 8), ("九", 9),
    ("十", 10), ("十一", 11), ("十九", 19), ("二十", 20), ("二十一", 21),
    ("六十四", 64), ("六十五", 65), ("六十六", 66), ("六十七", 67),
    ("七十", 70), ("七十七", 77), ("八十八", 88), ("九十九", 99),
    ("一百", 100), ("一百零一", 101), ("一百零七", 107), ("一百零九", 109),
    ("一百一十", 110),
    ("7", 7), ("107", 107), ("110", 110),
]:
    eq(f"cn2int({s!r})", cn2int(s), want)

print("\n=== cn2int：非法输入必须返回 None（不得静默取错值）===")
for s in ["甲", "低阶", "abc", ""]:
    eq(f"cn2int({s!r})", cn2int(s), None)

print("\n=== int2cn：整数 → 章号串（Q85：父章一律中文数字）===")
for n, want in [
    (1, "一"), (7, "七"), (9, "九"), (10, "十"), (11, "十一"), (19, "十九"),
    (20, "二十"), (21, "二十一"), (64, "六十四"), (65, "六十五"), (66, "六十六"),
    (67, "六十七"), (70, "七十"), (77, "七十七"), (99, "九十九"),
    # 2026-10-23 按 Q85 修正：n>=100 也输出中文（旧行为返回阿拉伯，违反「父章一律中文」）
    (100, "一百"), (101, "一百零一"), (107, "一百零七"), (110, "一百一十"),
    (111, "一百一十一"), (118, "一百一十八"), (119, "一百一十九"),
    (120, "一百二十"), (127, "一百二十七"), (134, "一百三十四"), (999, "九百九十九"),
]:
    eq(f"int2cn({n})", int2cn(n), want)

print("\n=== int2cn：输出不得含阿拉伯数字（Q85 父章中文硬要求，0–999 全域）===")
_bad_digit = [(n, int2cn(n)) for n in range(0, 1000) if any(ch.isdigit() for ch in int2cn(n))]
eq("含阿拉伯数字的取值数", len(_bad_digit), 0)

print("\n=== 往返一致性：int2cn(n) → cn2int 须回到 n（0–999 全域）===")
_bad_rt = [(n, int2cn(n), cn2int(int2cn(n))) for n in range(0, 1000) if cn2int(int2cn(n)) != n]
eq("往返不一致的取值数", len(_bad_rt), 0)
print(f"  ℹ️ 0–999 共 1000 个取值，逐一往返核对：{'全过 ✅' if not _bad_rt else '❌ ' + str(_bad_rt[:5])}")

print("\n=== 与本岗实盘台账章号表的交叉校验（真实标题全量）===")
REG = os.path.join(os.path.dirname(HERE), "99_交付说明.md")
import re
if os.path.exists(REG):
    txt = open(REG, encoding="utf-8").read()
    heads = re.findall(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)
    vals = [cn2int(h) for h in heads]
    bad = [(h, v) for h, v in zip(heads, vals) if v is None]
    dup = [v for v in set(vals) if v is not None and vals.count(v) > 1]
    eq("全量标题可解析（None 数）", len(bad), 0)
    eq("重复章号数", len(dup), 0)
    eq("可解析章号总数", len(vals), len(heads))
else:
    print(f"  ⚠️ 台账不存在：{REG}（跳过交叉校验）")

print()
if fails:
    print(f"❌ 单测失败 {len(fails)} 项：")
    for f in fails:
        print("   -", f)
    sys.exit(1)
print("✅ 取号函数单测全部通过")
sys.exit(0)
