#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_42_mavis.py —— 故事架构：**新立并闭合「U03 D06 静默回退雷」＋ A17 反静默回退守卫（含负测）
                                     ＋ U01 两表 must_happen 待裁项的代价量化
                                     ＋ U01 D06/D07 回退雷排查（无雷）＋ 骨纹收口/ep022 销号复核**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**；指针数字**写入时现取**（本仓指针高速变动）。
用法：python3 scripts/append_ledger_104_42_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime


def json_version(p):
    try:
        return json.load(open(p, encoding="utf-8")).get("version", "?")
    except Exception:
        return "?"


def ptr(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return f"`{rel}` 不存在"
    raw = open(p, "rb").read()
    mt = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%H:%M:%S")
    return (f"`{rel}` v{json_version(p)}｜{len(raw):,} B｜{mt}｜"
            f"sha {hashlib.sha256(raw).hexdigest()[:16]}")


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
    MARK = "TBZ-13-4x-U03D06静默回退雷闭合-A17守卫负测-两表代价量化-2026-10-23"

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
    p = {k: ptr(root, v) for k, v in {
        "u01d06": "units/U01/D06.json", "u01d07": "units/U01/D07.json",
        "u03d06": "units/U03/D06.json", "u03d07": "units/U03/D07.json",
        "gen": "scripts/build_D06_D07_U03.py",
        "patch": "scripts/patch_D06_U03_hooktype_back.py",
        "selftest": "scripts/selftest_D06_U03_rollback_guard.py",
    }.items()}

    body = f"""{sub_head} **⭐ 新立并闭合「U03 D06 静默回退雷」＋ A17 反静默回退守卫（含三腿负测）＋ U01 两表 must_happen 待裁项的代价量化 ＋ U01 D06/D07 回退雷排查（结论：无雷）＋ 上一轮两件销号复核**｜标记 `{MARK}`

**触发源**：Chief 13:1x 裁「真风险是**改 JSON 不并回脚本 ⇒ 将来按源脚本重建静默回退**」，台本编剧已在 D08/D09 侧回并并做零漂移自证。**本岗把这条纪律套回自己的交付物自查 ⇒ 命中一枚同型雷，且落点不在 D08，而在 D06。**

**一、上一轮两件的销号复核（13:4x 逐字复验，仍在位）**
- **骨纹措辞收口**：`units/U01/D06.json`「第一次亮起」**2** 处、`units/U01/D07.json`**3** 处；两表「浮出第一道」**0** 处 ⇒ 企划合规「核对成立、销号」的判断在现盘成立 ✅。
- **ep022 场景边界**：`units/U03/D07.json` v1.1，ep022 ＝ `B-16 21:00-21:38 38s` ＋ `B-17 21:38-21:45 7s`，与四段界 12/13/13/7 及 D11 镜1–3=B-16／镜4=B-17 对齐 ✅。

**二、⭐ 新立并闭合：U03 D06 的静默回退雷（同一类病灶，落在 D06）**
- **病灶（13:4x 实锤）**：`units/U03/D06.json` 现盘 v1.1 被并发加上了 8 集的 **`hook_type` / `hook_type_reason`**（schema `D06.episodes` 可选字段，枚举 5 类：悬念/反转/情绪/信息/危机）——**三单元 D06 现都有该字段（U01 v1.4／U02 v1.3／U03 v1.1），D07 均无**（D06 层字段，合规）。
  而本岗生成器 `scripts/build_D06_D07_U03.py` 内 `hook_type` 命中 **0** ⇒ **重跑生成器 = 这 8 集的 hook 字段被整份抹掉**（静默回退，且抹掉的正是「钩子类型」这一短剧节奏判据的输入）。
- **修法（Q40：改内容源后重跑，不手改产物）**：新增 `scripts/patch_D06_U03_hooktype_back.py` —— 值源取**现盘**（已过闸的值，不臆造文案）→ 逐字回并进 `D06_EPISODES`（插在 `foreshadow` 之后，与现盘键序一致）→ `D06_VERSION` v1.0→**v1.1** → 重跑生成器。
- **⭐ 零漂移自证**：沙箱产物与现盘 **JSON 语义完全等价**；字节差 **+1 B**，定位为**尾随换行**（生成器约定带 `\\n`，手工编辑那份没带）⇒ 由生成器规范化落盘（12,137 B → **12,138 B**，语义零变化）。
- **终态**：真盘重跑 `--force` 输出 **`[IDEMPOTENT] units/U03/D06.json 已存在且逐字节一致；未改动`** ＋ **`[IDEMPOTENT] units/U03/D07.json …`** ⇒ **现盘＝生成器产物，重跑不再丢字段**。

**三、⭐ A17 反静默回退守卫（写进生成器本岗自有断言组 A1–A17）**
- **守卫口径**：① 生成器自身产物每集 `hook_type` 必须在 schema 枚举内、`hook_type_reason` 非空；② **现盘若含生成器产不出的字段 ⇒ 源脚本已落后 ⇒ 拒绝写盘**（先回并内容源），而不是照写不误把现盘覆盖回旧形态。
- **负测（证明非恒真）**：`scripts/selftest_D06_U03_rollback_guard.py` 三腿全过 ✅ ——
　① **正测**：现盘＝生成器产物 ⇒ rc=0 且打印 `✓ A17 …`（守卫不误伤正常路径）；
　② **负测**：向沙箱 `units/U03/D06.json` ep017 注入生成器产不出的字段 `__injected_probe__` ⇒ **rc=1** 且命中 `A17`，且**该文件字节零变化**（是「拒绝写盘」，不是「写了再报」）；
　③ **真盘零写入**：全程真盘 D06/D07 的 size+sha256 前后全等。
- **本岗经验（留给全厂）**：守卫必须**负测证明能触发**；且写盘类守卫要验「文件零变化」，否则可能变成「先写了再报错」。

**四、⭐ U01 两表 `must_happen` 待裁项的代价量化（把 §104.41 的登记项做成可裁决形态）**
- **差异面（实测）**：ep001 槽位 2/3、ep002 槽位 3、ep003 槽位 5，共 **4 处**（表述层级不同，无语义冲突）。
- **下游触点（实测，字符串全文命中）**：`D08` **4 处**、`D11` **1 处**，且**全部集中在 ep002 槽位 3 的 D07 侧串**（「全城钟楼敲响十一下」）；其余 3 处差异串在 D08/D11 命中 **0**。
- **⇒ 统一成本（推荐方向）**：**只改 `units/U01/D06.json` 的 4 处措辞、逐字取 D07 侧写法，D08/D11 零改动**（因 D07 侧那串已被下游引用）；反向统一（改 D07）则会牵动 D08/D11 的 5 处引用 ⇒ **成本与风险都不对称**。
- **本岗仍不擅自改**：改动会牵动已落地 D08/D11 的引用面（他岗产物联动），**请 Chief 裁**；本岗已把成本数字备好，裁决后本岗可在 1 轮内改完并复跑 V1/V4/V8。

**五、U01 D06/D07 回退雷排查（结论：无雷）**
本岗逐一读了现存的三个写 `units/U01/D07.json` 的脚本：**`patch_golden3s_ep001.py`**（load→改 ep001 段1 note→save）、**`retime_ep001_panelshot.py`**（load→改 ep001 四段边界→save）、`patch_ledger_refresh_0228.py`（**只读**）⇒ **三者均为 ep001 字段作用域的原地补丁**，**不触碰 ep003 的骨纹措辞** ⇒ **重跑它们不会回退本岗 §104.41 的改动** ✅。
另：U01/U02 的 D06/D07 **无生成器**（本仓 `scripts/` 内确认）⇒ 不存在「按源脚本重建」这一路径；**其 `hook_type` 现为无源手工值**，若日后为 U01/U02 建生成器，**必须先回并这 8/8 集的 hook 字段**（否则同一枚雷会在 U01/U02 复现）。

**六、观察项（本岗不擅改，供企划合规／Chief 判）**
- U03 现盘 `hook_type` 配比：**情绪 3/8（37.5%）✅、信息 2/8（25%）⚠️ 高于 schema 参考 10–20%、悬念 1/8（12.5%）⚠️ 低于参考 20–30%、危机 1/8 ✅、反转 1/8 ✅**。schema 该字段原文为「**可选字段；配比参考**」⇒ 非硬规则；且这些取值**不是本岗写的**（本岗只做回并，值源＝现盘）⇒ **本岗不擅自调整他人取值**，仅登记。

**七、闸门（13:47 现盘复跑）**
```
U01  通过 11/12  error  5   ← 5/5 全为 V12「白模构图一致性（D11 景别 ↔ D14 投影占幅）」；缺件 0
U03  通过 11/12  error  5   ← 5/5 全为 V12；缺件 0（U03 D13/D14 已落 ⇒ V12 真跑，不再是跳过式）
```
- 本岗最相关的规则 **V1（字段完整性）/ V2（跨文件引用）/ V4（时长与四段制边界）/ V8（单元钩子链闭合）全 PASS** ✅；本节改动**未新增任何 error**。

**八、本岗指针现值（写入时现取，**动态中**）**
`{p['u01d06']}`｜`{p['u01d07']}`｜`{p['u03d06']}`｜`{p['u03d07']}`｜`{p['gen']}`｜`{p['patch']}`｜`{p['selftest']}`

**九、本岗状态与边界**
- **本轮改动**：`scripts/build_D06_D07_U03.py`（回并 hook_type ×8 集 ＋ `D06_VERSION` v1.1 ＋ **新增 A17 断言**）｜`units/U03/D06.json`（v1.1，尾随换行规范化，**语义零变化**）｜新增 `scripts/patch_D06_U03_hooktype_back.py`、`scripts/selftest_D06_U03_rollback_guard.py`。
- **未改**：`units/U01/D06.json`／`D07.json`（仅复验，**零改动**）｜`units/U03/D07.json`（**零改动**，仍 sha `8be06f83a7a587f1`）｜D02/D03/D04/D05/D08–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／他岗章节正文；**未改源素材** ⇒ 本轮无 `project.json.gaps_resolved` 新增条目。
- **未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；只出文档与白模。
- 本岗章节 **{sub_head} 已追加**（写后回读校验：缺号 0／重号 0）。

**以上游合规裁决为准（零血腥、D05 术语收口、D03 红线）。**"""
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
    assert new_text.endswith(post), "A7 后段被改动"

    if args.dry_run:
        print(f"[DRY-RUN] 将于 §一百零四 末尾追加 {sub_head}｜{len(body.encode())} B｜标记 {MARK}")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(root, "reports", f"_bak_ledger_104_42_{stamp}")
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(ledp, os.path.join(bdir, "99_交付说明.md"))
    print(f"ℹ️ 备份已落：{bdir}")

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    back_raw = open(ledp, "rb").read()
    back = back_raw.decode("utf-8").split("\n")
    if MARK not in "\n".join(back):
        sys.exit("[ABORT] 写后回读：标记缺失。")
    bl = [i for i, l in enumerate(back) if l.startswith(MY_HEADER)]
    if len(bl) != 1:
        sys.exit("[ABORT] 写后回读：本岗章节命中数异常。")
    bn = [i for i, l in enumerate(back) if i > bl[0] and l.startswith("## ")]
    b_ins = bn[0] if bn else len(back)
    nums = [int(m.group(1)) for l in back[bl[0]:b_ins]
            for m in [re.match(r"^### 104\.(\d+)", l)] if m]
    if len(nums) != len(set(nums)):
        sys.exit("[ABORT] 写后回读：子节号重号。")
    expect = list(range(min(nums), max(nums) + 1))
    if nums != expect:
        sys.exit(f"[ABORT] 写后回读：子节号缺号 {set(expect) - set(nums)}。")
    print(f"✅ 台账已追加：{sub_head}｜子节号 {min(nums)}–{max(nums)} 连续无缺号／无重号｜"
          f"台账 {snap_size:,} B → {len(back_raw):,} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
