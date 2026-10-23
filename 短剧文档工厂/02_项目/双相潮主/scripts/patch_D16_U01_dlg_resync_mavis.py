#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D16 U01 对白行再同步（B 批 / R-028b-r2 文本回正模式）——台本编剧 2026-10-23 改稿波次同步器

两种模式（同一内容源，运行时读 D15/D09/D08/D07/D11 现值，不采信任何转述坐标）
--------------------------------------------------------------------------
--text-first   【R-028b-r2 派单模式】**只改字幕行 text 字面**，时码零改动。
               依据 D18 Q124（不得为迁就上游旧时长截短台词）与派单
               「⛔ 不得改任何 in_sec／out_sec／d15_vo_dur_sec／at_sec」。
               · 对白行 text ＝ D09/D08 现值**去引号**形式（与 A 批 ep002 体例一致，
                 U01 全部 32 条对白行中 31 条为裸文本）
               · golden3s_first_line.text ＝ 「」包裹形式（与 A 批 ep002 golden3s 体例一致）
               · 时码不动 ⇒ out_sec 仍逐条等于 D15 现值 at_sec＋dur_sec（规则④不被破坏）
               · 「新稿装不进现行配音预算」的缺口写进 pending_d15_sync，等 D15 回填后
                 由独立一单回灌时长（本岗不代改 D15 —— 他岗单写点）
   默认（无 --text-first）
               【B 批延后模式】新稿若装不进 D15 现行配音预算，则该行文字与 out_sec 一并
               延后到 D15 回填后再同步（避免字幕早于新稿配音收音而消失）。

硬约束（台账既有口径，脚本内置自检，任一不过即中止不写盘）
  ① 正文行标称停留 ≥ 1.2s（片头/片尾/角标除外）
  ② 正文行两两不重叠（左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠）
  ③ 正文行不越出 D07 段窗口（四段制边界，含并行段）
  ④ 有配音锚点的对白行 out_sec == D15 配音 at_sec + dur_sec（标称网格，0.1s）
  ⑤ 正文行不越出 D11 镜时段（含并行段副线回切窗口）
  ⑥ 黄金 3 秒：首句台词 in_sec ≤ 1.5s
  ⑦ 片尾 43~45s 不被挤占

写法纪律
  · 改本脚本重跑落盘，⛔ 不手改 D16 JSON
  · 版本守卫（Q64/Q80）＋ sha256 CAS ＋ 原子替换 ＋ 写后回读校验
  · 溯源常量（synced_row_count／no_vo_anchor_rows／sync_basis／verified_note）与
    历史留痕（note 里既有的「台词改稿待重定时」段）一律**不删不改**，只允许追加

用法
  python3 scripts/patch_D16_U01_dlg_resync_mavis.py --eps ep001 --text-first --dry-run
  python3 scripts/patch_D16_U01_dlg_resync_mavis.py --eps ep001 --text-first
  python3 scripts/patch_D16_U01_dlg_resync_mavis.py --dry-run            # 延后模式
  python3 scripts/patch_D16_U01_dlg_resync_mavis.py --plan-dur 3.5,3.2,2.3,1.5 --eps ep001
  --force  跳过版本守卫基线比对（逃生口，默认仍会拦）
"""
import json, os, re, shutil, sys, time, hashlib, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
UNITS = os.path.join(PROJ, "units")
REPORTS = os.path.join(PROJ, "reports")

D16 = os.path.join(UNITS, "U01", "D16.json")
D07 = os.path.join(UNITS, "U01", "D07.json")
D09 = os.path.join(UNITS, "U01", "D09.json")
D08 = os.path.join(UNITS, "U01", "D08.json")
D11 = os.path.join(UNITS, "U01", "D11.json")
D15 = os.path.join(UNITS, "U01", "D15.json")

BASELINE_D16_VERSION = "v1.35"      # 版本守卫基线（Q64/Q80）／2026-10-23 13:43 R-028b-r2 文本回正落盘后
EPS_DEFAULT = ["ep001", "ep002"]

MIN_DWELL = 1.2                      # D16 subtitle_style.min_dwell_sec
MODEL_SAFETY = 0.2                   # 语速模型安全余量（RMSE 0.19s + 保守余量）
GAP_MARGIN = 0.1                     # 每段尾部留白（避免压到切点）
GRID = 0.1                           # 标称时码网格
EXCLUDE_TYPES = ("角标", "片尾", "片头")

# 全局模式开关（由 --text-first 置位；此处给出定义，避免 NameError）
TEXT_FIRST = False


def die(msg, code=2):
    print("[ABORT] %s" % msg)
    sys.exit(code)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha16(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def get_ep(doc, idx):
    for e in doc["episodes"]:
        for k in ("ep", "episode_id", "id", "index", "no"):
            if str(e.get(k)) == str(idx):
                return e
    die("未找到 ep%s" % idx)
    return None


def strip_q(t):
    return (t or "").strip().strip("「」").strip()


def quoted(t):
    """golden3s 体例：「」包裹。"""
    return "「%s」" % strip_q(t)


# ---------- 预演 TTS 实测语速模型（用于「D15 预算是否够装新稿」的判定） ----------
PREVIEW_ITEMS = os.path.join(PROJ, "preview", "U01_tts", "items.json")
_MODEL = None
MODEL_NOTE = ""


def _feats(t):
    core = re.sub(r"[\s「」“”\"'』]", "", t or "")
    han = len(re.findall(r"[一-鿿]", core))
    pa = len(re.findall(r"[。！？…，、；：]", core))
    return han, pa


def fit_model():
    """对 preview/U01_tts/items.json 的 dialogue 条目做最小二乘拟合 dur = a + b*汉字 + c*停顿。
    返回 (a, b, c, rmse, n)。无样本时返回 None。"""
    if not os.path.exists(PREVIEW_ITEMS):
        return None
    with open(PREVIEW_ITEMS, encoding="utf-8") as f:
        raw = json.load(f)
    items = raw if isinstance(raw, list) else raw.get("items", raw)
    xs, ys = [], []
    for it in items:
        if it.get("kind") != "dialogue" or not it.get("dur"):
            continue
        h, p = _feats(it.get("text", ""))
        xs.append([1.0, float(h), float(p)])
        ys.append(float(it["dur"]))
    n = len(xs)
    if n < 6:
        return None
    S = [[0.0] * 3 for _ in range(3)]
    T = [0.0] * 3
    for x, y in zip(xs, ys):
        for a_ in range(3):
            for b_ in range(3):
                S[a_][b_] += x[a_] * x[b_]
            T[a_] += x[a_] * y
    A = [S[r][:] + [T[r]] for r in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        if abs(A[i][i]) < 1e-9:
            return None
        for r in range(3):
            if r != i:
                f = A[r][i] / A[i][i]
                for c in range(i, 4):
                    A[r][c] -= f * A[i][c]
    coef = [A[i][3] / A[i][i] for i in range(3)]
    rmse = (sum((sum(c * x for c, x in zip(coef, xi)) - y) ** 2 for xi, y in zip(xs, ys)) / n) ** 0.5
    return (coef[0], coef[1], coef[2], rmse, n)


def model_dur(text):
    """按实测模型预测一句台词的配音时长（秒）。模型不可用时返回 None。"""
    global _MODEL, MODEL_NOTE
    if _MODEL is None:
        _MODEL = fit_model() or False
        if _MODEL:
            a, b, c, rmse, n = _MODEL
            MODEL_NOTE = ("预演 TTS 实测拟合（items.json dialogue 条目 %d 条）："
                          "dur = %.4f + %.4f×汉字 + %.4f×停顿，RMSE=%.3fs" % (n, a, b, c, rmse))
    if not _MODEL:
        return None
    a, b, c, rmse, n = _MODEL
    h, p = _feats(text)
    return a + b * h + c * p


def r1(x):
    return round(x + 1e-9, 1)


def model_rmse():
    """语速模型自身的误差带（RMSE，秒）；模型不可用时退回 0（不设误差带）。"""
    model_dur("")  # 预热
    if not _MODEL:
        return 0.0
    return _MODEL[3]


# ---------- 取数 ----------
def collect(ep_id):
    """ep_id 形如 'ep001'。返回该集的全部现值与派生窗口。"""
    n = int(ep_id[2:])
    d16 = load(D16); d07 = load(D07); d09 = load(D09); d08 = load(D08); d11 = load(D11); d15 = load(D15)

    ep16 = get_ep(d16, n); ep07 = get_ep(d07, n); ep11 = get_ep(d11, n); ep08 = get_ep(d08, n)

    # D09 对白行：idx -> text
    d9_lines = {}
    for l in d09["lines"]:
        if str(l.get("ep")) == str(n):
            d9_lines[l.get("idx")] = l.get("text", "")
    # D08 body 对白（逐字互证用）
    d8_dl = [b.get("text", "") for b in ep08.get("body", []) if b.get("type") == "dialogue"]
    # D15 配音锚：line_ref "D09 epN #K" -> entry
    vo = {}
    for v in get_ep(d15, n).get("voice_over", []):
        m = re.search(r"#(\d+)", v.get("line_ref", "") or "")
        if m:
            vo[int(m.group(1))] = v

    # D07 段窗口
    segs = [{"idx": q.get("index"), "start": float(q["start_sec"]), "end": float(q["end_sec"]),
             "mode": q.get("mode", "串行"), "name": q.get("name", "")}
            for q in ep07.get("quad_segments", [])]
    # ── 片尾标题卡硬边界（2026-10-23 14:xx Q124 回灌时补入）────────────────────────
    # 背景：段窗口是 D07 的**叙事段**边界（末段＝38~45s），而片尾标题卡固定占 43~45s
    # 且与对白同在底部字幕带 ⇒ **画面文字行不得越过 43.0s**。段级分配若直接用段末（45.0s）
    # 作上界，会把末段的画面文字行排到 43.0s 之后 ⇒ 撞片尾（校验⑦）。
    # 处置：把「片尾 in_sec」登记为**末段的分配上界**（只夹**画面文字行的空档上界**，
    #       对白行仍由 D15 at_sec＋dur_sec 硬锚定，不受此夹取影响）。
    tail_rows = [r for r in ep16.get("subtitle_style", {}).get("lines", [])
                 if r.get("type") == "片尾" and r.get("in_sec") is not None]
    tail_limit = min(float(r["in_sec"]) for r in tail_rows) if tail_rows else None
    # D11 镜时段（累计）
    shot_win = {}
    t = 0.0
    for s in ep11.get("shots", []):
        d = float(s.get("duration_sec") or 0)
        shot_win[int(s["shot_id"])] = (t, t + d)
        t += d
    # 并行段副线回切窗口：D16 transitions[].parallel_cross_cut.alternate_points
    # 主线/副线镜号从 parallel_cross_cut.lines 的「主线＝镜N／副线＝镜N」解析
    para_win = []
    for tr in ep16.get("transitions", []):
        pcc = tr.get("parallel_cross_cut") or {}
        seg = pcc.get("segment")
        if not seg:
            continue
        pts = sorted(float(x) for x in (pcc.get("alternate_points") or []))
        if len(pts) < 2:
            continue
        txt = pcc.get("lines", "") or ""
        m_main = re.search(r"主线[＝=]\s*镜\s*(\d+)", txt)
        m_sub = re.search(r"副线[＝=]\s*镜\s*(\d+)", txt)
        segdef = next((s for s in segs if s.get("idx") is not None and int(s["idx"]) == int(seg)), None)
        main_shot = int(m_main.group(1)) if m_main else None
        sub_shot = int(m_sub.group(1)) if m_sub else None
        if main_shot is None and segdef:
            for sid, (a, b) in shot_win.items():
                if a <= segdef["start"] < b:
                    main_shot = sid
        if sub_shot is None and main_shot is not None:
            for sid, (a, b) in shot_win.items():
                if sid != main_shot and segdef and a < segdef["end"] and b > segdef["start"]:
                    sub_shot = sid
                    break
        if sub_shot is None:
            continue
        for i in range(len(pts) - 1):
            para_win.append((pts[i], pts[i + 1], sub_shot))

    return {"n": n, "ep16": ep16, "d9": d9_lines, "d8": d8_dl, "vo": vo,
            "segs": segs, "shot_win": shot_win, "para_win": para_win,
            "tail_limit": tail_limit,
            "d16": d16, "d07": d07, "d09": d09, "d08": d08, "d11": d11, "d15": d15}


def valid_windows(ctx, shot_id):
    """某镜号在本集的全部合法时间窗（主窗 + 并行回切窗）。"""
    wins = []
    if shot_id in ctx["shot_win"]:
        wins.append(ctx["shot_win"][shot_id])
    for a, b, sid in ctx["para_win"]:
        if sid == shot_id:
            wins.append((a, b))
    return wins


def seg_of(ctx, t):
    for i, s in enumerate(ctx["segs"]):
        if s["start"] <= t < s["end"]:
            return i, s
    return None, None


# ---------- 排布演算 ----------
def layout(ctx, plan_dur=None):
    """返回 (new_rows_by_seq, text_fix, diag, need_refill, dlg)。

    TEXT_FIRST 模式：**不做任何重排**，new 直接取现盘时码（时码零改动），
    只把对白行的文字同步问题算出来。
    """
    ep16 = ctx["ep16"]
    ss = ep16["subtitle_style"]
    lines = ss["lines"]
    aud = ss.get("subtitle_sync_audit", {})
    arows = {r["seq"]: r for r in aud.get("rows", [])}

    # 1) 对白行：由 D15 硬锚驱动
    dlg = []
    for r in lines:
        if r.get("type") != "对白":
            continue
        a = arows.get(r["seq"], {})
        m = re.search(r"#(\d+)", a.get("d15_line_ref", "") or "")
        if not m:
            die("ep%s seq%s 无 d15_line_ref，无法硬锚" % (ctx["n"], r["seq"]))
        k = int(m.group(1))
        v = ctx["vo"].get(k)
        if v is None:
            die("ep%s D15 无 D09 ep%d #%d 配音条目" % (ctx["n"], ctx["n"], k))
        dur = float(v["dur_sec"])
        if plan_dur and k in plan_dur:
            dur = float(plan_dur[k])
        at = float(v["at_sec"])
        dlg.append({"row": r, "K": k, "at": at, "dur": dur,
                    "ref": a.get("d15_line_ref", ""), "shot_id": r.get("shot_id")})

    # 2) 文字真源：D09 与 D08 逐字互证
    text_fix = []
    for d in dlg:
        k = d["K"]
        t9 = ctx["d9"].get(k)
        t8 = ctx["d8"][k - 1] if 0 < k <= len(ctx["d8"]) else None
        if t9 is None or t8 is None:
            die("ep%s D09/D08 缺 #%d" % (ctx["n"], k))
        if strip_q(t9) != strip_q(t8):
            die("ep%s #%d D09/D08 逐字不一致，中止：\n  D09=%s\n  D08=%s" % (ctx["n"], k, t9, t8))
        cur = d["row"].get("text", "")
        content_diff = strip_q(t9) != strip_q(cur)
        # 文本模式的判据＝**字面**逐字相等（对白行目标体例＝裸文本，U01 其余 31 条对白行
        # 均为裸文本；仅 seq2 曾带「」）。延后模式仍按内容（去引号）比对，避免体例误报。
        if content_diff or (TEXT_FIRST and cur != strip_q(t9)):
            # 对白行 target ＝ **去引号**裸文本（与 A 批 ep002 体例一致）
            text_fix.append({"seq": d["row"]["seq"], "old": cur,
                             "new": strip_q(t9), "new_quoted": quoted(t9), "K": k,
                             "kind": "内容回正" if content_diff else "体例归一（去引号）"})

    # 2b) 逐对白行算「配音预算缺口」（**与文字是否已回正无关**）——
    #     缺口是「新稿装不进 D15 现行配音预算」的量化事实，必须驱动 pending 状态；
    #     若只在本批有文字变更时才算，已回正的行会永远留着「文字延后」措辞（假陈述）。
    gap_by_seq = {}
    for d in dlg:
        target = strip_q(ctx["d9"].get(d["K"]) or "")
        pred = model_dur(target)
        if pred is None:
            continue
        # ── 缺口判据加「模型误差带」门（2026-10-23 14:xx Q124 回灌时补入）────────────
        # 背景：D15 v1.15 起，本集 9 条配音的 dur_sec **逐条实测**（matrix TTS 重出后取
        # ffprobe format=duration），另 1 条为预算值。此时若仍以「语速模型预测 + 安全余量
        # ＞ D15 现值」判缺口，会把**模型自身残差**当成真缺口 ⇒ 把已同步的行误标成
        # 「⏳ 待 D15 回填时长」（假陈述）。实测实例：ep2#4「换我用了。」实测 1.346781s
        # → D15 dur 1.5s（正确），而模型预测 1.45s＋0.2 余量＝1.65s ＞ 1.5s ⇒ 误判缺口
        # 0.15s（＜ 模型 RMSE 0.254s，落在噪声带内）。
        # 处置：**缺口必须超出模型自身的误差带**（RMSE）才算数 —— 噪声带内的残差不判缺口。
        if pred + MODEL_SAFETY > d["dur"] + model_rmse():
            gap_by_seq[d["row"]["seq"]] = {"seq": d["row"]["seq"], "K": d["K"], "new_text": target,
                                          "model_pred": round(pred, 2), "d15_dur": d["dur"],
                                          "short": round(pred + MODEL_SAFETY - d["dur"], 2)}
    need_refill = []
    deferred_seqs = set()
    for tf in text_fix:
        g = gap_by_seq.get(tf["seq"])
        if not g:
            continue
        deferred_seqs.add(tf["seq"])
        need_refill.append(dict(g, new_text=tf["new"]))
    if TEXT_FIRST:
        # 派单 R-028b-r2：字幕行文本**必须**与 D09/D08 逐字相等；不得为迁就上游旧时长
        # 而截短台词。本模式恢复文本、保持 out_sec ＝ D15 现值（规则④ 逐条相等不被破坏），
        # 「新稿装不进现行预算」的时码缺口写入 pending_d15_sync，待 D15 回填后由独立一单回灌。
        deferred_seqs = set()
        need_refill = [dict(g) for g in gap_by_seq.values()]
    text_fix_ok = [tf for tf in text_fix if tf["seq"] not in deferred_seqs]

    new = {}
    diag = []

    if TEXT_FIRST:
        # ── 文本模式：**时码一律取现盘**，不重排、不压缩、不移动任何一行
        for r in lines:
            if r.get("type") in EXCLUDE_TYPES:
                continue
            new[r["seq"]] = {"in_sec": r["in_sec"], "out_sec": r["out_sec"],
                             "dur": r1(float(r["out_sec"]) - float(r["in_sec"])),
                             "kind": r.get("type"), "shot_id": r.get("shot_id"),
                             "K": next((d["K"] for d in dlg if d["row"]["seq"] == r["seq"]), None),
                             "at": next((d["at"] for d in dlg if d["row"]["seq"] == r["seq"]), None),
                             "vo_dur": next((d["dur"] for d in dlg if d["row"]["seq"] == r["seq"]), None)}
        for d in dlg:
            r = d["row"]
            diag.append("  对白 seq%-3d K%d  in %-6s out %-6s （时码不动）"
                        % (r["seq"], d["K"], r["in_sec"], r["out_sec"]))
        return new, text_fix_ok, diag, need_refill, dlg, gap_by_seq

    # 3) 分段归组
    body = [r for r in lines if r.get("type") not in EXCLUDE_TYPES]
    for r in body:
        seg_i, _ = seg_of(ctx, float(r["in_sec"]))
        r["_seg"] = seg_i

    for d in dlg:
        r = d["row"]
        new[r["seq"]] = {"in_sec": r1(d["at"]), "out_sec": r1(d["at"] + d["dur"]),
                         "dur": r1(d["dur"]), "kind": "对白", "K": d["K"],
                         "at": d["at"], "vo_dur": d["dur"]}
        diag.append("  对白 seq%-3d K%d  in %-6s→%-6s out %-6s→%-6s (dur %s→%s)" % (
            r["seq"], d["K"], r["in_sec"], r1(d["at"]), r["out_sec"], r1(d["at"] + d["dur"]),
            r["out_sec"] - r["in_sec"], d["dur"]))

    # 4) 画面文字行：按 gap 比例压缩
    for si, seg in enumerate(ctx["segs"]):
        seg_rows = [r for r in body if r.get("_seg") == si]
        seg_rows.sort(key=lambda r: r["seq"])
        dlg_in = [d for d in dlg if seg_of(ctx, d["at"])[0] == si]
        dlg_in.sort(key=lambda d: d["at"])
        desc = [r for r in seg_rows if r.get("type") != "对白"]
        if not desc:
            continue
        # gap 边界：[段首/上一对白 out, 下一对白 in/段尾]
        # gap 边界：**原边界**用于判定「某行属于哪一段空档」（行序语义），
        #            **新边界**用于实际重排（对白出点后移后，画面文字必须让位）
        # 片尾夹取：末段的分配上界取「片尾 in_sec」（43.0s）而非段末（45.0s）——
        #            片尾标题卡与对白同在底部字幕带，画面文字行不得压到它。
        seg_end = seg["end"]
        tl = ctx.get("tail_limit")
        if tl is not None and seg["start"] < tl < seg_end:
            seg_end = tl
        orig_bounds = [seg["start"]]
        for d in dlg_in:
            orig_bounds.append(r1(float(d["row"]["out_sec"])))
        orig_bounds.append(seg_end)
        new_bounds = [seg["start"]]
        for d in dlg_in:
            new_bounds.append(r1(d["at"] + d["dur"]))
        new_bounds.append(seg_end)
        for gi in range(len(dlg_in) + 1):
            g0, g1 = new_bounds[gi], new_bounds[gi + 1]
            o0, o1 = orig_bounds[gi], orig_bounds[gi + 1]
            # 归属于本 gap 的 desc 行：按**原** in_sec 落在原空档内
            grp = [r for r in desc if o0 <= float(r["in_sec"]) < o1]
            if not grp:
                continue
            grp.sort(key=lambda r: r["seq"])
            orig_dwell = [float(r["out_sec"]) - float(r["in_sec"]) for r in grp]
            total = sum(orig_dwell)
            avail = (g1 - g0) - GAP_MARGIN
            if total <= avail + 1e-9:
                scale = 1.0
            else:
                scale = max(0.0, avail / total)
            dwells = [max(MIN_DWELL, r1(x * scale)) for x in orig_dwell]
            # 若压缩后仍放不下，按余量从大到小逐格削（不破 1.2s 下限）
            guard = 0
            while sum(dwells) > avail + 1e-9 and guard < 200:
                guard += 1
                idx = max(range(len(dwells)), key=lambda i: dwells[i] - MIN_DWELL)
                if dwells[idx] - GRID < MIN_DWELL - 1e-9:
                    break
                dwells[idx] = r1(dwells[idx] - GRID)
            cursor = g0
            for r, d in zip(grp, dwells):
                in_s = max(float(r["in_sec"]), cursor)
                in_s = r1(in_s)
                out_s = r1(in_s + d)
                new[r["seq"]] = {"in_sec": in_s, "out_sec": out_s, "dur": r1(d),
                                 "kind": "字幕", "shot_id": r.get("shot_id")}
                cursor = out_s
                if r["in_sec"] != in_s or abs((r["out_sec"] - r["in_sec"]) - d) > 1e-9:
                    diag.append("  字幕 seq%-3d  in %-6s→%-6s out %-6s→%-6s (dwell %s→%s)" % (
                        r["seq"], r["in_sec"], in_s, r["out_sec"], out_s,
                        r["out_sec"] - r["in_sec"], d))

    return new, text_fix_ok, diag, need_refill, dlg, gap_by_seq


def verify(ctx, new, plan_dur=None):
    """四项硬校验 + 镜时段 + 黄金3秒 + 片尾。返回 (ok, lines[])"""
    msgs = []
    ep16 = ctx["ep16"]
    lines = ep16["subtitle_style"]["lines"]
    body = [r for r in lines if r.get("type") not in EXCLUDE_TYPES]
    body.sort(key=lambda r: r["seq"])

    # ① 停留 ≥ 1.2s
    for r in body:
        d = new[r["seq"]]["out_sec"] - new[r["seq"]]["in_sec"]
        if d < MIN_DWELL - 1e-9:
            msgs.append("① 停留不足：seq%s %.1fs < %.1fs" % (r["seq"], d, MIN_DWELL))
    # ② 两两不重叠
    for a, b in zip(body, body[1:]):
        if new[b["seq"]]["in_sec"] < new[a["seq"]]["out_sec"] - 1e-9:
            msgs.append("② 重叠：seq%s(→%.1f) 与 seq%s(%.1f)" % (
                a["seq"], new[a["seq"]]["out_sec"], b["seq"], new[b["seq"]]["in_sec"]))
    # ③ 不越 D07 段窗口
    for r in body:
        si, seg = seg_of(ctx, new[r["seq"]]["in_sec"])
        if si is None:
            msgs.append("③ 越段：seq%s in=%.1f 不在任何段窗口内" % (r["seq"], new[r["seq"]]["in_sec"]))
            continue
        if new[r["seq"]]["out_sec"] > seg["end"] + 1e-9:
            msgs.append("③ 越段：seq%s out=%.1f > seg%d end=%.1f" % (
                r["seq"], new[r["seq"]]["out_sec"], si + 1, seg["end"]))
    # ④ 对白 out_sec == D15 at+dur
    for r in body:
        if r.get("type") != "对白":
            continue
        a = next((x for x in ctx["ep16"]["subtitle_style"]["subtitle_sync_audit"].get("rows", [])
                  if x["seq"] == r["seq"]), {})
        m = re.search(r"#(\d+)", a.get("d15_line_ref", "") or "")
        k = int(m.group(1))
        v = ctx["vo"][k]
        dur = float(plan_dur[k]) if (plan_dur and k in plan_dur) else float(v["dur_sec"])
        want_out = r1(float(v["at_sec"]) + dur)
        if abs(new[r["seq"]]["out_sec"] - want_out) > 1e-9 or abs(new[r["seq"]]["in_sec"] - float(v["at_sec"])) > 1e-9:
            msgs.append("④ 配音锚不符：seq%s in=%.1f(应%.1f) out=%.1f(应%.1f)" % (
                r["seq"], new[r["seq"]]["in_sec"], float(v["at_sec"]),
                new[r["seq"]]["out_sec"], want_out))
    # ⑤ 不越 D11 镜时段
    for r in body:
        sid = r.get("shot_id")
        wins = valid_windows(ctx, sid)
        if not wins:
            continue
        ok = any(new[r["seq"]]["in_sec"] >= a - 1e-9 and new[r["seq"]]["out_sec"] <= b + 1e-9
                 for a, b in wins)
        if not ok:
            msgs.append("⑤ 越镜：seq%s shot%s [%.1f,%.1f] 不在任何合法窗 %s" % (
                r["seq"], sid, new[r["seq"]]["in_sec"], new[r["seq"]]["out_sec"],
                [(round(a, 1), round(b, 1)) for a, b in wins]))
    # ⑥ 黄金3秒：首句台词 ≤1.5s
    dlg_rows = [r for r in body if r.get("type") == "对白"]
    if dlg_rows:
        first = min(dlg_rows, key=lambda r: new[r["seq"]]["in_sec"])
        if new[first["seq"]]["in_sec"] > 1.5 + 1e-9:
            msgs.append("⑥ 黄金3秒：首句 seq%s in=%.1f > 1.5" % (first["seq"], new[first["seq"]]["in_sec"]))
    # ⑦ 片尾 43~45 不被挤占
    tail = next((r for r in lines if r.get("type") == "片尾"), None)
    if tail:
        for r in body:
            if new[r["seq"]]["out_sec"] > float(tail["in_sec"]) + 1e-9:
                msgs.append("⑦ 片尾被挤占：seq%s out=%.1f > 片尾 in=%.1f" % (
                    r["seq"], new[r["seq"]]["out_sec"], float(tail["in_sec"])))
    return (len(msgs) == 0), msgs


def apply_to_doc(doc, ctx, new, text_fix, plan_dur=None, need_refill=None, dlg=None,
                  gap_by_seq=None):
    """把演算结果写进内存 doc（apply 模式）。返回变更清单。"""
    ep16 = get_ep(doc, ctx["n"])
    ss = ep16["subtitle_style"]
    changes = []
    dlg = dlg or []
    stamp = time.strftime("%Y-%m-%d %H:%M")
    # 批次标签：文本模式＝R-028b-r2；回灌模式＝Q124（D15 实测 dur 回灌）
    batch = "R-028b-r2" if TEXT_FIRST else "Q124 回灌（D15 实测 dur 回灌 · 分镜导演岗）"
    # 原文快照：pending_d15_sync 按**原文**匹配到行号（文字可能被本批改写）
    orig_text_by_seq = {r["seq"]: r.get("text") for r in ss["lines"]}
    defer_by_seq = {x["seq"]: x for x in (need_refill or [])}
    for r in ss["lines"]:
        n = new.get(r["seq"])
        if not n:
            continue
        old_in, old_out, old_txt = r["in_sec"], r["out_sec"], r.get("text")
        if abs(float(old_in) - n["in_sec"]) > 1e-9 or abs(float(old_out) - n["out_sec"]) > 1e-9:
            r["in_sec"] = n["in_sec"]; r["out_sec"] = n["out_sec"]
            changes.append({"seq": r["seq"], "type": r.get("type"), "old": [old_in, old_out],
                            "new": [n["in_sec"], n["out_sec"]], "text": old_txt})
        # 文字同步（仅对白行，且 D09/D08 互证过）
        if r.get("type") == "对白":
            for tf in text_fix:
                if tf["seq"] == r["seq"]:
                    r["text"] = tf["new"]
                    changes.append({"seq": r["seq"], "type": "对白", "text_old": tf["old"],
                                    "text_new": tf["new"]})
            # Q114 首选：对白行锚点 ＝ D09 现值台词（锚点写进 JSON，产物自解释）
            # ⛔ R-028b-r2 文本模式不写 anchor：派单范围＝「只改这 4 条对白行的 text 字面
            #    ＋ golden3s_first_line.text」，新增键位超出范围且可能触发 V1 未定义字段。
            if not TEXT_FIRST:
                d = next((x for x in dlg if x["row"]["seq"] == r["seq"]), None)
                if d is not None:
                    src = ctx["d9"].get(d["K"])
                    if src and r.get("anchor") != src:
                        r["anchor"] = src
                        changes.append({"seq": r["seq"], "type": "对白",
                                        "anchor_old": r.get("anchor"), "anchor_new": src})
            # 追加式审计留痕（只追加，不删改历史留痕）
            if r["seq"] in {tf["seq"] for tf in text_fix}:
                tf = next((t for t in text_fix if t["seq"] == r["seq"]), None)
                kind_txt = tf.get("kind", "内容回正") if tf else "内容回正"
                seg = ("｜【台词文字回正 · %s · 分镜导演岗】本行文字已逐字同步为 D09/D08 现值「%s」"
                       "（R-028b-r2 派单；%s；对白行取裸文本体例）。"
                       "**时码未动**：in_sec/out_sec 仍为 D15 现值 at_sec＋dur_sec 逐条相等；"
                       "新稿配音预算未就绪，时长回灌待声音设计岗回填 D15 后由独立一单处理。"
                       % (stamp, strip_q(r.get("text")), kind_txt))
                _old_note = r.get("note", "")
                r["note"] = (_old_note + seg)
                changes.append({"seq": r["seq"], "type": "note", "text_old": _old_note[-40:],
                                "text_new": r["note"][-40:]})
    # 审计块 rows：同步 in/out/dwell/d15_vo_dur_sec + text + action/verdict
    aud = ss.get("subtitle_sync_audit", {})
    row_text = {r["seq"]: r.get("text") for r in ss["lines"]}
    for a in aud.get("rows", []):
        n = new.get(a["seq"])
        if not n:
            continue
        a["in_sec"] = n["in_sec"]; a["out_sec"] = n["out_sec"]
        a["nominal_dwell_sec"] = r1(n["out_sec"] - n["in_sec"])
        a["float_dwell_sec"] = round(n["out_sec"] - n["in_sec"], 10)
        if row_text.get(a["seq"]) is not None and a.get("text") != row_text[a["seq"]]:
            _old_at = a.get("text")
            a["text"] = row_text[a["seq"]]      # 审计块 text 必须镜像产物行 text
            changes.append({"seq": a["seq"], "type": "audit_row_text",
                            "text_old": _old_at, "text_new": a["text"]})
        if n.get("kind") == "对白":
            a["d15_vo_at_sec"] = n["at"]; a["d15_vo_dur_sec"] = n["vo_dur"]
            a["action"] = "不动（D15 现值落锚后逐条相等）"
            a["verdict"] = "合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）"
        # 追加式留痕（审计块与产物行各留一段，历史段一律不动）
        if a["seq"] in {tf["seq"] for tf in text_fix}:
            seg = ("｜【台词文字回正 · %s · 分镜导演岗】审计块 text 已与产物行同步为 D09/D08 "
                   "现值「%s」；时码与配音锚零改动。" % (stamp, strip_q(row_text.get(a["seq"], ""))))
            _old_an = a.get("note", "")
            a["note"] = (_old_an + seg)
            changes.append({"seq": a["seq"], "type": "audit_row_note",
                            "text_old": _old_an[-40:], "text_new": a["note"][-40:]})
    # golden3s_first_line
    g = ss.get("golden3s_first_line")
    if g:
        m = re.search(r"#(\d+)", g.get("d15_line_ref", "") or "")
        if m:
            k = int(m.group(1))
            bare = strip_q(ctx["d9"].get(k) or "")
            if bare and g.get("text") != quoted(bare):
                changes.append({"seq": "golden3s", "type": "golden3s",
                                "text_old": g.get("text"), "text_new": quoted(bare)})
                g["text"] = quoted(bare)
                g["note"] = (g.get("note", "") +
                             "｜【台词文字回正 · %s · 分镜导演岗】首句原文已逐字同步为 D09/D08 "
                             "现值「%s」（R-028b-r2 派单）；d15_vo_at_sec／d15_vo_dur_sec／"
                             "status／target_at_sec **一律未动**。" % (stamp, bare))
        if not TEXT_FIRST:
            if new.get(2):
                g["d15_vo_at_sec"] = new[2]["at"]
                g["d15_vo_dur_sec"] = new[2]["vo_dur"]
        # ── 活指针跟版（2026-10-23 14:xx Q124 回灌批）──────────────────────────────
        # `verified_against_d15` 是**活指针**（D15 每升一版都要跟，否则指针腐烂）；
        # `verified_note` 是**事件溯源陈述**，按追加式补一段本批结论，**历史段一律不动**。
        # 幂等：指针未变则既不改指针也不追加（避免重跑时注水）。
        _d15v = str(ctx["d15"].get("version") or "")
        _old_ptr = aud.get("verified_against_d15")
        _new_ptr = ("%s（黄金 3 秒判据落点见 golden3s_first_line；秒级真值回 D15 at_sec 取）"
                    % _d15v)
        if _old_ptr != _new_ptr:
            _ep_timed = any(c.get("type") in ("对白", "字幕", "面板文字") and "old" in c
                            for c in changes)
            aud["verified_against_d15"] = _new_ptr
            aud["verified_note"] = aud.get("verified_note", "") + (
                "｜【Q124 回灌 · %s · 分镜导演岗】%s"
                "活指针 verified_against_d15 由 %s 跟到 %s。"
                % (stamp,
                   ("本集对白行 out_sec 已按 D15 %s 的 dur_sec 逐条回灌"
                    "（out_sec ＝ 配音 at_sec＋dur_sec 逐条严格相等）；画面文字行按段级空档重排让位"
                    "（与对白出点后移相接、停留 ≥1.2s、不越 D11 镜时段、末段以片尾 43.0s 为硬上界）；"
                    % (_d15v)) if _ep_timed else
                   ("本集对白行时码**未变**（D15 %s 未改本集配音时长，数值仍逐条相等）；" % _d15v),
                   _old_ptr, _d15v))
            changes.append({"seq": "verified", "type": "verified_pointer",
                            "text_old": _old_ptr, "text_new": _new_ptr})
    # pending_d15_sync：**状态驱动**（不依赖本批变更列表）——
    #   行状态由「产物行文字是否已逐字等于 D09 真值」＋「该行是否仍有配音预算缺口」共同决定：
    #     TEXT_OK ＋ 有缺口 → ⏳ 待 D15 回填时长（文字已回正、时码未动）
    #     TEXT_OK ＋ 无缺口 → ✅ 已消解
    #     TEXT_STALE      → ⏳ 文字与时码均延后（延后模式）
    #   幂等：状态未变则不动 action（保留原时间戳）；状态变了才改口径，
    #   避免留下「文字已回正却写着保持旧稿文字」的假陈述。
    _pend_seen = []
    MARK = {"GAP": "待 D15 回填时长", "OK": "已消解", "STALE": "均**延后**"}
    d9_by_seq = {}
    for d in dlg:
        d9_by_seq[d["row"]["seq"]] = strip_q(ctx["d9"].get(d["K"]) or "")
    # 匹配主键：d15_current_anchor.line_ref（"D09 epN #K"）——每行唯一，
    # 且不随产物行文字改写而失效（文字匹配在回正后会失配）。
    k_to_seq = {d["K"]: d["row"]["seq"] for d in dlg}
    for p in aud.get("pending_d15_sync", []) or []:
        seq = None
        _m = re.search(r"#(\d+)", ((p.get("d15_current_anchor") or {}).get("line_ref") or ""))
        if _m and int(_m.group(1)) in k_to_seq:
            seq = k_to_seq[int(_m.group(1))]
        if seq is None:
            for r in ss["lines"]:
                if r.get("type") != "对白":
                    continue
                if strip_q(orig_text_by_seq.get(r["seq"])) == strip_q(p.get("text")):
                    seq = r["seq"]
                    break
        if seq is None:
            for r in ss["lines"]:
                if r.get("type") != "对白":
                    continue
                if strip_q(r.get("text")) == strip_q(p.get("text")):
                    seq = r["seq"]
                    break
        if seq is None:
            continue
        n = new.get(seq)
        if not n:
            continue
        p["row_in_sec"] = n["in_sec"]; p["row_out_sec"] = n["out_sec"]
        p["d15_current_anchor"] = {"at_sec": n["at"], "dur_sec": n["vo_dur"],
                                   "line_ref": "D09 ep%d #%d" % (ctx["n"], n["K"])}
        _old_act = p.get("action") or ""
        truth = d9_by_seq.get(seq, "")
        row_txt = strip_q(next((r.get("text") for r in ss["lines"] if r["seq"] == seq), ""))
        gap = (gap_by_seq or {}).get(seq)
        act = p.get("action") or ""
        _pend_seen.append((p, act))
        if row_txt == truth:
            # 文字已逐字等于真源
            p["text"] = row_txt
            if gap:
                if MARK["GAP"] not in act:
                    p["action"] = ("⏳ 待 D15 回填时长（%s · %s）：本行**文字已逐字回正**为 "
                                   "D09/D08 现值「%s」；**时码未动**（out_sec 仍＝D15 配音 "
                                   "at_sec＋dur_sec 逐条相等，不违反 sync_rule）。新稿无实测音频，"
                                   "配音预算未就绪（语速模型预测需 %.2fs，D15 现值 dur 仅 %.1fs，"
                                   "缺 %.2fs）⇒ 待声音设计岗回填 D15 dur_sec 后，由总控另派独立一单"
                                   "回灌 out_sec（本岗不代改 D15 —— 他岗单写点）。"
                                   % (batch, stamp, row_txt, gap["model_pred"], gap["d15_dur"], gap["short"]))
            else:
                if MARK["OK"] not in act:
                    p["action"] = ("✅ 已消解（%s · %s）：本行文字已同步为 D09/D08 现值「%s」，"
                                   "out_sec ＝ D15 配音 at_sec＋dur_sec 逐条相等。"
                                   % (batch, stamp, row_txt))
        else:
            # 文字尚未回正 ⇒ 必须是「延后」措辞
            if MARK["STALE"] not in act:
                if gap:
                    p["action"] = ("⏳ 待 D15 回填（B 批 · %s）：本行文字＝D09/D08 现值「%s」，"
                                   "语速模型预测需 %.2fs（预演 TTS 实测拟合，RMSE 0.19s），"
                                   "而 D15 现值 dur 仅 %.1fs，差 %+.2fs —— 新稿装不进现行配音预算，"
                                   "故文字与 out_sec 均**延后**到声音设计岗回填 D15 后再同步；"
                                   "在此之前本行保持旧稿文字与旧时码（不违反 sync_rule）。"
                                   % (stamp, truth, gap["model_pred"], gap["d15_dur"], -gap["short"]))
                else:
                    p["action"] = ("⏳ 待 D15 回填（B 批 · %s）：本行文字＝D09/D08 现值「%s」；"
                                   "新稿无实测音频，待声音设计岗回填 D15 dur_sec 后再同步。"
                                   % (stamp, truth))
    for _p, _old in _pend_seen:
        if _p.get("action") != _old:
            changes.append({"seq": "pending_d15_sync", "type": "pending_action",
                            "text_old": _old[:60], "text_new": _p.get("action", "")[:60]})
    # sync_records 追加事件
    recs = aud.setdefault("sync_records", [])
    _main = [c for c in changes if c.get("type") in ("对白", "golden3s") and "text_old" in c]
    _time = [c for c in changes if "old" in c and c.get("type") in ("对白", "字幕", "面板文字")]
    if _main:
        _ev = "D16 U01 ep%03d · 对白行文字逐字回正（R-028b-r2；时码零改动）" % ctx["n"]
        _bs = ("台本编剧 2026-10-23 改稿波次；台词真源＝D09 U01 lines[]，与 D08 body[] 逐字互证。"
               "B 批（13:25）曾以「新稿装不进 D15 现行配音预算」为由把文字与时码一并延后；"
               "R-028b-r2 派单改判为**文字立即回正、时码待 D15 回填后另单回灌**"
               "（D18 Q124：不得为迁就上游旧时长截短台词）。")
        _method = ("只改字幕行 text 字面（对白行取裸文本，golden3s 取「」包裹）＋ 追加式审计留痕；"
                   "in_sec／out_sec／d15_vo_at_sec／d15_vo_dur_sec／at_sec **一律不动**；"
                   "审计块 rows[].text 同步镜像产物行（否则产物自相矛盾）。")
        _notch = ["in_sec / out_sec", "d15_vo_at_sec / d15_vo_dur_sec",
                  "golden3s_first_line 的 status 与 target_at_sec",
                  "画面文字行与面板文字行", "43~45s 片尾行", "D15 本体", "D08／D09／D11／D12"]
        _rows = [{"ep": ctx["n"], "seq": c["seq"], "old_text": c.get("text_old"),
                  "new_text": c.get("text_new")} for c in changes if "text_old" in c]
    elif _time:
        # ── Q124 回灌批（2026-10-23 14:xx）：D15 v1.15 按新稿逐条重出 TTS 并实测 dur_sec，
        #    本岗按 D18 Q124 的固定顺序「先 D15 重定时长 → 再回灌 D16 out_sec → 最后回填
        #    golden3s_first_line.text」执行第三步的第二步：**回灌对白行 out_sec**，
        #    并让画面文字行（字幕／面板文字）为其让位（段级空档重排，末段以片尾 43.0s 为硬上界）。
        _ev = "D16 U01 ep%03d · Q124 回灌：按 D15 v1.15 实测 dur_sec 回灌对白行 out_sec ＋ 画面文字行让位重排" % ctx["n"]
        _bs = ("声音设计岗 D15 U01 v1.15 已按台本编剧 12:47／12:51 改稿波次的**新台词**逐条重出 TTS，"
               "并按 ffprobe format=duration **实测值**重定 dur_sec（ep1 4 条、ep2 4 条、ep3 1 条）。"
               "本岗按 D18 Q124 的固定顺序回灌 D16：D15 先定出正确时长 ⇒ 本岗再回灌对白行 out_sec"
               "（＝配音 at_sec＋dur_sec，逐条严格相等）⇒ golden3s_first_line 同步。"
               "**不回改 D15、不截短台词文字**（Q124 明禁「截短字幕行去凑上游旧时长」）。"
               "画面文字行（字幕／面板文字）按段级空档重排：与对白出点后移相接、停留不小于 1.2s、"
               "不越 D11 镜时段、末段以片尾标题卡 43.0s 为硬上界（片尾与对白同在底部字幕带）。")
        _method = ("对白行：in_sec ＝ D15 配音 at_sec（不动）、out_sec ＝ at_sec＋dur_sec（D15 v1.15 实测值）；"
                   "画面文字行：段级空档按比例压缩/平移，行间最小间隔 0.1s、尾留白 0.1s，停留 ≥1.2s，"
                   "不越镜时段、不越片尾 43.0s；审计块 rows[]／synced_row_count／pending_d15_sync 同步刷新；"
                   "pending 动作按**状态驱动**重算（不再用语速模型残差判缺口）。")
        _notch = ["D15 本体（他岗单写点）", "D08／D09／D11／D12", "对白行 text 字面",
                  "43~45s 片尾行本体", "D16 的 cuts／transitions／title_card", "golden3s 的 status 与 target_at_sec"]
        _rows = [{"ep": ctx["n"], "seq": c["seq"], "type": c.get("type"),
                  "old": c.get("old"), "new": c.get("new")} for c in _time]
    else:
        _ev = "D16 U01 ep%03d · pending_d15_sync 口径订正（文字已回正、时码待 D15 回填）" % ctx["n"]
        _bs = ("上一批把文字回正与时码一并写成「均延后…保持旧稿文字」，与产物行实际状态矛盾（假陈述）。"
               "本轮按状态驱动重算：产物行文字已逐字等于 D09 真值 ⇒ 口径改为「文字已回正、时码未动、"
               "待 D15 回填 dur_sec 后另单回灌 out_sec」。**本轮零文字改动、零时码改动。**")
        _method = "本轮零改动（仅口径订正）。"
        _notch = ["全部产物行"]
        _rows = []
    recs.append({
        "date": time.strftime("%Y-%m-%d"),
        "event": _ev,
        "basis": _bs,
        "method": _method,
        "not_changed": _notch,
        "rows": _rows,
        "applied_by": "分镜导演（bot_1855d6ce9cdd）",
    })
    return changes


def main():
    global TEXT_FIRST
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", default=",".join(EPS_DEFAULT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--text-first", action="store_true",
                    help="只改字幕行 text 字面，时码零改动（R-028b-r2 派单模式）")
    ap.add_argument("--plan-dur", default="", help="规划模式：逗号分隔的 dur 列表，按该集对白行 K 顺序")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    TEXT_FIRST = bool(args.text_first)

    d16 = load(D16)
    read_sha = sha16(D16)          # CAS 基准：本岗读取时的盘面 sha
    upstream_sha = {"D09": sha16(D09), "D08": sha16(D08), "D15": sha16(D15)}
    model_dur("")   # 预热拟合，确保 MODEL_NOTE 在任何分支都可见
    cur_ver = d16.get("version")
    if cur_ver != BASELINE_D16_VERSION and not args.force:
        die("版本守卫：D16 U01 现为 %s，基线 %s；确认后用 --force" % (cur_ver, BASELINE_D16_VERSION))

    eps = [e.strip() for e in args.eps.split(",") if e.strip()]
    plan_dur = None
    if args.plan_dur:
        plan_dur = {}
        vals = [float(x) for x in args.plan_dur.split(",")]
        # 只对第 1 个 ep 生效（规划模式按集单独跑）
        ctx0 = collect(eps[0])
        ks = []
        for r in ctx0["ep16"]["subtitle_style"]["lines"]:
            if r.get("type") == "对白":
                a = next((x for x in ctx0["ep16"]["subtitle_style"]["subtitle_sync_audit"].get("rows", [])
                          if x["seq"] == r["seq"]), {})
                m = re.search(r"#(\d+)", a.get("d15_line_ref", "") or "")
                if m:
                    ks.append(int(m.group(1)))
        if len(vals) != len(ks):
            die("--plan-dur 数量 %d 与对白行数 %d 不符（K=%s）" % (len(vals), len(ks), ks))
        plan_dur = dict(zip(ks, vals))

    doc = load(D16)
    all_changes = []
    blocked = []
    for ep_id in eps:
        ctx = collect(ep_id)
        new, text_fix, diag, need_refill, dlg, gap_by_seq = layout(ctx, plan_dur)
        ok, msgs = verify(ctx, new, plan_dur)
        print("\n=== %s（%s）===" % (
            ep_id, "文本回正模式（时码零改动）" if TEXT_FIRST else
            ("规划模式 dur 覆盖：%s" % plan_dur if plan_dur else "读 D15 现值")))
        print("  段窗口：%s" % [(s["start"], s["end"]) for s in ctx["segs"]])
        print("  %s" % (MODEL_NOTE or "（语速模型不可用）"))
        print("  文字脱节：%d 条；本批可同步 %d 条；其中时码待回灌 %d 条"
              % (len(text_fix), len(text_fix), len(need_refill)))
        for tf in text_fix:
            print("     ✔ seq%-3d 「%s」→「%s」［%s］%s"
                  % (tf["seq"], strip_q(tf["old"]), strip_q(tf["new"]), tf.get("kind", ""),
                     "（文字回正，时码不动）" if TEXT_FIRST else "（新稿装得进现行预算，零时码改动）"))
        for x in diag:
            print(x)
        if not ok:
            print("  ✗ 四硬校验未过：")
            for m in msgs:
                print("     - " + m)
            die("ep%s 校验未过，中止不写盘" % ep_id, 3)
        print("  ✅ 四硬校验 + 镜时段 + 黄金3秒 + 片尾 全部通过")
        if need_refill:
            print("  ⏳ D15 未回填（新稿装不进现行配音预算）：以下 %d 条**时码**待回灌：" % len(need_refill))
            for x in need_refill:
                print("     - seq%-3d K%d 「%s」 模型预测 %.2fs ＞ D15 现值 %.1fs（缺 %.2fs）"
                      % (x["seq"], x["K"], x["new_text"], x["model_pred"], x["d15_dur"], x["short"]))
            blocked += need_refill
        ch = apply_to_doc(doc, ctx, new, text_fix, plan_dur, need_refill, dlg, gap_by_seq)
        all_changes += ch
        print("  变更行数：%d" % len(ch))

    if blocked and not args.plan_dur and not TEXT_FIRST:
        print("\nℹ 本批已落「装得进现行预算」的部分；其余 %d 条延后，待声音设计岗回填 D15 后"
              "重跑本脚本即可自动同步（脚本运行时读 D15 现值）。**本岗不代改 D15（他岗单写点）。**"
              % len(blocked))
    if blocked and TEXT_FIRST:
        print("\nℹ 文字已全部回正；上列 %d 条的**时码缺口**待声音设计岗回填 D15 dur_sec 后，"
              "由总控另派独立一单回灌 out_sec（单写点纪律）。" % len(blocked))

    if not all_changes:
        print("\n[IDEMPOTENT] 演算结果与现盘逐字节一致，无需写盘。")
        return 0

    print("\n=== 变更清单 ===")
    for c in all_changes:
        if "text_old" in c:
            print("  %-8s %-4s 文字 「%s」→「%s」" % (c["seq"], c["type"], c["text_old"], c["text_new"]))
        elif "anchor_old" in c:
            print("  %-8s %-4s anchor %s→%s" % (c["seq"], c["type"],
                                                c["anchor_old"], c["anchor_new"]))
        elif "old" in c:
            print("  seq%-3s %-4s 时码 %s→%s" % (c["seq"], c["type"], c["old"], c["new"]))
        else:
            print("  seq%-3s %-4s 变更 %s" % (c["seq"], c["type"],
                                              {k: v for k, v in c.items() if k not in ("seq", "type")}))

    if args.dry_run or args.plan_dur:
        print("\n[dry-run] 不写盘。")
        return 0

    # 落盘：备份 → 上游复核 → CAS 比对 → 原子替换 → 回读校验
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(REPORTS, "_bak_D16_U01_%s_%s" % ("textresync_r028b2" if TEXT_FIRST else "dlgresync", ts))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(D16, os.path.join(bak, "D16.json"))
    for nm, p in (("D09", D09), ("D08", D08), ("D15", D15)):
        now = sha16(p)
        if now != upstream_sha[nm]:
            die("上游 %s 在本岗作业期间被改盘（sha %s → %s），本岗不落盘，请重跑。"
                % (nm, upstream_sha[nm], now), 6)
    before_sha = sha16(D16)
    # CAS：比对**读取时**的 sha 与写入前的 sha；若并发写者已改盘则中止，不覆盖他人字节
    if before_sha != read_sha:
        die("CAS 失败：本岗读取时 sha=%s，写入前 sha=%s（并发写者已改盘），"
            "本岗不覆盖他人字节，中止。请重跑（脚本会取新基线）。" % (read_sha, before_sha), 5)
    new_ver = "v%d.%d" % (int(cur_ver[1:].split(".")[0]), int(cur_ver[1:].split(".")[1]) + 1)
    doc["version"] = new_ver
    tmp = D16 + ".tmp.%s" % ts
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, D16)
    after_sha = sha16(D16)
    # 回读校验：四硬校验 + 本批文字必须与 D09 逐字相等
    chk = load(D16)
    for ep_id in eps:
        ctx = collect(ep_id)
        new2, tf2, _d2, _nr2, _dl2, _gs2 = layout(ctx, None)
        ok2, msgs2 = verify(ctx, new2, None)
        if not ok2:
            die("写后回读校验失败：%s" % msgs2, 4)
        ep_chk = get_ep(chk, ctx["n"])
        for r in ep_chk["subtitle_style"]["lines"]:
            if r.get("type") != "对白":
                continue
            a = next((x for x in ep_chk["subtitle_style"]["subtitle_sync_audit"].get("rows", [])
                      if x["seq"] == r["seq"]), {})
            m = re.search(r"#(\d+)", a.get("d15_line_ref", "") or "")
            if not m:
                continue
            k = int(m.group(1))
            if strip_q(ctx["d9"].get(k, "")) != strip_q(r.get("text", "")):
                die("写后回读：对白行 seq%s 与 D09 ep%d #%d 不逐字相等" % (r["seq"], ctx["n"], k), 4)
    print("\n落盘完成：D16 U01 %s → %s｜sha16 %s → %s｜备份 %s" % (
        cur_ver, new_ver, before_sha, after_sha, os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
