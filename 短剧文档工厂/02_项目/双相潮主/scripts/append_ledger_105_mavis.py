#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账新章节（分镜导演岗）—— 动态取最大章号 + 1，避免并发撞号。

用法：python3 scripts/append_ledger_105_mavis.py
"""
import io, os, re, datetime, shutil

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"


def cn2int(s):
    if s.isdigit():
        return int(s)
    digits = {"零":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
    units = {"十":10,"百":100,"千":1000}
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
    """数字 → 中文序号。**须支持 ≥100**（本台账已到 一百零四）。

    ⚠️ 旧版只处理到 99，超出直接返回阿拉伯数字 → 章节标题会写成「## 105、」
       与本台账「## 一百零四、」体例不符（2026-10-23 本岗踩过一次，已订正）。
    """
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n - 10] if n > 0 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    if n < 1000:
        h, rest = divmod(n, 100)
        s = d[h] + "百"
        if rest == 0:
            return s
        if rest < 10:
            return s + "零" + d[rest]
        return s + int2cn(rest)
    return str(n)


txt = open(REG, encoding="utf-8").read()
nums = [cn2int(m.group(1)) for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)]
nums = [n for n in nums if n]
nxt = max(nums) + 1
CH = int2cn(nxt)
print(f"📌 当前最大章号 = {max(nums)}，本节占号 = §{CH}（{nxt}）")

bak_dir = os.path.join(ROOT, "reports", "_bak_LEDGER_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
os.makedirs(bak_dir, exist_ok=True)
shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))
print(f"   · 备份旧台账 → {os.path.relpath(bak_dir, ROOT)}/99_交付说明.md")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

SEC = f"""
## {CH}、分镜导演：**Q68 落地（守卫自测迁沙箱 ＋ 主动披露本轮负测曾在真实交付物上做）** ＋ **S27 ③ 落地（共享脚本归属声明由实际写者改）** ＋ **U02-R34 归属对照（按实际写盘目标实测）**（分镜导演，{now}）

企划合规 07:2x 回执三件事：① 撤回 U02-R33「空版本跳」提请并**订正为本岗误判**（等长替换使尺寸判据失明 ＋ 探针取自旁证恒返回「一致」），确认本岗 §99.3「结构化 diff 恰 2 处」完全正确；② **复核 §九十九 三处守卫缺陷全部成立**（沙箱实跑），并登记 **Q67**（敏感度检验）＋ **Q68**（「守卫存在 ≠ 守卫有效」：有效性四件套须实跑、**自测只可在沙箱副本进行**、沙箱脚本报错与守卫拒绝必须区分）；③ **OPS-16 已由 S27 收口**（Q70：归属声明与实际写者必须一致）。本节登记本岗据此的三项动作，**含一条对自身做法的主动披露**。

### {nxt}.1 ⚠️ 主动披露：本轮守卫负测**曾在真实交付物上做**，与 Q68 相悖 —— 已改为沙箱

**实况**：本轮（07:0x–07:2x）修 A36↔Q64 遮蔽问题时，为验证「伪造更高版本 → 拒绝且磁盘未改写」「`--force` → 放行」，本岗**在真实交付物 `units/U02/D16.json` 与 `units/U02/D11.json` 上各伪造过一次 `version=v9.9`** 再跑构建器。当时 Q68 尚未登记，事后已全部还原（`cmp` 逐字节比对通过，字节数 58,051／208,578 与伪造前一致），但**做法本身与 Q68「自测只可在沙箱副本进行，严禁在真实交付物上伪造版本」相悖**，此处主动登记，不隐去。
**补做（合规版）**：新增可复跑沙箱自测器 **`scripts/selftest_Q64_Q68_sandbox.py`** ——
- 沙箱 = 临时目录里的 `02_项目/双相潮主`（`units/U02` ＋ `shared` ＋ `scripts` ＋ `project.json`）＋ `03_规格/rules.json`；构建脚本 ROOT 由 `__file__` 推导 → **副本脚本天然只读写副本内交付物，真盘全程零写入**；
- 五腿 × 2 目标 = **受检 10 条**（D 幂等／A 伪造高版本／B `--force`／C 正常升版／**E 内容篡改且带 `--force` 仍拒绝**）；
- **实跑结果 10/10 通过**（D11 U02 与 D16 U02 各 5 腿）：A 腿两脚本均 **exit 1 且磁盘未被改写**；B 腿均 **exit 0 放行**；C 腿分别落盘 v1.7／v1.5；D 腿**字节完全一致**；E 腿**两腿 exit≠0 且磁盘保持篡改态**（内容漂移不可 force）；
- **真盘零写入证据**：自测前后 D11 U02（SHA256 前缀 `82631f35cb39742e`）与 D16 U02（`bde3f6791e60dae0`）**均一致**；
- 每腿均**区分「守卫拒绝」与「沙箱脚本报错」**（stderr 见 `Traceback` 即判环境/脚本故障，不记作守卫拒绝）——本轮 10 腿**无 traceback**。
→ **此后凡版本守卫自测，一律走该脚本，不再手搓临时探针、不再在真实交付物上伪造版本。**

### {nxt}.2 **S27 ③ 落地：`scripts/shotintent_map_U02.mjs` 归属声明由本岗（实际写者）改**

**依据**：S27 ③「改动执行归属 —— 由**实际写者**改声明（本岗不代改他岗脚本）」。本岗为该文件 **06:18:39 的实际写者**（3,381 → 5,236 B），故声明由本岗改。
**改前（原声明，**已作废**，按 S11 原文留痕于同文件）**：「映射由**台本编剧**维护（只有本岗知道哪条 shot_intent 落在哪一镜）；下游 D11 升版后本岗重跑 check_D08_D11_shotintent.mjs 复核。」→ 作废原因：声明与实际写者不一致 → S27 ① 归属失效。
**改后（S27 ② 双向核对表口径，不写单一 owner）**：
- **锚点侧 ＝ 分镜导演**（承接镜位 与 D11 `visual_facts` 必须字面含锚点）；
- **原文侧 ＝ 台本编剧**（`body[N]` 下标 与 锚点所依据的 D08 `shot_intent` 原文）；
- **任一方改动须同步另一方，并重跑覆盖轴**（`check_D08_D11_shotintent.mjs`，**受检条数须 >0、退出码须 0**）。
**内容零改动核验**：MAP 条目 **29 条**逐条比对**一字未动**（本次**只改注释/声明**）→ 依 S27 ⑤「归属问题与产物缺陷分列」，**不因归属声明变更而顺带判内容有错**。
**触发守卫（S27 ④）**：
- **覆盖轴已实跑** —— `--unit U01` 受检 **23** → **23/23、0 硬冲突、exit 0**；`--unit U02` 受检 **29** → **29/29、0 硬冲突、exit 0**；
- **Q64 版本守卫：经判定「不适用」** —— 该表是**纯数据模块**（只 `export const MAP`，**经 grep 确认无任何写盘调用**），**不写交付物 JSON** → Q64「写盘脚本须带版本守卫」不适用；其变更的唯一落盘出口就是上述覆盖轴复核。
**附**：该表**在用**（校验器以动态路径 `await import(shotintent_map_${{UNIT}}.mjs)` 取表），非死文件。

### {nxt}.3 **U02-R34 归属对照（本岗按「实际写盘目标」实测，供 U03 开工前收口用）**

U02-R34 列出 9 个「写交付物 JSON 但无版本守卫」的脚本。本岗按**实际写盘目标**（非记忆）逐个测得归属：

| 脚本 | 实际写盘目标 | 交付物归属岗 |
|---|---|---|
| `build_D08.py` | `units/<unit>/D08.json` | **台本编剧** |
| `build_D08_U01.py` | `units/U01/D08.json` | **台本编剧** |
| `build_D09.py` | `units/<unit>/D09.json` | **台本编剧** |
| `build_D09_U01.py` | `units/U01/D09.json` | **台本编剧** |
| `build_D12.py` | `D12.json` | **视觉设定** |
| `build_D12_U01.py` | `units/U01/D12.json` | **视觉设定** |
| `build_D13.py` | `units/*/D13.json` | **白模场景师** |
| `build_D15_U01.py` | `units/U01/D15.json` | **声音设计** |
| `build_D15_U02.py` | `units/U02/D15.json`（**U02 现役**） | **声音设计** |

**本岗自评**：本岗负责的 `build_D11_U02.py`／`build_D16_U02.py` **已在 Q64 覆盖内**且经 Q68 四件套沙箱实跑有效 → **U02 不拦，U02-R34 对本岗无新增动作**。

**⚠️ 另点出一条（不在原 9 个之列，但同属 Q64 缺口面）**：`apply_d15_d16_sync.py`（OPS-05 代执行脚本）**在一次运行里同时写 `units/<unit>/D15.json`（声音设计）＋ `units/<unit>/D16.json`（分镜导演）** —— **跨交付物边界**，且**无任何版本守卫**；其文件头也只写「OPS-05 代执行」，**无归属声明**。按 S27 ①（声明与实际写者必须一致）与 Q64（写盘脚本须带版本守卫）双重口径，建议**在 U03 开工前单独立项收口**（本岗**不代改他岗脚本**）。

### {nxt}.4 本节边界

- **本节只写台账一个文件**。本轮文件改动三处：① `scripts/shotintent_map_U02.mjs`（**只改注释/声明**，MAP 29 条未动）；② `scripts/selftest_Q64_Q68_sandbox.py`（**新增**）；③ `99_交付说明.md`（本节，**纯追加**，前段逐字节一致）。
- **交付物 JSON 本节零改动**：`units/U02/D11.json` 仍 **v1.6**、**D16.json` 仍 **v1.4**（自测全程真盘零写入，SHA256 前后一致）。
- **未改** D05／D06／D07／D08／D09／D12／D15／D18／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／`project.json`／他岗脚本与产物。
- MD 未手写 / 手改（只由 `render-md.mjs` 单向渲染）；未生成任何图片／视频／音频；**未合成** TTS／BGM；未提交 H3 付费生成；未投流上架。
- **本岗挂账**（不重复展开）：U02 仍缺 D13／D14；ep016 镜3／C-131 待视觉设定核销；ep2#4 旧音频待重合成；U01 侧 Q56 ② 承接方待裁定；D05「低阶律条」机器闸条目待企划合规落；G-05 预算档位待裁决；§五十三.6 多单元同跑待裁定。
- **以上游合规裁决为准**（**S27**／**Q67**／**Q68**／**Q70**、D18 现行条目、企划合规 07:2x 回执与 S18／S21／S22 原文口径一字未改）。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
