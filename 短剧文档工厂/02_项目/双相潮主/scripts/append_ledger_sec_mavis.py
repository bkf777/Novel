#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_sec_mavis.py —— 分镜导演：**通用台账追加器**（v3 抗并发逻辑的通用版）

用法
----
    python3 scripts/append_ledger_sec_mavis.py --body-file <正文.md> --marker <幂等标记> [--dry-run]

正文文件里的占位符（渲染时替换）：
    {chap}  父章中文式（如「二百零七」）
    {nxt}   子章阿拉伯式（如「207」）
⚠️ 正文里若要**说明**占位符名称本身，一律写**双花括号**（{{chap}}）—— 渲染前会先转义，
   不会被替换命中（这是 12:4x 那次「写后计数异常」的真根因，见 v3 追加器 §206.4）。

沿用自 v3 的并发安全范式
----------------------
  · 动态取号（父章中文／子章阿拉伯，双格式兼容）＋ 重复章号即拒写
  · 写前 sha256 三锚 CAS ＋ 备份先行
  · **禁整文件回滚**（共享追加型台账上整文件还原的破坏面大于它要修的问题）：
    写后校验失败改为**定点摘除**（按前后分隔符精确裁剪，可逐字节还原）
  · 幂等重试 ＋ 延迟二次校验（抓「校验通过后又被并发重写抹掉」的晚到覆盖）
  · 自述章号一致性守卫（scripts/_ledger_selfchap_guard_mavis.py：A1 禁硬编码自身章号／A2 禁占位符残留）
"""
import hashlib
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ledger_selfchap_guard_mavis as G  # noqa: E402

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")
LOCK = os.path.join(ROOT, "reports", ".ledger_append.lock")
SENT_L, SENT_R = "\x00", "\x01"


def cn2int(s):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    d = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    u = {"十": 10, "百": 100, "千": 1000}
    total = sec = 0
    for ch in s:
        if ch in d:
            sec = d[ch]
        elif ch in u:
            x = u[ch]
            if sec == 0:
                sec = 1
            total += sec * x
            sec = 0
        else:
            return None
    return total + sec


def int2cn(n):
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
        return s + "一十" + d[rest - 10]
    return s + d[rest // 10] + "十" + (d[rest % 10] if rest % 10 else "")


def parse_chapters(txt):
    out = []
    for m in re.finditer(r"^## ([零一二三四五六七八九十百千\d]+)、", txt, re.M):
        v = cn2int(m.group(1))
        if v:
            out.append(v)
    return out


def snap():
    b = open(LEDGER, "rb").read()
    return b, hashlib.sha256(b).hexdigest(), len(b), os.path.getmtime(LEDGER)


def render(body_tpl, nxt, marker):
    chap = int2cn(nxt)
    esc = body_tpl.replace("{{", SENT_L).replace("}}", SENT_R)
    body = esc.replace("{chap}", chap).replace("{nxt}", str(nxt)).replace("{mark}", marker)
    body = body.replace(SENT_L, "{").replace(SENT_R, "}")
    return chap, body


def append_once(body):
    fd = os.open(LEDGER, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, body.encode("utf-8"))
    finally:
        os.close(fd)
    return open(LEDGER, "rb").read()


def strip_backticks(s):
    return re.sub(r"`[^`]*`", "", s)


def my_section(text, marker):
    """只取**本节**（本岗刚写的那一段）—— 写后检查的扫描范围必须与写入范围一致，
    否则他人章节里的合法字面量会被误判成「本节残留」。"""
    i = text.find(marker)
    if i < 0:
        return ""
    h = text.rfind("\n## ", 0, i)
    start = 0 if h < 0 else h
    nxt = text.find("\n## ", i)
    end = len(text) if nxt < 0 else nxt
    return text[start:end]


def excise(marker):
    b, sha, _, _ = snap()
    txt = b.decode("utf-8")
    if marker not in txt:
        return False, "本节已不存在（被并发者整段抹掉）"
    i = txt.index(marker)
    hdr = txt.rfind("\n## ", 0, i)
    nxt = txt.find("\n## ", i)
    start = 0 if hdr < 0 else hdr
    end = nxt if nxt > 0 else len(txt)
    block = txt[start:end]
    if marker not in block:
        return False, "定位块不含标记，放弃摘除"
    if hashlib.sha256(open(LEDGER, "rb").read()).hexdigest() != sha:
        return False, "CAS 不一致（并发者在摘除窗口内改了台账），放弃"
    tmp = LEDGER + ".tmp_excise"
    with open(tmp, "wb") as f:
        f.write((txt[:start] + txt[end:]).encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LEDGER)
    return True, "已定点摘除 %d B" % len(block.encode("utf-8"))


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    if "--body-file" not in argv or "--marker" not in argv:
        print("用法：append_ledger_sec_mavis.py --body-file <正文.md> --marker <幂等标记> [--dry-run]")
        return 2
    body_file = argv[argv.index("--body-file") + 1]
    marker = argv[argv.index("--marker") + 1]
    body_tpl = open(body_file, encoding="utf-8").read()

    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    import fcntl
    lf = open(LOCK, "w")
    fcntl.flock(lf, fcntl.LOCK_EX)
    try:
        b, sha, size, mtime = snap()
        txt = b.decode("utf-8")
        if marker in txt:
            print("[IDEMPOTENT] 台账已存在标记 %s；未改动台账。" % marker)
            return 0
        nums = parse_chapters(txt)
        if not nums:
            print("❌ 解析不到父章号；拒写。")
            return 2
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if dup:
            print("❌ 台账存在重复章号 %s；拒写。" % dup)
            return 2
        nxt = max(nums) + 1
        chap, body = render(body_tpl, nxt, marker)
        ok, msg = G.assert_self_chapno(template=body_tpl, rendered=body, chap_num=nxt)
        print("🛡️ 自述章号一致性守卫：%s" % msg)
        if not ok:
            print("❌ 中止；不写盘。")
            return 2
        scan = strip_backticks(body)
        if any(p in scan for p in ("{chap}", "{nxt}", "{now}", "{mark}")):
            print("❌ 写前预检：渲染后仍有未渲染占位符；中止。")
            return 2
        print("📌 当前最大章号 = %d｜本节占号 = §%s（%d）" % (max(nums), chap, nxt))
        if dry:
            print("（--dry-run：未写盘）")
            print(body[:1200])
            return 0

        bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_%s" % time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        shutil.copy2(LEDGER, os.path.join(bak_dir, "99_交付说明.md"))

        for attempt in range(1, 7):
            b2, sha2, size2, mtime2 = snap()
            t2 = b2.decode("utf-8")
            if marker in t2:
                print("[IDEMPOTENT] 第 %d 轮发现标记已存在；收工。" % attempt)
                return 0
            if attempt > 1:
                nums2 = parse_chapters(t2)
                dup2 = sorted({n for n in nums2 if nums2.count(n) > 1})
                if dup2:
                    print("❌ 第 %d 轮发现重复章号 %s；中止。" % (attempt, dup2))
                    return 2
                nxt = max(nums2) + 1
                chap, body = render(body_tpl, nxt, marker)
                ok, msg = G.assert_self_chapno(template=body_tpl, rendered=body, chap_num=nxt)
                if not ok:
                    print("❌ 第 %d 轮守卫不通过；中止。" % attempt)
                    return 2
            cur, cur_sha, cur_size, cur_mtime = snap()
            if (cur_size != size2 or cur_mtime != mtime2 or cur_sha != sha2):
                print("⚠️ 第 %d 轮 CAS 不一致；重取快照重试。" % attempt)
                continue
            back = append_once(body)
            cnt = back.count(marker.encode("utf-8"))
            sc = strip_backticks(my_section(back.decode("utf-8"), marker))   # ← 只扫本节
            ph = any(p in sc for p in ("{chap}", "{nxt}", "{now}", "{mark}"))
            print("🔍 第 %d 轮写后回读：size=%d B（%+d）｜标记计数=%d｜占位符残留=%s"
                  % (attempt, len(back), len(back) - size2, cnt, ph))
            if cnt == 1 and not ph:
                time.sleep(1.5)
                b3 = open(LEDGER, "rb").read()
                c3 = b3.count(marker.encode("utf-8"))
                p3 = any(p in strip_backticks(my_section(b3.decode("utf-8"), marker))
                         for p in ("{chap}", "{nxt}", "{now}", "{mark}"))
                if c3 == 1 and not p3:
                    print("✅ 已追加 §%s（%d 字符）｜文件现 %d B（%+d）"
                          % (chap, len(body), len(b3), len(b3) - size2))
                    return 0
                print("⚠️ 第 %d 轮延迟二次校验失败（计数=%d 残留=%s）⇒ 定点摘除后重试。" % (attempt, c3, p3))
                print("   定点摘除：%s" % excise(marker)[1])
                continue
            if cnt > 1:
                print("⚠️ 第 %d 轮标记计数=%d（重复件）⇒ 定点摘除。" % (attempt, cnt))
                print("   定点摘除：%s" % excise(marker)[1])
                continue
            print("⚠️ 第 %d 轮标记计数=0 ⇒ 被并发者整文件重写抹掉；不还原备份（还原会反向抹掉对方新章节），重试。" % attempt)
        print("❌ 重试 6 轮仍未落盘；台账未被本岗改动，如实上报。")
        return 5
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
        lf.close()


if __name__ == "__main__":
    sys.exit(main())
