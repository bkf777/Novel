#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台账回刷 + 章程条款订正（企划合规单点维护，2026-10-23 04:1x）。

起因
----
本轮五份回执（声音设计 D15 v1.3／分镜导演 D16 v1.7＋取景脚本／台本编剧 U02 D08 v1.1＋D09／
白模场景师 U02-R01 ①②③ ＋ g24/g27／视觉设定 D10 v1.9＋U02-R01 ③／故事架构 U02 D06/D07 v1.1）
已由并行实例登记到 **D18 v1.40**（含 Q47 版本戳持有权、S13 三镜不解冻、U02-R01~R06）。
本岗逐项回盘后补办**六处真实缺口**：

  ① **D10 v1.9 未登记**（磁盘 31,091 B / 04:03）—— `consistency_rules` 16→17「净火照射范围」＋
     `negatives` 45→46；U01 零返修。
  ② **D16 v1.7 未登记**（磁盘 112,588 B / 04:04）—— U01-R15 落地，`badge_avoid` 改可计算口径；
     时码零变化（cuts 26 / 计入 D17 仍 20）。
  ③ **U02 D06/D07 仍记 v1.0**（磁盘 v1.1 / 11,326 / 28,443）—— ep014 正文与在场名单冲突已修，
     附新增可复跑脚本 `check_D06_D07_roster_consistency.py`。
  ④ **U02 D08/D09 行 size 为 null**（磁盘 D08 **v1.1** / 33,892 B、D09 v1.0 / 17,246 B）。
  ⑤ **g24/g27 提示级发现未登记**（白模场景师请登记）→ 新增 open_issue **U02-R07**。
  ⑥ **章程 §七·九 v2.2 与现役工具链冲突** —— 条款仍写旧链
     `04_工具/handoff/make_plan.py → batch_build.py → finalize_d14.py`（`make_plan.py` 已按 S12 退役）
     且写「白模场景师不直接落盘、不直接改 `04_工具/handoff/**` 共享脚本」，与 S12 明派白模场景师改
     README／参数化脚本、以及现役链全在 `02_项目/双相潮主/scripts/` 的事实**直接矛盾**。
     章程是全团队 SSOT，两处矛盾必须收口 → **本岗订正条款措辞（保留实质：同一时刻单写者、
     取消≠turn 停止、重跑前清目录、并发即回报），只更新链名与职责归属表述**，
     并登记 **S14** ＋ D18 open issue 留痕。

另：本岗在台账上发现**回报与磁盘两处出入**，一律以磁盘为准：
  · 台本编剧报「D08 v1.0」→ 磁盘实为 **v1.1**（返修 U02-R03 已落）；
  · 索引 §六 U02 D08 行记 **33,817 B** → 磁盘实为 **33,892 B**。

用法
----
python3 scripts/patch_ledger_0410_refresh.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 04:12"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
    if "十" in s:
        head, tail = s.split("十", 1)
        return (CN[head] if head else 1) * 10 + (CN[tail] if tail else 0)
    return CN[s]


def int_to_cn(n):
    if n < 10:
        return "零一二三四五六七八九"[n]
    head, tail = divmod(n, 10)
    return ("零一二三四五六七八九"[head] if head > 1 else "") + "十" + \
           ("零一二三四五六七八九"[tail] if tail else "")


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


def rep(text, old, new, where, skipped, must=True):
    """定点替换：旧串命中 1 次 → 替换；新串已在 → 跳过（并行实例已做）；否则中止。"""
    if old in text:
        n = text.count(old)
        if n != 1:
            sys.exit(f"[ABORT] {where} 旧串命中 {n} 次（期望 1）：{old[:70]}…；不写盘。")
        return text.replace(old, new)
    if new in text:
        skipped.append(where)
        return text
    if must:
        sys.exit(f"[ABORT] {where} 旧串与新串均未命中（落盘态与预期不符）：{old[:70]}…；不写盘。")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # 脚本位于 <工厂根>/02_项目/双相潮主/scripts/ → 向上四层到 <工厂根>
    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)
    charter = os.path.join(factory, "00_团队章程.md")
    if not os.path.isfile(charter):
        sys.exit(f"[ABORT] 章程未找到：{charter}；不写盘。")

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
    char = read(charter)

    skipped = []

    # ---------- 磁盘实况（一切数字以磁盘为准，不采信回报） ----------
    def disk(rel):
        p = os.path.join(proj, rel)
        d = json.loads(read(p))
        return d, os.path.getsize(p)

    d10, d10_sz = disk("shared/D10.json")
    d15, d15_sz = disk("units/U01/D15.json")
    d16, d16_sz = disk("units/U01/D16.json")
    u06, u06_sz = disk("units/U02/D06.json")
    u07, u07_sz = disk("units/U02/D07.json")
    u08, u08_sz = disk("units/U02/D08.json")
    u09, u09_sz = disk("units/U02/D09.json")

    # ================= A. D18 =================
    if d18.get("version") != "v1.40":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.40；不写盘。")
    if serialize_like(json.loads(d18_raw), d18_raw) != d18_raw:
        sys.exit("[ABORT] D18.json 序列化格式不一致；不写盘。")

    oi_ids = [o.get("id") for o in d18["open_issues"]]
    if "U02-R07" in oi_ids:
        sys.exit("[ABORT] open_issues 已含 U02-R07，不重复登记；不写盘。")
    gc_ids = [g["id"] for g in d18["global_checks"]]
    if gc_ids[-1] != "Q49":
        sys.exit(f"[ABORT] global_checks 末条为 {gc_ids[-1]}，期望 Q49；不写盘。")

    u01 = [x for x in d18["unit_checks"] if x.get("unit") == "U01"][0]
    u02 = [x for x in d18["unit_checks"] if x.get("unit") == "U02"][0]

    def row(unit, doc):
        hits = [r for r in unit["delivery_checks"] if r.get("doc") == doc]
        if len(hits) != 1:
            sys.exit(f"[ABORT] delivery_checks 中 {doc} 命中 {len(hits)} 行，期望 1；不写盘。")
        return hits[0]

    r10, r15, r16 = row(u01, "D10"), row(u01, "D15"), row(u01, "D16")
    if r10.get("version") != "v1.8" or r16.get("version") != "v1.6":
        sys.exit(f"[ABORT] D10/D16 行版本为 {r10.get('version')}/{r16.get('version')}，期望 v1.8/v1.6；不写盘。")
    if r15.get("version") != "v1.3":
        sys.exit(f"[ABORT] D15 行版本为 {r15.get('version')}，期望 v1.3；不写盘。")

    # ① D10 v1.9
    r10["state"] = r10["state"].rstrip() + (
        f" → **v1.9（2026-10-23 04:03，视觉设定）：`consistency_rules` 16 → 17 追加「净火照射范围」共享层条款"
        f"＋ `negatives` 45 → 46 追加 `net fire illuminating more than a small contact patch of skin`** —— "
        f"U02 的 D12 要落「净火只照亮接触处一小片皮肤」，而原 D10 [12]「不形成持续暖主光」只限定电焊火花、"
        f"[13] 是色板收敛条，**都不涉及净火的空间照射范围** → D12 落该口径在共享层无据可依、必然分裂。"
        f"**这是把既有实践收口成条款、不是新增约束**：U01「净火作用于人」唯一处（ep007 镜2，D11/D12 均写"
        f"「黑白双焰贴上皮肤表面」）本就符合；palette/lighting/motifs/character_anchors 全部未动 → "
        f"**U01 D12 零返修、V7 不受影响**；`patch_D10_v19_netfire_scope.py` 带命中数断言、幂等。"
        f"实测磁盘：v{d10['version'][1:]}｜rules {len(d10.get('consistency_rules', []))} 条｜"
        f"negatives {len(d10.get('negatives', []))} 条｜{d10_sz:,} B"
    )
    r10["version"] = f"v{d10['version'][1:]}"
    r10["size"] = f"{d10_sz:,} B"

    # ② D16 v1.7
    cuts_total = sum(len(e.get("cuts", [])) for e in d16.get("episodes", []))
    cuts_cnt = sum(1 for e in d16.get("episodes", []) for c in e.get("cuts", [])
                   if c.get("counted_in_d17_cut_count"))
    r16["state"] = r16["state"].rstrip() + (
        f" → **v1.7（2026-10-23 04:04，分镜导演）：U01-R15 落地** —— `subtitle_style.badge_avoid` 的粗口径描述"
        f"改为**可计算口径**（对白字幕区＝字幕文字顶以下；基线距底 ≥15% 画面高 → 基线自顶 85%；字号 65~76px → "
        f"文字顶约 81%~81.6% 自顶；AI 角标带＝72%~78% 自顶；两区间须留 ≥2% 画面高间距，U01 实测 3.0%~3.6%）。"
        f"**时码零变化**：cuts 仍 **{cuts_total} 条**、计入 D17 仍 **{cuts_cnt} 条**（U01-R13 口径不变、"
        f"无新增破口）✅；实测磁盘 v{d16['version'][1:]}｜{d16_sz:,} B"
    )
    r16["version"] = f"v{d16['version'][1:]}"
    r16["size"] = f"{d16_sz:,} B"

    # ③ D15 v1.3 补「与 v1.1 时长数据逐字节一致」（声音设计明请）
    r15["state"] = r15["state"].rstrip() + (
        f" → **v1.3（2026-10-23 03:18，声音设计）**：撤除 D15 内的 D16 版本指针（双份版本指针必然互相追赶分叉），"
        f"改为指向 D16 `subtitle_sync_audit` 审计块；闭合戳**版本无关化**（「自 v1.1 收敛起，历版只改口径文本，"
        f"四组时长数据与 v1.1 逐字节一致」）→ 不随升版腐烂。**实测 `dur_sec` 分布与 v1.1／v1.2 逐字节一致** → "
        f"**Q40 三分法不变（收敛 11 条／落盘态 12 条）** ✅"
    )
    r15["size"] = f"{d15_sz:,} B"

    # ④ U02 四行
    r6, r7 = row(u02, "D06"), row(u02, "D07")
    r6["state"] = (
        f"已交付并审读通过（03:03:34 首落 v1.0 → **04:08 升 v1.1**：ep014 `must_happen[4]`"
        f"「叶崇岳摊开城防图，**与叶承钧一起确认暗杀组名单**」与本集在场名单 `[LC, YD-GC, YJ-JZ]`（**无 YJ-ES**）"
        f"自相矛盾 → 改为「**叶崇岳在会议桌另一头摊开城防图，笔尖点在机械厂的名字上，旁边按着继承人的印**」，"
        f"**与 D08 已落盘画面逐字对齐、hook_out 一字未动**、其余 8 集正文/钩子/伏笔/场景码/段界零改动。"
        f"**V1–V11 集体盲区**：无一条规则校「正文提及的角色是否在该集在场名单里」（V2 只校角色 id 存在于 D04"
        f"＋ D08 ⊆ D07）—— 雷被下游用「按着继承人的印」躲过去了，若不修则 D11 拍出叶承钧＝剧本 vs 分镜分裂。"
        f"新增可复跑脚本 `scripts/check_D06_D07_roster_consistency.py`（**故事架构名下维护；判据变更须同步改"
        f"脚本头部与 D18**；三域判据 ＋ 反向回归证明非恒真 ＋ 空集恒真守卫；是筛子不是判决书，别名/称号抓不到）。"
        f"｜v{u06['version'][1:]}｜{u06_sz:,} B"
    )
    r6["version"] = f"v{u06['version'][1:]}"
    r6["size"] = f"{u06_sz:,} B"
    r7["state"] = (
        f"已交付并审读通过（03:03:34 首落 v1.0 → **04:08 升 v1.1**：同步 ep014 `must_happen[4]` 一条，"
        f"其余 8 集正文/钩子/段界/伏笔/场景码零改动；8 集 × 四段制段界连续无缝、各 45s、代价 8/8 具体、"
        f"场景码 **B-1…B-10** 与 U01 的 A 码不撞、**全单元 8 集「串行」不设并行段**（D17 切点预算零余量 ＋ "
        f"无叙事需求）｜v{u07['version'][1:]}｜{u07_sz:,} B"
    )
    r7["version"] = f"v{u07['version'][1:]}"
    r7["size"] = f"{u07_sz:,} B"
    r8, r9 = row(u02, "D08"), row(u02, "D09")
    r8["state"] = (
        f"已交付并审读通过（03:34 落盘 v1.0 → **v1.1**：ep009 body[10] 的 `shot_intent`「敲板面」与正文「背面」"
        f"不一致 → 返修订正（**U02-R03**，改生成脚本 `d08_content_U02.py` 后重跑，未手改 JSON）；"
        f"**`shot_intent` 共 29 条**；base 193~216 全在 [180,240]、total 229~255 全 ≤330；"
        f"生成脚本已按 `--unit` 参数化、内容层下沉 `d08_content_U02.py`（**未复制副本**）；"
        f"**`shotintent_map_U02.mjs` 待 D11 落盘后建**（U02-R06：届时受检条数应 >0，仍报 0 条按 Q49 视为未检）"
        f"｜v{u08['version'][1:]}｜{u08_sz:,} B"
    )
    r8["version"] = f"v{u08['version'][1:]}"
    r8["size"] = f"{u08_sz:,} B"
    r9["state"] = (
        f"已交付并审读通过（03:34 落盘｜**顶层式** `{{doc_id,…}}` 非 episodes 嵌套｜`lines` **28 句**逐句有 "
        f"`subtext`、`voice_cards` **6 张**（LC8/YHY6/SQC9/YD-GC2/YJ-ES2/YJ-JZ1）；D04 口头禅尾句号不一致已按"
        f"D04 原文逐字登记、校验改严格相等；生成脚本 `build_D09.py` 已参数化、内容层 `d09_content_U02.py`"
        f"｜v{u09['version'][1:]}｜{u09_sz:,} B"
    )
    r9["version"] = f"v{u09['version'][1:]}"
    r9["size"] = f"{u09_sz:,} B"

    # ⑤ g24/g27 提示级发现 → U02-R07
    d18["open_issues"].append({
        "id": "U02-R07",
        "issue": "**U02 的 D13 机位复核前置：两镜的角色到机位距离 < 0.35m；并暴露 U01 锁定件 g27 的 `preview_video.mp4` "
                 "整帧灰板** —— 白模场景师 2026-10-23 03:4x 在工具链参数化回归中报出：新链按 POV 避让规则 "
                 "`clear_keys_from_camera` 把角色推到距机位 **0.35m**（`need` 值）；实测首采样与机位距离 "
                 "**g27 锁定 0.00000 → 新 0.35000、g24 锁定 0.28284 → 新 0.35000** —— **g24/g27 差异非本次改动所致**"
                 "（锁定白模建于 00:57–01:04，早于该规则与当前 D13 机位；D13 A-8/27 机位注原文「机位与角色眼位重合」）。"
                 "**据此暴露锁定件一处真实画面缺陷：g27 的 `preview_video.mp4` 整帧是一块灰板**（机位落在角色体块内部，"
                 "正是该函数注释所防的失效），新链同镜已渲出可读几何；两版 g27 实体清单一致（均无角色实体，"
                 "POV 镜本就看不到自身躯体）→ **不改变交接包实体面**。",
        "owner": "白模场景师（出判定）＋ 分镜导演（D11 机位与 visual_facts）＋ 企划合规（U02 开工前复核）",
        "blocks": "**不拦 U01 单元锁**（U01 已锁、已全量核验；g27 灰板属既有锁定件，不回改）；"
                  "**U02 的 D13 开工前须复核** —— 每个镜位实测「角色到机位距离」",
        "priority": "中",
        "status": "已登记·待复核",
        "resolution": "2026-10-23 04:12 企划合规登记（**只登记不代改**）：① **列入 U02 的 D13 机位复核清单** —— "
                      "U02 每个镜位须实测「角色到机位距离」，**< 0.35m 的镜位必须在 D13 层改机位或改角色站位**，"
                      "不得留到白模渲出来才发现；② **g27 灰板属 U01 锁定件，不回改**（实体面未变、回改代价高于收益）；"
                      "③ 该发现属 **V1–V11 集体盲区**（校验器零覆盖白模取景/机位距离轴），已由分镜导演 "
                      "`scripts/check_D11_framing_safe_area.py` 与故事架构 "
                      "`scripts/check_D06_D07_roster_consistency.py` 两条可复跑脚本补位 —— "
                      "**U02 起机位轴须纳入脚本化核验**。",
        "detected_by": "白模场景师 2026-10-23 03:4x（工具链参数化回归时）",
    })

    # ⑥ 章程条款与现役链冲突 → 登记 open issue（U02-R08）
    if "U02-R08" in oi_ids:
        sys.exit("[ABORT] open_issues 已含 U02-R08，不重复登记；不写盘。")
    d18["open_issues"].append({
        "id": "U02-R08",
        "issue": "**章程 §七·九 v2.2「单写者纪律」的 D13/D14 落盘链与职责表述，与现役事实直接矛盾** —— "
                 "条款仍写旧链 `04_工具/handoff/make_plan.py → batch_build.py → finalize_d14.py`"
                 "（**`make_plan.py` 已按 S12 退役**、现役链全在 `02_项目/双相潮主/scripts/`），"
                 "且写「白模场景师只出技术判定与问题清单回报总控，**不直接落盘、不直接改 `04_工具/handoff/**` 共享脚本**」"
                 "—— 与 **S12 已明派白模场景师改 README 与参数化脚本**、以及 D13/D14 现役由白模场景师落盘的"
                 "事实冲突。**章程是全团队 SSOT，两处矛盾必须收口**，否则下一位执行人会按旧链重跑。",
        "owner": "企划合规（条款订正已执行）＋ Chief（公示与备案）",
        "blocks": "**不拦任何单元锁**；**U02 的 D13/D14 开工前必须已收口**（否则下一位按旧链跑）",
        "priority": "中",
        "status": "已登记·条款已订正·待 Chief 备案",
        "resolution": "2026-10-23 04:12 企划合规**已执行条款订正**（登记 **S14_章程单写者条款与现役工具链对齐**）："
                      "① 链名更新为现役新链 `build_D13.py → build_white_model.py → d14_pipeline.py preflight/check/prompt "
                      "→ fill_D14_contracts.py → assemble_D14.py → validate.mjs --unit`（全在 `scripts/`，一律 `--unit` "
                      "参数化）；旧链标注**已退役、不是生产路径**；② **实质不变**：同一时刻 D13/D14 只允许一个写者、"
                      "取消≠turn 停止、重跑前清空目标目录、并发写入立即回报；③ 落盘执行岗与共享工具脚本的改动"
                      "**一律由总控明派**，明派须在 D18 登记后方生效（**未登记的明派视为未明派**）—— "
                      "S12 即为已登记的明派样板。**边界**：本岗只改事实性链名与职责归属表述，未改动纪律的实质约束；"
                      "条款订正已在 D18 与 `project.json` decisions.S14 留痕，待 Chief 备案。",
        "detected_by": "白模场景师 2026-10-23 03:4x（§44 交接项②）",
    })

    d18["version"] = "v1.41"
    u02["updated_at"] = NOW
    d18_out = serialize_like(d18, d18_raw)

    # ================= B. project.json：S14 =================
    if "S14_章程单写者条款与现役工具链对齐" in prj["decisions"]:
        sys.exit("[ABORT] project.json decisions 已含 S14，不重复登记；不写盘。")
    prj["decisions"]["S14_章程单写者条款与现役工具链对齐"] = (
        "企划合规裁决（2026-10-23 04:12，白模场景师 §44 交接项② 请裁章程旧链引用）："
        "**订正 `00_团队章程.md` §七·九 v2.2 的链名与职责表述，纪律实质一字不动**。理由："
        "① **条款的事实性链名已过期** —— 旧链 `04_工具/handoff/{make_plan.py, batch_build.py, finalize_d14.py}` "
        "中 `make_plan.py` 已按 S12 退役，现役新链全部落在 `02_项目/双相潮主/scripts/`（"
        "`build_D13.py` → `build_white_model.py` → `d14_pipeline.py preflight/check/prompt` → "
        "`fill_D14_contracts.py` → `assemble_D14.py` → `validate.mjs --unit`）；"
        "② **职责表述与已执行事实矛盾** —— 条款写「白模场景师不直接落盘、不直接改 `04_工具/handoff/**` 共享脚本」，"
        "而 S12 已明派其改 README 与参数化脚本、D13/D14 现役亦由其落盘；**章程与事实并存两套 SSOT＝下一位必然按旧链重跑**；"
        "③ **纪律实质一字未动**：同一时刻 D13/D14 只允许一个写者、取消≠turn 停止、重跑前清空目标目录、"
        "并发写入立即回报总控。④ **新增可执行判据**：落盘执行岗与共享工具脚本的改动**一律由总控明派**，"
        "**明派须在 D18 登记后方生效 —— 未登记的明派视为未明派**（S12 为已登记样板）。"
        "**边界**：本岗只改事实性链名与职责归属表述，不改纪律实质约束；条款订正在 D18（U02-R08）与索引留痕，"
        "**待 Chief 备案**。**Apply when**：章程条款与现役工具链/职责出现分叉时，由总控在 D18 登记后订正条款，"
        "不得让两套口径并存。"
    )
    prj["updated_at"] = NOW
    if serialize_like(json.loads(prj_raw), prj_raw) != prj_raw:
        sys.exit("[ABORT] project.json 序列化格式不一致；不写盘。")
    prj_out = serialize_like(prj, prj_raw)

    # ================= C. 00_团队章程.md 条款订正 =================
    char_old = (
        "- **D13 / D14 的落盘由总控产线唯一负责**：\n"
        "  `04_工具/handoff/make_plan.py` → `batch_build.py` → `finalize_d14.py`。\n"
        "  白模场景师只出**技术判定与问题清单**回报总控，不直接落盘、不直接改 `04_工具/handoff/**` 共享脚本。\n"
        "- 派活单里若出现「落盘 / 改文件」字样，与本条冲突时**以本条为准**。"
    )
    char_new = (
        "- **D13 / D14 的落盘链现役为**（**v2.3 · 2026-10-23 04:12 企划合规订正 · 对齐 "
        "`04_工具/handoff/README.md` 的「现役新链」**）：\n"
        "  `scripts/build_D13.py` → `scripts/build_white_model.py` → `scripts/d14_pipeline.py preflight/check/prompt` "
        "→ `scripts/fill_D14_contracts.py` → `scripts/assemble_D14.py` → `validate.mjs --unit <UNIT>`；\n"
        "  全部落在 `02_项目/双相潮主/scripts/`，**一律按 `--unit` 参数化**（逻辑层唯一一份，内容层按单元分文件，"
        "**禁止复制 `xxx_u02.py` 副本**）。\n"
        "  旧链 `04_工具/handoff/{make_plan.py, batch_build.py, finalize_d14.py}` **已退役、不是生产路径**（裁决 S12）。\n"
        "  **纪律实质不变**：同一时刻 D13 / D14 **只允许一个写者**；落盘执行岗与共享工具脚本"
        "（`04_工具/handoff/**`）的改动**一律由总控明派**，**明派须在 D18 登记后方生效 —— 未登记的明派视为未明派**"
        "（裁决 S12 即为已登记样板）。\n"
        "- 派活单里若出现「落盘 / 改文件」字样，与本条冲突时**以本条为准**；"
        "**总控已登记的明派裁决视为本条的显式例外**（以 D18 登记为准）。"
    )
    if char_old in char:
        char = char.replace(char_old, char_new)
    elif char_new not in char:
        sys.exit("[ABORT] 章程 §七·九 条款旧串与新串均未命中；不写盘。")
    else:
        skipped.append("章程 §七·九 条款（已订正）")

    # ================= D. 00_项目索引.md =================
    idx = rep(idx, "D18 **v1.38**（48 条 global_checks / 53 条 open_issues",
              f"D18 **v1.41**（{len(d18['global_checks'])} 条 global_checks / {len(d18['open_issues'])} 条 open_issues",
              "索引 §二 状态栏 D18 版本", skipped)
    idx = rep(idx, "**v1.8｜30,787 B｜02:09 落**", f"**v1.9｜{d10_sz:,} B｜04:03 落**",
              "索引 §六 D10 行", skipped)
    idx = rep(idx, "**v1.6｜107,609 B｜02:35 落**", f"**v1.7｜{d16_sz:,} B｜04:04 落**",
              "索引 §六 D16 行", skipped)
    idx = rep(idx, "**v1.2｜91,657 B｜02:31 落**", f"**v1.3｜{d15_sz:,} B｜03:18 落**",
              "索引 §六 D15 行", skipped)
    idx = rep(idx, "**v1.0｜11,281 B｜03:03 落**", f"**v1.1｜{u06_sz:,} B｜04:08 落**",
              "索引 §六 U02 D06 行", skipped)
    idx = rep(idx, "**v1.0｜28,398 B｜03:03 落**", f"**v1.1｜{u07_sz:,} B｜04:08 落**",
              "索引 §六 U02 D07 行", skipped)
    idx = rep(idx, "**v1.0｜33,817 B｜03:34 落**", f"**v1.1｜{u08_sz:,} B｜04:08 落**",
              "索引 §六 U02 D08 行", skipped)
    idx = rep(idx, "**v1.0｜17,246 B｜03:34 落**", f"**v1.0｜{u09_sz:,} B｜03:34 落**",
              "索引 §六 U02 D09 行", skipped)
    # 旧链引用行（两处）
    idx = rep(idx,
              "| `04_工具/handoff/{build_white_model.py, make_plan.py, project_bounds.py}` | 白模构建链路，仍在改（00:04 / 23:50 / 00:01） |",
              "| **现役白模链（v2.3 订正）** | `02_项目/双相潮主/scripts/{build_D13.py, build_white_model.py, "
              "d14_pipeline.py, fill_D14_contracts.py, assemble_D14.py}`（全部 `--unit` 参数化，03:39–03:54） |",
              "索引 旧链引用行", skipped)
    idx = rep(idx,
              "**另有约束（章程 §七·九 v2.2，本轮新增）**：D13/D14 的落盘改由**总控产线唯一负责**"
              "（`make_plan.py` → `batch_build.py` → `finalize_d14.py`），白模场景师只出技术判定与问题清单回报，"
              "**不再直接落盘**。U02 的派单链据此编排，不把 D13/D14 派给白模场景师。",
              "**另有约束（章程 §七·九 v2.2，**v2.3 已订正**）**：D13/D14 的**现役落盘链**为 "
              "`scripts/build_D13.py → build_white_model.py → d14_pipeline.py → fill_D14_contracts.py → "
              "assemble_D14.py`（全部 `--unit` 参数化）；旧链 `04_工具/handoff/{make_plan.py, batch_build.py, "
              "finalize_d14.py}` **已退役**。**纪律实质不变**（同一时刻单写者、取消≠turn 停止、重跑前清目录、"
              "并发即回报）；落盘执行岗与共享工具改动**由总控明派且须在 D18 登记**（S12 为样板）→ "
              "U02 的 D13/D14 按现役链派发，见 **U02-R01**／**U02-R08**。",
              "索引 章程引用段", skipped)
    # 新增 §十 节（节号按运行时最大节号＋1，不写死 —— 台账被并行实例并发写入）
    idx_heads = [l for l in idx.split("\n") if l.startswith("### 十·")]
    idx_nums = []
    for h in idx_heads:
        body = h[6:].split(" ", 1)[0].strip()
        try:
            idx_nums.append(cn_to_int(body))
        except KeyError:
            pass
    if not idx_nums:
        sys.exit("[ABORT] 索引未解析到任何 §十·N 节号；不写盘。")
    idx_max = max(idx_nums)
    idx_new = int_to_cn(idx_max + 1)
    if f"### 十·{idx_new}" in idx:
        sys.exit(f"[ABORT] 索引已含 §十·{idx_new}；不写盘。")
    idx = idx.rstrip("\n") + "\n" + f"""
### 十·{idx_new} 四份升版登记（D10 v1.9／D16 v1.7／D15 v1.3／U02 D06·D07 v1.1）＋ 章程 §七·九 条款订正 ＋ g24/g27 登记 · D18 v1.41（**企划合规 2026-10-23 04:00–04:12**）

#### 1. 认盘：并行实例已登记至 D18 v1.40，本岗补办**六处缺口**

| 缺口 | 实测（磁盘为准） | 本岗处置 |
|---|---|---|
| D10 未登记 v1.9 | v1.9｜31,091 B｜rules 17｜negatives 46 | D18 D10 行刷新 |
| D16 未登记 v1.7 | v1.7｜112,588 B｜cuts 26｜计入 D17 仍 20 | D18 D16 行刷新 |
| U02 D06/D07 仍记 v1.0 | v1.1｜11,326／28,443 B | D18 U02 两行刷新 ＋ 记 ep014 缺陷已修 |
| U02 D08/D09 行 size=null | D08 **v1.1**｜33,892 B｜D09 v1.0｜17,246 B | D18 U02 两行补齐 |
| g24/g27 提示级发现未登记 | 机位距离 g27 0.00000→0.35000、g24 0.28284→0.35000 | 新增 **U02-R07** |
| 章程 §七·九 与现役链矛盾 | 旧链 `make_plan.py` 已退役；职责表述与 S12 明派冲突 | **条款订正 ＋ S14 ＋ U02-R08** |

#### 2. 章程 §七·九 条款订正（**纪律实质一字未动**）

- 链名更新为现役新链（`scripts/` 下 6 步，全部 `--unit` 参数化），旧链标注**已退役、不是生产路径**。
- **保留全部实质约束**：同一时刻单写者、取消≠turn 停止、重跑前清空目标目录、并发写入立即回报。
- **新增可执行判据**：落盘执行岗与共享工具脚本的改动**一律由总控明派**，**明派须在 D18 登记后方生效**
  ——**未登记的明派视为未明派**（S12 为已登记样板）。条款订正在 D18（U02-R08）与 `decisions.S14` 留痕，**待 Chief 备案**。

#### 3. 回报与磁盘的两处出入（一律以磁盘为准）

- 台本编剧报「U02 D08 v1.0」→ 磁盘实为 **v1.1**（返修 U02-R03 已落）；
- 索引 §六 U02 D08 行记 **33,817 B** → 磁盘实为 **33,892 B**。

#### 4. 出口闸

`validate.mjs --unit U01` → **error 0 / 11-11 / warning 2**（既有项）；`--unit U02` → **error 0 / warning 12**（基线）；
`render-md.mjs` 单向重渲染；**U01 锁态未动**（locked @ 01:28）。
"""

    # ================= E. 99_交付说明.md =================
    heads = [l for l in deliv.split("\n") if l.startswith("## ")]
    nums = []
    for h in heads:
        body = h[3:].split("、", 1)[0].strip()
        try:
            nums.append(cn_to_int(body))
        except KeyError:
            pass
    if not nums:
        sys.exit("[ABORT] 交付说明未解析到任何中文节号；不写盘。")
    max_n = max(nums)
    new_cn = int_to_cn(max_n + 1)
    if f"## {new_cn}、" in deliv:
        sys.exit(f"[ABORT] 交付说明已含 §{new_cn}；不写盘。")
    deliv = deliv.rstrip("\n") + "\n" + f"""
## {new_cn}、四份升版登记 ＋ 章程 §七·九 条款订正 ＋ g24/g27 登记 ＋ D18 v1.41（**企划合规 2026-10-23 04:00–04:12**）

### {new_cn}.1 补办六处缺口（并行实例已登记至 D18 v1.40，本岗只补缺口、不重复记账）

D10 v1.9（31,091 B｜rules 17｜negatives 46）、D16 v1.7（112,588 B｜cuts 26｜计入 D17 仍 20）、
D15 v1.3（93,985 B｜与 v1.1 时长数据逐字节一致）、U02 D06/D07 v1.1（11,326／28,443 B｜ep014 在场名单冲突已修）、
U02 D08 **v1.1**（33,892 B）＋ D09 v1.0（17,246 B）—— 五行全部刷新；新增 **U02-R07**（g24/g27）＋ **U02-R08**（章程条款）。

### {new_cn}.2 章程 §七·九 条款订正（**实质未动**，S14 留痕）

链名更新为现役新链；旧链标注已退役；保留「同一时刻单写者／取消≠turn 停止／重跑前清目录／并发即回报」；
新增判据「落盘执行岗与共享工具改动**由总控明派且须在 D18 登记**，未登记的明派视为未明派」。

### {new_cn}.3 回报与磁盘两处出入（以磁盘为准）

台本编剧报 D08 v1.0 → 磁盘 **v1.1**；索引 §六 记 33,817 B → 磁盘 **33,892 B**。

### {new_cn}.4 出口闸与边界

`validate --unit U01` → **11/11、error 0、warning 2**（既有项）；`--unit U02` → error 0（基线）；MD 全由 `render-md.mjs` 渲染。
本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`00_团队章程.md`（§七·九 一处）、`99_交付说明.md`（本节）。
**未改**任何交付物 JSON、源素材、规格、工具脚本；未生成图片／视频／音频，未合成 TTS，未提交 H3 付费生成，未投流上架。
"""

    # ================= F. 终态自检 =================
    if "U02-R07" not in d18_out or "U02-R08" not in d18_out:
        sys.exit("[ABORT] D18 序列化后丢失新增条目；不写盘。")
    if "S14_章程单写者条款与现役工具链对齐" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S14；不写盘。")
    if "v2.3 · 2026-10-23 04:12 企划合规订正" not in char:
        sys.exit("[ABORT] 章程条款订正未生效；不写盘。")
    if idx.count(f"### 十·{idx_new}") != 1:
        sys.exit(f"[ABORT] 索引 §十·{idx_new} 写入异常；不写盘。")
    if deliv.count(f"## {new_cn}、") != 1:
        sys.exit(f"[ABORT] 交付说明 §{new_cn} 写入异常；不写盘。")
    # 节号唯一性：交付说明全档
    dup = [h for h in set(
        l[3:].split("、", 1)[0].strip() for l in deliv.split("\n") if l.startswith("## ")
    ) if sum(1 for l in deliv.split("\n") if l.startswith("## ") and
             l[3:].split("、", 1)[0].strip() == h) > 1]
    if dup:
        sys.exit(f"[ABORT] 交付说明节号重号 {dup}；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 v1.40→v1.41（U01 三行 + U02 四行刷新；+U02-R07 +U02-R08）；"
              f"project.json（+S14）；章程 §七·九 条款订正；索引（§二 1 处 ＋ §六 7 处 ＋ 旧链引用 2 处 ＋ §十·三十二）；"
              f"交付说明 §{new_cn}（运行时最大节号 {max_n}＋1）；索引 §十·{idx_new}（运行时最大 {idx_max}＋1）")
        return

    write(p18, d18_out)
    write(p_prj, prj_out)
    write(charter, char)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 台账回刷 ＋ 章程条款订正完成")
    print(f"   shared/D18.json：v1.40 → {d18['version']}（global_checks {len(d18['global_checks'])}、"
          f"open_issues {len(d18['open_issues'])}；U01 三行 ＋ U02 四行刷新）")
    print(f"   project.json：+S14_章程单写者条款与现役工具链对齐；updated_at → {NOW}")
    print("   00_团队章程.md：§七·九 链名与职责表述订正（纪律实质未动）")
    print(f"   00_项目索引.md：§二 1 处 ＋ §六 7 处 ＋ 旧链引用 2 处 ＋ §十·{idx_new}")
    print(f"   99_交付说明.md：新增 §{new_cn}")


if __name__ == "__main__":
    main()
