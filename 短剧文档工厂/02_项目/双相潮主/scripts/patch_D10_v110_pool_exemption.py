#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D10 v1.9 -> v1.10 补丁（视觉设定岗 · 2026-10-23）

唯一改动：`shared/D10.json` 的
  ① `consistency_rules` 追加 1 条「共享池下放口径」
  ② `version` v1.9 -> v1.10

【为什么改（企划合规 2026-10-23 裁定的落地）】
企划合规就视觉设定台账 §九十 §90.4（U02 D12 的「D10 共享池 46 条的 13 条血腥变体
未逐卡下放」）裁定：「**维持现状，语义冗余豁免成立**」，并要求
「**在 U02 D12 后续升版时保留这条豁免说明，避免下一位把『共享池未逐卡下放』误判成缺漏**」。

【落点判定（与企划合规指定落点的差异，须报备）】
企划合规指定落点为「U02 D12」，但 **D12 schema 装不下注记**：
`03_规格/schema.json` 的 D12 顶层为 `additionalProperties: false`，
properties 仅 `doc_id / unit / version / status / cards`；`cards[].items` 同样
`additionalProperties: false` → **无任何可承载说明的合法字段**（企划合规 §91.8 亦已
认定「例外只能落在校验器侧」）。
→ 本岗按「**池的 owner 落池的定义处**」处理：改为写入 **D10.consistency_rules**。
理由：① `negatives` 共享池定义在 D10，豁免是「本池怎么用」的口径，归属 D10 天然；
② D10 `consistency_rules` 已有同体例镜头级口径（第 15 条＝人物锚点闭合、第 17 条＝
净火照射范围），新增完全同体例；③ D12 的构建脚本本就从 D10 现读锚点／母题／色板，
下一位做 D12 升版时必然重读 D10，**落在 D10 比落在 D12 更根本、更不易被漏读**。
→ 落点差异已在本岗回执中报请企划合规确认。

【口径内容要点（可机械判定）】
- 共享池 46 条 = 全片池，各单元 D12 **按镜位风险择取，不要求逐卡全带**；
- 其中 **13 条血腥语义变体**（exposed skull／decaying skin 等）与每卡必带的零血腥核心块
  语义重复 → **按语义冗余豁免，不属缺漏**；
- 下游判读「共享池未逐卡下放」**不得据此报缺漏**；
- 逐单元的**可机械判定口径**：共享池中**非血腥语义条目须在该单元被覆盖**。

特性：文本级精确替换（不重排 JSON 其余字节）／命中数断言／写前备份＋并发守卫／
原子写／落盘后 deep-compare／既有条目逐条比对／幂等可复跑。
"""
import json
import os
import shutil
import sys
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(PROJECT, "shared", "D10.json")
BACKUP_DIR = os.path.join(PROJECT, "reports", "_bak_D10_v110_pool_exemption_20261023")

NEW_RULE_KEY = "共享池下放口径"
OLD_VER = '"version": "v1.9"'
NEW_VER = '"version": "v1.10"'

OLD_RULE_TAIL = ('    "净火照射范围：净火作用于灰斑者（净身位／演示位）时，只照亮接触处一小片皮肤，'
                 '其余环境保持原有冷调不变。来源：D07 ep010 scene_needs／D08 ep010 action 段（合规增量）。"\n')
NEW_RULE_TAIL = (
    '    "净火照射范围：净火作用于灰斑者（净身位／演示位）时，只照亮接触处一小片皮肤，'
    '其余环境保持原有冷调不变。来源：D07 ep010 scene_needs／D08 ep010 action 段（合规增量）。",\n'
    '    "共享池下放口径：本文件 negatives 的 46 条为全片共享负向词池，各单元 D12 按镜位风险择取，'
    '不要求逐卡全带；其中血腥语义的变体写法（如 exposed skull、decaying skin 等共 13 条）'
    '与每卡必带的零血腥核心块语义重复，按语义冗余豁免，不属缺漏——'
    '下游判读「共享池未逐卡下放」时不得据此报缺漏。'
    '逐单元的可机械判定口径为：共享池中非血腥语义条目须在该单元被覆盖。'
    '来源：企划合规 2026-10-23 裁定（D18 U02-R31 同批）。"\n'
)

if not os.path.exists(TARGET):
    sys.exit("ABORT: 找不到 %s" % TARGET)

with open(TARGET, "r", encoding="utf-8") as f:
    raw = f.read()

# ── 幂等检查（已是新版则直接退出，不重复写盘）──────────────────────────────
if NEW_RULE_KEY in raw and NEW_VER in raw:
    print("SKIP: 已是 v1.10（共享池下放口径条款已在），无需写盘")
    sys.exit(0)

before = json.loads(raw)

# ── 断言：每处旧串必须恰好命中 1 次 ─────────────────────────────────────────
for name, old in (("consistency_rules 尾条", OLD_RULE_TAIL), ("version 标记", OLD_VER)):
    n = raw.count(old)
    if n != 1:
        sys.exit("ABORT: %s 命中 %d 次（期望 1）——磁盘可能已被他人改动，请重新认盘" % (name, n))
if NEW_RULE_KEY in raw:
    sys.exit("ABORT: 新规则已存在，拒绝写盘")

# ── 写前备份 + 并发守卫（写前再核一次 mtime/size，防并发覆盖）──────────────
os.makedirs(BACKUP_DIR, exist_ok=True)
shutil.copy2(TARGET, os.path.join(BACKUP_DIR, "D10.json.bak"))
st = os.stat(TARGET)
guard = (st.st_mtime_ns, st.st_size)
time.sleep(0.2)
st2 = os.stat(TARGET)
if (st2.st_mtime_ns, st2.st_size) != guard:
    sys.exit("ABORT: 写盘前检测到目标文件被并发改动，拒绝写盘")

# ── 写盘（临时文件 + fsync + os.replace，原子替换）─────────────────────────
out = (raw.replace(OLD_RULE_TAIL, NEW_RULE_TAIL)
          .replace(OLD_VER, NEW_VER))
tmp = TARGET + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(out)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, TARGET)

# ── 落盘后校验（回读文件，不信任内存对象）──────────────────────────────────
with open(TARGET, "r", encoding="utf-8") as f:
    disk = f.read()
after = json.loads(disk)

if disk != out:
    sys.exit("ABORT: 回读内容与预期不一致")
if after.get("version") != "v1.10":
    sys.exit("ABORT: 落盘后 version != v1.10")
if len(after.get("consistency_rules", [])) != len(before.get("consistency_rules", [])) + 1:
    sys.exit("ABORT: consistency_rules 条数增量异常")
if not any(NEW_RULE_KEY in r for r in after["consistency_rules"]):
    sys.exit("ABORT: 新规则未落盘")
if len(after.get("negatives", [])) != len(before.get("negatives", [])):
    sys.exit("ABORT: negatives 条数被动，拒绝宣告完成")

# 除 consistency_rules / version 外逐值相等
b2, a2 = dict(before), dict(after)
for k in ("version", "consistency_rules"):
    b2.pop(k, None)
    a2.pop(k, None)
if b2 != a2:
    sys.exit("ABORT: 除 consistency_rules/version 外存在其他差异，拒绝宣告完成")

# 既有 consistency_rules 条目必须逐条未改动（纯追加）
for old, new in zip(before["consistency_rules"], after["consistency_rules"][:len(before["consistency_rules"])]):
    if old != new:
        sys.exit("ABORT: 既有 consistency_rules 条目被改动")

print("OK: D10 v1.9 -> v1.10")
print("  consistency_rules: %d -> %d（追加 1 条：共享池下放口径）"
      % (len(before["consistency_rules"]), len(after["consistency_rules"])))
print("  version: v1.9 -> v1.10")
print("  negatives: %d -> %d（未动）" % (len(before["negatives"]), len(after["negatives"])))
print("  其余字段 deep-compare: 全等；既有 consistency_rules 条目逐条比对: 未改动")
print("  备份: %s" % os.path.join(BACKUP_DIR, "D10.json.bak"))
