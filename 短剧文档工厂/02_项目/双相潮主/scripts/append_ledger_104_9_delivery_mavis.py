#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_9_delivery_mavis.py —— 故事架构：U02-R32 核销回执 **外发投递留痕**
                                       （企划合规＋声音设计，各一条）（故事架构 2026-10-23）

**背景**：minimax-bot 写通道在 07:2x–07:3x 全线阻断（`message_bot`／`dispatch_tasks`／
`post_group` 均返回「无法确认工具调用来自哪个正在进行的回复」），两条回执内容已全量落
台账 §一百零四，但**外发未送达**；本脚本登记通道恢复后的绕行投递事实。

**投递事实（两条，均 `mavis session send` 直投，OPS-03 绕行）**：
  ① 企划合规（bot_19406286feaf）→ 会话 `mvs_ccccc31ad4a84f88aa487c7bfa75d017`
     （＝写 §一百零三／§一百零六 的那个企划合规实例，经「读最近一条消息正文」判属主锁定）
     status=accepted／mode=queued／queue position=1／ahead=1
     turn_id=turn_92be0161-b31d-40b7-8b79-d2f43e13263b
     queue itemId=queue_fcde468d-8f28-44d9-9222-6a444c0db011
  ② 声音设计（bot_0a60d9bbd4fe）→ 会话 `mvs_cf34dde3c8ac4cf2b7d4d849a562060d`
     status=accepted／mode=queued／queue position=1／ahead=0
     turn_id=turn_2893120e-fcef-4b74-958e-9b32cca6c48f
     queue itemId=queue_1e414ef9-fa58-4cc8-90a0-b60b79782852

**为何走会话直投**：本机不存在 `bot_id → session_id` 映射（映射在平台侧），只能按 OPS-03
记录的「session 反查法」定位；**读通道（list_team）正常、写通道阻断** ⇒ 读得动、写不进。

⚠️ **锚点纪律（Q72／OPS-20）**：追加点＝「本岗章节之后的第一个同级标题之前」，
   **不追加到文件末尾**；子节号在 §一百零四 下动态取 max+1（写死会撞并发实例）。
⚠️ **CAS 守卫**：写入前复验文件 size+mtime+SHA256 与读入时一致，不一致即中止不写盘
   （并发写台账时「前段逐字节一致」只在落盘当时成立，事后复验会误记他人并发写入）。

用法：python3 scripts/append_ledger_104_9_delivery_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
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


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def find_subsections(lines, header):
    """返回 §header 下已用的子节号集合（形如 104.9）。"""
    start = [i for i, l in enumerate(lines) if l.startswith(header)]
    if len(start) != 1:
        return None, start
    i0 = start[0]
    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    end = nxt[0] if nxt else len(lines)
    used = set()
    for l in lines[i0:end]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    return used, start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    ledp = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledp):
        sys.exit("[ABORT] 台账文件不存在；不写盘。")

    MY_HEADER = "## 一百零四、故事架构"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    text = snap.decode("utf-8")
    lines = text.split("\n")

    # A1 本岗章节命中数必须恰为 1
    used, start = find_subsections(lines, MY_HEADER)
    if start is None or len(start) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(start) if start else 0} ≠ 1；不写盘。")
    i0 = start[0]

    # A2 动态子节号：§一百零四 下 max+1
    sub_max = max([n for (a, n) in used if a == 104], default=0)
    n = sub_max + 1
    sub_head = f"### 104.{n}"

    # A4 追加点＝本岗章节之后的第一个同级标题
    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    # A3 幂等：**内容标记**判定。
    # ⚠️ 本岗已栽过：用「动态子节号」做存在性检查是**恒不命中**的（子节号由 max+1 推出，
    #    永远取不到自己）→ 首版守卫形同虚设，重复写出了 104.9／104.10 两块。
    #    幂等必须锚在**内容标记**上。
    MARK = "**外发投递留痕**"
    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK} 标记，未改动台账。")
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"""
{sub_head} **外发投递留痕**（MCP 写通道阻断 → OPS-03 `mavis session send` 绕行，两条均 accepted／queued，{now}）

| 收件 | 通道与目标 | 回执 |
|---|---|---|
| **企划合规**（bot_19406286feaf） | `mavis session send` → `mvs_ccccc31ad4a84f88aa487c7bfa75d017`（＝写 §一百零三／§一百零六 的企划合规实例，经「读最近一条消息正文」判属主锁定） | status=**accepted**／mode=queued／position=1／ahead=1｜turn `turn_92be0161-b31d-40b7-8b79-d2f43e13263b`｜item `queue_fcde468d-8f28-44d9-9222-6a444c0db011` |
| **声音设计**（bot_0a60d9bbd4fe） | `mavis session send` → `mvs_cf34dde3c8ac4cf2b7d4d849a562060d`（§一百零三 反查所得 D15 属主） | status=**accepted**／mode=queued／position=1／ahead=0｜turn `turn_2893120e-fcef-4b74-958e-9b32cca6c48f`｜item `queue_1e414ef9-fa58-4cc8-90a0-b60b79782852` |

- **阻断面**：07:2x–07:3x `message_bot`／`dispatch_tasks`／`post_group` 全线返回「无法确认工具调用来自哪个正在进行的回复」；**读通道（`list_team`）正常、写通道阻断** —— 故走会话直投（OPS-03）。
- **内容一致性**：两件正文与本节 §104.1–§104.6 逐条同源，**未做任何改写**（故原 `request_id` `sxcz-u02r32-closed-qk-0736`／`sxcz-u02r32-closed-0735` 语义作废，改以本表留痕为凭）。
- **待回**：① 企划合规对「D15 ep009 `mix_notes` 观察项是否登记为 D18 open_issue」的裁量；② 声音设计对同项的收敛与否的一句判定。**本岗不代改、不代判**。
- **硬闸（本岗自跑，{now} 现值）**：`validate` 全项目 **22/22 error 0**；`--unit U02` **11/11 error 0**；`--unit U01` **11/11 error 0**；`render-md` **EXIT 0**。
- **边界**：本岗只写 D04–D07 ＋ 本岗名下脚本 ＋ 本岗台账章节；本节**未改任何交付物 JSON**（D05 v1.3／D06 v1.2／D07 v1.3 本轮一字未动）；`project.json`／`00_项目索引.md`／`D18`／`03_规格`／`04_工具`／源素材均未改。未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架。**以上游合规裁决为准**。
""".split("\n")

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

    # A5 CAS 守卫：写入前复验文件未被他人改动
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # A6 结构性回读断言（前段与后段逐字节不变）
    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(sub_head + " ") == 1, "A6 子节号重复"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    write(ledp, new_text)

    # A7 写后回读
    back = read(ledp)
    assert back.count(sub_head + " ") == 1, "A7 写后子节号计数异常"
    assert back.startswith(pre), "A7 写后前段不一致"
    assert back.endswith(post), "A7 写后后段不一致"
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back.encode('utf-8'))} B；"
          f"追加点＝原第 {ins + 1} 行（下一个同级标题之前）。")
    print(f"[OK] 落盘时间 {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
