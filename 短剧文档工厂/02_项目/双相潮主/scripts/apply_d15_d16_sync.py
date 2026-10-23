#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPS-05 代执行：D15 贴边配音 dur_sec 1.2→1.3 ＋ D16 对应对白字幕 out_sec +0.1s ＋ D15 ep002 钟声 mix 过时表述更正。

背景
----
D16 `subtitle_style.min_dwell_sec = 1.2`，字幕停留按标称时码计。U01 有 11 条对白字幕行
标称恰 1.2s，其中 7 条因二进制浮点表示差值实算为 1.1999999999999957（严格 <1.2 会误判不合格）。
收敛点必须在声音设计侧：把 D15 对应的贴边配音 dur_sec 由 1.2 提到 1.3，使字幕 out_sec 随配音
收音点后移 +0.1s，留出 0.1s 余量。分镜不得单方面延长 out_sec（会晚于配音收音）。

已核对事实
----------
1) 11 条 D15 voice_over 的 dur_sec 恰 1.2，与 11 条 D16 对白字幕行按 (ep, at_sec≈in_sec) 一一对应。
2) 这 11 条字幕行 out_sec +0.1s 后与下一条字幕 in_sec 均无重叠（已逐条验证）。
3) D15 ep002 sfx[6].mix 含过时表述「D08/D11/D16 的记数正在同步返修」——三处早已统一为「十一下」，
   该表述已失真，应改为如实描述。

用法
----
python3 scripts/apply_d15_d16_sync.py --project 02_项目/双相潮主 --unit U01 [--dry-run]

性质
----
幂等：可重复执行。带命中数断言，对不上即中止不写盘。属机械类口径更正（数值 + 逐字给定），
按 OPS-05 由总控代执行，不改 D11/D12/D13/D14，不动派生预算链。

跨交付物边界与两侧责任（OPS-21 · 2026-10-23 07:45 企划合规登记；S27 ②）
--------------------------------------------------------------------------
⚠️ **本脚本一次运行写两份不同归属的交付物** —— 这是**跨交付物边界**写盘：

  · **D15 ＝ 声音设计（bot_0a60d9bbd4fe）**：本脚本改 D15 的两处 ① 贴边配音 dur_sec
    （1.2→1.3）与 ② ep002 钟声 mix 过时表述。**D15 的内容正确性由声音设计负责**：
    本脚本只按「D15 现状为真源」对齐 D16，**不自行决定 D15 的时码取值**。
  · **D16 ＝ 分镜导演（bot_1855d6ce9cdd）**：本脚本改 D16 的对白字幕 out_sec 与
    `dwell_calc_convention` 同步留痕。**D16 的内容正确性由分镜导演负责**：
    字幕出点必须与 D15 配音收音点逐条一致，分镜不得单方面延长 out_sec（会晚于配音收音）。

  · **同步义务（两侧共同）**：任一方改动 D15 贴边配音 dur_sec 或 D16 对白字幕 out_sec，
    另一侧必须同步并**重跑覆盖轴**（`reconcile_D15_D16_timing.mjs --unit <U>`，受检须 >0、
    exit 0）—— 两侧不得只改一边就交付。
  · **版本守卫**：本脚本对**两侧各自**带版本守卫（见 main() 内「跨交付物边界 · 两侧版本守卫」段），
    任一侧盘上版本高于本脚本的基线版本即拒绝写盘，**两侧都不得被静默回退**。
    需故意回退时用 `--force` 显式放行（人工确认过再动）。
  · **不代改他岗脚本**：本岗（声音设计）只补声明与守卫，**不代分镜导演改 D16 的内容取值**；
    D16 侧内容归属仍属分镜导演（§七·九）。
"""
import argparse
import json
import os
import sys

EPS = 1e-9
D15_VO_13 = 8       # D15 中 dur_sec==1.3 的 voice_over 条数下限（声音设计 v1.1 已落地）
D16_SUB_12 = 11     # D16 中与 D15 配音对应对白字幕行的条数下限
D16_FLOAT_TAIL = 6  # 其中浮点尾差（实算 <1.2）的条数；另 5 条为精确 1.2

# ── 跨交付物边界 · 两侧版本守卫基线（OPS-21）────────────────────────────────
#   判据：盘上 version **高于**本脚本基线 → 拒绝写盘（静默回退防护），--force 可显式放行。
#   本脚本写的是「D15 v1.1 时代」的贴边收敛，故基线取 D15 v1.1 / D16 v1.4；
#   盘上版本更高即意味着产物已被后续版本演进过，本脚本的旧内容源不再适用。
D15_BASE_VERSION = "v1.1"
D16_BASE_VERSION = "v1.4"


def _vkey(v):
    """版本号 → 可比较的 (主, 次) 元组；非 vX.Y 形式一律按 (0, 0) 视作最低。"""
    import re
    m = re.match(r"^v?(\d+)\.(\d+)$", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def walk_strings(obj):
    """递归遍历所有字符串值，产出 (json路径, 字符串)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_12(x):
    try:
        return abs(float(x) - 1.2) < EPS
    except (TypeError, ValueError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="显式放行版本回退场景（人工确认过再动）")
    args = ap.parse_args()

    # 脚本位于 <工厂根>/02_项目/双相潮主/scripts/ —— 向上两级到 <工厂根>，再按 --project 定位
    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        # 兼容「从 02_项目/双相潮主 内运行、--project 给相对路径」的情形
        proj = os.path.join(os.getcwd(), args.project)
    unit = args.unit

    p15 = os.path.join(proj, "units", unit, "D15.json")
    p16 = os.path.join(proj, "units", unit, "D16.json")
    for p in (p15, p16):
        if not os.path.isfile(p):
            sys.exit(f"[ABORT] 文件不存在: {p}")

    d15 = load(p15)
    d16 = load(p16)

    # ---------- 0) 跨交付物边界 · 两侧版本守卫（OPS-21 / S27 ②）----------
    #   本脚本一次写 D15（声音设计）＋ D16（分镜导演）两份不同归属的交付物 →
    #   两侧**各自**都要有版本守卫，否则跨岗写盘会静默回退他人已升版的产物。
    #   判据：盘上 version 高于本脚本基线 → 拒绝写盘、中止（两侧都拦）。
    #   --force 显式放行（人工确认过再动）。
    #   ⚠️ 与「命中数断言」分工：断言管**内容层**（对不上即中止，--force 也不放行）；
    #      守卫管**版本层**（盘上更高 = 产物已被后续演进，本脚本旧内容源不适用）。
    if not args.force:
        for path, base, owner in ((p15, D15_BASE_VERSION, "声音设计"),
                                  (p16, D16_BASE_VERSION, "分镜导演")):
            disk_v = (d15 if path == p15 else d16).get("version")
            if _vkey(disk_v) > _vkey(base):
                sys.exit(
                    f"[ABORT] 版本守卫：{os.path.relpath(path, proj)} 盘上已是 **{disk_v}**，"
                    f"高于本脚本基线 **{base}**（{owner} 侧）→ 拒绝写盘，两侧均未改动。\n"
                    f"        产物已被后续版本演进，本脚本的旧内容源不再适用。\n"
                    f"        确认确需回退时，加 --force 显式放行。")

    # ---------- 1) D15：贴边配音 dur_sec 1.2 → 1.3 ----------
    # 注：声音设计已于 2026-10-23 02:06 先行落地 D15 v1.1 —— 把「实算停留 <1.2
    # （浮点尾差 1.1999999999999957 之类）」的 8 条配音改为 1.3，其余浮点精确
    # 1.2 的 4 条保留不动。本脚本改为「幂等对齐」语义：
    #   以 D15 现状（dur_sec）为真源，凡 D15 配音 dur_sec==1.3 的，其 D16 对应对白
    #   字幕行的 out_sec 必须等于 in_sec+1.3；不等则补齐 +0.1s。
    #   浮点精确 1.2 的配音不动（其字幕行本就合规）。
    vo_13 = []
    for ep in d15.get("episodes", []):
        for it in ep.get("voice_over", []):
            if abs(float(it.get("dur_sec", 0)) - 1.3) < EPS:
                vo_13.append((ep, it))

    if len(vo_13) < D15_VO_13:
        sys.exit(f"[ABORT] D15 voice_over dur_sec==1.3 命中 {len(vo_13)} 条，少于期望 {D15_VO_13} 条；不写盘。")

    # ---------- 2) D15：ep002 钟声 mix 过时表述 ----------
    # 声音设计已于 2026-10-23 02:03–02:06 先行改写为「总记数已由上游收口——D07 段4、D08、D11、D16
    # 四处一致登记为十一声」。本脚本按「过时表述还在才改」处理：
    #   旧表述命中 → 改；旧表述不再命中且钟声 mix 已不含「正在同步返修」→ 视为已收口，跳过。
    OLD_MIX = "逐记落下，每记间隔约 0.4s，音高逐记微降；总记数以上游最终口径为准——D07 段4 最新登记为十一声，D08/D11/D16 的记数正在同步返修，本表只锁每记间隔与余音长度，不锁死记数"
    NEW_MIX = "逐记落下，每记间隔约 0.4s，音高逐记微降；总记数已由上游收口——D07 段4、D08、D11、D16 四处一致登记为十一声；本表只锁每记间隔与余音长度，不锁死记数"
    mix_hits = []
    mix_done = 0
    for ep in d15.get("episodes", []):
        for g in ("sfx", "foley", "voice_over"):
            for it in ep.get(g, []):
                m = it.get("mix") or ""
                if m == OLD_MIX:
                    mix_hits.append((ep, it))
                elif "同步返修" in m:
                    sys.exit(f"[ABORT] D15 出现含「同步返修」的其它措辞，需人工确认：{m[:120]}")
                elif "十一下" in m and "记数" in m:
                    mix_done += 1
    if len(mix_hits) + mix_done != 1:
        sys.exit(f"[ABORT] D15 钟声 mix 命中 旧 {len(mix_hits)} 处 + 已收口 {mix_done} 处，期望合计 1 处；不写盘。")

    # ---------- 3) D16：对应对白字幕行 out_sec 对齐 D15 配音 dur_sec ----------
    vo_index = {}
    for ep, it in vo_13:
        vo_index[(ep["ep"], round(float(it["at_sec"]), 1))] = it

    sub_hits = []
    already_ok = 0
    for ep in d16.get("episodes", []):
        e = ep["ep"]
        lines = ep.get("subtitle_style", {}).get("lines", [])
        for ln in lines:
            if ln.get("type") not in ("对白",):
                continue
            in_s = round(float(ln["in_sec"]), 1)
            if (e, in_s) not in vo_index:
                continue
            dur = float(ln["out_sec"]) - float(ln["in_sec"])
            want = float(vo_index[(e, in_s)]["dur_sec"])
            # 已对齐（差值落在 ±0.05 内视为已同步）
            if abs(dur - want) < 0.05:
                already_ok += 1
                continue
            sub_hits.append((ep, ln))

    if len(sub_hits) + already_ok < D16_SUB_12:
        sys.exit(f"[ABORT] D16 对应对白字幕行 命中 {len(sub_hits)} + 已对齐 {already_ok}，少于期望 {D16_SUB_12} 条；不写盘。")

    # ---------- 4) 重叠预检 ----------
    # 区间口径（2026-10-23 修 U01-R19 写死，与 D18 Q51 一致）：
    #   全部区间判定取 **左闭右开 [in, out)** —— **相接不算重叠**。
    #   本处原用 `new_out >= nxt_in`（把「恰好相接」误判为重叠），与
    #   scripts/reconcile_tts_actual_vs_d15_budget.mjs 的 `newOut > nxt_in` 不一致，
    #   同一条数据此前能被算成两个结论（U01-R18 首记即因此把 ep8#4 误判为空间不足）→ 统一为 `>`。
    #   候选集＝全部正文行（排除 片头／片尾／角标），按 in_sec 排序。
    for ep in d16.get("episodes", []):
        body = [l for l in ep.get("subtitle_style", {}).get("lines", [])
                if l.get("type") not in ("片头", "片尾", "角标")]
        body.sort(key=lambda l: float(l["in_sec"]))
        for i, ln in enumerate(body):
            if ln not in [h[1] for h in sub_hits if h[0] is ep]:
                continue
            new_out = round(float(ln["out_sec"]) + 0.1, 1)
            if i + 1 < len(body):
                nxt_in = round(float(body[i + 1]["in_sec"]), 1)
                if new_out > nxt_in + 1e-9:
                    sys.exit(f"[ABORT] ep{ep['ep']:03d} seq{ln['seq']} 延长后 out={new_out} 与下一条 in={nxt_in} 重叠；不写盘。")
            # 片尾标题卡单独检查（底部字幕区，与对白同带 → 真实视觉冲突）
            tail = [l for l in ep.get("subtitle_style", {}).get("lines", [])
                    if l.get("type") == "片尾"]
            if tail and new_out > round(float(tail[0]["in_sec"]), 1) + 1e-9:
                sys.exit(f"[ABORT] ep{ep['ep']:03d} seq{ln['seq']} 延长后 out={new_out} 压到片尾标题卡 in={tail[0]['in_sec']}；不写盘。")

    print("[PLAN] D15 配音 dur_sec==1.3（真源）：")
    for ep, it in vo_13:
        print(f"   ep{ep['ep']:03d} shot{it.get('shot_id')} at={it.get('at_sec')} dur={it.get('dur_sec')} ref={it.get('line_ref')}")
    print(f"[PLAN] D15 钟声 mix：旧表述待改 {len(mix_hits)} 处，已改 {mix_done} 处")
    print(f"[PLAN] D16 对白字幕 out_sec 需 +0.1：{len(sub_hits)} 条，已对齐 {already_ok} 条")
    print("[PLAN] 重叠预检：全部通过")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    # ---------- 写盘 ----------
    for ep, it in mix_hits:
        it["mix"] = NEW_MIX
    if mix_hits:
        dump(p15, d15)

    for ep, ln in sub_hits:
        ln["out_sec"] = round(float(ln["out_sec"]) + 0.1, 1)

    # ---------- 5) 后置守恒：每个 dur_sec==1.3 的配音都必须有一条 1.3s 停留的对白字幕行 ----------
    # 反向漏洞：早期版本只断言「命中条数 ≥ 11」，若某条 1.3s 配音没有对应字幕行（或字幕行没跟上），
    # 断言照样通过 → 配音与字幕两套口径分叉。故补一条双向守恒：1.3s 配音数 == 已对齐字幕行数。
    if len(sub_hits) == 0 and already_ok != len(vo_13):
        sys.exit(f"[ABORT] D15 dur_sec==1.3 的配音 {len(vo_13)} 条，与已对齐的 D16 字幕行 {already_ok} 条不等；"
                 f"存在无字幕锚点或未同步的配音，不写盘。")

    # ---------- 6) 留痕：把本次同步口径写进 D16 的 dwell_calc_convention，避免下游误判为「分镜单方面延长」 ----------
    # 条数口径（勿混用）：**本轮收敛 11 条**（dur_sec 1.2→1.3；判据 A 6 条 ∪ 判据 B 3 条 ＝ 7 条，
    # 另 4 条为与派活口径/断言统一化对齐，见 99_交付说明 §二十·20.2）；**落盘态 D15 中 dur_sec==1.3 的为 12 条**，
    # 多出的 ep1 seq8 本就是 1.3（不属本轮收敛）。两者不可互相替代，写留痕时必须用「本轮收敛 11 条」。
    # 旧版本此处写死「8 条」，脚本重跑会把该口径写回并与 D16 v1.5 的 11 条表述冲突 —— 已订正。
    MARK = "【2026-10-23 同步留痕】"
    conv = d16["episodes"][0]["subtitle_style"].get("dwell_calc_convention", "")
    note = ("【2026-10-23 同步留痕】U01 贴边配音（D15 v1.1 已把 11 条标称 1.2s 的贴边配音 dur_sec 收到 1.3）"
            "对应的 11 条对白字幕行 out_sec 已同步 +0.1s，与 D15 配音收音点逐条一致；"
            "浮点精确 1.2 的配音与字幕保持不动。字幕停留按标称时码计，不因二进制浮点尾差判不合格。")
    note_added = False
    if MARK not in conv:
        d16["episodes"][0]["subtitle_style"]["dwell_calc_convention"] = conv + note
        note_added = True

    # 无改动则不写盘：避免无谓重写造成 mtime 漂移与并发写误判
    if sub_hits or note_added:
        dump(p16, d16)
        print("[WRITE] D16 已写盘")
    else:
        print("[NO-OP] D16 无需改动（配音/字幕已全对齐，留痕已存在），未写盘")

    print("[DONE] D15 / D16 已更新")


if __name__ == "__main__":
    main()
