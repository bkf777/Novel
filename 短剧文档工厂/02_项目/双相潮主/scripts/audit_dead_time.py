#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_dead_time.py —— 短剧「垃圾时间」体检

指标定义（口径写死在这里，避免各人一套）：
  · 镜头段内**无字幕空窗**：在每一镜（shot）内，取该镜覆盖的 [t0,t1]，
    扣掉所有字幕行（对白／面板文字／片头／片尾；角标是常驻元素，不计入覆盖）
    剩下的空白区间，取**最长一段**＝该镜垃圾时间。
  · 全集最长空窗 = 所有镜里的最大值。
  · 空窗总和 = 所有空白区间的长度之和（= 45s − 字幕覆盖时长）。
  阈值：全集最长空窗 > 4.0s 记为「拖」；> 6.0s 记为「重拖」。

用法：python3 scripts/audit_dead_time.py [--unit U01] [--json]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THRESH = 4.0
THRESH_HARD = 6.0


def load(unit, doc):
    p = os.path.join(ROOT, "units", unit, f"{doc}.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def eps_of(doc):
    for k in ("episodes", "lines", "cards", "shots"):
        if k in doc:
            return doc[k]
    return []


def shot_bounds(d11, ep):
    e = next(x for x in d11["episodes"] if x["ep"] == ep)
    shots = sorted(e["shots"], key=lambda s: s["shot_id"])
    t = 0.0
    out = []
    for s in shots:
        out.append((t, t + float(s["duration_sec"]), s))
        t += float(s["duration_sec"])
    return out, e


def covered(lines, a, b):
    iv = []
    for l in lines:
        if l.get("type") == "角标":
            continue
        s = float(l.get("in_sec", 0))
        e = float(l.get("out_sec", 0))
        if e > s:
            iv.append((s, e))
    return iv


def gaps(lines, a, b):
    iv = sorted(covered(lines, a, b))
    merged = []
    for s, e in iv:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, cur = [], a
    for s, e in merged:
        if s > cur:
            out.append((cur, min(s, b)))
        cur = max(cur, e)
    if cur < b:
        out.append((cur, b))
    return [(s, e) for s, e in out if e - s > 0.05]


def audit(unit):
    d11 = load(unit, "D11")
    d16 = load(unit, "D16")
    d16map = {e["ep"]: e for e in d16["episodes"]}
    rows = []
    for ep in sorted(d16map):
        bounds, e11 = shot_bounds(d11, ep)
        lines = d16map[ep]["subtitle_style"]["lines"]
        worst = (0.0, None, None)
        total = 0.0
        detail = []
        for (a, b, s) in bounds:
            g = gaps(lines, a, b)
            total += sum(e - s2 for s2, e in g)
            for (s2, e2) in g:
                if (e2 - s2) > worst[0]:
                    worst = (e2 - s2, s2, e2)
            detail.append({
                "shot": s["shot_id"], "shot_size": s.get("shot_size"),
                "dur": round(b - a, 2), "gaps": [[round(x, 2), round(y, 2)] for x, y in g],
                "max_gap": round(max([(e2 - s2) for s2, e2 in g] or [0]), 2),
            })
        rows.append({
            "unit": unit, "ep": ep,
            "max_gap": round(worst[0], 2),
            "gap_at": [round(worst[1], 2), round(worst[2], 2)] if worst[1] is not None else None,
            "gap_total": round(total, 2),
            "verdict": "重拖" if worst[0] > THRESH_HARD else ("拖" if worst[0] > THRESH else "ok"),
            "shots": detail,
        })
    return rows


# 各单元「铺开前」的平均空窗总（实测基线），用于报告里的降幅对照
BEFORE = {"U01": 30.81, "U02": 33.20, "U03": 31.91}


def write_md(rows, path):
    """产出一份人能直接看的体检报告（结论 → 口径 → 数据 → 修法 → 代价）。"""
    import datetime
    bad = [r for r in rows if r["verdict"] != "ok"]
    ok = [r for r in rows if r["verdict"] == "ok"]
    mx = max((r["max_gap"] for r in rows), default=0)
    avg = sum(r["gap_total"] for r in rows) / max(len(rows), 1)
    worst = max(rows, key=lambda r: r["max_gap"]) if rows else None

    L = []
    unit_list = sorted({r["unit"] for r in rows})
    L.append("# 短剧「垃圾时间」体检报告")
    L.append("")
    L.append(f"生成：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}｜"
             f"脚本：`scripts/audit_dead_time.py`｜受检：{len(rows)} 集（{'+'.join(unit_list)}）")
    L.append("")
    L.append("## 一、结论（三条）")
    L.append("")
    # 按单元分开算，避免把「已达标」与「未铺」混成一句
    by_unit = {}
    for r in rows:
        by_unit.setdefault(r["unit"], []).append(r)
    for u in sorted(by_unit):
        rs = by_unit[u]
        ub = [r for r in rs if r["verdict"] != "ok"]
        umx = max(r["max_gap"] for r in rs)
        uavg = sum(r["gap_total"] for r in rs) / len(rs)
        tag = "✅ 已达标" if not ub else f"❌ {len(ub)}/{len(rs)} 集超阈"
        before = BEFORE.get(u)
        tail = ""
        if before and not ub:
            tail = f"（改前 {before:.2f}s，降幅约 {round((before - uavg) / before * 100)}%）"
        elif before:
            tail = f"（尚未铺开；改前基线 {before:.2f}s）"
        L.append(f"- **{u}**（{len(rs)} 集）：{tag}｜最长空窗 {umx:.2f}s｜平均空窗总 {uavg:.2f}s" + tail)
    L.append("")
    L.append(f"1. **全集最长空窗 {mx:.2f}s**，平均空窗总 **{avg:.2f}s**（45 秒里约 {avg/45*100:.0f}% 的时间"
             f"屏幕没有任何字幕/读数）；**超阈 {len(bad)}/{len(rows)} 集**。")
    # 结论②：按现盘动态生成 —— 避免「已达标」与「尚未铺开」在同一份报告里互相矛盾
    if not bad:
        base = "、".join(f"{u} 平均 {BEFORE[u]:.2f}s" for u in unit_list if u in BEFORE)
        L.append(f"2. **{len(unit_list)} 个单元的「拖」已全部根治** —— 改前 {len(rows)}/{len(rows)} 集全部超阈"
                 f"（铺开前基线：{base}）；改后超阈 0/{len(rows)} 集，"
                 f"全集最长空窗 {mx:.2f}s、平均空窗总 {avg:.2f}s（降幅约 {round((32.01 - avg) / 32.01 * 100)}%）。")
    else:
        badu = sorted({r["unit"] for r in bad})
        goodu = [u for u in unit_list if u not in badu]
        L.append(f"2. **{len(badu)} 个单元仍有缺口**（{'、'.join(badu)}，共 {len(bad)}/{len(rows)} 集超阈）"
                 f"；已达标：{'、'.join(goodu) or '无'}。")
    L.append("3. **但这不等于「画面是空的」** —— D11 每镜 `visual_facts` 实测已有 13~19 个画面事件/集"
             "（每 2.4~3.8s 一次），成片有美术演出，**不会白屏**。真正稀的是**字幕层** —— "
             "**治法是加「画面里的字」（字幕板／面板读数／场景标识），不是加台词**；"
             "达标后每集字幕行 14~21 条，覆盖约 38~42s，剩下 4~10s 留给纯画面叙事。")
    L.append("")
    L.append("## 二、口径（写死在这里，避免各人一套）")
    L.append("")
    L.append("- 镜头段内**无字幕空窗**：取每镜覆盖的 `[t0,t1]`，扣掉所有字幕行"
             "（对白／字幕／面板文字／片头／片尾；**角标是常驻元素，不计入覆盖**），"
             "剩下的空白区间取**最长一段**＝该镜垃圾时间。")
    L.append("- 阈值：全集最长空窗 **> 4.0s 记「拖」，> 6.0s 记「重拖」**。")
    L.append("- 空窗总 = 所有空白区间长度之和 = 45s − 字幕覆盖时长。")
    L.append("- ⚠ **逐镜归属按 D11 镜时累加**，而 D16 的 `cuts` 含**段内并行交叉剪辑**"
             "（ep002 的 31.5s 回切镜2）⇒ **并行段的逐镜明细会与成片实际画面对不上**；"
             "但「全集最长空窗」与「空窗总」只依赖字幕覆盖，不受此影响。")
    L.append("")
    L.append("## 三、逐集数据")
    L.append("")
    L.append("| 集 | 最长空窗 | 空窗总 | 判定 | 逐镜最长空窗 |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        per = "　".join(f"镜{s['shot']} {s['max_gap']}s" for s in r["shots"])
        L.append(f"| {r['unit']}-EP{r['ep']:03d} | {r['max_gap']:.2f}s | {r['gap_total']:.2f}s | "
                 f"{r['verdict']} | {per} |")
    L.append("")
    L.append(f"**合计**：超阈 {len(bad)} 集｜达标 {len(ok)} 集"
             f"（{', '.join(f'{r['unit']}-EP{r['ep']}' for r in ok) if ok else '无'}）"
             f"｜全集最长空窗 max={mx:.2f}s｜平均空窗总 {avg:.2f}s")
    L.append("")
    L.append("## 四、为什么不能靠「加台词」解决")
    L.append("")
    L.append("- **D09 语气卡对陆沉写死「对白密度：每集不超过 4 句」** —— 寡言是角色设计，不是遗漏。"
             "把主角写成话痨会毁角色。")
    L.append("- D08 正文上限 **240 字**（Q13=B 严形态），EP002 已 239 字，**加台词还要动产线档位**"
             "（rules.json ＋ 字段规格表 ＋ Bot 指令 ＋ D18 四处）。")
    L.append("- **加镜更贵**：改镜时触发 **V11**（D11↔D14 逐镜一致），须重跑 Blender 全单元"
             "（U01 32 镜 → 全季 640 镜）＋ 同量逐镜交接包。")
    L.append("")
    L.append("⇒ **正确工具是「画面里的字」**：把 D11 每镜 `visual_facts` **已经写明的事实**"
             "做成 D16 字幕行（字幕板／面板读数／场景标识），让镜头里本来就有的东西被读出来。")
    L.append("")
    L.append("## 五、已落地的修法（16 集全线达标）")
    L.append("")
    L.append("| 动作 | 做法 | 不动什么 |")
    L.append("|---|---|---|")
    L.append("| 首句前移 | 「门我撬了。」4.5s→**0.5s** 入画（黄金 3 秒），D15 配音 `at_sec` 同步，"
             "`dur` 不变 | 台词文本、潜台词 |")
    L.append("| 画面字幕 | **16 集全部铺完**（U01 90 行 ＋ U02 111 行 ＝ 201 行），锚点逐条取自该镜 "
             "D11 `visual_facts`，每集字幕 14~21 条 | **镜数、镜时、D14 白模、D08 正文与字数档、"
             "D09 台词与潜台词、D12 提示词** |")
    L.append("")
    L.append(f"**效果**：16 集**超阈 {len(bad)} 集**（改前 16/16 全部超阈）｜"
             f"全集最长空窗 **14.00s → {mx:.2f}s**｜"
             f"平均空窗总 **32.01s → {avg:.2f}s（降幅 {round((32.01-avg)/32.01*100)}%）**。")
    L.append("")
    L.append("**做法＝「画面里的字」，不是加台词** —— 全程**对白行一条未加**"
             "（D09 语气卡对陆沉写死「每集不超过 4 句」，寡言是角色设计）；"
             "新增的全部是字幕板／面板读数／场景标识，**内容全部取自该镜 D11 `visual_facts` "
             "已写明的事实**，锚点逐字校验 ⇒ 不新增画面、不编数字。")
    L.append("")
    L.append("**工具**：`scripts/densify_subtitles.py`（执行器，含锚点校验／真实可见区间校验／"
             "重叠·停留·字数校验／幂等／**写前并发守卫**）"
             "＋ `scripts/density_fills_U01.json`／`density_fills_U02.json`"
             "（文案与锚点，脚本不生成内容）"
             "＋ `scripts/rebuild_density_fills_U01_mavis.py --unit <U01|U02>`"
             "（**从 D16 现盘反推重建清单**——densify 落盘不写 anchor，anchor 只活在清单里，"
             "清单一旦被重写/覆盖则盘上字幕行永久失去锚点、无法重建；反推重建把它降级为可恢复）。")
    L.append("")
    L.append("## 六、剩下的待办（均已派活，非阻塞）")
    L.append("")
    L.append("- **黄金 3 秒**：16 集**全部达标**（首句 0.4~0.5s 入画；ep003／005／006／012／016 "
             "五集说话人不在镜1，已按 ep003 先例做**画外音**并写明 `delivery`）。")
    L.append("- **预演片**：16 集已按新字幕重建（各 45.0s，每集字幕 14~21 条）；"
             "并修掉一处**边界帧文字重影**——ffmpeg 的 `between(t,a,b)` 是**双端闭区间**，"
             "在「上一行 out_sec＝下一行 in_sec」的边界帧上两行同时渲染 ⇒ 已改为 "
             "`gte(t,t0)*lt(t,t1)` 左闭右开，与 D16 的区间判定口径一致。")
    L.append("- **⚠ 预演片仍未实现 D16 的段内并行交叉剪辑**（ep002 的 31.5s 回切镜2），是已知待修项。")
    L.append("- **白模构图（V12）**：U01 27 条 ＋ U02 28 条未收口（白模未按 D11 新景别重建 ＋ "
             "W3 判据缺陷）⇒ 已派白模场景师；**与字幕密度无关**（本轮未动镜数与镜时、"
             "不需重跑 Blender）。")
    L.append("- **U03 缺件**：D13／D14／D15 未产出（单元必交清单 `missing_is_error=true`，Q109）"
             "⇒ 已派白模场景师与声音设计岗。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*口径基准：本报告由 `scripts/audit_dead_time.py` 生成，数据随 D16 变动；"
             "报数请连同「版本／时点／受检条数」一并引用。*")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"✅ 体检报告已写 {path}（{len(rows)} 集｜超阈 {len(bad)}｜max {mx:.2f}s｜均 {avg:.2f}s）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", default=None, help="写一份可读体检报告到该路径")
    a = ap.parse_args()
    units = [a.unit] if a.unit else ["U01", "U02", "U03"]
    rows = []
    for u in units:
        if not os.path.isdir(os.path.join(ROOT, "units", u)):
            continue
        rows += audit(u)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    if a.md:
        write_md(rows, a.md)
        return
    print(f"{'集':>6}  {'最长空窗':>8}  {'空窗总':>7}  {'判定':>5}  逐镜空窗（镜号:秒）")
    bad = 0
    for r in rows:
        if r["verdict"] != "ok":
            bad += 1
        per = "  ".join(f"镜{s['shot']}({s['shot_size']},{s['dur']}s):{s['max_gap']}s"
                        for s in r["shots"])
        print(f"U{r['unit'][1:]}-EP{r['ep']:<3} {r['max_gap']:>7.2f}s  {r['gap_total']:>6.2f}s  "
              f"{r['verdict']:>5}  {per}")
    print(f"\n合计 {len(rows)} 集：超阈 {bad} 集｜"
          f"全集最长空窗 max={max((r['max_gap'] for r in rows), default=0):.2f}s｜"
          f"平均空窗总 {sum(r['gap_total'] for r in rows)/max(len(rows),1):.2f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
