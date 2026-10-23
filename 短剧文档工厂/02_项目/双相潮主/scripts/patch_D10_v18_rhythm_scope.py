#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D10 v1.7 -> v1.8 补丁（视觉设定岗，R-032 派活 · 2026-10-23）

唯一改动：`shared/D10.json` 的 `camera_language.rhythm` 一处 ＋ `version`。
原因：v1.7 由企划合规 S6 裁决落地，例外句中的「（当前仅 ep002 段3）」是**时点快照**，
而 D10 是 **shared 共享层**（服务 U01–U20 全 20 单元）——把 U01 的实例钉成全局限定，
U02 起 D07 若新增 mode=并行 段，该句立即变成假陈述。
改法：把「当前仅」改为作用域标注「U01 实例」，判据（D07 mode=并行）保持不变、规则永真。

特性：
  - 文本级精确替换（不重排 JSON 其余字节）
  - 命中数断言：对不上即中止不写盘
  - 落盘后 deep-compare：除 rhythm 与 version 外，其余字段必须逐值相等
  - 幂等可复跑：已是 v1.8 则直接退出
"""
import json
import os
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(PROJECT, "shared", "D10.json")

OLD_FRAG = "D07 标注 mode=并行的段（当前仅 ep002 段3）"
NEW_FRAG = "凡 D07 标注 mode=并行的段（U01 实例：ep002 段3）"
OLD_VER = '"version": "v1.7"'
NEW_VER = '"version": "v1.8"'

if not os.path.exists(TARGET):
    sys.exit("ABORT: 找不到 %s" % TARGET)

with open(TARGET, "r", encoding="utf-8") as f:
    raw = f.read()

# --- 幂等检查 ---
if NEW_FRAG in raw and OLD_VER not in raw:
    print("SKIP: 已是 v1.8（rhythm 已含新措辞），无需写盘")
    sys.exit(0)

before = json.loads(raw)

# --- 断言 ---
if raw.count(OLD_FRAG) != 1:
    sys.exit("ABORT: 旧串命中 %d 次（期望 1）" % raw.count(OLD_FRAG))
if NEW_FRAG in raw:
    sys.exit("ABORT: 新串已存在（命中 %d 次），拒绝写盘" % raw.count(NEW_FRAG))
if raw.count(OLD_VER) != 1:
    sys.exit("ABORT: version 标记命中 %d 次（期望 1）" % raw.count(OLD_VER))

# --- 写盘 ---
out = raw.replace(OLD_FRAG, NEW_FRAG).replace(OLD_VER, NEW_VER)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(out)

# --- 落盘后校验 ---
after = json.loads(out)

if after.get("version") != "v1.8":
    sys.exit("ABORT: 落盘后 version != v1.8")
if out.count(NEW_FRAG) != 1:
    sys.exit("ABORT: 落盘后新串命中数异常")
if OLD_FRAG in out:
    sys.exit("ABORT: 落盘后旧串仍存在")

rhythm_before = before["camera_language"]["rhythm"]
rhythm_after = after["camera_language"]["rhythm"]
if rhythm_before == rhythm_after:
    sys.exit("ABORT: rhythm 未发生变化")

# 除 rhythm / version 外逐值相等
b2 = dict(before)
a2 = dict(after)
b2.pop("version"); a2.pop("version")
b2["camera_language"] = dict(before["camera_language"]); b2["camera_language"].pop("rhythm")
a2["camera_language"] = dict(after["camera_language"]);  a2["camera_language"].pop("rhythm")
if b2 != a2:
    sys.exit("ABORT: 除 rhythm/version 外存在其他差异，拒绝宣告完成")

print("OK: D10 v1.7 -> v1.8")
print("  rhythm 改动点数: 1")
print("  旧: ...%s..." % OLD_FRAG)
print("  新: ...%s..." % NEW_FRAG)
print("  version: v1.7 -> v1.8")
print("  其余字段 deep-compare: 全等")
