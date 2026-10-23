# -*- coding: utf-8 -*-
"""给 D18 注册脚本加「写盘前 schema 自检」＋ 根级 `updated_at` 统一刷新，
并登记本次共享层合法化裁定（Q134／Q135 ＋ U01-R70 ＋ R-028y 总控明派波次）。

背景（2026-10-23 13:42 总控/验收裁决人）：
  ① 事实：`03_规格/schema.json` 的 D18 定义 `additionalProperties: false` 且 properties
     未列 `updated_at`；13:35:14 产出 v1.149 的写入方在 D18 **根级**写了该字段
     ⇒ V1（字段完整性与枚举合法性）**三单元同时报红**
     （`✗ D18 $: 出现未定义字段 [updated_at]（additionalProperties=false）`）。
  ② 裁定（总控明派，Q110①）：**合法化**该字段 —— `03_规格/schema.json` 的 D18
     properties 补 `updated_at`（string，宽松 pattern）＋ `03_规格/字段规格表.md` §三 D18 节补行；
     理由＝多个在用写入脚本每次写盘都会写它，删除路线会让 V1 常红；
     且台账根级时标有审计价值，与 unit_checks 层既有 `updated_at` 口径一致。
     （schema 侧改动已由 `scripts/patch_schema_d18_updated_at.py` 执行完毕。）
  ③ 机制补缺（**真正的根因**）：**共享层交付物写盘前从未对 schema 自检** ——
     写入方可以在不报错的情况下往产物里塞未定义字段，直到 V1 在闸口才炸。
     ⇒ 新立 **Q134**：写盘前必须过 schema 自检（未定义字段 ⇒ 中止写盘）；
     ⇒ 新立 **Q135**：`updated_at` 合法化裁定 ＋ 全写入方统一刷新 ＋
     ⛔ 不得以「先写后补 schema」绕过（补 schema 必须先明派、先登记）。

本补丁做四件事：
  ① 注册脚本加 `enforce_schema_root(d)`：写盘前拿 `03_规格/schema.json` 的
     D18.properties 比对现盘根键，出现未定义字段 ⇒ **中止写盘**（不静默剥离）。
  ② 注册脚本写盘时统一刷新根级 `updated_at`（与另一写入方口径收敛）。
  ③ 登记 Q134／Q135（global_checks）＋ U01-R70（open_issue）。
  ④ 台账登记 R-028y 波次（总控明派·共享层 schema 合法化，总控执行）。

⛔ 只改注册脚本（spec 侧）；D18.json 由注册脚本负责写。
⛔ 注入的中文字符串内一律用「」，⛔ 不得用 ASCII 双引号。
"""
import ast
import io
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "register_d18_v135_ep002_regression.py")


def sub_once(s, old, new, label):
    assert s.count(old) == 1, "锚点异常：%s（命中 %d 次）" % (label, s.count(old))
    return s.replace(old, new)


BLOCK = '''
# ═══════════════════════════════════════════════════════════════════════
# 2026-10-23 13:42 总控轮追加（Q134 写盘前 schema 自检 ＋ Q135 updated_at 合法化
#                              ＋ U01-R70 ＋ R-028y 总控明派波次）
# ═══════════════════════════════════════════════════════════════════════
M_Q134 = "【Q134-SCHEMA-PREWRITE-SELFCHECK】"
M_Q135 = "【Q135-D18-UPDATED-AT-LEGALIZED】"

SPEC_SCHEMA = os.path.normpath(os.path.join(ROOT, "..", "..", "03_规格", "schema.json"))

Q134_SPEC = {
    "marker": M_Q134,
    "match": "共享层交付物写盘前必须过 schema 自检",
    "rule": (
        "**任何共享层交付物（D01–D05／D10／D17／D18）写盘前，必须用 "
        "`03_规格/schema.json` 对自己的根级字段集合做一次自检** —— "
        "① 出现 schema `properties` 未定义的字段 ⇒ **中止写盘并报错**，"
        "⛔ **不得静默剥离**（剥离会把「写入方越权」变成「无人知情地丢字段」）；"
        "② ⛔ **不得以「先写后补 schema」绕过** —— 若确实需要新增字段，"
        "必须先走**共享层变更流程**（总控明派 ＋ 先登记 D18 ＋ 改 schema ＋ 补字段规格表），"
        "再写产物；"
        "③ 自检口径必须与出口校验器（`04_工具/validate.mjs` 的 V1）**同一份 schema**"
        "（Q110②「同一规则只许有一处实现」），⛔ 不得自造一套字段清单。"
    ),
    "detail": (
        "**① 根因（总控 13:40–13:43 实证）** —— **共享层交付物的写入路径从未对 schema 自检**："
        "写入方可以往产物里塞 schema 未定义的字段，**写入时不报错**，"
        "直到出口闸 V1 才炸 —— 这一次就表现为 **V1 三单元同时报红**。"
        "**② 实证链（逐环可查）** —— "
        "① 备份 `_bak_d18_r028_20261023-133503/D18.json`（v1.147）**无** `updated_at`；"
        "② 备份 `_bak_d18_vv1148_20261023-133514/D18.json`（v1.148）**无** `updated_at` "
        "（⇒ 本岗 13:35 那一笔写盘**未引入**该字段）；"
        "③ 备份 `_bak_d18_renum_20261023-133643/D18.json`（v1.149）**有** "
        "`updated_at = 2026-10-23 13:35:14` ⇒ **引入点在 13:35:14 产出 v1.149 的那一笔**；"
        "④ 13:36:43 V1 报错原文：`✗ D18 $: 出现未定义字段 [updated_at]（additionalProperties=false）`，"
        "**U01／U02／U03 三单元同时红**。"
        "**③ 为什么必须补这道自检，而不是只删字段** —— 该字段被**在用写入脚本每次写盘都会写**；"
        "若只删字段，下一次写盘立刻复现 ⇒ **V1 常红**，而闸口常红会让所有单元都无法锁；"
        "⇒ 必须同时做两件事：**① 补自检（机制层）② 补契约（schema 层，见 Q135）**。"
        "**④ 处置已落地** —— 本岗已给本注册脚本加 `enforce_schema_root(d)`："
        "写盘前比对 `03_规格/schema.json` 的 D18.properties，"
        "出现未定义字段 ⇒ **中止写盘**（不静默剥离），"
        "并在本注册脚本写盘时**统一刷新根级 `updated_at`**（与另一写入方口径收敛）。"
        "**⑤ 适用面** —— 本条只针对**共享层**；单元层交付物（D06–D09／D11–D16）"
        "的字段约束由各单元 schema 分支承担，但「写盘前自检」的做法同样适用。"
    ),
    "status": "生效（共享层交付物写盘前必须过 schema 自检；未定义字段即中止写盘）",
    "scope": "全部共享层交付物（D01–D05／D10／D17／D18）的写盘路径",
    "source": "总控/验收裁决人 2026-10-23 13:40–13:43 备份链实证 ＋ 三单元 V1 实跑",
}

Q135_SPEC = {
    "marker": M_Q135,
    "match": "D18 根级 updated_at 的合法化裁定",
    "rule": (
        "**D18 根级 `updated_at` 予以合法化** —— "
        "① `03_规格/schema.json` 的 D18 `properties` 补 `updated_at`"
        "（`type: string`，宽松 pattern —— 接受 `YYYY-MM-DD HH:MM:SS` 与 ISO `T` 分隔两种写法；"
        "**精确 pattern 以 `03_规格/schema.json` 的 D18 定义为准**），"
        "同时接受 `YYYY-MM-DD HH:MM:SS` 与 ISO 两种写法）；"
        "② `03_规格/字段规格表.md` §三 D18 节补该字段一行；"
        "③ **全部 D18 写入方统一刷新该字段**（⛔ 不得有的写、有的不写 —— "
        "同一字段两种写法本身就是分歧）；"
        "④ ⛔ **不得以此条为据新增其他未定义字段** —— "
        "新增字段须逐个走共享层变更流程（Q110① ＋ Q134）。"
    ),
    "detail": (
        "**① 授权层** —— 本条是**总控明派**（D18 Q110①「共享工具/规格改动须总控明派并先登记 D18」，"
        "明派主体＝总控）；schema 侧改动已由 `scripts/patch_schema_d18_updated_at.py` 执行"
        "（带并发守卫 ＋ 备份 ＋ 落盘后回读断言），字段规格表同步补行。"
        "**② 裁定理由（三条）** —— "
        "① **既成事实**：该字段已被在用写入脚本持续写入（v1.149／v1.150 均带），"
        "删除路线会让 V1 每次写盘即复现 ⇒ **闸口常红**，代价高于一次性补齐契约；"
        "② **审计价值**：D18 是台账，根级时标让「这份台账最后是谁什么时候写的」可直接读出；"
        "③ **口径一致**：unit_checks 层早已有 `updated_at`（既有写入脚本写 `u01[\"updated_at\"]`），"
        "根级补齐后层级口径一致。"
        "**③ 为什么不改判据去迁就** —— ⛔ **不得改 V1 判据、放宽 `additionalProperties`、"
        "或把该字段列进豁免名单** —— 那会让「产物可以携带 schema 外字段」这件事被合法化，"
        "V1 就永久失去「根级字段集合受控」这一保证。**正解是补契约，不是松判据。**"
        "**④ 与 Q134 的关系** —— Q134 治**机制**（写盘前自检）；本条治**这一次的具体契约缺口**；"
        "Q119（派生量必须实算）治**数值**；三条同族，都是「产物不得自己长出规则之外的东西」。"
        "**⑤ 遗留动作** —— 企划合规的 V13 落地（`03_规格/schema.json` 增 `vo_type`／`speaker_in_frame`）"
        "**与本条改的是同一份 schema** ⇒ ⛔ 该岗改 schema 时必须**保留**本条补入的 "
        "`updated_at` 定义（并发合并，⛔ 不得整份覆盖）。"
    ),
    "status": "生效（D18 根级 updated_at 已入 schema ＋ 字段规格表；全写入方统一刷新）",
    "scope": "D18 共享层交付物的根级字段集合",
    "source": "总控/验收裁决人 2026-10-23 13:41 明派并执行（scripts/patch_schema_d18_updated_at.py）",
}

NEW_GLOBALS.append(Q134_SPEC)
NEW_GLOBALS.append(Q135_SPEC)

R70 = {
    "id": "U01-R70",
    "marker": "【U01-R70-V1-ROOT-EXTRA-FIELD】",
    "match": "D18 根级出现 schema 未定义字段 updated_at ⇒ V1 三单元同时报红",
    "issue": (
        "**D18 根级被写入 schema 未定义的 `updated_at` 字段 ⇒ V1（字段完整性与枚举合法性）"
        "在 U01／U02／U03 三个单元同时报红** —— 引入点为 **13:35:14 产出 v1.149 的那一笔写盘**"
        "（本岗 13:40–13:43 用备份链逐环坐实）。"
    ),
    "owner": "共享层 schema（总控明派本岗执行）＋ 全部 D18 写入方",
    "blocks": "**不拦任何交付物本身，但直接卡死三个单元的出口闸**（V1 error ⇒ 单元不得锁）",
    "priority": "高",
    "status": "已处置·已复验（13:41 schema ＋ 字段规格表已补；三单元 V1 恢复 PASS）",
    "detected_by": "总控/验收裁决人 13:36 闸态采样 → 13:40 备份链取证 ＋ V1 报错原文取证",
    "note": (
        "**① 取证链（逐环可查，非转述）** —— "
        "`_bak_d18_r028_20261023-133503`（v1.147）无 `updated_at`；"
        "`_bak_d18_vv1148_20261023-133514`（v1.148）无 `updated_at` "
        "（⇒ 本岗 13:35 的写盘未引入）；"
        "`_bak_d18_renum_20261023-133643`（v1.149）有 `updated_at = 2026-10-23 13:35:14` "
        "⇒ **引入点＝产出 v1.149 的那一笔**；"
        "13:36:43 V1 报错原文 `✗ D18 $: 出现未定义字段 [updated_at]（additionalProperties=false）`。"
        "**② 处置（两步，已完成）** —— "
        "① **契约层**：`03_规格/schema.json` 的 D18 `properties` 补 `updated_at`"
        "（string ＋ 宽松 pattern），`03_规格/字段规格表.md` §三 D18 节补行"
        "（脚本 `scripts/patch_schema_d18_updated_at.py`，带并发守卫 ＋ 备份 ＋ 回读断言）；"
        "② **机制层**：D18 写盘路径加 `enforce_schema_root(d)` —— "
        "写盘前比对 schema 的 D18.properties，出现未定义字段 ⇒ **中止写盘**（不静默剥离）。"
        "**③ 复验** —— 13:41 复跑三闸：**V1 三单元均恢复 PASS**"
        "（U01 error 5／U02 error 6／U03 error 5，余下全部为 V12 白模构图）。"
        "**④ 明确不做的事** —— ⛔ **未改 V1 判据、未放宽 `additionalProperties`、"
        "未把该字段列进任何豁免名单**（那会把「产物可携带 schema 外字段」合法化）；"
        "⛔ 未碰 V1–V12 任何语义。"
    ),
}

WAVE3 = {
    "wave": "R-028y",
    "at": "2026-10-23 13:41",
    "items": [
        {
            "id": "R-028y-1",
            "to": "（总控本岗执行 · 非派单）",
            "scope": (
                "**共享层明派：把 D18 根级 `updated_at` 合法化 ＋ 给 D18 写盘路径加 schema 自检** —— "
                "起因：13:35:14 产出 v1.149 的那一笔在 D18 根级写了 schema 未定义的 `updated_at` "
                "⇒ V1 三单元同时报红。处置：① `03_规格/schema.json` 的 D18 properties 补 "
                "`updated_at`（string ＋ 宽松 pattern）；② `03_规格/字段规格表.md` §三 D18 节补行；"
                "③ D18 写盘前加 schema 自检（未定义字段 ⇒ 中止写盘，不静默剥离）。"
                "⛔ 未改 V1 判据、未放宽 `additionalProperties`、未新增豁免。"
            ),
            "request_id": "（总控明派 · 总控执行）",
            "task_id": "scripts/patch_schema_d18_updated_at.py",
            "state": "已执行·已复验（13:41 三单元 V1 恢复 PASS）",
        },
    ],
}
'''


def main():
    with io.open(P, "r", encoding="utf-8") as f:
        s = f.read()

    # ① 注入块（插在 def find_oissue 之前）
    anchor = "def find_oissue(d, oid):"
    assert s.count(anchor) == 1, "find_oissue 锚点异常"
    s = s.replace(anchor, BLOCK.strip() + "\n\n\n" + anchor)

    # ② open_issues 注册元组扩项（R70）
    old = "for spec in (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63):"
    new = "for spec in (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63, R70):"
    assert s.count(old) == 1, "open_issues 注册元组锚点异常"
    s = s.replace(old, new)

    old2 = ('n_bf += backfill_markers(d, (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63), '
            '"open_issues", "note")')
    new2 = ('n_bf += backfill_markers(d, (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63, R70), '
            '"open_issues", "note")')
    assert s.count(old2) == 1, "backfill_markers 锚点异常"
    s = s.replace(old2, new2)

    # ③ schema 自检函数 + 根级 updated_at 刷新
    anchor3 = "def assert_marker_ids_aligned(d):"
    assert s.count(anchor3) == 1, "assert_marker_ids_aligned 锚点异常"
    fn = '''def enforce_schema_root(d):
    """写盘前自检：现盘根级字段集合必须是 schema 的 D18.properties 的子集。

    Q134：出现未定义字段 ⇒ **中止写盘**（⛔ 不静默剥离 —— 剥离会把「写入方越权」
    变成「无人知情地丢字段」）。口径与出口校验器 V1 同一份 schema（Q110②）。
    """
    try:
        sc = json.load(open(SPEC_SCHEMA, encoding="utf-8"))
        allowed = set((sc.get("D18") or {}).get("properties", {}).keys())
    except Exception as exc:                       # schema 读不到 ⇒ 不放行
        print(f"❌ 读不到 schema（{SPEC_SCHEMA}）：{exc} ⇒ 中止写盘")
        return False
    extra = sorted(set(d.keys()) - allowed)
    if extra:
        print(f"❌ D18 根级出现 schema 未定义字段 {extra}（additionalProperties=false）"
              f" ⇒ 中止写盘（Q134）")
        return False
    return True


'''
    s = s.replace(anchor3, fn + anchor3)

    # 写盘前：schema 自检 + 根级 updated_at 刷新
    old4 = '''    if not assert_marker_ids_aligned(d):
        return 2'''
    new4 = '''    if not assert_marker_ids_aligned(d):
        return 2
    if not enforce_schema_root(d):
        return 2
    # 根级 updated_at 统一刷新（Q135：全写入方口径收敛）
    d["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")'''
    assert s.count(old4) == 1, "写盘前锚点异常"
    s = s.replace(old4, new4)

    # ④ R-028y 波次台账
    anchor5 = ("    # ── ④′ 第二派活波次 R-028x（幂等：wave 已存在则按 item id 增量 upsert） ──")
    assert s.count(anchor5) == 1, "R-028x 波次锚点异常"
    w3 = '''    # ── ④″ 第三派活波次 R-028y（总控明派 · 总控执行） ──────────────────────
    w3_existed = any(w.get("wave") == WAVE3["wave"] for w in ledger)
    if w3_existed:
        w3 = next(x for x in ledger if x.get("wave") == WAVE3["wave"])
        have3 = {i.get("id") for i in w3.get("items", [])}
        for spec in WAVE3["items"]:
            cur = next((i for i in w3.get("items", []) if i.get("id") == spec["id"]), None)
            if cur is None:
                w3.setdefault("items", []).append(spec)
                added.append(f"{WAVE3['wave']}.{spec['id']}")
                print(f"   ➕ 台账补录 {WAVE3['wave']}.{spec['id']}")
                continue
            for k in ("note", "state", "scope", "request_id", "task_id"):
                if k in spec and cur.get(k) != spec[k]:
                    cur[k] = spec[k]
                    added.append(f"{WAVE3['wave']}.{spec['id']}.{k}")
                    print(f"   ✏️ 台账更新 {WAVE3['wave']}.{spec['id']}.{k}")
        skipped.append(f"wave {WAVE3['wave']}")
    else:
        ledger.append(WAVE3)
        for i in WAVE3["items"]:
            print(f"   ➕ 派活 {WAVE3['wave']}.{i['id']} → {i['to']}")

'''
    s = s.replace(anchor5, w3 + anchor5)

    ast.parse(s)
    with io.open(P, "w", encoding="utf-8") as f:
        f.write(s)
    print("✅ 已注入 Q134／Q135／U01-R70／R-028y ＋ schema 自检 ＋ updated_at 刷新，语法 OK")
    print("   字节数 =", len(s.encode("utf-8")))


if __name__ == "__main__":
    main()
