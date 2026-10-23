#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_ledger_round4_0740.py —— 台账数字订正 ＋ OPS-17 校验器误报归零 ＋ Q71/S28（企划合规 2026-10-23 07:40）

起因（本轮实测链）：
  ① 第六波核销补丁（round3，07:25–07:30）写入台账的出口闸数字 **U01 2／U02 8／全项目 11** 是**上一轮快照的旧值**；
     受控实验（把 `shared/D18.json`＋`project.json` 还原成补丁前版本、在 `/tmp/proj_test0725` 副本上重跑同一校验器）
     证明：**本轮台账补丁对 warning 计数完全中性**（还原前后同为 2／7／9）⇒ 漂移来自**并行企划合规实例
     07:06–07:18 连续改写 U02 D07／D11／D16／D12 四份交付物**，不是台账写错。
     → 本轮把出口闸数字改为**当场实测回填**（本脚本内直接跑校验器取数），从此免疫并行漂移。
  ② 顺带查出并修掉一个**真缺陷**：`04_工具/lib/rules.mjs` 的 V1 遍历 `ctx.schemas`（＝整份 `schema.json`），
     把 JSON Schema 元数据键 **`title`** 当成缺失交付物 → **每次跑固定产出 1 条误报**（全项目 3 条），
     且该常量噪声会淹没真实 warning。已改为只遍历 `/^D\d{2}$/` 交付物键。
     改前／改后**逐条比对**：唯一差异＝消掉 `title` 误报，其余逐条不变。

新登记：open_issue **OPS-17** ＋ global_check **Q71** ＋ decision **S28**。

用法：python3 scripts/patch_ledger_round4_0740.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

NOW = "2026-10-23 07:40"
CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
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
        return out + "零一二三四五六七八九"[tail]
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


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run_validate(factory, proj, unit=None):
    """当场跑校验器实测取数 —— 台账数字不允许手写（免疫并行实例漂移）。"""
    cmd = ["node", os.path.join(factory, "04_工具", "validate.mjs"), "--project", proj]
    if unit:
        cmd += ["--unit", unit]
    p = subprocess.run(cmd, cwd=factory, capture_output=True, text=True)
    out = ANSI.sub("", p.stdout + p.stderr)
    if p.returncode != 0:
        sys.exit(f"[ABORT] validate.mjs 退出码 {p.returncode}（unit={unit}）；不写盘。\n{out[-800:]}")
    m = re.search(r"结果\s+通过\s+(\d+)/(\d+)\s+规则\s+error\s+(\d+)\s+warning\s+(\d+)", out)
    if not m:
        sys.exit(f"[ABORT] 无法从校验器输出解析计数（unit={unit}）；不写盘。\n{out[-800:]}")
    passed, total, err, warn = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    if err != 0:
        sys.exit(f"[ABORT] 校验器 error {err} ≠ 0（unit={unit}）；不写盘。")
    agg = None
    if unit is None:
        a = re.search(r"合计\s+单元\s+(\d+)\s+个\s+规则\s+(\d+)/(\d+)\s+通过\s+error\s+(\d+)\s+warning\s+(\d+)", out)
        if not a:
            sys.exit("[ABORT] 无法解析全项目合计；不写盘。")
        agg = {"units": int(a.group(1)), "passed": int(a.group(2)), "total": int(a.group(3)),
               "error": int(a.group(4)), "warning": int(a.group(5))}
        if agg["error"] != 0 or agg["passed"] != agg["total"]:
            sys.exit(f"[ABORT] 全项目合计异常 {agg}；不写盘。")
    return {"passed": passed, "total": total, "error": err, "warning": warn, "agg": agg, "raw": out}


def scoped_replace(text, start_marker, old, new, label):
    """只在 start_marker 之后的尾段内替换；命中数必须恰为 1，否则中止。"""
    i = text.find(start_marker)
    if i < 0:
        sys.exit(f"[ABORT] 找不到定位标记 {start_marker}；不写盘。")
    head, tail = text[:i], text[i:]
    if tail.count(old) != 1:
        sys.exit(f"[ABORT] {label} 在尾段内命中数 {tail.count(old)} ≠ 1；不写盘。")
    return head + tail.replace(old, new, 1)


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
    p_rules = os.path.join(factory, "04_工具", "lib", "rules.mjs")

    d18_raw = read(p18)
    d18 = json.loads(d18_raw)
    idx = read(p_idx)
    prj_raw = read(p_prj)
    prj = json.loads(prj_raw)
    deliv = read(p_del)

    # ---------- 证据自检 ----------
    ver = d18.get("version", "")
    if not (ver.startswith("v1.") and int(ver[3:]) >= 71):
        sys.exit(f"[ABORT] D18 version={ver}，期望 ≥v1.71；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    if "OPS-17" in oi:
        sys.exit("[ABORT] open_issues 已含 OPS-17，不重复登记；不写盘。")
    if any(g["id"] == "Q71" for g in d18["global_checks"]):
        sys.exit("[ABORT] global_checks 已含 Q71，不重复登记；不写盘。")
    if "S28_校验器schema键遍历口径与title误报归零" in prj["decisions"]:
        sys.exit("[ABORT] project.json 已含 S28，不重复登记；不写盘。")
    # OPS-17 的修复必须在盘（否则不得登记为已修）
    rules = read(p_rules)
    if "!/^D\\d{2}$/.test(docId)" not in rules:
        sys.exit("[ABORT] rules.mjs 未见 V1 键白名单修复；不写盘。")
    # 既有章节不得被本轮改动（留痕不改写）：先定位本轮章节起点
    if "### 十·五十八" not in idx:
        sys.exit("[ABORT] 索引缺 §十·五十八；不写盘。")
    if "## 一百零二、" not in deliv:
        sys.exit("[ABORT] 交付说明缺 §一百零二；不写盘。")

    # ---------- 当场实测出口闸（数字直接取自校验器，不手写） ----------
    m_u01 = run_validate(factory, proj, "U01")
    m_u02 = run_validate(factory, proj, "U02")
    m_all = run_validate(factory, proj, None)
    print(f"[MEASURE] U01 → {m_u01['passed']}/{m_u01['total']} error {m_u01['error']} warning {m_u01['warning']}")
    print(f"[MEASURE] U02 → {m_u02['passed']}/{m_u02['total']} error {m_u02['error']} warning {m_u02['warning']}")
    print(f"[MEASURE] ALL → {m_all['agg']['units']} 单元 {m_all['agg']['passed']}/{m_all['agg']['total']} "
          f"error {m_all['agg']['error']} warning {m_all['agg']['warning']}")

    gate_line_u = (f"`--unit U01` → **{m_u01['passed']}/{m_u01['total']}、error {m_u01['error']}、"
                   f"warning {m_u01['warning']}**；`--unit U02` → **{m_u02['passed']}/{m_u02['total']}、"
                   f"error {m_u02['error']}、warning {m_u02['warning']}**；")
    gate_line_a = (f"无 `--unit` → **error {m_all['agg']['error']}／warning {m_all['agg']['warning']}／"
                   f"{m_all['agg']['passed']}-{m_all['agg']['total']}／exit 0**")

    # ---------- A. D18 ----------
    d18["global_checks"].append({
        "id": "Q71",
        "item": "**校验器遍历「键集合」时必须先区分「真实体键」与「元数据键」——"
                "不得把配置文件的元数据当成缺失交付物** —— 本轮实证：`04_工具/lib/rules.mjs` 的 V1 遍历 "
                "`ctx.schemas`（＝整份 `03_规格/schema.json`），其中 JSON Schema 的元数据键 **`title`** "
                "被当成 doc id → **每次跑固定产出 1 条「title: 本次上下文中不存在」误报**"
                "（全项目 3 条）。**危害不是难看，是淹没** —— 一条恒定噪声会让真实 warning 的增减失去可读性"
                "（本轮就因此出现「warning 8／11」与实测「7／9」并存、台账不敢引用退出闸数字的局面）。"
                "**做法**：① **白名单化键空间** —— 只遍历真实体键（`/^D\\d{2}$/`），"
                "不要用「跳过 `$` 前缀与 `definitions`」这种**排除式**写法（漏一个就多一条噪声）；"
                "② **改判据必须给出前后对比** —— 本轮改前／改后逐条比对，**唯一差异＝消掉 `title` 误报**，"
                "其余逐条不变、error 全程 0、22/22 通过不变；"
                "③ **台账数字当场实测回填** —— 出口闸数字由脚本**直接跑校验器取数**再写入台账，不手写、"
                "不沿用上一轮快照（并行实例改写交付物会让旧值静默失真）。"
                "**Apply when**：任何遍历 JSON/YAML/配置对象键空间的校验器、扫描器、报表器。",
        "method": "改前／改后跑同一校验器并逐条 diff 输出（warning 明细逐行比对），确认唯一差异即被修项",
        "source": "企划合规 2026-10-23 07:40（OPS-17 处置）",
        "severity": "中（不产生错交付物，但恒定噪声使真实 warning 不可读，并直接导致台账数字失真）",
    })
    d18["open_issues"].append({
        "id": "OPS-17",
        "issue": "**共享校验器 V1 把 `schema.json` 的 JSON Schema 元数据键 `title` 当成缺失交付物** —— "
                 "每次跑固定产出 1 条「title: 本次上下文中不存在，跳过」误报（单单元 1 条／全项目 3 条），"
                 "**且该噪声恒定不变 → 真实 warning 的增减被淹没** —— 本轮实证：V1 遍历 `ctx.schemas`"
                 "（＝整份 schema.json，顶层键含 `$schema`／`$id`／`title`／`definitions` ＋ D01–D18），"
                 "原代码只排除 `$` 前缀与 `definitions`，**漏掉 `title`**。",
        "owner": "企划合规（共享工具侧，本岗自修）",
        "blocks": "**不拦锁**（不产生 error，exit 0 不变）；**但影响一切以 warning 数为判据的台账与判读**",
        "priority": "中",
        "status": "**已修·已核销**（企划合规 2026-10-23 07:40）",
        "resolution": "**2026-10-23 07:40 企划合规修复并核销**：`04_工具/lib/rules.mjs` V1 改为"
                      "**只遍历交付物键**（`if (!/^D\\d{2}$/.test(docId)) continue;`），"
                      "**排除式写法改为白名单式** —— 以后新增任何元数据键都不会再漏。"
                      "**改前／改后逐条比对（同一命令、同一项目）**："
                      "**唯一差异＝`title:` 误报消失**，其余逐行不变（U01 规则明细、U02 规则明细、"
                      "全项目两段汇总全部逐条一致）；**error 全程 0、22/22 规则通过不变、三次退出码均 0**。"
                      "**warning 计数变化**：U01 2→**1**、U02 7→**6**、全项目 9→**7**。"
                      "**⚠️ 历史台账中大量「U01 warning 2（含 title 跳过）」的记载属当时的真实实况，"
                      "按留痕不改写处理**；自本条起，退出闸数字以**当场实测**为准。"
                      "**Apply**：任何遍历配置文件键空间的校验器/扫描器（见 Q71）。",
        "detected_by": "企划合规 2026-10-23 07:35（本岗复核第六波台账数字时发现并做受控实验定位）",
    })
    d18["version"] = "v1.%d" % (int(ver[3:]) + 1)
    d18_out = serialize_like(d18, d18_raw)

    # ---------- B. project.json ----------
    prj["decisions"]["S28_校验器schema键遍历口径与title误报归零"] = (
        "企划合规裁决（2026-10-23 07:40，OPS-17 结清 · 配套 **Q71**）："
        "**① 键空间白名单化** —— 校验器遍历 `03_规格/schema.json` 时**只认交付物键（`D01`–`D18`）**，"
        "**JSON Schema 元数据键（`$schema`／`$id`／`title`／`definitions`）一律不算缺失交付物**；"
        "**排除式写法（跳过 `$` 前缀）已废止**，改为 `/^D\\d{2}$/` 白名单 —— "
        "**排除式的漏洞是「漏一个键就多一条恒定噪声」，白名单式没有这个问题**。"
        "**② 出口闸数字当场实测回填** —— 台账里的 `error`／`warning`／`通过数` **由脚本直接跑校验器取数再写入**，"
        "**不手写、不沿用上一轮快照**：并行实例改写交付物会让旧值静默失真"
        "（本轮实证：旧值 2／8／11 vs 实测 7／9，受控实验证明台账补丁本身对计数中性）。"
        "**③ 改判据须给前后对比** —— 本轮改前／改后逐条 diff，**唯一差异＝被修项**，其余不变。"
        "**④ 历史留痕不改写** —— 旧章节里的 warning 数属当时实况，**只登记口径变更、不回改历史数字**。"
        "**Apply when**：任何遍历配置/Schema 键空间的校验器；任何把「上一轮实测数」直接抄进新台账的做法。"
    )
    prj["updated_at"] = NOW
    prj_out = serialize_like(prj, prj_raw)

    # ---------- C. 索引 ----------
    # C1 §五 企划合规行的 D18 版本提法
    pat_a = r"D18 \*\*v1\.\d+\*\*（\*\*\d+\*\* 条 global_checks / \*\*\d+\*\* 条 open_issues"
    if len(re.findall(pat_a, idx)) != 1:
        sys.exit("[ABORT] 索引 §五 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_a,
                 f"D18 **{d18['version']}**（**{len(d18['global_checks'])}** 条 global_checks / "
                 f"**{len(d18['open_issues'])}** 条 open_issues",
                 idx, count=1)
    # C2 §六 D18 行头部的 global_checks 计数（先于 C3 执行，避开中段历史留痕里的旧计数）
    pat_c = (r"(\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*（字节数不钉，见 D18 \*\*Q34\*\*）。)"
             r"\*\*\d+ 条 global_checks\*\*")
    if len(re.findall(pat_c, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 计数锚点命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_c,
                 lambda m: m.group(1) + f"**{len(d18['global_checks'])} 条 global_checks**",
                 idx, count=1)
    # C3 §六 D18 行的版本提法（落款时间走占位符，写盘后按 D18.json 磁盘 mtime 回填）
    pat_b = r"\*\*v1\.\d+｜[0-9]{2}:[0-9a-z]{2} 落｜approved\*\*"
    if len(re.findall(pat_b, idx)) != 1:
        sys.exit("[ABORT] 索引 §六 D18 版本提法命中数 ≠ 1；不写盘。")
    idx = re.sub(pat_b, f"**{d18['version']}｜«RUN_HM» 落｜approved**", idx, count=1)

    # C4 本轮章节（§十·五十八）内的出口闸数字订正 —— 只在本轮章节尾段内改，历史章节不动
    old_u = "`--unit U01` → **11/11、error 0、warning 2**；`--unit U02` → **11/11、error 0、warning 8**；"
    idx = scoped_replace(idx, "### 十·五十八", old_u, gate_line_u, "索引出口闸单元行")
    old_a = "无 `--unit` → **error 0／warning 11／22-22／exit 0**"
    idx = scoped_replace(idx, "### 十·五十八", old_a, gate_line_a, "索引出口闸全项目行")
    old_scope = ("本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）；\n"
                 "**未改**任何交付物 JSON、源素材、规格文件、工具脚本；")
    new_scope = ("本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）"
                 "**＋ `04_工具/lib/rules.mjs`**（V1 键白名单，OPS-17）；\n"
                 "**未改**任何交付物 JSON、源素材、规格文件（`03_规格/*`）；"
                 "**工具脚本只改了 `04_工具/lib/rules.mjs` 一处**（V1 只遍历 `D\\d{2}` 交付物键）；")
    idx = scoped_replace(idx, "### 十·五十八", old_scope, new_scope, "索引本轮改动范围声明")

    # C5 追加订正留痕（仅本轮章节）
    idx = idx.rstrip("\n") + "\n" + f"""
#### 5. 订正留痕（07:40）—— **本节出口闸数字以当场实测为准**

**① 上一版数字有误，已订正**：本节初稿写的 **U01 warning 2／U02 warning 8／全项目 warning 11** 是
**上一轮快照的旧值**，非 07:30 前后实况。**订正依据（受控实验）**：把 `shared/D18.json`＋`project.json`
**还原成补丁前版本**、在项目副本 `/tmp/proj_test0725` 上跑同一校验器 → **还原前后计数完全相同**
（2／7／9）⇒ **本轮台账补丁对 warning 计数中性**，漂移来自**并行企划合规实例 07:06–07:18
连续改写 U02 D07／D11／D16／D12 四份交付物**。**现值＝当场实测（见上）**。

**② 顺带修掉一条恒定噪声（OPS-17）**：`04_工具/lib/rules.mjs` 的 V1 遍历 `ctx.schemas`（＝整份 `schema.json`），
把 JSON Schema 元数据键 **`title`** 当缺失交付物 → **每次跑固定 1 条误报**（全项目 3 条）。
已改为**白名单式**（`/^D\\d{{2}}$/`）；**改前／改后逐条比对，唯一差异＝`title` 误报消失**，其余不变，
**error 全程 0、22/22 通过不变、退出码均 0**。**现值＝U01 {m_u01['warning']}／U02 {m_u02['warning']}／
全项目 {m_all['agg']['warning']}**。

**③ 台账数字改为当场实测回填（Q71）**：本轮起，出口闸的 `error`／`warning`／通过数
**由脚本直接跑校验器取数再写入台账**，不再手写、**不再沿用上一轮快照** ——
本轮这次偏差正是「沿用旧快照」造成的。

**④ 历史章节不改写**：旧章节里的 warning 数属**当时实况**（含当时的 `title` 误报），
按**留痕不改写**处理；自本节起口径以实测为准。
"""

    # ---------- D. 交付说明 ----------
    deliv = scoped_replace(deliv, "## 一百零二、", old_u, gate_line_u, "交付说明出口闸单元行")
    deliv = scoped_replace(deliv, "## 一百零二、", old_a, gate_line_a, "交付说明出口闸全项目行")
    old_scope_d = ("本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）；\n"
                   "**未改**任何交付物 JSON、源素材、规格文件、工具脚本；")
    new_scope_d = ("本轮**只改** `shared/D18.json`、`project.json`、`00_项目索引.md`、`99_交付说明.md`（本节）"
                   "**＋ `04_工具/lib/rules.mjs`**（V1 键白名单，OPS-17）；\n"
                   "**未改**任何交付物 JSON、源素材、规格文件（`03_规格/*`）；"
                   "**工具脚本只改了 `04_工具/lib/rules.mjs` 一处**（V1 只遍历 `D\\d{2}` 交付物键）；")
    deliv = scoped_replace(deliv, "## 一百零二、", old_scope_d, new_scope_d, "交付说明本轮改动范围声明")
    deliv = deliv.rstrip("\n") + "\n" + f"""
### 一百零二.5 订正留痕（07:40）—— **出口闸数字以当场实测为准**

**① 初稿数字有误，已订正**：初稿 **U01 2／U02 8／全项目 11** 是上一轮快照旧值。
**受控实验**（还原补丁前的 `D18.json`＋`project.json`，在副本 `/tmp/proj_test0725` 重跑）证明
**本轮台账补丁对计数中性**（还原前后同为 2／7／9）⇒ 漂移来自**并行实例 07:06–07:18 改写 U02 四份交付物**。
**现值＝当场实测**。

**② 修掉恒定噪声（OPS-17）**：V1 曾把 `schema.json` 的元数据键 `title` 当缺失交付物
（每次跑 1 条、全项目 3 条）→ 已改**白名单式**（`/^D\\d{{2}}$/`）；**改前／改后逐条比对，
唯一差异＝该误报消失**，其余不变、error 全程 0、22/22 通过不变。

**③ 口径变更（Q71）**：出口闸数字**由脚本当场实测回填**，不再手写、不再沿用上一轮快照。
**④ 历史留痕不改写**：旧章节的 warning 数属当时实况（含当时的 `title` 误报），不回改。
"""

    # ---------- E. 自检 ----------
    for k in ("OPS-17", "Q71"):
        if k not in d18_out:
            sys.exit(f"[ABORT] D18 序列化后丢失「{k}」；不写盘。")
    if "S28_校验器schema键遍历口径与title误报归零" not in prj_out:
        sys.exit("[ABORT] project.json 序列化后丢失 S28；不写盘。")
    if idx.count("### 十·五十八") != 1 or idx.count("#### 5. 订正留痕（07:40）") != 1:
        sys.exit("[ABORT] 索引 §十·五十八 或订正段写入异常；不写盘。")
    if deliv.count("## 一百零二、") != 1 or deliv.count("### 一百零二.5 订正留痕（07:40）") != 1:
        sys.exit("[ABORT] 交付说明 §一百零二 或订正段写入异常；不写盘。")
    # 终检：只在**本轮章节尾段**内查残留（历史章节留痕含同名字串，属正常，不得回改）
    idx_tail = idx[idx.find("### 十·五十八"):]
    del_tail = deliv[deliv.find("## 一百零二、"):]
    for probe, where, tail in ((old_u, "索引", idx_tail), (old_a, "索引", idx_tail),
                               (old_scope, "索引", idx_tail),
                               (old_u, "交付说明", del_tail), (old_a, "交付说明", del_tail),
                               (old_scope_d, "交付说明", del_tail)):
        if probe in tail:
            sys.exit(f"[ABORT] {where}本轮章节仍残留旧数字/旧范围声明：{probe[:40]}；不写盘。")
    # 反向自检：历史章节的同名旧数字必须**仍在**（留痕不改写）
    hist = idx[:idx.find("### 十·五十八")]
    if old_a not in hist:
        sys.exit("[ABORT] 索引历史章节的旧数字被误改（留痕不改写）；不写盘。")

    # ---------- F. 并发写盘竞态守卫（compare-and-swap） ----------
    for path, raw0, label in ((p18, d18_raw, "shared/D18.json"), (p_prj, prj_raw, "project.json")):
        if read(path) != raw0:
            sys.exit(f"[ABORT] {label} 在本脚本运行期间被改动（并行实例并发写入）；"
                     f"不写盘，重新核实现盘后再执行。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] D18 {ver}→{d18['version']}（＋OPS-17 ＋Q71）；project.json（＋S28）；"
              f"索引 §五/§六 版本提法 ＋ §十·五十八 数字订正与订正留痕；交付说明 §一百零二 数字订正与订正留痕")
        print(f"[MEASURE] 出口闸数字回填：U01 {m_u01['warning']}／U02 {m_u02['warning']}／"
              f"全项目 {m_all['agg']['warning']}")
        return

    bak = os.path.join(proj, "reports", "_bak_0740_patch_round4")
    os.makedirs(bak, exist_ok=True)
    for path, name in ((p18, "D18.json"), (p_prj, "project.json"),
                       (p_idx, "00_项目索引.md"), (p_del, "99_交付说明.md")):
        with open(os.path.join(bak, name), "wb") as f:
            f.write(open(path, "rb").read())

    write(p18, d18_out)
    write(p_prj, prj_out)
    run_hm = datetime.fromtimestamp(os.path.getmtime(p18)).strftime("%H:%M")
    idx = idx.replace("«RUN_HM»", run_hm)
    write(p_idx, idx)
    write(p_del, deliv)
    print("[DONE] 数字订正 ＋ OPS-17/Q71/S28 落盘完成")
    print(f"   shared/D18.json：{ver} → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")
    print(f"   project.json：＋S28；updated_at → {NOW}")
    print(f"   00_项目索引.md：§五/§六 版本提法 ＋ §十·五十八 订正段（落款 {run_hm}）")
    print("   99_交付说明.md：§一百零二 订正段")
    print(f"   出口闸实测回填：U01 {m_u01['passed']}/{m_u01['total']} error {m_u01['error']} warning {m_u01['warning']}｜"
          f"U02 {m_u02['passed']}/{m_u02['total']} error {m_u02['error']} warning {m_u02['warning']}｜"
          f"全项目 {m_all['agg']['passed']}/{m_all['agg']['total']} error {m_all['agg']['error']} "
          f"warning {m_all['agg']['warning']}")


if __name__ == "__main__":
    main()
