#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加器：写 §{动态取号}（分镜导演 · D11↔D13 机位/视点交叉核对 ＋ U02-R07 的 D11 侧欠账盘点
＋ 判据误报自订正 ＋ 台本编剧 07:4x 迟到报告按现盘逐项核销）。

【本节记什么】
  1. 新增**只读**校验器 `scripts/check_D11_D13_camera_alignment.py`（判据 A/B/C），
     把 U02-R07 裁定条件②「D11↔D14 同步」与附语义要求「g27 分离后须标注
     『近似 POV（视点代表位）』」变成**机器可检的触发器**；
  2. 新增负测自测器 `scripts/selftest_D11_D13_camera_alignment.py`（沙箱副本，5 腿）；
  3. **本岗判据第一版的一次误报自订正**（Q67 实证：判据须有区分力，误报会造出假缺陷）；
  4. U02-R07 的 **D11 侧欠账盘点**（U02 侧 32/32 配对齐、零视点冲突；U01 侧 g27 待分离，
     含**精确待改字段清单**与**触发条件**）；
  5. 台本编剧 07:4x 迟到报告**按现盘逐项核销**（Q42/Q58/Q72）；
  6. 一处提示级发现（U01 侧 D16 缺结构化面板口径声明）——**本岗不擅改，交企划合规裁定**。

【本追加器的规格（沿用本岗 §117／§120 追加器，不重复实现）】
  1. **动态取号**：扫全文件台账章标题（阿拉伯／中文两式都解析），取 max + 1；
  2. **章号形式**：阿拉伯数字（Q71／OPS-19；历史章节原文一字不改）；
  3. **并发护栏**：落盘前复检末章号与文件尾部；取号后末章变化 → 放弃写盘；
  4. **写后自检**：前段逐字节一致｜本节出现 1 次｜本节位于文件末章；
  5. **幂等**：标题已存在则 [NO-OP]。

用法：python3 scripts/append_ledger_121_mavis.py [--project .]
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

EVENT_TITLE = "D11↔D13 机位/视点交叉核对"


def build_section(num: int) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""

## {num}、分镜导演：**{EVENT_TITLE}**（新只读校验器 ＋ 负测自测器 ＋ 判据误报自订正）＋ **U02-R07 的 D11 侧欠账盘点**（U02 侧 32/32 配对齐零视点冲突；U01 侧 g27 待分离，附精确待改字段清单与触发条件）＋ **台本编剧 07:4x 迟到报告按现盘逐项核销**（分镜导演，{ts}）

> 本节为**本岗当轮独立复核与新增只读校验工具**的留痕。
> **本岗本轮交付物 JSON 零改动**（D11／D15／D16 六份字节与开工逐位一致），
> 只新增 2 个**只读/沙箱**脚本 ＋ 本台账节。
> **未代改任何他岗章节正文**（§七·九）；未代改 D13／D14（属白模场景师）。

### {num}.1 新增只读校验器 `scripts/check_D11_D13_camera_alignment.py`

**为什么要有**：U02-R07 裁定（企划合规 §一百一十六）条件②「若 D11 该镜含机位／视点字段、D14 package 含相机参数，须一并同步」＋附语义要求「g27 分离 0.35 m 后已不是严格 POV，须标注『**近似 POV（视点代表位）**』」——
⇒ 需要一个**机器可复跑**的判据，才能在白模落地（分离完成）那个时点**自动发现「D11 该改、还没改」**，而不是靠人盯台账。

- **只读**：只读 `units/<unit>/D11.json` 与 `units/<unit>/D13.json`，**不写任何文件**。
- **配对规则**：D13 的 `camera_positions` 按 **ep 内 `global_shot_no` 升序**配对 D11 的 `shot_id`（D13 U02 的 gsn 为 33–64，与 U01 连续；U01 为 1–32）。
- **判据 A（配对完整，硬失败）**：D11 每镜都要有唯一机位；缺配对 → **exit 1**。
- **判据 B（视点口径）**：
  - `pov_d11` = D11 `camera_angle` 含「主观」/「POV」；`approx_d11` = 含「近似 POV」；
    `pov_d13` = D13 `notes` 含「眼位重合」/「角色视点」/「视点代表位」。
  - **待同步（提示级）**：`pov_d11` 且 not `pov_d13` → 白模已分离 0.35 m，D11 仍写严格 POV → 按裁定须改「近似 POV（视点代表位）」。
  - **口径不对称（提示级·非缺陷）**：`pov_d13` 且 not `pov_d11`。
  - **分离前一致（通过）**：`pov_d11` 且 `pov_d13`；**已按裁定标注（通过）**：`approx_d11`。
- **判据 C（计数自证）**：打印受检组数（＝D11 镜数）、配对成功数、待同步数、口径不对称数、分离前一致数。

### {num}.2 ⚠️ 本岗判据第一版的**误报自订正**（Q67 实证）

首版把「`pov_d13` 且 not `pov_d11`」判成**硬失败**，在 U01 实跑报出 1 处：
`ep001/镜2`（D13 notes「机位与坐姿眼位重合，正对面板……」 vs D11 `camera_angle`＝「平视」）。
**本岗复核后判定：这是本岗判据的口径不对称误报，不是缺陷**，已降级为提示级。两条理由：

1. **D11 的 `camera_angle` 是俯仰/角度词表**（平视／俯视／仰视／客观跟拍／主观视角），
   其中**只有「主观视角」才是 POV 标记词**；「平视」只描述俯仰角，**不表达「客观」**。
2. **D13 的「眼位重合」是机位几何描述**，当该镜画面主体**不是角色代理体**时
   （`ep001/镜2`＝**特写面板、不给人体**）眼位重合**无害**；真正造成整帧灰板的是
   `ep007/镜3`（g27）——主体是角色代理体，代理体填满画面。

⇒ **教训**：跨文档判据不能把「两套词表的字面差异」当成矛盾；
**先问「两个词表各自在描述什么维度」，再谈一致性**。误报断言会造出假缺陷，
比漏报更贵（会让正确产物被要求返修）。

### {num}.3 负测自测器 `scripts/selftest_D11_D13_camera_alignment.py`（沙箱副本）

**受检 5 条｜通过 5｜不通过 0｜exit 0**；**真盘 6 份交付物 SHA256 前后逐字节一致**（Q68）。

| 腿 | 内容 | 结果 |
|---|---|---|
| L1 | 基线：现盘副本 → exit 0／受检 32／硬失败 0／待同步 0／不对称 1／分离前一致 5 | ✅ |
| L2 | **判据 A 有区分力**：沙箱删 D13 一条机位 → **exit 1** 且输出含「配对缺失」 | ✅ |
| L3 | **判据 B 有区分力**：沙箱把 g27 改成「分离 0.35 m」＋ D11 仍「主观视角」→ 提示「待同步」且 exit 0 | ✅ |
| L4 | **判据 B 收敛**：D11 g27 改「近似 POV（视点代表位）」→「待同步」消失、转「已按裁定标注 1 处」 | ✅ |
| L5 | **真盘零写入**：6 份交付物 SHA256 前后一致 | ✅ |

⚠️ **自测器自身的一处坑（本岗首轮实测留痕）**：首版**多腿共用同一个沙箱目录**，
L2 删掉的机位**残留到 L3/L4** ⇒ 两腿假红。**修法＝每条腿一个全新沙箱副本**
（`fresh()` 逐腿新建）——与本岗既有教训同源（「夹具污染导致腿空转」，Q73 的夹具纪律）。

### {num}.4 U02-R07 的 **D11 侧欠账盘点**（本岗独立实测，09:1x–09:2x）

**现盘实跑**（`check_D11_D13_camera_alignment.py`）：

| 单元 | 受检组数 | 配对 | 硬失败 | 待同步 | 口径不对称 | 分离前一致 | exit |
|---|---|---|---|---|---|---|---|
| U01 | **32** | 32/32 | 0 | 0 | 1（ep1/镜2，非缺陷） | **5** | 0 |
| U02 | **32** | 32/32 | 0 | 0 | 0 | 0 | 0 |

⇒ **U02 侧：D11 v1.6（07:11）↔ D13 v1.0（07:54）机位 1:1 对齐（32/32），零视点冲突，
本岗 U02 侧零欠账**（D11 U02 全 32 镜无 POV 镜，无需「近似 POV」标注）。

⇒ **U01 侧：g27 分离未执行 ⇒ 本轮不改 D11**（现盘「主观视角」与 D13「机位与角色眼位重合」一致，
提前改会与现盘自相矛盾）。**精确待改清单（白模落地后才动）**：

| 镜位 | 现值 | 待改 |
|---|---|---|
| **g27 ＝ ep007/镜3**（gsn 27，D11 `camera_angle`＝「主观视角」／lens 85／近景／固定） | D13 `notes`「机位与角色眼位重合」（距离 0.00000 m） | `camera_angle` → 「**近似 POV（视点代表位）**」；`note` 追加「机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量）」（裁定条件③，禁只写数字不留依据） |
| **g24 ＝ ep006/镜4**（gsn 24，`camera_angle`＝「俯视」／lens 35／中景／升降） | D13 机位 `pos=[44.0, 0.6, 2.4]`、`height_m=2.4`（**非 0.35 m**） | D11 **无机位数值字段**（只有 `shot_size`/`camera_angle`/`lens_mm`/`movement`）→ **倾向不改**；待白模落地后按裁定条件②「D14 package 含相机参数」逐镜包一致性（V11）再核 |

**触发条件（两条同时成立才动 D11）**：
① 白模场景师按裁定条件①③ 落 D13 U01 的 g24／g27 机位距离 0.35 m 并写明依据
（**改 `scripts/build_D13.py` 重跑落盘，禁只改 JSON**，Q40）；
② 重渲后 `check_white_model_frames.py --unit U01` **FAIL 0**
（含 **ep01_shot03 的 1/6 帧灰板同批定位**，裁定条件④）。

**落盘形态（预判）**：U01 侧 D11 **无构建脚本**（仅 U02 有 `build_D11_U02.py`）→
按 **S23「U01 侧不新建构建脚本」**，届时用 **patch 脚本**落盘（带版本守卫 + 数值零改动断言 + 备份），
再跑 `validate --unit U01`（error 0）与 `render-md.mjs`。

**本岗不重复派单**：U02-R07 的执行归属白模场景师，**企划合规已派单**（台账 §一百二十八 L10524：
「此前已派单白模场景师，本岗不重复派单」），本岗只负责**执行那一刻的 D11 同步**。

**裁定现况（本岗独立复现，与 §一百二十八 逐位一致）**：`units/U01/D13.json` 仍 **v1.0｜123,418 B｜mtime 03:39:26**；
`check_white_model_frames.py --unit U01` → **受检 32 镜｜PASS 30｜FAIL 2**
（ep01_shot03 1/6 帧 unique=1 std=0.00；ep07_shot03 6/6 帧 unique=2 std=0.41）；
`units/U01/D14_shots/` 逐镜包仍为 **01:20–01:41 的锁定旧包**（未按 0.35 m 重渲）→ **前置未满足，本轮不同步 D11**。

### {num}.5 台本编剧 07:4x 迟到报告 —— 按现盘逐项核销（Q42／Q58／Q72）

贵岗报告为 **07:4x 时点**，现盘已推进至 **09:2x**。**本岗不重做、不重复记账**；
以下逐项给「**他报旧值 → 现盘现行值**」：

| 项 | 他报（07:4x） | **现盘（09:2x 实测）** | 判定 |
|---|---|---|---|
| U01 D16 | v1.10 | **v1.12｜224,276 B｜08:05:46** | 已被超越 |
| U02 D16 | v1.4｜208,578 B（07:10） | **v1.5｜208,578 B｜08:03:28** | 已被超越 |
| U02 D09 | v1.0 | **v1.1｜17,537 B** | 已被超越 |
| U02 D13／D14 | **未产出**（取景轴受检 0 条） | **D13 v1.0｜119,186 B｜07:54**；**D14 v1.1｜3,487,153 B｜08:32** | 已被超越 |
| D05 | v1.3｜37,225 B（05:46） | **v1.4｜37,249 B**；「律条」`first_use_ep`＝**13**（此值仍成立） | 版本已进一版 |
| `validate --unit U02` | warning **6** | **warning 3**（11/11｜error 0） | 已被超越 |
| `check_D08_D11_shotintent` | U01 受检 23 条 23/23；U02 受检 29 条 29/29 | **本岗 09:2x 复跑逐位一致**（23/23、29/29，0 硬冲突，exit 0） | **仍成立** |
| ep2/镜2（g6）引文销号 | 已自行销号（§六十四 64.4 自纠） | **接受销号**；本岗 D11 U01 v1.8 现行引文与 D08 v1.9 `shot_intent` 逐字一致 | **仍成立** |
| 「读数退出字幕层」口径 | U02 D08 的 8 条归一度行全为 `type=action`，台词/字幕含读数 0 条 | **本岗侧已落实**：D16 U02 **8/8 集**有 `panel_subtitle_rule` ＋ `readout_in_frame`（各集 1 条）；**字幕行含读数 0** | **天然兼容，零改动** |

⇒ **本岗 D11／D16 因贵岗本报告无需任何改动**；本岗交付物六份字节与开工逐位一致。

### {num}.6 一处提示级发现（**本岗不擅改，交企划合规裁定**）

- **事实**：D16 **U02** 侧 8/8 集有结构化面板口径声明（`panel_subtitle_rule` ＋ `readout_in_frame`），
  明确「面板本体弹出的提示/通报文字进字幕层；**读数栏数值留画面、不进字幕层**」；
  而 D16 **U01** 侧 8/8 集**无这两个字段**（U01 的 `panel_subtitle_rule`/`readout_in_frame` 均缺）。
- **行为层已合规**：D16 U01 字幕行含读数 **0** 条；其 6 条面板类字幕行
  （ep1 2 条／ep3 2 条／ep4 1 条／ep8 1 条）均为**面板本体播报**（「倒计时跳到 2 小时 58 分。」等），
  与 U02 口径一致 → **现盘无实质缺陷**，缺的是**结构化声明**（Q57 口径落字段）。
- **本岗为何不直接改**：改 D16 U01 须升版（v1.12 → v1.13），
  而 **D18 `delivery_checks` 现记 U01 D16 ＝ v1.12**（企划合规维护）→ 升版会使**他岗指针失效**、
  需 D18 与索引同步刷新，**属跨岗成本**。
  ⇒ **本岗按单写者与不制造他岗返工原则，仅登记并上报，请企划合规裁定是否值得升版**；
  若裁定要改，落盘形态＝patch 脚本（Q40／S23，不新建 U01 构建脚本）＋ 时码零改动断言。

### {num}.7 U02-R37 双 v 闭合确认（本岗侧）

- 企划合规 **09:06** 已按现盘逐项核销 U02-R37（D18 **v1.93**、`open_issues` 中 `U02-R37.status`＝「**已闭合**」、台账 **§一百二十八**）。
- 本岗侧根因**已修**：`scripts/check_D10_D11_alignment.mjs` 引入归一化 helper `vtag()`（不单纯删 `v`），
  本岗 **09:2x 独立复跑** U01／U02 → `D10 版本：v1.11　D11 版本：v1.8`／
  `✅ 零冲突：D10 v1.11 × D11 v1.8 全口径核查通过` → **单 v**，两单元脚本实印 **双 v 命中 0**，均 **exit 0**。
- 本岗**不重复投递**同内容回执（并行同岗实例 09:05 已投声音设计与群；企划合规已据现盘闭合）。

### {num}.8 本轮出口闸与复核（**09:1x–09:2x 当场实跑**）

| 项 | 结果 |
|---|---|
| `validate.mjs --unit U01` | **11/11｜error 0｜warning 1** |
| `validate.mjs --unit U02` | **11/11｜error 0｜warning 3** |
| `render-md.mjs` | **exit 0** |
| `reconcile_D15_D16_timing.mjs --unit U01／U02` | 均 **exit 0**｜清单 12 ＝ 断言点 12｜不通过 0 |
| `reconcile_tts_actual_vs_d15_budget.mjs` | **exit 0**｜清单 12 ＝ 12｜已评估 12｜不通过 0 |
| `check_D08_D11_shotintent.mjs --unit U01／U02` | 受检 **23／29** 条｜全部覆盖｜0 硬冲突｜exit 0 |
| `check_D10_D11_alignment.mjs --unit U01／U02` | 均 **exit 0**｜**单 v**｜双 v 命中 0 |
| **新增** `check_D11_D13_camera_alignment.py --unit U01／U02` | 受检 **32／32** 组｜硬失败 0｜exit 0 |
| **新增** `selftest_D11_D13_camera_alignment.py` | **受检 5 条／通过 5／不通过 0**｜真盘 6 份 SHA256 一致 |
| `check_D05_lutiao_firstuse.py` | **断言 12 条｜通过 12｜失败 0**（B10 回归面「低阶律条」残留 **0**）→ **该机器闸条目已闭合** |
| `check_white_model_frames.py --unit U01` | **受检 32 镜｜PASS 30｜FAIL 2**（U02-R07 前置未满足） |

### {num}.9 边界

- 本节**只写台账一个文件**；本岗**新增 2 个脚本**（1 个只读校验器 ＋ 1 个沙箱负测自测器）。
- **本岗交付物 JSON 零改动**：U01 D11 **v1.8｜50,322 B**、U01 D16 **v1.12｜224,276 B**、
  U02 D11 **v1.6｜58,051 B**、U02 D16 **v1.5｜208,578 B**、
  U01 D15 **v1.6｜112,805 B**、U02 D15 **v1.2｜78,909 B**（六份字节与开工逐位一致）。
- **未改** D05–D10／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／**他岗章节正文**。
- MD 未手写手改；未生成图片／视频／音频；未合成 TTS／BGM；未提交 H3 付费生成；未投流上架。
- **以上游合规裁决为准**（企划合规 §一百一十六 U02-R07 裁定、§一百二十八、§一百二十七；
  D18 Q30／Q40／Q49／Q57／Q67／Q68／Q73／Q77／OPS-18／OPS-19；S11／S22／S23）。
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
