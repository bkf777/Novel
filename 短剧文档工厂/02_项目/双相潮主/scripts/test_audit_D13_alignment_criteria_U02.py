#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D13↔白模落位审计判据负测：证明 audit_D13_white_model_alignment_U02.py 的判据**不是恒真**。

背景（2026-10-23 总控派活）：
  旧判据在 U02 报「⛔ 违规（白模层单方面挪主体）14 条」。实测：
    ① 其中 1 条是**纯假阳性** —— 脚本按 `prop["name"]` 匹配 PROP_POS 键，
       没�� D13 `props[].shots` 消歧，把 (B-10,64,"灰框面板") 的覆盖同时拿去和
       该场**两个**同名面板各比一次，凭空造出 dx=12.33 / dy=-10.91 的 12 米级假偏移
       （该面板 shots=[61]，压根不在 g64 场，白模层根本没建它）；
    ② 其余 13 条是**真实几何差异**，但 D13 已用 `props[].state`/`props[].note`
       登记了该镜的逐镜状态（D11 亦有明文）⇒ 白模层是**据 D11/D13 实现**，
       不是「单方面挪主体」，而是 D13 缺逐镜坐标字段造成的**登记债务**。
  旧判据把 ② 也判成违规 ⇒ 该检查在任何正确产物上都必然变红（13/13）＝恒真闸。

本测试覆盖 7 条腿：
  L0 基线：未改动副本 → 硬违规 0 条、D2 登记债务 13 条、D3 0 条
  L1 鉴别力主腿：D13 撤掉该镜状态登记 → **同一份几何**必须翻红报 D1
  L2 合法换位腿：D13 保留该镜状态登记 → 必须不报 D1（只记 D2）
  L3 同名多实例消歧腿：同场第二个同名实例被拉进该镜 → 必报 X2 重叠，
       且灰框面板@64 的行数 = 2（实例数），**不得**出现 12.33m 假偏移
  L4 歧义腿：道具不在该镜 → 覆盖成悬空 → 必须记 D3 待人工确认，**不得**判违规
  L5 跨场同名腿：撤 B-1 数据板的状态登记 → 只许 B-1/g34 变红，B-2/g40 必不受影响
  L6 PROP_ANIM 消歧腿：灰框面板@61 行数必须 = 1（旧判据给 2）、火头@62 行数 = 3
  R1 反证腿：旧判据（.bak）在同一现盘上必报 14 条且含 12.33m 假偏移，新判据必不报
  R2 反证腿：旧判据的 PROP_ANIM 行数 = 13（含 1 条错配），新判据 = 12

夹具形态要求（工厂既有负测范式）：
  夹具直接用**真盘原文逐字**改造（改 D13.json 的 `state`/`note` 里的镜号措辞、
  改 `shots` 列表），不是另写一种说法。

用法：
    python3 scripts/test_audit_D13_alignment_criteria_U02.py --project .
退出码：0 = 全部腿通过；1 = 有腿失败。
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = "audit_D13_white_model_alignment_U02.py"
AUDIT_BAK = "audit_D13_white_model_alignment_U02.py.bak_20261023"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" —— {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def run_audit(project_dir: str, script: str = AUDIT):
    """跑审计脚本，返回 (exit_code, 解析后的 JSON 或 None, stdout 原文)。"""
    proc = subprocess.run(
        [sys.executable, os.path.join(project_dir, "scripts", script),
         "--project", project_dir, "--unit", "U02", "--json"],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(proc.stdout or "")
    except json.JSONDecodeError:
        data = None
    return proc.returncode, data, proc.stdout


def run_old(project_dir: str):
    """跑旧判据（无 --json），返回 (exit_code, stdout 原文)。"""
    proc = subprocess.run(
        [sys.executable, os.path.join(project_dir, "scripts", AUDIT_BAK)],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def find_class(data, cls, gsn=None, prop=None, scene=None):
    out = []
    for f in (data or {}).get("findings", []):
        if f.get("class") != cls:
            continue
        if gsn is not None and f.get("gsn") != gsn:
            continue
        if prop is not None and f.get("prop") != prop:
            continue
        if scene is not None and f.get("scene") != scene:
            continue
        out.append(f)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.path.dirname(HERE))
    args = ap.parse_args()
    src_project = os.path.abspath(args.project)

    tmp = tempfile.mkdtemp(prefix="d13align_negtest_")
    dst = os.path.join(tmp, "双相潮主")
    os.makedirs(os.path.join(dst, "scripts"))
    os.makedirs(os.path.join(dst, "units", "U02"))
    for f in (AUDIT, AUDIT_BAK, "white_model_content_U02.py"):
        shutil.copy2(os.path.join(src_project, "scripts", f),
                     os.path.join(dst, "scripts", f))
    for f in ("D13.json", "D11.json"):
        shutil.copy2(os.path.join(src_project, "units", "U02", f),
                     os.path.join(dst, "units", "U02", f))

    d13_path = os.path.join(dst, "units", "U02", "D13.json")

    def load_d13():
        with open(d13_path, encoding="utf-8") as fh:
            return json.load(fh)

    def save_d13(doc):
        with open(d13_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)

    def get_prop(doc, scene, name, index=0):
        sc = next(s for s in doc["scenes"] if s["scene_code"] == scene)
        hits = [p for p in sc["props"] if p["name"] == name]
        return hits[index]

    base_d13 = load_d13()

    print("D13↔白模落位审计判据负测（证明判据非恒真）")
    print("=" * 68)

    # ---- L0 基线 ----
    code, data, _ = run_audit(dst)
    c = (data or {}).get("counts", {})
    check("L0 基线：现盘硬违规 0 条、D2 登记债务 13 条、D3 0 条",
          code == 0 and (data or {}).get("violations") == 0
          and c.get("D2") == 13 and c.get("D1") == 0 and c.get("D3") == 0,
          f"exit={code} violations={(data or {}).get('violations')} "
          f"D1={c.get('D1')} D2={c.get('D2')} D3={c.get('D3')}")
    check("L0b 基线：现盘不出现 12.33m 假偏移（同名多实例已消歧）",
          "12.33" not in json.dumps(data or {}, ensure_ascii=False),
          "新判据输出里搜 '12.33'")

    # ---- L1 鉴别力主腿：撤掉 D13 的该镜状态登记 → 同一份几何必须翻红 ----
    d13_l1 = copy.deepcopy(base_d13)
    p = get_prop(d13_l1, "B-1", "数据板")
    before_state = p["state"]
    p["state"] = p["state"].replace("镜34 ", "")
    p["note"] = p["note"].replace("镜34 ", "")
    save_d13(d13_l1)
    code, data, _ = run_audit(dst)
    d1 = find_class(data, "D1", gsn=34, prop="数据板", scene="B-1")
    check("L1 鉴别力主腿：撤掉 D13 该镜状态登记 → 同一份几何必须报 D1 违规",
          len(d1) == 1 and code == 1,
          f"exit={code} D1命中={len(d1)}")
    check("L1b 该腿 D1 行的偏移量与原 D2 行一致（证明只翻转判级、不改几何）",
          bool(d1) and "dx=-0.55" in d1[0]["note"] and "dy=-1.55" in d1[0]["note"],
          d1[0]["note"][:110] if d1 else "无 D1 行")
    save_d13(base_d13)

    # ---- L2 合法换位腿：状态登记在位 → 不得判违规 ----
    code, data, _ = run_audit(dst)
    d2 = find_class(data, "D2", gsn=34, prop="数据板", scene="B-1")
    d1 = find_class(data, "D1", gsn=34, prop="数据板", scene="B-1")
    check("L2 合法换位腿：D13 登记该镜状态 → 只记 D2、不判违规",
          len(d2) == 1 and len(d1) == 0 and code == 0,
          f"exit={code} D2={len(d2)} D1={len(d1)}")

    # ---- L3 同名多实例消歧腿（**现盘形态**：不动任何真盘内容）----
    # 真盘 B-10 有两个同名灰框面板（shots=[61] / shots=[64]）。
    # 旧判据把 ("B-10",64,"灰框面板") 的覆盖拿去和**两个**面板各比一次
    # ⇒ 产出 2 行（其中一行 dx=12.33 的 12 米级假偏移）。
    # 新判据按 `props[].shots` 消歧 ⇒ 只有在场的那一个实例被比对 ⇒ 1 行、无假偏移。
    code, data, _ = run_audit(dst)
    panel64_rows = [f for f in (data or {}).get("findings", [])
                    if f.get("scene") == "B-10" and f.get("gsn") == 64
                    and f.get("prop") == "灰框面板" and f.get("class", "").startswith("D")]
    check("L3 消歧腿（现盘）：灰框面板@64 只出 1 行（旧判据给 2 行）",
          len(panel64_rows) == 1,
          f"灰框面板@64 的 D 类行数={len(panel64_rows)}")
    check("L3b 消歧腿（现盘）：该行比的是 shots=[64] 那个实例的登记点 [2.4,-13.6,1.7]",
          bool(panel64_rows) and panel64_rows[0]["d13_pos"] == [2.4, -13.6, 1.7],
          str(panel64_rows[0]["d13_pos"]) if panel64_rows else "无行")
    check("L3c 消歧腿（现盘）：不存在 dx=12.33 的行",
          "12.33" not in json.dumps(data or {}, ensure_ascii=False),
          "输出里搜 '12.33'")

    # ---- L3d 构造腿①：把 shots=[61] 面板真拉进 g64，但不给它登记 g64 状态 ----
    # ⇒ 这时 12.33m 的偏移是**真的**（白模层确实把它挪了 12m，D13 未登记）
    # ⇒ 判据必须报 D1（真偏移仍能抓到），并报 X2（两实例被同一覆盖到同一点）。
    d13_l3 = copy.deepcopy(base_d13)
    p61 = get_prop(d13_l3, "B-10", "灰框面板", index=0)
    check("L3d 前置：真盘 B-10 第一个灰框面板 shots=[61]",
          p61.get("shots") == [61], f"shots={p61.get('shots')}")
    p61["shots"] = [61, 64]
    save_d13(d13_l3)
    code, data, _ = run_audit(dst)
    x2 = find_class(data, "X2", gsn=64, prop="灰框面板", scene="B-10")
    d1 = find_class(data, "D1", gsn=64, prop="灰框面板", scene="B-10")
    check("L3d 同名多实例真拉进同镜 → 必报 D1（真偏移 12m 仍被抓到）",
          len(d1) == 1 and code == 1 and "12.33" in d1[0]["note"],
          f"exit={code} D1={len(d1)}")
    check("L3e 同镜 2 个同名实例被同一覆盖 → 必报 X2 重叠风险",
          len(x2) == 1, f"X2={len(x2)}")
    save_d13(base_d13)

    # ---- L3f 构造腿②：同构造，但给它补上 g64 的逐镜状态登记 ⇒ 判级转 D2 ----
    d13_l3b = copy.deepcopy(base_d13)
    p61b = get_prop(d13_l3b, "B-10", "灰框面板", index=0)
    p61b["shots"] = [61, 64]
    p61b["state"] = p61b["state"] + "；镜64 该面板移入路口视野"
    save_d13(d13_l3b)
    code, data, _ = run_audit(dst)
    d2 = find_class(data, "D2", gsn=64, prop="灰框面板", scene="B-10")
    d1b = find_class(data, "D1", gsn=64, prop="灰框面板", scene="B-10")
    check("L3f 补上 g64 状态登记 → 判级转 D2、D1 归零",
          len(d2) == 2 and len(d1b) == 0,
          f"D2={len(d2)} D1={len(d1b)}")
    check("L3g 两行各比各的登记点（逐实例消歧，不是交叉错配）",
          {tuple(f["d13_pos"]) for f in d2} == {(-14.23, 1.41, 1.7), (2.4, -13.6, 1.7)},
          str(sorted(tuple(f["d13_pos"]) for f in d2)))
    save_d13(base_d13)

    # ---- L4 歧义腿：道具不在该镜 ⇒ 覆盖悬空 ⇒ 待人工确认，不判违规 ----
    d13_l4 = copy.deepcopy(base_d13)
    p = get_prop(d13_l4, "B-8", "钢门柱")
    check("L4 前置：真盘 B-8 钢门柱 shots=[54]", p.get("shots") == [54],
          f"shots={p.get('shots')}")
    p["shots"] = [53]          # 把钢门柱移出 g54 ⇒ ("B-8",54,"钢门柱") 覆盖悬空
    save_d13(d13_l4)
    code, data, _ = run_audit(dst)
    d3 = find_class(data, "D3", gsn=54, prop="钢门柱", scene="B-8")
    d1 = find_class(data, "D1", gsn=54, prop="钢门柱", scene="B-8")
    check("L4 歧义腿：覆盖悬空 → 记 D3 待人工确认，且不判违规",
          len(d3) == 1 and len(d1) == 0 and code == 0,
          f"exit={code} D3={len(d3)} D1={len(d1)}")
    save_d13(base_d13)

    # ---- L5 跨场同名腿 ----
    d13_l5 = copy.deepcopy(base_d13)
    p = get_prop(d13_l5, "B-1", "数据板")
    p["state"] = p["state"].replace("镜34 ", "")
    p["note"] = p["note"].replace("镜34 ", "")
    save_d13(d13_l5)
    code, data, _ = run_audit(dst)
    b1 = find_class(data, "D1", gsn=34, prop="数据板", scene="B-1")
    b2 = find_class(data, "D1", gsn=40, prop="数据板", scene="B-2")
    b2d2 = find_class(data, "D2", gsn=40, prop="数据板", scene="B-2")
    check("L5 跨场同名腿：B-1/g34 变红，B-2/g40 必不受影响",
          len(b1) == 1 and len(b2) == 0 and len(b2d2) == 1,
          f"B-1 D1={len(b1)}｜B-2 D1={len(b2)} B-2 D2={len(b2d2)}")
    save_d13(base_d13)

    # ---- L6 PROP_ANIM 消歧腿 ----
    code, data, _ = run_audit(dst)
    e61 = find_class(data, "E2", gsn=61, prop="灰框面板", scene="B-10")
    e62 = find_class(data, "E2", gsn=62, prop="火头", scene="B-10")
    check("L6 PROP_ANIM 消歧腿：灰框面板@61 行数 = 1（旧判据给 2）",
          len(e61) == 1, f"E2@61 灰框面板行数={len(e61)}")
    check("L6b PROP_ANIM 作用于该镜在场的每个同名实例：火头@62 行数 = 3",
          len(e62) == 3, f"E2@62 火头行数={len(e62)}")

    # ---- R1 反证腿：旧判据在同��现盘上必误报 ----
    old_code, old_out = run_old(dst)
    m_old = re.search(r"违规（白模层单方面挪主体）：(\d+) 条", old_out)
    old_n = int(m_old.group(1)) if m_old else -1
    old_fp = "dx=12.33" in old_out
    new_fp = "12.33" in json.dumps(data or {}, ensure_ascii=False)
    check("R1 反证腿：旧判据在现盘上误报 12.33m 假偏移，新判据不报",
          old_fp and not new_fp,
          f"旧判据违规数={old_n} 旧判据含12.33m={old_fp} 新判据含12.33m={new_fp}")
    check("R1b 反证腿：旧判据报 14 条违规，新判据硬违规 0 条",
          old_n == 14 and (data or {}).get("violations") == 0,
          f"旧={old_n} 新={(data or {}).get('violations')}")

    # ---- R2 反证腿：旧判据的 PROP_ANIM 行数 ----
    old_e = len(re.findall(r"^A\s+B-\d+\s+灰框面板@gsn61|^A\s+B-\d+\s+火头@gsn62",
                            old_out, re.M))
    new_e = len(e61) + len(e62)
    check("R2 反证腿：旧判据 PROP_ANIM 错配多 1 行（灰框面板@61 给 2 行），新判据不多给",
          old_e == 5 and new_e == 4,
          f"旧灰框面板@61+火头@62 行数={old_e} 新={new_e}")

    shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 68)
    if failures:
        print(f"负测失败 {len(failures)} 条：{failures}")
        return 1
    print("负测全部通过 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
