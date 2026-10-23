#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_D08.py —— 分集剧本生成器（单元参数化，U02 起统一入口）

用法：
  python3 scripts/build_D08.py --project 02_项目/双相潮主 --unit U02
  python3 scripts/build_D08.py --project 02_项目/双相潮主 --unit U02 --dry-run

设计（对齐 U02-R01 裁决「禁止复制 _u02 副本」）：
  · **本文件是逻辑，内容在同目录 d08_content_<UNIT>.py**。
    换单元只换内容模块与 --unit 参数，不新增脚本副本，避免两套实现分叉。
  · 本岗自检（不依赖 validate.mjs，写盘前先拦）：
      ① 集号与 D06/D07 完全一致；标题与 D06 一致
      ② 台词角色 ∈ D07 在场名单（V2 前置）
      ③ 字数两档：base ∈ [180,240]、total ≤ 330（口径与 fix-wordcount.mjs 一致）
      ④ 禁词扫描（rules.forbidden_words）＋ D05 禁用同义写法扫描
      ⑤ 贬称扫描（rules.derogatory_terms，只对台词）
      ⑥ shot_intent：每集 ≥2 条、≤60 字、不含运镜词
      ⑦ 合规增量段必须写 compliance_reason
  · 任一项不过 → 报错退出，**不写盘**。
  · present_characters 直接取自 D07 在场名单（单一真源，不在内容里重复维护）。
"""

import argparse
import importlib
import json
import os
import re
import sys

def _find_factory_root(start: str) -> str:
    """向上查找含 `03_规格` 的工厂根目录（不靠固定层数，换目录层级即失效）。"""
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "03_规格")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise SystemExit("❌ 找不到含 03_规格 的工厂根目录")


FACTORY_ROOT = _find_factory_root(os.path.dirname(os.path.abspath(__file__)))
SPEC_DIR = os.path.join(FACTORY_ROOT, "03_规格")


# ── 字数口径：与 04_工具/fix-wordcount.mjs 完全一致 ──────────────────
def count_words(s: str) -> int:
    cjk = len(re.findall(r"[一-鿿]", s))
    words = len(re.findall(r"[A-Za-z0-9]+", s))
    return cjk + words


# ── shot_intent 禁写的运镜词（交给 D10／D11，本层越权即错）────────────
CAMERA_BAN = [
    "特写", "近景", "中景", "全景", "远景", "景深", "焦距", "机位", "运镜",
    "镜头", "视角", "构图", "长焦", "广角", "主观", "过肩", "俯拍", "仰拍",
    "平拍", "跟拍", "轨道", "摇臂", "画面角度", "景别",
]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="版本守卫下强行覆盖（人工确认后使用）")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    unit = args.unit
    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    D06 = load_json(os.path.join(project, "units", unit, "D06.json"))
    D07 = load_json(os.path.join(project, "units", unit, "D07.json"))
    D04 = load_json(os.path.join(project, "shared", "D04.json"))
    D05 = load_json(os.path.join(project, "shared", "D05.json"))
    RULES = load_json(os.path.join(SPEC_DIR, "rules.json"))

    content = importlib.import_module(f"d08_content_{unit}")
    EPISODES = content.EPISODES
    VERSION = getattr(content, "VERSION", "v1.0")
    STATUS = getattr(content, "STATUS", "in_review")

    chars = {c["id"]: c for c in D04["characters"]}
    minors = {c["id"] for c in D04["characters"] if c.get("minor")}
    d06 = {e["ep"]: e for e in D06["episodes"]}
    d07 = {e["ep"]: e for e in D07["episodes"]}

    banned = set(RULES["forbidden_words"])
    for g in D05["glossary"]:
        banned |= set(g.get("forbidden_synonyms") or [])
    derogatory = set(RULES["derogatory_terms"])
    wc = RULES["word_count"]
    base_min, base_max = wc["base_min"], wc["base_max"]
    total_max = wc["total_max"]

    errors = []
    warns = []
    out_eps = []

    # 集号集合必须与 D06/D07 一致
    src_eps = sorted(d06.keys())
    content_eps = sorted(e["ep"] for e in EPISODES)
    if content_eps != src_eps:
        errors.append(f"集号与 D06 不一致：内容 {content_eps} vs D06 {src_eps}")

    for e in EPISODES:
        ep = e["ep"]
        tag = f"ep{ep}"
        d6, d7 = d06.get(ep), d07.get(ep)
        if not d6 or not d7:
            errors.append(f"{tag}: D06/D07 缺该集")
            continue

        # 标题与 D06 一致
        if e.get("title") != d6.get("title"):
            errors.append(f"{tag}: 标题「{e.get('title')}」与 D06「{d6.get('title')}」不一致")
        # 时长取 D07（D07 的字段名是 duration_sum_sec，不是 duration_sec）
        duration_sec = d7.get("duration_sec") or d7.get("duration_sum_sec")
        if not isinstance(duration_sec, int):
            errors.append(f"{tag}: D07 缺可用的时长字段（duration_sec / duration_sum_sec）")
        # 在场名单直接取 D07（单一真源）
        present = [p["char_id"] for p in d7.get("present_characters", [])]
        d07_set = set(present)

        body = []
        base = 0
        add = 0
        intents = 0
        for i, b in enumerate(e["body"]):
            item = {"type": b["type"], "text": b["text"]}
            if b["type"] == "dialogue":
                cid = b.get("char_id")
                if not cid:
                    errors.append(f"{tag} body[{i}]: 台词缺 char_id")
                else:
                    item["char_id"] = cid
                if not cid:
                    pass
                elif cid not in chars:
                    errors.append(f"{tag} body[{i}]: 角色 {cid} 不在 D04")
                elif cid not in d07_set:
                    errors.append(
                        f"{tag} body[{i}]: 台词角色 {cid} 不在 D07 ep{ep} 在场名单 {sorted(d07_set)}"
                    )
                if cid in minors:
                    errors.append(f"{tag} body[{i}]: 角色 {cid} 为未成年，台词须按 Q14=C 从严处置")
                if b.get("emotion"):
                    item["emotion"] = b["emotion"]
                # 贬称扫描（只对台词）
                for d in derogatory:
                    if d in b["text"]:
                        errors.append(f"{tag} body[{i}]: 台词命中贬称「{d}」")
            if b.get("sfx"):
                item["sfx"] = b["sfx"]
            # 禁词扫描（正文 + 情绪）
            scan_text = f"{b['text']} {b.get('emotion','')}"
            for w in sorted(banned):
                if w and w in scan_text:
                    errors.append(f"{tag} body[{i}]: 命中禁用写法「{w}」:: {b['text'][:40]}")
            # 合规增量必须有理由
            if b.get("compliance_added"):
                if not str(b.get("compliance_reason") or "").strip():
                    errors.append(f"{tag} body[{i}]: 标了 compliance_added 却没写 compliance_reason")
                item["compliance_added"] = True
                item["compliance_reason"] = b["compliance_reason"]
            # shot_intent 校验
            if b.get("shot_intent"):
                si = b["shot_intent"]
                intents += 1
                if len(si) > 60:
                    errors.append(f"{tag} body[{i}]: shot_intent 超 60 字（{len(si)}）")
                for w in CAMERA_BAN:
                    if w in si:
                        errors.append(f"{tag} body[{i}]: shot_intent 含运镜词「{w}」（越权到 D10/D11）")
                item["shot_intent"] = si
            # 字数
            n = count_words(b["text"])
            if b.get("compliance_added"):
                add += n
            else:
                base += n
            body.append(item)

        if intents < 2:
            errors.append(f"{tag}: shot_intent 仅 {intents} 条，至少 2 条")
        if base < base_min:
            errors.append(f"{tag}: 基础字数 {base} < 下限 {base_min}")
        if base > base_max:
            errors.append(f"{tag}: 基础字数 {base} > 上限 {base_max}")
        total = base + add
        if total > total_max:
            errors.append(f"{tag}: 总字数 {total} > 硬上限 {total_max}")

        notes = list(e.get("compliance_notes") or [])
        if not notes:
            errors.append(f"{tag}: compliance_notes 为空")

        out_eps.append({
            "ep": ep,
            "title": e["title"],
            "duration_sec": duration_sec,
            "scene_heading": e["scene_heading"],
            "present_characters": present,
            "body": body,
            "word_count": {"base": base, "compliance_add": add, "total": total},
            "compliance_notes": notes,
        })

    if errors:
        print("❌ 自检未通过（未写盘）：")
        for x in errors:
            print("   -", x)
        sys.exit(1)

    print(f"✅ 自检通过｜{unit} D08 {VERSION}")
    for e in out_eps:
        w = e["word_count"]
        print(f"   ep{e['ep']:>3} {e['title']:<6} base={w['base']:>3} add={w['compliance_add']:>3} "
              f"total={w['total']:>3} 行数={len(e['body']):>2} 在场={len(e['present_characters'])}")
    for x in warns:
        print("   ! ", x)

    if args.dry_run:
        print("（--dry-run：未写盘）")
        return

    out = {
        "doc_id": "D08",
        "unit": unit,
        "version": VERSION,
        "status": STATUS,
        "episodes": out_eps,
    }
    target = os.path.join(project, "units", unit, "D08.json")

    # ── 版本守卫（2026-10-23 台本编剧加）──────────────────────────────
    # 防「第二个写者 / 旧内容源」把已升版的产物**静默回退**（Q27 教训）。
    # 判据：磁盘产物的 version **高于**本脚本要写的 version → 拒绝覆盖并中止。
    # 正常升版（磁盘 v1.0 → 脚本 v1.1）与幂等重跑（版本相同）均放行。
    # 需要故意回退时用 --force 显式放行（人工确认过再动）。
    def _vkey(v):
        m = re.match(r"^v?(\d+)\.(\d+)$", str(v or ""))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    if os.path.exists(target):
        try:
            cur = json.load(open(target, encoding="utf-8"))
            cur_v = cur.get("version")
            if _vkey(cur_v) > _vkey(VERSION) and not getattr(args, "force", False):
                print(f"❌ 版本守卫：磁盘 {target} 已是 **{cur_v}**，"
                      f"高于本脚本要写的 **{VERSION}** → 拒绝覆盖，未写盘。")
                print("   可能原因：另一个写者已用更新版本落盘，或本脚本用的是旧内容源。")
                print("   确认确需回退时，加 --force 显式放行。")
                sys.exit(1)
        except json.JSONDecodeError:
            pass  # 磁盘文件损坏 → 照常覆盖，交由自检与 validate 兜底

    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写 {target}")


if __name__ == "__main__":
    main()
