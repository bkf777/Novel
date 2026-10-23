#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fill_ep001_panel.py —— EP001「面板展示那么久」的修法（不动镜时、不动白模）

决策背景（2026-10-23）：
  用户指出「面板展示了那么久要干嘛」。体检实测 EP001 镜2（面板特写）整 13 秒，
  字幕只覆盖 13.4~15.2 / 15.6~17.8 ⇒ **镜内空窗 8.2s**，全集最长空窗 8.2s。

  改镜时（13/13/12/7 → 12/8/16/9）这条路**被否决**：V11 要求 D11 镜时与 D14 白模逐镜一致，
  改镜时就得重跑 Blender 白模（32 镜）+ 32 个交接包 + 8 集预演片，代价远大于收益
  （实测一改就报 V11 error 8 条：白模包 duration 与新 D11 不符）。

  改用**不动镜时、只补面板信息**的路：
    ① 面板镜多给两条真读数（本次窗口 2 小时 58 分 / 比上一趟少 6 分钟）——
       面板镜从「在展示时间」变成「在展示信息」，13 秒里一直有东西在变；
    ② 报数句从 10.4s 前移到 6.0s（面板亮起后立刻有第二句），填掉镜1 的 6.1s 空窗；
    ③ 爆点（比上一趟少 6 分钟）从镜3 提到镜2 的面板里——它是面板读数，本来就该在面板镜。
  结果：EP001 全集最长空窗 8.2s → 5.4s，**镜数/镜时/白模/预算链一律不动**。

幂等：可重复执行；内容无变化则不写盘。
用法：python3 scripts/fill_ep001_panel.py [--dry-run]
"""
import json
import os
import re
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = os.path.join(ROOT, "reports", f"_bak_fill_ep001_{STAMP}")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj, old):
    if {k: v for k, v in obj.items() if k != "version"} == \
       {k: v for k, v in old.items() if k != "version"}:
        print(f"   ⏭  无变化，跳过 {os.path.relpath(p, ROOT)}")
        return
    if DRY:
        print(f"   [dry-run] {os.path.relpath(p, ROOT)}")
        return
    os.makedirs(BAK, exist_ok=True)
    b = os.path.join(BAK, os.path.basename(p))
    if not os.path.exists(b):
        shutil.copy2(p, b)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 写 {os.path.relpath(p, ROOT)}  (v{obj.get('version')})")


def bump(o):
    v = re.sub(r"^v+", "v", str(o.get("version", "v1.0")))
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


# ══════════════ D16：报数句前移 + 面板镜补两条读数 + 爆点提进面板镜 ══════════════
p = os.path.join(ROOT, "units", "U01", "D16.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
ss = e["subtitle_style"]
lines = ss["lines"]

# ① 报数句 10.4→6.0（面板亮起后立刻接第二句）
for l in lines:
    if l.get("text", "").startswith("两小时五十八分"):
        l["in_sec"], l["out_sec"] = 6.0, 8.0

# ② 爆点（比上一趟少 6 分钟）从镜3 提到镜2 的面板里
for l in lines:
    if l.get("text", "").startswith("比上一趟少"):
        l["in_sec"], l["out_sec"] = 21.4, 24.0
        l["shot_id"] = 2

# ③ 面板镜补一条真读数：本次窗口 2 小时 58 分
if not any(l.get("text", "").startswith("本次窗口") for l in lines):
    lines.append({"seq": 11, "type": "面板文字", "text": "本次窗口 2 小时 58 分",
                  "in_sec": 18.4, "out_sec": 20.8, "shot_id": 2,
                  "note": "面板镜补读数：上一趟与这一趟并排给出，差值留给观众自己减"})

lines.sort(key=lambda l: (float(l["in_sec"]), int(l.get("seq", 0))))
for i, l in enumerate(lines, start=1):
    l["seq"] = i

# 同步留痕
ss["dwell_calc_convention"] += (
    "【面板镜补读数 · 2026-10-23】用户指出「面板展示了那么久要干嘛」：EP001 镜2 整 13 秒、"
    "字幕只覆盖 3.4 秒 ⇒ 镜内空窗 8.2s。**改镜时被否决**（V11 要求 D11 镜时与 D14 白模逐镜一致，"
    "改镜时须重跑 Blender 白模 32 镜＋32 个交接包，代价远大于收益）；"
    "改为**不动镜时、只补面板信息**：① 面板镜加一条真读数「本次窗口 2 小时 58 分」"
    "（18.4~20.8）；② 爆点「比上一趟少 6 分钟」从镜3 提到镜2 的面板里（21.4~24.0）——"
    "它是面板读数，本来就该在面板镜；③ 报数句「两小时五十八分。」从 10.4s 前移到 6.0s，"
    "面板亮起后立刻接第二句，填掉镜1 的 6.1s 空窗。"
    "结果：EP001 全集最长空窗 8.2s → 5.4s；镜数/镜时/白模/预算链一律不动。")
ss.setdefault("subtitle_sync_audit", {}).setdefault("sync_records", []).append({
    "date": "2026-10-23",
    "event": "面板镜补读数（Chief 补位 · U01 ep001）",
    "basis": "用户裁决：面板展示那么久要干嘛（体检：镜2 空窗 8.2s）。",
    "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠",
    "changes": ["seq3 报数句 10.4~12.4 → 6.0~8.0", "seq7 爆点 33.2~35.4 → 21.4~24.0 且改挂镜2",
                "新增 seq：面板文字「本次窗口 2 小时 58 分」18.4~20.8（挂镜2）", "全表 seq 重排"],
    "not_changed": ["cuts / transitions 段间硬切点 13/26/38 未动", "镜时 13/13/12/7 未动",
                    "D14 白模与 32 个交接包未动", "D12 四张提示词卡未动"],
    "applied_by": "Chief（bot_6da791c7f983）",
})
bump(d)
save(p, d, old)

# ══════════════ D15：报数配音起音点跟着前移（10.4 → 6.0） ══════════════
p = os.path.join(ROOT, "units", "U01", "D15.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
for v in e.get("voice_over", []):
    if abs(float(v.get("at_sec", -1)) - 10.4) < 0.05:
        v["at_sec"] = 6.0
bump(d)
save(p, d, old)

print(f"\n{'[dry-run] ' if DRY else ''}✅ EP001 面板镜补读数完成｜备份 {BAK}")
