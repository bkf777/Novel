#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_schema_hook_type.py —— 03_规格/schema.json 增补 D06 的钩子类型字段

背景（2026-10-23）
------------------
用户要求学习 https://github.com/0xsline/short-drama/tree/main 这个 skill 并据其描述改写。
该 skill 的核心方法论之一是 **5 种钩子类型**（悬念钩／反转钩／情绪钩／信息钩／危机钩）
及其配比参考（情绪 30-40%、悬念 20-30%、危机 10-20%、信息 10-20%、反转 5-15%）。

我们的 D06 只有 `hook_in`／`hook_out` 两段文字，**没有任何"钩子类型"的显式标注**，
因此：
  · 编剧/分镜/质检都只能凭感觉判断一集靠什么留住观众；
  · 无法做配比审计（skill 的节奏曲线与钩子配比检查都建立在"每集有类型"之上）；
  · 剧本正本里也就写不出 skill 格式要求的 `Hook Type` 字段。

处置
----
在 `D06.properties.episodes.items.properties` 下增两个**可选**字段：
  · `hook_type`         —— enum：悬念／反转／情绪／信息／危机
  · `hook_type_reason`  —— string，判定依据（为什么这一集是这个钩子）

⚠ **两个字段都不进 `required`** ⇒ 任何单元缺失都不会报 V1 错，只在写了的时候校验枚举合法性。
⚠ D06 的 `additionalProperties` 是 **false** ⇒ 不改 schema 就会把新增字段判成非法字段，
   所以这一步是「加钩子类型」的**前置条件**，不是可选项。

幂等：字段已存在且 schema 已含这两个键则不写盘。
用法：python3 scripts/patch_schema_hook_type.py [--dry-run]
"""
import json
import os
import re
import shutil
import sys
import datetime
import hashlib

FACTORY = "/Users/ezreal/projects/小说创作/短剧文档工厂"
SCHEMA = os.path.join(FACTORY, "03_规格", "schema.json")
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = os.path.join(FACTORY, "02_项目", "双相潮主", "reports", f"_bak_schema_hooktype_{STAMP}")

HOOK_TYPES = ["悬念", "反转", "情绪", "信息", "危机"]


def fingerprint(p):
    b = open(p, "rb").read()
    return {"version": json.loads(b.decode("utf-8")).get("version"),
            "size": len(b), "sha16": hashlib.sha256(b).hexdigest()[:16],
            "mtime": os.path.getmtime(p)}


def main():
    fp0 = fingerprint(SCHEMA)
    print(f"   基线：schema.json {fp0['size']} B sha16={fp0['sha16']}")
    with open(SCHEMA, encoding="utf-8") as f:
        d = json.load(f)

    ep = d["D06"]["properties"]["episodes"]["items"]
    props = ep.setdefault("properties", {})
    changed = False
    if "hook_type" not in props:
        props["hook_type"] = {
            "type": "string",
            "enum": HOOK_TYPES,
            "description": ("本集结尾钩子类型（short-drama skill 的 5 类）。"
                            "可选字段；配比参考：情绪 30-40%、悬念 20-30%、危机 10-20%、"
                            "信息 10-20%、反转 5-15%。"),
        }
        changed = True
        print("   ✅ 增补 D06.episodes.items.properties.hook_type")
    if "hook_type_reason" not in props:
        props["hook_type_reason"] = {
            "type": "string",
            "description": "钩子类型判定依据：为什么这一集的结尾靠这个钩子留住观众。",
        }
        changed = True
        print("   ✅ 增补 D06.episodes.items.properties.hook_type_reason")

    if not changed:
        print("   无变化，不写盘")
        return
    if DRY:
        print("   [dry-run] 将写 schema.json")
        return
    now = fingerprint(SCHEMA)
    if now != fp0:
        print(f"❌ 并发守卫：schema.json 在读盘后被改动（{fp0} → {now}）⇒ 放弃写盘")
        sys.exit(1)
    os.makedirs(BAK, exist_ok=True)
    shutil.copy2(SCHEMA, os.path.join(BAK, "schema.json"))
    with open(SCHEMA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"   ✅ 写 schema.json｜备份 {BAK}")


if __name__ == "__main__":
    main()
