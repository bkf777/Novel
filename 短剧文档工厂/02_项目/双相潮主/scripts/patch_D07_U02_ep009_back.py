#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_D07_U02_ep009_back.py —— U02-R32 断言式补丁

背景（企划合规 06:5x 裁定，台账 §九十六.3）：
  同一动作「陆沉指节敲数据板两下」，上游两件写法相反 ——
    · D07 U02 v1.2 ep009 段3 note：「……指节敲了两下**板面**」
    · D08 U02 v1.4 body[10].text：「陆沉没看脸，先接过数据板，指节敲了两下**背面**。」
  裁定：**以剧本层 D08 正文为准**，D07 应改为「背面」；
  D11 的 `visual_facts`（「指节在板背面敲了两下」）与 D12 卡片均已同向 → D07 是三者中唯一异项。

⚠️ 派单前提订正（故事架构 2026-10-23 实测）：
  企划合规 §九十六.3 写「D07 由脚本生成 → 须改生成脚本后重跑，禁只改 JSON」。
  **实测不成立**：本仓 `scripts/` 下**无任何脚本写 `units/U02/D07.json`**
  （`build_*` 只覆盖 D08/D09/D11/D12/D13/D15/D16；`patch_ledger_*` 只在台账正文提及路径）。
  → D07 是**手写 JSON**，故按派单对手写件的纪律：**带命中数断言的补丁脚本**执行。

断言清单（任一对不上即中止，不写盘）：
  A1 D07 文件存在且 JSON 可解析
  A2 「板面」在 D07 全文命中 **恰好 1** 处（同一事实；D06/D08 均已 0 命中）
  A3 该命中处位于 ep009 的 quad_segments[3].note，且**旧文本逐字匹配**
  A4 幂等：若已是「背面」→ 跳过并报「已应用」（不重复改、不报错）
  A5 落盘差异**只允许** = {version, 目标 note 文本}；出现任何未声明差异 → 中止并回滚

备份：落 `reports/_bak_D07_20261023/`（**不在 units/ 交付目录内留备份**）。

用法：
  python3 scripts/patch_D07_U02_ep009_back.py --project 02_项目/双相潮主
  python3 scripts/patch_D07_U02_ep009_back.py --project 02_项目/双相潮主 --check   # 只查不改
退出码：0 = 达成（改过或已应用）；1 = 断言不过/中止；2 = 参数或前置缺失
"""

import argparse
import json
import os
import shutil
import sys
import time

OLD_FRAG = "指节敲了两下板面"
NEW_FRAG = "指节敲了两下背面"
NOTE_FULL_OLD = "灯下露出灰斑，陆沉先看数据板再看人，指节敲了两下板面"
NOTE_FULL_NEW = "灯下露出灰斑，陆沉先看数据板再看人，指节敲了两下背面"
BAIL = "板面"          # 同一事实的残留判据
NEXT_VERSION = "v1.3"


def die(code, msg):
    print(f"❌ {msg}")
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="项目根（内含 shared/ 与 units/）")
    ap.add_argument("--check", action="store_true", help="只做断言检查，不写盘")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    p = os.path.join(root, "units", "U02", "D07.json")
    if not os.path.isfile(p):
        die(2, f"找不到 {p}")
    raw = open(p, encoding="utf-8").read()

    # A1 可解析
    try:
        data = json.loads(raw)
    except Exception as e:
        die(1, f"A1 失败：D07 非合法 JSON（{e}）")

    # A2 「板面」全文命中恰好 1
    hits = raw.count(BAIL)
    if hits == 0:
        # A4 幂等：确认已是新写法
        if NEW_FRAG in raw and OLD_FRAG not in raw:
            print(f"✅ A4 幂等命中：「{BAIL}」已 0 处，「{NEW_FRAG}」已在位 → 本脚本**无需再改**（已应用）")
            print(f"   交付物现值：units/U02/D07.json v{data.get('version')}｜{len(raw.encode())} B")
            return 0
        die(1, f"A2/A4 失败：「{BAIL}」0 命中，但「{NEW_FRAG}」也不在位 → 状态异常，请人工核")
    if hits != 1:
        die(1, f"A2 失败：「{BAIL}」命中 {hits} 处（应恰好 1）→ 中止，不写盘")

    # A3 逐字定位：ep009 的 quad_segments[3].note（同时记下列下标，供 A5 动态推导声明路径）
    target = None
    eps_list = data.get("episodes", [])
    for ei, ep in enumerate(eps_list):
        if ep.get("ep") != 9:
            continue
        for si, seg in enumerate(ep.get("quad_segments", [])):
            if seg.get("index") == 3 and seg.get("note") == NOTE_FULL_OLD:
                target = (ei, si, ep, seg)
    if target is None:
        # 退一步：找同 ep 下 note 含 OLD_FRAG 的段，打印上下文供人工核
        ctx = [f"ep{ep.get('ep')} seg{s.get('index')}: {s.get('note')}"
               for ep in eps_list for s in ep.get("quad_segments", [])
               if OLD_FRAG in str(s.get("note", ""))]
        die(1, "A3 失败：未找到 ep009 quad_segments[3].note 的逐字匹配。实际命中位置：\n   " +
               "\n   ".join(ctx))
    ei, si, ep9, seg3 = target
    print(f"✅ A3 命中：ep{ep9['ep']}（episodes[{ei}]）quad_segments[{seg3['index']}]（list 下标 {si}）.note 逐字匹配")
    print(f"   旧：{seg3['note']}")
    print(f"   新：{NOTE_FULL_NEW}")

    if args.check:
        print("ℹ️ --check：只验不改，未写盘。")
        return 0

    # 落盘差异声明式变换：只允许 version + 目标 note 两处
    new_seg3 = dict(seg3)
    new_seg3["note"] = NOTE_FULL_NEW
    new_data = json.loads(raw)
    for e in new_data.get("episodes", []):
        if e.get("ep") == 9:
            for s in e.get("quad_segments", []):
                if s.get("index") == 3:
                    s["note"] = NOTE_FULL_NEW
    old_version = new_data.get("version")
    new_data["version"] = NEXT_VERSION

    # A5：结构化差异必须恰为声明集合
    def flat(o, pre=""):
        out = {}
        if isinstance(o, dict):
            for k, v in o.items():
                out.update(flat(v, f"{pre}/{k}"))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                out.update(flat(v, f"{pre}[{i}]"))
        else:
            out[pre] = o
        return out

    fo, fn = flat(data), flat(new_data)
    diff_keys = sorted(k for k in set(fo) | set(fn) if fo.get(k) != fn.get(k))
    allowed = {"/version", f"/episodes[{ei}]/quad_segments[{si}]/note"}
    unexpected = [k for k in diff_keys if k not in allowed]
    if unexpected:
        die(1, f"A5 失败：出现未声明差异 {unexpected} → 中止，不写盘")
    if not diff_keys:
        die(1, "A5 失败：差异集为空（声明的改动未生效）→ 中止，不写盘")
    print(f"✅ A5 差异集恰为声明项：{diff_keys}")

    # 备份（不进 units/）
    bak_dir = os.path.join(root, "reports", "_bak_D07_20261023")
    os.makedirs(bak_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(p, os.path.join(bak_dir, f"D07.json.bak-{stamp}"))
    print(f"ℹ️ 备份已落：reports/_bak_D07_20261023/D07.json.bak-{stamp}")

    # 写盘（保持缩进/中文风格：与仓内既有 JSON 序列化一致）
    with open(p, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # 落盘后自检
    after = open(p, encoding="utf-8").read()
    if after.count(BAIL) != 0:
        die(1, f"落盘后自检失败：「{BAIL}」残留 {after.count(BAIL)} 处")
    d2 = json.loads(after)
    print(f"✅ 落盘完成：units/U02/D07.json {old_version} → {d2.get('version')}｜{len(after.encode())} B")
    print(f"✅ 落盘后自检：「{BAIL}」残留 0 处；「{NEW_FRAG}」在位 1 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
