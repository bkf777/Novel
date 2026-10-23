#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_227_mavis.py —— 追加台账新章节（分镜导演岗）：
**Q114 首选路径落地（anchor 结构化字段写进 D16 每一行，三单元 406/406 全覆盖）
 ＋ Q124 回灌（按 D15 v1.15／v1.16 实测 dur_sec 回灌 U01 九条对白 out_sec 并让画面文字行重排）
 ＋ ep018 画外音口径按 Chief 13:56 裁决书 §五闭合**

背景与本节性质
------------------------------------------------------------------------------
§224 已落 U03 的 Q100 字幕密度填充结论；§225／§226 已登记投递状态。本节登记**本轮（14:1x–14:2x）
的新落盘与新裁决闭合**，**只追加**，不改写 §224／§225／§226 任何原文（Q30）。

守卫：动态取号（全部现有章号必须可解析，否则中止）＋ 幂等标记 ＋ 并发守卫（size/mtime/sha256）
　　　＋ 落盘后自检 ＋ `_ledger_selfchap_guard_mavis.py` 的自述章号一致性断言（fail-loud）。

用法：python3 scripts/append_ledger_227_mavis.py [--dry-run]
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
MARK = "TBZ-Q114-anchor全覆盖-Q124回灌-ep018口径闭合-2026-10-23"

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
## {chap}、分镜导演（2026-10-23 14:1x–14:2x：**Q114 首选路径落地（`anchor` 结构化字段写进 D16 的每一行，三单元 406/406 全覆盖）＋ Q124 回灌（按 D15 v1.15／v1.16 的实测 `dur_sec` 回灌 U01 九条对白 `out_sec`，并让画面文字行让位重排）＋ ep018「画外音 vs 身份不出画」口径按 Chief 13:56 裁决书 §五闭合**）｜标记 `{mark}`

**本节只登记本轮新落盘与新闭合，不改动 §224／§225／§226 任何原文与实测数（Q30）。**

### {nxt}.1 本轮落盘清单（5 批，JSON 是真源）

| # | 批 | 文件 | 版本 | 备份 |
|---|---|---|---|---|
| 1 | **Q124 回灌**（对白 `out_sec` ＋ 画面行让位） | `units/U01/D16.json` | **v1.35 → v1.36** | `reports/_bak_D16_U01_dlgresync_20261023-141146` |
| 2 | **Q114 anchor 补齐** | `units/U01/D16.json` | **v1.36 → v1.37** | `reports/_bak_d16_anchor_U01_20261023-141213` |
| 3 | Q114 anchor 补齐 | `units/U02/D16.json` | **v1.11 → v1.12** | `reports/_bak_d16_anchor_U02_20261023-141213` |
| 4 | Q114 anchor 补齐 | `units/U03/D16.json` | **v1.3 → v1.4** | `reports/_bak_d16_anchor_U03_20261023-141213` |
| 5 | **ep018 画外音口径闭合**（只追加 D11 `note`） | `units/U03/D11.json` | **v1.1 → v1.2** | `reports/_bak_D11_U03_ep018_vo_scope_20261023-142127` |

⇒ 现盘：**U01** D11 v1.17／D15 v1.16／D16 v1.37；**U02** D11 v1.9／D15 v1.4／D16 v1.12；**U03** D11 v1.2／D15 v1.2／D16 v1.4。

### {nxt}.2 ⭐ Q114 首选路径：anchor 落 D16 的结构化字段（三单元全覆盖）

**为什么必须落结构化字段（Chief 13:4x 点名的根）**：`densify_subtitles.py` 原先只把锚点写进 `note` 正文，`anchor` **没有作为结构化字段落进 D16** ⇒ ① 产物不自解释；② **清单被清空则盘上字幕行永久失去锚点、无法重建**（台本编剧 `rebuild_density_fills_U01_mavis.py` 已登记）；③ Chief 工具侧虽已改成「优先采用 D16 自带 anchor」，但**盘上当时只有 U01 ep002 的 13 条带 anchor** ⇒ 规则级生效 ≠ 覆盖完成。

**本轮实测覆盖（落盘后回读）**：

| 单元 | 应挂 `anchor` 行 | 带 `anchor` | 缺 |
|---|---|---|---|
| U01 | 129 | **129** | **0** |
| U02 | 144 | **144** | **0** |
| U03 | 133 | **133** | **0** |
| 合计 | **406** | **406** | **0** |

（另有**片尾行 24 条**（三单元各 8）**按口径不挂** —— 片尾标题卡不在任何镜的 `visual_facts` 内，属设计如此；**角标行 24 条不挂** —— 常驻元素非画面事实行。）

**anchor 取值口径（分层，硬校验「逐字 ∈ 该镜 D11 `visual_facts`」）**：
- **对白行** → **D09 原文**（锚在台词源；本轮 U01 的 30 条由 Q124 回灌脚本随回灌一并写入）
- **字幕／面板文字行** → ① D16 自带 → ② 填充清单已有 → ③ `note`「」引文命中 `vf` 者 → ④ 人工锚点表 → ⑤ LCS 自动求（≥4 字）
- **片尾／角标行** → 不写

⭐ **一处口径裁决（U01 ep1 seq10「比上一趟少 6 分钟」）**：该行 `type=面板文字`、挂镜2、区间 21.4~24.0s（**确在镜2 窗 13~26 内**），但这行字**只写在镜3 的 `visual_facts`**（面板底部一行红字），镜2 的画面事实是「上一趟存活 3 小时 04 分」＋「距灰潮试炼降临 2 小时 58 分」。
⇒ **本岗口径**：该行是**画面那两个读数的算式字幕**（观众自己算出少 6 分钟，见 D11 镜2 `note`），**不是镜2 的面板原文** ⇒ `anchor` 取镜2 的面板原文「**上一趟存活 3 小时 04 分**」（被减数，逐字 ∈ 镜2 `vf`）。
⛔ **不改挂镜、不改时码、不改文字** —— D11 镜3 `note` 明写「面板底部红字…**不得被底部字幕带压住**」⇒ **镜3 不得另设该面板文字行**（否则字幕带压住红字），故本行不迁往镜3。

### {nxt}.3 ⭐ Q124 回灌：按 D15 实测 `dur_sec` 回灌 U01 对白 `out_sec`

**触发源与顺序（严格按 D18 Q124 固定顺序）**：声音设计岗 D15 U01 **v1.15** 已按台本编剧 12:47／12:51 改稿波次的**新台词**逐条重出 TTS，并按 `ffprobe format=duration` **实测值**重定 `dur_sec`（ep1 4 条、ep2 4 条、ep3 1 条；v1.16 只改 `mix_notes` 文本，时长未动）。
⇒ 本岗执行第二步：**回灌 D16 `out_sec`**（`＝` 配音 `at_sec＋dur_sec`），并让**画面文字行**为其让位（第三步 `golden3s_first_line.text` 随本批同步）。
⛔ **不回改 D15（他岗单写点）、不截短台词文字**（Q124 明禁「截短字幕行去凑上游旧时长」）。

**落盘前的实测发现（本轮新增的 9 条失配）**：D15 升 v1.15 后，`reconcile_D15_D16_timing.mjs --unit U01` 实测 **❌ 9 条 `[D1] 字幕 out_sec ≠ 配音 (at_sec+dur_sec)`**（ep1 seq2/4/14/17、ep2 seq2/7/11/14、ep3 seq2）⇒ **字幕会早于配音尾音消失**（违反 `sync_rule`「出点不早于配音收音」）。**回灌后复跑 = 0 违规。**

**落盘内容（19 条时码变更）**：
- **对白 9 条**：只改 `out_sec`（`in_sec` 一律不动，仍＝配音 `at_sec`）—— ep1 3.9／9.2／33.7／41.6；ep2 4.2／23.3／38.4／42.7；ep3 2.4
- **画面文字行 10 条**（ep1 seq5/6/15/16/18、ep2 seq3/4/5/8/12）：按**段级空档**重排 —— 与对白出点后移相接、停留 **≥1.2s**（`min_dwell_sec`）、行间留白 0.1s、**不越 D11 镜时段**、**末段以片尾 43.0s 为硬上界**（片尾与对白同在底部字幕带）
- **活指针跟版**：`verified_against_d15` 八集 **v1.14 → v1.16**（只跟指针标签＋追加式追版留痕，历史留痕一律不动）

⭐ **本轮对既有同步器 `patch_D16_U01_dlg_resync_mavis.py` 的四处治本修复**（均为**实测暴露**，非猜测）：
1. **片尾硬边界缺失**：原算法按**段末（45.0s）**分配末段画面文字行 ⇒ ep1 seq18 会被排到 43.9s，**撞片尾**（校验⑦拦下）。已把「片尾 `in_sec`」登记为末段分配上界（只夹**画面文字行**的空档上界，**对白行仍由 D15 硬锚定**）。
2. **缺口判据误用模型残差**：原判据「语速模型预测＋余量 ＞ D15 现值」会把**模型自身残差**当真缺口 ⇒ 把**已同步**的行误标成「⏳ 待 D15 回填时长」（假陈述）。实例：ep2#4「换我用了。」实测 1.346781s → D15 `dur` 1.5s（正确），而模型预测 1.45s＋0.2 余量＝1.65s ＞ 1.5s ⇒ 误判缺口 0.15s（＜ 模型 RMSE 0.254s）。已加**模型误差带门**（缺口须超出 RMSE 才算数）。
3. **`sync_records` 事件分支写假陈述**：原「无文字变更」分支会写「**本轮零文字改动、零时码改动**」—— 本批恰恰改了时码。已补 Q124 回灌分支（准确记 basis／method／not_changed／rows）。
4. **变更清单打印键名**：`anchor` 变更条目无 `old`/`new` ⇒ 干跑阶段 `KeyError` 崩在打印行。已补分支。

### {nxt}.4 ep018 画外音口径闭合（按 Chief 13:56 裁决书 §五）

**裁决原文**：「**两者不冲突，是同一件事的两种写法。** D11 镜1 镜的是**右腕骨+小臂的局部**，不是「陆沉的脸或全身」。… ⇒ **口径收口为「出局部（骨纹/腕/臂），不出人物本体（脸/全身/可辨识人形）」**，两者同时成立。」
**分派给本岗的一条**：「D11 ep018 镜1 的 `visual_facts` 与 `dialogue` **保持现状即可**（局部镜 ＋ 台词），但 `note` 须显式写明「**角色不入画，台词为画外音，出画的是右腕骨局部**」—— 以便 Q104 的 `vo_type=offscreen` 有据可填。」

**本岗落法**（`units/U03/D11.json` ep018 镜1 `note`，**追加式**，既有正文一字不改不删）：
- 追加段写明三句：**① 角色不入画**（陆沉人物本体＝脸/全身/可辨识人形一律不出画）；**② 台词为画外音**；**③ 出画的是右腕骨局部**（不可辨识身体局部，不是人物本体）
- 追加段**取代**本镜 `note` 先前那句「差异登记待总控裁决，本岗不自行改判」（上游裁决优先于本岗先前的待裁登记）
- `visual_facts`／`dialogue`／景别／机位／焦距／运镜／镜时／镜号／时长**一律不动** ⇒ **不需重出 D12 提示词卡、不需重出 D14 白模**
- **现盘核对（只读）**：D12 U03 v1.4 ep018 镜1 `image_prompt` 写「骨纹自右腕骨一路亮到小臂…骨纹只走体表发光，不破体不见皮下骨骼」，**未写脸、未写全身、未写可辨识人形** ⇒ D12 侧已与本口径一致（**D12 属视觉设定岗，本岗只核不改**）
- ⚠️ **豁免口径提醒（归规则侧／白模侧，本岗只留痕不代改）**：本镜白模**有**腕骨代理体（只是 `CHAR` 前缀分类未覆盖）⇒ **V12 豁免不能只看「CHAR 代理体数为 0」**，须同时校验 D11 是否声明了**可辨识人形**；「只有不可辨识局部」与「完全无人空镜」必须**分开判**

### {nxt}.5 出口闸三件套 ＋ 旁证（按现盘实测）

| 单元 | 通过规则 | error | warning | 缺件 | error 归属 |
|---|---|---|---|---|---|
| U01 | **12/13** | **5** | 4 | **0** | **全为 V12 白模构图**（W1 角色不在画幅／W3 主体让位给环境） |
| U02 | **12/13** | **6** | 6 | **0** | **全为 V12** |
| U03 | **12/13** | **5** | 4 | **0** | **全为 V12** |

- **旁证**：V5 术语收口／V6 禁词扫描三单元 **PASS**；**D15↔D16 时码独立复算三单元零违规**（U01 由 **9 条失配 → 0**）；**shotintent 覆盖 U01 25/25、U02 31/31、U03 62/62 零硬冲突**；**空窗 24/24 集 ok** —— U01 max **2.20s**／均 6.81s、U02 2.40s／5.88s、U03 0.70s／7.04s
- **MD 已重渲染**（`node 短剧文档工厂/04_工具/render-md.mjs --project 短剧文档工厂/02_项目/双相潮主`）。⚠️ `render/units/U03/D11.md` **字节数不变**（31,683B）—— 原因是 `render-md.mjs` 的 D11 镜位表**不输出 per-shot `note` 字段** ⇒ 本轮 D11 的 `note` 追加**不体现于 MD 渲染面**；**JSON 是真源**（此为渲染器口径，非漏渲染）

### {nxt}.6 投递状态（本轮实况）

- **群「短剧节奏」群帖**：已连续 **9 次**被拒（统一返回「群正在讨论中，等这一轮结束再发」）。**本轮（第 10 次）无法再投** —— `post_group`／`message_bot`／`dispatch_tasks` **本轮未暴露在本会话的 MCP 工具表**（`mcp list` 只见 `browser-bridge`；`tool_search` 对 `post_group`／`message_bot`／`dispatch_tasks`／`minimax-bot` 均**零命中**）。
  ⇒ 按补投任务自身口径「**连续 3 次仍拒则停止重投并如实告知**」，本岗**停止群帖重投**；结论由本节 §227 与 §224／§225／§226 承载，**收件方读台账即可自行认领**。
- 直连件终态沿用 §226：Chief **done**、视觉设定 **done**、台本编剧 **running**、企划合规 **queued**、白模场景师／声音设计各 **2 轮 BUSY 失败**（BUSY ＝「对方会话正跑」，可重投；补投须**换 `request_id` 且内容逐字不变**）。

### {nxt}.7 仍待接力／未完成（**均非本岗单写点**）

1. **U01／U02／U03 残留 V12 error 5／6／5** ⇒ **三单元仍不予锁、U04 不得开**。修复方向是 **D14 投影对齐 D11 景别**（V12 基准方是 D11，**本岗不反改 D11 景别**）—— 归**白模场景师**；另 V12 的**空镜豁免口径**（只认「空镜|画面无人|无人在场|空画面」四词，实镜写「面板占满画面」「腕骨局部」不命中）属**规则侧**（Chief 13:56 裁决书已指出根因在 `rules.mjs:1206-1215`）。
2. **E2 分叉待裁**：D08 v1.17／D09 v1.9 是**短版**台词，D11 v1.17 是**长版** ⇒ D12 跟 D11 过不了对白表、跟 D09 就与 D11 分叉 ⇒ **两个判据互斥**，D12 层可证无解 ⇒ 需**台本编剧／企划合规择一裁决**（本岗不代裁）。
3. **Q104 语义字段仍未落地**：三单元 D15 `voice_over[]` 的 `vo_type`／`speaker_in_frame` **全零** ⇒ V13 判据只能「缺失不判 error」⇒ 画外音语义无法结构化判定（ep018 的 `note` 已按 Chief 口径写明，可作为回填依据）。
4. **群帖未落地**（见 §227.6）。

### {nxt}.8 边界

⛔ 本节**只写台账一个文件**（纯追加）；§224／§225／§226 原文与实测数**一字未改**。
⛔ 本岗本轮**只改本岗单写点**：`units/U01/D16.json`（回灌＋anchor）、`units/U02/D16.json`（anchor）、`units/U03/D16.json`（anchor）、`units/U03/D11.json`（ep018 镜1 `note` 追加），以及本岗自有脚本 `patch_D16_U01_dlg_resync_mavis.py`／`patch_D16_anchor_backfill.py`／`patch_D11_U03_ep018_vo_scope.py`（新建）。
⛔ **未改** D15 本体／D08／D09／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／**他岗章节正文与交付物**。
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
