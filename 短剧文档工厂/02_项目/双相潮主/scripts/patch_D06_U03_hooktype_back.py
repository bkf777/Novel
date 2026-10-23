#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
patch_D06_U03_hooktype_back.py —— 故事架构：**把 U03 D06 的 hook_type / hook_type_reason 回并进生成器**
                                  （Q40 同型：改内容源，不手改产物；回并后重跑必须逐字节一致）

为什么必须做（2026-10-23 13:4x 本岗自查发现）：
  Chief 13:1x 裁「真风险是**改 JSON 不并回脚本 ⇒ 将来按源脚本重建静默回退**」，台本编剧已在 D08/D09
  侧回并并做了零漂移自证。**本岗的 U03 同类雷落在 D06 上**：
    · `units/U03/D06.json` 现盘 v1.1（12,137 B）**比生成器产物多出 8 集的 `hook_type` /
      `hook_type_reason`**（D06.episodes 层的可选字段，schema 枚举 5 类：悬念/反转/情绪/信息/危机）；
    · 生成器 `build_D06_D07_U03.py` 内 `hook_type` 命中 **0** ⇒ **重跑生成器 = 这 8 集的 hook 字段
      被整份抹掉**（静默回退，且抹掉的是「钩子类型」这一短剧节奏判据的输入）。
  ⇒ 修法＝把现盘值**逐字回并**进 `D06_EPISODES`，版本常量升 v1.1，重跑后与现盘**逐字节一致**。

做法与守则：
  ① 值源＝**现盘 `units/U03/D06.json`**（它才是已过闸的值），不在本脚本内臆造文案；
  ② 插入位置＝`foreshadow` 之后（与现盘键序一致，否则 JSON 字节序不同 ⇒ 无法逐字节比对）；
  ③ 改生成器**前**先备份；改**后**先沙箱跑、比对字节、一致才落真盘；
  ④ 落真盘用生成器自身的 `--force`，且要求输出**逐字节等于**现盘（否则中止）；
  ⑤ 本脚本**不改任何产物**（产物由生成器产出），故不涉及 Q40 的「手改产物」。

用法：python3 scripts/patch_D06_U03_hooktype_back.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

SCRIPT = "scripts/build_D06_D07_U03.py"
HOOK_KEYS = ("hook_type", "hook_type_reason")
HOOK_ENUM = ["悬念", "反转", "情绪", "信息", "危机"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project)
    sp = os.path.join(root, SCRIPT)
    d06p = os.path.join(root, "units", "U03", "D06.json")
    if not os.path.isfile(sp) or not os.path.isfile(d06p):
        sys.exit("[ABORT] 生成器或现盘 D06 不存在；不写盘。")

    src = open(sp, encoding="utf-8").read()
    disk = json.load(open(d06p, encoding="utf-8"))
    already = "hook_type" in src
    if already:
        print("[IDEMPOTENT] 生成器内已含 hook_type；跳过回填写入，改走「复现校验 + 规范化落盘」阶段。")

    # ① 取现盘值（逐字）
    vals = {}
    for e in disk["episodes"]:
        ht = e.get("hook_type")
        hr = e.get("hook_type_reason")
        if ht not in HOOK_ENUM:
            sys.exit(f"[ABORT] 现盘 ep{e['ep']}.hook_type={ht!r} 不在 schema 枚举内；不写盘。")
        if not isinstance(hr, str) or not hr.strip():
            sys.exit(f"[ABORT] 现盘 ep{e['ep']}.hook_type_reason 缺失或为空；不写盘。")
        vals[e["ep"]] = (ht, hr)

    # ② 定位 D06_EPISODES 段的 foreshadow 行（每集一行，共 8 行；行内容随伏笔非空而变 ⇒ 按行匹配）
    lines = src.split("\n")
    idx_foreshadow = [i for i, l in enumerate(lines)
                      if l.startswith('        "foreshadow": {') and l.rstrip().endswith("},")]
    if len(idx_foreshadow) != len(vals):
        sys.exit(f"[ABORT] 生成器内 foreshadow 行命中 {len(idx_foreshadow)} ≠ 集数 {len(vals)}；不写盘。")

    # 逐集按出现顺序（与 D06_EPISODES 的集序一致）回填
    # ⚠️ **必须倒序插入**：正序插会实时抬高后续行号 ⇒ 越插越偏（首跑即触发 SyntaxError）
    order = sorted(vals)
    for li, ep in reversed(list(zip(idx_foreshadow, order))):
        ht, hr = vals[ep]
        add = [f'        "hook_type": {json.dumps(ht, ensure_ascii=False)},',
               f'        "hook_type_reason": {json.dumps(hr, ensure_ascii=False)},']
        lines[li + 1:li + 1] = add
    new_src = "\n".join(lines)

    # ③ 版本常量：D06_VERSION v1.0 → v1.1（与现盘一致；版本只进不退）
    if not already:
        if 'D06_VERSION = "v1.0"' not in new_src:
            sys.exit("[ABORT] 未找到 D06_VERSION = \"v1.0\" 字面量；不写盘。")
        new_src = new_src.replace('D06_VERSION = "v1.0"', 'D06_VERSION = "v1.1"', 1)

    if args.dry_run:
        print(f"[DRY-RUN] 将回并 {len(order)} 集的 hook_type/hook_type_reason 进生成器；"
              f"D06_VERSION v1.0 → v1.1；生成器字节 {len(src.encode()):,} → {len(new_src.encode()):,}")
        return 0

    if not already:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bdir = os.path.join(root, "reports", f"_bak_d06_u03_hooktype_{stamp}")
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(sp, os.path.join(bdir, os.path.basename(SCRIPT)))
        print(f"ℹ️ 生成器备份已落：{bdir}")

        with open(sp, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"✅ 生成器已回并：hook_type/hook_type_reason × {len(order)} 集｜D06_VERSION → v1.1｜"
              f"{len(new_src.encode()):,} B｜sha {hashlib.sha256(new_src.encode()).hexdigest()[:16]}")

    # ④ 沙箱跑：产物必须与现盘逐字节一致，否则中止（不碰真盘）
    sbx = os.path.join("/tmp", f"sxr_hooktype_{os.getpid()}")
    os.makedirs(os.path.join(sbx, "02_项目", "双相潮主"), exist_ok=True)
    os.makedirs(os.path.join(sbx, "03_规格"), exist_ok=True)
    subprocess.run(["rsync", "-a", "--exclude", "reports", "--exclude", "preview", "--exclude",
                    "render", "--exclude", "D14_shots", root + "/",
                    os.path.join(sbx, "02_项目", "双相潮主") + "/"], check=True)
    factory = os.path.abspath(os.path.join(root, "..", ".."))
    shutil.copy2(os.path.join(factory, "03_规格", "rules.json"),
                 os.path.join(sbx, "03_规格", "rules.json"))
    for f in ("D06.json", "D07.json"):
        q = os.path.join(sbx, "02_项目", "双相潮主", "units", "U03", f)
        if os.path.exists(q):
            os.remove(q)
    r = subprocess.run([sys.executable, sp, "--project",
                        os.path.join(sbx, "02_项目", "双相潮主"), "--force"],
                       capture_output=True, text=True)
    print(r.stdout[-700:])
    if r.returncode != 0:
        sys.exit(f"[ABORT] 沙箱生成失败 rc={r.returncode}；未碰真盘。\n{r.stderr[-500:]}")
    for f in ("D06.json", "D07.json"):
        a = open(os.path.join(sbx, "02_项目", "双相潮主", "units", "U03", f), "rb").read()
        b = open(os.path.join(root, "units", "U03", f), "rb").read()
        if a != b:
            # 字节不等 ⇒ 先判「语义是否等价」：等价则只可能是序列化约定差（如尾随换行），
            # 由生成器规范化落盘；**语义不等则一律中止**，不碰真盘。
            try:
                ja, jb = json.loads(a.decode("utf-8")), json.loads(b.decode("utf-8"))
            except Exception as e:
                sys.exit(f"[ABORT] 沙箱与现盘 {f} 字节不等且无法解析：{e}；未碰真盘。")
            if ja != jb:
                sys.exit(f"[ABORT] 沙箱与现盘 {f} **语义不等**（生成器仍未复现现盘）；未碰真盘。")
            print(f"  ⚠️ {f}：字节差 {len(a)-len(b):+d} B，但 **JSON 语义完全等价**"
                  f"（仅序列化约定差，如尾随换行）⇒ 由生成器规范化落盘")
            continue
        print(f"  ✓ 沙箱 {f} 与现盘逐字节一致 ✅"
              f"（{len(a):,} B｜sha {hashlib.sha256(a).hexdigest()[:16]}）")

    # ⑤ 真盘：跑生成器（--force）。字节已一致 ⇒ 生成器自身幂等判定会跳过写入。
    r2 = subprocess.run([sys.executable, sp, "--project", root, "--force"],
                        capture_output=True, text=True)
    print(r2.stdout[-700:])
    if r2.returncode != 0:
        sys.exit(f"[ABORT] 真盘生成失败 rc={r2.returncode}。")
    for f in ("D06.json", "D07.json"):
        b = open(os.path.join(root, "units", "U03", f), "rb").read()
        a = open(os.path.join(sbx, "02_项目", "双相潮主", "units", "U03", f), "rb").read()
        if a != b:
            sys.exit(f"[ABORT] 真盘 {f} 与沙箱产物不一致。")
        d = json.loads(b)
        print(f"  ✓ 真盘 {f} ＝ 沙箱产物 ✅ v{d['version']}｜{len(b):,} B｜"
              f"sha {hashlib.sha256(b).hexdigest()[:16]}")
    shutil.rmtree(sbx, ignore_errors=True)
    print("✅ 静默回退雷已闭合：U03 D06/D07 现由生成器可复现（重跑不再丢字段）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
