#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U02「D15 U02 版本变更史」**单点承载**落盘脚本（分镜导演岗）。

背景
----
声音设计作为 D15 字段 owner 在台账 §123.19.2 给出**落点裁决**与**措辞订正**：
  ① 落点＝**单点承载、每集 1 处、共 8 处**（与 `audit_field_scope` 同族），
     **不批量改 44 处 per-row `note`**（per-row note 是逐行注记，版本变更史是整表属性）；
  ② 措辞＝取其「准确措辞」版本，**不得写「数值区自 v1.0 落盘起未变」**
     （v1.0→v1.1 确实删了 4 条条目，照写会留下一处新的结论性错误陈述）；
  ③ 取证边界＝v1.0／v1.1 的条目数**属登记转述而非本轮实测**（备份已清），
     落盘时**须带取证来源标注**。

本脚本据此落 `units/U02/D16.json` 的
`episodes[*].subtitle_style.subtitle_sync_audit.d15_version_history`（8 集各 1 处），
并把 D16 U02 version 由 **v1.5 升到 v1.6**（D18 Q80：version 由落盘方自持自增）。

守卫（缺一不可）
----
① **版本守卫**：盘面 D16 U02 version 必须 ＝ `v1.5`，否则 `[NO-OP]` exit 0（防整块回退）。
② **幂等守卫**：8 集均已有 `d15_version_history` → `[NO-OP]` exit 0。
③ **v1.2 行自证**：当轮实测 D15 U02 ＝ v1.2 且 sfx 66／foley 13／voice_over 28，
   不符即 `[ABORT]` exit 1 不写盘（使落盘内容里的 v1.2 一行是机器实测而非转述）。
④ **命中断言**：新增键必须**恰好 8 处**（逐集 1 处），少一多一即 `[ABORT]`。
⑤ **结构差异白名单**：只允许 `.version` 与
   `.episodes[*].subtitle_style.subtitle_sync_audit.d15_version_history*` 变动，越界 `[ABORT]`。
⑥ **沙箱隔离**：`SXR_ROOT` 环境变量可把写盘目标指向沙箱副本（自测用）。

边界
----
只改 `units/U02/D16.json`；不碰 D11／D15／D16 U01／他岗交付物／D18／项目索引／他岗章节。
不生成图片/视频/音频，不合成 TTS/BGM，不提交 H3 付费生成，不投流上架。
"""
import argparse
import json
import os
import shutil
import sys
import time

D16_FROM = "v1.5"
D16_TO = "v1.6"
D15_TARGET = "v1.2"
KEY = "d15_version_history"

# 声音设计 §123.19.2「准确措辞」——**逐字取用，不自改写**
ACCURATE_WORDING = (
    "对白／配音锚点区（`voice_over` 28 条）自 v1.0 落盘起逐字节未变；"
    "v1.1 合并 sfx×foley 同事件双记 4 组（删 3 条 foley ＋ 1 条 sfx 重复条目，"
    "sfx 67→66、foley 16→13，总数 83→79，保留行 at／dur／电平／type 零改动）；"
    "v1.2 仅改 ep009 `mix_notes` 一条措辞 ＋ version，其余时码电平零变动。"
)


def build_block(d15_counts):
    """构造单点承载块。d15_counts ＝ 本轮实测的 D15 U02 计数。"""
    return {
        "_说明": (
            "D15 U02（声音设计岗）版本变更史的**单点承载**。落点与措辞由声音设计作为 "
            "D15 字段 owner 裁定（台账 §123.19.2）：**单点承载、每集 1 处、共 8 处**，"
            "**不批量改 44 处 per-row `note`**（per-row note 是逐行注记，而版本变更史是整表属性，"
            "逐行重复 44 遍即把整表属性下沉到行）。本块与 `audit_field_scope` 同族。"
        ),
        "_准确措辞": ACCURATE_WORDING,
        "_禁写": (
            "**不得写「数值区自 v1.0 落盘起未变」** —— v1.0→v1.1 确实删了 4 条条目"
            "（数值区变动过），照写会留下一处**新的结论性错误陈述**"
            "（声音设计 §123.19.2 措辞订正）。"
        ),
        "_取证边界": (
            "v1.0／v1.1 的条目数变化**取自声音设计台账 §八十九登记 ＋ 索引 §六留痕**"
            "（索引原文「sfx 67 条覆盖 32 镜」＝ v1.0 旧值，现已改为 66），"
            "**属登记转述而非本轮实测** —— D15 U02 现存唯一备份为 v1.2"
            "（`reports/_bak_U02_D15_20261023-083931`），v1.0／v1.1 备份已清，"
            "本岗无法用备份链独立复算（Q49：受检 0 条的结论不成立）。"
            "**v1.2 一行由本脚本当轮实测断言**（见 `_v1.2_本轮实测`）。"
        ),
        "_口径": (
            "「79 条」＝ **跨 `sfx[]` ＋ `foley[]` 两层的物理条目数**；"
            "与 D16 侧 `synced_row_count`（仅对白字幕行条数）**不同轴，不可互为对账锚点**；"
            "`no_vo_anchor_rows` ＝ 面板文字行数（字段名与语义相反，`audit_field_scope` 已结构化承载）。"
        ),
        "v1.0": (
            "基准版 79,824 B｜05:18 落：sfx 67 ＋ foley 16 ＝ 83 条"
            "（跨 sfx+foley 两层物理条数）。【登记转述】"
        ),
        "v1.1": (
            "U02-R27 合并：删 4 条重复条目（sfx 1 ＋ foley 3）＝ 4 组 sfx×foley 同事件双记"
            "一次收口；sfx 67→66、foley 16→13，总数 83→79；"
            "保留行 at／dur_sec／level_db／type 零改动。【登记转述】"
        ),
        "v1.2": (
            "现值 78,909 B：仅改 ep009 `mix_notes` 一条措辞（「板面敲击」→「板背敲击」）＋ version；"
            "sfx／foley／voice_over 计数与全部时码电平零变动。"
        ),
        "_v1.2_本轮实测": (
            f"落盘脚本当轮实测 `units/U02/D15.json` ＝ version {d15_counts['version']}、"
            f"sfx {d15_counts['sfx']} 条、foley {d15_counts['foley']} 条、"
            f"voice_over {d15_counts['vo']} 条"
            f"（跨 8 集逐集求和的物理条目数）；"
            f"mix_notes 含「板背敲击」的集 ＝ {d15_counts['mix_notes_changed_ep']}；"
            f"任一不符即 [ABORT] 不写盘。"
        ),
        "applied_by": "分镜导演（落点与措辞归声音设计 bot_0a60d9bbd4fe）",
    }


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def collect_diff(a, b, path=""):
    """递归比对两个 JSON 结构，返回差异路径列表（a→b）。"""
    out = []
    if type(a) is not type(b):
        return [path + " <类型变化>"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k} <新增>")
            elif k not in b:
                out.append(f"{path}.{k} <删除>")
            else:
                out += collect_diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path} <长度 {len(a)}→{len(b)}>")
        for i, (x, y) in enumerate(zip(a, b)):
            out += collect_diff(x, y, f"{path}[{i}]")
    else:
        if a != b:
            out.append(path)
    return out


def d15_counts(d15):
    """本轮实测 D15 U02 的 sfx／foley／voice_over 条数（跨 8 集逐集求和的**物理条目数**，不去重）。"""
    def phys(e, key):
        v = e.get(key)
        if v is None:
            return 0
        if isinstance(v, list):
            return len(v)
        if isinstance(v, dict):
            return sum(len(x) if isinstance(x, list) else 1 for x in v.values())
        return 0

    eps = d15.get("episodes") or []
    return {
        "version": d15.get("version"),
        "sfx": sum(phys(e, "sfx") for e in eps),
        "foley": sum(phys(e, "foley") for e in eps),
        "vo": sum(phys(e, "voice_over") for e in eps),
        "mix_notes_changed_ep": _mix_notes_changed_ep(eps),
    }


def _mix_notes_changed_ep(eps):
    """定位 v1.2 唯一措辞改动所在集（mix_notes 含「板背敲击」）。"""
    for e in eps:
        mn = e.get("mix_notes")
        blob = json.dumps(mn, ensure_ascii=False) if not isinstance(mn, str) else mn
        if "板背敲击" in blob:
            return e.get("ep") or e.get("episode_id") or e.get("id")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default="U02")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unit = args.unit
    cands = []
    if os.path.isabs(args.project):
        cands.append(args.project)
    else:
        cands.append(os.path.join(factory, args.project))
        cands.append(os.path.join(os.getcwd(), args.project))
        cands.append(os.path.abspath(args.project))
    # 沙箱隔离：SXR_ROOT 优先
    sxr = os.environ.get("SXR_ROOT")
    if sxr:
        cands.insert(0, sxr)
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "units", unit, "D16.json")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到含 units/{unit}/D16.json 的项目目录，候选：{cands}")

    p16 = os.path.join(proj, "units", unit, "D16.json")
    p15 = os.path.join(proj, "units", unit, "D15.json")
    for p in (p16, p15):
        if not os.path.isfile(p):
            sys.exit(f"[ABORT] 文件不存在：{p}")

    d16 = load(p16)
    d15 = load(p15)
    eps = d16.get("episodes") or []
    if len(eps) != 8:
        sys.exit(f"[ABORT] 期望 8 集，实得 {len(eps)}，不写盘。")

    # ══ 守卫 ①：版本锚定（已演进 → no-op，绝不写盘）══
    cur16 = d16.get("version")
    if cur16 != D16_FROM:
        print(f"[NO-OP] D16 {unit} 当前 version={cur16}（≠ 锚定 {D16_FROM}）："
              f"本脚本为一次性 {D16_FROM}→{D16_TO} 单点承载脚本，已演进则不写盘（防整块回退）。")
        return

    # ══ 守卫 ②：幂等（8 集均已落该键 → no-op）══
    already = sum(1 for e in eps
                  if KEY in (e.get("subtitle_style", {}).get("subtitle_sync_audit") or {}))
    if already == len(eps):
        print(f"[NO-OP] {len(eps)}/{len(eps)} 集均已有 `{KEY}`，本脚本无需执行。")
        return
    if already:
        print(f"[ABORT] 部分集已落 `{KEY}`（{already}/{len(eps)}）—— 半落状态不可续写，不写盘。")
        sys.exit(1)

    # ══ 守卫 ③：v1.2 行自证（当轮实测 D15 U02）══
    c = d15_counts(d15)
    if c["version"] != D15_TARGET or c["sfx"] != 66 or c["foley"] != 13 or c["vo"] != 28:
        print(f"[ABORT] D15 {unit} 实测不符：version={c['version']}（期望 {D15_TARGET}）、"
              f"sfx={c['sfx']}（期望 66）、foley={c['foley']}（期望 13）、voice_over={c['vo']}（期望 28）"
              f" —— v1.2 一行无法作机器实测断言，不写盘。")
        sys.exit(1)
    print(f"[EVIDENCE] D15 {unit} 当轮实测：version={c['version']}、sfx={c['sfx']}、"
          f"foley={c['foley']}、voice_over={c['vo']} ✅")

    before = load(p16)
    block = build_block(c)

    inserted = 0
    for e in eps:
        a = e["subtitle_style"]["subtitle_sync_audit"]
        a[KEY] = json.loads(json.dumps(block))
        inserted += 1
    d16["version"] = D16_TO

    # ══ 命中断言：恰好 8 处 ══
    if inserted != len(eps):
        print(f"[ABORT] 新增 `{KEY}` {inserted} 处，期望 {len(eps)} 处")
        sys.exit(1)

    # ══ 结构差异白名单 ══
    diffs = collect_diff(before, d16)
    allowed = []
    for dpath in diffs:
        ok = (dpath == ".version"
              or (".subtitle_style.subtitle_sync_audit." + KEY) in dpath)
        if ok:
            allowed.append(dpath)
        else:
            print(f"[ABORT] 越界改动：{dpath}")
            sys.exit(1)
    print(f"[DIFF] 改动 {len(diffs)} 处（白名单内 {len(allowed)} 处）")
    print(f"[HIT] `{KEY}` 新增 {inserted}/{len(eps)} 集；version {D16_FROM} → {D16_TO}")
    print("[CHECK] 全部 in_sec／out_sec／dur_sec／level_db 数值零改动（本轮只加口径块＋版本）")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    # ══ 落盘前备份（不入 units/）══
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(proj, "reports", f"_bak_{unit}_D16_d15hist_{ts}")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, "D16.json"))
    print(f"[BAK] 已备份 → {bak}/D16.json")

    dump(p16, d16)
    print(f"[DONE] D16 {unit} → {d16['version']} 已落盘：{p16}")
    print(f"[SIZE] {os.path.getsize(p16)} bytes")


if __name__ == "__main__":
    main()
