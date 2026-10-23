#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_chapno_correction_mavis.py —— 分镜导演：**Q30 追加式订正本岗 10:0x 回执的自述章号**
                                       ＋ 落实「自述章号一致性断言」加固（v3）

来件
----
视觉设定岗 2026-10-23 10:3x 来函（**本岗按现盘实测复核后成立**）：
本岗 10:0x 的回执称核销已「补记入本岗台账 **§一百四十一**（§141.1 你的 C-131／C-105 回条核销表／
§141.2 出口闸与边界）」—— 现盘实测：
  · **§一百四十一 ＝ 台本编剧**（「故事架构迟到件核销…2026-10-23 10:02」）；
  · 本岗该节**实为 §一百四十二**（「## 一百四十二、分镜导演（2026-10-23 10:0x–10:1x）」），
    小节为 **142.1**（C-131／C-105 回条核销表）、142.2（D18 v1.100 指针复核）、
    142.3（幂等不能用章号·已修）、**142.4**（出口闸与边界）。
⇒ **内容全部在位，仅自述编号指向了同刻并发写入的台本编剧 §141。**

成因（贵岗给出、本岗接受，不追责，供留痕）
------------------------------------------
本岗 10:0x 落 §140 后做幂等复跑，脚本因「幂等按章号判定」的缺陷又追加了 **§141**（与 §140 逐字相同），
本岗随后回滚删除 —— 回执自述里的「§141」正是那次**已被回滚的重复件**；
真正的新章节因并发取号落在 **§142**，回执沿用了已被回滚的中间态编号。

处置（Q30 追加式订正：**不改写已落章节正文、不动他人章节**）
-----------------------------------------------------------
**新起一节**登记订正；已落的 §142 正文与台本编剧 §141 均**一字未动**。

加固（贵岗建议③，本轮已落实）
------------------------------
台账追加脚本加「自述章号一致性断言」（fail-loud）：共用模块 `scripts/_ledger_selfchap_guard_mavis.py` ——
  A1 模板正文若硬编码了**等于本节取到号**的 `§<数字>` ⇒ 中止（这正是 10:0x 那类指错的成因）；
  A2 渲染后正文若残留 `{chap}/{nxt}/{now}/{mark}` 任一占位符 ⇒ 中止；
  （跨岗引用他节号不受限 —— 只拦「等于自己那一节」的情形，不误伤正当的互引。）

v3 变更（2026-10-23 12:4x：v1/v2 连续失败的**真根因**）
-------------------------------------------------------
v1 实跑两次、v2 实跑六轮，均以「写后校验不通过」收场。**首次判定疑为并发者的整文件重写（lost-update），
经 v2 加诊断后证伪 —— 真根因是本岗模板自身的 bug**：

  · 本节模板正文里，为了说明守卫规则，**引用了占位符名称本身**（写在反引号内）；
  · 而渲染用的是**朴素 `.replace()`** ⇒ **说明文字里的那个占位符名也被替换成了真值**
    ⇒ 渲染后标记出现 **2 次** ⇒ v1 的 `count != 1` 判失败 ⇒ 触发整文件回滚；
  · 同理，说明文字里的另外两个占位符名在 **v2 追加器自带的写后检查**（未剔除反引号片段）里
    被误判为「占位符残留」⇒ v2 第 1~6 轮全部在「追加 → 误判 → 定点摘除」间空转（台账正文零损伤，
    仅末尾累积 6 个多余换行，已由 `scripts/fix_ledger_trailing_newlines_mavis.py` 收敛）。

⇒ v3 三处改造：
  ① **模板侧**：说明文字里的占位符名改用 **双花括号转义**（`{{chap}}`）；渲染前 `{{`→哨兵、`}}`→哨兵，
     渲染后再还原 ⇒ **说明文字不会被 `.replace()` 命中**，真占位符仍照常替换。
  ② **检查侧**：写后「占位符残留」检查**复用守卫模块的反引号剔除口径**（守卫 A2 本来就这么做，
     是追加器自己漏了）⇒ 说明文字不再误判。
  ③ **回滚侧**：**禁整文件还原** —— 共享追加型台账上 `copy2(备份, 台账)` 的破坏面大于它要修的问题
     （会把「我被覆盖」反转成「我用旧备份覆盖掉并发者的新章节」）；改为**定点摘除**
     （按「前一节分隔符 + 本节 + 后一节分隔符」精确裁剪，可逐字节还原）＋ 幂等重试 ＋ 延迟二次校验。

治理沿用本岗并发安全范式：动态取号（父章中文/子章阿拉伯，双格式兼容）＋ 标记幂等
＋ 写前 sha256 三锚 CAS ＋ 备份先行 ＋ 写后回读校验 ＋ 失败自动定点摘除。
用法：python3 scripts/append_ledger_chapno_correction_mavis.py [--dry-run] [--max-attempts N]
"""
import hashlib
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ledger_selfchap_guard_mavis as G  # noqa: E402  （本模块只定义函数、无顶层副作用）

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")
MARK = "TBZ-12-4x-自述章号订正-§142-2026-10-23"
LOCK = os.path.join(ROOT, "reports", ".ledger_append.lock")

# v3：说明文字里的占位符名一律写成双花括号，渲染时先转义再替换，避免被朴素 replace 命中
SENT_L, SENT_R = "\x00", "\x01"


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
    nums = []
    for m in re.finditer(r"^## ([零一二三四五六七八九十百千\d]+)、", txt, re.M):
        v = cn2int(m.group(1))
        if v:
            nums.append(v)
    return nums


BODY = r"""
## {chap}、分镜导演（2026-10-23 12:4x：⭐ **Q30 追加式订正本岗 10:0x 回执的自述章号** —— 自述「§一百四十一／§141.1／§141.2」**作废**，正确为 **§一百四十二／§142.1／§142.4**；内容全部在位、已落章节正文与他人章节**一字未动** ＋ 落实「**自述章号一致性断言**」加固（fail-loud））｜标记 `{mark}`

> **一句话**：视觉设定岗来函指出本岗 10:0x 回执的自述章号指错；本岗**按现盘实测复核后成立**，本节按 **Q30 追加式订正**登记该订正（不改已落正文、不动他人章节），并已把贵岗建议的通用防线做进台账追加脚本。

### {nxt}.1 订正对象与现盘实测
- **本岗 10:0x 回执的自述**（原文）：「核销已补记入本岗台账 **§一百四十一**（§141.1 你的 C-131／C-105 回条核销表／§141.2 出口闸与边界）」。
- **现盘实测（12:4x）**：
  · `## 一百四十一、台本编剧：故事架构迟到件核销（Q42 三分类）…（2026-10-23 10:02）` ⇒ **§141 属台本编剧**，非本岗；
  · `## 一百四十二、分镜导演（2026-10-23 10:0x–10:1x）` ⇒ **本岗该节实为 §142**，小节：
    **142.1** 视觉设定岗 C-131／C-105 回条核销（4/4 独立复现成立 ✅）｜142.2 D18 v1.100 指针复核｜
    142.3 本岗台账脚本的自查订正（幂等不能用章号·已修）｜**142.4** 出口闸与边界。
- **结论**：**内容全部在位**，仅**自述编号**指向了同刻并发写入的台本编剧 §141；本岗该节正文与台本编剧 §141 正文**均一字未动**（Q30 追加式订正，不改写已落章节正文、不动他人章节）。

### {nxt}.2 成因（贵岗给出，本岗接受，不追责，供留痕）
- 本岗 10:0x 落 §140 后做幂等复跑，脚本因「**幂等按章号判定**」的缺陷又追加了 **§141**（与 §140 逐字相同），本岗随后**回滚删除**；
- 回执自述里的「§141」正是那次**已被回滚的重复件**；真正的新章节因并发取号落在 **§142**，回执沿用了这个**已被回滚的中间态编号**。
- 本岗 §142.3 已记该缺陷（「幂等不能用章号」）并已修；本次补上**第二层防线**（见下节）。

### {nxt}.3 ⭐ 加固：台账追加脚本的「自述章号一致性断言」（已落实，fail-loud）
- **共用守卫模块**：`scripts/_ledger_selfchap_guard_mavis.py`（本模块**只定义函数、无顶层副作用**，可安全 import）。
  · **A1 自述章号不得硬编码**：模板正文若出现 `§<数字>` 且该数字**等于本次实际取到的章号**
    ⇒ 判为「硬编码了自身章号」（**正是 10:0x 那次指错的成因**）⇒ **中止，不写盘**。
    正确写法：正文里凡是自称本节，一律用占位符（父章中文式／子章阿拉伯式，见下）。
    ⚠️ **跨岗引用他节号不受限**（互引他节号是正当用途，如「台账 §150」）⇒ 只拦「等于自己那一节」的情形，**不误伤**。
  · **A2 占位符必须全部渲染**：渲染后正文若仍残留 `{{chap}}`／`{{nxt}}`／`{{now}}`／`{{mark}}` 任一 ⇒ **中止**（否则章号会渲染成字面量）。
- **本节自身的落地**：本节正文里的父章号＝占位符、子节号＝占位符，**零硬编码** ⇒ A1/A2 均通过（机械守卫在写盘前已跑）。
- **对外回执侧的配套纪律**：本岗此后**凡在回执中引用本岗台账节号，一律先实测当前节号再写**，不凭记忆写数字（这是本次唯一真正的根因面：**回执文本不受脚本守卫覆盖**）。

### {nxt}.4 ⭐ 追加器 v3：真根因＝「占位符语法」与「说明文字」**同形** ⇒ 双重替换（本轮新增）
- **v1 实跑两次、v2 实跑六轮，均以「写后校验不通过」收场**。首次判定疑为并发者的整文件重写（lost-update），
  **经 v2 加诊断后证伪 —— 真根因是本岗模板自身的 bug**：
  · 本节模板正文里，为了说明守卫规则，**引用了占位符名称本身**（写在反引号内）；
  · 而渲染用的是**朴素 `.replace()`** ⇒ **说明文字里的那个占位符名也被替换成了真值** ⇒ 渲染后标记出现 **2 次**
    ⇒ v1 的 `count != 1` 判失败 ⇒ 触发整文件回滚；
  · 同理，说明文字里的另两个占位符名在 **v2 追加器自带的写后检查**（未剔除反引号片段）里被误判为「占位符残留」
    ⇒ v2 第 1~6 轮全部在「追加 → 误判 → 定点摘除」间空转（**台账正文零损伤**，仅末尾累积 6 个多余换行，
      已由 `scripts/fix_ledger_trailing_newlines_mavis.py` 收敛为 1 个）。
- **修法（三处）**：
  ① **模板侧**：说明文字里的占位符名改用 **双花括号转义**；渲染前 `{{`→哨兵、`}}`→哨兵，渲染后再还原
     ⇒ **说明文字不会被 `.replace()` 命中**，真占位符仍照常替换；
  ② **检查侧**：写后「占位符残留」检查**复用守卫模块的反引号剔除口径**（守卫 A2 本来就是这么做，是追加器自己漏了）
     ⇒ 说明文字不再误判；
  ③ **回滚侧**：**禁整文件还原** —— 共享追加型台账上 `copy2(备份, 台账)` 的破坏面大于它要修的问题
     （会把「我被覆盖」反转成「我用旧备份覆盖掉并发者的新章节」）；改为**定点摘除**
     （按「前一节分隔符 ＋ 本节 ＋ 后一节分隔符」精确裁剪，可逐字节还原）＋ 幂等重试 ＋ 延迟二次校验。
- **可复用结论（跨岗适用）**：
  · **模板占位符与「说明占位符怎么用」的文字必须不同形** —— 否则朴素替换会连说明文字一起替换掉，
    且**失败方式极具迷惑性**（看起来像并发冲突，实则是自伤）⇒ 模板里凡引用占位符名称，一律双花括号转义。
  · **写后校验必须与前置守卫用同一套「反引号剔除」口径** —— 两端口径不一致时，后置校验会把前置放过的合法文本判成错误。
  · **共享追加型交付台账上的回滚，一律不得整文件还原** ⇒ 正确形态是「定点摘除 ＋ 幂等重试 ＋ 延迟二次校验」。

### {nxt}.5 边界
- 本节**只做订正登记**，未改写任何已落章节正文、未动台本编剧 §141 与 §143 等他人章节；未改任何交付物 JSON；
  未改 `03_规格/*`、`04_工具/*`；未生成图片/视频/音频；未合成 TTS/BGM；未提交 H3 付费生成；未投流上架。
- 本岗新增脚本：`scripts/_ledger_selfchap_guard_mavis.py`（共用守卫模块）｜`scripts/append_ledger_chapno_correction_mavis.py`（本节，v3）｜
  `scripts/fix_ledger_trailing_newlines_mavis.py`（末尾换行收敛，os.replace 原子替换）。
"""


def _snapshot():
    b = open(LEDGER, "rb").read()
    return b, hashlib.sha256(b).hexdigest(), len(b), os.path.getmtime(LEDGER)


def _render(nxt):
    chap = int2cn(nxt)
    esc = BODY.replace("{{", SENT_L).replace("}}", SENT_R)   # 先转义说明文字里的双花括号
    body = esc.replace("{chap}", chap).replace("{nxt}", str(nxt)).replace("{mark}", MARK)
    body = body.replace(SENT_L, "{").replace(SENT_R, "}")
    return chap, body


def _append_once(body):
    """O_APPEND 单次 write（原子追加），返回写后字节。"""
    data = body.encode("utf-8")
    fd = os.open(LEDGER, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return open(LEDGER, "rb").read()


def _strip_backticks(s):
    """与守卫模块 A2 同口径：剔除反引号片段后再查占位符残留。"""
    return re.sub(r"`[^`]*`", "", s)


def _excise(body):
    """定点摘除本节（含前后分隔符 ⇒ 可逐字节还原），sha256 CAS 保证不误伤他人内容。"""
    snap, snap_sha, _, _ = _snapshot()
    txt = snap.decode("utf-8")
    if MARK not in txt:
        return False, "本节已不存在（被并发者整段抹掉）"
    idx = txt.index(MARK)
    hdr = txt.rfind("\n## ", 0, idx)          # 本节标题前的分隔换行
    nxt_hdr = txt.find("\n## ", idx)          # 下一节标题前的分隔换行
    if hdr < 0:
        start, end = 0, (nxt_hdr if nxt_hdr > 0 else len(txt))
    else:
        start = hdr
        end = (nxt_hdr if nxt_hdr > 0 else len(txt))
    block = txt[start:end]
    if MARK not in block:
        return False, "定位到的块不含标记，放弃摘除（宁可不摘也不误伤）"
    new = txt[:start] + txt[end:]
    nb = new.encode("utf-8")
    cur = open(LEDGER, "rb").read()
    if hashlib.sha256(cur).hexdigest() != snap_sha:
        return False, "CAS 不一致（并发者在摘除窗口内改了台账），放弃"
    tmp = LEDGER + ".tmp_excise"
    with open(tmp, "wb") as f:
        f.write(nb)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LEDGER)   # 原子替换，不产生截断窗口
    return True, "已定点摘除 %d B（逐字节还原口径）" % len(block.encode("utf-8"))


def main():
    dry = "--dry-run" in sys.argv
    max_attempts = 6
    for i, a in enumerate(sys.argv):
        if a == "--max-attempts" and i + 1 < len(sys.argv):
            max_attempts = int(sys.argv[i + 1])

    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    import fcntl
    lf = open(LOCK, "w")
    fcntl.flock(lf, fcntl.LOCK_EX)

    try:
        snap, snap_sha, snap_size, snap_mtime = _snapshot()
        txt = snap.decode("utf-8")
        if MARK in txt:
            print("[IDEMPOTENT] 台账已存在标记 %s；未改动台账。" % MARK)
            return 0

        nums = parse_chapters(txt)
        if not nums:
            print("❌ 解析不到任何父章号；拒绝追加。")
            return 2
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if dup:
            print("❌ 台账存在重复章号 %s；拒绝追加（防撞号）。" % dup)
            return 2
        nxt = max(nums) + 1
        chap, body = _render(nxt)

        ok, msg = G.assert_self_chapno(template=BODY, rendered=body, chap_num=nxt)
        print("🛡️ 自述章号一致性守卫：%s" % msg)
        if not ok:
            print("❌ 中止；不写盘。")
            return 2
        # 追加器自身的写前预检：与守卫同口径（剔除反引号）
        pre_scan = _strip_backticks(body)
        if any(p in pre_scan for p in ("{chap}", "{nxt}", "{now}", "{mark}")):
            print("❌ 写前预检：渲染后仍有未渲染占位符；中止。")
            return 2
        print("🔍 写前预检：渲染体 MARK 计数=%d（应为 1）" % body.count(MARK))

        print("📌 当前最大章号 = %d｜本节占号 = §%s（%d）" % (max(nums), chap, nxt))
        if dry:
            print("（--dry-run：未写盘）")
            print(body[:900])
            return 0

        bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_%s" % time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bak_dir, exist_ok=True)
        bak = os.path.join(bak_dir, "99_交付说明.md")
        shutil.copy2(LEDGER, bak)
        print("📦 备份先行 → %s" % os.path.relpath(bak, ROOT))

        for attempt in range(1, max_attempts + 1):
            snap2, snap2_sha, snap2_size, snap2_mtime = _snapshot()
            t2 = snap2.decode("utf-8")
            if MARK in t2:
                print("[IDEMPOTENT] 第 %d 轮发现标记已存在（并发实例或上一轮成功）⇒ 收工。" % attempt)
                return 0
            if attempt > 1:
                nums2 = parse_chapters(t2)
                dup2 = sorted({n for n in nums2 if nums2.count(n) > 1})
                if dup2:
                    print("❌ 第 %d 轮发现台账重复章号 %s；中止。" % (attempt, dup2))
                    return 2
                nxt = max(nums2) + 1
                chap, body = _render(nxt)
                ok, msg = G.assert_self_chapno(template=BODY, rendered=body, chap_num=nxt)
                if not ok:
                    print("❌ 第 %d 轮守卫不通过：%s；中止。" % (attempt, msg))
                    return 2

            cur, cur_sha, cur_size, cur_mtime = _snapshot()
            if (cur_size != snap2_size or cur_mtime != snap2_mtime or cur_sha != snap2_sha):
                print("⚠️ 第 %d 轮 CAS 不一致（并发者在取号后改动）⇒ 重取快照重试。" % attempt)
                continue

            back = _append_once(body)
            cnt = back.count(MARK.encode("utf-8"))
            scan = _strip_backticks(back.decode("utf-8"))
            has_ph = any(p in scan for p in ("{chap}", "{nxt}", "{now}", "{mark}"))
            print("🔍 第 %d 轮写后回读：size=%d B（%+d）｜MARK 计数=%d｜占位符残留=%s"
                  % (attempt, len(back), len(back) - snap2_size, cnt, has_ph))

            if cnt == 1 and not has_ph:
                time.sleep(1.5)
                back2 = open(LEDGER, "rb").read()
                scan2 = _strip_backticks(back2.decode("utf-8"))
                cnt2 = back2.count(MARK.encode("utf-8"))
                ph2 = any(p in scan2 for p in ("{chap}", "{nxt}", "{now}", "{mark}"))
                if cnt2 == 1 and not ph2:
                    print("✅ 已追加 §%s（%d 字符）｜文件现 %d B（%+d）｜延迟二次校验通过（计数 1、占位符 0）"
                          % (chap, len(body), len(back2), len(back2) - snap2_size))
                    return 0
                print("⚠️ 第 %d 轮延迟二次校验失败（计数=%d、占位符残留=%s）⇒ 定点摘除后重试。" % (attempt, cnt2, ph2))
                okx, infox = _excise(body)
                print("   定点摘除：%s" % infox)
                continue

            if cnt > 1:
                print("⚠️ 第 %d 轮 MARK 计数=%d（>1，重复件）⇒ 定点摘除多余副本。" % (attempt, cnt))
                okx, infox = _excise(body)
                print("   定点摘除：%s" % infox)
                continue

            print("⚠️ 第 %d 轮 MARK 计数=0 ⇒ 本节被并发者的整文件重写抹掉（lost-update）。"
                  "不还原备份（还原会反向抹掉对方新章节），进入重试。" % attempt)

        print("❌ 重试 %d 轮仍未落盘；台账未被本岗改动，如实上报。" % max_attempts)
        return 5
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
        lf.close()


if __name__ == "__main__":
    sys.exit(main())
