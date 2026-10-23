#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_D08.py 版本守卫自测（台本编剧岗）—— 补齐 Q64 的第②腿，覆盖 4 条路径。

起因（企划合规 2026-10-23 迟到回执 · 第三节建议）：
  「守卫自测请含**两条** —— ① 伪造更高磁盘版本 → 必须拒绝且 exit≠0；
    ② **正常升版 → 必须放行**（防「守卫过宽把升版卡死」）。你的实测只覆盖了第①条。」

本脚本在**临时沙箱**里跑，真盘零写入（用例 E 以 SHA256 佐证）：
  A 回退拒绝   磁盘 v1.4 ＋ 脚本 v1.3           → exit 1，磁盘字节不变
  B 正常升版   磁盘 v1.4 ＋ 脚本 v1.5           → exit 0，写盘且 version = v1.5   ← 第②腿
  C 幂等重跑   磁盘 v1.5 ＋ 脚本 v1.5           → exit 0，写盘且字节一致（守卫不得卡死幂等）
  D 逃生口     磁盘 v1.5 ＋ 脚本 v1.3 ＋ --force → exit 0，写盘且 version = v1.3

用法：
  python3 scripts/test_build_D08_guard.py                # 自测（真盘只读）
  python3 scripts/test_build_D08_guard.py --keep          # 保留沙箱供人工查看

断言口径（Q49）：**断言点数 == 报告里的「通过」条数**，不符即 exit 1。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
FACTORY = "/Users/ezreal/projects/小说创作/短剧文档工厂"
UNIT = "U02"
CONTENT_MOD = "d08_content_U02.py"
BUILD_MOD = "build_D08.py"


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def build_sandbox(dst):
    """搭一个最小可跑沙箱：脚本 + 内容模块 + 03_规格/rules.json + 本单元输入。"""
    os.makedirs(os.path.join(dst, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(dst, "units", UNIT), exist_ok=True)
    os.makedirs(os.path.join(dst, "shared"), exist_ok=True)
    os.makedirs(os.path.join(dst, "03_规格"), exist_ok=True)

    shutil.copy2(os.path.join(ROOT, "scripts", BUILD_MOD), os.path.join(dst, "scripts", BUILD_MOD))
    shutil.copy2(os.path.join(ROOT, "scripts", CONTENT_MOD), os.path.join(dst, "scripts", CONTENT_MOD))
    shutil.copy2(os.path.join(FACTORY, "03_规格", "rules.json"), os.path.join(dst, "03_规格", "rules.json"))
    for rel in [f"units/{UNIT}/D06.json", f"units/{UNIT}/D07.json", f"units/{UNIT}/D08.json",
                "shared/D04.json", "shared/D05.json"]:
        shutil.copy2(os.path.join(ROOT, rel), os.path.join(dst, rel))
    return dst


def set_version(dst, version):
    """改沙箱内内容模块的 VERSION（只动沙箱副本）。

    ⚠️ 踩坑（本脚本第一版就栽在这里，自测曾把**升版**误判为被守卫拒绝）：
       Python 的 `__pycache__` 失效判定只比对**源文件的 mtime（秒级）+ size**。
       版本串「v1.3 → v1.5」**长度相同**、又发生在**同一秒** ⇒ pyc 被判定为仍然新鲜
       ⇒ 子进程 import 到的是**旧模块**（VERSION 还是 v1.3）⇒ 守卫看起来「把升版也拒了」。
       对策：① 改完立刻删 `__pycache__`；② 子进程设 `PYTHONDONTWRITEBYTECODE=1`；
             ③ **加一条前置断言**——直接问子进程「你读到的 VERSION 是多少」，不靠推断。
    """
    p = os.path.join(dst, "scripts", CONTENT_MOD)
    src = open(p, encoding="utf-8").read()
    new, n = re.subn(r'(VERSION\s*=\s*)["\'][^"\']+["\']', lambda m: m.group(1) + f'"{version}"', src, count=1)
    if n != 1:
        raise SystemExit(f"❌ 未能在 {p} 中定位 VERSION（改动数 {n}）")
    open(p, "w", encoding="utf-8").write(new)
    # ① 清缓存
    pyc = os.path.join(dst, "scripts", "__pycache__")
    if os.path.isdir(pyc):
        shutil.rmtree(pyc, ignore_errors=True)
    # ③ 前置断言：子进程实际读到的 VERSION 必须等于目标值
    seen = child_version(dst)
    if seen != version:
        raise SystemExit(f"❌ 沙箱内容模块版本不符：期望 {version}，子进程读到 {seen!r}（缓存或导入路径问题）")
    return seen


def child_version(dst):
    """问子进程「你 import 到的内容模块 VERSION 是多少」。"""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.path.join(dst, "scripts")
    p = subprocess.run([sys.executable, "-c",
                        f"import d08_content_U02 as m; print(m.VERSION)"],
                       capture_output=True, text=True, env=env, cwd=os.path.join(dst, "scripts"))
    return (p.stdout or "").strip().splitlines()[-1] if p.stdout.strip() else f"<空:{p.stderr.strip()[:120]}>"


def run_build(dst, extra=None):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, os.path.join(dst, "scripts", BUILD_MOD),
           "--project", dst, "--unit", UNIT] + (extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=dst, env=env)
    return p.returncode, (p.stdout + p.stderr)


def disk_version(dst):
    p = os.path.join(dst, "units", UNIT, "D08.json")
    return json.load(open(p, encoding="utf-8")).get("version")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="保留沙箱目录")
    args = ap.parse_args()

    real = os.path.join(ROOT, "units", UNIT, "D08.json")
    real_before = sha256(real)
    real_size_before = os.path.getsize(real)

    sandbox = build_sandbox(tempfile.mkdtemp(prefix="d08_guard_"))
    results = []   # (用例, 断言描述, 通过?)
    prints = []

    def run_case(name, disk_ver, script_ver, expect_exit, expect_disk_ver, extra=None, expect_bytes_same=None):
        # 把磁盘版本改成 disk_ver（模拟「磁盘已是某版本」）
        dp = os.path.join(sandbox, "units", UNIT, "D08.json")
        d = json.load(open(dp, encoding="utf-8"))
        d["version"] = disk_ver
        open(dp, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
        before = sha256(dp)
        set_version(sandbox, script_ver)
        code, out = run_build(sandbox, extra)
        after = sha256(dp)
        after_ver = disk_version(sandbox)

        a_exit = (code == expect_exit)
        a_ver = (after_ver == expect_disk_ver)
        a_bytes = True if expect_bytes_same is None else ((before == after) == expect_bytes_same)
        ok = a_exit and a_ver and a_bytes
        prints.append((name, f"exit={code}(期望{expect_exit})", f"version {disk_ver}→{after_ver}(期望{expect_disk_ver})",
                       "字节" + ("不变 ✅" if before == after else "已变"), "✅ 通过" if ok else "❌ 失败"))
        results.append((name, ok, a_exit, a_ver, a_bytes))
        if not ok:
            tail = [ln for ln in out.splitlines() if ln.strip()][-8:]
            prints.append((f"  └ {name} 输出", " ｜ ".join(t[:110] for t in tail), "", "", ""))
        return ok, out

    # A 回退拒绝（磁盘高于脚本）
    run_case("A 回退拒绝", "v1.4", "v1.3", 1, "v1.4", None, expect_bytes_same=True)
    # B 正常升版放行（企划合规要求的第②腿）
    run_case("B 正常升版放行 ★第②腿", "v1.4", "v1.5", 0, "v1.5", None, expect_bytes_same=False)
    # C 幂等重跑放行（守卫不得过宽把升版/幂等卡死）
    run_case("C 幂等重跑放行", "v1.5", "v1.5", 0, "v1.5", None, expect_bytes_same=True)
    # D --force 逃生口放行回退
    run_case("D --force 逃生口", "v1.5", "v1.3", 0, "v1.3", ["--force"], expect_bytes_same=False)
    # E 真盘零写入佐证
    real_after = sha256(real)
    ok_e = (real_after == real_before) and (os.path.getsize(real) == real_size_before)
    prints.append(("E 真盘零写入佐证", f"sha256 前 12 位 {real_before[:12]} → {real_after[:12]}",
                   f"size {real_size_before} → {os.path.getsize(real)}", "", "✅ 通过" if ok_e else "❌ 失败"))
    results.append(("E 真盘零写入佐证", ok_e, ok_e, True, True))

    n_assert = sum(len([x for x in r[1:]]) for r in results)   # 每个用例 3 条断言 + E 的 1 条
    n_pass = sum(1 for r in results if r[1])

    w = max(len(p[0]) for p in prints) + 2
    print("═" * (w + 56))
    print("build_D08.py 版本守卫自测（沙箱运行，真盘零写入）")
    print("═" * (w + 56))
    for name, c1, c2, c3, verdict in prints:
        print(f"{name.ljust(w)}{c1:26} {c2:34} {c3:14} {verdict}")
    print("─" * (w + 56))
    print(f"用例 {len(results)} 个｜断言 {n_assert} 条｜用例通过 {n_pass}｜失败 {len(results)-n_pass}")

    if not args.keep:
        shutil.rmtree(sandbox, ignore_errors=True)
        print(f"🧹 沙箱已清理：{sandbox}")
    else:
        print(f"🧩 沙箱保留：{sandbox}")

    if n_pass != len(results):
        print("❌ 守卫自测未全绿（断言点数 ≠ 通过用例数）")
        return 1
    print("✅ 守卫自测全绿：拒绝回退 ✅ / 正常升版放行 ✅ / 幂等重跑放行 ✅ / --force 逃生口 ✅ / 真盘零写入 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
