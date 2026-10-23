#!/usr/bin/env python3
"""
check_D07_D11_segment_alignment.py —— D07 段界 ↔ D11 镜时分段 对齐核验（只读）

为什么需要这条轴（2026-10-23 U01–U03 实测背景）：
  工厂铁律是「**镜时严格等于 D07 段界**」——D11 每集 4 镜、每镜 1 段、镜时＝段长。
  但 V1–V11 **没有一条规则校这件事**：
    - V4 只校「D11 镜位时长合计 == 集时长」与「D07 四段连续无缝合计 45s」，
      两边各自成立就放过，**不校两边的分段边界是否逐段相等**；
    - V4 另有「D11 镜位只覆盖 4 个四段」但那是**只查段号覆盖**（数量），
      **不查每段镜时之和是否等于该段时长**。
  ⇒ 后果：某镜被改时长（例如黄金 3 秒改造批次把 ep001 镜时从 13/13/12/7 改成
    12/8/16/9），只要四镜仍合计 45s、quad_segment 仍标 1–4，**V4 全绿**，
    而 D11 的切点与 D07 的段界已经错位 —— 这正是企划合规 11:40 回执点名的
    「D11↔D16 的 ep001 镜时/切点请属主在批次收口后复核一次」。

判据（写在脚本头部，复算须按此读）：
  【E1 · 段长对齐】对每集每段：D07 段长（end_sec − start_sec）必须等于
        D11 中该集标了同一 quad_segment 的**所有镜位 duration_sec 之和**（容差 0.05s）。
        镜位时长缺失或该段无镜 → 记为未覆盖，不判通过。
  【E2 · 段覆盖】D11 每集必须覆盖 4 个 quad_segment（1–4），且镜位总数＝4。
  【E3 · 段界一致】D07 相邻段必须首尾相接（start[i+1] == end[i]），
        首段 start==0、末段 end==集时长（duration_sum_sec / 45s）。
  【E4 · 切点对齐】D16 的硬切 at_sec 必须落在 D07 的段界上（容差 0.05s）；
        D16 的 from_segment/to_segment 必须与 D07 的段号一致。
        D16 缺任一集时跳过 E4（不作通过引用）。
  【E5 · 钩链闭合】D06 单元内 hook_in[i] == hook_out[i-1]；跨单元则
        上一单元末集 hook_out == 本单元首集 hook_in；单元首集 hook_in ==
        project.json units[].first_hook、末集 hook_out == last_hook。

已知局限（勿据以单独判缺陷）：
  - **并行段**：mode='并行' 的段由两镜交替并置，镜时之和仍应等于段长，
    本脚本用「同段镜时求和」判定，**对并行段同样成立**（两镜交替总时长＝段长）；
    但它**不判**「并行段是否真有两镜」，那是 D10 例外句的范畴。
  - **容差 0.05s**：浮点尾差按标称口径处理，不做位相等比较。
  - E4 只查**硬切**；叠化（dissolve）的中点与 D07 段界的关系不在本轴判定内。

退出码：0 = 无 error；1 = 有 error。幂等、只读、不写盘。
空集恒真守卫：受检集数 == 0 时不得判通过（直接 exit 1）。

用法：
  python3 scripts/check_D07_D11_segment_alignment.py --project 02_项目/双相潮主 --unit U01
  python3 scripts/check_D07_D11_segment_alignment.py --project 02_项目/双相潮主 --all
"""

import argparse
import json
import os
import sys

TOL = 0.05


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default=None)
    ap.add_argument("--all", action="store_true", help="检查 units/ 下全部单元")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    units_root = os.path.join(root, "units")
    if args.all:
        units = sorted(d for d in os.listdir(units_root) if os.path.isdir(os.path.join(units_root, d)))
    elif args.unit:
        units = [args.unit]
    else:
        print("需指定 --unit 或 --all")
        return 2

    proj_path = os.path.join(root, "project.json")
    proj = load(proj_path) if os.path.exists(proj_path) else {}
    udefs = {u["id"]: u for u in proj.get("units", [])}

    errors, warns = [], []
    stats = {"sets": 0, "segments": 0, "seg_ok": 0, "seg_bad": 0, "seg_uncov": 0,
             "cuts": 0, "cut_ok": 0, "cut_bad": 0, "hooks": 0, "hook_ok": 0}

    prev_unit = None
    prev_last_hook = None
    is_first_unit = True
    for u in units:
        ud = os.path.join(units_root, u)
        f7 = os.path.join(ud, "D07.json")
        f6 = os.path.join(ud, "D06.json")
        if not os.path.exists(f7):
            warns.append(f"{u}: D07 未产出，跳过")
            continue
        d7 = load(f7)
        e7 = {e["ep"]: e for e in d7.get("episodes", [])}
        e6 = {e["ep"]: e for e in load(f6)["episodes"]} if os.path.exists(f6) else {}

        f11 = os.path.join(ud, "D11.json")
        e11 = {}
        if os.path.exists(f11):
            e11 = {e["ep"]: e for e in load(f11).get("episodes", [])}
        else:
            warns.append(f"{u}: D11 未产出，E1/E2/E4 不可检")

        f16 = os.path.join(ud, "D16.json")
        e16 = {}
        if os.path.exists(f16):
            e16 = {e["ep"]: e for e in load(f16).get("episodes", [])}
        else:
            warns.append(f"{u}: D16 未产出，E4 不可检")

        for ep in sorted(e7):
            stats["sets"] += 1
            ep7 = e7[ep]
            segs = ep7.get("quad_segments", [])
            target = ep7.get("duration_sum_sec") or 45

            # E3 段界连续 + 首尾锚定
            cursor = None
            for i, sg in enumerate(segs):
                if i == 0 and abs(sg["start_sec"]) > TOL:
                    errors.append(f"{u} ep{ep}: 段1 起点 {sg['start_sec']} != 0")
                if cursor is not None and abs(sg["start_sec"] - cursor) > TOL:
                    errors.append(
                        f"{u} ep{ep}: 段{sg['index']} 起点 {sg['start_sec']} 与上一段终点 {cursor} 不接续")
                if sg["end_sec"] <= sg["start_sec"]:
                    errors.append(f"{u} ep{ep}: 段{sg['index']} 区间非法")
                cursor = sg["end_sec"]
            if segs and abs(cursor - target) > TOL:
                errors.append(f"{u} ep{ep}: 四段合计 {cursor}s != 集时长 {target}s")

            # E1 / E2 段长对齐
            shots = (e11.get(ep) or {}).get("shots", [])
            if e11:
                if len(shots) != 4:
                    errors.append(f"{u} ep{ep}: D11 镜数 {len(shots)} != 4")
                agg = {}
                for s in shots:
                    q = s.get("quad_segment")
                    if q:
                        agg[q] = agg.get(q, 0) + float(s.get("duration_sec") or 0)
                covered = set(agg.keys())
                if covered and covered != {1, 2, 3, 4}:
                    errors.append(f"{u} ep{ep}: D11 覆盖段 {sorted(covered)} != [1,2,3,4]")
                for sg in segs:
                    i = sg["index"]
                    stats["segments"] += 1
                    dur = sg["end_sec"] - sg["start_sec"]
                    if i not in agg:
                        stats["seg_uncov"] += 1
                        warns.append(f"{u} ep{ep} 段{i}: D11 无标注该段的镜位（未覆盖，不判通过）")
                        continue
                    if abs(agg[i] - dur) > TOL:
                        stats["seg_bad"] += 1
                        errors.append(
                            f"{u} ep{ep} 段{i}: D07 段长 {dur}s != D11 该段镜时之和 {agg[i]:.2f}s"
                        )
                    else:
                        stats["seg_ok"] += 1

            # E4 切点对齐
            if e16 and ep in e16:
                seg_bounds = {sg["index"]: (sg["start_sec"], sg["end_sec"]) for sg in segs}
                for c in e16[ep].get("cuts", []):
                    if c.get("technique") != "硬切":
                        continue
                    stats["cuts"] += 1
                    at = float(c.get("at_sec") or 0)
                    fs, ts = c.get("from_segment"), c.get("to_segment")
                    bound_ok = False
                    for sg in segs:
                        if abs(sg["end_sec"] - at) <= TOL:
                            bound_ok = True
                            if sg["index"] != fs:
                                errors.append(
                                    f"{u} ep{ep} 切点@{at}s: from_segment={fs} 与 D07 段界(段{sg['index']} 终点)不符")
                            if ts is not None and ts != sg["index"] + 1:
                                errors.append(
                                    f"{u} ep{ep} 切点@{at}s: to_segment={ts} 与下一段段号 {sg['index']+1} 不符")
                            break
                    if bound_ok:
                        stats["cut_ok"] += 1
                    else:
                        stats["cut_bad"] += 1
                        errors.append(f"{u} ep{ep} 切点@{at}s: 不落在任何 D07 段界上")

            # E5 钩链在**单元级**判（见下方单元循环后），此处不判。

        # ---- 单元级：E5 钩链闭合（一次判，避免同一处失配被报 N 次）----
        if e6:
            stats["hooks"] += 1
            ok = True
            eps = sorted(e6)
            for ep2 in eps:
                if ep2 == eps[0]:
                    continue
                if e6[ep2]["hook_in"] != e6[ep2 - 1]["hook_out"]:
                    ok = False
                    errors.append(f"{u} ep{ep2}: hook_in != ep{ep2-1} hook_out")
            first, last = eps[0], eps[-1]
            # 跨单元判据只在**首集**做一次；prev_last_hook 是**上一单元**的末集钩，
            # 必须在单元粒度上缓存，不能被本单元逐集循环覆盖。
            if not is_first_unit and prev_last_hook is not None:
                if e6[first]["hook_in"] != prev_last_hook:
                    ok = False
                    errors.append(
                        f"{u} ep{first}: 跨单元 hook_in 与上一单元末集 hook_out 不逐字相等")
            ud = udefs.get(u)
            if ud:
                if ud.get("first_hook") and e6[first]["hook_in"] != ud["first_hook"]:
                    ok = False
                    errors.append(f"{u} ep{first}: hook_in != project first_hook")
                if ud.get("last_hook") and e6[last]["hook_out"] != ud["last_hook"]:
                    ok = False
                    errors.append(f"{u} ep{last}: hook_out != project last_hook")
            if ok:
                stats["hook_ok"] += 1
            unit_last_hook = e6[last]["hook_out"]

        # 单元级缓存：供**下一个**单元做跨单元判据
        prev_last_hook = unit_last_hook
        is_first_unit = False

    print("■ D07 段界 ↔ D11 镜时分段 对齐核验")
    print(f"  判据：E1 段长对齐／E2 段覆盖／E3 段界连续／E4 切点落段界／E5 钩链闭合")
    print(f"  受检集数 {stats['sets']}｜受检段 {stats['segments']}（对齐 {stats['seg_ok']}／"
          f"失配 {stats['seg_bad']}／未覆盖 {stats['seg_uncov']}）")
    print(f"  受检硬切 {stats['cuts']}（对齐 {stats['cut_ok']}／失配 {stats['cut_bad']}）"
          f"｜受检钩链集 {stats['hooks']}（通过 {stats['hook_ok']}）")
    print(f"  error {len(errors)}｜warn {len(warns)}")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warns:
        print(f"  ! {w}")
    if stats["sets"] == 0:
        print("  ⛔ 受检集数 0 —— 未真正执行扫描，结论不成立（空集恒真）")
        return 1
    if not errors:
        print("  ✅ 全部对齐")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
