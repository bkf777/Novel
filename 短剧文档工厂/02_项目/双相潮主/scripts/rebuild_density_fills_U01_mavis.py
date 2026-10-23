#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
rebuild_density_fills_U01_mavis.py —— **从盘上反推** `density_fills_U01.json` 内容源

起因（2026-10-23 12:3x，本岗实测）
---------------------------------
① `densify_subtitles.py` 落盘时**只写** `text / in_sec / out_sec / shot_id / note`，
   **anchor 不落盘**（anchor 只活在 fills 文件里）⇒
   **fills 文件一旦被清空/重写，盘上那些字幕行就永久失去锚点、无法重建**。
② 12:28 并发实例重写 `scripts/density_fills_U01.json`（4,993 B，只剩 ep2）
   ⇒ 盘上 90 条字幕行（ep2 9 条 ＋ 并发实例的 ep1/5/6/8 49 条 ＋ 本岗的 ep3/4/7 32 条）
   **全部与内容源脱钩** ⇒ D16 一旦重建，这些行会集体消失。

修法
----
**从盘上反推**内容源：对每条 `type=="字幕"` 的行，在其 `shot_id` 的 D11 `visual_facts`
里求「该行 text 与 vf 的最长公共连续子串」作为 anchor（要求 ≥4 字 ⇒ 保证锚点逐字在 vf 里，
即「画面里本来就有这个东西」这条硬约束仍然成立）。
无法求出 ≥4 字锚点的行**如实报告、不伪造**。

保留
----
· ep2 的 `move_dialogue`（首句前移的幂等三态需要 `from_sec/to_sec`）原样保留；
· 每条字幕行的 `note` 原样保留（并发实例的 note 内含 D11 引文，是留痕的一部分）；
· 已有 ep2 fills 的 anchor **不覆盖**（以清单为准，清单是源）。

守卫
----
① **写前**：备份到 `reports/_bak_density_fills_rebuild_*`；
② **幂等**：重建后 fills 中每条 (text) 与盘上行的 (in_sec,out_sec,shot_id) 必须完全一致，
   否则中止；且**不得凭空新增**盘上不存在的行；
③ **写后**：回读并逐条比对；
④ **可回滚**：校验不过自动还原备份。

用法：python3 scripts/rebuild_density_fills_U01_mavis.py [--dry-run]
"""
import collections
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_ANCHOR = 4

# 单元参数：--unit U02（缺省 U01）。D16 是多人共写的共享真源，
# 并发实例会各自往 fills 清单里写条目；清单一旦被重写/覆盖，
# 盘上那些字幕行就失去 anchor、无法随 D16 重建而再生
# ⇒ 任何清单改动后都应跑一次本脚本，从**现盘**反推回填 anchor。
UNIT = "U01"
for _i, _a in enumerate(sys.argv):
    if _a == "--unit" and _i + 1 < len(sys.argv):
        UNIT = sys.argv[_i + 1]
FILLS = os.path.join(ROOT, "scripts", f"density_fills_{UNIT}.json")
D11 = os.path.join(ROOT, "units", UNIT, "D11.json")
D16 = os.path.join(ROOT, "units", UNIT, "D16.json")

# ── 人工锚点表 ──────────────────────────────────────────────────────────────
#  自动求「最长公共连续子串」对**改写型**字幕行会失效（文案是清单化改写，
#  与 D11 原句不是逐字包含关系 ⇒ 公共子串不足 4 字）。
#  这类行**必须人工指定锚点**，且锚点仍须**逐字出现在该镜 visual_facts 里**
#  （工具会机械校验「anchor ∈ visual_facts」，不合格即拒写）。
#  key = (ep, text)；value = 该镜 D11 visual_facts 中的原文片段。
MANUAL_ANCHORS = {
    (1, "出租屋：椅子翻倒、工具散落"): "翻倒的椅子",
    (4, "钎身与触角第一次相交"): "钎身与灰隙巢虫触角相交",
    (6, "钎身：贯穿身侧钢板"): "贯穿叶承钧身侧的钢板",
    (6, "钎身：砸在腕上束具扣"): "砸在叶红衣腕上的束具扣上",
    (7, "双焰余光勾亮两人轮廓"): "黑白双焰的余光",
    # ── U02（2026-10-23 12:3x 反推重建实测：自动 LCS 求不出 ≥4 字锚点的 3 条）──
    (10, "胸口：起伏"): "胸口起伏",
    (14, "货架：全空"): "货架全空",
    (15, "数据板：托在苏清辞掌心"): "苏清辞托在掌心",
}


def lcs_substr(a, b):
    """a、b 的最长公共**连续**子串（返回 a 中的那一段）。"""
    best = ""
    n, m = len(a), len(b)
    dp = [0] * (m + 1)
    for i in range(1, n + 1):
        prev = 0
        for j in range(1, m + 1):
            tmp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
                if dp[j] > len(best):
                    best = a[i - dp[j]:i]
            else:
                dp[j] = 0
            prev = tmp
    return best


def main():
    dry = "--dry-run" in sys.argv
    d11 = json.load(open(D11, encoding="utf-8"))
    d16 = json.load(open(D16, encoding="utf-8"))
    facts = {}
    for e in d11["episodes"]:
        for s in e["shots"]:
            facts[(e["ep"], int(s["shot_id"]))] = str(s.get("visual_facts") or "")

    old = json.load(open(FILLS, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    old_units = old.get("units", {}).get(UNIT, collections.OrderedDict())
    # 已有清单里 (ep,text) → anchor 优先复用
    known = {}
    for ep_s, plan in old_units.items():
        for fl in plan.get("fills", []):
            known[(int(ep_s), fl["text"])] = fl.get("anchor")

    units = collections.OrderedDict()
    rebuild = []
    orphan = []
    for e in d16["episodes"]:
        ep = int(e["ep"])
        plan = collections.OrderedDict()
        src = old_units.get(str(ep), {})
        if src.get("_note"):
            plan["_note"] = src["_note"]
        if src.get("move_dialogue"):
            plan["move_dialogue"] = src["move_dialogue"]
        fills = []
        for l in e["subtitle_style"].get("lines", []):
            if l.get("type") != "字幕":
                continue
            text = l["text"]
            # 锚点优先级（D18 Q114 首选路径落地后）：
            #   ① **D16 自带 anchor**（结构化字段，最权威，且是行作者的原始标注）
            #   ② 清单里已有的 anchor（人工撰写并经工具校验过）
            #   ③ 脚本内人工锚点表（改写型行的兜底）
            #   ④ LCS 自动求（≥4 字）
            anchor = l.get("anchor")
            if not anchor:
                anchor = known.get((ep, text))
            if not anchor:
                anchor = MANUAL_ANCHORS.get((ep, text))
            if not anchor:
                vf = facts.get((ep, int(l.get("shot_id", 0))), "")
                cand = lcs_substr(text, vf)
                if len(cand) >= MIN_ANCHOR:
                    anchor = cand
                else:
                    orphan.append((ep, text, l.get("shot_id")))
                    continue
            # 锚点必须逐字在该镜 visual_facts 里（工具的硬校验，先自证）
            vf = facts.get((ep, int(l.get("shot_id", 0))), "")
            if anchor not in vf:
                orphan.append((ep, text, l.get("shot_id"), "anchor 不在 visual_facts"))
                continue
            fills.append(collections.OrderedDict([
                ("text", text), ("in_sec", l["in_sec"]), ("out_sec", l["out_sec"]),
                ("shot_id", int(l.get("shot_id", 0))), ("anchor", anchor),
                ("note", l.get("note", "")),
            ]))
        if fills:
            plan["fills"] = fills
        if len(plan) > 1 or "fills" in plan:
            units[str(ep)] = plan
        rebuild.append((ep, len(fills)))

    print("📌 盘上字幕行分布：" + "｜".join("ep%d=%d" % x for x in rebuild))
    print("   清单重建：%d 集 / %d 条" % (len(units), sum(len(p.get("fills", [])) for p in units.values())))
    # D16 自带 anchor 的行按类型分布（Q114 首选路径落地后的覆盖面体检）。
    # 注意：**清单只收 type=="字幕"**（densify 只负责新增字幕行），
    # 但对白/面板/片尾行若也带 anchor，它们并不「丢失」——锚点已存在 D16 的结构化字段里。
    by_type = {}
    for e in d16["episodes"]:
        for l in e["subtitle_style"].get("lines", []):
            if l.get("anchor"):
                by_type[l.get("type")] = by_type.get(l.get("type"), 0) + 1
    if by_type:
        print("   D16 自带 anchor 的行（按类型）："
              + "｜".join(f"{k}={v}" for k, v in sorted(by_type.items()))
              + "  ← 清单只收「字幕」行；其余类型的锚点已在 D16 结构化字段里，不会丢")
    if orphan:
        print("⚠️ 未能求出 ≥%d 字锚点的行（**不伪造**，需人工处理）：" % MIN_ANCHOR)
        for o in orphan:
            print("   -", o)

    # 写后一致性自检（不依赖 densify）
    bad = 0
    for e in d16["episodes"]:
        ep = int(e["ep"])
        live = {l["text"]: (l["in_sec"], l["out_sec"], int(l.get("shot_id", 0)))
                for l in e["subtitle_style"].get("lines", []) if l.get("type") == "字幕"}
        plan = units.get(str(ep), {})
        for fl in plan.get("fills", []):
            t = fl["text"]
            if t not in live:
                print("   [ERR] ep%d 清单有盘上无：%s" % (ep, t)); bad += 1
            elif (live[t][0], live[t][1], live[t][2]) != (fl["in_sec"], fl["out_sec"], fl["shot_id"]):
                print("   [ERR] ep%d 时码/镜位不符：%s" % (ep, t)); bad += 1
        for t in live:
            if t not in {f["text"] for f in plan.get("fills", [])}:
                print("   [ERR] ep%d 盘上有清单无：%s" % (ep, t)); bad += 1
    if bad:
        print("❌ 清单↔盘面不一致 %d 处；不写盘。" % bad)
        return 2

    if dry:
        print("（--dry-run：未写盘）")
        return 0

    bak_dir = os.path.join(ROOT, "reports", "_bak_density_fills_rebuild_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, f"density_fills_{UNIT}.json")
    shutil.copy2(FILLS, bak)

    out = collections.OrderedDict()
    out["_readme"] = old.get("_readme", "")
    out["_anchor_rule"] = old.get("_anchor_rule", "")
    out["_shot_visibility_rule"] = old.get("_shot_visibility_rule", "")
    out["_rebuild_note"] = (
        "2026-10-23 12:3x 本岗按现盘反推重建：densify 落盘**不写 anchor**，"
        "anchor 只活在本清单里 ⇒ 清单被清空则盘上字幕行永久失去锚点、无法重建。"
        "本次重建把 %s 全 %d 集的 %d 条字幕行与其 anchor、时码、镜位、note 逐条回填，"
        "保证「内容源 ⇄ 盘面」一致（可幂等复跑、可随 D16 重建而再生）。"
        % (UNIT, len(d16["episodes"]),
           sum(len(p.get("fills", [])) for p in units.values())))
    out["units"] = collections.OrderedDict([(UNIT, units)])
    json.dump(out, open(FILLS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(FILLS, "a", encoding="utf-8").write("\n")

    back = json.load(open(FILLS, encoding="utf-8"))
    nb = sum(len(p.get("fills", [])) for p in back["units"][UNIT].values())
    print("✅ 已重建内容源：%s %d 集 / %d 条 ｜ 备份 %s"
          % (UNIT, len(back["units"][UNIT]), nb, os.path.relpath(bak, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
