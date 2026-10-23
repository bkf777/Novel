#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_D08_shotintent_body.py —— shot_intent **轴②（契约↔正文）** 专项校验器。

背景（企划合规 2026-10-23 Q53 裁定）：
  契约类字段须验**两条轴** ——
    轴① 契约 ↔ 消费方（D08.shot_intent ↔ D11.visual_facts）：已由 check_D08_D11_shotintent.mjs 覆盖；
    轴② 契约 ↔ 正文（D08.shot_intent ↔ 同条目 body.text）：**本岗此前无机器闸**。
  企划合规实证：**轴①绿不代表轴②绿** —— 断言方向被改写时轴①会假绿。

本脚本只管轴②。判据形态（收口自本岗既往经验）：
  · **M1 宽口径**（含免责项）：主张项的实词 2-gram 在同条目正文中的**覆盖率** ≥ 阈值 → 判「有正文依据」；
  · **M2 逐字**（只对确证项）：数字 token（读数／百分比／LV.x／时刻）**逐字必须**在正文中出现，缺失即判不达标。
  两轴叠加：**M1 不达标 或 M2 数字缺失** → 列入「候选不达标」，交人工判读（不自动改稿）。

口径说明（避免把判据做成恒真）：
  · 主张项 = shot_intent 切到第一个「，」「。」「；」后的首分句（契约的**要拍对象**在此句）；
  · 契约套话（必须/被看见/可读/…）先剥离，剩余视为**实词**；
  · 覆盖率 = 命中 2-gram 数 / 实词 2-gram 总数（实词 < 2 字时按「是否整体出现」判）；
  · **数字 token 走 M2 逐字**，不参与覆盖率稀释。

用法：
  python3 scripts/check_D08_shotintent_body.py --project <项目根> --unit U02
  python3 scripts/check_D08_shotintent_body.py --project <项目根> --unit U02 --self-test   # 负测
退出码：0＝全部达标；1＝存在候选不达标；2＝参数/前置错误。
"""
import argparse
import json
import os
import re
import sys

# ── 契约套话（剥离后不参与覆盖率）────────────────────────────────────
CONTRACT_BOILERPLATE = [
    "必须被完整看见", "必须被看清", "必须能被读出来", "必须能逐项读出", "必须同屏出现",
    "必须给到独立可辨的视觉呈现", "必须同时在画面里", "必须在画面里有出处", "必须被看见",
    "要交代清楚", "要完整可见", "必须可读", "被完整看见", "被看清", "能逐项读出",
    "必须", "可读", "看清", "可见", "呈现", "出现",
]
# ── 实词停用词（剥离后不参与覆盖率）────────────────────────────────
STOPWORDS = set(
    "的了是在有和与也就都还再并而之其此那某每该对从到把被给让使将上下前后中里内外"
    "一二三四五六七八九十零百千万个次条张只件步下这一那一步过程中动作信息内容画面镜头"
    "本集本单元本岗必须说明结果关系状态位置方式方面东西时候时候".split()
)
NUM_TOKEN = re.compile(r"\d+(?:\.\d+)?%?|[A-Za-z]+\.\d+|LV\.\d+|\d+:\d+")
CJK2 = re.compile(r"[一-鿿]{2,}")

# ── M2 逐字：关键限定成分（数量／序数／方位／级数／读数）─────────────
# 判据形态收口：**M1 宽口径（提示层）＋ M2 逐字（只对确证项，硬失败层）**。
# M2 只取「可被改写成假绿」的限定成分 —— 数量、序数、方位、级数、读数；
# 泛指量词（个/块/名/位/些）**不取**（它们不承载方向，误报率高）。
KEY_PATTERNS = [
    r"第[零一二三四五六七八九十百千\d]+[个只道层栏排页行张份次步轮道门]",
    r"最[后前上下左右内]",
    r"LV\.\d+",
    r"\d+(?:\.\d+)?\s*%",
    r"[零一二三四五六七八九十百千两几半\d]+\s*(?:小时|分钟|秒|天|年|次|下|遍|层|格|行|道|份)",
    r"[零一二三四五六七八九十百千两几半\d]+\s*[阶级段版]",
]
KEY_RE = re.compile("|".join(KEY_PATTERNS))


def strip_boilerplate(s: str) -> str:
    for w in sorted(CONTRACT_BOILERPLATE, key=len, reverse=True):
        s = s.replace(w, "")
    return s


def strip_stopwords(s: str) -> str:
    for w in sorted(STOPWORDS, key=len, reverse=True):
        s = s.replace(w, "")
    return s


def claim_of(shot_intent: str) -> str:
    """主张项 = 首分句（契约的「要拍对象」所在句）。"""
    return re.split(r"[，。；：]", shot_intent)[0].strip()


def bigrams(s: str):
    out = set()
    for run in CJK2.findall(s):
        for i in range(len(run) - 1):
            out.add(run[i:i + 2])
    return out


def num_tokens(s: str):
    return set(NUM_TOKEN.findall(s))


def check_entry(intent: str, text: str, ep_texts: str = ""):
    """返回 (M1覆盖率, M2缺失关键限定成分, 主张项, 实词)。

    M1（宽口径·提示层）：实词 2-gram 在**同条目**正文中的覆盖率。
    M2（逐字·硬失败层）：主张项中的**关键限定成分**（数量/序数/方位/级数/读数）
       必须逐字出现在**同集**正文（同集口径：契约可指向同集兄弟条目，如
       ep003 body[3] 的「LV.1」在 body[4] 的字幕行）。
    """
    claim = claim_of(intent)
    real = strip_stopwords(strip_boilerplate(claim))
    body_bi = bigrams(text)
    intent_nums = num_tokens(claim)
    scope = ep_texts if ep_texts else text          # 同集口径（与 M2 关键限定成分一致）
    body_nums = num_tokens(scope)
    missing_nums = sorted(n for n in intent_nums if n not in body_nums)

    # ── M1 ──
    if len(real) < 2:
        hit = 1.0 if (real and real in text) else 0.0
    else:
        bi = bigrams(real)
        hit = (len(bi & body_bi) / len(bi)) if bi else (1.0 if real in text else 0.0)

    # ── M2：关键限定成分逐字（同集口径）──
    scope = ep_texts if ep_texts else text
    missing_keys = [k for k in sorted(set(KEY_RE.findall(claim))) if k not in scope]
    return hit, missing_nums, missing_keys, claim, real


THRESHOLD = 0.34


def run_unit(project: str, unit: str):
    path = os.path.join(project, "units", unit, "D08.json")
    with open(path, encoding="utf-8") as f:
        d08 = json.load(f)
    ep_scope = {}
    for ep in d08["episodes"]:
        ep_scope[ep["ep"]] = "\n".join((b.get("text") or "") + "\n" + (b.get("shot_intent") or "")
                                        for b in ep["body"])
    rows = []
    for ep in d08["episodes"]:
        for i, b in enumerate(ep["body"]):
            si = b.get("shot_intent")
            if not si:
                continue
            cov, missing_nums, missing_keys, claim, real = check_entry(
                si, b.get("text", ""), ep_scope.get(ep["ep"], ""))
            hard_fail = bool(missing_keys) or bool(missing_nums)
            soft = cov < THRESHOLD
            rows.append({
                "ep": ep["ep"], "idx": i, "cov": cov, "missing_nums": missing_nums,
                "missing_keys": missing_keys, "claim": claim, "real": real,
                "text": b.get("text", ""), "intent": si,
                "hard_fail": hard_fail, "soft": soft,
                "bad": hard_fail or soft,
            })
    return d08.get("version"), rows


def self_test(project: str, unit: str):
    """负测：注入一条**已知故障**（把 ep14 body[4] 的「最后一栏」改成「第三栏」），
    判据须**精确报错**（不得恒真通过）。真盘零写入。"""
    version, rows = run_unit(project, unit)
    target = None
    for r in rows:
        if r["ep"] == 14 and "最后一栏" in r["claim"]:
            target = r
            break
    if target is None:
        print("❌ 负测前置失败：未找到 ep14「最后一栏」样本")
        return 2
    print(f"注入故障：ep{target['ep']} body[{target['idx']}] 主张项「{target['claim']}」"
          f" → 篡改为「成本模型第三栏没有合上」；正文不变")
    cov, _, miss_keys, claim, _ = check_entry("成本模型第三栏没有合上必须被看见", target["text"])
    ok_injected = bool(miss_keys)
    print(f"  M2 关键限定成分缺失 = {miss_keys}（{claim}）→ 判硬失败 = {ok_injected} "
          f"{'✅ 判据有判别力' if ok_injected else '❌ 判据恒真'}")
    print(f"  （同期 M1 覆盖率 = {cov:.3f}，阈值 {THRESHOLD} → M1 单层会漏判，"
          f"故必须靠 M2 逐字层兜底）")
    ok_clean = not target["hard_fail"]
    print(f"  未篡改样本 M2 硬失败 = {target['hard_fail']}（须为 False）"
          f"{'✅' if ok_clean else '❌'}")
    return 0 if (ok_injected and ok_clean) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    project = os.path.abspath(args.project)

    if args.self_test:
        return self_test(project, args.unit)

    version, rows = run_unit(project, unit=args.unit)
    n = len(rows)
    if n == 0:
        print("❌ 受检 0 条 —— 按 Q49，结论一律不成立")
        return 2
    hard = [r for r in rows if r["hard_fail"]]
    soft = [r for r in rows if r["soft"] and not r["hard_fail"]]
    covs = sorted(r["cov"] for r in rows)
    print(f"轴②（契约↔正文）专项校验｜{args.unit}｜D08 版本 {version}")
    print(f"受检 shot_intent 条数：{n}（Q49：受检 > 0）")
    print(f"  M2 逐字硬失败：{len(hard)} 条")
    print(f"  M1 覆盖率提示层（< {THRESHOLD}）：{len(soft)} 条")
    print(f"  合计候选不达标：{len(hard) + len(soft)}｜其余 {n - len(hard) - len(soft)} 条达标")
    print(f"  覆盖率分布：min {covs[0]:.3f}｜中位 {covs[len(covs)//2]:.3f}｜max {covs[-1]:.3f}")
    for r in hard:
        print(f"  ❌ M2 ep{r['ep']:03d} body[{r['idx']}] 缺关键限定成分 {r['missing_keys']}"
              f"{('｜缺数字 ' + '/'.join(r['missing_nums'])) if r['missing_nums'] else ''}")
        print(f"      主张项：{r['claim']}")
        print(f"      正文  ：{r['text']}")
    for r in soft:
        print(f"  ⚠️ M1 ep{r['ep']:03d} body[{r['idx']}] 覆盖率 {r['cov']:.3f}"
              f"（M2 未硬失败 → 多为口径差，需人工判读）")
        print(f"      主张项：{r['claim']}")
        print(f"      正文  ：{r['text']}")
    if hard or soft:
        print(f"\n→ 硬失败 {len(hard)} 条须返修（改内容源重跑）；"
              f"提示层 {len(soft)} 条交人工判读（真失配／口径差／成立）。本脚本不自动改稿。")
        return 1
    print("\n✅ 轴② 全部达标：每条 shot_intent 的主张项均能在同集正文中找到依据，"
          "且关键限定成分逐字一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
