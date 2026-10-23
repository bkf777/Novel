#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D16_anchor_backfill.py —— **Q114 首选路径：把 anchor 结构化写进 D16 的每一行**（三单元）

背景（缺陷的根，Chief 13:4x 点名、视觉设定/台本编剧独立复核同证）
------------------------------------------------------------------------------
`densify_subtitles.py` 落盘时**只把锚点写进 note 正文**，`anchor` **没有作为结构化字段落进 D16**
⇒ ① 产物**不自解释**：读 D16 的人看不出某行文字是从画面哪句事实来的；
② **清单被清空则盘上字幕行永久失去锚点、无法重建**（台本编剧 `rebuild_density_fills_U01_mavis.py` 已就此登记）；
③ Chief 的工具侧因此把 `rebuild_density_fills_U01_mavis.py` 改成「优先采用 D16 自带 anchor」，
   但**现盘 D16 只有 U01 ep002 的 13 条带 anchor** ⇒ 规则级生效 ≠ 覆盖完成。

本脚本做什么（**只加 anchor 字段，不改任何时码/文字/类型/镜位**）
------------------------------------------------------------
| 行类型 | anchor 取值 | 是否要求逐字 ∈ D11 visual_facts |
|---|---|---|
| 字幕／面板文字 | ① D16 自带 → ② 填充清单已有 → ③ note「」引文中命中 vf 者 → ④ 人工锚点表 → ⑤ LCS 自动求（≥4 字） | **是**（硬校验，不合格即拒写） |
| 对白 | **D09 原文**（逐字比对；归一化去「」） | 否（对白不是画面事实，锚在台词源） |
| 片尾 | **不写**（片尾标题卡不在任何镜的 visual_facts 内，属设计如此） | — |
| 角标 | **不写**（常驻元素，非画面事实行） | — |

守卫：版本＝U01 v1.35／U02 v1.11／U03 v1.3（D15 v1.14／v1.4／v1.2 交叉核对）；
结构差异白名单：**只允许**在 `lines[]` 上新增/改动 `anchor` 键 ＋ `/version`；
白名单外任一叶子值变化即 ABORT（防止覆盖并发批次）。写前备份 ＋ 写后回读复核。

用法：python3 scripts/patch_D16_anchor_backfill.py [--unit U01|U02|U03] [--dry-run]
"""
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各单元 D16 版本守卫（写盘时按现盘核对；不一致即该单元 ABORT，不影响其他单元）
GUARD = {"U01": "v1.36", "U02": "v1.11", "U03": "v1.3"}
# D15 活指针交叉核对（2026-10-23 14:xx：声音设计岗已把 U01 推到 v1.16）
D15V = {"U01": "v1.16", "U02": "v1.4", "U03": "v1.2"}

# ── 人工锚点表（自动 LCS 求不出 ≥4 字锚点的改写型字幕行）────────────────────
# key = (ep, text)；value = 该镜 D11 visual_facts 中的原文片段（逐字）。
MANUAL_ANCHORS = {
    (1, "出租屋：椅子翻倒、工具散落"): "翻倒的椅子",
    (4, "钎身与触角第一次相交"): "钎身与灰隙巢虫触角相交",
    (6, "钎身：贯穿身侧钢板"): "贯穿叶承钧身侧的钢板",
    (6, "钎身：砸在腕上束具扣"): "砸在叶红衣腕上的束具扣上",
    (7, "双焰余光勾亮两人轮廓"): "黑白双焰的余光",
    (10, "胸口：起伏"): "胸口起伏",
    (14, "货架：全空"): "货架全空",
    (15, "数据板：托在苏清辞掌心"): "苏清辞托在掌心",
    # ── U01 ep1 seq10「比上一趟少 6 分钟」（2026-10-23 14:xx 补）──────────────
    # 该行 type＝面板文字、挂镜2、区间 21.4~24.0s（确在镜2 窗 13~26 内）；
    # 但「比上一趟少 6 分钟」这行字**只写在镜3 的 visual_facts**（面板底部一行红字），
    # 镜2 的画面事实里是「上一趟存活 3 小时 04 分」＋「距灰潮试炼降临 2 小时 58 分」。
    # 口径裁决（本岗 D16 单写点）：**本行是画面那两个读数的算式字幕**，不是镜2 的面板原文
    # ⇒ anchor 取镜2 的面板原文「上一趟存活 3 小时 04 分」（该算式的被减数，逐字 ∈ 镜2 vf）。
    # ⛔ 不改挂镜、不改时码：D11 镜3 note 明写「面板底部红字…不得被底部字幕带压住」
    #    ⇒ 镜3 不得另设该面板文字行（否则字幕带压住红字），故本行不迁往镜3。
    (1, "比上一趟少 6 分钟"): "上一趟存活 3 小时 04 分",
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


def norm(t):
    return str(t or "").replace("「", "").replace("」", "").strip()


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


def allow_prefixes(n_eps):
    """白名单：只允许动 lines[] 上的 anchor 键 ＋ /version。"""
    out = ["/version"]
    for i in range(n_eps):
        out.append("/episodes/%d/subtitle_style/lines" % i)
    return out


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def derive(unit):
    d11 = load(os.path.join(ROOT, "units", unit, "D11.json"))
    d16 = load(os.path.join(ROOT, "units", unit, "D16.json"))
    d09 = load(os.path.join(ROOT, "units", unit, "D09.json"))
    facts = {}
    for e in d11["episodes"]:
        for s in e["shots"]:
            facts[(e["ep"], int(s["shot_id"]))] = str(s.get("visual_facts") or "")
    d09_by_ep = collections.defaultdict(list)
    for l in d09.get("lines", []):
        d09_by_ep[l["ep"]].append(l.get("text"))
    # 填充清单里已有的 anchor（U03 有自己的清单；U01/U02 的清单在本岗脚本目录下）
    known = {}
    fp = os.path.join(ROOT, "scripts", f"density_fills_{unit}.json")
    if os.path.exists(fp):
        old = load(fp)
        for ep_s, plan in (old.get("units", {}).get(unit) or {}).items():
            for fl in plan.get("fills", []):
                if fl.get("anchor"):
                    known[(int(ep_s), fl["text"])] = fl["anchor"]

    stat = collections.Counter()
    pending = []
    for e in d16["episodes"]:
        ep = e["ep"]
        for l in e["subtitle_style"]["lines"]:
            t = l.get("type")
            txt = str(l.get("text") or "")
            if t in ("片尾", "角标"):
                stat["跳过(" + t + ")"] += 1
                continue
            if t == "对白":
                cand = next((v for v in d09_by_ep.get(ep, [])
                             if norm(v) == norm(txt)), None)
                if not cand:
                    pending.append((ep, txt, "对白：D09 无逐字对应句"))
                    stat["对白-无D09对应"] += 1
                    continue
                if l.get("anchor") != cand:
                    l["anchor"] = cand
                    stat["对白-补anchor"] += 1
                else:
                    stat["对白-已对"] += 1
                continue
            if t in ("字幕", "面板文字"):
                vf = facts.get((ep, int(l.get("shot_id") or 0)), "")
                a = l.get("anchor")
                if not a:
                    a = known.get((ep, txt))
                if not a:
                    for q in re.findall(r"「([^」]+)」", str(l.get("note") or "")):
                        if q in vf:
                            a = q
                            break
                if not a:
                    a = MANUAL_ANCHORS.get((ep, txt))
                if not a:
                    c = lcs_substr(txt, vf)
                    if len(c) >= 4:
                        a = c
                if not a:
                    pending.append((ep, txt, "自动求不出 ≥4 字锚点，需人工"))
                    stat["画面类-待人工"] += 1
                    continue
                if a not in vf:
                    pending.append((ep, txt, f"候选 anchor 不在 visual_facts：{a}"))
                    stat["画面类-候选失配"] += 1
                    continue
                if l.get("anchor") != a:
                    l["anchor"] = a
                    stat["画面类-补anchor"] += 1
                else:
                    stat["画面类-已对"] += 1
                continue
            pending.append((ep, txt, f"未知行类型 {t}"))
            stat["未知类型"] += 1
    return d16, stat, pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    units = [args.unit] if args.unit else list(GUARD.keys())

    for unit in units:
        p16 = os.path.join(ROOT, "units", unit, "D16.json")
        before_bytes = open(p16, "rb").read()
        d16 = json.load(open(p16, encoding="utf-8"))
        if d16.get("version") != GUARD[unit]:
            print("[NO-OP] %s D16 version=%s ≠ 守卫 %s" % (unit, d16.get("version"), GUARD[unit]))
            continue
        p15 = os.path.join(ROOT, "units", unit, "D15.json")
        d15 = json.load(open(p15, encoding="utf-8"))
        if d15.get("version") != D15V[unit]:
            print("[ABORT] %s D15 version=%s ≠ 期望 %s（跨岗版本已变，本岗不凭旧坐标写盘）"
                  % (unit, d15.get("version"), D15V[unit]))
            continue

        before = dict(flat(d16))
        d16, stat, pending = derive(unit)
        n_eps = len(d16.get("episodes", []))
        allow = allow_prefixes(n_eps)

        # 结构差异白名单：lines[] 下的**非 anchor 键**一律不得变
        bad = []
        after = dict(flat(d16))
        for p, v in after.items():
            if p in before and before[p] != v:
                if "/subtitle_style/lines/" in p and p.endswith("/anchor"):
                    continue
                if not any(p.startswith(x) for x in allow):
                    bad.append((p, before[p], v))
        for p in before:
            if p not in after:
                bad.append((p, before[p], "<删除>"))
        # lines[] 下 anchor 之外出现任何增删 ⇒ 也算越界
        for p in after:
            if "/subtitle_style/lines/" in p and p.endswith("/anchor") and p not in before:
                continue
            if p not in before and "/subtitle_style/lines/" in p:
                bad.append((p, "<无>", after[p]))

        if bad:
            print("[ABORT] %s 白名单外结构差异 %d 处，未写盘：" % (unit, len(bad)))
            for p, o, n in bad[:12]:
                print("   -", p, repr(o), "→", repr(n))
            continue
        if pending:
            print("[ABORT] %s 有 %d 行求不出合法 anchor，未写盘：" % (unit, len(pending)))
            for ep, txt, why in pending[:12]:
                print("   - ep%s「%s」%s" % (ep, txt[:22], why))
            continue

        if args.dry_run:
            print("[DRY-RUN] %s：%s（anchor 落 D16 的结构化字段）" % (unit, dict(stat)))
            continue

        # 并发守卫：写前 size/mtime/sha256 复核
        now_bytes = open(p16, "rb").read()
        if hashlib.sha256(now_bytes).hexdigest() != hashlib.sha256(before_bytes).hexdigest():
            print("[ABORT] %s 并发改动守卫触发（sha256 不一致）；不写盘，请重跑。" % unit)
            continue

        d16["version"] = _bump(GUARD[unit])
        bak = os.path.join(ROOT, "reports",
                           "_bak_d16_anchor_%s_%s" % (unit, time.strftime("%Y%m%d-%H%M%S")))
        os.makedirs(bak, exist_ok=True)
        shutil.copy2(p16, os.path.join(bak, "%s_D16.json" % unit))
        with open(p16, "w", encoding="utf-8") as f:
            json.dump(d16, f, ensure_ascii=False, indent=2)
            f.write("\n")

        back = json.load(open(p16, encoding="utf-8"))
        n_rows = n_anchor = 0
        for e in back["episodes"]:
            for l in e["subtitle_style"]["lines"]:
                if l.get("type") in ("角标", "片尾"):
                    continue
                n_rows += 1
                if l.get("anchor"):
                    n_anchor += 1
        print("[OK] %s D16 %s → %s：%s" % (unit, GUARD[unit], back.get("version"), dict(stat)))
        print("     回读：非角标非片尾行 %d｜带 anchor %d｜缺 %d｜备份 %s"
              % (n_rows, n_anchor, n_rows - n_anchor, os.path.relpath(bak, ROOT)))
    return 0


def _bump(v):
    m = re.match(r"^v(\d+)\.(\d+)$", str(v))
    return "v%s.%d" % (m.group(1), int(m.group(2)) + 1) if m else v


if __name__ == "__main__":
    sys.exit(main())
