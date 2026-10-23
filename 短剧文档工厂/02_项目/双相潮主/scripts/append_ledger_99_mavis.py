#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加台账新章节（分镜导演岗）—— 动态取最大章号 + 1，避免并发撞号。

用法：python3 scripts/append_ledger_99_mavis.py
"""
import io, os, re, sys, datetime, shutil

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
    d = "零一二三四五六七八九"
    if n < 10:
        return d[n]
    if n < 20:
        return "十" + (d[n - 10] if n > 0 else "")
    if n < 100:
        return d[n // 10] + "十" + (d[n % 10] if n % 10 else "")
    return str(n)


txt = open(REG, encoding="utf-8").read()
nums = [cn2int(m.group(1)) for m in re.finditer(r"^## ([零一二三四五六七八九十百\d]+)、", txt, re.M)]
nums = [n for n in nums if n]
nxt = max(nums) + 1
CH = int2cn(nxt)
print(f"📌 当前最大章号 = {max(nums)}，本节占号 = §{CH}（{nxt}）")

# 备份纪律：备份落 reports/_bak_*，不在交付目录内写备份
bak_dir = os.path.join(ROOT, "reports", "_bak_LEDGER_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
os.makedirs(bak_dir, exist_ok=True)
shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))
print(f"   · 备份旧台账 → {os.path.relpath(bak_dir, ROOT)}/99_交付说明.md")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

SEC = f"""
## {CH}、分镜导演：**U02-R29 落盘（D16 v1.4 ＋ 计数字段结构化口径）** ＋ **U02-R32 连带项落地（D11 v1.6）** ＋ **自查发现并修复守卫缺陷三处（A36↔Q64 互相遮蔽、`_vkey` 缺失致版本守卫从未执行、漂移守卫副本致清单 33≠34）**（分镜导演，{now}）

本轮起点是收尾 **U02-R29**（D16 审计计数字段落 `audit_field_scope` 结构化口径字段），中途被「脚本跑不起来」挡住；顺着查下去，发现**三处「以为已完成、实则从未生效」的守卫缺陷**。本节如实登记，**含对 §九十七 结论的订正**。**全部结论附受检条数（Q49）。**

### {nxt}.1 认盘：三处「以为已完成、实则未落盘／未执行」

**发现 1 · U02-R29 上一轮**并未落盘**。** 查盘：`units/U02/D16.json` ＝ **v1.3**（178,794 B），`audit_field_scope` 在 8 集**全部缺失**；备份链 8 个目录（`_bak_U02_D11_D16_20261023-052734`～`-070600`）**逐个查版本全是 v1.3**，**无任何 v1.4** → 上一轮结论「D16 v1.4 已落盘且结构化 diff ＝ 61 处」**不成立**（落盘被漂移守卫的 exit 2 挡住，只算出了 diff、没写成盘）。

**发现 2 · D16 的 Q64 版本守卫**从未执行过一次**。** `build_D16_U02.py` 调用了 `_vkey(...)`，但**全文件没有它的定义** → 实际落盘时会 `NameError`。该异常恰被**上游漂移守卫的 exit 2** 遮蔽 → 守卫**一次都没跑到**。
→ **据此订正 §九十七 的结论**：该节记「Q64 版本守卫 3 项自测全过」，**对 `build_D11_U02.py` 成立、对 `build_D16_U02.py` 不成立**（D16 当时从未真正落盘成功，测不到版本守卫）。§九十七 的「D11/U02 两脚本已合规」结论**就 D16 部分予以撤回**，本节为补做。

**发现 3 · 写盘段残留**第二份**漂移守卫副本。** `grep` 得 `chk(drift_ok, ...)` 出现在**两处**：新守卫（正确位置，在 `if errors:` **之前**）与**写盘段里的旧副本**（且旧副本**没套文本替换**）→ Q56 清单守卫报 **清单 33 ≠ 断言点 34** → `build_D16_U02.py` 的 `--check` 与**实际构建全部 exit 2 中止**（这正是发现 1 的直接成因）。

### {nxt}.2 U02-R29 落盘：D16 U02 v1.3 → **v1.4**（208,578 B）

**落盘内容**：8 集 × `subtitle_style.subtitle_sync_audit.audit_field_scope`，含 **4 个计数字段**（`synced_row_count`／`float_tail_row_count`／`no_vo_anchor_rows`／`dwell_floor_rows`）的 `row_filter` ＋ `predicate` ＋ 覆盖范围说明，**外加** `actual_audio_axis.已测 = False`（U02 无预演音频资产 → 实测音频轴**受检 0 条**，按 Q49 **不作任何「实际音频已核」声明**）。
**字段名不改**（U02-R29 ②③）：`no_vo_anchor_rows` 的字面义（「无配音锚点的行数」）与实际口径（「面板文字行数」）不一致，**本岗不擅改他岗约定**，改以 `read_as` ＋ `name_semantics_mismatch: true` 落进结构化字段供脚本直接消费。

**A31 从 2 字段扩到 4 字段**（自查发现：清单措辞「各计数字段」比实现宽 —— 原实现只复算 `float_tail_row_count`／`no_vo_anchor_rows` 两个）→ 现按 `row_filter` ＋ `predicate` 套回实际字幕行集合独立复算，**受检 8 集 × 4 字段 = 32 项**，全部与落盘值相等（清单同步改为「全部 4 个计数字段/明细……8 集 × 4 字段 = 32 项复算」，**断言点数不变，33 ＝ 33**）。

**版本戳同步 52 处**（D15 U02 v1.0 → v1.1）：落在 `sync_basis`／`verified_against_d15`／`lines[].note`／`dwell_calc_convention`。写成**精确 token 替换**（`D15 U02 v1.0` → `D15 U02 v1.1`；`v1.0（D15 U02 落盘后现算复核` → `v1.1（…`），**不做裸 `v1.0`→`v1.1`** —— 裸替换会误伤 `verified_note` 里「本轮 D16 升级 v1.0→v1.1 的实质变更」这类 **S11 历史留痕**。

**结构化 diff 核验（v1.3 备份 → v1.4 盘上）**：

| 项 | 处数 |
|---|---|
| 已声明版本变更（`version`） | **1** |
| 已声明新增键（8 集 `audit_field_scope`） | **8** |
| 已声明文本替换（D15 版本戳同步） | **52** |
| **未声明差异** | **0** |
| **涉及时码字段的差异**（`in_sec`／`out_sec`／`at_sec`／`dur_sec`／`dwell_sec`） | **0** |

**幂等**：重跑 → **exit 0**，产物与盘上**字节完全一致**（`cmp` 通过）。
**断言清单**：D16 **33 条 ＝ 33 实际断言点**（机械守卫自证）；D11 **39 条 ＝ 39**。

### {nxt}.3 U02-R32 连带项落地：D11 U02 v1.5 → **v1.6**（58,051 B）

**来源**：故事架构 07:0x 已把 D07 U02 升 **v1.3**（`ep009 段3`「指节敲了两下**板面**」→「指节敲了两下**背面**」，本岗实查备份比对：**D07 v1.2→v1.3 差异恰 2 处**＝版本＋该引文），并**派单本岗**同步 D11 对应引文。
**机制**：D11 的 `note` 是**逐字引用 D07 段 note**（A39 断言「D07 段引文逐字」受检 32 条）→ **D07 一改，D11 引文必须同步**，否则 A39 与 A36 漂移守卫同时判红（本岗实跑确认：产物写「背面」、盘上仍是「板面」）。
**处置**：**只同步引文这一处** —— 本岗**不改 D07**（归故事架构）、**不改 `visual_facts`／`sfx`**（按 D08 正文写「背面」，本就不改）。**结构化 diff 恰 2 处**：`version` ＋ `episodes[0].shots[2].note` 的引文。
**逐字辨析（防止误改同形字）**：D11 交付物里「板面」**4 → 3**，余下 3 处是**另一语义** —— 「**板面朝外**」（数据板正面朝向，镜1）与「**视线落在板面上**」（落点，镜3），与「敲板正背」无关，**未动**；「背面」3 → 4。

### {nxt}.4 守卫修复：**A36 与 Q64 互相遮蔽 → `--force` 逃生口曾被挡死**

**缺陷**：A36 漂移守卫（内容差异）与 Q64 版本守卫（版本序）**职责不同但执行顺序相压** —— 盘上版本**高于**脚本时，**A36 先判「盘上可能已被他人改动」并中止** → **Q64 明文要求的「显式 `--force` 逃生口」实际失效**（加 `--force` 仍被 A36 挡在门外）。D11／D16 **两个脚本同构同缺**。
**修复（两脚本同改）**：
- 盘上版本**高于**脚本 → 判为「**版本回退场景**」，**交 Q64 判定**（带 `--force` 逃生口），A36 不再抢活；
- A36 **只管内容差异**：内容层未声明差异**一律拒绝，`--force` 也不放行**（否则等于允许**静默吞掉他人手改** —— 那正是本守卫要防的事）；
- `_vkey` 由**函数内**提到**模块级**（D11／D16 各一份，两处定义不得再漂移）。

**Q64 四项自测（D16 脚本，实跑）**：

| 自测 | 做法 | 实测 |
|---|---|---|
| **1 · 幂等放行** | 磁盘 v1.4 ＝ 脚本 v1.4，重跑 | **exit 0**，产物与盘上**字节完全一致** |
| **2 · 拒绝回退** | 伪造磁盘 `version=v9.9` | **exit 1**，报「版本守卫：磁盘已是 v9.9，高于本脚本要写的 v1.4 → 拒绝覆盖，未写盘」，**磁盘实况仍 v9.9（未被改写）** |
| **3 · `--force` 逃生口** | 伪造磁盘 v9.9 ＋ `--force` | **exit 0**，放行回退落盘 **v1.4** |
| **4 · 内容漂移不可 force** | 篡改 `episodes[0].subtitle_style.lines[0].text` | **exit 1**（报「未声明差异 → …lines[0].text」），**再加 `--force` 仍 exit 1**，**磁盘保持篡改态**（不被静默覆盖） |

**D11 脚本同项**：伪造 v9.9 → **由 Q64 拒绝**（不再由 A36 抢判）；`--force` → 放行回退；`--check` **exit 0**（清单 **39**）。

### {nxt}.5 本轮全套闸门复跑（exit 数逐条贴出）

| 闸门 | 实测 |
|---|---|
| `validate.mjs --unit U01` | **通过 11/11 规则｜error 0｜warning 2**｜**EXIT 0** |
| `validate.mjs --unit U02` | **通过 11/11 规则｜error 0｜warning 7**｜**EXIT 0** |
| `render-md.mjs` | **EXIT 0**（MD 全部由本工具单向渲染，**未手写/手改 MD**） |
| `check_D08_D11_shotintent.mjs --unit U01` | 受检 **23** → **23/23｜0 硬冲突｜0 引文失配**｜**EXIT 0** |
| `check_D08_D11_shotintent.mjs --unit U02` | 受检 **29** → **29/29｜0 硬冲突｜0 引文失配**｜**EXIT 0** |
| `check_D12_D11_alignment.py --unit U01` | **error 0｜warn 0｜已核销 11**｜**EXIT 0** |
| `check_D12_D11_alignment.py --unit U02` | **error 0｜warn 1**（A 疑似漏写 ep016 镜3／C-131／命中 0.12，**待视觉设定补卡后核销**）｜**EXIT 0** |
| `reconcile_D15_D16_timing.mjs --unit U01` | **零违规：0 越窗／0 跨切点，字幕与配音逐条同步**｜**EXIT 0** |
| `reconcile_D15_D16_timing.mjs --unit U02` | **零违规：0 越窗／0 跨切点，字幕与配音逐条同步**｜**EXIT 0** |
| `reconcile_tts_actual_vs_d15_budget.mjs` | **受检 27 条**：越窗 0／跨切点 0／重叠 0／停留<1.2s 0；A3 候选 **35 条**｜**EXIT 0** |
| `build_D11_U02.py --check` | **断言清单 39 ＝ 39**｜**EXIT 0** |
| `build_D16_U02.py --check` | **断言清单 33 ＝ 33**｜**EXIT 0** |
| `check_D11_framing_safe_area.py --unit U01` | **error 0**｜**EXIT 0**（U02 无 D14 → 受检 0 条，**不作通过引用**） |
| 交付物「低阶」字面 | `units/U02/D11.json` **0**｜`units/U02/D16.json` **0** |

### {nxt}.6 本节边界

- **本节只写台账一个文件**。本轮脚本改动：`scripts/build_D16_U02.py`（清单守卫 33＝33｜删写盘段漂移守卫副本｜`_vkey` 提模块级｜A36↔Q64 分工｜A31 扩 4 字段）、`scripts/build_D11_U02.py`（同 A36↔Q64 分工｜`_vkey` 提模块级｜`DECLARED_CHANGES` 换为本轮声明项｜历史声明移入留痕注释）。
- **本岗交付物改动**：`units/U02/D16.json`（**v1.3 → v1.4**）、`units/U02/D11.json`（**v1.5 → v1.6**）。**其余交付物零改动**（U01 侧 D11 v1.8／D16 v1.10 未动）。
- **未改** D07／D08／D09／D12／D15／D05／D06／D18／`03_规格/*`／`04_工具/*`／`00_项目索引.md`／`project.json`／他岗脚本与产物。**本岗未代改 `scripts/shotintent_map_U02.mjs`**（OPS-16 归属待裁定，裁定前不碰）。
- **未新建 `d12_check_data_U02.py`**（内容层归视觉设定）。
- MD 未手写 / 手改；未生成任何图片／视频／音频；**未合成 TTS／BGM**；未提交 H3 付费生成；未投流上架。
- **本岗挂账**：U02 仍缺 D13／D14（取景轴受检 0 条）；ep016 镜3／C-131 待视觉设定补卡；ep2#4 旧音频待重合成（不属本岗边界）；U01 侧断言清单化（Q56 ②）承接方待裁定；D05「低阶律条」机器闸条目待企划合规落；OPS-16 映射表归属待裁定；G-05 预算档位待裁决；§五十三.6 多单元同跑待裁定。
- **以上游合规裁决为准**（D18 Q40／Q42／Q49／Q56／Q57／**Q64**／Q65／S11／S22／S23、企划合规 §九十三／§九十六、故事架构 §九十八 U02-R32）。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §{CH}（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
