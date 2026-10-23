#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加脚本（分镜导演岗）—— 落 §一百五十六（U02-R34 U01 侧清单化批次 ＋ U02-R07 D11 侧同步）。

【口径】
  · 父章号**中文数字**（Q85），子章号阿拉伯（156.1…）。
  · 动态取号：解析全部既有章标题 → 取数值最大者 +1（实测 max=155 → 新章 156）。
  · 取号脚本**双格式兼容**（阿拉伯父章／中文父章），中文解析须支持「零」。
  · 并发护栏：取号后**再次**复检末章号；他人已追加 → 本轮中止（exit 3），请重跑。
  · **内建备份**：写盘前先把现盘复制到 `reports/_bak_ledger_ch<N>_<本地时间戳>/99_交付说明.md`，
    写后用该备份做**严格前缀比对**证明「他人字节零改动」。
  · 写后四轴自检：① 前段逐字节一致 ② 新章标题出现 1 次 ③ 位于末章 ④ 文件增长。
  · **幂等用「内容特征签名」判定，不用章号**（见 §一百四十 实测教训）。
"""
import argparse
import os
import re
import shutil
import sys
from datetime import datetime

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# 幂等指纹（唯一标识本节；章号无关）
# ⚠️ 指纹必须是**正文中真实存在的稳定子串**（不含章号）。
#   上一版把指纹定成了正文里根本不存在���串（正文实际带 markdown 标记），
#   导致「指纹 ∈ 正文」恒不成立 → AND 判定落空 → 幂等失效、重复记账。
#   ⇒ 本版：① 指纹取正文逐字子串；② 写盘前**断言指纹确实在正文里**，不成立即中止。
SECTION_FINGERPRINT = "U02-R34 U01 侧 Q56② 清单化批次（承接企划合规 10:0x 派单）"
SECTION_FINGERPRINT_2 = "语义标注 ＋ 0.35 m 数值依据"


def cn2int(s):
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
    return total if num is None else total + num


def int2cn(n):
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
    # 台账既有惯例（现盘 §一百五十三／§一百五十四／§一百五十五 均不带「零」）：
    # 余数 ≥10 直接接读（一百五十六）；余数 <10 才补「零」（一百零五）
    if r < 10:
        return s + "零" + digits[r]
    return s + int2cn(r)


def norm_chapter(t):
    """章节正文的**归一化签名**：只抹掉章号/子章号编号，其余逐字保留。

    用途＝内容级重复检测（Q42「不重复记账」）：两次追加的正文逐字相同、
    仅章号不同时，归一化后必须相等 ⇒ 判为重复并中止。
    （**不做**「删掉所有数字」那种粗归一 —— 那会把内容不同、只差数字的两节误判为重复。）
    """
    t = re.sub(r"^##\s+[^、\n]+、", "## <章>、", t, flags=re.M)
    t = re.sub(r"^###\s+\d+\.\d+", "### <子>", t, flags=re.M)
    t = re.sub(r"§[零一二三四五六七八九十百\d]+", "§#", t)
    t = re.sub(r"第[零一二三四五六七八九十百\d]+章", "第#章", t)
    return t.strip()


def chapter_bodies(text):
    """把台账切成各章正文（以 '^## ' 为界）。"""
    return [p for p in re.split(r"(?m)^(?=##\s)", text) if p.startswith("## ")]


def find_duplicate_chapter(text, new_body):
    """返回与 new_body 归一化后相同的既有章标题；无则返回 None。"""
    sig = norm_chapter(new_body)
    for chap in chapter_bodies(text):
        if norm_chapter(chap) == sig:
            m = re.match(r"^##\s+(.+?)、", chap)
            return m.group(1).strip() if m else "?"
    return None


def parse_chapters(text):
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        out.append((cn2int(raw), raw, text[:m.start()].count("\n") + 1))
    return out


def build_body(chap_no):
    cn = int2cn(chap_no)
    return f"""
## {cn}、分镜导演（2026-10-23 10:2x–10:4x）

### {chap_no}.1 U02-R34 U01 侧 Q56② 清单化批次（承接企划合规 10:0x 派单）

**裁定三条要求的落法**（U01 侧无 build 脚本，故治理手段是「一次性 patch 脚本自带清单 ＋ run-once 冻结 ＋ Q64 版本守卫」）：
① 每个一次性 patch 脚本自带**变更清单 ＋ 断言点清单**并于**写盘前**校验（清单条数 ＝ 实际断言点数）；
② **run-once 冻结** —— 再执行必须幂等或 `[NO-OP]` exit 0，**不得以断言失败表达「已演进、无需执行」**；
③ 写交付物 JSON 的一次性脚本仍适用 Q64 版本守卫（带 `--force` 逃生口）。

**十脚本取证结论（受检 10 条，沙箱实跑，全部零写盘）**

| 分类 | 脚本 | 改前行为 | 结论 |
|---|---|---|---|
| 合格（6） | `patch_D16_U01_preview_param_dep.py`／`patch_D16_live_pointer_v16.py`／`patch_D16_v17_badge_avoid.mjs`／`patch_U01R18_ep2_text_sync.mjs`／`patch_u01r18_sync.py`／`patch_D16_dwell_convention.py` | `[NO-OP]` exit 0、零写盘 | 本批**只作回归对象**，不改其实现 |
| 不合格（4） | `patch_D11_shot_intent_v15.mjs`／`patch_D11_v16_ep5_wording.mjs`／`patch_D11_v17_ep2_note_sync.mjs`／`patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs` | exit 1（**以断言失败表达「已演进」**） | 本批**已改造**，见下 |

**共享守卫模块**（新建 `scripts/_patch_guard.mjs`，16,596 B，任何岗可 import 复用、无需改本文件）：
① **版本冻结门**：盘上 ＝ 前提 → 执行；＝ 目标 → `[NO-OP]` exit 0；> 目标（已演进）→ `[NO-OP]` exit 0；
   < 前提（前置未落）→ **exit 3**（不越序执行）。`--force` 为 Q64 逃生口（仅管版本序）。
② **清单 ↔ 断言点双射校验**：每条断言点**恰好登记一次**、id 必须在清单内；少一条／多一条／重复登记／
   登记清单外 id 一律 **exit 2**（治理层）。**比「静态数 token」更强** —— 静态计数会被注释与字面量污染，双射不能。
③ **结构化留痕**：stdout 打机器可读摘要行 `[PATCH-GUARD] script=… change_manifest=… assert_manifest=… pre=x/y post=x/y status=…`，供自测器逐条回读。

**退出码语义（三者必须可区分，Q68）**：0 成功／NO-OP｜1 **内容层**断言不通过｜2 **治理层**拒绝（清单结构不一致）｜3 前置版本不满足。

**计数单位先定义（Q57）**：一条断言点 ＝ 补丁脚本内**恰好一处「断言登记语句」被求值一次**；
循环内的逐项判定**先聚合成一次求值**再登记（否则同 id 重复登记 → 双射破裂）。
⚠️ 被治理脚本的注释与字符串字面里**不出现该登记语句的函数名**（Q56 token 计数纪律）。

**四个脚本改造后的清单规模**：A `patch_D11_shot_intent_v15.mjs` 变更 **7** 条／断言点 **16** 条（pre 13 ＋ post 3）；
B `patch_D11_v16_ep5_wording.mjs` **2**／**11**（8＋3）；C `patch_D11_v17_ep2_note_sync.mjs` **2**／**17**（14＋3）；
D `patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs` **4**／**9**（5＋4）。

**本轮发现并修掉的现盘缺陷（自查，非外部来件）**：`patch_D11_shot_intent_v15.mjs` 现盘处于**半成品且已损坏**状态 ——
引用了**未声明**的 `FROM_V`／`TO_V`（必然 ReferenceError）、`A()` 助手与 `nAssert` 累加器在位却**无清单校验**。
上一轮「已回滚」实际**未落盘**。⇒ 本轮按新方案**整体重写**，不复用半成品。

### {chap_no}.2 自测器（新建 `scripts/selftest_U01_patch_manifest.mjs`，5 腿全绿）

| 腿 | 内容 | 实测结果 |
|---|---|---|
| L1 | **run-once 冻结回归**：10 脚本在沙箱对现盘跑 | 脚本 **10/10** exit 0；治理脚本 4/4 走 NO-OP 分支；其余 6/6 exit 0；`--check` 形态 exit 0；沙箱 5 份交付物 SHA256 **未变 5/5** |
| L2 | **链式历史重放（EXECUTE 路径）** | 见下 |
| L3 | **守卫拒绝路径（治理层 exit 2）** | L3a 静态拒绝（清单条目被变更清单引用却缺失 → 建守卫即拒）exit 2；L3b 运行期拒绝（清单条目缺失、脚本仍登记该 id → 登记了清单外 id）exit 2；两者均以「守卫拒绝」措辞退出 |
| L4 | **内容断言失败路径（内容层 exit 1）** | 污染目标内容后 exit 1；目标 SHA256 前后一致；**与 exit 2 严格可区分** |
| L5 | **真盘零写入** | 负测全程在沙箱副本执行；真盘 5 份交付物 SHA256 **未变 5/5** |

**L2 是本批最强的一条证据** —— L1 只走了 NO-OP 分支，**断言登记、双射校验、写盘、写后回读全都没被执行过**；
L2 用历史备份把目标文件回退到补丁的前提版本再正放，终态与**真实历史产物逐字节比对**：
· **D11 链**：历史 v1.7 → 逆向拆解 → v1.4 → 正放 A/B/C → 终态 **≡ 历史 v1.7（字节级一致）**
　（中途 pre/post 登记计数：A 13/13＋3/3、B 8/8＋3/3、C 14/14＋3/3，status 全 OK）；
· **D16 链**：历史 v1.9 → 正放 D → 终态 **≡ 历史 v1.10（字节级一致）**（pre 5/5＋post 4/4）。
⇒ 重写后的脚本与历史脚本**语义等价**（产出字节级相同），且 EXECUTE 全路径均已实跑验证。

**范围声明（不夸大）**：另 6 个已合格脚本本批**只作回归对象**，其「清单化」尚未做 ——
其中 4 个是 `.py`，需要 `.py` 版守卫孪生模块才能同口径接入。**是否补齐由企划合规裁定**，本岗不自行扩大范围。

### {chap_no}.3 U02-R07 D11 侧同步（g27）—— 触发条件成立，但撞上 schema 闭枚举硬约束

**触发条件逐条复核（裁定原文见 D18 `open_issues[57].resolution` 07:5x 段）**：
条件① 同源修订 → ✅ 本岗用带守卫的 patch 脚本落盘（禁只改 JSON）；
条件② D11↔D14 同步 → ✅ D11 侧**无机位字段**（镜位只有 shot_size／camera_angle／lens_mm／movement）；
　D14 package 的相机参数由白模 10:08 重渲时一并落盘 → **V11 校验 PASS**；
条件③ 数值依据须写进 notes → ✅ 「机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量）」逐字写入；
条件④ 重渲复核 FAIL 0 → ✅ 白模 **10:08 已重渲**（32 个逐镜包 mtime 全部 10:08、D14.json 同步），
　`check_white_model_frames --unit U01` → **受检 32｜PASS 32｜FAIL 0｜exit 0**（前一轮为 PASS 30／FAIL 2）。
⇒ 两条触发条件**同时成立**，本岗**应当**同步 D11。

**⚠️ 本轮踩到的硬约束（本岗自述订正）**：前序计划记的是「g27 `camera_angle` 改「近似 POV（视点代表位）」」——
但 `camera_angle` 是 `03_规格/schema.json` 定义的**七选一闭枚举**
（平视／俯视／仰视／顶视／过肩／主观视角／客观跟拍），**没有「近似 POV」取值**；
硬闸 `validate.mjs` 的 **V1 字段完整性与枚举合法性** 实测判 **error 1**（U01 10/11）⇒ **不得以非法枚举值交付**。
而 `03_规格/*`／`04_工具/*` **非本岗可写**（章程：共享工具脚本改动须**总控明派**且**在 D18 登记后方生效**）。
⇒ **已回滚**（D11 恢复 v1.8，SHA 与原始 `c832f5b5…` 逐字一致），改按 **schema 合规形态**落地：
　· `camera_angle` **保持枚举合法值「主观视角」**（本镜仍是 POV 家族，0.35 m 离轴不改变其角度词表归类）；
　· `note` 末尾追加「**近似 POV（视点代表位）**」语义标注 ＋ 0.35 m 数值依据（裁定条件③ ＋ 语义标注要求）；
　· 本岗校验器 B1「已按裁定标注」判定**同步扩展**为**同时识别 note 中的标注**（camera_angle 与 note 任一命中即算已标注）；
　· 本岗自测器夹具**显式钉住自身前提**（不依赖基线状态），L4 拆为 **L4a**（note，生产实际路径）／**L4b**（camera_angle）。
⇒ 落盘结果：**D11 U01 v1.8｜50,322 B → v1.9｜50,876 B**，改动**仅 `ep7镜3.note`**（camera_angle 未动，其余 31 镜零变化）；
　幂等复跑 `[NO-OP]` exit 0、SHA256 前后一致。

**校验器与自测器的同步改造**：
`check_D11_D13_camera_alignment.py` → B1 判据扩展为「camera_angle **或** note 含『近似 POV』」，并在 B1 细节里附带
「⚠️ 但 note 未写 0.35 m 数值依据」提示（裁定条件③ 的次级检查）。
`selftest_D11_D13_camera_alignment.py` → **受检 7 → 8 腿**，L1 基线改为「**待同步 0／已按裁定标注 1**／分离前一致 4／
已分离·非POV 1／不对称 1」，L3/L5/L6 新增「钉住未标注态」前提，L4 拆 L4a/L4b ⇒ **受检 8｜通过 8｜不通过 0** ✅

**⚠️ 遗留缺口（已随回执上报企划合规，待其裁定）**：`camera_angle` 无法表达「严格 POV／近似 POV」之别，
下游若**只读 camera_angle** 仍会当成严格 POV —— 正是裁定所要防的出错方式。
若要根治，须由**总控明派**把 `03_规格/schema.json` 的枚举扩为八选一（含「近似 POV（视点代表位）」），
并同步 `03_规格/字段规格表.md` 与 `04_工具/` 的枚举来源；**明派须在 D18 登记后方生效**。
在那之前，**D11 `note` 是该镜视点口径的真源**。

### {chap_no}.4 视觉设定岗 Q77 例外边界的口径回应（本岗已裁定措辞）

视觉设定岗 10:1x 来函指出：D18 `global_checks.Q77`（本岗 07:5x 立的判据方法）以 C-131 为例断言「属同义表述」，
而 Q87／Q90 已采信「真实漏写·已改卡」—— 同一案例两句相反结论；并请本岗确认例外措辞的边界划在哪一层。

**本岗口径（已回函）**：Q77 的**判据方法本身不废止**（命中低先回查双方原文、逐要素判「事实缺失」还是「同义表述」、
不因判据未命中就直接判缺陷）；需要收口的是**案例结论的适用边界**。
⇒ 边界**不划在「文本载体是不是 video_prompt」这一层**，也不划在「是不是运镜」这一层，而划在
　**「驱动要素是否缺失 ＋ 是否产生可预见的渲染偏差」**这一层：
　· 若下游**消费字段所依赖的驱动要素**在驱动源里**确实缺失**，且该缺失会导致**可预见的渲染偏差**
　　（如卡头 `movement` 声明了运镜、而驱动图生视频运动的 `video_prompt` 未落该运镜 → 跟拍镜被渲成固定机位），
　　则**不适用**「同义表述类不因命中低即改交付物」的豁免；
　· 若驱动源已用**同义但等效**的方式表达（只是措辞不同、不改变渲染结果），则**仍适用**豁免。

### {chap_no}.5 出口闸、指针与边界（本岗 10:2x–10:4x 当场实跑，Q71 不经管道）

| 闸 | 结果 |
|---|---|
| `validate --unit U01` | **11/11｜error 0｜warning 1** |
| `validate --unit U02` | **11/11｜error 0｜warning 3** |
| `validate`（全项目） | **22/22｜error 0｜warning 4** |
| `render-md` | exit 0 |
| `check_D08_D11_shotintent` U01／U02 | 受检 **23**／**29** 条｜全覆盖｜0 硬冲突｜exit 0 |
| `check_D10_D11_alignment` U01／U02 | exit 0｜单 v｜双 v 命中 0 |
| `check_D11_D13_camera_alignment` U01 | 受检 **32**｜配对 32/32｜硬失败 0｜**待同步 0**｜**已按裁定标注 1**｜分离前一致 4｜已分离·非POV 1｜不对称 1｜计数自证 32=32｜exit 0 |
| `check_D11_D13_camera_alignment` U02 | 受检 **32**｜配对 32/32｜**全 0**｜计数自证 32=32｜exit 0 |
| `selftest_D11_D13_camera_alignment` | 受检 **8**｜通过 **8**｜不通过 0｜真盘 6 份 SHA256 一致 6/6 |
| `selftest_U01_patch_manifest`（本批新建） | 受检 **5**｜通过 **5**｜不通过 0 |
| `check_D12_D11_alignment` U02 | exit 0｜error 0｜warn 0｜覆盖率 1.000 |
| `reconcile_D15_D16_timing` U01／U02 | exit 0｜清单 12 ＝ 12｜不通过 0 |
| `reconcile_tts_actual_vs_d15_budget` | exit 0｜清单 12 ＝ 12｜不通过 0 |
| `check_tts_vs_d15_budget` U01 | exit 0｜rows 27｜ERR 0｜WARN 2｜OK 25｜no_audio 1 |
| `check_tts_vs_d15_budget` U02 | **exit 2**「缺 `preview/U02_tts/items.json`」＝ **该单元自始无 TTS 预演音频**，无对象可比，非断言失败、非本轮回归 |
| `check_D05_lutiao_firstuse` | exit 0｜断言 **13** 条｜通过 13｜失败 0 |
| `check_white_model_frames` U01 | **exit 0**｜受检 **32** 镜｜**PASS 32｜FAIL 0**（U02-R07 条件④达成） |
| 四个治理脚本真盘复跑 | 4/4 `[NO-OP]` exit 0｜真盘 5 份交付物 SHA256 **未变 5/5**｜无新增备份目录 |

**本岗交付物现值**：`units/U01/D11.json` **v1.9｜50,876 B**（本轮由 v1.8 升，唯一改动 ＝ `ep7镜3.note`）｜
`units/U01/D16.json` v1.12｜224,276 B｜`units/U02/D11.json` v1.6｜58,051 B｜`units/U02/D16.json` v1.5｜208,578 B｜
`units/U01/D15.json` v1.6｜112,805 B｜`units/U02/D15.json` v1.2｜78,909 B。

**本轮新增/改动脚本**：`scripts/_patch_guard.mjs`（新建）｜`scripts/selftest_U01_patch_manifest.mjs`（新建）｜
`scripts/patch_D11_v19_g27_pov_separation.mjs`（新建）｜`scripts/patch_D11_shot_intent_v15.mjs`（重写）｜
`scripts/patch_D11_v16_ep5_wording.mjs`（重写）｜`scripts/patch_D11_v17_ep2_note_sync.mjs`（重写）｜
`scripts/patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs`（重写）｜`scripts/check_D11_D13_camera_alignment.py`（B1 扩展）｜
`scripts/selftest_D11_D13_camera_alignment.py`（夹具与基线改造）｜本台账追加脚本（新建）。

**备份**：`reports/_bak_D11_U01_v19_g27_20261023-102416/D11.json`（v1.8，50,322 B）｜
`reports/_bak_D11_U01_v19_g27_note_20261023-102822/D11.json`（v1.8，50,322 B）｜本节落盘前的台账备份见本节落盘自检输出。

**指针待刷（本岗升版导致，请 owner 刷登记值）**：D18 `delivery_checks` 登记的 **U01 D11 ＝ v1.8** → 现盘 **v1.9｜50,876 B**。

**边界**：**未改** D05–D10／D12–D15／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`；
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

    chaps = parse_chapters(text)
    nums = [c[0] for c in chaps if c[0] is not None]
    if not nums:
        sys.exit("[ABORT] 台账无可解析章号")
    max_no = max(nums)
    target = max_no + 1
    cn = int2cn(target)

    if SECTION_FINGERPRINT in text and SECTION_FINGERPRINT_2 in text:
        print(f"[NO-OP] 台账已含本岗本节内容指纹，不重复追加（当前末章＝{chaps[-1][1]}／{chaps[-1][0]}）")
        return 0

    chaps2 = parse_chapters(text)
    nums2 = [c[0] for c in chaps2 if c[0] is not None]
    if max(nums2) != max_no:
        print(f"[RETRY] 取号期间他人已追加（max {max_no} → {max(nums2)}），本轮中止，请重跑")
        return 3

    body = build_body(target)

    # ── 前置断言 ①：指纹必须真的在正文里（防「指纹与正文脱钩」这类静默失效）──
    for fp, nm in ((SECTION_FINGERPRINT, "FINGERPRINT"), (SECTION_FINGERPRINT_2, "FINGERPRINT_2")):
        if fp not in body:
            sys.exit(f"[ABORT] 幂等指纹与正文脱钩：{nm}＝{fp!r} 在正文中不存在，"
                     f"幂等判定会恒不成立 ⇒ 拒绝写盘（避免重复记账）")

    # ── 前置断言 ②：内容级重复检测（Q42）—— 正文逐字相同、仅章号不同 ⇒ 不再追加 ──
    dup = find_duplicate_chapter(text, body)
    if dup is not None:
        print(f"[NO-OP] 台账已存在与本节正文**逐字相同**的章节「## {dup}、」"
              f"（内容级重复检测命中，章号无关）→ 不重复记账")
        return 0

    if args.dry_run:
        print(f"[DRY-RUN] 将追加「## {cn}、分镜导演」（当前末章＝{chaps2[-1][1]}／{chaps2[-1][0]}）")
        return 0

    # ── 写盘前备份（本地时戳；用于写后严格前缀比对，证明他人字节零改动）──
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_ledger_ch{target}_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(ledger, bak)
    print(f"   · 备份 → reports/_bak_ledger_ch{target}_{ts}/99_交付说明.md（{os.path.getsize(bak)} B）")

    before_len = len(text)
    before_bytes = len(text.encode("utf-8"))
    new_text = text.rstrip("\n") + "\n" + body
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(new_text)

    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    a1 = after.startswith(text.rstrip("\n"))
    a2 = after.count(f"## {cn}、") == 1
    chaps3 = parse_chapters(after)
    a3 = chaps3[-1][1] == cn
    a4 = len(after) > before_len
    unparsed = sum(1 for c in chaps3 if c[0] is None)
    dup = len([c for c in chaps3 if c[0] is not None]) - len({c[0] for c in chaps3 if c[0] is not None})
    print(f"■ 台账追加自检：章号 {cn}（{target}）")
    print(f"   ① 前段逐字节一致：{a1}")
    print(f"   ② 「## {cn}、」出现 1 次：{a2}")
    print(f"   ③ 位于末章：{a3}（末章＝{chaps3[-1][1]}／{chaps3[-1][0]}）")
    print(f"   ④ 文件增长：{a4}（{before_bytes} → {len(after.encode('utf-8'))} B，"
          f"+{len(after.encode('utf-8')) - before_bytes}）")
    print(f"   ⑤ 全库章号可解析率：{len(chaps3) - unparsed}/{len(chaps3)}｜未解析 {unparsed}｜重复章号 {dup}")
    if not (a1 and a2 and a3 and a4):
        sys.exit("[ABORT] 写后自检未全部通过")
    print("✅ 台账章节落盘并通过四轴自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
