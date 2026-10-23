#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D18 v1.22 → v1.23 收尾回刷（企划合规单点维护）。

背景
----
R-032 收尾三岗回执落盘后，台账存在两处**并行实例已刷过、但仍留缺口**的地方：

  ① D15 行文案仍写「7 条贴边配音 dur_sec 1.2→1.3」—— 实际本轮收敛 **11 条**
     （判据 A「实算停留 <1.2」6 条 ∪ 判据 B「out_sec == at_sec+dur_sec 位相等」3 条 ＝ 7 条，
     另 4 条为与派活口径及 OPS-05 断言统一化对齐）；且**落盘态 D15 中 dur_sec==1.3 实测 12 条**
     （多出的 ep1 seq8 at 31.4 本就是 1.3，不属本轮收敛）。三个数不可互相替代。
  ② D15 行「最小余量 1.7s」是**针对 D16 v1.3 的旧快照**；对 D16 v1.5 重跑实测最紧处为
     **0.5s**（ep7 镜4：硬切 37.0s 落在配音起音 37.5s 之前 0.5s，不跨界）—— 结论
     「D16 不需改、声音设计不需返修」仍成立，但数值与版本号必须同步（见 Q39）。

本脚本做三件事：
  A. 订正 D15 行文案（条数口径 ＋ 余量口径）。
  B. 新增 **Q40**：条数口径的判据（与并行实例的 Q39「下游升版后核验结论作废」是两条不同判据）。
  C. dispatch_ledger 追加 **OPS-07**（脚本留痕订正 ＋ 台账回刷 ＋ 索引回刷 ＋ D14 派活撤单），
     并推进 D18 版本号。

带命中数断言，对不上即中止不写盘；落盘后 deep-compare 逐键比对，只允许预期键变化。

用法
----
python3 scripts/patch_D18_v123_ledger_gapfill.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import copy
import json
import os
import sys

NOW = "2026-10-23 02:32"


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)
    p18 = os.path.join(proj, "shared", "D18.json")

    with open(p18, "r", encoding="utf-8") as f:
        raw = f.read()
    d18 = json.loads(raw)

    # ---------- 0) 格式自检：当前文件必须是 indent=2 且无尾随换行，否则改写会引入纯格式 diff ----------
    if json.dumps(d18, ensure_ascii=False, indent=2) != raw:
        sys.exit("[ABORT] D18.json 序列化格式与 indent=2（无尾随换行）不一致，改写会引入纯格式 diff；不写盘。")

    if d18.get("version") != "v1.22":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.22；不写盘。")

    u01 = [x for x in d18["unit_checks"] if x.get("unit") == "U01"]
    if len(u01) != 1:
        sys.exit(f"[ABORT] unit_checks 中 U01 命中 {len(u01)} 条，期望 1 条；不写盘。")
    u01 = u01[0]

    rows = {r["doc"]: r for r in u01["delivery_checks"]}
    for d in ("D10", "D15", "D16"):
        if d not in rows:
            sys.exit(f"[ABORT] delivery_checks 缺 {d}；不写盘。")

    before = copy.deepcopy(d18)

    # ---------- A. D15 行：订正条数口径与余量口径 ----------
    r15 = rows["D15"]
    if r15.get("version") != "v1.1" or r15.get("size") != "86273 B":
        sys.exit(f"[ABORT] D15 行 version/size={r15.get('version')}/{r15.get('size')}，期望 v1.1/86273 B；不写盘。")
    st = r15["state"]
    if "7 条贴边配音 dur_sec 1.2→1.3" not in st:
        sys.exit("[ABORT] D15 行未命中待订正的「7 条贴边配音 dur_sec 1.2→1.3」；不写盘。")
    if "最小余量 1.7s" not in st:
        sys.exit("[ABORT] D15 行未命中待订正的「最小余量 1.7s」；不写盘。")

    st = st.replace(
        "7 条贴边配音 dur_sec 1.2→1.3",
        "**11 条贴边配音 dur_sec 1.2→1.3**（本轮收敛 11 条 ＝ 判据 A「实算停留 <1.2」6 条 ∪ "
        "判据 B「out_sec == at_sec+dur_sec 位相等」3 条 ＝ 7 条，另 4 条为与派活口径及 OPS-05 断言"
        "统一化对齐；⚠️ **落盘态 D15 中 dur_sec==1.3 的实测为 12 条** —— 多出的 ep1 seq8（at 31.4）"
        "**本就是 1.3、不属本轮收敛**，两个数不可互相替代，见 Q40）",
    )
    st = st.replace(
        "**企划合规 02:05 复算：28 条配音 0 条越出本镜时间窗、0 条跨 D16 切点（最小余量 1.7s）"
        "→ D16 不需改、声音设计不需返修**",
        "**企划合规 02:28 对 D16 v1.5 重跑复算：28 条配音 0 条越出本镜时间窗、0 条跨 D16 切点，"
        "最小余量 **0.5s**（ep7 镜4：硬切 37.0s 落在配音起音 37.5s **之前** 0.5s，不跨界）"
        "→ D16 不需改、声音设计不需返修**"
        "（⚠️ 此前记录的「最小余量 1.7s（ep4 镜2，22.3s vs 镜窗 24.0s）」是**针对 D16 v1.3 的旧快照**，"
        "已作废，不得沿用；下游一升版该结论即失效，须重跑，见 Q39）",
    )
    r15["state"] = st

    # ---------- B. global_checks 追加 Q40（条数口径判据；Q39 已被并行实例占用：下游升版后核验结论作废） ----------
    gc = d18["global_checks"]
    ids = [g["id"] for g in gc]
    if "Q40" in ids:
        sys.exit("[ABORT] global_checks 已含 Q40，不重复登记；不写盘。")
    if ids[-1] != "Q39":
        sys.exit(f"[ABORT] global_checks 末条为 {ids[-1]}，期望 Q39；不写盘。")
    gc.append({
        "id": "Q40",
        "item": "**台账/留痕里的条数必须回磁盘实测，且必须区分「本轮收敛条数」「落盘态条数」「派单点名条数」三个数；"
                "生成脚本里写死的条数会被重跑写回，必须与落盘口径同步** —— 本轮实证：同一个「条数」在四处出现四个值 —— "
                "Chief 派单按浮点判据点「7 条」、`apply_d15_d16_sync.py` 留痕写「8 条」、声音设计实际收敛 "
                "**11 条**、D15 落盘态 dur_sec==1.3 实测 **12 条**（多出的 ep1 seq8 at 31.4 本就是 1.3，不属本轮收敛）。"
                "更严重的是脚本把「8 条」写死进 D16 留痕串 —— 脚本一重跑就把过期口径写回、与 D16 v1.5 的「11 条」表述并存。"
                "**做法**：① 引用条数前先回磁盘跑一次实测，并在回刷文本里写明口径来源"
                "（本轮：派单 7 条／收敛 11 条／落盘态 12 条／无配音锚点 3 条）；② 派单条数与执行条数不同时，"
                "回报必须写明**差额来源**；③ **生成脚本里任何写死的条数/版本/文案都是会被重跑写回的活雷** —— "
                "改内容必须同步改脚本，否则下次重跑即回退（见 Q27）；④ 脚本留痕串加**幂等守卫**"
                "（已有同标记则不追加）＋ **双向守恒断言**（1.3s 配音数 == 已对齐字幕行数），"
                "杜绝「断言过了但两套口径分叉」。",
        "method": "派单条数 vs 回报条数 vs 落盘实测 三方对照；grep 脚本内写死的条数与落盘文本是否一致；"
                  "脚本重跑后 diff 目标 JSON 应为空（零写盘）",
        "source": "企划合规 2026-10-23 02:32（R-032 收尾台账缺口回填时实测）",
        "severity": "中",
    })

    # ---------- C. dispatch_ledger 追加 OPS-07 ----------
    ledger = u01.setdefault("dispatch_ledger", [])
    if any(it.get("id") == "OPS-07" for w in ledger for it in w.get("items", [])):
        sys.exit("[ABORT] dispatch_ledger 已含 OPS-07，不重复记账；不写盘。")
    ledger.append({
        "wave": "R-032 收尾三岗回执 · 缺口回填 ＋ D14 派活撤单（企划合规单点维护）",
        "at": NOW,
        "items": [
            {
                "id": "OPS-07",
                "scope": "① apply_d15_d16_sync.py 留痕口径订正（8 条→11 条 ＋ 幂等守卫 ＋ 配音↔字幕双向守恒断言，"
                         "重跑零写盘已实测）② D18 D15 行条数/余量口径订正 ＋ Q40 条数判据 ③ project.json S10 登记 "
                         "④ 00_项目索引.md D15 行与状态栏回刷 ⑤ **D14 派活撤单**（已完成并锁定，见下）",
                "state": "企划合规代执行完成（validate error 0 / 11/11 PASS）",
            },
            {
                "id": "OPS-07-撤单",
                "scope": "D14 白模→H3 交接包派活（32 镜）",
                "state": "**撤单（不重复劳动）** —— 白模场景师已于 01:20–01:41 用同一套 `04_工具/handoff/` 工具链"
                         "落盘 D14 v1.1（32 个 ep<NN>_shot<NN> 目录 × 每镜 11 个文件 ＋ source_anchor_frames/），"
                         "企划合规 01:23/01:30/01:50/02:20 四次全量核验通过（package.json 32/32 过 D14ShotPackage schema、"
                         "与 D11 四项全等、preview_video 32/32 非空、h3_prompt 5,792~6,500 字符 0 超限、"
                         "实体清单与 manifest 可见对象 32/32 双向相等），**U01 已于 01:28 锁**；"
                         "工具链目录命名与派活描述一致（batch_build.py 第 79 行：ep/shot 齐备即输出 "
                         "ep<NN>_shot<NN>，仅内部日志用 G%04d 标签），**不存在「需按新工具链重出」的理由** → 本单撤销",
            },
        ],
    })

    # ---------- D. 版本与时间戳 ----------
    d18["version"] = "v1.23"
    u01["updated_at"] = NOW

    # ---------- E. deep-compare：只允许预期键变化 ----------
    def row_index(doc):
        for i, r in enumerate(u01["delivery_checks"]):
            if r.get("doc") == doc:
                return i
        sys.exit(f"[ABORT] delivery_checks 中找不到 {doc}；不写盘。")

    i15 = row_index("D15")
    allowed = {
        ("version",),
        ("unit_checks", 0, "updated_at"),
        ("unit_checks", 0, "dispatch_ledger"),
        ("unit_checks", 0, "delivery_checks", i15, "state"),
        ("global_checks",),
    }

    def diff_paths(a, b, path=()):
        out = []
        if type(a) is not type(b):
            return [path]
        if isinstance(a, dict):
            for k in set(a) | set(b):
                if k not in a or k not in b:
                    out.append(path + (k,))
                else:
                    out.extend(diff_paths(a[k], b[k], path + (k,)))
        elif isinstance(a, list):
            if len(a) != len(b):
                out.append(path + ("length", len(a), len(b)))
            else:
                for i, (x, y) in enumerate(zip(a, b)):
                    out.extend(diff_paths(x, y, path + (i,)))
        elif a != b:
            out.append(path)
        return out

    changed = set(diff_paths(before, d18))
    unexpected = [p for p in changed
                  if not any(len(p) >= len(a) and p[: len(a)] == a for a in allowed)]
    if unexpected:
        sys.exit(f"[ABORT] 检出 {len(unexpected)} 处非预期改动：{unexpected}；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print(f"[PLAN] 改动路径 {len(changed)} 处：")
        for p in sorted(changed, key=str):
            print("   ", p)
        return

    dump(p18, d18)
    print(f"[DONE] D18 已更新：v1.22 → {d18['version']}，改动路径 {len(changed)} 处")
    for p in sorted(changed, key=str):
        print("   ", p)


if __name__ == "__main__":
    main()
