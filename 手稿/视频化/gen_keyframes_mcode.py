#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《注销通知》竖屏短剧版 · 关键帧生成（mcode / matrix generate_image）

为什么换成 mcode 而不是本地 ComfyUI —— 2026-10-16 实测：
  耗时    31–41 秒/张  vs  本地 420 秒/张   （快 10×）
  分辨率  1536×2752 2K  vs  本地 832×1472   （3.5× 像素）
  画幅    原生 9:16    vs  本地手算 0.5652
  中文    一字不差      vs  本地 Qwen-Image 预计乱码
  锁脸    input_urls 验证通过（沈砚三视图 → C02 一致）

产出 14 张：10 个片段各 1 张首帧 + 4 个 FL2VA 双锚段各 1 张尾帧
  FL2VA 段：C01 / C05 / C07 / C10

用法：python3 gen_keyframes_mcode.py
"""
import json, subprocess, sys, os, time

CHAR = "/Users/ezreal/projects/小说创作/手稿/人物图"
OUT = "/Users/ezreal/projects/小说创作/手稿/视频化/关键帧"
os.makedirs(OUT, exist_ok=True)

# ---------------- 参考图（先上传拿 temp_url）----------------
REFS = {
    "SY": os.path.join(CHAR, "01_沈砚_turnaround.png"),   # 纯白棚拍三视图，不污染背景
    "CS": os.path.join(CHAR, "07_陈素芬_portrait.png"),
    "DAUGHTER": os.path.join(CHAR, "12_陈素芬之女_portrait.png"),
}

ROOM = ("背景是一间封闭狭小的注销间：浅灰色墙面，天花板两盏冷白面板灯，"
        "一张金属桌，两把不锈钢椅，墙上没有窗没有海报，房间很小很安静，背景空无一人。")
OFFICE = ("背景是一间普通机关的开放式办公室：成排的灰色办公桌，每张桌上有一台显示器，"
          "天花板长条冷白灯管，远处几张空桌，浅灰色地板，没有服务台，没有排队的人群。")
DARK = "背景是一间灯光很暗的办公室，只有电脑屏幕的冷白光从下方照亮人脸，远处隐约有办公桌和顶灯的轮廓。"
STYLE = ("竖屏电影感剧照，冷白色顶灯，浅灰蓝低饱和色调，写实电影摄影，浅景深，眼平机位，"
         "真实皮肤质感。画面为 9:16 竖构图。")
# 取景句不再写死在 STYLE 里：2026-10-16 发现 C05/C06/C07_end/C08 是纯屏幕特写、
# C05_end/C10_end 是手部特写，硬带"人物占据画面上方三分之二"会让模型凭空加人。
# 有人的帧各自已写明取景，这里只保留公共氛围与竖构图。
CORRIDOR = ("这是一段昏暗的医院走廊：浅灰色墙面，灰色钢门带一小片铁丝玻璃，墙上装着防撞扶手，"
            "天花板冷白面板灯，走廊很长很空，背景空无一人。")
SY = ("44岁中国男性，清瘦身形，黑色立领制式外套偏大肩线塌落，胸前别着工牌，"
      "眼下有洗不掉的青灰色倦意，左眉尾一道极淡旧疤，短黑发两鬓微白，双手戴黑色薄款手套，坐姿极直。")
CS = ("82岁中国女性，短银白头发，深藏青色羊毛外套内搭浅色衬衣，双手捧着一只白色纸杯，"
      "皮肤比周围真人略去饱和，轮廓边缘有一层极细的颗粒微光。")
SCREEN = ("屏幕底色为纯黑，显示清晰锐利的浅白色等宽中文，字体笔画锐利，没有模糊、没有错别字、"
          "没有乱码字符。屏幕玻璃有一层极轻微的反光和一道细微划痕。画面除屏幕外全部是纯黑。")
SY_REF_NOTE = ("参考图是同一个44岁中国男性角色的三视图设定稿（正面、侧面、背面），"
               "三个人是同一个人的三个角度。画面中只能出现一个人，不是一个人，不出现三个人并排，"
               "不是角色设定表。")


def upload(path):
    out = subprocess.run(["mcode-tools", "upload_temp_url", path],
                         capture_output=True, text=True).stdout
    raw = out[out.find("{"):out.rfind("}") + 1]
    return json.loads(raw)["temp_url"]


def call(tool, args):
    p = "/tmp/_mk_args.json"
    with open(p, "w") as f:
        json.dump(args, f, ensure_ascii=False)
    out = subprocess.run(["mcode-tools", "connector", "call", tool, "--args-file", p],
                         capture_output=True, text=True).stdout
    raw = out[out.find("{"):out.rfind("}") + 1]
    return json.loads(raw)


# ---------------- 14 张关键帧定义 ----------------
def frames(u):
    R = u["SY"]
    return [
        # ===== 第 1 集 =====
        dict(name="C01_first", out="C01_first", ref="CS",
             prompt=STYLE + "画面上方三分之二是这位82岁中国女性的正面特写：" + CS +
                     "她抬眼直视镜头，神情平静，没有求生的表情。" + ROOM),
        dict(name="C01_end", out="C01_end", ref="DAUGHTER",
             prompt=STYLE + "极低机位仰拍，一个三十岁左右的中国女性蹲坐在走廊地面上，背靠浅灰色墙壁，"
                     "双膝曲起，长款黑色羽绒服外套，头发被雨打湿贴在脸侧，脸色苍白疲惫，眼下有哭过的红血丝，"
                     "黑色长裤，膝盖处有一块暗紫色淤青。她抬头望向画外，眼神绝望但克制，没有开口说话。"
                     "人物占据画面上方三分之二，镜头贴近地面从下往上拍。" + CORRIDOR),
        dict(name="C02_first", out="C02_first", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "画面上方三分之二是这位44岁中国男性坐在金属桌前的正侧面中景，"
                     "他面朝画面右侧。他右手握一支笔，笔尖悬在桌角斜置的记录板上方约两厘米处，完全静止。"
                     "桌面上有一张空白纸。" + ROOM),
        dict(name="C03_first", out="C03_first", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "标准的胸像正面特写，肩部被画面下边缘切掉，"
                     "头顶到画面顶部留出正常的头部空间，人物大小与房间的空间比例正确，"
                     "不是一个被放大的头部贴在背景上。"
                     "这位44岁中国男性正开口说话，嘴唇微张，表情平直没有起伏。"
                     "他穿着黑色立领制式外套，胸前别着一张白色工牌，戴黑色薄款手套。"
                     "浅景深，他的脸清晰，身后的注销间和一台虚化的电脑屏幕被强烈虚化成一片模糊的冷白色块。"
                     + ROOM),
        dict(name="C04_first", out="C04_first", ref="CS",
             prompt=STYLE + "画面上方三分之二是这位82岁中国女性的正面中景：" + CS +
                     "她低头用拇指沿杯口慢慢擦拭，肩膀完全不动。" + ROOM),
        dict(name="C05_first", out="C05_first", ref=None,
             prompt=STYLE + "画面是一台现代扁平液晶显示器的极近距离正面特写，镜头与屏幕中心齐平、正视屏幕。"
                     "屏幕平整无弧面，屏幕四角都在画面之内，画面里没有人、没有手、没有身体、没有鼠标。"
                     + SCREEN +
                     "屏幕正中央只有一行巨大的等宽数字，严格为：00:47:12。"
                     "除这一行数字以外，屏幕上没有任何其他内容——没有第二行、没有段落、没有中文、"
                     "没有英文、没有按钮、没有边框、没有图标、没有光标、没有窗口。"
                     "数字的上方和下方都是纯粹的空白黑色。"),
        dict(name="C05_end", out="C05_end", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "画面上方三分之二是这位44岁中国男性的一双手的极近特写："
                     "两只手都戴着黑色薄款皮革手套，手套贴合每一个指节，皮革哑光没有反光。"
                     "右手握着一支黑色签字笔，笔尖悬在斜置记录板上方约两厘米处，完全静止，没有落下。"
                     "左手戴着同样的黑色手套，扶着记录板的下缘。"
                     "记录板是硬质背板夹着白色表格纸，纸上印着细线表格。"
                     "手背骨节明显，有薄茧，手腕处露出黑色制服袖口。" + ROOM),
        # ===== 第 2 集 =====
        dict(name="C06_first", out="C06_first", ref=None,
             prompt=STYLE + "画面是一台电脑显示器的极近距离正面特写。" + SCREEN +
                     "屏幕中央显示两行中文记录文字，居中偏上，左对齐，行距均匀。"
                     "第一行严格为：最近一次续期：第 1095 次 。"
                     "第二行严格为：申请人签名：沈砚 。"
                     "除这两行外屏幕上没有任何其他文字。"),
        dict(name="C07_first", out="C07_first", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "俯拍角度，画面上方三分之二是这位44岁中国男性坐在办公桌前操作电脑，"
                     "他右手握着鼠标放在鼠标垫上，屏幕上是一列长长的中文任务队列列表，条目整齐排列。"
                     "他穿着黑色立领制式外套，双手戴黑色薄款手套，胸前别着工牌。" + OFFICE),
        dict(name="C07_end", out="C07_end", ref=None,
             prompt=STYLE + "画面是一台现代液晶显示器的正面特写，镜头与屏幕中心齐平，"
                     "整幅画面里只有这一块屏幕，没有拼接、没有分屏、没有上下两块画面。"
                     "屏幕上只有一组文字和一个白色鼠标箭头指针，没有边框、没有按钮、没有光标、没有图标。"
                     "鼠标箭头指针完全静止地悬停在屏幕右上角，指针必须清晰可见，"
                     "这是全片「手停住了」的关键信息，不能省略。"
                     + SCREEN +
                     "屏幕上显示的全部文字严格如下，一共七行，从上到下依次是："
                     "第一行：待办队列"
                     "第二行：1  已归档"
                     "第三行：2  已归档"
                     "第四行：3  已归档"
                     "第五行：4  已归档"
                     "第六行：5  已归档"
                     "第七行：续期申请 待审"
                     "前六行左对齐，行距均匀。前五行的编号前面有一个浅色方框，第六行是最后一条已归档的条目。"
                     "第七行是画面最下面的一行，它前面没有编号、没有方框、没有任何颜色、没有任何高亮、"
                     "没有任何标记，和上面几行的外观完全不同，它孤零零地待在下面的空白里。"
                     "除这七行以外，屏幕上没有任何其他文字。"),
        dict(name="C08_first", out="C08_first", ref=None,
             prompt=STYLE + "画面是一台电脑显示器的极近距离正面特写。" + SCREEN +
                     "屏幕中央显示三行中文档案字段，左对齐，行距均匀。"
                     "第一行严格为：回声编号：E-1109-林秀云 。"
                     "第二行严格为：状态：已注销 。"
                     "第三行严格为：归档日：2042-10-12 。"),
        dict(name="C09_first", out="C09_first", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "过肩视角。画面上方三分之二是这位44岁中国男性坐在办公桌前。"
                     "他的头明显低垂，下巴收向胸口，视线向下落在面前的电脑屏幕上，眼睛在看屏幕，"
                     "不是看向镜头，不是看向任何别处。"
                     "他的脸只被屏幕的冷白光从正下方照亮，光在他下巴和鼻孔下方形成向上的阴影，眼窝和额头是暗的。"
                     "天花板没有任何灯直接照在他的脸上，他的头顶和肩膀都是暗的。"
                     "画面右侧前景有一个虚化的人的肩膀和后脑勺，是过肩镜头对面那个人。"
                     "他面前的电脑屏幕就在他视线正下方，屏幕显示一片冷白色的中文档案详情页，"
                     "多行小号灰色文字，看不清具体内容。"),
        dict(name="C10_first", out="C10_first", ref="SY",
             prompt=STYLE + SY_REF_NOTE + "画面上方三分之二是这位44岁中国男性站在昏暗办公室的桌前。"
                     "他整个身体侧对镜头、背对镜头，脸完全看不到，只见侧后方的轮廓，"
                     "他的脸没有转回来。"
                     "戴黑色薄款手套的右手正把一块斜置的记录板推到一边，手已经推开记录板，"
                     "身体重心已经移向画面外，他正在离开。"
                     "转身时胸前工牌露出正面一角。" + DARK),
        dict(name="C10_end", out="C10_end", ref=None,
             prompt=STYLE + "画面上方三分之二是一只手的极近特写：这只手戴着黑色薄款皮革手套，"
                     "手套贴合每一个指节，皮革哑光没有反光。一根食指按在电梯面板的一个方形按钮上，"
                     "指尖因为用力而微微发白。电梯面板是拉丝不锈钢与哑光深灰，按钮微微凹陷。"
                     "手腕处露出黑色制服袖口。背景虚化成冷白色走廊，有防撞扶手的模糊轮廓。"
                     "手指必须戴着手套，绝不能是裸露的皮肤。画面静止。"),
    ]


if __name__ == "__main__":
    t0 = time.time()
    only = set(sys.argv[1:])           # 不带参数 = 全部 14 张；带名字 = 只重做这几张
    print("上传参考图...", flush=True)
    urls = {k: upload(v) for k, v in REFS.items()}
    for k, v in urls.items():
        print(f"  {k:<8} {os.path.basename(REFS[k])}", flush=True)

    jobs = frames(urls)
    if only:
        jobs = [j for j in jobs if j["name"] in only]
        unknown = only - {j["name"] for j in jobs}
        if unknown:
            sys.exit(f"未知片段名: {sorted(unknown)}\n可选: "
                     + " ".join(j["name"] for j in frames(urls)))
        print(f"\n只重做 {len(jobs)} 张: {', '.join(j['name'] for j in jobs)}", flush=True)

    def build(j):
        return {"prompt": j["prompt"], "aspect_ratio": "9:16", "resolution": "2K",
                "output_file": f"{j['out']}.png",
                **({"input_urls": [urls[j["ref"]]]} if j["ref"] else {})}

    # 平台硬限制：单次 requests 最多 10 条，超了直接 400
    BATCH = 10
    chunks = [jobs[i:i + BATCH] for i in range(0, len(jobs), BATCH)]
    results = []          # [(job, success_item), ...]
    for ci, chunk in enumerate(chunks, 1):
        print(f"\n批次 {ci}/{len(chunks)}（{len(chunk)} 张）提交...", flush=True)
        res = call("connector__matrix__generate_image",
                   {"requests": [build(j) for j in chunk]})
        print(f"  {res.get('summary')}", flush=True)
        for f in res.get("failed_items", []):
            i = f.get("index")
            name = chunk[i]["name"] if isinstance(i, int) and i < len(chunk) else "?"
            print(f"  FAIL {name}: {f.get('error_msg', '')[:200]}", flush=True)
        for i, item in enumerate(res.get("success_items", [])):
            results.append((chunk[i] if i < len(chunk) else None, item))

    print("\n下载...", flush=True)
    ok = 0
    for job, item in results:
        node_id, fname = item["node_id"], item["file_name"]
        out = subprocess.run(["mcode-tools", "get_asset_url", node_id],
                             capture_output=True, text=True).stdout
        dl = json.loads(out[out.find("{"):out.rfind("}") + 1])["download_url"]
        # 服务端可能把 .png 转存为 .jpg，落地名统一用 job 名
        ext = os.path.splitext(fname)[1] or ".png"
        base = job["out"] if job else os.path.splitext(fname)[0]
        dst = os.path.join(OUT, base + ext)
        subprocess.run(["curl", "-s", "-m", "180", "-o", dst, dl], check=True)
        print(f"  OK {os.path.basename(dst):<20} {os.path.getsize(dst)//1024} KB", flush=True)
        ok += 1

    print(f"\n完成 {ok}/{len(jobs)} 张，耗时 {(time.time()-t0)/60:.1f} 分钟", flush=True)
    print(f"目录: {OUT}", flush=True)
