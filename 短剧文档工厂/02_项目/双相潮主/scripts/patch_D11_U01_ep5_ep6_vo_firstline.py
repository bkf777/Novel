#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01 D11 补丁：ep005 / ep006 首句前移至 0.5s 后，在**镜1** 承接为画外音首句。

背景（R-026a / R-026d，总控 2026-10-23 11:55 派）：
  声音设计岗已把 D15 U01 ep004–ep008 首句配音 at_sec 前移至 0.5s（dur 不变）；
  其中 **ep005 / ep006 做成画外音** —— D15 U01 v1.11 该两条 `voice_over` 已带
  `delivery: "画外音（人物不出画，首帧给最强符号）"` 与 mix 追加
  「本条作画外音：按主观声处理，画面内无该角色口型，人物不出画」。

  0.5s 落在**镜1 的时间窗**内（ep5 镜1 = 0~12.0s；ep6 镜1 = 0~11.0s），
  而 D11 现盘把这两句挂在镜2 → 本补丁把首句迁到镜1 并按画外音口径承接，
  镜2 相应减去该句。

本补丁**只改 `dialogue` 与 `note` 两个字段**：
  · 景别 / 机位 / 镜时 / 镜头运动 / visual_facts / sfx / global_shot_no **一律不动**
    ⇒ V12 白模构图轴（D11 景别 ↔ D14 投影占幅）不受影响，D14 白模件无需重出；
  · D12 提示词卡也不需要改：ep005 镜1 卡 C-017 的 `consistency_refs.char_ids` 本就为空
    （画面内无叶承钧），ep006 镜1 卡 C-021 的陆沉是**不可辨识剪影**（只给「黑色战术风衣」
    轮廓、不给面部），画外音不要求改写该卡；
  · `delivery` 不写入 D11 —— D11 shot 的 schema 是 `additionalProperties: false`
    且字段表里没有 `delivery`，画外音标识一律写在 `note`（与 U01 ep003 镜1 先例同构）。

⚠️ ep006 的口径差异（必须随回报上报，不自行改判）：
  D15 v1.11 ep006 #1 的 delivery 写「人物不出画」，但 D11 ep006 镜1 的 visual_facts
  是「厂房暗处的一道剪影暴起冲出」—— 陆沉**以不可辨识剪影在画幅内**。
  本补丁按上游裁决把该句做成画外音并落在镜1，落点口径为
  「**身份不出画／先声后人**」（画面内无该角色口型、无面部、无身份锚点，
  D12 C-021 `char_descriptions` 仅「黑色战术风衣」），
  与 D15 mix 追加语「画面内无该角色口型」严格一致；
  「人物完全不在画幅内」在 ep006 本镜不成立，差异已登记在镜1 note 内并随回报上报。

用法：python3 scripts/patch_D11_U01_ep5_ep6_vo_firstline.py          # 落盘
      python3 scripts/patch_D11_U01_ep5_ep6_vo_firstline.py --check  # 只校验，不写盘
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

D11_PATH = P("units", "U01", "D11.json")
D11 = json.load(open(D11_PATH, encoding="utf-8"))

EXPECT_VERSION = "v1.13"
NEW_VERSION = "v1.14"

# ---- 断言清单（本脚本跑了哪些断言，逐条写死） ------------------------------
ASSERT_MANIFEST = [
    ("B01", "D11 磁盘版本 == 预期基线 v1.13（有并发写入即中止）"),
    ("B02", "ep005 镜1 现盘 dialogue 为空（否则说明首句已被他人迁入，本脚本中止）"),
    ("B03", "ep006 镜1 现盘 dialogue 为空（同上）"),
    ("B04", "ep005 镜2 现盘 dialogue 含首句「按规程投入，回收雾核。」与第二句"),
    ("B05", "ep006 镜2 现盘 dialogue == 「陆沉「走开。」」"),
    ("B06", "ep005 镜2 迁出后 dialogue == 「叶承钧「序号三，逾期十一天。」」"),
    ("B07", "ep006 镜2 迁出后 dialogue == 空串"),
    ("B08", "景别/机位/镜时/镜号/visual_facts/sfx/global_shot_no 逐镜零改动"),
    ("B09", "D11 落盘后 shot 字段集合仍等于 schema 允许集（不新增 delivery 等非法键）"),
    ("B10", "版本号 = 现盘 + 1（v1.13 → v1.14），不沿用旧号"),
]

D11_SCHEMA_SHOT_KEYS = {
    "shot_id", "global_shot_no", "scene_code", "shot_size", "camera_angle",
    "lens_mm", "movement", "duration_sec", "visual_facts", "dialogue", "sfx",
    "note", "needs_image", "minor_present", "quad_segment", "parallel_with",
}

# ---- 补丁内容（逐集逐镜写死；不靠序号猜） -------------------------------
NOTE_EP5_SHOT1 = (
    "📌 黄金 3 秒首句承接（2026-10-23 · R-026a／R-026d）：声音设计岗把本集首句配音"
    "「按规程投入，回收雾核。」前移到 **0.5s**（dur 不变＝2.8s），并在 D15 U01 v1.11 该条"
    "标注 `delivery: 画外音（人物不出画，首帧给最强符号）`（mix 追加：按主观声处理，"
    "画面内无该角色口型，人物不出画）。0.5s 落在**镜1 时间窗 0~12.0s** 内，"
    "故本镜承接该句为画外音首句：第 0 帧即最强符号（装甲车灯扫过钢板围栏、护卫队押队列进厂），"
    "叶承钧的声音压在队列进场的第一秒落下——下令者不在画幅内，被下令的人先到。"
    "⚠️ 画外音 ⇒ **叶承钧不在本镜画幅内**：D12 提示词卡 C-017 的 `consistency_refs.char_ids` "
    "本就是空数组（画面内无该角色），保持不动；D15 按画外音／主观声处理。"
    "景别（中远景）／机位（平视）／镜时（12.0s）／镜号一律不动 —— 镜1 是 V12 白模构图轴基准，"
    "白模按此重建，D14 无需重出。"
)
NOTE_EP5_SHOT2 = (
    "📌 黄金 3 秒首句迁出（2026-10-23 · R-026a／R-026d）：本集首句「按规程投入，回收雾核。」"
    "已随 D15 U01 v1.11 前移到 0.5s 并做成画外音，**改由镜1 承接**（镜1 时间窗 0~12.0s，"
    "画面内无叶承钧）；本镜自此只保留第二句「序号三，逾期十一天。」，"
    "原 D08 v1.13 body 序位（叶承钧站在终端前 → 首句 → 终端亮屏 → 第二句）随之变为"
    "「镜1 画外音首句 → 镜2 终端亮屏 → 第二句」，**D08 由台本编剧岗同步**（本岗不改 D08）。"
)
NOTE_EP6_SHOT1 = (
    "📌 黄金 3 秒首句承接（2026-10-23 · R-026a／R-026d）：声音设计岗把本集首句配音"
    "「走开。」前移到 **0.5s**（dur 不变＝1.3s），并在 D15 U01 v1.11 该条标注 "
    "`delivery: 画外音（人物不出画，首帧给最强符号）`（mix 追加：按主观声处理，"
    "画面内无该角色口型，人物不出画）。0.5s 落在**镜1 时间窗 0~11.0s** 内，"
    "故本镜承接该句为画外音首句：第 0 帧即最强符号（厂房暗处剪影暴起、重钢钎拖地划出火星），"
    "命令压在剪影冲出暗处的一秒落下 —— 先声后人。"
    "⚠️ **口径差异（登记待总控裁决，不自行改判）**：D15 v1.11 该条 delivery 写「人物不出画」，"
    "但本镜 visual_facts 是「厂房暗处的一道剪影暴起冲出」，陆沉**以不可辨识剪影在画幅内**"
    "（D12 C-021：`char_ids=[\"LC\"]`、`char_descriptions=[\"黑色战术风衣\"]`，不给面部、不给身份锚点）。"
    "本镜落点口径按 **「身份不出画／先声后人」** 执行 —— 与 D15 mix 追加语"
    "「画面内无该角色口型」严格一致；「人物完全不在画幅内」在 ep006 本镜不成立。"
    "若总控要求字面达成「人物不出画」，须改写本镜 visual_facts 并重出 D12 C-021 与 D14 白模"
    "（景别/机位/镜时不动，只改画面内容），该动作超出本岗本轮授权。"
    "景别（中景）／机位（平视）／镜时（11.0s）／镜号一律不动 —— 镜1 是 V12 白模构图轴基准。"
)
NOTE_EP6_SHOT2 = (
    "📌 黄金 3 秒首句迁出（2026-10-23 · R-026a／R-026d）：本集首句「走开。」"
    "已随 D15 U01 v1.11 前移到 0.5s 并做成画外音，**改由镜1 承接**（镜1 时间窗 0~11.0s）；"
    "本镜自此无台词，只保留「一击震退守卫队长，人向后滑出半米，单膝落地」这一动作，"
    "**原 D08 v1.13 body 序位随之改变**（D08 由台本编剧岗同步，本岗不改 D08）。"
)

PATCH = {
    5: {
        1: {"dialogue": "叶承钧「按规程投入，回收雾核。」", "note_append": NOTE_EP5_SHOT1},
        2: {"dialogue": "叶承钧「序号三，逾期十一天。」", "note_append": NOTE_EP5_SHOT2},
    },
    6: {
        1: {"dialogue": "陆沉「走开。」", "note_append": NOTE_EP6_SHOT1},
        2: {"dialogue": "", "note_append": NOTE_EP6_SHOT2},
    },
}

EXPECTED_OLD = {
    (5, 1): "",
    (5, 2): "叶承钧「按规程投入，回收雾核。」／叶承钧「序号三，逾期十一天。」",
    (6, 1): "",
    (6, 2): "陆沉「走开。」",
}


def shot_of(ep):
    e = [x for x in D11["episodes"] if x["ep"] == ep][0]
    return e, {s["shot_id"]: s for s in e["shots"]}


def snapshot():
    """记录不被本补丁触碰的字段，用于事后逐镜比对（B08）。"""
    snap = {}
    for ep in PATCH:
        e, sm = shot_of(ep)
        for sid, s in sm.items():
            snap[(ep, sid)] = {k: s.get(k) for k in (
                "shot_id", "global_shot_no", "scene_code", "shot_size", "camera_angle",
                "lens_mm", "movement", "duration_sec", "visual_facts", "sfx",
                "needs_image", "minor_present", "quad_segment")}
    return snap


def main():
    check_only = "--check" in sys.argv
    errors = []

    # B01 版本基线
    if D11.get("version") != EXPECT_VERSION:
        print(f"❌ 中止：U01 D11 现盘版本 {D11.get('version')} ≠ 预期基线 {EXPECT_VERSION}"
              f"（可能有并发写入；先做条目级 diff 再决定是否续写）")
        return 2

    before = snapshot()

    for (ep, sid), exp in EXPECTED_OLD.items():
        e, sm = shot_of(ep)
        cur = sm[sid].get("dialogue", "")
        if cur != exp:
            errors.append(f"B0x {ep} 镜{sid} dialogue 现值 ≠ 预期：{cur!r} ≠ {exp!r}")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # 落补丁
    for ep, shots in PATCH.items():
        e, sm = shot_of(ep)
        for sid, spec in shots.items():
            s = sm[sid]
            s["dialogue"] = spec["dialogue"]
            s["note"] = (s.get("note", "") + spec["note_append"])

    # B06/B07 复核
    e5, sm5 = shot_of(5)
    if sm5[2]["dialogue"] != "叶承钧「序号三，逾期十一天。」":
        print("❌ B06 ep005 镜2 dialogue 迁出结果不符")
        return 1
    e6, sm6 = shot_of(6)
    if sm6[2]["dialogue"] != "":
        print("❌ B07 ep006 镜2 dialogue 迁出结果不符")
        return 1

    # B08 未触碰字段零改动
    after = snapshot()
    if before != after:
        print("❌ B08 景别/机位/镜时/镜号/visual_facts/sfx 等字段被改动，中止")
        return 1

    # B09 字段集合合法
    for ep in PATCH:
        e, sm = shot_of(ep)
        for sid, s in sm.items():
            extra = set(s.keys()) - D11_SCHEMA_SHOT_KEYS
            if extra:
                print(f"❌ B09 ep{ep} 镜{sid} 出现非法键 {sorted(extra)}")
                return 1

    # B10 版本号
    D11["version"] = NEW_VERSION

    if check_only:
        print("✅ --check 通过：B01~B10 全部成立，未写盘")
        return 0

    bak = P("reports", "_bak_director_golden3s_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(bak, "units", "U01"), exist_ok=True)
    shutil.copy2(D11_PATH, os.path.join(bak, "units", "U01", "D11.json"))

    with open(D11_PATH, "w", encoding="utf-8") as f:
        json.dump(D11, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ 已落盘 {D11_PATH}  {EXPECT_VERSION} → {NEW_VERSION}")
    print(f"   备份：{bak}")
    print("   断言：" + "；".join(f"{a} {b}" for a, b in ASSERT_MANIFEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
