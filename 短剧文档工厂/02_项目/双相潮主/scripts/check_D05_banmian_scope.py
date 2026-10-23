#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
check_D05_banmian_scope.py —— 故事架构：「板面／板背」**敲击面口径机器闸**（只读，2026-10-23）

**为什么有这支闸**：2026-10-23 U02-R32 闭环过程中，声音设计在 `units/U02/D15.json`
ep009 `mix_notes` 写过「钢架落地与**板面敲击**属拟音层」，而同文件 `sfx` 25.6s 写的是
「指节敲击**板背**的两声闷响」—— **同一事件、同一文件、两个面**。上游判「非分歧」
（机器可查的 `sfx` 层已对齐基准），但**写法冲突客观存在**：下游执行者若照 `mix_notes`
准备声音，会理解成「敲亮着屏的那一面」，与 `sfx` 事件描述相反。
声音设计已收敛为「板背敲击」（D15 v1.2）并升版；**本闸把这条口径固化成可复跑的机器断言**，
防止任一交付物再次把「板面」用作敲击面。

**全链现行口径（本岗逐条独立复核，7/7 一致）**：
  · 「板面」＝**板的正面／屏幕面**（朝向、视线落点）—— D11 U02 v1.6 三处 ＋ D12 U02 v1.0 四处
  · 敲击面一律写「**板背**」或「**背面**」—— D07／D08／D11／D12／D15 已同向
  · → 本闸 G5 把「正面义的板面存量」**锁死为 3（D11）／4（D12）**，防止有人连正面义的一并改掉
    （这正是声音设计回执第六条「勿误改项」要求的固化）

**断言清单（G1–G8，共 13 条）**：
  G1 可解析；G2 D05 `glossary` 条数（承 S20 口径，本轮未新增词条）；
  G3 **「板面」用作敲击面 → 全库 0 命中**（本闸主判据，跨 全部交付物 JSON ＋ 源素材）；
  G4 基准链在位：D15 U02 ep009 `mix_notes` 必含「板背敲击」＋「敲击面为数据板背面」；
  G5 正面义存量锁定：D11「板面」== 3、D12「板面」== 4、D15 U02「板面」== 0；
  G6 剧本层基准：D07 U02 ep009 段3 ＝「指节敲了两下背面」、D08 U02 正文含同一事实；
  G7 回归面：「低阶律条」**活跃写法**全库 0 命中（承 B10，防「律条」档位写法回归）——
     ⚠️ 扫描面**排除 D05 自身的词条注册位** `glossary[*].forbidden_synonyms`：
     S31 ④／OPS-23 面② 起该词**必须**出现在那里（那是它的注册位，不是违规写法；
     上游 V5 亦整份豁免 D05：`rules.mjs` `if (docId === 'D05') continue`）。
     本岗在 D05 v1.4 落地后踩中此坑：G7 把注册位误判成违规 → **实测 1 命中 = 假红**。
     故 D05 走**结构化遍历**跳过该键（比 V5 的整份豁免更严：D05 其他字段仍受检）；
     ⚠️ **2026-10-23 09:3x 判据边界二次精确化**（D05 v1.5 落地后第二次假红）：
     D05 v1.5 的 `glossary[律条].definition` 新增「未命名期台词口径」段，**字面列举**了
     `forbidden_synonyms` 全列（骨签／规则石／低阶律条）⇒ 该词条**自身 definition 内的
     自引述**又被打成违规（命中位＝`D05.json glossary/34/definition`，G7 由 13/13 退化为 12/13）。
     ⇒ 豁免面**精确化**为：**某词条自身 `forbidden_synonyms` 的字面，在该词条自身
     `definition` 内的引述 ＝ 注册位引述，豁免**；而**其他文档／其他字段／其他词条的
     `definition` 内出现该词，一律仍判命中**（不跨词条豁免、不整份豁免 D05）。
     ⇒ **D05 内容零改动、version 不变、字节不变**（不制造新指针漂移）；
     按 **Q62**（放宽判据必须配负测）配 3 例负测，见文件末尾「负测」说明。
  G7b 配套正向断言：D05 律条词条 `forbidden_synonyms` **确已注册**「低阶律条」
     （防止豁免面把「注册缺失」一起遮掉）；
  G8 「守卫队长」回源在位（源素材逐集内容概述 ep006「一击震退守卫队长使其单膝跪地」
     ↔ U01 D07 ep006 `must_happen` 逐字采用；G12-a 缺口仅剩「D04 是否补编号角色」）。
  G3b 受检面非空（防空集恒真：豁免面不得把受检文本清成 0）。

  ⚠️ **2026-10-23 10:3x 判据边界第三次精确化（G3 留痕子树豁免）**
     —— 触发事件：声音设计 2026-10-23 10:32:34 把 `units/U02/D16.json` 升到 v1.6
        （208,578 → 232,059 B），新增的 `episodes[].subtitle_style.subtitle_sync_audit.
        d15_version_history.v1.2` 字段写的是**版本订正留痕**：
        「仅改 ep009 `mix_notes` 一条措辞（「板面敲击」→「板背敲击」）＋ version …」
        —— 其中「板面敲击」是**如实引述订正前的旧写法**（与 D18 台账里「敲板面的两下」→「敲板背的两下」
        同一性质），**不是活跃违规写法**；而原 G3 走**原文全文扫描**（不看字段职责）⇒ 命中 8 处假红。
     —— 处置＝**判据边界精确化，零内容改动**（不要求声音设计改任何交付物）：
        ① G3 改为**结构化遍历**，跳过**「版本历史／订正留痕」类子树**（键名以 `version_history` 结尾）；
        ② 豁免**精确到子树**，不整份排除任何交付物（D18 的整份排除是台账特例，不推广）；
        ③ **活跃内容面照旧全查**（字幕行、mix_notes、must_happen、正文等一律命中即报）；
        ④ 配 **Q62 负测三腿**（`scripts/selftest_banmian_G3_exemption.py`，/tmp 沙箱、真盘零写入）：
           腿1 基线须 rc=0 且受检面 >0；腿2 活跃面注入「板面敲击」须 rc≠0 且命中路径**不在**留痕子树；
           腿3 留痕子树内写入须 rc=0（豁免面生效）。
     —— **同形异指原则**：如实引述旧写法／缺陷说明文字／登记表引用一律保留，闸只判活跃面。

  ⚠️ **2026-10-23 11:0x 判据边界第四次精确化（G7 统一到 G3 的同一活跃面）**
     —— 触发事件：声音设计 10:4x 回执⑤ 指出本闸受检面**硬编码单元名单**（U03 漏检，已修），
        并实测发现 `project.json` 的**登记台账**引述进受检面 ⇒ 本岗回查发现**两条规则活跃面不一致**：
        G3 走结构化遍历（吃留痕/登记豁免），**G7 走原文全文计数**（不吃任何豁免）
        ⇒ `project.json` 的 `decisions/S31`·`S32`（引述「低阶律条」3 处）必然触发 G7
        ⇒ **G7 恒红**（沙箱实测 rc=1、命中 1）。
     —— 处置＝**G7 改为结构化遍历**，与 G3 共用同一活跃面（留痕子树 ＋ 登记台账子树豁免），
        另保留 D05 侧两项既有豁免（`forbidden_synonyms` 注册位 ＋ 词条自身 definition 自引述）；
        **登记台账豁免面扩到 `gaps_resolved` ＋ `decisions` 两个子树，且按文件名精确到 `project.json`**
        （取证：31 份交付物中 0 处出现这两个键 ⇒ 豁免面不触及任何交付物内容）。
     —— **G3 判据保持不动**：「板面」**不在**任何词条的 `forbidden_synonyms`（唯一注册位是
        `glossary[律条].forbidden_synonyms` 里的「低阶律条」）⇒ G3 **无注册位可豁免** ⇒ 不动它，
        避免无负测支撑的判据放宽（Q62）。
     —— 按 **Q62** 配负测腿8/9/10（`scripts/selftest_banmian_G3_exemption.py`）：
        腿8 登记语境放行（`project.json → decisions` 注入「低阶律条」须 rc=0 且 G7 ✅）；
        腿9 同文件**兄弟键必拦**（`project.json → source_of_truth` 注入须 G7 ❌ ⇒ 不整份排除）；
        腿10 豁免**不外溢到交付物**（交付物内 `decisions` 键注入须 G7 ❌ ⇒ 豁免按文件名精确）。

  ⚠️ **已知边界（G7 登记台账豁免的语义边界）**：登记台账语境按「如实引述」豁免 ⇒ 若将来出现
     「**把被裁的违规写法登记为现行口径**」的记录（如 `decisions` 写下「自即日起改用低阶律条」），
     本闸不会拦。触发条件：出现此类记录 ⇒ 须由企划合规/总控**显式裁决**后再收口豁免面或改判据。

用法：python3 scripts/check_D05_banmian_scope.py --project 02_项目/双相潮主 \
        [--source /path/to/01_漫剧策划] [--dry-run]
退出码：0 = 全部通过；1 = 有断言失败。
"""
import argparse
import json
import os
import re
import sys

# 「板面」用作敲击面：板面 前后 4 字内出现敲击类动词
STRIKE_VERBS = r"(敲|击|叩|砸|弹|撞|拍)"
STRIKE_PAT = re.compile(STRIKE_VERBS + r".{0,4}板面|板面.{0,4}" + STRIKE_VERBS)


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# 「版本历史／订正留痕／同步变更留痕」子树判定：
#   ① 键名以 version_history 结尾（覆盖 d15_version_history / version_history 等命名变体；
#      职责＝记录各版本改了什么）
#   ② 键名恰为 sync_records（职责＝**同步/变更留痕**：basis 事件溯源 ＋ rows old→new 时码对照
#      ＋ changes 逐版本变更记录；**会逐字引述订正前的旧写法**，与 ① 同族）
#      —— 2026-10-23 10:5x 声音设计主动知会并请求裁定，本岗裁定：**纳入留痕面**。
#      裁定理由：① 语义同族（记录「改了什么」而非「现在是什么」）；
#      ② 现状**无雷**（四件交付物中「板面」命中除已豁免的 8 处外全为 0）⇒ 纳入豁免**不掩盖现存违规**；
#      ③ 不纳入则将来一次「板面→板背」同步会在 `changes` 里逐字写下旧写法 ⇒ **重演今天这次假红**。
#      ⚠️ 豁免**精确到 `sync_records` 这一层**，**不豁免其父键 `subtitle_sync_audit`**
#      （父键下还有 `d16_out_matches_contract` 等活跃字段必须照查）。
def is_history_key(k: str) -> bool:
    return k == "version_history" or k.endswith("_version_history") or k == "sync_records"


# 「缺口登记台账语境」子树判定：键名 ∈ {gaps_resolved, decisions}，且**文件为 project.json**
#   （`project.json` 是**项目总账**：`gaps_resolved`＝缺口消解记录（25 条）、`decisions`＝决策登记簿（68 条），
#     两者都逐字引述**被裁定的旧写法**或**被裁词条本身**，与 D18 的 `open_issues`/`global_checks` 同性质
#     ⇒ 登记语境，不判缺陷）
#   —— 2026-10-23 10:5x 声音设计实测发现：以 `--source` 指向项目根时 `project.json` 进入受检面
#      并命中（G25 `gaps_resolved/23` 引述「板面」；`decisions/S31`·`S32` 引述「低阶律条」）。
#      本岗裁定：**按登记台账语境豁免这两个子树**，**不整份排除 `project.json`**
#      （其 `project`/`source_of_truth`/`terminology`/`characters`/`units` 等仍是活跃面）。
#   ⚠️ **按文件名精确到 project.json**：取证（10:5x）31 份交付物中 **0 处**出现 `gaps_resolved`/`decisions` 键
#      ⇒ 豁免面**不触及任何交付物内容**；将来若某交付物引入同名键，本闸**仍照查不豁免**
#      （负测腿10 以「交付物内 `decisions` 键注入必须被拦」锁死这一条）。
REGISTRY_KEYS = ("gaps_resolved", "decisions")
REGISTRY_FILES = ("project.json",)


def is_registry_key(k: str, fname: str = "") -> bool:
    return fname in REGISTRY_FILES and k in REGISTRY_KEYS


def active_text(node, path=(), out=None, stats=None, fname="", d05=False):
    """结构化取「活跃文本」：跳过版本历史/订正留痕/同步变更留痕子树、缺口登记台账子树，
    （仅 D05）再跳过词条**注册位** `forbidden_synonyms`。

    返回 ( [(路径, 文本), ...], stats )，stats = {"history": n, "registry": n, "registration": n}。
    留痕子树里的旧写法是**如实引述**，不判缺陷；路径随文本返回，供负测断言
    「命中位落在活跃面而非留痕/登记子树」。

    ⚠️ `d05=True` 只用于 **G7**（G7 的禁词「低阶律条」**确已注册**在 `glossary[律条].forbidden_synonyms`
       ⇒ 注册位必须豁免，否则假红）；**G3 不传 d05**（「板面」不在任何词条的 `forbidden_synonyms`
       ⇒ G3 **无注册位可豁免**，判据保持不动，见文件头「已知边界」条）。
    """
    if out is None:
        out, stats = [], {"history": 0, "registry": 0, "registration": 0}
    if isinstance(node, str):
        out.append(("/".join(path), node))
    elif isinstance(node, list):
        for i, n in enumerate(node):
            active_text(n, path + (str(i),), out, stats, fname, d05)
    elif isinstance(node, dict):
        for k, v in node.items():
            if is_history_key(k):
                stats["history"] += 1
                continue
            if is_registry_key(k, fname):
                stats["registry"] += 1
                continue
            if d05 and k == "forbidden_synonyms":
                stats["registration"] += 1
                continue
            active_text(v, path + (k,), out, stats, fname, d05)
    return out, stats


def scan_files(root, source):
    """**交付物** JSON 全集 ＋ 源素材（若给到）。

    ⚠️ **受检面按磁盘实况动态发现**（2026-10-23 10:5x 修正，本岗自闸缺陷）：
    原实现硬编码 `("shared", "units/U01", "units/U02")` ⇒ **新开工单元（U03 起）完全不在受检面**，
    构成**漏检面**（与同轮修掉的假红同源、**方向相反**：假红＝误报，漏检＝漏报）。
    声音设计以沙箱注入实测确证：向 U03 D07 活跃面注入违规，闸仍「命中 0｜断言全绿｜exit 0」
    ⇒ **已落单元对 G3／G7 两条规则完全无感**（两者共用同一份 `files`）。
    ⇒ 现改为**遍历 `units/` 下全部单元目录**；并加 **G3c 覆盖度自证断言**
      （受检交付物文件数必须 == 磁盘实况）⇒ **防再犯**（不可能再悄悄漏掉下一个单元）。
    ⭐ 代价透明：新增单元进受检面后，若其产物含旧写法，G3/G7 会**首次**报出 —— 那是**既有数据的真实状态**、
      不是新缺陷；但「**命中 ≠ 缺陷**」，须按「同形异指」逐处分类（引述/登记留痕 vs 活跃违规）。

    ⚠️ **`shared/D18.json` 排除在外**：D18 是缺陷/派单台账，其中大量「敲板面」「低阶律条」
    是**引用旧缺陷原文的历史留痕**（「敲板面的两下」→「敲板背的两下」的订正记录、U02-R32 的
    issue 描述、F04 伏笔描述等），不是活跃违规。
    ——「**全文扫描命中数 ≠ 缺陷数**」：命中必须回查「是代码还是被引用的内容」；
    D18 侧的同词命中另行上报企划合规，由其在自己的单点文件里收敛。
    """
    out = []
    subs = ["shared"]
    units_root = os.path.join(root, "units")
    if os.path.isdir(units_root):
        subs += ["units/" + u for u in sorted(os.listdir(units_root))
                 if os.path.isdir(os.path.join(units_root, u))]
    for sub in subs:
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json"):
                continue
            if sub == "shared" and name == "D18.json":
                continue          # 台账引用性文本，排除
            out.append(os.path.join(d, name))
    if source and os.path.isdir(source):
        for name in sorted(os.listdir(source)):
            if name.endswith(".json"):
                out.append(os.path.join(source, name))
    return out


def delivery_inventory(root):
    """独立于 `scan_files` 的**磁盘实况**盘点（供 G3c 覆盖度自证：两种算法必须一致）。

    返回 (交付物文件列表, 交付物目录集合)。`project.json` 等非交付物不在其中。
    """
    files, dirs = [], set()
    sd = os.path.join(root, "shared")
    if os.path.isdir(sd):
        dirs.add(sd)
        files += [os.path.join(sd, n) for n in sorted(os.listdir(sd))
                  if n.endswith(".json") and n != "D18.json"]
    ud = os.path.join(root, "units")
    if os.path.isdir(ud):
        for u in sorted(os.listdir(ud)):
            uu = os.path.join(ud, u)
            if not os.path.isdir(uu):
                continue
            dirs.add(uu)
            files += [os.path.join(uu, n) for n in sorted(os.listdir(uu)) if n.endswith(".json")]
    return files, dirs


def find_ep(doc, key="ep"):
    for e in doc.get("episodes", []):
        if str(e.get(key)) == "9":
            return e
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--source", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    src = os.path.abspath(args.source) if args.source else None
    res = []

    def ok(label, cond, detail=""):
        res.append((bool(cond), label, detail))
        return bool(cond)

    # G1 可解析
    d05p = os.path.join(root, "shared/D05.json")
    if not ok("G1 D05 可解析", os.path.isfile(d05p)):
        for l, _, d in res:
            print(f"{'✅' if l else '❌'} {l} {d}")
        return 1
    d05 = load(d05p)
    print(f"  ✅ G1 D05 可解析 —— version={d05.get('version')}")

    # G2 glossary 条数
    gl = d05.get("glossary", [])
    ok("G2 D05 glossary 条数 == 42（承 S20 口径，本轮未新增词条）", len(gl) == 42, f"实测 {len(gl)}")

    # G3 「板面」用作敲击面 → 0 命中（**只判活跃面**：D18 台账整份排除 ＋ 留痕/登记语境子树排除）
    files = scan_files(root, src)
    hits = []
    scanned_chars = 0
    skipped_nodes = 0
    skipped_reg = 0
    for p in files:
        raw = open(p, encoding="utf-8").read()
        try:
            doc = json.loads(raw)
        except Exception:
            doc = None
        if doc is None:
            texts = [("<raw>", raw)]
            st = {"history": 0, "registry": 0, "registration": 0}
        else:
            texts, st = active_text(doc, fname=os.path.basename(p))
        skipped_nodes += st["history"]
        skipped_reg += st["registry"]
        scanned_chars += sum(len(t) for _, t in texts)
        for tpath, txt in texts:
            for m in STRIKE_PAT.finditer(txt):
                hits.append((os.path.basename(p), tpath, m.group(0)))
    hit_detail = "｜" + "；".join(f"{f} {p_}「{g}」" for f, p_, g in hits[:5]) if hits else ""
    ok("G3 「板面」用作敲击面 → 交付物全库 0 命中（D18 台账引用性文本 ＋ 版本历史/订正留痕/同步变更留痕/缺口登记子树已排除）",
       len(hits) == 0,
       f"受检文件 {len(files)}（不含 D18）｜活跃面受检 {scanned_chars} 字符｜"
       f"留痕子树豁免 {skipped_nodes} 个｜登记台账豁免 {skipped_reg} 个｜命中 {len(hits)}" + hit_detail)
    ok("G3b 受检面非空（防空集恒真：豁免面不得把受检文本清成 0）", scanned_chars > 0,
       f"活跃面受检 {scanned_chars} 字符｜留痕豁免 {skipped_nodes} 个｜登记台账豁免 {skipped_reg} 个")

    # G3c 受检面覆盖度自证（防漏检再犯）：受检交付物必须 == 磁盘实况，两种独立算法一致
    disk_files, disk_dirs = delivery_inventory(root)
    scanned_deliv = [p for p in files if os.path.dirname(p) in disk_dirs]
    missing = sorted(set(disk_files) - set(scanned_deliv))
    extra = sorted(set(scanned_deliv) - set(disk_files))
    units_seen = sorted(os.path.basename(d) for d in disk_dirs
                        if os.path.basename(d).startswith("U"))
    ok("G3c 受检面覆盖磁盘全集（防漏检：不得硬编码单元名单）",
       (not missing) and (not extra) and len(scanned_deliv) == len(disk_files),
       f"磁盘交付物 {len(disk_files)} 份（shared 去 D18 ＋ units/* 全量）｜受检 {len(scanned_deliv)} 份｜"
       f"漏扫 {len(missing)}｜多扫 {len(extra)}｜覆盖单元 {units_seen}"
       + (f"｜漏扫清单 {[os.path.relpath(m, root) for m in missing[:5]]}" if missing else ""))

    # G4 收敛文案在位
    d15 = load(os.path.join(root, "units/U02/D15.json"))
    ep9 = find_ep(d15)
    mn = (ep9 or {}).get("mix_notes", [])
    tail = mn[-1] if mn else ""
    ok("G4 D15 U02 ep009 mix_notes 末条含「板背敲击」", "板背敲击" in tail,
       f"实测：{tail[-60:] if tail else '（无）'}")
    ok("G4 D15 U02 ep009 mix_notes 末条含「敲击面为数据板背面」", "敲击面为数据板背面" in tail)

    # G5 正面义存量锁定
    d11s = open(os.path.join(root, "units/U02/D11.json"), encoding="utf-8").read()
    d12s = open(os.path.join(root, "units/U02/D12.json"), encoding="utf-8").read()
    d15s = open(os.path.join(root, "units/U02/D15.json"), encoding="utf-8").read()
    n11, n12, n15 = d11s.count("板面"), d12s.count("板面"), d15s.count("板面")
    ok("G5 D11 U02「板面」== 3（正面义存量锁定，勿误改）", n11 == 3, f"实测 {n11}")
    ok("G5 D12 U02「板面」== 4（正面义存量锁定，勿误改）", n12 == 4, f"实测 {n12}")
    ok("G5 D15 U02「板面」== 0（已收敛）", n15 == 0, f"实测 {n15}")

    # G6 基准链
    d07 = load(os.path.join(root, "units/U02/D07.json"))
    d08 = load(os.path.join(root, "units/U02/D08.json"))
    d07s = json.dumps(d07, ensure_ascii=False)
    d08s = json.dumps(d08, ensure_ascii=False)
    ok("G6 D07 U02 含基准句「指节敲了两下背面」", "指节敲了两下背面" in d07s)
    ok("G6 D08 U02（剧本层）含基准事实「指节敲了两下背面」", "指节敲了两下背面" in d08s)

    # G7 回归面 —— ⚠️ 扫描面须排除 D05 自身的**词条注册位**（见文件头说明）
    #   「低阶律条」自 S31 ④／OPS-23 面② 起**必须**出现在 D05 `glossary[律条].forbidden_synonyms`
    #   —— 那是**注册位**，不是活跃违规写法。故：不能整份排除 D05（会漏 D05 其他字段的同词违规），
    #   也不能原样计入（注册位被误判 → 假红）。做法：D05 走结构化遍历、跳过 `forbidden_synonyms` 键；
    #   其余交付物（含源素材）走原样文本计数。
    #   ⚠️ **2026-10-23 11:0x 判据边界第四次精确化（G7 与 G3 统一到同一活跃面）**：
    #      原实现里**只有 G3** 吃留痕/登记豁免，**G7 走原文全文计数** ⇒ 二者活跃面不一致
    #      ⇒ `project.json` 的登记台账引述（`decisions/S31`·`S32`、「低阶律条」3 处；
    #      `gaps_resolved/22`）在 G7 上必然命中 ⇒ **G7 恒红**（实测 rc=1、命中 1）。
    #      本岗处置：**G7 改为结构化遍历**，与 G3 共用留痕子树 ＋ 登记台账子树豁免；
    #      另加 D05 注册位豁免（`forbidden_synonyms`）与词条自身 definition 自引述豁免（保留原语义）；
    #      **G3 判据保持不动**（「板面」不在任何词条的 `forbidden_synonyms` ⇒ G3 无注册位可豁免）。
    #      按 **Q62** 配负测腿8/9/10（放行／同文件兄弟键必拦／豁免不外溢到交付物）。
    WORD = "低阶律条"
    hits7 = []
    reg7 = []
    quotes7 = []
    scanned7 = 0
    sk7 = {"history": 0, "registry": 0, "registration": 0}

    # 词条自身 forbidden_synonyms → 该词条自身 definition 内的「自引述注册位」豁免
    # （不跨词条豁免、不整份豁免 D05；见文件头「2026-10-23 09:3x 判据边界二次精确化」）
    d05_all = json.loads(open(os.path.join(root, "shared/D05.json"), encoding="utf-8").read())
    own_syns = {}
    for _i, _g in enumerate(d05_all.get("glossary") or []):
        if isinstance(_g, dict) and isinstance(_g.get("term"), str):
            own_syns[_i] = set(x for x in (_g.get("forbidden_synonyms") or []) if isinstance(x, str))

    # 注册位收集（G7b 用）：独立走查，**不受任何豁免影响**（防止豁免面把「注册缺失」一起遮掉）
    def _collect_reg(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "forbidden_synonyms":
                    if isinstance(v, list):
                        reg7.extend([x for x in v if isinstance(x, str)])
                    continue
                _collect_reg(v)
        elif isinstance(node, list):
            for v in node:
                _collect_reg(v)

    _collect_reg(d05_all)

    for p in files:
        raw = open(p, encoding="utf-8").read()
        fname = os.path.basename(p)
        try:
            doc = json.loads(raw)
        except Exception:
            doc = None
        if doc is None:
            texts = [("<raw>", raw)]
            st = {"history": 0, "registry": 0, "registration": 0}
        else:
            texts, st = active_text(doc, fname=fname, d05=(fname == "D05.json"))
        for _k in sk7:
            sk7[_k] += st[_k]
        scanned7 += sum(len(t) for _, t in texts)
        for tpath, txt in texts:
            if WORD not in txt:
                continue
            if fname == "D05.json":
                seg = tpath.split("/")
                if (len(seg) >= 3 and seg[0] == "glossary" and seg[-1] == "definition"
                        and seg[1].isdigit() and WORD in own_syns.get(int(seg[1]), ())):
                    quotes7.append((fname, tpath))
                    continue
            hits7.append((fname, tpath))

    ok("G7 「低阶律条」活跃写法全库 0 命中（D18 台账引用性文本 ＋ 版本历史/订正留痕/同步变更留痕/缺口登记台账/决策登记簿 ＋ D05 词条注册位已排除）",
       len(hits7) == 0,
       f"受检 {len(files)} 个交付物文件｜活跃面受检 {scanned7} 字符｜留痕豁免 {sk7['history']}｜"
       f"登记台账豁免 {sk7['registry']}｜注册位豁免 {sk7['registration']}｜命中 {len(hits7)}"
       + (f"｜{hits7[:5]}" if hits7 else "")
       + (f"｜注册位自引述豁免 {len(quotes7)} 处（D05 词条自身 definition 内的 forbidden_synonyms 列举）" if quotes7 else ""))
    ok("G7b D05 律条词条 forbidden_synonyms 已注册「低阶律条」（S31 ④／OPS-23 面② 落地）",
       WORD in reg7, f"注册位含该词 {WORD in reg7}｜注册位该词出现 {reg7.count(WORD)} 次")

    # G8 守卫队长回源
    d07u = load(os.path.join(root, "units/U01/D07.json"))
    mh = []
    for e in d07u.get("episodes", []):
        if str(e.get("ep")) == "6":
            mh = e.get("must_happen", []) or []
    ok("G8 U01 D07 ep006 must_happen 含源素材原句「一击震退守卫队长使其单膝跪地」",
       any("一击震退守卫队长使其单膝跪地" in x for x in mh),
       f"受检 {len(mh)} 条")

    failed = [r for r in res if not r[0]]
    print("■ 断言结果")
    for good, label, detail in res:
        print(f"  {'✅' if good else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    print(f"■ 合计：断言 {len(res)} 条｜通过 {len(res) - len(failed)}｜失败 {len(failed)}")
    if failed:
        print("❌ 有断言失败")
        return 1
    print("✅ 「板面／板背」敲击面口径闸全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
