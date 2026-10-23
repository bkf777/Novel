#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D10 v1.8 -> v1.9 补丁（视觉设定岗 · 2026-10-23）

唯一改动：`shared/D10.json` 的
  ① `consistency_rules` 追加 1 条「净火照射范围」
  ② `negatives` 追加 1 条对应负向词
  ③ `version` v1.8 -> v1.9

【为什么改】
U02 ep010 的净火画面口径在**共享层 D10 里无对应条款**：
  - 来源（D07 上游 / D08 下游，两处一致）：
      D07 ep010 `scene_needs`：「双相净火为黑白双焰、只照亮接触处一小片皮肤，周围仍是工业冷光」
      D08 ep010 action 段：「净火演示位只照亮接触处一小片皮肤，厂房其余部分保持工业冷光」（compliance_added）
  - D10 现状缺口：`consistency_rules[12]`「不形成持续暖主光、不改变环境冷调」**限定于电焊火花及金属局部暖反光**；
    `[13]` 是色板收敛条，**均不涉及净火的空间照射范围**。
  - 后果：D12 是 D10 下游，U02 的 D12 落笔时若写「只照亮接触处一小片皮肤」，
    在 D10 里**无据可依** → D12 与 D10 口径分裂（台本编剧 D08 里引 D10[13] 其实引得不准）。
  → 本补丁把该口径**收口进共享层**，让 U02 D12 有溯源依据。

【作用域限定（防误伤 U01）】
新规则仅约束「净火作用于灰斑者（净身位／演示位）时」。
U01 全库实测无此镜位：U01 的「净火」只以**色板名（净火白）**与合规 note 出现；
唯一「净火作用于人」的镜位 ep007 镜2，其 D11/D12 已写「黑白双焰**贴上皮肤表面**」，
本就符合「只照亮接触处一小片皮肤」→ **U01 零影响、零返修**。

特性：文本级精确替换（不重排 JSON 其余字节）／命中数断言／落盘后 deep-compare／幂等可复跑。
"""
import json
import os
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(PROJECT, "shared", "D10.json")

# ── 待插入的两条内容 ───────────────────────────────────────────────────────
OLD_NEG_TAIL = '    "recognizable real-world landmark"\n'
NEW_NEG_TAIL = ('    "recognizable real-world landmark",\n'
                '    "net fire illuminating more than a small contact patch of skin"\n')

OLD_RULE_TAIL = ('    "母题锁定：14 条视觉母题的 seed 家族固定，同一母题跨集不换形；'
                 '改母题须改本文件并递增版本，不得在单元文件里就地改写。"\n')
NEW_RULE_TAIL = ('    "母题锁定：14 条视觉母题的 seed 家族固定，同一母题跨集不换形；'
                 '改母题须改本文件并递增版本，不得在单元文件里就地改写。",\n'
                 '    "净火照射范围：净火作用于灰斑者（净身位／演示位）时，只照亮接触处一小片皮肤，'
                 '其余环境保持原有冷调不变。来源：D07 ep010 scene_needs／D08 ep010 action 段（合规增量）。"\n')

OLD_VER = '"version": "v1.8"'
NEW_VER = '"version": "v1.9"'

NEW_RULE_KEY = "净火照射范围"
NEW_NEG_KEY = "net fire illuminating more than a small contact patch of skin"

if not os.path.exists(TARGET):
    sys.exit("ABORT: 找不到 %s" % TARGET)

with open(TARGET, "r", encoding="utf-8") as f:
    raw = f.read()

# ── 幂等检查（已是新版则直接退出，不重复写盘）──────────────────────────────
if NEW_RULE_KEY in raw and NEW_VER in raw:
    print("SKIP: 已是 v1.9（净火照射范围条款已在），无需写盘")
    sys.exit(0)

before = json.loads(raw)

# ── 断言：每处旧串必须恰好命中 1 次 ─────────────────────────────────────────
for name, old in (("negatives 尾条", OLD_NEG_TAIL),
                   ("consistency_rules 尾条", OLD_RULE_TAIL),
                   ("version 标记", OLD_VER)):
    n = raw.count(old)
    if n != 1:
        sys.exit("ABORT: %s 命中 %d 次（期望 1）" % (name, n))
if NEW_RULE_KEY in raw:
    sys.exit("ABORT: 新规则已存在，拒绝写盘")
if NEW_NEG_KEY in raw:
    sys.exit("ABORT: 新负向词已存在，拒绝写盘")

# ── 写盘 ───────────────────────────────────────────────────────────────────
out = (raw.replace(OLD_NEG_TAIL, NEW_NEG_TAIL)
          .replace(OLD_RULE_TAIL, NEW_RULE_TAIL)
          .replace(OLD_VER, NEW_VER))

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(out)

# ── 落盘后校验 ─────────────────────────────────────────────────────────────
after = json.loads(out)

if after.get("version") != "v1.9":
    sys.exit("ABORT: 落盘后 version != v1.9")
if len(after.get("consistency_rules", [])) != len(before.get("consistency_rules", [])) + 1:
    sys.exit("ABORT: consistency_rules 条数增量异常")
if len(after.get("negatives", [])) != len(before.get("negatives", [])) + 1:
    sys.exit("ABORT: negatives 条数增量异常")
if not any(NEW_RULE_KEY in r for r in after["consistency_rules"]):
    sys.exit("ABORT: 新规则未落盘")
if NEW_NEG_KEY not in after["negatives"]:
    sys.exit("ABORT: 新负向词未落盘")

# 除 consistency_rules / negatives / version 外逐值相等
b2, a2 = dict(before), dict(after)
for k in ("version", "consistency_rules", "negatives"):
    b2.pop(k, None)
    a2.pop(k, None)
if b2 != a2:
    sys.exit("ABORT: 除 consistency_rules/negatives/version 外存在其他差异，拒绝宣告完成")

# 新条目必须是追加（不改动既有条目）
for old, new in zip(before["consistency_rules"], after["consistency_rules"][:len(before["consistency_rules"])]):
    if old != new:
        sys.exit("ABORT: 既有 consistency_rules 条目被改动")
for old, new in zip(before["negatives"], after["negatives"][:len(before["negatives"])]):
    if old != new:
        sys.exit("ABORT: 既有 negatives 条目被改动")

print("OK: D10 v1.8 -> v1.9")
print("  consistency_rules: %d -> %d（追加 1 条：净火照射范围）"
      % (len(before["consistency_rules"]), len(after["consistency_rules"])))
print("  negatives:         %d -> %d（追加 1 条）"
      % (len(before["negatives"]), len(after["negatives"])))
print("  version: v1.8 -> v1.9")
print("  其余字段 deep-compare: 全等；既有条目逐条比对: 未改动")
