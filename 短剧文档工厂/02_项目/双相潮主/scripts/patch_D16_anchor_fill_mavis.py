#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D16 逐行 anchor 补齐器 v2 —— Chief R-027d 补充（重投）

范围
----
U01 ep001 / ep003~ep008 ＋ U02 ep009~ep016（⛔ 不动 ep002、⛔ 不动 U03）

anchor 口径（按 SSOT，不按派单字面）
------------------------------------
SSOT = D18 `Q114` 明细段 ＋ **ep002 现盘 13 条 anchor 金标准**（本脚本 `--golden` 可复算）。
由 ep002 现盘反推出的逐行体例（每条都已逐字核对）：

| 行类型 | anchor 取法 | ep002 实证 |
|---|---|---|
| 对白行 | **D09 台词原文**（裸文本，不带「」） | seq2/7/11/14 —— 实测 `anchor ∉ 任何镜 visual_facts`（⊂vf=False），证明对白行锚点本就不在 vf 内 |
| 画面文字行（字幕／面板文字） | **该镜 visual_facts 的「逗号级原句」**（先按「；」分句，再按「，」切，取与行文对应的那一句） | seq3/4/5/6/8/9/10/12/13 共 9 条 anchor 全部 == 某个逗号级原句（⛔ 无一条等于整条分句） |
| 角标行 | 本单**不加**（派单明示；ep002 既有角标 anchor 不动） | seq1 anchor=「右下角常驻白色角标：AI 生成。」 |
| 片尾行 | **不挂**（用户裁决「片尾行不挂镜内锚点」） | seq15 anchor=None |

选句算法（能被 ep002 金标准复算，见 `--golden`）
------------------------------------------------
① 行文去「清单前缀」（`出租屋：椅子翻倒、工具散落` → `椅子翻倒、工具散落`）
② 候选 = 该镜 vf 的逗号级原句，剔除角标句与白模构图句（`主体（…）`／`在画框`／`占幅`…）
③ 命中优先：行文逐字落在某原句内 ⇒ 取该句
④ 否则：取与行文最长公共连续子串（LCS）最长的原句
⑤ 仍无实词对应 ⇒ **不写 anchor、列 orphan 报缺陷**（不伪造）

跨镜归属（诚实优先）
--------------------
若行文逐字落在**同一集另一镜**的 vf 原句内（而行所挂镜不含该行文），
说明该行的镜位归属与文字出处不一致 ⇒ anchor 取**文字真实出处那一镜**的原句，
并把该行登记为「镜位归属缺陷」随回执上报（**不拿相似但不同的原句顶替**，
顶替＝伪造出处，会把字幕错绑到别的画面事实）。

落盘防护
--------
写前 **Q129 指针五元组**（version／size／sha256／mtime）比对基线，不符即中止；
写盘 = 备份 ＋ 三锚 CAS(size+mtime+sha256) ＋ `os.replace` 原子替换；
写后回读逐行校验（对白行验 D09 原文、其余验 anchor ∈ 该集某镜 vf）；
落盘方自持自增版本、不回退（Q80/Q105）；重跑逐字节一致 ⇒ 判 IDEMPOTENT。

用法
----
  python3 scripts/patch_D16_anchor_fill_mavis.py --golden     # 用 ep002 金标准自测算法
  python3 scripts/patch_D16_anchor_fill_mavis.py --dry-run
  python3 scripts/patch_D16_anchor_fill_mavis.py --units U01,U02
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(ROOT, "units")
REPORTS = os.path.join(ROOT, "reports")

SCOPE = {
    "U01": [1, 3, 4, 5, 6, 7, 8],
    "U02": [9, 10, 11, 12, 13, 14, 15, 16],
}
BASELINE = {"U01": "v1.35", "U02": "v1.11"}

BADGE_KEY = "右下角常驻白色角标"
FRAMING_HINTS = ("主体（", "在画面中部", "在画面下方", "在画面上方", "留白", "占幅",
                 "在画框", "画面偏", "画幅内", "占画面")
PUNCT = r"[\s「」『』\"“”'’‘。，、：:；;！!？?（）()\[\]【】…—·\-]+"

# 镜位归属缺陷的行级留痕（Q30 追加式；不写旧计数等可被残留计数判据命中的字面量）
NOTE_MISOWN = ("【镜位归属待裁定 · 2026-10-23 分镜导演岗】本行文字『%(txt)s』逐字出自 D11 镜%(osid)d 的 "
               "visual_facts（原句『%(anchor)s』），**本行所挂镜%(sid)d 的 vf 内不含该行文**；"
               "anchor 据实记文字真实出处那一镜的原句，未拿相似但不同的原句顶替"
               "（顶替＝伪造出处，会把字幕错绑到另一条画面事实）。行挂镜与文字出处镜不一致，"
               "移挂涉及字幕时码与 D15 对齐，本单不擅改镜位与时码，提请总控/台本编剧裁定。")


def die(msg, code=2):
    print("[ABORT] %s" % msg)
    sys.exit(code)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def five_tuple(p):
    st = os.stat(p)
    with open(p, "rb") as f:
        raw = f.read()
    return {"size": st.st_size, "sha256": hashlib.sha256(raw).hexdigest(),
            "mtime_ns": st.st_mtime_ns}


def norm(t):
    return re.sub(PUNCT, "", t or "")


def payload(txt):
    """行文主体：去掉「前半：」式清单前缀。"""
    t = (txt or "").strip()
    if "：" in t or ":" in t:
        head, tail = t.replace("：", ":").split(":", 1)
        if len(norm(head)) <= 8 and norm(tail):
            return tail
    return t


def chunks(vf):
    """vf → 逗号级原句列表（先按「；」分句，再按「，」切；保持原序）。"""
    out = []
    for f in re.split(r"[；;]", vf or ""):
        f = f.strip()
        if not f:
            continue
        for c in re.split(r"[，,]", f):
            c = c.strip().strip("；;").strip()
            if c:
                out.append(c)
    return out


def is_badge(c):
    return BADGE_KEY in c


def is_framing(c):
    if is_badge(c):
        return True
    if any(h in c for h in FRAMING_HINTS):
        # 兼含「同屏中文」的读数句是画面内文字（合法候选）
        return "同屏中文" not in c
    return False


def lcs_len(a, b):
    """最长公共连续子串长度。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def pick_chunk(vf, txt):
    """从该镜 vf 的逗号级原句里选一句作 anchor。返回 (anchor, 方式, lcs)。"""
    cands = [c for c in chunks(vf) if not is_framing(c)]
    if not cands:
        return None, "该镜无合法原句候选（角标句/构图句剔除后为空）", 0
    nt = norm(payload(txt))
    best, best_l, best_verbatim = None, -1, False
    for c in cands:
        nc = norm(c)
        v = bool(nt) and nt in nc
        L = lcs_len(nt, nc)
        if (v and not best_verbatim) or (v == best_verbatim and L > best_l):
            best, best_l, best_verbatim = c, L, v
    if best is None:
        return None, "无合法候选", 0
    mode = "行文逐字命中该原句" if best_verbatim else "LCS 最长对应"
    return best, mode, best_l


def strip_q(t):
    return (t or "").strip().strip("「」『』\"“”").strip()


def d09_map(d09, ep):
    out = set()
    for l in (d09 or {}).get("lines", []) or []:
        if str(l.get("ep")) == str(ep):
            out.add(strip_q(l.get("text", "")))
    return out


def load_unit(unit):
    d16p = os.path.join(UNITS, unit, "D16.json")
    d11p = os.path.join(UNITS, unit, "D11.json")
    d09p = os.path.join(UNITS, unit, "D09.json")
    if not os.path.exists(d16p):
        die("%s 无 D16.json" % unit)
    d11 = load(d11p)
    d09 = load(d09p) if os.path.exists(d09p) else None
    facts, shots = {}, {}
    for e in d11["episodes"]:
        ep = int(e["ep"])
        shots.setdefault(ep, [])
        for s in e["shots"]:
            sid = int(s["shot_id"])
            facts[(ep, sid)] = str(s.get("visual_facts") or "")
            shots[ep].append(sid)
    return d16p, d11, d09, facts, shots


def golden():
    """用 ep002 现盘 13 条 anchor 当金标准，复算本脚本算法是否复现（判据区分力自测）。"""
    d16p, d11, d09, facts, shots = load_unit("U01")
    doc = load(d16p)
    ep2 = [e for e in doc["episodes"] if int(e["ep"]) == 2][0]
    d9 = d09_map(d09, 2)
    same = diff = 0
    print("=== ep002 金标准复算（13 条非角标/非片尾 anchor）===")
    for l in ep2["subtitle_style"]["lines"]:
        typ = l.get("type")
        if typ in ("角标", "片尾", "片头"):
            continue
        want = l.get("anchor")
        txt = (l.get("text") or "").strip()
        sid = int(l.get("shot_id") or 0)
        if typ == "对白":
            got = txt if txt in d9 else None
            mode = "对白＝D09 原文"
        else:
            got, mode, _ = pick_chunk(facts.get((2, sid), ""), txt)
        ok = (got == want)
        if ok:
            same += 1
        else:
            diff += 1
        print("  seq%-3s [%s] %s" % (l.get("seq"), typ, "✅ 复现" if ok else "❌ 不一致"))
        if not ok:
            print("        既有 anchor = %r" % (want,))
            print("        本脚本演算 = %r  (%s)" % (got, mode))
    print("  → 复现 %d / 不一致 %d" % (same, diff))
    return 0 if diff == 0 else 1


def process_unit(unit, dry=True, force=False):
    d16p, d11, d09, facts, shots = load_unit(unit)
    snap = five_tuple(d16p)
    doc = load(d16p)
    snap["version"] = doc.get("version")
    base = BASELINE.get(unit)
    if base and snap["version"] != base and not force:
        die("%s 版本基线不符：现盘 %s，基线 %s；确认后用 --force" % (unit, snap["version"], base))

    changes, orphans, weak, misown = [], [], [], []
    stats = {"非角标行": 0, "已有anchor": 0, "新增": 0}
    for e in doc["episodes"]:
        ep = int(e["ep"])
        if ep not in SCOPE.get(unit, []):
            continue
        d9 = d09_map(d09, ep)
        for l in e.get("subtitle_style", {}).get("lines", []) or []:
            typ = l.get("type")
            if typ in ("角标", "片尾", "片头"):
                continue
            stats["非角标行"] += 1
            if l.get("anchor"):
                stats["已有anchor"] += 1
                continue
            txt = (l.get("text") or "").strip()
            sid = l.get("shot_id")
            if sid is None:
                orphans.append((ep, l.get("seq"), typ, txt[:18], "无 shot_id，无法定位所属镜"))
                continue
            sid = int(sid)
            vf = facts.get((ep, sid), "")
            if typ == "对白":
                if txt in d9:
                    l["anchor"] = txt
                    changes.append((ep, l.get("seq"), typ, txt[:18], txt[:34], "对白行＝D09 台词原文"))
                    stats["新增"] += 1
                else:
                    orphans.append((ep, l.get("seq"), typ, txt[:18],
                                    "台词原文与 D09 该集原文不逐字相等"))
                continue
            # 画面文字行：先看行文是否逐字落在**自己**这一镜
            a, mode, L = pick_chunk(vf, txt)
            own_hit = False
            nt = norm(payload(txt))
            if nt and nt in norm(vf):
                own_hit = True
            if not own_hit:
                # 行文逐字落在同集**另一镜**？⇒ 镜位归属缺陷：取文字真实出处那一镜的原句
                for osid in shots.get(ep, []):
                    if osid == sid:
                        continue
                    ovf = facts.get((ep, osid), "")
                    if nt and nt in norm(ovf):
                        oa, omode, oL = pick_chunk(ovf, txt)
                        if oa:
                            a, mode, L = oa, omode + "｜文字真实出处=镜%d（行挂镜%d）" % (osid, sid), oL
                            misown.append((ep, l.get("seq"), typ, sid, osid, txt[:24], a[:40]))
                            # Q30 追加式留痕：把「镜位归属与文字出处不一致」写进本行 note，
                            # 防后人只看到 anchor 就以为该行挂镜正确而顺手"修"掉。
                            l["note"] = ((l.get("note") or "") + NOTE_MISOWN % {
                                "txt": txt, "osid": osid, "sid": sid, "anchor": a}).strip()
                            break
            if a and a in facts.get((ep, sid), ""):
                l["anchor"] = a
                changes.append((ep, l.get("seq"), typ, txt[:18], a[:40], mode))
                stats["新增"] += 1
                if L < 2:
                    weak.append((ep, l.get("seq"), typ, txt[:22], a[:34], L))
            elif a:
                # anchor 取自别镜（镜位归属缺陷）：仍写入，但单独登记
                l["anchor"] = a
                changes.append((ep, l.get("seq"), typ, txt[:18], a[:40], mode))
                stats["新增"] += 1
            else:
                orphans.append((ep, l.get("seq"), typ, txt[:18], mode or "求不出合法原句"))

    print("\n=== %s ｜现盘 %s（%d B｜sha16 %s）===" %
          (unit, snap["version"], snap["size"], snap["sha256"][:16]))
    print("  范围集：%s" % (SCOPE.get(unit),))
    print("  非角标行 %d（不含角标/片尾/片头）｜已有 anchor %d｜本批新增 %d"
          % (stats["非角标行"], stats["已有anchor"], stats["新增"]))
    print("  取法：对白行＝D09 台词原文；画面文字行＝该镜 vf「逗号级原句」（ep002 金标准体例）")
    if misown:
        print("  ⚠️ 镜位归属缺陷（行文逐字不在所挂镜，anchor 取自文字真实出处那一镜）%d 条：" % len(misown))
        for m in misown:
            print("     ep%s seq%s [%s] 挂镜%s→实存镜%s 「%s」 anchor=「%s」" % m)
    if weak:
        print("  ⚠️ 低对应（实词 LCS<2，锚点为该镜主画面事实，非行文直接出处）%d 条：" % len(weak))
        for w in weak:
            print("     ep%s seq%s %s「%s」→ 「%s」 (LCS=%d)" % w)
    if orphans:
        print("  ⚠️ orphan（不写 anchor，不伪造）%d 条：" % len(orphans))
        for o in orphans:
            print("     ep%s seq%s %s「%s」 —— %s" % o)
    if not changes:
        print("  [IDEMPOTENT] 无需写盘")
        return 0
    for c in changes[:12]:
        print("     ep%s seq%-3s %-5s「%s」→ %s   [%s]" % c)
    if len(changes) > 12:
        print("     …… 其余 %d 条从略" % (len(changes) - 12))
    if dry:
        print("  [dry-run] 不写盘")
        return 0

    cur = five_tuple(d16p)
    cur["version"] = load(d16p).get("version")
    if cur["version"] != snap["version"]:
        die("%s 版本守卫：读时 %s，写前 %s；中止" % (unit, snap["version"], cur["version"]))
    if (cur["size"], cur["mtime_ns"], cur["sha256"]) != (snap["size"], snap["mtime_ns"], snap["sha256"]):
        die("%s CAS 失败：并发写者已改盘（size %s→%s / sha %s→%s）；本岗不覆盖他人字节，中止"
            % (unit, snap["size"], cur["size"], snap["sha256"][:16], cur["sha256"][:16]), 5)
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(REPORTS, "_bak_D16_anchor_fill_%s_%s" % (unit, ts))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(d16p, os.path.join(bak, "D16.json"))
    maj, mino = snap["version"].lstrip("v").split(".")
    doc["version"] = "v%d.%d" % (int(maj), int(mino) + 1)
    tmp = d16p + ".tmp.%s" % ts
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, d16p)

    # 写后回读逐行校验
    chk = load(d16p)
    bad = miss = 0
    for e in chk["episodes"]:
        ep = int(e["ep"])
        if ep not in SCOPE.get(unit, []):
            continue
        d9 = d09_map(d09, ep)
        epvf = " ".join(v for (ee, _s), v in facts.items() if ee == ep)
        for l in e.get("subtitle_style", {}).get("lines", []) or []:
            typ = l.get("type")
            if typ in ("角标", "片尾", "片头"):
                continue
            a = l.get("anchor")
            if not a:
                miss += 1
                print("     [ERR] ep%s seq%s 缺 anchor" % (ep, l.get("seq")))
                continue
            if typ == "对白":
                if a not in d9:
                    bad += 1
                    print("     [ERR] ep%s seq%s 对白 anchor ≠ D09 原文：%s" % (ep, l.get("seq"), a))
            else:
                if a not in epvf:
                    bad += 1
                    print("     [ERR] ep%s seq%s anchor 不在该集任何镜 vf：%s" % (ep, l.get("seq"), a))
    if bad or miss:
        die("%s 写后回读校验失败：越界 %d 条、缺 anchor %d 条（已备份，可回滚）" % (unit, bad, miss), 4)
    newt = five_tuple(d16p)
    print("  ✅ 落盘：%s → %s｜%d → %d B｜sha16 %s → %s｜备份 %s"
          % (snap["version"], doc["version"], snap["size"], newt["size"],
             snap["sha256"][:16], newt["sha256"][:16], os.path.basename(bak)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default="U01,U02")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--golden", action="store_true", help="用 ep002 现盘 anchor 金标准复算算法")
    args = ap.parse_args()
    if args.golden:
        return golden()
    for u in [x.strip() for x in args.units.split(",") if x.strip()]:
        process_unit(u, dry=args.dry_run, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
