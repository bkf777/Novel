#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ledger_round3_0725.py —— 第六波核销 ＋ 三项裁定 ＋ 两处新登记（企划合规 2026-10-23 07:25）

本轮是「分镜导演 07:1x 交付通报」后的集中核销。三项裁定：
  ① **面板口径收口**（分镜导演请求复核）→ 裁「读数栏数值留画面、不进字幕层；面板本体提示/通报文字进字幕层」
  ② **Q56② U01 侧判据清单化落点**（分镜导演 §七十一.4 提问）→ 落点＝**在 reconcile 脚本内加判据清单＋机械守卫**，
     **不新建构建脚本**（U01 侧不存在该载体）
  ③ **共享脚本归属口径**（OPS-16）→ 声明唯一 ＋ 双向核对表写明两侧责任 ＋ 改动须同步并重跑覆盖轴

核销：U02-R09（我复核通过）／U01-R20（唯一残留已落盘 D12 v1.5）／U01-R18（9+9 达标、ERR 0）
新登记：U01-R33（U01 侧清单化派单）／Q70（归属声明与实际写者必须一致）

⚠️ 编号口径：Q67/Q68/Q69 已被并行企划合规实例占用（Q67＝敏感度检验），**本轮新判据一律取 Q70**，不与并行实例撞号。
⚠️ 索引 D18 版本提法**有两处**（§五 企划合规行 ＋ §六 交付物表 D18 行），两处都要更新；§六 行**中段历史留痕里的旧计数不动**。

用法：python3 scripts/patch_ledger_round3_0725.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

NOW = "2026-10-23 07:25"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
    """支持 零/一/…/九/十/十一/…/九十九/一百/一百零一 等写法。"""
    s = s.strip()
    if "百" in s:
        head, tail = s.split("百", 1)
        base = (CN[head] if head else 1) * 100
        return base + (cn_to_int(tail) if tail else 0)
    if "十" in s:
        head, tail = s.split("十", 1)
        return (CN[head] if head else 1) * 10 + (CN[tail] if tail else 0)
    return CN[s]


def int_to_cn(n):
    if n < 10:
        return "零一二三四五六七八九"[n]
    if n < 20:
        return "十" + ("" if n == 10 else "一二三四五六七八九"[n - 10])
    if n < 100:
        head, tail = divmod(n, 10)
        return ("零一二三四五六七八九"[head] if head > 1 else "") + "十" + \
               ("零一二三四五六七八九"[tail] if tail else 0)
    head, tail = divmod(n, 100)
    out = "零一二三四五六七八九"[head] + "百"
    if tail == 0:
        return out
    if tail < 10:
        return out + "零" + "一二三四五六七八九"[tail]
    return out + int_to_cn(tail)


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    p_idx = os.path.join(proj, "00_项目索引.md")
    p_prj = os.path.join(proj, "project.json")
    p_del = os.path.join(proj, "99_交付说明.md")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检（全部以磁盘实况为准） ----------
    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 69):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.69；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    for i in ("U01-R33",):
        if i in oi:
            sys.exit(f"[ABORT] open_issues 已含 {i}，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if "Q70" in gc_ids:
        sys.exit("[ABORT] global_checks 已含 Q70，不重复登记；不写盘。")
    for i in ("U02-R09", "U01-R18", "U01-R20", "U01-R22", "OPS-16"):
        if i not in oi:
            sys.exit(f"[ABORT] open_issues 无 {i}；不写盘。")

    # 交付物实况自检（防止台账与盘脱节）
    u01d15 = json.load(open(os.path.join(proj, "units", "U01", "D15.json"), encoding="utf-8"))
    u01d16 = json.load(open(os.path.join(proj, "units", "U01", "D16.json"), encoding="utf-8"))
    u01d12 = json.load(open(os.path.join(proj, "units", "U01", "D12.json"), encoding="utf-8"))
    u02d16 = json.load(open(os.path.join(proj, "units", "U02", "D16.json"), encoding="utf-8"))
    u02d11 = json.load(open(os.path.join(proj, "units", "U02", "D11.json"), encoding="utf-8"))
    vo = {v["line_ref"]: v["dur_sec"] for e in u01d15["episodes"] for v in e.get("voice_over", [])}
    want9 = {"D09 ep1 #1": 2.0, "D09 ep2 #2": 2.9, "D09 ep2 #3": 1.8, "D09 ep3 #2": 2.7,
             "D09 ep5 #1": 2.8, "D09 ep5 #2": 2.8, "D09 ep5 #4": 1.7,
             "D09 ep8 #1": 2.3, "D09 ep8 #4": 2.8}
    if sum(1 for k, v in want9.items() if vo.get(k) == v) != 9:
        sys.exit("[ABORT] D15 U01 的 9 条终表 dur_sec 未全达标；不写盘。")
    if vo.get("D09 ep2 #4") != 1.8:
        sys.exit("[ABORT] D15 U01 ep2#4 dur_sec ≠ 1.8；不写盘。")
    outs = {(e["ep"], l["seq"]): l.get("out_sec") for e in u01d16["episodes"]
            for l in e["subtitle_style"]["lines"]}
    want_out = {(1, 6): 12.4, (2, 6): 21.9, (2, 7): 36.8, (3, 8): 33.2, (5, 5): 15.8,
                (5, 6): 20.2, (5, 8): 41.7, (8, 5): 4.3, (8, 8): 41.4}
    if sum(1 for k, v in want_out.items() if outs.get(k) == v) != 9:
        sys.exit("[ABORT] D16 U01 的 9 行终表 out_sec 未全达标；不写盘。")
    if "左闭右开" not in (u01d16["episodes"][0]["subtitle_style"].get("sync_rule") or ""):
        sys.exit("[ABORT] D16 U01 sync_rule 未含左闭右开口径；不写盘。")
    neg53 = next((c.get("negatives", []) for c in u01d12.get("cards", [])
                  if c.get("ep") == 5 and c.get("shot_id") == 3), [])
    if any("no smoke from humans" in str(x) for x in neg53):
        sys.exit("[ABORT] D12 U01 ep5 镜3 仍含 no smoke from humans；不写盘。")
    if not any("no burning, no smoke" in str(x) for x in neg53):
        sys.exit("[ABORT] D12 U01 ep5 镜3 未含 no burning, no smoke；不写盘。")
    if any("归一度" in str(l.get("text", "")) for e in u02d16["episodes"]
           for l in e["subtitle_style"]["lines"]):
        sys.exit("[ABORT] D16 U02 仍有「归一度」字幕行；不写盘。")
    if len([e for e in u02d16["episodes"] if e["subtitle_style"].get("readout_in_frame")]) != 8:
        sys.exit("[ABORT] D16 U02 的 readout_in_frame 登记集 ≠ 8 集；不写盘。")

    # ---------- A. D18 ----------
    # A1 U02-R09 核销
    oi["U02-R09"]["status"] = "已复核·已闭环（企划合规 2026-10-23 07:2x）"
    oi["U02-R09"]["resolution"] = oi["U02-R09"]["resolution"].rstrip() + (
        "　**2026-10-23 07:2x 企划合规复核通过 → 闭环**：磁盘 `units/U02/D11.json` 现为 **v1.6**"
        "（分镜导演 07:1x 通报时报 v1.3，**以磁盘为准**）；ep014 镜3 visual_facts 实测逐字为"
        "「…委员会屏幕在另一侧亮起，冷金底色上**一列成本条目停在最后一栏，最后一栏数字没有合上**；…」"
        "→ 与 **D08 U02 body[4]**（「成本模型在屏幕上停住，最后一栏数字没有合上」）**方向对齐**；"
        "`scripts/shotintent_map_U02.mjs` 复跑 **exit 0**。**原冲突（方向相反）不复现。**"
    )

    # A2 U01-R20 核销
    oi["U01-R20"]["status"] = "已闭环（唯一残留已落盘 · 企划合规 2026-10-23 07:2x 复核）"
    oi["U01-R20"]["resolution"] = oi["U01-R20"]["resolution"].rstrip() + (
        "　**2026-10-23 07:2x 企划合规复核通过 → 闭环**：磁盘 `units/U01/D12.json` 现为 **v1.5**，"
        "ep5 镜3 negatives 实测 = **`no burning, no smoke` ＋ `frost-layer cold white mist preserved`**，"
        "**`no smoke from humans` 已除**；其余 31 张卡未动（视觉设定 07:1x 已回执核销，见 99_交付说明 §一百）。"
        "**结论：唯一真残留已处置，本条闭环；C-019「无霜白」与 C-031「盖住手腕」两项仍维持「不予转派」**"
        "（磁盘早已闭环，重复转派＝两个写者，§七·九）。"
    )

    # A3 U01-R18 追加核销事实
    if "07:2x 企划合规独立复核" not in oi["U01-R18"]["resolution"]:
        oi["U01-R18"]["resolution"] = oi["U01-R18"]["resolution"].rstrip() + (
            "　**2026-10-23 07:2x 企划合规独立复核**：磁盘 `units/U01/D15.json` 现为 **v1.6**、"
            "`units/U01/D16.json` 现为 **v1.10** → **终表 9 条 `dur_sec` 逐条 9/9 达标**"
            "（ep1#1 2.0／ep2#2 2.9／ep2#3 1.8／ep3#2 2.7／ep5#1 2.8／ep5#2 2.8／ep5#4 1.7／"
            "ep8#1 2.3／ep8#4 2.8）、**ep2#4 保持 1.8**；**D16 对应 9 行 `out_sec` 逐条 9/9 达标**"
            "（12.4／21.9／36.8／33.2／15.8／20.2／41.7／4.3／41.4）、**ep2 seq9 字幕文字＝「换我用了。」"
            "且 `out_sec` ＝ 43.0**（＝at+dur，同步口径成立）；`sync_rule` 已写死「左闭右开 ＋ 相接不算重叠 ＋ "
            "重叠检查覆盖全部正文行 ＋ 片尾标题卡单独检查」（Q51 落地）。"
            "**实测**：只读比对报告 `preview/U01_tts/tts_budget_check_U01.json`（06:45 落盘）＝ "
            "**verdict WARN／error_count 0／warn 2／ok 25／measured 27／vo_total 28／no_audio 1／"
            "d16_out_mismatch_count 0**。**⚠️ 注意口径**：**ERR 0 ≠ 28 条全过** —— 破坏项已清零，"
            "但 **ep2#4 因旧音频未重合成而未被实测**（`no_audio=1`），该条已转 **U01-R22** 归出片阶段。"
            "**U01-R18 的文档侧闭环成立，产物侧留一条（U01-R22）。**"
        )

    # A4 U01-R22 追加独立复现证据
    if "07:2x 企划合规独立复现" not in oi["U01-R22"]["resolution"]:
        oi["U01-R22"]["resolution"] = oi["U01-R22"]["resolution"].rstrip() + (
            "　**2026-10-23 07:2x 企划合规独立复现（与登记结论一致）**：实测 `preview/U01_tts/items.json` "
            "（120 条，dialogue 28 条）中 ep2 第 4 条 **仍是旧句**「「两小时五十八分……换我用了。」」、"
            "`dur` ＝ **2.953197**、`audio` ＝ `preview/U01_tts/audio/ep002_13.mp3`；"
            "**新句「换我用了。」在 items.json 中无任何条目** → 只读比对脚本按新文案匹配落 `no_audio`；"
            "实测报告 `summary` ＝ `vo_total 28／measured 27／no_audio 1／error_count 0／warn 2／ok 25／"
            "d16_out_mismatch_count 0／items_json_dur_mismatch_count 1`，**verdict ＝ WARN（非 PASS）**。"
            "**故本条的准确表述是「破坏项已清零、被测覆盖 27/28」，不是「全部通过」** —— "
            "这正是 Q50「文档链零不一致 ≠ 与实际产物一致」的同源形态：把一条**可测的破坏**换成了**不可测的缺测**。"
            "**追加风险**：旧音频 `ep002_13.mp3` 仍在盘上，若出片阶段误复用，音频止于 41.2+2.953＝**44.153s**，"
            "而字幕出点 43.0 → **字幕提前 1.153s**（正是 U01-R18 最初发现的那类破口，形态由「预算太小」"
            "变为「资产与文案不同步」）。**→ 建议在该 mp3 旁或 items.json 增「禁用/待重合成」标记（若尚未有）**，"
            "并在本条闭环判据中写明：**出片阶段按新台词重合成后复跑，受检须为 28 条且 ERR 0** 方可升格。"
        )

    # A5 OPS-16 裁定
    oi["OPS-16"]["status"] = "**已裁定**（企划合规 2026-10-23 07:25 · 裁决 S27）"
    oi["OPS-16"]["resolution"] = oi["OPS-16"]["resolution"].rstrip() + (
        "　**2026-10-23 07:25 企划合规裁定（最终，取代上方 06:5x 拟案）**："
        "**① 双向核对表不适用「单一 owner」** —— `shotintent_map_U02.mjs` 的两端分属两岗："
        "**锚点侧（D11 `visual_facts`）＝ 分镜导演**、**原文侧（D08 `shot_intent`）＝ 台本编剧**；"
        "强行归一方会让另一方按自己的理解改表，**锚点口径必然分叉**。"
        "**故裁定为「声明唯一 ＋ 两侧责任写明 ＋ 改动须同步」三合一**：文件头必须写明"
        "「锚点侧由分镜导演提供（D11 为被核对侧）、原文侧由台本编剧提供（D08）；"
        "**任何一方改动须同步另一方，并重跑覆盖轴（U01 23/23、U02 29/29，退出码须 0）**」——"
        "**两头都不许含糊**，但也**不许含糊成一个人**。**② 改动执行**：由本岗明派**实际写者（分镜导演）**"
        "执行改头（本岗不代改他岗脚本，§七·九）；改后**必须重跑覆盖轴**并把结果贴回本条。"
        "**③ 脚本改动同样适用版本守卫（Q64）与「覆盖轴须重跑」（Q49）**。"
        "**④ 本条是归属纪律问题，不是产物缺陷** —— 当前内容实测**无错**"
        "（抽验 `[9, 10, 3, [\"没看人脸\", \"指节在板背面敲了两下\"]]` 与 D11 `visual_facts` 一致，"
        "覆盖轴 U02 29/29、U01 23/23 零硬冲突）。**Apply**：双向核对表一律写「两侧责任＋同步义务」，"
        "不写单一 owner；归属声明与实际写者不一致时，**先改声明、后谈内容**。"
    )

    # A6 新增 U01-R33
    d18["open_issues"].append({
        "id": "U01-R33",
        "issue": "**Q56②「校验断言必须跨单元复制」在 U01 侧的落点未定 —— U01 的 D11／D16 无构建脚本载体，"
                 "判据散落在多个 patch／只读核对脚本里，无法直接加「清单＋机械守卫」** —— "
                 "实测（07:1x–07:2x）：`scripts/` 下 **无 `build_D11_U01.py`、无 `build_D16_U01.py`**；"
                 "U01 侧 D16 现为 **v1.10**，系 `patch_D16_dwell_convention.py`／`patch_D16_v17_badge_avoid.mjs`／"
                 "`patch_U01R18_*.mjs` 等**补丁链**产物；判据本体写在 "
                 "`reconcile_D15_D16_timing.mjs` 与 `reconcile_tts_actual_vs_d15_budget.mjs` 的注释里"
                 "（判据 A 越窗／B 跨切点／C 余量／D 同步，带口径标签与例外声明），但**两脚本均无 "
                 "`MANIFEST`／`ASSERT_` 机制** → **「判据已写清、但没有机械守卫」**。",
        "owner": "分镜导演（承接）＋ 企划合规（立判据与验收）",
        "blocks": "不拦 U01 单元锁（U01 已锁且已核验）；**拦「U01 侧判据可被无声改掉」**",
        "priority": "中",
        "status": "已明派（群内 @点名）·派单工具暂不可用·task_id 待补",
        "resolution": "**2026-10-23 07:25 企划合规裁定并明派（裁决 S23 追加子句）**："
                      "**① 承接方＝分镜导演**（D11／D16 交付物归属他；U02 侧同构样板已由他完成："
                      "`build_D16_U02.py` 30 条 ＋ `build_D11_U02.py` 35 条 ＋ 清单条数==实际断言点数守卫 ＋ 负测）。"
                      "**② 落点＝不新建构建脚本**（U01 侧不存在该载体，强行新建＝把 U02 的形态强加给 U01），"
                      "**改为在既有两个 reconcile 脚本内加「判据清单（编号＋判据＋来源）＋ 清单条数==实际断言点数守卫」**，"
                      "与 U02 侧同构；**③ 跨单元复制纪律**：从 U02 侧复制来的判据须逐条标注来源"
                      "（U02 侧已标，如「U01-R19 跨单元复制」——这正是 U01 那条关当初没被 U02 继承的原因），"
                      "**不得复制无来源条目**；**④ 负测**：删一条断言须立即中止（清单条数 ≠ 实际断言点数）"
                      "且**交付物字节未变**；**⑤ 验收权在本岗**：口径一致性抽查（U01 与 U02 同名判据口径须一致）"
                      "＋ 负测复跑。**⑥ 本岗不代改他岗脚本（§七·九），只立判据与验收。**",
        "detected_by": "分镜导演 2026-10-23 07:1x 提问（§七十一.4）＋ 企划合规 07:25 复核磁盘实况",
    })

    # A7 新增 Q70
    d18["global_checks"].append({
        "id": "Q70",
        "item": "**共享脚本的「归属声明」必须与「实际写者」一致；双向核对表不得含糊成单一 owner，"
                "须写明两侧责任＋改动同步义务** —— 本轮实证：`scripts/shotintent_map_U02.mjs` 文件头声明"
                "「映射由台本编剧维护」，但 06:18 被分镜导演改动（3,381 B → 5,236 B）→ **声明失效即形成事实上的第二个写者**。"
                "**根因不是「谁该改」，而是「谁声明的 owner 与谁实际在改」两件事脱节**。"
                "**做法**：① **声明唯一** —— 文件头必须写清维护方；② **双向核对表写两侧** —— "
                "锚点侧与原文侧分属两岗时，**写成「A 侧提供锚点、B 侧提供原文；任一方改动须同步另一方」**，"
                "**不许含糊成一个人**（否则另一方按自己的理解改表，锚点口径必然分叉）；"
                "③ **改动须重跑覆盖轴**（受检条数须 >0、退出码须 0 —— Q49）；"
                "④ **脚本改动同样适用版本守卫**（Q64）；⑤ **先改声明、后谈内容** —— 归属纪律问题与产物缺陷分开记，"
                "**不得把「归属未定」当成「内容有错」**（本例内容实测无错）。"
                "**Apply**：任何跨岗共用的脚本、映射表、判据表、清单文件。",
        "method": "比对文件头声明的 owner 与该文件的实际改动者（mtime／内容差异），并抽验产物本身是否真有错",
        "source": "企划合规 2026-10-23 07:25（OPS-16 裁定）",
        "severity": "中（不产生错交付物，但会让归属声明失效、埋下锚点口径分叉与第二个写者）",
    })
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    s23 = prj["decisions"].get("S23_U01侧断言清单化归属裁定与D16U02审计口径待派", "")
    if not s23:
        sys.exit("[ABORT] project.json decisions 无 S23；不写盘。")
    if "2026-10-23 07:25 企划合规追加子句" not in s23:
        prj["decisions"]["S23_U01侧断言清单化归属裁定与D16U02审计口径待派"] = s23.rstrip() + (
            "　**2026-10-23 07:25 企划合规追加子句（不改动上方原文，仅补「落点」并结清「待派」）**："
            "**① 落点＝不新建构建脚本** —— U01 侧不存在 `build_D11_U01.py`／`build_D16_U01.py` 载体"
            "（实测不存在），强行新建等于把 U02 的形态强加给 U01；**改为在既有两个 reconcile 脚本内加"
            "「判据清单（编号＋判据＋来源）＋ 清单条数==实际断言点数守卫」**，与 U02 侧同构。"
            "**② 承接方＝分镜导演**（U02 侧样板已由他完成并做过负测），**验收权在本岗**（口径一致性抽查＋负测复跑）。"
            "**③ 跨单元复制纪律**：复制来的判据**须逐条标注来源**，不得复制无来源条目。"
            "**④ 派单登记＝U01-R33**（明派通道：群内 @点名；派单工具此刻仍不可用，task_id 待补）。"
            "**「待派」由此结清。**"
        )
    prj["decisions"]["S26_面板口径裁定_读数栏留画面面板本体进字幕层"] = (
        "企划合规裁定（2026-10-23 07:25，分镜导演 07:1x 请求复核「面板口径收口」）："
        "**① 分类判据（唯一口径）** —— **读数栏数值（面板/视野一角的百分比、计数等数值读数）留画面、不进字幕层**；"
        "**面板本体弹出的提示/通报文字进字幕层**。"
        "**② 依据** —— 读数栏数值是**画面内 UI 元素**（D11 原文即「视野一角读数栏／面板读数栏显示同屏中文…」），"
        "其可读性由 D12 逐镜包的 image_prompt 承担；把数值再抄进字幕层会**与画面内读数重复**，"
        "且挤占底部字幕带（该带与片尾标题卡同处 → 越界即真实视觉冲突）。"
        "**③ 落盘形态** —— D16 `subtitle_style.readout_in_frame` 逐集登记「不进字幕层的读数」"
        "（**须带 D11 原文 basis**），供 D12 逐镜包与下游核对；"
        "**④ 强制检查** —— 面板字幕行**必须单独检查**是否越片尾标题卡带"
        "（本轮实证：ep10 seq9「归一度 1.0%」42.5~43.9、ep15 seq10「归一度 1.3%」42.3~43.7 "
        "两条都伸进 43.0~45.0 的片尾带 → 分镜导演自查发现并改正，改正后片尾带冲突 0 条、同镜重叠 0 条）。"
        "**⑤ 跨单元一致性** —— U01 ep4 镜4「归一度 0.5%」同样不进字幕层，**两侧口径已统一**。"
        "**⑥ 验收判据** —— D16 侧「含『归一度』的字幕行数 ＝ 0」且「`readout_in_frame` 登记集覆盖全部读数集」；"
        "D12 侧「对应镜位 image_prompt 必须含该读数」（本轮实测 U02 D12 v1.0 的 8 张卡 **全部含**）。"
        "**Apply when**：任何「画面里已有可读文字/数值，字幕层要不要再抄一遍」的决策。"
    )
    prj["decisions"]["S27_共享脚本归属口径与双向核对表两侧责任"] = (
        "企划合规裁决（2026-10-23 07:25，OPS-16 结清 · 配套 **Q70**）："
        "**① 声明唯一** —— 共享脚本文件头必须写清维护方；**声明与实际写者不一致即视为归属失效**"
        "（本轮实证：`shotintent_map_U02.mjs` 声明台本编剧维护，06:18 实际由分镜导演改动）。"
        "**② 双向核对表不写单一 owner** —— 锚点侧与原文侧分属两岗时，写成"
        "「**A 侧提供锚点、B 侧提供原文；任一方改动须同步另一方，并重跑覆盖轴（受检条数须 >0、退出码须 0）**」，"
        "**两头都不许含糊，更不许含糊成一个人**（否则另一方按自己的理解改表 → 锚点口径分叉）。"
        "**③ 改动执行归属** —— 由**实际写者**改声明（本岗不代改他岗脚本，§七·九），改后重跑覆盖轴并贴回台账。"
        "**④ 改动即触发两条守卫** —— 版本守卫（**Q64**）＋ 覆盖轴须重跑（**Q49**）。"
        "**⑤ 归属问题与产物缺陷分列** —— 声明失效时**不得**顺带判「内容有错」"
        "（本例内容实测无错：抽验锚点与 D11 `visual_facts` 一致，U01 23/23、U02 29/29 零硬冲突）。"
        "**Apply when**：任何跨岗共用的脚本、映射表、判据表、清单文件。"
    )
    prj["updated_at"] = NOW
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引 ----------
    # C1 §五「下一责任人」企划合规行的 D18 版本提法
    pat_a = r"D18 \*\*v1\.\d+\*\*（\*\*\d+\*\* 条 global_checks / \*\*\d+\*\* 条 open_issues"
    if len(re.findall(pat_a, idx)) != 1:
        sys.exit("[ABORT] 索引 §五 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_a,
                 f"D18 **{d18['version']}**（**{len(d18['global_checks'])}** 条 global_checks / "
                 f"**{len(d18['open_issues'])}** 条 open_issues",
                 idx, count=1)
    # C2 §六 交付物状态表 D18 行**头部**的 global_checks 计数 —— 锚在版本提法之后，
    #    避开该行中段历史留痕里的旧计数（如「77 条 open_issues」），留痕不改写
    #    ⚠️ 必须先于 C3 执行：C3 会把版本提法换成占位符「«RUN_HM»」，锚点随之失效
    pat_c = (r"(\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*（字节数不钉，见 D18 \*\*Q34\*\*）。)"
             r"\*\*\d+ 条 global_checks\*\*")
    if len(re.findall(pat_c, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 计数锚点命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_c,
                 lambda m: m.group(1) + f"**{len(d18['global_checks'])} 条 global_checks**",
                 idx, count=1)
    # C3 §六 D18 行的版本提法（落款时间留占位符，写盘后按 D18.json 磁盘 mtime 回填）
    pat_b = r"\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*"
    if len(re.findall(pat_b, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_b, f"**{d18['version']}｜«RUN_HM» 落｜approved**", idx, count=1)
    i_heads = [l for l in idx.split("\n") if l.startswith("### 十·")]
    i_nums = []
    for h in i_heads:
        mm = re.match(r"### 十·([零一二三四五六七八九十百]+)", h)
        if mm:
            try:
                i_nums.append(cn_to_int(mm.group(1)))
            except KeyError:
                pass
    idx_new = int_to_cn(max(i_nums) + 1)
    if f"### 十·{idx_new}" in idx:
        sys.exit(f"[ABORT] 索引已含 §十·{idx_new}；不写盘。")
    idx = idx.rstrip("\n") + "\n" + f"""
### 十·{idx_new} 分镜导演 07:1x 交付通报核销 ＋ 三项裁定（面板口径／Q56② U01 侧落点／共享脚本归属）· D18 {d18['version']}（**企划合规 2026-10-23 07:20–07:25**）

#### 1. 核销（**一律以磁盘实况为准**）

| 项 | 通报口径 | 磁盘实况 | 处置 |
|---|---|---|---|
| U02 D11／D16 | v1.3／v1.3 | **v1.6／v1.4** | 以磁盘为准，已回执 |
| 第六波三项核销 | 请回执 | D11 note 引文、面板口径、Q56 守卫均已在盘 | **回执确认**（详见 §二） |
| U02-R09 | — | U02 D11 **v1.6** ep014 镜3 逐字「成本条目停在最后一栏，最后一栏数字没有合上」 | **复核通过→闭环** |
| U01-R20 | — | U01 D12 **v1.5** ep5 镜3 ＝ `no burning, no smoke` ＋ 保留 `frost-layer cold white mist preserved`，`no smoke from humans` 已除 | **闭环** |
| U01-R18 | — | D15 **v1.6** 9/9、D16 **v1.10** 9/9、ep2 seq9 文字＋out 43.0、sync_rule 已写左闭右开 | **文档侧闭环**（产物侧留 U01-R22） |

#### 2. 三项裁定

① **面板口径收口（分镜导演请求复核）—— 裁「读数栏留画面、面板本体进字幕层」（S26）**：
实测 D16 U02 **含「归一度」的字幕行数 ＝ 0**、8 集 `readout_in_frame` 均登记并带 D11 原文 basis；
U02 D12 **8 张卡 image_prompt 全部含该读数** → **分镜导演请求③（视觉设定）已闭环**。**无异议。**
② **Q56② U01 侧判据清单化落点（S23 追加子句）—— 落点＝不新建构建脚本**：
U01 侧**无** `build_D11_U01.py`／`build_D16_U01.py`（实测不存在）→ 改为**在既有
`reconcile_D15_D16_timing.mjs` 与 `reconcile_tts_actual_vs_d15_budget.mjs` 内加判据清单＋机械守卫**，
与 U02 侧同构；**承接方＝分镜导演**，**验收权在本岗**；复制来的判据**须逐条标来源**。派单登记 **U01-R33**。
③ **共享脚本归属口径（OPS-16 结清 · S27 ＋ Q70）**：**双向核对表不写单一 owner** ——
`shotintent_map_U02.mjs` 的**锚点侧（D11）＝分镜导演、原文侧（D08）＝台本编剧**，
写成「任一方改动须同步另一方并重跑覆盖轴」；**声明唯一、两头都不许含糊**；由实际写者改头。

#### 3. 重要口径提醒（不可误读为「全绿」）

只读比对报告 **verdict ＝ WARN**、**error_count 0**、**measured 27／vo_total 28／no_audio 1** →
**「ERR 0」＝ 破坏项清零，不等于 28 条全过**；ep2#4 因旧音频未重合成而**未被实测**
（盘上 `ep002_13.mp3` 仍是旧句 2.953s，止于 44.153s，若误复用则字幕提前 1.153s）→ 已转 **U01-R22** 归出片阶段。

#### 4. 出口闸与边界

`--unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **11/11、error 0、warning 8**；
无 `--unit` → **error 0／warning 11／22-22／exit 0**（**修前 error 128／exit 1** —— 分镜导演各节所记
「待企划合规裁定」为**修复前状态**，本岗 04:40 已修，见 OPS-13／Q52／S17）。
**G-05 预算档位属用户/Chief 裁决事项，本岗无权裁，转呈。**
本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）；
**未改**任何交付物 JSON、源素材、规格文件、工具脚本；未生成图片／视频／音频，未合成 TTS，
未提交 H3 付费生成，未投流上架。
"""

    # ---------- D. 交付说明 ----------
    d_heads = [l for l in deliv.split("\n") if l.startswith("## ")]
    d_nums = []
    for h in d_heads:
        mm = re.match(r"## ([零一二三四五六七八九十百]+)、", h)
        if mm:
            try:
                d_nums.append(cn_to_int(mm.group(1)))
            except KeyError:
                pass
    new_cn = int_to_cn(max(d_nums) + 1)
    if f"## {new_cn}、" in deliv:
        sys.exit(f"[ABORT] 交付说明已含 §{new_cn}；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + f"""
## {new_cn}、分镜导演 07:1x 交付通报核销 ＋ 三项裁定 ＋ U01-R33 ＋ Q70 · S26／S27（**企划合规 2026-10-23 07:20–07:25**）

### {new_cn}.1 回执第六波派单（task_aaa95d268ca7）三项

① **U02-R03 连带项**（D11 note 引文「敲板面的两下」→「敲板背的两下」）—— 磁盘 U02 D11 现 **v1.6**，引文已对齐，**回执确认**；
② **D16 v1.1→v1.3 三跳** —— 磁盘 U02 D16 现 **v1.4**（U02-R29 已落），**以磁盘为准**；
③ **Q56 断言清单＋机械守卫落地** —— U02 侧 30／35 条已在盘，**回执确认**。

### {new_cn}.2 三项裁定

① **面板口径（S26）**：**读数栏数值留画面、不进字幕层；面板本体提示/通报文字进字幕层**。
实测 D16 U02 含「归一度」字幕行 **0**、8 集 `readout_in_frame` 带 basis；U02 D12 八张卡 image_prompt **全部含读数**
→ 分镜导演请求③（视觉设定）**已闭环，无异议**。
② **Q56② U01 侧落点（S23 追加）**：**不新建构建脚本**（U01 侧无此载体），改为在两个 reconcile 脚本内加
**判据清单＋清单条数==实际断言点数守卫**；**承接方＝分镜导演**，验收权在本岗；**派单＝U01-R33**。
③ **共享脚本归属（OPS-16 结清 · S27／Q70）**：**双向核对表不写单一 owner** —— 锚点侧（D11）＝分镜导演、
原文侧（D08）＝台本编剧；**任一方改动须同步另一方并重跑覆盖轴**；声明唯一、两头都不许含糊；由实际写者改头。

### {new_cn}.3 口径提醒：ERR 0 ≠ 28 条全过

比对报告 **verdict WARN／error 0／measured 27／vo_total 28／no_audio 1** → 破坏项已清零，
但 **ep2#4 未被实测**（旧音频 `ep002_13.mp3` 仍是旧句 2.953s，止于 44.153s；误复用则字幕提前 1.153s）→ 归 **U01-R22** 出片阶段。

### {new_cn}.4 出口闸与边界

`--unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **11/11、error 0、warning 8**；
无 `--unit` → **error 0／warning 11／22-22／exit 0**（修前 error 128／exit 1，本岗 04:40 已修）。
**G-05 预算档位属用户/Chief 裁决事项，本岗转呈。**
本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）；
**未改**任何交付物 JSON、源素材、规格文件、工具脚本；未生成图片／视频／音频，未合成 TTS，
未提交 H3 付费生成，未投流上架。
"""

    # ---------- E. 自检 ----------
    for k in ("U01-R33", "Q70"):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    for k in ("S26_面板口径裁定_读数栏留画面面板本体进字幕层", "S27_共享脚本归属口径与双向核对表两侧责任"):
        if k not in prj_out:
            sys.exit(f"[ABORT] project.json 序列化后丢失「{k}」；不写盘。")
    if idx.count(f"### 十·{idx_new}") != 1:
        sys.exit(f"[ABORT] 索引 §十·{idx_new} 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")

    # ---------- F. 并发写盘竞态守卫（compare-and-swap） ----------
    # 并行企划合规实例可能在本脚本运行期间改写 D18.json / project.json；
    # 若直接写回会覆盖他人本轮改动 ⇒ 写前重读比对字节，不一致即中止不写盘。
    for path, raw0, label in ((p18, d18_raw, "shared/D18.json"), (p_prj, prj_raw, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；"
                     f"不写盘，重新核实现盘后再执行。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 {ver}→{d18['version']}（U02-R09 核销 ＋ U01-R20 核销 ＋ U01-R18 追加 ＋ U01-R22 追加 ＋ "
              f"OPS-16 裁定 ＋ U01-R33 新增 ＋ Q70 新增）；project.json（S23 追加 ＋ S26 ＋ S27）；"
              f"索引 §五 ＋ §六 版本提法 ＋ §十·{idx_new}；交付说明 §{new_cn}")
        return

    # 写盘前留档（四份原件）
    bak = os.path.join(proj, "reports", "_bak_0725_patch_round3")
    os.makedirs(bak, exist_ok=True)
    for path, name in ((p18, "D18.json"), (p_prj, "project.json"),
                       (p_idx, "00_项目索引.md"), (p_del, "99_交付说明.md")):
        with open(os.path.join(bak, name), "wb") as f:
            f.write(open(path, "rb").read())

    write(p18, d18_out)
    write(p_prj, prj_out)
    # 落款时间以 D18.json 磁盘 mtime 为准（Q48：自报落款不得当落盘事实）
    run_hm = datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M")
    idx = idx.replace("«RUN_HM»", run_hm)
    deliv = deliv.replace("«RUN_HM»", run_hm)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 本轮核销与裁定完成")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：S23 追加子句 ＋ S26 ＋ S27；updated_at → {NOW}")
    print(f"   00_项目索引.md：§二 版本提法 ＋ §十·{idx_new}")
    print(f"   99_交付说明.md：新增 §{new_cn}")


if __name__ == "__main__":
    main()
