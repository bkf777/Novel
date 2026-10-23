#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 结构化 diff（只读）—— 交付物升版「恰好改了几处」的独立取证工具。

用途
----
任一岗交付物升版后，需要回答「除版本号与版本指针外，是否**恰好零改动**」——
即：① 时码叶子 0 处；② 结构差异 0 处；③ 其余差异**逐条列明**。
本工具**不依赖构建器自带的守卫**（守卫可能是作者自己的判据），而是独立比对两份 JSON。

类别划分（**键级条目**；标量级口径见输出第二行）
------------------
| 类别 | 判定 | 期望 |
|---|---|---|
| **版本号** | 路径末段 ＝ `version` | 1 处（升版本身） |
| **版本戳/指针** | 字符串差异**仅**为版本 token（`v1.x` → `v1.y`） | 活指针处数 |
| **时码** | 路径含时间语义键（`*_sec` / `in` / `out` / `at` / `dur` / `start` / `end` / `offset` / `duration`）且为数值 | **0 处** |
| **结构** | 新增／删除键、类型变化、数组长度变化 | **0 处** |
| **其他** | 其余值差异（如口径文本改写） | 逐条列明 |

用法
----
python3 scripts/diff_D16_unit.py --project 02_项目/双相潮主 --unit U01 \
    --old reports/_bak_U01_D16_liveptr_20261023-075449/D16.json \
    --new units/U01/D16.json [--json]

退出码
------
0 ＝ 读完并出报告（**不代表**零差异）；1 ＝ 参数／文件错误。

边界
----
**只读**：不写任何文件、不改任何交付物。Q76 副作用隔离：本脚本无写盘流程，
全部逻辑在 `main()` 内并由 `if __name__ == "__main__":` 守卫。
"""
import argparse
import difflib
import json
import os
import re
import sys

# 时间语义键（命中即判「时码类」）
TIME_KEY_RE = re.compile(
    r"(^|[._])(in|out|at|dur|duration|start|end|offset|sec|secs|second|seconds|"
    r"time|timestamp|tc|timecode)([._]|$)|_sec$|^sec$",
    re.I,
)
# 版本 token
VER_RE = re.compile(r"v\d+(?:\.\d+)*")


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def leaves(a, b, path="", out=None):
    """并行遍历两棵树，返回差异叶子列表。out 元素为 (kind, path, old, new)。"""
    if out is None:
        out = []
    if type(a) is not type(b):
        out.append(("结构", path, a, b))
        return out
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                # **新增键**＝新增块/新增字段（合法增量，如 Q57 机器可读口径块）；
                # 与「结构损坏」分列 —— 结构差异只保留「删键／改类型／数组非纯追加」。
                out.append(("新增", f"{path}.{k}", None, b[k]))
            elif k not in b:
                out.append(("结构", f"{path}.{k}", a[k], None))
            else:
                leaves(a[k], b[k], f"{path}.{k}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            # **纯追加**（旧列表是新区间的前缀，且原元素逐个未变）→ 单列「追加」，
            # 不算「结构差异」——S11「只追加不覆盖」的落盘表现为数组变长，
            # 若计入结构差异会把合规的追加误判为结构损坏。
            pure_append = len(b) > len(a) and a == b[:len(a)]
            out.append(("追加" if pure_append else "结构", path,
                        f"<长度 {len(a)}>", f"<长度 {len(b)}>"))
        for i, (x, y) in enumerate(zip(a, b)):
            leaves(x, y, f"{path}[{i}]", out)
    else:
        if a != b:
            out.append(("值", path, a, b))
    return out


def classify(kind, path, old, new):
    if kind == "追加":
        return "追加"
    if kind == "新增":
        return "新增"
    if kind == "结构":
        return "结构"
    key = path.rsplit(".", 1)[-1]
    if key == "version":
        return "版本号"
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        # 数值：看路径里的键名是否时间语义
        seg = re.split(r"[.\[]", path)
        if any(TIME_KEY_RE.search(s) for s in seg):
            return "时码"
        return "其他"
    if isinstance(old, str) and isinstance(new, str):
        told, tnew = VER_RE.findall(old), VER_RE.findall(new)
        if told != tnew:
            # 版本 token 集有变 → 再看「去掉版本 token 后」剩余文本是否相同：
            #   相同 ＝ 纯版本戳改写；不同 ＝ 版本戳＋句内文本改写
            return "版本戳" if VER_RE.sub("#", old) == VER_RE.sub("#", new) else "版本戳＋文本"
        return "其他"
    return "其他"


def brief(v, n=70):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def scalar_leaves(o):
    """标量叶子数：递归到标量层（str／int／float／bool／None）逐个计数。

    ⚠ 2026-10-23 补：键级条目数 ≠ 标量叶子数 —— 一个**新增键**在键级记 1 条，
    但其子树展开到标量可能是 N 个（D16 U02 的 `d15_version_history` 块 ＝ 10 个标量／集）。
    两个数都对但**不可互代**，故本工具同给两个口径。
    """
    if isinstance(o, dict):
        return sum(scalar_leaves(v) for v in o.values())
    if isinstance(o, list):
        return sum(scalar_leaves(x) for x in o)
    return 1


def inline_segments(old, new, ctx=28):
    """长文本段级内联 diff —— 只打印**变动片段**及少量上下文。

    用途：口径文本动辄数千字，整段打印会淹没其中真正的改动点；
    本函数让「长字符串里到底改了几处、改了什么」一眼可见（活指针处数即变动片段数）。
    """
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        pre = old[max(0, i1 - ctx):i1]
        post = old[i2:i2 + ctx]
        out.append(f"…{pre}【−{old[i1:i2]!r} → ＋{new[j1:j2]!r}】{post}…")
    return out or ["（无逐字差异，差异来自类型/结构）"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--old", required=True, help="旧版 JSON 路径（相对 --project 或绝对）")
    ap.add_argument("--new", default=None, help="新版 JSON 路径（默认 units/<unit>/D16.json）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = ap.parse_args()

    root = args.project
    if not os.path.isdir(root):
        cand = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            args.project)
        if os.path.isdir(cand):
            root = cand
        else:
            sys.exit(f"[ABORT] 项目目录不存在：{args.project}")

    def rp(p):
        return p if os.path.isabs(p) else os.path.join(root, p)

    p_old = rp(args.old)
    p_new = rp(args.new) if args.new else os.path.join(root, "units", args.unit, "D16.json")
    for p in (p_old, p_new):
        if not os.path.isfile(p):
            sys.exit(f"[ABORT] 文件不存在：{p}")

    old, new = load(p_old), load(p_new)
    diffs = leaves(old, new)
    cats = {}
    for kind, path, o, n in diffs:
        cats.setdefault(classify(kind, path, o, n), []).append((path, o, n))

    n_time = len(cats.get("时码", []))
    n_struct = len(cats.get("结构", []))
    n_append = len(cats.get("追加", []))
    n_new = len(cats.get("新增", []))
    total = len(diffs)

    # ── 标量叶子级口径（键级条目的子树展开）──
    n_scalar = 0
    for kind, path, o, n in diffs:
        if kind == "新增":
            n_scalar += scalar_leaves(n)
        elif kind == "结构" and o is not None and not isinstance(o, str):
            n_scalar += scalar_leaves(o)
        else:
            n_scalar += 1

    if args.json:
        print(json.dumps({
            "old": p_old, "new": p_new,
            "diff_leaf_total": total,
            "diff_scalar_leaf_total": n_scalar,
            "by_category": {k: len(v) for k, v in cats.items()},
            "time_leaves": n_time, "struct_leaves": n_struct,
            "append_leaves": n_append, "new_key_leaves": n_new,
            "detail": {k: [{"path": p, "old": brief(o, 200), "new": brief(n, 200)} for p, o, n in v]
                       for k, v in cats.items()},
        }, ensure_ascii=False, indent=2))
        return

    print("=" * 74)
    print(f"D16 结构化 diff（只读）　单元 {args.unit}")
    print(f"  旧：{p_old}")
    print(f"  新：{p_new}")
    print("=" * 74)
    print(f"差异条目总数（**键级**口径）：**{total}**")
    print(f"差异叶子数（**标量级**口径）：**{n_scalar}**")
    print("ℹ 口径说明：**键级** ＝ 一个新增／删除键记 1 条；**标量级** ＝ 该键子树展开到标量后计数。"
          "两个数都对但**不可互代**，本工具两者同给。（数组纯追加项按 1 计，未逐标量展开。）")
    for k in sorted(cats):
        print(f"  · {k}：{len(cats[k])} 处")
    print()
    print(f"▶ **时码叶子：{n_time} 处**　（期望 0）　→ {'✅ 零改动' if n_time == 0 else '❌ 存在时码改动'}")
    print(f"▶ **真结构差异：{n_struct} 处**　（期望 0）　→ {'✅ 零结构改动' if n_struct == 0 else '❌ 存在结构改动'}")
    if n_append:
        print(f"ℹ **数组纯追加：{n_append} 处**（S11「只追加不覆盖」的正常落盘形态："
              f"旧列表为新列表前缀、原元素逐个未变 → **不计入结构差异**）")
    if n_new:
        print(f"ℹ **新增键：{n_new} 处**（新增块/新增字段，合法增量 → **不计入结构差异**）")
    print()
    for k in ("版本号", "版本戳", "版本戳＋文本", "追加", "新增", "时码", "结构", "其他"):
        if k not in cats:
            continue
        print(f"── {k}（{len(cats[k])}）" + "─" * max(0, 60 - len(k)))
        for p, o, n in cats[k]:
            print(f"   {p}")
            if k in ("时码", "结构"):
                print(f"      旧: {brief(o, 110)}")
                print(f"      新: {brief(n, 110)}")
            elif k == "其他" and isinstance(o, str) and isinstance(n, str):
                for seg in inline_segments(o, n):
                    print(f"      {seg}")
        print()


if __name__ == "__main__":
    main()
