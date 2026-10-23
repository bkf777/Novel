#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通知投递取证清单生成器（台本编剧岗）—— 把「已发消息」变成「逐条可查证的状态表」。

背景（为什么需要这个脚本）：
  `get_tasks` 只接受 batch_id 或 task_id，**不接受 request_id**；而本岗所有消息都是
  用 `message_bot` / `dispatch_tasks` 以 request_id 发出的，batch_id 只在会话存档的
  工具返回体里出现。逐条翻档案找 batch_id 极慢，且极易把「某条消息的 batch」与
  「相邻一条消息的 batch」配错（本次实测就配错过一次：把 040 的 batch_id 认成 028 的）。

做法：
  1. 扫描会话快照目录（g*.jsonl），用**已调试好**的正则从工具返回体里成对抽出
     `batch_id` 与 `request_id`（顺序固定：batch_id 在前、request_id 在后）。
  2. 再从工具调用参数里抽出 `request_id → to(bot_id)` 与消息正文首行标题。
  3. 输出一张「取证清单」表：request_id | 对象 bot_id | batch_id | 标题前 40 字。
     → 拿到 batch_id 后逐条 `get_tasks(batch_id=...)` 即可查 status / error /
       started_at / ended_at / notification，**不凭任务状态猜**。

用法：
  python3 scripts/audit_notifications.py                # 打印清单
  python3 scripts/audit_notifications.py --out 证据.md   # 同时落盘

注意（踩坑记录）：
  * 快照里的工具返回体是 **JSON 字符串内嵌 JSON**，字段间以 `\\n  `（反斜杠+n+空格）
    分隔 —— 正则里用 `\\s*` 匹配不到，必须写成 `[\\s\\n]{0,12}`，且 `request_id` 前的
    `\\"` 不能漏。这是本次调试耗时最长的点。
  * **不要**用「从 request_id 出现位置往后找第一个 batch_id」的贪心前向法：工具调用
    参数在前、工具返回体在后，前向法会把**下一条**消息的 batch_id 配过来。
"""
import argparse
import glob
import json
import os
import re
import sys

# 会话快照根目录：默认取当前 runtime 的 sessions 目录（可用 --sessions 覆盖）
DEFAULT_SESSIONS = "/Users/ezreal/.minimax/v2/sessions"

# 工具返回体：batch_id 在前、request_id 在后（顺序固定，成对抽取才安全）
PAIR_RE = re.compile(
    r'batch_id\\":\s*\\"(batch_[0-9a-f]+)\\",[\s\\n]{0,12}\\?"request_id\\":\s*\\"(sjc-[A-Za-z0-9._-]+)'
)
# 工具调用参数：request_id → to / message
CALL_RE = re.compile(r'"request_id"\s*:\s*"(sjc-[A-Za-z0-9._-]+)"')


def walk(node, out):
    """在任意嵌套结构里收集 message_bot 的调用参数。"""
    if isinstance(node, dict):
        if node.get("name") == "mcp__minimax-bot__message_bot" and isinstance(node.get("arguments"), dict):
            out.append(node["arguments"])
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)


def collect(sessions_root, prefix="sjc-"):
    pair = {}          # request_id -> batch_id
    calls = {}         # request_id -> {to, title}
    files = sorted(glob.glob(os.path.join(sessions_root, "**", "snapshots", "g*.jsonl"), recursive=True))
    for f in files:
        try:
            data = open(f, encoding="utf-8").read()
        except OSError:
            continue
        for b, r in PAIR_RE.findall(data):
            pair.setdefault(r, b)
        # 调用参数：逐行反序列化，抓 message_bot 的 arguments
        for line in data.splitlines():
            if "message_bot" not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            got = []
            walk(obj, got)
            for a in got:
                rid = a.get("request_id")
                if rid and prefix and not rid.startswith(prefix):
                    continue
                if rid and rid not in calls:
                    msg = a.get("message", "")
                    calls[rid] = {
                        "to": a.get("to", ""),
                        "title": msg.split("\n")[0][:60],
                    }
    pair = {k: v for k, v in pair.items() if not prefix or k.startswith(prefix)}
    return pair, calls, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", default=DEFAULT_SESSIONS, help="sessions 根目录")
    ap.add_argument("--prefix", default="sjc-", help="request_id 前缀过滤（本岗一律 sjc-；传空串则不过滤）")
    ap.add_argument("--out", default=None, help="落盘路径（markdown）")
    args = ap.parse_args()

    pair, calls, nfiles = collect(args.sessions, args.prefix)
    rows = []
    for rid in sorted(set(pair) | set(calls)):
        c = calls.get(rid, {})
        rows.append((rid, c.get("to", "?"), pair.get(rid, "（未在快照中配到 batch_id）"), c.get("title", "")))

    lines = [
        "# 通知投递取证清单（自动生成）",
        "",
        f"- 扫描快照文件数：**{nfiles}**",
        f"- 配到 batch_id 的 request_id 数：**{len(pair)}**",
        f"- 抓到调用参数的 request_id 数：**{len(calls)}**",
        "",
        "> 用法：对下表每行用 `get_tasks(batch_id=...)` 逐条查 status / error / started_at / ended_at。",
        "> **不要**凭任务状态或转述推断是否已被对方处理。",
        "",
        "| request_id | 对象 | batch_id | 标题前 60 字 |",
        "|---|---|---|---|",
    ]
    for rid, to, b, title in rows:
        lines.append(f"| `{rid}` | `{to}` | `{b}` | {title.replace('|', '／')} |")
    text = "\n".join(lines) + "\n"

    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ 已落盘 {args.out}（{os.path.getsize(args.out)} B）", file=sys.stderr)


if __name__ == "__main__":
    main()
