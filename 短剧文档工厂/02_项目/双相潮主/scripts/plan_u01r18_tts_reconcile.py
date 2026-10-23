#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan_u01r18_tts_reconcile.py —— U01-R18 处置方案的**独立复算**（企划合规，2026-10-23 04:35）

为什么要有这份脚本
------------------
仓库里已有两份相关脚本，**判据不一致、覆盖面有缺口**，直接采信任一份都会得出不同的结论：

  ① `reconcile_tts_actual_vs_d15_budget.mjs`（分镜导演）
     - A3 重叠检查的候选集 `rows` **只含 `type === "对白"`** 的字幕行
       → **漏掉「字幕」「面板文字」「片尾」**；
     - 重叠判据用 `newOut > next.subIn`（严格大于）→ **相接（==）不算重叠**；
     - 结论「方案 A 零破口」因此**未覆盖** ep2 seq9（会压到片尾 43）与 ep8 seq8（与面板文字相接）。
  ② `apply_d15_d16_sync.py`（企划合规，轮 1）
     - 重叠预检用 `new_out >= nxt_in`（大于等于）→ **相接算重叠**，比 ① 更严。

**本脚本把两条判据统一并写死，并补齐覆盖缺口**，产出一张**可审计的逐条可行性表**，
作为 U01-R18 返修单的唯一判据来源。

【写死的判定基准】（与 Q50 一致：凡有阈值必写死基准与容差）
  预算     = D15 voice_over[].dur_sec（0.1s 标称网格）
  实测     = ffprobe format=duration（**只信实测**，不信 items.json 的 dur 缓存字段）
  归一     = ceil(actual × 10) / 10（0.1s 网格**向上**取整；浮点尾差不作不合格依据）
  破坏     = 实测标称 > 预算；贴边 = ==；合规 = <
  字幕区间 = **左闭右开 [in_sec, out_sec)** → 后一条 in_sec **严格大于**前一条 out_sec 视为不重叠；
             **相接（in == 前一条 out）不算重叠**（渲染上 A 在 out 时刻结束、B 同一时刻开始，不共帧）。
  镜窗     = D11 各镜 duration_sec 累加得到的绝对时间窗（[start, end]）
  硬切点   = D16 cuts 中 counted_in_d17_cut_count == true 的 at_sec

【为什么不采用 ① 的 `>=`（更严）而采用 `>`】
  ① 采用 `>=` 是轮 1 的**保守选择**，并非有物理依据：区间左闭右开下 `out == next.in` 不共帧渲染。
  ② 改为 `>` **不会使任何已在盘的字幕失格**：轮 1 那 11 条是按 `>=` 通过的，
     必然同时满足 `>`（`>=` 成立 ⟹ `>` 成立），故**本脚本放开的部分，磁盘上不存在违规数据**。
  ③ 统一后须写死进 D16 的 `subtitle_style.sync_rule` 文本，避免下一个读的人各判各的（Q50 同源）。

边界：只读脚本 —— **不写任何交付物**，只出报告。

用法：python3 scripts/plan_u01r18_tts_reconcile.py [--unit U01]
"""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)


def jload(p):
    with open(os.path.join(PROJ, p), "r", encoding="utf-8") as f:
        return json.load(f)


def ceil10(n):
    return math.ceil(n * 10 - 1e-9) / 10


def r1(n):
    return round(n + 0.0, 1)


def ffprobe_dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default="U01")
    args = ap.parse_args()
    u = args.unit

    d11 = jload(f"units/{u}/D11.json")
    d15 = jload(f"units/{u}/D15.json")
    d16 = jload(f"units/{u}/D16.json")
    items = jload(f"preview/{u}_tts/items.json")

    # ---- 镜位时间窗 ----
    windows = {}
    for e in d11["episodes"]:
        t = 0.0
        windows[e["ep"]] = []
        for s in e["shots"]:
            windows[e["ep"]].append({"shot_id": s["shot_id"], "start": r1(t), "end": r1(t + s["duration_sec"])})
            t += s["duration_sec"]

    def win_of(ep, sid):
        for w in windows[ep]:
            if w["shot_id"] == sid:
                return w
        return None

    # ---- 段间硬切点 ----
    hardcuts = {e["ep"]: sorted(c["at_sec"] for c in e["cuts"] if c.get("counted_in_d17_cut_count") is True)
                for e in d16["episodes"]}

    # ---- items 对白：按 (ep, text) 归一匹配 ----
    def norm(s):
        return str(s or "").replace("「", "").replace("」", "").replace("“", "").replace("”", "").strip()

    vo_by_ep = {e["ep"]: e["voice_over"] for e in d15["episodes"]}

    rows = []
    unmatched = []
    for e in d16["episodes"]:
        ep = e["ep"]
        lines = e["subtitle_style"]["lines"]
        # 正文行：排除片头/片尾/角标（标题卡与常驻角标不参与对白时序比较）
        body = sorted([l for l in lines if l.get("type") not in ("片头", "片尾", "角标")],
                      key=lambda l: float(l["in_sec"]))
        tail = [l for l in lines if l.get("type") == "片尾"]
        for sub in [l for l in lines if l.get("type") == "对白"]:
            vo = next((v for v in vo_by_ep[ep]
                       if abs(v["at_sec"] - sub["in_sec"]) < 1e-6), None)
            if vo is None:
                unmatched.append(f"ep{ep} seq{sub['seq']}（D15 无同 at_sec 配音）")
                continue
            it = next((i for i in items if i.get("kind") == "dialogue" and i.get("ep") == ep
                       and norm(i.get("text")) == norm(sub.get("text"))), None)
            if it is None:
                unmatched.append(f"ep{ep} seq{sub['seq']}「{sub.get('text')}」（items 无对应音频）")
                continue
            actual = ffprobe_dur(os.path.join(PROJ, it["audio"]))
            # 下一条正文行（in_sec 严格大于本行 in_sec）
            nxt = next((l for l in body if float(l["in_sec"]) > float(sub["in_sec"]) + 1e-9), None)
            tail_hit = next((l for l in tail if float(l["in_sec"]) > float(sub["in_sec"]) + 1e-9), None)
            rows.append({
                "ep": ep, "seq": sub["seq"], "text": sub.get("text"),
                "shot": vo.get("shot_id"), "at": float(vo["at_sec"]), "budget": float(vo["dur_sec"]),
                "sub_in": float(sub["in_sec"]), "sub_out": float(sub["out_sec"]),
                "items_dur": it.get("dur"), "actual": actual, "nom": ceil10(actual),
                "nxt_seq": nxt.get("seq") if nxt else None, "nxt_in": float(nxt["in_sec"]) if nxt else None,
                "nxt_type": nxt.get("type") if nxt else None,
                "tail_in": float(tail_hit["in_sec"]) if tail_hit else None,
            })

    if unmatched:
        print("❌ 映射未完成（不产出结论）：")
        for u_ in unmatched:
            print("   -", u_)
        sys.exit(1)

    broken = [r for r in rows if r["nom"] > r["budget"]]
    edge = [r for r in rows if abs(r["nom"] - r["budget"]) < 1e-9]
    ok = [r for r in rows if r["nom"] < r["budget"]]

    print(f"版本：D11 {d11['version']}　D15 {d15['version']}　D16 {d16['version']}")
    print(f"映射：{len(rows)} 条对白（三向：items↔D16 对白↔D15 配音）全部命中，零错位")
    print("")
    print("── 独立复算（判据见脚本头）──")
    print(f"  破坏（实测标称 > 预算）：**{len(broken)}** 条")
    print(f"  贴边（==）：{len(edge)} 条")
    print(f"  合规（<）：{len(ok)} 条")
    print(f"  items.json 的 dur 与 ffprobe 实测不一致："
          f"{sum(1 for r in rows if r['items_dur'] is not None and abs(r['items_dur'] - r['actual']) > 0.01)} 条")

    print("")
    print("── 方案 A 逐条可行性（上调 D15 dur_sec 至实测标称 ＋ 同步 D16 out_sec）──")
    print("  区间口径：[in, out) 左闭右开 → 相接（==）不算重叠；片尾标题卡单独检查")
    print("")
    hdr = ("  {:<4} {:<4} {:>6} {:>6} {:>6} {:>6}  {:<9} {:<9} {:<7} {}".format(
        "ep", "seq", "预算", "实测", "新out", "停留", "越镜窗", "跨硬切", "正文重叠", "片尾重叠"))
    print(hdr)
    print("  " + "-" * (len(hdr) + 2))

    feasible, blocked = [], []
    for r in broken:
        nb = r["nom"]
        no = r1(r["at"] + nb)
        w = win_of(r["ep"], r["shot"])
        over = no > w["end"] + 1e-9
        crossed = [c for c in hardcuts[r["ep"]] if r["at"] + 1e-9 < c < no - 1e-9]
        dwell = r1(no - r["sub_in"])
        dwell_ok = dwell >= 1.2 - 1e-9
        # 正文下一条：严格大于才算重叠
        ov_sub = (r["nxt_in"] is not None) and (no > r["nxt_in"] + 1e-9)
        touch_sub = (r["nxt_in"] is not None) and abs(no - r["nxt_in"]) < 1e-9
        # 片尾标题卡
        ov_tail = (r["tail_in"] is not None) and (no > r["tail_in"] + 1e-9)
        touch_tail = (r["tail_in"] is not None) and abs(no - r["tail_in"]) < 1e-9
        verdict = "方案A可行" if not (over or crossed or ov_sub or ov_tail or not dwell_ok) else "空间不足"
        rec = dict(r, new_budget=nb, new_out=no, dwell=dwell, over=over, crossed=crossed,
                   ov_sub=ov_sub, touch_sub=touch_sub, ov_tail=ov_tail, touch_tail=touch_tail,
                   dwell_ok=dwell_ok, win=w, verdict=verdict)
        (feasible if verdict == "方案A可行" else blocked).append(rec)
        print("  {:<4} {:<4} {:>6} {:>6} {:>6} {:>6}  {:<9} {:<9} {:<7} {}".format(
            f"ep{r['ep']}", f"seq{r['seq']}", f"{r['budget']}", f"{r['nom']}", f"{no}", f"{dwell}",
            "越窗" if over else "ok",
            ("跨" + ",".join(str(c) for c in crossed)) if crossed else "ok",
            ("重叠" if ov_sub else ("相接" if touch_sub else "ok")),
            ("重叠" if ov_tail else ("相接" if touch_tail else "ok"))))
        if not dwell_ok:
            print(f"       ⚠️ 停留 {dwell} < 1.2s")

    print("")
    print(f"── 结论：方案 A 可直接上调 **{len(feasible)}** 条；空间不足须走文案侧 **{len(blocked)}** 条 ──")
    for r in blocked:
        reasons = []
        if r["over"]:
            reasons.append(f"越镜窗（{r['win']['start']}~{r['win']['end']}）")
        if r["crossed"]:
            reasons.append(f"跨硬切点 {r['crossed']}")
        if r["ov_sub"]:
            reasons.append(f"压到下一条正文（seq{r['nxt_seq']} {r['nxt_type']} in={r['nxt_in']}）")
        if r["ov_tail"]:
            reasons.append(f"压到片尾标题卡（in={r['tail_in']}）")
        if not r["dwell_ok"]:
            reasons.append(f"停留 {r['dwell']} < 1.2s")
        need = round(r["nom"] - r["budget"], 1)
        print(f"   ep{r['ep']} seq{r['seq']}「{r['text']}」需 +{need}s"
              f"（预算 {r['budget']} → 实测标称 {r['nom']}，新出点 {r['new_out']}）→ "
              + "；".join(reasons))
    print("")
    print("── 方案 A 可行条目的新值（D15 dur_sec / D16 out_sec）──")
    for r in feasible:
        print(f"   ep{r['ep']} seq{r['seq']}「{r['text']}」：D15 dur_sec {r['budget']} → {r['new_budget']}"
              f"；D16 out_sec {r['sub_out']} → {r['new_out']}"
              f"（镜窗 {r['win']['start']}~{r['win']['end']}，停留 {r['dwell']}s）")


if __name__ == "__main__":
    main()
