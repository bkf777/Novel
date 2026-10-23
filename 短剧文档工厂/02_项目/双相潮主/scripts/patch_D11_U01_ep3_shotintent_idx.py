#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 U01 ep3 镜3 的 `shot_intent` 引文 idx 漂移修复（分镜导演岗 · 一次性守卫式补丁）。

起因
----
台本编剧 2026-10-23 11:19:04 落 `units/U01/D08.json` **v1.11**，ep3 body **重排**
（15 条，带 `shot_intent` 的 idx 由 3／8／12 变为 **1／4／9／13**）⇒
`units/U01/D11.json` v1.11 的 ep3 镜3 note 里 **「body[8]」指向的已不是带
`shot_intent` 的那条**（现 idx 8 ＝「面板四维数值同时浮现，四项依次跳动。」，无 SI；
承载该 SI 的是 **idx 9**）。

实测（`check_D08_D11_shotintent.mjs --unit U01` 现印）：
    ⚠️ 引文/引用提示 1 条：ep3 镜3: note 引用 body[8]，该条无 shot_intent
（该提示**不计入硬冲突**，但确为**引文漂移**——idx 指向已错位。）

本脚本只改**一个字符**（`body[8]` → `body[9]`）＋ version。

守卫（缺一不可）
----------------
① **版本守卫**：盘面 D11 U01 version 必须 ＝ `v1.11`，否则 `[NO-OP]` exit 0（防整块回退）。
② **内容指纹自证**：目标 note 必须含「body[8] 要求骨纹第一次亮起」；且
   `D08 v1.11` 的 `ep3 body[9].shot_intent` 必须含「必须给到独立可辨的视觉呈现，
   不与人体同框混作」——**证明新 idx 正确**（不靠 idx 猜）。
③ **命中断言**：全 D11 U01 内 `body[8]` 与 `body[9]` 的 note 引用必须**恰好命中 1 处**
   （即 ep3 镜3），多一处即 `[ABORT]`。
④ **结构差异白名单**：只允许 `.version` 与
   `.episodes[2].shots[2].note` 变动，越界 `[ABORT]`。
⑤ **幂等**：目标 note 已含 `body[9]` → `[NO-OP]` exit 0。

边界
----
只改 `units/U01/D11.json`；不碰 D08／D15／D16／D12／D13／D14／D18／项目索引／他岗章节。
**不改** `shotintent_map_U01.mjs`（本岗已于同批次单独重刷 ep3 三行）。
**不处理** ep3 body[1]「「比上一趟早。」」的 D11 承接缺口 —— 台词归 D08 owner，
本岗只报不改（台账 §125.15 登记、已报总控／台本编剧）。
不生成图片/视频/音频，不合成 TTS/BGM，不提交 H3 付费生成，不投流上架。
"""
import json
import os
import shutil
import sys
import time

D11_FROM = "v1.11"
D11_TO = "v1.12"
D08_PATH = "shared/../units/U01/D08.json"
OLD_REF = "body[8]"
NEW_REF = "body[9]"
FINGER_OLD = "body[8] 要求骨纹第一次亮起"
FINGER_NEW = "必须给到独立可辨的视觉呈现，不与人体同框混作"


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def collect_diff(a, b, path=""):
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
    elif a != b:
        out.append(path)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proj = args.project
    if not os.path.isabs(proj):
        factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for cand in (os.path.join(factory, proj), os.path.abspath(proj),
                     os.path.join(os.getcwd(), proj)):
            if os.path.isfile(os.path.join(cand, "units", "U01", "D11.json")):
                proj = cand
                break
    p11 = os.path.join(proj, "units", "U01", "D11.json")
    p08 = os.path.join(proj, "units", "U01", "D08.json")
    if not os.path.isfile(p11):
        sys.exit(f"[ABORT] 未找到 {p11}")

    d11 = load(p11)
    d08 = load(p08)

    # ── 守卫 ①：版本锚定 ──
    cur = d11.get("version")
    if cur != D11_FROM:
        print(f"[NO-OP] D11 U01 当前 version={cur}（≠ 锚定 {D11_FROM}）："
              f"本脚本为一次性 {D11_FROM}→{D11_TO} 引文漂移修复，已演进则不写盘。")
        return

    # ── 守卫 ②：内容指纹自证（D08 侧证明新 idx 正确）──
    ep3_body = next(e for e in d08["episodes"] if e.get("ep") == 3).get("body") or []
    if len(ep3_body) <= 9:
        sys.exit("[ABORT] D08 ep3 body 不足 10 条，不写盘。")
    si9 = str(ep3_body[9].get("shot_intent") or "")
    if FINGER_NEW not in si9:
        sys.exit(f"[ABORT] D08 ep3 body[9] 的 shot_intent 不含指纹「{FINGER_NEW}」，"
                 f"新 idx 未获证，不写盘。")
    si8 = ep3_body[8].get("shot_intent")
    if si8:
        sys.exit("[ABORT] D08 ep3 body[8] 仍带 shot_intent，本脚本前提不成立，不写盘。")

    # ── 守卫 ③：命中断言（与 check_D08_D11_shotintent.mjs 同源）──
    # ⚠️ 判据必须是「**引用位现盘无 shot_intent**」的**失配处数**，
    #    **不是** note 文字里 `body[8]` 的**出现次数** —— 全 D11 U01 内
    #    「body[8]」文字出现 2 处，其中 1 处指对的（那集 body[8] 仍有 SI），
    #    按文字计数会误判「命中 2 处」而误 [ABORT]。
    import re as _re
    eps08 = {e.get("ep"): (e.get("body") or []) for e in d08.get("episodes") or []}
    bad_refs = []
    for e in d11.get("episodes") or []:
        epn = e.get("ep")
        body08 = eps08.get(epn) or []
        for s in e.get("shots") or []:
            note = str(s.get("note") or "")
            for m in _re.finditer(r"body\[(\d+)\]", note):
                i = int(m.group(1))
                if i >= len(body08) or not body08[i].get("shot_intent"):
                    bad_refs.append((epn, s.get("shot_id"), i, note))
    if len(bad_refs) != 1:
        sys.exit(f"[ABORT] D11 U01 内 **引文失配** {len(bad_refs)} 处（期望恰好 1 处），"
                 f"不写盘。失配明细：{[(b[0], b[1], b[2]) for b in bad_refs]}")
    ep, sid, bad_idx, note = bad_refs[0]
    if (ep, sid, bad_idx) != (3, 3, 8):
        sys.exit(f"[ABORT] 失配位置 ep{ep} 镜{sid} body[{bad_idx}] ≠ 期望 ep3 镜3 body[8]，不写盘。")
    if FINGER_OLD not in note:
        sys.exit(f"[ABORT] 目标 note 不含指纹「{FINGER_OLD}」，不写盘。")
    if NEW_REF in note:
        print(f"[NO-OP] 目标 note 已含 `{NEW_REF}`，无需修复。")
        return

    before = load(p11)
    target = next(s for e in d11["episodes"] if e.get("ep") == ep
                   for s in e["shots"] if s.get("shot_id") == sid)
    target["note"] = target["note"].replace(OLD_REF, NEW_REF)
    d11["version"] = D11_TO

    # ── 守卫 ④：结构差异白名单 ──
    diffs = collect_diff(before, d11)
    allowed = {".version", f".episodes[2].shots[2].note"}
    for dpath in diffs:
        if dpath not in allowed:
            print(f"[ABORT] 越界改动：{dpath}")
            sys.exit(1)
    print(f"[DIFF] 改动 {len(diffs)} 处：{diffs}")
    print(f"[HIT] ep{ep} 镜{sid} note 的 `{OLD_REF}` → `{NEW_REF}`；version {D11_FROM} → {D11_TO}")
    print("[CHECK] 仅 note 内 1 个字符 ＋ version 变动；镜位/时码/画面事实零改动")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        return

    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(proj, "reports", f"_bak_D11_U01_ep3_si_idx_{ts}")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p11, os.path.join(bak, "D11.json"))
    print(f"[BAK] 已备份 → {bak}/D11.json")

    dump(p11, d11)
    print(f"[DONE] D11 U01 → {d11['version']} 已落盘：{p11}")
    print(f"[SIZE] {os.path.getsize(p11)} bytes")


if __name__ == "__main__":
    main()
