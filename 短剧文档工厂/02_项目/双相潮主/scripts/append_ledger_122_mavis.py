#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加器：写 §{动态取号}（分镜导演 · §133.6 事实订正 ＋ 故事架构 09:1x 回执逐项核销
＋ U02 `delivery_checks` D12 指针不一致新发现）。

【本节记什么】
  1. **本岗自查订正**：§133.6 里「D18 `delivery_checks` 现记 U01 D16 ＝ v1.12」**写错了** ——
     实测 D18 的**登记值 ＝ `v1.9`**，`v1.12` 是本岗**交付物文件**的现盘版本；两者被我混为一谈。
     按 Q30 **追加式订正**，§133.6 原正文一字不改。
  2. **故事架构 09:1x 回执的逐项核销**（受检 8 组，不采信转述）：其第四节「L1.detail 现状陈述
     未随现盘刷新」的**定位成立、结论部分不成立**（L1.detail 是追加式多段，尾部已有 08:4x 现盘段）；
     **真正未刷新的是 L2.detail 首段的 `warning 8`**（其未提）。
  3. **新发现**：**U02 `delivery_checks` 的 D12 登记 v1.0 ／ 现盘 v1.1** → U02 侧指针不一致 1 条
     （故事架构只报了 U01 侧 3 条）；全量指针不一致＝**4 条**（受检 24 组）。

【规格（沿用本岗 §117／§120／§121 追加器）】
  动态取号（阿拉伯／中文两式都解析）｜**父章号用中文数字**（Q85：父章中文 ＋ 子章阿拉伯）｜
  并发护栏（取号后复检末章号与文件尾部）｜写后四轴自检（前段逐字节一致｜本节出现 1 次｜位于末章）｜幂等。

用法：python3 scripts/append_ledger_122_mavis.py [--project .]
"""
import argparse
import importlib.util
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "ledger117_helpers", os.path.join(HERE, "append_ledger_117_mavis.py"))
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)

max_heading_num = _h.max_heading_num
LEDGER_MIN = _h.LEDGER_MIN

EVENT_TITLE = "§133.6 事实订正"

CN_DIGITS = "零一二三四五六七八九"


def int2cn(n: int) -> str:
    """1–999 中文数字（Q85：父章用中文数字）。"""
    if n < 0 or n > 999:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n < 20:
        return "十" + (CN_DIGITS[n % 10] if n % 10 else "")
    if n < 100:
        s = CN_DIGITS[n // 10] + "十"
        return s + (CN_DIGITS[n % 10] if n % 10 else "")
    s = CN_DIGITS[n // 100] + "百"
    rest = n % 100
    if rest == 0:
        return s
    if rest < 10:
        return s + "零" + CN_DIGITS[rest]
    return s + int2cn(rest)


def build_section(num: int) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cn = int2cn(num)
    return f"""

## {cn}、分镜导演：**{EVENT_TITLE}**（D18 U01 D16 登记值应为 `v1.9` 而非 `v1.12`）＋ **故事架构 09:1x 回执逐项核销**（受检 8 组）＋ **L1.detail 为追加式多段、其第四节定位成立而结论部分不成立；真正待刷的是 L2 的 `warning` 数** ＋ **U02 `delivery_checks` D12 指针不一致新发现**（全量 4 条）（分镜导演，{ts}）

> 本节为**本岗自查订正 ＋ 对故事架构来件的按现盘核销**。
> 本岗交付物 JSON **零改动**；本节**只写台账一个文件**；
> **未代改他岗章节正文**（§七·九），未代改 D18（属企划合规）。

### {num}.1 ⚠️ 本岗自查订正：§133.6 的 D18 指针值写错了（Q71 同型）

- **§133.6 原文写**：「D18 `delivery_checks` **现记 U01 D16 ＝ v1.12**」。
- **现盘实测**（`shared/D18.json` **v1.97｜521,714 B**，09:2x）：U01 `delivery_checks` 中 D16 的
  **登记值 ＝ `v1.9`**；**`v1.12` 是本岗交付物文件的现盘版本**（`units/U01/D16.json`｜224,276 B｜08:05:46）
  —— 两者被我**混为一谈**。
- ⇒ **D18 的 U01 D16 指针仍滞后 3 跳（登记 `v1.9` → 现盘 `v1.12`），且至 09:2x 仍未刷**。
- **§133.6 的结论方向不变且更强**：若本岗再把 D16 U01 升到 `v1.13`，指针漂移将由「3 跳」扩大为「4 跳」，
  仍需企划合规刷 D18 与索引 ⇒ **本岗不擅改的依据成立**；但**依据数字必须订正**
  （按 Q30 **追加式订正**，§133.6 原正文一字不改）。
- **教训**：**引用他岗维护的指针值，必须当场合回现盘复核**（Q71 同型：台账与回执里的数值须当场实跑回填）。
  本岗这次是把**摘要里的记忆值**当**实测值**写进了台账 —— **摘要不是实测**。

### {num}.2 故事架构 09:1x 回执：逐项核销（**受检 8 组**，不采信转述）

| # | 其所述 | 现盘实测（09:2x） | 判定 |
|---|---|---|---|
| ① | D11 U02 `v1.6`／58,051 B／07:11:50；「低阶」**0** 处、「律条」**16** 处 | 逐字一致（版本／字节／时点） | ✅ 成立 |
| ② | D07 U02 `v1.3`／28,431 B／07:06:33；台账 §112.4 在册 | 逐字一致 | ✅ 成立 |
| ③ | U02 `lock_state` 已 `locked`、L1–L4 全 pass（08:43） | **现盘确认**：`lock_state=locked`、`locked_at=2026-10-23 08:43`、`locked_by=企划合规 bot_19406286feaf`、L1–L4 `status=pass`（4/4） | ✅ 成立 |
| ④ | `delivery_checks` 由 7 份 → **10 份**（D12／D13／D14 已补登） | **现盘确认**：U02 **10 份**、U01 **14 份** | ✅ 成立 |
| ⑤ | **「U02 `L1.detail` 仍写 05:5x 旧文本『已落盘 7 份…缺 3 份』且其中版本号全不符 → 现状陈述未随现盘刷新」** | **定位成立、结论部分不成立**：该 05:5x 段**确实还在**（首段逐字），但**同一 detail 的尾部已有 08:4x 现盘段**（逐份列 D06–D16 十份现值 ＋「D14 逐镜包 32 个目录齐全」→ 「L1 由 pending 转 pass」），并**显式声明**「前序留痕不改写：上方 05:5x／06:4x／06:5x 各段均为当时点实况，按 **Q30** 保留」⇒ **「现状陈述未刷新」不成立**（现盘段已刷）；残留的是**可读性问题**（读首段会误读） | ⚠️ **部分成立** |
| ⑥ | （其未提）**U02 `L2.detail` 首段写「`warning 8`」** | **现盘 `warning 3`**；L2.detail 尾部 08:4x 段列了 ⑧roster 受检 1617 条／⑨D05 断言 12-12 等实跑，但**未重述 `warning` 数** ⇒ **这才是真正未随现盘刷新的现状陈述** | ⭐ **本岗补证** |
| ⑦ | 指针不一致剩 **3** 条（U01 D05／D10／D16） | 本岗全量复核**受检 24 组**（U01 14 ＋ U02 10）→ 不一致 **4 条**：**U01 D05**（登记 `v1.2`／现盘 `v1.5`）｜**U01 D10**（登记 `v1.9`／现盘 `v1.11`）｜**U01 D16**（登记 `v1.9`／现盘 `v1.12`）｜**U02 D12**（登记 `v1.0`／现盘 `v1.1`） | ⚠️ **其漏 1 条：U02 D12** |
| ⑧ | D05 现盘 `v1.4`／37,249 B／08:31:02 | **现盘 `v1.5`／38,574 B**（企划合规 09:1x 后再落一版） | **已被超越** |

⇒ **「本轮双向清零」结论不变**（U02-R32／U02-R25／U02-F01 本岗无待办；故事架构对 D04–D07 无待办）；
**本岗本轮新增/更正三项**：§133.6 事实订正（135.1）、L2 补证（135.2 ⑥）、U02 D12 指针（135.3）。

### {num}.3 指针全量复核（**受检 24 组** ＝ U01 14 ＋ U02 10｜不一致 **4 条**、一致 **20/24**）

| 单元 | 文档 | D18 登记值 | 现盘文件版本 | 判定 |
|---|---|---|---|---|
| U01 | **D05** | `v1.2` | **`v1.5`**（38,574 B） | ⚠️ 不一致（故事架构岗） |
| U01 | **D10** | `v1.9` | **`v1.11`**（31,842 B） | ⚠️ 不一致（视觉设定岗） |
| U01 | **D16** | `v1.9` | **`v1.12`**（224,276 B｜08:05:46） | ⚠️ 不一致（**本岗交付物**，归位归企划合规） |
| U02 | **D12** | `v1.0` | **`v1.1`**（101,788 B） | ⚠️ 不一致（视觉设定岗） |

- ⚠️ **计数口径**：D18 内的命中数**随每次写入变化**（企划合规刷指针所致）
  ⇒ 「命中 N 处」必须带**取数时点**（本表＝**09:2x**）与**路径口径**。
- ⚠️ **路径口径**：D02／D03／D04／D05／D10／D18 在 `shared/`，其余在 `units/<unit>/`
  —— **路径拼错会把「一致」误判为「缺」**（本岗首轮自查即踩此坑：修正前 8 条 → 修正后 **4 条**）。
- **归口**：四条指针的刷新**均归企划合规**（D18 owner）；本岗**不代改 D18**，亦**不代改他岗交付物**。

### {num}.4 边界与出口闸（09:2x 当场实跑）

- 本节**只写台账一个文件**；本岗**交付物 JSON 零改动**（D11 U01 `v1.8`／50,322 B｜D16 U01 `v1.12`／224,276 B｜
  D11 U02 `v1.6`／58,051 B｜D16 U02 `v1.5`／208,578 B｜D15 U01 `v1.6`／112,805 B｜D15 U02 `v1.2`／78,909 B，
  六份与开工逐位一致）；本轮**未新增脚本**（本岗 09:1x 新增的 2 个脚本见 §133）。
- **出口闸（09:2x 当场实跑）**：`validate --unit U01` **11/11｜error 0｜warning 1**｜
  `--unit U02` **11/11｜error 0｜warning 3**｜`render-md.mjs` **exit 0**｜
  `reconcile_D15_D16_timing.mjs --unit U01／U02` 均 **exit 0**（判据清单 12 ＝ 断言点 12｜不通过 0）。
- **未改** D18／D13／D14／`project.json`／`00_项目索引.md`／**他岗章节正文**／`03_规格/*`／`04_工具/*`；
  MD 未手写手改；未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架。
- **以上游合规裁决为准**（Q30／Q71／Q77／**Q85**／OPS-19、S7／S19–S32、企划合规 §一百一十六／§一百三十二／§一百三十四）。
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
    print(f"[NUM] 现存最大台账章号 {mx} → 本节取 §{num}（{int2cn(num)}）")

    if num <= mx:
        sys.exit(f"[ABORT] 取号异常：{num} ≤ 现存最大 {mx}")
    if re.search(rf"^## {num}[、．.]", old, re.M) or re.search(rf"^## {int2cn(num)}[、．.]", old, re.M):
        sys.exit(f"[ABORT] 章号 {num}／{int2cn(num)} 在文件中已存在（重号）")

    section = build_section(num)

    # 落盘前并发复检
    with open(p, "r", encoding="utf-8") as f:
        recheck = f.read()
    mx2, _low2, _bad2 = max_heading_num(recheck)
    if mx2 != mx:
        sys.exit(f"[ABORT] 并发增量检查：取号后末章从 {mx} 变为 {mx2}，本脚本放弃写盘（请重跑）。")
    if not recheck.endswith(old[-50:]):
        sys.exit("[ABORT] 并发增量检查：文件尾部在取号期间被改动，本脚本放弃写盘（请重跑）。")
    if re.search(rf"^## {num}[、．.]", recheck, re.M) or re.search(rf"^## {int2cn(num)}[、．.]", recheck, re.M):
        sys.exit(f"[ABORT] 并发增量检查：章号 {num} 在取号期间已被他人占用（重号），放弃写盘。")

    with open(p, "w", encoding="utf-8") as f:
        f.write(old + section)

    with open(p, "r", encoding="utf-8") as f:
        new = f.read()
    new_bytes = new.encode("utf-8")

    prefix_ok = new_bytes[:len(old_bytes)] == old_bytes
    cn = int2cn(num)
    occ = new.count(f"## {cn}、")
    tail_is_ours = (f"## {cn}、" in new
                     and new.rindex(f"## {cn}、") > new.rindex("\n## "))
    print(f"[SELF] 前段逐字节一致：{prefix_ok}｜本节出现 {occ} 次｜"
          f"位于文件末章：{tail_is_ours}")
    print(f"[SELF] 文件字节 {len(old_bytes)} → {len(new_bytes)}（+{len(new_bytes)-len(old_bytes)}）")
    if not (prefix_ok and occ == 1 and tail_is_ours):
        sys.exit("[ABORT] 写后自检未通过")
    print("[OK] 台账已落盘。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
