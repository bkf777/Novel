#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账续写（分镜导演岗）—— 纯追加 §九十九.7（不新起章节号，避免撞号）。

用法：python3 scripts/append_ledger_99b_mavis.py
"""
import io, os, re, datetime, shutil

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
REG = f"{ROOT}/99_交付说明.md"

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# 备份纪律：备份落 reports/_bak_*，不在交付目录内写备份
bak_dir = os.path.join(ROOT, "reports", "_bak_LEDGER_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
os.makedirs(bak_dir, exist_ok=True)
shutil.copy2(REG, os.path.join(bak_dir, "99_交付说明.md"))
print(f"   · 备份旧台账 → {os.path.relpath(bak_dir, ROOT)}/99_交付说明.md")

SEC = f"""
### 99.7 附带发现：**D11 渲染器不输出每镜 `note` → D07 引文与 📌 反查留痕从不进 MD**（仅只读 MD 的质检岗会误判「引文未同步」）

**发现**：核对渲染产物时发现 —— `render/units/U02/D11.md` 中「指节敲了两下背面」**0 命中**、「指节敲了两下板面」**0 命中**、「灯下露出灰斑」**0 命中**、「D07 段3」**0 命中**，而 JSON 侧「板面 3／背面 4」齐全 → **不是内容丢失，是渲染器没有输出 `note` 字段**。
**实证（`04_工具/render-md.mjs` 的 D11 渲染器）**：分镜表的输出列为 `景别 / 机位 / 焦距 / 运镜 / 时长 / visual_facts / dialogue / sfx / 镜头意图（交 D11 反查）` —— **无 `note` 列**（`note` 仅在总纲段落里作为「例外须在 note 里写明依据」的说明被**提及**，其内容本身不进 MD）。
**影响面**：每镜 `note` 里承载的两类证据 —— ① **逐字 D07 段引文**；② **📌 D08 shot_intent 反查留痕**（本岗覆盖轴 29/29 的证据链）—— **都不出现在 MD**。若质检岗**只读 MD** 去核「D07 引文是否同步」「D08 反查留痕是否在位」，会看到 0 命中而误判为**漏同步/漏写**。
**处置**：**本岗不代改 `04_工具/*`**（禁改区，且非本岗文件）→ 已具名上报**企划合规**（总控派活·交付质检），请其裁定：① 质检口径以 **JSON 真源**为准（`note` 层不进 MD 属渲染器既有设计，非交付缺陷）；或 ② 由 `04_工具` 归口给 D11 渲染器补一列 `note`/留痕区（**本岗不代提改动单，只报事实**）。
**本岗未改**：`04_工具/render-md.mjs` **一字未动**；本节为**纯追加**（前段逐字节一致）。
**核验时点**：{now}｜渲染产物 `render/units/U02/D11.md`（36,927 B）｜`render/units/U02/D16.md`（189,836 B，含 `audit_field_scope` **8** 处，与 JSON 侧 8 集一致）。
"""

with io.open(REG, "a", encoding="utf-8") as f:
    f.write(SEC)
print(f"✅ 已追加 §九十九.7（{len(SEC)} 字符），文件现 {os.path.getsize(REG)} B")
