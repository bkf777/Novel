#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加脚本（分镜导演岗）—— 落 §一百四十。

【口径】
  · 父章号**中文数字**（Q85 企划合规 09:14 裁定），子章号阿拉伯（140.1…）。
  · 动态取号：解析全部既有章标题 → 取数值最大者 +1（本轮实测 max=139 → 新章 140）。
  · 取号脚本**双格式兼容**：阿拉伯父章（历史遗留）与中文父章都要能解析，
    否则会跳号并撞号。中文解析须支持「零」（如「一百零一」＝101）。
  · 并发护栏：取号后**再次**复检末章号与文件尾部；若他人已追加 → 重新取号。
  · 写后四轴自检：① 前段逐字节一致 ② 新章标题出现 1 次 ③ 位于末章 ④ 计数自证。
  · 幂等：重复执行输出 [NO-OP] 且不写盘。

【单写者纪律】
  本岗只写本岗章节；不代改他岗章节；追加到文件末尾前先确认末章是他人章节时
  仍按 OPS-20 归位（追加到末尾会落进他人章节 → 须节内定点 edit）。
  实际上：若本岗章节不是最后写入者，则**不能**简单追加到文件末尾，
  须插入到正确位置。此脚本按「找到末章标题行 → 在其后插入」处理。

【⚠️ 幂等必须用「内容特征签名」，不能用「章号」（本轮实测踩坑）】
  首版幂等检查是「若台账已存在『## <max+1 的中文>、』则 NO-OP」——
  **这是错的**：第一轮写完后 max 变成新章号，第二次跑时 max+1 又变成下一个号，
  于是**追加出内容完全相同、仅章号不同的第二章**（本轮实测：§140 之后又多出 §141，
  8936 B 重复记账，违反 Q42「不重复记账」）。
  ⇒ 幂等改为**内容特征签名**判定：正文里含本脚本的**唯一指纹**（章节级标识串）
    即判已落盘 → NO-OP。章号无关。
"""
import argparse
import os
import re
import sys

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# ── 幂等指纹（唯一标识本章节；章号无关） ──────────────────────────
# 内容特征串：既出现在标题行下方，也在正文首段 —— 双处命中才算已落盘。
SECTION_FINGERPRINT = "按「是否已分离」语义轴重写（本岗自查订正）"
SECTION_FINGERPRINT_2 = "夹具形态必须 == 真实落盘形态（新增 L5／L6 两条回归腿）"


def cn2int(s):
    """中文数字 → int；阿拉伯数字直返；无法解析返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    num = None
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == "十":
            total += (num if num is not None else 1) * 10
            num = None
        elif ch == "百":
            total += (num if num is not None else 1) * 100
            num = None
        else:
            return None
    if num is None:
        return total
    return total + num


def int2cn(n):
    """int → 中文数字（本岗只需 100–999 区间，但实现覆盖 1–999）。"""
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n < 20:
        return "十" + (digits[n % 10] if n % 10 else "")
    if n < 100:
        s = digits[n // 10] + "十"
        return s + (digits[n % 10] if n % 10 else "")
    s = digits[n // 100] + "百"
    r = n % 100
    if r == 0:
        return s
    if r < 10:
        return s + "零" + digits[r]
    return s + int2cn(r)


def parse_chapters(text):
    """返回 [(数值, 原始标题文本, 行号)]，行号 1-based。"""
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        line = text[:m.start()].count("\n") + 1
        out.append((cn2int(raw), raw, line))
    return out


def build_body(chap_no):
    cn = int2cn(chap_no)
    return f"""
## {cn}、分镜导演（2026-10-23 09:4x–10:0x）

### {chap_no}.1 判据修正：`check_D11_D13_camera_alignment.py` 按「是否已分离」语义轴重写（本岗自查订正）

**背景**：白模场景师于 09:28 把 U01 D13 推到 **v1.1**（123,915 B），g27（ep007/镜3）notes 首次实落
「机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量）；…分离后已不是严格 POV，
本镜为近似 POV（视点代表位）」。本岗实跑既有校验器，却仍把 g27 报成「分离前一致」——**漏报**。

**根因（是我自己的判据缺陷，不是数据问题）**：旧版把「视点代表位」与「眼位重合／角色视点」并入**同一键组**
`pov_d13`，于是「notes 里有没有 POV 词」被当成了「机位与眼位是否已分离」的代理量。白模补记分离时
必然同时写出「视点代表位」→ 旧键组仍为真 → 归入「分离前一致」→ **该报的「待同步」没报**。
⇒ 判据必须改读**语义轴（是否已分离）**，不能读关键词表。

**改法**：判据 B 由 4 类改为 7 类（按分离语义轴）：

| 类别 | 条件 | 处置 |
|---|---|---|
| B1 | D11 已含「近似 POV」 | 已按裁定标注（通过） |
| B2 | D11 严格 POV ＋ D13 **已分离** | **提示级「待同步」** ⭐ 本轮新增的正确检出 |
| B3 | D11 严格 POV ＋ D13 仍重合 | 分离前一致（通过，等白模分离） |
| B4 | D11 严格 POV ＋ D13 未声明眼位关系 | **不判定**（无证据不推定，不提示不阻断） |
| B5 | D11 非 POV 声明 ＋ D13 已分离 | **已分离·非 POV 镜 → 无需改 D11，非欠账** |
| B6 | D11 非 POV 声明 ＋ D13 含眼位表述 | 口径不对称（提示级·**非缺陷**） |
| B7 | 其余 | 无关项 |

**分离优先于重合**：同一句里两者并存时以分离为准（白模补记时两句常并存）。
「已分离」判定＝正则 `分离 <数> m` 或含「已不是严格 POV」或含「近似 POV」。

**实跑（09:5x 当场）**：
- U01：受检 **32** 组｜配对 32/32｜硬失败 0｜**待同步（B2）1 处（ep7 镜3 ＝ g27）**｜分离前一致（B3）4 处｜
  已分离·非 POV（B5）1 处（ep6 镜4 ＝ g24）｜口径不对称（B6）1 处（ep1 镜2）｜计数自证「硬失败 0 ＋ 已分类 32 ＝ 32」✅｜exit 0
- U02：受检 **32** 组｜配对 32/32｜全 0（B7 无关项 32）｜计数自证 32 ＝ 32 ✅｜exit 0（**无假阳性**）

**B5 的意义**：g24（ep006/镜4）D11 `camera_angle`＝「俯视」非 POV 声明，白模分离属常规机位设置，
**本岗不欠账、不改 D11**。此前 §一百三十三 的「g24 倾向不改」由「倾向」升级为「**已判定无需改**」。

### {chap_no}.2 负测自测器：夹具形态必须 == 真实落盘形态（新增 L5／L6 两条回归腿）

**旧版假绿的根因（比判据缺陷本身更值得记）**：旧自测器「全绿」，但**真盘上判据是坏的**。
旧 L3 夹具把 g27 notes 写成**简化措辞**「机位与角色眼位分离 0.35 m（…），视线下俯约 35° 指向右腕」
—— **不含「视点代表位」**，与真实落盘形态不同 ⇒ **夹具把判据缺陷掩盖了**。
⇒ 新纪律：**夹具写成「另一种说法」会掩盖真实措辞的缺陷；负测必须用真盘逐字原文**。

**新自测器 7 腿**（`scripts/selftest_D11_D13_camera_alignment.py`，13,236 B）：

| 腿 | 断言 |
|---|---|
| L1 | 基线：现盘副本 → exit 0／受检 32／硬失败 0／待同步 1／分离前一致 4／已分离·非 POV 1／不对称 1／计数自证 32=32 |
| L2 | 判据 A 有区分力：删 D13 机位 → **exit 1** 且含「配对缺失」 |
| L3 | 判据 B 有区分力：g27 改**真实落盘措辞**、D11 仍「主观视角」→ 含「待同步」且 exit 0 |
| L4 | 判据 B 收敛：D11 改「近似 POV（视点代表位）」→ 待同步消失、转「已按裁定标注 1 处」 |
| L5 | **真实落盘形态回归**：真盘 g27 notes **逐字原文**灌入（与预期原文一致＝True）→ 仍须报「待同步」 |
| L6 | **措辞区分力**：g27 改**同义但无「视点代表位」**的简化措辞 → **仍**须报「待同步」（证明判据读语义轴而非关键词表） |
| L7 | 真盘零写入：6 份交付物 SHA256 前后逐字节一致 |

**实跑**：受检 **7** 条｜通过 **7**｜不通过 **0**｜exit 0；真盘 6 份 SHA256 一致 6/6。

**L5／L6 有区分力的反证（避免恒真断言）**：用**旧判据**在真盘现跑 → **待同步＝0**、分离前一致＝5（**漏报 g27**）；
用**新判据**同现盘 → 待同步＝1 ⇒ 两条腿确实在检验判据，不是恒真通过。

### {chap_no}.3 U02-R07 的 D11 侧：触发条件①已满足，②未满足 → 本岗仍不改 D11

**触发条件（两条同时成立才动 D11）复核**：

| 条件 | 状态 | 现盘证据 |
|---|---|---|
| ① 白模按条件①③ 落 D13 U01 g24／g27＝0.35 m 并写明依据 | ✅ **已满足** | D13 U01 **v1.1**（123,915 B｜09:28:11）；g27 notes 实含「分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量）」且**写明「分离后已不是严格 POV，本镜为近似 POV（视点代表位）」**；g24 notes 同含 0.35 m 依据（水平离轴实取 0.354 m，机位高 +2.40 m 另计） |
| ② 重渲后 `check_white_model_frames --unit U01` **FAIL 0** | ❌ **未满足** | 实跑 **受检 32 镜｜PASS 30｜FAIL 2**（exit 1）：ep07_shot03 **6/6** 帧灰板（unique 2／std 0.41）、ep01_shot03 **1/6** 帧灰板（unique 1／std 0.00）。`units/U01/D14_shots/` 全部 **32** 个逐镜包仍为 **01:41:48 旧包**（ep07_shot03 锚帧仅 8 个、缺 anchor_09，锚帧为 01:20 前素材）→ 白模**只改了 D13 数据、未重渲** |

⇒ **本岗本轮不改 D11**（提前改会与「白模未重渲」的现盘自相矛盾）。
⇒ **一条命令即知**：待白模重渲且 FAIL 0 后，`python3 scripts/check_D11_D13_camera_alignment.py --project . --unit U01`
出现「[待同步] ep7 镜3」即为本岗待改点——按裁定改 g27 `camera_angle`「主观视角」→「**近似 POV（视点代表位）**」
＋ `note` 写 0.35 m 依据（U01 侧无构建脚本 → 按 S23 用 **patch 脚本**，版本守卫＋数值零改动断言＋备份）。
⇒ g24 依 B5 **无需改**。

### {chap_no}.4 台本编剧来件核销：补遗② 三块逐项复现 ＋ 044 数字订正

**补遗②·§一「画面描述面以通称『律条』为准」—— 成立 ✅**（本岗逐字复核）：
- D05 现盘 **v1.5**（38,574 B｜09:17:52）`glossary[34]`（term＝「律条」）definition 逐字含
  「ep013–ep040 台词与字幕不得出现「律条」三字（**画面描述可用**）」「档位修饰语只在需与上位载体并列时用
  「普通律条」／「天律」，其余场合用通称「律条」，不得自造第三种档位修饰语」；`first_use_ep`＝**13** ✅
- 上游真源用的是通称：`units/U02/D06.json` 与 `units/U02/D07.json` `episodes[4].must_happen[2]` ＝
  「**一枚律条出现在交易台上**，苏清辞确认它是真的」；D07 `episodes[4].quad_segments[2].note` ＝
  「**一枚律条压上交易台**，苏清辞摸过纹路确认它是真的，同时说它不能当材料拆用」 ✅
- 正面样板现值：U02 D11 **v1.6**（58,051 B）`episodes[4]`（ep013）镜3 `visual_facts` 逐字为
  「一枚律条被推上交易台，纹路压着冷光，条面朝上完整入画；苏清辞的手摸过纹路，指腹在纹路上停住；
  台面上只有这一枚实物；律条躺在画面正中，四周各留一段台面；右下角常驻白色角标：AI 生成。」，
  同镜 `note` 引 D07 段3 原文并带「📌 D08 shot_intent 反查（2026-10-23）：…已正面拍到」 ✅ **可直接照此推进 U03+**
- 「台面上的货」全库实测（Python 扫描，禁 shell grep 中文 pattern）：`units/` ＋ `shared/` ＋ `project.json`
  ＝ **0 文件 / 0 处**；**台账留痕层 5 处**（他报 3 处 → 逐项订正为 5 处，含本岗 §一百三十三／一百三十五 留痕）✅ 内容面已彻底清零

**补遗②·§二「两处是本岗自身的错、已一致」—— 成立 ✅**（本岗现盘逐字核对）：
- ep012 镜1 现为「商既衡「请把人数换算成成本。配额按贡献发，不是按人**头发**的。」」✅（不是按人头）
- ep015 镜4 现为「陆沉「门禁加固。钢钎和弹药，发到墙位。」／叶红衣「……人比我想的多。」」✅（陆沉先）
- 对照 D09 U02 现盘：ep015 `idx4` LC「门禁加固。钢钎和弹药，发到墙位。」／`idx5` YHY「……人比我想的多。」 ✅ 顺序一致

**补遗②·§三「请把两条断言纳入 `ASSERT_MANIFEST`」—— 本岗侧**已满足**，无需再改 ✅**（本岗实测）：
`scripts/build_D11_U02.py`（70,324 B）`ASSERT_MANIFEST` 现 **39 条**，编号 **A01–A39 连续无缺口**；
静态计数 `chk(` 调用点 **39 处** ＝ 清单 39 条 ✅；
- ① 「D11↔D09 逐条比对（台词轴，受检 28/28）」→ 已在清单内，拆为 **A32–A35**
  （A32 条数一致／A33 角色 char_id 一致／A34 文本逐字一致／A35 解析条数一致）
- ② 「A37 产物全文 0 命中自造档位修饰语『低阶律条』」→ 已在清单内，编号 **A37**（来源「D05 v1.3 律条词条」）
⇒ **他报「请纳入」＝ 请求已由本岗先前落实**；本岗本轮**未改** `build_D11_U02.py`（零改动核销）。

**补遗②·§四 边界**：本岗责任产物本轮**一字未动**（U01 D08 v1.9／D09 v1.5、U02 D08 v1.4／D09 v1.2）✅

**044 第四节数字订正 —— 成立但现值已被超越，逐项订正（他报 → 现盘）**：

| 项 | 他报（08:2x） | 现盘（10:0x 实测） |
|---|---|---|
| U02 D14 产出 | v1.1｜**3,495,016 B**｜08:13:47 | v1.1｜**3,487,153 B**｜**08:32:28**（体量差 7,863 B、时点差 19 分） |
| U02 份数 | 9 份只缺 D14 → 订正为 10 份全齐 | **10 份全齐** ✅（D14_shots 32 个逐镜包在位） |
| U02 出口闸 | warning 5 → 订正为 **3** | **11/11｜error 0｜warning 3** ✅ 一致 |
| U01 出口闸 | warning 1 | **11/11｜error 0｜warning 1** ✅ 一致 |

### {chap_no}.5 故事架构来件核销：U02-R32 连带项 6/6 复现 ＋ 接受对等机制

本岗**独立复算**（不采信转述），6 项全部成立 ✅：

| # | 主张 | 本岗实测 | 结论 |
|---|---|---|---|
| 1 | D11 U02 v1.6／58,051 B | **v1.6｜58,051 B｜07:11:50** | ✅ |
| 2 | 「板面」4→3、「背面」3→4 | **「板面」3 处／「背面」4 处** | ✅ |
| 3 | ep009 shots[2].note 内引文已改「背面」 | note 内**「板面」0／「背面」2**；**D07 U02 ep009 段3 现值整串「灯下露出灰斑，陆沉先看数据板再看人，指节敲了两下背面」逐字出现在该 note 内**（整串包含判定＝True，非抽样） | ✅ |
| 4 | 未改 visual_facts／sfx | 镜3 `visual_facts` 仍为「陆沉没看人脸，先接过数据板，指节在板背面敲了两下…」；`sfx`「指节敲击数据板背面的两声闷响；引擎声退到门外。」**未动** | ✅ |
| 5 | D16 U02「板面/背面」各 0、不引用 D11 版本戳 | **「板面」0／「背面」0**；`D11 v` 版本戳命中 **0** | ✅ |
| 6 | 回归 exit 0、断言 39、shotintent 29/29 | `build_D11_U02.py --check` → **exit 0**、清单 **39 条**；`check_D08_D11_shotintent.mjs --unit U02` → 受检 **29** 条｜29/29｜0 硬冲突｜exit 0 | ✅ |

**接受「D07 段 note 改动前提前告知」对等机制 ✅**（本岗采纳并回执确认）：
本岗承诺：① 改 D07 任一段 `note` 措辞**前**提前告知故事架构，连带范围＝**D11 U02 的 D07 段引文**，
D16 无需动（他报「D16 不引用 D11 版本戳、全文『板面/背面』各 0 处」本岗已独立复现 ✅）；
② 落盘前两边绿灯（本岗三闸 ＋ 故事架构 `build_D11_U02.py --check`）；③ 维持「带断言的补丁脚本」＋ 回执附路径级结构化 diff 清单。

**一处现值刷新（他报终态已被超越）**：
`shared/D05.json` 他报 **v1.4｜37,249 B｜08:31:02** → **现盘 v1.5｜38,574 B｜09:17:52**（体量 +1,325 B、时点 +47 分）；
`units/U02/D09.json` 他报 v1.1 → **现盘 v1.2｜17,859 B｜09:31:35**。
⇒ 其余主张不受影响；**以现盘为准**。

### {chap_no}.6 出口闸（10:0x 当场实跑，禁管道）

| 闸 | 结果 |
|---|---|
| `validate --unit U01` | **11/11｜error 0｜warning 1** |
| `validate --unit U02` | **11/11｜error 0｜warning 3** |
| `validate`（全项目） | **22/22｜error 0｜warning 4** |
| `render-md` | **exit 0** |
| `check_D08_D11_shotintent` U01／U02 | 受检 **23**／**29** 条｜全覆盖｜0 硬冲突｜exit 0 |
| `check_D10_D11_alignment` U01／U02 | exit 0｜**单 v**（D10 v1.11 × D11 v1.8／D11 v1.6）｜双 v 命中 0 |
| `check_D11_D13_camera_alignment` U01 | 受检 **32**｜配对 32/32｜硬失败 0｜**待同步 1**｜exit 0 |
| `check_D11_D13_camera_alignment` U02 | 受检 **32**｜配对 32/32｜全 0｜exit 0 |
| `selftest_D11_D13_camera_alignment` | 受检 **7**｜通过 **7**｜不通过 0｜真盘 6 份 SHA256 一致 6/6 |
| `reconcile_D15_D16_timing` U01／U02 | exit 0｜清单 12 ＝ 断言点 12｜不通过 0 |
| `reconcile_tts_actual_vs_d15_budget` | exit 0｜清单 12 ＝ 12｜已评估 12｜不通过 0 |
| `check_tts_vs_d15_budget` U01 | exit 0｜rows 27｜ERR 0｜WARN 2｜OK 25｜d16_out_mismatch 0｜no_audio 1 |
| `check_tts_vs_d15_budget` U02 | **exit 2**：「缺预演音频清单 `preview/U02_tts/items.json`」→ **该单元自始无 TTS 预演音频**（`preview/U02_tts/` 目录不存在，`preview/` 下仅 U01_tts／U01_video），属**无对象可比**，**非断言失败、非本轮回归、非缺陷** |
| `check_D05_lutiao_firstuse` | exit 0｜断言 **13** 条｜通过 13｜失败 0 |
| `check_white_model_frames` U01 | **exit 1**｜受检 32 镜｜PASS 30｜**FAIL 2**（ep07_shot03 6/6、ep01_shot03 1/6） |

### {chap_no}.7 指针复核与本岗边界

**D18 指针全量复核（24 组 ＝ U01 14 ＋ U02 10）**：D18 现盘 **v1.98**（**535,901 B**，较本岗 §一百三十五 复核时的 v1.97｜521,714 B 又升一版）；
**不一致 1 条**（一致 23/24）—— 较上轮 4 条**收敛 3 条**：

| 项 | 上轮（v1.97） | 本轮（v1.98） |
|---|---|---|
| U01 D05 | 登记 v1.2／现盘 v1.5 ❌ | **已一致** ✅ |
| U01 D10 | 登记 v1.9／现盘 v1.11 ❌ | **已一致** ✅ |
| U01 D16 | 登记 v1.9／现盘 v1.12 ❌ | **已一致** ✅ |
| U02 D12 | 登记 v1.0／现盘 v1.1 ❌ | **已一致** ✅ |
| **U01 D13** | 未列 | **登记 v1.0｜123,418 B／现盘 v1.1｜123,915 B ❌**（白模 09:28 推 v1.1，登记未跟上） |

⇒ 唯一剩余不一致＝**U01 D13**，owner ＝ 白模场景师；已随本轮回执一并告知。

**本岗交付物本轮零改动**：`units/U01/D11.json` v1.8｜50,322 B｜`units/U01/D16.json` v1.12｜224,276 B｜
`units/U02/D11.json` v1.6｜58,051 B｜`units/U02/D16.json` v1.5｜208,578 B（**D11 触发条件②未满足，故不改**）。

**本岗本轮改动**：`scripts/check_D11_D13_camera_alignment.py`（判据重写，12,504 B）、
`scripts/selftest_D11_D13_camera_alignment.py`（7 腿重写，13,236 B）、本台账章节。
**未改** D15／D05–D07／D08／D09／D10／D12／D13／D14／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`；
**未生成**图片／视频／音频，**未合成** TTS／BGM，**未提交** H3 付费生成，**未投流**上架。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()

    # ── 幂等：按**内容特征签名**判定（章号无关；见文件头说明） ────
    chaps = parse_chapters(text)
    nums = [c[0] for c in chaps if c[0] is not None]
    if not nums:
        sys.exit("[ABORT] 台账无可解析章号")
    max_no = max(nums)
    target = max_no + 1
    cn = int2cn(target)
    if SECTION_FINGERPRINT in text and SECTION_FINGERPRINT_2 in text:
        print(f"[NO-OP] 台账已含本岗本节内容指纹（{SECTION_FINGERPRINT[:24]}…），不重复追加")
        print(f"        当前末章＝{chaps[-1][1]}／{chaps[-1][0]}；本节已落盘，章号无关")
        return 0

    # ── 并发护栏：取号后复检末章号与尾部 ─────────────────────────
    chaps2 = parse_chapters(text)
    nums2 = [c[0] for c in chaps2 if c[0] is not None]
    if max(nums2) != max_no:
        print(f"[RETRY] 取号期间他人已追加（max {max_no} → {max(nums2)}），本轮中止，请重跑")
        return 3

    body = build_body(target)

    # ── 并发护栏：确认末章位置（追加位置在末章之后） ────────────
    last = chaps2[-1]
    lines = text.split("\n")
    ins_at = None
    for i, ln in enumerate(lines):
        if ln.startswith(f"## {last[1]}、"):
            ins_at = i
    if ins_at is None:
        sys.exit("[ABORT] 未能定位末章标题行")
    tail = "\n".join(lines[ins_at:]).rstrip("\n")
    if tail:
        new_text = text.rstrip("\n") + "\n" + body
    else:
        new_text = text.rstrip("\n") + "\n" + body

    if args.dry_run:
        print(f"[DRY-RUN] 将追加「## {cn}、分镜导演」到文件末尾（当前末章＝{last[1]}／{last[0]}）")
        return 0

    before_len = len(text)
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(new_text)

    # ── 写后四轴自检 ────────────────────────────────────────────
    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    a1 = after.startswith(text[:before_len].rstrip("\n"))  # 前段逐字节一致
    a2 = after.count(f"## {cn}、") == 1                    # 出现 1 次
    chaps3 = parse_chapters(after)
    a3 = chaps3[-1][1] == cn                              # 位于末章
    a4 = len(after) > before_len                          # 确有增长
    print(f"■ 台账追加自检：章号 {cn}（{target}）")
    print(f"   ① 前段逐字节一致：{a1}")
    print(f"   ② 「## {cn}、」出现 1 次：{a2}")
    print(f"   ③ 位于末章：{a3}（末章＝{chaps3[-1][1]}／{chaps3[-1][0]}）")
    print(f"   ④ 文件增长：{a4}（{before_len} → {len(after)} B，+{len(after) - before_len}）")
    if not (a1 and a2 and a3 and a4):
        sys.exit("[ABORT] 写后自检未全部通过")
    print("✅ 台账章节落盘并通过四轴自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
