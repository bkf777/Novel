#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账 §七十一（分镜导演岗）—— Q56 落地：断言清单 ＋ 机械守卫。动态取 max+1。"""
import io, os, re, datetime

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"

def cn2int(s):
    if s.isdigit(): return int(s)
    d = {"零":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
    u = {"十":10,"百":100,"千":1000}
    t = sec = 0
    for ch in s:
        if ch in d: sec = d[ch]
        elif ch in u:
            x = u[ch]
            if sec == 0: sec = 1
            t += sec * x; sec = 0
        else: return None
    return t + sec

def int2cn(n):
    d = "零一二三四五六七八九"
    if n < 10: return d[n]
    if n < 20: return "十" + (d[n-10] if n > 10 else "")
    if n < 100: return d[n//10] + "十" + (d[n%10] if n%10 else "")
    return str(n)

txt = open(REG, encoding="utf-8").read()
nums = [cn2int(m.group(1)) for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)]
nums = [n for n in nums if n]
nxt = max(nums) + 1
CH = int2cn(nxt)
print(f"📌 当前最大章号 = {max(nums)}，本节占号 = {CH}（{nxt}）")
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

SEC = f"""
## {CH}、分镜导演：**Q56 落地** —— 构建脚本**断言清单 ＋ 机械守卫**（D16 U02 30 条／D11 U02 35 条）＋ 负测证明（**分镜导演，{now}**）

对应企划合规 §六十九.2 登记的 **Q56**「校验断言必须跨单元复制」。Q56 的 ①（脚本显式声明跑了哪些断言）与 ③（新断言一律负测）本岗已落地；②（跨单元复用时清单随脚本带走）以**清单随脚本内嵌**的方式满足。

### {nxt}.1 做法：清单不是注释，是**可执行守卫**

「在脚本头部写死判据清单」若只当注释，仍可能被后人删掉断言而清单纹丝不动 → **清单与实际不符即中止**：

```
def assert_manifest_guard():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    token = "ch" + "k("                      # 拼接，避免本函数把自己数进去
    n_call = src.count(token) - 1            # 减去函数定义那一处
    n_decl = len(ASSERT_MANIFEST)
    if n_call != n_decl:
        print(f"❌ 中止：断言清单 {{n_decl}} 条 ≠ 实际断言点 {{n_call}} 处 —— "
              "Q56：新增/删除断言必须同步更新 ASSERT_MANIFEST（禁「跑到什么算什么」）。")
        sys.exit(2)
```

| 脚本 | 断言清单条数 | 实际断言点 | 守卫 |
|---|---|---|---|
| `scripts/build_D16_U02.py` | **30 条** | **30 处** | ✅ 一致（`--check` 通过） |
| `scripts/build_D11_U02.py` | **35 条** | **35 处** | ✅ 一致（`--check` 通过） |

清单每条带**编号 ＋ 判据 ＋ 来源**（`U01-R19 跨单元复制`／`U02-自检`／`S18 台词轴`／`S22 停留口径`／`S9`／`D05 术语收口`／`D10 镜头语言`／`D03 角标强制`／`覆盖轴`／`V3/V4`）—— **来源标注是 Q56 的核心**：只有写明「这条来自 U01-R19、必须跨单元复制」，下一个单元的脚本作者才可能知道它存在。

### {nxt}.2 **负测**（Q56 ③：断言非恒真的唯一证明）

删掉 `build_D16_U02.py` 的「字幕行不跨切点」一条断言（模拟「复制脚本时漏抄一条」的真实事故形态）→ 守卫立即中止：

```
❌ 中止：断言清单 30 条 ≠ 实际断言点 29 处 —— Q56：新增/删除断言必须同步更新 ASSERT_MANIFEST（禁「跑到什么算什么」）。   exit 2
```

→ 负测脚本已删除。**「自检通过」从此有了可审计的含义**：不是「跑到的都过了」，而是「清单声明的 N 条断言，一条不少地在跑」。

### {nxt}.3 交付物**字节级未变**（脚本改动不得污染交付物）

加入清单与守卫后重跑落盘，与改动前的文件**逐字节比对**：

| 文件 | 结果 |
|---|---|
| `units/U02/D16.json` v1.3（178,794 B） | ✅ **字节完全一致** |
| `units/U02/D11.json` v1.3（57,350 B） | ✅ **字节完全一致** |

→ 脚本侧改动（清单 ＋ 守卫 ＋ 输出行）**未改变任何交付物内容**，也未触发版本递增（版本号只随交付物内容变化递增）。

### {nxt}.4 仍待补的一格（Q56 ② 的边界，本岗如实登记）

Q56 ② 要求「跨单元复用构建脚本时断言清单随脚本带走，禁在单元层新写一份缺断言的副本」。**本仓现状**：

| 交付物 | 单元 | 构建脚本 | 断言清单 |
|---|---|---|---|
| D16 | U02 | `build_D16_U02.py`（本岗） | ✅ **30 条 ＋ 守卫** |
| D16 | U01 | **无独立构建脚本**（由 OPS 脚本 ＋ `patch_D16_*.mjs` 链维护） | ⚠️ 判据散在 `reconcile_D15_D16_timing.mjs`（判据 A/B/C/D）与 `reconcile_tts_actual_vs_d15_budget.mjs`（A1~A4）中，**无清单化** |
| D11 | U02 | `build_D11_U02.py`（本岗） | ✅ **35 条 ＋ 守卫** |
| D11 | U01 | `build_D11_U01.py`（他岗） | ⚠️ **不在本岗写入范围**，未动 |

→ **本岗如实登记**：D11 U01 与 D16 U01 两侧的断言清单化**尚未完成**，且 U01 侧脚本归属他岗 / 已被 OPS 链路接管 → **本岗不越界代改**，提请企划合规裁定「U01 侧清单化由谁承接」。**在裁定前，本岗的 U02 两支脚本已按 Q56 自证到位**。

### {nxt}.5 边界

本轮只改：`scripts/build_D16_U02.py`、`scripts/build_D11_U02.py`（**仅加清单 ＋ 守卫 ＋ 一行输出**）、本节台账。**交付物 JSON 字节未变**；未改任何交付物内容、未改他岗脚本、未改 `04_工具/**`。

未生成任何图片／视频／音频，未合成 TTS/BGM，未提交 H3 付费生成，未投流上架。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
