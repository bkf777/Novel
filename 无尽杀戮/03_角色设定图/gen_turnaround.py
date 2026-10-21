#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《末世火葬工》角色三视图（turnaround）生成

链路：mcode-tools connector call connector__matrix__generate_image
  - input_urls 传入该角色的定妆肖像（先 upload_temp_url 换临时 URL）→ 锁脸
  - 纯白无缝影棚背景 → 不污染后续场景合成
  - 16:9 横版三视图（正面 / 四分之三侧 / 背面），与同工作区《注销通知》手稿/人物图 的规格对齐

用法：python3 gen_turnaround.py            # 全部
      python3 gen_turnaround.py 01 03      # 只跑指定编号
"""
import json, subprocess, sys, os

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"

# 角色外貌描述（与 01_短剧策划/02_短剧人物设定档案.md 对齐）
CHARS = {
    "01": ("陈野", "26岁中国男性，遗体接运员，瘦高身形，短寸黑发，穿洗得发旧的深灰色连体工装连衣裤，"
                   "工装肩袖与胸口有石灰白污渍，手背有洗不掉的灰白印痕，左掌心有一小片灰白色骨纹并透出微弱暖橙火光，"
                   "面容疲惫脱敏，眼睑下垂"),
    "02": ("苏晓棠", "24岁中国女性，遗体修复师，长发在脑后束成低马尾，穿白色医用工装大褂，"
                     "护目镜推在额头上，下半张脸戴白色口罩，双手手背布满细密旧疤痕，指尖缠着医用缝合线头，"
                     "眼神温柔专注"),
    "03": ("裴烈", "43岁中国男性，收骨人首领，极干净整洁，穿纯白长款白大褂内搭深色立领衬衣，"
                   "黑发梳得一丝不苟，指甲修剪整齐，面带克制浅笑，眼神冷静深不见底"),
    "04": ("纪梵", "27岁中国男性，副手，浅灰色高领内搭，五官端正近乎不像真人，"
                   "右脸颊有一道极浅的旧缝合痕迹，神情阴郁面无表情"),
    "05": ("陈远", "19岁中国男性，建筑系大一学生，清瘦，黑色连帽卫衣配深色长裤，"
                   "肩上斜挎一只装建筑图纸的旧帆布包，眼神干净偏执"),
    "06": ("赵岚", "32岁中国女性，收容局现场处置三队队长，穿深灰橄榄绿战术制服配战术腰带，"
                   "利落短发，眼神沉稳有压迫感，下颌线绷紧，肩线笔挺"),
    "07": ("骆红", "46岁中国女性，收容局局长，穿深炭灰职业套装，领口别一枚简洁金属胸针，"
                   "利落短卷发，目光疲惫务实"),
    "08": ("老沈", "64岁中国男性，殡仪馆老馆长，花白短发，法令纹深刻，"
                   "穿一件洗得发白的旧藏青色中山装外套，手掌宽厚布满老茧与烫伤旧疤，眼神温和沉静"),
    "09": ("阿飞", "21岁中国男性，黑市掮客，乱蓬蓬的碎发，穿脏兮兮的连帽卫衣外套配工装裤，"
                   "耳后别着一支笔，眼神灵活带笑，痞气又有点紧张不安"),
    "10": ("田坤", "34岁中国男性，货运司机，肩宽体壮，寸头，晒得黝黑的脸与络腮胡茬，"
                   "穿脏旧的藏蓝色工装夹克，小臂粗壮，眼神憨厚温和"),
    "11": ("无主", "一个非人角色，由白骨、灰烬与破碎记忆残片聚成的人形轮廓，骨白色没有五官，"
                   "胸腔空洞处透出微弱暖橙火光，周身漂浮灰烬与骨屑，身形修长"),
}

STYLE = ("角色设定稿三视图（character turnaround sheet），纯白无缝摄影棚背景，"
         "同一个角色的正面全身、四分之三侧面全身、背面全身，三个完整人体视图等高并排，"
         "身高一致、头高一致、间距均匀，人物完全相同——同一张脸、同一发型、同一套服装与配色，"
         "中性站姿，双臂自然微张，均匀柔和的白色影棚布光，无强烈阴影，"
         "只有脚下极淡的接地阴影。写实摄影质感，真实皮肤与布料纹理，"
         "不是插画，不是漫画，不是游戏设定稿，无文字无标注无尺寸线无水印无边框")

LOCK = ("参考图是这个角色本人的定妆照片，请严格保持同一张脸、同一五官比例、同一发型、同一套服装与配色，"
        "不要改变人物长相，不要把参考图的背景带进来。")


def run(args, timeout=900):
    p = os.path.join(DIR, "_args_tmp.json")
    with open(p, "w") as f:
        json.dump(args, f, ensure_ascii=False)
    r = subprocess.run(["mcode-tools", "connector", "call", TOOL, "--args-file", p],
                       capture_output=True, text=True, timeout=timeout)
    out = r.stdout
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def upload(path):
    r = subprocess.run(["mcode-tools", "upload_temp_url", path], capture_output=True, text=True)
    out = r.stdout
    return json.loads(out[out.find("{"):out.rfind("}") + 1])["temp_url"]


def main():
    only = set(sys.argv[1:])
    reqs = []
    for num, (name, desc) in CHARS.items():
        if only and num not in only:
            continue
        portrait = os.path.join(DIR, f"{num}_{name}_portrait.png")
        if not os.path.exists(portrait):
            print(f"⚠️ 缺肖像，跳过 {num}_{name}")
            continue
        url = upload(portrait)
        reqs.append({
            "prompt": f"{STYLE}。角色设定：{desc}。{LOCK}",
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "input_urls": [url],
            "output_file": f"{num}_{name}_turnaround.png",
        })

    if not reqs:
        print("无可生成项")
        return
    res = run({"requests": reqs})
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
