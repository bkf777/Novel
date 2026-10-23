#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_224_mavis.py —— 追加台账新章节（分镜导演岗）：**U03 Q100 字幕密度填充落盘 ＋ D15 落锚回填 ＋ 活指针跟版**

取号
----
动态取「现有最大章号 + 1」，**全部现有章号必须可解析**（有一条解析不了即中止不写盘）——
静默过滤正是历史上跳号的直接成因（台本编剧 §111.4 已登记的规范建议）。
章号按台账尾部现行写法输出**中文式**（如「二百二十四」），与紧邻的 §219–§223 一致。

守卫四件套
----------
① 取号前置断言（章号全可解析）② 幂等（标记命中即不写盘）
③ 并发守卫（写前 size/mtime/sha256 快照复核）④ 落盘后自检（前段逐字节一致／本节出现 1 次／归位正常）
⑤ 追加 `scripts/_ledger_selfchap_guard_mavis.py` 的**自述章号一致性断言**（fail-loud）

用法：python3 scripts/append_ledger_224_mavis.py [--dry-run]
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
MARK = "TBZ-Q100-U03-字幕密度填充-D15回填-2026-10-23"

_D = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_U = {"十": 10, "百": 100, "千": 1000}


def cn2int(s):
    """中文／阿拉伯章号 → 整数；不可解析返回 None。"""
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
    """整数 → 中文式章号（1–9999），与台账尾部现行写法一致。"""
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
    # 「一十X」→「十X」
    return s.replace("一十", "十", 1) if s.startswith("一十") else s


_CN_D = "零一二三四五六七八九"

TEMPLATE = r"""
## {chap}、分镜导演（2026-10-23 13:2x–13:3x：⭐ **U03 的 Q100 字幕密度填充落盘（D16 U03 v1.0 → v1.2，新增 102 行「字幕」类型行）——全集最长空窗 11.00s → 0.70s、平均空窗总 31.91s → 7.04s** ＋ ⭐ **D15 U03 v1.2 落锚回填：`golden3s_first_line` 八集「待 D15 落锚」→「达标」，31 条对白逐条相等，`pending_d15_sync`＝0** ＋ ⭐ **U01／U02 的 `verified_against_d15` 活指针跟到 D15 v1.14／v1.4（数值零改动）** ＋ ⚠️ **群「短剧节奏」群帖连发 4 次被拒（该群本轮讨论未结束）⇒ 已改走 6 份直连件 ＋ 补投提醒**）｜标记 `{mark}`

**处置原则**：Q42「以磁盘实况为准」；Q30「留痕不改写（自我订正用追加式登记）」；**单写者纪律**；**上游合规裁决高于派活指令**。**复算时点 2026-10-23 13:18–13:30。**

### {nxt}.1 交付物落盘清单（本岗单写点）

| 文件 | 版本 | 落盘时点 | 性质 |
|---|---|---|---|
| `units/U03/D16.json` | v1.0 → **v1.2** | 13:18:31／13:21:09 | Q100 字幕密度填充 ＋ D15 落锚回填 |
| `units/U01/D16.json` | v1.31 → **v1.32** | 13:23:06 | 仅 `verified_against_d15` 活指针跟版（**数值零改动**） |
| `units/U02/D16.json` | v1.10 → **v1.11** | 13:23:06 | 同上 |

**未改**：D11（三个单元）／D15 本体／D08／D09／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／他岗章节正文与交付物。MD **未手写／未手改**（`render-md.mjs` 单向渲染，13:2x 复跑 exit 0）。

### {nxt}.2 ⭐ Q100 填充口径（为什么不用「加台词」）

- **起因**：用户反馈「还是很拖啊，白模视频有很长时间什么也没有」。体检 `scripts/audit_dead_time.py` 实测 U03 八集**全集最长空窗 11.00s、平均空窗总 31.91s**（45s 里约 71% 的时间屏幕无字幕）⇒ 八集全判「重拖」（阈值：>4.0s 拖／>6.0s 重拖）。
- **不用「加台词」**：D09 语气卡对陆沉写死「**每集不超过 4 句**」⇒ 改用**画面里的字**（字幕板／面板读数／场景标识）。
- **内容纪律**：每行**逐字锚定该镜 D11 `visual_facts` 已写明的事实**（`anchor` 是 visual_facts 的**字面子串**，由脚本写前硬校验，不命中即中止）⇒ **不新增物件、不编数字、不改镜数与镜时**。
- **停留**：按本厂 4.5 字/秒阅读速度下限估算（向上取 0.1s 网格），且**不小于 1.6s**（高于 D16 的 1.2s 下限）⇒ 不用一闪而过的碎行凑覆盖。
- **落法**：新增行一律为 D16 的「**字幕**」类型行（与 U01／U02 的既有填充同一类型；U03 原本无「面板文字」行）⇒ `no_vo_anchor_rows` 口径不受影响。
- ⭐ **工具链**（本岗本轮新增 4 件，均可复跑）：`scripts/build_density_fills_U03.py`（**文案人工撰写 ＋ 时码由 DP 推算**）→ `scripts/densify_subtitles.py --unit U03`（既有执行器，`FILL_FILES` 接入 U03；5 项硬校验 ＋ 写前指纹并发守卫 ＋ 自动备份 ＋ seq 重排）→ `scripts/patch_D16_U03_d15_backfill.py`（落锚回填）→ `scripts/patch_D16_d15_pointer_refresh.py`（活指针跟版）。
- ⭐ **选行用 DP 而非贪心前缀**（本轮实测踩坑的正解）：空区间能放几行、哪几行最优是背包问题；按「取前 k 条能放下的」，一旦第 k+1 条偏长就整体停下、后面短的也放不进去 ⇒ 区间尾部留下大段空窗。改用 DP 在 `sum(dwell) + (k-1)*SEP ≤ 区间长` 下**最大化覆盖时长**，同覆盖时优先取靠前（优先级高）的行；**每镜第一条保底**（该镜最该被读到的事实放得下就一定排上，避免「覆盖率最大化」把主信息挤掉）。
- ⭐ **打包开销修正**：行间最小间隔 0.2s **只在行与行之间**留（原先行首行尾也各留 0.2s，短区间如 ep17 镜4 仅 2.3s 会一行都放不下）；剩余空隙在 k+1 个空位里尽量均分 ⇒ 最大空窗最小化。

### {nxt}.3 ⭐ 实测数据（前后对比，本岗当场复算）

**空窗体检 `audit_dead_time.py`（三单元 24 集全部 ok，阈值 4.0s）**

| 单元 | 最长空窗（前 → 后） | 平均空窗总（前 → 后） | 判定 |
|---|---|---|---|
| U01 | 2.40s（未动） | 7.19s | 8/8 ok |
| U02 | 2.40s（未动） | 5.88s | 8/8 ok |
| **U03** | **11.00s → 0.70s** | **31.91s → 7.04s** | **8/8 ok（原 8/8 重拖）** |

**出口闸三件套（`validate.mjs --unit <U>`，按现盘实测，非沿用旧坐标）**

| 单元 | 规则数 | error | warning | 缺件 | error 归属 |
|---|---|---|---|---|---|
| U01 | 通过 11/12 | **7** | 2 | 0 | **全为 V12 白模构图**（W1 角色不在画幅／W2 主体占幅越区间／W3 主体让位给环境） |
| U02 | 通过 11/12 | **6** | 4 | 0 | **全为 V12** |
| U03 | 通过 11/12（缺 1 件） | **1** | 4 | 1 | **D14 缺件**（D13 已于 13:05／13:21 落盘） |

> ⚠️ U01／U02 的 error 全部归白模场景师侧：按 §207 诊断口径，修复方向是 **D14 投影占幅去对齐 D11 景别**，**不得反向改 D11 景别**（V12 基准方＝D11）⇒ 本岗**不为了过闸而改景别**，故本岗出口闸**不能报 error 0**。

**其余三轴**：V5 术语收口／V6 禁词扫描三单元 **PASS**（102 行**连 note 全文**双面扫 D05 禁用同义写法零命中、「律条」首用集禁面零命中、`readout_in_frame`「归一度 1.4%」零命中）｜D15↔D16 时码独立复算 `reconcile_D15_D16_timing.mjs` 三单元**零违规**（0 越窗／0 跨切点／逐条同步）｜shotintent 覆盖 U01 **25/25**、U02 **31/31**、U03 **62/62** **零硬冲突**。

### {nxt}.4 ⭐ D15 落锚回填（Q101）＋ 活指针跟版

- **背景**：U03 D16 v1.0 的 `subtitle_sync_audit` 写的是「（未核对）D15 U03 尚未落盘／受检 0 条」、`golden3s_first_line` 逐集 status「待 D15 落锚」——那是 D15 缺件时期的**占位态**，现已过期。声音设计岗 13:0x–13:2x 落 D15 **U01 v1.14／U02 v1.4／U03 v1.2**（台账 §219 已登记）。
- **实测**：D15 U03 v1.2 八集首句**全部 at_sec=0.5**（8/8 达标）；31 条 `voice_over` 与 D16 对白行**逐条相等**（`in_sec`＝`at_sec`、`out_sec`＝`at_sec`＋`dur_sec`）；`reconcile_D15_D16_timing.mjs --unit U03` 独立复算**零违规**。
- **回填结果**（`scripts/patch_D16_U03_d15_backfill.py`，守卫 U03 D16 v1.1／D15 v1.2，结构差异白名单只含 `/version`、`subtitle_sync_audit/**`、`golden3s_first_line/**`）：`golden3s_first_line` 八集 status「待 D15 落锚」→「**达标**」（含 `d15_vo_at_sec`／`d15_vo_dur_sec`／`d15_line_ref`）｜审计镜像按**权威实现 `refresh_audit()` 口径**重刷：31 条对白入 `rows[]`、`synced_row_count` 逐集 4/4/4/4/4/4/3/3、`pending_d15_sync`＝0。
- ⭐ **口径订正**：`no_vo_anchor_rows` 现盘写的是 4/3（＝对白行数，**D15 缺件期的占位口径**），而权威实现 `patch_D16_U01_audit_mirror_and_hook_note.py` 的 `refresh_audit()` 里该字段 ＝ **type=='面板文字' 的行数**（**不是对白数**）⇒ U03 无「面板文字」行 ⇒ 刷成 **0**。此字段若照旧沿用，下游按它判「有几行没有配音锚点」会得到错误结论。
- ⭐ **活指针跟版**（`scripts/patch_D16_d15_pointer_refresh.py`）：U01／U02 的 `subtitle_sync_audit.verified_against_d15` 仍写「v1.13／v1.3」，而 D15 已升 v1.14／v1.4 ⇒ **只跟指针标签 ＋ 追加一条追版复核留痕**。⛔ **不动任何 `in_sec`／`out_sec`／`d15_vo_*` 数值**；⛔ **不动历史留痕**（`sync_records`／`d15_version_history` 里的旧版号是「哪一版做了什么」的历史陈述，全量字符串替换会把审计史改坏）。

### {nxt}.5 ⚠️ 群回报的投递状态（如实登记，不粉饰）

- **群「短剧节奏」（grp_2b2aead14863）群帖连发 4 次均被拒**，返回「群「{name}」正在讨论中，等这一轮结束再发」（群名占位符未渲染属工具侧表现；换 `group_id` 同样被拒）⇒ **群帖至今未落地**。
- ⭐ **投递不押在群消息上**（同 Q30 精神：结论先落盘，再投递）：
  ① **直连 3 份**（`message_bot`）：台本编剧（该群管理员/默认回复位，含其自述章节的 U01 改稿与字数余量两项）、企划合规（三条待裁/待登记）、Chief（知悉 ＋ 请转派白模场景师）；
  ② **直连 3 份接力件**（`dispatch_tasks`）：白模场景师（U03 D14 缺件 ＋ U01/U02 的 V12 残留 7/6 条 ＋ §207 诊断出的规则实现缺陷）、声音设计（U01 ep001/ep002 改稿后的 TTS 预算重出）、视觉设定（新增画面文字行与提示词卡的可读物对齐，并告知本岗自述章号订正已在 §206 闭合、不再挂其账）；
  ③ **已设一次性补投提醒**（7 分钟后重投群帖，`request_id` 固定 ⇒ 幂等）。
- ⇒ **本节即本轮交付的权威副本**：即使群帖持续被拒，结论、实测数、边界、待接力清单**已完整落盘**，收件方读本节即可自行认领。

### {nxt}.6 待接力清单（本岗只报不改，不越他岗文件）

- **白模场景师**：**U03 `D14.json` 仍缺** ⇒ U03 出口闸 error 1／缺件 1、V12 跳过、**锁四条件未满足、U04 不得开**；U01／U02 残留 V12 7／6 条（修复方向＝D14 对齐 D11 景别，不得反改 D11）。⚠️ 另：§207 诊断出一条**规则实现缺陷** —— 角色占幅 100.0% 与环境件 100.0% 同值时，规则比较用严格 `>` 且遍历顺序先遇 EXT ⇒ 判「主体让位给环境」，**角色明明占满画幅仍判失败**（U01 ep01_shot04 1 条）⇒ 建议在白模侧或规则侧修，**别靠改 D11 绕开**。
- **企划合规／Chief**：**ep018「画外音 vs 身份不出画」口径冲突** —— D08 的 SI 写「画面内不出陆沉」，而 D11 镜1 `visual_facts` 含陆沉腕骨纹路这一**不可辨识局部**；并发批次已登记待裁，本岗**未擅自改判**（若裁为「出画」，受影响的是 D11 镜1 的 `visual_facts` 措辞，属本岗域但须先有裁）。
- **企划合规**：**U03 ep018／ep024 的 base 字数余量各只剩 5 字**，下一轮任何加字会破 240（台本编剧已提请登记；本岗复现现盘确认**数字仍成立**）。
- **台本编剧／声音设计**：**U01 ep001／ep002 台词改稿待重定时** —— D16 现盘 `pending_d15_sync` 共 **7 条**（ep1 4 条、ep2 3 条）：D08／D09 已改到新稿而 D16 仍是上一版台词，属「**改稿只传一层**」的跨层分叉；本岗**不擅自回退、不擅自定稿**，待新稿定稿 ＋ D15 重出 TTS 预算后由本岗同步这 7 行的文字与 `out_sec`。
- **故事架构**：**U01 的 D06／D07 两表 `must_happen` 并非逐字相同**（ep001/002/003 不一致，属既存差异），而 U03 脚本 A15 断言「两表逐字相同」在 U01 恒假；企划合规已登记待 Chief 裁决，本岗未擅自改。
- ✅ **已闭合并销号**：本岗 10:0x 回执的自述章号订正（§一百四十一 → §一百四十二）已在 §206 追加式闭合，**不再挂视觉设定的账**（本轮已一并告知）。

### {nxt}.7 边界声明

⛔ 本岗本轮写盘**仅**：`units/U03/D16.json`（v1.2）、`units/U01/D16.json`（v1.32）、`units/U02/D16.json`（v1.11）、本节台账、以及本岗新增/修改的 4 个 `scripts/` 工具与 1 个清单 JSON（`scripts/density_fills_U03.json`）。
⛔ **未改** D11（三个单元）／D15 本体／D08／D09／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／**他岗章节正文与交付物**；**未替任何岗位改写措辞**。
⛔ **未生成**图片／视频／音频，**未合成** TTS／BGM，**未提交** H3 付费生成，**未投流**上架（只出文档与白模的硬边界）。
⛔ 本岗**不改 D11 景别**去迎合 V12；V12 基准方是 D11，修复在白模侧。
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

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (TEMPLATE
            .replace("{chap}", chap)
            .replace("{nxt}", str(nxt))
            .replace("{mark}", MARK)
            .replace("{now}", now))

    ok, msg = G.assert_self_chapno(template=TEMPLATE, rendered=body, chap_num=nxt)
    if not ok:
        raise SystemExit("❌ 自述章号一致性守卫未过：%s" % msg)
    print("   · %s" % msg)

    sec = body.rstrip("\n") + "\n"
    if args.dry_run:
        print("[DRY-RUN] 将追加 §%s（%d 行）；未写盘。" % (chap, len(sec.splitlines())))
        return 0

    # 并发守卫：写前复核（size/mtime/sha256）
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
    heads = re.findall(r"^## (\S+?)、", after_txt, re.M)
    last_head = heads[-1] if heads else None
    mark_n = after_txt.count(MARK)
    print("\n✅ 落盘：%s" % REG)
    print("   · 前段逐字节一致 = %s｜本节章号 = §%s｜出现次数 = %d（应为 1）｜标记命中 = %d（应为 1）"
          % (ok_prefix, chap, len(mine), mark_n))
    print("   · 文件末章 = §%s（应为本节）｜字节数 %d → %d（+%d）"
          % (last_head, len(before_bytes), len(after_bytes), len(after_bytes) - len(before_bytes)))
    print("   · 备份 → %s" % os.path.relpath(bdir, ROOT))
    if not ok_prefix:
        raise SystemExit("❌ 前段被改动 —— 并发写入，需复核")
    if len(mine) != 1 or mark_n != 1:
        raise SystemExit("❌ 归位异常：本节出现 %d 次／标记 %d 次" % (len(mine), mark_n))
    if last_head != chap:
        print("   ⚠️ 末章为 §%s（本节 §%s）⇒ 落盘期间有其他岗追加；本节内容已完整在位，属正常并发。"
              % (last_head, chap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
