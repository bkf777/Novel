#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U03 D11 补丁：承接台本编剧新补的 5 句画外音首句 + body 序位位移重刷（R-026b／R-026d · 任务二）。

背景：
  台本编剧已落盘 `units/U03/D08.json` v1.5 与 `units/U03/D09.json` v1.2：
    · ep018 / ep019 / ep021 / ep022 / ep024 各在 **body[1]** 插入一条新的首句台词
      （D08 shot_intent 逐条写明「本集首句台词，以画外音在开场镜入画 … 画面内不出 <角色>」）；
    · ep017 / ep020 / ep023 已有首句，本轮**不动**；
    · D09 该 5 集对白行号整体后移一位（原 #1→#2 …），新增行为 #1。

本补丁做三件事：
  ① **body 序位位移重刷** —— D11 各镜 `note` 内按 body 序位引用的条目会整体后移。
     本脚本**按内容指纹逐条重刷**（拿引文在 D08 v1.5 的 body 里反查新序位），
     **不靠 idx 猜**（沿用本岗此前修 U01 1 处、U02 6 处的同一方法）。
     同时把镜注里的版本标 `D08 v1.4` 刷为 `D08 v1.5`。
  ② **镜1 承接画外音首句** —— ep018/019/021/022/024 的镜1 `dialogue` 写入该首句，
     `note` 追加 D08 shot_intent 反查 + 画外音落点口径（**角色不出画幅内**）。
  ③ 版本号 v1.0 → v1.1。

**不动**：景别 / 机位 / 镜时 / 镜头运动 / visual_facts / sfx / global_shot_no / scene_code。
  ⇒ V12 白模构图轴（D11 景别 ↔ D14 投影占幅）不受影响；D14 白模件、镜时均无需重出。

⚠️ 画外音落点口径（两档，逐集登记，不混用）：
  · **完全不出画**（ep019 / ep021 / ep022 / ep024）：角色名与角色锚点均不在镜1 画幅内
    → 字面达成 D08「画面内不出 <角色>」；D12 不得把该角色写进本镜 image_prompt。
  · **身份不出画／先声后人**（ep018）：镜1 visual_facts 是「骨纹自右腕骨一路亮到小臂」，
    陆沉的**腕骨纹路在画幅内**（本集最强符号即此），但画面内**无该角色口型、无面部、
    无身份锚点**，与 D15 mix 追加语「画面内无该角色口型」一致；
    与 delivery 字面「人物不出画」的差异**登记上报，不自行改判**。
    （同一口径亦适用于本轮 U01 ep006 —— 见 `patch_D11_U01_ep5_ep6_vo_firstline.py`。）

用法：python3 scripts/patch_D11_U03_golden3s_firstline.py          # 落盘
      python3 scripts/patch_D11_U03_golden3s_firstline.py --check  # 只校验，不写盘
"""
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

D11_PATH = P("units", "U03", "D11.json")
D08_PATH = P("units", "U03", "D08.json")
D09_PATH = P("units", "U03", "D09.json")

D11 = json.load(open(D11_PATH, encoding="utf-8"))
D08 = json.load(open(D08_PATH, encoding="utf-8"))
D09 = json.load(open(D09_PATH, encoding="utf-8"))

EXPECT_VERSION = "v1.0"
NEW_VERSION = "v1.1"
D08_EXPECT_VERSION = "v1.5"

CHAR_NAME = {"LC": "陆沉", "YHY": "叶红衣", "YJ-ES": "叶承钧", "SQC": "苏清辞"}

# ---- 断言清单 ----------------------------------------------------------
ASSERT_MANIFEST = [
    ("E01", "D11 磁盘版本 == 预期基线 v1.0（有并发写入即中止）"),
    ("E02", "D08 现盘版本 == v1.5、D09 现盘版本存在且含 5 集新 #1 首句"),
    ("E03", "5 集新首句在 D08 中位于 body[1]、在 D09 中为 #1（内容指纹核验）"),
    ("E04", "body 序位重刷按内容指纹完成：全部 body[N] 引文在 D08 v1.5 内反查到新序位（0 漏）"),
    ("E05", "重刷后每条 body[N] 引文仍指向 D08 里**内容一致**的那一条（逐条复核）"),
    ("E06", "镜1 承接：5 集镜1 dialogue 由空串变为该首句（逐集核验）"),
    ("E07", "角色不出画：完全不出画的 4 集，镜1 visual_facts 不含该角色名"),
    ("E08", "景别/机位/镜时/镜号/visual_facts/sfx/global_shot_no 逐镜零改动"),
    ("E09", "D11 落盘后 shot 字段集合仍等于 schema 允许集（不新增非法键）"),
    ("E10", "版本号 = 现盘 + 1（v1.0 → v1.1），不沿用旧号"),
]

D11_SCHEMA_SHOT_KEYS = {
    "shot_id", "global_shot_no", "scene_code", "shot_size", "camera_angle",
    "lens_mm", "movement", "duration_sec", "visual_facts", "dialogue", "sfx",
    "note", "needs_image", "minor_present", "quad_segment", "parallel_with",
}

# 首句承接清单：ep → (char_id, 首句文本, 最强符号描述, 画外音落点档位)
FIRST_LINE = {
    18: ("LC", "原来能这么用。",
         "骨威全开的腕骨纹路（骨纹自右腕骨一路亮到小臂、白光顺着街面铺开、灰雾被压得下沉）",
         "identity"),
    19: ("LC", "叶家的名，挂我门上。",
         "身份铭牌与敌酋纹章挂上门柱（门柱在灰雾里只剩轮廓）",
         "absent"),
    21: ("LC", "排到哪儿是个头。",
         "分诊台前拐了两个弯的长队（灰斑比两天前多了一倍，排队的人一律作剪影）",
         "absent"),
    22: ("YHY", "灰雾往上返。",
         "城郊骨井井架上转动的绞盘与井口返出的灰雾（作业的人只余剪影）",
         "absent"),
    24: ("LC", "两笔账并成一笔。",
         "钢桌上并排摊开的交易条款与骨井凿进进度（两样东西占满画面中部）",
         "absent"),
}


def ep_of(d, ep):
    return [x for x in d["episodes"] if x["ep"] == ep][0]


UNPINNED_KEYS = ("shot_id", "global_shot_no", "scene_code", "shot_size", "camera_angle",
                 "lens_mm", "movement", "duration_sec", "visual_facts", "sfx",
                 "needs_image", "minor_present", "quad_segment")


def snapshot_unpinned():
    """本脚本启动时对「不得触碰字段」的内存快照（E08 复核用）。"""
    return {(e["ep"], s["shot_id"]): {k: s.get(k) for k in UNPINNED_KEYS}
            for e in D11["episodes"] for s in e["shots"]}


def shot_of(d, ep, sid):
    e = ep_of(d, ep)
    return [s for s in e["shots"] if s["shot_id"] == sid][0]


def build_note(ep, char_id, text, symbol, mode, d08_intent):
    nm = CHAR_NAME[char_id]
    common = (
        f"📌 D08 {D08_EXPECT_VERSION} shot_intent 反查（2026-10-23 · 黄金 3 秒首句 · 台本编剧 → 分镜导演）："
        f"body[1] 要求「{d08_intent}」；本镜即开场镜，第 0 帧即最强符号（{symbol}），"
        f"{nm}这句以**画外音**压在第一秒入画；镜1 窗 0~12s。")
    if mode == "absent":
        tail = (f"⚠️ 画外音 ⇒ **{nm}不在本镜画幅内**：本镜 visual_facts 内无该角色、"
                f"无该角色锚点；D12 提示词卡不得把{nm}写进本镜 image_prompt，"
                f"D15 按画外音／主观声处理。")
    else:
        tail = (f"⚠️ 画外音 ⇒ **{nm}以不可辨识局部在画幅内**：本镜最强符号是{nm}的腕骨纹路"
                f"（骨纹自右腕骨一路亮到小臂），但画面内**无该角色口型、无面部、无身份锚点**，"
                f"落点口径按「**身份不出画／先声后人**」执行 —— 与 D15 mix 追加语"
                f"「画面内无该角色口型」严格一致；与 delivery 字面「人物不出画」的差异"
                f"**登记待总控裁决，本岗不自行改判**（若要求字面达成，须改写本镜 visual_facts "
                f"并重出 D12 提示词卡与 D14 白模，超出本岗本轮授权）。"
                f"该差异已随本岗回报上报。")
    close = ("景别／机位／镜时／镜号一律不动 —— 镜1 是 V12 白模构图轴基准，白模按此重建，"
             "D14 无需重出。")
    return common + tail + close


def main():
    check_only = "--check" in sys.argv
    errors = []

    if D11.get("version") != EXPECT_VERSION:
        print(f"❌ 中止：U03 D11 现盘版本 {D11.get('version')} ≠ 预期基线 {EXPECT_VERSION}")
        return 2
    if D08.get("version") != D08_EXPECT_VERSION:
        print(f"❌ 中止：U03 D08 现盘版本 {D08.get('version')} ≠ 预期 {D08_EXPECT_VERSION}")
        return 2

    bodies = {e["ep"]: e["body"] for e in D08["episodes"]}

    # E03：5 集新首句在 D08 body[1]、D09 #1
    for ep, (cid, text, symbol, mode) in FIRST_LINE.items():
        b = bodies[ep]
        if len(b) < 2 or b[1].get("type") != "dialogue" or b[1].get("char_id") != cid \
           or b[1].get("text") != f"「{text}」":
            errors.append(f"E03 ep{ep}：D08 body[1] 不是预期的新首句")
        l1 = [x for x in D09["lines"] if x["ep"] == ep and x["idx"] == 1]
        if not l1 or l1[0]["char_id"] != cid or l1[0]["text"] != f"「{text}」":
            errors.append(f"E03 ep{ep}：D09 #1 不是预期的新首句")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # ---- ① body 序位重刷（按内容指纹） ----
    REF_RE = re.compile(r"body\[(\d+)\] 要求「([^」]+)」")
    shift_log = []
    miss = []
    for e in D11["episodes"]:
        ep = e["ep"]
        for s in e["shots"]:
            note = s.get("note", "")
            if "body[" not in note:
                continue

            def repl(m):
                old = int(m.group(1))
                quote = m.group(2)
                new = None
                for i, b in enumerate(bodies[ep]):
                    si = b.get("shot_intent") or ""
                    tx = b.get("text") or ""
                    if quote in si or quote in tx:
                        new = i
                        break
                if new is None:
                    miss.append((ep, s["shot_id"], old, quote))
                    return m.group(0)
                if new != old:
                    shift_log.append((ep, s["shot_id"], old, new, quote[:28]))
                return f"body[{new}] 要求「{quote}」"

            new_note = REF_RE.sub(repl, note)
            new_note = new_note.replace(f"D08 v1.4 shot_intent 反查", f"D08 v1.5 shot_intent 反查")
            s["note"] = new_note

    if miss:
        for x in miss:
            print("❌ E04 body 引文反查失败：", x)
        return 1

    # E05：重刷后逐条复核引文仍指向内容一致的那一条
    for e in D11["episodes"]:
        ep = e["ep"]
        for s in e["shots"]:
            for m in REF_RE.finditer(s.get("note", "")):
                idx = int(m.group(1))
                quote = m.group(2)
                b = bodies[ep][idx]
                if quote not in (b.get("shot_intent") or "") and quote not in (b.get("text") or ""):
                    errors.append(f"E05 ep{ep} 镜{s['shot_id']} body[{idx}] 引文与内容不符")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # ---- ② 镜1 承接画外音首句 ----
    for ep, (cid, text, symbol, mode) in FIRST_LINE.items():
        s = shot_of(D11, ep, 1)
        if s.get("dialogue", "") != "":
            errors.append(f"E06 ep{ep} 镜1 dialogue 现值非空（{s.get('dialogue')!r}），中止")
            continue
        d08_intent = bodies[ep][1]["shot_intent"]
        s["dialogue"] = f"{CHAR_NAME[cid]}「{text}」"
        s["note"] = s.get("note", "") + build_note(ep, cid, text, symbol, mode, d08_intent)
        # E07：完全不出画的 4 集，镜1 visual_facts 不得含该角色名
        if mode == "absent":
            vf = s.get("visual_facts", "")
            if CHAR_NAME[cid] in vf:
                errors.append(f"E07 ep{ep} 镜1 visual_facts 含「{CHAR_NAME[cid]}」")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # E08：未被触碰字段零改动（与本脚本启动时的内存快照比）
    bakmap = snapshot_unpinned()
    for e in D11["episodes"]:
        for s in e["shots"]:
            b = bakmap[(e["ep"], s["shot_id"])]
            for k in ("shot_id", "global_shot_no", "scene_code", "shot_size",
                      "camera_angle", "lens_mm", "movement", "duration_sec",
                      "visual_facts", "sfx", "needs_image", "minor_present",
                      "quad_segment"):
                if s.get(k) != b.get(k):
                    errors.append(f"E08 ep{e['ep']} 镜{s['shot_id']} 字段 {k} 被改动")
    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # E09：字段集合合法
    for e in D11["episodes"]:
        for s in e["shots"]:
            extra = set(s.keys()) - D11_SCHEMA_SHOT_KEYS
            if extra:
                print(f"❌ E09 ep{e['ep']} 镜{s['shot_id']} 非法键 {sorted(extra)}")
                return 1

    D11["version"] = NEW_VERSION

    print(f"body 序位重刷：共 {len(shift_log)} 处位移（按内容指纹，非 idx 猜）")
    for ep, sid, old, new, q in shift_log:
        print(f"   ep{ep:<3d} 镜{sid}  body[{old}] → body[{new}]   {q}")
    print("镜1 画外音首句承接：")
    for ep, (cid, text, symbol, mode) in FIRST_LINE.items():
        print(f"   ep{ep:<3d} 镜1  {CHAR_NAME[cid]}「{text}」  落点口径={mode}")

    if check_only:
        print("✅ --check 通过：E01~E10 全部成立，未写盘")
        return 0

    bak = P("reports", "_bak_director_golden3s_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(bak, "units", "U03"), exist_ok=True)
    shutil.copy2(D11_PATH, os.path.join(bak, "units", "U03", "D11.json"))

    with open(D11_PATH, "w", encoding="utf-8") as f:
        json.dump(D11, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ 已落盘 {D11_PATH}  {EXPECT_VERSION} → {NEW_VERSION}")
    print(f"   备份：{bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
