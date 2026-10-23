#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
selftest_D05_bone_scopes.py —— D05 首用集 patch 脚本 **A6 判据**的 Q62 负测（三腿 ＋ 真盘零写入）

【为什么有这一支负测（2026-10-23 11:3x）】
本岗脚本 `patch_D05_firstuse_shadow_bone.py` 的 A6 断言原实现＝「units/ 全库原文任一命中「骨龙」即拒写」。
11:2x 台本编剧落盘 U03 D08 v1.4／D09 v1.1 后，其中
  · D08 `episodes[*].compliance_notes[*]` ＝「D05 骨龙词条：first_use_ep=26，ep026 之前禁「骨龙」二字…」
  · D09 `voice_cards[*].forbidden_words[*]` ＝「★ 本单元台词禁出现「骨龙」二字…」
**逐字引述禁令本身** ⇒ 说明位／清单位（登记语境）＝ **同形异指**，**不是活跃违规**；
而 A6 全库字面扫描把它们算成命中 ⇒ **假红**（本脚本在现盘上**永久不可用**）。
⇒ 本岗裁定：**拒写权归 A5（受约束面＝台词面/字幕面，母本 `rules.json` `_term_first_use_note` 明文口径）**；
  A6 改为**分桶记账**（受约束面／说明位清单位／其它面），**只报告不阻断**。
⇒ 按 Q62（放宽必须配负测）配本支三腿。

【三腿设计（腿形 == 真盘真实落盘形态；沙箱在 /tmp；真盘零写入）】
  腿1 **基线放行**：沙箱（D05 置回 v1.5 备份 ＋ units 全量副本）⇒ 脚本跑通，**A5 受约束面 0**、
        **A6 说明位/清单位 14 处（只记账不拒写）**、**其它面 0**、脚本**写盘成功**。
  腿2 ⭐ **受约束面注入必须拒写**：向 U03 D09 `lines[0].text`（台词行，母本受检面）注入「骨龙」
        ⇒ 脚本**拒绝写盘**（A5 触发）⇒ 证拒写权未被放宽。
  腿3 ⭐ **说明位注入必须放行**：向 U03 D08 `episodes[0].compliance_notes[0]` 注入「骨龙」
        ⇒ 脚本**不因 A6 拒写**、写盘成功 ⇒ 证放宽只到「说明位/清单位」，未到「全部面」。

用法：python3 scripts/selftest_D05_bone_scopes.py --project 02_项目/双相潮主 [--source <01_漫剧策划>]
退出码：0 = 全过；1 = 有腿失败。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP = "reports/_bak_D05_firstuse_20261023-105451/D05.json"


def sha_size(p):
    b = open(p, "rb").read()
    return hashlib.sha256(b).hexdigest()[:16], len(b)


def build_sandbox(project_root, tag):
    """沙箱：units/ 全量副本 ＋ shared/D05.json 置回 v1.5 备份（使脚本走 A2–A9 落地路径）。"""
    sb = tempfile.mkdtemp(prefix=f"bone_scope_{tag}_")
    sd = os.path.join(project_root, "shared")
    if os.path.isdir(sd):
        os.makedirs(os.path.join(sb, "shared"), exist_ok=True)
        for f in os.listdir(sd):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(sd, f), os.path.join(sb, "shared", f))
    bkp = os.path.join(project_root, BACKUP)
    if os.path.isfile(bkp):
        shutil.copy2(bkp, os.path.join(sb, "shared", "D05.json"))
    ud = os.path.join(project_root, "units")
    if os.path.isdir(ud):
        for u in sorted(os.listdir(ud)):
            uu = os.path.join(ud, u)
            if not os.path.isdir(uu):
                continue
            d = os.path.join(sb, "units", u)
            os.makedirs(d, exist_ok=True)
            for f in os.listdir(uu):
                if f.endswith(".json"):
                    shutil.copy2(os.path.join(uu, f), os.path.join(d, f))
    return sb


def run_script(sb, source):
    cmd = [sys.executable, os.path.join(HERE, "patch_D05_firstuse_shadow_bone.py"),
           "--project", sb, "--source", source]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def inject_d09_dialogue(sb):
    """U03 D09 `lines[0].text`（台词行＝母本受检面）注入「骨龙」。"""
    p = os.path.join(sb, "units/U03/D09.json")
    d = json.load(open(p, encoding="utf-8"))
    lines = d.get("lines") or []
    if not lines:
        raise SystemExit("[ABORT] U03 D09 无 lines，无法构造受约束面注入形态")
    lines[0]["text"] = str(lines[0].get("text", "")) + " 骨龙"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "units/U03/D09.json lines[0].text"


def inject_d08_note(sb):
    """U03 D08 `episodes[0].compliance_notes[0]`（说明位＝登记语境）注入「骨龙」。"""
    p = os.path.join(sb, "units/U03/D08.json")
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0]
    notes = e.setdefault("compliance_notes", [])
    if not notes:
        notes.append("说明位注入：骨龙")
    else:
        notes[0] = str(notes[0]) + " 说明位注入：骨龙"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "units/U03/D08.json episodes[0].compliance_notes[0]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--source", required=True)
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    watch = ["shared/D05.json", "units/U03/D08.json", "units/U03/D09.json"]
    before = {}
    for rel in watch:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            before[rel] = sha_size(p)
            print(f"■ 真盘基准：{rel}｜sha256 {before[rel][0]}｜{before[rel][1]} B")

    failures, legs = [], []

    def leg(name, ok, note=""):
        legs.append((name, ok))
        print(f"  {'✅' if ok else '❌'} {name}" + (f"｜{note}" if note else ""))
        if not ok:
            failures.append(name)

    # ── 腿1：基线放行 ──
    sb = build_sandbox(root, "leg1")
    rc, out = run_script(sb, args.source)
    a5_ok = "台词面/字幕面（D11 dialogue＋D08 type=dialogue＋D09 lines＋D16 subtitle）命中 = 0" in out
    note_cnt = None
    for l in out.split("\n"):
        if "说明位/清单位 =" in l:
            try:
                note_cnt = int(l.split("说明位/清单位 =")[1].split("处")[0].strip())
            except Exception:
                note_cnt = None
    wrote = json.load(open(os.path.join(sb, "shared/D05.json"), encoding="utf-8")).get("version")
    ok1 = (rc == 0) and a5_ok and (note_cnt is not None and note_cnt > 0) and (wrote == "v1.6")
    leg("腿1 基线放行（A5 受约束面 0 ＋ A6 说明位只记账不拒写 ＋ 写盘成功 v1.6）",
        ok1, f"rc={rc}｜说明位命中 {note_cnt} 处｜沙箱 D05 version={wrote}")
    for l in out.split("\n"):
        if l.strip().startswith(("受约束面", "说明位/清单位 =", "其它面 =")) or "A6" in l:
            print(f"     {l.strip()}")
    if not ok1:
        failures.append("腿1 基线未通过 —— 说明位仍被拒写（假红未修）或 A5 口径失守")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿2：受约束面注入必须拒写 ──
    sb = build_sandbox(root, "leg2")
    p_inj = inject_d09_dialogue(sb)
    rc, out = run_script(sb, args.source)
    a5_hit = "[ABORT A5]" in out
    ok2 = (rc != 0) and a5_hit
    leg("腿2 ⭐ 受约束面注入必须拒写（台词面命中「骨龙」⇒ A5 拒绝写盘）",
        ok2, f"rc={rc}｜注入位 {p_inj}")
    for l in out.split("\n"):
        if "A5" in l or "台词面/字幕面命中" in l:
            print(f"     {l.strip()}")
    if not ok2:
        failures.append("腿2 受约束面注入未被拒写 —— 拒写权被误放宽（假绿）")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿3：说明位注入必须放行 ──
    sb = build_sandbox(root, "leg3")
    p_inj3 = inject_d08_note(sb)
    rc, out = run_gate = run_script(sb, args.source)
    a6_block = "[ABORT A6]" in out
    wrote3 = json.load(open(os.path.join(sb, "shared/D05.json"), encoding="utf-8")).get("version")
    ok3 = (rc == 0) and (not a6_block) and (wrote3 == "v1.6")
    leg("腿3 ⭐ 说明位注入必须放行（compliance_notes 引述不触发 A6 拒写）",
        ok3, f"rc={rc}｜注入位 {p_inj3}｜沙箱 D05 version={wrote3}")
    for l in out.split("\n"):
        if "说明位/清单位 =" in l or "其它面 =" in l:
            print(f"     {l.strip()}")
    if not ok3:
        failures.append("腿3 说明位注入仍被 A6 拒写 —— 假红未修（脚本在现盘上不可用）")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 真盘零写入 ──
    zero = True
    for rel, b0 in before.items():
        p = os.path.join(root, rel)
        a1 = sha_size(p)
        if a1 != b0:
            zero = False
            print(f"  ❌ 真盘被改动：{rel}｜{b0} → {a1}")
    leg("真盘零写入（3 份文件 sha256 前后全等）", zero,
        "｜".join(f"{r}:{v[0]}" for r, v in before.items()))
    if not zero:
        failures.append("真盘文件被负测改动 —— 违反沙箱纪律")

    passed = sum(1 for _, ok in legs if ok)
    print(f"■ 合计：{len(legs)} 腿（含真盘零写入）｜通过 {passed}｜失败 {len(failures)}")
    if failures:
        for f in failures:
            print(f"  ❌ {f}")
        return 1
    print("✅ A6 判据负测全过（拒写权只归受约束面；说明位/清单位只记账，未假绿）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
