#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPS-06（分镜导演岗）：D16 字幕停留口径收口 ＋ 逐集同步审计块落盘。

版本沿革
--------
- v1.4 → v1.5：口径文本收口（8 集 dwell_calc_convention 重写 ＋ 新增 subtitle_sync_audit）。
- v1.5 → v1.6：**审计块键名消歧**（`synced_with_d15_v11` 用版本样键名装行数，已被下游误读为全局陈述）
  ＋ 补 D15 v1.2 闭合戳（上游升版后复核 0 失效）。

本脚本为 D16 字幕口径与审计块的**唯一写入脚本**，幂等、名字不带版本号。

背景
----
D15 v1.1（声音设计）把 11 条贴边配音 dur_sec 由 1.2 提到 1.3；总控 OPS-05 脚本
`apply_d15_d16_sync.py` 已于 2026-10-23 02:11:56 把 D16 对应的 11 条对白字幕行 out_sec
同步 +0.1s（D16 v1.3 → v1.4）。**数值部分本脚本只校验、不改**（除非校验不过则按标称网格补齐）。

脚本遗留的三处口径失真（本次收口；全部落在 D16 自有字段内，不动任何时码）
----
1. 8 集 `dwell_calc_convention` 的「本集 1.2s 边界行 seq [...]」清单已随同步整体失效：
   ep1 seq9｜ep2 seq5｜ep3 seq7｜ep4 seq5·6·8｜ep5 seq7｜ep6 seq5｜ep7 seq5·8｜ep8 seq7
   以上 11 行已由标称 1.2s 收敛为 1.3s；全片仍为标称 1.2s 的只剩 **3 条**：
   ep2 seq8、ep4 seq7、ep8 seq9。
2. 同一句「与 D15 配音条目 dur_sec 逐条一致」对这 3 条**不成立**：它们没有 D15 配音条目
   （ep2 seq8 随钟声 sfx 出现，ep4 seq7「全区首杀」与 ep8 seq9「求救信号 城西」是画面文字），
   属越界宣称。
3. ep1 留痕段写「实算停留 <1.2 的 **8 条** voice_over 提到 1.3」，实际收敛 **11 条**
   （声音设计 §二十 的口径：判据 A 6 条 ∪ 判据 B 3 条 ＝ 7 条，另 4 条为统一化对齐，共 11 条）。

裁决（无配音锚点的 3 条 1.2s 行一律保持标称 1.2s 不动）
----
- ep2 seq8「全城钟楼敲响十一下。」（40.0→41.2）：延长到 41.3 必然与下一条对白 seq9（41.2 起音）重叠 → 不可延长。
- ep4 seq7「全区首杀」（36.2→37.4）：延长到 37.5 会与对白 seq8（37.5 起音）同刻上屏、零间隙相接 → 不可延长。
- ep8 seq9「求救信号 城西」（41.4→42.6）：虽有余量（43.0 前），但无配音锚点，分镜侧不自由裁量 → 保持不动。
- 三条同属一类、同一判据，不按集分叉。判定基准统一为 **0.1s 标称时码网格**：
  `min_dwell_sec = 1.2` 是**下限**，标称 1.2 即达标；二进制浮点表示尾差
  （如 37.4−36.2 实算 1.1999999999999957）不是时码精度问题，不构成不合格依据。
  真正的缺陷在口径文本（清单失效＋越界宣称），修文本而不是动时码。

用法
----
python3 scripts/patch_D16_v15_dwell_convention.py --project 02_项目/双相潮主 --unit U01 [--dry-run]

性质
----
幂等：重复执行不产生二次 diff。带命中数断言与**结构差异白名单**，对不上即中止不写盘。
只改 D16.json：`version` ＋ 8 集 `subtitle_style.dwell_calc_convention` ＋ 新增 `subtitle_style.subtitle_sync_audit`。
不动任何 in_sec／out_sec（除校验不过时按标称网格补齐）、不动 cuts／transitions／title_card／paywall_point。

边界
----
只出文档。不生成图片/视频/音频，不提交 H3 付费生成，不投流上架。
"""
import argparse
import json
import os
import sys

EPS = 1e-9
P = "短剧文档工厂/02_项目/双相潮主"

# ---- 已由 OPS-05 落盘的 11 条同步行：(ep, seq) → 期望标称停留 ----
SYNCED = {
    (1, 9): 1.3, (2, 5): 1.3, (3, 7): 1.3, (4, 5): 1.3, (4, 6): 1.3, (4, 8): 1.3,
    (5, 7): 1.3, (6, 5): 1.3, (7, 5): 1.3, (7, 8): 1.3, (8, 7): 1.3,
}

# ---- 无 D15 配音锚点、保持标称 1.2s 不动的 3 条 ----
NO_VO_12 = {
    (2, 8): "字幕行「全城钟楼敲响十一下。」，随 D15 ep002 钟声 sfx（at 40.0）出现，无独立配音条目；"
            "延长至 41.3 必然与下一条对白 seq9（41.2 起音）重叠，故不可延长。",
    (4, 7): "面板文字「全区首杀」（D11 ep4 镜4 通报条自面板底部滚出），属画面文字、无配音条目；"
            "延长至 37.5 会与对白 seq8（37.5 起音）同刻上屏、零间隙相接，故不可延长。",
    (8, 9): "面板文字「求救信号 城西」（D11 ep8 镜4 面板底部浮出求救信号条），属画面文字、无配音条目；"
            "虽有余量（片尾 43.0 前），但无配音锚点，分镜侧不自由裁量，故保持标称 1.2s。",
}

# ---- 浮点尾差证据行（非 1.2 边界，但足以证明严格位相等会误报）----
FLOAT_EVIDENCE = {(1, 8): "31.4＋1.3", (5, 6): "17.4＋2.2"}

HEADER = ("停留按标称时码计（in_sec/out_sec 均为 0.1s 精度时间码），标称 ≥1.2s 即合规；"
          "二进制浮点表示尾差（如 37.4−36.2 实算 1.1999999999999957）不是时码精度问题，"
          "不构成不合格依据，判定基准一律取 0.1s 标称网格。")


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def round1(x):
    return round(float(x) + 0.0, 1)


def collect_diff(a, b, path=""):
    """递归比对两个 JSON 结构，返回差异路径列表（a→b）。"""
    out = []
    if type(a) is not type(b):
        return [path + " <类型变化>"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k} <新增>")
            elif k not in b:
                out.append(f"{path}.{k} <删除>")
            else:
                out += collect_diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path} <长度 {len(a)}→{len(b)}>")
        for i, (x, y) in enumerate(zip(a, b)):
            out += collect_diff(x, y, f"{path}[{i}]")
    else:
        if a != b:
            out.append(path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unit = args.unit
    # 候选路径择优：取第一个真正含 units/<unit>/D16.json 的目录，避免相对路径拼接歧义
    cands = []
    if os.path.isabs(args.project):
        cands.append(args.project)
    else:
        cands.append(os.path.join(factory, args.project))
        cands.append(os.path.join(os.getcwd(), args.project))
        cands.append(os.path.abspath(args.project))
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "units", unit, "D16.json")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到含 units/{unit}/D16.json 的项目目录，候选：{cands}")

    p16 = os.path.join(proj, "units", unit, "D16.json")
    p15 = os.path.join(proj, "units", unit, "D15.json")
    p07 = os.path.join(proj, "units", unit, "D07.json")
    for p in (p16, p15, p07):
        if not os.path.isfile(p):
            sys.exit(f"[ABORT] 文件不存在：{p}")

    d16 = load(p16)
    d15 = load(p15)
    d07 = load(p07)

    # ---------- D15 配音索引 (ep, at) ----------
    vo = {}
    for ep in d15.get("episodes", []):
        for it in ep.get("voice_over", []):
            vo[(ep["ep"], round1(it["at_sec"]))] = it

    # ---------- D07 段窗口（字幕不得越出所属段/镜位时窗）----------
    seg = {}
    for ep in d07.get("episodes", []):
        seg[ep["ep"]] = [(float(s["start_sec"] if "start_sec" in s else s["start"]),
                          float(s["end_sec"] if "end_sec" in s else s["end"]))
                         for s in ep.get("quad_segments", [])]

    # ── 幂等守卫：一次性脚本，只在 v1.4~v1.6 上执行 ──
    # 2026-10-23 补：本脚本整块重写 dwell_calc_convention 与 subtitle_sync_audit、
    # 且 version 硬写 v1.6 → 在更新的版本上重跑会回退（已回退过一次：并行实例 v1.7 的
    # verified_against_d15=v1.3 等字段曾被它写回 v1.2）。故加版本守卫：已演进 → no-op。
    if d16.get("version") not in ("v1.4", "v1.5", "v1.6"):
        print(f"[NO-OP] D16 当前 version={d16.get('version')}（∉ v1.4~v1.6）："
              f"本脚本为一次性 v1.4→v1.5→v1.6 口径收口脚本，已演进则不写盘（防整块回退）。")
        return

    before = load(p16)
    fixed_times = []
    verified = []
    audit = {}
    problems = []

    for e in d16["episodes"]:
        ep = e["ep"]
        ss = e["subtitle_style"]
        lines = ss["lines"]
        rows = []

        for ln in lines:
            seq = ln["seq"]
            i, o = float(ln["in_sec"]), float(ln["out_sec"])
            nominal = round(round1(o) - round1(i), 1)
            f_dwell = o - i
            v = vo.get((ep, round1(i)))
            vd = float(v["dur_sec"]) if v else None

            # 1) 11 条同步行：校验 out_sec == in_sec + 期望停留（标称网格）；不符则补齐
            if (ep, seq) in SYNCED:
                want = SYNCED[(ep, seq)]
                if v is None:
                    problems.append(f"ep{ep} seq{seq}: D15 无 at_sec={round1(i)} 的配音条目，无法核对")
                elif abs(vd - want) > EPS:
                    problems.append(f"ep{ep} seq{seq}: D15 配音 dur_sec={vd} ≠ 期望 {want}")
                if abs(nominal - want) > EPS:
                    ln["out_sec"] = round1(i + want)
                    fixed_times.append((ep, seq, o, ln["out_sec"]))
                    nominal = want
                    f_dwell = float(ln["out_sec"]) - float(ln["in_sec"])
                else:
                    verified.append((ep, seq, nominal))
                rows.append({
                    "seq": seq, "type": ln["type"], "in_sec": round1(i), "out_sec": round1(o),
                    "nominal_dwell_sec": nominal, "float_dwell_sec": f_dwell,
                    "d15_vo_at_sec": round1(i), "d15_vo_dur_sec": vd,
                    "action": "已随 D15 v1.1 同步 +0.1s（out_sec ＝ 配音 at_sec＋dur_sec）",
                    "verdict": "合规",
                })

            # 2) 3 条无配音锚点的 1.2s 行：断言停留为标称 1.2 且确无配音对应
            if (ep, seq) in NO_VO_12:
                if abs(nominal - 1.2) > EPS:
                    problems.append(f"ep{ep} seq{seq}: 标称停留 {nominal} ≠ 1.2，需人工确认")
                if v is not None:
                    problems.append(f"ep{ep} seq{seq}: 存在 D15 配音条目 at={round1(i)}，"
                                    f"与「无配音锚点」前提冲突")
                rows.append({
                    "seq": seq, "type": ln["type"], "in_sec": round1(i), "out_sec": round1(o),
                    "nominal_dwell_sec": nominal, "float_dwell_sec": f_dwell,
                    "d15_vo_at_sec": None, "d15_vo_dur_sec": None,
                    "action": "保持不动（无 D15 配音锚点，分镜侧不自由裁量）",
                    "verdict": "合规（标称 1.2s ＝ min_dwell_sec 下限，浮点尾差不判不合格）",
                    "note": NO_VO_12[(ep, seq)],
                })

            # 3) 浮点尾差证据行
            if (ep, seq) in FLOAT_EVIDENCE:
                rows.append({
                    "seq": seq, "type": ln["type"], "in_sec": round1(i), "out_sec": round1(o),
                    "nominal_dwell_sec": nominal, "float_dwell_sec": f_dwell,
                    "d15_vo_at_sec": round1(i), "d15_vo_dur_sec": vd,
                    "action": "不动",
                    "verdict": "合规（标称网格与 D15 配音逐条一致；浮点尾差仅存在于二进制表示）",
                    "note": f"尾差实证：{FLOAT_EVIDENCE[(ep, seq)]} 实算 ≠ 标称值，"
                            f"任何按浮点位相等写法的自动校验都会误报，故判定一律走标称网格。",
                })

        # ---- 硬校验 A：正文行标称停留 ≥ 1.2（片头/片尾/角标除外）----
        for ln in lines:
            if ln["type"] in ("片头", "片尾", "角标"):
                continue
            if round1(ln["out_sec"]) - round1(ln["in_sec"]) < 1.2 - EPS:
                problems.append(f"ep{ep} seq{ln['seq']}: 标称停留 "
                                f"{round1(ln['out_sec']) - round1(ln['in_sec'])} < 1.2")

        # ---- 硬校验 B：正文行两两不重叠 ----
        body = sorted([l for l in lines if l["type"] not in ("片头", "片尾", "角标")],
                      key=lambda l: round1(l["in_sec"]))
        for a, b in zip(body, body[1:]):
            if round1(a["out_sec"]) > round1(b["in_sec"]) + EPS:
                problems.append(f"ep{ep}: seq{a['seq']} out={a['out_sec']} 与 seq{b['seq']} "
                                f"in={b['in_sec']} 重叠")

        # ---- 硬校验 C：正文行不越出所属段（D07 quad_segments）----
        for ln in lines:
            if ln["type"] in ("片头", "片尾", "角标"):
                continue
            ok = any(w[0] - EPS <= round1(ln["in_sec"]) and round1(ln["out_sec"]) <= w[1] + EPS
                     for w in seg.get(ep, []))
            if not ok:
                problems.append(f"ep{ep} seq{ln['seq']}: [{ln['in_sec']},{ln['out_sec']}] "
                                f"越出 D07 段窗口 {seg.get(ep)}")

        # ---- 硬校验 D：有配音锚点的对白行 out_sec ＝ 配音 at_sec＋dur_sec（标称网格）----
        for ln in lines:
            if ln["type"] not in ("对白", "字幕"):
                continue
            v = vo.get((ep, round1(ln["in_sec"])))
            if v is None:
                continue
            want = round1(round1(ln["in_sec"]) + float(v["dur_sec"]))
            if abs(round1(ln["out_sec"]) - want) > EPS:
                problems.append(f"ep{ep} seq{ln['seq']}: out_sec={ln['out_sec']} ≠ "
                                f"配音 at_sec＋dur_sec = {want}")

        rows.sort(key=lambda r: r["seq"])
        audit[ep] = rows

    if problems:
        print("[ABORT] 校验不通过，不写盘：")
        for p in problems:
            print("   -", p)
        sys.exit(1)

    if len(verified) + len(fixed_times) != len(SYNCED):
        sys.exit(f"[ABORT] 同步行命中 {len(verified) + len(fixed_times)} 条，"
                 f"少于期望 {len(SYNCED)} 条；不写盘。")

    # ---------- 改写 8 集 dwell_calc_convention + 写入审计块 ----------
    for e in d16["episodes"]:
        ep = e["ep"]
        ss = e["subtitle_style"]
        rows = audit[ep]
        synced_rows = [r for r in rows if r["seq"] in [s for (a, s) in SYNCED if a == ep]]
        resid = [r for r in rows if (ep, r["seq"]) in NO_VO_12]
        ev = [r for r in rows if (ep, r["seq"]) in FLOAT_EVIDENCE]

        parts = [HEADER]
        if synced_rows:
            parts.append("本集与 D15 配音逐条对应的字幕行：seq "
                         + "、".join(str(r["seq"]) for r in synced_rows)
                         + "，out_sec ＝ 配音 at_sec＋dur_sec，已随 D15 v1.1 的 dur_sec 收敛同步。")
        else:
            parts.append("本集无随 D15 v1.1 同步的字幕行。")
        if resid:
            glob = "／".join(f"ep{a} seq{b}" for (a, b) in sorted(NO_VO_12))
            parts.append("本集标称恰 1.2s 的行：seq "
                         + "、".join(str(r["seq"]) for r in resid)
                         + "——"
                         + "；".join(f"seq{r['seq']}（{r['type']}）：{r['note'].rstrip('。')}"
                                     for r in resid)
                         + f"。（全片此类共 {len(NO_VO_12)} 条：{glob}，同属一类、同一判据，"
                           "均保持标称 1.2s 不动。）")
        else:
            parts.append("本集无标称 1.2s 的行（正文行全部 ≥1.3s）。")
        if ev:
            parts.append("浮点尾差证据行：seq "
                         + "、".join(str(r["seq"]) for r in ev)
                         + "，标称网格下与 D15 配音逐条一致，实算尾差不作判定依据。")
        parts.append(
            "【2026-10-23 同步留痕】D15 v1.1 已把 11 条贴边配音 dur_sec 由 1.2 提到 1.3（判据 A 6 条 ∪ "
            "判据 B 3 条 ＝ 7 条，另 4 条统一化对齐），对应的 11 条对白字幕行 out_sec 已同步 +0.1s，"
            "由总控 OPS-05 脚本 apply_d15_d16_sync.py 落盘（2026-10-23 02:11:56，D16 v1.3→v1.4），"
            "分镜导演逐条复核 11 条与 D15 配音 at_sec＋dur_sec 一致；无配音锚点的 3 条标称 1.2s 行保持不动；"
            "本表口径文本由 OPS-06 脚本 patch_D16_dwell_convention.py 收口（D16 v1.4→v1.5→v1.6），"
            "明细见 subtitle_sync_audit。"
            "【上游闭合戳】D15 已升至 v1.2，仅改口径文本、时长数据与 v1.1 逐字节一致，"
            "故本留痕的 v1.1 事件溯源仍成立，11 行同步结论经重跑零失效。")

        ss["dwell_calc_convention"] = "".join(parts)
        ss["subtitle_sync_audit"] = {
            "synced_row_count": len(synced_rows),
            "no_vo_anchor_rows": len(resid),
            "sync_basis": ("D15 v1.1 贴边配音收敛（dur_sec 1.2→1.3，共 11 条，分布见各集 synced_row_count；"
                           "其中 ep1 seq8 本就是 1.3、不属本轮收敛，故落盘态 dur_sec==1.3 实测 12 条）。"
                           "本字段是**事件溯源陈述**，不是活链接 —— 改名成活链接会丢失「哪一版收敛」的溯源，"
                           "且 D15 每升一版都要改 8 集、漏一处即分叉。"),
            "verified_against_d15": "v1.2",
            "verified_note": ("本次复核所依据的 D15 版本（数值必须带版本号，判据同 D18 Q39）。"
                              "D15 v1.2 仅改口径文本，voice_over/sfx/foley/bgm_curve 与 v1.1 逐字节一致，"
                              "故 v1.1 事件溯源仍成立、11 行同步结论零失效。"),
            "rows": rows,
        }

    d16["version"] = "v1.6"

    # ---------- 结构差异白名单 ----------
    diffs = collect_diff(before, d16)
    allowed = []
    for d in diffs:
        if d == ".version" or d.endswith(".dwell_calc_convention") or ".subtitle_sync_audit" in d:
            allowed.append(d)
        else:
            print(f"[ABORT] 越界改动：{d}")
            sys.exit(1)
    print(f"[DIFF] 改动 {len(diffs)} 处（白名单内 {len(allowed)} 处）：")
    for d in allowed:
        print("   -", d)

    print(f"[CHECK] 11 条同步行复核通过 {len(verified) + len(fixed_times)} 条"
          + (f"，其中本脚本补齐 {len(fixed_times)} 条：{fixed_times}" if fixed_times else "，无需补齐"))
    print(f"[CHECK] 无配音锚点行 {sum(1 for k in NO_VO_12)} 条，全部保持标称 1.2s")
    print("[CHECK] 停留下限 / 不重叠 / 不越段 / 配音同步 四项硬校验全部通过")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    dump(p16, d16)
    print(f"[DONE] D16 → {d16['version']} 已落盘：{p16}")


if __name__ == "__main__":
    main()
