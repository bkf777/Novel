#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""densify_subtitles.py —— 字幕密度填充（治「成片长时间没信息」）

问题（2026-10-23 用户反馈「还是很拖啊，白模视频有很长时间什么也没有」）：
  体检（scripts/audit_dead_time.py）实测 U01+U02 十六集：45 秒里平均 32.8 秒屏幕上没有任何
  字幕/读数，最长一段空白 14.0s。逐集看，规律一致——**信息只集中在三四个点上**：
  开头一句、镜2 中间一句、结尾一句，中间 10~14 秒完全静音。

判定为什么不能靠「加台词」解决：
  D09 语气卡对陆沉写死「对白密度：每集不超过 4 句」——寡言是角色设计，不是遗漏。
  把主角写成话痨会毁角色。
⇒ 正确工具是**画面里的字**（字幕板 / 面板读数 / 场景标识）：让镜头里本来就有的东西被读出来。

本脚本做什么：
  ① 把 D11 每镜 visual_facts 里**已经写明的事实**写成 D16 字幕行，填掉空窗；
  ② 把首句台词前移到 0.5s（黄金 3 秒），同步 D15 配音 at_sec；
  ③ 全程不动：镜数、镜时、白模（D14）、D08 正文、D09 潜台词、D12 提示词。
     ⇒ V11（D11↔D14 逐镜一致）不受影响，**不需要重跑 Blender**。

硬校验（任一不过即中止，不写盘）：
  · anchor 必须逐字出现在该集**该镜**的 D11 visual_facts 中 —— 不许编造画面；
  · 挂载区间必须落在该镜的**真实可见区间**内 —— D16 cuts 含段内并行交叉剪辑
    （ep002 的 31.5s 回切镜2），按 D11 镜时累加会挂错画面；
  · 不与任何已有字幕行时间重叠（左闭右开）；
  · 停留 ≥1.2s（D16 subtitle_style.min_dwell_sec）；
  · 单行 ≤15 字（D16 subtitle_style.max_chars_per_line）。

幂等：可重复执行；内容无变化则不写盘、不动版本号。
用法：python3 scripts/densify_subtitles.py [--unit U01] [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FILL_FILES = {
    "U01": "density_fills_U01.json",
    "U02": "density_fills_U02.json",
    "U03": "density_fills_U03.json",
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def fingerprint(p):
    """写前并发守卫用的指纹：version + mtime + sha16。

    D16/D15 是多人共写的共享真源（分镜导演、声音设计岗、Chief 都写）。
    读盘到写盘之间若被他人升版，直接写回＝静默覆盖对方的改动。
    ⇒ 写盘前重算指纹，与读盘时不一致即中止。
    """
    import hashlib
    b = open(p, "rb").read()
    o = json.loads(b.decode("utf-8"))
    return {
        "version": o.get("version"),
        "size": len(b),
        "sha16": hashlib.sha256(b).hexdigest()[:16],
        "mtime": os.path.getmtime(p),
    }


def bump(o):
    v = re.sub(r"^v+", "v", str(o.get("version", "v1.0")))
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def shot_visibility(cuts, shots):
    """按 D16 cuts 推导每镜的**真实可见区间** [(t0,t1,shot_id)]。

    cuts 里 from_shot/to_shot 描述切换；段内并行交叉剪辑会出现 to_shot 回切旧镜
    （ep002：13→镜2、28→镜3、31.5→镜2、34→镜3、40→镜4），
    所以可见区间是「一段里可能反复出现同一镜」，不能按 D11 镜时累加。
    """
    order = []
    t = 0.0
    if cuts:
        order.append((t, float(cuts[0]["at_sec"]), int(cuts[0]["from_shot"])))
        for c in cuts:
            order.append((float(c["at_sec"]), None, int(c["to_shot"])))
        out = []
        for i, (t0, _x, sid) in enumerate(order):
            t1 = order[i + 1][0] if i + 1 < len(order) else max(
                float(s["duration_sec"]) for s in shots) + t0
            out.append((t0, t1, sid))
        # 收尾修正：最后一段终点用 D11 镜时累加总长
        total = sum(float(s["duration_sec"]) for s in shots)
        out[-1] = (out[-1][0], total, out[-1][2])
        return out
    t = 0.0
    out = []
    for s in shots:
        out.append((t, t + float(s["duration_sec"]), int(s["shot_id"])))
        t += float(s["duration_sec"])
    return out


def overlaps(a0, a1, b0, b1):
    """左闭右开：out_sec == 下一条 in_sec 视为相接，不算重叠。"""
    return a0 < b1 and b0 < a1


def norm_text(t):
    """对白在 D09 带「」引号、D16 不带，比对前先归一。"""
    return str(t or "").replace("「", "").replace("」", "").strip()


def process(unit, dry=False):
    fill_file = FILL_FILES.get(unit)
    if not fill_file or not os.path.exists(os.path.join(SCRIPTS, fill_file)):
        print(f"⏭  {unit} 无填充清单，跳过")
        return
    spec = load(os.path.join(SCRIPTS, fill_file))["units"][unit]

    d11 = load(os.path.join(ROOT, "units", unit, "D11.json"))
    d16 = load(os.path.join(ROOT, "units", unit, "D16.json"))
    d15 = load(os.path.join(ROOT, "units", unit, "D15.json"))
    d09 = load(os.path.join(ROOT, "units", unit, "D09.json"))

    # 读盘时的基线指纹（写盘前复核用）
    fp0 = {
        "D16": fingerprint(os.path.join(ROOT, "units", unit, "D16.json")),
        "D15": fingerprint(os.path.join(ROOT, "units", unit, "D15.json")),
    }
    print(f"   基线：D16 v{fp0['D16']['version']} sha16={fp0['D16']['sha16']}｜"
          f"D15 v{fp0['D15']['version']} sha16={fp0['D15']['sha16']}")

    d11map = {e["ep"]: e for e in d11["episodes"]}
    d16map = {e["ep"]: e for e in d16["episodes"]}
    d15map = {e["ep"]: e for e in d15["episodes"]}
    d09map = {}
    for l in d09["lines"]:
        d09map[(l["ep"], l["idx"])] = l

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(ROOT, "reports", f"_bak_densify_{unit}_{stamp}")
    errors = []
    changed16 = False
    changed15 = False
    records = []

    for ep_s, plan in spec.items():
        ep = int(ep_s)
        e11 = d11map[ep]
        e16 = d16map[ep]
        e15 = d15map[ep]
        ss = e16["subtitle_style"]
        lines = ss["lines"]
        shots = sorted(e11["shots"], key=lambda s: s["shot_id"])
        vis = shot_visibility(e16.get("cuts") or [], shots)
        facts = {int(s["shot_id"]): str(s.get("visual_facts") or "") for s in shots}
        min_dwell = float(ss.get("min_dwell_sec", 1.2))
        max_chars = int(ss.get("max_chars_per_line", 15))

        # ── ① 首句前移（黄金 3 秒）────────────────────────────────────────
        for mv in plan.get("move_dialogue", []):
            m = re.match(r"D09 ep(\d+) #(\d+)$", mv["line_ref"])
            if not m:
                errors.append(f"ep{ep} line_ref 格式错：{mv['line_ref']}")
                continue
            if int(m.group(1)) != ep:
                errors.append(f"ep{ep} line_ref 集号不符：{mv['line_ref']}")
                continue
            idx = int(m.group(2))
            d09l = d09map.get((ep, idx))
            if not d09l:
                errors.append(f"ep{ep} D09 无第{idx}句")
                continue
            txt = d09l["text"]
            row = next((l for l in lines if l.get("type") == "对白"
                        and norm_text(l.get("text")) == norm_text(txt)), None)
            if row is None:
                errors.append(f"ep{ep} D16 无对白行「{txt}」")
                continue
            dur = round(float(row["out_sec"]) - float(row["in_sec"]), 2)
            cur_in = float(row["in_sec"])
            new_in = float(mv["to_sec"])
            # 幂等三态：
            #   ① 已在目标位（cur == to）⇒ 已应用过，跳过，**不算失败**
            #   ② 还在起点位（cur == from）⇒ 本次应用
            #   ③ 既不在起点也不在目标 ⇒ 前提过期（真冲突），中止
            if abs(cur_in - new_in) < 0.01:
                print(f"   ⏭  ep{ep} 首句「{txt}」已在 {new_in}s（已应用），跳过")
                for v in e15.get("voice_over", []):
                    if v.get("line_ref") == mv["line_ref"]:
                        if abs(float(v.get("at_sec", -1)) - new_in) > 0.01:
                            v["at_sec"] = new_in
                            changed15 = True
                continue
            if abs(cur_in - float(mv["from_sec"])) > 0.05:
                errors.append(f"ep{ep} 「{txt}」当前 in_sec={row['in_sec']}，"
                              f"既不在起点 {mv['from_sec']} 也不在目标 {mv['to_sec']}"
                              f"（前提过期，可能是别岗已改动）")
                continue
            new_out = round(new_in + dur, 2)
            if abs(new_in - float(row["in_sec"])) > 0.01:
                row["in_sec"], row["out_sec"] = new_in, new_out
                row["note"] = mv.get("note", "")
                changed16 = True
                records.append(f"ep{ep} 首句「{txt}」{mv['from_sec']}→{new_in}s（dur {dur}s 不变）")
            # D15 同步
            for v in e15.get("voice_over", []):
                if v.get("line_ref") == mv["line_ref"]:
                    if abs(float(v.get("at_sec", -1)) - new_in) > 0.01:
                        v["at_sec"] = new_in
                        changed15 = True
            # golden3s_first_line 状态推进
            g = ss.get("golden3s_first_line")
            if isinstance(g, dict) and g.get("status") == "待 D15 前移":
                g["status"] = "达标"
                g.pop("d15_pending", None)
                g.pop("current_d15_vo_at_sec", None)
                g["text"] = txt
                g["d15_vo_at_sec"] = new_in
                g["d15_vo_dur_sec"] = dur
                g["d15_line_ref"] = mv["line_ref"]
                g["note"] = ("本岗（Chief 补位）直接把 D15 首句配音 at_sec 前移至 "
                             f"{new_in}s、dur 不变，D16 对白行同步为 {new_in}~{new_out}s，"
                             "逐条相等。首句与第 0 帧画面同刻发生，不另加铺垫。")
                changed16 = True

        # ── ② 字幕行填充 ──────────────────────────────────────────────────
        for fl in plan.get("fills", []):
            txt = fl["text"]
            sid = int(fl["shot_id"])
            i0, o0 = float(fl["in_sec"]), float(fl["out_sec"])

            # 校验 1：锚点必须在该镜 visual_facts 里
            if fl["anchor"] not in facts.get(sid, ""):
                errors.append(f"ep{ep} 「{txt}」锚点「{fl['anchor']}」不在镜{sid} 的 "
                              f"D11 visual_facts 中 → 画面里没有这个东西，不许写")
                continue
            # 校验 2：区间必须落在该镜真实可见区间内
            ok_vis = any(a <= i0 and o0 <= b and s == sid for a, b, s in vis)
            if not ok_vis:
                errors.append(f"ep{ep} 「{txt}」区间 {i0}~{o0} 不在镜{sid} 的真实可见区间内"
                              f"（可见：{[ (a,b,s) for a,b,s in vis if s==sid ]}）")
                continue
            # 校验 3：停留时长
            if round(o0 - i0, 2) < min_dwell - 1e-9:
                errors.append(f"ep{ep} 「{txt}」停留 {round(o0-i0,2)}s < {min_dwell}s")
                continue
            # 校验 4：字数
            if len(txt) > max_chars:
                errors.append(f"ep{ep} 「{txt}」{len(txt)} 字 > {max_chars} 字上限")
                continue
            # 校验 5：与已有行重叠（角标是常驻元素，不占字幕带，排除）
            hit = next((l for l in lines if l.get("text") == txt), None)
            clash = next((l for l in lines if l.get("text") != txt
                          and l.get("type") != "角标"
                          and overlaps(i0, o0, float(l["in_sec"]), float(l["out_sec"]))), None)
            if clash:
                errors.append(f"ep{ep} 「{txt}」{i0}~{o0}s 与既有行「{clash.get('text')}」"
                              f"{clash['in_sec']}~{clash['out_sec']}s 重叠")
                continue
            if hit:
                if (abs(float(hit["in_sec"]) - i0) < 0.01
                        and abs(float(hit["out_sec"]) - o0) < 0.01
                        and hit.get("type") == "字幕"):
                    # Q114 首选路径：anchor 必须**结构化落进 D16 JSON**，
                    # 不能只藏在 note 正文里（否则产物不自解释、清单丢了就重建不出来）。
                    if fl.get("anchor") and hit.get("anchor") != fl["anchor"]:
                        hit["anchor"] = fl["anchor"]
                        changed16 = True
                        records.append(f"ep{ep} 字幕「{txt}」补写 anchor 字段「{fl['anchor']}」")
                    print(f"   ⏭  ep{ep} 「{txt}」已存在且一致，跳过")
                    continue
                hit["in_sec"], hit["out_sec"], hit["shot_id"] = i0, o0, sid
                hit["type"] = "字幕"
                hit["note"] = fl.get("note", "")
                if fl.get("anchor"):
                    hit["anchor"] = fl["anchor"]
                changed16 = True
                records.append(f"ep{ep} 字幕「{txt}」定位更新为 {i0}~{o0}s（挂镜{sid}）")
            else:
                lines.append({
                    "seq": 0, "type": "字幕", "text": txt,
                    "in_sec": i0, "out_sec": o0, "shot_id": sid,
                    "anchor": fl.get("anchor", ""),
                    "note": fl.get("note", ""),
                })
                changed16 = True
                records.append(f"ep{ep} 新增字幕「{txt}」{i0}~{o0}s（挂镜{sid}，"
                               f"锚点「{fl['anchor']}」）")

        # seq 重排
        lines.sort(key=lambda l: (float(l["in_sec"]), int(l.get("seq", 0) or 0)))
        for i, l in enumerate(lines, start=1):
            if l.get("seq") != i:
                l["seq"] = i
                changed16 = True

    if errors:
        print("❌ 校验未通过，不写盘：")
        for e in errors:
            print("   -", e)
        sys.exit(1)

    # ── 留痕 ─────────────────────────────────────────────────────────────
    if changed16:
        # 留痕按单元生成：不同单元的实测基线与执行者不同，不能共用一条文案。
        UNIT_BASIS = {
            "U01": ("体检实测 U01 16 集全集最长空窗 14.00s、平均空窗总 30.81s"
                    "（45s 里约 33s 屏幕无字幕）。"),
            "U02": ("体检实测 U02 16 集全集最长空窗 13.30s、平均空窗总 33.20s"
                    "（45s 里约 33s 屏幕无字幕）。"),
            "U03": ("体检实测 U03 8 集全集最长空窗 11.00s、平均空窗总 31.91s"
                    "（45s 里约 32s 屏幕无字幕）。"),
        }
        moved = any(plan.get("move_dialogue") for plan in spec.values())
        n_fill = sum(len(p.get("fills", [])) for p in spec.values())
        basis = UNIT_BASIS.get(unit, "")
        event = ("字幕密度填充 ＋ 首句前移（治成片空窗）" if moved
                 else "字幕密度填充（Q100 · 治成片空窗）")
        method = ("把 D11 每镜 visual_facts 已写明的事实写成 D16「字幕」类型行填掉空窗；"
                  + ("首句台词前移到 0.5s 同步 D15 配音。" if moved else
                     "本单元 D15 首句已落锚于 0.5s，无需再前移。"))
        for ep_s, plan in spec.items():
            e = d16map[int(ep_s)]
            e["subtitle_style"].setdefault("subtitle_sync_audit", {}).setdefault(
                "sync_records", []).append({
                "date": "2026-10-23",
                "event": event,
                "basis": ("用户反馈「还是很拖啊」；" + basis +
                          "D09 语气卡对陆沉写死「每集不超过 4 句」，故不加台词，"
                          "改用画面里的字。"),
                "method": method,
                "not_changed": ["镜数与镜时", "D14 白模与逐镜交接包（V11 不受影响，不重跑 Blender）",
                                "D08 正文与字数档", "D09 台词与潜台词", "D12 提示词", "D15 混音曲线"],
                "applied_by": "分镜导演（bot_1855d6ce9cdd）",
            })
        bump(d16)
    if changed15:
        bump(d15)

    if not (changed16 or changed15):
        print(f"✅ {unit} 无变化，不写盘")
        return

    if dry:
        print(f"   [dry-run] 将写 {unit} D16" + ("／D15" if changed15 else ""))
        for r in records:
            print("   ·", r)
        return

    os.makedirs(bak, exist_ok=True)
    for doc, obj, changed in (("D16", d16, changed16), ("D15", d15, changed15)):
        if not changed:
            continue
        p = os.path.join(ROOT, "units", unit, f"{doc}.json")
        # ── 写前并发复核：读盘后若被他人升版，立即中止（不覆盖对方改动）──
        now = fingerprint(p)
        if now != fp0[doc]:
            print(f"❌ 并发守卫：{doc}.json 在读盘后被改动（读盘时 {fp0[doc]} → 现在 {now}）"
                  f" ⇒ 放弃本次写盘，请重新核对基线后再跑。")
            sys.exit(1)
        b = os.path.join(bak, f"{doc}.json")
        if not os.path.exists(b):
            shutil.copy2(p, b)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 写 {doc}.json（v{obj.get('version')}）")
    for r in records:
        print("   ·", r)
    print(f"   备份 {bak}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    units = [a.unit] if a.unit else list(FILL_FILES.keys())
    for u in units:
        if os.path.isdir(os.path.join(ROOT, "units", u)):
            process(u, a.dry_run)


if __name__ == "__main__":
    main()
