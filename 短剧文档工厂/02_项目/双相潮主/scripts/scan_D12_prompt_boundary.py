#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
《双相潮主》D12 image_prompt 边界缺陷扫描器（Q107 复算口径）

用法：
    python3 scripts/scan_D12_prompt_boundary.py                 # 扫三单元
    python3 scripts/scan_D12_prompt_boundary.py --unit U03      # 只扫一个单元
    python3 scripts/scan_D12_prompt_boundary.py --json          # 机读输出

口径（与 D18 global_checks Q107「验收判据」逐字一致）：
    ① 同卡重复句计数：按「。」「；」切分 image_prompt，取长度 ≥12 的句子，
       在同一张卡内查重复（同一句出现 ≥2 次记 1 处）。
    ② 黏连正则命中：正则 `[^\s，。；]{6,}右下角` 在 image_prompt 上的命中数。

关于 ① 的两个变体（都报，避免口径歧义）：
    - exact      ：句子串完全相等 ⇒ 判重复。
    - containment ：句子 A 被同卡另一句 B 完整包含 ⇒ 判重复。
      **这一变体才抓得住 C-213** —— 它的第二处重复被黏连吞掉了尾标点，
      切出来的句子是「排队的人一律作剪影，队形一路拐进灰雾深处右下角 72%~78% …」，
      与第一处不完全相等，exact 变体会漏判。验收要求「同卡重复句计数 = 0」，
      以 containment 变体为准（更严）。

退出码：0 = 全部单元归零；1 = 仍有缺陷。
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))

RUNON_RE = re.compile(r"[^\s，。；]{6,}右下角")
SENT_SPLIT_RE = re.compile(r"[。；]")
MIN_SENT_LEN = 12


def sentences(text):
    """按「。」「；」切分，去空白，取长度 ≥12 的句子。"""
    out = []
    for seg in SENT_SPLIT_RE.split(text or ""):
        s = seg.strip()
        if len(s) >= MIN_SENT_LEN:
            out.append(s)
    return out


def scan_card(card):
    ip = card.get("image_prompt", "")
    sents = sentences(ip)
    seen, dup_exact = set(), []
    for s in sents:
        if s in seen and s not in dup_exact:
            dup_exact.append(s)
        seen.add(s)
    # containment 变体：句 A 被另一句 B 完整包含 ⇒ 判重复（更严，抓得住被黏连吞尾标点的重复）
    dup_cont = []
    for i, a in enumerate(sents):
        for j, b in enumerate(sents):
            if i != j and a != b and a in b and a not in dup_cont:
                dup_cont.append(a)
                break
    runs = RUNON_RE.findall(ip)
    return {"card_id": card.get("card_id"), "dups": dup_exact,
            "dups_contain": dup_cont, "runons": runs}


def scan_unit(unit):
    path = os.path.join(PROJ, "units", unit, "D12.json")
    doc = json.load(open(path, encoding="utf-8"))
    cards = doc.get("cards", [])
    dup_cards, runon_cards, dup_cont_cards = [], [], []
    n_dup, n_runon, n_cont = 0, 0, 0
    for c in cards:
        r = scan_card(c)
        if r["dups"]:
            n_dup += len(r["dups"])
            dup_cards.append(r)
        if r["dups_contain"]:
            n_cont += len(r["dups_contain"])
            dup_cont_cards.append(r)
        if r["runons"]:
            n_runon += len(r["runons"])
            runon_cards.append(r)
    return {
        "unit": unit,
        "version": doc.get("version"),
        "cards": len(cards),
        "dup_cards": dup_cards,
        "dup_cont_cards": dup_cont_cards,
        "runon_cards": runon_cards,
        "dup_count": n_dup,
        "dup_contain_count": n_cont,
        "runon_count": n_runon,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", action="append", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    units = args.unit or ["U01", "U02", "U03"]

    results = [scan_unit(u) for u in units]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("Q107 边界扫描（重复句计数 / 黏连正则命中）")
        print("-" * 78)
        for r in results:
            print(f"{r['unit']}  v{r['version']}  {r['cards']} 卡  "
                  f"重复句(exact)={r['dup_count']}  重复句(containment)={r['dup_contain_count']}  "
                  f"黏连命中={r['runon_count']}")
            for d in r["dup_cards"]:
                print(f"    [重复句-exact] {d['card_id']}  ×{len(d['dups'])}  {d['dups'][0][:60]}")
            for d in r["dup_cont_cards"]:
                print(f"    [重复句-cont]  {d['card_id']}  ×{len(d['dups_contain'])}  {d['dups_contain'][0][:60]}")
            for c in r["runon_cards"]:
                print(f"    [黏连]   {c['card_id']}  ×{len(c['runons'])}  …{c['runons'][0][:60]}")
        print("-" * 78)
        total_dup = sum(r["dup_count"] for r in results)
        total_cont = sum(r["dup_contain_count"] for r in results)
        total_run = sum(r["runon_count"] for r in results)
        print(f"合计：重复句(exact)={total_dup}  重复句(containment)={total_cont}  黏连命中={total_run}")
    return 0 if all(r["dup_count"] == 0 and r["dup_contain_count"] == 0
                    and r["runon_count"] == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
