#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D12 × D11 画面文案轴核验（**只读，不写盘**）— 逻辑层（unit 无关）

【为什么需要本脚本】
V7 校验器只管「D12.char_descriptions 必须出自 D10 锚点表」，
**不校验 D12 的 image_prompt / video_prompt 是否与 D11.visual_facts 同口径**——
这条轴校验器覆盖不到。D18 `global_checks/34` 已把它登记为方法论
（下游改 visual_facts 后必须回头核 D12 同集同镜位的卡）。

【分层纪律（U02-R01）】
本文件是**逻辑层**：判据代码与 unit 无关，**禁止复制 `_u02` 副本**（副本＝第二套实现，必然分叉）。
人工核销台账与已登记旧口径表属**内容层**，放在同目录 `d12_check_data_<UNIT>.py`，
由本脚本按 `--unit` 动态加载；内容层不存在时用**空表**并显式提示
（单元尚未开工时「无台账」是事实，不是缺陷）。

【口径定义（复算必须按此读，改判据请改本注释）】
判据 A｜要素覆盖（**提示级**，不单独构成缺陷）：
  - D11.visual_facts 按「；」切句，剔除含「角标」的句；
  - 每句取长度 ≥4 的实义片段（去空白后切 4 字窗）；
  - 片段命中率 = 该句 4 字窗中出现在「image_prompt + video_prompt」拼接串里的比例；
  - 命中率 < 0.34 → 记「疑似漏写」（warn）。
  ⚠️ 阈值 0.34 是**经验值**。D12 允许同义改写（D11「手掌撑住床沿坐起」→
    C-001「撑起上身坐起」；D11「获救的灰斑者沿钢板墙排成长队」→
    C-031「获救队列沿钢板墙自画面纵深排开」），
    故**逐字/子串判据会大量假阳性**——本脚本首版用「8 字连续子串」判覆盖，
    U01 32 镜误报 18 条，**全部经人工复核为假阳性**。
    故 A 只作提示，**不得据 A 单独判缺陷**（改判据，不改交付物）。
    人工复核结论由内容层台账 `RESOLVED_LEGACY` 承载。

判据 B｜已登记旧口径复现扫描（**error 级**）：
  - 内容层 `KNOWN_STALE` 表列出「镜位 → 旧口径片段」；
  - 命中 = 旧口径片段出现在卡文案中 → 判 error（又写回旧口径了）；
  - ⚠️ B 的词表是**已登记旧口径的枚举，不是完备证明**：
    未命中 **≠ 全无矛盾**，只代表「已登记过的旧口径未被复现」。

【用法】
  python3 check_D12_D11_alignment.py [--unit U01] [--project <项目根>]
  exit 0 = 无 error；exit 1 = 存在 error
  D11／D12 尚未产出（单元未开工）→ 打印实况并 exit 0（非缺陷）。
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROJECT = os.path.dirname(HERE)

# ── 判据 A 参数（逻辑层，全 unit 通用）──────────────────────────────────────
WINDOW = 4          # 实义片段窗长（字）
MIN_HIT = 0.34      # 片段命中率下限，低于此记 warn
MIN_LEN = 8         # 短于该字数的句子不判（信息量不足，如「无红色」）

# ── 内容层默认（该 unit 尚无内容层时使用）──────────────────────────────────
DEFAULT_RESOLVED = []
DEFAULT_STALE = []


def load_content(unit, project):
    """加载内容层 `d12_check_data_<UNIT>.py`；不存在则返回空表 + 说明。

    查找顺序：① 原样 unit ② 小写 unit ③ 目录内不区分大小写匹配。
    ①② 是为兼容大小写敏感/不敏感两种文件系统；③ 是兜底。
    """
    bases = [HERE, os.path.join(project, "scripts")]
    candidates = ["d12_check_data_%s.py" % unit, "d12_check_data_%s.py" % unit.lower()]
    for base in bases:
        for cand in candidates:
            path = os.path.join(base, cand)
            if os.path.exists(path):
                return _load_module(path)
    # ③ 不区分大小写扫描
    for base in bases:
        if not os.path.isdir(base):
            continue
        want = ("d12_check_data_%s.py" % unit).lower()
        for f in os.listdir(base):
            if f.lower() == want:
                return _load_module(os.path.join(base, f))
    return DEFAULT_RESOLVED, DEFAULT_STALE, None


def _load_module(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return (getattr(mod, "RESOLVED_LEGACY", DEFAULT_RESOLVED),
            getattr(mod, "KNOWN_STALE", DEFAULT_STALE),
            path)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def windows(sentence):
    """取 ≥WINDOW 的实义片段窗（去空白）。"""
    s = "".join(sentence.split())
    if len(s) < WINDOW:
        return []
    return [s[i:i + WINDOW] for i in range(len(s) - WINDOW + 1)]


def guard_no_unit_copy():
    """禁副本守卫（对齐 S12／U02-R01 与本岗既有做法）：
    本脚本是 unit 无关的**唯一逻辑层**；若同目录出现按单元派生的副本
    （如 check_D12_D11_alignment_U02.py / _u02.py），即 exit 2 拒绝运行 ——
    副本＝第二套实现，必然与本脚本分叉。
    内容层 `d12_check_data_<UNIT>.py` 是**数据**不是副本，不在拦截范围。
    """
    stem = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
    hits = []
    for base in (HERE,):
        if not os.path.isdir(base):
            continue
        for f in sorted(os.listdir(base)):
            if not f.endswith(".py"):
                continue
            name = os.path.splitext(f)[0]
            if name == stem:
                continue
            if name.lower().startswith(stem.lower()):
                hits.append(os.path.join(base, f))
    if hits:
        print("=" * 72)
        print("⛔ 检出单元副本，拒运行（副本＝第二套实现，必然分叉）：")
        for h in hits:
            print("  - %s" % h)
        print("  正确做法：改本脚本使其支持 --unit，**不要**复制副本。")
        print("=" * 72)
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser(description="D12 × D11 画面文案轴核验（只读）")
    ap.add_argument("--unit", default="U01", help="单元号，默认 U01")
    ap.add_argument("--project", default=DEFAULT_PROJECT, help="项目根（含 units/ 与 shared/）")
    args = ap.parse_args()

    guard = guard_no_unit_copy()
    if guard:
        return guard

    unit = args.unit
    project = os.path.abspath(args.project)
    d11_path = os.path.join(project, "units", unit, "D11.json")
    d12_path = os.path.join(project, "units", unit, "D12.json")

    resolved, stale, content_path = load_content(unit, project)

    print("=" * 72)
    print("D12 × D11 画面文案轴核验（只读）｜unit=%s" % unit)
    print("  内容层: %s" % (content_path if content_path else "**无**（该单元尚无人工核销台账，用空表）"))
    print("-" * 72)

    # ── 前置：上游是否已产出 ────────────────────────────────────────────────
    missing = [p for p in (d11_path, d12_path) if not os.path.exists(p)]
    if missing:
        print("实况：以下文件尚未产出 → 本轴当前**无覆盖**（单元未开工，非缺陷）：")
        for p in missing:
            print("  - %s" % os.path.relpath(p, project))
        print("  产出 D11＋D12 后复跑本脚本。")
        print("=" * 72)
        print("error: 0    warn: 0    （未开工，非缺陷）")
        return 0

    d11 = load_json(d11_path)
    d12 = load_json(d12_path)

    shots = {}
    for ep in d11.get("episodes", []):
        for s in ep.get("shots", []):
            shots[(ep["ep"], s["shot_id"])] = s

    cards = {(c["ep"], c["shot_id"]): c for c in d12.get("cards", [])}

    errors = []
    warns = []
    cov_rows = []
    resolved_count = 0

    # ── 覆盖完整性：镜/卡双向齐平 ───────────────────────────────────────────
    for k in sorted(set(shots) - set(cards)):
        errors.append("D12 缺卡: ep%03d 镜%d" % k)
    for k in sorted(set(cards) - set(shots)):
        errors.append("D12 多卡: ep%03d 镜%d" % k)

    for k in sorted(set(shots) & set(cards)):
        shot, card = shots[k], cards[k]
        blob = (card.get("image_prompt", "") or "") + " " + (card.get("video_prompt", "") or "")
        facts = shot.get("visual_facts", "") or ""
        sent_total = 0
        sent_hit = 0
        low = []
        for seg in facts.split("；"):
            seg = seg.strip().rstrip("。")
            if not seg or "角标" in seg:
                continue
            if len("".join(seg.split())) < MIN_LEN:
                continue
            wins = windows(seg)
            if not wins:
                continue
            sent_total += 1
            hits = sum(1 for w in wins if w in blob)
            ratio = hits / len(wins)
            if ratio >= MIN_HIT:
                sent_hit += 1
                continue
            # 已人工核销台账命中 → 记为「已核销」，不计 warn
            hit_res = next((r for r in resolved
                            if r[0] == k[0] and r[1] == k[1] and seg.startswith(r[2])), None)
            if hit_res:
                resolved_count += 1
                continue
            low.append((seg, ratio))
        cov = (sent_hit / sent_total) if sent_total else 1.0
        cov_rows.append((k, card.get("card_id", "?"), cov, sent_total))
        for seg, ratio in low:
            warns.append("A 疑似漏写 ep%03d 镜%d (%s, 命中%.2f): %s"
                         % (k[0], k[1], card.get("card_id", "?"), ratio, seg[:48]))

    # ── 判据 B：已登记旧口径复现 ─────────────────────────────────────────────
    for ep, sid, old, why in stale:
        card = cards.get((ep, sid))
        if card is None:
            continue
        blob = (card.get("image_prompt", "") or "") + " " + (card.get("video_prompt", "") or "")
        if old in blob:
            errors.append("B 旧口径复现 ep%03d 镜%d (%s): 「%s」——%s"
                          % (ep, sid, card.get("card_id", "?"), old, why))

    # ── 机位/时长轴（可直接判定的硬项）────────────────────────────────────
    for k in sorted(set(shots) & set(cards)):
        shot, card = shots[k], cards[k]
        head = (card.get("image_prompt", "") or "")[:120]
        for field, label in (("shot_size", "景别"), ("camera_angle", "角度")):
            val = shot.get(field)
            if val and val not in head:
                errors.append("卡头缺%s ep%03d 镜%d: %s" % (label, k[0], k[1], val))
        lens = shot.get("lens_mm")
        if lens and ("%dmm" % lens) not in head:
            errors.append("卡头缺焦距 ep%03d 镜%d: %dmm" % (k[0], k[1], lens))
        m = re.search(r"(\d+)\s*秒", card.get("video_prompt", "") or "")
        if not m:
            errors.append("video_prompt 无时长 ep%03d 镜%d" % (k[0], k[1]))
        elif int(m.group(1)) != int(shot.get("duration_sec", -1)):
            errors.append("时长不符 ep%03d 镜%d: D12=%ss D11=%ss"
                          % (k[0], k[1], m.group(1), shot.get("duration_sec")))

    # ── 汇总 ───────────────────────────────────────────────────────────────
    low_cov = [r for r in cov_rows if r[2] < 0.5]
    print("  镜数 %d ／ 卡数 %d ／ 判据B 旧口径表 %d 条"
          % (len(shots), len(cards), len(stale)))
    print("-" * 72)
    print("判据 A 要素覆盖（提示级）：")
    if cov_rows:
        avg = sum(r[2] for r in cov_rows) / len(cov_rows)
        print("  平均覆盖率 = %.3f   最低 = %.3f (%s)"
              % (avg, min(r[2] for r in cov_rows), min(cov_rows, key=lambda r: r[2])[1]))
    print("  覆盖率 <0.5 的镜: %s"
          % (", ".join("ep%03d镜%d" % (r[0][0], r[0][1]) for r in low_cov) or "无"))
    print("  人工核销台账命中（已确认覆盖，非漏写）: %d 条" % resolved_count)
    print("-" * 72)
    print("判据 B 已登记旧口径扫描：%s"
          % ("未复现 ✅（注意：词表非完备，未命中≠全无矛盾）"
             if not any("B 旧口径" in e for e in errors) else "有复现 ❌"))
    print("-" * 72)
    print("error: %d    warn: %d    已核销: %d" % (len(errors), len(warns), resolved_count))
    for e in errors:
        print("  [ERROR] " + e)
    for w in warns:
        print("  [WARN ] " + w)
    print("=" * 72)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
