#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_hook_types.py —— 按 short-drama skill 的 5 类钩子为 D06 补 `hook_type`

来源
----
用户 2026-10-23 指派：学习 https://github.com/0xsline/short-drama/tree/main 这个 skill
并据其描述改写。该 skill 的 `references/hook-design.md` 定义 **5 种钩子类型**
（悬念／反转／情绪／信息／危机）与配比参考：
    情绪钩 30-40%｜悬念钩 20-30%｜危机钩 10-20%｜信息钩 10-20%｜反转钩 5-15%

我们的 D06 只有 `hook_in`／`hook_out` 两段文字，**没有类型标注** ⇒
既写不出 skill 格式剧本的 `Hook Type` 字段，也做不了配比审计。

判定口径（**按 hook_out 的落点判，不按 beats 判**）
--------------------------------------------------
钩子是把观众按在下一集的那个信息，所以看的是"这一集最后落在观众眼前的到底是什么"：
  · 信息钩 —— 落在**新信息/新变量**被揭示（面板读数、新角色、新势力、新规则）
  · 悬念钩 —— 落在**一个问题被抛出但没答**（十一下钟声意味着什么、那封信写了什么）
  · 危机钩 —— 落在**威胁已经到场**（追兵进窗框、暗杀组点名、灰雾不散）
  · 情绪钩 —— 落在**情绪的兑现或决裂**（有人站到你这边、有人对你动手、有人为你烧了三天）
  · 反转钩 —— 落在**认知被推翻**（你以为他是军阀，他画出了防御图；你以为救人，条款里只有价钱）

幂等：已写且一致则不写盘。
用法：python3 scripts/plan_hook_types.py [--unit U01] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# ── 人工撰写的分配表（可改；改后重跑即可，幂等）────────────────────────
PLAN = {
    "U01": {
        1: ("信息", "hook_out 落在**新信息揭示**：面板倒计时 2 小时 58 分与目的地同时给出，"
                     "观众第一次知道这一趟的时间和战场——是信息，不是威胁。"),
        2: ("悬念", "hook_out 落在**一个被抛出但没答的问题**：全城钟楼敲响十一下，"
                     "十一下意味着什么全片未解，观众要留着看。"),
        3: ("危机", "hook_out 落在**威胁已经到场**：触角顶开水泥地面，灾变从预告变成眼前。"),
        4: ("危机", "hook_out 落在**追兵进窗框**：车灯把装甲车照进来，威胁已抵近，不是悬念而是压迫。"),
        5: ("悬念", "hook_out 落在**身份问题**：那张脸是谁、上一趟的处置令是谁签的，"
                     "只抛不解。"),
        6: ("危机", "hook_out 落在**处境骤变**：跃下钢板直接落进深坑，退路断在脚底下。"),
        7: ("情绪", "hook_out 落在**情绪兑现**：她站到他身侧——不是新信息也不是威胁，"
                     "是这一集攒下来的信任终于兑现。"),
        8: ("信息", "hook_out 落在**新变量入场**：苏清辞求救，一个此前不存在的力量进场。"),
    },
    "U02": {
        9: ("悬念", "hook_out 落在**误会未解**：苏清辞认定这是军阀，误读本身就是钩子。"),
        10: ("反转", "hook_out 落在**认知被推翻**：他画出的防御图连陆沉都看不懂——"
                      "从「军阀」到「技术靠山」，是典型反转钩。"),
        11: ("信息", "hook_out 落在**新规则开启**：新手期结束、黑市开市，规则变了。"),
        12: ("反转", "hook_out 落在**功能反转**：净火从「武器」变成「能买卖的商品」，"
                      "主角第一次把自己变成了生意人。"),
        13: ("信息", "hook_out 落在**格局变动**：叶家与云顶财阀第一次同席，敌敌关系换了位。"),
        14: ("危机", "hook_out 落在**杀意落定**：城防图上点掉机械厂的名字，威胁已下文书。"),
        15: ("危机", "hook_out 落在**威胁已现身**：围墙上一排不该在的影子，敌人已经到了。"),
        16: ("情绪", "hook_out 落在**情绪兑现**：叶红衣迎战，大限夜当口顶上，是燃点不是悬念。"),
    },
    "U03": {
        17: ("情绪", "hook_out 落在**燃点**：骨威全开、切断退路、从阴影里走出来——爽感兑现。"),
        18: ("信息", "hook_out 落在**新线索**：留下主谋身份铭牌**与敌酋纹章**，"
                      "敌酋第一次有了可查的符号。"),
        19: ("情绪", "hook_out 落在**人心向附**：四面流民涌向机械厂，是被认可的情绪兑现。"),
        20: ("危机", "hook_out 落在**规则失效**：大限夜已过而灰雾不散，靠山塌了，威胁升级。"),
        21: ("信息", "hook_out 落在**新势力亮相**：同心潮纹标记浮出，第三方第一次现身。"),
        22: ("悬念", "hook_out 落在**未拆的信**：读出来但没说是写了什么。"),
        23: ("反转", "hook_out 落在**信仰被推翻**：条款里没有一句救人，只有雾核数目——"
                      "他救人，对方牟利，认知整个翻面。"),
        24: ("情绪", "hook_out 落在**代价的重量**：日夜焚斑救人数万，代价是命在烧。"),
    },
}

# skill 的配比参考（references/hook-design.md）
BENCH = {"情绪": (0.30, 0.40), "悬念": (0.20, 0.30), "危机": (0.10, 0.20),
         "信息": (0.10, 0.20), "反转": (0.05, 0.15)}


def fingerprint(p):
    b = open(p, "rb").read()
    return {"version": json.loads(b.decode("utf-8")).get("version"),
            "size": len(b), "sha16": hashlib.sha256(b).hexdigest()[:16],
            "mtime": os.path.getmtime(p)}


def bump(o):
    v = re.sub(r"^v+", "v", str(o.get("version", "v1.0")))
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    units = [a.unit] if a.unit else list(PLAN.keys())
    all_rows = []
    for unit in units:
        p = os.path.join(ROOT, "units", unit, "D06.json")
        if not os.path.exists(p):
            print(f"⏭  {unit} 无 D06，跳过")
            continue
        fp0 = fingerprint(p)
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        print(f"\n[{unit}] 基线 D06 v{fp0['version']} {fp0['size']} B sha16={fp0['sha16']}")

        changed = False
        for e in d.get("episodes", []):
            ep = e.get("ep")
            item = PLAN.get(unit, {}).get(ep)
            if not item:
                print(f"   ⚠ ep{ep} 无人工分配条目，跳过")
                continue
            ht, reason = item
            if e.get("hook_type") == ht and e.get("hook_type_reason") == reason:
                print(f"   ⏭ ep{ep} 已是「{ht}」，跳过")
            else:
                e["hook_type"] = ht
                e["hook_type_reason"] = reason
                changed = True
                print(f"   ✅ ep{ep} hook_type = {ht}")
            all_rows.append((unit, ep, ht))

        if not changed:
            print(f"   {unit} 无变化，不写盘")
            continue
        if a.dry_run:
            print(f"   [dry-run] 将写 {unit} D06")
            continue
        now = fingerprint(p)
        if now != fp0:
            print(f"❌ 并发守卫：{unit} D06 在读盘后被改动（{fp0} → {now}）⇒ 放弃写盘")
            sys.exit(1)
        bak = os.path.join(ROOT, "reports", f"_bak_hooktype_{unit}_{STAMP}")
        os.makedirs(bak, exist_ok=True)
        shutil.copy2(p, os.path.join(bak, "D06.json"))
        bump(d)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 写 {unit} D06.json（v{d.get('version')}）｜备份 {bak}")

    # ── 配比审计（对全部单元汇总）──────────────────────────────────────
    if all_rows:
        from collections import Counter
        c = Counter(h for _u, _e, h in all_rows)
        n = len(all_rows)
        print(f"\n=== 钩子配比审计（受检 {n} 集）===")
        print(f"{'类型':>4} {'实得':>5} {'占比':>7}   skill 参考")
        for k, (lo, hi) in BENCH.items():
            v = c.get(k, 0)
            pct = v / n * 100
            flag = "" if lo * 100 <= pct <= hi * 100 else "  ⚠ 偏离"
            print(f"{k:>4} {v:>5} {pct:>6.1f}%   {lo*100:.0f}-{hi*100:.0f}%{flag}")
        off = [k for k, (lo, hi) in BENCH.items()
               if not (lo * 100 <= c.get(k, 0) / n * 100 <= hi * 100)]
        if off:
            print(f"   ⚠ 偏离类型：{'、'.join(off)} —— 铺开 160 集前须按 skill 配比重排"
                  f"（情绪钩偏少、信息/危机偏多）")


if __name__ == "__main__":
    main()
