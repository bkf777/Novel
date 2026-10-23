# -*- coding: utf-8 -*-
"""总控明派·共享层变更：把 D18 根级 `updated_at` 合法化 ＋ 补字段规格表一行。

裁定依据（2026-10-23 13:42 总控/验收裁决人）：
  · 事实：`03_规格/schema.json` 的 D18 定义 `additionalProperties: false`，
    且 properties 未列 `updated_at`；而 13:35:14 产出 v1.149 的写入方在 D18 **根级**
    写了 `updated_at` ⇒ V1（字段完整性与枚举合法性）**三个单元同时报红**：
    `✗ D18 $: 出现未定义字段 [updated_at]（additionalProperties=false）`。
  · 为何合法化而不是删字段：多个在用写入脚本**每次写盘都会写该字段**，
    删除路线会让 V1 常红（每次写盘即复现），代价高于一次性把契约补齐；
    且 D18 是台账，根级时标有审计价值，与 unit_checks 层既有 `updated_at` 口径一致。
  · 授权层：共享层规格改动须**总控明派并先登记 D18**（Q110①）——
    本岗为总控，本单即明派执行；D18 登记见 Q134／U01-R70。

⛔ 写入前做并发守卫（读盘 sha/size/mtime → 改 → 落盘前复核 → 不一致即中止）。
⛔ 本脚本只改 `03_规格/schema.json` ＋ `03_规格/字段规格表.md` 两处。
"""
import hashlib
import io
import json
import os
import shutil
import sys
import time

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂"
SCHEMA = os.path.join(ROOT, "03_规格", "schema.json")
SPEC_MD = os.path.join(ROOT, "03_规格", "字段规格表.md")
BAK = os.path.join(ROOT, "03_规格", "_bak_schema_d18_updated_at_" +
                   time.strftime("%Y%m%d-%H%M%S"))


def fp(p):
    st = os.stat(p)
    return (os.path.getsize(p), st.st_mtime,
            hashlib.sha256(open(p, "rb").read()).hexdigest())


def main():
    s0 = fp(SCHEMA)
    m0 = fp(SPEC_MD)
    src = io.open(SCHEMA, encoding="utf-8").read()

    if '"updated_at"' in src[src.find('"D18"'):]:
        print("⏭ D18 定义里已有 updated_at ⇒ 无需变更，退出")
        return 0

    old = ('      "open_issues": {\n'
           '        "type": "array",\n'
           '        "items": {\n'
           '          "type": "object"\n'
           '        }\n'
           '      }\n'
           '    }\n'
           '  }\n'
           '}')
    new = ('      "open_issues": {\n'
           '        "type": "array",\n'
           '        "items": {\n'
           '          "type": "object"\n'
           '        }\n'
           '      },\n'
           '      "updated_at": {\n'
           '        "type": "string",\n'
           '        "pattern": "^\\\\d{4}-\\\\d{2}-\\\\d{2}[ T]\\\\d{2}:\\\\d{2}(:\\\\d{2})?$",\n'
           '        "description": "台账根级时标：D18 最后一次写盘时刻（YYYY-MM-DD HH:MM:SS 或 ISO）"\n'
           '      }\n'
           '    }\n'
           '  }\n'
           '}')
    assert src.count(old) == 1, "D18 properties 尾块锚点命中 %d 次" % src.count(old)
    out = src.replace(old, new)

    # 落盘前复核（并发守卫）
    if fp(SCHEMA) != s0:
        print("❌ schema.json 在读盘后被改动 ⇒ 中止")
        return 2
    if fp(SPEC_MD) != m0:
        print("❌ 字段规格表.md 在读盘后被改动 ⇒ 中止")
        return 2

    # 自检：改后的 JSON 必须可解析，且 D18.properties 确实含 updated_at
    sc = json.loads(out)
    assert "updated_at" in sc["D18"]["properties"], "D18.properties 未含 updated_at"
    assert sc["D18"].get("additionalProperties") is False, "D18 additionalProperties 口径变了"

    os.makedirs(BAK, exist_ok=True)
    shutil.copy2(SCHEMA, os.path.join(BAK, "schema.json"))
    shutil.copy2(SPEC_MD, os.path.join(BAK, "字段规格表.md"))

    # ── 字段规格表 D18 节补一行 ────────────────────────────────────────
    md = io.open(SPEC_MD, encoding="utf-8").read()
    md_old = ("### D18 交付与质检清单（共享）\n"
              "`unit_checks[]` `global_checks[]` `open_issues[]`\n")
    md_new = ("### D18 交付与质检清单（共享）\n"
              "`unit_checks[]` `global_checks[]` `open_issues[]` `updated_at`（根级时标，"
              "YYYY-MM-DD HH:MM:SS 或 ISO；由写盘方在每次落盘时刷新）\n")
    assert md.count(md_old) == 1, "字段规格表 D18 节锚点命中 %d 次" % md.count(md_old)
    md_out = md.replace(md_old, md_new)

    with io.open(SCHEMA, "w", encoding="utf-8") as f:
        f.write(out)
    with io.open(SPEC_MD, "w", encoding="utf-8") as f:
        f.write(md_out)

    # 落盘后回读断言
    sc2 = json.load(open(SCHEMA, encoding="utf-8"))
    assert "updated_at" in sc2["D18"]["properties"], "回读失败：D18.properties 无 updated_at"
    md2 = io.open(SPEC_MD, encoding="utf-8").read()
    assert "`updated_at`（根级时标" in md2, "回读失败：字段规格表未补行"
    print("✅ schema.json D18 已补 updated_at；字段规格表 §三 D18 节已补行")
    print("   schema %d B sha16=%s | 字段规格表 %d B sha16=%s"
          % (os.path.getsize(SCHEMA), hashlib.sha256(open(SCHEMA, "rb").read()).hexdigest()[:16],
             os.path.getsize(SPEC_MD), hashlib.sha256(open(SPEC_MD, "rb").read()).hexdigest()[:16]))
    print("   备份 →", os.path.relpath(BAK, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
