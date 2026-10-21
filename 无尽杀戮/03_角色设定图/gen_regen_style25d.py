#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《末世火葬工》角色图 2.5D 质感重做

问题：现有角色图是纯真人写实（照片级），与总案《七、视觉方案：2.5D 虚拟制片规范》
      的半写实 CG 角色层咬不上——参考图是真人味，AI 图生视频出来的也是真人味，
      与 2.5D 成片质感冲突。

做法：形象设计（脸型 / 服装 / 道具 / 骨纹）全部保留，只把**渲染质感**换成
      半写实 3D CG（Unreal 游戏过场动画风）：
        - 面部风格化：眼睛略放大、下颌柔化、鼻梁简化、皮肤光滑哑光无毛孔
        - 发型块面化：游戏渲染发片
        - 服装 PBR 材质：明确厚度与高光
        - 强轮廓光 + 体积光（CG 角色"有厚度"的关键视觉标记）
      三视图以新肖像作 input_urls 锁脸。

用法：
      python3 gen_regen_style25d.py 01 02      # 只做指定编号（肖像+三视图）
      python3 gen_regen_style25d.py all        # 全部 11 个
"""
import json, os, subprocess, sys

DIR = os.path.dirname(os.path.abspath(__file__))
TOOL = "connector__matrix__generate_image"

# ---------------------------------------------------------------- 风格
# 迭代记录：v1 写了「块面化／皮肤光滑无毛孔／不是照片」，模型直接理解成**低多边形手办**
#（硬边眉毛、塑料皮肤、玩具感）。v2 改为「高端游戏 CG 写实」：保留真实五官与肤质细节，
# 用渲染语言（次表面散射、轮廓光、体积光、PBR 布料）建立"这是 CG"而非靠"降低精度"建立。
PORTRAIT_STYLE = (
    "高端电影级 3D 角色渲染，high-end cinematic CGI character render，"
    "Unreal Engine 5 级别的人物渲染品质，游戏过场动画的高预算 CG 质感。"
    "五官比例写实清晰、面部轮廓自然，眼神有神；"
    "皮肤为高质量次表面散射渲染，保留自然肤质与轻微毛孔，皮肤不油不塑料。"
    "头发有清晰的丝缕结构与自然高光，不是硬块面。"
    "服装为 PBR 材质，有真实的布料纹理、自然褶皱与厚度，高光柔和有质感。"
    "三点柔光布光加一道清晰的亮色轮廓光勾出人物边缘，空气中悬浮体积光与灰尘颗粒。"
    "竖屏胸像构图，人物正面居中，占据画面主要区域。"
    "背景是废弃殡仪馆走廊：浅灰色墙面、锈蚀铁门、剥落的墙皮、天花板冷白面板灯，背景虚化。"
    "低饱和冷灰青色调，浅景深，画面干净锐利，有 CG 渲染特有的体积感与光质感。"
    "排除：低多边形低模，PS1 复古画质，塑料手办感，二维平面动画，日式动漫，赛博朋克霓虹，廉价游戏截图，真人照片"
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

# ---------------------------------------------------------------- 角色（形象设计沿用，仅换渲染质感）
CHARS = {
    "01": ("陈野", "一名26岁中国男性，殡仪馆遗体接运员，英俊清隽的东方男性面孔，"
                   "身高腿长，肩背挺拔，骨相分明，下颌线利落，眉形清朗，眼神锐利而沉静、"
                   "带着熬夜后的倦意但依然有神，是好看的那种瘦，短寸黑发干净利落，"
                   "穿一件洗得发旧但整洁的深灰色连体工装连衣裤，工装肩袖与胸口有石灰白污渍，"
                   "手背有洗不掉的灰白印痕，左掌心浮现一小片灰白色骨纹并透出微弱暖橙火光，"
                   "神情平静克制，带一点疏离的英俊，不凶狠不阴鸷，"
                   "脚上穿着一双黑色劳保工靴，鞋面完整可见"),
    "02": ("苏晓棠", "一名24岁中国女性，殡仪馆遗体修复师，清冷明艳的东方女性面孔，"
                     "五官精致立体，鹅蛋脸型，皮肤干净细腻，眼睛明亮有神，眼尾微微上挑，"
                     "神情温柔而带执念，长发在脑后束成低马尾，碎发自然垂落，"
                     "穿白色医用工装大褂，护目镜推在额头上、白色医用口罩已经拉到下巴以下，"
                     "完整露出整张脸，看得见鼻子、嘴唇和下颌线，"
                     "双手手背布满细密旧疤痕，指尖缠绕着医用缝合线头，"
                     "脚上穿着一双干净的白色平底护士鞋，鞋面完整可见"),
    "03": ("裴烈", "一名43岁中国男性，收骨人首领，极度整洁的纯白长款白大褂没有一丝褶皱，"
                   "内搭深色立领衬衣，黑发梳得一丝不苟，指甲修剪整齐，"
                   "面带克制浅笑，眼神冷静深不见底，干净体面到令人不适，"
                   "脚上穿着一双黑色系带皮鞋，鞋面完整可见"),
    "04": ("纪梵", "一名27岁中国男性，阴沉内敛的副手，五官端正近乎不像真人，"
                   "眉眼有细微的复制感违和，浅灰色高领内搭，"
                   "右脸颊有一道极浅的旧缝合痕迹，眼神藏着恐惧，面无表情，"
                   "脚上穿着一双深灰色系带皮靴，鞋面完整可见"),
    "05": ("陈远", "一名19岁中国男性，建筑系大一学生，与哥哥陈野有相似的下颌线和眉形，"
                   "清瘦但干净的少年脸，眼神干净偏执，黑色连帽卫衣，"
                   "肩上斜挎一只装建筑图纸的旧帆布包，掌心浮现微弱的共振波纹状灰光，"
                   "脚上穿着一双白色运动鞋，鞋面完整可见"),
    "06": ("赵岚", "一名32岁中国女性，收容局现场处置三队队长，深灰橄榄绿战术制服配战术腰带，"
                   "利落短发，眼神沉稳有压迫感，下颌线绷紧，肩线笔挺，站姿像一把出鞘的刀，"
                   "脚上穿着一双黑色系带战术靴，鞋面完整可见"),
    "07": ("骆红", "一名46岁中国女性，收容局局长，深炭灰职业套装，领口别一枚简洁金属胸针，"
                   "利落短卷发，目光疲惫务实，手指交叠在身前，"
                   "脚上穿着一双黑色低跟系带皮鞋，鞋面完整可见"),
    "08": ("老沈", "一名64岁中国男性，殡仪馆老馆长，花白短发，法令纹深刻，"
                   "穿一件洗得发白的旧藏青色中山装外套，手掌宽厚布满老茧与烫伤旧疤，"
                   "眼神温和沉静，脚上穿着一双黑色布鞋，鞋面完整可见"),
    "09": ("阿飞", "一名21岁中国男性，黑市掮客，乱蓬蓬的碎发，脏兮兮的连帽卫衣外套配工装裤，"
                   "耳后别着一支笔，眼神灵活带笑，痞气又有点紧张不安，"
                   "脚上穿着一双磨旧的运动鞋，鞋面完整可见"),
    "10": ("田坤", "一名34岁中国男性，货运司机，肩宽体壮，寸头，晒得黝黑的脸与络腮胡茬，"
                   "穿脏旧的藏蓝色工装夹克，小臂粗壮结实，眼神憨厚温和，"
                   "脚上穿着一双厚底工装靴，鞋面完整可见"),
    "11": ("无主", "一个非人角色，由白骨、灰烬与破碎记忆残片聚成的人形轮廓，骨白色没有五官，"
                   "胸腔空洞处透出微弱暖橙火光，周身漂浮灰烬与骨屑，身形修长，"
                   "保持 CG 渲染的体积感与骨体质感，不是真人"),
}


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def upload(path):
    out = sh(["mcode-tools", "upload_temp_url", path])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])["temp_url"]


def download(node_id, dest):
    out = sh(["mcode-tools", "get_asset_url", node_id])
    url = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
    subprocess.run(["curl", "-sL", url, "-o", dest], check=True)


def call(requests):
    p = os.path.join(DIR, "_s25d_args.json")
    with open(p, "w") as f:
        json.dump({"requests": requests}, f, ensure_ascii=False)
    out = sh(["mcode-tools", "connector", "call", TOOL, "--args-file", p])
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def run_batch(nums):
    # 第一轮：肖像（纯文生图）
    reqs = [{"prompt": f"{CHARS[n][1]}。{PORTRAIT_STYLE}",
             "aspect_ratio": "9:16", "resolution": "2K",
             "output_file": f"{n}_{CHARS[n][0]}_portrait.png"} for n in nums]
    res = call(reqs)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        download(it["node_id"], os.path.join(DIR, f"{base}.png"))
        print("  ↓", base)

    # 第二轮：三视图（用新肖像锁脸）
    reqs = []
    for n in nums:
        name = CHARS[n][0]
        ref = os.path.join(DIR, f"{n}_{name}_portrait.png")
        item = {"prompt": f"{CHARS[n][1]}。{TURNAROUND_STYLE}。{LOCK}",
                "aspect_ratio": "16:9", "resolution": "2K",
                "output_file": f"{n}_{name}_turnaround.png"}
        if os.path.exists(ref):
            item["input_urls"] = [upload(ref)]
        reqs.append(item)
    res = call(reqs)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for it in res.get("success_items", []):
        base = it["file_name"].rsplit(".", 1)[0]
        download(it["node_id"], os.path.join(DIR, f"{base}.png"))
        print("  ↓", base)


if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    nums = list(CHARS) if args == ["all"] else [a.zfill(2) for a in args]
    run_batch(nums)
