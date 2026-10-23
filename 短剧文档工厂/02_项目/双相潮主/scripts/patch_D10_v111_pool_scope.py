#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D10 v1.10 -> v1.11 补丁（视觉设定岗 · 2026-10-23）

唯一改动：`consistency_rules[17]`「共享池下放口径」**末尾补一句适用范围限定**，version v1.10 -> v1.11。

【为什么改】
v1.10 落盘后实测发现：把该规则当成「所有单元都必须达标」会产生**回溯性假缺漏**——
  - 「net fire illuminating more than a small contact patch of skin」是 D10 **v1.9** 才进池的条目；
  - U01 D12 **v1.5**（已由企划合规 Q61 判定为现行值并锁定、企划合规 §91.3 核销）的成卡时点**早于 v1.9**，
    池里当时没有这条 → 以 v1.10 的池口径回溯要求 U01，等于用后来的口径否定当时的验收结论。
  - 同理，「religious processions／candle-lit shrines」也是本岗 v1.10 扩 RELIG 组后才逐卡下放的。
→ 故补「适用范围：自 v1.10 起适用；此前已验收单元按其验收时的池口径，不回溯要求」，
  把「池条目缺项」与「池口径演进」两件事分开，避免下一位拿新口径去判旧单元。
  U01 的 3 条缺项已作为**发现**上报企划合规，由其决定是否开返修单，本岗不擅改已锁定交付物。
"""
import json, os, shutil, sys, time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(PROJECT, "shared", "D10.json")
BACKUP_DIR = os.path.join(PROJECT, "reports", "_bak_D10_v111_pool_scope_20261023")

OLD_TAIL = ('逐单元的可机械判定口径为：共享池中非血腥语义条目须在该单元被覆盖。'
            '来源：企划合规 2026-10-23 裁定（D18 U02-R31 同批）。"')
NEW_TAIL = ('逐单元的可机械判定口径为：共享池中非血腥语义条目须在该单元被覆盖。'
            '适用范围：自 v1.10 起适用；此前已验收单元按其验收时的池口径，不回溯要求'
            '（池条目随 v1.9／v1.10 演进，新增条目不构成旧单元缺漏）。'
            '来源：企划合规 2026-10-23 裁定（D18 U02-R31 同批）。"')
OLD_VER = '"version": "v1.10"'
NEW_VER = '"version": "v1.11"'
KEY = "共享池下放口径"

if not os.path.exists(TARGET):
    sys.exit("ABORT: 找不到 %s" % TARGET)
raw = open(TARGET, encoding="utf-8").read()
if NEW_TAIL in raw and NEW_VER in raw:
    print("SKIP: 已是 v1.11（适用范围限定已加），无需写盘"); sys.exit(0)
before = json.loads(raw)
for name, old in (("规则尾串", OLD_TAIL), ("version", OLD_VER)):
    n = raw.count(old)
    if n != 1:
        sys.exit("ABORT: %s 命中 %d 次（期望 1）——磁盘可能已被他人改动，请重新认盘" % (name, n))

os.makedirs(BACKUP_DIR, exist_ok=True)
shutil.copy2(TARGET, os.path.join(BACKUP_DIR, "D10.json.bak"))
st = os.stat(TARGET); guard = (st.st_mtime_ns, st.st_size); time.sleep(0.2); st2 = os.stat(TARGET)
if (st2.st_mtime_ns, st2.st_size) != guard:
    sys.exit("ABORT: 写盘前检测到目标文件被并发改动，拒绝写盘")

out = raw.replace(OLD_TAIL, NEW_TAIL).replace(OLD_VER, NEW_VER)
tmp = TARGET + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(out); f.flush(); os.fsync(f.fileno())
os.replace(tmp, TARGET)

disk = open(TARGET, encoding="utf-8").read(); after = json.loads(disk)
if disk != out: sys.exit("ABORT: 回读内容与预期不一致")
if after.get("version") != "v1.11": sys.exit("ABORT: version != v1.11")
if len(after["consistency_rules"]) != len(before["consistency_rules"]): sys.exit("ABORT: 条数异常")
if not any(KEY in r and "适用范围：自 v1.10 起适用" in r for r in after["consistency_rules"]):
    sys.exit("ABORT: 适用范围限定未落盘")
b2, a2 = dict(before), dict(after)
for k in ("version", "consistency_rules"): b2.pop(k, None); a2.pop(k, None)
if b2 != a2: sys.exit("ABORT: 除 consistency_rules/version 外存在其他差异")
# 本补丁的设计意图就是改**末条**（补适用范围限定），其余条目必须逐条未动
if len(before["consistency_rules"]) != len(after["consistency_rules"]):
    sys.exit("ABORT: 条数变化，拒绝宣告完成")
for o, n in zip(before["consistency_rules"][:-1], after["consistency_rules"][:-1]):
    if o != n: sys.exit("ABORT: 除末条外的 consistency_rules 条目被改动")
if after["consistency_rules"][-1] == before["consistency_rules"][-1]:
    sys.exit("ABORT: 末条未被修改，补丁未生效")
print("OK: D10 v1.10 -> v1.11")
print("  consistency_rules: %d -> %d（条目 17 末尾补适用范围限定，其余逐条未改）"
      % (len(before["consistency_rules"]), len(after["consistency_rules"])))
print("  version: v1.10 -> v1.11")
print("  备份: %s" % os.path.join(BACKUP_DIR, "D10.json.bak"))
