#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_d16_density_mavis.py —— 分镜导演：**Chief 12:1x 来件四项逐项核销**
                                    ＋ **字幕密度三集落盘（ep003/004/007）**
                                    ＋ ⭐ **「anchor 不落盘」内容源脱钩的发现与反推重建**
                                    ＋ **审计块行号失配机制**与两轮对位刷新
                                    ＋ 垃圾时间终测 16/16 达标

治理沿用本岗并发安全范式：动态取号（父章中文/子章阿拉伯，双格式兼容）＋ 标记幂等
＋ 写前 sha256 三锚 CAS ＋ 备份先行 ＋ 写后回读校验 ＋ 失败自动回滚。
用法：python3 scripts/append_ledger_d16_density_mavis.py [--dry-run]
"""
import hashlib
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ledger_selfchap_guard_mavis as G  # noqa: E402  （只定义函数、无顶层副作用）

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")
MARK = "TBZ-12-3x-Chief来件核销-字幕密度-anchor脱钩重建-2026-10-23"


def cn2int(s):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    total = section = 0
    for ch in s:
        if ch in digits:
            section = digits[ch]
        elif ch in units:
            u = units[ch]
            if section == 0:
                section = 1
            total += section * u
            section = 0
        else:
            return None
    return total + section


def int2cn(n):
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n - 10] if n > 10 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    s = d[n // 100] + "百"
    rest = n % 100
    if rest == 0:
        return s
    if rest < 10:
        return s + "零" + d[rest]
    if rest < 20:
        return s + "一十" + d[rest - 10]
    return s + d[rest // 10] + "十" + (d[rest % 10] if rest % 10 else "")


def parse_chapters(txt):
    nums = []
    for m in re.finditer(r"^## ([零一二三四五六七八九十百千\d]+)、", txt, re.M):
        v = cn2int(m.group(1))
        if v:
            nums.append(v)
    return nums


BODY = r"""
## {chap}、分镜导演（2026-10-23 12:2x–12:3x：⭐ **Chief 12:1x 来件四项逐项核销（按现盘实测，4 项里 3 项已被并发实例修掉，唯一真待办＝活戳追版）** ＋ **字幕密度 ep003/004/007 三集落盘 32 行** ＋ ⭐ **发现「densify 落盘不写 anchor」⇒ 90 条字幕行与内容源整体脱钩 → 已从盘上反推重建** ＋ ⭐ **审计块行号失配的机制性成因**（每次插行必重排 seq）＋ **垃圾时间终测 16/16 达标**）｜标记 `{mark}`

> **一句话**：Chief 派来的四件事，本岗按现盘逐项实测后**只有一项是真待办**（活戳追到 v1.13）；字幕密度已完成 U01 全 8 集（**超阈 15 集 → 0 集，最长空窗 14.0s → 2.40s，平均空窗总 32.01s → 6.55s**）；过程中发现并修掉一个**内容源整体脱钩**的隐患（`anchor` 不落盘 ＋ 清单被并发实例重写 ⇒ 90 条行永久失去锚点、不可重建）。

### {nxt}.1 Chief 来件四项逐项实测核销（**以现盘为准，不采信转述坐标**）
| 项 | 来件所述 | **本岗现盘实测（12:2x）** | 结论 |
|---|---|---|---|
| ① | `verified_against_d15` 仍写 v1.7 | 现盘 8 集**均为 `v1.12`**（D15 U01 现值 **v1.13**） | ⚠️ **落后一版 ＝ 唯一真待办** → 已刷为 v1.13 |
| ② | `pending_d15_sync` 2 条已过期 | **该字段 8 集全无**（黄金 3 秒已落锚，字段已被并发实例移除） | **不成立**，无需刷 |
| ③ | `rows[]` 行序与活字幕行错位一格 | 8 集**时码级对位，0 错位 0 失效**（并发实例 v1.22 已修） | **不成立**（但见 §nxt.3 的**机制性成因**） |
| ④ | ep3 seq4/seq5「line_ref 仍指旧编号」 | D09 U01 v1.7 现盘 ep3 台词 idx=1/2/3 ＝「比上一趟早。」/「九小时。」/「腕子上这个，是它给的？」；rows 的 `d15_line_ref` ＝ `D09 ep3 #1/#2/#3` **逐条一致** | **不成立**，警告已过期 |

- **核销依据的可复现性**：判定全部走**现盘读数 + 可复跑判据**，不引用来件字面值。⚠️ 过程中实测到**两次读取之间文件被并发实例改写**（D16 U01 v1.21→v1.22→v1.26）⇒ 同一文件前后两次 dump 结论会相反 ⇒ **凡报数必带时点**。

### {nxt}.2 第②项：字幕密度落盘（本岗写 ep003/004/007 共 **32 行**）
- **内容源**：`scripts/density_fills_U01.json` 增写 ep3/ep4/ep7（人工撰写的文案＋锚点，脚本不生成内容）。
- **锚点纪律**：每行 `anchor` **逐字取自该镜 D11 `visual_facts`**（「画面里本来就有这个东西」硬约束）⇒ 工具的 5 项硬校验（锚点存在／落在该镜**真实可见区间**（按 D16 `cuts` 推导，含段内并行交叉剪辑）／停留 ≥1.2s／字数 ≤15／不与既有行重叠）**32 条全过**。
- **本岗落盘**：D16 U01 **v1.23 → v1.24**（`densify_subtitles.py` 自持升版，写前并发守卫 + 备份 `reports/_bak_densify_U01_*`）。
- **实测效果**（`scripts/audit_dead_time.py` 复测）：

| 集 | 最长空窗 | 空窗总 | 判定 |
|---|---|---|---|
| U01-EP003 | 10.00s → **1.00s** | 34.70s → **9.30s** | 重拖 → **ok** |
| U01-EP004 | 12.00s → **1.70s** | 37.90s → **8.30s** | 重拖 → **ok** |
| U01-EP007 | 12.00s → **1.60s** | 37.20s → **10.00s** | 重拖 → **ok** |

- **并发实例同期铺了 ep001/005/006/008**：本岗为同四集写的 fills **被工具的重叠校验全部拦下、零写入**（既有行文案与本岗语义重合）⇒ 本岗**撤回**该四集 fills，**不夺回、不二次改写**；并发实例成果保留并被本岗采纳。**终测：16 集超阈 0 集｜最长空窗 2.40s｜平均空窗总 6.55s**。

### {nxt}.3 ⭐⭐ 机制性发现：**「anchor 不落盘」⇒ 90 条字幕行与内容源整体脱钩**
- **根因（读源码取证）**：`densify_subtitles.py` 落盘时只写 `text / in_sec / out_sec / shot_id / note`，
  **不写 `anchor`** —— 而 `anchor` **只活在本清单里**（工具靠它做「不许编造画面」校验）。
  ⇒ **清单一旦被清空/重写，盘上这些行就永久失去锚点、无法重建**（D16 一旦重建即集体消失）。
- **触发事实**：12:28 并发实例重写 `scripts/density_fills_U01.json`（4,993 B，**只剩 ep2**）
  ⇒ 盘上 **90 条**字幕行（ep2 9 ＋ 并发实例 ep1/5/6/8 49 ＋ 本岗 ep3/4/7 32）**全部与内容源脱钩**。
- **修法（从盘上反推，不凭空造）**：本岗新增 `scripts/rebuild_density_fills_U01_mavis.py` ——
  对每条 `type=="字幕"` 的行，在其 `shot_id` 的 D11 `visual_facts` 里求「text × vf 的**最长公共连续子串**」作 anchor（要求 ≥4 字）；
  改写型行（清单化改写，非逐字包含）走**人工锚点表**（5 条：`翻倒的椅子`／`钎身与灰隙巢虫触角相交`／`贯穿叶承钧身侧的钢板`／`砸在叶红衣腕上的束具扣上`／`黑白双焰的余光`）。
  **求得 ≥4 字锚点的行一律不伪造**；锚点仍须逐字 ∈ `visual_facts`（工具会再机械校验一次）。
- **落地**：清单重建为 **8 集 / 90 条**；**densify 幂等复跑 90 条全部「已存在且一致，跳过」、零新增零变更** ⇒ **内容源 ⇄ 盘面已对齐**（可幂等复跑、可随 D16 重建而再生）。

### {nxt}.4 ⭐ 审计块行号失配的**机制性成因**（非孤立缺陷）
- `subtitle_style.lines` 在每次插入字幕行后按 `in_sec` **重排并重编 `seq`**；而 `subtitle_sync_audit.rows[]` 是**事件溯源留痕**，**不跟着重排**
  ⇒ **每次字幕密度填充后必然行号错位**。本轮实测两轮：densify 落盘后 **10 条**错位（ep3/4/7）；并发实例铺完 ep1/5/6/8 后又 **14 条**（ep1/ep8 等）。
- **刷新方式**（`scripts/refresh_D16_U01_audit_mavis.py`）：按 **(in_sec, out_sec) 对位**到活 lines 取活行 `seq` 覆写 `row.seq` —— **不按行序猜、不改任何数值字段**。
- **有意不动的字段**：`synced_row_count` / `no_vo_anchor_rows` / `sync_basis` / `verified_note` / `sync_records` ——
  `sync_basis` 自述「本字段是**事件溯源陈述**，不是活链接」；且实测各集口径本就不同源（ep01 3+1=4、ep03 3+2=5≠rows 3、ep08 4+1=5≠rows 4）⇒ 改它们会**破坏溯源**。
- **活戳追版**：`verified_against_d15` v1.12 → **v1.13**（D15 U01 现值）；依据 `node scripts/reconcile_D15_D16_timing.mjs --unit U01` 实跑 **EXIT 0** —— 对白字幕 **30 条** / D15 配音 **30 条**，`out_sec ≠ 配音(at_sec+dur_sec)` **0 条**、配对距离 >0.05s **0 条** ⇒ D16 现盘数值对 D15 v1.13 全部成立。
- **落盘**：D16 U01 **v1.24 → v1.25**（本岗轮）→ **v1.26 → v1.27**（并发实例铺完后再刷一轮）；脚本**幂等**（复跑 `[IDEMPOTENT]` 退出）、带版本守卫（盘面被他人升版 ⇒ `[NO-OP]` 不抢写）。

### {nxt}.5 判据与出口闸（当场实跑）
- `node scripts/reconcile_D15_D16_timing.mjs --unit U01` → **EXIT 0**｜对白字幕 30 / D15 配音 30｜`out_sec` 失配 **0** 条｜配对距离越阈 **0** 条｜**0 越窗 / 0 跨切点 / 0 重叠**。
- `node 04_工具/validate.mjs --unit U01` → **exit 1｜error 44｜warning 2｜通过 10/12 规则**。
  ⚠️ **44 条 error 均不在本岗文件**：
  · **V9 字数基础档 17 条** —— 全部指向 **D08 U01**（`word_count.base/total` 声明 **0**、实际 196~312）。
    **归因（磁盘实测）**：D08 U01 于 **12:23** 被并发实例重建至 **v1.13** 时漏填 `word_count` ⇒ **D08 属台本编剧岗单写点，本岗不改**，已去函。
  · **V12 白模构图一致性 27 条** —— W1/W2/W3 全部，属**已知未收口项**（白模未按新景别重建 ＋ W3 判据缺陷），与字幕密度无关（镜数/镜时/白模/D14 一律未动 ⇒ V11 全程 PASS）。
- `node scripts/check_D08_D11_shotintent.mjs --unit U02` → EXIT 0｜受检 **31 条**｜**31/31 零硬冲突**（本岗 §198 已交付）。
- 垃圾时间终测：**16 集超阈 0 集｜全集最长空窗 2.40s｜平均空窗总 6.55s**（基线：超阈 15 集 / 14.00s / 32.01s）。

### {nxt}.6 边界与未结项
- 本轮**写面**：`scripts/build_D11_U02.py`（§198 内容源）｜`units/U01/D16.json`（字幕密度 + 审计块）｜`scripts/density_fills_U01.json`（内容源）｜本岗脚本 4 支（台账追加器 ×2、内容源反推重建、审计块刷新）。
  **未改** D08/D09/D11/D12/D14/D15/D17/D18、`03_规格/*`、`04_工具/*`；**未动**白模/D14/镜数/镜时；未生成图片/视频/音频；未合成 TTS/BGM；未提交 H3 付费生成；未投流上架。
- **未结项**：① **D16 U01 单写点实例归属**待裁定（本轮与并发实例在同一单写点并发写 4 次：v1.23→v1.27，**已发生 3 次版本自持升版**，本岗每次均走守卫未覆盖对方字节）；② **D08 U01 `word_count` 漏填**（V9 17 条）待台本编剧修；③ **V12 白模重建与 W3 判据三选一**待裁定；④ **U02 ep009~ep016 字幕密度**（8 集）待铺（需新建 `density_fills_U02.json`）；⑤ **黄金 3 秒剩余 5 集**（ep004/005/006/007/008）待前移（ep005/ep006 首句说话人不在镜1，须按 ep003 先例做画外音）。
"""


def main():
    dry = "--dry-run" in sys.argv
    snap = open(LEDGER, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(LEDGER)
    txt = snap.decode("utf-8")

    if MARK in txt:
        print("[IDEMPOTENT] 台账已存在标记 %s；未改动台账。" % MARK)
        return 0

    nums = parse_chapters(txt)
    if not nums:
        print("❌ 解析不到任何父章号；拒绝追加。")
        return 2
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        print("❌ 台账存在重复章号 %s；拒绝追加（防撞号）。" % dup)
        return 2
    nxt = max(nums) + 1
    chap = int2cn(nxt)
    body = BODY.replace("{chap}", chap).replace("{nxt}", str(nxt)).replace("{mark}", MARK).rstrip("\n") + "\n"

    # 🛡️ 自述章号一致性守卫（A1 禁硬编码自身章号／A2 禁占位符残留）—— fail-loud
    ok, gmsg = G.assert_self_chapno(template=BODY, rendered=body, chap_num=nxt)
    print("🛡️ %s" % gmsg)
    if not ok:
        print("❌ 中止；不写盘。")
        return 2

    print("📌 当前最大章号 = %d｜本节占号 = §%s（%d）" % (max(nums), chap, nxt))
    if dry:
        print("（--dry-run：未写盘）")
        print(body[:1200])
        return 0

    cur = open(LEDGER, "rb").read()
    if (len(cur) != snap_size or os.path.getmtime(LEDGER) != snap_mtime
            or hashlib.sha256(cur).hexdigest() != snap_sha):
        print("[ABORT] 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")
        return 3

    bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(LEDGER, bak)

    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(body if body.startswith("\n") else "\n" + body)

    back = open(LEDGER, "rb").read()
    if back.count(MARK.encode("utf-8")) != 1:
        shutil.copy2(bak, LEDGER)
        print("[ROLLBACK] 写后标记计数异常，已回滚。")
        return 4
    if "### {nxt}." in back.decode("utf-8"):
        shutil.copy2(bak, LEDGER)
        print("[ROLLBACK] 写后子节占位符残留，已回滚。")
        return 4
    print("✅ 已追加 §%s（%d 字符）｜文件现 %d B（%+d）｜备份 %s"
          % (chap, len(body), os.path.getsize(LEDGER), os.path.getsize(LEDGER) - snap_size,
             os.path.relpath(bak, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
