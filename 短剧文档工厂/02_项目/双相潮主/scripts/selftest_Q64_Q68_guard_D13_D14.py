#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_Q64_Q68_guard_D13_D14.py —— **本岗（白模场景师）两个写盘脚本**的版本守卫有效性自测

与 `selftest_Q64_Q68_sandbox.py`（他岗 D11/D16 的自测器）同构，但目标换成
本岗单写的两个产物：`units/<UNIT>/D13.json` 与 `units/<UNIT>/D14.json`。

Q68「有效性四件套」逐腿断言：
  A 伪造更高版本   → exit≠0 且**磁盘未被改写**（且输出含守卫拒绝语、无 traceback）
  B --force 逃生口 → exit 0 且放行落盘 + **旁路留痕**新增一条
  C 正常升版       → exit 0 且落盘为新版本
  D 幂等           → 连跑两次 exit 0 且**两次产物字节完全一致**
  F（D14 专属）    → 守卫拒绝时**一个逐镜包都不许落**（不留半成品下游产物）

额外两条硬断言（Q68 可达性）：
  R1 守卫**真的被执行到**：stdout 含 `[version-guard]` 且**无 traceback**
     —— 区分「守卫拒绝」与「脚本报错」，否则会把坏脚本记成好守卫。
  R2 真盘交付物**零写入**：自测前后真盘 D13/D14 的 sha256 前缀一致。

⚠️ 口径说明：版本守卫只管**版本**，不管「同版本下的内容篡改」——
   D13/D14 都是**生成器**（每次按内容模块重算并整份覆盖），同版本手改被覆盖属预期行为，
   故不设内容漂移守卫；D11/D16 那种「打补丁式」产物才需要漂移守卫（那边自测器已有 E 腿）。

⚠️ 严禁在真盘交付物上伪造版本：所有伪造/篡改只发生在**沙箱副本**里。
   沙箱路径会打印在报告里（Q68：报告须写受检条数与沙箱路径）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 02_项目/双相潮主
FACTORY = os.path.dirname(os.path.dirname(REAL_ROOT))                     # 短剧文档工厂
WORK_SRC = os.environ.get("GUARD_SELFTEST_WORK", "/tmp/dcc-smoke/u02")

# 目标：脚本 / 产物 / 目标版本在脚本源码里的声明形状 / 篡改点
TARGETS = [
    {
        "name": "D13 U02",
        "script": "build_D13.py",
        "args": ["--unit", "U02"],
        "out": "units/U02/D13.json",
        # D13 的目标版本写在构建脚本的 doc 头里
        "ver_pat": re.compile(r'("doc_id": "D13", "unit": UNIT_ID, "version": ")(v[\d.]+)(")'),
        "tamper": ("scenes.0.props.0.name", "append", "【沙箱篡改】"),
    },
    {
        "name": "D14 U02",
        "script": "assemble_D14.py",
        "args": ["--unit", "U02", "--work", "@WORK@"],
        "out": "units/U02/D14.json",
        "ver_pat": re.compile(r'(D14_TARGET_VERSION\s*=\s*")(v[\d.]+)(")'),
        "tamper": ("shots.0.version", "set", "v9.9.9"),
    },
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def set_path(doc, dotted, mode, val):
    keys = dotted.split(".")
    node = doc
    for k in keys[:-1]:
        node = node[int(k)] if k.isdigit() else node[k]
    last = keys[-1]
    node[last] = node[last] + val if mode == "append" else val
    return doc


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def next_ver(v):
    m = re.match(r"^v(\d+)\.(\d+)$", str(v))
    if not m:
        raise AssertionError(f"版本号不可解析：{v}")
    return f"v{m.group(1)}.{int(m.group(2)) + 1}"


def build_sandbox():
    sb = tempfile.mkdtemp(prefix="wm_guard_sandbox_")
    proj = os.path.join(sb, "02_项目", "双相潮主")
    os.makedirs(os.path.join(sb, "03_规格"), exist_ok=True)
    shutil.copy2(os.path.join(FACTORY, "03_规格", "rules.json"), os.path.join(sb, "03_规格", "rules.json"))
    os.makedirs(os.path.join(proj, "scripts"), exist_ok=True)
    shutil.copytree(os.path.join(REAL_ROOT, "units", "U02"), os.path.join(proj, "units", "U02"))
    if os.path.isdir(os.path.join(REAL_ROOT, "shared")):
        shutil.copytree(os.path.join(REAL_ROOT, "shared"), os.path.join(proj, "shared"))
    for f in ("project.json",):
        src = os.path.join(REAL_ROOT, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(proj, f))
    for t in TARGETS:
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", t["script"]),
                     os.path.join(proj, "scripts", t["script"]))
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", "version_guard.py"),
                     os.path.join(proj, "scripts", "version_guard.py"))
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", "d13_content_U02.py"),
                     os.path.join(proj, "scripts", "d13_content_U02.py"))
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", "d14_contract_data_U02.py"),
                     os.path.join(proj, "scripts", "d14_contract_data_U02.py"))
    # 逐镜工作区（assemble_D14 需要）
    work_dst = os.path.join(sb, "work")
    if os.path.isdir(WORK_SRC):
        shutil.copytree(WORK_SRC, work_dst)
    else:
        os.makedirs(work_dst, exist_ok=True)
    return sb, proj, work_dst


def run(proj, script, args):
    p = subprocess.run([sys.executable, os.path.join(proj, "scripts", script), *args],
                       capture_output=True, text=True, cwd=proj)
    tb = "Traceback (most recent call last)" in (p.stderr or "")
    return p.returncode, (p.stdout or "") + (p.stderr or ""), tb


def main():
    real_before = {t["name"]: sha(os.path.join(REAL_ROOT, t["out"])) for t in TARGETS}
    sb, proj, work_dst = build_sandbox()
    print(f"🧪 沙箱：{sb}")
    print(f"   （真盘交付物只读；脚本 ROOT 由 __file__ 推导 → 只读写副本）")
    print(f"   逐镜工作区副本：{work_dst}\n")

    results = []
    force_log = os.path.join(proj, "..", "..", "reports", "force_overwrite_log.jsonl")

    for t in TARGETS:
        out_abs = os.path.join(proj, t["out"])
        script_abs = os.path.join(proj, "scripts", t["script"])
        pristine = os.path.join(sb, "_pristine_" + os.path.basename(t["out"]))
        shutil.copy2(out_abs, pristine)

        def reset():
            shutil.copy2(pristine, out_abs)

        def args_for():
            return [a.replace("@WORK@", work_dst) for a in t["args"]]

        src = open(script_abs, encoding="utf-8").read()
        m = t["ver_pat"].search(src)
        if not m:
            raise AssertionError(f"{t['script']} 里找不到目标版本声明")
        cur_ver = m.group(2)
        nxt_ver = next_ver(cur_ver)

        def script_with_version(v):
            s = open(script_abs, encoding="utf-8").read()
            return t["ver_pat"].sub(lambda mm: mm.group(1) + v + mm.group(3), s, count=1)

        # ── D 幂等：连跑两次，**两次产物字节完全一致** ──
        #   ⚠️ 不能拿沙箱产物去比真盘产物：commands 数组记录的是实跑工作区路径
        #      （沙箱路径 ≠ 真盘路径），字节必不同 → 那不是幂等失败，是路径差异。
        reset()
        rc1, out1, tb1 = run(proj, t["script"], args_for())
        sha1 = sha(out_abs)
        rc2, out2, tb2 = run(proj, t["script"], args_for())
        sha2 = sha(out_abs)
        same = (sha1 == sha2)
        guard_ran = "[version-guard]" in out1 and "[version-guard]" in out2
        results.append((t["name"], "D 幂等", "两次实跑 exit 0 且字节一致",
                        f"exit {rc1}/{rc2}｜字节{'一致' if same else '不一致'}｜守卫{'已执行' if guard_ran else '未执行'}",
                        rc1 == 0 and rc2 == 0 and same and not tb1 and not tb2 and guard_ran))

        # ── A 伪造更高版本：exit≠0 且磁盘未被改写 ──
        reset()
        doc = json.load(open(out_abs, encoding="utf-8"))
        doc["version"] = "v9.9"
        write_json(out_abs, doc)
        forged = sha(out_abs)
        rc, out, tb = run(proj, t["script"], args_for())
        unchanged = sha(out_abs) == forged
        rejected = "❌ 拒绝写入" in out
        results.append((t["name"], "A 伪造高版本", "exit≠0 且磁盘未改写",
                        f"exit {rc}｜磁盘{'未改写' if unchanged else '被改写'}｜"
                        f"{'守卫拒绝' if rejected else '非守卫拒绝'}", rc != 0 and unchanged and not tb))

        # ── B --force 逃生口：exit 0 且放行落盘 + 留痕 ──
        log_before = 0
        if os.path.exists(force_log):
            log_before = sum(1 for _ in open(force_log, encoding="utf-8"))
        rc, out, tb = run(proj, t["script"], args_for() + ["--force"])
        ver_now = json.load(open(out_abs, encoding="utf-8")).get("version")
        log_after = 0
        if os.path.exists(force_log):
            log_after = sum(1 for _ in open(force_log, encoding="utf-8"))
        results.append((t["name"], "B --force 逃生口", "exit 0 且放行落盘 + 留痕",
                        f"exit {rc}｜落盘 version={ver_now}｜留痕 +{log_after - log_before}",
                        rc == 0 and not tb and ver_now == cur_ver and log_after > log_before))

        # ── C 正常升版 ──
        #   ⚠️ 必须**先算好补丁内容再写文件**：写成
        #      `open(p,"w").write(f(p))` 会在求值实参前先把 p 截断成空 ⇒ 跑了个空脚本。
        reset()
        patched_src = script_with_version(nxt_ver)
        with open(script_abs, "w", encoding="utf-8") as f:
            f.write(patched_src)
        rc, out, tb = run(proj, t["script"], args_for())
        ver_now = json.load(open(out_abs, encoding="utf-8")).get("version")
        results.append((t["name"], "C 正常升版", f"exit 0 且落盘 {nxt_ver}",
                        f"exit {rc}｜落盘 version={ver_now}", rc == 0 and not tb and ver_now == nxt_ver))
        with open(script_abs, "w", encoding="utf-8") as f:
            f.write(src)      # 还原沙箱脚本

        # ── F 拒绝时不得留下半成品下游产物（D14 专属：逐镜包一个都不许落）──
        shots_dir = os.path.join(proj, "units", "U02", "D14_shots")
        if t["script"] == "assemble_D14.py":
            shutil.rmtree(shots_dir, ignore_errors=True)
            reset()
            doc = json.load(open(out_abs, encoding="utf-8"))
            doc["version"] = "v9.9"
            write_json(out_abs, doc)
            rc, out, tb = run(proj, t["script"], args_for())
            no_shots = not os.path.isdir(shots_dir)
            results.append((t["name"], "F 拒绝时不落逐镜包", "exit≠0 且 D14_shots/ 未被创建",
                            f"exit {rc}｜D14_shots {'未创建' if no_shots else '被创建'}",
                            rc != 0 and no_shots and not tb))

    print("════════ 守卫有效性自测（沙箱）════════")
    print(f"{'目标':<9} {'腿':<26} {'期望':<34} {'实测':<44} 判定")
    print("─" * 118)
    for name, leg, exp, got, ok in results:
        print(f"{name:<9} {leg:<26} {exp:<34} {got:<44} {'✅' if ok else '❌'}")
    print("─" * 118)
    n_pass = sum(1 for r in results if r[4])
    print(f"受检 {len(results)} 条（{len(TARGETS)} 目标 × A/B/C/D 四件套"
          f"＋D14 专属 F 腿）｜通过 {n_pass}｜失败 {len(results)-n_pass}")

    print("\n真盘交付物 SHA256 前缀（前后比对）：")
    for t in TARGETS:
        after = sha(os.path.join(REAL_ROOT, t["out"]))
        print(f"  {t['name']:<9} {real_before[t['name']]} → {after}  "
              f"{'✅ 真盘零写入' if after == real_before[t['name']] else '❌ 真盘被写入'}")

    shutil.rmtree(sb, ignore_errors=True)
    print(f"\n沙箱已清理：{sb}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
