#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01-R33 · 判据清单守卫 负测自测器（沙箱内跑，真盘零写入）

【为什么在沙箱里做】
  Q73：**版本／漂移守卫的负测只能在沙箱副本做**，禁在真实交付物上伪造 version。
  本单要验的是「**删／增断言 → 守卫必须 exit 2 中止**」，
  负测必然要破坏脚本与判据的对齐关系 —— 若在真盘脚本上做，
  中途一旦中断就会把**残缺脚本**留在生产路径上。
  故：一切改动只发生在沙箱副本，真盘脚本与交付物全程只读。

【自测腿（每条脚本 × 4 腿）】
  A  基线   ：原样副本跑 → exit 0，且「清单 N 条 ＝ 实际断言点 N 处」「不通过 0 条」
  B1 删一条 ：删掉**一整条断言语句**（语法保持有效）→ 清单 12 ≠ 断言点 11 → exit 2
  B2 增一条 ：多插一条断言语句 → 清单 12 ≠ 断言点 13 → exit 2
  C  真盘   ：全部腿跑完后，真盘脚本与交付物 SHA256 与跑前**逐字节一致**

【关键纪律】
  · **区分「守卫拒绝」与「沙箱脚本报错」**（Q73）：
    守卫拒绝的特征＝ stderr 出现「❌ 中止：判据清单 …」且**无** JS 栈回溯；
    脚本报错的特征＝ stderr 出现 SyntaxError／ReferenceError 等栈回溯。
    两者必须分开计数，不能都算成「负测通过」。
  · **ROOT 由 __file__ 推导**（Q73）—— 不依赖调用方 cwd。
  · 沙箱内 items.json 的音频绝对路径**改写为沙箱路径**，使沙箱自洽（不回落读真盘音频）。

用法：python3 scripts/selftest_U01_R33_manifest_guard.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # ← 由 __file__ 推导（Q73）
SCRIPTS = ROOT / "scripts"

# 受测脚本 → 正常运行附加参数
TARGETS = [
    ("reconcile_D15_D16_timing.mjs", ["--unit", "U01"]),
    ("reconcile_tts_actual_vs_d15_budget.mjs", []),
]

GUARD_MARK = "❌ 中止：判据清单"      # 守卫拒绝的特征串
JS_ERRORS = ("SyntaxError", "ReferenceError", "TypeError", "at Object.", "at Module.")


# ── 工具 ──────────────────────────────────────────────────────────────────────
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fingerprint() -> dict:
    """真盘指纹：受测脚本 + 本岗 U01/U02 交付物。"""
    fps = {}
    for name, _ in TARGETS:
        fps[f"scripts/{name}"] = sha256(SCRIPTS / name)
    for u in ("U01", "U02"):
        for f in ("D11.json", "D15.json", "D16.json"):
            p = ROOT / "units" / u / f
            if p.exists():
                fps[f"units/{u}/{f}"] = sha256(p)
    return fps


def drop_first_assertion(src: str) -> str:
    """删掉**一整条断言语句**（从行首 'chk(' 起到语句末尾 ';'），语法保持有效。

    用括号配平找语句边界 —— 断言消息里有中文与模板串，直接按行删会截断多行语句。
    """
    i = src.index("\nchk(")
    j = src.index("(", i)
    depth, in_str, k = 0, None, j
    while k < len(src):
        c = src[k]
        if in_str:
            if c == "\\":
                k += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "\"'`":
            in_str = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        k += 1
    end = k + 1
    while end < len(src) and src[end] in " \t":
        end += 1
    if end < len(src) and src[end] == ";":
        end += 1
    return src[: i + 1] + src[end:]


def add_one_assertion(src: str) -> str:
    """多插一条断言语句（放在最后一次 process.exit 之前，保证语法有效）。"""
    ins = '\nchk(true, "Z9", "sandbox 额外断言点");\n'
    p = src.rindex("process.exit(")
    return src[:p] + ins + src[p:]


def build_sandbox(tmp: Path) -> Path:
    """搭沙箱：脚本副本 + U01/U02 的 D11/D15/D16 + preview/U01_tts（路径改写到沙箱）。"""
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    for u in ("U01", "U02"):
        (tmp / "units" / u).mkdir(parents=True, exist_ok=True)
        for f in ("D11.json", "D15.json", "D16.json"):
            src = ROOT / "units" / u / f
            if src.exists():
                shutil.copy2(src, tmp / "units" / u / f)

    prev = tmp / "preview" / "U01_tts"
    (prev / "audio").mkdir(parents=True, exist_ok=True)
    items_src = ROOT / "preview" / "U01_tts" / "items.json"
    audio_src = ROOT / "preview" / "U01_tts" / "audio"
    shutil.copy2(items_src, prev / "items.json")
    for m in sorted(audio_src.glob("*.mp3")):
        shutil.copy2(m, prev / "audio" / m.name)
    # 绝对路径 → 沙箱路径（沙箱自洽：不回落读真盘音频）
    items = json.loads((prev / "items.json").read_text(encoding="utf-8"))
    for it in items:
        a = it.get("audio")
        if isinstance(a, str) and a.startswith("/"):
            it["audio"] = str(prev / "audio" / Path(a).name)
    (prev / "items.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp


def run(script: Path, args) -> tuple[int, str, str]:
    p = subprocess.run(["node", str(script)] + list(args), cwd=str(script.parent.parent),
                       capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


# ── 自测 ──────────────────────────────────────────────────────────────────────
def main() -> int:
    before = fingerprint()
    tmp = Path(tempfile.mkdtemp(prefix="u01r33_sandbox_"))
    legs_total, legs_ok = 0, 0
    print("═" * 78)
    print("U01-R33 · 判据清单守卫 负测（沙箱自测器 · Q73）")
    print(f"ROOT（由 __file__ 推导）＝ {ROOT}")
    print(f"沙箱 ＝ {tmp}")
    print("═" * 78)

    try:
        build_sandbox(tmp)
        for name, args in TARGETS:
            print(f"\n── 受测脚本：{name}")
            src = (SCRIPTS / name).read_text(encoding="utf-8")
            sandbox_script = tmp / "scripts" / name

            # ── 腿 A：基线（沙箱原样副本应与真盘同结论）──
            sandbox_script.write_text(src, encoding="utf-8")
            rc, out, err = run(sandbox_script, args)
            legs_total += 1
            okA = (rc == 0 and "判据清单" in out and "不通过 0 条" in out
                   and "Traceback" not in err and not any(e in err for e in JS_ERRORS))
            print(f"  [腿A 基线 ] exit={rc}｜{'✅ 通过' if okA else '❌ 未通过'}"
                  f"｜期望 exit 0 且「不通过 0 条」")
            if not okA:
                print("      stdout 尾段：", out[-400:])
                print("      stderr 尾段：", err[-400:])
            legs_ok += 1 if okA else 0

            # ── 腿 B1：删一条断言 → 必须 exit 2 ──
            sandbox_script.write_text(drop_first_assertion(src), encoding="utf-8")
            rc, out, err = run(sandbox_script, args)
            legs_total += 1
            guard_reject = GUARD_MARK in err
            script_error = any(e in err for e in JS_ERRORS)
            okB = (rc == 2 and guard_reject and not script_error)
            print(f"  [腿B1 删一条] exit={rc}｜{'✅ 通过' if okB else '❌ 未通过'}"
                  f"｜期望 exit 2 且属「守卫拒绝」")
            print(f"      守卫拒绝＝{guard_reject}｜脚本报错＝{script_error}"
                  f"｜stderr：{err.strip()[:160] or '(空)'}")
            legs_ok += 1 if okB else 0

            # ── 腿 B2：增一条断言 → 必须 exit 2 ──
            sandbox_script.write_text(add_one_assertion(src), encoding="utf-8")
            rc, out, err = run(sandbox_script, args)
            legs_total += 1
            guard_reject = GUARD_MARK in err
            script_error = any(e in err for e in JS_ERRORS)
            okC = (rc == 2 and guard_reject and not script_error)
            print(f"  [腿B2 增一条] exit={rc}｜{'✅ 通过' if okC else '❌ 未通过'}"
                  f"｜期望 exit 2 且属「守卫拒绝」")
            print(f"      守卫拒绝＝{guard_reject}｜脚本报错＝{script_error}"
                  f"｜stderr：{err.strip()[:160] or '(空)'}")
            legs_ok += 1 if okC else 0

        # ── 腿 C：真盘零写入 ──
        after = fingerprint()
        legs_total += 1
        diff = [k for k in before if before.get(k) != after.get(k)]
        okD = (not diff)
        print(f"\n── 腿C 真盘零写入：比对 {len(before)} 个文件"
              f"（2 脚本 + U01/U02 的 D11/D15/D16）")
        for k, v in before.items():
            same = before.get(k) == after.get(k)
            print(f"   {'✅' if same else '❌'} {k}  sha256={v[:16]}…")
        print(f"   → {'✅ 真盘逐字节未变' if okD else '❌ 真盘被改动：' + ', '.join(diff)}")
        legs_ok += 1 if okD else 0

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "═" * 78)
    print(f"受检腿数 {legs_total}｜通过 {legs_ok}｜"
          f"{'✅ 全部通过' if legs_ok == legs_total else '❌ 有未通过'}")
    print("═" * 78)
    return 0 if legs_ok == legs_total else 1


if __name__ == "__main__":
    sys.exit(main())
