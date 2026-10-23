#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D13 ↔ 白模层 落位一致性审计（只读审计脚本，不写任何盘）

目的：落实三条归口纪律第 ③ 条 —— ⛔ D14 白模侧不得单独挪主体（D11↔D14 分叉）。
      故须逐条比对：D13 登记的 position_m 与白模层实际落位是否一致，
      并把每一处分歧归类为「白模层单方面偏移」或「D13 未约束字段的白模层解释」。

────────────────────────────────────────────────────────────────────────────
【v1.1 · 2026-10-23 判据修复】同名多实例消歧 + 授权门（见下「修复要点」）

修复要点（缺陷编号与总控派单一致）：
  缺陷①（主）**同名多实例未用 `props[].shots` 消歧**
     旧版按 `prop["name"]` 匹配 PROP_POS/PROP_ANIM 键，把一条 (scene,gsn,name)
     覆盖拿去和该场**每一个**同名实例各比一次 ⇒ 凭空造出 12.33 m 级假偏移。
     真实白模侧 `build_white_model.py:388-391` 是**先按 `props[].shots` 过滤**
     （该镜没有的实例根本不建），`:236` 才把覆盖套上去 ⇒
     **落位模型必须与白模侧同源**：只有该镜**在场**的实例才可能被覆盖命中。
     现按 (scene_code, gsn) → `props[].shots` 逐实例比对，跨场同名天然隔离
     （键含 scene_code），同场同名由 shots 唯一化。

  缺陷②（主）**D 类判据恒被触发，失去鉴别力**
     D13 的 `props[].position_m` 是**该道具的锚点**（一个道具一个），
     而 D13 用 `props[].state`/`props[].note` 登记**逐镜状态**（一镜一条）——
     D13 的 schema **没有**逐镜坐标字段 ⇒ 剧情驱动的逐镜换位**只能**由白模层承载。
     旧判据把「D13 已登记该镜状态、白模层据此实现」也判成「白模层单方面挪主体」
     ⇒ 该检查在任何正确产物上都必然变红（U02 现盘 13/13 全触发）＝恒真闸。
     现加**授权门**：该镜的逐镜状态已在 D13 `state`/`note` 登记 ⇒ 判为
     **D2 ◐ 登记债务**（非阻断；坐标待按第②档回填 D13）；
     D13 **未**登记该镜状态却仍被白模层挪动 ⇒ **D1 ⛔ 白模层单方面挪主体**。

  缺陷③ B 类是**永不报警的死检查**
     `build_white_model.py:235` 的 GEOM 锚点恒取 D13 `position_m`，
     `GEOM_OVERRIDE` 只改尺寸/count/spread ⇒ 「GEOM 锚点被改写」永不可能发生。
     保留为护栏，但结论口径须写明：白模层无独立锚点源。

  缺陷④ 静默跳过：旧版对「白模层未建模」的道具 `continue`，
     连同它的 PROP_POS/PROP_ANIM 检查一起跳过 ⇒ 无声失败。现记为 ❓ 待人工确认。

  缺陷⑤ C2 的 ±0.5 m 容差对巨型体块恒真（围墙 X −22..14 / Y −15..24 等）
     ⇒ 登记点几乎必然落在其中，C2 对这类道具失去鉴别力。保留但标注体块跨度。

  新增 ❓ 待人工确认类（不计违规、不静默）：
     D3  PROP_POS 悬空覆盖（该镜无同名实例 ⇒ 白模层不会应用它）
     X1  同场同名 MULTI 实例必然重叠（parts 坐标烧死在内容模块）
     X2  同一镜内多个同名实例被同一条 PROP_POS 覆盖到同一点 ⇒ 必然重叠

判据分级（severity）：
  ok        A / F / C2 / E2 —— 锚点一致或 D13 未约束
  debt      D2 —— D13 已登记该镜逐镜状态，白模层据 D11/D13 实现；坐标待回填 D13
  review    D3 / X1 / X2 / ? —— 结构歧义，需人工确认（**不判违规**）
  violation D1 / B / C / E1 —— 白模层单方面挪主体（阻断）

用法：
    python3 scripts/audit_D13_white_model_alignment_U02.py
    python3 scripts/audit_D13_white_model_alignment_U02.py --project . --unit U02
    python3 scripts/audit_D13_white_model_alignment_U02.py --project . --unit U02 --json
退出码：0 = 无 violation（review 项会打印 ⚠ 但不阻断）；1 = 有 violation。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROJECT = os.path.dirname(HERE)

SEV_ORDER = {"violation": 0, "review": 1, "debt": 2, "ok": 3}


# ---------------------------------------------------------------- 载入
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_wm(project: str, unit: str):
    """载入白模内容模块（几何表/位置表/复合结构/动画表）。"""
    path = os.path.join(project, "scripts", f"white_model_content_{unit}.py")
    if not os.path.isfile(path):
        raise SystemExit(f"❌ 找不到白模内容模块：{path}")
    wm = load_module(f"white_model_content_{unit}", path)
    return {
        "GEOM": getattr(wm, "GEOM", {}) or {},
        "GEOM_OVERRIDE": getattr(wm, "GEOM_OVERRIDE", {}) or {},
        "MULTI": getattr(wm, "MULTI", {}) or {},
        "PROP_POS": getattr(wm, "PROP_POS", {}) or {},
        "PROP_ANIM": getattr(wm, "PROP_ANIM", {}) or {},
    }


def load_d11(project: str, unit: str):
    """D11 逐镜事实（仅作 D2 行的交叉佐证显示；判定本身不依赖 D11）。"""
    path = os.path.join(project, "units", unit, "D11.json")
    if not os.path.isfile(path):
        return {}
    try:
        d11 = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for ep in d11.get("episodes", []) or []:
        for sh in ep.get("shots", []) or []:
            out[sh.get("global_shot_no")] = sh
    return out


# ---------------------------------------------------------------- 白模侧同源查找
def geom_for(wm, sc_code, name):
    """镜像 build_white_model.py:139 `geom_for`。"""
    return wm["GEOM_OVERRIDE"].get((sc_code, name)) or wm["GEOM"].get(name)


def multi_for(wm, sc_code, name):
    """镜像 build_white_model.py:143 `multi_for`。"""
    return wm["MULTI"].get((sc_code, name)) or wm["MULTI"].get(name)


def prop_in_shot(prop, gsn):
    """该 D13 道具实例是否**在场**于该镜。

    镜像 build_white_model.py:389-391：
        prop_shots = prop.get("shots")
        if prop_shots is not None and gsn not in prop_shots:
            continue
    ⇒ `shots` 缺省 = 该场全程在场；否则仅在列出的镜号在场。
    """
    shots = prop.get("shots")
    return shots is None or gsn in shots


def d13_shot_state(prop, gsn):
    """D13 是否为该道具登记了**该镜**的逐镜状态。

    真源 = `props[].state` + `props[].note`（D13 的逐镜状态登记位）。
    D13 的 `position_m` 是单锚点、无逐镜坐标字段 ⇒ 逐镜状态只能落在 state/note。
    返回 (bool, 证据串)。
    """
    token = f"镜{gsn}"
    for field in ("state", "note"):
        txt = prop.get(field) or ""
        if token in txt:
            return True, f"D13.{field} 含『{token}』"
    return False, "D13.state/note 未登记该镜逐镜状态"


# ---------------------------------------------------------------- 审计主体
def audit(project: str, unit: str):
    d13_path = os.path.join(project, "units", unit, "D13.json")
    if not os.path.isfile(d13_path):
        raise SystemExit(f"❌ 找不到 {d13_path}")
    d13 = json.load(open(d13_path, encoding="utf-8"))
    wm = load_wm(project, unit)
    d11 = load_d11(project, unit)

    rows = []
    counts = {"A": 0, "B": 0, "C": 0, "C2": 0, "D1": 0, "D2": 0, "D3": 0,
              "E1": 0, "E2": 0, "F": 0, "X1": 0, "X2": 0, "?": 0}

    def add(cls, sev, sc, name, gsn, d13_pos, wm_pos, note):
        counts[cls] = counts.get(cls, 0) + 1
        rows.append({
            "class": cls, "severity": sev, "scene": sc, "prop": name,
            "gsn": gsn, "d13_pos": d13_pos, "wm_pos": wm_pos, "note": note,
        })

    prop_pos_keys = set(wm["PROP_POS"].keys())
    prop_anim_keys = set(wm["PROP_ANIM"].keys())

    for sc in d13["scenes"]:
        sc_code = sc["scene_code"]
        props = sc.get("props", []) or []
        gsns = sorted(cp["global_shot_no"] for cp in sc.get("camera_positions", []) or [])
        gsn_set = set(gsns)

        # ---------- 场景级：锚点类（A/B/C/C2/F）与同场同名结构风险（X1） ----------
        from collections import Counter
        name_cnt = Counter(p["name"] for p in props)
        for p in props:
            name = p["name"]
            d13_pos = list(p["position_m"])

            # 同场同名 MULTI 实例 ⇒ parts 坐标烧死 ⇒ 必然重叠（❓ X1）
            if name_cnt[name] > 1 and multi_for(wm, sc_code, name) is not None:
                add("X1", "review", sc_code, name, None, d13_pos, None,
                    f"同场同名 MULTI 实例 ×{name_cnt[name]}：parts 坐标烧死在内容模块 ⇒ 必然重叠")

            # --- C/C2/A：MULTI parts 锚点 ---
            m = multi_for(wm, sc_code, name)
            if m is not None:
                parts = m["parts"]
                pminx = min(loc[0] for _, _, loc, _ in parts)
                pmaxx = max(loc[0] for _, _, loc, _ in parts)
                pminy = min(loc[1] for _, _, loc, _ in parts)
                pmaxy = max(loc[1] for _, _, loc, _ in parts)
                exact = any(abs(loc[0] - d13_pos[0]) < 1e-6 and abs(loc[1] - d13_pos[1]) < 1e-6
                            for _, _, loc, _ in parts)
                covered = (pminx - 0.5 <= d13_pos[0] <= pmaxx + 0.5
                           and pminy - 0.5 <= d13_pos[1] <= pmaxy + 0.5)
                span = max(pmaxx - pminx, pmaxy - pminy)
                if exact:
                    add("A", "ok", sc_code, name, None, d13_pos, None,
                        "MULTI 存在与 D13 登记点重合的体块 ⇒ 锚点一致")
                elif covered:
                    add("C2", "ok", sc_code, name, None, d13_pos, None,
                        f"一个登记道具的多体块结构表达（体块 X {pminx:.2f}..{pmaxx:.2f} / "
                        f"Y {pminy:.2f}..{pmaxy:.2f}，跨度 {span:.1f}m，登记点落在结构范围内）"
                        f"⇒ 非挪主体" + ("　⚠ 体块跨度大 ⇒ 本条鉴别力弱" if span > 20 else ""))
                else:
                    add("C", "violation", sc_code, name, None, d13_pos, None,
                        f"⛔ 整体挪位：登记点不在体块结构范围内"
                        f"（体块 X {pminx:.2f}..{pmaxx:.2f} / Y {pminy:.2f}..{pmaxy:.2f}）")
                continue

            # --- B/A/F：GEOM 锚点 ---
            g = geom_for(wm, sc_code, name)
            if g is None:
                # 缺陷④：旧版此处 continue，会连同该道具的 PROP_POS/PROP_ANIM 检查一起跳过
                add("?", "review", sc_code, name, None, d13_pos, None,
                    "白模层无 GEOM/MULTI 定义（未建模）⇒ 其逐镜覆盖无从核对"
                    "（旧版在此 continue，会静默跳过该道具的 D/E 检查）")
                continue
            spread = (g[6] or {}).get("spread")
            step = (g[6] or {}).get("step")
            if spread == "x":
                add("F", "ok", sc_code, name, None, d13_pos, None,
                    f"沿 X 展开 step={step}；实例#1 锚点=D13 登记点，实例#2 位置 D13 未约束")
            elif spread == "y":
                add("F", "ok", sc_code, name, None, d13_pos, None,
                    f"沿 Y 展开 step={step}；实例#1 锚点=D13 登记点，实例#2 位置 D13 未约束")
            elif spread in ("z", "x_center", "y_center", "queue", "explicit"):
                add("F", "ok", sc_code, name, None, d13_pos, None,
                    f"展开方式 {spread}；D13 未约束实例分布")
            else:
                add("A", "ok", sc_code, name, None, d13_pos, None,
                    "GEOM 单实例锚点 = D13 登记点（白模层 GEOM 锚点恒取 D13 position_m）")

        # ---------- 逐镜级：落位类（D1/D2/D3/E1/E2/X2） ----------
        for gsn in gsns:
            present = [p for p in props if prop_in_shot(p, gsn)]

            # D3：PROP_POS 悬空覆盖（该镜无同名实例 ⇒ 白模层不会应用）
            names_present = {p["name"] for p in present}
            for (k_sc, k_gsn, k_name) in prop_pos_keys:
                if k_sc == sc_code and k_gsn == gsn and k_name not in names_present:
                    add("D3", "review", sc_code, k_name, gsn, None,
                        tuple(wm["PROP_POS"][(k_sc, k_gsn, k_name)]),
                        "❓ PROP_POS 悬空覆盖：该镜无同名实例在场 ⇒ 白模层不会应用它"
                        "（须人工确认是键写错还是道具该镜不该在场）")

            # X2：同一镜内多个同名实例被同一条 PROP_POS 覆盖到同一点
            for name in sorted(names_present):
                same = [p for p in present if p["name"] == name]
                if len(same) > 1 and (sc_code, gsn, name) in prop_pos_keys:
                    add("X2", "review", sc_code, name, gsn, None,
                        tuple(wm["PROP_POS"][(sc_code, gsn, name)]),
                        f"❓ 同镜 {len(same)} 个同名实例被同一条 PROP_POS 覆盖到同一点 ⇒ 必然重叠")

            for p in present:
                name = p["name"]
                d13_pos = list(p["position_m"])

                # --- D：PROP_POS 逐镜覆盖（白模侧 :236/:237） ---
                k = (sc_code, gsn, name)
                if k in prop_pos_keys:
                    o = list(wm["PROP_POS"][k])
                    dx = round(o[0] - d13_pos[0], 4)
                    dy = round(o[1] - d13_pos[1], 4)
                    dz = round(o[2] - d13_pos[2], 4)
                    if abs(dx) < 1e-6 and abs(dy) < 1e-6 and abs(dz) < 1e-6:
                        add("A", "ok", sc_code, name, gsn, d13_pos, tuple(o),
                            "PROP_POS 覆盖值 == D13 登记点（无效应覆盖）")
                        continue
                    ok_state, evidence = d13_shot_state(p, gsn)
                    if ok_state:
                        d11ev = ""
                        sh = d11.get(gsn)
                        if sh:
                            vf = (sh.get("visual_facts") or "").replace("\n", " ")
                            d11ev = f"　｜D11: {vf[:96]}"
                        add("D2", "debt", sc_code, name, gsn, d13_pos, tuple(o),
                            f"◐ D13 已登记该镜逐镜状态（{evidence}）⇒ 白模层据 D11/D13 实现，"
                            f"非「单方面挪主体」；坐标待按第②档回填 D13"
                            f"（dx={dx} dy={dy} dz={dz}）{d11ev}")
                    else:
                        add("D1", "violation", sc_code, name, gsn, d13_pos, tuple(o),
                            f"⛔ 白模层单方面挪主体：{evidence}，"
                            f"但白模层把该道具移到别处（dx={dx} dy={dy} dz={dz}）"
                            f"⇒ 须回 D13 登记该镜落位，或把白模层改回 D13 驱动")

                # --- E：PROP_ANIM 起点（白模侧 :619/:625，作用于该镜**在场**的每个同名实例） ---
                ka = (sc_code, gsn, name)
                if ka in prop_anim_keys:
                    seq = wm["PROP_ANIM"][ka]
                    first = seq[0]
                    dx, dy, dz = first[1], first[2], first[3]
                    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                        add("E1", "violation", sc_code, name, gsn, d13_pos, (dx, dy, dz),
                            f"⛔ PROP_ANIM 起点偏离 D13 登记点 dx={dx} dy={dy}")
                    else:
                        add("E2", "ok", sc_code, name, gsn, d13_pos, (dx, dy, dz),
                            "PROP_ANIM 起点锚在 D13 登记点（仅 Z 抬升/缩放）")

    rows.sort(key=lambda r: (SEV_ORDER.get(r["severity"], 9),
                              r["scene"], r["gsn"] if r["gsn"] is not None else 0,
                              r["prop"]))
    return rows, counts


# ---------------------------------------------------------------- 输出
def print_report(rows, counts, unit):
    print("=" * 108)
    print(f"D13 ↔ 白模层 落位一致性审计 · {unit}（只读）")
    print("=" * 108)
    hdr = (f'{"类":<4} {"严重度":<10} {"场景":<6} {"镜":<5} {"道具":<16} '
           f'{"D13 position_m":<22} {"白模落位":<22} 说明')
    print(hdr)
    print("-" * 108)
    sev_cn = {"violation": "⛔违规", "review": "❓待确认", "debt": "◐登记债务", "ok": "ok"}
    for r in rows:
        gsn = "-" if r["gsn"] is None else str(r["gsn"])
        print(f'{r["class"]:<4} {sev_cn[r["severity"]]:<10} {r["scene"]:<6} {gsn:<5} '
              f'{r["prop"]:<16} {str(r["d13_pos"]):<22} {str(r["wm_pos"]):<22} {r["note"]}')

    print("-" * 108)
    print(f"A  锚点一致（白模层未偏移）        : {counts['A']}")
    print(f"B  GEOM 锚点被白模层改写           : {counts['B']}   "
          f"（注：白模层 GEOM 锚点恒取 D13 position_m ⇒ 本类为死检查/护栏）")
    print(f"C  MULTI 整体挪位（违规）          : {counts['C']}")
    print(f"C2 MULTI 结构表达（非挪主体）      : {counts['C2']}")
    print(f"D1 PROP_POS 逐镜覆盖·未获 D13 登记 : {counts['D1']}   ⛔ 违规")
    print(f"D2 PROP_POS 逐镜覆盖·D13 已登记    : {counts['D2']}   ◐ 登记债务（非阻断）")
    print(f"D3 PROP_POS 悬空覆盖              : {counts['D3']}   ❓ 待人工确认")
    print(f"E1 PROP_ANIM 起点致偏移            : {counts['E1']}   ⛔ 违规")
    print(f"E2 PROP_ANIM 起点锚定              : {counts['E2']}")
    print(f"F  D13 未约束字段的白模层解释       : {counts['F']}")
    print(f"X1 同场同名 MULTI 实例重叠风险      : {counts['X1']}   ❓ 待人工确认")
    print(f"X2 同镜多实例被同一覆盖            : {counts['X2']}   ❓ 待人工确认")
    print(f"?  白模层未建模（检查被跳过）       : {counts['?']}   ❓ 待人工确认")
    viol = counts["B"] + counts["C"] + counts["D1"] + counts["E1"]
    review = counts["D3"] + counts["X1"] + counts["X2"] + counts["?"]
    debt = counts["D2"]
    print("-" * 108)
    print(f"⛔ 违规（白模层单方面挪主体）：{viol} 条")
    print(f"◐ 登记债务（D13 已授权的逐镜覆盖，坐标待回填 D13）：{debt} 条")
    print(f"❓ 待人工确认（结构歧义，不判违规）：{review} 条")
    if viol:
        print("   ⇒ 须按三条归口纪律第 ② 档改 D13 登记，或把白模层改回 D13 驱动。")
    else:
        print("   ⇒ 无白模层单方面偏移。")
    if debt:
        print(f"   ⇒ D2 {debt} 条为**登记债务**：白模层按 D11/D13 逐镜状态实现，"
              f"但 D13 的 position_m 只有单锚点、无逐镜坐标字段 ⇒ 坐标待按第②档回填。")
    if review:
        print(f"   ⇒ ❓ {review} 条须人工确认（旧判据会把其中一部分误判为违规）。")
    return viol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=DEFAULT_PROJECT,
                    help="项目根（含 units/ 与 scripts/）；默认取本脚本上级目录")
    ap.add_argument("--unit", default="U02")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    rows, counts = audit(project, args.unit)
    viol = counts["B"] + counts["C"] + counts["D1"] + counts["E1"]

    if args.json:
        print(json.dumps({
            "unit": args.unit,
            "counts": counts,
            "violations": viol,
            "findings": rows,
        }, ensure_ascii=False, indent=1))
    else:
        viol = print_report(rows, counts, args.unit)
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main())
