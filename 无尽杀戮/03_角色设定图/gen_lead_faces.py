#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《末世火葬工》陈野男主脸候选 — 3 个方向，供选角

问题诊断（v2 2.5D 版）：
  - 「骨相分明 + 眼神锐利」被模型推过头 → 眉压眼、方腮、唇线紧 → 阴鸷硬汉脸 / 反派感
  - 掌心骨纹被画成爪状血管纹，顺着手指延伸 → 观感怪异（这是"丑"的最大来源之一）
  - 短剧男主要的是「苏感」：清冷、干净、有恋爱感，而不是狠

本脚本出 3 个方向（均为 2.5D CG 质感 + 修好的骨纹 + 深灰工装 + 殡仪馆走廊）：
  A 清冷少年感   —— 肖战/成毅式，窄脸大眼，少年感
  B 温润疏朗     —— 李现/张若昀式，柔和有故事感，有少年气
  C 硬朗干净     —— 朱一龙式，深邃立体但干净可靠，不阴鸷

用法：python3 gen_lead_faces.py
"""
import json, os, subprocess

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"

# 2.5D CG 渲染语言（沿用已通过质检的 v2 版本）
STYLE = (
    "高端电影级 3D 角色渲染，high-end cinematic CGI character render，"
    "Unreal Engine 5 级别的人物渲染品质，游戏过场动画的高预算 CG 质感。"
    "五官比例写实清晰、面部轮廓自然，眼神明亮有神；"
    "皮肤为高质量次表面散射渲染，保留自然肤质与轻微毛孔，皮肤干净不油不塑料，没有黑眼圈没有胡茬没有法令纹。"
    "头发有清晰的丝缕结构与自然高光，不是硬块面。"
    "服装为 PBR 材质，有真实的布料纹理、自然褶皱与厚度，高光柔和有质感。"
    "三点柔光布光加一道清晰的亮色轮廓光勾出人物边缘，空气中悬浮体积光与灰尘颗粒。"
    "竖屏胸像构图，人物正面居中，占据画面主要区域。"
    "背景是废弃殡仪馆走廊：浅灰色墙面、锈蚀铁门、剥落的墙皮、天花板冷白面板灯，背景虚化。"
    "低饱和冷灰青色调，浅景深，画面干净锐利，有 CG 渲染特有的体积感与光质感。"
    "排除：低多边形低模，PS1 复古画质，塑料手办感，二维平面动画，日式动漫，赛博朋克霓虹，廉价游戏截图，真人照片，"
    "阴鸷狠戾的表情，阴沉反派气质，方腮，浓眉压眼，过深的法令纹，络腮胡，胡茬，黑眼圈，疲惫憔悴感"
)

# 骨纹修正：简洁几何骨纹，**不延伸到手指**
BONE = (
    "左掌心有一小片简洁的灰白色骨纹符号，是抽象的几何骨节纹样，"
    "线条清晰短促、收在掌心范围内，**不向手指延伸、不形成爪状或血管状的纹路**，"
    "纹样内部透出微弱的暖橙火光；"
    "手型正常，五指清晰完整自然张开"
)

# 共同设定
COMMON = (
    "一名26岁中国男性，殡仪馆遗体接运员，"
    "身高腿长，肩背挺拔，站姿放松但不佝偻，"
    "穿一件洗得发旧但整洁的深灰色连体工装连衣裤，工装肩袖与胸口有石灰白污渍，"
    "手背有洗不掉的灰白印痕，"
    "神情平静克制、疏离但不阴沉，嘴角不带笑也不带敌意，"
    "脚上穿着一双黑色劳保工靴，鞋面完整可见"
)

FACES = {
    "A_清冷少年感": (
        "清冷系少年感的长相，**非常帅**：脸型偏窄偏鹅蛋，轮廓干净不带攻击性，"
        "眼睛大而清澈有神、眼神柔和却专注，睫毛清晰，瞳色自然深棕，"
        "眉形清秀舒展不浓重，唇形精致清晰、下颌线流畅圆润不方，"
        "颧骨与下颌自然衔接，介于少年与青年之间的气质，干净、克制、带一点恋爱感"
    ),
    "B_温润疏朗": (
        "温润疏朗的长相，**非常帅**：轮廓清晰但线条柔和，"
        "眉骨立体、眼神温和有故事感、眼尾略长显得含蓄，"
        "鼻梁挺而不尖，唇线柔和自然，笑意若隐若现显少年气，"
        "下颌线清晰但不过分方阔，脸型端正饱满，"
        "整体给人「可靠、温柔、值得托付」的气质"
    ),
    "C_硬朗干净": (
        "硬朗但干净的长相，**非常帅**：骨相分明，五官深邃立体，"
        "眉眼锋利但眼神是正向的自信而非阴鸷，鼻梁高挺，"
        "唇形厚实利落，下颌线立体有型却不粗犷，脸型方正偏长，"
        "短寸发干净利落，气质是沉稳可靠的年轻男人——"
        "有攻击性的五官但没有敌意，是能扛事的那种帅，不是反派"
    ),
}

WARN = "（手部特写要清晰正常：五指完整、自然张开、无畸形无多余指节）"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def download(node_id, dest):
    out = sh(["mcode-tools", "get_asset_url", node_id])
    url = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
    subprocess.run(["curl", "-sL", url, "-o", dest], check=True)


def main():
    reqs = []
    for key, face in FACES.items():
        prompt = f"{COMMON}。{face}。{BONE}。{WARN}。{STYLE}"
        reqs.append({
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "resolution": "2K",
            "output_file": f"陈野候选_{key}.png",
        })

    p = os.path.join(DIR, "_face_args.json")
    with open(p, "w") as f:
        json.dump({"requests": reqs}, f, ensure_ascii=False)
    out = sh(["mcode-tools", "connector", "call", TOOL, "--args-file", p])
    res = json.loads(out[out.find("{"):out.rfind("}") + 1])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        dest = os.path.join(DIR, f"{base}.png")
        download(it["node_id"], dest)
        print("  ↓", os.path.basename(dest))


if __name__ == "__main__":
    main()
