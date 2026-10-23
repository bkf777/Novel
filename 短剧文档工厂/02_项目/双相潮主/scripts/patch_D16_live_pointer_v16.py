#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜导演岗：D16「活戳」刷新 —— D15 U01 现行版本 v1.4 → v1.6。

派活来源
--------
声音设计（@声音设计）追加派活（接 task_80f96d3b8320）：把 D16 中指向 D15 的「活戳」
更新到当前 D15 版本 —— U02 侧 52 处目标由 v1.1 改为 v1.2；U01 侧目标为 v1.6。

认盘结论（2026-10-23）
----------------------
- **U02 侧 52 处已由并行实例落好**（`scripts/build_D16_U02.py` 于 07:49:50 落 D16 v1.5）：
  `D15 U02 v1.2` 44 命中、`D15 U02 v1.0` 0 命中、`D15 U02 v1.1` 0 命中。
  → 本脚本**不碰 U02**，避免重复记账。
- **U01 侧实测仍指 v1.4**（非派活前提所说的「仍指 v1.6 不变」）：磁盘实况优先于转述。
  D15 U01 现行版本为 **v1.6**（声音设计 `build_D15_U01.py` 06:08:13 落盘），
  故 U01 侧活戳目标版本 = v1.6，本脚本执行刷新。

本脚本只改「活戳」（当前有效性指针），只追加不改「事件溯源」
----------------------------------------------------------------
| 字段 | 性质 | 本轮处理 |
|---|---|---|
| `subtitle_sync_audit.verified_against_d15` | 活链接（当前复核所依据的 D15 版本） | 改 v1.4 → v1.6（8 集） |
| `subtitle_sync_audit.verified_note` 末句 | 活链接（待复核 → 已复核） | 改并追加 v1.6 复算证据段（8 集） |
| `subtitle_style.dwell_calc_convention` 终表段 | 活链接 | 改 v1.4 → v1.6（ep1/2/3/5/8，5 集） |
| `subtitle_style.dwell_calc_convention` 非终表集 | 活链接（现值为 / 现行为） | 改 v1.4 → v1.6（ep4/6/7，3 集 × 2 处） |
| `subtitle_sync_audit.sync_basis` | **事件溯源**（哪一版收敛） | 不动 |
| `subtitle_sync_audit.sync_records[*].basis` | **事件溯源**（S11 只追加不覆盖） | 不动，旧条目原文保留 |
| `dwell_calc_convention`【上游闭合戳】段、「D16 v1.3→v1.4」 | **事件溯源** | 不动 |
| `verified_note` 中段「D15 v1.3 × D16 v1.6 × D11 v1.6 复算」 | **事件溯源** | 不动 |

活戳改动合计 **27 处**：8（verified_against_d15）＋ 8（verified_note 末句）＋ 5（终表段）＋ 6（非终表集 ×2）。
派活文按字段类型计为「21 处」＝ 8＋8＋5，未计入非终表集 3 集的 2 处 `**v1.4**` 活链接 —— 本脚本补齐差额。

数值零改动
----------
本轮**不动任何 in_sec／out_sec／dur_sec／cuts／transitions／title_card／paywall_point**。
证据（D15 U01 v1.6 × D16 v1.10 × D11 v1.8 现盘复算）：
  ① U01-R18 终表 9 条 dur_sec 与 D15 U01 v1.6 现盘逐条比对 9/9 一致；
  ② 28 条对白字幕 out_sec ＝ 配音 at_sec＋dur_sec 逐条严格相等，0 条不符；
  ③ 配音 28 ＋ sfx/foley 80 共 108 对象 0 越出本镜时间窗 / 0 跨段间硬切点；
  ④ 字幕 75 行 0 越窗 / 0 跨切点 / 0 重叠；
  → `node scripts/reconcile_D15_D16_timing.mjs --unit U01` → **exit 0**。
上游声明（声音设计 build_D15_U01.py 变更说明：v1.5／v1.6「均只改口径文本，时长数据与 v1.4 逐字节一致」）
**仅作转述**：本岗无 D15 U01 v1.4 备份可比对（全树检索无、git 从未追踪 units/），
故本岗结论只限于「D16 现盘数值对 D15 v1.6 全部成立」，不越界声称「v1.4 与 v1.6 逐字节一致」。

用法
----
python3 scripts/patch_D16_live_pointer_v16.py --project 02_项目/双相潮主 --unit U01 [--dry-run]

性质
----
一次性活戳刷新脚本，**幂等**（重复执行不再产生二次 diff）。
守卫：① D16 version 锚定 v1.10（已演进 → `[NO-OP]` exit 0，绝不写盘）；
      ② D15 version 必须为 v1.6（否则 `[NO-OP]` exit 0 —— 目标版本已变，本脚本失效）；
      ③ 内容态幂等（8 集 verified_against_d15 已是 v1.6 → `[NO-OP]` exit 0）。
命中断言：每处替换的命中数必须**精确等于**预期值，对不上即 `[ABORT]` exit 1 不写盘。
结构差异白名单：只允许 `.version` 与 `.episodes[*].subtitle_style.{dwell_calc_convention,
subtitle_sync_audit.*}` 变动，越界即 `[ABORT]` exit 1 不写盘。

边界
----
只出文档。不生成图片/视频/音频，不提交 H3 付费生成，不投流上架。
只改 units/U01/D16.json；不碰 D11／D15／他岗交付物／D18／项目索引。
"""
import argparse
import json
import os
import shutil
import sys
import time

# ---- 目标版本锚定 ----
D16_FROM = "v1.10"
D16_TO = "v1.11"
D15_TARGET = "v1.6"

# ---- 精确替换锚点（原 → 新）；每条附预期命中数 ----
# (标签, 字段路径类别, 旧串, 新串, 预期命中数)
EDITS = [
    ("verified_against_d15",
     "verified_against_d15",
     "v1.4（终表口径；D15 v1.4 落盘后复核）",
     "v1.6（终表口径；D15 v1.6 落盘后复核）",
     8),
    ("verified_note末句",
     "verified_note",
     "D15 v1.4 落盘后须复核 9 行逐条一致。",
     "D15 v1.6 落盘后已复核 9 行逐条一致（9/9 一致）。",
     8),
    ("dwell终表段",
     "dwell_calc_convention",
     "out_sec ＝ 配音 at_sec＋新 dur_sec，D15 v1.4 落盘后复核）",
     "out_sec ＝ 配音 at_sec＋新 dur_sec，D15 v1.6 落盘后复核）",
     5),
    ("dwell非终表集·现值",
     "dwell_calc_convention",
     "现值仍为 D15 **v1.4** 现行预算",
     "现值仍为 D15 **v1.6** 现行预算",
     3),
    ("dwell非终表集·现行为",
     "dwell_calc_convention",
     "D15 现行为 **v1.4**",
     "D15 现行为 **v1.6**",
     3),
]

# ---- 追加到 verified_note 末尾的证据段（8 集通用）----
APPEND_NOTE = (
    "｜2026-10-23 D15 v1.6 活戳刷新（声音设计 D15 U02 v1.2 落盘后的活戳同步派活）："
    "本岗**现盘直接复算**（不依赖上游声明）："
    "① U01-R18 终表 9 条 dur_sec 与 D15 U01 v1.6 现盘逐条比对 9/9 一致；"
    "② 28 条对白字幕 out_sec ＝ 配音 at_sec＋dur_sec 逐条严格相等，0 条不符；"
    "③ 配音 28 ＋ sfx/foley 80 共 108 对象 0 越出本镜时间窗 / 0 跨段间硬切点"
    "（11 条 D16 明文预铺位属设计豁免）；"
    "④ 字幕 75 行 0 越窗 / 0 跨切点 / 0 重叠"
    "（scripts/reconcile_D15_D16_timing.mjs --unit U01 → exit 0）。"
    "→ D16 v1.10 现盘数值对 D15 v1.6 全部成立，活戳由 v1.4 刷新为 v1.6。"
    "上游声明转述（非本岗独立实测）：声音设计在 build_D15_U01.py 变更说明中称 v1.5／v1.6"
    "「均只改口径文本，时长数据与 v1.4 逐字节一致」——本岗**无 D15 U01 v1.4 备份可比对**"
    "（全树检索无、git 从未追踪 units/），故该条仅作转述，本岗结论限于「D16 现盘数值对 D15 v1.6 全部成立」。"
    "余量三口径现值：口径1 镜尾余量 **0.6s**（ep1 镜1，10.4＋2.0＝12.4，镜窗 0~13）／"
    "口径2 起音间隙 0.5s（ep7 镜4）／口径3 镜首余量 0.5s（ep7 镜4）；"
    "上文「余量三口径 1.0s（ep1 镜1）」为 D15 v1.3 时点的历史留痕"
    "（当时 ep1 镜1 配音 dur 1.6 → 12.0 → 镜尾余量 1.0s），"
    "D15 v1.4 起该行预算上调为 2.0，余量收窄为 0.6s，按 S11 原文保留、不改写。"
)

# ---- 追加到 sync_records 的新条目（S11 只追加，不改旧条目）----
SYNC_RECORD = {
    "date": "2026-10-23",
    "event": "D15 U01 活戳刷新 v1.4 → v1.6",
    "basis": "声音设计 D15 U02 v1.2 落盘（2026-10-23 07:45:45）后的活戳同步派活"
             "（接 task_80f96d3b8320）；U01 侧活戳原指 v1.4，按当前 D15 U01 v1.6 刷新。"
             "U02 侧 52 处已由并行实例 scripts/build_D16_U02.py 于 07:49:50 落好，本岗不重复记账。",
    "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
    "changes": [
        "verified_against_d15：v1.4 → v1.6（8 集）",
        "verified_note：末句「D15 v1.4 落盘后须复核 9 行逐条一致」→「D15 v1.6 落盘后已复核 9 行逐条一致（9/9 一致）」，"
        "并追加 v1.6 复算证据段与余量三口径现值（8 集）",
        "dwell_calc_convention 终表段：「D15 v1.4 落盘后复核」→「D15 v1.6 落盘后复核」（ep1/2/3/5/8，5 集）",
        "dwell_calc_convention 非终表集：「现值仍为 D15 **v1.4** 现行预算」与「D15 现行为 **v1.4**」→「v1.6」"
        "（ep4/6/7，3 集 × 2 处）",
    ],
    "not_changed": [
        "sync_records 旧条目（U01-R18 终表）内「D15 新 dur_sec 待声音设计落 v1.4 后复核」为事件溯源，"
        "按 S11 只追加不覆盖，原文保留（旧值留痕于本条目）",
        "sync_basis 的「D15 v1.1 贴边配音收敛」、dwell_calc_convention 的【上游闭合戳】段与"
        "「D16 v1.3→v1.4」、verified_note 中段「D15 v1.3 × D16 v1.6 × D11 v1.6 复算」均为事件溯源，原文保留",
        "全部 in_sec／out_sec／dur_sec 数值零改动（本轮只改口径文本与版本指针）",
    ],
    "verification": {
        "d15_u01_version": D15_TARGET,
        "d16_u01_version_before": D16_FROM,
        "r18_9_rows_dur_sec_vs_terminal_table": "9/9 一致",
        "subtitle_vo_sync": "28 条对白字幕 out_sec ＝ 配音 at_sec＋dur_sec，0 条不符",
        "reconcile": "node scripts/reconcile_D15_D16_timing.mjs --unit U01 → exit 0；"
                     "配音 28 ＋ sfx/foley 80 共 108 对象 0 越窗 / 0 跨段间硬切点；"
                     "字幕 75 行 0 越窗 / 0 跨切点 / 0 重叠",
        "margin_calibers_current": "口径1 镜尾余量 0.6s（ep1 镜1）｜口径2 起音间隙 0.5s（ep7 镜4）｜"
                                   "口径3 镜首余量 0.5s（ep7 镜4）",
        "margin_caliber1_change_reason": "D15 v1.4 起 ep1 镜1 配音预算由 1.6 上调为 2.0（U01-R18 终表），"
                                         "镜尾余量由 1.0s 收窄为 0.6s",
    },
    "applied_by": "分镜导演",
}


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


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
    for p in (p16, p15):
        if not os.path.isfile(p):
            sys.exit(f"[ABORT] 文件不存在：{p}")

    d16 = load(p16)
    d15 = load(p15)

    # ══ 守卫 ①：D16 版本锚定（已演进 → no-op，绝不写盘）══
    cur16 = d16.get("version")
    if cur16 != D16_FROM:
        print(f"[NO-OP] D16 当前 version={cur16}（≠ 锚定 {D16_FROM}）："
              f"本脚本为一次性 {D16_FROM}→{D16_TO} 活戳刷新脚本，已演进则不写盘（防整块回退）。")
        return

    # ══ 守卫 ②：D15 目标版本（上游已再升版 → no-op）══
    cur15 = d15.get("version")
    if cur15 != D15_TARGET:
        print(f"[NO-OP] D15 当前 version={cur15}（≠ 目标 {D15_TARGET}）："
              f"上游已再升版，本脚本的目标指针失效，不写盘。")
        return

    # ══ 守卫 ③：内容态幂等（已是 v1.6 → no-op）══
    all_verified = [e["subtitle_style"]["subtitle_sync_audit"]["verified_against_d15"]
                    for e in d16["episodes"]]
    if all(v.startswith("v1.6") for v in all_verified):
        print(f"[NO-OP] 8 集 verified_against_d15 均已是 v1.6 口径，本脚本无需执行。")
        return

    before = load(p16)
    hits = {label: 0 for label, *_ in EDITS}
    appended_note = 0
    appended_record = 0

    for e in d16["episodes"]:
        ss = e["subtitle_style"]
        a = ss["subtitle_sync_audit"]

        for label, field, old, new, _want in EDITS:
            if field == "verified_against_d15":
                s = a[field]
                n = s.count(old)
                hits[label] += n
                a[field] = s.replace(old, new)
            elif field == "verified_note":
                s = a[field]
                n = s.count(old)
                hits[label] += n
                s = s.replace(old, new)
                # 追加证据段（幂等：已含则不重复追加）
                if "D15 v1.6 活戳刷新" not in s:
                    s = s + APPEND_NOTE
                    appended_note += 1
                a[field] = s
            elif field == "dwell_calc_convention":
                s = ss[field]
                n = s.count(old)
                hits[label] += n
                ss[field] = s.replace(old, new)

        # sync_records 只追加（S11）
        recs = a.setdefault("sync_records", [])
        if not any(r.get("event") == SYNC_RECORD["event"] for r in recs):
            recs.append(json.loads(json.dumps(SYNC_RECORD)))
            appended_record += 1

    d16["version"] = D16_TO

    # ══ 命中断言：每处必须精确等于预期命中数 ══
    bad = False
    for label, _field, old, _new, want in EDITS:
        got = hits[label]
        if got != want:
            print(f"[ABORT] 命中数不符：{label} 期望 {want}，实得 {got}（锚点：{old[:40]}…）")
            bad = True
    if appended_note != len(d16["episodes"]):
        print(f"[ABORT] verified_note 证据段追加 {appended_note} 处，"
              f"期望 {len(d16['episodes'])} 处")
        bad = True
    # sync_records 是**逐集独立数组**（既有 U01-R18 记录亦为 8 集各一条），
    # 故本轮应追加「集数」条，而非 1 条。
    if appended_record != len(d16["episodes"]):
        print(f"[ABORT] sync_records 新条目追加 {appended_record} 处，"
              f"期望 {len(d16['episodes'])} 处（逐集各一条）")
        bad = True
    if bad:
        sys.exit(1)

    # ══ 结构差异白名单 ══
    diffs = collect_diff(before, d16)
    allowed = []
    for d in diffs:
        ok = (
            d == ".version"
            or d.endswith(".subtitle_style.dwell_calc_convention")
            or ".subtitle_style.subtitle_sync_audit" in d
        )
        if ok:
            allowed.append(d)
        else:
            print(f"[ABORT] 越界改动：{d}")
            sys.exit(1)

    print(f"[DIFF] 改动 {len(diffs)} 处（白名单内 {len(allowed)} 处）：")
    for d in allowed:
        print("   -", d)
    print("[HIT] 各锚点命中数：")
    for label, _f, _o, _n, want in EDITS:
        print(f"    {label}: {hits[label]} / 期望 {want}")
    print(f"[APPEND] verified_note 证据段 {appended_note} 处；sync_records 新条目 {appended_record} 条")
    print(f"[CHECK] D15 {cur15} / D16 {cur16} → {D16_TO}；全部 in_sec/out_sec/dur_sec 数值零改动")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    # ══ 落盘前备份 ══
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(proj, "reports", f"_bak_U01_D16_liveptr_{ts}")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, "D16.json"))
    print(f"[BAK] 已备份 → {bak}/D16.json")

    dump(p16, d16)
    print(f"[DONE] D16 → {d16['version']} 已落盘：{p16}")
    print(f"[SIZE] {os.path.getsize(p16)} bytes")


if __name__ == "__main__":
    main()
