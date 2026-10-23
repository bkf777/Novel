#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账脚本（视觉设定岗）｜追加 §<max+1>：C-131 核销回执 ＋ 索引两处残留 ＋ D18 Q77/Q87 口径分叉提示

取号纪律（Q85／Q86）：父章中文 ＋ 子章阿拉伯；动态取 max+1；**中文／阿拉伯两种章号形态
都解析、取数值最大者**；**全库章号可解析率必须 100%，有一条解析不了即中止不写盘（禁止静默过滤）**。
写盘：写前备份 ＋ 落笔前并发守卫 ＋ 原子写 ＋ 落盘后回读断言（重复章号归一化后为 0、不可解析为 0）。

**正文不入脚本**（纪律：取号器与写盘解耦 —— import 本模块不得触发任何写盘）；
正文经 `--body-file` 或 stdin 传入，`{parent}`／`{n}` 占位符在落笔前替换。

用法：
  python3 scripts/append_ledger_145_visual.py --body-file <正文.md> [--dry-run]
  cat 正文.md | python3 scripts/append_ledger_145_visual.py
"""

import argparse
import datetime
import io
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(ROOT, "99_交付说明.md")

DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
D_CN = "零一二三四五六七八九"


def cn2int(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    section = number = 0
    seen = False
    for ch in s:
        if ch in DIGITS:
            number = DIGITS[ch]
            seen = True
        elif ch in ("十", "百", "千"):
            section += (number if number else 1) * {"十": 10, "百": 100, "千": 1000}[ch]
            number = 0
            seen = True
        else:
            return None
    return section + number if seen else None


def int2cn(n):
    if n < 10:
        return D_CN[n]
    if n < 100:
        t, o = divmod(n, 10)
        return ("一" if t == 1 else D_CN[t]) + "十" + (D_CN[o] if o else "")
    h, rem = divmod(n, 100)
    s = D_CN[h] + "百"
    if rem == 0:
        return s
    if rem < 10:
        return s + "零" + D_CN[rem]
    t, o = divmod(rem, 10)
    return s + ("一" if t == 1 else D_CN[t]) + "十" + (D_CN[o] if o else "")


def chapters(text):
    rows, unparsable = [], []
    for i, line in enumerate(text.split("\n"), 1):
        if not line.startswith("## "):
            continue
        raw = line[3:].split("、", 1)[0].strip()
        v = cn2int(raw)
        if v is None:
            unparsable.append((i, raw))
        else:
            rows.append((i, raw, v))
    return rows, unparsable


def read_body(args):
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("❌ 需提供 --body-file 或经 stdin 传入正文（正文不入脚本，避免 import 即写盘）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    body = read_body(args)
    if not body.strip():
        raise SystemExit("❌ 正文为空，中止不写盘")
    if "{parent}" not in body or "{n}" not in body:
        raise SystemExit("❌ 正文缺占位符 {parent}／{n}（须含父章中文与子章阿拉伯号），中止不写盘")

    for attempt in range(5):
        base = open(REG, encoding="utf-8").read()
        rows, unp = chapters(base)
        if unp:
            raise SystemExit("❌ Q86 硬要求：全库章号可解析率须 100%%，当前 %d 条不可解析 %r → 中止不写盘"
                             % (len(unp), unp))
        vals = [v for _, _, v in rows]
        maxnum = max(vals)
        nxt = maxnum + 1
        parent = int2cn(nxt)
        assert cn2int(parent) == nxt, "int2cn 往返断言失败"
        sec = body.replace("{parent}", parent).replace("{n}", str(nxt))

        # ---------- 自述章号一致性守卫（fail-loud，不静默写盘） ----------
        # 共用模块＝分镜导演 `scripts/_ledger_selfchap_guard_mavis.py`（只定义函数、无顶层副作用）
        # 起因：本岗 12:0x 建议 ＋ 分镜导演 10:0x 的自述章号指错事故（其 §206.3 登记）。
        # 本岗补两处该模块**未覆盖**的口径（详见本节台账）：
        #   ① A1 只认阿拉伯数字（`§213`）⇒ **本项目父章用中文式**（`§二百一十三`），
        #      中文式硬编码自身章号会**漏检** ⇒ 本岗自补中文式比对；
        #   ② A2 的 PLACEHOLDERS 是 `{chap}/{nxt}/{now}/{mark}` ⇒ **不含本岗的 `{parent}/{n}`**
        #      ⇒ 本岗自补本岗占位符残留检查（同样剔除反引号片段，合法引用不算残留）。
        gpath = os.path.join(HERE, "_ledger_selfchap_guard_mavis.py")
        if os.path.exists(gpath):
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location("_ledger_selfchap_guard_mavis", gpath)
            G = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(G)
            ok, gmsg = G.assert_self_chapno(template=body, rendered=sec, chap_num=nxt)
        else:
            ok, gmsg = True, "⚠️ 共用守卫模块缺失（%s）→ 本次未执行 A1/A2 断言" % gpath
        if not ok:
            print("❌ 自述章号一致性守卫未通过（共用模块）：\n   %s" % gmsg)
            print("   ⇒ 中止，不写盘（fail-loud）")
            return 3
        # 本岗补 ①：中文式父章号硬编码自身章号
        for _s in re.findall(r"§([零一二三四五六七八九十百千]+)", body):
            _v = cn2int(_s)
            if _v is not None and _v == nxt:
                print("❌ 模板正文里硬编码了自身章号（中文式）§%s（=%d）⇒ 一律改用 {parent}／{n} 占位符。"
                      % (_s, nxt))
                print("   ⇒ 中止，不写盘（fail-loud）")
                return 3
        # 本岗补 ②：渲染后**残留占位符样式 token** 扫描（剔除反引号片段，合法引用不算残留）
        #   ⚠️ 2026-10-23 12:2x 自查修正：先前只查 `{parent}`／`{n}` 两个**精确**形态 ⇒ **恒不触发**
        #   （本岗语法下这两个形态必被 replace 全量替换，残留不可能出现）——典型的「存在但无效的守卫」。
        #   改为扫描**任意** `{标识符}` 形态 ⇒ 能抓住：拼写错的 `{parentx}`／`{n2}`、
        #   他岗语法的 `{chap}`／`{nxt}`／`{now}`／`{mark}`、以及任何漏网的占位符。
        _scan = re.sub(r"`[^`]*`", "", sec)
        _left = sorted(set(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", _scan)))
        if _left:
            print("❌ 渲染后正文仍残留占位符样式 token %r ⇒ 章号/小节号会渲染成字面量。" % _left)
            print("   ⇒ 中止，不写盘（fail-loud）")
            return 3
        print("=== 自述章号一致性守卫 ===")
        print("  %s" % gmsg)
        print("  本岗补项：中文式自身章号 0 处｜本岗占位符残留 0 处 ✅")

        print("=== 取号（Q85/Q86）===")
        print("  标题 %d｜max %d｜不可解析 0 ✅" % (len(rows), maxnum))
        print("  本节占号 = §%s（%d）" % (parent, nxt))
        if args.dry_run:
            print("🔍 --dry-run：未写盘")
            return 0

        now = open(REG, encoding="utf-8").read()
        if now != base:
            print("⚠️ 落笔前检测到文件已被他人改动 → 重算取号重来")
            continue

        bak_dir = os.path.join(ROOT, "reports",
                               "_bak_LEDGER_%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))

        out = base.rstrip("\n") + "\n" + sec.lstrip("\n")
        tmp = REG + ".tmp.%d" % os.getpid()
        st = os.stat(REG)
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(out)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, REG)

        after = open(REG, encoding="utf-8").read()
        rows2, unp2 = chapters(after)
        vals2 = [v for _, _, v in rows2]
        dup2 = {v: vals2.count(v) for v in set(vals2) if vals2.count(v) > 1}
        assert dup2 == {}, "❌ 落盘后重复章号 %r" % dup2
        assert unp2 == [], "❌ 落盘后不可解析章号 %r" % unp2
        assert ("## %s、视觉设定（bot_db3fd3817800）" % parent) in after
        print("=== 落盘后回读断言 ===")
        print("  标题 %d｜重复 %r｜不可解析 %d ✅" % (len(rows2), dup2 or "无", len(unp2)))
        print("  备份 → %s" % os.path.relpath(bak_dir, ROOT))
        print("  ✅ 新章 §%s（%d）已追加" % (parent, nxt))
        return 0

    print("❌ 连续 5 轮并发冲突，未写盘")
    return 2


if __name__ == "__main__":
    sys.exit(main())
