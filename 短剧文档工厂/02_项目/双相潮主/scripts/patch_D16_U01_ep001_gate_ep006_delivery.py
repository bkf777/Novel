#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01 D16 补丁：ep001 闸位补齐完整字段集 ＋ ep006 `delivery` 字面改档（R-026f · 任务一/任务二）。

背景（总控 2026-10-23 12:1x 派单，D18 v1.119 Q101①／Q104）：

  【任务一】D16 U01 的 `subtitle_style.golden3s_first_line` 是黄金 3 秒的**判据登记位**
    （Q101①：D08/D09 无秒级字段、承担不了判据）。派单时 ep001 **无该键**，属更早批次的落盘缺口。
    **落盘事实**：12:13:28 由并行实例把 D16 U01 升到 v1.21 并**补上了 ep001 的闸位**
    （status「达标」／d15_vo_at_sec 0.5／d15_vo_dur_sec 3.5／d15_line_ref「D09 ep1 #1」），
    12:20:30 又升到 v1.22。⇒ **登记位本身已闭合**；但逐键比对发现 ep001 仍是
    ep002–ep008 里**唯一缺 `text`（首句原文）** 的一集（ep002 有、ep003–ep008 都有），
    且比 ep002 少 `target_at_sec` ⇒ 同一字段仍存在两套写法。
    本补丁**只做补齐**（加 `text` ＋ `target_at_sec`），**逐字照 ep002 现盘的键集合与顺序**，
    不新造字段名、不改写他人已落的 note 原文（只追加一条留痕）。

  【任务二】Q104 裁定画外音 `delivery` 字面按「身份是否在画幅内可辨识」分三档：
    ①「人物不出画」＝ 角色完全无任何形象出现在画幅内；
    ②「**身份不出画**」＝ 角色在画幅内以可辨识形象出现、但身份不可辨识（如无面部剪影）—— **ep006 属这一档**；
    ③「主观声」＝ 角色以内心声出现且画幅内无其任何形象。
    「首帧给最强符号」是独立于三档的通用约束，**不随档位变，仍须保留**。
    ep006 镜1 的画幅事实：D11 U01 v1.14 `visual_facts`＝「厂房暗处的一道**剪影**暴起冲出……」
    ＋ D12 卡 C-021 `params.seed_strategy`「角色域 seed 固定 **LC:110101**」、`char_ids=[\"LC\"]`
    ⇒ 陆沉（LC）**确实在画幅内**，只是不给面部/不给身份锚点。
    **落盘事实**：并行实例已于 D16 U01 v1.22 把 `delivery` 改为
    「画外音（**身份**不出画，首帧给最强符号）」（D15 U01 v1.13 同字面，两侧可逐字段比对），
    并把 Q104 裁定写进闸位 note 与对白行 note。⇒ **任务二已闭合**；
    本脚本只做**复核**（若现盘仍是旧字面才落改，属幂等），**不重复改写他人已落的裁定记录**。

**真值源＝D15 现盘**（本脚本每次运行都现读 `units/U01/D15.json`），D16 只落副本。
**不动的**：D15 配音数据、D08/D09/D11/D12/D14、shared/**、ep002–ep008 其余六集的闸位字段、
  全部 in_sec／out_sec 数值。

用法：python3 scripts/patch_D16_U01_ep001_gate_ep006_delivery.py          # 落盘
      python3 scripts/patch_D16_U01_ep001_gate_ep006_delivery.py --check  # 只校验，不写盘
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

D16_PATH = P("units", "U01", "D16.json")
D15_PATH = P("units", "U01", "D15.json")
D11_PATH = P("units", "U01", "D11.json")
D12_PATH = P("units", "U01", "D12.json")

TARGET = "首句台词 ≤1.5s 入画（短剧黄金 3 秒）"
OLD_DELIVERY = "画外音（人物不出画，首帧给最强符号）"
NEW_DELIVERY = "画外音（身份不出画，首帧给最强符号）"

# ---- 断言清单 ----------------------------------------------------------
ASSERT_MANIFEST = [
    ("C01", "D16 U01 磁盘版本可读；新版本号 = 现盘 + 1（不沿用旧号）"),
    ("C02", "ep002 现盘闸位键集合 == ep001 本轮落盘所用的键集合（同一模板，不新造字段名）"),
    ("C03", "D15 U01 ep001 首条 voice_over：at_sec==0.5、dur_sec==3.5、line_ref=='D09 ep1 #1'"),
    ("C04", "D15 U01 ep001 首条**无** delivery 键（非画外音）"),
    ("C05", "D11 U01 ep001 镜1 visual_facts 含该角色（陆沉在画幅内）→ ep001 闸位**不加** delivery"),
    ("C06", "D16 ep001 首条对白字幕行 in/out == (0.5, 4.0)，与 D15 at_sec＋dur_sec 逐条相等"),
    ("C07", "ep001 首句原文取 D09 U01 ep1 #1 逐字（含「」），与 D08 口径一致"),
    ("C08", "ep006 delivery 现值 ∈ {旧字面, 新字面}；若为旧字面则按 Q104 改档并登记裁定"),
    ("C09", "D11 U01 ep006 镜1 visual_facts 含「剪影」（角色以不可辨识形象在画幅内 → 第二档）"),
    ("C10", "D12 U01 卡 C-021：consistency_refs.char_ids 含 'LC' 且 seed_strategy 含 'LC:110101'"),
    ("C11", "ep006 delivery 终值 == 新字面「画外音（身份不出画，首帧给最强符号）」（首帧给最强符号保留）"),
    ("C12", "ep005 delivery 保持「人物不出画」（该集说话人不在镜1 画幅内，D12 C-017 char_ids 为空）"),
    ("C13", "ep002–ep008 其余各集闸位字段零改动（逐键比对改前改后）"),
    ("C14", "全部 in_sec／out_sec 数值零改动（数值区逐值比对）"),
    ("C15", "写盘前复核磁盘版本未变（并发守卫；变了即中止）"),
]


def nominal(x):
    return round(x + 1e-9, 1)


def ep_of(doc, ep):
    return [e for e in doc["episodes"] if e["ep"] == ep][0]


def d15_first(ep):
    e = ep_of(D15, ep)
    vos = sorted(e["voice_over"], key=lambda v: v["at_sec"])
    first = vos[0]
    assert first["line_ref"] == f"D09 ep{ep} #1", f"ep{ep} 首条 line_ref 异常：{first['line_ref']}"
    return first


def d11_shot(ep, shot_id):
    for s in ep_of(D11, ep)["shots"]:
        if s["shot_id"] == shot_id:
            return s
    raise AssertionError(f"ep{ep} 无镜{shot_id}")


def numeric_snapshot(doc):
    out = []
    for e in doc["episodes"]:
        for l in e["subtitle_style"].get("lines", []):
            out.append((e["ep"], l.get("seq"), l.get("in_sec"), l.get("out_sec")))
    return out


def main():
    check_only = "--check" in sys.argv
    errors = []

    global D16, D15, D11, D12
    D16 = json.load(open(D16_PATH, encoding="utf-8"))
    D15 = json.load(open(D15_PATH, encoding="utf-8"))
    D11 = json.load(open(D11_PATH, encoding="utf-8"))
    D12 = json.load(open(D12_PATH, encoding="utf-8"))

    base_version = D16.get("version")
    m = base_version.lstrip("v").split(".")
    NEW_VERSION = f"v{int(m[0])}.{int(m[1]) + 1}"
    d15_version = D15.get("version")

    eps16 = {e["ep"]: e for e in D16["episodes"]}
    ss1 = eps16[1]["subtitle_style"]
    ss2 = eps16[2]["subtitle_style"]
    ss5 = eps16[5]["subtitle_style"]
    ss6 = eps16[6]["subtitle_style"]

    # C02 模板键集合：以 ep002 现盘为准
    template_keys = list(ss2["golden3s_first_line"].keys())

    # C03 / C04 D15 真值
    v1 = d15_first(1)
    if v1["at_sec"] != 0.5:
        errors.append(f"C03 ep001：D15 首条 at_sec={v1['at_sec']} ≠ 0.5")
    if v1["dur_sec"] != 3.5:
        errors.append(f"C04 ep001：D15 首条 dur_sec={v1['dur_sec']} ≠ 3.5")
    if "delivery" in v1:
        errors.append("C04 ep001：D15 首条带 delivery 键 → 该句是画外音，本补丁「不加 delivery」前提不成立")

    # C05 D11 画幅事实
    s1 = d11_shot(1, 1)
    if "陆沉" not in s1.get("visual_facts", ""):
        errors.append("C05 ep001：D11 镜1 visual_facts 未见该角色 → 本补丁「不加 delivery」前提不成立")

    # C06 字幕行时码与 D15 实测逐条相等
    hit = None
    for l in ss1["lines"]:
        if l.get("type") == "对白" and l.get("text") == "上一趟我死在第三个小时。":
            hit = l
            break
    if hit is None:
        errors.append("C06 ep001：subtitle_style.lines 内找不到首句对白行")
    elif hit.get("in_sec") != 0.5 or hit.get("out_sec") != 4.0:
        errors.append(f"C06 ep001：首句行现值 ({hit.get('in_sec')}, {hit.get('out_sec')}) ≠ (0.5, 4.0)")

    # C07 首句原文取 D09
    d09 = json.load(open(P("units", "U01", "D09.json"), encoding="utf-8"))
    d09_1 = [l for l in d09["lines"] if l["ep"] == 1 and l["idx"] == 1]
    if not d09_1:
        errors.append("C07 ep001：D09 U01 无 ep1 #1")
        first_text = "「上一趟我死在第三个小时。」"
    else:
        first_text = d09_1[0]["text"]

    # C08 ep006 delivery 现值
    g6 = ss6["golden3s_first_line"]
    cur_delivery = g6.get("delivery")
    if cur_delivery not in (OLD_DELIVERY, NEW_DELIVERY):
        errors.append(f"C08 ep006 现盘 delivery={cur_delivery!r} 既非旧字面也非新字面（疑似并发改写）")

    # C09 / C10 画幅事实取证
    s6 = d11_shot(6, 1)
    if "剪影" not in s6.get("visual_facts", ""):
        errors.append("C09 ep006：D11 镜1 visual_facts 未见「剪影」→ 分档前提不成立")
    card = [c for c in D12["cards"] if c.get("card_id") == "C-021"]
    if not card:
        errors.append("C10 ep006：D12 无 C-021 卡")
    else:
        c21 = card[0]
        if "LC" not in (c21.get("consistency_refs", {}).get("char_ids") or []):
            errors.append("C10 ep006：C-021 consistency_refs.char_ids 未含 'LC'")
        if "LC:110101" not in (c21.get("params", {}).get("seed_strategy") or ""):
            errors.append("C10 ep006：C-021 params.seed_strategy 未含 'LC:110101'")

    # C12 ep005 保持「人物不出画」
    c017 = [c for c in D12["cards"] if c.get("card_id") == "C-017"]
    if c017 and (c017[0].get("consistency_refs", {}).get("char_ids") or []):
        errors.append("C12 ep005：C-017 char_ids 非空 → 该集说话人可能在画幅内，须重判分档")
    if ss5["golden3s_first_line"].get("delivery") != OLD_DELIVERY:
        errors.append(f"C12 ep005：delivery 现值 {ss5['golden3s_first_line'].get('delivery')!r} "
                      "≠ 旧字面（本补丁不改 ep005）")

    if errors:
        for x in errors:
            print("❌ " + x)
        return 1

    # ── 落盘前的逐键快照（C13／C14 用） ──
    before_gates = {ep: json.dumps(eps16[ep]["subtitle_style"].get("golden3s_first_line"),
                                  ensure_ascii=False, sort_keys=True)
                    for ep in range(2, 9)}
    before_nums = numeric_snapshot(D16)

    # ── 任务一：ep001 闸位补齐（逐字照 ep002 现盘键集合与顺序）──
    g1 = ss1.get("golden3s_first_line")
    if g1 is None:
        # 极端兜底：闸位整体缺失 → 整块新建
        g1 = {
            "target": TARGET,
            "status": "达标",
            "target_at_sec": 0.5,
            "text": first_text,
            "d15_vo_at_sec": v1["at_sec"],
            "d15_vo_dur_sec": v1["dur_sec"],
            "d15_line_ref": v1["line_ref"],
            "note": "",
        }
        ss1["golden3s_first_line"] = g1
        created = True
    else:
        created = False
        # 已有闸位 → 只补齐缺失键，保留他人已落的值与 note 原文
        if "text" not in g1:
            g1["text"] = first_text
        if "target_at_sec" not in g1:
            g1["target_at_sec"] = 0.5
        if g1.get("status") != "达标":
            errors.append(f"C01 ep001：闸位 status 现值 {g1.get('status')!r} ≠ 达标")

    # 按 ep002 的键顺序重排（同一模板不两套写法）
    ordered = {}
    for k in template_keys:
        if k in g1:
            ordered[k] = g1[k]
    for k, v in g1.items():
        if k not in ordered:
            ordered[k] = v
    ss1["golden3s_first_line"] = ordered

    # note 追加留痕（不覆盖他人原文）
    note1 = ordered.get("note", "")
    trace = ("｜【R-026f 补齐 · 2026-10-23 · 分镜导演岗】本闸位由并行实例于 D16 U01 v1.21 补上"
             "（status「达标」／d15_vo_at_sec 0.5／d15_vo_dur_sec 3.5／d15_line_ref「D09 ep1 #1」）；"
             "本轮按派单把 `text`（首句原文，取 D09 U01 ep1 #1 逐字）与 `target_at_sec` 补齐，"
             "使 ep001 与 ep002–ep008 同一模板、同一键集合。"
             "D15 U01 " + str(d15_version) + " 现盘实测：首句 at_sec＝0.5s、dur_sec＝3.5s，"
             "本表该行 0.5~4.0s 与之逐条相等；镜1 的 visual_facts 为「陆沉抬起右手腕占住画面前景」，"
             "角色在画幅内（D15 该条无 `delivery`，非画外音），故本闸位**不加** delivery。"
             "首帧给最强符号＝已经出事的画面（腕上旧印＋满地狼藉的出租屋）。")
    if trace not in note1:
        ordered["note"] = note1 + trace

    # ── 任务二：ep006 delivery 字面（幂等；已是新字面则只复核不重写）──
    task2_changed = False
    if g6.get("delivery") == OLD_DELIVERY:
        g6["delivery"] = NEW_DELIVERY
        task2_changed = True
        OLD_CLAUSE = ("⚠️ **口径差异（登记待总控裁决，本岗不自行改判）**")
        NEW_CLAUSE = ("⚠️ **口径已由总控 Q104 裁定（本轮落字）**")
        if OLD_CLAUSE in g6.get("note", ""):
            g6["note"] = g6["note"].replace(OLD_CLAUSE, NEW_CLAUSE)

    # C11 复核
    if g6["delivery"] != NEW_DELIVERY:
        print("❌ C11 中止：ep006 delivery 终值异常")
        return 1
    if "首帧给最强符号" not in g6["delivery"]:
        print("❌ C11 中止：ep006 delivery 丢失「首帧给最强符号」")
        return 1

    # C13 / C14 复核（ep001 的闸位是本轮唯一允许变化的条目）
    after_gates = {ep: json.dumps(eps16[ep]["subtitle_style"].get("golden3s_first_line"),
                                  ensure_ascii=False, sort_keys=True)
                   for ep in range(2, 9)}
    for ep in range(2, 9):
        if ep == 6 and task2_changed:
            continue  # ep006 本轮由旧字面改档（任务二本体）
        if before_gates[ep] != after_gates[ep]:
            print(f"❌ C13 中止：ep{ep} 闸位被意外改动")
            return 1
    if before_nums != numeric_snapshot(D16):
        print("❌ C14 中止：in_sec／out_sec 数值区被意外改动")
        return 1

    # C02 复核：ep001 键集合 == ep002 键集合
    if list(ss1["golden3s_first_line"].keys()) != template_keys:
        print(f"❌ C02 中止：ep001 闸位键集合 {list(ss1['golden3s_first_line'].keys())} ≠ ep002 {template_keys}")
        return 1

    D16["version"] = NEW_VERSION

    if check_only:
        print(f"✅ --check 通过（C01–C15 全部成立）；未写盘。")
        print(f"   ep001 闸位键集合：{template_keys}")
        print(f"   ep006 delivery：{g6['delivery']}"
              f"（{'本轮改档' if task2_changed else '已由并行实例闭合，本轮只复核'}）")
        print(f"   版本：{base_version} → {NEW_VERSION}")
        return 0

    # C15 并发守卫：写盘前复核磁盘版本未变
    disk_now = json.load(open(D16_PATH, encoding="utf-8")).get("version")
    if disk_now != base_version:
        print(f"❌ C15 中止：写盘前磁盘版本已变为 {disk_now}（本轮基线 {base_version}）—— 并发改写，本岗不写盘。")
        return 2

    ts = time.strftime("%Y%m%d-%H%M%S")
    bakdir = P("reports", f"_bak_D16_U01_ep001gate_ep006delivery_{ts}")
    os.makedirs(bakdir, exist_ok=True)
    shutil.copy2(D16_PATH, os.path.join(bakdir, "D16.json"))

    tmp = D16_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(D16, f, ensure_ascii=False, indent=2)
    os.replace(tmp, D16_PATH)

    print(f"✅ 已落盘：{os.path.relpath(D16_PATH, ROOT)}  {base_version} → {NEW_VERSION}")
    print(f"   备份：{os.path.relpath(bakdir, ROOT)}")
    print(f"   ① ep001 闸位补齐：键集合 == ep002 现盘 {template_keys}"
          f"（{'整块新建' if created else '补 text ＋ target_at_sec，保留他人 note 原文并追加留痕'}）")
    print(f"   ② ep006 delivery：{g6['delivery']}"
          f"（{'本轮改档' if task2_changed else '已是新字面（并行实例已闭合），本轮只复核不改写'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
