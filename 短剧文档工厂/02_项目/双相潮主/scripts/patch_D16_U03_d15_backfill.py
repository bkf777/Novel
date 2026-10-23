#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_D16_U03_d15_backfill.py —— U03 D16 按 D15 U03 v1.1 实测回填审计与判据字段

背景
----
声音设计岗已于 13:17 落 `units/U03/D15.json` **v1.2**（此前 U03 D16 v1.0 的
`subtitle_sync_audit` 写的是「D15 U03 尚未落盘／受检 0 条」、`golden3s_first_line`
逐集 status「待 D15 落锚」——那是 D15 缺件时期的占位态，现已过期）。
实测（D15 v1.2 现盘，本岗当场复算）：八集首句**全部** at_sec=0.5（8/8 达标）；
31 条 voice_over 与 D16 对白行**逐条相等**（in_sec＝at_sec，out_sec＝at_sec＋dur_sec；
`reconcile_D15_D16_timing.mjs --unit U03` 独立复算 0 违规）。

本脚本只做「审计镜像与判据字段回填」，口径**逐键照搬**权威实现
`scripts/patch_D16_U01_audit_mirror_and_hook_note.py` 的 `refresh_audit()`：
  · rows[] 只收「对白」行（字幕行无配音锚点，不进 rows[]）；
  · 锚点解析＝vo_by_text 优先、vo_by_ref 兜底（ref→D09 idx→D09 原文）；
  · no_vo_anchor_rows ＝ **type=='面板文字'** 的行数（不是对白数！）；
  · dwell_floor_rows ＝ 对白行中名义停留恰为 1.2s 的行。

⚠️ U03 现盘 no_vo_anchor_rows 写的是 4/3（＝对白行数，D15 缺件期的占位口径），
   与权威口径不符；本脚本刷成真实值（U03 无「面板文字」行 ⇒ 0）。

守卫：U03 D16 version＝v1.1 ／ D15 version＝v1.1；
结构差异白名单：只允许动 `/version`、`subtitle_sync_audit/**`、`golden3s_first_line/**`，
其余任一叶子值变化即 ABORT（防止覆盖并发批次的改动）。
"""
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P16 = os.path.join(ROOT, "units", "U03", "D16.json")
P15 = os.path.join(ROOT, "units", "U03", "D15.json")
P09 = os.path.join(ROOT, "units", "U03", "D09.json")
GUARD_16 = "v1.1"
GUARD_15 = "v1.2"
TO_16 = "v1.2"

# 结构差异白名单（前缀匹配；episodes 下标按 flat() 的数组下标 0 起算）
ALLOW_BASE = (
    "/version",
    "/episodes/%d/subtitle_style/subtitle_sync_audit",
    "/episodes/%d/subtitle_style/golden3s_first_line",
)


def allow_prefixes(n_eps):
    out = []
    for pre in ALLOW_BASE:
        if "%d" in pre:
            out.extend(pre % i for i in range(n_eps))
        else:
            out.append(pre)
    return out


def norm(t):
    return re.sub(r"[「」『』\"'（）()\s]", "", str(t or ""))


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            for x in flat(v, p + "/" + str(k)):
                yield x
    elif isinstance(o, list):
        for i, v in enumerate(o):
            for x in flat(v, p + "/" + str(i)):
                yield x
    else:
        yield p, o


def build_anchor_maps(d15, d09, ep):
    d09map = {l["idx"]: norm(l.get("text")) for l in d09.get("lines", []) if l["ep"] == ep}
    vo_by_text, vo_by_ref = {}, {}
    for e15 in d15.get("episodes", []):
        if e15["ep"] != ep:
            continue
        for v in e15.get("voice_over", []):
            vo_by_text.setdefault(norm(v.get("text")), v)
            m = re.search(r"#(\d+)$", v.get("line_ref") or "")
            if m:
                vo_by_ref[norm(d09map.get(int(m.group(1)), ""))] = v

    def anchor_for(text):
        k = norm(text)
        return vo_by_text.get(k) or vo_by_ref.get(k)

    return anchor_for


def refresh_audit(d16_ep, d15, d09, d15v):
    """按现盘 lines[] 重算一集的审计镜像（口径同 refresh_audit 权威实现）。"""
    ep = d16_ep["ep"]
    ss = d16_ep["subtitle_style"]
    aud = ss["subtitle_sync_audit"]
    anchor_for = build_anchor_maps(d15, d09, ep)

    synced = 0
    no_vo = 0
    floor = []
    rows = []
    pending = []
    for l in ss.get("lines", []):
        t = l.get("type")
        if t == "对白":
            a = anchor_for(l.get("text"))
            in_s = round(float(l["in_sec"]), 1)
            out_s = round(float(l["out_sec"]), 1)
            if a is not None and in_s == round(float(a["at_sec"]), 1) \
                    and abs(out_s - (float(a["at_sec"]) + float(a["dur_sec"]))) < 1e-6:
                synced += 1
                verdict = "合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）"
                action = "不动（D15 %s 落锚后逐条相等）" % d15v
            else:
                verdict = "待 D15 落锚（本行时码为黄金 3 秒目标值，尚未与 D15 锚点对齐）"
                action = "本批新增/改期，待 D15 落锚"
                pending.append({
                    "text": l.get("text"), "type": "对白", "shot_id": l.get("shot_id"),
                    "row_in_sec": in_s, "row_out_sec": out_s,
                    "d15_current_anchor": (None if a is None else
                                           {"at_sec": a["at_sec"], "dur_sec": a["dur_sec"],
                                            "line_ref": a.get("line_ref")}),
                    "action": "待声音设计岗落 D15 后由本岗按实测复核",
                })
            dwell = round(out_s - in_s, 1)
            rows.append({
                "seq": l.get("seq"), "type": "对白", "text": l.get("text"),
                "char_id": l.get("char_id"), "shot_id": l.get("shot_id"),
                "in_sec": in_s, "out_sec": out_s,
                "nominal_dwell_sec": dwell, "float_dwell_sec": out_s - in_s,
                "d15_vo_at_sec": (a["at_sec"] if a else None),
                "d15_vo_dur_sec": (a["dur_sec"] if a else None),
                "d15_line_ref": (a.get("line_ref") if a else None),
                "action": action,
                "verdict": verdict,
                "note": str(l.get("note", "") or ""),
            })
            if abs(dwell - 1.2) < 1e-6:
                floor.append({"seq": l.get("seq"), "text": l.get("text"),
                              "in_sec": in_s, "out_sec": out_s,
                              "nominal_dwell_sec": 1.2, "float_dwell_sec": out_s - in_s})
        elif t == "面板文字":
            no_vo += 1

    aud["synced_row_count"] = synced
    aud["no_vo_anchor_rows"] = no_vo
    if floor:
        aud["dwell_floor_rows"] = floor
    else:
        aud.pop("dwell_floor_rows", None)
    aud["rows"] = rows
    if pending:
        aud["pending_d15_sync"] = pending
    else:
        aud.pop("pending_d15_sync", None)
    aud["verified_against_d15"] = (
        "%s（黄金 3 秒判据落点见 golden3s_first_line；秒级真值回 D15 at_sec 取）" % d15v)
    return aud, len(rows), synced, no_vo, len(pending)


def main():
    d16 = json.load(open(P16, encoding="utf-8"))
    d15 = json.load(open(P15, encoding="utf-8"))
    d09 = json.load(open(P09, encoding="utf-8"))
    if d16.get("version") != GUARD_16:
        print("[NO-OP] U03 D16 version=%s ≠ 守卫 %s" % (d16.get("version"), GUARD_16))
        return 0
    if d15.get("version") != GUARD_15:
        print("[ABORT] U03 D15 version=%s ≠ 守卫 %s" % (d15.get("version"), GUARD_15))
        return 1

    before = dict(flat(d16))
    totals = {"rows": 0, "synced": 0, "no_vo": 0, "pending": 0}
    for e in d16["episodes"]:
        aud, n_rows, n_synced, n_novo, n_pending = refresh_audit(e, d15, d09, GUARD_15)
        totals["rows"] += n_rows
        totals["synced"] += n_synced
        totals["no_vo"] += n_novo
        totals["pending"] += n_pending
        ss = e["subtitle_style"]
        # 黄金 3 秒判据：按 D15 实测回填（Q101：真值回 D15 at_sec）
        g3 = ss.get("golden3s_first_line")
        if g3 is None:
            g3 = {"target": "首句台词 ≤1.5s 入画（短剧黄金 3 秒）"}
            ss["golden3s_first_line"] = g3
        vos = sorted(next(x for x in d15["episodes"] if x["ep"] == e["ep"]).get("voice_over", []),
                     key=lambda v: v.get("at_sec", 0))
        if vos:
            v0 = vos[0]
            if float(v0.get("at_sec", 99)) <= 1.5:
                g3["status"] = "达标"
                g3["d15_vo_at_sec"] = v0.get("at_sec")
                g3["d15_vo_dur_sec"] = v0.get("dur_sec")
                g3["d15_line_ref"] = v0.get("line_ref")
                for k in ("planned_in_sec", "planned_out_sec", "budget_dur_sec",
                          "current_d15_vo_at_sec", "current_d15_line_ref", "d15_pending"):
                    g3.pop(k, None)
                old_note = str(g3.get("note", "") or "").rstrip("｜")
                g3["note"] = (
                    old_note + "｜" if old_note else "") + (
                    "D15 %s 实测：首句 at_sec=%.1fs（≤1.5s 达标），本表该行与配音逐条相等。"
                    % (GUARD_15, float(v0.get("at_sec"))))
            else:
                g3["status"] = "待 D15 前移"
                g3["current_d15_vo_at_sec"] = v0.get("at_sec")
                g3["current_d15_line_ref"] = v0.get("line_ref")
                g3["target_at_sec"] = 0.5
                g3["d15_pending"] = ("声音设计岗需把本集首句配音 at_sec 前移至 0.5s（dur 不变），"
                                     "本岗随后按实测同步本表该行。")
    d16["version"] = TO_16

    # ── 结构差异白名单核对：白名单外任一叶子值变化即 ABORT ──
    after = dict(flat(d16))
    allow = allow_prefixes(len(d16.get("episodes", [])))
    bad = []
    for p, v in after.items():
        if p in before and before[p] != v:
            if not any(p.startswith(pre) for pre in allow):
                bad.append((p, before[p], v))
    for p in before:
        if p not in after and not any(p.startswith(pre) for pre in allow):
            bad.append((p, before[p], "<删除>"))
    if bad:
        print("[ABORT] 白名单外结构差异 %d 处，未写盘：" % len(bad))
        for p, o, n in bad[:20]:
            print("   -", p, repr(o), "→", repr(n))
        return 1

    bak = os.path.join(ROOT, "reports",
                       "_bak_d16_U03_d15back_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(P16, os.path.join(bak, "U03_D16.json"))
    with open(P16, "w", encoding="utf-8") as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("[OK] U03 D16 %s → %s：审计镜像与黄金 3 秒判据按 D15 %s 回填"
          % (GUARD_16, TO_16, GUARD_15))
    print("     对白行 %d 条／逐条相等 %d 条／面板文字(无配音锚点) %d 条／待 D15 同步 %d 条"
          % (totals["rows"], totals["synced"], totals["no_vo"], totals["pending"]))
    print("     备份：%s" % bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())
