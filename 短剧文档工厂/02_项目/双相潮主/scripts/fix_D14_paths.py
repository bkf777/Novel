#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 D14 交接包里的 /tmp 绝对路径断链（2026-10-23 Chief）。

问题：白模流水线在 /tmp/dcc-smoke/u01 下工作，产物里所有路径字段
（source_frame / preflight.source.path / manifest_path / timeline_plan.source.path …）
写的是 /tmp 绝对路径。锚点参考帧虽然已被拷进项目内，但**引用仍指向 /tmp**，
系统一旦清理临时目录，交接包就断链，用户的出片流程取不到参考帧。

修法：把 `/tmp/dcc-smoke/u01/<shot>/<rest>` 与 `/private/tmp/...` 统一重写为
`D14_shots/<shot>/<rest>` —— 相对 `units/<UNIT>/`，与 package_path 同基准。

幂等：已重写的路径不以 /tmp 开头，重复跑不会二次改写。
同步：必须同时改 D14.json 与逐镜 package.json，否则 V11「两者同形」会失败。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主")
UNIT = "U01"
SHOTS_DIR = ROOT / "units" / UNIT / "D14_shots"
D14 = ROOT / "units" / UNIT / "D14.json"
TMP_PREFIXES = ("/private/tmp/dcc-smoke/u01/", "/tmp/dcc-smoke/u01/")


def rewrite(obj):
    """递归重写；返回 (新对象, 命中条数)。"""
    n = 0
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nv, c = rewrite(v)
            out[k] = nv
            n += c
        return out, n
    if isinstance(obj, list):
        out = []
        for v in obj:
            nv, c = rewrite(v)
            out.append(nv)
            n += c
        return out, n
    if isinstance(obj, str):
        for pfx in TMP_PREFIXES:
            if obj.startswith(pfx):
                return "D14_shots/" + obj[len(pfx):], 1
        return obj, 0
    return obj, 0


def fix_file(p: Path) -> int:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return 0
    nd, n = rewrite(d)
    if n:
        p.write_text(json.dumps(nd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def main() -> int:
    targets = [D14] + sorted(SHOTS_DIR.glob("*/package.json")) \
        + sorted(SHOTS_DIR.glob("*/render_contract.json")) \
        + sorted(SHOTS_DIR.glob("*/preflight.json")) \
        + sorted(SHOTS_DIR.glob("*/appearance.json")) \
        + sorted(SHOTS_DIR.glob("*/manifest.json")) \
        + sorted(SHOTS_DIR.glob("*/shot_spec.json")) \
        + sorted(SHOTS_DIR.glob("*/h3_prompt_budget.json"))
    total = 0
    touched = 0
    for p in targets:
        if not p.is_file():
            continue
        n = fix_file(p)
        total += n
        if n:
            touched += 1
    print(f"扫描 {len(targets)} 个文件，命中 /tmp 路径 {total} 条，改写 {touched} 个文件")
    # 复查
    left = 0
    for p in targets:
        if p.is_file():
            try:
                t = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for pfx in TMP_PREFIXES:
                left += t.count(pfx)
    print(f"复查：残留 /tmp 路径引用 = {left} （应为 0）")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
