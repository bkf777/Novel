#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账通用追加器（分镜导演岗）—— 取号与写盘解耦，正文走 --body-file。

【为什么不再复用 append_ledger_125_mavis.py】
  那个脚本把「正文」硬编码在源码里（`build_body()`），导致：
  · 想复用到别的章节就必须复制一份脚本（复制即分叉）；
  · **import 该模块 = 执行一次追加**（正文硬编码在模块层）——这是上一轮
    「只读取号函数却凭空多出一节」的根因（教训见 main 记忆：
    「取号脚本必须与写盘动作解耦：import 一个会写盘的取号器＝执行一次追加」）。
  ⇒ 本脚本：**正文一律由 --body-file 传入**；模块层只有纯函数，
    写盘动作全部在 `if __name__ == "__main__":` 之下 ⇒ import 无副作用。

【正文占位符】
  @@CHAP@@    → 中文父章号（如「一百五十九」）
  @@CHAPNO@@  → 阿拉伯父章号（如「159」，供 `### @@CHAPNO@@.1` 子节用）

【口径与护栏（全部沿用已实跑验证过的规则）】
  · 父章号中文数字（Q85），子章号阿拉伯；取号＝解析全部既有章标题取 max+1。
  · 取号脚本双格式兼容（阿拉伯父章／中文父章），中文解析支持「零」。
  · 并发护栏：取号后再次复检末章号；他人已追加 → exit 3，请重跑。
  · 内建备份 → reports/_bak_ledger_ch<N>_<时戳>/99_交付说明.md
  · 写后自检：① 前段逐字节一致 ② 新章标题出现 1 次 ③ 位于末章 ④ 文件增长
              ⑤ 全库章号可解析率／重复章号
  · 幂等用「内容特征签名」(--fingerprint) 判定，**不用章号**（章号会递增 ⇒ 恒判不出已落）。
  · 写盘前**断言指纹逐字在正文里**（防「指纹与正文脱钩」致幂等恒不成立）。
  · 内容级重复检测：正文归一化后与既有某章相同 ⇒ NO-OP（Q42 不重复记账）。
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s):
    """中文数字 → int（支持「零」；阿拉伯数字直接返回）。"""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total = 0
    num = None
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == "十":
            total += (num if num is not None else 1) * 10
            num = None
        elif ch == "百":
            total += (num if num is not None else 1) * 100
            num = None
        else:
            return None
    return total if num is None else total + num


def int2cn(n):
    """int → 中文数字，跟台账既有惯例一致：
    百位后接两位数不带「零」（一百五十六）；余数 <10 才补「零」（一百零五）；
    余数 10–19 走「一十」体例（一百一十五），与现盘 §一百一十…§一百一十九 的写法一致。"""
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n < 20:
        return "十" + (digits[n % 10] if n % 10 else "")
    if n < 100:
        s = digits[n // 10] + "十"
        return s + (digits[n % 10] if n % 10 else "")
    s = digits[n // 100] + "百"
    r = n % 100
    if r == 0:
        return s
    if r < 10:
        return s + "零" + digits[r]
    if r < 20:
        return s + "一十" + (digits[r - 10] if r > 10 else "")
    return s + int2cn(r)


def norm_chapter(t):
    """章节正文归一化签名：只抹掉章号/子章号编号，其余逐字保留。
    用途＝内容级重复检测（两次追加正文逐字相同、仅章号不同时必须判为重复）。"""
    t = re.sub(r"^##\s+[^、\n]+、", "## <章>、", t, flags=re.M)
    t = re.sub(r"^###\s+[\d零一二三四五六七八九十百]+\.[\d零一二三四五六七八九十百]+",
               "### <子>", t, flags=re.M)
    t = re.sub(r"§[零一二三四五六七八九十百\d]+", "§#", t)
    t = re.sub(r"第[零一二三四五六七八九十百\d]+章", "第#章", t)
    return t.strip()


def chapter_bodies(text):
    return [p for p in re.split(r"(?m)^(?=##\s)", text) if p.startswith("## ")]


def find_duplicate_chapter(text, new_body):
    """返回与 new_body 归一化后相同的既有章标题；无则 None。"""
    sig = norm_chapter(new_body)
    for chap in chapter_bodies(text):
        if norm_chapter(chap) == sig:
            m = re.match(r"^##\s+(.+?)、", chap)
            return m.group(1).strip() if m else "?"
    return None


def parse_chapters(text):
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        out.append((cn2int(raw), raw, text[:m.start()].count("\n") + 1))
    return out


def render_body(body_tpl, chap_no):
    """占位符替换：@@CHAP@@ → 中文章号；@@CHAPNO@@ → 阿拉伯章号。"""
    return (body_tpl.replace("@@CHAPNO@@", str(chap_no))
                 .replace("@@CHAP@@", int2cn(chap_no)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--body-file", required=True,
                    help="正文文件；含 @@CHAP@@ / @@CHAPNO@@ 占位符")
    ap.add_argument("--fingerprint", action="append", default=[],
                    help="幂等指纹（可多次）；必须逐字出现在正文里，且逐字出现在台账里才判已落")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")
    if not os.path.isfile(args.body_file):
        sys.exit(f"[ABORT] 找不到正文文件：{args.body_file}")

    with open(args.body_file, "r", encoding="utf-8") as f:
        body_tpl = f.read()

    # ── 写前守卫①（2026-10-23 11:1x 新增）：正文模板必须自带顶级章标题行 ──
    #    起因：11:1x 本岗误用——正文只写了「### @@CHAPNO@@ …」而漏了「## @@CHAP@@、…」这一行，
    #    追加器照写 ⇒ 本节**落在他人章内、无顶级标题**；写后自检②③虽拦下，但**写在自检之前、
    #    报错不回滚** ⇒ 台账留下错位态（本岗已用带 CAS 的外科修复收口，见台账 §170.1）。
    #    ⇒ 本守卫把该类错误移到**写盘前**拦截（Q64 守卫 + Q68：区分「守卫拒绝」与「脚本报错」）。
    if not re.search(r"(?m)^## @@CHAP@@、", body_tpl):
        sys.exit("[ABORT] 正文模板缺顶级章标题行「## @@CHAP@@、…」（占位符须逐字出现）"
                 "⇒ 否则本节会落进他人章内 ⇒ 拒绝写盘（未做任何写盘动作）")
    # ── 写前守卫②：子节号必须带「.N」（父章中文 ＋ 子章阿拉伯，Q85）──
    if not re.search(r"(?m)^### @@CHAPNO@@\.\d+ ", body_tpl):
        sys.exit("[ABORT] 正文模板的子节标题须为「### @@CHAPNO@@.N …」"
                 "（父章中文＋子章阿拉伯，Q85；缺 .N 会写成「### 170」而非「### 170.1」）⇒ 拒绝写盘")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()

    chaps = parse_chapters(text)
    nums = [c[0] for c in chaps if c[0] is not None]
    if not nums:
        sys.exit("[ABORT] 台账无可解析章号")
    max_no = max(nums)
    target = max_no + 1
    cn = int2cn(target)

    # ── 幂等：指纹须逐字都在台账里（全部命中才算已落，避免单指纹误判）──
    if args.fingerprint:
        hits = [fp for fp in args.fingerprint if fp in text]
        if len(hits) == len(args.fingerprint):
            print(f"[NO-OP] 台账已含全部内容指纹（{len(hits)}/{len(args.fingerprint)} 命中），"
                  f"不重复追加（当前末章＝{chaps[-1][1]}／{chaps[-1][0]}）")
            return 0

    # ── 并发复检（CAS 守卫）：取号期间他人是否已追加 ──
    nums2 = [c[0] for c in parse_chapters(text) if c[0] is not None]
    if max(nums2) != max_no:
        print(f"[RETRY] 取号期间他人已追加（max {max_no} → {max(nums2)}），本轮中止，请重跑")
        return 3

    body = render_body(body_tpl, target)

    # ── 前置断言：指纹必须真的在正文里（否则幂等判定恒不成立）──
    for fp in args.fingerprint:
        if fp not in body:
            sys.exit(f"[ABORT] 幂等指纹与正文脱钩：{fp!r} 不在正文中 ⇒ 幂等判定会恒不成立 ⇒ 拒绝写盘")

    # ── 前置断言：内容级重复检测（Q42）──
    dup = find_duplicate_chapter(text, body)
    if dup is not None:
        print(f"[NO-OP] 台账已存在与本节正文**逐字相同**的章节「## {dup}、」（内容级重复检测命中）→ 不重复记账")
        return 0

    if args.dry_run:
        print(f"[DRY-RUN] 将追加「## {cn}、…」（当前末章＝{chaps[-1][1]}／{chaps[-1][0]}）")
        return 0

    # ── CAS 守卫：写盘前复检台账 SHA256（读后若被他人改动 ⇒ 中止，不覆盖他人字节）──
    sha_before = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with open(ledger, "r", encoding="utf-8") as f:
        if hashlib.sha256(f.read().encode("utf-8")).hexdigest() != sha_before:
            print("[RETRY] 读盘后台账已被他人改动（SHA256 不一致）⇒ 本轮中止，请重跑")
            return 3

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(root, "reports", f"_bak_ledger_ch{target}_{ts}")
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(ledger, bak)
    print(f"   · 备份 → reports/_bak_ledger_ch{target}_{ts}/99_交付说明.md（{os.path.getsize(bak)} B）")

    before_len = len(text)
    before_bytes = len(text.encode("utf-8"))
    new_text = text.rstrip("\n") + "\n" + body
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(new_text)

    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    a1 = after.startswith(text.rstrip("\n"))
    # ② 统计对象＝**行首的顶级章标题行**（不是全文子串出现次数）——
    #    2026-10-23 11:1x 实测教训：正文里行内提到占位符（渲染后成为行内「## 一百七十一、」文本）
    #    会让子串计数变成 2 ⇒ 误判「重复章标题」⇒ 触发自动回滚、白白重写一次。
    #    ⇒ 计数必须写明统计对象（Q49 口径）。
    a2 = sum(1 for l in after.split("\n") if re.match(r"^## " + re.escape(cn) + r"、", l)) == 1
    a2_raw = after.count(f"## {cn}、")
    chaps3 = parse_chapters(after)
    a3 = chaps3[-1][1] == cn
    a4 = len(after) > before_len
    parsed = [c[0] for c in chaps3 if c[0] is not None]
    unparsed = len(chaps3) - len(parsed)
    dupno = len(parsed) - len(set(parsed))
    print(f"■ 台账追加自检：章号 {cn}（{target}）")
    print(f"   ① 前段逐字节一致：{a1}")
    print(f"   ② 行首顶级章标题「## {cn}、」计数 ＝ 1：{a2}（全文子串出现 {a2_raw} 次；"
          f"行内提及不计）")
    print(f"   ③ 位于末章：{a3}（末章＝{chaps3[-1][1]}／{chaps3[-1][0]}）")
    print(f"   ④ 文件增长：{a4}（{before_bytes} → {len(after.encode('utf-8'))} B，"
          f"+{len(after.encode('utf-8')) - before_bytes}）")
    print(f"   ⑤ 全库章号可解析率：{len(parsed)}/{len(chaps3)}｜未解析 {unparsed}｜重复章号 {dupno}")
    if not (a1 and a2 and a3 and a4):
        # ── 写后自检失败：**能安全回滚就回滚**（Q68：不得留下半成品）──
        #   仅当「写盘后无人再改过本文件」（现盘 SHA256 仍等于我方写入值）时，才从备份原子还原；
        #   若他人已在写后动过 ⇒ **不回滚**（避免覆盖他人字节），改为报错＋指认人工处理。
        written_sha = hashlib.sha256(after.encode("utf-8")).hexdigest()
        with open(ledger, "r", encoding="utf-8") as f:
            now_sha = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
        if now_sha == written_sha:
            shutil.copy2(bak, ledger + ".tmp_rollback")
            os.replace(ledger + ".tmp_rollback", ledger)
            print("[ROLLBACK] 写后自检未过，且写后无人改动本文件 ⇒ 已从备份原子还原，"
                  f"台账回到 {before_bytes} B（备份 {bak}）")
            return 3
        print("[ABORT] 写后自检未过，但写盘后本文件已被他人改动 ⇒ **不自动回滚**（避免覆盖他人字节）；"
              f"请人工核（备份 {bak}）")
        return 3
    print("✅ 台账章节落盘并通过四轴自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
