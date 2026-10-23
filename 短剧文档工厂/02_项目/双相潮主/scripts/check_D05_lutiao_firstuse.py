#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_D05_lutiao_firstuse.py —— D05「律条」词条首用锚点回读断言（S20 落地复核）

背景：企划合规 05:2x 裁决 S20 并派单故事架构落 `shared/D05.json` → v1.3；
派单要求的回读断言（`first_use_ep == 13`｜`definition` 含三层锚点句｜`glossary` 仍 42 条｜其余零变化）
在本脚本里**固化为可复跑的只读断言**，供上游随时独立复核，不必依赖一次性回执。

只读：本脚本**不写任何文件**。

断言清单：
  B1 D05 存在且 JSON 可解析
  B2 `glossary` 条数 == 42
  B3 词条「律条」存在，`first_use_ep` == 13
  B4 `forbidden_synonyms` == ["骨签", "规则石", "低阶律条"]（v1.4 起含自造档位修饰语，遵 S31 ④／OPS-23 面②）
  B5 `definition` 含四层锚点：ep013（实物）／ep035（破境凭证）／ep041（观众获名）／ep044（主角夺取）
  B6 `definition` 含台词禁说带（ep013–ep040 台词与字幕不得出现「律条」三字）
  B7 `definition` 含档位写法规范（普通律条／天律；通称「律条」）
  B8 `power_system.gauge_readings` 中 ep35 条目 event 保持原样（未动）
  B9 `definition` 内「低阶律条」**仅可出现在禁用声明窗口内**（窗口 ＝ 自 `forbidden_synonyms` 提及起至所在分句结束）；窗口外出现即失败 —— D05 v1.5 起 definition 必须枚举 forbidden_synonyms 做「可机读定义」，该枚举属**声明禁用**，不得与「正文使用」混同
  B10 回归面：U02 D06/D07/D08/D11 + 源素材《脉络确认》中不存在「低阶律条」残留
  B12 禁用声明窗口枚举完整性：窗口存在时，窗口内枚举的 forbidden_synonyms 项数必须 == 列表长度（防漏项）
  B11 回归面：全库 JSON 层不存在 D05 以外文档对「律条」写死首用集的断言文本（只报，不判失败）

用法：
  python3 scripts/check_D05_lutiao_firstuse.py --project 02_项目/双相潮主
退出码：0 = 全部断言通过；1 = 有断言失败
"""

import argparse
import json
import os
import sys

ANCHORS = {
    "①实物首现 ep013": "ep013",
    "②破境凭证 ep035": "ep035",
    "③观众获名 ep041": "ep041",
    "④主角夺取 ep044": "ep044",
}
FORBIDDEN_WRITE = "低阶律条"
EPS35_EVENT = "3→4 跨档破境（升 3%），普通律条"
GUARD_FILES = [
    "units/U02/D06.json", "units/U02/D07.json", "units/U02/D08.json",
    "units/U02/D09.json", "units/U02/D11.json", "units/U02/D12.json",
    "units/U02/D16.json", "units/U02/D15.json",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--source", default="", help="源素材目录（可选，如 ../../双相潮主/01_漫剧策划）")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    fails = []
    lines = []

    p = os.path.join(root, "shared", "D05.json")
    if not os.path.isfile(p):
        print(f"❌ B1 失败：找不到 {p}")
        return 1
    try:
        d5 = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"❌ B1 失败：D05 非合法 JSON（{e}）")
        return 1
    lines.append(f"ℹ️ D05 现值：v{d5.get('version')}｜{os.path.getsize(p)} B｜mtime {os.path.getmtime(p):.0f}")

    # B2
    gl = d5.get("glossary", [])
    ok = len(gl) == 42
    lines.append(f"{'✅' if ok else '❌'} B2 `glossary` 条数 == 42 → 实测 {len(gl)}")
    if not ok:
        fails.append("B2")

    entry = next((g for g in gl if g.get("term") == "律条"), None)
    if entry is None:
        print("❌ B3 失败：glossary 无「律条」词条")
        return 1
    lines.append(f"ℹ️ 词条「律条」：first_use_ep={entry.get('first_use_ep')}｜forbidden_synonyms={entry.get('forbidden_synonyms')}")

    # B3
    ok = entry.get("first_use_ep") == 13
    lines.append(f"{'✅' if ok else '❌'} B3 `first_use_ep` == 13 → 实测 {entry.get('first_use_ep')}")
    if not ok:
        fails.append("B3")

    # B4
    ok = entry.get("forbidden_synonyms") == ["骨签", "规则石", "低阶律条"]
    lines.append(f"{'✅' if ok else '❌'} B4 `forbidden_synonyms` == [骨签, 规则石, 低阶律条] → 实测 {entry.get('forbidden_synonyms')}")
    if not ok:
        fails.append("B4")

    d = entry.get("definition", "")
    # B5
    for label, token in ANCHORS.items():
        ok = token in d
        lines.append(f"{'✅' if ok else '❌'} B5 {label} → definition {'含' if ok else '缺'}「{token}」")
        if not ok:
            fails.append(f"B5:{token}")
    # B6
    ok = "台词与字幕不得出现" in d and "ep013–ep040" in d
    lines.append(f"{'✅' if ok else '❌'} B6 台词禁说带（ep013–ep040）→ {'在位' if ok else '缺失'}")
    if not ok:
        fails.append("B6")
    # B7
    ok = ("普通律条" in d and "天律" in d and "档位修饰语" in d)
    lines.append(f"{'✅' if ok else '❌'} B7 档位写法规范（普通律条／天律／通称）→ {'在位' if ok else '缺失'}")
    if not ok:
        fails.append("B7")
    # B9 / B12  definition 内「低阶律条」只允许以「被禁用的写法」身份出现
    #   —— D05 v1.5 起 definition 必须枚举 forbidden_synonyms 以做「可机读定义」，
    #      该枚举属**声明禁用**；B9 原实现是纯子串判定（FORBIDDEN_WRITE not in d），
    #      会把「声明禁用」误判为「使用禁用」→ 假红。判据升级（Q86）：
    #      ① 禁用声明窗口 ＝ 自 definition 中出现 `forbidden_synonyms` 起，至其所在分句结束（下一个「。」「；」）；
    #      ② B9  ＝ 窗口外出现次数 == 0（正文把该词当可用写法 → 失败）；
    #      ③ B12 ＝ 窗口存在时，窗口内枚举的 forbidden_synonyms 项数必须 == 列表长度（防漏项）。
    def _decl_windows(text):
        wins = []
        key = "forbidden_synonyms"
        pos = text.find(key)
        while pos != -1:
            end = len(text)
            for stop in ("。", "；"):
                idx = text.find(stop, pos)
                if idx != -1 and idx < end:
                    end = idx
            wins.append((pos, end))
            pos = text.find(key, pos + len(key))
        return wins

    def _hit_positions(text, token):
        out = []
        p = text.find(token)
        while p != -1:
            out.append(p)
            p = text.find(token, p + len(token))
        return out

    wins = _decl_windows(d)
    hits = _hit_positions(d, FORBIDDEN_WRITE)
    outside = [p for p in hits if not any(lo <= p < hi for lo, hi in wins)]
    ok9 = len(outside) == 0
    lines.append(f"{'✅' if ok9 else '❌'} B9 definition 内「{FORBIDDEN_WRITE}」仅可出现在禁用声明窗口内（窗口外 {len(outside)} 处 / 全篇 {len(hits)} 处）→ {'确认' if ok9 else '命中'}")
    if not ok9:
        fails.append("B9")

    fs = entry.get("forbidden_synonyms") or []
    if wins:
        win_text = "".join(d[lo:hi] for lo, hi in wins)
        got = [w for w in fs if w in win_text]
        ok12 = len(got) == len(fs)
        lines.append(f"{'✅' if ok12 else '❌'} B12 禁用声明窗口枚举完整性（须全列）→ {len(got)}/{len(fs)} 项")
        if not ok12:
            fails.append("B12")
    else:
        ok12 = True
        lines.append(f"✅ B12 禁用声明窗口枚举完整性 → 不适用（definition 未枚举 forbidden_synonyms，窗口 0 个）")

    # B8
    gr = d5.get("power_system", {}).get("gauge_readings", [])
    ep35 = next((g for g in gr if g.get("ep") == 35), None)
    ok = ep35 is not None and ep35.get("event") == EPS35_EVENT
    lines.append(f"{'✅' if ok else '❌'} B8 `gauge_readings` ep35 event 保持原样 → 实测 {(ep35 or {}).get('event')!r}")
    if not ok:
        fails.append("B8")

    # B10 回归面：自造档位修饰语残留
    residues = []
    for rel in GUARD_FILES:
        fp = os.path.join(root, rel)
        if os.path.isfile(fp):
            n = open(fp, encoding="utf-8").read().count(FORBIDDEN_WRITE)
            if n:
                residues.append(f"{rel}×{n}")
    if args.source:
        sp = os.path.abspath(args.source)
        if os.path.isdir(sp):
            for dp, dn, fn in os.walk(sp):
                for f in fn:
                    if f.endswith(".md"):
                        fp = os.path.join(dp, f)
                        n = open(fp, encoding="utf-8", errors="ignore").read().count(FORBIDDEN_WRITE)
                        if n:
                            residues.append(f"{os.path.relpath(fp, sp)}×{n}")
    ok = not residues
    lines.append(f"{'✅' if ok else '❌'} B10 回归面「{FORBIDDEN_WRITE}」残留 → {'0 处' if ok else residues}")
    if not ok:
        fails.append("B10")

    # B11 只报：全库 JSON 层是否有别处写死「律条」首用集
    hardcoded = []
    for dp, dn, fn in os.walk(root):
        if any(x in dp for x in [".git", "__pycache__", "_bak", "render", "reports", "迁移备份"]):
            continue
        for f in fn:
            if not f.endswith(".json"):
                continue
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, root)
            if rel.endswith("shared/D05.json"):
                continue
            s = open(fp, encoding="utf-8", errors="ignore").read()
            for token in ("first_use_ep\": 41", "first_use_ep\":41"):
                if token in s:
                    hardcoded.append(f"{rel}: {token}")
    lines.append(f"{'ℹ️' if not hardcoded else '⚠️'} B11 他文档写死「first_use_ep: 41」→ {hardcoded or '无'}（历史留痕不计失败）")

    print("\n".join(lines))
    n_assert = sum(1 for l in lines if l.startswith("✅") or l.startswith("❌"))
    print(f"\n■ 结果：断言 {n_assert} 条｜通过 {n_assert - len(fails)}｜失败 {len(fails)}")
    if fails:
        print("❌ 失败项：" + ", ".join(fails))
        return 1
    print("✅ D05「律条」首用锚点回读断言全部通过（S20 落地成立）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
