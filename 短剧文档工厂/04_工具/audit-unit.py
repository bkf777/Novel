#!/usr/bin/env python3
"""单元内容层独立审读（校验器之外的第二道关卡）。

**为什么需要它**：工厂校验器（validate.mjs）查的是结构完整性——字段齐不齐、枚举合不合法、
跨文件引用在不在。它**不查内容口径是否分叉**：同一个动作在 D06 写「跪伏」在 D08 写「单膝跪」，
结构上完全合法，但交付给用户时是两条分叉的设定。
所以单元锁放行前，必须跑这一层。

用法：
    python3 短剧文档工厂/04_工具/audit-unit.py --project 短剧文档工厂/02_项目/双相潮主 --unit U01
    python3 短剧文档工厂/04_工具/audit-unit.py --project ... --unit U01 --json

退出码：0 = 无待确认项；1 = 有待确认项（逐条打印）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


def load(project_dir: str, rel: str):
    fp = os.path.join(project_dir, rel)
    if not os.path.exists(fp):
        return None
    with open(fp, encoding="utf-8") as fh:
        return json.load(fh)


def _norm_path(path: list[str]) -> str:
    """把路径归一化为 'a[].b' 形式（与 rules.mjs 的 allTextExceptPaths 同一口径）。"""
    out: list[str] = []
    for seg in path:
        if seg == "[]":
            if out:
                out[-1] = f"{out[-1]}[]"
            else:
                out.append("[]")
        else:
            out.append(seg)
    return ".".join(out)


def text_except_paths(node, skip_paths: list[str], path: list[str] = None) -> list[str]:
    """按路径级豁免取全文文本。

    ⚠️ 与 04_工具/lib/rules.mjs 的 allTextExceptPaths 保持同一语义：
    豁免路径命中时**跳过整棵子树**，其余照常扫描。豁免真源 = 03_规格/rules.json 的
    term_scan_exempt（D03.red_lines / D18.global_checks / D12.cards[].negatives /
    D08.compliance_notes 等「职责就是逐词声明作废写法」的字段）。
    """
    if path is None:
        path = []
    if node is None:
        return []
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        acc: list[str] = []
        for n in node:
            acc.extend(text_except_paths(n, skip_paths, path + ["[]"]))
        return acc
    if isinstance(node, dict):
        acc = []
        for k, v in node.items():
            child = path + [k]
            if _norm_path(child) in skip_paths:
                continue
            acc.extend(text_except_paths(v, skip_paths, child))
        return acc
    return []


def audit(project_dir: str, unit: str):
    issues: list[tuple[str, str]] = []

    def flag(cat: str, msg: str):
        issues.append((cat, msg))

    shared = os.path.join(project_dir, "shared")
    unit_dir = os.path.join(project_dir, "units", unit)

    d04 = load(shared, "D04.json")
    d05 = load(shared, "D05.json")
    d10 = load(shared, "D10.json")
    d16 = load(shared, "D16.json") or load(unit_dir, "D16.json")
    d07 = load(unit_dir, "D07.json")
    d08 = load(unit_dir, "D08.json")
    d09 = load(unit_dir, "D09.json")
    d11 = load(unit_dir, "D11.json")
    d12 = load(unit_dir, "D12.json")
    d15 = load(unit_dir, "D15.json")

    if not d11:
        print("D11 不存在，无法审读", file=sys.stderr)
        return issues

    # ---------- 1. 角色集合：D04 ↔ D10 锚点表 ----------
    if d04 and d10:
        cids = {c["id"] for c in d04.get("characters", [])}
        a10 = {a["char_id"] for a in d10.get("character_anchors", [])}
        if cids != a10:
            flag("角色", f"D04 与 D10 角色集不一致：D04独有={sorted(cids - a10)} D10独有={sorted(a10 - cids)}")

    # ---------- 2. 禁用同义写法扫描（字段级豁免） ----------
    # ⚠️ 2026-10-23 修判据缺陷：此前用 json.dumps(doc) 全量扫描，把 D08 的
    #    episodes[].compliance_notes（**合规备注本身在解释禁用词**：正文里写
    #    「不用『灰斑感染者／感染者』等身份标签写法」）也判成命中 → 假阳性。
    #    豁免真源 = 03_规格/rules.json 的 term_scan_exempt，与 rules.mjs V5 同一口径。
    if d05:
        forbidden: list[str] = []
        for g in d05.get("glossary", []):
            forbidden += g.get("forbidden_synonyms", [])
        rules = load(project_dir, os.path.join("..", "..", "03_规格", "rules.json")) or {}
        exemptions = rules.get("term_scan_exempt", {}) or {}
        for name, doc in (("D07", d07), ("D08", d08), ("D09", d09), ("D11", d11),
                          ("D12", d12), ("D15", d15), ("D16", d16)):
            if not doc:
                continue
            skip = list(exemptions.get(name, []) or [])
            texts = text_except_paths(doc, skip)
            txt = "\n".join(texts)
            hits = sorted({w for w in forbidden if w and w in txt})
            if hits:
                flag("禁词", f"{name} 命中禁用同义写法 {hits[:8]}")

    # ---------- 3. 归一度读数：按 D05 gauge_rule 真规则判 ----------
    # ⚠️ 2026-10-23 修判据缺陷：此前只判「读数是否 ∈ 12 点锚点集合」，
    #    把**非锚点集的区间读数**（D05 明文允许）误判为违规 → U02 假阳性 37 项。
    #    D05.power_system.gauge_rule 真规则（三条，缺一不可）：
    #      ① 锚点集（升阶集＋里程碑集）读数必须**精确命中**锚点值；
    #      ② 非锚点集读数落在 [前一锚点读数, 后一锚点读数] **闭区间**内；
    #      ③ 读数**单调不减**。
    if d05:
        gauge = d05.get("power_system", {}).get("gauge_readings", [])
        anchor_vals: list[float] = []
        if isinstance(gauge, list):
            for item in gauge:
                # ⚠️ 只抽 `reading` 字段本身 —— 早期版本对整条 gauge_readings 做
                # JSON 正则，会把 event 文本里的「升 3%」（ep35 跨档描述）吸成
                # 伪锚点，实测锚点集变 13 个（多出 3.0），真实锚点只有 12 个。
                m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)%\s*", str(item.get("reading", "")))
                if m:
                    anchor_vals.append(float(m.group(1)))
        anchor_set = set(anchor_vals)
        if anchor_vals:
            for name, doc in (("D08", d08), ("D11", d11), ("D12", d12), ("D15", d15)):
                if not doc:
                    continue
                # 逐集读数：按**集号**收集（每集取该集内出现的最大读数 = 该集面板读数），
                # 规则③单调性必须按集序判定 —— 按文档出现顺序会把「同一集内
                # visual_facts 与 note 重复出现同一读数」误判成倒退。
                # ⚠️ 不同文档的集号承载结构不同：D08／D11／D15 是 `episodes[].ep`，
                #    **D12 顶层是 `cards[]`（无 episodes）**，其集号在
                #    `cards[].ep` —— 早期版本只读 `episodes`
                #    ⇒ D12 的逐集单调性**恒空过**（判据对 D12 失效）。
                per_ep: dict[int, float] = {}
                for ep in (doc.get("episodes") or []):
                    ep_no = ep.get("ep")
                    if ep_no is None:
                        continue
                    blob = json.dumps(ep, ensure_ascii=False)
                    vals = [float(m.group(1)) for m in
                            re.finditer(r"归一度\s*(\d+(?:\.\d+)?)%", blob)]
                    if vals:
                        # ⚠️ 一集可能横跨**多条记录**（D12 每集 4 张卡），
                        #    必须取该集**全局最大值** —— 逐条赋值会被后一条覆盖
                        #    （企划合规 Q91 复核发现的第二处缺口）。
                        per_ep[int(ep_no)] = max(max(vals), per_ep.get(int(ep_no), 0.0))
                if not per_ep:
                    # D12 结构：cards[].ep
                    for c in (doc.get("cards") or []):
                        ep_no = c.get("ep")
                        if ep_no is None:
                            continue
                        blob = json.dumps(c, ensure_ascii=False)
                        vals = [float(m.group(1)) for m in
                                re.finditer(r"归一度\s*(\d+(?:\.\d+)?)%", blob)]
                        if vals:
                            per_ep[int(ep_no)] = max(max(vals), per_ep.get(int(ep_no), 0.0))
                # 全文档出现过的读数（用于区间判定，覆盖非 episodes 结构的文档）
                found: list[float] = []
                for m in re.finditer(r"归一度\s*(\d+(?:\.\d+)?)%", json.dumps(doc, ensure_ascii=False)):
                    v = float(m.group(1))
                    if v not in found:
                        found.append(v)
                for v in found:
                    if v in anchor_set:
                        continue  # 规则①：锚点集精确命中 → 合规
                    # ⚠️ 区间判定必须用**严格小于/大于**找锚点，不能用 <=/>= ——
                    #    后者会把 v 自身选成 lo 与 hi，致 `lo <= v <= hi` **恒真**，
                    #    实际只校验了「读数 ∈ [最小锚点, 最大锚点]」，区间语义被掩盖
                    #    （企划合规 Q91 复核发现的恒真缺口）。
                    lo_cands = [a for a in anchor_vals if a < v]
                    hi_cands = [a for a in anchor_vals if a > v]
                    lo = max(lo_cands) if lo_cands else None
                    hi = min(hi_cands) if hi_cands else None
                    if lo is None:
                        flag("归一度", f"{name} 读数 {v}% 低于最小锚点 "
                                       f"{min(anchor_vals)}%（锚点集 {sorted(anchor_set)}）")
                    elif hi is None:
                        flag("归一度", f"{name} 读数 {v}% 高于最大锚点 "
                                       f"{max(anchor_vals)}%（锚点集 {sorted(anchor_set)}）")
                    elif not (lo <= v <= hi):
                        flag("归一度", f"{name} 读数 {v}% 越出锚点区间 "
                                       f"[{lo}, {hi}]（锚点集 {sorted(anchor_set)}）")
                # 规则③：单调不减（按**集序**判定；不排序 —— 排序后必然单调，判据恒真）
                ep_seq = [per_ep[k] for k in sorted(per_ep)]
                if any(ep_seq[i] > ep_seq[i + 1] for i in range(len(ep_seq) - 1)):
                    flag("归一度", f"{name} 逐集读数非单调不减：{ep_seq}")

    # ---------- 4. D11 镜号连续 + 集时长 ----------
    d11_shots: dict[tuple[int, int], dict] = {}
    for e in d11["episodes"]:
        prev = 0
        for s in e["shots"]:
            d11_shots[(e["ep"], s["shot_id"])] = s
            if s["shot_id"] != prev + 1:
                flag("镜号", f"D11 ep{e['ep']} 镜号不连续：{prev} → {s['shot_id']}")
            prev = s["shot_id"]
        total = sum(s["duration_sec"] for s in e["shots"])
        if total != 45:
            flag("时长", f"D11 ep{e['ep']} 镜长合计 {total} ≠ 45")
        if e.get("duration_sum_sec") != total:
            flag("时长", f"D11 ep{e['ep']} duration_sum_sec={e.get('duration_sum_sec')} ≠ 实算 {total}")

    # ---------- 5. D11 ↔ D12 镜覆盖 ----------
    if d12:
        k12 = {(c["ep"], c["shot_id"]) for c in d12.get("cards", [])}
        if set(d11_shots) != k12:
            flag("覆盖", f"D11/D12 镜集合不一致 缺={sorted(set(d11_shots)-k12)} 多={sorted(k12-set(d11_shots))}")

    # ---------- 6. D11 ↔ D15 音效覆盖 + 时间落点（允许 D16 记的声音预铺位） ----------
    if d15 and d16:
        audio_lead = set()
        for e16 in d16.get("episodes", []):
            for t in e16.get("transitions", []):
                al = str(t.get("audio_lead", ""))
                for m in re.finditer(r"切点\s*\d+\s*[（(]\s*(\d+(?:\.\d+)?)\s*s", al):
                    audio_lead.add((e16["ep"], float(m.group(1))))
        for e in d11["episodes"]:
            t = 0
            spans = {}
            for s in e["shots"]:
                spans[s["shot_id"]] = (t, t + s["duration_sec"]); t += s["duration_sec"]
            e15 = next((x for x in d15["episodes"] if x["ep"] == e["ep"]), None)
            if not e15:
                continue
            for s in e["shots"]:
                sid = s["shot_id"]
                mine = [x for x in e15.get("sfx", []) if x.get("shot_id") == sid]
                if s.get("sfx") and not mine:
                    flag("音效", f"D15 ep{e['ep']} 镜{sid} 缺音效（D11：{s['sfx'][:32]}）")
                for x in mine:
                    at = x.get("at_sec", -1)
                    lo, hi = spans[sid]
                    if not (lo <= at < hi):
                        near = min((abs(at - c) for ep2, c in audio_lead if ep2 == e["ep"]), default=None)
                        if near is None or near > 1.0:
                            flag("音效", f"D15 ep{e['ep']} 镜{sid} 音效 at={at}s 越出镜区间[{lo},{hi})，且 D16 未记该切点声音预铺")

    # ---------- 7. D16 段间切点 == D11 镜起点（段内并行交替点不参与） ----------
    if d16:
        for e16 in d16["episodes"]:
            e11 = next((x for x in d11["episodes"] if x["ep"] == e16["ep"]), None)
            if not e11:
                continue
            t = 0
            starts = {}
            for s in e11["shots"]:
                starts[s["shot_id"]] = t; t += s["duration_sec"]
            for c in e16.get("cuts", []):
                if c.get("counted_in_d17_cut_count") is False:
                    continue
                exp = starts.get(c.get("to_shot"))
                if exp is None or abs(c.get("at_sec", -1) - exp) > 0.05:
                    flag("切点", f"D16 ep{e16['ep']} 段间切点 {c.get('at_sec')}s 与 D11 镜{c.get('to_shot')} 起点 {exp} 不符")

    # ---------- 8. 色板越界（D10 palette 外颜色） ----------
    if d10:
        for name, doc in (("D11", d11), ("D12", d12)):
            if not doc:
                continue
            txt = json.dumps(doc, ensure_ascii=False)
            for word in ("金色", "金光"):
                for m in re.finditer(word, txt):
                    ctx = txt[max(0, m.start() - 14): m.end() + 14]
                    if not any(k in ctx for k in ("不作金", "非金", "不得", "无金")):
                        flag("色板", f"{name} 出现色板外颜色「{word}」：…{ctx}…")

    return issues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    project_dir = os.path.abspath(args.project)
    issues = audit(project_dir, args.unit)

    if args.json:
        print(json.dumps([{"category": c, "issue": m} for c, m in issues],
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"内容层独立审读 {args.unit}：{len(issues)} 项待确认")
        print("=" * 60)
        for cat, msg in issues:
            print(f"[{cat}] {msg}")
        if not issues:
            print("未发现跨文档内容口径分叉。")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
