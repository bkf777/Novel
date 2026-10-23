#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《双相潮主》D12 image_prompt 拼接边界 · 负测（D18 global_checks Q107）

用法：
    python3 scripts/test_d12_prompt_boundary.py        # 跑全部腿
    python3 scripts/test_d12_prompt_boundary.py -v     # 附见证细节

两腿（章程纪律：判据改宽改严必先补负测证明不是恒真）：
    腿① —— 一张**有**取景句的卡：断言交界处有句读分隔、且无黏连、无同卡重复句；
    腿② —— 一张**无**取景句（frame 为空）的卡：断言不产生多余标点、且拼接合法。

**反恒真见证（每腿都配一条「会失败的旧实现」）** ——
    腿① 的见证 = 旧裸拼实现 legacy_join：同一输入下黏连正则命中 ⇒ 若有人把拼接器改回裸拼，本腿立刻红。
    腿② 的见证 = 无脑补句号实现 naive_join：同一输入下出现「。。」⇒ 若有人改成「每段后面都加。」，本腿立刻红。
    ⇒ 断言不是恒真：它们能区分「修好的实现」与「两种典型错修」。

退出码：0 = 全过；1 = 有腿失败。
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
VERBOSE = False

RESULTS = []


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENG = _load(os.path.join(HERE, "build_D12.py"), "build_D12")


# ---------------------------------------------------------------- 两种「错修」见证实现
def legacy_join(frags):
    """旧裸拼（build_D12.py 修复前的表达式原样）：frame 无尾标点 ⇒ 与 BADGE_POS 黏成一句。"""
    header, lens_phrase, appear, body, frame, badge, style = frags
    return header + lens_phrase + "。" + appear + body + frame + badge + style


def naive_join(frags):
    """无脑补句号（典型错修）：每段后面都加「。」⇒ frame 为空时出现「。。」。"""
    out = ""
    for f in frags:
        f = (f or "").strip()
        if not f:
            continue
        out += f + "。"
    return out


# ---------------------------------------------------------------- 取真实卡数据
def load_unit(unit):
    content = _load(os.path.join(HERE, f"d12_content_{unit}.py"), f"d12_content_{unit}")
    d11 = json.load(open(os.path.join(PROJ, "units", unit, "D11.json"), encoding="utf-8"))
    shots = {(e["ep"], s["shot_id"]): s for e in d11["episodes"] for s in e["shots"]}
    return content, shots


def card_fragments(content, shots, ep, shot_id, frame_override=None):
    """按引擎同款算法拼出该卡的 7 个片段。"""
    shot = shots[(ep, shot_id)]
    frame = ENG.framing_of(shot["visual_facts"]) if frame_override is None else frame_override
    header = (f"{shot['shot_size']}，{shot['camera_angle']}，{shot['lens_mm']}mm，"
              f"{shot['movement']}，9:16 竖屏。")
    lens_phrase = ENG.LENS_PHRASE[int(shot["lens_mm"])]
    appear = content.SCENE_APPEARANCE[shot["scene_code"]]
    item = next(c for c in content.CARDS if c["ep"] == ep and c["shot_id"] == shot_id)
    return [header, lens_phrase, appear, item["body_image"], frame, ENG.BADGE_POS, ENG.STYLE], frame, item


def check(leg, name, cond, detail=""):
    ok = bool(cond)
    RESULTS.append((leg, name, ok, detail))
    print(f"  {'✅' if ok else '❌'} [{leg}] {name}" + (f"  —— {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 腿① 有取景句
def leg1():
    print("腿① —— 一张【有】取景句的卡（断言：交界处有句读分隔、且无黏连、无同卡重复句）")
    content, shots = load_unit("U02")
    frags, frame, item = card_fragments(content, shots, 11, 1)
    check("腿①", "样本卡确为有取景句的卡", bool(frame), f"frame={frame!r}")
    ip = ENG.join_fragments(frags)

    # ① 取景声明落地
    check("腿①", "取景声明仍落在 image_prompt 内", frame in ip)
    # ② 交界处补了句读分隔：frame 之后紧跟的字符是句读终止符
    idx = ip.find(frame)
    after = ip[idx + len(frame)] if idx >= 0 else ""
    check("腿①", "frame 与下一片段之间有句读分隔", after in ENG.SENT_END_CHARS,
          f"frame 后一个字符={after!r}")
    # ③ 无黏连
    m = ENG.RUNON_RE.search(ip)
    check("腿①", "黏连正则零命中", m is None, (m.group(0) if m else "0 命中"))
    # ④ 无同卡重复句
    dups = ENG.dup_sentences(ip)
    check("腿①", "同卡重复句计数 = 0", not dups, (dups[0] if dups else "0"))
    # ⑤ 无多余标点
    check("腿①", "无「。。」", "。。" not in ip)

    # ---- 反恒真见证：旧裸拼实现必须在同一输入下失败 ----
    old = legacy_join(frags)
    old_m = ENG.RUNON_RE.search(old)
    check("腿①", "【见证】旧裸拼实现确实黏连（本腿不是恒真）", old_m is not None,
          (f"旧实现命中 {old_m.group(0)!r}" if old_m else "旧实现竟然没命中 —— 见证失效"))
    check("腿①", "【见证】旧裸拼实现的 frame 后一个字符非句读终止符",
          old[old.find(frame) + len(frame)] not in ENG.SENT_END_CHARS)


# ---------------------------------------------------------------- 腿② 无取景句
def leg2():
    print("腿② —— 一张【无】取景句的卡（断言：不产生多余标点、且拼接合法）")
    content, shots = load_unit("U02")
    frags, frame, item = card_fragments(content, shots, 11, 1, frame_override="")
    check("腿②", "样本卡确为无取景句的卡（frame 为空）", frame == "", f"frame={frame!r}")
    ip = ENG.join_fragments(frags)

    # ① 无多余标点
    check("腿②", "无「。。」", "。。" not in ip)
    check("腿②", "无悬空分隔（无「；。」「：。」等）",
          not any(a + b in ip for a in "；：！？，、" for b in "。；：！？"))
    # ② 拼接合法：frame 为空 ⇒ 其余片段原样相接，一个字符都不多
    expect = (frags[0] + frags[1] + "。" + frags[2] + frags[3] + frags[5] + frags[6])
    check("腿②", "拼接结果与「跳过空片段」的预期逐字一致", ip == expect,
          f"长度 {len(ip)} vs 预期 {len(expect)}")
    # ③ 无黏连、无重复句
    m = ENG.RUNON_RE.search(ip)
    check("腿②", "黏连正则零命中", m is None, (m.group(0) if m else "0 命中"))
    dups = ENG.dup_sentences(ip)
    check("腿②", "同卡重复句计数 = 0", not dups, (dups[0] if dups else "0"))
    # ④ 空片段路径可达（不是死代码）：真实 visual_facts 末段不是角标语、且无任何取景关键词时
    #    framing_of 返回空 ⇒ 引擎必须能安全跳过空片段
    vf = "远处传来脚步声；门缝里透出微光"
    check("腿②", "空片段路径真实可达（framing_of 对无取景段返回空）",
          ENG.framing_of(vf) == "", f"framing_of({vf!r})={ENG.framing_of(vf)!r}")

    # ---- 反恒真见证：无脑补句号实现必须在同一输入下失败 ----
    naive = naive_join(frags)
    check("腿②", "【见证】无脑补句号实现确实产生「。。」（本腿不是恒真）", "。。" in naive,
          "见证失效" if "。。" not in naive else "命中「。。」")


# ---------------------------------------------------------------- 腿③ 去重腿（C-213 同源）
def leg3():
    print("腿③ —— 重复片段去重腿（U03 C-213 同源：frame 与 body 重复）")
    content, shots = load_unit("U03")
    frags, frame, item = card_fragments(content, shots, 20, 1)
    check("腿③", "样本卡 frame 与 body 确有重复", frame and frame in item["body_image"],
          f"frame={frame!r}")
    ip = ENG.join_fragments(frags)
    check("腿③", "重复片段只出现一次", ip.count(frame) == 1, f"出现 {ip.count(frame)} 次")
    dups = ENG.dup_sentences(ip)
    check("腿③", "同卡重复句计数 = 0", not dups, (dups[0] if dups else "0"))
    m = ENG.RUNON_RE.search(ip)
    check("腿③", "黏连正则零命中", m is None, (m.group(0) if m else "0 命中"))
    # 见证：旧裸拼下该卡同时出现黏连与重复短语
    old = legacy_join(frags)
    check("腿③", "【见证】旧裸拼实现下该卡重复短语出现 2 次",
          old.count(frame) == 2, f"旧实现出现 {old.count(frame)} 次")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    global VERBOSE
    VERBOSE = args.verbose

    print("D12 拼接边界负测（Q107）")
    print("=" * 78)
    leg1()
    leg2()
    leg3()
    print("=" * 78)
    failed = [r for r in RESULTS if not r[2]]
    print(f"共 {len(RESULTS)} 项断言，通过 {len(RESULTS) - len(failed)}，失败 {len(failed)}")
    if failed:
        for leg, name, _, detail in failed:
            print(f"  ❌ [{leg}] {name}  {detail}")
        return 1
    print("✅ 全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
