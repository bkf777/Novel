#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜导演岗：D16 U01 侧补「预演参数依赖声明」—— 与 D15 U01 v1.5/v1.6 的同名口径条对称。

派活来源
--------
声音设计（bot_0a60d9bbd4fe）两条派活（05:5x「D16 v1.9 全库实测：verified_note 共 8 条，
8/8 均不含『预演参数』或 speed 字样 ⇒ 两侧目前不对称」＋ 06:0x 追加条「四、05:5x 那条的
其余请求仍然有效、仍然待你落」）。请求原文给定了措辞，本岗按派单原文落笔。

认盘结论（2026-10-23，现盘实测）
--------------------------------
| 事实 | 实测 |
|---|---|
| D15 U01 版本 | **v1.6**（112,805 B｜06:08:13）—— 派单里的 v1.5 已过时 |
| D15 U01 「预演参数依赖声明」 | **8/8 集 mix_notes[6] 命中**（全局口径条全文，1392 字符）→ 上游已落 |
| D16 U01 版本 | **v1.11**（183,220 B｜07:54:49 并行实例落）—— 派单里的 v1.9 已过时 |
| D16 U01 `verified_note` 含「预演参数」／`speed` | **0/8 集** → **不对称在现盘仍成立，本轮补** |
| D16 U01 `verified_against_d15` | 8/8 已是「v1.6（终表口径；D15 v1.6 落盘后复核）」→ **派单第二项「活戳措辞更新」已被 §115 落好，本脚本不改**（防重复记账） |
| 派单第四项「测量来源口径复述」 | 声音设计明言「引用 D15 这句即可，不必在本岗产物里重复登记」→ **本脚本不重复登记** |

本脚本只做一件事
--------------
在 D16 U01 侧 8 集的 `subtitle_style.subtitle_sync_audit` 下：
1. `verified_note` **末尾追加**（S11 只追加不重写）一段「预演参数依赖声明」；
2. 新增结构化字段 `preview_param_dependency`（Q57：口径须落进结构化字段供脚本消费），
   载明：参数来源、实测来源口径引用（指向 D15 v1.6，不复制）、复跑命令、同步对象、
   「尚非成片最终参数」定性；
3. `sync_records` **追加**一条留痕（S11 只追加，不改旧条目）。

数值零改动
----------
不动任何 in_sec／out_sec／dur_sec／cuts／transitions／title_card／paywall_point／
dwell_calc_convention／verified_against_d15／sync_basis。
结构差异白名单只允许 `.version` 与 `.episodes[*].subtitle_style.subtitle_sync_audit.*`。

本脚本**不做**的事（防越界）
--------------------------
- 不改 D15（声音设计岗）／D11／D08／D09／D12／D13／D14／D18／project.json／03_规格／04_工具；
- 不改 U02（D16 U02 v1.5 为并行实例产物，且 U02 无预演 TTS 资产 —— preview/ 下只有
  U01_tts 与 U01_video，U02 无 items.json，故「预演参数依赖声明」对 U02 无适用对象）；
- 不改 ep2#4 的 dur_sec（声音设计与台本编剧两方均确认：新句「换我用了。」无实测音频，
  出片阶段重合成前不据此调预算、不据此调语速；本脚本对此只做口径登记，零数值改动）。

用法
----
python3 scripts/patch_D16_U01_preview_param_dep.py --project . --unit U01 [--dry-run] [--force]

守卫
----
① 版本守卫（Q64）：盘上 D16 version 锚定 v1.11；高于 v1.11 → 拒写（`--force` 逃生口）；
   ② 幂等守卫：8 集 verified_note 均已含本声明 → `[NO-OP]` exit 0；
③ 命中断言：每处替换命中数必须**精确等于**预期；
④ 结构差异白名单：越界即 `[ABORT]` exit 1 不写盘；
⑤ 数值零改动断言：写盘前逐条比对所有数值字段，改动 ≠ 0 即中止。

边界
----
只出文档。不生成图片/视频/音频，不合成 TTS/BGM，不提交 H3 付费生成，不投流上架。
"""
import argparse
import json
import os
import shutil
import sys
import time

# ── 版本锚定（Q64）──
D16_FROM = "v1.11"
D16_TO = "v1.12"
D15_EXPECT = "v1.6"          # 上游口径条所在版本；≠ 则本脚本目标失效（no-op）

# ── 幂等标记（写进 verified_note 与结构化字段，便于脚本判重）──
MARK = "预演参数依赖声明"

# ── 追加到 verified_note 末尾的声明段（8 集通用；措辞取自声音设计派单原文并按现盘事实校正）──
APPEND_NOTE = (
    "｜2026-10-23 预演参数依赖声明（与 D15 U01 v1.5/v1.6 同名口径条对称；"
    "派活：声音设计 05:5x 与 06:0x 两条，本岗按原文落笔）："
    "本表对白字幕 out_sec 所依据的 D15 配音预算，**对应的是当前预演 TTS 参数**"
    "（音色 voice_id／语速 speed／音高 pitch 逐条以 preview/U01_tts/items.json 为准），"
    "**尚非成片最终参数**；成片若改语速或音色，实测时长会随之变化，"
    "须重跑 scripts/check_tts_vs_d15_budget.py --unit U01，"
    "并按新实测再次同步 D15 dur_sec 与本表对应行 out_sec；"
    "在成片参数确定并复跑之前，本表预算按**预演参数口径**理解，**不得当作成片定值**。"
    "测量来源口径（只信 ffprobe format=duration 实测值、不取 preview/U01_tts/items.json 的 "
    "dur 缓存字段——该字段已有 1 条陈旧：ep008_13 记 3.41746／ffprobe 实测 2.800，差 0.617s）"
    "**以 D15 U01 v1.6 全局口径条为准，本岗不重复登记**（派单明言）。"
    "本段只登记口径，**未改动任何 in_sec／out_sec／dur_sec 数值**。"
)

# ── 结构化字段（Q57：口径落进结构化字段供脚本消费）──
STRUCT_FIELD = {
    "_说明": "本块是「预演参数依赖声明」的机器可读口径定义（Q57）。"
             "自然语言版载于同层 verified_note 末段；本块供脚本按字段消费，勿改自然语言即改数值。",
    "声明版本": "D15 U01 v1.5 起生效、v1.6 补测量来源口径；本岗 D16 侧对称登记于 D16 U01 v1.12",
    "适用范围": "本表全部对白字幕行（out_sec ＝ 对应 D15 配音 dur_sec 之源）",
    "参数来源": {
        "文件": "preview/U01_tts/items.json",
        "逐条字段": ["voice_id", "speed", "pitch"],
        "口径": "音色／语速／音高逐条以该文件现值为准；该文件同时是成片参数的**预演期**快照",
    },
    "时长测量来源": {
        "口径位置": "D15 U01 v1.6 全局口径条（本岗不重复登记，派单明言）",
        "要点": "只信 ffprobe format=duration 实测值；不取 preview/U01_tts/items.json 的 dur 缓存字段",
        "已知陈旧": {"id": "ep008_13", "items_json_dur": 3.41746, "ffprobe_dur": 2.800, "差": 0.617},
    },
    "定性": "本表预算对应预演参数口径，尚非成片最终参数，不得当作成片定值",
    "成片参数变更后的动作": {
        "复跑命令": "python3 scripts/check_tts_vs_d15_budget.py --unit U01",
        "须同步": ["D15 U01 对应 voice_over.dur_sec", "D16 U01 对应行 out_sec"],
        "同步方": "D15 dur_sec 归声音设计岗（bot_0a60d9bbd4fe）；D16 out_sec 归本岗（bot_1855d6ce9cdd）",
    },
    "已知挂账": {
        "ep2_seq9": "新句「换我用了。」尚无实测音频（preview/U01_tts/items.json 的 ep002_13 已标 "
                    "stale_audio，实测 2.953s 为旧句）→ 出片阶段按新句重合成后实测复核；"
                    "在此之前**不据此调预算、不据此调语速**（声音设计与台本编剧两方口径一致）",
    },
    "applied_by": "分镜导演",
}

# ── 追加到 sync_records 的留痕条目（S11 只追加）──
SYNC_RECORD = {
    "date": "2026-10-23",
    "event": "D16 U01 补「预演参数依赖声明」（与 D15 U01 v1.5/v1.6 对称）",
    "basis": "声音设计 05:5x 与 06:0x 两条派活（请求在 D16 侧补同口径一句；"
             "派单实测「D16 v1.9 全库 verified_note 共 8 条，8/8 均不含『预演参数』或 speed」）。"
             "本岗按现盘独立复核：派单所述版本号（D15 v1.5／D16 v1.9）均已过时，"
             "现盘为 D15 U01 v1.6／D16 U01 v1.11；「8/8 集 verified_note 不含预演参数口径」"
             "这一条在现盘**仍成立**（0/8 命中），故本轮落笔。",
    "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
    "changes": [
        "verified_note：末尾追加「预演参数依赖声明」段（8 集，逐集追加，S11 只追加不重写）",
        "subtitle_sync_audit 新增结构化字段 preview_param_dependency（8 集，Q57 口径落结构化字段）",
        "sync_records 追加本条目（逐集各一条）",
    ],
    "not_changed": [
        "verified_against_d15：8 集现值已是「v1.6（终表口径；D15 v1.6 落盘后复核）」"
        "（并行实例 §115 已落）→ 本轮**不改**，防重复记账",
        "dwell_calc_convention、sync_basis、verified_note 中段与既有 sync_records 条目："
        "均为事件溯源，按 S11 原文保留",
        "全部 in_sec／out_sec／dur_sec 数值零改动（本轮只改口径文本与结构化字段）",
        "D15 U02 ep9 两条 1.2s 贴边：本轮**未改**（裁决见台账，变更需 D15 侧先落）",
    ],
    "applied_by": "分镜导演",
}

# 数值字段白名单（数值零改动断言的比对范围）
NUMERIC_KEYS = ("in_sec", "out_sec", "at_sec", "dur_sec", "min_dwell_sec",
                "duration_sum", "start_sec", "end_sec")


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


def collect_numbers(obj, path="", out=None):
    """收集所有数值字段的 (路径, 值) 列表，用于数值零改动断言。"""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            collect_numbers(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            collect_numbers(v, f"{path}[{i}]", out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if any(path.endswith("." + k) for k in NUMERIC_KEYS):
            out.append((path, obj))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="Q64 逃生口：盘上版本高于本脚本锚定版本时仍强制写盘")
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
    cur16 = d16.get("version")
    cur15 = d15.get("version")

    # ══ 守卫 ①（内容态幂等）：**必须最先判** ══
    # 分层划界（教训：上游守卫抢先 exit 会把下游守卫的合法路径挡死）：
    # 「内容已达成、无需写盘」是比版本更基本的判断；若把版本守卫放在它之前，
    # 则本脚本自己写出的 v1.12 会在第二次运行时被版本守卫当成「他人升版」而拒写，
    # 幂等路径被遮蔽。故幂等判定前置。
    notes = [e["subtitle_style"]["subtitle_sync_audit"]["verified_note"]
             for e in d16["episodes"]]
    if all(MARK in s for s in notes):
        print(f"[NO-OP] {len(notes)} 集 verified_note 均已含「{MARK}」，本脚本无需执行。")
        return

    # ══ 守卫 ②：版本守卫（Q64）══
    # 分层划界（教训：版本回退场景归版本守卫，内容层不得抢这个活）：
    #   · 盘上版本**高于**脚本锚定版本 → 属「已被他人升版」场景 → 版本守卫判定，
    #     带 --force 逃生口；逃生口放行时**不把版本号改回** D16_TO（那会造成版本回退），
    #     而是按盘上版本 minor 递增。
    #   · 盘上版本**低于/不等于**锚定版本且非更高 → 一致性不成立 → no-op，不写盘。
    #   · 内容层（差异白名单、数值零改动）**不受 --force 影响**：--force 只豁免版本守卫，
    #     绝不豁免内容层拒写（否则逃生口会变成万能钥匙）。
    version_target = D16_TO
    if cur16 != D16_FROM:
        higher = False
        try:
            c_parts = [int(x) for x in str(cur16).lstrip("v").split(".")]
            f_parts = [int(x) for x in D16_FROM.lstrip("v").split(".")]
            higher = c_parts > f_parts
        except Exception:
            higher = False
        if higher and not args.force:
            sys.exit(f"[ABORT] 版本守卫：盘上 D16 version={cur16} 高于本脚本锚定 {D16_FROM} —— "
                     f"可能已被他人升版，拒绝写盘。如确需覆盖，用 --force（Q64 逃生口）。")
        if not higher:
            print(f"[NO-OP] D16 当前 version={cur16}（≠ 锚定 {D16_FROM} 且非更高版本）："
                  f"本脚本为一次性 {D16_FROM}→{D16_TO} 脚本，已演进则不写盘（防整块回退）。")
            return
        if higher and args.force:
            # 逃生口：按盘上版本 minor 递增，绝不回退版本号
            try:
                c_parts = [int(x) for x in str(cur16).lstrip("v").split(".")]
                version_target = "v{}.{}".format(c_parts[0], c_parts[1] + 1)
            except Exception:
                version_target = D16_TO
            print(f"[FORCE] 版本守卫逃生口：盘上 {cur16} 高于锚定 {D16_FROM}，"
                  f"按 --force 继续；版本目标 {version_target}（不回落至 {D16_TO}）")

    # ══ 守卫 ②：上游口径条版本（≠ 预期 → 目标失效，no-op）══
    if cur15 != D15_EXPECT:
        print(f"[NO-OP] D15 当前 version={cur15}（≠ 预期 {D15_EXPECT}）："
              f"上游口径条所在版本已变，本脚本引用的措辞基线失效，不写盘。")
        return

    # ══ 守卫 ③：内容态幂等 ══
    notes = [e["subtitle_style"]["subtitle_sync_audit"]["verified_note"]
             for e in d16["episodes"]]
    if all(MARK in s for s in notes):
        print("[NO-OP] 8 集 verified_note 均已含「预演参数依赖声明」，本脚本无需执行。")
        return

    before = load(p16)
    appended_note = 0
    appended_field = 0
    appended_record = 0
    hits_note = 0

    for e in d16["episodes"]:
        a = e["subtitle_style"]["subtitle_sync_audit"]

        # 1) verified_note 末尾追加（S11 只追加）
        s = a["verified_note"]
        if MARK in s:
            pass
        else:
            hits_note += s.count("｜2026-10-23 预演参数依赖声明")  # 命中数应为 0（尚未追加）
            a["verified_note"] = s + APPEND_NOTE
            appended_note += 1

        # 2) 结构化字段（Q57）
        if "preview_param_dependency" not in a:
            a["preview_param_dependency"] = json.loads(json.dumps(STRUCT_FIELD))
            appended_field += 1

        # 3) sync_records 只追加（S11）
        recs = a.setdefault("sync_records", [])
        if not any(r.get("event") == SYNC_RECORD["event"] for r in recs):
            recs.append(json.loads(json.dumps(SYNC_RECORD)))
            appended_record += 1

    d16["version"] = version_target

    # ══ 命中断断言 ══
    n_ep = len(d16["episodes"])
    bad = False
    if appended_note != n_ep:
        print(f"[ABORT] verified_note 追加 {appended_note} 处，期望 {n_ep} 处"); bad = True
    if appended_field != n_ep:
        print(f"[ABORT] preview_param_dependency 新增 {appended_field} 处，期望 {n_ep} 处"); bad = True
    if appended_record != n_ep:
        print(f"[ABORT] sync_records 追加 {appended_record} 条，期望 {n_ep} 条（逐集各一条）"); bad = True
    if bad:
        sys.exit(1)

    # ══ 结构差异白名单 ══
    diffs = collect_diff(before, d16)
    allowed = []
    for d in diffs:
        ok = (d == ".version"
              or ".subtitle_style.subtitle_sync_audit" in d)
        if ok:
            allowed.append(d)
        else:
            print(f"[ABORT] 越界改动：{d}")
            sys.exit(1)

    # ══ 数值零改动断言 ══
    nums_before = collect_numbers(before)
    nums_after = collect_numbers(d16)
    if len(nums_before) != len(nums_after):
        print(f"[ABORT] 数值字段条数变化：{len(nums_before)} → {len(nums_after)}")
        sys.exit(1)
    num_diffs = [(p, x, y) for (p, x), (_, y) in zip(nums_before, nums_after) if x != y]
    if num_diffs:
        print(f"[ABORT] 数值字段改动 {len(num_diffs)} 处（应为零）：")
        for p, x, y in num_diffs[:20]:
            print(f"    {p}: {x} → {y}")
        sys.exit(1)

    print(f"[DIFF] 改动 {len(diffs)} 处（白名单内 {len(allowed)} 处）：")
    for d in allowed:
        print("   -", d)
    print(f"[APPEND] verified_note {appended_note} 处；preview_param_dependency {appended_field} 处；"
          f"sync_records {appended_record} 条")
    print(f"[NUM] 数值字段 {len(nums_before)} 个，改动 0 处（逐条比对）")
    print(f"[CHECK] D15 {cur15} / D16 {cur16} → {D16_TO}")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(proj, "reports", f"_bak_U01_D16_previewparam_{ts}")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, "D16.json"))
    print(f"[BAK] 已备份 → {bak}/D16.json")

    dump(p16, d16)
    print(f"[DONE] D16 → {d16['version']} 已落盘：{p16}")
    print(f"[SIZE] {os.path.getsize(p16)} bytes")


if __name__ == "__main__":
    main()
