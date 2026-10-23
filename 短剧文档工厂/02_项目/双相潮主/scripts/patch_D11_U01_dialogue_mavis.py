#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D11 U01 `dialogue` 字段逐字回正（派单 r4 第一件）＋ D16 U01 ep003 字幕行 note 三档档位词（第二件）

第一件：台词真源 ＝ D09 U01 `lines[].text`（与 D08 U01 `body` dialogue 逐字互证）
  镜号归属用**硬锚**推导，不靠顺序猜：
    D15 `voice_over[].line_ref`（形如 "D09 ep2 #1"）→ D09 行号 K
    D16 `subtitle_style.lines[]` 的对白行 → shot_id（且带 `d15_line_ref`）
    ⇒ shot_id → 该镜该念的 D09 行号集合 → 该镜 dialogue 的逐字内容
  角色名前缀沿用现值（现值首个「」之前的中文名），不新造。
  ⛔ 只改 `dialogue` 字面；visual_facts／shot_size／camera_angle／lens_mm／movement／
     duration_sec／note 等一律零改动 —— 脚本内置**逐镜逐字段递归 diff** 自证。

第二件：D16 U01 ep003 首句（画外音）字幕行 `note` 补 Q104 三档档位词「人物不出画」。
  ⛔ 不改该行 text／in_sec／out_sec。

落盘防护：版本守卫（--force 逃生口）＋ sha256＋mtime 双锚 CAS ＋ os.replace 原子替换
          ＋ 写后回读 ＋ 备份至 reports/_bak_*

用法：python3 scripts/patch_D11_U01_dialogue_mavis.py [--dry-run] [--force]
"""
import json, os, re, shutil, sys, time, hashlib, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
UNITS = os.path.join(PROJ, "units")
REPORTS = os.path.join(PROJ, "reports")
D11 = os.path.join(UNITS, "U01", "D11.json")
D09 = os.path.join(UNITS, "U01", "D09.json")
D08 = os.path.join(UNITS, "U01", "D08.json")
D16 = os.path.join(UNITS, "U01", "D16.json")


def die(msg, code=2):
    print("[ABORT] %s" % msg)
    sys.exit(code)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def guard(p):
    st = os.stat(p)
    with open(p, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:16]
    return h, st.st_mtime_ns


def get_ep(doc, idx):
    for e in doc["episodes"]:
        for k in ("ep", "episode_id", "id", "index", "no"):
            if str(e.get(k)) == str(idx):
                return e
    return None


def strip_q(t):
    return (t or "").strip().strip("「」").strip()


def role_of(dlg):
    m = re.match(r"^([^「『]{1,8})[「『]", (dlg or "").strip())
    return m.group(1).strip() if m else ""


def diff_shots(old_doc, new_doc, ignore_keys=("dialogue",)):
    """递归比较两文档的 episodes[].shots[]，返回 (差异清单, 忽略键之外的差异清单)。
    差异项形如 (ep, shot_id, 字段路径, 旧值, 新值)。"""
    diffs, hard = [], []
    o = {int(e["ep"]): e for e in old_doc["episodes"]}
    n = {int(e["ep"]): e for e in new_doc["episodes"]}
    if set(o) != set(n):
        hard.append(("episode 集合不同", sorted(o), sorted(n)))
        return diffs, hard
    for ep in sorted(o):
        os_, ns_ = o[ep].get("shots", []), n[ep].get("shots", [])
        if len(os_) != len(ns_):
            hard.append(("ep%s 镜数不同" % ep, len(os_), len(ns_)))
            continue
        for so, sn in zip(os_, ns_):
            if set(so.keys()) != set(sn.keys()):
                hard.append(("ep%s shot%s 字段集合不同" % (ep, so.get("shot_id")),
                             sorted(so.keys()), sorted(sn.keys())))
                continue
            for k in so:
                if so.get(k) == sn.get(k):
                    continue
                diffs.append((ep, so.get("shot_id"), k, so.get(k), sn.get(k)))
                if k not in ignore_keys:
                    hard.append((ep, so.get("shot_id"), k, so.get(k), sn.get(k)))
    # 顶层与 episodes 级非 shots 字段
    for k in set(old_doc) | set(new_doc):
        if k == "episodes":
            continue
        if old_doc.get(k) != new_doc.get(k):
            hard.append(("顶层", k, old_doc.get(k), new_doc.get(k)))
    for ep in sorted(o):
        for k in set(o[ep]) | set(n[ep]):
            if k == "shots":
                continue
            if o[ep].get(k) != n[ep].get(k):
                hard.append(("ep%s 非镜字段" % ep, k, o[ep].get(k), n[ep].get(k)))
    return diffs, hard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    d11 = load(D11); d09 = load(D09); d08 = load(D08); d16 = load(D16)
    ver0 = d11.get("version")
    print("=== D11 U01 现盘 %s｜台词真源 D09 %s／D08 %s 互证 ===" %
          (ver0, d09.get("version"), d08.get("version")))

    # D09 行号 → 文本（**按集**，行号每集重置）；D08 body 对白（逐字互证）
    d9_by_ep = {}
    for l in d09.get("lines", []):
        d9_by_ep.setdefault(int(l.get("ep")), {})[l.get("idx")] = (l.get("text") or "")
    d8_by_ep = {}
    for e in d08["episodes"]:
        d8_by_ep[int(e["ep"])] = [b.get("text", "") for b in e.get("body", []) if b.get("type") == "dialogue"]

    # D16 对白行 → shot_id + D09 行号 K（硬锚：行上的 d15_line_ref）
    shot_k = {}
    for e in d16["episodes"]:
        ep = int(e["ep"])
        aud = e.get("subtitle_style", {}).get("subtitle_sync_audit", {})
        ref_by_seq = {r.get("seq"): r.get("d15_line_ref", "") for r in aud.get("rows", [])}
        for l in e.get("subtitle_style", {}).get("lines", []):
            if l.get("type") != "对白":
                continue
            m = re.search(r"#(\d+)", ref_by_seq.get(l.get("seq"), "") or "")
            if not m:
                die("ep%s seq%s 无 d15_line_ref，硬锚缺失" % (ep, l.get("seq")))
            shot_k.setdefault((ep, l.get("shot_id")), []).append(int(m.group(1)))

    changes = []
    for e in d11["episodes"]:
        ep = int(e["ep"])
        for s in e.get("shots", []):
            cur = (s.get("dialogue") or "").strip()
            ks = shot_k.get((ep, s.get("shot_id")), [])
            if not ks or not cur:
                continue
            role = role_of(cur)
            if not role:
                continue
            texts = []
            for k in ks:
                t = d9_lines.get(k)
                if t is None:
                    die("ep%s D09 缺行 #%s" % (ep, k))
                # 与 D08 body 逐字互证
                dl = d8_by_ep.get(ep, [])
                if k <= len(dl) and strip_q(dl[k - 1]) != strip_q(t):
                    die("ep%s #%s D09/D08 逐字不一致，中止：\n  D09=%s\n  D08=%s" % (ep, k, t, dl[k - 1]))
                texts.append(t.strip())
            new = "／".join("%s「%s」" % (role, t) for t in texts)
            if new != cur:
                changes.append({"ep": ep, "shot_id": s.get("shot_id"), "old": cur, "new": new,
                                "K": ks})
    print("\n=== dialogue 回正清单（%d 个字段）===" % len(changes))
    for c in changes:
        print("  ep%s shot%s（D09 %s）" % (c["ep"], c["shot_id"],
              "/".join("ep%d #%d" % (c["ep"], k) for k in c["K"])))
        print("     旧：%s" % c["old"])
        print("     新：%s" % c["new"])

    # ── 第二件：D16 U01 ep003 首句 note 补档位词
    ep3 = get_ep(d16, 3)
    note_change = None
    if ep3:
        for l in ep3.get("subtitle_style", {}).get("lines", []):
            if l.get("type") == "对白" and l.get("seq") == 2:
                old = l.get("note") or ""
                if "人物不出画" not in old:
                    new = old.replace("（画外音，不出画）", "（画外音 · 人物不出画 · 不出画）")
                    if new == old:
                        new = old.replace("画外音，不出画", "画外音 · 人物不出画 · 不出画")
                    if new != old:
                        note_change = {"old": old, "new": new}
                        l["note"] = new
                break
    print("\n=== D16 ep003 seq2 note ===")
    if note_change:
        print("  旧：%s" % note_change["old"])
        print("  新：%s" % note_change["new"])
    else:
        print("  无需改动（已含档位词或未命中待改写法）")

    if not changes and not note_change:
        print("\n[IDEMPOTENT] 无需写盘")
        return 0
    if args.dry_run:
        print("\n[dry-run] 不写盘")
        return 0

    # ── 落 D11（只改 dialogue）
    if changes:
        new_doc = load(D11)
        for e in new_doc["episodes"]:
            for s in e.get("shots", []):
                for c in changes:
                    if int(e["ep"]) == c["ep"] and s.get("shot_id") == c["shot_id"]:
                        s["dialogue"] = c["new"]
        diffs, hard = diff_shots(d11, new_doc)
        print("\n=== 「只改 dialogue」自证 ===")
        print("  dialogue 差异 %d 条；非 dialogue 差异 %d 条" % (len(diffs), len(hard)))
        for h in hard:
            print("     ⛔ %s" % (h,))
        if hard:
            die("存在 dialogue 之外的字段变化，中止不写盘", 3)
        sha0, mt0 = guard(D11)
        cur = load(D11).get("version")
        if cur != ver0 and not args.force:
            die("版本守卫：读时 %s，写前 %s；确认后 --force" % (ver0, cur))
        sha1, mt1 = guard(D11)
        if (sha1, mt1) != (sha0, mt0):
            die("CAS 失败：并发写者已改盘，本岗不覆盖他人字节", 5)
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak = os.path.join(REPORTS, "_bak_D11_U01_dialogue_%s" % ts)
        os.makedirs(bak, exist_ok=True)
        shutil.copy2(D11, os.path.join(bak, "D11.json"))
        maj, mino = ver0.lstrip("v").split(".")
        new_doc["version"] = "v%d.%d" % (int(maj), int(mino) + 1)
        tmp = D11 + ".tmp.%s" % ts
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(new_doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, D11)
        # 回读：再比一次
        back = load(D11)
        d2, h2 = diff_shots(d11, back)
        if h2:
            die("写后回读：出现 dialogue 之外的字段变化 %d 条" % len(h2), 4)
        print("  ✅ D11 U01 %s → %s｜sha16 %s → %s｜备份 %s" %
              (ver0, new_doc["version"], sha0, guard(D11)[0], os.path.basename(bak)))

    # ── 落 D16（只改 ep003 seq2 的 note）
    if note_change:
        new16 = load(D16)
        ver16 = new16.get("version")
        sha0, mt0 = guard(D16)
        cur = load(D16).get("version")
        if cur != ver16 and not args.force:
            die("D16 版本守卫：读时 %s，写前 %s" % (ver16, cur))
        sha1, mt1 = guard(D16)
        if (sha1, mt1) != (sha0, mt0):
            die("D16 CAS 失败：并发写者已改盘", 5)
        e3 = get_ep(new16, 3)
        for l in e3.get("subtitle_style", {}).get("lines", []):
            if l.get("type") == "对白" and l.get("seq") == 2:
                l["note"] = note_change["new"]
                break
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak = os.path.join(REPORTS, "_bak_D16_U01_ep003_note_%s" % ts)
        os.makedirs(bak, exist_ok=True)
        shutil.copy2(D16, os.path.join(bak, "D16.json"))
        maj, mino = ver16.lstrip("v").split(".")
        new16["version"] = "v%d.%d" % (int(maj), int(mino) + 1)
        tmp = D16 + ".tmp.%s" % ts
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(new16, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, D16)
        print("  ✅ D16 U01 %s → %s｜sha16 %s → %s｜备份 %s" %
              (ver16, new16["version"], sha0, guard(D16)[0], os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
