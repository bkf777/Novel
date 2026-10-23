#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_D16_d15_pointer_refresh.py —— D16 审计「活指针」追版（U01／U02）· 分镜导演岗

问题
----
声音设计岗 13:0x–13:2x 落 D15 **U01 v1.14 ／ U02 v1.4**（见台账 §219），
而 D16 U01/U02 的 `subtitle_sync_audit.verified_against_d15` 仍写「v1.13／v1.3」
⇒ 读者按指针去找核对对象会落到**旧版 D15**，这是审计链上的错指针。

⚠️ **只改「活指针」，不碰历史留痕**：
D16 里 `D15 v1.1／v1.4／v1.5／v1.6…` 大量出现，其中绝大多数是
`sync_records`／`d15_version_history` 的**历史陈述**（哪一版做了什么），
全量字符串替换会把审计史改坏。故本脚本只动两处：
  ① `subtitle_sync_audit.verified_against_d15` 的版本前缀（设计上的活指针）；
  ② 追加一条 `sync_records`（追版复核留痕）。

核对依据（本岗当场实测，非沿用旧结论）
--------------------------------------
  · D15 U01 v1.14 ／ U02 v1.4 现盘逐集首句 at_sec 与 D16 `golden3s_first_line.
    d15_vo_at_sec` **逐集相等**（U01 8/8 at=0.5；U02 7 集 0.4、ep012/ep016 0.5）；
  · `node scripts/reconcile_D15_D16_timing.mjs --unit U01|U02` 独立复算
    **零违规**（0 越窗／0 跨切点／字幕与配音逐条同步）——即：数值层零失配，
    旧指针只是**标签过期**，不是数据错误。
  ⇒ 因此本脚本**不改任何 in_sec／out_sec／d15_vo_* 数值**，只更指针与留痕。

守卫：D16 version＝U01 v1.31 ／ U02 v1.10；D15 version＝U01 v1.14 ／ U02 v1.4。
结构差异白名单：只允许动 `/version`、`subtitle_sync_audit/verified_against_d15`、
`subtitle_sync_audit/sync_records/**`；白名单外任一叶子值变化即 ABORT。
"""
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = {
    "U01": {"d16": "v1.31", "d15": "v1.14", "to": "v1.32"},
    "U02": {"d16": "v1.10", "d15": "v1.4", "to": "v1.11"},
}
ALLOW_BASE = (
    "/version",
    "/episodes/%d/subtitle_style/subtitle_sync_audit/verified_against_d15",
    "/episodes/%d/subtitle_style/subtitle_sync_audit/sync_records",
)


def allow_prefixes(n_eps):
    out = []
    for pre in ALLOW_BASE:
        if "%d" in pre:
            out.extend(pre % i for i in range(n_eps))
        else:
            out.append(pre)
    return out


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


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(ROOT, "reports", "_bak_d16_d15ptr_%s" % stamp)
    os.makedirs(bak, exist_ok=True)
    for unit, g in GUARD.items():
        p16 = os.path.join(ROOT, "units", unit, "D16.json")
        p15 = os.path.join(ROOT, "units", unit, "D15.json")
        d16 = json.load(open(p16, encoding="utf-8"))
        d15 = json.load(open(p15, encoding="utf-8"))
        if d16.get("version") != g["d16"]:
            print("[NO-OP] %s D16 version=%s ≠ 守卫 %s" % (unit, d16.get("version"), g["d16"]))
            continue
        if d15.get("version") != g["d15"]:
            print("[ABORT] %s D15 version=%s ≠ 守卫 %s" % (unit, d15.get("version"), g["d15"]))
            continue

        before = dict(flat(d16))
        n_ep = 0
        for e in d16["episodes"]:
            aud = e["subtitle_style"].setdefault("subtitle_sync_audit", {})
            old = str(aud.get("verified_against_d15", "") or "")
            m = re.match(r"^(v[\d.]+)(.*)$", old, re.S)
            if m and m.group(1) != g["d15"]:
                aud["verified_against_d15"] = g["d15"] + m.group(2)
            recs = aud.setdefault("sync_records", [])
            if not any(r.get("event", "").startswith("D15 追版复核") for r in recs):
                recs.append({
                    "date": "2026-10-23",
                    "event": "D15 追版复核（活指针跟版 · 数值零改动）",
                    "basis": ("声音设计岗 13:0x–13:2x 落 D15 %s %s；本表 `verified_against_d15` "
                              "仍写旧版号，读者按指针会核到旧 D15。"
                              "本岗当场实测：D15 现盘逐集首句 at_sec 与本表 "
                              "`golden3s_first_line.d15_vo_at_sec` 逐集相等；"
                              "reconcile_D15_D16_timing 独立复算零违规 ⇒ 数值层零失配，"
                              "旧指针只是标签过期。"
                              % (unit, g["d15"])),
                    "method": ("只把 `verified_against_d15` 的版本前缀跟到 D15 现盘版本；"
                               "**不改任何 in_sec／out_sec／d15_vo_* 数值**；"
                               "历史留痕（sync_records／d15_version_history 里的旧版号）一律不动。"),
                    "not_changed": ["in_sec / out_sec", "d15_vo_at_sec / d15_vo_dur_sec",
                                    "golden3s_first_line 的 status 与全部数值",
                                    "lines[] 任何一行", "D15 本体", "镜数与镜时"],
                    "applied_by": "分镜导演（bot_1855d6ce9cdd）",
                })
            n_ep += 1
        d16["version"] = g["to"]

        after = dict(flat(d16))
        allow = allow_prefixes(len(d16.get("episodes", [])))
        bad = []
        for p, v in after.items():
            if p in before and before[p] != v and not any(p.startswith(x) for x in allow):
                bad.append((p, before[p], v))
        for p in before:
            if p not in after and not any(p.startswith(x) for x in allow):
                bad.append((p, before[p], "<删除>"))
        if bad:
            print("[ABORT] %s 白名单外结构差异 %d 处，未写盘：" % (unit, len(bad)))
            for p, o, n in bad[:20]:
                print("   -", p, repr(o), "→", repr(n))
            return 1

        shutil.copy2(p16, os.path.join(bak, "%s_D16.json" % unit))
        with open(p16, "w", encoding="utf-8") as f:
            json.dump(d16, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("[OK] %s D16 %s → %s：%d 集活指针跟到 D15 %s（数值零改动）"
              % (unit, g["d16"], g["to"], n_ep, g["d15"]))
    print("备份：%s" % bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())
