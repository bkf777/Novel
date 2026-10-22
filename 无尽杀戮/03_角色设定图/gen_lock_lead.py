#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《末世火葬工》陈野定稿（选定方向 A · 清冷少年感）+ 陈远血缘脸同步

A 方向选定后需修两处：
  1. 掌心骨纹被画成**悬浮在掌心之上的立体金属符文** → 改成长在皮肤表面的平面骨纹（B 方向是对的）
  2. 工装污渍跑偏成**绿色苔藓** → 设定是干燥结块的灰白石灰粉

做法：图生图定点修（input_urls 传入候选 A，锁住脸/发型/姿态/服装/场景，只改手纹与污渍）
     → 定稿肖像 → 三视图（用定稿肖像锁脸）→ 陈远（用定稿陈野锁血缘脸）→ 陈远三视图

用法：python3 gen_lock_lead.py
"""
import json, os, subprocess

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"
CAND = os.path.join(DIR, "陈野候选_A_清冷少年感.png")

# ---------------------------------------------------------------- 风格（沿用已通过质检的 2.5D CG 版）
STYLE = (
    "高端电影级 3D 角色渲染，high-end cinematic CGI character render，"
    "Unreal Engine 5 级别的人物渲染品质，游戏过场动画的高预算 CG 质感。"
    "五官比例写实清晰、面部轮廓自然，眼神明亮有神；"
    "皮肤为高质量次表面散射渲染，保留自然肤质与轻微毛孔，"
    "皮肤干净不油不塑料，没有黑眼圈没有胡茬没有法令纹。"
    "头发有清晰的丝缕结构与自然高光，不是硬块面。"
    "服装为 PBR 材质，有真实的布料纹理、自然褶皱与厚度，高光柔和有质感。"
    "三点柔光布光加一道清晰的亮色轮廓光勾出人物边缘，空气中悬浮体积光与灰尘颗粒。"
    "竖屏全身构图，人物正面居中，占据画面主要区域。"
    "背景是废弃殡仪馆走廊：浅灰色墙面、锈蚀铁门、剥落的墙皮、天花板冷白面板灯，背景虚化。"
    "低饱和冷灰青色调，浅景深，画面干净锐利，有 CG 渲染特有的体积感与光质感。"
    "排除：低多边形低模，PS1 复古画质，塑料手办感，二维平面动画，日式动漫，赛博朋克霓虹，廉价游戏截图，真人照片，"
    "阴鸷狠戾的表情，阴沉反派气质，方腮，浓眉压眼，过深的法令纹，络腮胡，胡茬，黑眼圈，疲惫憔悴感"
)

TURNAROUND_STYLE = (
    "角色设定稿三视图（character turnaround sheet），高端电影级 3D 角色渲染，"
    "high-end cinematic CGI character render，纯白无缝影棚背景。"
    "同一个角色的正面全身、四分之三侧面全身、背面全身，三个完整人体视图等高并排，"
    "身高一致、头高一致、间距均匀，人物完全相同——同一张脸、同一发型、同一套服装与鞋。"
    "中性站姿，双臂自然微张，均匀柔和的白色影棚布光加一道清晰的轮廓光，无强烈阴影，"
    "只有脚下极淡的接地阴影。保留 CG 渲染的体积感、材质厚度与真实的布料纹理，"
    "皮肤为高质量次表面散射渲染，五官写实清晰。"
    "排除：低多边形低模，PS1 复古画质，塑料手办感，二维平面动画，无文字无标注无尺寸线无水印"
)

LOCK = ("参考图是这个角色本人的定妆渲染图，请严格保持同一张脸、同一五官比例、同一发型、"
        "同一套服装与配色、同一种 CG 渲染质感，不要改变人物长相与风格，不要把参考图的背景带进来。")

# 骨纹与污渍的固定描述（定稿后所有素材沿用）
BONE = ("左掌心皮肤表层浮现一小片灰白色骨纹，像骨头内部的细密骨缝线，"
        "是长在皮肤表面的平面纹路，线条短促收在掌心中央，透出极微弱的暖橙余烬光；"
        "五指完整自然张开，手型正常")
STAIN = "工装肩袖与胸口沾着干燥结块的灰白色石灰粉末，泛白偏灰"

EDIT = (
    "严格保持参考图中这位男性的面部、发型、姿态、服装款式与场景完全不变。"
    "只做两处修改："
    "第一，去掉左掌心上那个悬浮在掌心之上的立体金属符文，"
    "改为长在掌心皮肤表面的一小片平面的灰白色骨纹，像骨头内部的细密骨缝线，"
    "线条短促收在掌心中央，透出极微弱的暖橙余烬光，不要任何悬浮的立体物体；"
    "五指完整自然张开。"
    "第二，把工装上的绿色苔藓状污渍改为干燥结块的灰白色石灰粉末，泛白偏灰。"
    "其余一切保持不变。"
)

CHENYE = (
    "一名26岁中国男性，殡仪馆遗体接运员，清冷系少年感的长相，非常帅："
    "脸型偏窄偏鹅蛋，轮廓干净不带攻击性，眼睛大而清澈有神、眼神柔和却专注，睫毛清晰，"
    "眉形清秀舒展不浓重，唇形精致清晰、下颌线流畅圆润不方，颧骨与下颌自然衔接，"
    "介于少年与青年之间的气质，干净、克制、带一点恋爱感。"
    "身高腿长，肩背挺拔，穿一件洗得发旧但整洁的深灰色连体工装连衣裤，"
    f"{STAIN}，手背有洗不掉的灰白印痕，{BONE}，"
    "神情平静克制、疏离但不阴沉，脚上穿着一双黑色劳保工靴，鞋面完整可见"
)

CHENYUAN = (
    "一名19岁中国男性，建筑系大一学生，**与参考图中的哥哥陈野有相似的下颌线、眉形和眼睛形状**，"
    "但更年轻更清瘦，五官还带少年的圆润，眼神干净偏执，黑色连帽卫衣，"
    "肩上斜挎一只装建筑图纸的旧帆布包，掌心浮现微弱的共振波纹状灰光，"
    "脚上穿着一双白色运动鞋，鞋面完整可见"
)


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def upload(path):
    out = sh(["mcode-tools", "upload_temp_url", path])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])["temp_url"]


def download(node_id, dest):
    out = sh(["mcode-tools", "get_asset_url", node_id])
    url = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
    subprocess.run(["curl", "-sL", url, "-o", dest], check=True)


def call(reqs, tag):
    p = os.path.join(DIR, f"_{tag}.json")
    with open(p, "w") as f:
        json.dump({"requests": reqs}, f, ensure_ascii=False)
    out = sh(["mcode-tools", "connector", "call", TOOL, "--args-file", p])
    res = json.loads(out[out.find("{"):out.rfind("}") + 1])
    print(f"--- {tag} ---")
    print(json.dumps({k: res.get(k) for k in ("summary", "total_success", "total_failed")}, ensure_ascii=False))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        dest = os.path.join(DIR, f"{base}.png")
        download(it["node_id"], dest)
        print("  ↓", os.path.basename(dest))
    for it in res.get("failed_items", []):
        print("  ✗", it)
    return res


def main():
    # 1) 定点修 A：骨纹 + 污渍
    call([{"prompt": EDIT, "aspect_ratio": "9:16", "resolution": "2K",
           "input_urls": [upload(CAND)], "output_file": "01_陈野_portrait.png"}], "lock1")

    # 2) 陈野三视图（用定稿肖像锁脸）
    call([{"prompt": f"{CHENYE}。{TURNAROUND_STYLE}。{LOCK}", "aspect_ratio": "16:9", "resolution": "2K",
           "input_urls": [upload(os.path.join(DIR, "01_陈野_portrait.png"))],
           "output_file": "01_陈野_turnaround.png"}], "lock2")

    # 3) 陈远（用定稿陈野锁血缘脸）
    call([{"prompt": f"{CHENYUAN}。{STYLE}", "aspect_ratio": "9:16", "resolution": "2K",
           "input_urls": [upload(os.path.join(DIR, "01_陈野_portrait.png"))],
           "output_file": "05_陈远_portrait.png"}], "lock3")

    # 4) 陈远三视图
    call([{"prompt": f"{CHENYUAN}。{TURNAROUND_STYLE}。{LOCK}", "aspect_ratio": "16:9", "resolution": "2K",
           "input_urls": [upload(os.path.join(DIR, "05_陈远_portrait.png"))],
           "output_file": "05_陈远_turnaround.png"}], "lock4")


if __name__ == "__main__":
    main()
