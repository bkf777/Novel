#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q64／Q68 守卫有效性「四件套 ＋ 内容不可 force」—— **沙箱隔离**自测（分镜导演岗）

规则来源：企划合规 07:2x 登记 **Q68**「**守卫存在 ≠ 守卫有效**」，守卫验收必须实跑：
    A 伪造更高版本   → exit≠0，且**磁盘未被改写**
    B ＋ `--force`   → 放行（exit 0）
    C 正常升版       → 放行（exit 0）
    D 幂等           → exit 0，且产物与盘上**字节完全一致**
    E 内容篡改       → 拒绝；且**带 `--force` 仍拒绝**（内容漂移不可 force，否则等于允许
                       静默吞掉他人手改）

⚠️ **自测只在沙箱副本进行，严禁在真实交付物上伪造版本**（Q68 明文）。
   沙箱 = 临时目录里的 `02_项目/双相潮主`（units/U02 ＋ shared ＋ scripts ＋ project.json）
   ＋ `03_规格/rules.json`；构建脚本的 ROOT 由 `__file__` 推导，故副本脚本**天然只读写
   副本内交付物**，真盘全程零写入（本脚本收尾会比对真盘 SHA256 前后一致作为证据）。

⚠️ **沙箱脚本报错 ≠ 守卫拒绝**（Q68 明文）：stderr 出现 `Traceback` ⇒ 是脚本自身出错，
   该腿判为「环境/脚本故障」，**不得**记作「守卫拒绝」。

用法：python3 scripts/selftest_Q64_Q68_sandbox.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_SRC = os.path.abspath(os.path.join(REAL_ROOT, "..", "..", "03_规格", "rules.json"))

TARGETS = [
    {
        "name": "D11 U02",
        "script": "build_D11_U02.py",
        "out": "units/U02/D11.json",
        "tamper": ("episodes.0.shots.0.visual_facts", "append", "【沙箱篡改】"),
    },
    {
        "name": "D16 U02",
        "script": "build_D16_U02.py",
        "out": "units/U02/D16.json",
        "tamper": ("episodes.0.subtitle_style.lines.0.text", "set", "【沙箱篡改】"),
    },
]

# ── 版本声明**动态推导**（不再硬编码）────────────────────────────────────────
#   ⚠️ 教训（2026-10-23 实踩）：本自测器原先把 `VERSION = "v1.4"`、
#      `DECLARED_VERSION_CHANGE = ("v1.3", "v1.4")` 等**硬编码**成期望值 ——
#      交付物每升一次版，自测器就断一次（2026-10-23 D16 v1.5 落盘即触发）。
#      硬编码的期望值 = 必然会腐烂的断言。故改为**从脚本源码现读现推**：
#      脚本当前版本 → 下一版本 → 同步平移「声明的版本变更」元组。
#   两种声明写法都要支持：
#      形状 A：D16 —— DECLARED_VERSION_CHANGE = ("vA", "vB")
#      形状 B：D11 —— (("version",), "vA", "vB")
PAT_VER_CONST = re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.M)
PAT_DECL_A = re.compile(r'(DECLARED_VERSION_CHANGE\s*=\s*\(\s*)"(v[^"]+)"\s*,\s*"(v[^"]+)"(\s*\))')
PAT_DECL_B = re.compile(r'(\(\("version",\)\s*,\s*)"(v[^"]+)"\s*,\s*"(v[^"]+)"(\s*\))')


def script_version(src):
    """从构建脚本源码读出当前 VERSION 常量的值。"""
    m = PAT_VER_CONST.search(src)
    if not m:
        raise AssertionError("构建脚本里找不到 VERSION 常量")
    return m.group(1)


def next_ver(v):
    """vX.Y → 下一个次版本 vX.(Y+1)（自测腿 C 用「正常升版」语义）。"""
    m = re.match(r"^v(\d+)\.(\d+)$", str(v))
    if not m:
        raise AssertionError(f"版本号不可解析：{v}")
    return f"v{m.group(1)}.{int(m.group(2)) + 1}"


def shift_decl(src, cur, nxt):
    """把「声明的版本变更」由 (prev, cur) 平移为 (cur, nxt)。

    只在**元组末位等于脚本当前版本**时才动手 —— 命中不到就抛错，
    绝不静默跑一个没改到东西的「升版」腿（那等于把假通过记成真通过）。
    """
    for pat in (PAT_DECL_A, PAT_DECL_B):
        for m in pat.finditer(src):
            if m.group(3) == cur:
                return src[:m.start()] + m.group(1) + f'"{cur}", "{nxt}"' + m.group(4) + src[m.end():]
    raise AssertionError(f"声明的版本变更元组末位不是 {cur} —— 未命中，拒绝伪造升版腿")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def build_sandbox():
    sb = tempfile.mkdtemp(prefix="mavis_guard_sandbox_")
    proj = os.path.join(sb, "02_项目", "双相潮主")
    os.makedirs(os.path.join(sb, "03_规格"), exist_ok=True)
    shutil.copy2(RULES_SRC, os.path.join(sb, "03_规格", "rules.json"))
    os.makedirs(os.path.join(proj, "scripts"), exist_ok=True)
    shutil.copytree(os.path.join(REAL_ROOT, "units", "U02"), os.path.join(proj, "units", "U02"))
    shutil.copytree(os.path.join(REAL_ROOT, "shared"), os.path.join(proj, "shared"))
    shutil.copy2(os.path.join(REAL_ROOT, "project.json"), os.path.join(proj, "project.json"))
    for t in TARGETS:
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", t["script"]),
                     os.path.join(proj, "scripts", t["script"]))
    return sb, proj


def run(proj, script, args=()):
    p = subprocess.run([sys.executable, os.path.join(proj, "scripts", script), *args],
                       capture_output=True, text=True, cwd=proj)
    tb = "Traceback (most recent call last)" in (p.stderr or "")
    return p.returncode, (p.stdout or "") + (p.stderr or ""), tb


def set_path(doc, dotted, mode, val):
    keys = dotted.split(".")
    node = doc
    for k in keys[:-1]:
        node = node[int(k)] if k.isdigit() else node[k]
    last = keys[-1]
    if mode == "append":
        node[last] = node[last] + val
    else:
        node[last] = val
    return doc


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def main():
    real_hash_before = {t["name"]: sha(os.path.join(REAL_ROOT, t["out"])) for t in TARGETS}
    sb, proj = build_sandbox()
    print(f"🧪 沙箱：{sb}")
    print(f"   （真盘交付物只读；构建脚本 ROOT 由 __file__ 推导 → 只读写副本）\n")

    results = []   # (target, leg, 期望, 实测, 判定)

    for t in TARGETS:
        out_abs = os.path.join(proj, t["out"])
        script_abs = os.path.join(proj, "scripts", t["script"])
        pristine = os.path.join(sb, "_pristine_" + os.path.basename(t["out"]))
        shutil.copy2(out_abs, pristine)

        def reset():
            shutil.copy2(pristine, out_abs)

        # ── D 幂等：exit 0 且产物与盘上字节完全一致 ──
        reset()
        before = sha(out_abs)
        rc, out, tb = run(proj, t["script"])
        ok = (rc == 0) and (sha(out_abs) == before) and not tb
        results.append((t["name"], "D 幂等", "exit 0 且字节一致", f"exit {rc}｜字节{'一致' if sha(out_abs)==before else '不一致'}", ok))

        # ── A 伪造更高版本：exit≠0 且磁盘未被改写 ──
        reset()
        doc = json.load(open(out_abs, encoding="utf-8"))
        doc["version"] = "v9.9"
        write_json(out_abs, doc)
        forged = sha(out_abs)
        rc, out, tb = run(proj, t["script"])
        unchanged = sha(out_abs) == forged
        ok = (rc != 0) and unchanged and not tb
        results.append((t["name"], "A 伪造高版本", "exit≠0 且磁盘未改写",
                        f"exit {rc}｜磁盘{'未改写' if unchanged else '被改写'}", ok))

        # ── B ＋--force：放行 ──
        reset()
        doc = json.load(open(out_abs, encoding="utf-8"))
        doc["version"] = "v9.9"
        write_json(out_abs, doc)
        rc, out, tb = run(proj, t["script"], ["--force"])
        ver = json.load(open(out_abs, encoding="utf-8")).get("version")
        ok = (rc == 0) and not tb and ver != "v9.9"
        results.append((t["name"], "B --force 逃生口", "exit 0 且放行落盘",
                        f"exit {rc}｜落盘 version={ver}", ok))

        # ── C 正常升版：放行（版本声明**动态推导**，不硬编码）──
        reset()
        src = open(script_abs, encoding="utf-8").read()
        cur = script_version(src)
        nxt = next_ver(cur)
        src = shift_decl(src, cur, nxt)
        old_const = f'VERSION = "{cur}"'
        if old_const not in src:
            raise AssertionError(f"版本常量未命中：{old_const}")
        src = src.replace(old_const, f'VERSION = "{nxt}"')
        open(script_abs, "w", encoding="utf-8").write(src)
        rc, out, tb = run(proj, t["script"])
        ver = json.load(open(out_abs, encoding="utf-8")).get("version")
        ok = (rc == 0) and not tb and ver == nxt
        results.append((t["name"], "C 正常升版", f"exit 0 且落盘 {nxt}",
                        f"exit {rc}｜落盘 version={ver}", ok))
        # 还原脚本副本（下一腿从原始脚本开始）
        shutil.copy2(os.path.join(REAL_ROOT, "scripts", t["script"]), script_abs)

        # ── E 内容篡改：拒绝；带 --force 仍拒绝；磁盘保持篡改态 ──
        reset()
        doc = json.load(open(out_abs, encoding="utf-8"))
        dotted, mode, val = t["tamper"]
        set_path(doc, dotted, mode, val)
        write_json(out_abs, doc)
        tampered = sha(out_abs)
        rc1, _, tb1 = run(proj, t["script"])
        rc2, _, tb2 = run(proj, t["script"], ["--force"])
        still = sha(out_abs) == tampered
        ok = (rc1 != 0) and (rc2 != 0) and still and not tb1 and not tb2
        results.append((t["name"], "E 内容篡改不可 force", "两腿均 exit≠0 且磁盘保持篡改态",
                        f"exit {rc1} / --force exit {rc2}｜磁盘{'保持篡改态' if still else '被覆盖'}", ok))

    print("════════ 守卫有效性自测（沙箱）════════")
    print(f"{'目标':<10}{'腿':<22}{'期望':<30}{'实测':<34}{'判定'}")
    print("─" * 108)
    n_pass = 0
    for name, leg, exp, got, ok in results:
        n_pass += 1 if ok else 0
        print(f"{name:<10}{leg:<22}{exp:<30}{got:<34}{'✅' if ok else '❌'}")
    print("─" * 108)
    print(f"受检 {len(results)} 条（{len(TARGETS)} 目标 × 5 腿）｜通过 {n_pass}｜失败 {len(results)-n_pass}")

    # 真盘零写入证据
    print("\n真盘交付物 SHA256 前缀（前后比对）：")
    zero = True
    for t in TARGETS:
        h = sha(os.path.join(REAL_ROOT, t["out"]))
        same = (h == real_hash_before[t["name"]])
        zero = zero and same
        print(f"  {t['name']:<10} {h}  {'✅ 与自测前一致（真盘零写入）' if same else '❌ 真盘被改动！'}")
    shutil.rmtree(sb, ignore_errors=True)
    print(f"\n沙箱已清理：{sb}")
    sys.exit(0 if (n_pass == len(results) and zero) else 1)


if __name__ == "__main__":
    main()
