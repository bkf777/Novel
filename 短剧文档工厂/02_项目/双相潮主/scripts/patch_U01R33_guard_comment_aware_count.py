#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U01-R33 补丁 · 判据清单守卫的「注释盲区」修复（Q74）

【缺陷（本岗独立复核发现，Q67 敏感度检验证实）】
  U01 侧两个只读对账脚本的清单守卫用**全文 token 计数**核对
  「判据清单条数 == 实际断言点数」：
      const src = readFileSync(fileURLToPath(import.meta.url), "utf8");
      const token = "ch" + "k(";
      const nCall = src.split(token).length - 1;
  该计数**把注释里的 token 也算进去** ⇒ 把一条判据**注释掉**（`// chk(...)`）
  不会改变 token 计数 ⇒ 守卫仍然报「清单 12 条 ＝ 实际断言点 12 处」并放行，
  而**该判据实际已死**。这正是守卫自己声称要防的「判据被无声删改」（Q56③）。

  【实测证据（沙箱，本岗独立复现，非采信转述）】
    破坏方式            守卫反应                真实违规是否仍被拦
    ────────────────────────────────────────────────────────────
    删除整行            ✅ exit 2 中止           —
    **注释掉该行**      ❌ **未察觉**（仍报 12＝12） ✅ 仍被 hardFail 抓到（exit 1）
    新增一条            ✅ exit 2 中止           —

  【性质界定（重要，勿夸大）】
    **不是假绿（无放行缺口）** —— `hardFail` 独立于 `assertFails` 计算
    （hardFail = voRep.over.length + ... + sfxCross.length），
    故越窗／跨切／不同步类违规即便对应断言被注释，**仍会被 exit 1 拦下**。
    本缺陷的性质是**可审计性缺口**：守卫谎报「12 条断言点在跑」，实际在跑 11 条；
    清单中该条判据已死而报告里看不出来。

【修法】
  计数前**剔除注释**再数 token：
    ① 去掉块注释 /* ... */（保留换行，维持行结构）；
    ② 去掉行注释 // ...（只截到该行第一个 // 之前）。
  ⇒ 注释掉一条判据 ⇒ token 计数 12→11 ⇒ 守卫 exit 2 中止（与「删除整行」同等待遇）。

【安全前提（已实测）】
  · 两脚本内**无字符串字面含 `//` 或 `/*`**（仅文件头 `/**` 一处块注释）；
  · 两个脚本的守卫锚点块**逐字一致** ⇒ 同一补丁可复用；
  · 计数仍用 `"ch" + "k("` 拼接 ⇒ 守卫函数自身不被数进去（原有性质保持）。

【约束】
  · **只读脚本，不改任何判据内容、时码、口径**（本补丁只动守卫的计数实现）；
  · 只改 `scripts/` 下这两个**本岗产出**的只读对账脚本，不碰他人交付物；
  · 带备份（reports/_bak_*）与幂等性（已修则 [NO-OP]）；
  · 落盘后必须复跑两个脚本 U01／U02，并确认 exit 0 与「清单 12 ＝ 断言点 12」不变。

用法：python3 scripts/patch_U01R33_guard_comment_aware_count.py --project .
"""
import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGETS = [
    "reconcile_D15_D16_timing.mjs",
    "reconcile_tts_actual_vs_d15_budget.mjs",
]

# 旧计数块（两脚本逐字一致）
OLD_BLOCK = '''  const token = "ch" + "k(";
  const nCall = src.split(token).length - 1;
'''

# 新计数块：剔除注释后再计数
#
# ⚠️ 自指陷阱（本补丁实测踩过，必须避开）：
#   剔除块注释的正则若以**字面 `/*`** 写进被注入的源码，
#   该正则自己会被「剔除块注释」的动作吃掉（自指），
#   导致注入块整段消失、断言点计数归 0。
#   故此处用 `String.fromCharCode` 构造分隔符，源码里**不出现字面 `/*` 与 `*/`**。
#   同理，行注释分隔符以字面 `//` 出现是安全的 —— 它只影响**注释文本**，
#   而注释文本内不含断言函数名（该约束由 Q56 token 规则保证）。
NEW_BLOCK = '''  const token = "ch" + "k(";
  // 【Q74】计数前必须**剔除注释** —— 否则「把一条判据注释掉」这一最常见的
  //   静默删改手法不会改变 token 计数，守卫会继续谎报「清单 N 条 ＝ 实际断言点
  //   N 处」而该判据实际已死（Q67：恒真判据零信息量；Q56③ 的本意即防无声删改）。
  //   实测（沙箱）：删整行 → 守卫 exit 2；注释掉该行 → 旧实现**未察觉**仍放行。
  //   注：`hardFail` 独立于断言清单计算，故真实违规仍会被 exit 1 拦下，
  //   本条修的是**可审计性**（守卫不再谎报在跑的断言点条数），不是放行缺口。
  //   安全前提：脚本内无字符串字面含行注释分隔符（已实测），故按行截断安全。
  //   ⚠️ 分隔符用 charCode 构造，源码里不写字面块注释起始符（避免自指，见补丁脚本头）。
  const SL = String.fromCharCode(47, 42);
  const SR = String.fromCharCode(42, 47);
  const blockRe = new RegExp(SL.replace("*", "\\\\*") + "[\\\\s\\\\S]*?" + SR.replace("*", "\\\\*"), "g");
  const noBlock = src.replace(blockRe, (m) => m.replace(/[^\\n]/g, " "));
  const codeOnly = noBlock
    .split("\\n")
    .map((ln) => { const i = ln.indexOf("//"); return i >= 0 ? ln.slice(0, i) : ln; })
    .join("\\n");
  const nCall = codeOnly.split(token).length - 1;
'''

MARKER = "Q74"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def count_chk_code_only(src: str) -> int:
    """与守卫实现**同口径**的 token 计数（剔除注释后再数）。

    ⚠️ 必须与注入代码同口径：块注释分隔符同样用 charCode 构造，
       否则本函数会把注入块当成块注释吃掉（自指）而误判断言点为 0。
    """
    sl, sr = chr(47) + chr(42), chr(42) + chr(47)
    no_block = re.sub(
        re.escape(sl) + r"[\s\S]*?" + re.escape(sr),
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        src,
    )
    code_only = "\n".join(
        (ln[: ln.index("//")] if "//" in ln else ln) for ln in no_block.split("\n")
    )
    return code_only.split("chk(").__len__() - 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".", help="项目根目录")
    args = ap.parse_args()
    root = Path(args.project).resolve()
    scripts = root / "scripts"

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = root / "reports" / f"_bak_U01R33_guard_comment_count_{ts}"
    bak.mkdir(parents=True, exist_ok=True)

    changed, noop, failed = [], [], []
    for name in TARGETS:
        p = scripts / name
        if not p.exists():
            print(f"[SKIP] 不存在：{name}")
            failed.append(name)
            continue
        src = p.read_text(encoding="utf-8")
        if MARKER in src and "noBlock" in src:
            print(f"[NO-OP] 已是注释感知计数：{name}")
            noop.append(name)
            continue
        if OLD_BLOCK not in src:
            print(f"[ABORT] 锚点块未命中（脚本已被他人改动）：{name}")
            failed.append(name)
            continue

        n_before = src.count("chk(")
        n_code_after = count_chk_code_only(src)
        new_src = src.replace(OLD_BLOCK, NEW_BLOCK, 1)
        n_code_new = count_chk_code_only(new_src)

        # 自洽性：剔除注释后的计数须与清单条数一致（改后仍为 12）
        m = re.search(r"const ASSERT_MANIFEST = \[(.*?)\n\];", new_src, re.S)
        if not m:
            print(f"[ABORT] 未找到 ASSERT_MANIFEST：{name}")
            failed.append(name)
            continue
        n_manifest = len(re.findall(r'\{ id: "', m.group(1)))
        if n_code_new != n_manifest:
            print(f"[ABORT] 改后代码区断言点 {n_code_new} ≠ 清单 {n_manifest}：{name}")
            failed.append(name)
            continue

        shutil.copy2(p, bak / name)
        p.write_text(new_src, encoding="utf-8")
        print(f"[OK] {name}：全文 token {n_before} → 代码区 token {n_code_new}（清单 {n_manifest}）")
        changed.append(name)

    print(f"\n备份目录：{bak}")
    print(f"改动 {len(changed)} 个｜[NO-OP] {len(noop)} 个｜失败 {len(failed)} 个")
    if failed:
        print("失败项：", failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
