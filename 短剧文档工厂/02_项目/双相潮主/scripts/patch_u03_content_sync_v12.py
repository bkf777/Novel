#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 U03 内容源回填到「黄金 3 秒」补位批次之后的现盘，并订正词形自相矛盾。

背景（2026-10-23 11:17–11:19 实测取证）：
  · 总控「黄金 3 秒」补位批次于 11:17:28 备份 `_bak_golden3s_u01_20261023-111728/`
    与 11:18:50 备份 `_bak_golden3s_u02u03_20261023-111850/`，并于 11:19 重写
    **本岗单写点** `units/U03/D08.json`（v1.1→v1.2）与 `units/U03/D09.json`（v1.0→v1.1）：
      ① 各集 `compliance_added` 正文段整体移出正文，改写入 `compliance_notes`
         （每集追加 3 条：【合规交付 · 已从正文移出】×2 ＋「合规交付口径」×1；
          ep023 另加「黄金 3 秒口径」×1）；
      ② ep023 新增首句台词 LC「从头念。」并前移至开场位（台词数补足 ≥3）。
  · **补位批次只写了 JSON，没同步本岗内容源** ⇒ 内容源 VERSION 仍停在 v1.1，
    重跑会回退 Chief 的改动（且版本守卫会拦下）。本脚本把内容源补齐到现盘。

本脚本同时订正一处**本岗自身的真缺口**：
  · ep017／ep018 正文写「散成灰烬光尘」，而同集 `compliance_notes` 自述
    「D05 溃散为灰烬光尘：first_use_ep=17，本集即首用，写法已定死」——
    **notes 自述与正文用词自相矛盾**；且 D05 词条唯一写法为「溃散为灰烬光尘」
    （`forbidden_synonyms` 未列「散成灰烬光尘」，故非禁用同义词，只是词形未统一）。
    ⇒ 正文与 notes 同步订正为「溃散为灰烬光尘」（U01 ep4 现盘已用该写法）。
  · 「散成灰烬光尘」→「溃散为灰烬光尘」为 1:1 字面替换，不改任何事实与语义。

用法：python3 patch_u03_content_sync_v12.py [--dry-run]
写盘顺序：先改**内容源**，再由 build_D08.py / build_D09.py 生成 JSON（Q40：禁手改 JSON）。
"""
import argparse
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BAK = os.path.join(PROJ, "reports", "_bak_golden3s_u02u03_20261023-111850")
SRC_D08 = os.path.join(HERE, "d08_content_U03.py")
SRC_D09 = os.path.join(HERE, "d09_content_U03.py")

NEW_DIALOGUE = {
    "type": "dialogue",
    "char_id": "LC",
    "text": "「从头念。」",
    "emotion": "喉音压着，两个字像落刀",
    "shot_intent": (
        "这句命令必须与密信摊开同帧——第 0 帧就要给出「他在审这封信」的姿态，"
        "不能是环境铺陈。"
    ),
}

# D07 ep023 首句新台词的潜台词（逐字取自现盘 D09 v1.1）
LC23_SUBTEXT = (
    "他没有让苏清辞解释，也没有表态——他要对方逐行念，因为重生者最不缺的就是时间，"
    "最缺的是对方漏掉的细节。一个字的命令，暴露的是他已经默认自己手里有答案。"
)


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def py_str(s):
    """把字符串转成可安全嵌入 Python 源码的双引号字面量。"""
    return json.dumps(s, ensure_ascii=False)


def new_notes_by_ep(disk_d08, bak_d08):
    """逐集取出「补位批次新写入的 compliance_notes 条目」（按现盘顺序）。"""
    bak_notes = {e["ep"]: list(e.get("compliance_notes") or []) for e in bak_d08["episodes"]}
    out = {}
    for e in disk_d08["episodes"]:
        cur = list(e.get("compliance_notes") or [])
        old = bak_notes.get(e["ep"], [])
        out[e["ep"]] = [n for n in cur if n not in old]
    return out


def patch_d08(dry_run=False):
    disk = json.load(open(os.path.join(PROJ, "units", "U03", "D08.json"), encoding="utf-8"))
    bak = json.load(open(os.path.join(BAK, "U03_D08.json"), encoding="utf-8"))
    adds = new_notes_by_ep(disk, bak)
    src = read(SRC_D08)
    orig = src

    # ── ① 移出各集正文尾部的 compliance_added 段（AI_MARK + 各集专项）──
    comp_pat = re.compile(
        r"\n            AI_MARK,\n            \{\n                \"type\": \"action\",\n"
        r"                \"text\": \".*?\",\n                \"compliance_added\": True,\n"
        r"                \"compliance_reason\": \(\n.*?\n                \),\n            \},",
        re.S,
    )
    src, n_comp = comp_pat.subn("", src)

    # ── ② 把新 notes 条目追加到各集 compliance_notes 末尾（代价落点之后）──
    notes_by_ep = {e["ep"]: e.get("compliance_notes") or [] for e in disk["episodes"]}
    cost_pat = re.compile(r"(            \"代价落点（D07）：[^\"]*\",\n)(        \],)")
    n_notes = 0
    for ep in sorted(adds):
        lines = adds[ep]
        if not lines:
            continue
        # 只在该集所属的 ep 块内替换第一处「代价落点」收尾
        block_pat = re.compile(
            r"(# ═+ ep0*" + str(ep) + r"[^═]*═+\n.*?)" + cost_pat.pattern,
            re.S,
        )

        def _repl(m):
            add_txt = "".join(f"            {py_str(x)},\n" for x in lines)
            return m.group(1) + m.group(2) + add_txt + m.group(3)

        src, k = block_pat.subn(_repl, src, count=1)
        n_notes += k
        if k != 1:
            print(f"⚠️  ep{ep} notes 注入未命中（k={k}）")

    # ── ③ ep023 首句新台词插入到 body[0] 之后 ──
    dl_src = (
        "            {\n"
        f"                \"type\": \"dialogue\",\n"
        f"                \"char_id\": \"LC\",\n"
        f"                \"text\": \"「从头念。」\",\n"
        f"                \"emotion\": \"喉音压着，两个字像落刀\",\n"
        f"                \"shot_intent\": \"这句命令必须与密信摊开同帧——第 0 帧就要给出「他在审这封信」的姿态，不能是环境铺陈。\",\n"
        f"            }},\n"
    )
    ep23_block = re.compile(r"(# ═+ ep0*23[^═]*═+\n.*?)(\n        \],)", re.S)
    m = ep23_block.search(src)
    if not m:
        print("❌ 未定位 ep023 块")
        sys.exit(1)
    # 找 ep023 body 里第一条 action 结束的位置
    body_start = m.group(1)
    anchor = re.search(
        r"(            \{\n                \"type\": \"action\",\n                \"text\": \"一封密信在钢桌上摊开，排版是合同的样子。\",\n"
        r"                \"shot_intent\": \"密信摊开且排版是合同的样子必须被看见，商业条款口径要立住。\",\n            \},\n)",
        body_start,
        re.S,
    )
    if not anchor:
        print("❌ 未定位 ep023 body[0]")
        sys.exit(1)
    body_start2 = body_start.replace(anchor.group(1), anchor.group(1) + dl_src, 1)
    src = src.replace(body_start, body_start2, 1)

    # ── ④ 词形订正：散成灰烬光尘 → 溃散为灰烬光尘 ──
    n_form = src.count("散成灰烬光尘")
    src = src.replace("散成灰烬光尘", "溃散为灰烬光尘")

    # ── ⑤ 版本与变更说明 ──
    src = src.replace(
        'VERSION = "v1.1"',
        'VERSION = "v1.2"',
        1,
    )
    marker = 'VERSION = "v1.2"'
    changelog = (
        "# v1.2（2026-10-23 11:2x）：**回填本岗内容源至「黄金 3 秒」补位批次后的现盘** ＋ 词形自洽订正\n"
        "#   ① 总控补位批次 11:17:28／11:18:50 备份后于 11:19 重写本岗单写点\n"
        "#      `units/U03/D08.json`（v1.1→v1.2）与 `units/U03/D09.json`（v1.0→v1.1）：\n"
        "#      各集 `compliance_added` 正文段整体移出正文、逐条改写入 `compliance_notes`；\n"
        "#      ep023 新增首句台词 LC「从头念。」并前移至开场位。\n"
        "#      **该批次只写了 JSON，未同步本岗内容源** ⇒ 重跑会回退其改动，故本版按现盘回填。\n"
        "#   ② 词形自洽订正（本岗自身缺口）：ep017／ep018 正文原写「散成灰烬光尘」，\n"
        "#      与同集 notes 自述「D05 溃散为灰烬光尘：first_use_ep=17，本集即首用，写法已定死」\n"
        "#      自相矛盾；D05 词条唯一写法为「溃散为灰烬光尘」（`forbidden_synonyms` 未列\n"
        "#      「散成灰烬光尘」⇒ 非禁用同义词，仅词形未统一；U01 ep4 现盘已用该写法）。\n"
        "#      ⇒ 正文 2 处 ＋ notes 1 处同步订正为「溃散为灰烬光尘」（1:1 字面替换，不改事实）。\n"
    )
    src = src.replace(marker, changelog + marker, 1)

    print(f"  D08 内容源：合规段移出 {n_comp} 处｜notes 注入 {n_notes} 集｜"
          f"词形替换 {n_form} 处｜VERSION→v1.2")
    if dry_run:
        return
    shutil.copy2(SRC_D08, SRC_D08 + ".bak_sync_v12")
    write(SRC_D08, src)


def patch_d09(dry_run=False):
    src = read(SRC_D09)
    # ep023 原有两条 SQC 潜台词后移一位（idx 1→2、2→3），并新增 LC 的 idx 1
    old1 = "    (23, 1): \"她把话说死："
    old2 = "    (23, 2): \"最狠的一句是她自己的："
    if old1 not in src or old2 not in src:
        print("❌ D09 内容源未定位 ep023 两条旧潜台词")
        sys.exit(1)
    body_new = (
        "    (23, 1): " + py_str(LC23_SUBTEXT) + ",\n"
        "    (23, 2): \"她把话说死："
    )
    src = src.replace(old1, body_new, 1)
    src = src.replace(old2, "    (23, 3): \"最狠的一句是她自己的：", 1)
    src = src.replace(
        'VERSION = "v1.0"',
        'VERSION = "v1.1"',
        1,
    )
    marker = 'VERSION = "v1.1"'
    changelog = (
        "# v1.1（2026-10-23 11:2x）：跟随机读 D08 v1.2 —— ep023 新增首句台词 LC「从头念。」，\n"
        "#   原 ep023 两条 SQC 潜台词的 idx 由 1／2 顺移为 2／3，并补齐 LC idx=1 的潜台词\n"
        "#   （逐字取自现盘 D09 v1.1，涉未成年口径写明指向成年人）。\n"
    )
    src = src.replace(marker, changelog + marker, 1)
    print("  D09 内容源：ep023 潜台词重排（新增 LC idx1，SQC 1→2／2→3）｜VERSION→v1.1")
    if dry_run:
        return
    shutil.copy2(SRC_D09, SRC_D09 + ".bak_sync_v11")
    write(SRC_D09, src)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print("▶ 回填 U03 内容源 → 现盘（Q40：只改内容源，JSON 由构建脚本生成）")
    patch_d08(a.dry_run)
    patch_d09(a.dry_run)
    print("✅ 完成")
