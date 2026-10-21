#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《末世火葬工》主角/女主角色图重做

改动：
  陈野   —— 原版偏干瘦憔悴，改「英俊清隽、好看的那种瘦」，骨相分明、下颌线利落
  苏晓棠 —— 原版口罩遮住鼻/口/下颌，改为「口罩拉到下巴」露出完整面部，五官更精致明艳
  陈远   —— 弟弟，需与新版陈野有相似下颌线（血缘锚点），用新版陈野肖像作 input_urls

用法：python3 gen_regen_leads.py
"""
import json, os, subprocess

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"

STYLE = ("电影级写实人物定妆照，竖屏构图，冷灰青调末日工业质感，柔和顶光加侧逆光，"
         "空气中悬浮细微灰尘颗粒，中国面孔，浅景深，高细节皮肤纹理与布料质感，"
         "人物正面胸像居中，背景为模糊的废弃殡仪馆走廊与锈蚀铁门，"
         "无文字无水印无标语")

TA_STYLE = ("角色设定稿三视图（character turnaround sheet），纯白无缝摄影棚背景，"
            "同一个角色的正面全身、四分之三侧面全身、背面全身，三个完整人体视图等高并排，"
            "身高一致、头高一致、间距均匀，人物完全相同——同一张脸、同一发型、同一套服装与配色，"
            "中性站姿，双臂自然微张，均匀柔和的白色影棚布光，无强烈阴影，"
            "只有脚下极淡的接地阴影。写实摄影质感，真实皮肤与布料纹理，"
            "不是插画，不是漫画，不是游戏设定稿，无文字无标注无尺寸线无水印无边框")

LOCK = ("参考图是这个角色本人的定妆照片，请严格保持同一张脸、同一五官比例、同一发型、"
        "同一套服装与配色，不要改变人物长相，不要把参考图的背景带进来。")

CHENYE = ("一名26岁中国男性，殡仪馆遗体接运员，**英俊清隽的东方男性面孔**，身高腿长，肩背挺拔，"
          "骨相分明，下颌线利落清晰，眉形清朗，眼神锐利而沉静、带着熬夜后的倦意但依然有神，"
          "**是好看的那种瘦，不是消瘦憔悴**，短寸黑发干净利落，"
          "穿一件洗得发旧但整洁的深灰色连体工装连衣裤，工装肩袖与胸口有石灰白污渍，"
          "手背有洗不掉的灰白印痕，左掌心浮现一小片灰白色骨纹并透出微弱暖橙火光，"
          "神情平静克制，带一点疏离的英俊，不凶狠不阴鸷")

SUXIAOTANG = ("一名24岁中国女性，殡仪馆遗体修复师，**清冷明艳的东方女性面孔**，"
               "五官精致立体，鹅蛋脸型，皮肤干净细腻，眼睛明亮有神，眼尾微微上挑，"
               "神情温柔而带执念，长发在脑后束成低马尾，碎发自然垂落，"
               "穿白色医用工装大褂，**护目镜推在额头上、白色医用口罩已经拉到下巴以下，完整露出整张脸，"
               "看得见鼻子、嘴唇和下颌线**，双手手背布满细密旧疤痕，指尖缠绕着医用缝合线头")

CHENYUAN = ("一名19岁中国男性，建筑系大一学生，**与哥哥陈野有相似的下颌线和眉形**，"
            "清瘦但干净的少年脸，眼神干净偏执，黑色连帽卫衣，"
            "肩上斜挎一只装建筑图纸的旧帆布包，掌心浮现微弱的共振波纹状灰光")

# (输出名, prompt, aspect, resolution, 参考图本地路径或 None)
JOBS = [
    ("01_陈野_portrait",      CHENYE,     "9:16", "2K", None),
    ("02_苏晓棠_portrait",    SUXIAOTANG, "9:16", "2K", None),
    ("01_陈野_turnaround",    CHENYE,     "16:9", "2K", "01_陈野_portrait.png"),
    ("02_苏晓棠_turnaround",  SUXIAOTANG, "16:9", "2K", "02_苏晓棠_portrait.png"),
    ("05_陈远_portrait",      CHENYUAN,   "9:16", "2K", "01_陈野_portrait.png"),
    ("05_陈远_turnaround",    CHENYUAN,   "16:9", "2K", "05_陈远_portrait.png"),
]


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout


def upload(path):
    out = sh(["mcode-tools", "upload_temp_url", path])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])["temp_url"]


def download(node_id, dest):
    out = sh(["mcode-tools", "get_asset_url", node_id])
    url = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
    subprocess.run(["curl", "-sL", url, "-o", dest], check=True)


def call(requests):
    p = os.path.join(DIR, "_regen_args.json")
    with open(p, "w") as f:
        json.dump({"requests": requests}, f, ensure_ascii=False)
    out = sh(["mcode-tools", "connector", "call", TOOL, "--args-file", p])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def main():
    # 第一轮：两张新肖像
    res = call([{"prompt": f"{p}。{STYLE}", "aspect_ratio": ar, "resolution": rs,
                 "output_file": f"{out}.png"}
                for out, p, ar, rs, _ in JOBS if out.endswith("portrait")
                and out in ("01_陈野_portrait", "02_苏晓棠_portrait")])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        download(it["node_id"], os.path.join(DIR, f"{base}.png"))
        print("  ↓", base)

    # 第二轮：三视图 + 陈远肖像（依赖上一轮产出）
    reqs = []
    for out, p, ar, rs, ref in JOBS:
        if out in ("01_陈野_portrait", "02_苏晓棠_portrait"):
            continue
        ref_path = os.path.join(DIR, ref)
        item = {"prompt": f"{p}。{TA_STYLE if ar == '16:9' else STYLE}。{LOCK}",
                "aspect_ratio": ar, "resolution": rs, "output_file": f"{out}.png"}
        if os.path.exists(ref_path):
            item["input_urls"] = [upload(ref_path)]
        reqs.append(item)

    res2 = call(reqs)
    print(json.dumps(res2, ensure_ascii=False, indent=1))
    for it in res2.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        download(it["node_id"], os.path.join(DIR, f"{base}.png"))
        print("  ↓", base)


if __name__ == "__main__":
    main()
