#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_D16_q100_finalize.py —— Q100 字幕密度填充的收口补丁（分镜导演岗 · 2026-10-23）

背景
  密度填充（scripts/densify_subtitles.py）落地后，全表按 (in_sec, seq) 重排 ⇒ **seq 重编**。
  D16 各集 `subtitle_style.dwell_calc_convention`（口径长文本）与
  `subtitle_style.subtitle_sync_audit.rows[]／dwell_floor_rows[]`（结构化镜像）里
  写着**改号前的 seq 指针**，会指向别的行 ⇒ 指针失效。

本脚本做三件事，**只改 D16**（不碰 D08／D09／D11／D12／D15／D13／D14／shared）：

① **新增行不留 1.2s 贴边行**（U02 3 条）
   D16 `min_dwell_sec = 1.2`，但各集口径句「本集标称 1.2s 的行：…」按**本集全部 1.2s 行**列举。
   本轮新增行若也压到 1.2s，这些口径句就变成**漏列**。
   ⇒ 把 3 条新增行从标称 1.2s 放宽到 1.3s：口径句保持原样即真，新增行全部 ≥1.3s。

② **按仓库既有规则订正指针**（复用本岗既有工具，不另起炉灶）
   直接调用 `scripts/patch_D16_U01_audit_mirror_and_hook_note.py` 里的
   `refresh_audit()`（重刷结构化镜像）与 `fix_convention()`（订正口径长文本指针，R1–R9）。
   该工具的口径＝**事件叙述原文保留、只订正现盘指针**，本脚本沿用同一口径，
   不重新发明规则。已存在的「seq 指针订正」段先摘掉再由工具按现盘重生成。

③ 追加本轮 Q100 的留痕（sync_records）。

守卫：写前重读 version＋SHA，与读盘时不一致即中止（防并发抢盘）；
      差异白名单只允许 `/version`、`/episodes/<n>/subtitle_style/dwell_calc_convention`、
      `/episodes/<n>/subtitle_style/subtitle_sync_audit/**`，
      以及 `lines[]` 里那 3 条被放宽时码的行。

用法：python3 scripts/patch_D16_q100_finalize.py --project . [--unit U01] [--dry-run]
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ① 需要放宽到 1.3s 的新增行：(集, 文本, 新 in_sec, 新 out_sec)
TIMING_FIX = {
    "U02": [
        (9, "人影：沉默站立", 41.6, 42.9),
        (12, "公告第二栏：不计入救治序列", 11.6, 12.9),
        (14, "城防图：标着机械厂的名字", 40.7, 42.0),
    ],
}

# 本轮 densify 的写前备份（= 改号前状态），用于核验「旧 seq → 文本」映射
OLD_SRC = {
    "U01": "reports/_bak_densify_U01_20261023-122718/D16.json",
    "U02": "reports/_bak_densify_U02_20261023-122710/D16.json",
}

STAMP_HEAD = "【seq 指针订正 · 2026-10-23 · 分镜导演岗】"


def load_mirror():
    spec = importlib.util.spec_from_file_location(
        "mirror", os.path.join(HERE, "patch_D16_U01_audit_mirror_and_hook_note.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def bump(o):
    v = re.sub(r"^v+", "v", str(o.get("version", "v1.0")))
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def all_one2_rows(d16):
    """全单元标称 1.2s 的正文行（排除角标／片尾）→ [(ep, seq), ...]"""
    out = []
    for e in d16["episodes"]:
        for l in e["subtitle_style"]["lines"]:
            if l.get("type") in ("角标", "片尾"):
                continue
            if abs((round(float(l.get("out_sec", 0)), 1)
                    - round(float(l.get("in_sec", 0)), 1)) - 1.2) < 1e-9:
                out.append((e["ep"], l.get("seq")))
    return out


def fix_u02_one2_sentence(ss, ep, lines):
    """U02 口径句「本集标称 1.2s 的行：seqN「text」…」按文本锚点订正 seq。"""
    dcc = ss.get("dwell_calc_convention")
    if not isinstance(dcc, str):
        return False
    by_text = {}
    for l in lines:
        by_text.setdefault(str(l.get("text") or ""), []).append(l)
    fixed = [0]

    def sub(m):
        txt = m.group("text")
        cand = by_text.get(txt)
        if cand and len(cand) == 1:
            fixed[0] += 1
            return "seq%s「%s」" % (cand[0].get("seq"), txt)
        return m.group(0)

    pat = re.compile(r"seq\s*(?P<num>\d+)「(?P<text>[^」]*)」")
    new = pat.sub(sub, dcc)
    if new != dcc:
        ss["dwell_calc_convention"] = new
    return bool(fixed[0])


def process(unit, root, dry=False):
    mirror = load_mirror()
    p16 = os.path.join(root, "units", unit, "D16.json")
    p15 = os.path.join(root, "units", unit, "D15.json")
    p09 = os.path.join(root, "units", unit, "D09.json")
    d16 = json.load(open(p16, encoding="utf-8"))
    d15 = json.load(open(p15, encoding="utf-8"))
    d09 = json.load(open(p09, encoding="utf-8"))

    before_sha = sha16(p16)
    before_ver = d16.get("version")
    snapshot = copy.deepcopy(d16)

    # ── ① 时码放宽 ──
    tweak_rows = set()
    for (ep_no, txt, ni, no) in TIMING_FIX.get(unit, []):
        e = next((x for x in d16["episodes"] if x["ep"] == ep_no), None)
        if e is None:
            print(f"⚠ {unit} ep{ep_no} 不存在，跳过时码放宽")
            continue
        row = next((l for l in e["subtitle_style"]["lines"]
                    if l.get("text") == txt and l.get("type") == "字幕"), None)
        if row is None:
            print(f"⚠ {unit} ep{ep_no} 找不到待放宽的行「{txt}」，跳过")
            continue
        if abs(float(row["in_sec"]) - ni) < 1e-9 and abs(float(row["out_sec"]) - no) < 1e-9:
            continue
        if round(float(no) - float(ni), 2) < 1.2 - 1e-9:
            print(f"❌ {unit} ep{ep_no}「{txt}」放宽后停留 <1.2s，放弃")
            return 1
        row["in_sec"], row["out_sec"] = ni, no
        tweak_rows.add((ep_no, txt))

    # ── ② 按既有规则订正指针 ──
    mirror.D15_VERSION = d15.get("version")          # 现盘真实版本，别用脚本里的历史戳
    mirror.REFRESH_EPS = [e["ep"] for e in d16["episodes"]]
    one2 = all_one2_rows(d16)
    n_fixed = 0
    for e in d16["episodes"]:
        ss = e["subtitle_style"]
        ep = e["ep"]
        # 先摘掉旧的「seq 指针订正」段，让工具按现盘重生成（避免旧段落里的现盘指针残留）
        dcc = ss.get("dwell_calc_convention")
        if isinstance(dcc, str) and STAMP_HEAD in dcc:
            head, _, _tail = dcc.partition(STAMP_HEAD)
            ss["dwell_calc_convention"] = head.rstrip("｜").rstrip()
        _aud, rows, _floor, _pending = mirror.refresh_audit(e, d15, d09)
        if mirror.fix_convention(ss, ep, rows, one2):
            n_fixed += 1
        if fix_u02_one2_sentence(ss, ep, ss.get("lines", [])):
            n_fixed += 1
        aud = ss.get("subtitle_sync_audit")
        if isinstance(aud, dict):
            aud.setdefault("sync_records", []).append({
                "date": "2026-10-23",
                "event": "Q100 字幕密度填充收口：seq 指针订正 ＋ 新增行时码放宽到 ≥1.3s",
                "basis": ("密度填充后全表按 (in_sec,seq) 重排（seq 重编），各集 dwell_calc_convention "
                          "口径长文本与 subtitle_sync_audit.rows[]／dwell_floor_rows[] 里写着"
                          "改号前的 seq 指针，会指向别的行 ⇒ 按文本锚点订正。"),
                "method": ("复用本岗既有工具 scripts/patch_D16_U01_audit_mirror_and_hook_note.py 的 "
                           "refresh_audit()／fix_convention()（R1–R9），口径不变："
                           "**事件叙述原文保留、只订正现盘指针**；"
                           "另把 3 条新增行由标称 1.2s 放宽到 1.3s，"
                           "以保持各集「本集标称 1.2s 的行」口径句仍为真。"),
                "not_changed": ["镜数与镜时", "D14 白模与逐镜交接包（V11 不受影响，不重跑 Blender）",
                                "D08 正文与字数档", "D09 台词与潜台词", "D12 提示词", "D15 混音曲线",
                                "D16 对白行的 in_sec/out_sec（与 D15 配音逐条相等，未触碰）"],
                "applied_by": "分镜导演（bot_1855d6ce9cdd）",
            })

    # ── 差异白名单 ──
    def flat(o, p=""):
        out = {}
        if isinstance(o, dict):
            for k, v in o.items():
                out.update(flat(v, f"{p}/{k}"))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                out.update(flat(v, f"{p}/{i}"))
        else:
            out[p] = o
        return out

    allowed = ["/version"]
    for i in range(0, 20):
        allowed.append(f"/episodes/{i}/subtitle_style/dwell_calc_convention")
        allowed.append(f"/episodes/{i}/subtitle_style/subtitle_sync_audit/")
    # lines[] 里只允许「被放宽时码的那几条」的 in_sec/out_sec 变化
    allowed_line_paths = set()
    for e in d16["episodes"]:
        for idx, l in enumerate(e["subtitle_style"]["lines"]):
            if (e["ep"], str(l.get("text") or "")) in tweak_rows:
                eidx = d16["episodes"].index(e)
                allowed_line_paths.add(f"/episodes/{eidx}/subtitle_style/lines/{idx}/in_sec")
                allowed_line_paths.add(f"/episodes/{eidx}/subtitle_style/lines/{idx}/out_sec")
    a, b = flat(snapshot), flat(d16)
    bad = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) == b.get(k):
            continue
        if any(k.startswith(pfx) for pfx in allowed):
            continue
        if k in allowed_line_paths:
            continue
        bad.append(k)
    if bad:
        print(f"❌ {unit} 差异白名单外变更 {len(bad)} 处，首 8：{bad[:8]}")
        return 1

    bump(d16)
    if dry:
        print(f"[DRY-RUN] {unit} D16 {before_ver} → {d16['version']}；"
              f"口径指针订正集数 {n_fixed}；时码放宽 {len(tweak_rows)} 条")
        return 0

    cur = json.load(open(p16, encoding="utf-8"))
    if cur.get("version") != before_ver or sha16(p16) != before_sha:
        print(f"❌ {unit} 并发守卫：写前复核失败（version/sha 漂移）⇒ 另一写者已动盘，退出不抢盘")
        return 1

    bak = os.path.join(root, "reports",
                       f"_bak_D16_q100_finalize_{unit}_{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, "D16.json"))
    tmp = p16 + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, p16)
    after = json.load(open(p16, encoding="utf-8"))
    if after.get("version") != d16["version"]:
        print("❌ 写后 version 校验失败")
        return 1
    print(f"✅ {unit} D16 {before_ver} → {d16['version']}；口径指针订正集数 {n_fixed}；"
          f"时码放宽 {len(tweak_rows)} 条；备份 {bak}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--unit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    units = [args.unit] if args.unit else ["U01", "U02"]
    rc = 0
    for u in units:
        rc |= process(u, root, args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
