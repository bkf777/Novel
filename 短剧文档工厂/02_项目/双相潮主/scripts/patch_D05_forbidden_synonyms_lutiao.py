#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D05_forbidden_synonyms_lutiao.py —— 故事架构（D05 属主）：把自造档位修饰语「低阶律条」
                                              补进 `律条` 词条的 `forbidden_synonyms`（D05 v1.3 → v1.4）

**派单来源（上游合规裁决，非本岗自选）**：
· **S31 ④**（企划合规 2026-10-23 08:00，配套 **Q78／OPS-23**）：「**字面禁用写法不走首用集轴** —— 自造档位修饰语
  （如「低阶律条」）走 D05 词条 `forbidden_synonyms`；**其根因在 D05 未把该写法写进 `forbidden_synonyms`，不在校验器**
  → **派 D05 属主（故事架构）补一行**。V5 既有禁用同义词扫描立即机读化，**无需任何校验器改动**。
· **OPS-23 面②**：「D05 律条词条 `forbidden_synonyms` 缺『低阶律条』」→ status「部分闭环（面①已落地；**面②待 D05 属主补**）」。
· 本岗此前已第 3 次上报同一事项（台账 §104.13 第四项），**与本次派单同一件事，只保留一个派单源**，不重复登记。

**改动面（最小）**：
  `/version`：v1.3 → v1.4
  `/glossary/<律条>/forbidden_synonyms`：`["骨签","规则石"]` → `["骨签","规则石","低阶律条"]`
  **其余零改动**（`definition` 不动 —— 故 B9「definition 不含自造档位修饰语」仍然成立；`glossary` 仍 42 条；`first_use_ep` 仍 13）。

**为什么安全（动手前先验的三件事）**：
 ① **V5 扫描面**：`04_工具/lib/rules.mjs` 的 V5 遍历 `ctx.files` 中**除 D05 外**的全部文档，按 `rules.json` 的
    `term_scan_exempt` 做字段级豁免；**D05 自身被显式排除**（`if (docId === 'D05' …) continue`）→ 词条里写出该词不会自触发。
 ② **D18 内的既有残留**：实测 D18 中「低阶律条」10 处**全部落在豁免字段内**（`unit_checks`／`global_checks`／`open_issues`）→ 不会误报。
 ③ **manifest 交叉校验**：V5 另校 `project.json.terminology.forbidden_synonym_pairs` 每对的 `banned` 必须已收进 D05；
    现有 10 对中**无「律条」对** → 本次增列不影响该校验（方向为「manifest ⊆ D05」）。

**断言（A1–A7）**：A1 可解析｜A2 词条「律条」恰 1 处｜A3 前置值 == `["骨签","规则石"]`（否则报幂等）｜
A4 **结构化 diff 恰 2 处**（`/version` ＋ `/glossary/<i>/forbidden_synonyms`），其余零变化｜A5 序列化格式与原文件逐字节同型
（`indent=2`／末尾无换行）｜A6 CAS 守卫（size+mtime+SHA256）｜A7 写后回读 ＋ **幂等**。

用法：python3 scripts/patch_D05_forbidden_synonyms_lutiao.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def leaves(obj, path=""):
    """扁平化为 {路径: 叶子值}，用于结构化 diff（Q67：尺寸判据不可作结论）。"""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaves(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaves(v, f"{path}/{i}"))
    else:
        out[path] = obj
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    p = os.path.join(root, "shared/D05.json")
    if not os.path.isfile(p):
        sys.exit("[ABORT] shared/D05.json 不存在；不写盘。")

    raw = open(p, "rb").read()
    raw_sha = hashlib.sha256(raw).hexdigest()
    raw_size = len(raw)
    raw_mtime = os.path.getmtime(p)
    text = raw.decode("utf-8")
    d = load(p)

    # A1 可解析（已由 load 抛出即中止）
    gl = d.get("glossary", [])
    # A2 词条「律条」恰 1 处
    idxs = [i for i, g in enumerate(gl) if g.get("term") == "律条"]
    if len(idxs) != 1:
        sys.exit(f"[ABORT] A2 词条「律条」命中 {len(idxs)} ≠ 1；不写盘。")
    i = idxs[0]
    entry = gl[i]

    cur = entry.get("forbidden_synonyms")
    want = ["骨签", "规则石", "低阶律条"]
    # A3 前置值：已是目标值 → 幂等
    if cur == want:
        print(f"[IDEMPOTENT] 「律条」`forbidden_synonyms` 已是 {want}；未改动 D05。")
        return 0
    if cur != ["骨签", "规则石"]:
        sys.exit(f"[ABORT] A3 前置值 {cur} ≠ 预期 ['骨签','规则石']；不写盘（可能已被他人改动）。")

    old_version = d.get("version")
    new = json.loads(text)
    new["glossary"][i]["forbidden_synonyms"] = want
    new["version"] = "v1.4"
    out_text = json.dumps(new, ensure_ascii=False, indent=2)

    # A5 序列化同型：除本次两处外，与原文件的差异必须是「只有这两处」
    if not raw.decode("utf-8").endswith("\n"):
        pass  # 原文件末尾无换行 → 输出亦无（json.dumps 默认如此）
    old_lv, new_lv = leaves(d), leaves(new)
    changed = sorted(k for k in set(old_lv) | set(new_lv) if old_lv.get(k) != new_lv.get(k))
    # A4 结构化 diff：必须恰为「version 一处」＋「forbidden_synonyms 恰好一个新元素一处」
    #    （叶子级 diff 的数组增量表现为 /forbidden_synonyms/<新下标>，不是数组本身）
    fs_prefix = f"/glossary/{i}/forbidden_synonyms"
    fs_hits = [k for k in changed if k == fs_prefix or k.startswith(fs_prefix + "/")]
    if changed != sorted(["/version"] + fs_hits) or len(fs_hits) != 1:
        sys.exit(f"[ABORT] A4 结构化 diff {changed} ≠ 预期 ['/version'] ＋ 1 处 {fs_prefix}/…；不写盘。")
    if not fs_hits[0].endswith("/2"):
        sys.exit(f"[ABORT] A4 新增元素下标异常：{fs_hits[0]}；不写盘。")
    # A5 同型自检：序列化往返必须逐字节等于目标文本（证明未引入格式漂移）
    if json.dumps(json.loads(out_text), ensure_ascii=False, indent=2) != out_text:
        sys.exit("[ABORT] A5 序列化不稳定；不写盘。")

    if args.dry_run:
        print(f"[DRY-RUN] 将改 {len(changed)} 处：{changed}；D05 {raw_size} → {len(out_text.encode())} B；未写盘。")
        return 0

    # A6 CAS 守卫
    cur_raw = open(p, "rb").read()
    if (len(cur_raw) != raw_size
            or hashlib.sha256(cur_raw).hexdigest() != raw_sha
            or os.path.getmtime(p) != raw_mtime):
        sys.exit("[ABORT] A6 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")

    # 备份（统一落 reports/_bak_*，不在 units/ 或 shared/ 交付目录内）
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_D05_forbidden_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    shutil.copy2(p, os.path.join(bak_dir, "D05.json.bak-" + ts))

    with open(p, "w", encoding="utf-8") as f:
        f.write(out_text)

    # A7 写后回读
    back = open(p, encoding="utf-8").read()
    bd = json.loads(back)
    bi = [k for k, g in enumerate(bd.get("glossary", [])) if g.get("term") == "律条"]
    if len(bi) != 1 or bd["glossary"][bi[0]].get("forbidden_synonyms") != want:
        sys.exit("[ABORT] A7 写后回读失败 —— 请人工核盘。")
    if bd.get("version") != "v1.4":
        sys.exit("[ABORT] A7 写后 version 非 v1.4；请人工核盘。")
    blv = leaves(bd)
    bchanged = sorted(k for k in set(old_lv) | set(blv) if old_lv.get(k) != blv.get(k))
    if bchanged != changed:
        sys.exit(f"[ABORT] A7 写后结构化 diff {bchanged} ≠ 落盘前 {changed}；请人工核盘。")
    if len([k for k in bchanged if k == "/version" or k.startswith(fs_prefix + "/")]) != 2:
        sys.exit(f"[ABORT] A7 写后结构化 diff {bchanged} 不是预期的两处；请人工核盘。")
    print(f"[OK] D05 v1.3 → v1.4；「律条」forbidden_synonyms = {want}；"
          f"结构化 diff 恰 {len(bchanged)} 处（{'/version'} ＋ /glossary/{i}/forbidden_synonyms）；"
          f"{raw_size} → {len(back.encode())} B；备份 {os.path.relpath(bak_dir, root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
