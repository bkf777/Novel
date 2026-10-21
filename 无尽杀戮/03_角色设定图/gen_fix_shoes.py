#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐女角色三视图的鞋履细节

问题：三视图 prompt 未指定鞋款，模型给苏晓棠/赵岚/骆红 生成了赤脚，
      但角色设定稿是给服装组/道具组用的，鞋必须明确。

做法：以各自肖像作 input_urls 锁脸，重出三视图，prompt 里写死鞋款。
"""
import json, os, subprocess

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"

TA_STYLE = ("角色设定稿三视图（character turnaround sheet），纯白无缝摄影棚背景，"
            "同一个角色的正面全身、四分之三侧面全身、背面全身，三个完整人体视图等高并排，"
            "身高一致、头高一致、间距均匀，人物完全相同——同一张脸、同一发型、同一套服装与鞋，"
            "中性站姿，双臂自然微张，均匀柔和的白色影棚布光，无强烈阴影，"
            "只有脚下极淡的接地阴影。写实摄影质感，真实皮肤与布料纹理，"
            "不是插画，不是漫画，不是游戏设定稿，无文字无标注无尺寸线无水印无边框")

LOCK = ("参考图是这个角色本人的定妆照片，请严格保持同一张脸、同一五官比例、同一发型、"
        "同一套服装与配色，不要改变人物长相，不要把参考图的背景带进来。")

JOBS = [
    ("02_苏晓棠_turnaround",
     "一名24岁中国女性，遗体修复师，清冷明艳的东方女性面孔，五官精致立体，鹅蛋脸型，"
     "皮肤干净细腻，眼睛明亮有神，眼尾微微上挑，长发在脑后束成低马尾，"
     "穿白色医用工装大褂，护目镜推在额头上、白色医用口罩已经拉到下巴以下露出完整的脸，"
     "双手手背布满细密旧疤痕，指尖缠绕着医用缝合线头，"
     "脚上穿着一双干净的白色平底护士鞋，鞋面完整可见",
     "02_苏晓棠_portrait.png"),

    ("06_赵岚_turnaround",
     "一名32岁中国女性，收容局现场处置三队队长，深灰橄榄绿战术制服配战术腰带，"
     "利落短发，眼神沉稳有压迫感，下颌线绷紧，肩线笔挺，"
     "脚上穿着一双黑色系带战术靴，鞋面完整可见",
     "06_赵岚_portrait.png"),

    ("07_骆红_turnaround",
     "一名46岁中国女性，收容局局长，深炭灰职业套装，领口别一枚简洁金属胸针，利落短卷发，"
     "目光疲惫务实，"
     "脚上穿着一双黑色低跟系带皮鞋，鞋面完整可见",
     "07_骆红_portrait.png"),
]


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def upload(path):
    out = sh(["mcode-tools", "upload_temp_url", path])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])["temp_url"]


def download(node_id, dest):
    out = sh(["mcode-tools", "get_asset_url", node_id])
    url = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
    subprocess.run(["curl", "-sL", url, "-o", dest], check=True)


def main():
    reqs = []
    for out, desc, ref in JOBS:
        ref_path = os.path.join(DIR, ref)
        reqs.append({
            "prompt": f"{desc}。{TA_STYLE}。{LOCK}",
            "aspect_ratio": "16:9", "resolution": "2K",
            "input_urls": [upload(ref_path)],
            "output_file": f"{out}.png",
        })

    p = os.path.join(DIR, "_shoes_args.json")
    with open(p, "w") as f:
        json.dump({"requests": reqs}, f, ensure_ascii=False)
    out = sh(["mcode-tools", "connector", "call", TOOL, "--args-file", p])
    res = json.loads(out[out.find("{"):out.rfind("}") + 1])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        download(it["node_id"], os.path.join(DIR, f"{base}.png"))
        print("  ↓", base)


if __name__ == "__main__":
    main()
