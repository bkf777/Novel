#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_D09.py —— 对白表与角色语气卡生成器（单元参数化，U02 起统一入口）

用法：
  python3 scripts/build_D09.py --project 02_项目/双相潮主 --unit U02
  python3 scripts/build_D09.py --project 02_项目/双相潮主 --unit U02 --dry-run

设计：
  · **对白行直接从 D08.json 抽取**（ep/char_id/text 三元组与 D08 完全一致），
    不另建一份台词清单 —— 否则两处一漂，V6 的潜台词匹配就会失配。
  · 潜台词与语气卡在同目录 d09_content_<UNIT>.py。
  · 自检（写盘前拦）：
      ① D08 每句台词都在 D09 登记（V6 靠三元组匹配潜台词，缺登记＝从严一票否决）
      ② 每行 subtext 非空（潜台词缺失＝保守从严一票否决）
      ③ char_id ∈ D04；未成年角色不得有台词（Q14=C）
      ④ 台词不命中贬称词；正文与口头禅不命中禁词表
      ⑤ 全文不命中 D05 禁用同义写法
      ⑥ 语气卡字段合法、char_id ∈ D04、tone_rules 非空
"""

import argparse
import importlib
import json
import os
import re
import sys


def _find_factory_root(start: str) -> str:
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "03_规格")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise SystemExit("❌ 找不到含 03_规格 的工厂根目录")


FACTORY_ROOT = _find_factory_root(os.path.dirname(os.path.abspath(__file__)))
SPEC_DIR = os.path.join(FACTORY_ROOT, "03_规格")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def scan_text(node, path, banned, errors, out):
    """递归扫描字符串节点里的禁用写法。"""
    if isinstance(node, str):
        for w in sorted(banned):
            if w and w in node:
                errors.append(f"{path}: 命中禁用写法「{w}」:: {node[:50]}")
                out.add(w)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            scan_text(x, f"{path}[{i}]", banned, errors, out)
    elif isinstance(node, dict):
        for k, v in node.items():
            scan_text(v, f"{path}.{k}", banned, errors, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="版本守卫下强行覆盖（人工确认后使用）")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    unit = args.unit

    D08 = load_json(os.path.join(project, "units", unit, "D08.json"))
    D04 = load_json(os.path.join(project, "shared", "D04.json"))
    D05 = load_json(os.path.join(project, "shared", "D05.json"))
    RULES = load_json(os.path.join(SPEC_DIR, "rules.json"))

    content = importlib.import_module(f"d09_content_{unit}")
    SUBTEXT = content.SUBTEXT
    VOICE_CARDS = content.VOICE_CARDS
    VERSION = getattr(content, "VERSION", "v1.0")
    STATUS = getattr(content, "STATUS", "in_review")

    chars = {c["id"]: c for c in D04["characters"]}
    minors = {c["id"] for c in D04["characters"] if c.get("minor")}
    derogatory = set(RULES["derogatory_terms"])
    forbidden = set(RULES["forbidden_words"])
    # D05 禁用同义写法（V5 口径）—— D09 全文扫描
    banned = set(forbidden)
    for g in D05["glossary"]:
        banned |= set(g.get("forbidden_synonyms") or [])

    errors = []
    lines = []
    for ep in D08["episodes"]:
        idx = 0
        for b in ep["body"]:
            if b["type"] != "dialogue":
                continue
            idx += 1
            key = (ep["ep"], idx)
            if key not in SUBTEXT:
                errors.append(f"缺潜台词：ep{ep['ep']} 第{idx}句 {b['text']}")
            cid = b.get("char_id")
            if cid not in chars:
                errors.append(f"ep{ep['ep']}#{idx}: 角色 {cid} 不在 D04")
            if cid in minors:
                errors.append(f"ep{ep['ep']}#{idx}: 角色 {cid} 为未成年，台词须按 Q14=C 从严处置")
            for d in derogatory:
                if d in b["text"]:
                    errors.append(f"ep{ep['ep']}#{idx}: 台词命中贬称「{d}」")
            lines.append({
                "ep": ep["ep"],
                "idx": idx,
                "char_id": cid,
                "text": b["text"],
                "tone": b.get("emotion", ""),
                "subtext": SUBTEXT.get(key, ""),
            })

    # 语气卡
    spoken = {l["char_id"] for l in lines}
    card_ids = {c["char_id"] for c in VOICE_CARDS}
    for cid in sorted(spoken - card_ids):
        errors.append(f"有台词但缺语气卡：{cid}")
    for c in VOICE_CARDS:
        if c["char_id"] not in chars:
            errors.append(f"语气卡 {c['char_id']} 不在 D04")
        if not c.get("tone_rules"):
            errors.append(f"语气卡 {c['char_id']} 缺 tone_rules")
        for k in c:
            if k not in {"char_id", "tone_rules", "catchphrases", "forbidden_words"}:
                errors.append(f"语气卡 {c['char_id']} 非法字段 {k}")
        # 口头禅必须是 D04 原文（逐字一致，尾随句号亦计入）
        d04_cp = chars.get(c["char_id"], {}).get("catchphrase")
        for cp in c.get("catchphrases", []):
            if cp != d04_cp:
                errors.append(
                    f"语气卡 {c['char_id']} 口头禅与 D04 原文不一致：{cp!r} vs D04 {d04_cp!r}"
                )

    # 全文扫描（lines + voice_cards）—— V5/V6 口径
    hit = set()
    scan_text({"lines": lines, "voice_cards": VOICE_CARDS}, "D09", banned, errors, hit)

    if errors:
        print("❌ 自检未通过（未写盘）：")
        for e in errors:
            print("   -", e)
        sys.exit(1)

    out = {
        "doc_id": "D09",
        "unit": unit,
        "version": VERSION,
        "status": STATUS,
        "lines": lines,
        "voice_cards": VOICE_CARDS,
    }
    print(f"✅ 自检通过｜{unit} D09 {VERSION}")
    print(f"   lines={len(lines)} 句（逐句有 subtext）｜voice_cards={len(VOICE_CARDS)} 张")
    for c in VOICE_CARDS:
        n = sum(1 for l in lines if l["char_id"] == c["char_id"])
        print(f"   {c['char_id']}: {n} 句")

    if args.dry_run:
        print("（--dry-run：未写盘）")
        return

    target = os.path.join(project, "units", unit, "D09.json")

    # ── Q64 版本守卫 ──────────────────────────────────────────────────
    # 防「第二个写者 / 旧内容源」把已升版的产物**静默回退**（Q27 教训）。
    # 判据：磁盘产物的 version **高于**本脚本要写的 version → 拒绝覆盖并中止。
    # 正常升版（磁盘 v1.1 → 脚本 v1.2）与幂等重跑（版本相同）均放行。
    # 需要故意回退时用 --force 显式放行（人工确认过再动）。
    # 【2026-10-23 补记】本守卫此前只落在 build_D08.py，build_D09.py 缺失 ⇒
    #   本岗自查发现（Q64 要求「通用构建脚本写盘须带版本守卫」），本轮补齐，
    #   判据与 --force 逃生口与 build_D08.py 逐字对齐，不另立口径。
    def _vkey(v):
        m = re.match(r"^v?(\d+)\.(\d+)$", str(v or ""))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    if os.path.exists(target):
        try:
            cur = json.load(open(target, encoding="utf-8"))
            cur_v = cur.get("version")
            if _vkey(cur_v) > _vkey(VERSION) and not getattr(args, "force", False):
                print(f"❌ 版本守卫：磁盘 {target} 已是 **{cur_v}**，"
                      f"高于本脚本要写的 **{VERSION}** → 拒绝覆盖，未写盘。")
                print("   可能原因：另一个写者已用更新版本落盘，或本脚本用的是旧内容源。")
                print("   确认确需回退时，加 --force 显式放行。")
                sys.exit(1)
        except json.JSONDecodeError:
            pass  # 磁盘文件损坏 → 照常覆盖，交由自检与 validate 兜底

    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写 {target}")


if __name__ == "__main__":
    main()
