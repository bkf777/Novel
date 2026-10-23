#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01-R33 补丁 · 「注释盲区」负测自测器（Q74 · 沙箱内跑，真盘零写入）

【为什么要有这个自测器】
  `selftest_U01_R33_manifest_guard.py` 覆盖的是「删一条断言」与「增一条断言」两种破坏。
  本自测器覆盖**第三种、最隐蔽的一种**：**把一条判据注释掉**。

  【缺陷机理（Q67 敏感度检验证实）】
    守卫原实现用**全文 token 计数**核对「清单条数 == 实际断言点数」：
        const nCall = src.split(token).length - 1;
    该计数把**注释里的 token 也算进去** ⇒ 注释掉一条判据**不改变计数**
    ⇒ 守卫继续报「清单 12 条 ＝ 实际断言点 12 处」并放行，而该判据**实际已死**。
    这正是守卫自己声称要防的「判据被无声删改」（Q56③）。

    【实测对照（修复前）】
      破坏方式        守卫反应                      真实违规是否仍被拦
      删除整行        ✅ exit 2 中止                —
      注释掉该行      ❌ 未察觉（仍报 12 ＝ 12）      ✅ 仍被 hardFail 抓到（exit 1）
      新增一条        ✅ exit 2 中止                —
      块注释包裹      ❌ 未察觉（修复前同样漏）        ✅ 同上

    【性质界定（勿夸大）】
      **不是假绿（无放行缺口）** —— `hardFail` 独立于 `assertFails` 计算，
      越窗／跨切／不同步类违规即便对应断言被注释，**仍会被 exit 1 拦下**。
      缺陷性质是**可审计性缺口**：守卫谎报「12 条断言点在跑」，实际在跑 11 条。

  【修复后应达成】
    四种破坏方式**一律 exit 2 中止**，且 stderr 出现守卫拒绝特征串、**无 JS 栈回溯**。

【自测腿（每脚本 × 4 腿）】
  A   基线      ：原样副本跑 → exit 0，且「清单 N 条 ＝ 实际断言点 N 处」「不通过 0 条」
  B1  删一行    ：删掉一整条断言语句              → exit 2（守卫拒绝）
  B2  注释一行  ：把一整条断言语句注释掉          → exit 2（守卫拒绝）★ 本次新增的关键腿
  B3  块注释包裹：用 /* ... */ 包裹一整条断言语句  → exit 2（守卫拒绝）★ 同上
  C   真盘零写入：全部腿跑完后，真盘脚本与交付物 SHA256 与跑前**逐字节一致**

【关键纪律】
  · **区分「守卫拒绝」与「沙箱脚本报错」**（Q73）：
    守卫拒绝＝ stderr 出现「❌ 中止：判据清单 …」且**无** JS 栈回溯；
    脚本报错＝ stderr 出现 SyntaxError／ReferenceError 等栈回溯。
  · **ROOT 由 __file__ 推导**（Q73）—— 不依赖调用方 cwd。
  · 负测**只在沙箱副本**做，真盘脚本与交付物全程只读（Q73）。

用法：python3 scripts/selftest_U01R33_guard_comment_blindspot.py
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # ← 由 __file__ 推导（Q73）
SCRIPTS = ROOT / "scripts"

TARGETS = [
    ("reconcile_D15_D16_timing.mjs", ["--unit", "U01"]),
    ("reconcile_tts_actual_vs_d15_budget.mjs", []),
]

GUARD_MARK = "❌ 中止：判据清单"      # 守卫拒绝的特征串
JS_ERRORS = ("SyntaxError", "ReferenceError", "TypeError", "at Object.", "at Module.")


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


def first_assertion_span(src: str) -> tuple[int, int]:
    """定位第一条断言语句的完整跨度（含分号）。返回 (行首索引, 结束索引)。"""
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
    return i + 1, end


def drop_line(src: str) -> str:
    """B1：删掉一整条断言语句（保留语法有效）。"""
    a, b = first_assertion_span(src)
    return src[:a] + src[b:]


def comment_out_line(src: str) -> str:
    """B2：把一整条断言语句**注释掉**（前置 // 前缀，语句本体保留）。

    ★ 这正是修复前守卫漏掉的那条破坏方式：
      全文 token 计数不变 ⇒ 守卫察觉不到 ⇒ 继续报「清单 N ＝ 断言点 N」并放行。
    """
    a, b = first_assertion_span(src)
    stmt = src[a:b]
    # 多行语句逐行加 // 前缀（保持行结构）
    commented = "\n".join(("// " + ln) if ln.strip() else ln for ln in stmt.split("\n"))
    return src[:a] + commented + src[b:]


def block_comment_line(src: str) -> str:
    """B3：用块注释 /* ... */ 包裹一整条断言语句。"""
    a, b = first_assertion_span(src)
    stmt = src[a:b]
    return src[:a] + "/* " + stmt + " */" + src[b:]


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


def is_guard_reject(rc: int, err: str) -> bool:
    """是否为「守卫拒绝」而非「沙箱脚本报错」（Q73）。"""
    return rc == 2 and GUARD_MARK in err and not any(e in err for e in JS_ERRORS)


def main() -> int:
    print("=" * 70)
    print("U01-R33 · 「注释盲区」负测（Q74 · 沙箱自测器 · Q73）")
    print(f"ROOT（由 __file__ 推导）＝ {ROOT}")
    print("=" * 70)

    before = fingerprint()
    legs_total, legs_ok = 0, 0

    with tempfile.TemporaryDirectory(prefix="u01r33_blindspot_") as td:
        tmp = Path(td)
        build_sandbox(tmp)
        print(f"沙箱 ＝ {tmp}\n")

        for name, args in TARGETS:
            print(f"── 受测脚本：{name}")
            src = (SCRIPTS / name).read_text(encoding="utf-8")
            sb = tmp / "scripts" / name

            # 腿A 基线
            sb.write_text(src, encoding="utf-8")
            rc, out, err = run(sb, args)
            okA = (rc == 0 and "不通过 0 条" in out
                   and re.search(r"清单 \d+ 条 ＝ 实际断言点 \d+ 处", out) is not None)
            legs_total += 1
            print(f"  [腿A 基线  ] exit={rc}｜{'✅ 通过' if okA else '❌ 未通过'}"
                  f"｜期望 exit 0 且「不通过 0 条」")
            legs_ok += 1 if okA else 0

            # 三种破坏方式
            for leg_name, mut, label in (
                ("B1 删一行", drop_line, "删掉一整条断言语句"),
                ("B2 注释一行", comment_out_line, "把一整条断言语句注释掉 ★关键腿"),
                ("B3 块注释包裹", block_comment_line, "用 /* */ 包裹一整条断言语句"),
            ):
                sb.write_text(mut(src), encoding="utf-8")
                rc, out, err = run(sb, args)
                ok = is_guard_reject(rc, err)
                legs_total += 1
                print(f"  [腿{leg_name}] exit={rc}｜{'✅ 通过' if ok else '❌ 未通过'}"
                      f"｜期望 exit 2 且属「守卫拒绝」")
                print(f"      守卫拒绝＝{is_guard_reject(rc, err)}｜"
                      f"脚本报错＝{any(e in err for e in JS_ERRORS)}")
                if err.strip():
                    first = err.strip().splitlines()[0]
                    print(f"      stderr：{first[:150]}")
                legs_ok += 1 if ok else 0
            print()

        # 腿C 真盘零写入
        after = fingerprint()
        print("── 腿C 真盘零写入：比对 %d 个文件（2 脚本 + U01/U02 的 D11/D15/D16）" % len(after))
        legs_total += 1
        unchanged = True
        for k, v in after.items():
            same = before.get(k) == v
            unchanged &= same
            print(f"   {'✅' if same else '❌'} {k}  sha256={v[:16]}…")
        print(f"   → {'✅ 真盘逐字节未变' if unchanged else '❌ 真盘发生变化！'}")
        legs_ok += 1 if unchanged else 0

    print("\n" + "=" * 70)
    print(f"受检腿数 {legs_total}｜通过 {legs_ok}｜"
          f"{'✅ 全部通过' if legs_ok == legs_total else '❌ 有未通过'}")
    print("=" * 70)
    return 0 if legs_ok == legs_total else 1


if __name__ == "__main__":
    sys.exit(main())
