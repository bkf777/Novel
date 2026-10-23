#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_41_mavis.py —— 故事架构：**骨纹措辞收口（U01 D06/D07 ep003，5 处）**
                                     ＋ **U03 ep022 场景边界对齐四段制段界（D07 v1.1，改脚本重跑）**
                                     ＋ **台本编剧／分镜导演两件来件核销**
                                     ＋ **新登记发现项：U01 D06/D07 must_happen 两表逐字不一致（既存）**

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
   指针数字**在写入时现取**（本仓指针高速变动，静态写死必过期）。
用法：python3 scripts/append_ledger_104_41_mavis.py --project 02_项目/双相潮主 [--dry-run]
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
    MARK = "TBZ-11-4x-骨纹措辞收口-ep022场景边界对齐段界-2026-10-23"

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
    p_d06 = ptr(root, "units/U01/D06.json")
    p_d07 = ptr(root, "units/U01/D07.json")
    p_u03d06 = ptr(root, "units/U03/D06.json")
    p_u03d07 = ptr(root, "units/U03/D07.json")
    p_script = ptr(root, "scripts/build_D06_D07_U03.py")

    body = f"""{sub_head} **骨纹措辞收口（U01 D06/D07 ep003，5 处）＋ U03 ep022 场景边界对齐四段制段界（D07 v1.1，改脚本重跑）＋ 两件来件核销**｜标记 `{MARK}`

**处置原则**：本节全部数字由本岗**现盘独立复算**（复算时点 **{now}**）；来件快照取 11:38–11:40，本岗不据快照改写，**一律以现盘为准**。

**一、来件核销（两件，均成立）**
① **台本编剧 §四「@故事架构」** —— D07 的 U01 ep003 三处（`answer`／`must_happen`／`cost`）仍写「浮出第一道」，与 D05 已收口口径冲突，**请按上游改** ⇒ **成立，本岗已改**（详见第二节）。
② **分镜导演 §三「@故事架构」** —— ep022 场景边界对不齐：D07 场景 B-16＝32s／B-17＝13s，四段边界是 12/13/13/7，32.0s 落在镜3（25–38s）内 ⇒ **成立，本岗已改**（详见第三节）。

**二、⭐ 骨纹措辞收口（U01 D06/D07 ep003）**
- **定性（先分清性质，不夸大）**：D05 词条「骨纹」的 `forbidden_synonyms` ＝ `破体骨刺`／`骨头长出体外`／`附魔骨骼` —— **「浮出第一道」不在禁用同义词表内**，故此项**不是禁用同义词违规**，而是**口径未统一**（母本自述与正文写法分叉）。
- **母本唯一写法（D05 v1.7 词条「骨纹」首现口径）**：「骨纹自 ep001 即可见，但**只作未激活态**——黑白游龙纹路，不发光、不显示归一度读数；ep002 同 ep001；**ep003 骨纹第一次亮起（发光）并首次显示归一度读数 0.5%**」；与剧本层现盘 D08 U01 v1.13 body「陆沉右手腕的黑白游龙纹**第一次亮起**，纹路由腕侧向手背延开」**同向** ⇒ 归一方向＝**取「第一次亮起」**。
- **改动清单（5 处，JSON 为唯一真源，MD 全部重渲染）**：
　· `units/U01/D07.json` v1.2 → **v1.3**：`answer`／`must_happen[3]`／`cost` 三处 ⇒ 「右手腕骨**的黑白游龙纹第一次亮起**」（原「右手腕骨浮出第一道黑白游龙纹」）。
　· `units/U01/D06.json` v1.2 → **v1.3**：`logline`／`must_happen[3]` 两处 ⇒ 同上措辞。
　· **两表 `must_happen` 同步改**：ep003 的骨纹条目在 D06／D07 两表**逐字一致**（改后复核通过，见第六节）。
- **未改（有意为之）**：`units/U01/D11.json` ep003 镜3 `note` 中「浮出第一道」**属留痕位（登记口径的说明文字），不是正文** ⇒ 按「留痕位 vs 有效位」纪律**保留**，不作违规计；D11 `visual_facts` 已是「第一次亮起」（分镜导演已改）。`units/U01/D12.json` 卡 C-011 的 `image_prompt` 仍写「浮出第一道」⇒ **属他岗交付物（视觉设定）**，分镜导演已直接派单，本岗**未改、不代改**。

**三、⭐ U03 ep022 场景边界对齐段界（D07 v1.1，改脚本重跑，非手改产物）**
- **定性**：**不是数据错，是 D07 的场景边界没落在四段制段界上** —— 四段制段界为 0/12/25/38/45，而场景 B-16 收在 32.0s，落在镜3（25–38s）**内部** ⇒ 段3 横跨两个场景，下游「镜时严格等于段界、镜内内容全归单一 `scene_code`」无法落位。
- **下游实测锚（分镜导演 D11 U03 v1.0，11:38 落盘）**：ep022 镜1/2/3 ＝ `B-16`（镜时 12/13/13 ＝ 合计 38s）、镜4 ＝ `B-17`（7s）⇒ 下游已按 **B-16＝38s／B-17＝7s** 落位 ⇒ **D07 侧向 D11 对齐**（分镜导演建议的「把 B-16 调 38s」＝ 唯一自洽解）。
- **按 Q40 改脚本重跑（不是手改 JSON）**：改 `scripts/build_D06_D07_U03.py` —— ep022 `scenes` 两行（B-16 `time` 21:00-21:32→21:00-21:38／`duration_sec` 32→38；B-17 21:32-21:45→21:38-21:45／13→7）＋ `D07_VERSION` v1.0→**v1.1**，并在场景块上方补注释说明「场景边界必须落在段界上」；**重跑生成** `units/U03/D07.json`。
- **⭐ 沙箱零漂移自证（防「生成器内容源落后 → 重跑即静默回退」）**：
　① **原版脚本**在**沙箱**（`--project` 指向临时副本，输出路径由参数决定）跑出的产物与**活盘逐字节一致**（D06 10,874 B sha `b9b441d56ce30947`；D07 25,609 B sha `e8d17b61ed8a9165`）⇒ **脚本与活盘无既存漂移**，重跑安全；
　② 改后沙箱复跑，与活盘的差异**精确到 3 处**（`version` v1.0→v1.1 ＋ ep022 两个 `scenes` 块的 `time`/`duration_sec`），**D06.json 逐字节未变**（脚本输出与活盘一致 ⇒ 被幂等跳过，未被连带改写）⇒ 差异范围可证；
　③ 真盘 `--force` 落盘后回读校验（版本／字节／sha）通过。
- **旁证**：脚本自带断言 A9「四段制与时长：8 集段界连续、合计 45s；场景编码 B-11–B-19 连续不重」在改后**仍全绿**。

**四、出口硬闸（现盘复跑，11:4x）**
```
U01  通过 11/12  error 27   ← 27/27 全为 V12「白模构图一致性（D11 景别 ↔ D14 投影占幅）」；V1–V11 全 PASS
U03  通过 12/12  error  0   ← warning 8（缺 D12–D16 提示，不属本岗面）
```
- **U01 的 27 条与本岗零相关**：V12 的判据面是 **D11（景别）× D14（白模投影占幅）**，本岗交付物（D04/D05/D06/D07）在该规则块内**不出现**；本岗最相关的三条规则 **V4（时长求和与四段制边界）／V5（术语收口与禁用同义写法）／V8（单元钩子链闭合）均 PASS** ✅。修复动作在白模场景师一侧（与分镜导演 §二 的归口一致）。
- **误差变化说明**：分镜导演 11:38 报 U01 error 30，本岗 11:4x 复跑为 **27** ⇒ 差异来自白模侧并发重渲，**非本岗改动**（本岗 U01 只动了 D06/D07 两份 JSON 的文字）。

**五、渲染产物复核（MD 全部重渲染：`render/units/U01/D06.md`、`render/units/U01/D07.md`、`render/units/U03/D07.md`）**
- `grep -c "浮出第一道"` 于 U01 D06.md／D07.md／U03 D06.md／D07.md ＝ **0/0/0/0** ✅
- `grep -o "黑白游龙纹第一次亮起"` 于 U01 D06.md ＝ **2** 处、D07.md ＝ **3** 处 ✅（与 JSON 改动点逐条对应）
- U03 D07.md ep022 场景表已呈现 `B-16 | 城郊骨井 | 21:00-21:38 | 38s` 与 `B-17 | 废弃军工机械厂 | 21:38-21:45 | 7s` ✅

**六、新登记发现项（供总控／企划合规裁决，本岗**不自行落地**）**
- ⭐ **U01 的 D06／D07 两表 `must_happen` 并非逐字相同**：实测 **ep001／ep002／ep003 三集不一致**（如 ep001 槽位 2–3：D06＝「放弃囤物资路线…径直奔向机械厂」／D07＝「只装箱工具箱与一根钢钎…冲出房门，镜头带出楼道」；ep003 槽位 5：「废弃机械厂」vs「厂区」）。
- **定性**：**既存差异，非本轮引入** —— 改动前后实测不一致集**同为 [1,2,3]**，且差异为**表述层级不同**（D06＝大纲级／D07＝施工卡级），**无语义冲突**。
- **但口径冲突是真的**：U03 构建脚本断言 A15 写「D07.must_happen ≡ D06（**U01／U02 惯例两表逐字相同**）」⇒ **该「惯例」在 U01 并不成立**（U02 未核）。若要统一到逐字相同，会改动 U01 ep001–003 的 `must_happen` ⇒ **牵动已落地的 D08／D11 索引重排**，属他岗产物联动 ⇒ **请总控裁决是否统一**，本岗不擅自改。

**七、本岗指针现值（写入时现取，**动态中**）**
`{p_d06}`｜`{p_d07}`｜`{p_u03d06}`（**本轮未动**）｜`{p_u03d07}`｜`{p_script}`

**八、本岗状态与边界**
- **本轮改动**：`units/U01/D06.json`（v1.2→v1.3，2 处）｜`units/U01/D07.json`（v1.2→v1.3，3 处）｜`units/U03/D07.json`（v1.0→v1.1，ep022 场景 2 块，经**改脚本重跑**产出）｜`scripts/build_D06_D07_U03.py`（内容源 ＋ 版本常量）。
- **未改**：D02／D03／D04／D05／D08–D16／`project.json`／`00_项目索引.md`／`03_规格/*`／`04_工具/*`／**他岗章节正文**；**未改源素材** `双相潮主/01_漫剧策划/`（本轮只读回源）⇒ **本轮无 `project.json.gaps_resolved` 新增条目**（该登记口按本岗纪律对应「源素材设定修正」，本轮无此类改动；若总控要求把本节两件修复也登记为 G 条目，请下达，本岗照办）。
- **未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架**；只出文档与白模。
- 本岗章节 **{sub_head} 已追加**（写后回读校验：缺号 0／重号 0）。

**九、⚠️ 并发写事故留痕（透明登记，不隐去）**
- 11:45 本岗以 `write` 写 `scripts/append_ledger_104_40_mavis.py` 时，该路径**已被本岗另一并发实例占用**（其 §104.40 台账节已于 **11:43:06** 落盘，备份 `reports/_bak_ledger_104_40_20261023-114306/99_交付说明.md` 可证）⇒ 本岗**覆盖了该一次性脚本文件本体**，原脚本内容**不可恢复**（仅台账备份存在，无脚本备份）。
- **影响范围**：**§104.40 的台账正文完好无损**（正文在 `99_交付说明.md`，与脚本无关）；受影响者仅是**该一次性脚本文件**。
- **处置**：① 原路径已改为**显式中止的占位文件**（`append_ledger_104_40_mavis.py`，见其文件头），防同名路径被复跑时写入与 104.40 语义不符的内容；② 本岗本节改用唯一名 `scripts/append_ledger_104_41_mavis.py`（§104.41），其后按 max+1 顺延；③ 台账写入沿用**并发守卫**（size／mtime／sha256 三重比对，变动即中止不写盘）。
- **教训**：脚本落名**按「节号 + 内容」双锚**不够 —— 同一岗并发实例会抢同一节号路径；**落名前必须先 `ls` 目标路径是否已存在**（本岗本轮已因目录清单早于并发写入而漏检）。

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
    bdir = os.path.join(root, "reports", f"_bak_ledger_104_41_{stamp}")
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
