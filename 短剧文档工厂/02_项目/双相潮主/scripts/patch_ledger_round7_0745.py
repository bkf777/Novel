#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_ledger_round7_0745.py —— 分镜导演 Q68／S27③／U02-R34 回执核销 ＋ U01-R33 投递留痕
                              ＋ 新判据（沙箱负测）＋ 新 open_issue（跨交付物边界脚本）（企划合规 2026-10-23 07:45）

核销依据（**全部本岗独立复跑，非转述**）：
  ① S27 ③ 共享脚本归属声明 —— `scripts/shotintent_map_U02.mjs` 文件头实测已改为双向口径
     （锚点侧＝分镜导演／原文侧＝台本编剧），原「台本编剧维护」声明按 S11 留痕作废未删；
     MAP 29 条未动；覆盖轴 U01 23/23、U02 29/29 exit 0；Q64 适用性判定「不适用」成立。
  ② Q68 沙箱自测器 —— 实跑 `scripts/selftest_Q64_Q68_sandbox.py` 受检 10 条／通过 10／失败 0／exit 0；
     **真盘零写入实测成立**（D11 U02 SHA256 前缀 82631f35cb39742e、D16 U02 bde3f6791e60dae0，与自测前一致）。
  ③ U02-R34 —— 分镜导演侧「9 脚本按实际写盘目标实测归属」已交（台本编剧 4／视觉设定 2／白模场景师 1／声音设计 2）；
     余 `build_D15_U02.py`（U02 现役）版本守卫 → **声音设计**；新发现 `apply_d15_d16_sync.py`
     一次运行同时写 D15＋D16 ＝ **跨交付物边界** → 本岗单独立项登记（不属分镜导演，不代改）。
  ④ U01-R33 投递 —— `mavis session send` 直投分镜导演会话 `mvs_778c258f…`：
     **status=accepted／mode=queued／queue position 1／ahead 0**（MCP 通道仍断，绕行生效）。

⚠️ 本脚本的台账追加**锚点＝「下一节标题之前」**（动态查找本岗章节之后的第一个同级标题），
**不再使用「追加到文件末尾」** —— 遵 Q72／OPS-20。

用法：python3 scripts/patch_ledger_round7_0745.py --project 02_项目/双相潮主 [--dry-run]
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
    """把 block 插到「本岗章节之后的第一个同级标题」之前 —— Q72 锚点纪律。"""
    mine = [i for i, l in enumerate(lines) if l.startswith(my_header)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] {note} 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    nxt = [i for i, l in enumerate(lines) if i > mine[0] and l.startswith(section_prefix)]
    if not nxt:
        sys.exit(f"[ABORT] {note} 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
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

    # ---------- 证据自检：编号运行时取 max+1 ----------
    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 77):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.77；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    for k in ("OPS-16", "U02-R34", "U01-R33"):
        if k not in oi:
            sys.exit(f"[ABORT] open_issues 无 {k}；不写盘。")
    ops_max = max(int(i.split("-")[1]) for i in oi if i.startswith("OPS-") and i.split("-")[1].isdigit())
    q_max = max(int(g["id"][1:]) for g in d18["global_checks"]
                if g["id"].startswith("Q") and g["id"][1:].isdigit())
    ops_id = "OPS-%d" % (ops_max + 1)
    q_id = "Q%d" % (q_max + 1)
    if ops_id in oi:
        sys.exit(f"[ABORT] open_issues 已含 {ops_id}；不写盘。")
    if any(g["id"] == q_id for g in d18["global_checks"]):
        sys.exit(f"[ABORT] global_checks 已含 {q_id}；不写盘。")
    if "S30_版本守卫负测沙箱化与跨交付物边界脚本归属" in prj["decisions"]:
        sys.exit("[ABORT] project.json 已含 S30；不写盘。")
    print(f"[ID] 运行时取号：{ops_id}（现 max OPS-{ops_max}）、{q_id}（现 max Q{q_max}）")

    # ---------- A. D18 ----------
    # A1 OPS-16 → 已裁定·已落地
    oi["OPS-16"]["status"] = "**已裁定·已落地**（企划合规 2026-10-23 07:25 裁定 S27 · 07:45 核销分镜导演落地）"
    oi["OPS-16"]["resolution"] = oi["OPS-16"]["resolution"].rstrip() + (
        "　**2026-10-23 07:45 企划合规独立核销（落地）**：实测 `scripts/shotintent_map_U02.mjs` 文件头"
        "**已改为双向口径**（锚点侧＝分镜导演／原文侧＝台本编剧，任一方改动须同步另一方并重跑覆盖轴），"
        "原「台本编剧维护」声明按 **S11 留痕作废未删**（含作废原因：06:18:39 实际写者为分镜导演）；"
        "**MAP 29 条一字未动**；覆盖轴 **U01 23/23、U02 29/29 exit 0**；"
        "**Q64 适用性判定「不适用」成立**（纯数据模块、只 `export const MAP`、无写盘调用）。"
        "→ **本条由「已裁定」升为「已裁定·已落地」，闭环。**"
    )

    # A2 U02-R34 → 分镜导演侧已核销
    oi["U02-R34"]["status"] = ("**部分核销**（分镜导演侧 07:3x 已交并经本岗 07:45 核销；"
                              "余 **声音设计** 侧 `build_D15_U02.py` 版本守卫；U02 不拦，U03 开工前须收口）")
    oi["U02-R34"]["resolution"] = oi["U02-R34"]["resolution"].rstrip() + (
        "　**2026-10-23 07:45 企划合规核销（分镜导演侧）**：分镜导演已交「**9 个脚本按实际写盘目标实测归属**」"
        "（台本编剧 4／视觉设定 2／白模场景师 1／声音设计 2；`build_D15_U02.py` 为 U02 现役）→ **本岗收讫**。"
        "**余项不在分镜导演**：① `build_D15_U02.py` 版本守卫 → **声音设计**（U02 现役，须在 U03 开工前补齐）；"
        "② 分镜导演另报 **`apply_d15_d16_sync.py` 一次运行同时写 D15（声音设计）＋D16（分镜导演）**"
        "＝ **跨交付物边界、无版本守卫、文件头无归属声明** → **本岗已单独立项登记为 " + ops_id + "**"
        "（不属分镜导演，**本岗不代改他岗脚本**，§七·九）。"
        "**本条不因上述两项而闭合**，须待声音设计侧补齐后方可结。"
    )

    # A3 U01-R33 投递留痕
    oi["U01-R33"]["status"] = ("**已明派·已投递**（群内 @点名 ＋ `mavis session send` 直投分镜导演会话，"
                              "07:45 status=accepted／mode=queued／queue position 1；"
                              "MCP 派单通道仍断，**task_id 待通道恢复后补登记**）")
    oi["U01-R33"]["resolution"] = oi["U01-R33"]["resolution"].rstrip() + (
        "　**2026-10-23 07:45 企划合规投递留痕**：minimax-bot MCP 派单通道自 04:45 起断"
        "（`message_bot`／`dispatch_tasks`／`post_group`／`list_team` 全线返回"
        "「这个 Bot 正在多个聊天里回复，暂时无法确认工具调用属于哪个聊天」），"
        "故改用 **`mavis session send` 直投**分镜导演会话 `mvs_778c258f17b44a92a2a99186e51d7341`："
        "**status=accepted／mode=queued／queue itemId=queue_22b4f631-43b1-427c-8c40-ed36284b5c57／"
        "position=1／ahead=0**。**同封内容含三部分**：① 本岗对分镜导演 **S27③／Q68 沙箱自测器／U02-R34** 的核销回执；"
        "② **U01-R33 派单本体**（落点＝两个既有 reconcile 脚本内加判据清单＋机械守卫，**不新建构建脚本**；"
        "复制来的判据**须逐条标来源**；负测须中止且交付物字节未变；**交付物 JSON 内容一字不得改**）；"
        "③ 通道说明与 **warning 计数新值**（U01 1／U02 6／全项目 7，OPS-17 修掉 `title` 误报后）。"
        "**待办**：通道恢复后补登记 task_id（**不得重复投递**，同 request_id 幂等）。"
    )

    # A4 新 open_issue（运行时取号）：跨交付物边界脚本
    d18["open_issues"].append({
        "id": ops_id,
        "issue": "**`scripts/apply_d15_d16_sync.py` 一次运行同时写两份不同归属的交付物** "
                 "（D15 ＝ **声音设计**、D16 ＝ **分镜导演**）→ **跨交付物边界**；"
                 "且该脚本**无版本守卫**、**文件头无归属声明** —— "
                 "实测来源：分镜导演 07:3x 在 U02-R34 归属对照中报出（本岗 07:45 独立复核后登记）。"
                 "**危害**：① **单写者纪律失效** —— 一次运行可同时改两岗交付物，无人声明归属；"
                 "② **版本守卫缺口** —— 跨岗写盘却无回退保护，重跑可能静默回退他人改动；"
                 "③ **归属无法追溯** —— 文件头无声明，出事后无法判定实际写者。",
        "owner": "声音设计 ＋ 分镜导演（**双方共同**；按 S27 ② 写「两侧责任＋同步义务」，不写单一 owner）",
        "blocks": "不拦 U02 单元锁（D13／D14 之外项）；**拦 U03 开工** —— 开工前须收口",
        "priority": "中",
        "status": "**已登记·待收口**（企划合规 2026-10-23 07:45；待两岗处置，本岗不代改他岗脚本）",
        "resolution": "**2026-10-23 07:45 企划合规登记**：处置方向 ① **拆分**（D15 侧与 D16 侧各自独立脚本，"
                      "各带版本守卫与归属声明）；② 或 **保留单脚本但补齐**—— 文件头按 **S27 ②** 写明两侧责任、"
                      "**两侧各自带版本守卫**、任一方改动须同步另一方并重跑覆盖轴（受检须 >0、exit 0）；"
                      "③ **本岗不代改他岗脚本**（§七·九），**不代写归属声明**。"
                      "**Apply when**：任何「一次运行写多份不同归属交付物」的脚本。",
        "detected_by": "分镜导演 2026-10-23 07:3x（U02-R34 归属对照）＋ 企划合规 07:45 登记",
    })

    # A5 新 global_check（运行时取号）：沙箱负测纪律
    d18["global_checks"].append({
        "id": q_id,
        "item": "**版本守卫／漂移守卫的「负测」（伪造高版本、篡改内容等试探）只能在沙箱副本上做 —— "
                "禁止在真实交付物上做** —— 本轮实证：分镜导演 07:3x **主动披露** —— "
                "在 **Q68 尚未登记**时，曾在真实 `D11 U02`／`D16 U02` 上各伪造一次 `version=v9.9` 做负测"
                "（事后全部还原、cmp 逐字节一致）。**后果**：真盘交付物在测试窗口内处于**被人为改写**的状态，"
                "**任何并发读盘者都会读到伪造版本**，而守卫本该防的正是这种「版本被改」——"
                "**测试行为本身复现了它要防的风险**。**做法**：① **沙箱由 `__file__` 推导 ROOT**"
                "（确保只读写副本，真盘零写入）；② **负测前后打印真盘 SHA256 前缀并比对**（本例 "
                "`82631f35cb39742e`／`bde3f6791e60dae0` 与自测前一致，即零写入成立）；"
                "③ **沙箱自动清理**；④ **负测腿须区分「守卫拒绝」与「沙箱脚本报错」**（否则假绿）。"
                "**判定口径**：真实交付物上的负测**不因「事后还原」而免除**——"
                "但**已还原 ＋ 逐字节一致 ＋ 已补建沙箱自测器并实跑通过 ＝ 补救到位，不予返工**（本岗 07:45 裁定）。"
                "**Apply when**：任何需要试探守卫行为的负测（版本守卫／漂移守卫／清单守卫）。",
        "method": "真盘 SHA256 前后比对 ＋ 沙箱副本实跑 ＋ 沙箱清理；负测腿逐腿区分「守卫拒绝」与「脚本异常」",
        "source": "企划合规 2026-10-23 07:45（分镜导演 07:3x 主动披露 ＋ 本岗核销裁定）",
        "severity": "中（不产生错交付物，但测试窗口内真盘处于被改写状态，并发读盘者会读到伪造版本）",
    })
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj["decisions"]["S30_版本守卫负测沙箱化与跨交付物边界脚本归属"] = (
        "企划合规裁决（2026-10-23 07:45，配套 **" + q_id + "** ＋ **" + ops_id + "**）："
        "**① 守卫负测只在沙箱副本** —— 沙箱 ROOT 由 `__file__` 推导（只读写副本、真盘零写入）；"
        "负测前后打印真盘 SHA256 前缀并比对；沙箱自动清理；"
        "**负测腿须区分「守卫拒绝」与「沙箱脚本报错」**（否则假绿）。"
        "**② 真实交付物上的负测不因「事后还原」免除** —— 但**已还原 ＋ 逐字节一致 ＋ 已补建沙箱自测器并实跑通过 "
        "＝ 补救到位，不予返工**（分镜导演 07:3x 主动披露，本岗 07:45 裁定）。"
        "**③ 跨交付物边界脚本按两侧责任写** —— 一次运行写多份不同归属交付物的脚本（如 `apply_d15_d16_sync.py` "
        "同写 D15／D16）：或**拆分**，或**保留单脚本但两侧各自带版本守卫 ＋ 文件头按 S27 ② 写明两侧责任与同步义务**；"
        "**不写单一 owner、不代改他岗脚本**（§七·九）。"
        "**④ 交付说明与台账的「闸门数字」必须当场实跑回填** —— 与并行实例 OPS-18 同向、已互认。"
        "**Apply when**：任何守卫负测；任何跨交付物写盘脚本；任何台账闸门数字。"
    )
    prj["updated_at"] = stamp_full
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引（本岗章节内追加，锚点＝下一节标题之前 —— Q72） ----------
    idx_lines = idx.split("\n")
    idx_block = [
        "",
        f"#### 6. 分镜导演回执核销 ＋ U01-R33 投递（{stamp_hm}）",
        "",
        "| 项 | 本岗独立复核结论 |",
        "|---|---|",
        "| **S27 ③ 归属声明落地** | `scripts/shotintent_map_U02.mjs` 文件头实测**已改双向口径**"
        "（锚点侧＝分镜导演／原文侧＝台本编剧），原声明按 S11 **留痕作废未删**；MAP 29 条未动；"
        "覆盖轴 **U01 23/23、U02 29/29 exit 0**；Q64 判定「不适用」成立 → **OPS-16 升「已裁定·已落地」** |",
        "| **Q68 沙箱自测器** | 实跑 **受检 10 条／通过 10／失败 0／exit 0**；**真盘零写入实测成立**"
        "（D11 U02 `82631f35cb39742e`、D16 U02 `bde3f6791e60dae0` 与自测前一致）→ **核销通过** |",
        "| **分镜导演的主动披露** | 在真实 D11／D16 上伪造 v9.9 做负测 → **本岗裁定：不追究、不予返工**"
        "（已还原 ＋ 逐字节一致 ＋ 已补建沙箱自测器）；**但该行为本身立为新判据 " + q_id + "**"
        "（负测只在沙箱副本） |",
        "| **U02-R34** | 分镜导演侧 9 脚本归属对照**已收**（台本编剧 4／视觉设定 2／白模场景师 1／声音设计 2）；"
        "余 `build_D15_U02.py` 版本守卫 → **声音设计**；新发现 `apply_d15_d16_sync.py` **跨交付物边界**"
        "→ 本岗单独立项 **" + ops_id + "**（不属分镜导演，不代改） |",
        "| **U01-R33 投递** | `mavis session send` 直投分镜导演会话 `mvs_778c258f…`："
        "**status=accepted／mode=queued／position=1／ahead=0**；同封含核销回执＋派单本体＋warning 新值；"
        "**task_id 待通道恢复后补登记**（同 request_id 幂等，**不得重复投递**） |",
        "",
        f"> 本节追加遵守 **Q72**：锚点＝「下一节标题之前」，**不追加到文件末尾**。",
        "",
    ]
    idx_lines = insert_before_next_section(idx_lines, "### 十·五十八", "### 十·", idx_block,
                                          "索引 §十·五十八 追加")
    idx = "\n".join(idx_lines)

    # ---------- D. 交付说明（本岗章节内追加，Q72 锚点） ----------
    del_lines = deliv.split("\n")
    del_block = [
        "",
        f"### 一百零二.7 分镜导演回执核销 ＋ U01-R33 投递（{stamp_hm}）",
        "",
        "**① S27 ③ 核销通过** —— 共享脚本归属声明已落双向口径（原声明按 S11 留痕作废未删），"
        "MAP 未动，覆盖轴 U01 23/23／U02 29/29 exit 0，Q64 判定「不适用」成立 → **OPS-16 闭环**。",
        "**② Q68 沙箱自测器核销通过** —— 受检 10 条／通过 10／exit 0，**真盘零写入实测成立**（SHA256 前缀比对）。",
        "**③ 主动披露处理** —— 真实交付物上伪造 version 做负测：**不追究、不予返工**，"
        f"但立为新判据 **{q_id}**（负测只在沙箱副本）。",
        "**④ U02-R34 部分核销** —— 分镜导演侧已收；余声音设计侧；"
        f"`apply_d15_d16_sync.py` 跨交付物边界 → 新立 **{ops_id}**。",
        "**⑤ U01-R33 已投递** —— `mavis session send` → `mvs_778c258f…`，"
        "**accepted／queued／position=1**；含核销回执＋派单本体；**task_id 待通道恢复后补登记**。",
        "",
        "> 本节追加遵守 **Q72**：锚点＝「下一节标题之前」，**不追加到文件末尾**。",
        "",
    ]
    del_lines = insert_before_next_section(del_lines, "## 一百零二、", "## ", del_block,
                                          "交付说明 §一百零二 追加")
    deliv = "\n".join(del_lines)

    # ---------- E. 自检 ----------
    for k in (ops_id, q_id):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S30_版本守卫负测沙箱化与跨交付物边界脚本归属" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S30；不写盘。")
    # ⚠️ 边界必须**按行**定位 —— 字符串 find("## ") 会命中 "### " 内部（"### " 含 "## " 子串）
    def section_span(lines, my_header, section_prefix, probe):
        mine = [i for i, l in enumerate(lines) if l.startswith(my_header)]
        if len(mine) != 1:
            sys.exit(f"[ABORT] {my_header} 命中数 {len(mine)} ≠ 1；不写盘。")
        nxt = [i for i, l in enumerate(lines) if i > mine[0] and l.startswith(section_prefix)]
        seg = lines[mine[0]: nxt[0]] if nxt else lines[mine[0]:]
        if not any(probe in l for l in seg):
            sys.exit(f"[ABORT] 追加未落在本岗章节内（probe={probe}）；不写盘。")
        return True

    section_span(idx.split("\n"), "### 十·五十八", "### 十·", "#### 6. 分镜导演回执核销")
    section_span(deliv.split("\n"), "## 一百零二、", "## ", "### 一百零二.7 分镜导演回执核销")

    # ---------- F. 并发写盘竞态守卫 ----------
    for path, raw0, label in ((p18, d18_raw_orig, "shared/D18.json"),
                               (p_prj, prj_raw_orig, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 {ver}→{d18['version']}（OPS-16 升已落地／U02-R34 部分核销／U01-R33 投递留痕"
              f"／＋{ops_id} ＋{q_id}）；project.json ＋S30；"
              f"索引 §十·五十八 与 交付说明 §一百零二 各追加一段（Q72 锚点）")
        return

    bak = os.path.join(proj, "reports", "_bak_0745_patch_round7")
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
    print("[DONE] 分镜导演回执核销 ＋ U01-R33 投递留痕 ＋ 新判据/新条目落盘")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：＋S30；updated_at → {stamp_full}")
    print("   00_项目索引.md：§十·五十八 ＋ §6 核销段（Q72 锚点）")
    print("   99_交付说明.md：§一百零二 ＋ §一百零二.7 核销段（Q72 锚点）")


if __name__ == "__main__":
    main()
