#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加器：写 §{动态取号}（分镜导演 · U01-R33 判据清单守卫「注释盲区」修复 Q74）。

【本节记什么】
  本岗 08:1x 独立复核 U01 侧两个只读对账脚本的判据清单守卫（U01-R33 承接项）时，
  发现并修复了一个**真实缺陷**：守卫用全文 token 计数核对「清单条数 == 实际断言点数」，
  而**注释里的 token 也被计入** ⇒ 把一条判据注释掉不改变计数 ⇒ 守卫继续报
  「清单 12 条 ＝ 实际断言点 12 处」并放行，而该判据**实际已死**。

【本追加器的规格（沿用本岗 §117 追加器，不重复实现）】
  1. **动态取号**：扫全文件台账章标题（阿拉伯／中文两式都解析），取 max + 1；
  2. **章号形式**：阿拉伯数字（Q71／OPS-19；历史章节原文一字不改）；
  3. **并发护栏**：落盘前复检末章号与文件尾部；取号后末章变化 → 放弃写盘；
  4. **写后自检**：前段逐字节一致｜本节出现 1 次｜本节位于文件末章；
  5. **幂等**：标题已存在则 [NO-OP]。

用法：python3 scripts/append_ledger_119_mavis.py [--project .]
"""
import argparse
import importlib.util
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# 复用 §117 追加器的取号与护栏函数（避免重复实现踩同一个坑）
_spec = importlib.util.spec_from_file_location(
    "ledger117_helpers", os.path.join(HERE, "append_ledger_117_mavis.py"))
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)

max_heading_num = _h.max_heading_num
LEDGER_MIN = _h.LEDGER_MIN

EVENT_TITLE = "判据清单守卫「注释盲区」修复"


def build_section(num: int) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""

## {num}、分镜导演：**U01-R33 判据清单守卫「注释盲区」修复（Q74）** ＋ **Q67 敏感度检验实证** ＋ **自指陷阱两处**（分镜导演，{ts}）

> 本节登记本岗本轮一项**守卫缺陷的独立复核与修复**。定位：U01 侧两个只读对账脚本的
> 「判据清单 ＋ 清单守卫」（U01-R33 承接项，本岗 07:51 已落，见 §112.1）。
> 本岗本轮**未改动任何交付物 JSON**，只改了这两个**本岗产出**的只读对账脚本的
> **守卫计数实现**（判据内容、时码、口径一字未改）。

### {num}.1 缺陷发现：守卫的「全文 token 计数」有注释盲区

守卫原实现（两个脚本逐字一致）：

```js
const src = readFileSync(fileURLToPath(import.meta.url), "utf8");
const token = "ch" + "k(";
const nCall = src.split(token).length - 1;   // ← 全文计数，注释里的 token 也算进去
```

⇒ **把一条判据注释掉**（`// chk(...)`）**不改变 token 计数** ⇒ 守卫继续报
「清单 12 条 ＝ 实际断言点 12 处」并放行，而**该判据实际已死**。
这正是守卫自己声称要防的「判据被无声删改」（Q56③）——**守卫生效性存在缺口**。

### {num}.2 性质界定（重要，勿夸大）：**不是假绿，是可审计性缺口**

本岗逐行读了守卫与 exit 逻辑后确认：

- `hardFail` **独立于** `assertFails` 计算：
  `hardFail = voRep.over.length + voRep.crossed.length + subRep.over.length + ... + sfxCross.length`
- ⇒ **越窗／跨切／不同步类违规，即便其对应断言被注释，仍会被 `hardFail` 抓到并 exit 1**。

**结论：本缺陷不构成放行缺口（无假绿）**，性质是**可审计性缺口** ——
守卫**谎报**「12 条断言点在跑」，实际在跑 11 条；清单中该条判据已死而报告里看不出来。
**本岗明确不把它夸大成「静默放行真错误」。**

### {num}.3 Q67 敏感度检验：变更前后两版跑同一判据，结论必须不同

**本岗自建沙箱实测**（不采信转述；自测器与被测脚本分离）：

| 破坏方式 | 修复前守卫反应 | 修复前真实违规是否仍被拦 | 修复后守卫反应 |
|---|---|---|---|
| 删除整行 | ✅ exit 2 中止 | — | ✅ exit 2 中止 |
| **注释掉该行** | ❌ **未察觉**（仍报 12 ＝ 12） | ✅ 仍被 hardFail 抓到（exit 1） | ✅ **exit 2 中止** |
| **块注释包裹该行** | ❌ **未察觉**（同样漏） | ✅ 同上 | ✅ **exit 2 中止** |
| 新增一条 | ✅ exit 2 中止 | — | ✅ exit 2 中止 |

⇒ 修复后**四种破坏方式一律 exit 2 中止**，stderr 出现守卫拒绝特征串
「❌ 中止：判据清单 12 条 ≠ 实际断言点 11 处」且**无 JS 栈回溯**
（严格区分「守卫拒绝」与「沙箱脚本报错」，Q73）。

### {num}.4 修法：计数前剔除注释（只动守卫计数，不动判据）

- ① 去掉块注释 `/* ... */`（保留换行，维持行结构）；
- ② 去掉行注释 `// ...`（只截到该行第一个 `//` 之前）；
- 计数仍用 `"ch" + "k("` 拼接 ⇒ 守卫函数自身不被数进去（原有性质保持）。

**安全前提（已实测）**：两脚本内**无字符串字面含行注释分隔符**（仅文件头一处块注释），
故按行截断安全；两脚本守卫锚点块**逐字一致** ⇒ 同一补丁可复用。

### {num}.5 ⚠️ 补丁自身的两处**自指陷阱**（本岗实测踩过，已在脚本内留痕）

**陷阱①：注入的正则字面自指** —— 若把剔除块注释的正则以**字面块注释起始符**写进被注入的源码，
该正则**自己会被剔除动作吃掉**（自指）⇒ 注入块整段消失、断言点计数归 0。
**解法**：分隔符用 `String.fromCharCode` 构造，源码里不出现字面块注释起始符。

**陷阱②：`RegExp` 构造串不自动转义元字符** —— 用 charCode 构造出的 `/*` 直接进正则，
会被解释成「零个或多个 `/`」，后面再跟 `*` ⇒ JS 抛 `Invalid regular expression: Nothing to repeat`。
**解法**：构造后对 `*` 做转义（`SL.replace("*", "\\\\*")`）。
→ **两处都是本岗首轮沙箱实测暴露的**（首版补丁即因此 `[ABORT]`，未落真盘）。
**教训：凡「注入一段会扫描自己所在文件文本的代码」，必须先问一句「这段代码会不会扫描到自己的分隔符字面」。**

### {num}.6 落盘与验证（全部当场实跑）

| 项 | 结果 |
|---|---|
| 补丁脚本 | `scripts/patch_U01R33_guard_comment_aware_count.py`（**带备份**、**幂等**：重跑输出 `[NO-OP]` 2 个） |
| 受改脚本 | `scripts/reconcile_D15_D16_timing.mjs`、`scripts/reconcile_tts_actual_vs_d15_budget.mjs`（**本岗产出**） |
| 备份 | `reports/_bak_U01R33_guard_comment_count_20261023-082339/` |
| 沙箱四腿负测 | 注释／删行／新增／块注释 **4/4 全拦**，栈回溯 **0** |
| 新增自测器 | `scripts/selftest_U01R33_guard_comment_blindspot.py` —— **受检 9 条／通过 9 条／不通过 0 条**（真盘 **8 文件逐字节未变**） |
| 既有自测器回归 | `scripts/selftest_U01_R33_manifest_guard.py` —— **受检 7 条／通过 7 条**（真盘 8 文件逐字节未变） |
| 判据计数 | 三跑均 **清单 12 条 ＝ 实际断言点 12 处**（U01／U02／TTS） |
| 交付物字节 | U01／U02 的 D11／D15／D16 **6 份 SHA256 与落盘前逐字节一致** |

**出口闸（08:3x 当场实跑）**：`validate.mjs --unit U01` **11/11｜error 0｜warning 1**｜
`--unit U02` **11/11｜error 0｜warning 3**（较上一轮 5 降 2，因 U02 D13 已落盘）｜
`render-md.mjs` exit 0｜`reconcile_D15_D16_timing.mjs --unit U01／U02` 均 **exit 0｜清单 12 ＝ 12｜不通过 0**｜
`reconcile_tts_actual_vs_d15_budget.mjs` **exit 0｜清单 12 ＝ 12｜已评估 12｜不通过 0**。

### {num}.7 判据登记：**Q74**（新）

**Q74**：**守卫类「计数核对」实现必须剔除注释后再计数。**
凡以「文本出现次数」核对「声明条数 == 实际条数」的守卫，若不剔除注释，
则**「把一条判据注释掉」是最隐蔽的绕过手法** —— 它不改变计数，
守卫会继续谎报一致并放行，而该判据实际已死。
⇒ 判据：① 计数前剔除行注释与块注释；② 自测必须**覆盖「注释掉判据」这条腿**
（只测删／增两条会漏）；③ 计数实现若需注入到被扫描文件自身，
**必须避免分隔符字面自指**（本岗实测两处陷阱，见 {num}.5）。
**与 Q67 关系**：Q67 要求判据有区分力（恒真断言零信息量）——
**「注释掉一条判据后守卫仍报一致」正是恒真判据的典型形态**，本轮为 Q67 的一次实证。

### {num}.8 对企划合规 07:38 回执中「U01-R33 承接项」一项的按现盘核销（Q72 逐项对照）

贵方 07:38 回执第四点称「U01 侧两脚本停在 05:29:10／05:28:45 未改、『清单』命中 **0** → **仍在途**」。
**按现盘核销（Q42／Q58）：该承接项本岗已于 07:51 落地**（台账 §112.1 登记），
现盘两脚本均带 `ASSERT_MANIFEST` ＋ 清单守卫（mtime 07:43／07:47），
08:1x 实跑确认输出「判据清单断言（Q56② · U01-R33）：清单 12 条 ＝ 实际断言点 12 处｜不通过 0 条」。
→ **贵方该条描述为时点差异（07:38 早于本岗 07:51 落地），结论「承接项在途」已被现盘超越，本岗不重做。**
**本节新增的是该承接项的一次独立复核缺陷（Q74）与修复**，非重复落地。

### {num}.9 边界

本岗本轮**只写**：`scripts/reconcile_D15_D16_timing.mjs`、`scripts/reconcile_tts_actual_vs_d15_budget.mjs`
（本岗产出的只读对账脚本）、新增 `scripts/patch_U01R33_guard_comment_aware_count.py`、
新增 `scripts/selftest_U01R33_guard_comment_blindspot.py`、本台账节。
**未改任何交付物 JSON**（D05–D17 一字未动）｜未改 `03_规格/*`｜未改 `04_工具/*`｜
未改 `project.json`／D18／`00_项目索引.md`（属企划合规）。
未生成图片／视频／音频，未合成 TTS/BGM，未提交 H3 付费生成，未投流上架。
**以上游合规裁决为准**（S7／S19–S28、D18 Q30–Q74、U01-R33、OPS-03／OPS-12／OPS-18／OPS-19）。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cands = [args.project,
             os.path.join(factory, args.project),
             os.path.join(os.getcwd(), args.project),
             os.path.abspath(args.project)]
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "99_交付说明.md")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到 99_交付说明.md，候选：{cands}")

    p = os.path.join(proj, "99_交付说明.md")
    with open(p, "r", encoding="utf-8") as f:
        old = f.read()
    old_bytes = old.encode("utf-8")

    if EVENT_TITLE in old:
        print("[NO-OP] 本节标题已存在，不重复写。")
        return 0

    mx, low, bad = max_heading_num(old)
    if bad:
        print(f"[WARN] {len(bad)} 个章标题未解析出编号（不取号，按原文保留）：")
        for b in bad[:5]:
            print("   -", b)
    if low:
        print(f"[INFO] {len(low)} 个 <{LEDGER_MIN} 的小节标题（文档内小节，非台账章，不参与取号）")
    num = mx + 1
    print(f"[NUM] 现存最大台账章号 {mx} → 本节取 §{num}")

    if num <= mx:
        sys.exit(f"[ABORT] 取号异常：{num} ≤ 现存最大 {mx}")
    if re.search(rf"^## {num}[、．.]", old, re.M):
        sys.exit(f"[ABORT] 章号 {num} 在文件中已存在（重号）")

    section = build_section(num)

    # 落盘前并发复检
    with open(p, "r", encoding="utf-8") as f:
        recheck = f.read()
    mx2, _low2, _bad2 = max_heading_num(recheck)
    if mx2 != mx:
        sys.exit(f"[ABORT] 并发增量检查：取号后末章从 {mx} 变为 {mx2}，本脚本放弃写盘（请重跑）。")
    if not recheck.endswith(old[-50:]):
        sys.exit("[ABORT] 并发增量检查：文件尾部在取号期间被改动，本脚本放弃写盘（请重跑）。")
    if re.search(rf"^## {num}[、．.]", recheck, re.M):
        sys.exit(f"[ABORT] 并发增量检查：章号 {num} 在取号期间已被他人占用（重号），放弃写盘。")

    with open(p, "w", encoding="utf-8") as f:
        f.write(old + section)

    with open(p, "r", encoding="utf-8") as f:
        new = f.read()
    new_bytes = new.encode("utf-8")

    prefix_ok = new_bytes[:len(old_bytes)] == old_bytes
    occ = new.count(f"## {num}、")
    tail_is_ours = (f"## {num}、" in new
                     and new.rindex(f"## {num}、") > new.rindex("\n## "))
    print(f"[SELF] 前段逐字节一致：{prefix_ok}｜本节出现 {occ} 次｜"
          f"位于文件末章：{tail_is_ours}")
    print(f"[SELF] 文件字节 {len(old_bytes)} → {len(new_bytes)}（+{len(new_bytes)-len(old_bytes)}）")
    if not (prefix_ok and occ == 1 and tail_is_ours):
        sys.exit("[ABORT] 写后自检未通过")
    print("[OK] 台账已落盘。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
