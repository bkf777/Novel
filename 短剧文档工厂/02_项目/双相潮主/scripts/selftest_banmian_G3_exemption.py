#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
selftest_banmian_G3_exemption.py —— 「板面／板背」闸 **G3 判据**的 Q62 负测（八腿 ＋ 两自证）

【为什么从三腿扩到八腿（2026-10-23 10:5x）】
本轮本岗自闸同时暴露**两个方向相反的缺陷**：
  · **假红（误报）**：G3 走原文全文扫描，把「版本订正留痕」里的旧写法判成违规（10:32:34 声音设计
    `units/U02/D16.json` v1.6 新增 `d15_version_history`）⇒ 已修（结构化遍历 ＋ 留痕子树豁免）。
  · **漏检（漏报）**：受检面**硬编码** `("shared","units/U01","units/U02")` ⇒ **U03 的 2 份交付物
    完全不在受检面** ⇒ 已修（按 `units/*` 动态发现 ＋ 新增 G3c 覆盖度自证断言）。
    ⭐ 声音设计以沙箱注入实测确证：向 U03 D07 活跃面注入违规，闸仍「命中 0｜全绿｜exit 0」。
  · 本轮新增两项**判据放宽**：① `sync_records` 纳入留痕面（声音设计主动知会并请求裁定）；
    ② `gaps_resolved` 纳入登记台账语境（`project.json` 缺口消解记录逐字引述旧写法）。
  ⇒ **判据放宽/改边界必须配负测**（Q62）：必须同时证明「该放行的放行了」与「不该放行的仍被拦住」。

【腿设计（G3 侧八腿 ＋ G7 侧三腿 ＋ 两自证 ＝ 13 条断言腿）】
  腿0 **夹具基线自证**：沙箱交付物文件集与 sha256 **与真盘逐份全等**（含 U03）⇒ 证明夹具＝声明基线。
  腿1 **基线必须放行**：rc=0、G3/G3b/G3c 全 ✅、G3b 受检面 > 0（防空集恒真）、**G3c 覆盖单元含 U03**。
  腿2 **活跃面注入必须拦**（U02 D16 字幕行）⇒ rc≠0，且命中路径**不含** `version_history`。
  腿3 **留痕子树注入必须放行**（`d15_version_history`）⇒ rc=0。
  腿4 ⭐ **U03 漏检自证**：向 **U03 D07 ep0 `story_time`** 注入「板面敲击」⇒ rc≠0 且命中路径含 `D07.json`
      —— **这条腿直接锁死「受检面不得硬编码单元名单」**；若有人把 units 名单写回硬编码，本腿立刻红。
  腿5 ⭐ **同步变更留痕注入必须放行**（`subtitle_sync_audit.sync_records[]`，真实形态 date/event/changes）⇒ rc=0。
  腿6 ⭐ **父键兄弟键注入必须拦**（`subtitle_sync_audit.verified_note`，活跃面）⇒ rc≠0 且命中路径含
      `subtitle_sync_audit` 而**不含** `sync_records` —— 证豁免**精确到子树**、不整份排除父键。
  腿7 ⭐ **登记台账语境（G3 侧）**：
      腿7a **基线放行**：`project.json` 进入受检面（`--source` 指向沙箱根）时，其 `gaps_resolved/23`
            （G25 订正记录，**逐字引述旧写法**「敲了两下板面」「板面敲击」）**不得**触发 ⇒ rc=0
            （**若不豁免则 rc≠0** ⇒ 本腿同时证明该豁免是**必要且有效**的）。
      腿7b **非登记位置注入必须拦**（`project.json → project.title`）⇒ rc≠0 ⇒ 证豁免**不整份排除** project.json。
  腿8 ⭐ **G7 侧登记台账语境放行**：`project.json → decisions`（决策登记簿，真实形态 dict[str,str]）
            新增一条含「低阶律条」的裁定记录 ⇒ rc=0 且 **G7 ✅** ⇒ 证 G7 的登记台账豁免真实生效
            （**否则 G7 恒红**——基线 `decisions/S31`·`S32` 本就含 3 处「低阶律条」）。
  腿9 ⭐ **G7 侧同文件兄弟键必拦**：`project.json → source_of_truth` 注入「低阶律条」⇒ **G7 ❌** 且 rc≠0
            ⇒ 证 G7 的登记豁免**不整份排除 `project.json`**（与腿7b 构成 G3/G7 双向对称）。
  腿10 ⭐ **G7 侧豁免不外溢到交付物**：在**交付物**（U03 D07）里新建 `decisions` 键并注入「低阶律条」
            ⇒ **G7 ❌** 且命中路径含 `D07.json` ⇒ 证登记台账豁免**按文件名精确到 `project.json`**
            （取证支撑：31 份交付物中 0 处出现 `gaps_resolved`/`decisions` 键）。

【沙箱纪律（S30／Q73）】
  · 沙箱 ROOT 由本脚本在 `/tmp` 下创建，**只读写副本，真盘零写入**；
  · 负测前后打印**真盘** `units/U02/D16.json` / `units/U03/D07.json` / `project.json` 的 size + sha256 前缀并比对；
  · 腿之间**各用一份独立沙箱**（互不污染），跑完清理；
  · 腿的失败要区分「**守卫拒绝**」与「**沙箱脚本报错**」——否则是假绿。

用法：python3 scripts/selftest_banmian_G3_exemption.py --project 02_项目/双相潮主 [--source <01_漫剧策划>]
退出码：0 = 全过；1 = 有腿失败。
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZERO_WRITE_FILES = ("units/U02/D16.json", "units/U03/D07.json", "project.json")


def sha_size(p):
    b = open(p, "rb").read()
    return hashlib.sha256(b).hexdigest()[:16], len(b)


def real_delivery(root):
    """真盘交付物清单（shared 去 D18 ＋ units/* 全量）——夹具基线自证用。"""
    out = {}
    sd = os.path.join(root, "shared")
    if os.path.isdir(sd):
        for n in sorted(os.listdir(sd)):
            if n.endswith(".json") and n != "D18.json":
                out[os.path.join("shared", n)] = sha_size(os.path.join(sd, n))
    ud = os.path.join(root, "units")
    if os.path.isdir(ud):
        for u in sorted(os.listdir(ud)):
            uu = os.path.join(ud, u)
            if os.path.isdir(uu):
                for n in sorted(os.listdir(uu)):
                    if n.endswith(".json"):
                        out[os.path.join("units", u, n)] = sha_size(os.path.join(uu, n))
    return out


def build_sandbox(project_root, tag, with_project_json=False):
    """复制真盘交付物到独立沙箱（**动态遍历 units/，不硬编码单元**）；返回沙箱项目根。"""
    sb = tempfile.mkdtemp(prefix=f"banmian_g3_{tag}_")
    for sub in ("shared",):
        s = os.path.join(project_root, sub)
        if os.path.isdir(s):
            d = os.path.join(sb, sub)
            os.makedirs(d, exist_ok=True)
            for f in os.listdir(s):
                if f.endswith(".json"):
                    shutil.copy2(os.path.join(s, f), os.path.join(d, f))
    ud = os.path.join(project_root, "units")
    if os.path.isdir(ud):
        for u in sorted(os.listdir(ud)):
            uu = os.path.join(ud, u)
            if not os.path.isdir(uu):
                continue
            d = os.path.join(sb, "units", u)
            os.makedirs(d, exist_ok=True)
            for f in os.listdir(uu):
                if f.endswith(".json"):
                    shutil.copy2(os.path.join(uu, f), os.path.join(d, f))
    if with_project_json:
        pj = os.path.join(project_root, "project.json")
        if os.path.isfile(pj):
            shutil.copy2(pj, os.path.join(sb, "project.json"))
    return sb


def run_gate(sb, source):
    cmd = [sys.executable, os.path.join(HERE, "check_D05_banmian_scope.py"),
           "--project", sb]
    if source:
        cmd += ["--source", source]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def line_of(out, key):
    for l in out.split("\n"):
        if l.strip().startswith(("✅ " + key, "❌ " + key)):
            return l.strip()
    return ""


def g3_line(out):
    return line_of(out, "G3 ")


def g3b_line(out):
    return line_of(out, "G3b ")


def g3c_line(out):
    return line_of(out, "G3c ")


def g7_line(out):
    return line_of(out, "G7 ")


# ── 注入器（腿形 == 真盘真实落盘形态）──
def inject_active(sb):
    """U02 D16 活跃字幕行写入「板面敲击」（真盘形态：`episodes[].subtitle_style.lines[].text`）。"""
    p = os.path.join(sb, "units/U02/D16.json")
    d = json.load(open(p, encoding="utf-8"))
    for e in d.get("episodes", []):
        ss = e.setdefault("subtitle_style", {})
        lines = ss.get("lines")
        if isinstance(lines, list) and lines:
            lines[0]["text"] = str(lines[0].get("text", "")) + " 板面敲击"
            json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            return "episodes[?].subtitle_style.lines[0].text"
    raise SystemExit("[ABORT] 沙箱腿2：U02 D16 未找到字幕行，无法构造活跃面注入形态")


def inject_history(sb):
    """U02 D16 `d15_version_history` 写入「板面敲击」（版本订正留痕子树）。"""
    p = os.path.join(sb, "units/U02/D16.json")
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0]
    ss = e.setdefault("subtitle_style", {})
    aud = ss.setdefault("subtitle_sync_audit", {})
    hist = aud.setdefault("d15_version_history", {})
    hist["v9.9"] = "仅作登记：「板面敲击」→「板背敲击」；此为版本订正留痕。"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "episodes[0].subtitle_style.subtitle_sync_audit.d15_version_history.v9.9"


def inject_u03(sb):
    """⭐ U03 D07 ep0 `story_time` 写入「板面敲击」——**漏检自证腿**。
    （`story_time` 是 D07 真实字段；真盘 D07 ep0 形如「灾变第 14 日 21:45（大限夜·暗杀组合围）」）"""
    p = os.path.join(sb, "units/U03/D07.json")
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0]
    e["story_time"] = str(e.get("story_time", "")) + " 板面敲击"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "episodes[0].story_time"


def inject_sync_records(sb):
    """U02 D16 `subtitle_sync_audit.sync_records[]` 追加一条（真盘形态：date/event/changes）。"""
    p = os.path.join(sb, "units/U02/D16.json")
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0]
    ss = e.setdefault("subtitle_style", {})
    aud = ss.setdefault("subtitle_sync_audit", {})
    recs = aud.setdefault("sync_records", [])
    recs.append({"date": "2026-10-23", "event": "selftest v9.9",
                 "changes": ["v9.9：板面敲击 → 板背敲击（同步变更留痕）"]})
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "episodes[0].subtitle_style.subtitle_sync_audit.sync_records[].changes"


def inject_sibling_active(sb):
    """U02 D16 `subtitle_sync_audit.verified_note`（**父键的兄弟键，活跃面**）写入「板面敲击」
    —— 证 `sync_records` 豁免**精确到子树**、不整份排除父键。"""
    p = os.path.join(sb, "units/U02/D16.json")
    d = json.load(open(p, encoding="utf-8"))
    e = d["episodes"][0]
    ss = e.setdefault("subtitle_style", {})
    aud = ss.setdefault("subtitle_sync_audit", {})
    aud["verified_note"] = str(aud.get("verified_note", "")) + " 板面敲击"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "episodes[0].subtitle_style.subtitle_sync_audit.verified_note"


def inject_project_title(sb):
    """`project.json → project.title`（**非登记位置，活跃面**）写入「板面敲击」。"""
    p = os.path.join(sb, "project.json")
    d = json.load(open(p, encoding="utf-8"))
    d.setdefault("project", {})["title"] = str(d.get("project", {}).get("title", "")) + " 板面敲击"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "project.title"


def inject_decisions_word(sb):
    """`project.json → decisions`（**决策登记簿，登记语境**）新增一条含「低阶律条」的裁定记录。

    腿形 == 真盘真实形态：`decisions` 是 dict（键＝裁定号，值＝裁定正文字符串）。
    """
    p = os.path.join(sb, "project.json")
    d = json.load(open(p, encoding="utf-8"))
    dec = d.setdefault("decisions", {})
    key = "SELFTEST_登记语境_低阶律条"
    dec[key] = ("裁定：档位写法收口，D06／D07 的「低阶律条」→「律条」"
                "（自造档位修饰语按 D05 `forbidden_synonyms` 管理）——本条为登记台账引述。")
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "decisions.SELFTEST_登记语境_低阶律条"


def inject_source_of_truth_word(sb):
    """`project.json → source_of_truth`（**同文件非登记键，活跃面**）写入「低阶律条」。

    ⇒ 证登记台账豁免**不整份排除 `project.json`**（G7 侧对称于腿7b 的 G3 侧）。
    """
    p = os.path.join(sb, "project.json")
    d = json.load(open(p, encoding="utf-8"))
    sot = d.setdefault("source_of_truth", {})
    sot["selftest_note"] = "活跃面自证：低阶律条 不得出现在现行口径中。"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "source_of_truth.selftest_note"


def inject_delivery_decisions_word(sb):
    """**交付物**（U03 D07）内新建 `decisions` 键并写入「低阶律条」。

    ⇒ 证登记台账豁免**按文件名精确到 `project.json`**，**不外溢到交付物**。
    """
    p = os.path.join(sb, "units/U03/D07.json")
    d = json.load(open(p, encoding="utf-8"))
    d["decisions"] = {"SELFTEST": "现行口径：低阶律条（交付物内不得以登记键名藏活跃违规）"}
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return "units/U03/D07.json decisions.SELFTEST"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--source", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    before = {}
    for rel in ZERO_WRITE_FILES:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            before[rel] = sha_size(p)
            print(f"■ 真盘基准：{rel}｜sha256 {before[rel][0]}｜{before[rel][1]} B")

    failures = []
    legs = []

    def leg(name, ok, note=""):
        legs.append((name, ok))
        print(f"  {'✅' if ok else '❌'} {name}" + (f"｜{note}" if note else ""))
        if not ok:
            failures.append(name)

    # ── 腿0：夹具基线自证 ──
    sb = build_sandbox(root, "leg0")
    real = real_delivery(root)
    sb_map = {}
    for rel in real:
        p = os.path.join(sb, rel)
        if os.path.isfile(p):
            sb_map[rel] = sha_size(p)
    same_set = set(real) == set(sb_map)
    same_sha = all(real[k] == sb_map.get(k) for k in real)
    has_u03 = any(k.startswith("units/U03/") for k in sb_map)
    leg("腿0 夹具基线自证（沙箱 == 真盘交付物全集，逐份 sha 全等 ＋ 含 U03）",
        same_set and same_sha and has_u03,
        f"真盘 {len(real)} 份｜沙箱 {len(sb_map)} 份｜集合一致 {same_set}｜sha 全等 {same_sha}｜含 U03 {has_u03}")
    if not (same_set and same_sha):
        failures.append("腿0 夹具与真盘基线不一致 —— 负测结论不可信")
    if not has_u03:
        failures.append("腿0 沙箱不含 U03 —— 腿4（漏检自证）无法成立")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿1：基线必须放行 ──
    sb = build_sandbox(root, "leg1")
    rc, out = run_gate(sb, args.source)
    g3, g3b, g3c = g3_line(out), g3b_line(out), g3c_line(out)
    ok1 = ((rc == 0) and g3.strip().startswith("✅") and g3b.strip().startswith("✅")
           and g3c.strip().startswith("✅") and "U03" in g3c)
    leg("腿1 基线放行（rc=0 ＋ G3/G3b/G3c 全绿 ＋ 覆盖单元含 U03）", ok1, f"rc={rc}")
    print(f"     {g3.strip()}")
    print(f"     {g3b.strip()}")
    print(f"     {g3c.strip()}")
    if not ok1:
        failures.append("腿1 基线未通过（豁免面可能过宽 / 覆盖度自证未过 / 沙箱脚本报错）")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿2：活跃面注入必须拦 ──
    sb = build_sandbox(root, "leg2")
    p_act = inject_active(sb)
    rc, out = run_gate(sb, args.source)
    g3 = g3_line(out)
    hit_ok = "命中 0" not in g3 and "❌ G3 " in g3
    path_ok = "version_history" not in g3
    ok2 = (rc != 0) and hit_ok and path_ok
    leg("腿2 活跃面注入必拦（命中位不在留痕子树）", ok2, f"rc={rc}｜注入位 {p_act}")
    print(f"     {g3.strip()}")
    if not hit_ok:
        failures.append("腿2 注入活跃面后 G3 未命中 —— 判据被放宽过头（假绿）")
    if not path_ok:
        failures.append("腿2 命中位落在 version_history 留痕子树 —— 活跃面被误豁免")
    if rc == 0:
        failures.append("腿2 闸未报错（rc=0）—— 可能是沙箱脚本报错而非守卫拒绝")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿3：留痕子树注入必须放行 ──
    sb = build_sandbox(root, "leg3")
    inject_history(sb)
    rc, out = run_gate(sb, args.source)
    g3 = g3_line(out)
    ok3 = (rc == 0) and g3.strip().startswith("✅")
    leg("腿3 留痕子树注入须放行（豁免面真实生效）", ok3, f"rc={rc}")
    print(f"     {g3.strip()}")
    if not ok3:
        failures.append("腿3 留痕子树注入未被豁免 —— 豁免面未生效或闸整体报错")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿4 ⭐：U03 漏检自证 ──
    sb = build_sandbox(root, "leg4")
    p_u03 = inject_u03(sb)
    rc, out = run_gate(sb, args.source)
    g3 = g3_line(out)
    ok4 = (rc != 0) and ("命中 0" not in g3) and "D07.json" in g3
    leg("腿4 ⭐ U03 漏检自证（向 U03 D07 活跃面注入必被拦）", ok4, f"rc={rc}｜注入位 {p_u03}")
    print(f"     {g3.strip()}")
    if not ok4:
        failures.append("腿4 U03 注入未被拦 —— 受检面又把单元名单写死（漏检复发）")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿5 ⭐：同步变更留痕注入必须放行 ──
    sb = build_sandbox(root, "leg5")
    p_sync = inject_sync_records(sb)
    rc, out = run_gate(sb, args.source)
    g3 = g3_line(out)
    ok5 = (rc == 0) and g3.strip().startswith("✅")
    leg("腿5 ⭐ 同步变更留痕注入须放行（sync_records 豁免生效）", ok5, f"rc={rc}｜注入位 {p_sync}")
    print(f"     {g3.strip()}")
    if not ok5:
        failures.append("腿5 sync_records 注入未被豁免 —— 新增豁免面未生效")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿6 ⭐：父键兄弟键注入必须拦 ──
    sb = build_sandbox(root, "leg6")
    p_sib = inject_sibling_active(sb)
    rc, out = run_gate(sb, args.source)
    g3 = g3_line(out)
    ok6 = ((rc != 0) and ("命中 0" not in g3) and "subtitle_sync_audit" in g3
           and "sync_records" not in g3 and "version_history" not in g3)
    leg("腿6 ⭐ 父键兄弟键注入必拦（豁免精确到子树、不整份排除父键）", ok6, f"rc={rc}｜注入位 {p_sib}")
    print(f"     {g3.strip()}")
    if not ok6:
        failures.append("腿6 父键兄弟键未被拦 —— 豁免面扩大到整个 subtitle_sync_audit（过宽）")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿7 ⭐：登记台账语境（project.json）──
    sb = build_sandbox(root, "leg7a", with_project_json=True)
    rc, out = run_gate(sb, sb)          # --source 指向沙箱根 ⇒ project.json 进入受检面
    g3 = g3_line(out)
    ok7a = (rc == 0) and g3.strip().startswith("✅")
    leg("腿7a ⭐ 登记台账语境放行（project.json gaps_resolved 内既有引述不触发）",
        ok7a, f"rc={rc}｜受检面含 project.json")
    print(f"     {g3.strip()}")
    if not ok7a:
        failures.append("腿7a project.json 的 gaps_resolved 引述仍被命中 —— 登记台账豁免未生效")
    shutil.rmtree(sb, ignore_errors=True)

    sb = build_sandbox(root, "leg7b", with_project_json=True)
    p_t = inject_project_title(sb)
    rc, out = run_gate(sb, sb)
    g3 = g3_line(out)
    ok7b = (rc != 0) and ("命中 0" not in g3) and "project.json" in g3
    leg("腿7b ⭐ 非登记位置注入必拦（豁免不整份排除 project.json）", ok7b, f"rc={rc}｜注入位 {p_t}")
    print(f"     {g3.strip()}")
    if not ok7b:
        failures.append("腿7b project.json 非登记位置未被拦 —— 豁免面整份排除过头")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿8 ⭐：G7 登记台账语境放行 ──
    sb = build_sandbox(root, "leg8", with_project_json=True)
    p_dec = inject_decisions_word(sb)
    rc, out = run_gate(sb, sb)
    g7 = g7_line(out)
    ok8 = (rc == 0) and g7.strip().startswith("✅")
    leg("腿8 ⭐ G7 登记台账语境放行（project.json decisions 内引述「低阶律条」不触发）",
        ok8, f"rc={rc}｜注入位 {p_dec}")
    print(f"     {g7.strip()}")
    if not ok8:
        failures.append("腿8 project.json decisions 的登记引述仍被 G7 命中 —— 登记台账豁免未生效")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿9 ⭐：G7 同文件兄弟键必拦（不整份排除 project.json）──
    sb = build_sandbox(root, "leg9", with_project_json=True)
    p_sot = inject_source_of_truth_word(sb)
    rc, out = run_gate(sb, sb)
    g7 = g7_line(out)
    ok9 = (rc != 0) and ("命中 0" not in g7) and "❌ G7 " in g7
    leg("腿9 ⭐ G7 同文件兄弟键注入必拦（豁免不整份排除 project.json）",
        ok9, f"rc={rc}｜注入位 {p_sot}")
    print(f"     {g7.strip()}")
    if not ok9:
        failures.append("腿9 project.json 非登记键未被 G7 拦 —— 登记台账豁免整份排除过头")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 腿10 ⭐：G7 登记豁免不外溢到交付物 ──
    sb = build_sandbox(root, "leg10")
    p_dd = inject_delivery_decisions_word(sb)
    rc, out = run_gate(sb, sb)
    g7 = g7_line(out)
    ok10 = (rc != 0) and ("命中 0" not in g7) and "❌ G7 " in g7 and "D07.json" in g7
    leg("腿10 ⭐ G7 登记豁免不外溢到交付物（交付物内 decisions 键注入必拦）",
        ok10, f"rc={rc}｜注入位 {p_dd}")
    print(f"     {g7.strip()}")
    if not ok10:
        failures.append("腿10 交付物内的 decisions 键被豁免 —— 登记台账豁免按文件名失守")
    shutil.rmtree(sb, ignore_errors=True)

    # ── 真盘零写入校验（多文件）──
    zero = True
    for rel, b0 in before.items():
        p = os.path.join(root, rel)
        a1 = sha_size(p)
        if a1 != b0:
            zero = False
            print(f"  ❌ 真盘被改动：{rel}｜{b0} → {a1}")
    leg("真盘零写入（3 份文件 sha256 前后全等）", zero,
        "｜".join(f"{r}:{v[0]}" for r, v in before.items()))
    if not zero:
        failures.append("真盘文件被负测改动 —— 违反沙箱纪律")

    passed = sum(1 for _, ok in legs if ok)
    print(f"■ 合计：{len(legs)} 腿（含基线自证与零写入）｜通过 {passed}｜失败 {len(failures)}")
    if failures:
        for f in failures:
            print(f"  ❌ {f}")
        return 1
    print("✅ G3 判据负测全过（假红已修 ＋ 漏检已修 ＋ 两项新豁免精确到子树，未假绿）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
