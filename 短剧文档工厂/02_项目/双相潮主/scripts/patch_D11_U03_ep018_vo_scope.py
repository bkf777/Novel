#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D11_U03_ep018_vo_scope.py —— **按 Chief 13:56 裁决书 §五，把 ep018 镜1 的画外音口径写进 D11 note**

裁决原文（reports/CHIEF裁决_20261023-1356.md §五「裁决：ep018『画外音 vs 身份不出画』冲突」）
------------------------------------------------------------------------------
  「**两者不冲突，是同一件事的两种写法。** D11 镜1 镜的是**右腕骨+小臂的局部**，不是「陆沉的脸或全身」。」
  「⇒ **口径收口为**：**「出局部（骨纹/腕/臂），不出人物本体（脸/全身/可辨识人形）」**，两者同时成立。」
  「1. **@分镜导演**：D11 ep018 镜1 的 `visual_facts` 与 `dialogue` **保持现状即可**（局部镜 + 台词），
      但 `note` 须显式写明「**角色不入画，台词为画外音，出画的是右腕骨局部**」
      ——**以便 Q104 的 `vo_type=offscreen` 有据可填**。」

本脚本做什么
------------------------------------------------------------------------------
  · **只改** `units/U03/D11.json` 的 ep018 镜1 `note`（**追加式**，Q30：既有正文一字不改不删）
  · `visual_facts` / `dialogue` / 景别 / 机位 / 焦距 / 运镜 / 镜时 / 镜号 **一律不动**
    （裁决明写「保持现状即可」⇒ 不需要重出 D12 提示词卡与 D14 白模）
  · 追加段同时写明：口径收口原文、取代上文「登记待总控裁决」的登记、
    D12 现盘核对证据（ep18 镜1 image_prompt 无脸/无全身/无可辨识人形 ⇒ D12 v1.4 已合规）、
    以及**豁免口径提醒**（白模侧**有**腕骨代理体，豁免不能只看「CHAR 代理体数为 0」——
    否则会把「只有局部」误当「完全无人」豁免掉；该条归规则侧/白模侧，本岗只留痕不代改）

守卫：版本守卫 ＋ sha256 并发守卫 ＋ 结构差异白名单（**只允许** note 键与 /version 变化）
      ＋ 写前备份 ＋ 写后回读复核 ＋ 幂等（标记命中即跳过）

用法：python3 scripts/patch_D11_U03_ep018_vo_scope.py [--dry-run]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D11 = os.path.join(ROOT, "units", "U03", "D11.json")
REPORTS = os.path.join(ROOT, "reports")
RULES = os.path.join(os.path.dirname(ROOT), "..", "03_规格", "rules.json")

GUARD_VERSION = "v1.1"
MARK = "【ep018 画外音口径 · Chief 13:56 裁决书 §五 · 已闭合】"

APPEND = (
    "｜" + MARK +
    "口径收口（裁决原文）：**「出局部（骨纹/腕/臂），不出人物本体（脸/全身/可辨识人形）」** —— "
    "两者**同时成立**、是同一件事的两种写法："
    "**① 角色不入画**（陆沉**人物本体**＝脸、全身、可辨识人形，**一律不出画**）；"
    "**② 台词为画外音**（本镜 `dialogue`「原来能这么用。」是画外音／先声后人，"
    "D08 v1.5 body[1] 与 D15 `delivery` 口径据此判定，Q104 的 `vo_type=offscreen` 有据可填）；"
    "**③ 出画的是右腕骨局部**（画面主体与钩子载体＝右腕骨至小臂的骨纹，"
    "属**不可辨识的身体局部**，不是人物本体）。"
    "**本段取代**上文「与 delivery 字面『人物不出画』的差异**登记待总控裁决，本岗不自行改判**」"
    "（该登记已由 Chief 13:56 裁决书 §五闭合，**上游裁决优先于本岗先前的待裁登记**）。"
    "**`visual_facts` 与 `dialogue` 按裁决「保持现状即可」** ⇒ 本镜**不需重出 D12 提示词卡、不需重出 D14 白模**。"
    "现盘核对（只读）：D12 U03 v1.4 ep018 镜1 `image_prompt` 写「骨纹自右腕骨一路亮到小臂…"
    "骨纹只走体表发光，不破体不见皮下骨骼」，**未写脸、未写全身、未写可辨识人形** ⇒ D12 侧已与本口径一致。"
    "⚠️ **豁免口径提醒（归规则侧/白模侧，本岗只留痕不代改）**：本镜白模**有**腕骨代理体"
    "（只是 `CHAR` 前缀分类未覆盖），故 **V12 豁免不能只看「CHAR 代理体数为 0」** —— "
    "须同时校验 D11 是否声明了**可辨识人形**：声明了可辨识人形 ⇒ 不豁免；"
    "只有不可辨识局部 ⇒ 属「局部镜」，与「完全无人空镜」必须**分开判**。"
    "**景别／机位／焦距／运镜／镜时／镜号／时长一律不动**（镜1 是 V12 白模构图轴基准）。"
)


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


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


def die(msg, code=1):
    print("[ABORT] " + msg)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = open(D11, "rb").read()
    read_sha = hashlib.sha256(raw).hexdigest()
    d = json.loads(raw.decode("utf-8"))
    ver = d.get("version")
    if ver != GUARD_VERSION:
        die("D11 U03 version=%s ≠ 守卫 %s" % (ver, GUARD_VERSION))

    # 定位 ep018 镜1
    ep_i = shot_i = None
    for i, e in enumerate(d.get("episodes", [])):
        if int(e.get("episode_id") or e.get("ep")) != 18:
            continue
        for j, s in enumerate(e.get("shots", [])):
            if int(s.get("shot_id")) == 1:
                ep_i, shot_i = i, j
    if ep_i is None:
        die("D11 U03 未找到 ep018 镜1")
    ep = d["episodes"][ep_i]
    sh = ep["shots"][shot_i]
    note = str(sh.get("note", "") or "")

    if MARK in note:
        print("[IDEMPOTENT] ep018 镜1 note 已含本轮闭合标记，未写盘。")
        return 0

    before_facts = sh.get("visual_facts")
    before_dlg = sh.get("dialogue")
    before_shot = {k: sh.get(k) for k in ("shot_size", "camera_angle", "lens_mm", "movement",
                                          "duration_sec", "shot_id", "global_shot_no")}
    new_note = note + APPEND
    sh["note"] = new_note

    # 禁词自检（V5 forbidden_words，含 note 全文）
    try:
        rules = json.load(open(RULES, encoding="utf-8"))
        for w in rules.get("forbidden_words", []):
            if w and w in new_note:
                die("追加段命中 V5 禁用词「%s」" % w)
    except FileNotFoundError:
        print("[WARN] 未找到 rules.json，跳过禁词自检")

    d["version"] = "v%d.%d" % (int(ver[1:].split(".")[0]), int(ver[1:].split(".")[1]) + 1)

    # 结构差异白名单：只允许 note 与 /version 变
    before = dict(flat(json.loads(raw.decode("utf-8"))))
    after = dict(flat(d))
    allow = {"/episodes/%d/shots/%d/note" % (ep_i, shot_i), "/version"}
    for k in set(before) | set(after):
        if k in allow:
            continue
        if before.get(k) != after.get(k):
            die("白名单外变化：%s" % k)
    # 不变量：visual_facts / dialogue / 镜头参数零改动
    assert sh.get("visual_facts") == before_facts
    assert sh.get("dialogue") == before_dlg
    for k, v in before_shot.items():
        assert sh.get(k) == v, "镜头参数被改：%s" % k

    print("追加段长度：%d 字符（note 由 %d → %d）" % (len(APPEND), len(note), len(new_note)))
    print("新增内容尾部：…%s" % new_note[-220:])

    if args.dry_run:
        print("\n[dry-run] 不写盘。")
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(REPORTS, "_bak_D11_U03_ep018_vo_scope_%s" % ts)
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(D11, os.path.join(bak, "D11.json"))
    if sha16(D11) != read_sha[:16]:
        die("并发写者已改盘（sha %s → %s），本岗不覆盖他人字节" % (read_sha[:16], sha16(D11)), 5)
    tmp = D11 + ".tmp.%s" % ts
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, D11)
    # 写后回读
    chk = json.load(open(D11, encoding="utf-8"))
    s2 = chk["episodes"][ep_i]["shots"][shot_i]
    if MARK not in str(s2.get("note", "")):
        die("写后回读失败：闭合标记不在位", 4)
    if s2.get("visual_facts") != before_facts or s2.get("dialogue") != before_dlg:
        die("写后回读失败：visual_facts/dialogue 被改", 4)
    print("\n落盘完成：D11 U03 %s → %s｜sha16 %s → %s｜备份 %s" % (
        ver, chk["version"], read_sha[:16], sha16(D11), os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
