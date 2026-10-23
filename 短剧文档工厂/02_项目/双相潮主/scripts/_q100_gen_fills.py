#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_q100_gen_fills.py —— 由 _q100_plan.py 生成 densify_subtitles.py 用的填充清单

只做格式转换，不生成内容（内容全部来自 _q100_plan.py 的 PLAN）。
U01 清单**合并**进既有 density_fills_U01.json（保留 EP002 样板条目不动）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _q100_plan import PLAN, OWNED  # noqa: E402

HEADER = {
    "_readme": ("字幕密度填充清单（人工撰写文案 ＋ 机器校验锚点）。densify_subtitles.py 只做技术执行："
                "按 D16 cuts 校验挂载区间、按 D11 visual_facts 校验锚点、按时码规则校验重叠/停留/字数，"
                "然后把行写进 D16。文案由人写，脚本不生成内容。"),
    "_anchor_rule": ("anchor 必须逐字出现在该集该镜的 D11 visual_facts 中；这是「不编造画面」的硬约束"
                     "——字幕只能写画面里已经有的东西。"),
    "_shot_visibility_rule": ("挂载区间必须落在该镜的**真实可见区间**内。D16 的 cuts 里含段内并行交叉剪辑"
                              "（如 ep002 的 31.5s 回切镜2），按 D11 镜时累加会对不上，因此用 cuts 推导真实可见区间。"),
    "_q100_note": ("【Q100 字幕密度下限 · 2026-10-23 · 分镜导演岗】用户反馈「还是很拖啊，白模视频有很长一段时间"
                   "什么也没有」。体检（scripts/audit_dead_time.py）实测 U01+U02 十六集：平均空窗总 32.0s，"
                   "最长一段空白 31.7s。判定不用「加台词」：D09 语气卡对陆沉写死「每集不超过 4 句」，"
                   "本轮**对白行一条未加、时码一字未动**；改用画面里的字（字幕板／面板读数／场景标识），"
                   "内容全部取自 D11 每镜 visual_facts 已写明的事实。不动镜数与镜时 ⇒ V11 不受影响，不重跑 Blender。"),
}


def main():
    root = os.path.dirname(HERE)
    sc = os.path.join(root, "scripts")

    # ── U01：合并进既有清单 ──
    p1 = os.path.join(sc, "density_fills_U01.json")
    with open(p1, encoding="utf-8") as f:
        u01 = json.load(f)
    u01.setdefault("_readme", HEADER["_readme"])
    u01.setdefault("_anchor_rule", HEADER["_anchor_rule"])
    u01.setdefault("_shot_visibility_rule", HEADER["_shot_visibility_rule"])
    u01["_q100_note"] = HEADER["_q100_note"]
    for ep_s in OWNED["U01"]:
        rows = PLAN["U01"][ep_s]
        u01["units"]["U01"].setdefault(ep_s, {})
        u01["units"]["U01"][ep_s]["_note"] = (
            "Q100 字幕密度填充：本集按 D11 每镜 visual_facts 已写明的事实补画面文字，"
            "填掉成片空窗；不加台词、不改镜数与镜时。")
        u01["units"]["U01"][ep_s]["fills"] = [
            {"text": t, "in_sec": i, "out_sec": o, "shot_id": s,
             "anchor": a, "note": n, "_type": ty}
            for (t, ty, i, o, s, a, n) in rows
        ]
    # 保留但**不重做**同岗另一实例已落盘的 U01 ep003／ep004／ep007：
    # 把它们的 fills 段整段移除，避免本岗的文案与已落盘行撞车（撞车＝写盘中止）。
    for ep_s in ("3", "4", "7"):
        u01["units"]["U01"].pop(ep_s, None)
    u01["_q100_scope"] = (
        "本清单只覆盖分镜导演岗本轮实际负责的集：U01 ep001／ep005／ep006／ep008 "
        "＋ U02 ep009–ep016。U01 ep003／ep004／ep007 已由同岗另一实例于 2026-10-23 "
        "12:2x 落盘（D16 v1.22→v1.24），本岗不重做、不覆盖。")
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(u01, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 写 {p1}｜单元 {sorted(u01['units']['U01'].keys())}")

    # ── U02：新建清单 ──
    p2 = os.path.join(sc, "density_fills_U02.json")
    u02 = dict(HEADER)
    u02["units"] = {"U02": {}}
    for ep_s in OWNED["U02"]:
        rows = PLAN["U02"][ep_s]
        u02["units"]["U02"][ep_s] = {
            "_note": ("Q100 字幕密度填充：本集按 D11 每镜 visual_facts 已写明的事实补画面文字，"
                      "填掉成片空窗；不加台词、不改镜数与镜时。"),
            "fills": [
                {"text": t, "in_sec": i, "out_sec": o, "shot_id": s,
                 "anchor": a, "note": n, "_type": ty}
                for (t, ty, i, o, s, a, n) in rows
            ],
        }
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(u02, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ 写 {p2}｜单元 {sorted(u02['units']['U02'].keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
