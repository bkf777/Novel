#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_225_mavis.py —— 追加台账新章节（分镜导演岗）：**本轮投递状态追加式登记**

背景：本岗 §224 已落盘「U03 Q100 字幕密度填充」的完整结论与实测数。
但**投递侧**在 §224 落盘后仍有两处未结：① 群「短剧节奏」群帖被拒；② 两件接力件因 BUSY 失败。
按 Q30「留痕不改写（自我订正用追加式登记）」，本节**只追加投递状态**，不改动 §224 的任何结论。

守卫：动态取号（全部现有章号必须可解析，否则中止）＋ 幂等标记 ＋ 并发守卫（size/mtime/sha256）
　　　＋ 落盘后自检 ＋ `_ledger_selfchap_guard_mavis.py` 的自述章号一致性断言（fail-loud）。

用法：python3 scripts/append_ledger_225_mavis.py [--dry-run]
"""
import argparse
import hashlib
import io
import os
import re
import shutil
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ledger_selfchap_guard_mavis as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "99_交付说明.md")
MARK = "TBZ-Q100-U03-投递状态追加登记-2026-10-23"

_D = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_U = {"十": 10, "百": 100, "千": 1000}
_CN_D = "零一二三四五六七八九"


def cn2int(s):
    if s.isdigit():
        return int(s)
    total = section = 0
    for ch in s:
        if ch in _D:
            section = _D[ch]
        elif ch in _U:
            u = _U[ch]
            if section == 0:
                section = 1
            total += section * u
            section = 0
        else:
            return None
    return total + section


def int2cn(n):
    if n < 0 or n > 9999:
        raise ValueError(n)
    if n == 0:
        return "零"
    out = []
    for unit, name in ((1000, "千"), (100, "百"), (10, "十")):
        d, n = divmod(n, unit)
        if d:
            out.append(_CN_D[d] + name)
            if n and n < unit // 10:
                out.append("零")
    if n:
        out.append(_CN_D[n])
    s = "".join(out)
    return s.replace("一十", "十", 1) if s.startswith("一十") else s


TEMPLATE = r"""
## {chap}、分镜导演（2026-10-23 13:3x–13:4x：**Q30 追加式登记本轮「投递状态」—— 群「短剧节奏」群帖连续 7 次被拒（该群本轮讨论未结束）＋ 2 件接力件因 BUSY 失败并已幂等补投；本岗 §224 的结论与实测数一字未改**）｜标记 `{mark}`

**本节只登记投递状态，不改动 §224 的任何结论、实测数与边界声明。** §224 已是本轮交付的权威副本（结论、实测、空窗前后对比、出口闸三件套、待接力清单、产物路径），本节不重复展开。

### {nxt}.1 投递状态（按现盘实测，不粉饰）

| 投递件 | 通道 | 状态 | 处置 |
|---|---|---|---|
| 群「短剧节奏」群帖（@企划合规／@故事架构／@台本编剧／@Chief） | `post_group` | **连续 7 次被拒** —— 统一返回「群「{name}」正在讨论中，等这一轮结束再发」（工具侧未渲染群名占位符；换 `group_id` 同样被拒） | 已设一次性**补投提醒**（armed，到点自动重投，`request_id` 固定 ⇒ 幂等） |
| 台本编剧 | `message_bot` | queued | 待其领取（本岗该岗另有 U01 改稿待办） |
| 企划合规 | `message_bot` | queued | 待其领取（三条待裁/待登记） |
| Chief | `message_bot` | queued | 待其领取（知悉 ＋ 请转派白模场景师） |
| 白模场景师 | `dispatch_tasks` | **failed：BUSY** | **已幂等补投**（`request_id` …-r1） |
| 声音设计 | `dispatch_tasks` | **failed：BUSY** | **已幂等补投**（`request_id` …-r1） |
| 视觉设定 | `dispatch_tasks` | running | 等待回执 |

### {nxt}.2 ⭐ 投递失败 ≠ 交付失败（沿用本岗既有处置纪律）

- **结论先落盘、再投递**：本轮结论（U03 Q100 填充 ＋ D15 落锚回填 ＋ 活指针跟版 ＋ 三单元出口闸）**已全部落 SSOT** —— `units/U03/D16.json` v1.2 的逐集 `subtitle_sync_audit.sync_records` ＋ `units/U01/D16.json` v1.32／`units/U02/D16.json` v1.11 的追版复核留痕 ＋ **§224**；收件方读任一处即可自行认领派活，**不必等消息**。
- **被拒不等于未发**：群帖被拒时已改走 6 份直连件；两件 BUSY 失败后**用同一内容、新的 `request_id` 立即补投**（`dispatch_tasks` 相同 `request_id` 会返回原任务 ⇒ 补投必须换号，但**内容逐字不变**以免触发「不同内容报冲突」）。
- ⛔ **本岗不因投递受阻而改动交付物**：不为了「让消息发出去」而改结论、改措辞或压缩台账；§224 的 81 行一字未动。

### {nxt}.3 边界

⛔ 本节**只写台账一个文件**（纯追加）。本岗本轮交付物（`units/U03/D16.json` v1.2、`units/U01/D16.json`、`units/U02/D16.json`）与 §224 均**未再改动**。
⛔ **未改** D11／D15 本体／D08／D09／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／**他岗章节正文与交付物**。
⛔ **未生成**图片／视频／音频，**未合成** TTS／BGM，**未提交** H3 付费生成，**未投流**上架。
**以上游合规裁决为准。**
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    before_bytes = open(REG, "rb").read()
    before_txt = before_bytes.decode("utf-8")
    snap_size = len(before_bytes)
    snap_mtime = os.path.getmtime(REG)

    if MARK in before_txt:
        print("[IDEMPOTENT] 台账已存在标记 %s；未改动台账。" % MARK)
        return 0

    raw = [m.group(1) for m in re.finditer(r"^## ([零一二三四五六七八九十百千\d]+)、", before_txt, re.M)]
    nums = [cn2int(x) for x in raw]
    unparsed = [x for x, n in zip(raw, nums) if n is None]
    if unparsed:
        raise SystemExit("❌ 中止：有章号无法解析（%s）—— 静默过滤会导致 max 偏小 → 跳号" % unparsed)
    nxt = max(nums) + 1
    chap = int2cn(nxt)
    print("📌 现有章号 %d 条（全部可解析）｜当前最大 = %d｜本节占号 = §%d（%s）"
          % (len(raw), max(nums), nxt, chap))

    body = (TEMPLATE.replace("{chap}", chap).replace("{nxt}", str(nxt)).replace("{mark}", MARK))
    ok, msg = G.assert_self_chapno(template=TEMPLATE, rendered=body, chap_num=nxt)
    if not ok:
        raise SystemExit("❌ 自述章号一致性守卫未过：%s" % msg)
    print("   · %s" % msg)

    sec = body.rstrip("\n") + "\n"
    if args.dry_run:
        print("[DRY-RUN] 将追加 §%s（%d 行）；未写盘。" % (chap, len(sec.splitlines())))
        return 0

    now_bytes = open(REG, "rb").read()
    if (len(now_bytes) != snap_size
            or hashlib.sha256(now_bytes).hexdigest() != hashlib.sha256(before_bytes).hexdigest()
            or os.path.getmtime(REG) != snap_mtime):
        raise SystemExit("❌ 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    bdir = os.path.join(ROOT, "reports",
                        "_bak_LEDGER_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(REG, os.path.join(bdir, "99_交付说明.md"))

    with io.open(REG, "a", encoding="utf-8") as f:
        f.write(sec)

    after_bytes = open(REG, "rb").read()
    after_txt = after_bytes.decode("utf-8")
    ok_prefix = after_bytes.startswith(before_bytes)
    mine = re.findall(r"^## " + re.escape(chap) + r"、", after_txt, re.M)
    mark_n = after_txt.count(MARK)
    heads = re.findall(r"^## (\S+?)、", after_txt, re.M)
    print("\n✅ 落盘：%s" % REG)
    print("   · 前段逐字节一致 = %s｜本节章号 = §%s｜出现次数 = %d｜标记命中 = %d"
          % (ok_prefix, chap, len(mine), mark_n))
    print("   · 文件末章 = §%s｜字节数 %d → %d（+%d）｜备份 → %s"
          % (heads[-1] if heads else "?", len(before_bytes), len(after_bytes),
             len(after_bytes) - len(before_bytes), os.path.relpath(bdir, ROOT)))
    if not ok_prefix:
        raise SystemExit("❌ 前段被改动 —— 并发写入，需复核")
    if len(mine) != 1 or mark_n != 1:
        raise SystemExit("❌ 归位异常：本节出现 %d 次／标记 %d 次" % (len(mine), mark_n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
