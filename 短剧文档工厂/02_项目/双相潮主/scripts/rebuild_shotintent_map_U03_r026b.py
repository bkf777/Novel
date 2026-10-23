#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按「黄金 3 秒」R-026b 批次（12:04:13）后的现盘，重刷 U03 的 shot_intent 映射表。

起因（2026-10-23 12:03–12:12 实测取证）：
  · R-026b 批次为 **ep018／ep019／ep021／ep022／ep024 五集**各在 `body[1]`
    插入一条首句画外音台词 ＋ 同形 `shot_intent`（D08 v1.4→v1.5）。
    ⇒ 五集各 +1 条 body ⇒ **其后各条 body 下标整体 +1**
    ⇒ `shotintent_map_U03.mjs` 的 idx 锚**整段作废**（57 条 → 现盘 **62** 条），
      覆盖轴① 降为 38/57、exit 1。
  · 本岗内容源（`d08_content_U03.py` v1.5／`d09_content_U03.py` v1.2）与重跑
    已由并行执行体完成并经本岗核验（内容源↔产物 6/6 一致、D08 body+notes 8/8 全等），
    本脚本**只重建映射表**，不碰内容源与交付物 JSON。

重挂方法（沿用本岗既有「以原文为锚」口径，不靠下标位移推算）：
  ① 取改前基线＝批次留存的 `reports/_bak_scriptwriter_u03_golden3s_20261023-120310/units/U03/D08.json`（v1.4）；
  ② 旧映射表每行的 (ep, old_idx) → 取出改前 body[old_idx].shot_intent **原文**；
  ③ 在现盘 v1.5 中按**该原文**定位新下标 new_idx ⇒ 得 (ep, new_idx, 旧镜号, 旧锚点)；
  ④ 五条**新增** shot_intent（各集 body[1]）在改前基线中不存在 ⇒ 另行补入，
     承接镜位取**该集 D11 镜1**（首句台词以画外音在开场镜入画），锚点取镜1
     `visual_facts` 里与该条 `shot_intent` 要求对应的事实的**字面**。

用法：python3 rebuild_shotintent_map_U03_r026b.py [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BAK = os.path.join(PROJ, "reports", "_bak_scriptwriter_u03_golden3s_20261023-120310", "units", "U03", "D08.json")
MAP = os.path.join(HERE, "shotintent_map_U03.mjs")
DISK_D08 = os.path.join(PROJ, "units", "U03", "D08.json")
DISK_D11 = os.path.join(PROJ, "units", "U03", "D11.json")

# 五条新增首句 shot_intent → (承接镜号, 锚点)：锚点取 D11 镜1 visual_facts 的字面事实，
# 与该条 shot_intent 要求对应；均由现盘逐字核对（见 --dry-run 输出）。
NEW_ROWS = {
    18: (1, ["骨威全开", "骨纹自右腕骨一路亮到小臂"]),
    19: (1, ["身份铭牌与敌酋纹章被挂上门柱", "只挂两件金属件"]),
    21: (1, ["分诊台前的队伍拐了两个弯", "排队的人一律作剪影"]),
    22: (1, ["井口开始返出灰雾", "作业的人只余剪影"]),
    24: (1, ["交易条款，和骨井凿进的进度", "两样东西并排占满画面中部"]),
}


def main(dry_run):
    old_disk = json.load(open(BAK, encoding="utf-8"))
    new_disk = json.load(open(DISK_D08, encoding="utf-8"))
    d11 = json.load(open(DISK_D11, encoding="utf-8"))
    old_map = {e["ep"]: e for e in old_disk["episodes"]}
    new_map = {e["ep"]: e for e in new_disk["episodes"]}
    shots11 = {e["ep"]: e.get("shots", []) for e in d11["episodes"]}

    src = open(MAP, encoding="utf-8").read()
    rows = re.findall(r"^\s*\[(\d+),\s*(\d+),\s*(\d+),\s*\[(.*?)\]\],\s*$", src, re.M)
    if not rows:
        print("❌ 未解析到旧映射行")
        sys.exit(1)
    print(f"  旧映射条目 {len(rows)}｜改前基线 v{old_disk.get('version')}｜现盘 v{new_disk.get('version')}"
          f"｜D11 v{d11.get('version')}")

    out = {}
    unmatched = []
    for ep_s, idx_s, sid_s, anc_s in rows:
        ep, idx, sid = int(ep_s), int(idx_s), int(sid_s)
        ob = old_map[ep]["body"]
        if idx >= len(ob):
            unmatched.append((ep, idx, "改前 body 无此下标"))
            continue
        quote = ob[idx].get("shot_intent", "")
        if not quote:
            unmatched.append((ep, idx, "改前该条无 shot_intent"))
            continue
        cand = [i for i, b in enumerate(new_map[ep]["body"]) if b.get("shot_intent", "") == quote]
        if len(cand) != 1:
            unmatched.append((ep, idx, f"原文在现盘定位 {len(cand)} 处"))
            continue
        anchors = json.loads("[" + anc_s + "]")
        out[(ep, cand[0])] = (sid, anchors)
    if unmatched:
        for u in unmatched:
            print(f"  ❌ 未重挂：ep{u[0]} old_idx{u[1]}｜{u[2]}")
        sys.exit(1)
    print(f"  旧 {len(rows)} 行按原文重挂成功 {len(out)} 行")

    # 五条新增 shot_intent 补入
    for ep, (sid, anchors) in NEW_ROWS.items():
        b1 = new_map[ep]["body"][1]
        assert b1.get("shot_intent"), ep
        vf = shots11[ep][sid - 1].get("visual_facts", "")
        miss = [a for a in anchors if a not in vf]
        if miss:
            print(f"  ❌ ep{ep} 新增行锚点不在 D11 镜{sid} visual_facts：{miss}")
            sys.exit(1)
        out[(ep, 1)] = (sid, anchors)
        print(f"  ＋ ep{ep} body[1] → D11 镜{sid}｜锚点 {anchors}｜SI「{b1['shot_intent'][:34]}…」")

    # 完备性：映射占用 idx 集合 ＝ 现盘带 SI 的 idx 集合（两个方向差集都须为空）
    all_si = {(ep, i) for ep, e in new_map.items() for i, b in enumerate(e["body"]) if b.get("shot_intent")}
    miss_map = sorted(all_si - set(out))
    extra_map = sorted(set(out) - all_si)
    print(f"  完备性：现盘带 SI {len(all_si)} 条｜映射 {len(out)} 条｜表缺 {miss_map}｜表多 {extra_map}")
    if miss_map or extra_map:
        sys.exit(1)

    # 生成新表
    lines = []
    for (ep, idx) in sorted(out):
        sid, anchors = out[(ep, idx)]
        anc_txt = ", ".join(json.dumps(a, ensure_ascii=False) for a in anchors)
        lines.append(f"  [{ep}, {idx}, {sid}, [{anc_txt}]],")
    body = "\n".join(lines)
    header = (
        "export const MAP = [\n"
        + body
        + "\n];\n"
    )
    m = re.search(r"export const MAP = \[.*?\n\];\n", src, re.S)
    if not m:
        print("❌ 未定位旧 MAP 块")
        sys.exit(1)
    new_src = src[:m.start()] + header + src[m.end():]
    # 追加式说明（不改上文留痕原文）
    note = (
        "/* ── 【2026-10-23 12:1x · 追加式重建（不改上文留痕原文）】────────────────\n"
        " *   起因：总控「黄金 3 秒」**R-026b** 批次于 12:03:10 备份\n"
        " *   `reports/_bak_scriptwriter_u03_golden3s_20261023-120310/`（内含 edit_script.mjs\n"
        " *   ＋ 改前 D08/D09），12:04:13 重写本岗单写点 `units/U03/D08.json` v1.4→v1.5：\n"
        " *   **ep018／ep019／ep021／ep022／ep024 五集**各在 `body[1]` 插入一条首句画外音\n"
        " *   台词 ＋ 同形 `shot_intent`（「本集首句台词，以画外音在开场镜入画：…秒码由 D15/D16\n"
        " *   承接」）⇒ 五集各 +1 条 body ⇒ **其后各条 body 下标整体 +1** ⇒ 本表 idx 锚\n"
        " *   **整段作废**（57 条 → 现盘 **62** 条），覆盖轴① 曾降为 38/57、exit 1。\n"
        " *   本表按现盘重建：**旧 57 行以「改前 body 原文为锚」在现盘定位新下标**（不靠位移\n"
        " *   推算），**五条新增 shot_intent 另行补入**（承接镜位＝该集 D11 镜1，首句台词以\n"
        " *   画外音在开场镜入画；锚点取镜1 `visual_facts` 的字面事实）。\n"
        " *   完备性：现盘带 SI **62** 条 ＝ 本表受检 **62** 条（两个方向差集均空）。\n"
        " *   ⚠️ 本表为**纯数据模块**（只 `export const MAP`，无任何写盘调用）⇒ Q64「写盘脚本\n"
        " *   须带版本守卫」**不适用**；本表变更的唯一落盘出口是覆盖轴复核。\n"
        " */\n"
    )
    new_src = new_src.replace("export const MAP = [", note + "export const MAP = [", 1)
    if dry_run:
        print("  （--dry-run：不写盘）")
        return
    shutil.copy2(MAP, MAP + ".bak_r026b")
    open(MAP, "w", encoding="utf-8").write(new_src)
    print(f"  ✅ 已重建 {MAP}（{len(out)} 条）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    main(a.dry_run)
