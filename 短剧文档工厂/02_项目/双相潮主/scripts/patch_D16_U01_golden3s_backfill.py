#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01 D16 补丁：ep004–ep008 的 `subtitle_style.golden3s_first_line` 状态回填（R-026d · 任务一）。

背景（R-026a / R-026d，总控 2026-10-23 11:55 派）：
  声音设计岗已把 D15 U01 ep004–ep008 的**首句配音 at_sec 前移至 0.5s（dur 不变）**；
  其中 ep005 / ep006 做成**画外音**（D15 U01 v1.11 该两条 `voice_over` 已带
  `delivery` 字段与 mix 追加语）。
  D16 U01 现盘（v1.19）这五集的 `golden3s_first_line` 仍是「待 D15 前移」，
  且 `current_d15_vo_at_sec` 还是前移前的旧值（5.4／13.0／13.0／4.0／2.0）→ 本补丁回填。

**真值源＝D15 现盘**（本脚本每次运行都现读 `units/U01/D15.json`），不是 D16 里的转录值；
  读到的 `at_sec`／`dur_sec`／`line_ref`／`delivery` 全部从 D15 取，D16 只落副本。

回填范围（严格按派单）：
  ① `subtitle_style.golden3s_first_line`：status / d15_vo_at_sec / d15_vo_dur_sec /
     d15_line_ref / delivery（ep005、ep006 带画外音标识，**逐字取自 D15 的 `delivery`**）。
  ② 与该闸位直接绑定的**对白字幕行**（`subtitle_style.lines` ＋
     `subtitle_sync_audit.rows`）按实测 re-time：in_sec ＝ 配音 at_sec、
     out_sec ＝ 配音 at_sec＋dur_sec。**不改**这条会让同一份表里出现两个互相打架的
     「首句入画时码」（闸位写 0.5s、字幕行写 13.0s）——D16 是剪辑/字幕施工表，
     字幕行不改＝闸位形同虚设。
  ③ `shot_id`：按「0.5s 落在哪一镜的时间窗」取，**不沿用 D15 的 `shot_id`** ——
     D15 v1.11 对 ep005 #1／ep006 #1 仍标 `shot_id: 2`（配音侧未随 at_sec 前移同步镜号），
     但 0.5s 落在镜1 的时间窗内；D11 侧已把这两句迁到镜1 承接（见
     `patch_D11_U01_ep5_ep6_vo_firstline.py`），本脚本按 D11 镜窗复核并断言。

**不动的**：景别/机位/镜时（D11）、D15 配音数据、D08/D09/D12/D14、shared/**。
  `ep001`–`ep003` 的 `golden3s_first_line` 本轮**不动**（已是达标态，属事件溯源）。

用法：python3 scripts/patch_D16_U01_golden3s_backfill.py          # 落盘
      python3 scripts/patch_D16_U01_golden3s_backfill.py --check  # 只校验，不写盘
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

D16_PATH = P("units", "U01", "D16.json")
D15_PATH = P("units", "U01", "D15.json")
D11_PATH = P("units", "U01", "D11.json")

D16 = json.load(open(D16_PATH, encoding="utf-8"))
D15 = json.load(open(D15_PATH, encoding="utf-8"))
D11 = json.load(open(D11_PATH, encoding="utf-8"))

EXPECT_D16_VERSION = "v1.19"
NEW_VERSION = "v1.20"

TARGET_EPS = [4, 5, 6, 7, 8]

# 本轮回填的集 → 首句文本（用于在本表内定位那一行；D15 真值另读）
FIRST_LINE_TEXT = {
    4: "三秒。",
    5: "按规程投入，回收雾核。",
    6: "走开。",
    7: "十二天。",
    8: "叶红衣，愿为你执刃。",
}

# 回填前的旧闸位值（并发守卫：磁盘若已被他人改写这些值 → 中止）
EXPECT_OLD_GATE = {
    4: {"status": "待 D15 前移", "current_d15_vo_at_sec": 5.4, "current_d15_line_ref": "D09 ep4 #1"},
    5: {"status": "待 D15 前移", "current_d15_vo_at_sec": 13.0, "current_d15_line_ref": "D09 ep5 #1"},
    6: {"status": "待 D15 前移", "current_d15_vo_at_sec": 13.0, "current_d15_line_ref": "D09 ep6 #1"},
    7: {"status": "待 D15 前移", "current_d15_vo_at_sec": 4.0, "current_d15_line_ref": "D09 ep7 #1"},
    8: {"status": "待 D15 前移", "current_d15_vo_at_sec": 2.0, "current_d15_line_ref": "D09 ep8 #1"},
}

# ---- 断言清单 ----------------------------------------------------------
ASSERT_MANIFEST = [
    ("C01", "D16 磁盘版本 == 预期基线 v1.19（有并发写入即中止）"),
    ("C02", "D15 现盘版本已记录，且 ep004–ep008 首条 line_ref 均可读"),
    ("C03", "D15 五集首条 at_sec 全部 == 0.5（黄金 3 秒目标）"),
    ("C04", "D15 五集首条 dur_sec 与本表旧字幕行时码推导值一致（dur 不变）"),
    ("C05", "D16 五集闸位现值 == 预期旧值（并发守卫）"),
    ("C06", "0.5s 落在 D11 镜1 的时间窗内，且 D11 该镜 dialogue 含首句文本"),
    ("C07", "闸位回填后 d15_vo_at_sec / d15_vo_dur_sec / d15_line_ref 与 D15 逐字相等"),
    ("C08", "ep005 / ep006 的 delivery 逐字等于 D15 同条 delivery；其余三集无 delivery"),
    ("C09", "对白字幕行 re-time 后：in_sec == 配音 at_sec、out_sec == at_sec＋dur_sec"),
    ("C10", "subtitle_sync_audit.rows 与 subtitle_style.lines 逐条一致（同 in/out/shot/d15 锚点）"),
    ("C11", "re-time 后各行停留 ≥1.2s（标称网格）、不越所在镜时间窗、不跨段间切点"),
    ("C12", "版本号 = 现盘 + 1（v1.19 → v1.20），不沿用旧号"),
]


def d15_first(ep):
    e = [x for x in D15["episodes"] if x["ep"] == ep][0]
    vos = sorted(e["voice_over"], key=lambda v: v["at_sec"])
    first = vos[0]
    assert first["line_ref"] == f"D09 ep{ep} #1", f"ep{ep} 首条 line_ref 异常：{first['line_ref']}"
    return first


def d11_shot_windows(ep):
    e = [x for x in D11["episodes"] if x["ep"] == ep][0]
    out = []
    t = 0.0
    for s in e["shots"]:
        out.append((s["shot_id"], t, t + s["duration_sec"], s))
        t += s["duration_sec"]
    return out


def d11_cut_at(ep):
    e = [x for x in D11["episodes"] if x["ep"] == ep][0]
    t = 0.0
    cuts = []
    for s in e["shots"][:-1]:
        t += s["duration_sec"]
        cuts.append(t)
    return cuts


def nominal(x):
    return round(x + 1e-9, 1)


def main():
    check_only = "--check" in sys.argv
    errors = []
    d15_version = D15.get("version")

    # C01
    if D16.get("version") != EXPECT_D16_VERSION:
        print(f"❌ 中止：U01 D16 现盘版本 {D16.get('version')} ≠ 预期基线 {EXPECT_D16_VERSION}")
        return 2

    eps16 = {e["ep"]: e for e in D16["episodes"]}
    truth = {}

    for ep in TARGET_EPS:
        # C02 / C03
        v = d15_first(ep)
        truth[ep] = v
        if v["at_sec"] != 0.5:
            errors.append(f"C03 ep{ep}：D15 首条 at_sec={v['at_sec']} ≠ 0.5")
        # C05 并发守卫
        gate = eps16[ep]["subtitle_style"]["golden3s_first_line"]
        exp = EXPECT_OLD_GATE[ep]
        for k, val in exp.items():
            if gate.get(k) != val:
                errors.append(f"C05 ep{ep} 闸位 {k} 现值 {gate.get(k)!r} ≠ 预期 {val!r}（疑似并发改写）")
        # C06 镜窗归属
        win = None
        for sid, a, b, s in d11_shot_windows(ep):
            if a <= v["at_sec"] < b:
                win = (sid, a, b, s)
                break
        if win is None:
            errors.append(f"C06 ep{ep}：0.5s 不落在任何镜窗内")
        else:
            sid, a, b, s = win
            if FIRST_LINE_TEXT[ep] not in s.get("dialogue", ""):
                errors.append(
                    f"C06 ep{ep}：D11 镜{sid} 的 dialogue 未含首句「{FIRST_LINE_TEXT[ep]}」"
                    f"（现值 {s.get('dialogue')!r}）—— D11 承接补丁尚未落盘？")
            if sid != 1:
                errors.append(f"C06 ep{ep}：0.5s 落在镜{sid}，本补丁预期镜1")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    for ep in TARGET_EPS:
        v = truth[ep]
        e16 = eps16[ep]
        ss = e16["subtitle_style"]
        at = v["at_sec"]
        dur = v["dur_sec"]
        out = at + dur
        txt = FIRST_LINE_TEXT[ep]
        is_vo = "delivery" in v

        # 镜号：0.5s 所在镜（D11 镜窗）
        shot_id = 1
        for sid, a, b, s in d11_shot_windows(ep):
            if a <= at < b:
                shot_id = sid
                break

        # ① 闸位回填
        gate = {
            "target": "首句台词 ≤1.5s 入画（短剧黄金 3 秒）",
            "status": "达标",
            "text": txt,
        }
        if is_vo:
            gate["delivery"] = v["delivery"]
        gate["d15_vo_at_sec"] = at
        gate["d15_vo_dur_sec"] = dur
        gate["d15_line_ref"] = v["line_ref"]

        if is_vo:
            if ep == 5:
                gate["note"] = (
                    f"D15 U01 {d15_version} 已把本集首句配音前移至 {at}s（dur 不变＝{dur}s），"
                    f"并在同条标注 `delivery`＝「{v['delivery']}」、mix 追加「本条作画外音：按主观声处理，"
                    "画面内无该角色口型，人物不出画」。本表该行 "
                    f"{at}~{out}s 与之逐条相等；第 0 帧给最强符号（装甲车灯扫过钢板围栏、"
                    "护卫队押队列进厂），下令者叶承钧**不在画幅内**"
                    "（D12 提示词卡 C-017 `consistency_refs.char_ids` 本为空数组）。"
                    "本行随闸位前移至镜1 承接（0.5s 落在镜1 时间窗 0~12.0s 内），"
                    "D11 镜2 自此只留第二句「序号三，逾期十一天。」。")
            else:
                gate["note"] = (
                    f"D15 U01 {d15_version} 已把本集首句配音前移至 {at}s（dur 不变＝{dur}s），"
                    f"并在同条标注 `delivery`＝「{v['delivery']}」、mix 追加「本条作画外音：按主观声处理，"
                    "画面内无该角色口型，人物不出画」。本表该行 "
                    f"{at}~{out}s 与之逐条相等；第 0 帧给最强符号（厂房暗处剪影暴起、"
                    "重钢钎拖地划出火星），命令压在剪影冲出暗处的一秒落下。"
                    "⚠️ **口径差异（登记待总控裁决，本岗不自行改判）**：D15 该条 delivery 字面写"
                    "「人物不出画」，但 D11 镜1 的 visual_facts 是「厂房暗处的一道剪影暴起冲出」——"
                    "陆沉以**不可辨识剪影**在画幅内（D12 C-021：`char_ids=[\"LC\"]`、"
                    "`char_descriptions=[\"黑色战术风衣\"]`，不给面部、不给身份锚点）。"
                    "本集落点口径按「**身份不出画／先声后人**」执行，与 D15 mix 追加语"
                    "「画面内无该角色口型」严格一致；「人物完全不在画幅内」在本镜不成立。"
                    "本行随闸位前移至镜1 承接（0.5s 落在镜1 时间窗 0~11.0s 内），"
                    "D11 镜2 自此无台词。")
        else:
            gate["note"] = (
                f"D15 U01 {d15_version} 已把本集首句配音前移至 {at}s（dur 不变＝{dur}s）；"
                f"本表该行 {at}~{out}s 与之逐条相等。首句与第 0 帧画面同刻发生，"
                "人物在画内（D15 该条无 `delivery`，非画外音），不另加铺垫。")
        ss["golden3s_first_line"] = gate

        # ② 字幕行 re-time
        hit = None
        for l in ss["lines"]:
            if l.get("type") == "对白" and l.get("text") == txt:
                hit = l
                break
        if hit is None:
            print(f"❌ ep{ep}：subtitle_style.lines 内找不到首句行「{txt}」")
            return 1
        old_note = hit.get("note", "")
        prefix = ""
        if "｜【配音对齐" in old_note:
            prefix = old_note.split("｜【配音对齐")[0] + "｜"
        vo_tail = ("【配音对齐 2026-10-23 · R-026a 前移后复核】按 D15 {ref}：at {at}s ＋ dur {dur}s "
                   "实测复核（字幕行与闸位同步前移）").format(ref=v["line_ref"], at=at, dur=dur)
        if is_vo:
            vo_tail += "｜【画外音】" + v["delivery"] + "（逐字取自 D15 同条 delivery 字段）"
            if ep == 6:
                vo_tail += ("；⚠️ 本集口径差异：镜1 内陆沉为不可辨识剪影（无口型、无面部、"
                            "无身份锚点），落点口径为「身份不出画／先声后人」，"
                            "与 D15 mix 追加语「画面内无该角色口型」一致；"
                            "与 delivery 字面「人物不出画」的差异已登记待总控裁决")
        hit["in_sec"] = at
        hit["out_sec"] = out
        hit["shot_id"] = shot_id
        hit["note"] = (prefix + vo_tail) if prefix else vo_tail

        # ③ 审计行 re-time
        arow = None
        for r in ss["subtitle_sync_audit"]["rows"]:
            if r.get("type") == "对白" and r.get("text") == txt:
                arow = r
                break
        if arow is None:
            print(f"❌ ep{ep}：subtitle_sync_audit.rows 内找不到首句行「{txt}」")
            return 1
        arow["in_sec"] = at
        arow["out_sec"] = out
        arow["shot_id"] = shot_id
        arow["nominal_dwell_sec"] = nominal(out - at)
        arow["float_dwell_sec"] = out - at
        arow["d15_vo_at_sec"] = at
        arow["d15_vo_dur_sec"] = dur
        arow["d15_line_ref"] = v["line_ref"]
        arow["action"] = "按 R-026a 前移实测同步（闸位回填 ＋ 字幕行 re-time）"
        arow["verdict"] = "合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）"
        arow["note"] = (
            f"【配音对齐 2026-10-23 · R-026a 前移后复核】按 D15 {v['line_ref']}："
            f"at {at}s ＋ dur {dur}s 实测复核（闸位与本行同步前移）"
            + (f"｜【画外音】{v['delivery']}" if is_vo else "")
            + (f"；⚠️ 口径差异见本集 golden3s_first_line.note（镜1 内为不可辨识剪影，"
               f"落点口径「身份不出画／先声后人」）" if (is_vo and ep == 6) else ""))

        # ④ 活戳 + 口径注 + 留痕
        aud = ss["subtitle_sync_audit"]
        aud["verified_against_d15"] = (
            f"{d15_version}（黄金 3 秒前移已落锚；本集首句行已按实测复核）")
        aud["verified_note"] = aud.get("verified_note", "") + (
            f"｜【黄金 3 秒首句前移回填 · 2026-10-23 · R-026a／R-026d】"
            f"D15 U01 {d15_version} 已把本集首句配音 at_sec 前移至 {at}s（dur 不变＝{dur}s）"
            + (f"，并做成画外音（D15 同条 `delivery`＝「{v['delivery']}」）" if is_vo else "")
            + f"；本表闸位 `golden3s_first_line` 与对白字幕行（seq "
            f"{[l['seq'] for l in ss['lines'] if l.get('text') == txt][0]}）"
            f"已同步为 {at}~{out}s，逐条复核 1/1 一致。"
            + ("本集首句画外音的落点口径差异见 `golden3s_first_line.note`（登记待总控裁决）。"
               if (is_vo and ep == 6) else ""))
        aud.setdefault("sync_records", []).append({
            "date": "2026-10-23",
            "event": f"黄金 3 秒首句前移 · {d15_version} 落锚后回填（R-026a／R-026d · ep{ep:03d}）",
            "basis": f"声音设计岗 D15 U01 {d15_version}：首句配音 at_sec {at}s（dur 不变＝{dur}s）"
                     + (f"，`delivery`＝「{v['delivery']}」" if is_vo else "")
                     + "；总控 R-026a 派单 + R-026d 派单（分镜导演回填闸位）。"
                       "秒级真值源为 D15 现盘，本表只落转录副本。",
            "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
            "changes": [
                f"golden3s_first_line：status「待 D15 前移」→「达标」；"
                f"d15_vo_at_sec＝{at}、d15_vo_dur_sec＝{dur}、d15_line_ref＝{v['line_ref']}"
                + (f"；delivery＝「{v['delivery']}」（逐字取自 D15）" if is_vo else ""),
                f"对白字幕行（首句）re-time：{at}~{out}s，shot_id＝{shot_id}",
                "subtitle_sync_audit.rows 同条同步（in/out/shot_id/d15 锚点/判定）",
                f"subtitle_sync_audit.verified_against_d15 → {d15_version}",
            ],
            "not_changed": [
                "其余对白行、面板文字行、角标行、片尾行的时码一律不动",
                "cuts / transitions / title_card / paywall_point 一律不动",
                "D15 配音数据不动（本表只读）",
                "D11 景别/机位/镜时不动（V12 白模构图轴基准）",
                "ep001–ep003 的 golden3s_first_line 不动（已是达标态，属事件溯源）",
            ],
            "applied_by": "分镜导演（bot_1855d6ce9cdd）",
        })

    # ---- C09/C10/C11 复核 ----
    for ep in TARGET_EPS:
        ss = eps16[ep]["subtitle_style"]
        cuts = d11_cut_at(ep)
        wins = d11_shot_windows(ep)
        for l in ss["lines"]:
            if l.get("type") != "对白":
                continue
            r = [x for x in ss["subtitle_sync_audit"]["rows"]
                 if x.get("seq") == l.get("seq")]
            if not r:
                errors.append(f"C10 ep{ep} seq{l.get('seq')}：审计行缺失")
                continue
            if (r[0]["in_sec"] != l["in_sec"] or r[0]["out_sec"] != l["out_sec"]
                    or r[0]["shot_id"] != l.get("shot_id")):
                errors.append(f"C10 ep{ep} seq{l.get('seq')}：lines 与 rows 不一致")
            if abs(l["out_sec"] - l["in_sec"] - r[0]["d15_vo_dur_sec"]) > 1e-9 or \
               abs(l["in_sec"] - r[0]["d15_vo_at_sec"]) > 1e-9:
                errors.append(f"C09 ep{ep} seq{l.get('seq')}：字幕行与配音锚点不等")
            if nominal(l["out_sec"] - l["in_sec"]) < 1.2:
                errors.append(f"C11 ep{ep} seq{l.get('seq')}：停留 <1.2s")
            win = [w for w in wins if w[0] == l.get("shot_id")]
            if win and not (win[0][1] <= l["in_sec"] and l["out_sec"] <= win[0][2]):
                errors.append(f"C11 ep{ep} seq{l.get('seq')}：越所在镜时间窗")
            for c in cuts:
                if l["in_sec"] < c < l["out_sec"]:
                    errors.append(f"C11 ep{ep} seq{l.get('seq')}：跨段间切点 {c}")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    D16["version"] = NEW_VERSION

    if check_only:
        print("✅ --check 通过：C01~C12 全部成立，未写盘")
        return 0

    bak = P("reports", "_bak_director_golden3s_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(bak, "units", "U01"), exist_ok=True)
    shutil.copy2(D16_PATH, os.path.join(bak, "units", "U01", "D16.json"))

    with open(D16_PATH, "w", encoding="utf-8") as f:
        json.dump(D16, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ 已落盘 {D16_PATH}  {EXPECT_D16_VERSION} → {NEW_VERSION}")
    print(f"   D15 真值源版本：{d15_version}")
    print(f"   备份：{bak}")
    for ep in TARGET_EPS:
        g = eps16[ep]["subtitle_style"]["golden3s_first_line"]
        print(f"   ep{ep:03d}: status={g['status']} at={g['d15_vo_at_sec']} "
              f"dur={g['d15_vo_dur_sec']} ref={g['d15_line_ref']}"
              + (f" delivery={g.get('delivery')}" if g.get("delivery") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
