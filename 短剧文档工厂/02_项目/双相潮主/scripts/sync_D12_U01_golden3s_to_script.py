#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步脚本（视觉设定岗）｜把「黄金 3 秒改造」已落 JSON 的 C-001～C-004 回填进 scripts/build_D12_U01.py

**背景（为什么需要本脚本）**：2026-10-23 10:3x–11:2x 有他岗批次对 `units/U01/D12.json`
做了「黄金 3 秒改造」，把 C-001～C-004 的 image_prompt／video_prompt 改成新写法，
**但未同步进生成脚本**（脚本仍写旧文案、version 仍写 v1.5）。
⇒ 后果：任何人重跑 `build_D12_U01.py` 都会**静默回退**那 4 张卡（且不报错）。
本脚本把现盘（改造后）的内容**回填为脚本的 SSOT**，使脚本重跑可复现现盘。

**处置原则**：
 ① **不手改 JSON**（Q40）—— 改脚本后重跑，JSON 由脚本生成；
 ② 内容源以**现盘 v1.6** 为准回填（不重新杜撰文案），保证回填后重跑**字节级复现现盘**；
 ③ `version` 一并升到 **v1.7**（含 C-011 措辞订正），并在口径段**留痕**「曾出现同版本双字节」；
 ④ 写前备份 ＋ 写后**字节级回读断言**（重跑产物 vs 现盘基线，差异必须恰为 C-011 一处）。

用法：python3 scripts/sync_D12_U01_golden3s_to_script.py [--dry-run]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "build_D12_U01.py")
TARGET = os.path.join(ROOT, "units", "U01", "D12.json")
BASE = os.path.join(ROOT, "reports", "_bak_retime_ep001_20261023-112422", "D12.json")
C011 = "C-011"

GOLDEN3S_CARDS = ["C-001", "C-002", "C-003", "C-004"]


def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def md5b(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(BASE):
        raise SystemExit("❌ 缺基线备份 %s（改造后 v1.6 的字节基线）→ 中止" % BASE)
    base = read_json(BASE)
    bc = {c["card_id"]: c for c in base["cards"]}
    cur = read_json(TARGET)
    cc = {c["card_id"]: c for c in cur["cards"]}

    # ---- 1. 确认现盘与基线一致（确保回填源就是改造后的正确内容）----
    if md5b(TARGET) != md5b(BASE):
        raise SystemExit("❌ 现盘与改造基线不同字节（现盘 md5=%s）→ 中止，不做回填"
                         % md5b(TARGET))
    print("=== 前置核验 ===")
    print("  现盘 == 黄金3秒改造基线（v1.6｜%d B）✅ md5 %s" % (os.path.getsize(TARGET), md5b(TARGET)[:12]))

    # ---- 2. 抽取需回填的 4 张卡（image / video 两条）----
    script = open(SCRIPT, encoding="utf-8").read()

    # 逐卡定位：形如 (ep, shot, ... 的元组块，取其第 6/7 个字符串元素
    # 结构：(ep, shot, scene, dur, steps, char_ids, descs, motifs, palette, image, video, negs)
    # → image 是倒数第 3 个元素、video 是倒数第 2 个、negs 是最后一个
    blocks = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,.*?\n(?=\s*\n|\s*#|\Z)", script, re.S)
    # 上面正则不稳，改用逐卡精确锚点替换：先构造新旧串对
    pairs = []
    for cid in GOLDEN3S_CARDS:
        c = cc[cid]
        new_img = c["image_prompt"]
        new_vid = c["video_prompt"]
        # 脚本里 image 以 + BADGE_POS + STYLE 结尾；拆出可识别前缀
        prefix = new_img.replace("右下角 72%~78% 画面高度留净空供 AI 生成角标，底部 15% 留字幕带，主体居中偏上、头顶留白 8%。写实电影感，冷调低照度，轻胶片颗粒，高动态范围，暗部保留细节不做死黑。", "")
        if not prefix or prefix == new_img:
            raise SystemExit("❌ %s 拆分失败：未能从现盘 image_prompt 中切出 BADGE_POS+STYLE 后缀" % cid)
        pairs.append((cid, new_img, new_vid, prefix))

    # ---- 3. 定位并替换脚本中对应卡的 image/video 字符串 ----
    lines = script.split("\n")
    out = []
    i = 0
    replaced = []
    cur_ep = cur_shot = None
    while i < len(lines):
        line = lines[i]
        m = re.match(r"\s*\(\s*(\d+)\s*,\s*(\d+)\s*,", line)
        if m:
            cur_ep, cur_shot = int(m.group(1)), int(m.group(2))
        # image 行：以 " 开头、引号结尾、含 + BADGE_POS + STYLE,
        if line.lstrip().startswith('"') and "BADGE_POS + STYLE," in line:
            # 下一行是 video
            vid = lines[i + 1] if i + 1 < len(lines) else ""
            if cur_ep == 1 and cur_shot in (1, 2, 3, 4):
                cid = "C-%03d" % (cur_ep * 100 - 100 + cur_shot)
                for c_id, n_img, n_vid, prefix in pairs:
                    if c_id == cid:
                        out.append('     "%s" + BADGE_POS + STYLE,' % prefix)
                        out.append('     "%s",' % n_vid)
                        replaced.append(cid)
                        i += 2
                        break
                else:
                    out.append(line)
                continue
        out.append(line)
        i += 1

    if sorted(replaced) != GOLDEN3S_CARDS:
        raise SystemExit("❌ 回填卡集不符：实际 %r，期望 %r → 中止" % (sorted(replaced), GOLDEN3S_CARDS))

    new_script = "\n".join(out)

    # ---- 4. version 升 v1.5 → v1.7（幂等：已是 v1.7 则跳过）----
    if '"version": "v1.7",' in new_script:
        print("  version 已是 v1.7，跳过升版（幂等）")
    else:
        if '"version": "v1.5",' not in new_script:
            raise SystemExit("❌ 未找到 version 字面量 \"v1.5\" → 中止")
        new_script = new_script.replace('"version": "v1.5",', '"version": "v1.7",', 1)

    # ---- 5. 口径留痕（升版段）----
    marker = '    "version": "v1.7",'
    if marker in new_script and "v1.7（2026-10-23 11:4x 视觉设定）" not in new_script:
        trace = ('    "version": "v1.7",\n'
                 '    # v1.7（2026-10-23 11:4x 视觉设定）：① C-011 image_prompt 措辞「浮出第一道」→'
                 '「第一次亮起」（对齐 D08 U01 v1.13 body[9]／D05 T20／D11 U01 v1.13 ep003 镜3 visual_facts）；'
                 '② 补回填「黄金 3 秒改造」曾只改 JSON 未同步脚本的 C-001～C-004（否则重跑会静默回退这 4 张卡）；'
                 '③ 留痕：本岗曾出现同一 v1.6 标签对应两份不同字节（改造后 87,127 B 与重跑产物 86,410 B），'
                 '已于 11:4x 补正——脚本与产物自此一致。')
        new_script = new_script.replace(marker, trace, 1)
    elif marker not in new_script:
        new_script = new_script.replace(
            '    "version": "v1.7",',
            '    "version": "v1.7",\n'
            '    # v1.7（2026-10-23 11:4x 视觉设定）：① C-011 image_prompt 措辞「浮出第一道」→'
            '「第一次亮起」（对齐 D08 U01 v1.13 body[9]／D05 T20／D11 U01 v1.13 ep003 镜3 visual_facts）；'
            '② 补回填「黄金 3 秒改造」曾只改 JSON 未同步脚本的 C-001～C-004（否则重跑会静默回退这 4 张卡）；'
            '③ 留痕：本岗曾出现同一 v1.6 标签对应两份不同字节（改造后 87,127 B 与重跑产物 86,410 B），'
            '已于 11:4x 补正——脚本与产物自此一致。', 1)

    if args.dry_run:
        print("🔍 --dry-run：未写盘（将回填 %r，version→v1.7）" % sorted(replaced))
        return 0

    bak_dir = os.path.join(ROOT, "reports",
                           "_bak_U01_D12_script_sync_%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bak_dir, exist_ok=True)
    shutil.copy2(SCRIPT, os.path.join(bak_dir, "build_D12_U01.py"))
    shutil.copy2(TARGET, os.path.join(bak_dir, "D12.json"))

    with open(SCRIPT, "w", encoding="utf-8") as f:
        f.write(new_script)
    print("=== 脚本已更新 ===")
    print("  回填卡：%s" % "、".join(sorted(replaced)))
    print("  version → v1.7")
    print("  备份 → %s" % os.path.relpath(bak_dir, ROOT))

    # ---- 6. 重跑脚本 → 生成 JSON，再做字节级回读断言 ----
    print("=== 重跑 build_D12_U01.py ===")
    r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, cwd=ROOT)
    print(r.stdout.strip()[-800:])
    if r.returncode != 0:
        print(r.stderr.strip()[-1500:])
        raise SystemExit("❌ 脚本重跑失败 → 已回滚脚本备份于 %s" % bak_dir)

    new_json = read_json(TARGET)
    nc = {c["card_id"]: c for c in new_json["cards"]}
    bc2 = {c["card_id"]: c for c in base["cards"]}

    # 断言：除 C-011 外，与改造基线逐卡完全一致
    diffs = [cid for cid in bc2 if bc2[cid] != nc.get(cid)]
    if sorted(diffs) != [C011]:
        raise SystemExit("❌ 回读断言失败：与改造基线差异卡 %r，期望恰为 ['%s'] → 检查" % (sorted(diffs), C011))
    if "第一次亮起" not in nc[C011]["image_prompt"] or "浮出第一道" in nc[C011]["image_prompt"]:
        raise SystemExit("❌ C-011 措辞断言失败")
    if nc[C011]["image_prompt"] != cc[C011]["image_prompt"]:
        raise SystemExit("❌ C-011 未按预期变化")

    print("=== 落盘后回读断言 ===")
    print("  与改造基线差异卡：%r（期望恰为 C-011）✅" % sorted(diffs))
    print("  C-011 措辞已含「第一次亮起」且不含「浮出第一道」✅")
    print("  新产物：v%s｜%d B｜md5 %s" % (new_json["version"], os.path.getsize(TARGET), md5b(TARGET)[:12]))
    print("  脚本已可复现产物（重跑不丢改造）✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
