#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读校验：分镜导演（D11）↔ 白模场景师（D13）机位／视点口径交叉核对。

【为什么要有】
  U02-R07 裁定（企划合规 §一百一十六）条件② 要求：「若 D11 该镜含机位／视点字段、
  D14 package 含相机参数，须一并同步」；附语义要求：**g27 分离 0.35 m 后已不是严格 POV，
  须标注「近似 POV（视点代表位）」**。
  ⇒ 需要一个**机器可复跑**的判据，才能在白模落地（分离完成）的那个时点
  **自动发现「D11 该改、但还没改」**，而不是靠人盯台账。

【本脚本只读】
  只读取 units/<unit>/D11.json 与 units/<unit>/D13.json，**不写任何文件**。

【判据（每条都有区分力，恒真断言零信息量；Q67 误报比漏报更贵）】
  A 配对完整：D11 每镜都能在 D13 找到唯一机位（按 ep 内 global_shot_no 升序配对）。
      缺配对 → **硬失败**（D13 少机位或 D11 多镜位）。

  B 视点口径 —— **按「机位与眼位是否已分离」这条真实语义轴分类**，
    而**不是**按「notes 里有没有某个 POV 词」分类：

      pov_d11     = D11.camera_angle 含「主观」或「POV」（严格 POV）
      approx_d11  = D11.camera_angle **或 D11.note** 含「近似 POV」（已按裁定标注）
                    ⚠️ 2026-10-23 10:3x 扩展：`camera_angle` 是 `03_规格/schema.json`
                    定义的**七选一闭枚举**（平视／俯视／仰视／顶视／过肩／主观视角／客观跟拍），
                    **无「近似 POV」取值**；硬闸 V1 会把新枚举值判成 error。
                    故 U02-R07 的「须标注『近似 POV（视点代表位）』」在 D11 侧的
                    **schema 合规落点是 `note` 字段**（本岗已按此落地并上报 schema 缺口）。
                    ⇒ 标注既可在 camera_angle、也可在 note 命中 —— 两者皆算「已按裁定标注」。
      sep_d13     = D13.notes 表明机位**已与眼位分离**
                    （正则「分离 <数> m」或「已不是严格 POV」或「近似 POV」）
      coincide_d13= D13.notes 表明机位**仍与眼位重合**（含「眼位重合」或「角色视点」）
                    且**不**含分离表述（分离优先于重合：同一句里两者并存时以分离为准）
      eye_d13     = D13.notes 含眼位/视点位表述（眼位重合／角色视点／视点代表位）

      B1  approx_d11                                        → 已按裁定标注（通过）
      B2  pov_d11 且 sep_d13                                → **提示级「待同步」** ⭐
          （白模已执行分离、D11 仍写严格 POV → 按裁定须标注「近似 POV（视点代表位）」，
            标注落 D11 `note`；`camera_angle` 保持闭枚举合法值）
      B3  pov_d11 且 coincide_d13                           → 分离前一致（通过，等白模分离）
      B4  pov_d11 且 neither                                → D13 未声明眼位关系（**不判定**，
          不提示、不阻断 —— 无证据不推定，避免误报）
      B5  非 pov_d11 且 sep_d13                             → 已分离·非 POV 镜（**无需改 D11**；
          该镜 D11 根本没作 POV 声明，白模分离属常规机位设置，不构成 D11 欠账）
      B6  非 pov_d11 且 eye_d13（非 sep）                   → 提示级「口径不对称」（**非缺陷**）
          D11 的 camera_angle 是俯仰/角度词表（平视／俯视／仰视／客观跟拍／主观视角），
          其中只有「主观视角」才是 POV 标记词；「平视」只说俯仰角，不表达「客观」。
          且 D13 的「眼位重合」是**机位几何描述**，当该镜画面主体不是角色代理体时
          （例：ep001/镜2 特写面板、不给人体）眼位重合**无害**。
          ⇒ 「D13 眼位表述 ＋ D11 未用 POV 词」**不构成矛盾**，只能作提示级登记。

  C 计数自证：打印受检组数（＝D11 镜数）＋ 六类计数，**各类之和 == 受检组数**（可自校验）。

【本版修订（2026-10-23，本岗自查）—— 修的是**判据本身**，不是数据】
  上一版把「视点代表位」与「眼位重合／角色视点」并入同一键组 pov_d13，
  于是白模 v1.1 真落地「机位与角色眼位分离 0.35 m … 视线自**视点代表位**…本镜为近似 POV」
  时，pov_d13 仍为真 → 误判成「分离前一致」，**该报「待同步」却没报**。
  根因＝**用「有没有 POV 词」代替了「是否已分离」**。
  ⇒ 本版改为按分离语义轴分六类，并新增 B5（已分离但 D11 无 POV 声明 → 明确判「无需改」）。
  ⚠️ 旧版负测之所以假绿：夹具把 notes 写成**简化措辞**（不含「视点代表位」），
  形态≠真实落盘形态 —— 判据缺陷因此被夹具掩盖。
  ⇒ 新增「真实落盘形态」回归腿（见 selftest L5/L6），专门盯这一类。

【退出码】
  0 = 无硬失败（提示级「待同步」不阻断，只提示；判定依据不足者不提示）
  1 = 存在硬失败（配对缺失）

用法：
  python3 scripts/check_D11_D13_camera_alignment.py --project . --unit U01
  python3 scripts/check_D11_D13_camera_alignment.py --project . --unit U02
"""
import argparse
import json
import os
import re
import sys

# D11 侧：camera_angle 词表里只有「主观视角」是严格 POV 标记词
POV_D11_KEYS = ("主观", "POV")
# D11 侧：已按裁定标注
APPROX_D11_KEY = "近似 POV"
# D11 侧：裁定的**数值依据**（条件③：写明「机位与角色眼位分离 0.35 m（…0.25 m ＋ 0.10 m 余量）」，
# 禁只写数字不留依据）。用于 B1 的附带提示：已标注但未留依据者提示。
BASIS_KEYS = ("分离 0.35 m", "0.25 m ＋ 0.10 m 余量")
# D13 侧：含眼位/视点位表述（用于 B6 口径不对称登记）
EYE_D13_KEYS = ("眼位重合", "角色视点", "视点代表位")
# D13 侧：表明机位**仍与眼位重合**（B3）
COINCIDE_D13_KEYS = ("眼位重合", "角色视点")
# D13 侧：表明机位**已与眼位分离**（B2/B5）。正则优先，其次关键措辞。
SEP_D13_RE = re.compile(r"分离\s*[0-9]+(?:\.[0-9]+)?\s*m")
SEP_D13_KEYS = ("已不是严格 POV", APPROX_D11_KEY)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def d13_camera_map(d13):
    """按 ep 聚合 camera_positions，按 global_shot_no 升序 → {(ep, shot_id): camera}"""
    by_ep = {}
    for sc in d13.get("scenes", []):
        ep = sc.get("ep")
        for cp in sc.get("camera_positions", []) or []:
            by_ep.setdefault(ep, []).append(cp)
    out = {}
    for ep, lst in by_ep.items():
        lst.sort(key=lambda c: (c.get("global_shot_no") if isinstance(c.get("global_shot_no"), int) else 0))
        for i, cp in enumerate(lst, 1):
            out[(ep, i)] = cp
    return out


def d11_shots(d11):
    out = []
    for ep in d11.get("episodes", []):
        for s in ep.get("shots", []) or []:
            out.append((ep.get("ep"), s))
    return out


def classify(angle, notes, d11_note=""):
    """返回 (类别键, 细节)。类别键 ∈ B1..B6 之一。

    d11_note：D11 该镜的 note 字段。U02-R07 的「近似 POV（视点代表位）」标注
    在 D11 侧的 schema 合规落点是 note（camera_angle 为七选一闭枚举），
    故「已按裁定标注」须同时看 camera_angle 与 note。
    """
    pov_d11 = any(k in angle for k in POV_D11_KEYS)
    approx_d11 = (APPROX_D11_KEY in angle) or (APPROX_D11_KEY in d11_note)
    sep_d13 = bool(SEP_D13_RE.search(notes)) or any(k in notes for k in SEP_D13_KEYS)
    # 分离优先于重合：同一句里两者并存时以分离为准（白模补记时两句常并存）
    coincide_d13 = (not sep_d13) and any(k in notes for k in COINCIDE_D13_KEYS)
    eye_d13 = any(k in notes for k in EYE_D13_KEYS)

    if approx_d11:
        where = "camera_angle" if APPROX_D11_KEY in angle else "note"
        basis = "" if any(k in d11_note for k in BASIS_KEYS) else "；⚠️ 但 note 未写 0.35 m 数值依据（裁定条件③）"
        return "B1", (f"D11 已按裁定标注「近似 POV（视点代表位）」（标注落在 {where}）"
                      f"｜camera_angle＝「{angle}」{basis}")
    if pov_d11 and sep_d13:
        return "B2", (f"D11 camera_angle＝「{angle}」为严格 POV，但 D13 已声明机位与眼位分离"
                      f"（notes：{notes[:80]}）→ 按 U02-R07 附语义要求须标注「近似 POV（视点代表位）」"
                      f"（落 D11 note；camera_angle 保持闭枚举合法值）")
    if pov_d11 and coincide_d13:
        return "B3", (f"D11 camera_angle＝「{angle}」为严格 POV，D13 仍为眼位重合"
                      f"（notes：{notes[:80]}）→ 分离前一致，待白模分离后同步")
    if pov_d11:
        return "B4", (f"D11 camera_angle＝「{angle}」为严格 POV，但 D13 未声明眼位关系"
                      f"（notes：{notes[:80]}）→ 无证据不推定，不提示不阻断")
    if sep_d13:
        return "B5", (f"D11 camera_angle＝「{angle}」非 POV 声明，D13 已分离"
                      f"（notes：{notes[:80]}）→ 该镜无需改 D11，非欠账")
    if eye_d13:
        return "B6", (f"D13 notes 含眼位/视点位表述（{notes[:60]}），D11 camera_angle＝「{angle}」未用 POV 词"
                      f"（camera_angle 是俯仰/角度词表，只有「主观视角」才是 POV 标记词）"
                      f"→ 口径不对称，非缺陷")
    return "B7", (f"D11 camera_angle＝「{angle}」非 POV 声明，D13 亦未提眼位关系"
                  f"（notes：{notes[:60]}）→ 无关项")


def check_unit(project, unit):
    d11_path = os.path.join(project, "units", unit, "D11.json")
    d13_path = os.path.join(project, "units", unit, "D13.json")
    for p in (d11_path, d13_path):
        if not os.path.exists(p):
            print(f"[ABORT] 缺文件：{p}")
            return 2, None
    d11 = load(d11_path)
    d13 = load(d13_path)
    shots = d11_shots(d11)
    cmap = d13_camera_map(d13)

    checked = 0
    paired = 0
    hard = []          # (ep, shot_id, reason, detail)
    buckets = {"B1": [], "B2": [], "B3": [], "B4": [], "B5": [], "B6": [], "B7": []}

    for ep, s in shots:
        checked += 1
        sid = s.get("shot_id")
        cp = cmap.get((ep, sid))
        angle = str(s.get("camera_angle", "") or "")
        notes = str(cp.get("notes", "") or "") if cp else ""
        if cp is None:
            hard.append((ep, sid, "配对缺失",
                         f"D13 无 ep{ep}/镜{sid} 的机位（按 global_shot_no 升序配对）"))
            continue
        paired += 1
        d11_note = str(s.get("note", "") or "")
        key, detail = classify(angle, notes, d11_note)
        buckets[key].append((ep, sid, detail))

    n_miss = len([h for h in hard if h[2] == "配对缺失"])
    total_classified = sum(len(v) for v in buckets.values())

    print(f"■ 机位／视点交叉核对 · {unit}")
    print(f"  受检组数（D11 镜数）＝ {checked}｜D13 机位总数 ＝ {len(cmap)}｜配对成功 ＝ {paired}")
    print(f"  判据 A 配对完整：配对 {paired}/{checked}｜缺配对 {n_miss} 处")
    print(f"  判据 B 视点口径（按「是否已分离」语义轴）："
          f"待同步（B2）{len(buckets['B2'])} 处｜"
          f"已按裁定标注（B1）{len(buckets['B1'])} 处｜"
          f"分离前一致（B3）{len(buckets['B3'])} 处｜"
          f"已分离·非 POV（B5）{len(buckets['B5'])} 处｜"
          f"口径不对称（B6·非缺陷）{len(buckets['B6'])} 处｜"
          f"D13 未声明（B4·不判定）{len(buckets['B4'])} 处｜"
          f"无关项（B7）{len(buckets['B7'])} 处")
    print(f"  计数自证：硬失败 {len(hard)} ＋ 已分类 {total_classified} ＝ {len(hard) + total_classified}"
          f"（应 == 受检组数 {checked}）→ {'一致 ✅' if len(hard) + total_classified == checked else '不一致 ❌'}")
    for e, sid, reason, detail in hard:
        print(f"   [FAIL] ep{e} 镜{sid} · {reason}：{detail}")
    for e, sid, detail in buckets["B2"]:
        print(f"   · [待同步] ep{e} 镜{sid} · {detail}")
    for e, sid, detail in buckets["B1"]:
        print(f"   · ep{e} 镜{sid}：{detail}")
    for e, sid, detail in buckets["B3"]:
        print(f"   · ep{e} 镜{sid}：{detail}")
    for e, sid, detail in buckets["B5"]:
        print(f"   · ep{e} 镜{sid}：{detail}")
    for e, sid, detail in buckets["B6"]:
        print(f"   · [口径不对称·非缺陷] ep{e} 镜{sid} · {detail}")
    if not hard and not buckets["B2"]:
        print("  ✅ 无硬失败，且无待同步项（视点口径与白模现盘一致）")
    elif not hard:
        print(f"  ⚠️ 无硬失败，但有 {len(buckets['B2'])} 处待同步（D11 侧须按裁定改「近似 POV」）")
    return (1 if hard else 0), {
        "checked": checked, "paired": paired, "hard": hard,
        "B1": buckets["B1"], "B2": buckets["B2"], "B3": buckets["B3"],
        "B4": buckets["B4"], "B5": buckets["B5"], "B6": buckets["B6"], "B7": buckets["B7"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--unit", default="U01")
    args = ap.parse_args()
    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cands = [args.project, os.path.join(factory, args.project),
             os.path.join(os.getcwd(), args.project), os.path.abspath(args.project)]
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "units", args.unit, "D11.json")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到 units/{args.unit}/D11.json，候选：{cands}")
    rc, _ = check_unit(proj, args.unit)
    sys.exit(rc)


if __name__ == "__main__":
    main()
