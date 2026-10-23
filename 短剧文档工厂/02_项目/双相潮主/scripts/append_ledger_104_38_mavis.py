#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_38_mavis.py —— 故事架构：**分镜导演 11:0x 来件核销（8 项）＋ ⭐ D05 v1.7 口径保全核验
                                     ＋ ⭐ V12 双口径收口（62 失败镜次 vs 103 判据条数）
                                     ＋ ⭐ 本岗自闸 A6 第五次精确化（说明位假红）＋ 负测 4/4**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_38_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime


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
    MARK = "TBZ-11-0x-分镜导演核销-D05v17保全-V12双口径-2026-10-23"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    mine = [i for i, l in enumerate(lines) if l.startswith(MY_HEADER)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    i0 = mine[0]

    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK}；未改动台账。")
        return 0

    used = set()
    for l in lines[i0:ins]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    n = max([k for (a, k) in used if a == 104], default=0) + 1
    sub_head = f"### 104.{n}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""{sub_head} **分镜导演 11:0x 来件核销（8 项）＋ ⭐ D05 v1.7 口径保全核验 ＋ ⭐ V12 双口径收口 ＋ ⭐ 本岗自闸 A6 第五次精确化（说明位假红）＋ 负测 4/4**｜标记 `{MARK}`

**处置原则**：Q42「以磁盘实况为准」——本节全部数字由本岗**现盘独立复算**（复算时点 **2026-10-23 11:28–11:35**）；**来件数字与现盘不一致处逐条列明**；**Q30 留痕不改写**——对既有结论只作**追加式订正**。

**一、分镜导演 11:0x 来件 8 项核销**

| # | 来件要点 | 本岗现盘核验（11:3x） | 判定 |
|---|---|---|---|
| ① | 接受本岗 U02 L2 拦截件，且不再就 L2 单独发刷单 | 两单元已分清（见第二节） | ✅ 闭环 |
| ② | 此前要订正的是 **U01** L2，本岗核的是 **U02** L2；U01 L2 已由企划合规 10:59 追加式订正完成（01:22 旧句原字保留） | U02 L2 现行值「warning 3」（08:4x 锁前全量重跑）**仍成立**；U01 L2 段内写「warning 1」**已过期**，现盘 **warning 4**（11:05:53 实跑）⇒ **与来件所报一致** | ✅ 两岗无冲突 |
| ③ | V12 归属印证：V12 warning 明写「白模投影未提供 `pose`／`rotation_euler_deg` 字段，建议白模构建器补该字段」；W3 属判据与数据不同轴；W1/W2 归白模场景师 | **本岗独立复算逐条印证成立**（见第三节双口径表） | ✅ 印证成立 |
| ④ | 请本岗核一眼 **D05 v1.7 的内容口径是否仍是本岗的** | **逐路径 diff 结论：仍是本岗的**（见第二节） | ✅ **已答复** |
| ⑤ | 指针普查 24 组｜一致 15｜不一致 9（7 条黄金 3 秒联动 ＋ 2 条贵岗自有） | 登记刷新**统一归企划合规**（D18 单写点）——本岗无异议；但**指针仍在高速变动**（见第五节） | ✅ 采信，**不再逐次催刷** |
| ⑥ | 闸门现值 U01 11/12｜e30｜w4；U02 11/12｜e32｜w6；全为 V12 白模侧揭盖，既有 33 条零回归 | **本岗 11:3x 复跑逐字一致**：U01 11/12｜**e30｜w4**｜U02 11/12｜**e32｜w6**｜U03 12/12｜**e0｜w10** | ✅ 一致 |
| ⑦ | 本岗 09:3x 报的「2 条 D13 不一致已刷一致」成立（U01/U02 D13 均 v1.1） | 采信 | ✅ 闭环 |
| ⑧ | 贵岗本轮未改任何交付物 JSON、未出片、未合成、未提交 H3、未投流 | 与本岗同口径 | ✅ 边界一致 |

**二、⭐ ④ 答复：D05 v1.7 的内容口径 —— 逐路径 diff 结论「仍是本岗的」**
- **核法**：用本岗自己的落盘脚本 `patch_D05_firstuse_shadow_bone.py`（A2–A9 断言 ＋ A4 回源）在沙箱里**重生成本岗 v1.6**（D05 置回 v1.5 备份 ＋ units 全量副本），再与现盘 v1.7 做**逐路径结构化 diff**。
- **结果（时点 11:34）**：**本岗专有路径被删 0｜现盘新增路径 0｜同路径值不同 4** —— 4 处差异**全部是「骨纹未激活态」口径 ＋ 版本号**：
  ① `glossary/16/definition`（骨纹词条）＋「【首现口径 · 2026-10-23 用户裁决】骨纹自 ep001 即可见但只作未激活态；ep002 同 ep001；ep003 第一次亮起并首次显示归一度读数 0.5%」；
  ② `motifs/1/desc`（＋「ep001-002 以未激活态（纹路不发光）出现，ep003 起点亮」）；
  ③ `power_system/gauge_readings/0]/event`（＋「本行 0.5% 自 ep003 首次亮起时起读」）；
  ④ `version` v1.6 → v1.7。
- ⭐ **本岗专有内容逐字核验全部保全**：`影刃封路 first_use_ep=36` ✅｜`骨龙贯穿/骨龙威压 first_use_ep=26` ✅｜两条 `definition` 的「首用口径」段 ✅（含 ep036／ep026 锚点）。
- ⇒ **答复贵岗**：**v1.7 ＝ 本岗 v1.6 ＋ 贵方总控「黄金 3 秒」批次叠加的三处骨纹首现口径，本岗内容零改动、零丢失**；本岗不认领这三处（属总控裁决直贯），但**认领权保留**（本岗是 D05 单写点，后续母本口径仍走本岗）。
- 附带：贵岗「D05 指针漂移已闭合、D18 登记值仍 v1.5｜38,574 B ⇒ 待刷登记归企划合规」的判断**成立**；本岗**不刷 D18**（非本岗单写点）。

**三、⭐⭐ V12 红灯双口径收口（本岗独立复算）—— 兼对 §104.37 第五节的追加式订正**
- ⭐ **来件与本岗台账的数字不冲突，而是两套口径**（这正是 §104.35 提请母本收口的「口径字母＋统计对象」问题）：
  - **口径①（失败镜次／shot 级）＝ 官方闸 error 数**：U01 **30** ＋ U02 **32** ＝ **62**。
  - **口径②（判据条数／finding 级）＝ V12 逐镜告警里 W 级判定条数**：U01 **46**（W1 9／W2 14／W3 23）＋ U02 **57**（W1 15／W2 11／W3 31）＝ **103**（W1 **24**／W2 **25**／W3 **54**）。
  - ⇒ **贵岗报的 W1 24／W2 25／W3 54 ＝ 103，逐字成立**；本岗此前台账报的「62 条 error 全部形如…」＝ 失败镜次 62。**两者都对，统计对象不同**（一个镜次可含多条判据）。
- ⚠️ **追加式订正（Q30：不改写 §104.37 原文）**：§104.37 第五节把「62」与「W1 9／W2 14／W3 23 等」写在同一句里，**未标明统计对象**，易被读成「62 条判据」⇒ **本节订正：V12 红灯的准确表述＝「失败镜次 62（官方闸 error 口径）／判据条数 103（finding 口径，W1 24／W2 25／W3 54）」，两数须同时给出并各带统计对象**。请总控裁「改数据／改规则／解锁重跑」时**以 62 为闸门口径、103 为归因口径**。
- ⭐ **贵岗「W3 画面最大对象无一例是 CHAR」—— 本岗独立复算逐字成立**：W3 命中 54 处（U01 23＋U02 31）的最大对象类型分布＝**EXT 33／PROP 14／LGT 7，CHAR 0 例**。⇒ 「EXT 是场景外壳、相机入景时必然占幅 100%」的机制解释成立，**W3 确属判据与数据不同轴**（与贵岗提请总控裁的口径一致）。
- **归属三方一致**（本岗不代改 `03_规格/**` 与 `04_工具/**`）：W1/W2 归**白模场景师**（D14 投影占幅数据 ＋ 缺 `pose`／`rotation_euler_deg` 字段）；W3 属**判据口径**问题（规则属主＝企划合规）；对端 D11 `shot_size` 属**分镜导演**。**新规撞存量数据**证据：`rules.mjs` V12 规则 mtime＝**10:51:40** ≺ D14 投影 mtime＝U01 10:08:20／U02 08:32:28。

**四、⭐ 本岗自闸 A6 第五次精确化（说明位假红）＋ Q62 负测 4/4**
- **触发**：为答复④需重生成 v1.6，脚本 **A6 断言触发拒写**：「「骨龙」在已落交付物仍有命中 [('U03','D08.json',10),('U03','D09.json',4)]」。
- **取证结论：这 14 处全是「同形异指」的说明位／清单位，**台本编剧合规**：D08 `episodes[*].compliance_notes[*]`＝「D05 骨龙词条：first_use_ep=26，ep026 之前禁「骨龙」二字，本集只用「骨威」词形（画面面）」；D09 `voice_cards[*].forbidden_words[*]`＝「★ 本单元台词禁出现「骨龙」二字（D05 词条 first_use_ep=26，ep026 之前一律用「骨威」词形）」。⇒ **逐字引述禁令本身**，属登记/说明语境，**不是活跃违规**；且母本机器口径（`rules.json _term_first_use_note`）本就把首用集**只约束台词面与字幕面**。
- **缺陷定性**：A6 原实现＝「units/ 全库原文任一命中即拒写」⇒ 把说明位/清单位算成命中 ⇒ **假红（误报）**，且会让本脚本在现盘上**永久不可用**（与 §104.37 修掉的「受检面硬编码漏检」方向相反：一个漏报、一个误报，**同源于受检面定义没跟着产线走**）。
- **裁定**：**拒写权归 A5（受约束面＝台词面/字幕面）**；**A6 改为分桶记账**（受约束面／说明位·清单位／其它面），**只报告不阻断**。
- ⭐ **负测（Q62）新脚本 `scripts/selftest_D05_bone_scopes.py`，实跑 4 腿｜通过 4｜失败 0**：
  腿1 基线放行（A5 受约束面 **0** ＋ A6 说明位 **14** 处只记账 ＋ 其它面 **0** ＋ 沙箱写盘成功 v1.6）｜腿2 ⭐ **受约束面注入必须拒写**（向 U03 D09 `lines[0].text` 注入「骨龙」⇒ `[ABORT A5]` rc=1）｜腿3 ⭐ **说明位注入必须放行**（向 U03 D08 `compliance_notes[0]` 注入「骨龙」⇒ 不触发 A6、写盘成功）｜**真盘零写入**（`shared/D05.json`／`units/U03/D08.json`／`units/U03/D09.json` 三份 sha256 前后全等）。腿形 == 真盘真实落盘形态；沙箱在 `/tmp`。
- ⭐ **本岗 §104.36 的历史结论**（当时记「「骨龙」在 units/ 全部已落交付物命中 0 ✅ ⇒ 17→26 无回改需求」）**现按追加式订正**：11:2x 台本编剧落 U03 D08／D09 后，全库命中由 **0 → 14**，但**全部在说明位/清单位** ⇒ **实质结论不变（受约束面 0、回改需求 0）**；按 Q30 留痕不改写，原节保留。

**五、指针现值（11:3x 实测，**动态中**，引用前须回盘重取）**
| 产物 | 现值 | 产物 | 现值 |
|---|---|---|---|
| shared/D05 | v1.7｜41,166 B｜11:03:46 | units/U02/D11 | v1.9｜59,191 B｜11:32:48 |
| units/U01/D07 | v1.2｜25,580 B｜11:26:33 | units/U02/D16 | v1.7｜253,585 B｜11:31:26 |
| units/U01/D08 | v1.13｜37,226 B｜11:30:01 | units/U03/D08 | v1.4｜39,660 B｜11:30:26 |
| units/U01/D09 | v1.7｜13,371 B｜11:30:00 | units/U03/D09 | v1.1｜16,017 B｜11:30:13 |
| units/U01/D11 | v1.13｜56,478 B｜11:32:48 | units/U01/D12 | v1.6｜87,127 B｜11:26:33 |
| units/U01/D16 | v1.17｜262,895 B｜11:32:28 | — | — |

- ⇒ **指针仍在高速变动**（11:26–11:33 七分钟内 U01 D08／D09／D11／D16、U02 D11／D16 全部换版）⇒ 再次印证「**不再逐次催刷、待冻结后由企划合规统一收口 D18 与索引 §六**」；本岗台账与回执中一切指针数字**均带时点**。

**六、本岗状态与边界**
- **本轮交付物改动＝零**：D04 v1.2｜D05 v1.7（总控批次）｜U01 D07 v1.2｜U02 D06 v1.2｜U02 D07 v1.3｜U03 D06 v1.0｜U03 D07 v1.0 —— 本岗 U02／U03 四份产物 sha 全等未动。
- **本轮脚本改动 2 份（均为本岗名下）**：`patch_D05_firstuse_shadow_bone.py`（A6 判据第五次精确化 ＋ 账积分桶）｜**新写** `selftest_D05_bone_scopes.py`（Q62 负测四腿）。
- 本岗章节 **104.1–104.38 连续 38 节**（写后回读校验：缺号 0／重号 0）。
- **边界**：本轮**未改** D18／D03／D04／D06–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；源素材 `双相潮主/01_漫剧策划/` 本轮**只读回源、未改动**；负测沙箱在 `/tmp`，**真盘零写入已校验**。

**七、仍挂待回复（合并去重，不逐条重派）**
- **V12 撞 U01／U02 存量白模数据（企划合规/总控裁「改数据／改规则／解锁重跑」）** —— 本节已给出双口径数字（失败镜次 62／判据条数 103）供裁时引用｜**「影刃」是否立为受控词条／是否引入「词干首用集」机制（须总控裁）**｜`term_first_use` 登记「影刃封路」（from=13/until=35）与「骨龙」（from=1/until=25）｜D03 B08 `eps` 区间｜概述 ep018 阶位冲突｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条落点｜口径字母母本收口 ＋ 口径D｜audit-unit.py 空集恒真｜「受检叶」定义钉为字符串叶｜**本岗单写点 D05／D07 写入授权登记（企划合规/总控裁）**｜**D18 指针 2 条（动态中，待冻结后由企划合规统一收口）**。

**以上游合规裁决为准。**"""
    block = [""] + body.split("\n") + [""]

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(MARK) == 1, "A6 标记计数异常"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    bdir = os.path.join(root, "reports",
                        "_bak_ledger_104_38_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(ledp, os.path.join(bdir, "99_交付说明.md"))

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    back_raw = open(ledp, "rb").read()
    back = back_raw.decode("utf-8")
    assert back.count(MARK) == 1, "A7 写后标记计数异常"
    assert back.startswith(pre), "A7 写后前段不一致"
    assert back.endswith(post), "A7 写后后段不一致"
    blines = back.split("\n")
    subnums = sorted(int(m.group(1)) for m in
                     (re.match(r"^### 104\.(\d+)", l) for l in blines) if m)
    gaps = [k for k in range(min(subnums), max(subnums) + 1) if k not in subnums]
    dups = sorted({k for k in subnums if subnums.count(k) > 1})
    assert not gaps, f"A7 本岗子节号有缺号：{gaps}"
    assert not dups, f"A7 本岗子节号有重号：{dups}"
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back_raw)} B；"
          f"追加点＝原第 {ins + 1} 行。落盘时间 {now}")
    print(f"[A7] 写后回读：104.1–{max(subnums)} 连续 {len(subnums)} 节（缺号 0／重号 0）；"
          f"全库 U+FFFD ＝ {back.count(chr(0xFFFD))}；标记命中 1；前段/后段逐字不变；备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
