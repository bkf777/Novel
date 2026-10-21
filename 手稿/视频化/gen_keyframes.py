#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《注销通知》竖屏短剧版 · 关键帧生成

链路：Qwen-Image 2.1 GGUF @ 本地 ComfyUI（127.0.0.1:8188）
产出：13 张关键帧（10 首帧 + 3 尾帧）+ 1 张女儿角色图
竖屏 9:16 用 832x1472（与 9:16 偏差 0.48%，H3 首尾帧模式取输入图比例）

用法：python3 gen_keyframes.py            # 全量
      python3 gen_keyframes.py C01 C05end # 只跑指定任务
"""
import json, time, os, sys, random, urllib.request, urllib.parse

HOST = "http://127.0.0.1:8188"
ROOT = "/Users/ezreal/projects/小说创作/手稿"
KF_DIR = os.path.join(ROOT, "视频化", "关键帧")
CHAR_DIR = os.path.join(ROOT, "人物图")

REF_SY = "01_沈砚_turnaround.png"   # 三视图：纯白摄影棚背景，不污染场景，且正面/侧面/背面可选机位
REF_CS = "07_陈素芬_portrait.png"

# 沈砚的三视图参考必须压掉"三个人"
REF_SY_NOTE = ("参考图是同一个角色的三视图设定稿（正面、侧面、背面），"
               "三个人是同一个人的三个角度。画面中只能出现一个人，不是三个人，"
               "不是并排的三视图，不是角色设定表。")
REF_SY_NOTE_NEG = "三个人并排，三视图设定表，角色设定稿，多个人物，分身"

W, H = 832, 1472          # 竖屏 9:16

NEG = ("低质量，模糊，变形，多余肢体，坏手，断指，文本乱码，错别字，水印，"
       "漫画，动漫，插画，卡通，二维，赛博朋克，霓虹，HUD面板，游戏界面，"
       "横向构图，人物过小，大头，畸变脸，塑料感，过曝，"
       # ↓ 参考图会把原场景带进来，这组词专门压公共空间
       "大厅，开放式空间，公共场所，人群，服务台，柜台，接待处，机场，银行，"
       "医院大厅，售票处，玻璃幕墙大厅，背景人群，远处人物")

# ---- 共用风格前缀：竖屏、冷白顶灯、低饱和、写实 ----
STYLE = ("竖屏9:16电影感剧照，冷白色顶灯，浅灰蓝低饱和色调，写实电影摄影，"
         "浅景深，眼平机位，真实皮肤质感，无文字无字幕无水印。")

# ---- 背景强制约束 ----
# 根因：TextEncodeQwenImage21 会把参考图的「场景」连同人物一起带出，
# 而 07/01 号参考图的原背景是服务大厅。必须在 prompt 里显式反压，
# 同时在 NEG 里压掉一切公共空间词。漏这一条 = 7 张关键帧全部穿帮。
ROOM = ("背景是一间封闭狭小的注销间：浅灰色墙面，天花板两盏冷白面板灯，"
        "一张金属桌，两把不锈钢椅，墙上没有窗没有海报，房间很小很安静，"
        "背景空无一人。")

OFFICE = ("背景是一间普通机关的开放式办公室：成排的灰色办公桌，每张桌上有一台显示器，"
          "天花板长条冷白灯管，远处几张空桌，浅灰色地板，房间开阔但不拥挤，"
          "没有服务台，没有窗口，没有排队的人群。")

DARK_OFFICE = ("背景是一间灯光很暗的办公室，只有电脑屏幕的冷白光从下方照亮人脸，"
               "远处隐约有其他办公桌和顶灯的轮廓，看不清细节。")


def build_prompt(positive, negative, width, height, seed, prefix, ref_image):
    """有参考图走 TextEncodeQwenImage21 的 images.image_1；无参考图走纯文生图。"""
    nodes = {
        "1": {"class_type": "UnetLoaderGGUF",
              "inputs": {"unet_name": "qwen-image-2.1-UC-BF16.gguf"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
    }
    enc_inputs = {"clip": ["2", 0], "vae": ["3", 0],
                  "prompt": positive, "negative_prompt": negative, "resolution": 1024}
    if ref_image:
        nodes["10"] = {"class_type": "LoadImage", "inputs": {"image": ref_image}}
        enc_inputs["images.image_1"] = ["10", 0]
    nodes["4"] = {"class_type": "TextEncodeQwenImage21", "inputs": enc_inputs}
    nodes["5"] = {"class_type": "EmptyLatentImage",
                  "inputs": {"width": width, "height": height, "batch_size": 1}}
    nodes["6"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1],
        "latent_image": ["5", 0], "seed": seed, "steps": 25, "cfg": 1,
        "sampler_name": "euler", "scheduler": "simple", "denoise": 1}}
    nodes["7"] = {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}}
    nodes["8"] = {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}}
    return nodes


def post(path, data):
    req = urllib.request.Request(HOST + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get(path):
    with urllib.request.urlopen(HOST + path, timeout=30) as r:
        return json.loads(r.read())


def download(fname, subfolder, out_path):
    q = urllib.parse.urlencode({"filename": fname, "subfolder": subfolder, "type": "output"})
    with urllib.request.urlopen(HOST + "/view?" + q, timeout=60) as r:
        data = r.read()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)


def run_job(job):
    t0 = time.time()
    positive, negative = job["positive"], NEG
    # 沈砚用三视图做参考：自动补「只能出现一个人」的约束与对应负面词
    if job.get("ref") == REF_SY:
        positive = REF_SY_NOTE + positive
        negative = negative + "，" + REF_SY_NOTE_NEG
    wf = build_prompt(positive, negative, job["width"], job["height"],
                      job["seed"], job["prefix"], job.get("ref"))
    try:
        pid = post("/prompt", {"prompt": wf, "client_id": "mavis-novel"})["prompt_id"]
    except Exception as e:
        print(f"FAIL {job['name']}: 提交失败 {e}", flush=True)
        return None
    while True:
        time.sleep(3)
        hist = get("/history/" + pid)
        if pid not in hist:
            continue
        h = hist[pid]
        for out in h.get("outputs", {}).values():
            for img in out.get("images", []):
                if img["type"] == "output":
                    p = os.path.join(job["out_dir"], f"{job['prefix']}.png")
                    download(img["filename"], img.get("subfolder", ""), p)
                    print(f"OK   {job['name']:<12} -> {p}  ({time.time()-t0:.0f}s)", flush=True)
                    return p
        if h.get("status", {}).get("status_str") == "error":
            msg = json.dumps(h.get("status", {}), ensure_ascii=False)[:400]
            print(f"FAIL {job['name']}: {msg}", flush=True)
            return None


# ---------------- 任务定义 ----------------
SY = ("44岁中国男性，清瘦，黑色立领制式外套偏大肩线塌落，胸前工牌，"
      "眼下有洗不掉的青灰色倦意，左眉尾一道极淡旧疤，短黑发两鬓微白，"
      "左眉尾旧疤，右手黑色薄款权限手套，坐姿极直，手几乎不动。")
CS = ("82岁中国女性，短银白头发，深藏青色羊毛外套内搭浅色衬衣，"
      "双手捧一只白色纸杯，皮肤比周围真人略去饱和，轮廓边缘有一层极细的颗粒微光。")

SCREEN = "近黑色屏幕底，冷白色等宽中文字体，字号大，清晰锐利，无图标，无进度条，无霓虹，无光效。"

JOBS = [
    # ---- 0. 女儿角色图（缺资源，先补）----
    dict(name="女儿角色图", prefix="12_陈素芬之女_portrait", width=832, height=1216,
         out_dir=CHAR_DIR, ref=None, seed=20261116,
         positive=("写实电影摄影人物肖像，冷白色走廊顶灯，浅景深。"
                   "一个三十岁左右的中国女性蹲坐在地，背靠浅灰色墙壁，双膝曲起。"
                   "长款黑色羽绒服外套，头发被雨打湿贴在脸侧，脸色苍白疲惫，"
                   "眼下有哭过的红血丝，黑色长裤，右手膝盖处有一块暗紫色淤青。"
                   "抬头望向画外，眼神绝望但克制。真实皮肤质感，均匀柔和顶光。")),

    # ---- 1. 首帧 C01 钩子 ----
    dict(name="C01_first", prefix="C01_first", width=W, height=H, ref=REF_CS, seed=20261117,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一位82岁中国女性的正面特写：" + CS +
                   "她抬眼直视镜头，神情平静没有求生的表情。" + ROOM),

    # ---- 2. 首帧 C02 ----
    dict(name="C02_first", prefix="C02_first", width=W, height=H, ref=REF_SY, seed=20261118,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一位44岁中国男性坐在金属桌前的侧面中景，"
                   "镜头拍的是他的正侧面，他面朝画面右侧：" + SY +
                   "他右手握一支笔，笔尖悬在桌角斜置的记录板上方约两厘米处，完全静止。"
                   "桌面上有一张空白纸。" + ROOM),

    # ---- 3. 首帧 C03 ----
    dict(name="C03_first", prefix="C03_first", width=W, height=H, ref=REF_SY, seed=20261119,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一位44岁中国男性的正面特写：" + SY +
                   "他正开口说话，嘴唇微张，表情平直没有起伏。"
                   "身后是虚化的电脑屏幕，屏幕发出冷白色界面光。" + ROOM),

    # ---- 4. 首帧 C04 ----
    dict(name="C04_first", prefix="C04_first", width=W, height=H, ref=REF_CS, seed=20261120,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一位82岁中国女性的正面中景：" + CS +
                   "她低头用拇指沿杯口慢慢擦拭，肩膀完全不动。" + ROOM),

    # ---- 5. 首帧 C05 倒计时屏幕 ----
    dict(name="C05_first", prefix="C05_first", width=W, height=H, ref=None, seed=20261121,
         out_dir=KF_DIR,
         positive=STYLE + "画面是一块电脑屏幕的极近距离特写。" + SCREEN +
                   "屏幕中央偏上显示一行巨大的等宽数字倒计时：00:47:12。"
                   "屏幕玻璃有极轻微的反光和一道细微划痕。纯黑背景，无人物。"),

    # ---- 6. 首帧 C06 钩子屏幕 ----
    dict(name="C06_first", prefix="C06_first", width=W, height=H, ref=None, seed=20261122,
         out_dir=KF_DIR,
         positive=STYLE + "画面是一块电脑屏幕的极近距离特写。" + SCREEN +
                   "屏幕中央显示两行中文记录文字：" +
                   "第一行「最近一次续期：第 1095 次」，第二行「申请人签名：沈砚」。"
                   "两行字左对齐，间距均匀。纯黑背景，无人物。"),

    # ---- 7. 首帧 C07 工位俯拍 ----
    dict(name="C07_first", prefix="C07_first", width=W, height=H, ref=REF_SY, seed=20261123,
         out_dir=KF_DIR,
         positive=STYLE + "俯拍角度，画面上方三分之二是一位44岁中国男性坐在办公桌前操作电脑：" + SY +
                   "他右手握鼠标，屏幕上是一列长长的中文任务队列列表。" + OFFICE),

    # ---- 8. 首帧 C08 档案屏幕 ----
    dict(name="C08_first", prefix="C08_first", width=W, height=H, ref=None, seed=20261124,
         out_dir=KF_DIR,
         positive=STYLE + "画面是一块电脑屏幕的极近距离特写。" + SCREEN +
                   "屏幕中央显示三行中文档案字段，左对齐：" +
                   "「回声编号：E-1109-林秀云」、「状态：已注销」、「归档日：2042-10-12」。"
                   "纯黑背景，无人物。"),

    # ---- 9. 首帧 C09 详情页 ----
    dict(name="C09_first", prefix="C09_first", width=W, height=H, ref=REF_SY, seed=20261125,
         out_dir=KF_DIR,
         positive=STYLE + "过肩视角，画面上方三分之二是一位44岁中国男性正低头看电脑屏幕：" + SY +
                   "屏幕上是一片冷白色的中文档案详情页，多行灰色文字。"
                   "屏幕的光从下方照亮他的脸。" + DARK_OFFICE),

    # ---- 10. 首帧 C10 已驳回屏幕 ----
    dict(name="C10_first", prefix="C10_first", width=W, height=H, ref=None, seed=20261126,
         out_dir=KF_DIR,
         positive=STYLE + "画面是一块电脑屏幕的极近距离特写。" + SCREEN +
                   "屏幕中央显示两行中文记录文字：" +
                   "第一行「最后一次续期申请：已驳回」，第二行「申请人签名：沈砚」。"
                   "纯黑背景，无人物。"),

    # ---- 11. 尾帧 C05 悬停的笔 ----
    dict(name="C05_end", prefix="C05_end", width=W, height=H, ref=REF_SY, seed=20261127,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一只手的极近特写：44岁中国男性的右手，"
                   "指节分明、指甲剪到贴着肉，握着一支黑色签字笔，笔尖悬在斜置记录板上方约两厘米处，"
                   "完全静止。手背有薄茧。" + ROOM),

    # ---- 12. 尾帧 C07 停住的鼠标 ----
    dict(name="C07_end", prefix="C07_end", width=W, height=H, ref=None, seed=20261128,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是电脑屏幕下半部分的近距离特写。" + SCREEN +
                   "屏幕下方是一列编号的中文任务队列条目，每行前面有一个浅色方框编号。"
                   "最后一行下面多出了一条没有任何颜色、没有高亮、没有任何标记的额外文字行。"
                   "画面静止。纯黑背景，无人物。"),

    # ---- 13. 尾帧 C10 电梯按钮 ----
    dict(name="C10_end", prefix="C10_end", width=W, height=H, ref=None, seed=20261129,
         out_dir=KF_DIR,
         positive=STYLE + "画面上方三分之二是一只手的极近特写：一根食指按在电梯面板的一个方形按钮上，"
                   "指尖微微发白用力。电梯面板是拉丝不锈钢与哑光深灰，背景虚化成冷白色走廊。"),
]


if __name__ == "__main__":
    want = sys.argv[1:]
    jobs = [j for j in JOBS if not want or j["name"] in want]
    print(f"共 {len(jobs)} 个任务，竖屏 {W}x{H}\n", flush=True)

    # 跳过已产出且非空的文件（支持断点续跑；文件损坏/小于 10KB 视为失败需重跑）
    todo = []
    for j in jobs:
        p = os.path.join(j["out_dir"], f"{j['prefix']}.png")
        if os.path.exists(p) and os.path.getsize(p) > 10240:
            print(f"SKIP {j['name']}（已存在）", flush=True)
        else:
            todo.append(j)

    t_all = time.time()
    for i, j in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {j['name']} ...", flush=True)
        run_job(j)
    print(f"\n全部结束，本次新增 {len(todo)} 张，耗时 {(time.time()-t_all)/60:.1f} 分钟", flush=True)
    print(f"关键帧目录: {KF_DIR}", flush=True)
    print(f"角色图目录: {CHAR_DIR}", flush=True)
