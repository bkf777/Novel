#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原著结构化解剖：章节骨架 / 系统提示 / 人物词频 / 术语表"""
import re, json, collections, os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "00_原著资料", "原著原文_无尽杀戮.txt")

raw = open(SRC, encoding="utf-8", errors="replace").read()

# ---------- 1. 章节切分 ----------
ch_pat = re.compile(r"^第(\d+)章\s+(.+?)\s*$", re.M)
marks = list(ch_pat.finditer(raw))
chapters = []
for i, m in enumerate(marks):
    start = m.end()
    end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
    body = raw[start:end]
    chapters.append({
        "no": int(m.group(1)),
        "title": m.group(2).strip(),
        "chars": len(re.sub(r"\s", "", body)),
        "body": body,
    })

# 前置内容（书名/简介/作者）
head = raw[: marks[0].start()] if marks else raw

# ---------- 2. 系统提示（【...】） ----------
sys_lines = collections.Counter()
sys_by_ch = collections.defaultdict(list)
for c in chapters:
    for s in re.findall(r"[【\[]([^】\]]{2,120})[】\]]", c["body"]):
        s = s.strip()
        sys_lines[s] += 1
        sys_by_ch[c["no"]].append(s)

# ---------- 3. 人物候选名 ----------
name_pat = re.compile(r"([\u4e00-\u9fa5]{2,4})(?:说道|说|道|问道|问|笑道|喊道|怒道|冷声道|开口|点头|摇头|皱眉|一愣|盯着|看向|冲到|转身|上前)")
names = collections.Counter()
for c in chapters:
    for n in name_pat.findall(c["body"]):
        names[n] += 1
# 过滤明显非人名/常见词
STOP = set("""林川这个那个他们自己我们你们这个那个什么一个众人自己对方所有人而且但是因为所以如果就是还是已经正在一直突然立刻瞬间猛地顿时一个两个三个没有不是不能不会只能知道感觉仿佛似乎好像终于竟然居然果然果然没想到当然其实主要关键是原因结果目的方法方式东西事情问题情况状态力量速度精神体质等级属性天赋技能装备物品材料金币晶核晶石兽虫怪物玩家系统提示消息世界游戏战斗死亡活人尸体空间时间区域地图副本boss主线任务奖励经验值战斗力防御攻击生命值状态栏面板数据化全球公告""".split())
cand = [(n, c) for n, c in names.items() if c >= 25 and n not in STOP and len(n) <= 3]

# ---------- 4. 术语表（设定名词）----------
term_pat = re.compile(r"[【\[]([^】\]]{2,40})[】\]]")
terms = collections.Counter()
for c in chapters:
    for t in term_pat.findall(c["body"]):
        terms[t.strip()] += 1

# ---------- 5. 大纲输出 ----------
out = {
    "meta": {
        "title": "无尽杀戮：我的火球有bug！",
        "author": "是也",
        "total_chapters": len(chapters),
        "total_chars": sum(c["chars"] for c in chapters),
    },
    "chapters": [
        {k: c[k] for k in ("no", "title", "chars")} for c in chapters
    ],
}
with open(os.path.join(BASE, "00_原著资料", "_章节骨架.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# 分章正文切片文件（供并行解读）
chdir = os.path.join(BASE, "00_原著资料", "_chapters")
os.makedirs(chdir, exist_ok=True)
# 按 25 章一段分桶
for b in range(0, len(chapters), 25):
    chunk = chapters[b : b + 25]
    name = f"ch{b+1:04d}-{chunk[-1]['no']:04d}.txt"
    with open(os.path.join(chdir, name), "w", encoding="utf-8") as f:
        for c in chunk:
            f.write(f"\n===== 第{c['no']}章 {c['title']} ({c['chars']}字) =====\n")
            f.write(c["body"])

# ---------- 6. 统计报告 ----------
lines = []
lines.append(f"总章节 {len(chapters)}  总字数 {out['meta']['total_chars']}")
lines.append("\n## 章节标题全表\n")
for c in chapters:
    lines.append(f"{c['no']:>4} | {c['title']}")
lines.append("\n## 高频人名 Top 60\n")
for n, c in cand[:60]:
    lines.append(f"{n}\t{c}")
lines.append("\n## 系统提示 Top 120\n")
for s, c in sys_lines.most_common(120):
    lines.append(f"[{c}] {s}")
lines.append("\n## 术语/面板名 Top 120\n")
for t, c in terms.most_common(120):
    lines.append(f"[{c}] {t}")

with open(os.path.join(BASE, "00_原著资料", "_结构解剖.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"章节 {len(chapters)} / 字数 {out['meta']['total_chars']}")
print(f"分桶 {len(os.listdir(chdir))} 个切片 -> {chdir}")
print(f"人名候选 {len(cand)}, 系统提示 {len(sys_lines)}, 术语 {len(terms)}")
print("\n--- 章节标题前 30 ---")
for c in chapters[:30]:
    print(f"{c['no']:>4} | {c['title']}")
