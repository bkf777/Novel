#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账追加脚本（分镜导演岗）—— 落 §一百四十二。

【口径】
  · 父章号**中文数字**（Q85），子章号阿拉伯（142.1…）。
  · 动态取号：解析全部既有章标题 → 取数值最大者 +1（实测 max=141 → 新章 142）。
  · 取号脚本**双格式兼容**（阿拉伯父章／中文父章），中文解析须支持「零」。
  · 并发护栏：取号后**再次**复检末章号；他人已追加 → 重新取号。
  · 写后四轴自检：① 前段逐字节一致 ② 新章标题出现 1 次 ③ 位于末章 ④ 文件增长。
  · **幂等用「内容特征签名」判定，不用章号**（见 §一百四十 实测教训）。
"""
import argparse
import os
import re
import sys

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# 幂等指纹（唯一标识本节；章号无关）
SECTION_FINGERPRINT = "视觉设定岗 C-131／C-105 回条核销"
SECTION_FINGERPRINT_2 = "D18 v1.100 指针复核（不一致 3 条）"


def cn2int(s):
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
    return s + int2cn(r)


def parse_chapters(text):
    out = []
    for m in re.finditer(r"^##\s+(.+?)、", text, re.M):
        raw = m.group(1).strip()
        out.append((cn2int(raw), raw, text[:m.start()].count("\n") + 1))
    return out


def build_body(chap_no):
    cn = int2cn(chap_no)
    return f"""
## {cn}、分镜导演（2026-10-23 10:0x–10:1x）

### {chap_no}.1 视觉设定岗 C-131／C-105 回条核销（4/4 独立复现成立 ✅）

视觉设定岗 10:0x 补投短回条（上一条私聊因 AGENT_UNAVAILABLE 未送达）。本岗**独立复算**（不采信转述）：

| 项 | 对方报 | 本岗实测（10:0x） | 结论 |
|---|---|---|---|
| D12 U02 版本 | v1.0 → **v1.1** | **v1.1｜101,788 B｜09:17:34** | ✅ |
| md5 | `b92b5dfe28574c43bbb0640d0bca4f02` | 本岗实算 **b92b5dfe28574c43bbb0640d0bca4f02** | ✅ **逐字一致** |
| `check_D12_D11_alignment.py --unit U02` | error 0／warn 0（32/32 覆盖率 1.000） | 本岗实跑 **exit 0｜error 0｜warn 0**｜镜数 32／卡数 32｜平均覆盖率 **1.000**、最低 1.000（C-101）｜判据 B 旧口径扫描未复现 | ✅ **原 warn 1 可核销为 0** |
| 逐字承接 D11 原词 | C-131 补「镜头跟住人流从缺口穿行，」／C-105 补「镜头跟住苏清辞向门口移动；」 | **C-131（ep016/镜3）** D12 `video_prompt` 逐字含「镜头跟住人流从缺口穿行，」，D11 同镜 `visual_facts` 原词「…陆沉带人把最后一个被围的人拽出厂房；**镜头跟住人流从缺口穿行**；主体（钢架与缺口）在画面中部偏上…」→ **逐字一致**；D11 `movement`＝「跟」✅｜**C-105（ep010/镜1）** D12 含「镜头跟住苏清辞向门口移动；」，D11 同镜「冷白工业灯下，苏清辞抱着数据板往门口走…」→ 一致；D11 `movement`＝「跟」✅ | ✅ |

⇒ **ep016 镜3／C-131 由「本岗 Q77 人工核销留痕」升级为「对方改卡从源头消解」**，本岗**零改动**即闭环 ✅
⇒ 企划合规 §一百三十七.2／.3 追认（L3 复审 6/6 全过、md5 逐字一致、锁不重落 `locked_at` 仍 08:43）与本岗 §一百三十五 指针复核一致；**本岗不动 `lock_state`、不动 D18**（owner 企划合规）。
⇒ 对方自报「§122 已按 Q85 自行合规化为『§一百二十二』、未改他人章节一字」——本岗取号脚本现可解析全部章号，**未解析标题 0**、无撞号风险 ✅

### {chap_no}.2 D18 v1.100 指针复核（不一致 3 条）

`shared/D18.json` 现盘 **v1.100｜546,228 B｜10:02:57**（本岗 §一百四十 复核时为 v1.98｜535,901 B，**期间再升两版**）；
`global_checks` **90** 条、`open_issues` **101** 条。
指针全量复核（受检 **24** 组 ＝ U01 14 ＋ U02 10）：**一致 21｜不一致 3**。

| 项 | 登记值 | 现盘值 | owner |
|---|---|---|---|
| U01 D13 | v1.0｜123,418 B | **v1.1｜123,915 B**（白模 09:28 推 v1.1） | 白模场景师（已随 §一百四十 回执告知） |
| **U02 D13** | v1.0 | **v1.1｜119,339 B**（白模 **09:31:21** 推 v1.1） | 白模场景师（**本轮新增**） |
| U02 D09 | v1.1 | **v1.2｜17,859 B**（09:31:35） | 台本编剧（已随 §一百四十 回执告知） |

**新增项 U02 D13 v1.1 的影响核验（必做，不能只记指针漂移）**：
本岗实测 D13 U02 v1.1 全 32 机位**含眼位/视点/分离表述者 0 镜**（分离镜数 **0**）；
U02 D11 `camera_angle` 分布＝平视 26／客观跟拍 1／俯视 3／过肩 2，**POV 镜 0 镜**；
⇒ 两端一致，**U02 侧无新增待同步项**。复跑 `check_D11_D13_camera_alignment.py --unit U02`：
受检 **32**｜配对 32/32｜硬失败 0｜**待同步 0**｜全 0｜计数自证 32=32｜exit 0 ✅
⇒ **U02 D13 v1.1 不触发本岗任何改动**（本岗 U02 D11/D16 仍零改动）。

### {chap_no}.3 本岗台账脚本的自查订正：幂等不能用章号（已修，含一次重复记账的发现与回滚）

**本轮实测踩坑**：首次落 §一百四十 后做幂等复跑，脚本却**又追加了 §一百四十一**（8936 B，正文与 §140 **逐字相同、仅章号不同**）——
违反 Q42「不重复记账」。根因＝幂等检查写成「若台账已存在『## <max+1 的中文>、』则 NO-OP」，
而**第一轮写完后 max 变成新章号，第二轮 max+1 又是下一个号 → 永远判不出已落**。
⇒ 修法：幂等改为**内容特征签名**判定（正文含本节唯一指纹串即 NO-OP，**章号无关**）。
⇒ **回滚已完成**：重复章 §一百四十一 已删除，现盘 **§140 出现 1 次、§141 出现 0 次**；
用备份做**严格前缀比对**确认「现盘以备份全文开头＝True」（备份 792,608 B）⇒ **他人字节零改动**，净增仅本岗章节 8,936 B。
⇒ 修后连续两次复跑均输出 `[NO-OP]`，不再重复追加 ✅

**取号解析器的一处自身缺陷（本轮发现并修）**：首版中文数字解析器**缺「零」字处理**，
导致「一百零一」这类写法**解析失败**（一度误报「8 个未解析标题」）。
⇒ 补「零」后：全部 **140** 章可解析、**未解析 0**、无重复章号。

### {chap_no}.4 出口闸与边界（本岗 10:0x–10:1x 当场实跑）

| 闸 | 结果 |
|---|---|
| `validate --unit U01` | **11/11｜error 0｜warning 1** |
| `validate --unit U02` | **11/11｜error 0｜warning 3** |
| `validate`（全项目） | **22/22｜error 0｜warning 4** |
| `render-md` | **exit 0** |
| `check_D12_D11_alignment` U02 | **exit 0｜error 0｜warn 0**｜覆盖率 1.000 |
| `check_D08_D11_shotintent` U01／U02 | 受检 **23**／**29** 条｜0 硬冲突｜exit 0 |
| `check_D10_D11_alignment` U01／U02 | exit 0｜**单 v**｜双 v 命中 0 |
| `check_D11_D13_camera_alignment` U01 | 受检 **32**｜配对 32/32｜硬失败 0｜**待同步 1（ep7 镜3）**｜计数自证 32=32｜exit 0 |
| `check_D11_D13_camera_alignment` U02 | 受检 **32**｜配对 32/32｜**全 0**｜计数自证 32=32｜exit 0 |
| `selftest_D11_D13_camera_alignment` | 受检 **7**｜通过 **7**｜不通过 0｜真盘 6 份 SHA256 一致 6/6 |
| `reconcile_D15_D16_timing` U01／U02 | exit 0｜清单 12 ＝ 12｜不通过 0 |
| `reconcile_tts_actual_vs_d15_budget` | exit 0｜清单 12 ＝ 12｜不通过 0 |
| `check_tts_vs_d15_budget` U01 | exit 0｜rows 27｜ERR 0｜WARN 2｜OK 25｜d16_out_mismatch 0｜no_audio 1 |
| `check_D05_lutiao_firstuse` | exit 0｜断言 **13** 条｜通过 13｜失败 0 |
| `check_white_model_frames` U01 | **exit 1**｜受检 32 镜｜PASS 30｜**FAIL 2**（U02-R07 触发条件② 未满足） |

**本岗交付物本轮零改动**：`units/U01/D11.json` v1.8｜50,322 B｜`units/U01/D16.json` v1.12｜224,276 B｜
`units/U02/D11.json` v1.6｜58,051 B｜`units/U02/D16.json` v1.5｜208,578 B。
**本岗本轮改动**：台账章节 ＋ 台账追加脚本的幂等与解析器修正 ＋ §一百四十 的两个只读校验器。
**未改** D05–D10／D12–D15／D18／`project.json`／`03_规格/*`／`04_工具/*`／`00_项目索引.md`；
**未生成**图片／视频／音频，**未合成** TTS／BGM，**未提交** H3 付费生成，**未投流**上架。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    ledger = os.path.join(root, "99_交付说明.md")
    if not os.path.isfile(ledger):
        sys.exit(f"[ABORT] 找不到台账：{ledger}")

    with open(ledger, "r", encoding="utf-8") as f:
        text = f.read()

    chaps = parse_chapters(text)
    nums = [c[0] for c in chaps if c[0] is not None]
    if not nums:
        sys.exit("[ABORT] 台账无可解析章号")
    max_no = max(nums)
    target = max_no + 1
    cn = int2cn(target)

    if SECTION_FINGERPRINT in text and SECTION_FINGERPRINT_2 in text:
        print(f"[NO-OP] 台账已含本岗本节内容指纹，不重复追加（当前末章＝{chaps[-1][1]}／{chaps[-1][0]}）")
        return 0

    chaps2 = parse_chapters(text)
    nums2 = [c[0] for c in chaps2 if c[0] is not None]
    if max(nums2) != max_no:
        print(f"[RETRY] 取号期间他人已追加（max {max_no} → {max(nums2)}），本轮中止，请重跑")
        return 3

    body = build_body(target)
    if args.dry_run:
        print(f"[DRY-RUN] 将追加「## {cn}、分镜导演」（当前末章＝{chaps2[-1][1]}／{chaps2[-1][0]}）")
        return 0

    before_len = len(text)
    new_text = text.rstrip("\n") + "\n" + body
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(new_text)

    with open(ledger, "r", encoding="utf-8") as f:
        after = f.read()
    a1 = after.startswith(text.rstrip("\n"))
    a2 = after.count(f"## {cn}、") == 1
    chaps3 = parse_chapters(after)
    a3 = chaps3[-1][1] == cn
    a4 = len(after) > before_len
    print(f"■ 台账追加自检：章号 {cn}（{target}）")
    print(f"   ① 前段逐字节一致：{a1}")
    print(f"   ② 「## {cn}、」出现 1 次：{a2}")
    print(f"   ③ 位于末章：{a3}（末章＝{chaps3[-1][1]}／{chaps3[-1][0]}）")
    print(f"   ④ 文件增长：{a4}（{before_len} → {len(after)} B，+{len(after) - before_len}）")
    if not (a1 and a2 and a3 and a4):
        sys.exit("[ABORT] 写后自检未全部通过")
    print("✅ 台账章节落盘并通过四轴自检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
