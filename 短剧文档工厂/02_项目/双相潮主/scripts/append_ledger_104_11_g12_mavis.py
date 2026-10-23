#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_104_11_g12_mavis.py —— 故事架构：**G12 重复条目实测结论（两件事、不可简单删）**
                                     ＋ 两处口径缺口现状复核 ＋ 补报投递留痕（2026-10-23）

**为什么补报**：本岗本轮首次完整复核 `project.json` `gaps_resolved` —— 发现**两条 `id: G12`**，
此前**从未向总控上报**（07:0x 与 07:3x 两条外发件均未含此项）。

**实测结论（两条 G12 实为两件事，不能简单删一条）**：
  · **G12-b（已裁决，企划合规 2026-10-22）** ＝ 占位角色 **GJ-HJ「雾盟雾盟首座」**（职责与 WM-SZ 重叠）
    → 裁决「未写入 D04；源素材删除该条；职责并入 WM-SZ」。
    **本岗实测复核全部属实 ✅**：`shared/D04.json` `characters` 恰 **7** 个
    （LC／YHY／SQC／YJ-JZ／YJ-ES／WM-SZ／YD-GC），**无 GJ-HJ**；源素材 `01_漫剧策划/`
    全库 grep「雾盟雾盟首座」**0 处**（仅 `逐集内容概述.md` 保留「雾盟首座」作为剧情叙述）→ **该部分确已闭合**。
  · **G12-a（未闭合）** ＝ **「叶家护卫队队长」无编号角色**（D06/D07 ep006 需其在场并被击退，
    D04 指定的 7 角色无此编号角色，只能按无名功能角色写入 must_happen）
    **本岗实测复核仍成立 ✅**，且缺口有明确登记点：
    **`units/U01/D07.json` ep006 `open_questions` 的 `Q-U01-01`**（owner＝总控／企划合规）
    —— **至今既无 `status` 也无 `resolution`**（同集合 `Q-U01-02` 已有 status＝已裁决）→ **确实还没结**。
  → **建议**（贵岗裁）：合并为一条（或第二条改号），**保留「护卫队队长」部分为未闭合并指向 `Q-U01-01`**；
    **GJ-HJ 部分按已裁决闭合**；**不得简单删一条**（删错会把未闭合项一并抹掉）。

**两处口径缺口现状复核（均仍在，未收口）**：
  ① `00_项目索引.md` 第 1218 行仍写「『律条』**三层**首用＝ep013／ep035／ep044 → `first_use_ep: 41` 三不沾、必错」
     —— 与 D05 v1.3 现行**四层**锚点（①实物 ep013＝取值层／②破境凭证 ep035／**③观众获名 ep041**／④主角夺取 ep044）**层数不一致**；
     且「41 三不沾」措辞易被误读为「41 是无效值」（实为**名称／观众层**首用集，与实物层 13 分属两层不冲突）。
  ② `shared/D18.json` `U02-R25` 的 `issue` 正文仍只列三层（缺「③观众获名 ep041」），
     而其 `status` 已写「并补**第④层**（ep044 主角首夺）」—— **同一条目内两层数表述互相矛盾**。
  → 两处均在**企划合规单点文件**（`00_项目索引.md`／`D18`），**本岗不代改**。

⚠️ 锚点＝「本岗章节之后的第一个同级标题之前」（Q72／OPS-20）；子节号动态取 max+1；
   **幂等守卫锚在内容标记上**（不是动态编号 —— 本岗已栽过一次，见 §104.10）。
用法：python3 scripts/append_ledger_104_11_g12_mavis.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import os
import re
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
    MARK = "G12 重复条目实测结论（两件事、不可简单删）"

    snap = open(ledp, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(ledp)
    lines = snap.decode("utf-8").split("\n")

    # A1 本岗章节命中数恰为 1
    mine = [i for i, l in enumerate(lines) if l.startswith(MY_HEADER)]
    if len(mine) != 1:
        sys.exit(f"[ABORT] A1 本岗章节命中数 {len(mine)} ≠ 1；不写盘。")
    i0 = mine[0]

    # A4 追加点
    nxt = [i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")]
    if not nxt:
        sys.exit("[ABORT] A4 本岗章节之后无同级标题（无法定位追加点）；不写盘。")
    ins = nxt[0]

    # A3 幂等：内容标记（不用动态编号）
    if any(MARK in l for l in lines[i0:ins]):
        print(f"[IDEMPOTENT] §一百零四 下已存在 {MARK}；未改动台账。")
        return 0

    # A2 动态子节号
    used = set()
    for l in lines[i0:ins]:
        m = re.match(r"^### (\d+)\.(\d+)", l)
        if m:
            used.add((int(m.group(1)), int(m.group(2))))
    n = max([k for (a, k) in used if a == 104], default=0) + 1
    sub_head = f"### 104.{n}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""{sub_head} **{MARK}** ＋ 两处口径缺口现状复核 ＋ 补报投递留痕（{now}）

**为什么补报**：本岗本轮首次完整复核 `project.json` `gaps_resolved` —— 发现**两条 `id: G12`**；此前**从未向总控上报**（07:0x 与 07:3x 两条外发件均未含此项）。

**一、G12 重复条目：两条实为两件事，不可简单删一条**

| 条目 | 状态 | 事项 | 本岗实测复核 |
|---|---|---|---|
| **G12-b** | **已裁决**（企划合规 2026-10-22） | 占位角色 **GJ-HJ「雾盟雾盟首座」**（appearance 全待补、名称重复、与 WM-SZ 职责重叠）→ 裁决「未写入 D04；源素材删除该条；职责并入 WM-SZ 闻照白」 | **全部属实 ✅**：`shared/D04.json` `characters` 恰 **7** 个（LC 陆沉／YHY 叶红衣／SQC 苏清辞／YJ-JZ 叶崇岳／YJ-ES 叶承钧／WM-SZ 闻照白／YD-GC 商既衡），**无 GJ-HJ**；源素材 `01_漫剧策划/` 全库 grep「雾盟雾盟首座」**0 处**（仅 `逐集内容概述.md` 保留「雾盟首座」作为剧情叙述，非角色条目）→ **该部分确已闭合** |
| **G12-a** | **未闭合**（resolution 结尾「由总控裁决」） | **「叶家护卫队队长」无编号角色** —— D06／D07 的 ep006 需该角色在场并被击退，但 D04 指定的 7 角色无此编号角色，只能按**无名功能角色**写入 must_happen | **仍成立 ✅**，且缺口有明确登记点：**`units/U01/D07.json` ep006 `open_questions` 的 `Q-U01-01`**（owner＝总控／企划合规）—— **至今既无 `status` 也无 `resolution`**（同集合 `Q-U01-02` 已有 status＝已裁决）→ **确实还没结** |

**建议处置（贵岗裁）**：两条**合并为一条**（或第二条改号），**保留「护卫队队长」部分为未闭合并指向 `Q-U01-01`**；GJ-HJ 部分按已裁决闭合。**不得简单删一条** —— 删错会把仍未闭合的护卫队队长缺口一并抹掉。本岗**未改他岗条目**（`project.json` 归企划合规单点）。

**二、两处口径缺口现状复核（均仍在，未收口）**
① **`00_项目索引.md` 第 1218 行**仍写：「S20 裁定（回源素材）：『律条』**三层**首用＝实物首现 ep013／破境凭证 ep035／主角首夺 ep044 → D05 的 `first_use_ep: 41` **三不沾、必错**」—— 与 `shared/D05.json` **v1.3** 现行**四层**锚点**层数不一致**（①实物 ep013＝取值层／②破境凭证 ep035／**③观众获名 ep041**／④主角夺取 ep044）；且「41 三不沾」措辞易被误读为「41 是无效值」——**41 并非无效值**，它是**名称／观众层**首用集（脉络确认 §三／§二／§十 三处有出处），与实物层 13 **分属两层不冲突**。
② **`shared/D18.json` `U02-R25` 的 `issue` 正文**仍只列三层（缺「③观众获名 ep041」），而其 `status` 已写「并补**第④层**（ep044 主角首夺）」—— **同一条目内两层数表述互相矛盾**（正文把 ep044 当第③层，status 把它当第④层）。
→ 两处均在**企划合规单点文件**（`00_项目索引.md`／`D18`），**本岗不代改**；建议按 D05 v1.3 四层锚点统一收口。

**三、机器闸建议（第 3 次上报，仍待贵岗落）**
待 D08／D11 收敛后，把「**低阶律条**」写进 D05 律条词条 `forbidden_synonyms`（现 `["骨签","规则石"]`；schema `additionalProperties: false` ⇒ 只能改现有数组、不得新增字段）。理由：V5 会做**全文扫**，现仅有正文约束（档位写法规范），机器闸缺口仍在。

**四、投递留痕（OPS-03 `mavis session send` 绕行；MCP 读可写不可）**
· 07:43 两条（企划合规 核销回执 ＋ 声音设计 销号与可选收敛项）→ 均 **accepted／queued**（详见 §104.9）；
· 本节内容 → 企划合规 `mvs_ccccc31a…` **accepted／queued，position=2／ahead=2**，turn `turn_9fa44e32-2833-462e-ae61-e844e8f6883f`，item `queue_ec7d866c-a6b2-4307-9271-a8baca6e094b`。

**五、本岗状态与边界**
D05 v1.3／D06 v1.2／D07 v1.3 本轮**一字未动**；本岗名下脚本 **6 支**在位可复跑（`check_D06_D07_roster_consistency.py`／`check_D05_lutiao_firstuse.py`／`patch_D07_U02_ep009_back.py`／`append_ledger_104_9_delivery_mavis.py`／`fix_ledger_104_dup_mavis.py`／`append_ledger_104_10_guardfix_mavis.py` ＋ 本节脚本）。硬闸本岗自跑：**全项目 22/22 error 0 warning 7｜U02 11/11 error 0 warning 6｜U01 11/11 error 0 warning 1｜render-md EXIT 0**。**未改他岗章节**（§一百零五／§一百零六 由脚本前段/后段不变断言覆盖）；**未生成图片／视频／音频，未合成 TTS／BGM，未提交 H3 付费生成，未投流上架。****以上游合规裁决为准**。"""
    block = [""] + body.split("\n") + [""]

    new_lines = lines[:ins] + block + lines[ins:]
    new_text = "\n".join(new_lines)

    # A5 CAS 守卫
    cur = open(ledp, "rb").read()
    if (len(cur) != snap_size
            or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(ledp) != snap_mtime):
        sys.exit("[ABORT] A5 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # A6 结构性断言
    pre = "\n".join(lines[:ins])
    post = "\n".join(lines[ins:])
    assert new_text.startswith(pre), "A6 前段被改动"
    assert new_text.endswith(post), "A6 后段被改动"
    assert new_text.count(MARK) == 1, "A6 标记计数异常"

    if args.dry_run:
        print(f"[DRY-RUN] 将在第 {ins + 1} 行前插入 {sub_head}（{len(block)} 行）；未写盘。")
        return 0

    with open(ledp, "w", encoding="utf-8") as f:
        f.write(new_text)

    back = open(ledp, "rb").read().decode("utf-8")
    assert back.count(MARK) == 1, "A7 写后标记计数异常"
    assert back.startswith(pre), "A7 写后前段不一致"
    assert back.endswith(post), "A7 写后后段不一致"
    print(f"[OK] 已写入 {sub_head}（{len(block)} 行）；台账 {snap_size} → {len(back.encode('utf-8'))} B；"
          f"追加点＝原第 {ins + 1} 行（下一个同级标题之前）。落盘时间 {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
