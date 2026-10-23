#!/usr/bin/env python3
"""
check_D06_D07_roster_consistency.py —— 在场名单 × 正文提及 一致性核验（只读）

为什么需要这条轴（2026-10-23 U02 实测事故）：
  V1–V11 全部只校「字段在不在、枚举合不合法、时长对不对」，**没有任何一条规则校
  「正文里提到某个角色，但这个角色不在该集在场名单里」**。于是 D06 ep014 的
  must_happen 写了「与叶承钧一起确认暗杀组名单」，而该集在场名单是
  [LC, YD-GC, YJ-JZ]（无 YJ-ES）→ 台本编剧只能改用「按着继承人的印」绕开，
  分镜导演若照 D06 拍就会出现「D08 不在场 / D11 在场」的**剧本 vs 分镜分裂**。

判据分域（本脚本头写死，复算须按此读）：
  【域 1 · 本集域】只扫「本集画面内发生」的字段 → 命中的角色必须在本集在场名单里。
      ⚠️ **「提及」≠「在场」**：远端/间接提及（求救信号／远处传来／来电／屏上…）**不构成在场要求**
      → 命中角色不在名单且该句含此类标记时，降为**提示级（warn）**，不判缺陷。
      （标记表不含「名单」「一起」——同框表述仍判 error。）
      扫：title / logline / must_happen / emotion_goal / D07 的 story_time、
          carry_over / answer / cost / scenes / quad_segments[].note / scene_needs
  【域 2 · 承接层】hook_in 是**上一集的收尾画面**，按定义发生在上一集 —— 不能拿
      本集在场名单判它。hook_out 是**本集的收尾画面**，属本集域。
      → 故 hook_in 单独跳过，hook_out 纳入本集域。
  【域 3 · 名单一致性】D06.characters 与 D07.present_characters 必须逐集完全相等
      （企划合规人工审读第 4 项的规则化）。D08.present_characters 必须是
      D07.present_characters 的**子集**（D08 可以不给某人台词，但 D08 不能有
      D07 没有的人 —— 这一条由 V2 负责 error 级，本脚本只做交叉提示）。

已知盲区（假阳性来源；勿据以单独判缺陷）—— **D18 Q63 ① 要求：盲区必须写在脚本头**
  - 角色以**别名/称号/代称/多字简称**出现时，姓名匹配抓不到（如「继承人」指 YJ-ES）
    → 本脚本只做姓名精确匹配，抓不到即不报，**不是漏检的保证**。
  - 同一角色在正文里被提及但其实是「画外音/电话那头」→ 属本脚本抓不到的口径，
    需人工判读。**本脚本是筛子不是判决书。**
  - **「提及」≠「在场」**：远端/间接提及（求救信号／远处传来／来电／屏上…）**不构成在场要求**
    → 命中角色不在名单且该句含此类标记时降为**提示级**，不判缺陷（U01 ep008 实测 4 条误报已修）。
    ⚠️ 但这**只是把已知的误报模式降级，不是消除误报**：新增表述若不在标记表内，仍可能误报或漏报。
  - ⇒ 本脚本 PASS **只能缩小人工审读范围**，不得作为内容合格依据（Q63 ③）；
    同理 **FAIL 也不等于内容缺陷**：提示级（warn）须人工判读，error 级须回原文核。
    D03–D20 单元正文改动前先跑本脚本，再人工判读（Q63 ②）。

退出码：0 = 无 error；1 = 有 error。幂等、只读、不写盘。

用法：
  python3 scripts/check_D06_D07_roster_consistency.py --project 02_项目/双相潮主 --unit U02
"""

import argparse
import json
import os
import re
import sys

# 域 1 假阳性守卫（2026-10-23 U01 实测）：**「提及」≠「在场」**
#   U01 ep008「远处传来云顶财阀装甲车的引擎声，苏清辞的求救信号出现在面板上」——
#   苏清辞本人在 U01 未出场（ep009 才登场），在场名单 [LC, YHY] **正确**；
#   原判据把「远端信号」当「在场角色」→ 误报 4 条，且 U01 是**已锁单元**，误报会误导解冻。
#   故：命中角色不在名单、但该句含**远端/间接提及标记**时，降为**提示级（warn）**，不判缺陷。
#   ⚠️ 标记表刻意**不含「名单」「一起」「同框」** —— U02 ep014「与叶承钧一起确认暗杀组名单」
#   是**真缺陷**（同框），含「名单」必须仍判 error（负测已实跑，见脚本头）。
NON_PRESENCE = re.compile(
    r"求救信号|求救|呼救|信号|呼叫|来电|消息|远处传来|传来|电话|无线电|广播"
    r"|屏上|面板上|屏幕亮起|浮现"
)

# 本集域字段（D06）
D06_PRESENT_FIELDS = ["title", "logline", "emotion_goal", "hook_out"]
# 承接层字段：按定义发生在上一集，跳过本集在场判定
D06_CARRY_FIELDS = ["hook_in"]
# 本集域字段（D07）
D07_PRESENT_FIELDS = ["story_time", "carry_over", "answer", "cost", "emotion_goal"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def collect_texts_ep6(ep):
    out = []
    for k in D06_PRESENT_FIELDS:
        if ep.get(k):
            out.append((k, ep[k]))
    for i, m in enumerate(ep.get("must_happen") or []):
        out.append((f"must_happen[{i}]", m))
    for i, l in enumerate(ep.get("locations") or []):
        out.append((f"locations[{i}]", l))
    return out


def collect_texts_ep7(ep):
    out = []
    for k in D07_PRESENT_FIELDS:
        if ep.get(k):
            out.append((k, ep[k]))
    for i, m in enumerate(ep.get("must_happen") or []):
        out.append((f"must_happen[{i}]", m))
    for s in ep.get("scenes") or []:
        out.append((f"scenes[{s.get('code')}]", f"{s.get('location','')} {s.get('time','')}"))
    for q in ep.get("quad_segments") or []:
        if q.get("note"):
            out.append((f"quad_segments[{q.get('index')}].note", q["note"]))
    for i, s in enumerate(ep.get("scene_needs") or []):
        out.append((f"scene_needs[{i}]", json.dumps(s, ensure_ascii=False)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    unit = args.unit
    f_d04 = os.path.join(root, "shared", "D04.json")
    f_d06 = os.path.join(root, "units", unit, "D06.json")
    f_d07 = os.path.join(root, "units", unit, "D07.json")
    f_d08 = os.path.join(root, "units", unit, "D08.json")

    missing = [p for p in [f_d04, f_d06, f_d07] if not os.path.exists(p)]
    if missing:
        print(f"[SKIP] 缺少文件（非缺陷，尚未开工）：{missing}")
        return 0

    d04 = load(f_d04)
    d06 = load(f_d06)
    d07 = load(f_d07)
    d08 = load(f_d08) if os.path.exists(f_d08) else None

    names = {c["id"]: c["name"] for c in d04.get("characters", [])}
    e6 = {e["ep"]: e for e in d06.get("episodes", [])}
    e7 = {e["ep"]: e for e in d07.get("episodes", [])}
    e8 = {e["ep"]: e for e in d08.get("episodes", [])} if d08 else {}

    errors, warns = [], []
    scanned = 0   # 受检条目数（字段 × 角色 的检查次数）—— 独立于错误数统计
    matched = 0   # 命中的角色提及数
    checked = 0   # 命中且构成缺陷的条数
    remote = 0    # 命中但属远端/间接提及（提示级，不计缺陷）的条数

    def scan(items, roster, doc, ep, layer="本集域"):
        nonlocal scanned, matched, checked, remote
        for fld, txt in items:
            for cid, nm in names.items():
                scanned += 1
                if nm not in txt:
                    continue
                matched += 1
                if cid not in roster:
                    m = NON_PRESENCE.search(txt)
                    if m:
                        remote += 1
                        warns.append(
                            f"ep{ep} {doc}.{fld}({layer}): 提及「{nm}」({cid}) 不在在场名单 "
                            f"{sorted(roster)} —— 但该句为**远端/间接提及**（命中「{m.group(0)}」），"
                            f"不构成在场要求 → 提示级，不判缺陷"
                        )
                        continue
                    checked += 1
                    errors.append(
                        f"ep{ep} {doc}.{fld}({layer}): 提及「{nm}」({cid}) "
                        f"但不在在场名单 {sorted(roster)}"
                    )

    # 域 3：D06.characters == D07.present_characters
    for ep in sorted(e6):
        if ep not in e7:
            errors.append(f"ep{ep}: D06 有该集但 D07 没有")
            continue
        r6 = set(e6[ep].get("characters") or [])
        r7 = set(p["char_id"] for p in (e7[ep].get("present_characters") or []))
        if r6 != r7:
            errors.append(
                f"ep{ep}: D06.characters {sorted(r6)} != D07.present_characters {sorted(r7)}"
            )

    # 域 1：本集域 —— 正文提及必须在场
    for ep in sorted(e6):
        roster6 = set(e6[ep].get("characters") or [])
        roster7 = set(p["char_id"] for p in (e7.get(ep, {}).get("present_characters") or []))
        scan(collect_texts_ep6(e6[ep]), roster6, "D06", ep)
        if ep in e7:
            scan(collect_texts_ep7(e7[ep]), roster7, "D07", ep)

    # 域 2：承接层 —— hook_in 提及的角色必须在上集在场名单里（不是本集）
    for ep in sorted(e6):
        prev = e6.get(ep - 1)
        if not prev:
            continue
        prev_roster = set(prev.get("characters") or [])
        carry = [(f, t) for f, t in collect_texts_ep6(e6[ep]) if f in D06_CARRY_FIELDS]
        scan(carry, prev_roster, "D06", ep, layer="承接层")

    # 域 3b：D08.present_characters ⊆ D07.present_characters
    for ep in sorted(e8):
        r8 = set(e8[ep].get("present_characters") or [])
        r7 = set(p["char_id"] for p in (e7.get(ep, {}).get("present_characters") or []))
        for cid in sorted(r8 - r7):
            warns.append(f"ep{ep} D08.present_characters 含 {cid}，但不在 D07 在场名单里")

    print(f"■ 在场名单一致性核验 {unit}")
    print(f"  判据：域1 本集域正文提及 / 域2 承接层按上集判 / 域3 D06==D07 名单逐集相等")
    print(f"  受检集数 {len(e6)}｜受检条目 {scanned} 条（字段×角色）｜命中角色提及 {matched} 条"
          f"｜构成缺陷 {checked} 条｜远端提及(提示级) {remote} 条｜error {len(errors)}｜warn {len(warns)}")
    # Q63 ①：结论必须附「受检条数 ＋ 覆盖轴 ＋ 已知盲区」
    print("  已知盲区：本脚本只做姓名精确匹配，**抓不到别名/称号/代称/多字简称**"
          "（如「继承人」指 YJ-ES）与画外音口径 → PASS 只能缩小人工审读范围，不得当作内容合格依据（Q63 ③）")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warns:
        print(f"  ! {w}")
    # 空集恒真守卫：受检条目为 0 时不得判通过
    if scanned == 0:
        print("  ⛔ 受检条目 0 条 —— 本次未真正执行扫描，结论不成立（空集恒真）")
        return 1
    if not errors:
        print(f"  ✅ 一致性通过（受检 {scanned} 条，命中 {matched} 条）")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
