#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
append_ledger_d11u02_srcsync_mavis.py —— 分镜导演：**D11 U02 生成器内容源同步（脚本 v1.6 → v1.9）**
                                     ＋ 覆盖轴守恒 29/31 → 31/31 ＋ note header 三形态建模
                                     ＋ 写盘末尾换行缺陷修复 ＋ 守卫四件套实测

⚠️ 治理（沿用本岗 12:05 并发安全范式）：
   ① **动态取号**（父章中文数字／子章阿拉伯数字，双格式兼容解析，防撞号）；
   ② **标记幂等**（幂等守卫锚在内容标记 MARK 上，**不是**动态编号）；
   ③ **写前并发守卫**（size/mtime/sha256 三锚 CAS，读后被他人改动即中止，不写盘）；
   ④ **写后回读校验**＋失败自动回滚（备份在 reports/_bak_*）。

用法：python3 scripts/append_ledger_d11u02_srcsync_mavis.py [--dry-run]
"""
import hashlib
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ledger_selfchap_guard_mavis as G  # noqa: E402  （只定义函数、无顶层副作用）

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
LEDGER = os.path.join(ROOT, "99_交付说明.md")
MARK = "TBZ-12-1x-D11U02内容源同步-守卫四件套-2026-10-23"


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
## {chap}、分镜导演（2026-10-23 12:0x–12:2x：⭐ **D11 U02 生成器内容源全量同步（脚本 v1.6 → v1.9）** —— 覆盖轴守恒由 29/31 补齐为 **31/31** ＋ note header **三形态建模** ＋ ⭐ 写盘**末尾换行缺陷**修复 ＋ 守卫四件套全过 ＋ **交付物零改动**）｜标记 `{mark}`

> **一句话**：D11 U02 的**唯一生成器** `scripts/build_D11_U02.py` 长期落后于盘上（脚本 v1.6 vs 盘上 v1.9），本轮把盘上三次演进（v1.7 黄金 3 秒改版／v1.8 黄金 3 秒落盘／v1.9 引文同步）**全量回填进内容源**，使 `--check` 0 差异、产物与盘上**逐字节一致**；**因内容已一致，未重写交付物**（交付物 sha/mtime 零变动）。

### {nxt}.1 现状取证（以实盘为准，不采信先前摘要）
- **脚本**：`scripts/build_D11_U02.py` ＝ **v1.6**（源内 `VERSION`）｜70,324 B｜sha `7edf610e8450…`｜mtime 07:11:46。
  ⚠️ 先前摘要记「脚本 v1.7」与现盘不符 ⇒ **一律以现盘复跑为准**。
- **盘上交付物**：`units/U02/D11.json` ＝ **v1.9**｜59,191 B｜sha `b8a156ea05a2beb04a5239a91743e5b8a95a1c69a7988108c071598028c4d67f`｜mtime **11:32:48**。
  落盘方＝**并行分镜导演实例**（其 11:28 落 `patch_D11_golden3s_dialogue.py`、11:32 落 `patch_D11_si_quote_sync.py`），本岗**不夺回、不二次改写**其业务内容。
- **他岗现值**：D08 U02 v1.7（37,386 B）｜D09 U02 v1.3｜D05 v1.7｜D10 v1.9。
- **判据脚本真相**：`check_D08_D11_shotintent.mjs` 以 `BODYREF = /body\[(\d+)\]/g` 定位（**不按 header 文本匹配**）⇒ 盘上多种 header 形态不影响覆盖核验。

### {nxt}.2 ⭐ 全量差异探针（自建，不受 A36 的 8 条上限约束）
- A36 漂移守卫的 `_diff` 只印前 8 条且截断 ⇒ 本轮**另建递归 walk 探针**（沙箱取产物 → 与盘上逐字段比对），实测**全量差异 9 条**：
  `dialogue` 2（ep012 镜1 缺 `陆沉「贡献是谁定的。」／` 前缀；ep016 镜1 缺 `陆沉「十四天 tonight。」`）／`note` 5／`visual_facts` 1（ep014 镜3 缺「先滚过，」）／`version` 1（产物 v1.6 vs 盘上 v1.9）。
- **根因（守恒法定位）**：D08 U02 v1.7 现行 `shot_intent` 共 **31** 条，而源侧 `cover` 仅 **29** 条 ⇒ **源漏承接 ep012 `body[1]` 与 ep016 `body[1]`** 两条（正是上游新增的两句黄金 3 秒首句）⇒ 引文索引整段错位。
  守恒法＝「D08 现行 SI 索引集合 ⇄ D11 note 声明的 `body[N]` 集合」逐集求差，可同时检出「源漏承接／盘上漏承接／越权承接」三类。
- ⚠️ **判据正则分支覆盖必须自证**：首次守恒脚本只匹配 `D08 v1.5` 一支，误报「未承接 28 条」；改为 `📌 D08(?: (v[\d.]+))? shot_intent 反查（…）：body\[(\d+)\]` 后得 **31/31**。

### {nxt}.3 ⭐ note header **三形态**建模（生成器原表达力不足的破解）
盘上 `note` 实存 **3 种** header 形态，而生成器原只产 1 种（`📌 D08 shot_intent 反查（2026-10-23）`）：
1. **标准式**（29 条）＝ `📌 D08 shot_intent 反查（2026-10-23）：body[N] 要求「…」；本镜 visual_facts 已正面拍到（锚点：…）。`
2. **v1.5 版式**（ep012 镜1 内第 2 段）＝ header 带 D08 版本前缀 —— 系 v1.8 落盘时**随带产生**的历史形态。
3. **黄金 3 秒改版式**（ep012 镜1／ep016 镜1 各 1 条）＝ header 加副标「· 黄金 3 秒改版」＋尾句改为「第 0 帧即…」＋**画外音处置**（陆沉不在画幅内 ⇒ D12 不得写进 image_prompt、D15 按画外音处理）。

**改法（内容源侧建模，不改盘）**：把 `cover` 项由固定 2 元组扩为 **2／3／4 元组** ——
`2`＝标准式；`3`＝第 3 项为自定义 header；`4`＝第 3 项为自定义 header、第 4 项为自定义尾句（尾句内 `{anchors}` 占位符替换为锚点串）。
⇒ 样式**随 cover 项同行携带**，不另建样式表 ⇒ 无「样式表键随 body 重排而失效」的额外漂移面。

### {nxt}.4 改内容源（9 处 · Q40 改源不改盘）
| # | 位置 | 改动 |
|---|---|---|
| 1 | `VERSION` | `v1.6` → **`v1.9`**（与盘上对齐；`DECLARED_CHANGES` 版本项同步改为 `v1.8`→`v1.9`，走「已应用即跳过」分支） |
| 2 | ep012 镜1 `dialogue` | 前置 `陆沉「贡献是谁定的。」／` |
| 3 | ep012 镜1 `cover` | `(2,…)` → `(1,…)`（黄金 3 秒形态 ＋ 4 元组）＋ 新增 `(3,…)`（v1.5 header） |
| 4 | ep012 镜2 `cover` | `(6,…)` → `(7,…)` |
| 5 | ep012 镜4 `cover` | `(10,…)` → `(11,…)` |
| 6 | ep014 镜3 `visual_facts` | 补回 D08 `body[3]` 的过程动作「先滚过，」（覆盖度缺口修正，不新建契约） |
| 7 | ep016 镜1 `dialogue` | `""` → `陆沉「十四天，今晚到。」` |
| 8 | ep016 镜1 `cover` | `(0,…)` → `(0,…)` ＋ 新增 `(1,…)`（黄金 3 秒形态 ＋ 4 元组） |
| 9 | ep016 镜4 `cover` | `(8)/(11)/(12)` → `(9)/(12)/(13)` |

- **断言点数未变**（`src.count("chk(")-1 == 39 == len(ASSERT_MANIFEST)`）⇒ **Q56 ③ 清单无需改**（未新增／删除断言点）。
- ⚠️ `DECLARED_CHANGES` 只支持「同一路径内旧值→新值**子串替换**」，**不支持结构性增量**（新增一条 `body[N]` 反查段）⇒ 故本轮以**源侧 cover/模板改造为主**，使产物**直接等于**盘上，而非靠声明差异蒙混。

### {nxt}.5 ⭐ 附带修复：写盘**末尾换行**缺陷（1 字节差）
- 现象：脚本落盘产物 **59,190 B** vs 盘上 **59,191 B** ⇒ 差 **1 字节**。
- 根因：脚本写盘用 `json.dump(...)` **不追加**末尾 `\n`；而盘上 D11 由 patch 脚本的 `dump()` 写入，**带**末尾 `\n`（实测：D11 U01/U02 末字节 `0a`，D08/D09/D10 末字节 `7d` —— 逐文件格式不同，非全库统一约定）。
- 后果：任何一次落盘都会**抹掉盘上末字节** ⇒ A36 判内容一致但**字节不一致**（违 Q80「同一版本号不得对应两个字节态」）。
- 修复：写盘处补 `f.write("\n")`，使「脚本落盘产物 == 盘上交付物」**逐字节**成立。

### {nxt}.6 验收四件套（守卫实跑，非纸面条款）
1. **正向（沙箱）**：`python3 scripts/build_D11_U02.py --check` → **EXIT 0**｜39 条断言全过｜覆盖轴 **31/31**｜台词轴 **30/30**（受检 D11 对白 30 条 / D09 台词 30 条）。
2. **独立比对（不只信 A36）**：沙箱取产物 → 与盘上 **json 结构全等 = True**、**序列化文本逐字全等 = True**、**sha 相同 = `b8a156ea05a2beb0`**、**逐字段差异 0 条**。
3. **逐字节落盘（沙箱）**：沙箱实跑落盘 → 59,191 B｜`cmp` 与真盘交付物**逐字节完全一致**；**幂等**：连续两轮落盘 sha 相同（`b5173189…` → `b5173189…`）⇒ 字节稳定。
4. **负测（沙箱副本，禁动真盘）**：篡改沙箱盘上 `ep016 镜1 dialogue` → `--check` **EXIT 1**，A36 精确报出 `.episodes[7].shots[0].dialogue: 产物=… 盘上=…` ⇒ 守卫有区分力（Q67）。
5. **真盘**：`--check` **EXIT 0**；交付物 **sha `b8a156ea05a2beb0…` / 59,191 B / mtime 11:32 全部未变** ⇒ **零改动交付物**（不消耗版本号、不引发无谓 mtime 变动）。

### {nxt}.7 判据与出口闸（当场实跑，贴受检条数）
- `node scripts/check_D08_D11_shotintent.mjs --unit U02` → **EXIT 0**｜受检 shot_intent **31 条**（D08 v1.7 / D11 v1.9）｜**31/31 零硬冲突**（本轮前为 29/29 ⇒ 增量即本轮补齐的两条漏承接）。
- 出口硬闸（`cmd > log 2>&1; echo $?`，不经管道）：U01 **exit 1**（error 27 / warning 2）、U02 **exit 1**（error 28 / warning 4）。
  ⚠️ **全部 error 集中在 V12「白模构图一致性（D11 景别 ↔ 投影占幅）」**（W1 角色不在画幅 / W2 主体占幅越界 / W3 主体让位给环境），其余 **11 条规则全 PASS**。
  **与本轮无关的证明**：本轮**零交付物字节变动**（交付物 sha/mtime 未变，`units/` 内 12:00 后被改的 10 份文件全部是**并行实例**与**他岗**产物，且不含本岗目标文件 `units/U02/D11.json`）；且 V12 失败项含 ep09/ep10/ep11/ep13/ep15 等**本轮从未触碰**的镜位 ⇒ V12 属**已知未收口项**（白模未按新景别重建 ＋ W3 判据缺陷），待 U03 开工前收口。

### {nxt}.8 边界与未结项
- 本轮**只改** `scripts/build_D11_U02.py`（本岗脚本）；**未改任何交付物 JSON**；未改 `03_规格/*`、`04_工具/*`；未生成图片/视频/音频；未合成 TTS/BGM；未提交 H3 付费生成；未投流上架。
- **未结项（承前）**：① 并行实例仍在写同一批文件（12:0x 又写 D11 U01 v1.14／D16 U01 v1.21／D15 U01 v1.13 等）⇒ 任何真盘写操作前必须重查盘面；② 单写点实例归属待企划合规裁定；③ V12 白模重建与 W3 判据三选一待裁定；④ U03 开工前须收口 camera_angle 闭枚举 vs note 真源二择一。
"""


def main():
    dry = "--dry-run" in sys.argv
    snap = open(LEDGER, "rb").read()
    snap_sha = hashlib.sha256(snap).hexdigest()
    snap_size = len(snap)
    snap_mtime = os.path.getmtime(LEDGER)
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
    chap = int2cn(nxt)
    now = time.strftime("%Y-%m-%d %H:%M")
    body = BODY.replace("{chap}", chap).replace("{nxt}", str(nxt)).replace("{now}", now).replace("{mark}", MARK)
    body = body.rstrip("\n") + "\n"

    # 🛡️ 自述章号一致性守卫（A1 禁硬编码自身章号／A2 禁占位符残留）—— fail-loud
    ok, gmsg = G.assert_self_chapno(template=BODY, rendered=body, chap_num=nxt)
    print("🛡️ %s" % gmsg)
    if not ok:
        print("❌ 中止；不写盘。")
        return 2

    print("📌 当前最大章号 = %d｜本节占号 = §%s（%d）｜父章中文式 ✔" % (max(nums), chap, nxt))
    if dry:
        print("（--dry-run：未写盘）")
        print(body)
        return 0

    # 写前并发守卫：size/mtime/sha256 三锚 CAS
    cur = open(LEDGER, "rb").read()
    if (len(cur) != snap_size or os.path.getmtime(LEDGER) != snap_mtime
            or hashlib.sha256(cur).hexdigest() != snap_sha):
        print("[ABORT] 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")
        return 3

    bak_dir = os.path.join(ROOT, "reports", "_bak_ledger_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, "99_交付说明.md")
    shutil.copy2(LEDGER, bak)

    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(body if body.startswith("\n") else "\n" + body)

    back = open(LEDGER, "rb").read()
    if back.count(MARK.encode("utf-8")) != 1:
        shutil.copy2(bak, LEDGER)
        print("[ROLLBACK] 写后标记计数异常，已回滚。")
        return 4
    print("✅ 已追加 §%s（%d 字符）｜文件现 %d B（%+d）｜备份 %s"
          % (chap, len(body), os.path.getsize(LEDGER), os.path.getsize(LEDGER) - snap_size,
             os.path.relpath(bak, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
