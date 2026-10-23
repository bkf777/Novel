#!/usr/bin/env python3
"""W6 · 白模姿态数据一致性检查（白模层数据自洽性）

为什么需要这条检查（2026-10-23 · Q94 背景）：
工厂此前**没有任何一条规则**把白模层的数据自洽性纳入校验，于是：
  · `POSE_SIZE` 缺 `run` ⇒ `CHAR_ANIM` 里写了 `run` 时静默回退 `stand`（或直接 KeyError）
  · `CHAR_ANIM` 与 `CHARS` 在同一 (scene, gsn) 姿态相反，而构建器让 ANIM 静默覆盖 CHARS
    ⇒ 冲突永远不会暴露，只会在实拍帧里变成「一个翻滚的板子」
  · `lie` 的尺寸已按「长轴沿 X」给，构建器却又加 `rotation_euler=(0,-90°,0)`
    ⇒ 躺着的人被立成竖板，且 rotation 关键帧插值产生 45° 翻滚

V12（`04_工具/lib/rules.mjs`）判的是**输出**（投影占幅）；本脚本判的是**输入**（内容层数据）。
两者同源于 `03_规格/rules.json` → `white_model_framing`，但实现不同源，可交叉复核。

用法：
    python3 04_工具/check_white_model_poses.py --project 02_项目/双相潮主
    python3 04_工具/check_white_model_poses.py --project 02_项目/双相潮主 --unit U01

退出码：0 = 通过；1 = 有 error
"""

import argparse
import importlib.util
import json
import os
import re
import sys

FACTORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_rules():
    p = os.path.join(FACTORY_ROOT, "03_规格", "rules.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块：{path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def chars_of(anim_entry):
    """CHAR_ANIM[ (scene, gsn) ] = { 英文名: [(t,x,y,z,pose), ...] }"""
    if not isinstance(anim_entry, dict):
        return {}
    out = {}
    for en, keys in anim_entry.items():
        if not isinstance(keys, list) or not keys:
            continue
        out[en] = keys[0][4] if len(keys[0]) > 4 else None
    return out


def chars_static(chars_entry):
    """CHARS[ (scene, gsn) ] = [(en, cn, x, y, z, h, pose), ...]"""
    out = {}
    for spec in chars_entry or []:
        try:
            en = spec[0]
            pose = spec[6] if len(spec) > 6 else None
        except (TypeError, IndexError):
            continue
        out[en] = pose
    return out


def check_unit(scripts_dir, unit, cfg, errors, warnings):
    fname = f"white_model_content_{unit}.py"
    fpath = os.path.join(scripts_dir, fname)
    if not os.path.exists(fpath):
        warnings.append(f"{unit}: 未找到 {fname}，跳过姿态数据检查")
        return
    mod = load_module(fpath, f"wm_content_{unit}")

    pose_size = getattr(mod, "POSE_SIZE", {}) or {}
    char_anim = getattr(mod, "CHAR_ANIM", {}) or {}
    chars = getattr(mod, "CHARS", {}) or {}
    vocab = cfg.get("pose_vocabulary") or []

    # W6a 词表覆盖：POSE_SIZE 必须覆盖所有实际用到的 pose
    used = set()
    for keys in char_anim.values():
        for k in keys.values():
            for item in k:
                if len(item) > 4:
                    used.add(item[4])
    for spec in chars.values():
        for item in spec:
            if len(item) > 6:
                used.add(item[6])
    for p in sorted(used):
        if p not in pose_size:
            errors.append(f"{unit}: 姿态「{p}」被使用但 POSE_SIZE 未定义（构建时会 KeyError 或静默回退）")
    if vocab:
        for p in sorted(used):
            if p not in vocab:
                errors.append(f"{unit}: 姿态「{p}」不在白模姿态词表内（允许：{'/'.join(vocab)}）")
        for p in sorted(pose_size.keys()):
            if p not in vocab:
                warnings.append(f"{unit}: POSE_SIZE 定义了「{p}」但不在词表内（词表真源：rules.json white_model_framing.pose_vocabulary）")

    # W6b CHAR_ANIM 与 CHARS 冲突：构建器让 ANIM 静默覆盖 CHARS，冲突必须显式暴露
    conflicts = 0
    for key, anim in char_anim.items():
        a = chars_of(anim)
        c = chars_static(chars.get(key))
        for en, pose_a in a.items():
            if en in c and c[en] is not None and pose_a is not None and c[en] != pose_a:
                conflicts += 1
                errors.append(
                    f"{unit}: 姿态冲突 {key} 角色「{en}」—— CHAR_ANIM 首帧「{pose_a}」vs CHARS「{c[en]}」"
                    f"（构建器 ANIM 覆盖 CHARS，冲突不会自行暴露）"
                )
    if not conflicts:
        warnings.append(f"{unit}: CHAR_ANIM / CHARS 姿态冲突 0 处")

    # W6c run 姿态：历史上缺 `run` 导致 A-1 镜4 的跑动被静默回退
    if "run" in used and "run" not in pose_size:
        errors.append(f"{unit}: 使用了「run」但 POSE_SIZE 未定义 run")


def check_builder(scripts_dir, cfg, errors, warnings):
    """构建器源码扫描：`lie` 不得再叠加 -90° 旋转；rotation 不得对 lie 插关键帧。"""
    bpath = os.path.join(scripts_dir, "build_white_model.py")
    if not os.path.exists(bpath):
        warnings.append("未找到 build_white_model.py，跳过构建器源码检查")
        return
    src = open(bpath, "r", encoding="utf-8").read()
    # lie 姿态叠加 -90° 绕 Y 旋转 ⇒ 躺着的人被立成竖板（历史缺陷）
    lie_rot = re.findall(r'["\']lie["\']\s*:\s*[^#\n]*?rotation_euler', src)
    if lie_rot:
        errors.append("build_white_model.py: 检测到 lie 姿态叠加 rotation_euler（会把躺着的人立成竖板）")
    for m in re.finditer(r'rotation_euler[^\n]*radians\(\s*-?\d+', src):
        line = src[: m.start()].count("\n") + 1
        seg = src[max(0, m.start() - 260) : m.start() + 120]
        if "lie" in seg:
            errors.append(f"build_white_model.py:{line}: lie 相关分支仍写入 rotation_euler")
    # rotate 关键帧：animate_char 对 rotation_euler 插关键帧会造出翻滚
    if re.search(r'keyframe_insert\(\s*["\']rotation_euler["\']', src):
        warnings.append(
            "build_white_model.py: animate_char 对 rotation_euler 插了关键帧 —— "
            "相邻姿态插值会产生翻滚，W4 上限 30°"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--unit", default=None)
    args = ap.parse_args()

    project_dir = os.path.abspath(os.path.join(FACTORY_ROOT, args.project))
    scripts_dir = os.path.join(project_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        print(f"找不到 scripts 目录：{scripts_dir}")
        return 2

    cfg = load_rules().get("white_model_framing", {}) or {}
    units_root = os.path.join(project_dir, "units")
    units = (
        [args.unit]
        if args.unit
        else sorted(d for d in os.listdir(units_root) if os.path.isdir(os.path.join(units_root, d)))
    )

    errors, warnings = [], []
    for u in units:
        check_unit(scripts_dir, u, cfg, errors, warnings)
    check_builder(scripts_dir, cfg, errors, warnings)

    print("\n■ 白模姿态数据一致性检查（W6）")
    for w in warnings:
        print(f"   ! {w}")
    for e in errors:
        print(f"   ✗ {e}")
    print(f"■ 结果  error {len(errors)}  warning {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
