#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U01-R18 终表同步（D16 v1.7 → v1.8；D11 v1.7 → v1.8）—— 分镜导演岗

派活
----
企划合规 U01-R18 终表明派（取代 batch_2fd55abc2d82 的 ① ② 两单，那两单未执行）：
- **D16**：上表 9 行 `out_sec` 同步 ＋ **ep2 seq9 字幕文字**改「换我用了。」（`out_sec` 保持 43.0）
  ＋ `sync_rule` 补写**区间口径** ＋ `subtitle_sync_audit` **按 S11 只追加** → **D16 v1.8**
- **D11**：ep2 镜4 `dialogue` 同步 → **D11 v1.8**

终表（预算取「实测标称 +0.1」；D15 新 dur_sec → D16 新 out_sec）
----------------------------------------------------------
| D09 ref | 镜位 | at | D15 新 dur_sec | D16 seq | D16 新 out_sec |
| D09 ep1 #1 | ep1 镜1 | 10.4 | 2.0 | seq6 | 12.4 |
| D09 ep2 #2 | ep2 镜2 | 19.0 | 2.9 | seq6 | 21.9 |
| D09 ep2 #3 | ep2 镜3 | 35.0 | 1.8 | seq7 | 36.8 |
| D09 ep3 #2 | ep3 镜3 | 30.5 | 2.7 | seq8 | 33.2 |
| D09 ep5 #1 | ep5 镜2 | 13.0 | 2.8 | seq5 | 15.8 |
| D09 ep5 #2 | ep5 镜2 | 17.4 | 2.8 | seq6 | 20.2 |
| D09 ep5 #4 | ep5 镜4 | 40.0 | 1.7 | seq8 | 41.7 |
| D09 ep8 #1 | ep8 镜1 |  2.0 | 2.3 | seq5 |  4.3 |
| D09 ep8 #4 | ep8 镜4 | 38.6 | 2.8 | seq8 | 41.4 |

ep8#4 例外（贴边）：out 41.4 与下一条面板文字 in 41.4 **恰好相接**，按 Q51 左闭右开**不算重叠**。

「只追加不覆盖」（S11）的具体做法
-------------------------------
`subtitle_sync_audit` 既有键**不删不改**：
- 新增 **`sync_records`（数组，只追加）**：本次 9 行同步的完整留痕（日期/依据/逐行 old→new/判据）。
- `sync_basis` / `verified_note`：**字符串末尾追加**新段，不替换原文。
- `verified_against_d15`：**改为** `v1.4（终表口径；D15 v1.4 落盘后复核）`——该键本就是「当前复核所依据的版本」，
  追加式保留会与新复核版本矛盾，故按其**语义**更新，并在 `sync_records` 里留下旧值留痕。
- `rows`：**当前态证据**，随时码变化刷新（留旧值会变成假数据）；历史由 `sync_records` 承担。

脚本纪律
--------
- **一次性 + 版本守卫**：目标文件版本不符即 **no-op 退出 0**（不写盘），杜绝旧脚本重跑回退。
- **命中数断言**：逐条核对 old→new，任一条对不上即中止不写盘。
- **差异白名单**：越界改动即中止不写盘。

用法
----
python3 scripts/patch_u01r18_sync.py --project 02_项目/双相潮主 --unit U01 [--dry-run]

边界
----
只改 `units/U01/D16.json`、`units/U01/D11.json`。不改 D08／D09／D10／D12／D13／D14／D15／D18／
project.json／索引／章程／规格／工具／源素材。未生成任何图片／视频／音频，未提交 H3 付费生成。
"""
import argparse
import json
import os
import sys

EPS = 1e-9
R = lambda x: round(float(x), 1)

# (ep, seq) -> (at, old_out, new_out, d15_new_dur, d09_ref)
TABLE = [
    (1, 6, 10.4, 12.0, 12.4, 2.0, "D09 ep1 #1"),
    (2, 6, 19.0, 21.2, 21.9, 2.9, "D09 ep2 #2"),
    (2, 7, 35.0, 36.4, 36.8, 1.8, "D09 ep2 #3"),
    (3, 8, 30.5, 32.5, 33.2, 2.7, "D09 ep3 #2"),
    (5, 5, 13.0, 15.6, 15.8, 2.8, "D09 ep5 #1"),
    (5, 6, 17.4, 19.6, 20.2, 2.8, "D09 ep5 #2"),
    (5, 8, 40.0, 41.4, 41.7, 1.7, "D09 ep5 #4"),
    (8, 5,  2.0,  4.0,  4.3, 2.3, "D09 ep8 #1"),
    (8, 8, 38.6, 41.2, 41.4, 2.8, "D09 ep8 #4"),
]

OLD_SEQ9_TEXT = "两小时五十八分……换我用了。"
NEW_SEQ9_TEXT = "换我用了。"
OLD_D11_DIALOGUE = "陆沉「两小时五十八分……换我用了。」"
NEW_D11_DIALOGUE = "陆沉「换我用了。」"

OLD_SYNC_RULE = "字幕不得早于配音起音，出点不早于配音收音"
NEW_SYNC_RULE = ("字幕不得早于配音起音，出点不早于配音收音；"
                 "区间口径按**左闭右开**判定（out_sec 等于下一条 in_sec 视为相接，不算重叠）；"
                 "重叠检查须覆盖**全部正文行**（对白／字幕／面板文字），**片尾标题卡单独检查**"
                 "（其位置与对白同在底部字幕带，与对白同刻即构成真实视觉冲突）。")

MARK = "【U01-R18 终表同步（2026-10-23）】"


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def collect_diff(a, b, path=""):
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
    p11 = os.path.join(proj, "units", unit, "D11.json")
    d16 = load(p16)
    d11 = load(p11)

    # ---------- 幂等守卫：**内容态**（不看版本号；并行实例已把 D16 升到 v1.8）----------
    rows_ = {(e["ep"], l["seq"]): l for e in d16["episodes"] for l in e["subtitle_style"]["lines"]}
    already = sum(1 for ep, seq, at, o, nw, d, r in TABLE if R(rows_[(ep, seq)]["out_sec"]) == nw)
    rule_new = all(e["subtitle_style"].get("sync_rule") == NEW_SYNC_RULE for e in d16["episodes"])
    if already == len(TABLE) and rule_new:
        print("[NO-OP] 终表 9 行与 sync_rule 区间口径均已落盘，不写盘。")
        return
    if d16.get("version") not in ("v1.7", "v1.8"):
        sys.exit(f"[ABORT] D16 版本为 {d16.get('version')}，期望 v1.7/v1.8；不写盘。")
    if d11.get("version") not in ("v1.7", "v1.8"):
        sys.exit(f"[ABORT] D11 版本为 {d11.get('version')}，期望 v1.7/v1.8；不写盘。")

    problems = []
    lines = {(e["ep"], l["seq"]): l for e in d16["episodes"] for l in e["subtitle_style"]["lines"]}

    # ---------- 1) 9 行 out_sec：命中数断言 ----------
    for ep, seq, at, old_out, new_out, dur, ref in TABLE:
        l = lines.get((ep, seq))
        if l is None:
            problems.append(f"D16 缺 ep{ep} seq{seq}")
            continue
        if R(l["in_sec"]) != at:
            problems.append(f"D16 ep{ep} seq{seq} in_sec={l['in_sec']} ≠ 终表 {at}")
        if R(l["out_sec"]) not in (old_out, new_out):
            problems.append(f"D16 ep{ep} seq{seq} out_sec={l['out_sec']} ∉ {{old {old_out}, new {new_out}}}")
        if abs((at + dur) - new_out) > EPS:
            problems.append(f"终表自身不自洽：ep{ep} seq{seq} at+dur={at + dur} ≠ {new_out}")

    # ---------- 2) ep2 seq9 文字 ----------
    l9 = lines.get((2, 9))
    if l9 is None:
        problems.append("D16 缺 ep2 seq9")
    else:
        if l9.get("text") not in (OLD_SEQ9_TEXT, NEW_SEQ9_TEXT):
            problems.append(f"D16 ep2 seq9 text={l9.get('text')!r} ∉ {{old, new}}")
        if R(l9["out_sec"]) != 43.0:
            problems.append(f"D16 ep2 seq9 out_sec={l9['out_sec']} ≠ 43.0（终表要求保持不变）")

    # ---------- 3) sync_rule ----------
    for e in d16["episodes"]:
        sr = e["subtitle_style"].get("sync_rule")
        if sr not in (OLD_SYNC_RULE, NEW_SYNC_RULE):
            problems.append(f"D16 ep{e['ep']} sync_rule 与预期值不符：{sr!r}")

    # ---------- 4) D11 ep2 镜4 dialogue ----------
    hit = 0
    for e in d11["episodes"]:
        if e["ep"] != 2:
            continue
        for s in e["shots"]:
            if s["shot_id"] == 4:
                hit += 1
                if s.get("dialogue") not in (OLD_D11_DIALOGUE, NEW_D11_DIALOGUE):
                    problems.append(f"D11 ep2 镜4 dialogue={s.get('dialogue')!r} ∉ {{old, new}}")
    if hit != 1:
        problems.append(f"D11 ep2 镜4 命中 {hit} 处，期望 1 处")

    if problems:
        print("[ABORT] 前置核对不通过，不写盘：")
        for p in problems:
            print("   -", p)
        sys.exit(1)

    before16 = load(p16)
    before11 = load(p11)

    # ---------- 落 9 行 ----------
    for ep, seq, at, old_out, new_out, dur, ref in TABLE:
        lines[(ep, seq)]["out_sec"] = new_out

    # ---------- ep2 seq9 文字（out_sec 保持 43.0） ----------
    lines[(2, 9)]["text"] = NEW_SEQ9_TEXT

    # ---------- sync_rule：8 集统一 ----------
    for e in d16["episodes"]:
        e["subtitle_style"]["sync_rule"] = NEW_SYNC_RULE

    # ---------- 口径文本：逐集追加 U01-R18 留痕 ----------
    by_ep = {}
    for ep, seq, at, old_out, new_out, dur, ref in TABLE:
        by_ep.setdefault(ep, []).append((seq, old_out, new_out, dur, ref))
    for e in d16["episodes"]:
        ep = e["ep"]
        ss = e["subtitle_style"]
        if ep in by_ep:
            items = "、".join(f"seq{s}（{o}→{n}，新 dur_sec {d}）" for s, o, n, d, _ in by_ep[ep])
            refs = "、".join(sorted({rf for _, _, _, _, rf in by_ep[ep]}))
            add = (f"{MARK}本集按总控 U01-R18 终表重算并同步的字幕行：{items}；"
                   f"依据 {refs}（预算取实测 TTS 标称+0.1；out_sec ＝ 配音 at_sec＋新 dur_sec，"
                   f"D15 v1.4 落盘后复核）。ep8 seq8 的 out 41.4 与下一条面板文字 in 41.4 恰好相接，"
                   f"按 Q51 左闭右开不算重叠。"
                   if ep == 8 else
                   f"{MARK}本集按总控 U01-R18 终表重算并同步的字幕行：{items}；"
                   f"依据 {refs}（预算取实测 TTS 标称+0.1；out_sec ＝ 配音 at_sec＋新 dur_sec，"
                   f"D15 v1.4 落盘后复核）。")
            if ep == 2:
                add += ("ep2 seq9 字幕文字随 D08 U01 v1.9／D09 U01 v1.5 压缩改为「换我用了。」，"
                        "out_sec 保持 43.0 不变（D15 ep2#4 预算仍为 1.8）；"
                        "ep2 seq8「全城钟楼敲响十一下。」属画面内可见文字层，未动。")
            if MARK not in ss["dwell_calc_convention"]:
                ss["dwell_calc_convention"] = ss["dwell_calc_convention"] + add
        # 审计块：sync_records 只追加
        aud = ss.setdefault("subtitle_sync_audit", {})
        recs = aud.setdefault("sync_records", [])
        if not any(r.get("event") == "U01-R18 终表" for r in recs):
            recs.append({
                "date": "2026-10-23",
                "event": "U01-R18 终表",
                "basis": "企划合规 U01-R18 终表（预算取实测 TTS 标称+0.1）；"
                         "D15 新 dur_sec 待声音设计落 v1.4 后复核",
                "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
                "rows": [{"ep": ep_, "seq": s_, "in_sec": at_, "old_out_sec": o_, "new_out_sec": n_,
                          "d15_new_dur_sec": d_, "d09_ref": rf_}
                         for ep_, s_, at_, o_, n_, d_, rf_ in TABLE],
                "seq9_text_change": {"ep": 2, "seq": 9, "old": OLD_SEQ9_TEXT, "new": NEW_SEQ9_TEXT,
                                     "out_sec_kept": 43.0,
                                     "reason": "D08 U01 v1.9／D09 U01 v1.5 压缩末句（缩文案是唯一解）；"
                                               "D15 ep2#4 预算保持 1.8 → out_sec 不变"},
                "applied_by": "分镜导演",
            })
        # 当前态证据 rows 刷新 + 版本戳（语义更新，旧值留痕在 sync_records）
        aud["verified_against_d15"] = "v1.4（终表口径；D15 v1.4 落盘后复核）"
        aud["verified_note"] = (aud.get("verified_note", "") +
                                "｜2026-10-23 U01-R18 终表：本次同步依据终表 9 行（预算取实测 TTS 标称+0.1），"
                                "D15 v1.4 落盘后须复核 9 行逐条一致。")
        aud["sync_basis"] = (aud.get("sync_basis", "") +
                             "｜U01-R18 终表（2026-10-23）：9 行按实测 TTS 标称+0.1 重算并同步，明细见 sync_records。")

    d16["version"] = "v1.9"

    # ---------- D11：ep2 镜4 dialogue ----------
    for e in d11["episodes"]:
        if e["ep"] != 2:
            continue
        for s in e["shots"]:
            if s["shot_id"] == 4:
                s["dialogue"] = NEW_D11_DIALOGUE
    # D11 版本**不动**：v1.8 已由并行实例落（ep2#4 文案同步），本岗不改其版本

    # ---------- 差异白名单 ----------
    ALLOW16 = (".version", ".episodes[].subtitle_style.dwell_calc_convention",
               ".episodes[].subtitle_style.sync_rule",
               ".episodes[].subtitle_style.subtitle_sync_audit",
               ".episodes[].subtitle_style.lines")
    ALLOW11 = (".version", ".episodes[1].shots[3].dialogue")

    def check(after, before, allow, path):
        for d in collect_diff(before, after):
            ok = any(d == a or d.startswith(a) or
                     (a.endswith("[]") and f".{a.split('[]')[0]}[" in d) or
                     (a.startswith(".episodes[") and ".episodes[" in d and a.split("]")[1] in d)
                     for a in allow)
            if not ok:
                print(f"[ABORT] 越界改动：{path} {d}")
                sys.exit(1)

    check(d16, before16, ALLOW16, p16)
    check(d11, before11, ALLOW11, p11)

    # ---------- 复核：9 行 + 无重叠 + 不越镜时段 ----------
    lines2 = {(e["ep"], l["seq"]): l for e in d16["episodes"] for l in e["subtitle_style"]["lines"]}
    for ep, seq, at, old_out, new_out, dur, ref in TABLE:
        if R(lines2[(ep, seq)]["out_sec"]) != new_out:
            sys.exit(f"[ABORT] ep{ep} seq{seq} 未同步到 {new_out}")
    for e in d16["episodes"]:
        body = sorted([l for l in e["subtitle_style"]["lines"]
                       if l["type"] not in ("片头", "片尾", "角标")], key=lambda l: R(l["in_sec"]))
        for a, b in zip(body, body[1:]):
            if R(a["out_sec"]) > R(b["in_sec"]) + EPS:
                sys.exit(f"[ABORT] ep{e['ep']} seq{a['seq']} out={a['out_sec']} 与 seq{b['seq']} "
                         f"in={b['in_sec']} 重叠")
    if R(lines2[(2, 9)]["out_sec"]) != 43.0:
        sys.exit("[ABORT] ep2 seq9 out_sec 未保持 43.0")

    print(f"[PLAN] D16 → v1.9：9 行 out_sec 同步 + ep2 seq9 文字改「{NEW_SEQ9_TEXT}」"
          f"（out 保持 43.0）+ sync_rule 补区间口径 + audit 追加 sync_records")
    print(f"[PLAN] D11：ep2 镜4 dialogue → 「{NEW_D11_DIALOGUE}」（若已落则不动、不改版本）")
    print("[CHECK] 9 行同步命中 9/9；正文行两两不重叠；ep2 seq9 out 保持 43.0")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    dump(p16, d16)
    if collect_diff(before11, d11):
        dump(p11, d11)
        print("[DONE] D11 ep2 镜4 dialogue 已落盘")
    else:
        print("[DONE] D11 无变化（ep2#4 文案已由并行实例落 v1.8），未写盘")
    print(f"[DONE] D16 → {d16['version']} 已落盘")


if __name__ == "__main__":
    main()
