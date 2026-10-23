#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_script.py —— D08 分集剧本 → **人能读的剧本**

格式基准：short-drama skill（https://github.com/0xsline/short-drama）的**国内剧本格式**
—— 2026-10-23 用户指派「学习这个 skill 并据其描述改写」，本脚本按该 skill 的
`/episode {N}` 单集剧本格式重排产线剧本。

    # 第{N}集：{集标题}
    > 本集关键词 / 本集爽点 / 钩子类型 / 前情提要
    ## 场次一
    **场景：** 内景/外景 · {地点} · 日/夜　**出场人物：**
    △ （全景/中景/近景/特写）{画面}
    **{角色名}**（{语气}）："{台词}"
    【屏幕文字】{画面内文字}
    ♪ 配乐提示：{音乐}
    ...
    > 🎣 本集钩子：{悬念描述}
    > 📺 下集预告：{下一集核心看点，1句}

为什么这么排
------------
`render-md.mjs` 渲出来的 D08 是**产线表格**（类型/角色/内容/情绪/音效/镜头意图/合规增量），
给机器和岗位看，不是剧本。给用户看的必须是能读、能直接拍的剧本。
本脚本同时把 skill 的方法论维度接进产线：
  · **钩子类型**（5 类）—— 取自 D06 `hook_type`（由 `scripts/plan_hook_types.py` 按
    skill 的 `hook-design.md` 配比规则规划）
  · **前情提要** —— 取自 D07 `carry_over`
  · **配乐提示** —— 取自 D15 `bgm_curve`（段名/情绪/动机/配器）
  · **场次** —— 我们的「四段制 4 镜」即 skill 的 4 个场次（段＝场，镜＝场次内的一次拍摄）

数据来源
--------
· `units/<UNIT>/D06.json` —— 钩子类型、hook_out、beats、emotion_goal
· `units/<UNIT>/D07.json` —— carry_over（前情提要）、story_time、scenes、在场角色
· `units/<UNIT>/D08.json` —— 动作行 / 台词 / 字幕板 / 情绪
· `units/<UNIT>/D09.json` —— 台词语气（tone）与潜台词（subtext）
· `units/<UNIT>/D11.json` —— 镜位（景别/机位/运镜/画面事实/该镜台词）
· `units/<UNIT>/D15.json` —— bgm_curve（配乐提示）
· `units/<UNIT>/D16.json` —— 画面内文字（字幕/面板文字）按镜归属

输出
----
`preview/<UNIT>_script/EP001..EP0NN.md`（每集一份）＋ `script_<UNIT>.md`（合订本）

用法
----
python3 scripts/render_script.py --unit U01
"""
import argparse
import json
import os
import re

CHAR_NAME = {
    "LC": "陆沉", "YHY": "叶红衣", "SQC": "苏清辞",
    "YJ-ES": "叶承钧", "YJ-JZ": "叶崇岳", "YD-GC": "商既衡",
    "WM-SZ": "闻照白", "SQC-XX": "苏清辞",
}

# skill 的爽感矩阵 8 类 → 本剧（末世悬疑·男频）实际用得上的映射
SATISFACTION = {
    "爽点": "燃", "转折": "悬疑", "铺垫": "信息", "伏笔": "悬疑", "回收": "逆袭",
}


def cname(cid):
    """角色 id → 中文名。D07 的 present_characters 是对象数组（{char_id, role, minor}），
    D08 的是字符串数组 —— 两种都收。"""
    if isinstance(cid, dict):
        cid = cid.get("char_id") or cid.get("id") or ""
    if not cid:
        return ""
    if cid in CHAR_NAME:
        return CHAR_NAME[cid]
    m = re.match(r"^([A-Z]{2,3})-", cid)
    if m and m.group(1) in CHAR_NAME:
        return CHAR_NAME[m.group(1)]
    return cid


def cnames(chars):
    """角色列表 → 中文名串（去重、保序）。"""
    out = []
    for c in chars or []:
        n = cname(c)
        if n and n not in out:
            out.append(n)
    return "、".join(out) or "—"


def strip_quotes(t):
    return re.sub(r"^[「『\"“]|[」』\"”]$", "", str(t or "")).strip()


def night_or_day(story_time):
    """从 story_time 推「日/夜」。6 点到 18 点算日，其余算夜。"""
    m = re.search(r"(\d{1,2}):(\d{2})", str(story_time or ""))
    if not m:
        return "夜"
    h = int(m.group(1))
    return "日" if 6 <= h < 18 else "夜"


def parse_scene_heading(scene_heading, scenes, shot_scene_code):
    """推每镜的场景头：内/外 · 地点 · 日/夜。

    D08 的 scene_heading 形如「外 · 废弃军工机械厂 → 外 · 归废处置线外圈 · 灾变前夜 21:04-21:47」，
    按 → 切成段；段序与 D07 `scenes[]` 对齐；D11 镜的 `scene_code` 指到 D07 的 scene.code。
    """
    segs = [s.strip() for s in re.split(r"→", str(scene_heading or "")) if s.strip()]
    parsed = []
    for s in segs:
        parts = [p.strip() for p in s.split("·") if p.strip()]
        io = parts[0] if parts and parts[0] in ("内", "外", "内外") else ""
        loc = ""
        for p in parts[1:]:
            if re.search(r"\d{1,2}:\d{2}", p) or p.startswith("灾变") or p.startswith("次日"):
                continue
            loc = p
            break
        parsed.append({"io": io, "loc": loc})
    out = {}
    for i, sc in enumerate(scenes or []):
        code = sc.get("code")
        p = parsed[i] if i < len(parsed) else {}
        out[code] = {"io": p.get("io") or "外",
                     "loc": p.get("loc") or sc.get("location", "")}
    return out


def split_facts(vf):
    """把 D11 的 visual_facts 拆成可读的短句（去掉角标合规句）。"""
    t = str(vf or "").replace("右下角常驻白色角标：AI 生成。", "")
    t = re.sub(r"\s+", "", t)
    out = []
    for seg in re.split(r"[；。]", t):
        for c in re.split(r"[，,]", seg):
            c = c.strip("。、 ")
            if len(c) >= 4:
                out.append(c)
    return out


def parse_shot_dialogue(d):
    """D11 shot.dialogue 形如「陆沉「门我撬了。」」，多句时用「／」分隔；
    可能是 str 或 list。"""
    items = d if isinstance(d, list) else ([d] if d else [])
    res = []
    for it in items:
        for piece in re.split(r"／", str(it or "")):
            piece = piece.strip()
            if not piece:
                continue
            m = re.match(r"^(.+?)[「『](.+?)[」』]\s*$", piece)
            if m:
                res.append((m.group(1).strip(), m.group(2).strip()))
            else:
                res.append(("", piece))
    return res


def short_kw(text, limit=14):
    """从一句长句里取一个可读的短关键词：优先取第一个分句，超长则按标点切。"""
    t = strip_quotes(str(text or "")).strip()
    if not t:
        return ""
    if len(t) <= limit:
        return t
    for sep in ("：", "，", "、", "；", "。", " "):
        if sep in t:
            head = t.split(sep)[0].strip()
            if 4 <= len(head) <= limit:
                return head
    return t[:limit] + "…"


def build(unit, proj):
    def ld(name):
        p = os.path.join(proj, "units", unit, f"{name}.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    d6, d7, d8, d9, d11, d15, d16 = (ld(n) for n in
                                     ("D06", "D07", "D08", "D09", "D11", "D15", "D16"))

    tone = {}
    for ln in d9.get("lines", []):
        tone[(ln.get("ep"), strip_quotes(ln.get("text")))] = {
            "tone": ln.get("tone", ""), "subtext": ln.get("subtext", "")}

    m6 = {e["ep"]: e for e in d6.get("episodes", [])}
    m7 = {e["ep"]: e for e in d7.get("episodes", [])}
    m11 = {e["ep"]: e for e in d11.get("episodes", [])}
    m15 = {e["ep"]: e for e in d15.get("episodes", [])}
    m16 = {e["ep"]: e for e in d16.get("episodes", [])}
    eps_meta = {e["ep"]: e for e in d8.get("episodes", [])}
    max_ep = max(eps_meta) if eps_meta else 0

    eps = []
    for ep in sorted(eps_meta):
        e8 = eps_meta[ep]
        e6 = m6.get(ep, {})
        e7 = m7.get(ep, {})
        shot_list = sorted(m11.get(ep, {}).get("shots", []), key=lambda s: s.get("shot_id", 0))

        # 该集所有台词（按 D08 body 顺序），建立 文本 → (emotion, tone, subtext)
        dlg = {}
        for b in e8.get("body", []):
            if b.get("type") != "dialogue":
                continue
            key = strip_quotes(b.get("text"))
            meta = tone.get((ep, key), {})
            dlg[key] = {"char": cname(b.get("char_id")),
                        "emotion": b.get("emotion", ""),
                        "tone": meta.get("tone", ""),
                        "subtext": meta.get("subtext", "")}

        # 画面内文字（D16 按镜归属）
        words = {}
        for l in m16.get(ep, {}).get("subtitle_style", {}).get("lines", []):
            if l.get("type") in ("对白", "角标", "片头", "片尾"):
                continue
            words.setdefault(l.get("shot_id"), []).append((l.get("text", ""), l.get("in_sec")))

        # 配乐（D15 bgm_curve 按时间落段）
        bgm = m15.get(ep, {}).get("bgm_curve", [])

        scmap = parse_scene_heading(e8.get("scene_heading"), e7.get("scenes", []),
                                    shot_list[0].get("scene_code") if shot_list else None)
        daynight = night_or_day(e7.get("story_time"))

        out = [f"# 第 {ep} 集　{e8.get('title', '')}", ""]

        # ── 顶部元信息（skill 格式）────────────────────────────────────
        emo = e7.get("emotion_goal") or e6.get("emotion_goal") or ""
        beats = e6.get("beats") or []
        sat = "、".join(sorted({SATISFACTION.get(x, x) for x in beats})) or "信息"
        kws = [emo.replace("·", "・") if emo else "信息"]
        mh = e7.get("must_happen") or []
        if mh:
            kw2 = short_kw(mh[0])
            if kw2 and kw2 not in kws:
                kws.append(kw2)
        if e6.get("hook_type"):
            kws.append(f"{e6['hook_type']}钩")
        out.append(f"> **本集关键词：** {' / '.join(kws)}")
        out.append(f"> **本集爽点：** {sat}　　**钩子类型：** {e6.get('hook_type') or '（未标注）'}")
        if e7.get("carry_over"):
            out.append(f"> **前情提要：** {e7['carry_over']}")
        out.append("")
        out.append(f"**时长** {e8.get('duration_sec')} 秒　|　**场次** {e8.get('scene_heading','')}　|　"
                   f"**在场** {cnames(e7.get('present_characters') or e8.get('present_characters', []))}")
        out.append("")

        # ── 场次（段＝场，镜＝场次内的一次拍摄）────────────────────────
        t = 0.0
        for si, s in enumerate(shot_list, start=1):
            dur = float(s.get("duration_sec", 0))
            t0, t1 = t, t + dur
            t = t1
            sc = scmap.get(s.get("scene_code"), {})
            io = sc.get("io") or "外"
            loc = sc.get("loc") or (e7.get("scenes") or [{}])[0].get("location", "")
            out.append("---")
            out.append("")
            out.append(f"## 场次{['一','二','三','四','五','六','七','八'][si-1] if si <= 8 else si}")
            out.append("")
            out.append(f"**场景：** {io}景 · {loc} · {daynight}"
                       f"　**出场人物：** {cnames(e7.get('present_characters') or [])}"
                       f"　**镜 {s.get('shot_id')}**（{t0:g}–{t1:g}s｜{s.get('shot_size')}｜"
                       f"{s.get('camera_angle')}｜{s.get('movement')}）")
            out.append("")
            size = s.get("shot_size") or "中景"
            facts = split_facts(s.get("visual_facts"))
            for k, f in enumerate(facts):
                out.append(f"△ （{size}）{f}" if k == 0 else f"　　{f}")
            for who, line in parse_shot_dialogue(s.get("dialogue")):
                key = strip_quotes(line)
                meta = dlg.get(key, {})
                nm = who or meta.get("char") or ""
                emo_txt = meta.get("emotion") or meta.get("tone") or ""
                out.append("")
                out.append(f"**{nm}**" + (f"（{emo_txt}）" if emo_txt else "") + f"：「{line}」")
                if meta.get("subtext"):
                    out.append(f"　　（潜台词：{meta['subtext']}）")
            for txt, ts in words.get(s.get("shot_id"), []):
                out.append("")
                out.append(f"【屏幕文字】{txt}　（{ts}s）")
            seg = next((b for b in bgm if float(b.get("start_sec", -1)) < t1
                        and float(b.get("end_sec", 0)) > t0), None)
            if seg:
                out.append("")
                out.append(f"♪ 配乐提示：{seg.get('emotion','')}｜{seg.get('motif','')}｜"
                           f"{seg.get('arrangement','')}")
            out.append("")

        # ── 结尾钩子（skill 格式）─────────────────────────────────────
        out.append("---")
        out.append("")
        if e6.get("hook_out"):
            out.append(f"> 🎣 **本集钩子：** {e6['hook_out']}")
        if e6.get("hook_type_reason"):
            out.append(f"> 　　（钩型依据：{e6['hook_type_reason']}）")
        nxt = m6.get(ep + 1)
        if nxt:
            # 下集预告用**下集 logline**（本集 hook_out 与下集 hook_in 往往是同一句，
            # 直接引用会变成「本集钩子」复读）；无 logline 时退回下集 carry_over。
            prev = nxt.get("logline") or ""
            if not prev:
                nxt7 = m7.get(ep + 1) or {}
                prev = nxt7.get("carry_over") or nxt.get("hook_in") or ""
            if prev:
                out.append(f"> 📺 **下集预告：** 第 {ep+1} 集《{nxt.get('title','')}》——{prev}")
        out.append("")

        # ── 附录（产线信息，不进拍摄正文）──────────────────────────────
        if shot_list:
            out.append("---")
            out.append("")
            out.append("<details><summary>附：本集镜位表（产线用）</summary>")
            out.append("")
            out.append("| 镜 | 场景 | 景别 | 机位 | 运镜 | 时长 | 画面 |")
            out.append("|---|---|---|---|---|---|---|")
            for s in shot_list:
                out.append(f"| {s.get('shot_id')} | {s.get('scene_code')} | {s.get('shot_size')} | "
                           f"{s.get('camera_angle')} | {s.get('movement')} | {s.get('duration_sec')}s | "
                           f"{str(s.get('visual_facts',''))[:120]} |")
            out.append("")
            out.append("</details>")
        if e8.get("compliance_notes"):
            out.append("")
            out.append("<details><summary>附：合规备注（供过审用，正文不出现）</summary>")
            out.append("")
            for n in e8["compliance_notes"]:
                out.append(f"- {n}")
            out.append("")
            out.append("</details>")
        out.append("")
        eps.append((ep, "\n".join(out)))
    return eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default="U01")
    args = ap.parse_args()
    proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = args.unit
    out_dir = os.path.join(proj, "preview", f"{unit}_script")
    os.makedirs(out_dir, exist_ok=True)

    eps = build(unit, proj)
    book = [f"# 《双相潮主》{unit} 分集剧本（{eps[0][0]}–{eps[-1][0]}）", "",
            "> 格式基准：short-drama skill（国内剧本格式）｜每集 = 4 段制 4 镜 = 4 场次", ""]
    for ep, md in eps:
        fn = os.path.join(out_dir, f"EP{ep:03d}.md")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        book.append(md)
        book.append("\n---\n")
    bookp = os.path.join(out_dir, f"script_{unit}.md")
    with open(bookp, "w", encoding="utf-8") as f:
        f.write("\n".join(book))
    print(f"[DONE] {len(eps)} 集剧本（short-drama skill 格式）→ {out_dir}")
    for ep, md in eps:
        print(f"   EP{ep:03d}.md  {len(md)} B")


if __name__ == "__main__":
    main()
