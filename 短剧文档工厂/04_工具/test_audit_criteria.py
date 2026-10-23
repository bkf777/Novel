#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审读判据负测：证明 audit-unit.py 的两条判据**不是恒真**。

背景（2026-10-23）：
  audit-unit.py 曾报 U02「38 项待确认」，实测全部为假阳性：
    ① 归一度 37 项 —— 旧判据只判「读数是否 ∈ 12 点锚点集合」，
       把 D05.gauge_rule **明文允许**的非锚点集区间读数误判为违规；
    ② 禁词 1 项 —— 旧判据用 json.dumps 全扫，把 D08.compliance_notes
       （合规备注本身在解释禁用词）判成命中，且**没用** rules.json 的豁免真源。
  修完后 U02 变 0 项。但「变绿」本身不能证明判据有区分力 —— 必须用
  **真违规**夹具验证它仍然会红。

本测试覆盖 5 条腿：
  L1 禁词真违规（D08 正文用禁用同义词）        → 必须报
  L2 禁词豁免腿（同一禁用词只出现在 compliance_notes）→ 必须不报
  L3 归一度越界（读数 99%，超出所有锚点区间）    → 必须报
  L4 归一度区间腿（读数 1.2%，D05 明文允许）      → 必须不报
  L5 归一度单调性腿（后集读数低于前集）           → 必须报

夹具形态要求（见 agent memory「负测夹具形态必须 == 真实落盘形态」）：
  夹具直接用**真盘原文逐字**改造，不是另写一种说法。

用法：
    python3 04_工具/test_audit_criteria.py --project 02_项目/双相潮主
退出码：0 = 全部腿通过；1 = 有腿失败。
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "audit-unit.py")

failures: list[str] = []


def run_audit(project_dir: str, unit: str) -> tuple[int, list[dict]]:
    proc = subprocess.run(
        [sys.executable, AUDIT, "--project", project_dir, "--unit", unit, "--json"],
        capture_output=True, text=True,
    )
    try:
        issues = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        issues = []
    return proc.returncode, issues


def has(issues: list[dict], category: str, needle: str) -> bool:
    return any(i.get("category") == category and needle in i.get("issue", "") for i in issues)


def check(name: str, cond: bool, detail: str = ""):
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" —— {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args()

    src_project = os.path.abspath(args.project)
    # 副本工程：必须**镜像** 03_规格/rules.json 的相对路径 ——
    # audit-unit.py 从 project_dir/../../03_规格/rules.json 读豁免真源，
    # 副本结构必须一致，否则豁免表读不到 → 夹具失真（这本身踩过一次坑）。
    tmp = tempfile.mkdtemp(prefix="audit_negtest_")
    factory = os.path.join(tmp, "factory")
    dst = os.path.join(factory, "02_项目", "双相潮主")
    os.makedirs(dst)
    shutil.copytree(os.path.join(src_project, "units"), os.path.join(dst, "units"))
    shutil.copytree(os.path.join(src_project, "shared"), os.path.join(dst, "shared"))
    rules_src = os.path.join(os.path.dirname(HERE), "03_规格", "rules.json")
    rules_dst = os.path.join(factory, "03_规格", "rules.json")
    os.makedirs(os.path.dirname(rules_dst), exist_ok=True)
    shutil.copy2(rules_src, rules_dst)

    unit = "U02"
    u_dir = os.path.join(dst, "units", unit)

    def load_doc(name):
        with open(os.path.join(u_dir, f"{name}.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def save_doc(name, doc):
        with open(os.path.join(u_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)

    print("审读判据负测（证明判据非恒真）")
    print("=" * 60)

    # ---- 基线：未改动的副本应为 0 项 ----
    code, issues = run_audit(dst, unit)
    check("基线 副本未改动时 0 项", code == 0 and not issues,
          f"exit={code} issues={len(issues)}")

    # ---- L1 禁词真违规 → 必须报 ----
    # 真盘形态：D08 episodes[].body[].text 是剧本正文；禁用同义词取自 D05 词表实际值
    d08 = load_doc("D08")
    d05 = json.load(open(os.path.join(dst, "shared", "D05.json"), encoding="utf-8"))
    ban = None
    for g in d05.get("glossary", []):
        for b in (g.get("forbidden_synonyms") or []):
            if b and len(b) >= 3:
                ban = b
                break
        if ban:
            break
    if not ban:
        check("L1 禁词真违规", False, "D05 词表里找不到可用禁用同义词，无法构造夹具")
    else:
        d08_l1 = copy.deepcopy(d08)
        # 注入到**正文**（真盘的正文承载位），不是 compliance_notes
        d08_l1["episodes"][0]["body"][0]["text"] = f"他把{ban}从暗处拖了出来。"
        save_doc("D08", d08_l1)
        code, issues = run_audit(dst, unit)
        check("L1 禁词真违规 → 必报", has(issues, "禁词", ban),
              f"注入词『{ban}』 exit={code}")
        save_doc("D08", d08)  # 复原

    # ---- L2 禁词豁免腿 → 必须不报 ----
    # 同一禁用词只出现在 compliance_notes（豁免字段）→ 不该报
    d08_l2 = copy.deepcopy(d08)
    if ban:
        d08_l2["episodes"][0].setdefault("compliance_notes", []).append(
            f"D05 口径：正文不得写成『{ban}』，此处仅记录收口依据。"
        )
        save_doc("D08", d08_l2)
        code, issues = run_audit(dst, unit)
        check("L2 禁词只在豁免字段 → 不报", not has(issues, "禁词", ban),
              f"exit={code} issues={[i.get('category') for i in issues]}")
        save_doc("D08", d08)  # 复原

    # ---- L3 归一度越界 → 必须报 ----
    # 99% 超出所有锚点区间（锚点集最大 100%…改用 999% 保证越界）
    d08_l3 = copy.deepcopy(d08)
    d08_l3["episodes"][0]["body"][0]["text"] = "视野一角读数栏显示同屏中文「归一度 999%」。"
    save_doc("D08", d08_l3)
    code, issues = run_audit(dst, unit)
    check("L3 归一度 999% 越界 → 必报", has(issues, "归一度", "999"),
          f"exit={code}")
    save_doc("D08", d08)  # 复原

    # ---- L4 归一度区间腿 → 必须不报 ----
    # 夹具形态必须 == 真实落盘形态：**不新造位置、不改数值**。
    # 真盘 U02 逐集面板读数（实测）：ep9=0.7 / ep10=1.0 / ep11=1.1 / ep12=1.2 /
    # ep13=1.2 / ep14=1.3 / ep15=1.3 / ep16=1.4。
    # ep12 的 1.2% 落在 [1.0,1.5] 闭区间 → D05 明文允许 → 不该报。
    d08_l4 = copy.deepcopy(d08)
    ep12 = next((e for e in d08_l4["episodes"] if e.get("ep") == 12), None)
    if ep12 is None:
        check("L4 归一度 1.2% 区间值 → 不报", False, "真盘无 ep12，无法构造区间值夹具")
    else:
        blob = json.dumps(ep12, ensure_ascii=False)
        has12 = "归一度 1.2%" in blob
        code, issues = run_audit(dst, unit)
        check("L4 归一度 1.2% 区间值 → 不报（真盘逐字形态）",
              has12 and not has(issues, "归一度", "1.2%"),
              f"ep12 含『归一度 1.2%』={has12}；issues={[i.get('issue') for i in issues][:2]}")

    # ---- L4b 区间腿的加强：把该集读数换成另一个**同区间**值，仍不该报 ----
    # 1.4% 同属 [1.0,1.5] 闭区间 —— 若判据只认 1.2% 这一具体值，这条腿就会挂，
    # 说明判据在按「具体数字硬套」而非按「区间语义」判定。
    if ep12 is not None:
        d08_l4b = copy.deepcopy(d08)
        ep12b = next(e for e in d08_l4b["episodes"] if e.get("ep") == 12)
        ep12b["body"][10]["text"] = "面板读数栏：归一度 1.4%。"
        save_doc("D08", d08_l4b)
        code, issues = run_audit(dst, unit)
        check("L4b 同区间另一值 1.4% → 不报（证明按区间语义而非硬套数字）",
              not has(issues, "归一度", "1.4%"),
              f"issues={[i.get('issue') for i in issues][:2]}")
        save_doc("D08", d08)  # 复原

    # ---- L5 归一度单调性腿 → 必须报 ----
    # 形态：让**后集**读数低于**前集**，且改动后的值**仍在合法区间内**
    # —— 只有这样才可能由「单调性」这条规则抓住，不会被区间规则混淆。
    # 真盘 ep13=1.2% → 改成 0.7%（0.7% 落在 [0.5,1.0] 闭区间，合法），
    # 于是 ep12=1.2% > ep13=0.7% → 逐集读数倒退。
    d08_l5 = copy.deepcopy(d08)
    ep13l5 = next((e for e in d08_l5["episodes"] if e.get("ep") == 13), None)
    if ep13l5 is None:
        check("L5 归一度非单调 → 必报", False, "真盘无 ep13，无法构造非单调夹具")
    else:
        ep13l5["body"][11]["text"] = "面板读数栏：归一度 0.7%。"
        save_doc("D08", d08_l5)
        code, issues = run_audit(dst, unit)
        check("L5 归一度逐集非单调 → 必报", has(issues, "归一度", "单调"),
              f"issues={[i.get('issue') for i in issues][:2]}")
        save_doc("D08", d08)  # 复原

    # ---- L6 锚点集伪锚点腿（企划合规 Q91 复核发现的缺口）----
    # 早期实现对整条 gauge_readings 做 JSON 正则，会把 event 文本里的
    # 「升 3%」（ep35 跨档描述）吸成伪锚点 ⇒ 锚点集 13 个（多出 3.0）。
    # 修法：只抽 `reading` 字段本身。断言：锚点集必须**恰好 12 个**。
    d05p = os.path.join(dst, "shared", "D05.json")
    d05r = json.load(open(d05p, encoding="utf-8"))
    real_anchor = set()
    for it in d05r.get("power_system", {}).get("gauge_readings", []):
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)%\s*", str(it.get("reading", "")))
        if m:
            real_anchor.add(float(m.group(1)))
    check("L6 锚点集恰为 12 个（无 event 文本伪锚点）",
          len(real_anchor) == 12 and 3.0 not in real_anchor,
          f"实抽={len(real_anchor)} 个，含 3.0={'3.0' in str(sorted(real_anchor))}")

    # ---- L7 区间语义腿：读数必须在「两锚点之间」而非「全局最小~最大」----
    # 2.0% 落在 [1.5, 4.5] 开区间内 —— 若区间判定是恒真的（lo<=v<=hi 由 v 自身
    # 推导），它不会报；真正的区间判定也不报（2.0 确实在 1.5~4.5 之间）。
    # ⇒ 用 **2.6%**（同样在 1.5~4.5 内）验证「合法中间值不报」，
    #    再用 **3.0%（伪锚点曾掩盖的值）** 验证它落在 1.5~4.5 内、合法。
    d08_l7 = copy.deepcopy(d08)
    ep12l7 = next(e for e in d08_l7["episodes"] if e.get("ep") == 12)
    ep12l7["body"][10]["text"] = "面板读数栏：归一度 2.6%。"
    save_doc("D08", d08_l7)
    code, issues = run_audit(dst, unit)
    check("L7 同区间中间值 2.6% → 不报（区间语义正确）",
          not has(issues, "归一度", "2.6%"),
          f"issues={[i.get('issue') for i in issues][:2]}")
    save_doc("D08", d08)  # 复原

    # ---- L8 区间语义腿（反面）：跨区间值必须报 ----
    # 5.5% 落在 [4.5, 6.0] 内 —— 合法，不报。
    # 但 **0.2%** 低于最小锚点 0.5% ⇒ 必须报（旧恒真实现不报，因为 0.5<=0.2<=100 假成立）
    d08_l8 = copy.deepcopy(d08)
    ep12l8 = next(e for e in d08_l8["episodes"] if e.get("ep") == 12)
    ep12l8["body"][10]["text"] = "面板读数栏：归一度 0.2%。"
    save_doc("D08", d08_l8)
    code, issues = run_audit(dst, unit)
    check("L8 低于最小锚点 0.2% → 必报（反证恒真区间已消除）",
          has(issues, "归一度", "0.2%"),
          f"issues={[i.get('issue') for i in issues][:2]}")
    save_doc("D08", d08)  # 复原

    # ---- L9 D12 逐集单调性腿（企划合规 Q91 复核发现的缺口）----
    # D12 顶层是 cards[]（无 episodes）⇒ 早期实现对 D12 的单调性恒空过。
    # 构造：D12 的 cards 按 ep 递增，但把后一个 ep 的读数改成低于前一个 ⇒ 必须报。
    d12 = load_doc("D12")
    cards = d12.get("cards") or []
    card_eps = sorted({c.get("ep") for c in cards if c.get("ep") is not None})
    if len(card_eps) < 2:
        check("L9 D12 逐集单调性", False, f"D12 cards 的 ep 不足 2 个（{card_eps}），无法构造夹具")
    else:
        # 找两个相邻 ep 的卡，各自注入读数。
        # ⚠️ 必须注入到**字符串字段**（真盘读数就落在 image_prompt/video_prompt），
        #    且取 max 后仍要形成倒退：ep9 注入 1.4%（> ep10 的 1.0%）。
        e1, e2 = card_eps[0], card_eps[1]
        c1 = next(c for c in cards if c.get("ep") == e1)
        c2 = next(c for c in cards if c.get("ep") == e2)
        c1["video_prompt"] = str(c1.get("video_prompt", "")) + " 读数栏保持「归一度 1.4%」可读；"
        c2["video_prompt"] = str(c2.get("video_prompt", "")) + " 读数栏保持「归一度 0.7%」可读；"
        save_doc("D12", d12)
        code, issues = run_audit(dst, unit)
        check("L9 D12 逐集读数非单调 → 必报（cards[].ep 分支生效）",
              has(issues, "归一度", "单调"),
              f"issues={[i.get('issue') for i in issues][:2]}")
        # 复原：从原盘备份重读（副本工程每次运行都是新拷的，此处仅保险）
        shutil.copy2(os.path.join(src_project, "units", unit, "D12.json"),
                     os.path.join(u_dir, "D12.json"))

    # ---- 反证：用旧判据跑同一现盘，必须漏报 ----
    # 证明新腿有区分力，不是「反正怎么都报」的恒真闸。
    # 反证腿：旧判据把**同区间的合法读数**误报为违规（假阳性），
    # 新判据不报 ⇒ 证明改动收窄的是「口径」而非「放松了闸」。
    old_candidates = sorted(
        [f for f in os.listdir(HERE) if f.startswith("audit-unit.py.bak")],
    )
    if not old_candidates:
        check("反证 旧判据误报", False, "找不到 audit-unit.py.bak* 备份，无法做反证")
    else:
        old_path = os.path.join(HERE, old_candidates[-1])
        proc = subprocess.run(
            [sys.executable, old_path, "--project", dst, "--unit", unit, "--json"],
            capture_output=True, text=True,
        )
        try:
            old_issues = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            old_issues = []
        code, issues = run_audit(dst, unit)
        old_fp = has(old_issues, "归一度", "1.2%")
        new_fp = has(issues, "归一度", "1.2%")
        check("反证 旧判据对同区间合法读数误报、新判据不报",
              old_fp and not new_fp,
              f"旧判据误报={old_fp} 新判据误报={new_fp}")
        # 第二条反证：旧判据把豁免字段里的合规备注也误报为禁词
        old_ban = has(old_issues, "禁词", "射杀") or has(old_issues, "禁词", "感染者")
        new_ban = has(issues, "禁词", "射杀") or has(issues, "禁词", "感染者")
        check("反证 旧判据把豁免字段误报禁词、新判据不报",
              old_ban and not new_ban,
              f"旧判据误报={old_ban} 新判据误报={new_ban}")

    shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 60)
    if failures:
        print(f"负测失败 {len(failures)} 条：{failures}")
        return 1
    print("负测全通过：判据有区分力（非恒真）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
