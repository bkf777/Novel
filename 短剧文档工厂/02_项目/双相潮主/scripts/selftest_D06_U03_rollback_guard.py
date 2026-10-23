#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
selftest_D06_U03_rollback_guard.py —— 故事架构：**A17 反静默回退守卫的负测（证明其非恒真）**

要证明的事（2026-10-23 13:4x 实锤的病灶）：
  生成器 `build_D06_D07_U03.py` 曾落后于现盘（现盘 D06 有 8 集的 hook_type／hook_type_reason，
  脚本内命中 0）⇒ **重跑生成器 = 静默抹掉这 8 集的 hook 字段**。
  A17 守卫的口径：**现盘若含生成器产不出的字段 ⇒ 拒绝写盘，先回并内容源**。

测法（全部在沙箱，真盘零写入）：
  腿1 正测：沙箱现盘＝生成器产物 ⇒ 生成器应 rc=0 且打印 A17 ✓（守卫不误伤正常路径）。
  腿2 **负测**：向沙箱 `units/U03/D06.json` 的 ep017 注入一个生成器产不出的字段
        （`__injected_probe__`）⇒ 生成器应 **rc≠0** 且输出命中 `A17`，且
        **沙箱该文件字节零变化**（拒绝写盘，不是先写了再报错）。
  腿3 真盘零写入：全程比对真盘 `units/U03/D06.json` / `D07.json` 的 size + sha256 前后全等。

退出码：0 = 三腿全过；1 = 失败（并打印实况）。
用法：python3 scripts/selftest_D06_U03_rollback_guard.py --project 02_项目/双相潮主
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

GEN = "scripts/build_D06_D07_U03.py"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    gen = os.path.join(root, GEN)
    if not os.path.isfile(gen):
        sys.exit(f"[ABORT] 找不到生成器 {gen}")

    real = {f: os.path.join(root, "units", "U03", f) for f in ("D06.json", "D07.json")}
    before = {f: (os.path.getsize(p), sha(p)) for f, p in real.items()}

    sbx = os.path.join("/tmp", f"sxr_a17_{os.getpid()}")
    shutil.rmtree(sbx, ignore_errors=True)
    os.makedirs(os.path.join(sbx, "02_项目", "双相潮主"), exist_ok=True)
    os.makedirs(os.path.join(sbx, "03_规格"), exist_ok=True)
    subprocess.run(["rsync", "-a", "--exclude", "reports", "--exclude", "preview", "--exclude",
                    "render", "--exclude", "D14_shots", root + "/",
                    os.path.join(sbx, "02_项目", "双相潮主") + "/"], check=True)
    factory = os.path.abspath(os.path.join(root, "..", ".."))
    shutil.copy2(os.path.join(factory, "03_规格", "rules.json"),
                 os.path.join(sbx, "03_规格", "rules.json"))
    sbx_root = os.path.join(sbx, "02_项目", "双相潮主")
    sbx_d06 = os.path.join(sbx_root, "units", "U03", "D06.json")

    ok = True

    # ── 腿1 正测 ───────────────────────────────────────────────
    r = subprocess.run([sys.executable, gen, "--project", sbx_root, "--force"],
                       capture_output=True, text=True)
    a17_ok = "A17" in r.stdout
    print(f"腿1 正测：rc={r.returncode}｜A17 命中={a17_ok}")
    if r.returncode != 0 or not a17_ok:
        ok = False
        print(r.stdout[-800:]); print(r.stderr[-400:])
    else:
        for line in r.stdout.splitlines():
            if "A17" in line:
                print("   ", line.strip())

    # ── 腿2 负测（注入生成器产不出的字段）───────────────────────
    pre_size, pre_sha = os.path.getsize(sbx_d06), sha(sbx_d06)
    d = json.load(open(sbx_d06, encoding="utf-8"))
    d["episodes"][0]["__injected_probe__"] = "negative-test-probe"
    with open(sbx_d06, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    post_size, post_sha = os.path.getsize(sbx_d06), sha(sbx_d06)
    r2 = subprocess.run([sys.executable, gen, "--project", sbx_root, "--force"],
                        capture_output=True, text=True)
    hit = "A17" in (r2.stdout + r2.stderr)
    after_size, after_sha = os.path.getsize(sbx_d06), sha(sbx_d06)
    unchanged = (after_size, after_sha) == (post_size, post_sha)
    print(f"腿2 负测：注入 __injected_probe__ ⇒ rc={r2.returncode}｜A17 命中={hit}｜"
          f"文件零变化={unchanged}")
    if r2.returncode == 0:
        ok = False
        print("   ❌ 生成器竟然 rc=0 —— 守卫恒不触发（恒真规则）")
    elif not hit:
        ok = False
        print("   ❌ 未命中 A17，拦截路径不对")
    elif not unchanged:
        ok = False
        print("   ❌ 守卫触发了但文件已被改动 —— 不是「拒绝写盘」而是「写了再报」")
    else:
        for line in (r2.stdout + r2.stderr).splitlines():
            if "A17" in line:
                print("   ", line.strip())

    # ── 腿3 真盘零写入 ──────────────────────────────────────────
    after = {f: (os.path.getsize(p), sha(p)) for f, p in real.items()}
    same = before == after
    print(f"腿3 真盘零写入：before==after ⇒ {same}")
    if not same:
        ok = False
        for f in before:
            if before[f] != after[f]:
                print(f"   ❌ {f} 真盘被改动：{before[f]} → {after[f]}")

    shutil.rmtree(sbx, ignore_errors=True)
    print(f"\n{'✅ 三腿全过：A17 非恒真，且真盘零写入' if ok else '❌ 自测失败'}"
          f"｜{datetime.now().strftime('%H:%M:%S')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
