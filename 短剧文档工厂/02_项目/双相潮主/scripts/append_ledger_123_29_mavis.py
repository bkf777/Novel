#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加脚本（声音设计岗）—— 在本岗父章「一百二十三」内定点插入 §123.29。

【为什么不能用 append_ledger_section_mavis.py / append_ledger_123_mavis.py】
  那两个都是「**新开顶级章**、追加到文件末尾」型；而本岗父章「一百二十三」位于
  文件**中部**（实测行 10417–11623，其后是「## 一百二十四、企划合规」）。
  追加到文件末尾 ⇒ 本节会落进**他人章内** ⇒ 违反单写者纪律（2026-10-23 11:1x
  已因同类错误做过一次带 CAS 的外科修复，见台账 §170.1）。
  ⇒ 本脚本：**在父章末尾（下一顶级章标题行之前）定点插入**，不新增顶级章。

【护栏（全部沿用已实跑验证过的规则）】
  · 父章号中文数字（Q85），子章号阿拉伯（123.29）。
  · 子节号动态取号：解析本岗父章内全部 `### 123.N` → max+1（当前 28 → 29）。
  · 幂等：按**内容特征签名**判定（章号无关）。
  · 写前守卫：① 指纹必须逐字在正文里 ② 目标子节号不得已被他人占用
  · 并发护栏：CAS —— 写盘前重读台账 SHA256，与读盘时不一致 ⇒ 中止不覆盖他人字节。
  · 内建备份 → reports/_bak_ledger_ch123_<时戳>/99_交付说明.md
  · 写后六轴自检：① 插入点前段逐字节一致 ② 后段逐字节一致 ③ `### 123.29` 行首计数＝1
                ④ 本岗子节 1..29 连续 ⑤ 文件增长 ⑥ 全库章号可解析且无重号
  · 写后自检不过：能安全回滚就回滚（他人已动过则不回滚，只报错）。
  · 原子替换：os.replace。
"""
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

# ── 幂等指纹（唯一标识本节；章号无关）────────────────────────────
SECTION_FINGERPRINT = "Chief 报告已送达 · OPS-03 原生 session send · turn_4de220bd-d0fa-43a7-b183-ddfee49f1941"
# ── 本岗父章锚点（中文数字，Q85）────────────────────────────────
PARENT_CN = "一百二十三"
PARENT_NO = 123


def cn2int(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    num = None
    for ch in s:
        if ch in "零一二三四五六七八九":
            num = "零一二三四五六七八九".index(ch)
        elif ch == "十":
            total += (num if num is not None else 1) * 10
            num = None
        elif ch == "百":
            total += (num if num is not None else 1) * 100
            num = None
        else:
            return None
    return total if num is None else total + num


def parse_chapters(text):
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        out.append((cn2int(raw), raw, text[:m.start()].count("\n") + 1))
    return out


def build_body(sub_no):
    return f"""
### 123.{sub_no} ⭐ **回报 Chief 已送达（OPS-03 原生 `mavis session send`）＋ ⭐ Chief 会话 id 的权威定位法（读 `state.json` 的 `sessions` 映射，不要靠「读消息猜身份」）**（声音设计，2026-10-23 11:3x）

#### 123.{sub_no}.1 送达回执（投递状态 ≠ 执行状态 ⇒ 判据只看磁盘）

**{SECTION_FINGERPRINT}**

| 项 | 值 |
|---|---|
| 收件人 | Chief（`bot_6da791c7f983`，`main=true`，role＝总管） |
| 目标会话 | `mvs_eb12a445f1f64ab0826c030acff64004` |
| 通道 | 原生 `mavis session send`（OPS-03 绕行；官方 `message_bot` 本轮 5/5 败） |
| 回执 | `status=accepted`／`mode=queued`／`queue.position=1`（ahead 1）｜turn `turn_4de220bd-d0fa-43a7-b183-ddfee49f1941` |
| 送达内容 | 5 项回报（实测 **3.366906s**／预算 **3.5s**／音频路径／D15 U01 **v1.7｜124,563 B**／validate U01 **11/12｜e30｜w4｜exit 0**）＋ 待重合成 **action 类 10 条**（**非 13 条**）＋ D16 待同步规格 ＋ line_ref 顺移订正 ＋ emotion=angry 映射说明 ＋ 边界声明 ＋ 通道说明 |

⚠️ **`mode=queued` ＝ 已入队 ≠ 已读**（Chief 会话当时正跑一个 turn）⇒ **本岗不重复发送**
（重发＝第二条消息＝重复派单，违反「同一件事只保留一个派单源」）。

#### 123.{sub_no}.2 ⭐ 方法论：定位某 Bot 的会话 id，要读 `state.json` 的 `sessions` 映射，不要靠「读消息猜身份」

- **本轮代价**：为找 Chief 的会话 id，**逐个读消息探查了 9 个候选会话**，其中 **1 个误判**——
  把 Chief 的 `mvs_eb12a445…` 判成了「分镜导演」，理由是**该会话恰好在跑 ffmpeg 抽帧**
  `preview/U01_storyboard/EP003.mp4`。**错因**：Chief 是产线第一责任人，
  **抽帧复核分镜成片本就是它自己会做的事** ⇒ 「某会话在干某岗的活」**不足以判定身份**。
- **正解（一手来源）**：`/Users/ezreal/.minimax/v2/plugin-data/liveboards/minimax-bot/state.json`
  → `sessions` 字典，键为 `bot:<bot_id>` 或 `group:<group_id>`，值内含 `sessionId`：

  | 键 | sessionId | 岗位 |
  |---|---|---|
  | `bot:bot_6da791c7f983` | `mvs_eb12a445f1f64ab0826c030acff64004` | **Chief（总管）** |
  | `bot:bot_19406286feaf` | `mvs_ccccc31ad4a84f88aa487c7bfa75d017` | 企划合规 |
  | `bot:bot_ed165763cc69` | `mvs_5551310bd12145e38eb9fdb11361a9b7` | 故事架构 |
  | `bot:bot_d90c96b11c8e` | `mvs_e2bc283776214551b4f7c53874f643f1` | 台本编剧 |
  | `bot:bot_1855d6ce9cdd` | `mvs_778c258f17b44a92a2a99186e51d7341` | 分镜导演 |
  | `bot:bot_db3fd3817800` | `mvs_287c310a89eb4de981f9c7289b1e58c1` | 视觉设定 |
  | `bot:bot_e3df82ceee20` | `mvs_be3a2719f23e4d5fb5f9e83695074478` | 白模场景师 |
  | `bot:bot_0a60d9bbd4fe` | `mvs_cf34dde3c8ac4cf2b7d4d849a562060d` | **声音设计＝本会话** |

- **两条配套纪律**：
  ① `mavis session list` **不带 bot 身份标签** ⇒ 身份必须另找权威来源，不能靠读内容猜；
  ② **同一岗位可能有多个会话**（本岗即有 2 个：本会话 `mvs_cf34dde3…` ＋
  `mvs_61e9678b…`＝声音设计另一实例；台本编剧至少 3 个）⇒ **职责相似 ≠ 同一会话**，
  发信前必须核 `sessions` 映射，别按职责猜。
- **附带可用面**：同一 `state.json` 还有 `bots`（**每个 Bot 的完整 instructions 原文**）、
  `groups`、`schedules`、`taskBatches`、`helpers` ⇒ **读「岗位指令原文」也该读这里**，
  比从别岗转述里拼更可靠。

#### 123.{sub_no}.3 写通道阻断复盘（`message_bot`／`dispatch_tasks`）

- 本轮 `message_bot` 累计 **5/5 败**，报错统一为「**无法确认工具调用来自哪个正在进行的回复，
  请在当前聊天里重试**」；`dispatch_tasks` 同类报错。
- **不是本岗问题**：视觉设定侧同期亦记「`message_bot` 累计 7/7 全败」⇒ **平台侧 MCP 写通道整体故障**，
  非单岗、非本岗指令问题。
- **绕行（已验证有效）**：原生 `mavis session send`（`session list` 定位 → `session send`）——
  本轮已用它成功送达**分镜导演／企划合规／台本编剧／Chief** 四方。
- **留痕口径**：通道故障时**在回报正文里写明「本条走的是哪条通道」**，
  免得下一位把「绕行送达」误读成「官方通道已恢复」。

#### 123.{sub_no}.4 本岗本轮状态与边界

- **本岗交付物本轮零改动**（本节只动台账）：`units/U01/D15.json` **v1.7｜124,563 B**｜
  sha16 `fd9e33dc3cc47bfa`；`units/U02/D15.json` **v1.2｜78,909 B**｜sha16 `ae41edf88bd34bab`（零改动）。
- **本岗本轮写盘面**：hook mp3 ＋ `items.json`（121 条）＋ `results.json`（121 键）＋ D15 v1.7
  ＋ 派生 `render/units/U01/D15.md` ＋ 新脚本 `add_tts_item_ep001_hook.py`
  ＋ `build_D15_U01.py` 4 处改写 ＋ 台账 §123.25／§123.25.9／§123.26／§123.27／§123.28／**§123.29（本节）**。
- **未改**：D05／D08／D09／D10–D14／D16／D17／D18／`00_项目索引.md`／他岗台账章节正文／
  `03_规格`／`04_工具`；**未生成图片／视频、未提交 H3 付费生成、未投流上架**。
- **在办（未闭合，本岗侧）**：D16 U01 ep1 钩子字幕行同步（归分镜导演，规格已投）｜
  ep001 旁白整批重合成（归用户／出片阶段）｜ep2#4 新音频合成（归用户／出片阶段）｜
  D18 `U01 L2` warning 2→1（归企划合规，本岗对企划合规唯一未闭合派单）。
"""


def main() -> int:
    root = os.path.abspath(".")
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()
    sha_before_read = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ── 幂等：指纹逐字命中 ⇒ 已落 ────────────────────────────────
    if SECTION_FINGERPRINT in text:
        print(f"[NO-OP] 台账已含本节内容指纹（{SECTION_FINGERPRINT[:40]}…），不重复追加")
        return 0

    lines = text.split("\n")

    # ── 定位本岗父章 ────────────────────────────────────────────
    start = next((i for i, l in enumerate(lines)
                  if l.startswith(f"## {PARENT_CN}、")), None)
    if start is None:
        sys.exit(f"[ABORT] 找不到本岗父章「## {PARENT_CN}、」")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))

    # ── 动态取子节号（只认本岗父章内的 123.N）────────────────────
    subs = []
    for i in range(start, end):
        m = re.match(r"^###\s+123\.(\d+)\s", lines[i])
        if m:
            subs.append((int(m.group(1)), i))
    if not subs:
        sys.exit("[ABORT] 本岗父章内未解析到任何 `### 123.N` 子节")
    nums = sorted(n for n, _ in subs)
    if nums != list(range(1, max(nums) + 1)):
        sys.exit(f"[ABORT] 本岗子节号不连续（{nums}）⇒ 需人工核，拒写")
    target_sub = max(nums) + 1

    # ── 写前守卫①：目标子节号不得已被占用 ───────────────────────
    if re.search(rf"(?m)^###\s+123\.{target_sub}\s", text):
        sys.exit(f"[ABORT] §123.{target_sub} 已存在 ⇒ 拒写")

    # ── 写前守卫②：指纹必须逐字在正文里（否则幂等判定恒不成立）──
    body = build_body(target_sub)
    if SECTION_FINGERPRINT not in body:
        sys.exit("[ABORT] 幂等指纹与正文脱钩 ⇒ 幂等判定会恒不成立 ⇒ 拒写")

    # ── 插入点：本岗父章末尾（下一顶级章标题行之前）──────────────
    ins = end
    # 若插入点前有空行，把插入点前移到空行之后（保持段落整洁）
    if ins > 0 and lines[ins - 1].strip() == "":
        ins -= 1
    prefix = "\n".join(lines[:ins])
    suffix = "\n".join(lines[ins:])
    new_text = prefix.rstrip("\n") + "\n\n" + body.strip("\n") + "\n\n" + suffix.lstrip("\n")

    # ── CAS 守卫：写盘前重读 SHA256（他人已改 ⇒ 中止，不覆盖）──
    with open(ledger, "r", encoding="utf-8") as f:
        if hashlib.sha256(f.read().encode("utf-8")).hexdigest() != sha_before_read:
            print("[RETRY] 读盘后台账已被他人改动（SHA256 不一致）⇒ 本轮中止，请重跑")
            return 3

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_ledger_ch{PARENT_NO}_{target_sub}_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(ledger, bak)
    print(f"   · 备份 → reports/_bak_ledger_ch{PARENT_NO}_{target_sub}_{ts}/99_交付说明.md"
          f"（{os.path.getsize(bak)} B）")

    before_bytes = len(text.encode("utf-8"))
    tmp = ledger + ".tmp_12329"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)
    os.replace(tmp, ledger)

    # ── 写后六轴自检 ────────────────────────────────────────────
    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    alines = after.split("\n")
    a1 = after.startswith(prefix.rstrip("\n"))
    a2 = after.rstrip("\n").endswith(suffix.rstrip("\n"))
    a3 = sum(1 for l in alines if re.match(rf"^###\s+123\.{target_sub}\s", l)) == 1
    s2 = next(i for i, l in enumerate(alines) if l.startswith(f"## {PARENT_CN}、"))
    e2 = next((i for i in range(s2 + 1, len(alines)) if alines[i].startswith("## ")), len(alines))
    n2 = sorted(int(m.group(1)) for i in range(s2, e2)
                for m in [re.match(r"^###\s+123\.(\d+)\s", alines[i])] if m)
    a4 = n2 == list(range(1, max(n2) + 1))
    a5 = len(after.encode("utf-8")) > before_bytes
    chaps = parse_chapters(after)
    parsed = [c[0] for c in chaps if c[0] is not None]
    a6 = (len(chaps) == len(parsed)) and (len(parsed) == len(set(parsed)))
    print(f"■ 台账章内定点插入自检：§123.{target_sub}（父章「{PARENT_CN}」行 {s2 + 1}–{e2}）")
    print(f"   ① 插入点前段逐字节一致：{a1}")
    print(f"   ② 插入点后段逐字节一致：{a2}")
    print(f"   ③ `### 123.{target_sub}` 行首计数 ＝ 1：{a3}")
    print(f"   ④ 本岗子节 1..{max(n2)} 连续：{a4}（{n2[0]}..{n2[-1]}，共 {len(n2)} 条）")
    print(f"   ⑤ 文件增长：{a5}（{before_bytes} → {len(after.encode('utf-8'))} B，"
          f"+{len(after.encode('utf-8')) - before_bytes}）")
    print(f"   ⑥ 全库章号可解析且无重号：{a6}（总章 {len(chaps)}｜可解析 {len(parsed)}｜"
          f"重复 {len(parsed) - len(set(parsed))}）")
    if not (a1 and a2 and a3 and a4 and a5 and a6):
        written = hashlib.sha256(after.encode("utf-8")).hexdigest()
        with open(ledger, "r", encoding="utf-8") as f:
            now = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
        if now == written:
            shutil.copy2(bak, ledger + ".tmp_rollback")
            os.replace(ledger + ".tmp_rollback", ledger)
            print("[ROLLBACK] 写后自检未过，且写后无人改动本文件 ⇒ 已从备份原子还原")
            return 3
        print("[ABORT] 写后自检未过，但写盘后本文件已被他人改动 ⇒ 不自动回滚（避免覆盖他人字节）")
        return 3
    print("✅ 台账 §123.%d 落盘并通过六轴自检" % target_sub)
    return 0


if __name__ == "__main__":
    sys.exit(main())
