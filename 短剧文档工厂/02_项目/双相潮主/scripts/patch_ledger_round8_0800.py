#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_ledger_round8_0800.py —— 分镜导演 06:20 通报核盘 ＋ 六项挂账逐项裁定
                              ＋ ④「律条四层锚点」机器闸落地登记（企划合规 2026-10-23 08:00）

本轮交付（本岗已完成，不派下游）：
  ① **④ 落地** —— `03_规格/rules.json` 新增 `term_first_use` 轴 ＋ `04_工具/lib/rules.mjs` **V5 内扩展**
     （**不新增规则编号**，全台账「11/11」不受影响）；**五腿负测**：三腿必须拦（全部拦下）／
     两腿必须放行（画面描述面、区间外，全部正确放行）；**真盘 SHA256 未变**（真盘零写入）。
  ② **分镜导演 06:20 通报的逐项核盘** —— 三处数字已过期（U02 D11 v1.4→**v1.6**、U02 D16 v1.3→**v1.5**、
     出口闸 U01 2／U02 8→**1／5**）；其余成立。
  ③ **六项挂账逐项裁定**（①③⑥ 已闭环／② 归出片阶段／④ 本岗已落地／⑤ 待用户答）。

用法：python3 scripts/patch_ledger_round8_0800.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def serialize_like(obj, raw):
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return body + "\n" if raw.endswith("\n") else body


def insert_before_next_section(lines, my_header, section_prefix, block, note):
    """插入到「本岗章节之后的第一个同级标题之前」—— Q72 锚点纪律（禁 EOF 锚点）。"""
    mine = [i for i, l in enumerate(lines) if l.startswith(my_header)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] {note} 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    nxt = [i for i, l in enumerate(lines) if i > mine[0] and l.startswith(section_prefix)]
    seg = lines[mine[0]: nxt[0]] if nxt else lines[mine[0]:]
    if not nxt:
        sys.exit(f"[ABORT] {note} 本岗章节之后无同级标题；不写盘。")
    return lines[:nxt[0]] + block + lines[nxt[0]:]


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
    p_rules = os.path.join(factory, "03_规格", "rules.json")
    p_rmjs = os.path.join(factory, "04_工具", "lib", "rules.mjs")

    now = datetime.now()
    stamp_hm = now.strftime("%H:%M")
    stamp_full = f"{now.strftime('%Y-%m-%d')} {stamp_hm}"

    d18_raw = read(p18)
    d18_raw_orig = d18_raw
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj_raw_orig = prj_raw
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检：编号运行时取 max+1（并行实例会连占） ----------
    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 84):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.84；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    ops_max = max(int(i.split("-")[1]) for i in oi if i.startswith("OPS-") and i.split("-")[1].isdigit())
    q_max = max(int(g["id"][1:]) for g in d18["global_checks"]
                if g["id"].startswith("Q") and g["id"][1:].isdigit())
    ops_id = "OPS-%d" % (ops_max + 1)
    q_id = "Q%d" % (q_max + 1)
    if ops_id in oi:
        sys.exit(f"[ABORT] open_issues 已含 {ops_id}；不写盘。")
    if any(g["id"] == q_id for g in d18["global_checks"]):
        sys.exit(f"[ABORT] global_checks 已含 {q_id}；不写盘。")
    if "S31_术语首用集机器闸与律条四层锚点落地裁定" in prj["decisions"]:
        sys.exit("[ABORT] project.json 已含 S31；不写盘。")
    print(f"[ID] 运行时取号：{ops_id}、{q_id}")

    # ---------- 证据自检：④ 的落地必须在盘 ----------
    rules_cfg = json.loads(read(p_rules))
    tfu = rules_cfg.get("term_first_use") or []
    if not tfu or tfu[0].get("term") != "律条" or tfu[0].get("first_use_ep") != 13:
        sys.exit("[ABORT] rules.json 的 term_first_use 轴未落「律条/first_use_ep=13」；不写盘。")
    if "术语首用集前禁用" not in read(p_rmjs):
        sys.exit("[ABORT] rules.mjs 未见 V5 内扩展「术语首用集前禁用」；不写盘。")

    # ---------- A. D18 ----------
    d18["global_checks"].append({
        "id": q_id,
        "item": "**术语「首用集前禁用」必须机器化，且「受检面」与「不检面」必须分列声明** —— "
                "本轮实证（分镜导演挂账④：D05 v1.3 律条四层锚点未进机器闸，U03 起需上游补规则条目）："
                "D05 词条已写死「**ep013–ep040 台词与字幕不得出现「律条」三字（画面描述可用）**」，"
                "但**机器闸无此判据** —— 分镜导演只能靠 U02 侧本地 A37／A38 补位，"
                "**U03 开工即复发**。**做法**：① **落点＝规则文件声明轴 ＋ 既有规则内扩展**，"
                "本岗在 `03_规格/rules.json` 新增 **`term_first_use` 轴**（工具侧声明，**不是交付物 JSON**，"
                "故不受 `additionalProperties:false` 限制）、在 **`04_工具/lib/rules.mjs` 的 V5 内扩展** —— "
                "**不新增规则编号**（全台账「11/11」不受影响）；"
                "② **面划分必须显式**：`dialogue`（台词面）＝D11 `shots[].dialogue` ＋ D08 `body[].text`"
                "（**仅 `type=dialogue`**）；`subtitle`（字幕面）＝D16 `subtitle_style.lines[].text`；"
                "**画面描述面不查**（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt`）—— "
                "**D08 正文里的「一枚律条被推上交易台」属画面描述面，不构成违规**（D05 明文允许），"
                "**若把面划错就会误伤正确内容**；"
                "③ **区间判定用集号**，不由字符串猜 —— 区间外（ep009）必须放行；"
                "④ **负测必须含「必须放行」两腿**（画面描述面 ＋ 区间外），"
                "只测「必须拦」会把误伤当成生效；"
                "⑤ **字面禁用写法（自造档位修饰语如「低阶律条」）不走此轴**，"
                "走 D05 词条的 `forbidden_synonyms`（V5 既有机制）—— **轴的职责不可混同**。"
                "**Apply when**：任何「某术语在首用集之前不得出现在某类文本面」的约定。",
        "method": "注入式负测：台词面／字幕面／画面描述面／区间外 四类注入各跑一次，"
                  "「必须拦」与「必须放行」分别断言；并比对真盘交付物 SHA256 确认零写入",
        "source": "企划合规 2026-10-23 08:00（分镜导演挂账④ 处置落地）",
        "severity": "中（不产生错交付物，但无此闸则约定只能靠人工与本地补丁守，跨单元必复发）",
    })
    d18["open_issues"].append({
        "id": ops_id,
        "issue": "**「D05 v1.3 律条四层锚点」未进机器闸 —— 约定只存在于词条散文里，"
                 "机器闸无从校验，跨单元必复发** —— 分镜导演挂账④ 原文："
                 "「D05 v1.3 律条四层锚点尚未进机器闸 → 本岗以 A37／A38 在 U02 侧本地补位，U03 起需上游补规则条目」。"
                 "**根因二分**：① **首用集前禁用面**（ep013–ep040 台词与字幕不得出现「律条」）"
                 "＝ **约定已写清、但无判据载体** → 本岗已落地（见 resolution）；"
                 "② **自造档位修饰语面**（「低阶律条」等第三种档位写法）＝ **D05 v1.3 已明令禁止、"
                 "却未把该写法写进词条的 `forbidden_synonyms`** → **机器闸缺口的根因在 D05，不在校验器**。",
        "owner": "企划合规（面①，已闭环）＋ 故事架构（面②，D05 属主，本岗不代改他岗交付物）",
        "blocks": "不拦 U02 单元锁（U02 只余 D14）；**面②须在 U03 开工前收口**，否则自造档位写法可再次写入",
        "priority": "中",
        "status": "**部分闭环**（面①本岗已落地并负测通过；面②待 D05 属主补 `forbidden_synonyms`）",
        "resolution": "**2026-10-23 08:00 企划合规落地（面①）**：`03_规格/rules.json` 新增 **`term_first_use` 轴**"
                      "（`term=律条`／`first_use_ep=13`／`forbidden_until_ep=40`／"
                      "`forbidden_faces=[dialogue,subtitle]`／附 `basis` 指回 D05 v1.3 词条原文），"
                      "`04_工具/lib/rules.mjs` **V5 内扩展**实现（**不新增规则编号**，全台账「11/11」不变）。"
                      "**五腿负测全部符合预期**：① D11 ep013 台词面注入「律条」→ **拦**；"
                      "② D16 ep013 字幕面注入 → **拦**；③ D08 ep013 `type=dialogue` 注入 → **拦**；"
                      "④ D08 ep013 `type=action`（画面描述面）注入 → **正确放行**；"
                      "⑤ D08 ep009（区间外）注入 → **正确放行**；"
                      "**真盘 U02 D11／D16／D08 SHA256 与测试前一致**（真盘零写入）。"
                      "**面②派单**：**@故事架构** 请在 D05 下一版把「低阶律条」等**自造档位修饰语**"
                      "补进 `律条` 词条的 `forbidden_synonyms`（一行）→ V5 既有禁用同义词扫描立即机读化，"
                      "**无需任何校验器改动**；**本岗不代改他岗交付物**（§七·九）。"
                      "**分镜导演 U02 侧本地 A37／A38 补位保留**（D13／D14 前的临时补位），**U03 起以机器闸为准**。",
        "detected_by": "分镜导演 2026-10-23 06:20 挂账④ ＋ 企划合规 08:00 落地与负测",
    })
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj["decisions"]["S31_术语首用集机器闸与律条四层锚点落地裁定"] = (
        "企划合规裁决（2026-10-23 08:00，配套 **" + q_id + "** ＋ **" + ops_id + "**）："
        "**① 首用集前禁用面由本岗直接落地，不派下游** —— 落点＝`03_规格/rules.json` 新增 `term_first_use` 轴"
        "（工具侧声明，**不是交付物 JSON**，不受 `additionalProperties:false` 限制）"
        "＋ `04_工具/lib/rules.mjs` **V5 内扩展**（**不新增规则编号**，全台账「11/11」不受影响）。"
        "**② 面划分必须显式且分列** —— 台词面（D11 `shots[].dialogue` ＋ D08 `body[].text` 仅 `type=dialogue`）"
        "＋字幕面（D16 `subtitle_style.lines[].text`）；**画面描述面不查**"
        "（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt`）—— "
        "**D08 正文「一枚律条被推上交易台」属画面描述面，不构成违规；面划错即误伤正确内容**。"
        "**③ 负测必须含「必须放行」两腿**（画面描述面 ＋ 区间外）—— 只测「必须拦」会把误伤当生效。"
        "**④ 字面禁用写法不走此轴** —— 自造档位修饰语（如「低阶律条」）走 D05 词条 `forbidden_synonyms`；"
        "**其根因在 D05 未把该写法写进 `forbidden_synonyms`，不在校验器** → 派 **D05 属主（故事架构）**补一行。"
        "**⑤ 台账闸门数字是「记录时点实测」，不是「当前值」** —— 引用时必须带时点或当场重跑"
        "（与并行实例 OPS-18 同向、已互认）。"
        "**Apply when**：任何「术语在首用集前不得出现在某类文本面」的约定；任何带区间/分面的文本禁用约定。"
    )
    prj["updated_at"] = stamp_full
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引（本岗章节内追加，Q72 锚点） ----------
    idx_lines = idx.split("\n")
    idx_block = [
        "",
        f"#### 7. 分镜导演 06:20 通报核盘 ＋ 六项挂账逐项裁定 ＋ **④ 机器闸落地**（{stamp_hm}）",
        "",
        "| 通报项 | 通报口径 | **磁盘实况** | 判定 |",
        "|---|---|---|---|",
        "| U02 D11 | v1.4／58,129 B | **v1.6／58,051 B** | 以磁盘为准（其后有升版） |",
        "| U02 D16 | v1.3 零改动 | **v1.5** | 以磁盘为准 |",
        "| U02 D12／D13／D14 | 缺 D12/D13/D14 | **D12 v1.0／D13 v1.0 已落**，**只余 D14** | 挂账①**已闭环** |",
        "| 出口闸 | U01 warning 2／U02 warning 8 | **U01 1／U02 5／全项目 6** | 通报数字**已过期**（OPS-17 消 `title` 误报 −1；U02 D13 落盘 −1） |",
        "| 「低阶」全库 | 0 命中 | **交付物内容面 0**（D05／D07／D08 v1.4／D11／D16 全 0）｜**shared/D18.json 判据/台账面 8 处**（属留痕引用，非内容） | **内容面成立** |",
        "| Q56 断言清单 | 39 条 | `build_D11_U02.py --check` 实跑 **39 条、exit 0** | 成立 |",
        "| ep13 锚点改通称 | 已改 | `shotintent_map_U02.mjs` 第 78 行 `[13,6,3,[\"一枚律条被推上交易台\",\"纹路压着冷光\"]]`，旧值按 S11 留痕 | 成立 |",
        "",
        "**六项挂账逐项裁定**：",
        "",
        "① **U02 缺 D12／D13／D14** → **已闭环**（D12 v1.0、D13 v1.0 已在盘，**只余 D14**；D14 派单 07:3x 已发白模场景师并入队）→ **U02 单元锁 L1 只余 D14**。",
        "② **ep2#4 旧音频** → 已在台账 **U01-R22**，归**出片阶段**重合成（本岗不合成 TTS／BGM，硬边界）；"
        "旧音频 `ep002_13.mp3` 若误复用则字幕提前 **1.153s**。",
        "③ **U01 侧断言清单化（Q56②）** → **已裁定并已派单 U01-R33**（落点＝**不新建构建脚本**；"
        "在 `reconcile_D15_D16_timing.mjs` 与 `reconcile_tts_actual_vs_d15_budget.mjs` 内加"
        "「判据清单（编号＋判据＋来源）＋ 清单条数==实际断言点数守卫」）；"
        "07:45 经 `mavis session send` 直投分镜导演会话，**status=accepted／mode=queued／position=1**；"
        "**task_id 待通道恢复后补登记**（同 request_id 幂等，**不得重复投递**）。",
        f"④ **D05 v1.3 律条四层锚点未进机器闸** → **本岗已落地，不派下游**："
        "`03_规格/rules.json` 新增 **`term_first_use` 轴**（工具侧声明）＋ `04_工具/lib/rules.mjs` "
        "**V5 内扩展**（**不新增规则编号**，全台账「11/11」不变）；"
        "**受检面＝台词面**（D11 `shots[].dialogue` ＋ D08 `body[].text` 仅 `type=dialogue`）"
        "**＋字幕面**（D16 `subtitle_style.lines[].text`）；**画面描述面不查**"
        "（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt` —— D05 明文允许，"
        "**D08 正文「一枚律条被推上交易台」不构成违规**）；"
        "**五腿负测全符合预期**（D11 台词／D16 字幕／D08 台词 **三腿必须拦→全部拦下**；"
        "D08 `type=action` **必须放行→放行**；ep009 区间外 **必须放行→放行**）；"
        "**真盘 U02 D11／D16／D08 SHA256 与测试前一致**（真盘零写入）。"
        f"**残留（面②）**：自造档位修饰语（「低阶律条」）走 D05 词条 `forbidden_synonyms`，"
        f"**根因在 D05 未写进 `forbidden_synonyms`、不在校验器** → **@故事架构** 在 D05 下一版补一行即可机读化"
        f"（**本岗不代改他岗交付物**，§七·九）。登记 **{ops_id}** ＋ **{q_id}**。",
        "⑤ **G-05 预算档位** → **本岗无权自裁，已向用户发出裁定问卷**（预算档位／备案申报主体／G-10 题材映射三项）；"
        "另已查证权威口径并将在群内附上：**AI 微短剧一类≥80万／二类 30万(含)–80万／三类<30万**，"
        "三类由平台播前审核＋标注节目编号（**无需备案公示**），一/二类须持《广播电视节目制作经营许可证》的"
        "法人机构申报（**自然人不能作为备案申报主体**）。",
        "⑥ **§五十三.6 多单元同跑** → **已裁定**（**S17／OPS-13／Q52：逐单元独立 collect ＋ 独立跑规则，"
        "禁止跨单元合并**；改后全项目 error 0／22-22／exit 0）。",
        "",
        f"> **另需告知**：**台账闸门数字是「记录时点实测」，不是「当前值」** —— 引用时必须带时点或当场重跑"
        f"（与并行实例 OPS-18 同向、已互认）。分镜导演 06:20 通报的 U01 warning 2／U02 warning 8 属**当时实况**，"
        f"现值已变为 **1／5**。",
        "",
    ]
    idx_lines = insert_before_next_section(idx_lines, "### 十·五十八", "### 十·", idx_block,
                                          "索引 §十·五十八 追加")
    idx = "\n".join(idx_lines)

    # ---------- D. 交付说明（本岗章节内追加，Q72 锚点） ----------
    del_lines = deliv.split("\n")
    del_block = [
        "",
        f"### 一百零二.8 分镜导演 06:20 通报核盘 ＋ 六项挂账裁定 ＋ ④ 机器闸落地（{stamp_hm}）",
        "",
        "**核盘（以磁盘为准）**：U02 D11 通报 v1.4／58,129B → **磁盘 v1.6／58,051B**；U02 D16 通报 v1.3 → **磁盘 v1.5**；"
        "「缺 D12/D13/D14」→ **D12 v1.0、D13 v1.0 已落，只余 D14**；"
        "出口闸通报 U01 2／U02 8 → **现值 1／5**（OPS-17 消 `title` 误报 −1；U02 D13 落盘 −1）；"
        "「低阶」→ **交付物内容面 0**，仅 `shared/D18.json` 判据/台账面 8 处（属留痕引用）；"
        "Q56 清单 39 条 → `build_D11_U02.py --check` 实跑 39／exit 0；ep13 锚点改通称 → 盘上已改、旧值按 S11 留痕。",
        "",
        "**六项挂账**：① **已闭环**（U02 只余 D14）｜② 归 **U01-R22** 出片阶段｜"
        "③ **U01-R33 已裁定并派单**（07:45 `mavis session send` accepted/queued，task_id 待补）｜"
        f"④ **本岗已落地机器闸**（`term_first_use` 轴 ＋ V5 内扩展，五腿负测三拦两放行，真盘零写入）｜"
        f"⑤ **待用户答**（已发问卷）｜⑥ **已裁定**（S17／OPS-13／Q52）。残留面②（自造档位修饰语）"
        f"**@故事架构** 在 D05 下一版补 `forbidden_synonyms` 一行即可机读化 → **{ops_id}** ＋ **{q_id}**。",
        "",
        "> 本节追加遵守 **Q72**：锚点＝「下一节标题之前」，**不追加到文件末尾**。",
        "",
    ]
    del_lines = insert_before_next_section(del_lines, "## 一百零二、", "## ", del_block,
                                          "交付说明 §一百零二 追加")
    deliv = "\n".join(del_lines)

    # ---------- E. 自检（按行定位边界，禁字符串 find） ----------
    def span(lines, my_header, section_prefix, probe):
        mine = [i for i, l in enumerate(lines) if l.startswith(my_header)]
        if len(mine) != 1:
            sys.exit(f"[ABORT] {my_header} 命中数 {len(mine)} ≠ 1；不写盘。")
        nxt = [i for i, l in enumerate(lines) if i > mine[0] and l.startswith(section_prefix)]
        seg = lines[mine[0]: nxt[0]] if nxt else lines[mine[0]:]
        if not any(probe in l for l in seg):
            sys.exit(f"[ABORT] 追加未落在本岗章节内（probe={probe}）；不写盘。")

    span(idx.split("\n"), "### 十·五十八", "### 十·", "#### 7. 分镜导演 06:20 通报核盘")
    span(deliv.split("\n"), "## 一百零二、", "## ", "### 一百零二.8 分镜导演 06:20 通报核盘")
    for k in (ops_id, q_id):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S31_术语首用集机器闸与律条四层锚点落地裁定" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S31；不写盘。")

    # ---------- F. 并发写盘竞态守卫 ----------
    for path, raw0, label in ((p18, d18_raw_orig, "shared/D18.json"),
                               (p_prj, prj_raw_orig, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 {ver}→{d18['version']}（＋{ops_id} ＋{q_id}）；project.json ＋S31；"
              f"索引 §十·五十八 ＋ §7；交付说明 §一百零二 ＋ §一百零二.8（均 Q72 锚点）")
        return

    bak = os.path.join(proj, "reports", "_bak_0800_patch_round8")
    os.makedirs(bak, exist_ok=True)
    for path, name in ((p18, "D18.json"), (p_prj, "project.json"),
                       (p_idx, "00_项目索引.md"), (p_del, "99_交付说明.md")):
        with open(os.path.join(bak, name), "wb") as f:
            f.write(open(path, "rb").read())

    write(p18, d18_out)
    write(p_prj, prj_out)
    idx = idx.replace("«RUN_HM»", datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M"))
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 分镜导演 06:20 通报核盘 ＋ 六项裁定 ＋ ④ 机器闸落地登记")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：＋S31；updated_at → {stamp_full}")
    print("   00_项目索引.md：§十·五十八 ＋ §7（Q72 锚点）")
    print("   99_交付说明.md：§一百零二 ＋ §一百零二.8（Q72 锚点）")


if __name__ == "__main__":
    main()
