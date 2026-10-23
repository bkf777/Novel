#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
check_D05_lutiao_naming_guard.py —— 故事架构：「律条」**未命名期不给名**机器闸（只读）

**为什么有这支闸（2026-10-23 09:2x）**
  · 台本编剧 09:1x 回执提出：**D05「ep013–ep040 台词与字幕不得出现『律条』」目前只是自然语言
    约束**，担心 U03–U20 跨 80+ 集「只能靠人工审读 —— 人工不现实」。
  · 本岗回源＋实跑后**部分证伪、部分证实**：
    ① **证伪**：`03_规格/rules.json` **并非没有**这条规则 —— 它在 **`term_first_use` 轴**
      （`{term:律条, first_use_ep:13, forbidden_until_ep:40, forbidden_faces:[dialogue,subtitle]}`），
      `04_工具/lib/rules.mjs` 在 **V5 内扩展**实现了它；**沙箱负测**：向 `units/U02/D08.json`
      ep013 台词面（`body[type=dialogue]`）注入「律条」→ **`✗ 术语首用集前禁用：D08 ep13 台词面
      body 出现「律条」`（error 1）** ⇒ **闸拦得住**，不是「没有闸」。
    ② **证实（且已按 09:3x 沙箱实测收窄）**：该闸**只有一个面没盖** ——
      **面 A**：受检面是 **D11 `shots[].dialogue` ＋ D08 `body[type=dialogue]` ＋
      D16 `subtitle_style.lines[].text`**（见 `04_工具/lib/rules.mjs` V5 内扩展
      `term_first_use` 分支），**D09 `lines[].text`（台词表 SSOT）不在受检面**
      ⇒ 沙箱负测：**只**改 D09 台词表、D08 不动 → 官方 validate **11/11 通过、error 0 静默放行**，
      本闸 G5 **失败、EXIT 1**。
      ~~面 B：同义专名（骨签／规则石）无闸~~ → **该判断有误，已于 09:3x 回源码＋沙箱证伪**：
      V5 的 `forbidden_synonyms` 分支是**全文档全文扫描**（`allText(data)`，仅 `term_scan_exempt`
      列出的字段豁免，而 **D09 未在豁免表内**）⇒ 同义专名在 D09/任意文档任意字段**均被官方拦下**
      （沙箱实测：向 D09 ep013 注入「骨签」→ 官方 V5 **FAIL error 1**）。
      ⇒ 本闸对**同义专名面**只是**冗余复核**（不声称补缺口），真正补的是**面 A**。
    ③ **本闸另给官方闸给不出的东西**：**未落单元覆盖度报告**（U03–U20 的 ep017–ep040
      属未命名期，台词/字幕面一旦落盘即受约束）＋ **ep ≤ 12「名称层前」warn 级提示**
      （官方 `inRange` 下界为 13，ep ≤ 12 官方**完全不拦**、静默放行）。
  ⇒ **本闸补的是面 A（只读、只读、不改 03_规格／04_工具 —— 非本岗单写点）**。

**判据源（全部可回源，不采信转述）**
  · `shared/D05.json` `glossary[律条]`：`first_use_ep=13`｜名称层集号 **41**｜
    `forbidden_synonyms`（骨签／规则石／低阶律条）｜**未命名期台词口径块**（D05 v1.5）。
  · 源素材《脉络确认》§三「实物层 ep013 已入画**未命名**」、§二「ep041+（名称层）」、
    《设定待核对清单》「名字晚、机制早」。

**本闸判据（可机读）**
  · **本字「律条」**：`ep ≤ 40`（名称层 ep041 之前）→ 台词面/字幕面 **禁**（error）；
    `ep ≥ 41` → 允许。
  · **同义专名**（`forbidden_synonyms` 全列）→ **任何集数**台词面/字幕面 **禁**（error）。
  · **画面描述面不查**（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt`）—— D05 明文允许。
  · `ep ≤ 12`（实物首现 ep013 之前）属「名称层前」，本闸按「名称层前一律不给名」给出
    **warn 级提示**（D05 明文区间自 ep013 起，此为**推导延伸**，不越权升级为 error）。

**断言清单（G1–G10）**
  G1 D05 可解析且 version ≥ v1.5；G2 律条词条恰 1 条、`first_use_ep == 13`；
  G3 名称层集号 == 41、`forbidden_synonyms` 恰 3 项且含「低阶律条」；
  G4 未命名期口径块在位；
  G5 D09 台词面「律条」命中 0（ep ≤ 40）；G6 D09 台词面同义专名 0（全集数）；
  G7 D08 台词面（type=dialogue）0；G8 D11 台词面 0；G9 D16 字幕面 0；
  G10 覆盖度报告：已落单元／受检集数／**未落单元清单（U03–U20 的台词面待覆盖）**。

用法：python3 scripts/check_D05_lutiao_naming_guard.py --project . [--source <源素材目录>]
退出码：0 = 全部通过；1 = 有断言失败。
"""
import argparse
import json
import os
import re
import sys

NAME_FIRST_EP = 41          # 名称层：观众获名、台词可说「律条」
PROLOGUE_EP = 13            # 实物首现（D05 first_use_ep）
PROLOGUE_WARN_END = 12      # 规则前区（推导延伸，warn 级）


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ep_num(v):
    m = re.match(r"(\d+)", str(v if v is not None else ""))
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--source", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    res = []

    def ok(label, cond, detail=""):
        res.append((bool(cond), label, detail))

    d05p = os.path.join(root, "shared/D05.json")
    if not os.path.isfile(d05p):
        print(f"❌ G1 D05 不存在：{d05p}")
        return 1
    d05 = load(d05p)
    ver = d05.get("version") or ""
    ok("G1 D05 可解析且含未命名期口径（version ≥ v1.5）", ver >= "v1.5", f"version={ver}")

    gl = d05.get("glossary") or []
    idxs = [i for i, g in enumerate(gl) if g.get("term") == "律条"]
    if len(idxs) != 1:
        print(f"❌ G2 律条词条命中 {len(idxs)} 条 ≠ 1")
        return 1
    g = gl[idxs[0]]
    ok("G2 律条词条恰 1 条且 first_use_ep == 13", g.get("first_use_ep") == 13,
       f"first_use_ep={g.get('first_use_ep')}")

    syn = list(g.get("forbidden_synonyms") or [])
    def_txt = g.get("definition") or ""
    name_ep_in_def = NAME_FIRST_EP if ("ep%03d" % NAME_FIRST_EP) in def_txt or ("ep%d" % NAME_FIRST_EP) in def_txt else None
    ok("G3 名称层集号锚 == 41 且 forbidden_synonyms 恰 3 项含「低阶律条」",
       name_ep_in_def == NAME_FIRST_EP and len(syn) == 3 and "低阶律条" in syn,
       f"definition 内 ep041 锚={name_ep_in_def}｜forbidden_synonyms={syn}")
    ok("G4 未命名期台词口径块在位",
       "【未命名期台词口径（ep013–ep040）】" in def_txt)

    # ── 受检面扫描 ────────────────────────────────────────────────
    units_dir = os.path.join(root, "units")
    units = sorted([u for u in os.listdir(units_dir) if os.path.isdir(os.path.join(units_dir, u))
                    and not u.startswith(".")])

    def scan_faces(unit):
        """返回 (hard_hits, warn_hits, scanned_lines, face_map)"""
        hard, warn, nlines = [], [], 0
        u = os.path.join(units_dir, unit)

        # D09 台词表（lines[].text）—— validate 的 term_first_use 未覆盖此面
        p = os.path.join(u, "D09.json")
        if os.path.isfile(p):
            d9 = load(p)
            for l in d9.get("lines") or []:
                txt = str(l.get("text") or "")
                if not txt:
                    continue
                nlines += 1
                ep = ep_num(l.get("ep"))
                for w in syn:
                    if w in txt:
                        hard.append(f"D09 ep{ep} 台词表「{w}」")
                if "律条" in txt and ep is not None and ep <= NAME_FIRST_EP - 1:
                    (warn if ep <= PROLOGUE_WARN_END else hard).append(
                        f"D09 ep{ep} 台词表「律条」（名称层 ep041 前）")

        # D08 台词面（type=dialogue）
        p = os.path.join(u, "D08.json")
        if os.path.isfile(p):
            d8 = load(p)
            for e in d8.get("episodes") or []:
                ep = ep_num(e.get("ep"))
                for b in e.get("body") or []:
                    if b.get("type") != "dialogue":
                        continue
                    txt = str(b.get("text") or "")
                    if not txt:
                        continue
                    nlines += 1
                    for w in syn:
                        if w in txt:
                            hard.append(f"D08 ep{ep} 台词面「{w}」")
                    if "律条" in txt and ep is not None and ep <= NAME_FIRST_EP - 1:
                        (warn if ep <= PROLOGUE_WARN_END else hard).append(
                            f"D08 ep{ep} 台词面「律条」（名称层 ep041 前）")

        # D11 台词面（shots[].dialogue）
        p = os.path.join(u, "D11.json")
        if os.path.isfile(p):
            d11 = load(p)
            for e in d11.get("episodes") or []:
                ep = ep_num(e.get("ep"))
                for s in e.get("shots") or []:
                    dd = s.get("dialogue")
                    vals = dd if isinstance(dd, list) else ([dd] if dd else [])
                    for t in vals:
                        txt = t if isinstance(t, str) else str((t or {}).get("text") or (t or {}).get("line") or "")
                        if not txt:
                            continue
                        nlines += 1
                        for w in syn:
                            if w in txt:
                                hard.append(f"D11 ep{ep} 镜{s.get('shot_id')} 台词面「{w}」")
                        if "律条" in txt and ep is not None and ep <= NAME_FIRST_EP - 1:
                            (warn if ep <= PROLOGUE_WARN_END else hard).append(
                                f"D11 ep{ep} 镜{s.get('shot_id')} 台词面「律条」（名称层 ep041 前）")

        # D16 字幕面
        p = os.path.join(u, "D16.json")
        if os.path.isfile(p):
            d16 = load(p)
            for e in d16.get("episodes") or []:
                ep = ep_num(e.get("ep"))
                for l in ((e.get("subtitle_style") or {}).get("lines") or []):
                    txt = str(l.get("text") or "")
                    if not txt:
                        continue
                    nlines += 1
                    for w in syn:
                        if w in txt:
                            hard.append(f"D16 ep{ep} 字幕 seq{l.get('seq')}「{w}」")
                    if "律条" in txt and ep is not None and ep <= NAME_FIRST_EP - 1:
                        (warn if ep <= PROLOGUE_WARN_END else hard).append(
                            f"D16 ep{ep} 字幕 seq{l.get('seq')}「律条」（名称层 ep041 前）")
        return hard, warn, nlines

    all_hard, all_warn, all_lines = [], [], 0
    per_unit = []
    for u in units:
        h, w, n = scan_faces(u)
        all_hard += h
        all_warn += w
        all_lines += n
        per_unit.append((u, n, len(h), len(w)))

    ok("G5 D09 台词表「律条」命中 0（ep ≤ 40）",
       not [x for x in all_hard if x.startswith("D09") and "「律条」" in x],
       f"D09 台词行受检 {all_lines} 条（含四类面）｜命中 {[x for x in all_hard if x.startswith('D09')]}")
    ok("G6 D09 台词表同义专名 0（全集数）〔冗余复核：官方 V5 forbidden_synonyms 已全文覆盖〕",
       not [x for x in all_hard if x.startswith("D09") and "「骨签」" in x or x.startswith("D09") and "「规则石」" in x],
       f"命中 {[x for x in all_hard if x.startswith('D09') and '「律条」' not in x]}")
    ok("G7 D08 台词面（type=dialogue）0〔冗余复核：官方 term_first_use 已覆盖〕",
       not [x for x in all_hard if x.startswith("D08")],
       f"命中 {[x for x in all_hard if x.startswith('D08')]}")
    ok("G8 D11 台词面 0〔冗余复核：官方 term_first_use 已覆盖〕",
       not [x for x in all_hard if x.startswith("D11")],
       f"命中 {[x for x in all_hard if x.startswith('D11')]}")
    ok("G9 D16 字幕面 0〔冗余复核：官方 term_first_use 已覆盖〕",
       not [x for x in all_hard if x.startswith("D16")],
       f"命中 {[x for x in all_hard if x.startswith('D16')]}")

    covered = ", ".join(f"{u}({n}行)" for u, n, _, _ in per_unit)
    # ⚠️ 2026-10-23 U03 开工后修正：原实现把「未落待覆盖」**硬编码**为 U03–U20，
    #    导致 U03（D06／D07 已落、台词/字幕面 0 行）同时出现在「已落」与「未落待覆盖」两张清单里，
    #    **同一行自相矛盾** → 读者无法判断 U03 到底开工没有。改为按磁盘实况分三档：
    #    ① 台词/字幕面已有行 ② 已开工（D06 或 D07 在盘）但台词/字幕面 0 行 ③ 未开工。
    all_units = [f"U{i:02d}" for i in range(1, 21)]
    zero_line_started, not_started = [], []
    for u in all_units:
        n = dict((a, b) for a, b, _, _ in per_unit).get(u, 0)
        d06 = os.path.exists(os.path.join(units_dir, u, "D06.json"))
        d07 = os.path.exists(os.path.join(units_dir, u, "D07.json"))
        if n > 0:
            continue
        if d06 or d07:
            zero_line_started.append(u)
        else:
            not_started.append(u)
    pending_units = not_started
    ok("G10 覆盖度：已落单元与待覆盖单元已登记",
       len(per_unit) >= 2,
       f"已落台词/字幕面 {len(per_unit)} 单元：{covered}｜受检台词/字幕行合计 {all_lines} 条｜"
       f"**已开工但台词/字幕面仍 0 行：{'、'.join(zero_line_started) or '无'}（台词/字幕面待他岗落盘）"
       f"｜未开工待覆盖 {len(pending_units)} 单元：{'、'.join(pending_units) or '无'}**"
       f"（ep025–ep160，其中 ep025–ep040 属未命名期，台词/字幕面一旦落盘即受本闸约束）")

    for l, lab, det in res:
        print(f"  {'✅' if l else '❌'} {lab} {det}")
    if all_warn:
        print(f"  ⚠️ 规则前区（ep ≤ {PROLOGUE_WARN_END}）提示级 {len(all_warn)} 条：{all_warn[:5]}")
    nfail = sum(1 for l, _, _ in res if not l)
    print(f"■ 合计：断言 {len(res)} 条｜通过 {len(res) - nfail}｜失败 {nfail}")
    if nfail:
        print("❌ 有断言失败")
        return 1
    print("✅ 「律条」未命名期不给名机器闸全部通过")
    print("   本闸独有价值：① **补官方 term_first_use 未覆盖的 D09 `lines[].text` 台词表面**（唯一真缺口）"
          "② 未落单元覆盖度报告 ③ ep ≤ 12「名称层前」warn 级提示（官方下界 13，ep ≤ 12 静默放行）")
    print("   同义专名面（G6/G7/G8/G9 的骨签／规则石／低阶律条部分）为**冗余复核**："
          "官方 V5 `forbidden_synonyms` 是全文档全文扫描，且 D09 未列入 `term_scan_exempt` → 官方已覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
