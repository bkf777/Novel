#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色图母版规范化 + 站点压缩版生成

两步：
  1. 母版规范化为真 PNG（mcode 部分产物实为 JPEG 却报 .png，扩展名与真实格式不符）
  2. 生成站点用压缩版 JPEG → assets/chars/（纯 ASCII 文件名，规避 URL 编码风险）

用法：python3 build_assets.py
"""
import os, re, subprocess, sys

DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(DIR, "assets", "chars")

# 中文名 → ASCII
ASCII = {
    "01_陈野": "01_chenye", "02_苏晓棠": "02_suxiaotang", "03_裴烈": "03_peilie",
    "04_纪梵": "04_jifan", "05_陈远": "05_chenyuan", "06_赵岚": "06_zhaolan",
    "07_骆红": "07_luohong", "08_老沈": "08_laoshen", "09_阿飞": "09_afei",
    "10_田坤": "10_tiankun", "11_无主": "11_wuzhu",
}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def mime(path):
    return subprocess.run(["file", "-b", "--mime-type", path],
                          capture_output=True, text=True).stdout.strip()


def main():
    os.makedirs(ASSETS, exist_ok=True)
    masters = sorted(f for f in os.listdir(DIR)
                     if re.match(r"^\d{2}_.+\_(portrait|turnaround)\.png$", f))
    n_png = n_site = 0
    for f in masters:
        src = os.path.join(DIR, f)
        # 1. 规范为真 PNG
        if mime(src) != "image/png":
            tmp = src + ".tmp.png"
            sh(["sips", "-s", "format", "png", src, "--out", tmp])
            os.replace(tmp, src)
            print(f"  转为真 PNG: {f}")
        # 2. 压缩版
        stem = f[:-4]                                   # NN_中文_kind
        base, kind = stem.rsplit("_", 1)
        en = ASCII.get(base)
        if not en:
            print(f"  ⚠️ 无 ASCII 映射，跳过 {f}")
            continue
        out = os.path.join(ASSETS, f"{en}_{kind}.jpg")
        size = 760 if kind == "portrait" else 1400
        sh(["sips", "-Z", str(size), src, "--out", out,
            "-s", "format", "jpeg", "-s", "formatOptions", "72"])
        n_png += 1
        n_site += 1
    print(f"\n母版 PNG: {n_png} 张")
    total = sum(os.path.getsize(os.path.join(ASSETS, f)) for f in os.listdir(ASSETS))
    print(f"站点资源: {n_site} 张 / {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
