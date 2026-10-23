#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_u01_tts_items_stale_flag.py —— U01 预演 TTS 清单（`preview/U01_tts/items.json`）的两类就地订正

派活来源
  企划合规 2026-10-23 05:2x（batch_6a5961e5e130 / task_0a3ee4732ed9）：
  「`items.json` 里 ep2#4 旧句条目标注为『音频待出片阶段重合成』」。
  声音设计 2026-10-23 10:0x（台本编剧 ep8#4 排轴口径派单）：扩展出「dur 回填」分支。

本脚本有三条正交职责
  ① mark     给「台词已被上游改写」的旧音频条目标注 stale（首版职责，行为不变）
  ② refresh  回填 `dur` 字段 —— 以 **ffprobe 实测** 为准订正生成物里的陈旧记录值
  ③ clear    当某条**已完成重合成**（items.json 的 text 已同步为新句）时，清掉 stale 标注
              并回填新 dur

为什么「就地订正」而不是 `build_tts_u01.py` 重跑
  `items.json` 是 2026-10-23 05:12 依**当时的 D08/D09** 生成的产物；上游台词已变，
  重跑会用新 D08 重建整份清单并指向尚不存在的音频文件，**破坏这份实况记录**。
  故本脚本**就地订正**、不重建清单，且**幂等**（已达目标态则 no-op）。

② 的依据（为何以实测为准，而不是信 `dur` 字段）
  `check_tts_vs_d15_budget.py` 的判定基准已明文：「实测 = ffprobe format=duration
  （毫秒级精度，**只信实测、不信 items.json 的 dur 字段**）」。
  ⇒ `dur` 是**记录值**，实测是**事实值**；两者不一致时，事实值优先。
  ⇒ 本脚本的 ffprobe 调用与 `check_tts_vs_d15_budget.py` **完全同口径**（同一 argv 形态）。

③ 的清标条件（严格）
  只有当 items.json 该条的 `text` **已经等于** `stale_new_text`（即台词层已同步）时，
  才认为「该条已重合成」→ 清 stale 标注并回填 dur。
  ⚠️ 若 text 仍是旧句 ⇒ 音频仍是旧句版本，**不得清标、不得回填 dur**（实测值此时无意义）。

沙箱
  `SXR_ROOT` 覆盖项目根（与本岗 `build_D15_U01.py` / `build_D15_U02.py` 同型），负测只在副本。

边界
  只改 `preview/<unit>_tts/items.json`；不碰任何交付物 JSON（D15/D16/…）、不碰音频文件、
  不合成音频、不调用任何付费生成、不改 D15 预算。

用法
  python3 scripts/patch_u01_tts_items_stale_flag.py --project . [--unit U01] [--mode mark|refresh|clear|all]
  默认 --mode all（等价于依次跑 mark → refresh → clear）。
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time

# 上游压缩后的新台词 → 旧句（预演音频仍为旧句）
STALE = {
    "U01": [{
        "item_id": "ep002_13",
        "old_text": "「两小时五十八分……换我用了。」",
        "new_text": "「换我用了。」",
        "upstream": "D08 U01 v1.9 ／ D09 U01 v1.5（企划合规 U01-R18 终表 seq9_text_change）",
        "reason": "台词已由上游压缩，本条音频为旧台词版本（实测 2.953s，超出 D15 v1.4 预算 1.8s）",
        "action": "音频待出片阶段重合成",
    }],
}

# dur 不一致的判定阈值 —— 与 check_tts_vs_d15_budget.py 的
# `items_json_dur_mismatch_count` 判定**同阈值**（|delta| > 0.05s）
DUR_TOLERANCE = 0.05

# 沙箱自测用 SXR_ROOT 覆盖根目录 —— 副本与真盘完全隔离
ROOT = os.environ.get("SXR_ROOT", "/Users/ezreal/projects/小说创作/短剧文档工厂")


def dur_of(path):
    """实测音频时长（秒）。与 check_tts_vs_d15_budget.py 的 dur_of() 完全同口径。"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None


def do_mark(items, by_id, unit):
    """① 给旧句条目打 stale 标注（首版职责，行为不变）。返回 (changed, notes)。"""
    changed = 0
    notes = []
    for spec in STALE.get(unit, []):
        it = by_id.get(spec["item_id"])
        if it is None:
            notes.append("[WARN] 清单中无 %s，跳过" % spec["item_id"])
            continue
        if it.get("text") != spec["old_text"]:
            notes.append("[WARN] %s 文本已非旧句（现为 %r），跳过"
                         % (spec["item_id"], it.get("text")))
            continue
        if it.get("stale_audio"):
            notes.append("[NO-OP] %s 已标注" % spec["item_id"])
            continue
        it["stale_audio"] = True
        it["stale_reason"] = spec["reason"]
        it["stale_new_text"] = spec["new_text"]
        it["stale_upstream"] = spec["upstream"]
        it["stale_action"] = spec["action"]
        changed += 1
        notes.append("已标注 %s" % spec["item_id"])
    return changed, notes


def do_refresh(items, by_id, unit):
    """② 以 ffprobe 实测回填 `dur`（只对「台词层已同步」的条目）。

    跳过条件：① stale_audio 仍为真（音频还是旧句版本，实测值无意义）
              ② 音频文件不存在
              ③ 非 dialogue
    """
    changed = 0
    notes = []
    for it in items:
        if (it.get("kind") or "") != "dialogue":
            continue
        iid = it.get("id")
        apath = it.get("audio")
        if not apath or not os.path.exists(apath):
            notes.append("[SKIP] %s 无音频文件，跳过" % iid)
            continue
        if it.get("stale_audio"):
            notes.append("[SKIP] %s 仍为旧句版本（stale_audio=true），实测值不适用于当前音频，"
                         "待重合成后再刷" % iid)
            continue
        actual = dur_of(apath)
        if actual is None:
            notes.append("[SKIP] %s ffprobe 未能读出时长，跳过" % iid)
            continue
        old = it.get("dur")
        if isinstance(old, (int, float)) and abs(float(old) - actual) <= DUR_TOLERANCE:
            notes.append("[NO-OP] %s dur 与实测一致（%.6f）" % (iid, actual))
            continue
        it["dur"] = round(actual, 6)
        changed += 1
        notes.append("回填 %s dur %s → %.6f（ffprobe 实测）" % (iid, old, actual))
    return changed, notes


def do_clear(items, by_id, unit):
    """③ 台词层已同步 ⇒ 视为已重合成 ⇒ 清 stale 标注（dur 由 ② 负责回填）。"""
    changed = 0
    notes = []
    for spec in STALE.get(unit, []):
        iid = spec["item_id"]
        it = by_id.get(iid)
        if it is None:
            notes.append("[WARN] 清单中无 %s，跳过" % iid)
            continue
        if not it.get("stale_audio"):
            notes.append("[NO-OP] %s 无 stale 标注" % iid)
            continue
        if it.get("text") != spec["new_text"]:
            notes.append("[SKIP] %s 台词层未同步（现为 %r，应为 %r）⇒ 音频仍是旧句版本，"
                         "不得清标" % (iid, it.get("text"), spec["new_text"]))
            continue
        for k in ("stale_audio", "stale_reason", "stale_new_text", "stale_upstream", "stale_action"):
            it.pop(k, None)
        changed += 1
        notes.append("已清 stale 标注：%s（台词层已同步，视为已重合成）" % iid)
    return changed, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U01")
    ap.add_argument("--mode", default="all",
                    choices=["mark", "refresh", "clear", "all"])
    ap.add_argument("--check", action="store_true",
                    help="只校验并打印将要发生的改动，不写盘")
    args = ap.parse_args()
    P = os.path.abspath(args.project)
    u = args.unit

    path = os.path.join(P, "preview", "%s_tts" % u, "items.json")
    if not os.path.exists(path):
        print("[FATAL] 缺 %s" % path, file=sys.stderr)
        return 2

    items = json.load(io.open(path, encoding="utf-8"))
    by_id = {it["id"]: it for it in items}

    total = 0
    all_notes = []
    if args.mode in ("mark", "all"):
        c, n = do_mark(items, by_id, u)
        total += c
        all_notes += n
    if args.mode in ("refresh", "all"):
        c, n = do_refresh(items, by_id, u)
        total += c
        all_notes += n
    if args.mode in ("clear", "all"):
        c, n = do_clear(items, by_id, u)
        total += c
        all_notes += n

    for line in all_notes:
        print(line)

    if not total:
        print("清单未变化（no-op）")
        return 0

    if args.check:
        print("（--check：将改动 %d 处，未写盘）" % total)
        return 0

    # 本岗备份纪律（U02-R10）：备份统一落 reports/_bak_*，不入 units/ 交付目录
    bak_dir = os.path.join(P, "reports", "_bak_U01_tts_items_" + time.strftime("%Y%m%d-%H%M%S"))
    if os.path.isdir(bak_dir):
        shutil.rmtree(bak_dir)
    os.makedirs(bak_dir)
    shutil.copy2(path, os.path.join(bak_dir, "items.json"))

    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print("已订正 %d 处 → %s（备份 %s）" % (total, path, bak_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
