#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
check_ledger_section15_pointers.py —— 台账 §十五 指针有效性核验（只读）

为什么需要这条轴（2026-10-23 13:2x–13:5x 实测背景）：
  企划合规 11:4x 在 `00_项目索引.md` §十·七十九「归属澄清」里写「故事架构 §十五 L562
  属指针错、归其自行归位」。但该指针错**本岗已于 2026-10-23 08:5x 自行归位**
  （台账 §104.24 登记，写后回读六项断言全过），企划合规**自己也已于 09:06 核销闭合**
  （D18 `U02-R37` status=已闭合 ＋ 索引 §十·六十七 标题「故事架构 §十五 指针已归位」）。
  ⇒ 11:4x 那句是**过期重述**：① 缺陷早已闭合；② 行号也已漂移（当时 L562 → 现盘 L563）。
  本脚本把「是否已归位」从「口头声明」变成**任何人都能一条命令复算的结论**，
  以终结同一处被反复重提（08:5x 派单 → 09:06 闭合 → 11:45 重提 → 13:4x 复发预防）。

判据（写在脚本头部，复算须按此读）：
  【P1 · 双 v 残留】台账 §十五 区间内 `vv[0-9]` 命中必须 **0 处**
        （历史缺陷形态：版本号处把 `v` 连写两遍，即双 v）。
  【P2 · 指针行单 v】§十五 内的**指针行本体**（表格首列恰为 `shared/D04.json` 且含
        `mtime` 的那一行）必须**唯一**，且版本串必须逐字为 `15,722 B｜**v1.2** |`（单 v）。
  【P3 · 真源一致】`shared/D04.json` 的 `version` repr 必须恰为 `'v1.2'`（单 v），
        字节数必须 15,722 —— 即台账指针与交付物真源逐项相等。
  【P4 · 行号指针有效】`shared/D04.json` **第 41 行**必须存在且其内容含
        catchphrase 值「我救下的人，谁也带不走。」；且 §十五 内必须有 `shared/D04.json:41`
        这一条 file:line 引用（否则 §十五 L574 的判据栏指向的是空处）。
  【P5 · 落地来源指针有效】台账 **§十三 的 13.2 子节标题**必须存在且含「R-024」与
        「OPS-05」；§十五 内必须引用了「§十三.2」。
  【P6 · 边界零改动】§十五 记录的两个交付物指针值（mtime 01:27:32、15,722 B）
        必须与 `shared/D04.json` 现盘一致 —— 证明「归位」只动台账文本、**没动交付物**。

⚠️ **两条写判据时的血泪约束（本脚本据此成型，勿删）**：
  ① **P2 必须锚定「指针行本体」，不能锚定「含某字符串的行」** ——
     本脚本首版用「含 `shared/D04.json` 且含 `mtime`」定位，结果本岗 §15.7 里
     **自述该指针的那几行也被命中**（4 行 ⇒ P2 假 FAIL）。判据必须锚在
     **内容标记**（表格首列恰为 `| \`shared/D04.json\` mtime |`）上，不是锚在运行时值上。
  ② **P1 刻意不豁免「引述上下文」** —— §十五 是被反复指认的一章，
     **保持该章 `vv<数字>` 命中恒为 0 才有诊断价值**（任何人 grep §十五 即可确认已归位）。
     代价：**在本章内引述历史缺陷形态时不得给出 `vv<数字>` 字面量**，改用
     「把 `v` 连写两遍（双 v）」这类文字描述（本岗 13:5x 已据此自修 3 处）。

已知局限（勿据以单独判缺陷）：
  - 本轴只核 §十五 这一章的指针；§三十／§一百二十四／§一百二十八 等他岗章节内的
    引述**不在本轴内**（那些是「如实抄录脚本实印输出」或「缺陷证据本体」，
    按 Q30 保留不需回改）。
  - P2/P4/P5 的**行号**随台账增长会漂移（现盘 §十五 指针行在 **L563**），
    本脚本**按内容定位、不按行号定位** —— 行号只作定位提示，不作判据。
  - `render/D04.md` 的 mtime 会随后续重渲染漂移（现盘 13:23:18，而 §十五 记录的是
    01:34:44 的时点快照，字节数 14,789 未变），**本轴不判 mtime 漂移**。
  - P4／P5 的「引用处数」在本岗追加澄清子节（§15.7）后会 **>1**（含自述引用），
    判据只要求「存在」，**引用处数不作缺陷依据**。

退出码：0 = 无 error；1 = 有 error。幂等、只读、不写盘。
空集恒真守卫：§十五 区间或 D04.json 任一取不到 → 直接 exit 1（不得判通过）。

用法：
  python3 scripts/check_ledger_section15_pointers.py --project 02_项目/双相潮主
  python3 scripts/check_ledger_section15_pointers.py --project 02_项目/双相潮主 --selftest
"""

import argparse
import json
import os
import re
import sys

LEDGER = "99_交付说明.md"
D04_REL = os.path.join("shared", "D04.json")
D04_VERSION = "v1.2"
D04_SIZE = 15722
D04_MTIME_STR = "01:27:32"
CATCHPHRASE = "我救下的人，谁也带不走。"
D04_LINE_NO = 41
# 指针行本体的内容标记（表格首列）—— 判据锚点，见文首约束①
PTR_ROW_PREFIX = "| `shared/D04.json` mtime |"


def find_section(lines, head_prefix):
    """返回 (start_idx, end_idx) —— 区间为 [start, end)，end 为下一个 '## ' 的下标。"""
    start = None
    for i, l in enumerate(lines):
        if l.startswith("## ") and l[len("## "):].startswith(head_prefix):
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def locate_ptr_rows(lines, s15, e15):
    """定位 §十五 内的指针行本体 —— 锚定表格首列（文首约束①）。"""
    return [(s15 + i + 1, l) for i, l in enumerate(lines[s15:e15])
            if l.strip().startswith(PTR_ROW_PREFIX)]


def run_judgments(ledger_text, d04_text, d04_bytes):
    """对给定文本执行 P1–P6；返回 [(id, 名称, ok, detail), ...]。文本全部走参数传入，
    以便 --selftest 做**内存态变异**负测（绝不落盘）。"""
    lines = ledger_text.split("\n")
    s15, e15 = find_section(lines, "十五、")
    s13, e13 = find_section(lines, "十三、")
    res = []

    if s15 is None:
        res.append(("P1", "双 v 残留", False, "台账 §十五 区间未找到（空集不得判通过）"))
        return res
    sec15 = lines[s15:e15]

    # P1 · 双 v 残留
    dvv = [(s15 + i + 1, l.strip()[:60]) for i, l in enumerate(sec15) if re.search(r"vv\d", l)]
    res.append(("P1", "双 v 残留", len(dvv) == 0,
                f"§十五(L{s15+1}–L{e15}) 内 `vv<数字>` 命中 {len(dvv)} 处" +
                ("" if not dvv else f" → {dvv[:3]}（本轴不豁免引述上下文，见文首约束②）")))

    # P2 · 指针行单 v
    rows = locate_ptr_rows(lines, s15, e15)
    if len(rows) != 1:
        res.append(("P2", "指针行单 v", False,
                    f"§十五 内指针行本体（首列 `{PTR_ROW_PREFIX}`）命中 {len(rows)} 处（应为唯一 1 处）"))
    else:
        ln, row = rows[0]
        want = f"15,722 B｜**{D04_VERSION}** |"
        ok = (want in row) and ("vv" not in row)
        res.append(("P2", "指针行单 v", ok,
                    f"L{ln} 版本串逐字核对：期望 `{want}` → " +
                    ("一致且无双 v" if ok else f"不一致（该行现为 `{row.strip()[:80]}`）")))

    # P3 · 真源一致
    try:
        d04 = json.loads(d04_text)
        ver = d04.get("version")
    except Exception as e:  # noqa: BLE001
        ver = f"<解析失败: {e}>"
    ver_repr = repr(ver)
    ok3 = (ver_repr == f"'{D04_VERSION}'") and (d04_bytes == D04_SIZE)
    res.append(("P3", "真源一致", ok3,
                f"D04.json version repr={ver_repr}（期望 '{D04_VERSION}' 单 v）；字节 {d04_bytes}（期望 {D04_SIZE}）"))

    # P4 · 行号指针有效
    d04_lines = d04_text.split("\n")
    idx = D04_LINE_NO - 1
    if idx >= len(d04_lines):
        res.append(("P4", "行号指针有效", False, f"D04.json 不足 {D04_LINE_NO} 行"))
    else:
        tgt = d04_lines[idx]
        ok4a = CATCHPHRASE in tgt and "catchphrase" in tgt
        ref = [(s15 + i + 1) for i, l in enumerate(sec15) if f"{D04_REL}:{D04_LINE_NO}" in l]
        ok4 = ok4a and len(ref) > 0
        res.append(("P4", "行号指针有效", ok4,
                    f"D04.json:{D04_LINE_NO} 现为 `{tgt.strip()[:60]}`（含 catchphrase 值：{ok4a}）；"
                    f"§十五 内该 file:line 引用 {len(ref)} 处 {ref}（含自述引用，**处数不作缺陷依据**）"))

    # P5 · 落地来源指针有效
    if s13 is None:
        res.append(("P5", "落地来源指针有效", False, "台账 §十三 区间未找到"))
    else:
        sub = [l for l in lines[s13:e13] if l.startswith("### ") and "13.2" in l]
        has_sub = len(sub) == 1
        has_kw = has_sub and ("R-024" in sub[0]) and ("OPS-05" in sub[0])
        cited = [(s15 + i + 1) for i, l in enumerate(sec15) if "§十三.2" in l]
        ok5 = has_kw and len(cited) > 0
        res.append(("P5", "落地来源指针有效", ok5,
                    f"§13.2 子节标题 {len(sub)} 处" +
                    (f"（`{sub[0].strip()[:70]}`）" if sub else "") +
                    f"；§十五 内「§十三.2」引用 {len(cited)} 处 {cited}（含自述引用，**处数不作缺陷依据**）"))

    # P6 · 边界零改动
    ok6 = (f"{D04_SIZE:,} B" in " ".join(sec15)) and (D04_MTIME_STR in " ".join(sec15))
    res.append(("P6", "边界零改动", ok6,
                f"§十五 记录的交付物指针值（mtime {D04_MTIME_STR}／{D04_SIZE:,} B）与现盘一致 → "
                "归位只动台账文本，未动交付物"))

    return res


def _mutate_ptr_row(ledger_text, old_sub, new_sub):
    """只对**指针行本体**做定点替换（不碰自述行）。找不到唯一指针行则返回 None。"""
    lines = ledger_text.split("\n")
    s15, e15 = find_section(lines, "十五、")
    if s15 is None:
        return None
    rows = locate_ptr_rows(lines, s15, e15)
    if len(rows) != 1:
        return None
    ln, row = rows[0]
    if old_sub not in row:
        return None
    out = list(lines)
    out[ln - 1] = out[ln - 1].replace(old_sub, new_sub, 1)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--selftest", action="store_true",
                    help="做内存态变异负测，证明判据非恒真（不写盘）")
    args = ap.parse_args()

    proj = args.project
    ledger_path = os.path.join(proj, LEDGER)
    d04_path = os.path.join(proj, D04_REL)
    for p in (ledger_path, d04_path):
        if not os.path.isfile(p):
            print(f"[FATAL] 缺文件：{p}", file=sys.stderr)
            return 1

    with open(ledger_path, encoding="utf-8") as f:
        ledger_text = f.read()
    with open(d04_path, encoding="utf-8") as f:
        d04_text = f.read()
    d04_bytes = os.path.getsize(d04_path)

    if args.selftest:
        base = dict((i, ok) for i, _, ok, _ in run_judgments(ledger_text, d04_text, d04_bytes))
        if base.get("P2") is not True:
            print(f"[SELFTEST FAIL] 基线 P2 非 PASS（P2={base.get('P2')}）⇒ 判据本体已失效，先修判据")
            return 1
        # 负测1：向**指针行本体**注入双 v → P1/P2 必须转 FAIL
        mut1 = _mutate_ptr_row(ledger_text, f"**{D04_VERSION}** |", f"**vv{D04_VERSION[1:]}** |")
        if mut1 is None:
            print("[SELFTEST FAIL] 负测1 注入失败：未唯一定位指针行本体")
            return 1
        m1 = dict((i, ok) for i, _, ok, _ in run_judgments(mut1, d04_text, d04_bytes))
        if m1.get("P1") is not False or m1.get("P2") is not False:
            print(f"[SELFTEST FAIL] 负测1 未生效：P1={m1.get('P1')} P2={m1.get('P2')}（应双双 False）")
            return 1
        # 负测2：抹掉 §十三.2 的 13.2 子节标题 → P5 必须转 FAIL
        mut2 = ledger_text.replace("### 13.2 R-024", "### 13.9 XXXX", 1)
        if mut2 == ledger_text:
            print("[SELFTEST FAIL] 负测2 注入失败：未找到 §13.2 标题")
            return 1
        m2 = dict((i, ok) for i, _, ok, _ in run_judgments(mut2, d04_text, d04_bytes))
        if m2.get("P5") is not False:
            print(f"[SELFTEST FAIL] 负测2 未生效：P5={m2.get('P5')}（应 False）")
            return 1
        # 负测3：把指针行版本串改成另一版本号 → P2 必须转 FAIL（证明 P2 真在校验版本串）
        mut3 = _mutate_ptr_row(ledger_text, f"**{D04_VERSION}** |", "**v9.9** |")
        if mut3 is None:
            print("[SELFTEST FAIL] 负测3 注入失败：未唯一定位指针行本体")
            return 1
        m3 = dict((i, ok) for i, _, ok, _ in run_judgments(mut3, d04_text, d04_bytes))
        if m3.get("P2") is not False:
            print(f"[SELFTEST FAIL] 负测3 未生效：P2={m3.get('P2')}（应 False）")
            return 1
        print("[SELFTEST PASS] 负测1（注入双 v → P1/P2 转失败）、负测2（抹 §13.2 标题 → P5 转失败）、"
              "负测3（改版本号 → P2 转失败）均实跑生效 ⇒ 判据非恒真")
        return 0

    res = run_judgments(ledger_text, d04_text, d04_bytes)
    print("=" * 78)
    print("台账 §十五 指针有效性核验（只读）")
    print("=" * 78)
    err = 0
    for pid, name, ok, detail in res:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            err += 1
        print(f"[{flag}] {pid} · {name} —— {detail}")
    print("-" * 78)
    print(f"受检判据 {len(res)} 条｜error {err}")
    if err == 0:
        print("结论：§十五 指针已归位且与交付物真源逐项一致（无残留指针错）")
    else:
        print("结论：§十五 仍有指针错，见上列 FAIL 项")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
