#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D16_U01_ep002_a_batch_mavis.py —— 分镜导演：**D16 U01 ep002 A 批**
  ① 3 条对白字幕行文字同步为**对白真源现值**（D09 U01，与 D08 U01 逐字互证）
  ② 6 条画面文字行锚点修复（重锚／改写，新文案逐字命中该镜 D11 visual_facts）
  ③ 另 1 条画面文字行一并重锚（「工具箱清单：扳手 · 半卷胶布」——旧稿物资段已删）
  ④ **Q114 首选**：把锚点写进 D16 JSON 结构化字段（每行加 `anchor`），不再只活在外部清单
  ⑤ 审计块 rows[].text / pending_d15_sync[] 同步为新稿（文本已同步、时长仍待 B 批）
  ⑥ golden3s_first_line.text 一并同步为真源现值（d15_vo_dur_sec 属 B 批，不动）

派单
----
企划合规 2026-10-23 12:43 / 12:52 重投《D16 U01 ep002 字幕行同步与锚点修复》A 批（总控/验收裁决人）。

⚠️ **派单里的对白文本已过期 —— 本脚本不采信转述，一律以现盘真源为准**
------------------------------------------------------------
派单（12:43/12:52）给的 3 条新对白是**台本编剧 12:33/12:34 那一版**。但现盘已再改一轮：
  · **D08 U01 v1.16**（12:51，body 13 条，word_count base=232 ✅）＝ 剧本层真源
  · **D09 U01 v1.8**（12:47）＝ 对白真源，ep2 #1~#4 与 D08 v1.16 **逐字一致**
  · D11 v1.17（12:39）／D12 v1.10（12:37）／D15 v1.13（12:16）／D16 v1.30（12:36）**均落后**
⇒ 本脚本**运行时从 D09 实时取对白**，并断言 **D09 与 D08 逐字互证**；两边不一致即中止（不猜、不折中）。
⇒ D11 的 dialogue 字段仍落后于 D09（派单红线④禁止本批碰 D11）⇒ 本脚本**只报告不阻断**，随回执呈报。

不动的部分（A 批范围外）
------------------------
  · **时码一律不动**：in_sec／out_sec 一个字节都不改（out_sec ＝ D15 配音 at_sec＋dur_sec 的等式必须保住）；
    时长同步属 B 批（等声音设计岗按新句重出 TTS 预算与 D15 dur_sec）。
  · **对白行一条都不新增**（D09 对陆沉写死每集 ≤4 句）；「垃圾时间」靠画面里的字解决。
  · **43–45s 片尾行原样保留**（用户 2026-10-23 裁决：片头四行移至片尾，不是缺陷；它不在 visual_facts 内属设计如此）。
  · **首句入画时码 0.5s 不动**（黄金 3 秒硬线）。
  · 角标行（AI 生成）与「换我用了。」行不动。
  · 不碰 D08／D09／D11／D12／D15。

写盘纪律
--------
  · **Q64 版本守卫**：期望基线 v1.30；不符即中止（`--force` 逃生口）。
  · **写前并发守卫**：D16 的 version／size／sha256／mtime 四锚复核；**D09／D08 各加一道 sha 双读**（防上游边改边取）。
  · 备份先行（reports/_bak_D16_U01_ep002_a_<ts>/），**os.replace 原子替换**。
  · **写后回读校验**：逐条断言终态（行数／seq／时码／类型／锚点命中／对白行数／片尾行／首句时码）＋ D09 复核。
  · 幂等：终态已达成则 `[IDEMPOTENT]` exit 0，不写盘、不动版本。

用法：python3 scripts/patch_D16_U01_ep002_a_batch_mavis.py [--dry-run] [--force]
"""
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = "/Users/ezreal/projects/小说创作/短剧文档工厂/02_项目/双相潮主"
D16P = os.path.join(ROOT, "units/U01/D16.json")
D11P = os.path.join(ROOT, "units/U01/D11.json")
D09P = os.path.join(ROOT, "units/U01/D09.json")
D08P = os.path.join(ROOT, "units/U01/D08.json")
EXPECT_VERSION = "v1.30"
NEXT_VERSION = "v1.31"

# 画面文字行终态：(seq, in_sec, out_sec, type, 新文, anchor)
#   anchor 必须逐字 ∈ 该镜 D11 visual_facts（对白行的 anchor 取 D09 原文，另行校验）
VISUAL_ROWS = [
    (3,  2.0, 5.8,  "字幕", "钢钎顶起一人宽门缝", "卷帘门底槽被实心重钢钎顶起一人宽缝隙", 1),
    (4,  6.0, 9.8,  "字幕", "两桶净水", "陆沉提着两桶净水敏捷侧身滑入厂房内部", 1),
    (5,  10.0, 12.8, "字幕", "水桶按在门后墙根码齐", "反手将水桶按在门后墙根码齐", 1),
    (6,  13.0, 16.8, "字幕", "工具箱扣实封好", "半箱压缩饼干与工具箱扣实封好", 2),
    (9,  28.0, 31.4, "字幕", "归废处置线外圈", "归废处置线外圈", 3),
    (10, 31.6, 33.8, "字幕", "侧门内侧焊起简易闸门", "侧门内侧焊起简易闸门", 2),
    (12, 37.0, 39.8, "字幕", "排渣闸口与管廊暗扣停步记下", "他在排渣闸口与管廊暗扣停步丈量记下", 3),
]
# 不改文字、但要登记锚点的行
KEEP_ROWS = [
    (1,  0.0, 45.0, "角标", "AI 生成", "右下角常驻白色角标：AI 生成。", None),
    (8,  22.0, 25.6, "字幕", "压缩饼干：半箱", "半箱压缩饼干与工具箱扣实封好", 2),
    (13, 40.0, 41.2, "字幕", "全城钟楼敲响十一下。", "同屏中文字幕「全城钟楼敲响十一下。」", 4),
]
# 对白行：seq → (D09 idx, 旧稿文字, 时码, shot_id)
DLG_ROWS = [
    (2,  1, "门我撬了。", 0.5, 1.8, 1),
    (7,  2, "侧门焊死，谁都进不来。", 19.0, 21.9, 2),
    (11, 3, "这条路先记下。", 35.0, 36.8, 3),
    (14, 4, "换我用了。", 41.2, 43.0, 4),
]
# 画面文字行旧稿 → 新稿（白名单外的任何变更即中止）
VISUAL_ALLOWED = {
    "撬开的门缝：仅容一人侧身": "钢钎顶起一人宽门缝",
    "厂区空地：锈钢材 · 成卷缆线": "两桶净水",
    "井口绞盘：两桶水": "水桶按在门后墙根码齐",
    "工具箱清单：扳手 · 半卷胶布": "工具箱扣实封好",
    "归废处置线 · 外圈": "归废处置线外圈",
    "简易闸门 · 焊成": "侧门内侧焊起简易闸门",
    "管廊、闸口：已记": "排渣闸口与管廊暗扣停步记下",
}

ROW_NOTE_OLD = ("【台词改稿待重定时 · 2026-10-23 12:3x · 分镜导演岗】台本编剧重写 D09 U01 ep2 台词，"
                 "本行字幕**文字**与 D09 现值脱节；本行时码凭证（out_sec ＝ 配音 at_sec＋dur_sec）仍成立，"
                 "但新台词无实测音频 ⇒ 按本厂口径不据此调预算 ⇒ 待声音设计岗重出本句 TTS 预算与 D15 dur_sec、"
                 "且台本编剧岗确认新稿定稿后，由本岗同步本行文字与 out_sec。")
ROW_NOTE_NEW = ("【台词改稿 · 2026-10-23 12:5x · 分镜导演岗 · A 批文字已同步】台本编剧重写 D09 U01 ep2 台词"
                "（对白真源现值 D09 U01 v1.8，与 D08 U01 v1.16 逐字互证），本行字幕**文字**已于 A 批同步为真源现值；"
                "本行时码凭证（out_sec ＝ 配音 at_sec＋dur_sec）仍成立，但新句尚无实测音频 ⇒ 按本厂口径不据此调预算 ⇒ "
                "待声音设计岗按新句重出 TTS 预算与 D15 dur_sec 后，由本岗在 B 批同步本行 out_sec。")

PENDING_OLD_TMPL = ("⚠️ 台词改稿待重定时：台本编剧 2026-10-23 重写 D09 U01 ep2 台词，本行字幕文字与 D09 现值脱节；"
                     "锚点已在 D15 v1.13（at {at}／dur {dur}）且时码逐条相等，"
                     "待声音设计岗按新句重出 TTS 预算与 dur_sec、且台本编剧岗确认新稿定稿后，由本岗同步本行文字与 out_sec")
PENDING_NEW_TMPL = ("⚠️ 台词改稿待重定时（B 批）：台本编剧 2026-10-23 重写 D09 U01 ep2 台词，"
                    "**本行字幕文字已于 2026-10-23 12:5x A 批同步为对白真源现值**（D09 U01 v1.8，与 D08 U01 v1.16 逐字互证）；"
                    "锚点仍在 D15 v1.13（at {at}／dur {dur}）且时码逐条相等，但新句尚无实测音频 ⇒ "
                    "待声音设计岗按新句重出 TTS 预算与 dur_sec 后，由本岗在 B 批同步本行 out_sec")

G3S_NOTE_APPEND = ("｜【A 批 · 2026-10-23 12:5x · 分镜导演岗】本集 `subtitle_style.lines[]` 内 3 条对白字幕行的**文字**"
                   "已同批同步为对白真源现值（D09 U01 v1.8，与 D08 U01 v1.16 逐字互证）；"
                   "其 out_sec／dur 仍为旧稿预算，待 B 批按声音设计岗新 dur 同步（本次一个字码未动）。")


def fail(msg):
    print("❌ %s" % msg)
    sys.exit(2)


def read(p):
    b = open(p, "rb").read()
    return b, hashlib.sha256(b).hexdigest(), len(b), os.path.getmtime(p)


def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    raw, sha, size, mtime = read(D16P)
    d16 = json.loads(raw.decode("utf-8"))
    d11 = json.load(open(D11P, encoding="utf-8"))
    d09_raw, d09_sha, _, _ = read(D09P)
    d09 = json.loads(d09_raw.decode("utf-8"))
    d08_raw, d08_sha, _, _ = read(D08P)
    d08 = json.loads(d08_raw.decode("utf-8"))

    if d16.get("version") not in (EXPECT_VERSION, NEXT_VERSION) and not force:
        fail("版本守卫触发：现盘 %s ∉ 期望基线 {%s, %s}（请复核后重跑，或用 --force 逃生口）"
             % (d16.get("version"), EXPECT_VERSION, NEXT_VERSION))

    # ---------- 对白真源：运行时取 D09，并与 D08 逐字互证 ----------
    d09_ep2 = {l["idx"]: l["text"].strip("「」") for l in d09["lines"] if l.get("ep") == 2}
    d08_ep2 = [b["text"].strip("「」") for b in
               next(e for e in d08["episodes"] if e.get("ep") == 2)["body"]
               if b.get("type") == "dialogue"]
    if len(d09_ep2) != 4 or len(d08_ep2) != 4:
        fail("对白真源条数异常：D09 %d 条 / D08 %d 条（预期各 4 条）" % (len(d09_ep2), len(d08_ep2)))
    for i in (1, 2, 3, 4):
        if d09_ep2[i] != d08_ep2[i - 1]:
            fail("D09 与 D08 的 ep2 #%d 不一致，拒绝猜测：D09=%r D08=%r" % (i, d09_ep2[i], d08_ep2[i - 1]))
    print("🔗 对白真源互证通过：D09 U01 v%s ＋ D08 U01 v%s 逐字一致（4/4）"
          % (d09.get("version"), d08.get("version")))

    ep = next((e for e in d16["episodes"] if e.get("ep") == 2), None)
    if ep is None:
        fail("D16 U01 里找不到 ep002")
    ss = ep["subtitle_style"]
    lines = ss["lines"]
    if len(lines) != 15:
        fail("行数 %d ≠ 15（预期 15 行）" % len(lines))

    e11 = next(e for e in d11["episodes"] if e.get("ep") == 2)
    shots = {int(s["shot_id"]): s for s in e11["shots"]}

    byseq = {l.get("seq"): l for l in lines}

    # ---------- 构造终态表 ----------
    final = []   # (seq, in, out, type, text, anchor, kind)
    for (seq, i0, o0, typ, newtext, anchor, sid) in VISUAL_ROWS:
        final.append((seq, i0, o0, typ, newtext, anchor, "vf"))
    for (seq, i0, o0, typ, newtext, anchor, sid) in KEEP_ROWS:
        final.append((seq, i0, o0, typ, newtext, anchor, "vf"))
    for (seq, idx, old, i0, o0, sid) in DLG_ROWS:
        final.append((seq, i0, o0, "对白", d09_ep2[idx], d09_ep2[idx], "d09"))
    final.sort(key=lambda x: x[0])

    # ---------- 逐行核对（不变量） ----------
    changes = []
    for (seq, i0, o0, typ, newtext, anchor, kind) in final:
        cur = byseq.get(seq)
        if cur is None:
            fail("现盘缺 seq %d" % seq)
        if float(cur.get("in_sec")) != i0 or float(cur.get("out_sec")) != o0:
            fail("seq %d 时码不符：终态 %s~%s vs 现盘 %s~%s" % (seq, i0, o0, cur.get("in_sec"), cur.get("out_sec")))
        if cur.get("type") != typ:
            fail("seq %d 类型不符：终态 %s vs 现盘 %s" % (seq, typ, cur.get("type")))
        old = cur.get("text")
        if old != newtext:
            if typ == "对白":
                if old != dict((s, o) for s, _, o, _, _, _ in DLG_ROWS).get(seq):
                    fail("seq %d 对白行旧文非预期：%r" % (seq, old))
            elif VISUAL_ALLOWED.get(old) != newtext:
                fail("seq %d 出现白名单外的文字变更：%r → %r" % (seq, old, newtext))
            changes.append((seq, typ, old, newtext))
        # 锚点硬校验
        if kind == "vf":
            sid = cur.get("shot_id")
            if sid is None:
                if not any(anchor in str(s.get("visual_facts") or "") for s in shots.values()):
                    fail("seq %d 的常驻层锚点未在任何一镜的 visual_facts 内命中：%r" % (seq, anchor))
            else:
                vf = str(shots[int(sid)].get("visual_facts") or "")
                if anchor not in vf:
                    fail("seq %d 锚点未逐字命中 shot%s 的 visual_facts：%r" % (seq, sid, anchor))
        elif kind == "d09":
            idx = dict((s, i) for s, i, _, _, _, _ in DLG_ROWS)[seq]
            if anchor != d09_ep2[idx]:
                fail("seq %d 对白锚点不等于 D09 ep2 #%d 现值" % (seq, idx))

    # 画面文字行 shot_id 与锚点镜必须一致
    for (seq, i0, o0, typ, newtext, anchor, sid) in VISUAL_ROWS + KEEP_ROWS:
        if sid is not None and int(byseq[seq].get("shot_id") or -1) != sid:
            fail("seq %d 的 shot_id 与锚点镜不符：现盘 %s vs 终态 %s"
                 % (seq, byseq[seq].get("shot_id"), sid))

    # ---------- 不变量 ----------
    n_dlg = sum(1 for l in lines if l.get("type") == "对白")
    if n_dlg != 4:
        fail("对白行数 %d ≠ 4（一条都不许增删）" % n_dlg)
    if float(byseq[2].get("in_sec")) != 0.5:
        fail("首句入画时码 %s ≠ 0.5（黄金 3 秒硬线）" % byseq[2].get("in_sec"))
    tail = [l for l in lines if l.get("type") == "片尾"]
    if len(tail) != 1 or float(tail[0]["in_sec"]) != 43.0 or float(tail[0]["out_sec"]) != 45.0:
        fail("片尾行不是 43~45s 唯一一行（红线）")
    if tail[0].get("text") != "节目编号：〔待平台给出〕　编剧：〔待定〕　导演：〔待定〕　《双相潮主〕　本片由人工智能生成" \
            and "节目编号：〔待平台给出〕" not in (tail[0].get("text") or ""):
        fail("片尾行内容异常（红线）")
    badge = [l for l in lines if l.get("type") == "角标"]
    if len(badge) != 1 or badge[0].get("text") != "AI 生成":
        fail("角标行异常")

    # ---------- 只报告不阻断：上游落后情况 ----------
    d11_dlg = {int(s["shot_id"]): str(s.get("dialogue") or "") for s in e11["shots"]}
    lag = []
    for (seq, idx, old, i0, o0, sid) in DLG_ROWS:
        cur_d11 = d11_dlg.get(sid, "")
        if d09_ep2[idx] not in cur_d11:
            lag.append("  seq%d：shot%s 的 D11 dialogue＝%r，与 D09 ep2 #%d＝%r 不一致（D11 v%s，%s 落盘）"
                       % (seq, sid, cur_d11, idx, d09_ep2[idx], d11.get("version"),
                          time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(D11P)))))
    if lag:
        print("⚠️ 上游落后（只报告、派单红线禁止本批碰 D11/D12/D15）：")
        for l in lag:
            print(l)

    # ---------- 幂等判定 ----------
    if all(byseq[s].get("text") == t and byseq[s].get("anchor") == a
           for (s, _, _, _, t, a, _) in final) and d16.get("version") == NEXT_VERSION:
        print("[IDEMPOTENT] D16 U01 已是 %s 且 ep002 A 批终态达成（文字 ＋ anchor 全部就位）；未改动 D16。" % NEXT_VERSION)
        return 0

    # ---------- 写前并发守卫 ----------
    cur_raw, cur_sha, cur_size, cur_mtime = read(D16P)
    if (cur_size != size or cur_mtime != mtime or cur_sha != sha):
        print("[ABORT] D16 并发改动守卫触发（size/mtime/sha256 不一致）；不写盘，请重跑。")
        return 3
    if hashlib.sha256(read(D09P)[0]).hexdigest() != d09_sha:
        print("[ABORT] D09 在本轮读取期间被改（上游边改边取）；不写盘，请重跑。")
        return 3

    # ---------- 应用 ----------
    oldtexts = {seq: byseq[seq].get("text") for (seq, _, _, _, _, _, _) in final}
    for (seq, i0, o0, typ, newtext, anchor, kind) in final:
        byseq[seq]["text"] = newtext
        byseq[seq]["anchor"] = anchor

    audit = ss["subtitle_sync_audit"]
    n_rows = 0
    for r in audit.get("rows", []):
        seq = r.get("seq")
        f = next((x for x in final if x[0] == seq and x[3] == "对白"), None)
        if not f:
            continue
        if r.get("text") != f[4]:
            r["text"] = f[4]
            n_rows += 1
        if ROW_NOTE_OLD in (r.get("note") or ""):
            r["note"] = r["note"].replace(ROW_NOTE_OLD, ROW_NOTE_NEW)
    if n_rows != 3:
        fail("审计块 rows[] 对白行文本同步条数 %d ≠ 3" % n_rows)

    n_pend = 0
    for p in audit.get("pending_d15_sync", []):
        # 按（shot_id, row_in_sec, row_out_sec）三锚对位到活对白行（pending 里的 text 是旧稿，不能拿它当匹配键）
        f = next((x for x in final if x[3] == "对白"
                  and int(byseq[x[0]].get("shot_id") or -1) == int(p.get("shot_id") or -2)
                  and float(x[1]) == float(p.get("row_in_sec"))
                  and float(x[2]) == float(p.get("row_out_sec"))), None)
        if not f:
            fail("pending_d15_sync 有一条对不上活对白行（shot_id=%s in=%s out=%s）"
                 % (p.get("shot_id"), p.get("row_in_sec"), p.get("row_out_sec")))
        anc = p.get("d15_current_anchor") or {}
        old_act = PENDING_OLD_TMPL.format(at=anc.get("at_sec"), dur=anc.get("dur_sec"))
        if p.get("action") != old_act:
            fail("pending_d15_sync 的 action 与预期模板不符（拒绝盲改）：%r" % p.get("action"))
        idx = dict((s, i) for s, i, _, _, _, _ in DLG_ROWS)[f[0]]
        p["text"] = f[4]
        p["action"] = PENDING_NEW_TMPL.format(n=idx, at=anc.get("at_sec"), dur=anc.get("dur_sec"))
        n_pend += 1
    if n_pend != 3:
        fail("pending_d15_sync 同步条数 %d ≠ 3" % n_pend)

    g = ss.get("golden3s_first_line") or {}
    if g.get("text") != "「%s」" % d09_ep2[1]:
        g["text"] = "「%s」" % d09_ep2[1]
    if "A 批 · 2026-10-23 12:5x" not in (g.get("note") or ""):
        g["note"] = (g.get("note") or "") + G3S_NOTE_APPEND
    ss["golden3s_first_line"] = g

    audit.setdefault("sync_records", []).append({
        "date": "2026-10-23",
        "event": "D16 U01 ep002 A 批 · 对白字幕行文字同步 ＋ 画面文字行锚点修复 ＋ 锚点入 JSON（Q114 首选）",
        "basis": ("企划合规 12:43 / 12:52 派单《D16 U01 ep002 字幕行同步与锚点修复》A 批（总控/验收裁决人）；"
                  "台本编剧 12:47 重写 D09 U01（v1.8）、12:51 重写 D08 U01（v1.16，body 13 条，word_count base=232），"
                  "D11 v1.17（12:39）／D12 v1.10（12:37）／D15 v1.13（12:16）均落后，"
                  "D16 ep002 只同步了一半 ⇒ 现盘自相矛盾。"),
        "interval_rule": "Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠。A 批不动任何时码。",
        "rows": [{"ep": 2, "seq": s, "old_text": o, "new_text": d09_ep2[i]}
                 for (s, i, o, _, _, _) in DLG_ROWS],
        "anchor_note": ("本批新增 D16 JSON 结构化字段 `anchor`（Q114 首选：锚点写进 JSON，不再只活在外部清单）；"
                        "画面文字行 anchor 逐字 ∈ 该镜 D11 visual_facts，对白行 anchor ＝ D09 U01 ep2 原文，"
                        "均由脚本写前硬校验。"),
        "batch_scope": ("A 批＝只同步文字与锚点，**零时码改动**；B 批（依赖声音设计岗新 dur_sec）再同步 4 条对白行的 out_sec，"
                        "并保证 43–45s 片尾行不被挤掉。"),
        "truth_source": ("对白真源＝D09 U01 v%s，与 D08 U01 v%s **逐字互证 4/4**（派单所给文本为 12:33/12:34 那一版，"
                         "已过期，故不采信转述）。" % (d09.get("version"), d08.get("version"))),
    })
    d16["version"] = NEXT_VERSION

    out = json.dumps(d16, ensure_ascii=False, indent=2) + "\n"

    print("📝 逐条对照表（ep002，A 批；括号内＝锚点出处）")
    for (seq, i0, o0, typ, newtext, anchor, kind) in final:
        cur = byseq[seq]
        oldtxt = oldtexts.get(seq)
        mark = "改" if oldtxt != newtext else "留"
        src = ("D09 ep2 #%d" % dict((s, i) for s, i, _, _, _, _ in DLG_ROWS)[seq]) if typ == "对白" \
            else ("D11 shot%s visual_facts" % cur.get("shot_id"))
        print("  [%s] seq%-3d %-4s %5.1f~%-4.1f %r → %r" % (mark, seq, typ, i0, o0, oldtxt, newtext))
        print("        锚点：%s（%s）" % (anchor[:60], src))
    print("  ＋ 每行新增 anchor 字段（Q114 首选）｜rows[].text 同步 %d 条｜pending_d15_sync 同步 %d 条"
          % (n_rows, n_pend))
    print("  ⚠️ 对白行新字数：%s（max_chars_per_line=15 口径下将换行显示；校验器不检查该字段）"
          % "/".join(str(len(d09_ep2[i])) for (_, i, _, _, _, _) in DLG_ROWS))

    if dry:
        print("（--dry-run：未写盘）")
        return 0

    bak_dir = os.path.join(ROOT, "reports", "_bak_D16_U01_ep002_a_%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    shutil.copy2(D16P, os.path.join(bak_dir, "D16.json"))

    tmp = D16P + ".tmp_a"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, D16P)

    # ---------- 写后回读校验 ----------
    back = json.load(open(D16P, encoding="utf-8"))
    bep = next(e for e in back["episodes"] if e.get("ep") == 2)
    bl = {l.get("seq"): l for l in bep["subtitle_style"]["lines"]}
    errs = []
    if len(bl) != 15:
        errs.append("行数 %d ≠ 15" % len(bl))
    for (seq, i0, o0, typ, newtext, anchor, kind) in final:
        l = bl.get(seq, {})
        if l.get("text") != newtext:
            errs.append("seq %s text 不符" % seq)
        if l.get("anchor") != anchor:
            errs.append("seq %s anchor 不符" % seq)
        if float(l.get("in_sec")) != i0 or float(l.get("out_sec")) != o0:
            errs.append("seq %s 时码被改动" % seq)
    if back.get("version") != NEXT_VERSION:
        errs.append("version 未升到 %s" % NEXT_VERSION)
    if hashlib.sha256(read(D09P)[0]).hexdigest() != d09_sha:
        errs.append("D09 在落盘期间被改（真源漂移）")
    if errs:
        shutil.copy2(os.path.join(bak_dir, "D16.json"), D16P)
        print("[ROLLBACK] 写后校验失败，已回滚：%s" % errs)
        return 4

    print("✅ 已落盘 D16 U01 %s → %s｜%d B（%+d）｜备份 %s"
          % (EXPECT_VERSION, NEXT_VERSION, os.path.getsize(D16P), os.path.getsize(D16P) - size,
             os.path.relpath(bak_dir, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
