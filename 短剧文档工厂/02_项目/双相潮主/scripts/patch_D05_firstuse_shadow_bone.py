#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D05_firstuse_shadow_bone.py —— 故事架构（D05 单写点）：两条 glossary 词条首用集订正

【被订正的两条（原值均无源素材出处）】
  ① 「影刃封路」            first_use_ep 37 → **36**
     源《逐集内容概述》ep036「叶红衣影刃封路叶家族长退路」＝该四字词形**字面首现**。
     原值 37 无出处（疑为「斩叶家族长」beat 的〔B13〕标记集 ep037 —— beat 锚点 ≠ 词形首现集）。
  ② 「骨龙贯穿 / 骨龙威压」 first_use_ep 17 → **26**
     源《逐集内容概述》ep026〔B09〕「三纹破境，黑白双生骨龙威震全场」＝「骨龙」**字面首现**。
     原值 17 无出处（疑为「骨威」首现集 ep017 的串位）。
     「骨龙贯穿」字面首现 ep091、「骨龙威压」字面首现 ep099，均在 26 之后。
     「骨威」是**另一词形**（源 ep017／018／052／098），不在本词条范围。

【为什么 37→36 不会被判成「更严 ⇒ 存量违规」】
  母本机器口径（`03_规格/rules.json` `_term_first_use_note`）已明文：
  **首用集只约束台词面（D11 `shots[].dialogue` ＋ D08 `body[type=dialogue]`）与字幕面（D16 `subtitle_style.lines[].text`）；
  画面描述面（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt`／D06-D07 画面层字段）不查 —— D05 明文允许。**
  ⇒ 存量「影刃封路」命中全部落在**画面描述面**（U02 D06 `must_happen`／D07 `scene_needs`＋`quad_segments[].note`／
    D08 `compliance_notes`／D11 `shots[].note`＋`continuity`／D13／D16 `cuts`＋`transitions` `basis`）⇒ 零级联。
  ⇒ 本脚本以 **A5 断言实扫四个台词/字幕面命中必须为 0**，否则拒绝写盘。

【边界】
  · 只改 D05（本岗单写点）：两条词条的 `first_use_ep` 与 `definition`，以及 `version`。
  · **不新增 glossary 词条**（新立词条＝新增母本收口，须总控/企划合规裁，不在本岗权限内）。
  · **不动 `terminology_basis`**（其 T 编号与 glossary 序不对应：T13=叶家、T12=云顶财阀，追加会错位）。
  · 不改 `forbidden_synonyms`（禁写面与首用集正交，改它会引发 V5 全文扫描面变化）。
  · 不改 `03_规格/rules.json`（企划合规单写点）：「影刃封路」「骨龙」尚未登记进 `term_first_use` 机器轴，
    **故 V5 不会因本次 first_use_ep 变更产生新 error** —— 登记建议已随回报上呈。

用法：python3 scripts/patch_D05_firstuse_shadow_bone.py --project . [--source <源素材目录>] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime

OLD_VER = "v1.5"
NEW_VER = "v1.6"

OLD_DEF_SHADOW = "叶红衣以影刃切断退路，无枪械与射击呈现。"
OLD_DEF_BONE = "主角高阶战力的表达：骨龙形光影贯穿/压制，动作不接触人体。"

NEW_DEF_SHADOW = (
    "叶红衣以影刃切断退路，无枪械与射击呈现。"
    "【首用口径（三层，母本级收口）】"
    "① **词形首用集＝ep036**——源《逐集内容概述》ep036「叶红衣影刃封路叶家族长退路」为该四字词形的**字面首现**"
    "（母本原值 37 无源素材出处，2026-10-23 订正为 36；原值疑取「斩叶家族长」beat 的〔B13〕标记集 ep037，"
    "而 beat 锚点 ≠ 词形首现集）。"
    "② **形态规约自 ep016 起适用**——源 ep016〔归档大限日〕暗杀组夜袭，叶红衣封退路这一形态一出现即须以影刃呈现、"
    "禁枪械与射杀（禁写面＝本词条 `forbidden_synonyms`，与首用集正交、**始终生效**，不受首用集约束）。"
    "③ **形态可先于定名出现**（沿用「律条」词条已确立的先例「机制先、名字晚」）——"
    "**画面描述面不受词形首用集约束**（D06 `must_happen`、D07 `scene_needs`／`quad_segments[].note`、"
    "D08 `compliance_notes`、D11 `shots[].note`／`continuity`、D13、D16 `cuts`／`transitions` `basis` 等画面层字段，"
    "可在 ep036 前写「影刃封路」）；"
    "**台词面与字幕面自 ep036 起方可出现「影刃封路」四字**"
    "（受检面口径见 `03_规格/rules.json` `_term_first_use_note`：台词面＝D11 `shots[].dialogue` ＋ "
    "D08 `body[type=dialogue]`；字幕面＝D16 `subtitle_style.lines[].text`）。"
)

NEW_DEF_BONE = (
    "主角高阶战力的表达：骨龙形光影贯穿/压制，动作不接触人体。"
    "【首用口径（母本级收口）】"
    "本词条 `first_use_ep` 取**「骨龙」形态的源素材字面首现集 ep026**——"
    "源《逐集内容概述》ep026〔B09〕「三纹破境，黑白双生骨龙威震全场」"
    "（母本原值 17 无源素材出处，2026-10-23 订正为 26；原值疑为「骨威」首现集 ep017 的串位）。"
    "**具体词形**「骨龙贯穿」字面首现 ep091、「骨龙威压」字面首现 ep099（源同上），**均在首用集之后**。"
    "**「骨威」是另一词形**（源 ep017／ep018／ep052／ep098），**不在本词条范围**、不受本词条首用集约束；"
    "**ep026 之前不得使用「骨龙」这一名称及其派生词形**——源 ep017–ep025 一律用「骨威」。"
)

GLOSSARY_KEYS = {"term", "definition", "forbidden_synonyms", "first_use_ep"}


def die(code, msg):
    sys.exit(f"[ABORT {code}] {msg}")


def scan_dialogue_faces(proj: str):
    """实扫台词面/字幕面（官方受检口径）：D11 shots[].dialogue / D08 body[type=dialogue] /
    D16 subtitle_style.lines[].text；D09 lines[].text 亦为台词行，纳入。"""
    hits = []
    for unit in sorted(os.listdir(os.path.join(proj, "units"))):
        udir = os.path.join(proj, "units", unit)
        if not os.path.isdir(udir):
            continue
        for doc in ("D08", "D09", "D11", "D16"):
            p = os.path.join(udir, f"{doc}.json")
            if not os.path.exists(p):
                continue
            j = json.load(open(p, encoding="utf-8"))
            for e in j.get("episodes", []):
                ep = e.get("ep")
                if doc == "D11":
                    for i, s in enumerate(e.get("shots") or []):
                        dl = s.get("dialogue")
                        vals = dl if isinstance(dl, list) else ([dl] if dl else [])
                        for t in vals:
                            txt = t if isinstance(t, str) else json.dumps(t, ensure_ascii=False)
                            if "影刃封路" in txt or "骨龙" in txt:
                                hits.append((unit, doc, ep, f"shots[{i}].dialogue", txt[:60]))
                elif doc == "D16":
                    for i, l in enumerate(((e.get("subtitle_style") or {}).get("lines") or [])):
                        t = l.get("text") or ""
                        if "影刃封路" in t or "骨龙" in t:
                            hits.append((unit, doc, ep, f"subtitle[{i}]", t[:60]))
                elif doc == "D08":
                    for i, b in enumerate(e.get("body") or []):
                        if isinstance(b, dict) and b.get("type") == "dialogue":
                            t = b.get("text") or ""
                            if "影刃封路" in t or "骨龙" in t:
                                hits.append((unit, doc, ep, f"body[{i}].dialogue", t[:60]))
            if doc == "D09":
                for l in j.get("lines", []):
                    t = l.get("text") or ""
                    if "影刃封路" in t or "骨龙" in t:
                        hits.append((unit, doc, l.get("ep"), f"lines[{l.get('idx')}]", t[:60]))
    return hits


def source_first_eps(src_dir: str):
    """回源《逐集内容概述.md》：算出各词形的字面首现集。"""
    p = os.path.join(src_dir, "逐集内容概述.md")
    if not os.path.isfile(p):
        die("A4", f"找不到源素材：{p}")
    raw = open(p, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    out = {}
    for term in ("影刃封路", "骨龙贯穿", "骨龙威压", "骨龙", "骨威"):
        eps = []
        for m in re.finditer(r"\*\*ep(\d{3})\*\*([^\n]*)", text):
            if term in m.group(2):
                eps.append(int(m.group(1)))
        out[term] = (min(eps) if eps else None, eps)
    return out, sha, len(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--source", default="/Users/ezreal/projects/小说创作/双相潮主/01_漫剧策划")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    d05p = os.path.join(root, "shared", "D05.json")

    # ── A1 存在 + 版本 ──
    if not os.path.isfile(d05p):
        die("A1", f"找不到 {d05p}")
    raw = open(d05p, "rb").read()
    sha_before = hashlib.sha256(raw).hexdigest()
    size_before = len(raw)
    d05 = json.loads(raw.decode("utf-8"))

    if d05.get("version") == NEW_VER:
        g = {x["term"]: x for x in d05.get("glossary", [])}
        ok = (g.get("影刃封路", {}).get("first_use_ep") == 36
              and g.get("骨龙贯穿 / 骨龙威压", {}).get("first_use_ep") == 26
              and g.get("影刃封路", {}).get("definition") == NEW_DEF_SHADOW
              and g.get("骨龙贯穿 / 骨龙威压", {}).get("definition") == NEW_DEF_BONE)
        if ok:
            print(f"[IDEMPOTENT] D05 已是 {NEW_VER} 且两条词条均已订正（影刃封路=36／骨龙=26）；未改动。")
            return 0
        die("A1", f"D05 已是 {NEW_VER} 但词条内容与预期不符；请人工核对，拒绝写盘。")
    # ── A1b **内容锚**幂等（2026-10-23 11:0x 增补）────────────────────────────
    #   本脚本已于 2026-10-23 10:54:51 落地 v1.6；其后 **D05 于 11:03:46 被他人升到 v1.7**
    #   （新增「骨纹未激活态」用户裁决口径；本岗两条首用集订正**完整保留**）。
    #   ⇒ 版本锚 `== NEW_VER` 已随他岗升版失效，若仍只锚版本，本脚本会在现盘上**误报故障**。
    #   改法：**幂等判据锚「两条词条的现值」而非版本号**（版本可被他岗继续升，词条值不该回退）。
    _gl0 = {x.get("term"): x for x in (d05.get("glossary") or []) if isinstance(x, dict)}
    _applied = (_gl0.get("影刃封路", {}).get("first_use_ep") == 36
                and _gl0.get("骨龙贯穿 / 骨龙威压", {}).get("first_use_ep") == 26
                and _gl0.get("影刃封路", {}).get("definition") == NEW_DEF_SHADOW
                and _gl0.get("骨龙贯穿 / 骨龙威压", {}).get("definition") == NEW_DEF_BONE)
    if _applied:
        print(f"[IDEMPOTENT] D05 现版本 {d05.get('version')} 两条词条已订正（影刃封路=36／骨龙=26）；"
              f"未改动（版本锚仅用于本次一次性落地，幂等判据锚词条现值）。")
        return 0
    if d05.get("version") != OLD_VER:
        die("A1", f"D05 版本为 {d05.get('version')}，与预期 {OLD_VER} 不符；拒绝写盘。")

    # ── A2 词条定位 ──
    gl = d05.get("glossary", [])
    if len(gl) != 42:
        die("A2", f"glossary 条数 {len(gl)} ≠ 42；拒绝写盘。")
    idx = {}
    for i, g in enumerate(gl):
        if g.get("term") in ("影刃封路", "骨龙贯穿 / 骨龙威压"):
            if g["term"] in idx:
                die("A2", f"词条重复：{g['term']}")
            idx[g["term"]] = i
    if set(idx) != {"影刃封路", "骨龙贯穿 / 骨龙威压"}:
        die("A2", f"目标词条未齐备：{list(idx)}")

    # ── A3 原值逐字比对 ──
    s = gl[idx["影刃封路"]]
    b = gl[idx["骨龙贯穿 / 骨龙威压"]]
    if s.get("first_use_ep") != 37 or s.get("definition") != OLD_DEF_SHADOW:
        die("A3", f"「影刃封路」原值不符：first_use_ep={s.get('first_use_ep')} definition={s.get('definition')[:40]!r}")
    if b.get("first_use_ep") != 17 or b.get("definition") != OLD_DEF_BONE:
        die("A3", f"「骨龙贯穿 / 骨龙威压」原值不符：first_use_ep={b.get('first_use_ep')} definition={b.get('definition')[:40]!r}")
    s_fb = list(s.get("forbidden_synonyms") or [])
    b_fb = list(b.get("forbidden_synonyms") or [])

    # ── A4 回源：词形字面首现集必须与裁定的目标值一致 ──
    src, src_sha, src_size = source_first_eps(args.source)
    print("── A4 回源《逐集内容概述.md》──")
    print(f"   源文件 {src_size} B｜sha256 {src_sha[:16]}")
    for term, (first, eps) in src.items():
        print(f"   {term:<6} 字面首现 ep={first}  全集={eps}")
    if src["影刃封路"][0] != 36:
        die("A4", f"源素材「影刃封路」字面首现为 ep{src['影刃封路'][0]}，与裁定目标 36 不符；拒绝写盘。")
    if src["骨龙"][0] != 26:
        die("A4", f"源素材「骨龙」字面首现为 ep{src['骨龙'][0]}，与裁定目标 26 不符；拒绝写盘。")
    for term, must in (("骨龙贯穿", 91), ("骨龙威压", 99)):
        if src[term][0] != must:
            die("A4", f"源素材「{term}」字面首现为 ep{src[term][0]}，与引用值 {must} 不符；拒绝写盘。")
    if not src["骨威"][0] or src["骨威"][0] >= 26:
        die("A4", "源素材「骨威」首现集异常（应 < 26）；拒绝写盘。")

    # ── A5 零级联：台词面/字幕面命中必须为 0 ──
    hits = scan_dialogue_faces(root)
    if hits:
        for h in hits:
            print("   ⚠️ 台词面/字幕面命中：", h)
        die("A5", f"台词面/字幕面命中 {len(hits)} 处 ⇒ 改 first_use_ep 会产生存量违规；拒绝写盘。")
    print("── A5 零级联实测 ──")
    print("   台词面/字幕面（D11 dialogue＋D08 type=dialogue＋D09 lines＋D16 subtitle）命中 = 0 ✅")

    # ── A6 「骨龙」分布记账（2026-10-23 11:3x 判据**第五次**精确化）──
    #   原实现＝「units/ 全库原文任一命中即拒写」，11:2x 起**假红**：
    #     台本编剧 U03 D08 v1.4 的 `compliance_notes` 与 D09 v1.1 的 `voice_cards[].forbidden_words`
    #     **逐字引述禁令本身**（「D05 骨龙词条：first_use_ep=26，ep026 之前禁「骨龙」二字」）
    #     ⇒ 属**说明位／清单位**（登记语境，与 D18 台账、D05 `forbidden_synonyms` 注册位同族），
    #       **不是活跃违规**；贵岗据此拒写会让本脚本在现盘上**永久不可用**（假红）。
    #   依母本机器口径（`03_规格/rules.json` `_term_first_use_note`）：首用集**只约束台词面与字幕面**，
    #     画面描述面不查 ⇒ **受约束面命中 = 0** 才是「17→26 无回改需求」的真判据。
    #   ⇒ 现改为：**拒写权归 A5（受约束面）**；A6 改为**分桶记账**（受约束面／说明位／其它面），
    #     **只报告不阻断**（命中不阻断，但必须打印出来供人工按「同形异指」分类）。
    #   按 Q62（放宽必须配负测）配 `scripts/selftest_D05_bone_scopes.py`（三腿）。
    bone_buckets = {"受约束面（台词面/字幕面）": 0, "说明位/清单位": 0, "其它面": 0}
    bone_detail = {"说明位/清单位": [], "其它面": []}
    NOTE_KEYS = ("compliance_notes", "forbidden_words")

    def _bucket_walk(node, path=()):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in NOTE_KEYS:
                    s = json.dumps(v, ensure_ascii=False)
                    c = s.count("骨龙")
                    if c:
                        bone_buckets["说明位/清单位"] += c
                        bone_detail["说明位/清单位"].append(("/".join(path + (k,)), c))
                    continue
                _bucket_walk(v, path + (k,))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _bucket_walk(v, path + (str(i),))
        elif isinstance(node, str):
            c = node.count("骨龙")
            if c:
                bone_buckets["其它面"] += c
                bone_detail["其它面"].append(("/".join(path), c))

    for unit in sorted(os.listdir(os.path.join(root, "units"))):
        udir = os.path.join(root, "units", unit)
        if not os.path.isdir(udir):
            continue
        for fn in sorted(os.listdir(udir)):
            if not fn.endswith(".json"):
                continue
            _bucket_walk(json.load(open(os.path.join(udir, fn), encoding="utf-8")), (unit, fn))
    bone_buckets["受约束面（台词面/字幕面）"] = len(hits)   # 复用 A5 的受约束面实扫结果
    if bone_buckets["受约束面（台词面/字幕面）"]:
        die("A6", f"「骨龙」在受约束面（台词面/字幕面）命中 {bone_buckets['受约束面（台词面/字幕面）']} 处 "
                  f"⇒ 17→26 会产生存量违规；拒绝写盘。")
    print("── A6 「骨龙」全库分布记账（只报告不阻断）──")
    print(f"   受约束面（台词面/字幕面）= {bone_buckets['受约束面（台词面/字幕面）']} "
          f"⇒ 17→26 无回改需求 ✅")
    print(f"   说明位/清单位 = {bone_buckets['说明位/清单位']} 处"
          f"（{bone_detail['说明位/清单位'][:3]}…）—— 登记/引述语境，非活跃违规，不判缺陷")
    print(f"   其它面 = {bone_buckets['其它面']} 处"
          f"（{bone_detail['其它面'][:3]}…）—— 画面描述面等，母本口径不查；供人工按同形异指分类")

    # ── A7 schema 合规（改动后键集合不得越界）──
    new_gl = [dict(g) for g in gl]
    new_gl[idx["影刃封路"]]["first_use_ep"] = 36
    new_gl[idx["影刃封路"]]["definition"] = NEW_DEF_SHADOW
    new_gl[idx["骨龙贯穿 / 骨龙威压"]]["first_use_ep"] = 26
    new_gl[idx["骨龙贯穿 / 骨龙威压"]]["definition"] = NEW_DEF_BONE
    for g in new_gl:
        extra = set(g) - GLOSSARY_KEYS
        if extra:
            die("A7", f"词条 {g.get('term')} 含 schema 外字段 {extra}；拒绝写盘。")
        for req in ("term", "definition", "forbidden_synonyms"):
            if req not in g:
                die("A7", f"词条 {g.get('term')} 缺必填 {req}；拒绝写盘。")
    if not re.match(r"^v[0-9]+\.[0-9]+$", NEW_VER):
        die("A7", f"版本字面量非法：{NEW_VER}")

    # 禁写面未被改动
    if list(new_gl[idx["影刃封路"]]["forbidden_synonyms"]) != s_fb:
        die("A7", "「影刃封路」forbidden_synonyms 被改动；拒绝写盘。")
    if list(new_gl[idx["骨龙贯穿 / 骨龙威压"]]["forbidden_synonyms"]) != b_fb:
        die("A7", "「骨龙贯穿 / 骨龙威压」forbidden_synonyms 被改动；拒绝写盘。")

    # 其余 40 条词条必须逐字不变
    for i, g in enumerate(gl):
        if i in (idx["影刃封路"], idx["骨龙贯穿 / 骨龙威压"]):
            continue
        if json.dumps(g, ensure_ascii=False, sort_keys=True) != json.dumps(new_gl[i], ensure_ascii=False, sort_keys=True):
            die("A7", f"非目标词条 {g.get('term')} 发生变动；拒绝写盘。")

    new_d05 = dict(d05)
    new_d05["version"] = NEW_VER
    new_d05["glossary"] = new_gl
    out = json.dumps(new_d05, ensure_ascii=False, indent=2) + "\n"

    # ── A8 CAS 守卫 ──
    cur = open(d05p, "rb").read()
    if hashlib.sha256(cur).hexdigest() != sha_before or len(cur) != size_before:
        die("A8", "并发改动守卫触发（sha256/size 不一致）；请重跑。")

    if args.dry_run:
        print(f"[DRY-RUN] 将把 D05 {OLD_VER} → {NEW_VER}；影刃封路 37→36、骨龙 17→26；未写盘。")
        return 0

    # ── 备份 ──
    bdir = os.path.join(root, "reports",
                        "_bak_D05_firstuse_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(d05p, os.path.join(bdir, "D05.json"))

    with open(d05p, "w", encoding="utf-8") as f:
        f.write(out)

    # ── A9 写后回读校验 ──
    back_raw = open(d05p, "rb").read()
    back = json.loads(back_raw.decode("utf-8"))
    g2 = {x["term"]: x for x in back["glossary"]}
    if back.get("version") != NEW_VER:
        die("A9", "写后版本不符")
    if g2["影刃封路"]["first_use_ep"] != 36 or g2["影刃封路"]["definition"] != NEW_DEF_SHADOW:
        die("A9", "写后「影刃封路」不符")
    if g2["骨龙贯穿 / 骨龙威压"]["first_use_ep"] != 26 or g2["骨龙贯穿 / 骨龙威压"]["definition"] != NEW_DEF_BONE:
        die("A9", "写后「骨龙贯穿 / 骨龙威压」不符")
    if list(g2["影刃封路"]["forbidden_synonyms"]) != s_fb or list(g2["骨龙贯穿 / 骨龙威压"]["forbidden_synonyms"]) != b_fb:
        die("A9", "写后禁写面被改动")
    if len(back["glossary"]) != 42:
        die("A9", "写后词条数不为 42")
    for i, g in enumerate(gl):
        if i in (idx["影刃封路"], idx["骨龙贯穿 / 骨龙威压"]):
            continue
        if json.dumps(g, ensure_ascii=False, sort_keys=True) != json.dumps(back["glossary"][i], ensure_ascii=False, sort_keys=True):
            die("A9", f"写后非目标词条 {g.get('term')} 变动")
    # 结构白名单：顶层键不得增删
    if set(back) != set(d05):
        die("A9", "写后顶层键集合变化")

    print(f"[OK] D05 {OLD_VER} → {NEW_VER}｜{size_before} → {len(back_raw)} B｜"
          f"sha256 {sha_before[:16]} → {hashlib.sha256(back_raw).hexdigest()[:16]}")
    print(f"     · 「影刃封路」first_use_ep 37 → 36（源 ep036 字面首现）")
    print(f"     · 「骨龙贯穿 / 骨龙威压」first_use_ep 17 → 26（源 ep026 骨龙字面首现）")
    print(f"     · 其余 40 条词条逐字不变；禁写面未动；顶层键未增删")
    print(f"     · 备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
