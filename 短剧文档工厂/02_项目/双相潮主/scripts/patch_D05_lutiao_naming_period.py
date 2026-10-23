#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D05_lutiao_naming_period.py —— 故事架构：把「律条」词条的**未命名期台词口径**补进 D05
（D05 v1.4 → v1.5）。**只收口，不臆造代称。**

**为什么做这件事（派单来源：台本编剧 09:1x 回执第③节「措辞纪律」段）**
  · 台本编剧已在 `units/U02/D09.json` v1.1 的 SQC 语气卡落下 1 条禁写项：
    「ep013–ep040 的台词与字幕不得出现「律条」三字（画面描述可用）……此期间台词只呈现
    「贵重、神秘、可被财阀囤积」的物件特征，不给名称。」，并明确问本岗：
    **「若你认为应同时给出中性指代的具体写法，请给，本岗照落」**。
  · 本岗回源结论：**源素材没有给任何代称** ——《脉络确认》§三「律条／天律｜观众何时获得
    ep041（名称层；实物层 ep013 已入画**未命名**、凭证层 ep035 亦未命名）」、§二
    「ep041+（名称层；凭证机制 ep035 已以**未命名实物**呈现）」、《设定待核对清单》「名字晚、
    机制早」⇒ 源只给了「**未命名**」这一状态，**没给指代写法**。
  · ⇒ **指定一个专名（如「规则石」式的新称呼）＝臆造**，与本岗此前「D05『数据板』词条
    回源无据 → 不擅自立条」是同一类陷阱（见台账 §104.x）。**故本岗只收口「不给名称」的
    可机读边界，把具体用词留给剧作层**（D08 台词／D09 语气卡）——与台本编剧自己的判断一致。

**本脚本只做一件事**：在 `glossary[律条].definition` 末尾**追加**一段「未命名期台词口径」，
并把 `version` v1.4 → v1.5。**其余字段一字不动**（含 `first_use_ep`、`forbidden_synonyms`、
`glossary` 条数）。

**断言清单（A1–A8）**
  A1 D05 可解析且当前 version == v1.4（已是 v1.5 → `[IDEMPOTENT]` 退出 0）；
  A2 `glossary` 中 `term == "律条"` 恰 1 条；
  A3 该条 definition 含锚点尾句「…不得自造第三种档位修饰语。」；
  A4 definition **尚不含**本段新块（内容标记幂等锚）；
  A5 结构化 diff 白名单：**恰 2 处** —— `/version` ＋ `/glossary/<idx>/definition`；
  A6 落盘后不变量：`glossary` 仍 42 条、`first_use_ep` 仍 13、
     `forbidden_synonyms` 仍恰 3 项且内容不变、`definition` 仅**末尾追加**（前缀逐字不变）；
  A7 CAS 守卫（size/mtime/sha256）；A8 写后回读。

用法：python3 scripts/patch_D05_lutiao_naming_period.py --project .
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime

MARK = "【未命名期台词口径（ep013–ep040）"
ANCHOR = "不得自造第三种档位修饰语。"
FORBIDDEN_BEFORE = ["骨签", "规则石", "低阶律条"]

NEW_BLOCK = (
    "【未命名期台词口径（ep013–ep040）】源《脉络确认》§三「律条／天律｜观众何时获得 ep041"
    "（**名称层**；实物层 ep013 已入画**未命名**、凭证层 ep035 亦未命名）」、§二「ep041+"
    "（名称层；凭证机制 ep035 已以**未命名实物**呈现）」、《设定待核对清单》「名字晚、机制早」"
    "⇒ **未命名期**＝ep013（实物入画）至 ep040（名称层 ep041 的前一集）。该期**该物件只有画面特征、"
    "没有名称**：① **台词面与字幕面不得出现本词**，亦**不得出现其任何专名写法**"
    "（`forbidden_synonyms` 全列：骨签／规则石／低阶律条）—— 这是「不给名称」的**可机读定义**；"
    "② 台词替代**只能是指示性/泛指表述**，**不得是专名、不得带档位修饰语、不得暗示「可改写规则」"
    "或「可作破境凭证」**；**具体用词属剧作层**（D08 台词／D09 语气卡）决定——**本词条不指定代称**"
    "（回源无据：源素材只写「未命名」，未给任何指代写法；指定一个专名即臆造）；"
    "③ **画面描述面不受限**（ep013 实物可写「一枚律条被推上交易台」）；"
    "④ **ep041 起台词可说通称「律条」**（名称层已获），档位修饰语仍只用「普通律条」／「天律」。"
)


def norm_paths(a, b, path=""):
    """结构化 diff：返回 (新增/变更路径, 删除路径) 列表；数组增量落在叶子路径。"""
    added, removed = [], []
    if type(a) is not type(b):
        return [path or "/"], []
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}/{k}"
            if k not in a:
                added.append(p)
            elif k not in b:
                removed.append(p)
            else:
                x, y = norm_paths(a[k], b[k], p)
                added += x
                removed += y
    elif isinstance(a, list):
        if len(a) != len(b):
            added.append(f"{path}/{len(a)}")  # 数组长度变化 → 记增量为叶子
        for i in range(min(len(a), len(b))):
            x, y = norm_paths(a[i], b[i], f"{path}/{i}")
            added += x
            removed += y
    else:
        if a != b:
            added.append(path or "/")
    return added, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    p = os.path.join(root, "shared/D05.json")
    if not os.path.isfile(p):
        sys.exit("[ABORT] shared/D05.json 不存在；不写盘。")

    snap = open(p, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(p)
    d = json.loads(snap.decode("utf-8"))

    # A1 version
    ver = d.get("version")
    if ver == "v1.5":
        print("[IDEMPOTENT] D05 已是 v1.5（含未命名期台词口径）；未改动台账/交付物。")
        return 0
    if ver != "v1.4":
        sys.exit(f"[ABORT] A1 D05 version == {ver!r}，既非 v1.4（可升）亦非 v1.5（已应用）；不写盘。")

    # A2 律条恰 1 条
    gl = d.get("glossary") or []
    idxs = [i for i, g in enumerate(gl) if g.get("term") == "律条"]
    if len(idxs) != 1:
        sys.exit(f"[ABORT] A2 律条词条命中 {len(idxs)} 条 ≠ 1；不写盘。")
    gi = idxs[0]
    g = gl[gi]
    definition = g.get("definition") or ""

    # A3 锚点尾句
    if ANCHOR not in definition:
        sys.exit("[ABORT] A3 definition 不含锚点尾句（版本形态与预期不符）；不写盘。")
    # A4 内容标记幂等
    if MARK in definition:
        print("[IDEMPOTENT] definition 已含未命名期口径块；未改动。")
        return 0

    # 构造新值：只在末尾追加
    new_definition = definition + NEW_BLOCK
    new_gl = json.loads(json.dumps(gl))
    new_gl[gi]["definition"] = new_definition
    new_d = json.loads(json.dumps(d))
    new_d["glossary"] = new_gl
    new_d["version"] = "v1.5"

    # A5 结构化 diff 白名单
    added, removed = norm_paths(d, new_d)
    allowed = {"/version", f"/glossary/{gi}/definition"}
    if set(added) != allowed or removed:
        sys.exit(f"[ABORT] A5 结构化 diff 越界：added={added} removed={removed}；不写盘。")

    # A6 落盘前不变量
    if len(new_d["glossary"]) != len(gl):
        sys.exit("[ABORT] A6 glossary 条数变化；不写盘。")
    if new_gl[gi].get("first_use_ep") != g.get("first_use_ep"):
        sys.exit("[ABORT] A6 first_use_ep 变化；不写盘。")
    if list(new_gl[gi].get("forbidden_synonyms") or []) != list(g.get("forbidden_synonyms") or []):
        sys.exit("[ABORT] A6 forbidden_synonyms 变化；不写盘。")
    if not new_definition.startswith(definition):
        sys.exit("[ABORT] A6 definition 非纯末尾追加；不写盘。")
    if len(new_gl[gi]["forbidden_synonyms"]) != len(FORBIDDEN_BEFORE):
        sys.exit("[ABORT] A6 forbidden_synonyms 条数异常；不写盘。")

    if args.dry_run:
        print(f"[DRY-RUN] 将把 D05 v1.4 → v1.5，追加 {len(NEW_BLOCK)} 字符到 definition 末尾；未写盘。")
        return 0

    # A7 CAS
    cur = open(p, "rb").read()
    if (len(cur) != snap_size or hashlib.sha256(cur).hexdigest() != snap_sha
            or os.path.getmtime(p) != snap_mtime):
        sys.exit("[ABORT] A7 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # 备份
    bdir = os.path.join(root, "reports", "_bak_D05_naming_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(p, os.path.join(bdir, "D05.json.bak"))

    with open(p, "w", encoding="utf-8") as f:
        json.dump(new_d, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # A8 写后回读
    back = json.loads(open(p, encoding="utf-8").read())
    bg = [x for x in back["glossary"] if x.get("term") == "律条"][0]
    assert back.get("version") == "v1.5", "A8 version 未升"
    assert bg["definition"].startswith(definition), "A8 definition 前缀被改动"
    assert MARK in bg["definition"], "A8 新块未落盘"
    assert bg.get("first_use_ep") == g.get("first_use_ep"), "A8 first_use_ep 被改动"
    assert list(bg.get("forbidden_synonyms") or []) == list(g.get("forbidden_synonyms") or []), \
        "A8 forbidden_synonyms 被改动"
    assert len(back["glossary"]) == len(gl), "A8 glossary 条数变化"
    added2, removed2 = norm_paths(d, back)
    assert set(added2) == allowed and not removed2, f"A8 回读 diff 越界 {added2}/{removed2}"
    print(f"[OK] D05 v1.4 → v1.5｜{snap_size} → {os.path.getsize(p)} B｜"
          f"追加 {len(NEW_BLOCK)} 字符到 glossary[{gi}].definition 末尾｜"
          f"diff 恰 2 处（/version ＋ /glossary/{gi}/definition）｜备份 {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
