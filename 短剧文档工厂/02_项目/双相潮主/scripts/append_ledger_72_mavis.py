#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账（分镜导演岗）—— A/B/C 三条送达记录。动态取 max+1。"""
import io, os, re, datetime
ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"
def cn2int(s):
    if s.isdigit(): return int(s)
    d={"零":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}; u={"十":10,"百":100,"千":1000}
    t=sec=0
    for ch in s:
        if ch in d: sec=d[ch]
        elif ch in u:
            x=u[ch]
            if sec==0: sec=1
            t+=sec*x; sec=0
        else: return None
    return t+sec
def int2cn(n):
    d="零一二三四五六七八九"
    if n<10: return d[n]
    if n<20: return "十"+(d[n-10] if n>10 else "")
    if n<100: return d[n//10]+"十"+(d[n%10] if n%10 else "")
    return str(n)
txt=open(REG,encoding="utf-8").read()
nums=[cn2int(m.group(1)) for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)]
nums=[n for n in nums if n]
nxt=max(nums)+1; CH=int2cn(nxt)
print(f"📌 当前最大章号 = {max(nums)}，本节占号 = {CH}（{nxt}）")
now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
SEC = f"""
## {CH}、分镜导演：**A/B/C 三条全部送达**（群通报第 9 次进群）＋ §七十.7 第 6 项销号（**分镜导演，{now}**）

| 件 | 通道 | 对象 | request_id | task_id |
|---|---|---|---|---|
| **A** | `post_group` | 群 `grp_e728f66c5f7f`（AI短剧文档工厂） | `sxcz-group-u02-d11v13-d16v13-q56-20261023` | `task_a940992273e5`（posted_to 已确认，first_speaker 企划合规） |
| **B** | `message_bot` | 企划合规 `bot_19406286feaf` | `sxcz-u02-d11v13-d16v13-w6-closeout-q56-20261023` | `task_ce86cd2fdeb0` |
| **C** | `message_bot` | 视觉设定 `bot_db3fd3817800` | `sxcz-u02-d11v13-d16v13-visualsetting-ack-20261023` | `task_35aa619f3365` |

**本轮之前 post_group 累计 8 次尝试全部未发出**（错误码四类：①群正在讨论中 ②无法确认工具调用来自哪个正在进行的回复 ③这个 Bot 正在多个聊天里回复 ④同一 request_id 已用于不同内容）。**本轮成功的原因**：本轮为**用户消息触发**的轮次 —— 错误码 ② 的实质是「**自动触发轮次写操作 MCP 全不可用**」，用户消息触发的轮次则可用；**③「正在多个聊天里回复」也已自然解除**。

**教训（可复用）**：**定时/自动触发轮次不要尝试写操作**（群通报、私聊均不可用），把待发件正文落到 `reports/_outbox_*.md` 备好，等**用户消息触发**的轮次一次性发出 —— 正文与 request_id 一次成型，不用在受限通道里反复试错。

**⚠️ 受理 ≠ 完成**：群讨论任务可能仍在排队（返回 `notification: pending`），用上表 task_id 查进度。

**§七十.7 第 6 项「群通报与 2 条私聊仍待发出」→ 销号**；正文全文留档 `reports/_outbox_20261023.md`（已标记三条为已送达）。

边界：本节只写台账，未改任何交付物；未生成图片／视频／音频，未合成 TTS/BGM，未提交 H3 付费生成，未投流上架。
"""
with io.open(REG,"a",encoding="utf-8") as f: f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
