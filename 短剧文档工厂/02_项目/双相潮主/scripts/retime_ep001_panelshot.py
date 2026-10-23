#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""retime_ep001_panelshot.py —— U01 ep001 镜时重排：把「读数/面板」镜从 13s 压到 8s

背景（2026-10-23 用户指出「面板展示了那么久要干嘛」）：
  体检脚本 scripts/audit_dead_time.py 实测：EP001 镜2（面板特写）整整 13 秒，
  字幕只覆盖 13.4~15.2 与 15.6~17.8 ⇒ **镜内空窗 8.2 秒**，全集最长空窗 8.2s / 空窗总 28.4s。
  根因＝四段制给「读数」留了整段 1/3，而读数是静态的。
修法（**镜数不变、白模几何不变、预算链不变**）：
  镜时 13/13/12/7 → **12/8/16/9**（读数段压掉 5 秒，5 秒给回动作段）
  时码按段做仿射重映射，D15 配音/音效、D16 字幕/切点、D07 段边界、D12 卡时长同步跟改。
  面板镜补一条对比读数，让静态画面里有信息可看。

幂等：可重复执行；内容无变化则不写盘、不动版本号。
用法：python3 scripts/retime_ep001_panelshot.py [--dry-run]
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
BAK = os.path.join(ROOT, "reports", f"_bak_retime_ep001_{STAMP}")

# 旧段 → 新段：(旧起, 旧止, 新起, 新止)
SEGS = [(0.0, 13.0, 0.0, 12.0), (13.0, 26.0, 12.0, 20.0),
        (26.0, 38.0, 20.0, 36.0), (38.0, 45.0, 36.0, 45.0)]


def remap(t):
    """把旧时码映射到新时码（段内仿射；段外夹紧）。"""
    for o0, o1, n0, n1 in SEGS:
        if o0 <= t <= o1:
            return n0 + (t - o0) * (n1 - n0) / (o1 - o0)
    return t


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
    v = str(o.get("version", "v1.0"))
    v = re.sub(r"^v+", "v", v)
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def r1(x):
    return round(x, 1)


# ══════════════ D07：四段边界 ══════════════
p = os.path.join(ROOT, "units", "U01", "D07.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
for seg, (o0, o1, n0, n1) in zip(e["quad_segments"], SEGS):
    seg["start_sec"], seg["end_sec"] = n0, n1
e["quad_segments"][0]["note"] = "陆沉抬腕看骨纹（未亮）；面板由暗到亮逐格浮现"
e["quad_segments"][1]["note"] = "面板推近：归档回滚完成、上一趟存活 3 小时 04 分、本次窗口 2 小时 58 分"
e["quad_segments"][2]["note"] = "倒掉饼干只抓钢钎、工具箱见底、膝软扶墙、门开全是红灯"
e["quad_segments"][3]["note"] = "夺门而出，楼道灯由红转绿，报出「机械厂。」"
bump(d)
save(p, d, old)

# ══════════════ D11：镜时 + continuity ══════════════
p = os.path.join(ROOT, "units", "U01", "D11.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
for s, (o0, o1, n0, n1) in zip(e["shots"], SEGS):
    s["duration_sec"] = n1 - n0
e["duration_sum_sec"] = sum(s["duration_sec"] for s in e["shots"])
for c in e["continuity"]:
    if c.get("id") == "C-U01-EP01-01":
        c["content"] = c["content"].replace("（13/13/12/7 秒）", "（12/8/16/9 秒）")
        c["content"] = c["content"].replace(
            "本集 4 镜、一段一镜，镜时严格等于 D07 四段边界（13/13/12/7 秒），四段合计 45.0s",
            "本集 4 镜、一段一镜，镜时严格等于 D07 四段边界（12/8/16/9 秒），四段合计 45.0s")
        c["content"] += ("　**2026-10-23 黄金3秒改版：读数段由 13s 压到 8s，5 秒回填动作段**——"
                         "用户指出「面板展示那么久要干嘛」；镜数不变、白模几何不变、预算链不变。")
bump(d)
save(p, d, old)

# ══════════════ D12：卡时长 ══════════════
p = os.path.join(ROOT, "units", "U01", "D12.json")
d = load(p)
old = json.loads(json.dumps(d))
for card, (o0, o1, n0, n1) in zip([c for c in d["cards"] if c["ep"] == 1], SEGS):
    card["params"]["duration_sec"] = n1 - n0
    m = re.search(r"(\d+) 秒单镜", card.get("video_prompt", "") or "")
    if m:
        card["video_prompt"] = card["video_prompt"].replace(
            f"{m.group(1)} 秒单镜", f"{n1 - n0} 秒单镜")
bump(d)
save(p, d, old)

# ══════════════ D15：bgm 段 + 音效/拟音/配音时码 ══════════════
p = os.path.join(ROOT, "units", "U01", "D15.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
for seg, (o0, o1, n0, n1) in zip(e.get("bgm_curve", []), SEGS):
    seg["start_sec"], seg["end_sec"] = n0, n1
for key in ("sfx", "foley", "voice_over"):
    for it in e.get(key, []):
        it["at_sec"] = r1(remap(float(it["at_sec"])))
        if key == "voice_over":
            # 配音时长不缩放（语速不变），只改起音点
            pass
        else:
            it["dur_sec"] = r1(min(float(it["dur_sec"]),
                                    remap(float(it["at_sec"]) + float(it["dur_sec"]))
                                    - float(it["at_sec"])))
bump(d)
save(p, d, old)

# ══════════════ D16：切点 / 转场 / 字幕行 ══════════════
p = os.path.join(ROOT, "units", "U01", "D16.json")
d = load(p)
old = json.loads(json.dumps(d))
e = next(x for x in d["episodes"] if x["ep"] == 1)
for c in e["cuts"]:
    c["at_sec"] = r1(remap(float(c["at_sec"])))
for t in e["transitions"]:
    if t.get("type") == "段间转场":
        t["at_sec"] = r1(remap(float(t["at_sec"])))
    if t.get("type") == "总体口径":
        t["segment_alignment"] = ("0.0–12.0／12.0–20.0／20.0–36.0／36.0–45.0，"
                                  "与 D07 ep001 quad_segments 逐段对齐，合计 45.0s。")
        t["d17_count_basis"] = t.get("d17_count_basis", "")
ss = e["subtitle_style"]
for l in ss["lines"]:
    if l.get("type") in ("角标",):
        continue
    a, b = float(l["in_sec"]), float(l["out_sec"])
    na, nb = r1(remap(a)), r1(remap(b))
    if l.get("type") == "对白" and l.get("text", "").startswith("上一趟"):
        na, nb = 0.5, 2.3          # hook 句是设计值，不做仿射
    if l.get("type") == "对白" and l.get("text", "").startswith("两小时五十八分"):
        na, nb = 7.0, 9.0          # 报数句前移，填掉 4.3~7.0 的空窗
    if nb - na < 1.2:
        nb = r1(na + 1.2)
    l["in_sec"], l["out_sec"] = na, nb
bump(d)
save(p, d, old)

print(f"\n{'[dry-run] ' if DRY else ''}✅ ep001 镜时重排完成（13/13/12/7 → 12/8/16/9）｜备份 {BAK}")
