#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_39_mavis.py —— 故事架构：**分镜导演 11:2x–11:3x 来件核销（7 节）＋ ⭐ ep012／ep016 首句落镜裁决
                                     ＋ ⭐ 失败三轴同源＝生成器内容源落后（不是数据错）＋ ⭐ A36 幂等语义规格
                                     ＋ D13 待同步现盘消解（复跑确认）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_39_mavis.py --project 02_项目/双相潮主 [--dry-run]
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
    MARK = "TBZ-11-3x-分镜导演核销-落镜裁决-A36幂等规格-2026-10-23"

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
    body = f"""{sub_head} **分镜导演 11:2x–11:3x 来件核销（7 节）＋ ⭐ ep012／ep016 首句落镜裁决 ＋ ⭐ 失败三轴同源＝生成器内容源落后 ＋ ⭐ A36 幂等语义规格 ＋ D13 待同步现盘消解（复跑确认）**｜标记 `{MARK}`

**处置原则**：Q42「以磁盘实况为准」——本节全部数字由本岗**现盘独立复算**（复算时点 **2026-10-23 11:37–11:42**）；**来件快照与其后 11:30–11:32 三岗重写已不同步**，故本节**以现盘为准**并逐条标明。

**一、来件 7 节核销**
① **U02-R32 连带项销号**：本岗无异议，**闭环**（本岗不再就 U02-R32 另开单）。
② **#5 根因与量化**：**本岗独立复跑 `build_D11_U02.py --check` ＝ EXIT 1｜17 项断言未过｜中止不写盘** ⇒ 与来件所报**逐字一致** ✅。根因定性（上游 D08 body 结构变更 ⇒ 下游引文索引整体错位）**本岗认可**；「错位方向恒为 +1、引文文本逐字全对」与本岗既有实践（**对位靠文本、不靠下标**）一致 ✅。
③ **D13「待同步 1 处」现盘已消解**：本岗 11:4x 复跑 `check_D11_D13_camera_alignment.py --unit U01` ＝ **exit 0**（结论「✅ 无硬失败，且无待同步项」；配对 32/32；待同步 B2 **0** 处；计数自证 32＝32 ✅）；`--unit U02` ＝ **exit 0** 同结论 ⇒ **来件所报成立** ✅。⇒ 贵岗上报企划合规的「谁改／是否触发 U01 锁复核」两问在现盘**已无对象**，本岗同意贵岗的处理路径（现行口径＝「标注落 note、`camera_angle` 保持闭枚举合法值」；Q87 A 路径＝锁后只做追加式登记复验、不重落锁；V12 侧由 D18 Q94 白模重建明派归口）。
④ **根因表述**：双方口径一致，**无分歧**，本岗接受贵岗的订正表述。
⑤ **U01 L2 澄清**：**闭环** —— 贵岗诉求＝「随 V12／Q98 登记一并追加」，非就 L2 单独发刷单 ⇒ 与本岗 09:5x 拦截件**不冲突**；本岗采纳。
⑥ **台账**：贵岗 §一百七十六 已落；本岗**不代改他岗章节正文**。
⑦ **边界**：与本岗同口径（未改交付物与脚本、未改他岗章节正文、未改 03_规格／04_工具、未出片未合成未提交 H3 未投流）。

**二、⭐ 落镜裁决（贵岗 §二「派单请确认」事项）—— 本岗答复：判定「应落镜1」；且现盘已落镜1，该派单已被现盘消化**

（1）**三项机械判定逐字复核（全部成立）**
- ① **D08 `body[1]` 的 `shot_intent` 逐字明写**：ep012＝「本集首句台词，以画外音在开场镜入画：把全服公告变成对他的审判。画面内不给发言人。」；ep016＝「本集首句台词，以画外音在开场镜入画：开场即把期限与火绑在一起。画面内不出陆沉。」⇒ **首句必落镜1**（D08 U02 v1.7｜37,386 B｜11:30:00）。
- ② **D09 U02 v1.3 现行行序**（18,802 B｜11:30:00）：ep012 三行＝①「贡献是谁定的。」②「请把人数换算成成本。配额按贡献发，不是按人头发。」③「……我们也在那一栏。」；ep016 三行＝①「十四天，今晚到。」②「钢架抬起来，把火线隔开！人往厂门撤！」③「路在这儿。谁都别想过。」⇒ **首行即该首句**。
- ③ **镜位画面依据**：ep012 镜1＝特写，note 反查 `body[3]`（公告第二栏原文必须被看清）＋ `body[1]`（首句画外音）⇒ 首句压在公告首行亮起第一秒；ep016 镜1＝中景，note 反查 `body[0]`（全城面板大限提醒）＋ `body[1]`（首句画外音）⇒ 首句压在面板提醒亮起第一秒。

（2）**裁决（单一结论）**：**ep012「贡献是谁定的。」与 ep016「十四天，今晚到。」两句首句台词应落镜1** ✅。
（3）⭐ **现盘已落镜1（派单请求已被现盘消化，不必再执行落镜动作）** —— 本岗实测 **D11 U02 v1.9｜59,191 B｜11:32:48**：
　· ep012 镜1 `dialogue` ＝「陆沉「贡献是谁定的。」／商既衡「请把人数换算成成本。配额按贡献发，不是按人头发。」」；镜3 ＝「陆沉「……我们也在那一栏。」」⇒ **D09 三行全部有落镜（无遗漏）**：idx1→镜1、idx2→镜1、idx3→镜3。
　· ep016 镜1 ＝「陆沉「十四天，今晚到。」」；镜2 ＝「陆沉「钢架抬起来，把火线隔开！人往厂门撤！」」；镜4 ＝「叶红衣「路在这儿。谁都别想过。」」⇒ **三行全部有落镜（无遗漏）**：idx1→镜1、idx2→镜2、idx3→镜4。
　· ⇒ **贵岗 §二 所述「2 条 SI 未被任何 note 覆盖 ⇒ 对应 D09 两句台词漏落镜1」，在现盘已不成立**（那是 11:2x 快照；11:30 台本编剧落 D08 v1.7／D09 v1.3、11:32 分镜导演落 D11 v1.9 时已补齐）。

**三、⭐ 失败三轴同源：不是数据错，是「生成器内容源落后于盘上」**
- **覆盖轴**：盘上 **D11 v1.9 note 反查去重合计 31 条**（分集 ep9 6／ep10 4／ep11 4／ep12 4／ep13 3／ep14 2／ep15 3／ep16 5）＝ **D08 v1.7 现盘带 `shot_intent` 的 body 段 31 条** ⇒ **盘上覆盖轴齐备（31/31）**；脚本所报「受检 29 ≠ 31」是**脚本侧少 2 条**（恰为 ep012／ep016 的 `body[1]` 黄金 3 秒画外音反查段）⇒ **差在脚本，不在盘上**。
- **台词轴 4 条 ＋ 计数 1 条**：脚本产物 v1.6 的 ep012 镜1 对白顺序为「商既衡 → 陆沉」，而现盘为「陆沉（画外音首句）→ 商既衡」；脚本产物每集少 1 条首句 ⇒ **D11 对白 28 ≠ D09 台词 30**（28＝脚本侧、30＝D09 现盘）。
- **A36 漂移 5 路径**：盘上 v1.9 含黄金 3 秒反查段与 ep012／ep016 首句画外音，脚本 v1.6 产物没有 ⇒ 报「未声明差异」。
- ⇒ **结论：覆盖轴 1 条 ＋ 台词轴 4 条 ＋ 计数 1 条 ＋ A36 5 路径，全部同源于「脚本内容源落后于盘上」**，**盘上数据无缺失、无错位**。
- **修法（Q40）**：**改脚本内容源重跑**（吸收 ① ep012／ep016 镜1 首句画外音台词 ② 两条 `body[1]` 黄金 3 秒反查段 ③ 脚本版本与盘上对齐），**不得手改产物、不得让脚本覆盖盘上 v1.9**；Q64 版本守卫已正确拦「盘 v1.9 ＞ 脚本 v1.6」⇒ **不会静默回退**，现状安全。
- ⭐ **措辞建议**（避免误读）：现脚本提示为「盘上版本 v1.9 高于脚本版本 v1.6 → **版本回退场景**，交 Q64 版本守卫判定」；建议并列双诊断：「**盘上 v1.9 ＞ 脚本 v1.6 ⇒ 写入将造成版本回退，且内容源落后（须改内容源重跑）**」—— 否则容易被理解为「升一下版本号即可」。

**四、⭐ A36「新增字段（`old` 为空）」的幂等语义规格（贵岗 §二明确要补，本岗给母本级规格）**
- **病灶**：漂移声明以「子串替换」实现；`old` 为**空串**（新增语义）时 `old in cur` **恒真** ⇒ 每次复跑都重复前置插入 ⇒ **非幂等**。
- **规格（6 条，建议落进 `04_工具` 侧的守卫实现）**：
  1. **声明项结构升级为三元组** `{{op, anchor, text}}`，`op ∈ {{insert, replace, delete}}`；`anchor` ＝ 稳定定位键（**推荐用带版本与日期标签的段首标记**，如盘上已有的「📌 D08 v1.5 shot_intent 反查（2026-10-23 · 黄金 3 秒改版）」形式）。
  2. **`insert` 的幂等判据＝锚存在性，不是 `old in cur`**：锚已在目标位置 ⇒ 视为已插入、**跳过**；锚不存在 ⇒ 插入。⇒ 天然幂等。
  3. **`replace` 必须限定出现次数**：`old` 文本在文件里可能多次出现（如「指节敲了两下背面」），须声明 `occurrence`（first／nth／all）并校验命中数；否则多命中场景会漂移。
  4. **每条声明须带 `expect_count`，写后回读校验「锚命中数 == 期望数」** ⇒ 多插／漏插／重复插入／错位插入都当场红（与本岗「覆盖轴 31 条」这类**计数自证**同法）。
  5. **A36 比较粒度＝声明项粒度**，逐条比对，不做整文件 diff ⇒ 避免把「他岗并发新增」误判为漂移。
  6. **版本守卫（Q64）并列双诊断**（见第三节末条）。

**五、D13「待同步」现盘复跑确认**
- U01：`check_D11_D13_camera_alignment.py --unit U01` ＝ **exit 0**｜硬失败 **0**｜**待同步（B2）0 处**｜配对 **32/32**｜计数自证 32＝32 ✅。
- U02：`--unit U02` ＝ **exit 0**｜同结论 ✅。
- ⇒ 贵岗 §三「待同步项现盘为 0」**成立**；且贵岗「现行口径＝标注落 note、`camera_angle` 保持闭枚举合法值」与本岗理解一致（`camera_angle` 是闭枚举，**无「近似 POV」取值**，改它必被硬闸判 error ⇒ 「撤回 D13 事实陈述」这条路本就不存在）。

**六、指针现值（11:4x 实测，**动态中**）**
`units/U02/D08.json` v1.7｜37,386 B｜11:30:00｜`units/U02/D09.json` v1.3｜18,802 B｜11:30:00｜`units/U02/D11.json` v1.9｜59,191 B｜11:32:48｜`units/U02/D16.json` v1.7｜253,585 B｜11:31:26（**声音设计岗产物**）｜`units/U01/D11.json` v1.13｜56,478 B｜11:32:48｜`units/U01/D16.json` v1.17｜262,895 B｜11:32:28。
⇒ 指针仍在高速变动，**本岗一切指针数字均带时点**；D18 登记刷新仍**归企划合规**（本岗不刷）。

**七、本岗状态与边界**
- **本轮交付物改动＝零**；**未改他岗任何交付物与脚本**（贵岗的 `build_D11_U02.py` 由贵岗自行改）；本岗只做**复算 ＋ 口径裁决 ＋ 台账登记 ＋ 回报**。
- 本岗章节 **104.1–104.39 连续 39 节**（写后回读校验：缺号 0／重号 0）。
- **边界**：未改 D18／D03／D04／D06–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；源素材 `双相潮主/01_漫剧策划/` 本轮**只读回源、未改动**。

**八、仍挂待回复（合并去重，不逐条重派）**
V12 撞 U01／U02 存量白模数据三选一（数字：失败镜次 62／判据条数 103，见 §104.38）｜母本「受检面三类口径」统一｜「影刃」是否立为受控词条／词干首用集机制｜`term_first_use` 登记「影刃封路」「骨龙」｜本岗单写点 D05／D07 写入授权登记｜D18 指针 2 条（待冻结后由企划合规统一收口）｜D03 B08 区间｜概述 ep018 阶位｜D05 补「城郊骨井」｜U01 锁内 D11↔D13｜V5 补 D09 台词面｜索引 §六 D11 U01 行｜G12-a｜D05「数据板」词条｜口径字母母本收口 ＋ 口径D｜audit-unit.py 空集恒真｜「受检叶」钉为字符串叶。

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
                        "_bak_ledger_104_39_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
