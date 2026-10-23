#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""append_ledger_section.py —— 追加台账新章节（台本编剧岗）—— 动态取最大章号 + 1。

用法：
  python3 scripts/append_ledger_section.py --body-file <正文文件>

正文文件为**纯 Markdown 片段**，可用三个占位符：
  {chap}  → 中文父章号（如 一百三十八）—— 标题里用「## {chap}、…」
  {nxt}   → 子章数字前缀（如 138）—— 子标题里用「### {nxt}.1 …」
  {now}   → 执行时刻（YYYY-MM-DD HH:MM）

⚠️ **2026-10-23 修正两处（原实现的两个坑）**：
  ① **无 `if __name__ == "__main__"` 保护** —— 原实现把「追加」写在模块顶层，
     **import 本模块就会真的写盘**（本岗 09:3x 用 `import append_ledger_section`
     取号做只读核算，结果意外把 §134 的正文又追加了一遍 = §138 重复节）。
     现改为：**只有命令行执行才写盘**；import 永不产生副作用。
  ② **正文硬编码在脚本里** —— 原实现每次追加都写同一段文本，无法追加新内容。
     现改为：**正文从 `--body-file` 读入**，本脚本只负责「取号 + 排版 + 追加 + 查重」。

Q85 体例（企划合规裁定）：父章 `## ` 一律**中文数字**，子章 `### ` 一律**阿拉伯数字**。
取号脚本必须**双格式兼容**（台账存在历史阿拉伯父章），只用中文解析或只用 isdigit 都会跳号撞号。
"""
import argparse
import datetime
import hashlib
import io
import os
import re
import sys

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"


def cn2int(s):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    total = section = 0
    for ch in s:
        if ch in digits:
            section = digits[ch]
        elif ch in units:
            u = units[ch]
            if section == 0:
                section = 1
            total += section * u
            section = 0
        else:
            return None
    return total + section


def int2cn(n):
    """父章号转中文数字（100–999 全域输出中文，Q85 合规）。"""
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n - 10] if n > 10 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    s = d[n // 100] + "百"
    rest = n % 100
    if rest == 0:
        return s
    if rest < 10:
        return s + "零" + d[rest]
    if rest < 20:
        return s + "一十" + (d[rest - 10] if rest > 10 else "")
    return s + d[rest // 10] + "十" + (d[rest % 10] if rest % 10 else "")


def parse_chapters(txt):
    """双格式兼容地抽出所有父章号。"""
    nums = []
    for m in re.finditer(r"^## ([零一二三四五六七八九十百千\d]+)、", txt, re.M):
        v = cn2int(m.group(1))
        if v:
            nums.append(v)
    return nums


def main(argv=None):
    ap = argparse.ArgumentParser(description="追加台账新章节（动态取号）")
    ap.add_argument("--body-file", required=True, help="正文片段文件（含 {chap}/{nxt}/{now} 占位符）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要追加的内容，不写盘")
    args = ap.parse_args(argv)

    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()

    with io.open(REG, encoding="utf-8") as f:
        txt = f.read()
    nums = parse_chapters(txt)
    if not nums:
        print("❌ 台账里解析不到任何父章号，拒绝追加。")
        return 2

    # ── 幂等守卫：锚在**内容标记**上，不是锚在运行时章号上（2026-10-23 13:07 补装）──
    # 缺陷原委：原实现**完全没有**幂等守卫，只查「已有章号是否重复」；于是幂等复跑
    #   会**再追加一份逐字相同的块**（本次实测：12:0x 六段核销块被写入两次，
    #   台账 2,653,834 → 2,670,055 B）。这与台账 §104.10 登记过的缺陷同族：
    #   **存在性守卫必须锚在「内容标记」上** —— 锚在「运行时动态取到的编号」上恒不命中。
    # 判据：从正文里抽 `｜标记 \`XXX\`` 形式的标记；若台账已含该标记 ⇒ 判为已落盘，直接 NOOP。
    marks = re.findall(r"标记\s*`([^`]+)`", body)
    if marks:
        for mk in marks:
            if mk in txt:
                print(f"[IDEMPOTENT] 台账已含内容标记 `{mk}` ⇒ 本节此前已落盘；未改动台账。")
                return 0
        print(f"📌 本节内容标记：{marks}（台账中未命中 ⇒ 继续）")

    # ── 并发守卫：CAS（size+mtime+sha256 三锚），防止他岗在取号与写盘之间改动台账 ──
    snap_raw = open(REG, "rb").read()
    snap_sha = hashlib.sha256(snap_raw).hexdigest()
    snap_size = len(snap_raw)
    snap_mtime = os.path.getmtime(REG)

    nums = parse_chapters(txt)
    nxt = max(nums) + 1
    dup = [n for n in set(nums) if nums.count(n) > 1]
    if dup:
        print(f"❌ 台账存在重复章号 {sorted(dup)}，先修重复再追加（防撞号）。")
        return 2
    CH = int2cn(nxt)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sec = body.replace("{chap}", CH).replace("{nxt}", str(nxt)).replace("{now}", now)

    print(f"📌 当前最大章号 = {max(nums)}，本节占号 = {CH}（{nxt}）｜父章中文式 ✔")

    if args.dry_run:
        print("（--dry-run：未写盘）")
        print(sec)
        return 0

    # 并发守卫：写盘前 CAS（size+mtime+sha256 三锚）—— 他岗若在取号与写盘之间改动台账 ⇒ 中止
    cur_raw = open(REG, "rb").read()
    if (len(cur_raw) != snap_size
            or hashlib.sha256(cur_raw).hexdigest() != snap_sha
            or os.path.getmtime(REG) != snap_mtime):
        print("❌ 并发改动守卫触发（size/mtime/sha256 不一致）；未写盘，请重跑。")
        return 3

    with io.open(REG, "a", encoding="utf-8") as f:
        f.write(sec if sec.startswith("\n") else "\n" + sec)

    # 写后回读：标记命中恰 1（幂等守卫成立性自证）
    back = io.open(REG, encoding="utf-8").read()
    for mk in marks:
        assert back.count(mk) == 1, f"写后标记 {mk} 命中 {back.count(mk)} ≠ 1"
    print(f"✅ 已追加 §{CH}（{len(sec)} 字符），文件现 {os.path.getsize(REG)} B"
          + (f"｜写后回读：标记 {marks} 各命中 1" if marks else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
