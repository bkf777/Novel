#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_density_fills_U03.py —— 生成 U03 的 Q100 字幕密度填充清单

为什么单独一个脚本（而不是手写 JSON）
────────────────────────────────────
清单有两类内容：**文案**（人工撰写）与**时码**（机械推算）。
文案必须逐字锚定该镜 D11 `visual_facts` 已写明的事实（不编画面、不编数字），
而时码要同时满足五个硬约束（落在该镜真实可见区间内／不与既有行重叠／
停留 ≥1.6s 且 ≥阅读速度下限／单行 ≤15 字／不越过片尾标题卡 43.0s）
——手写 100+ 行时码极易算错。
⇒ 本脚本把「文案」写成人工表格（TABLE），把「时码」交给算法，并**在生成时就断言**：
  ① anchor 必须逐字是该镜 D11 visual_facts 的子串；
  ② 字幕文本 ≤15 字（D16 `max_chars_per_line`）；
  ③ 字幕文本**与 note 全文**不得命中 D05 禁用同义写法
     （V5 全文扫描 D16，含 note 文本；anchor 会进 note，故 note 一并检查）；
  ④ 不得命中「律条」（rules.json `term_first_use`：ep013–040 字幕面禁用）；
  ⑤ 不得命中本单元 `readout_in_frame` 登记的读数（归一度 1.4% 留画面、不进字幕层）；
  ⑥ 同一集内文本唯一（densify 执行器按文本命中既有行，撞文本会改到别人的行）；
  ⑦ 排布后每镜最长空窗 ≤4.0s、全集空窗总 ≤12s（Q100 判据）。

时码算法（为什么这样排）
──────────────────────
· **停留下限＝阅读速度**：本厂 D16 既有口径「按 4.5 字/秒估算」⇒ 一行字幕的停留不得
  少于 `字数 / 4.5`（向上取到 0.1s 网格），且不小于 1.6s（高于 D16 的 1.2s 下限）。
  这条约束保证了「填空窗」不是靠塞一堆一闪而过的碎行。
· **选行用 DP，不靠贪心前缀**：一个空区间能放几行、哪几行最优，是个背包问题。
  若按「取前 k 条能放下的」，一旦第 k+1 条偏长就整体停下，后面短的也放不进去 ⇒
  区间尾部留下大段空窗。故用 DP 在「sum(dwell) + (k-1)*SEP ≤ 区间长」下
  **最大化覆盖时长**；同覆盖时优先取靠前（优先级高）的行。
· **每镜第一条保底**：该镜最该被读到的事实（TABLE 里的第 1 条）放得下就一定排上，
  避免「覆盖率最大化」把主信息挤掉。
· **每个空区间留一点呼吸**：覆盖上限 = 区间长 − 0.4s，不做成满屏文字墙；
  区间太短放不下这点空隙时放宽到区间长（宁可这一段密一点，也不要留 3s 空窗）。
· **行间最小间隔 0.2s**；剩余空隙在「行前／行间／行后」之间尽量均分 ⇒ 最大空窗最小。

**不动**：镜数、镜时、对白行时码、D15（声音设计岗）、D08／D09／D12。
用法：python3 scripts/build_density_fills_U03.py [--dry-run]
"""
import argparse
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UNIT = "U03"
CHAR_PER_SEC = 4.5      # 本厂 D16 既有口径：台词/字幕按 4.5 字/秒估算
MIN_DWELL = 1.6         # 单行停留下限（> D16 的 1.2s 下限，避免贴边行）
SEP = 0.2               # 相邻行之间的最小间隔
GRID = 0.1              # 时码标称网格
MAX_GAP = 4.0           # Q100：单镜最长无字幕空窗上限（与 audit_dead_time.py 同口径）
MAX_TOTAL_GAP = 12.0    # Q100：全集空窗总上限（本岗自设的更严口径）
TAIL_LIMIT = 43.0       # D16 `sync_rule`：正文行 out_sec 不得越过片尾标题卡 in_sec
SLACK_FLOOR = 0.4       # 每个空区间保留的呼吸空隙

# ── 人工撰写的文案（唯一的内容来源）────────────────────────────────────────
# 结构：{集号: {镜号: [(字幕文本, anchor), ...]}}，anchor 必须是该镜 visual_facts 的字面子串。
# 每镜的候选按优先级排序：靠前的行＝该镜最该被读到的事实；DP 在容量不够时按此顺序取舍。
TABLE = {
    17: {
        1: [
            ("厂门外余火：还在烧", "厂门外的余火还在烧"),
            ("十几条影子压过来", "十几条影子从灰雾里压过来"),
            ("叶红衣守在缺口处", "叶红衣独自站在半圈缺口处"),
            ("街面被围成半圈", "把街面围成半圈"),
            ("影刃横在身前", "影刃横在身前"),
            ("街面只留一道暗色", "街面上只留下一道暗色"),
            ("刃面不反光", "刃面不反光"),
        ],
        2: [
            ("最前排影子溃散为灰烬光尘", "最前排的影子一个个溃散为灰烬光尘"),
            ("影刃切过街面", "影刃切过街面"),
            ("落灰积在砖缝里", "落灰积在砖缝里"),
            ("街面留下一道暗色", "街面上只留下一道暗色"),
            ("刃身不反光", "刃身不反光"),
        ],
        3: [
            ("剩下的影子退向街口暗处", "剩下的影子退向街口暗处"),
            ("主谋被逼到路口", "主谋被逼到路口"),
            ("退路一寸寸断掉", "退路一寸寸断掉"),
            ("街口只剩暗处与断路", "街口只剩暗处与被截断的路"),
            ("主谋只作剪影", "主谋只作剪影"),
        ],
        4: [
            ("厂门阴影里走出一个人", "厂门阴影里走出一个人"),
            ("整条街面被压住", "整条街面被压住"),
            ("黑白骨纹一路亮起", "右腕骨上的黑白骨纹一路亮起来"),
        ],
    },
    18: {
        1: [
            ("骨纹自右腕骨亮到小臂", "骨纹自右腕骨一路亮到小臂"),
            ("白光顺着街面铺开", "白光顺着街面铺开"),
            ("灰雾被压得下沉", "灰雾被压得下沉"),
            ("街面碎石跳起来", "街面碎石在震动里跳起"),
            ("骨威全开", "骨威全开"),
        ],
        2: [
            ("围上来的人溃散为灰烬光尘", "围上来的人一个个溃散为灰烬光尘"),
            ("人形轮廓散成发亮的灰点", "人形轮廓逐个散成发亮的灰点"),
            ("消解由近及远", "消解由近及远"),
            ("压下来的范围内", "压下来的范围内"),
        ],
        3: [
            ("屏上频谱一条条平下去", "屏上频谱一条条平下去"),
            ("多余的心跳信号全部消失", "多余的心跳信号全部消失"),
            ("数据板架在钢箱上", "苏清辞把数据板架在钢箱上"),
            ("街面安静下来", "街面安静下来"),
            ("落灰被风推成一道一道", "落灰被风推成一道一道"),
        ],
        4: [
            ("身份铭牌与敌酋纹章", "身份铭牌与敌酋纹章"),
            ("单独落在砖面上", "单独落在砖面上"),
            ("只剩两件金属件", "灰烬落定处只剩两件金属件"),
            ("陆沉弯腰取下两件", "陆沉弯腰把两件一件件取下握在手里"),
        ],
    },
    19: {
        1: [
            ("身份铭牌与敌酋纹章挂上门柱", "身份铭牌与敌酋纹章被挂上门柱"),
            ("只挂两件金属件", "只挂两件金属件"),
            ("门柱上没有别的东西", "门柱上没有别的东西"),
            ("门柱在灰雾里只剩轮廓", "门柱在灰雾里只剩轮廓"),
        ],
        2: [
            ("旗面一行字：踏入此线者死", "旗面上一行字：踏入此线者死"),
            ("叶红衣把旗杆压进石缝", "叶红衣把旗杆压进门槛石缝"),
            ("旗面在灰雾里展开", "旗面在灰雾里展开"),
            ("杆身立直", "杆身立直"),
        ],
        3: [
            ("铭牌编号抄进数据板", "苏清辞把铭牌编号抄进数据板"),
            ("抄完又核了一遍", "抄完又核了一遍"),
            ("陆沉站在门内看着旗面", "陆沉站在门内一侧看着旗面"),
            ("他没有接话", "没有接话"),
        ],
        4: [
            ("队伍沿车辙排到厂门外", "队伍已经沿着车辙排到厂门外"),
            ("车辙从四面压过来", "车辙从四面压过来"),
            ("天还没亮", "天还没亮"),
            ("厂门外的灰雾里", "厂门外的灰雾里车辙从四面压过来"),
        ],
    },
    20: {
        1: [
            ("队伍从厂门排到路口", "队伍从厂门一直排到路口"),
            ("车辙压进灰雾里", "车辙压进灰雾里"),
            ("轮印叠着轮印", "轮印叠着轮印"),
            ("排队的人一律作剪影", "排队的人一律作剪影"),
            ("队形拐进灰雾深处", "队形一路拐进灰雾深处"),
        ],
        2: [
            ("按灰斑轻重分出两列", "苏清辞在分诊台前按灰斑轻重分出两列"),
            ("两列之间留出一条通道", "两列之间留出一条通道"),
            ("净火排在最前面", "净火排在最前面"),
            ("队头是净火位", "队头是净火位"),
        ],
        3: [
            ("第一次按名册点人", "死士营第一次按名册点人"),
            ("笔尖一列列往下走", "笔尖一列列往下走"),
            ("名册翻到最后一页", "陆沉走到登记位前把名册接过来翻到最后一页"),
            ("陆沉接过来名册", "陆沉走到登记位前把名册接过来"),
        ],
        4: [
            ("门禁改成两班", "门禁改成两班"),
            ("叶红衣的刃没有离手", "叶红衣的刃没有离手"),
            ("天亮时灰雾没有散", "天亮时灰雾没有散"),
            ("街面上还是灰的", "街面上还是灰的"),
        ],
    },
    21: {
        1: [
            ("灰斑比两天前多了一倍", "灰斑比两天前多了一倍"),
            ("灰斑只在袖口手背可见", "灰斑只在袖口与手背上可见"),
            ("队伍拐了两个弯", "分诊台前的队伍拐了两个弯"),
            ("排队的人一律作剪影", "排队的人一律作剪影"),
        ],
        2: [
            ("逾期的人动作变慢", "逾期的人动作变慢"),
            ("街上的人绕着他们走", "街上的人绕着他们走"),
            ("灰斑从边缘往外扩", "灰斑从边缘往外扩"),
            ("异化者只作遮挡", "异化者只作遮挡，不给面部"),
            ("不给面部", "不给面部"),
        ],
        3: [
            ("告示：药剂按量分配", "药剂按量分配"),
            ("安全屋名额暂停发放", "安全屋名额暂停发放"),
            ("净火净化排到最前", "陆沉把净火净化排到最前"),
            ("按剩余药剂分诊", "苏清辞按剩余药剂分诊"),
            ("厂门贴出新的告示", "厂门贴出新的告示"),
        ],
        4: [
            ("袖口上是几何徽记", "袖口上是几何徽记"),
            ("步子齐得像一列", "步子齐得像一列"),
            ("看不出任何宗教符号", "看不出任何宗教符号"),
            ("徽记是抽象几何", "徽记是抽象几何"),
        ],
    },
    22: {
        1: [
            ("骨井井架上绞盘在转", "城郊骨井的井架上绞盘在转"),
            ("井口开始返出灰雾", "井口开始返出灰雾"),
            ("井架在灰雾里只剩轮廓", "井架在灰雾里只剩轮廓"),
            ("作业的人只余剪影", "作业的人只余剪影"),
        ],
        2: [
            ("数据板跳出持续低频", "数据板上跳出一段持续低频"),
            ("方向标指向城郊", "方向标指向城郊"),
            ("屏幕上一段波形不落", "屏幕上一段波形保持不落"),
        ],
        3: [
            ("只找到空井架", "只找到空井架"),
            ("井壁新凿痕还在掉灰", "井壁上一道新的凿痕还在掉灰"),
            ("绞盘的绳缠得更深", "绞盘的绳缠得更深了一层"),
            ("叶红衣带人出城查过", "叶红衣带人出城查过一趟"),
            ("返上来的灰雾", "返上来的灰雾"),
        ],
        4: [
            ("城西方向拖回一名信使", "城西方向拖回一名信使"),
            ("取出一封未拆的密信", "死士营从终端里取出一封未拆的密信"),
            ("终端还亮着", "终端还亮着"),
            ("纸面没有署名", "纸面没有署名"),
        ],
    },
    23: {
        1: [
            ("密信在钢桌上摊开", "一封密信在钢桌上摊开"),
            ("排版是合同的样子", "排版是合同的样子"),
            ("条款分栏排列", "条款分栏排列"),
            ("纸面没有署名", "纸面没有署名"),
        ],
        2: [
            ("云顶财阀按批次拨付", "云顶财阀按批次拨付安全屋配额与药剂"),
            ("雾盟按批次交付高阶雾核", "雾盟按批次交付高阶雾核"),
            ("两行条款逐行落在纸面上", "两行条款逐行落在纸面上"),
        ],
        3: [
            ("交付栏翻到最后一页", "交付栏翻到最后一页"),
            ("只有批次编号和四个字", "只有批次编号和四个字"),
            ("清退区域", "清退区域"),
            ("整页没有一个人的名字", "整页没有一个人的名字"),
            ("栏位是区域，不是人", "栏位是区域，不是人"),
            ("两张纸上的区域对上了", "两张纸上的区域对上了"),
            ("救治排班表摊在旁边", "苏清辞把自己的救治排班表摊在旁边"),
        ],
        4: [
            ("密信摊在面板上逐行读完", "陆沉把密信摊在面板上逐行读完"),
            ("指腹在最后一行停住", "指腹在最后一行停住"),
            ("逐行读完", "逐行读完"),
            ("最后一行", "指腹在最后一行停住"),
        ],
    },
    24: {
        1: [
            ("钢桌上并排摊着两样东西", "钢桌上并排摊着两样东西"),
            ("交易条款", "交易条款"),
            ("骨井凿进的进度", "骨井凿进的进度"),
            ("并排占满画面中部", "两样东西并排占满画面中部"),
        ],
        2: [
            ("算出一行数字", "苏清辞在名单板前算出一行数字"),
            ("名字排成几列", "名单板上的名字排成几列"),
            ("数字写在最下一行", "数字写在最下一行"),
            ("净火能覆盖的极限", "是净火能覆盖的极限"),
        ],
        3: [
            ("一枚雾核按在名单板上", "陆沉把一枚雾核按在名单板上"),
            ("灰斑从指节边缘退成浅色", "灰斑从指节边缘退成浅色"),
            ("黑白双焰烧过", "黑白双焰烧过"),
            ("一缕白烟", "净化结果是一缕白烟和恢复正常的手背颜色"),
            ("手背恢复正常的颜色", "恢复正常的手背颜色"),
        ],
        4: [
            ("把最后一行看了很久", "把名单板上的最后一行看了很久"),
            ("净化区的火烧到天亮", "净化区的火一直烧到天亮"),
            ("名单又长了一截", "名单又长了一截"),
            ("陆沉没有反驳", "陆沉没有反驳"),
        ],
    },
}

NOTE_TMPL = ("镜{shot} 画面文字行：内容逐字锚定本镜 D11 visual_facts「{anchor}」——"
             "只把画面里已经写明的事实读出来，不新增物件、不编数字、不改镜数与镜时；"
             "挂载区间落在本镜真实可见区间内（左闭右开，不与既有行重叠）；"
             "停留按本厂 4.5 字/秒阅读速度下限取，不压成一闪而过的碎行。")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def grid(x):
    return round(round(x / GRID) * GRID, 1)


def shot_windows(d11_ep):
    t = 0.0
    out = {}
    for s in sorted(d11_ep["shots"], key=lambda x: x["shot_id"]):
        out[s["shot_id"]] = (t, t + float(s["duration_sec"]))
        t += float(s["duration_sec"])
    return out


def free_intervals(t0, t1, covered):
    """[t0,t1] 内未被既有正文行覆盖的区间（角标是常驻元素，不占字幕带）。"""
    iv = sorted((max(a, t0), min(b, t1)) for a, b in covered
                if b > a and min(b, t1) > max(a, t0))
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, cur = [], t0
    for a, b in merged:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < t1:
        out.append((cur, t1))
    return [(a, b) for a, b in out if b - a > 0.05]


def dwell_of(text):
    """阅读速度下限：按 4.5 字/秒估算，向上取到 0.1s 网格，且不小于 1.6s。"""
    need = math.ceil(len(text) / CHAR_PER_SEC * 10) / 10.0
    return grid(max(MIN_DWELL, need))


def select_rows(L, rows, slack_floor=SLACK_FLOOR):
    """在长度 L 的空区间内，从 rows（按优先级排序）里选一个子集排布。

    · 第 0 行（该镜最该被读到的事实）**保底**：放得下就一定选中；
    · 其余行用 DP 在「sum(dwell) + (k-1)*SEP ≤ L」下**最大化覆盖时长**，
      同覆盖时优先取靠前（优先级高）的行；
    · 覆盖上限 = L − slack_floor（每区间留一点呼吸，不做满屏文字墙）；
      区间太短放不下这点空隙时放宽到 L。
    返回：按优先级排序的选中行列表。
    """
    if not rows:
        return []
    cap = L - slack_floor
    if cap < MIN_DWELL:
        cap = L
    forced, pool = [], list(range(len(rows)))
    if rows[0][-1] <= cap + 1e-9 and rows[0][-1] <= L + 1e-9:
        forced = [0]
        pool = pool[1:]
    base = sum(rows[i][-1] for i in forced)
    room_cap = cap - base
    room_len = L - base - len(forced) * SEP
    # DP: key = (覆盖时长, 行数) -> 选中的下标列表（列表更小＝优先级更高）
    dp = {(0.0, 0): []}
    for i in pool:
        d = rows[i][-1]
        nd = dict(dp)
        for (tot, k), idxs in dp.items():
            nt = tot + d
            nk = k + 1
            if nt > room_cap + 1e-9:
                continue
            if nt + (nk - 1) * SEP > room_len + 1e-9:
                continue
            key = (round(nt, 1), nk)
            cand = idxs + [i]
            cur = nd.get(key)
            if cur is None or cand < cur:
                nd[key] = cand
        dp = nd
    best = None
    for (tot, k), idxs in dp.items():
        if not idxs:
            continue
        score = (round(tot, 1), k)
        if best is None or score > best[0]:
            best = (score, idxs)
    sel = sorted(forced + (best[1] if best else []))
    return [rows[i] for i in sel]


def place_interval(a, b, rows):
    """把选中的行排进 [a,b]：行间留 SEP，剩余空隙在 k+1 个空位里尽量均分。"""
    if not rows:
        return []
    ds = [r[-1] for r in rows]
    k = len(rows)
    total = (b - a) - sum(ds)
    if total < 0:
        total = 0.0
    nslot = k + 1
    if total / nslot >= SEP - 1e-9:
        gaps = [total / nslot] * nslot
    else:
        extra = max(0.0, total - (k - 1) * SEP)
        gaps = [extra / 2.0] + [SEP] * (k - 1) + [extra / 2.0]
    out, cur = [], a
    for i in range(k):
        cur += gaps[i]
        s = grid(cur)
        e = grid(s + ds[i])
        out.append((s, e, rows[i]))
        cur = e
    # 取整后若溢出右端，整体左移（不缩停留），保证不越出该镜可见区间
    overflow = (out[-1][1] - b) if out else 0.0
    if overflow > 1e-9:
        shifted = []
        for (s, e, r) in out:
            s2 = grid(max(a, s - overflow))
            shifted.append((s2, grid(s2 + (e - s)), r))
        out = shifted
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d11 = load(os.path.join(ROOT, "units", UNIT, "D11.json"))
    d16 = load(os.path.join(ROOT, "units", UNIT, "D16.json"))
    d05 = load(os.path.join(ROOT, "shared", "D05.json"))
    rules_p = os.path.join(ROOT, "..", "..", "..", "03_规格", "rules.json")
    rules = load(rules_p) if os.path.exists(rules_p) else {}

    banned = []
    for g in d05.get("glossary", []):
        for b in (g.get("forbidden_synonyms") or []):
            if b:
                banned.append((g.get("term"), b))
    term_bans = [(e.get("term"), e.get("first_use_ep"), e.get("forbidden_until_ep"))
                 for e in (rules.get("term_first_use") or []) if e.get("term")]

    m11 = {e["ep"]: e for e in d11["episodes"]}
    m16 = {e["ep"]: e for e in d16["episodes"]}

    errors, warnings = [], []
    out_units, stats = {}, []

    for ep in sorted(m16):
        e16, e11 = m16[ep], m11[ep]
        ss = e16["subtitle_style"]
        lines = ss["lines"]
        wins = shot_windows(e11)
        covered = [(float(l["in_sec"]), float(l["out_sec"]))
                   for l in lines if l.get("type") != "角标"]
        existing_texts = {str(l.get("text") or "") for l in lines}
        readout_texts = {str(r.get("text") or "") for r in (ss.get("readout_in_frame") or [])}
        max_chars = int(ss.get("max_chars_per_line", 15))

        fills, pool_left = [], []
        for shot_id in sorted(wins):
            t0, t1 = wins[shot_id]
            vf = next((s.get("visual_facts") or "") for s in e11["shots"]
                      if int(s["shot_id"]) == shot_id)
            cand = TABLE.get(ep, {}).get(shot_id, [])
            rows = []
            for text, anchor in cand:
                note = NOTE_TMPL.format(shot=shot_id, anchor=anchor)
                if anchor not in vf:
                    errors.append(f"ep{ep} 镜{shot_id}「{text}」anchor「{anchor}」不在 D11 visual_facts 中")
                    continue
                if len(text) > max_chars:
                    errors.append(f"ep{ep}「{text}」{len(text)} 字 > {max_chars} 字上限")
                for term, bad in banned:
                    for scope, blob in (("字幕", text), ("note", note)):
                        if bad in blob:
                            errors.append(f"ep{ep}「{text}」{scope}命中 D05 禁用同义写法"
                                          f"「{bad}」（术语「{term}」）")
                for term, f_, t_ in term_bans:
                    if term in text and f_ is not None and ep >= f_ \
                            and t_ is not None and ep <= t_:
                        errors.append(f"ep{ep}「{text}」命中首用集禁用术语「{term}」")
                for rt in readout_texts:
                    if rt and rt in text:
                        errors.append(f"ep{ep}「{text}」命中 readout_in_frame 登记的读数"
                                      f"「{rt}」（该读数留画面、不进字幕层）")
                if text in existing_texts:
                    errors.append(f"ep{ep}「{text}」与既有行文本重复")
                rows.append((text, anchor, dwell_of(text)))

            intervals = free_intervals(t0, t1, covered)
            left = list(rows)
            for a, b in intervals:
                if not left:
                    break
                use = select_rows(b - a, left)
                if not use:
                    continue
                chosen_ids = {id(r) for r in use}
                left = [r for r in left if id(r) not in chosen_ids]
                for s, e, (text, anchor, _d) in place_interval(a, b, use):
                    if e - s < 1.2 - 1e-9:
                        errors.append(f"ep{ep}「{text}」停留 {round(e-s,2)}s < 1.2s")
                    if e > TAIL_LIMIT + 1e-9:
                        errors.append(f"ep{ep}「{text}」out_sec {e} 越过片尾标题卡 in_sec {TAIL_LIMIT}")
                    fills.append({
                        "text": text, "in_sec": s, "out_sec": e, "shot_id": shot_id,
                        "anchor": anchor,
                        "note": NOTE_TMPL.format(shot=shot_id, anchor=anchor),
                    })
                    covered.append((s, e))
                    existing_texts.add(text)
            if left:
                pool_left.append((shot_id, [t for t, _, _ in left]))

        # 排布后复核：最长空窗 / 空窗总
        merged = sorted(covered)
        worst, total = 0.0, 0.0
        for shot_id, (t0, t1) in wins.items():
            gaps = free_intervals(t0, t1, merged)
            worst = max(worst, max([b - a for a, b in gaps] or [0]))
            total += sum(b - a for a, b in gaps)
        if worst > MAX_GAP + 1e-9:
            errors.append(f"ep{ep} 排布后单镜最长空窗 {worst:.2f}s > {MAX_GAP}s")
        if total > MAX_TOTAL_GAP + 1e-9:
            errors.append(f"ep{ep} 排布后全集空窗总 {total:.2f}s > {MAX_TOTAL_GAP}s")
        stats.append((ep, len(fills), round(worst, 2), round(total, 2)))
        out_units[str(ep)] = {
            "_note": ("Q100 字幕密度填充：本集按 D11 每镜 visual_facts 已写明的事实补画面文字，"
                      "填掉成片空窗；不加台词（D09 语气卡对陆沉写死「每集不超过 4 句」）、"
                      "不改镜数与镜时、不碰 D15。"),
            "fills": fills,
        }

    if errors:
        print("❌ 生成前校验未通过：")
        for e in errors:
            print("   -", e)
        return 1

    print(f"{'集':>10} {'填充行数':>8} {'最长空窗':>9} {'空窗总':>8}  剩余候选")
    for ep, n, w, t in stats:
        drop_n = len([1 for sid, lst in pool_left if lst])
        print(f"U03-EP{ep:<5} {n:>8} {w:>8.2f}s {t:>7.2f}s"
              + (f"  {drop_n} 镜有剩余候选" if drop_n else ""))
    for sid, lst in pool_left:
        for t in lst:
            print(f"   · ep 镜{sid} 候选「{t}」未排入（该镜空区间容量不足）")

    tot = sum(n for _, n, _, _ in stats)
    print(f"合计：{tot} 行填充｜全集最长空窗 max="
          f"{max(w for _, _, w, _ in stats):.2f}s｜平均空窗总 "
          f"{sum(t for _, _, _, t in stats)/len(stats):.2f}s")

    doc = {
        "_readme": ("字幕密度填充清单（人工撰写文案 ＋ 机械推算时码）。"
                    "densify_subtitles.py 只做技术执行：按 D16 cuts 校验挂载区间、"
                    "按 D11 visual_facts 校验锚点、校验重叠/停留/字数，"
                    "然后把行写进 D16。内容由人写，时码由 "
                    "scripts/build_density_fills_U03.py 按 Q100 判据推算。"),
        "_anchor_rule": ("anchor 必须逐字出现在该集该镜的 D11 visual_facts 中；"
                         "这是「不编造画面」的硬约束——字幕只能写画面里已经有的东西。"),
        "_shot_visibility_rule": ("挂载区间必须落在该镜的**真实可见区间**内。"
                                  "本单元 D16 cuts 为 12/25/38 三个段间硬切、无段内并行交叉剪辑，"
                                  "故可见区间＝D11 镜时窗口（0~12/12~25/25~38/38~45）。"),
        "_dwell_rule": ("单行停留 ≥ 该行字数 ÷ 4.5（向上取 0.1s 网格，本厂 D16 既有估算口径），"
                        "且不小于 1.6s；避免用一闪而过的碎行凑覆盖。"),
        "_q100_note": ("【Q100 字幕密度下限 · 2026-10-23 · 分镜导演岗】用户反馈「还是很拖啊，"
                       "白模视频有很长时间什么也没有」。体检（scripts/audit_dead_time.py）实测 "
                       "U03 八集：全集最长空窗 11.00s、平均空窗总 31.91s（45s 里约 71% 的时间"
                       "屏幕无字幕）。判定不用「加台词」：D09 语气卡对陆沉写死「每集不超过 4 句」，"
                       "故改用**画面里的字**（字幕板／面板读数／场景标识），内容逐字锚定 D11 "
                       "visual_facts 已写明的事实，不新增物件、不编数字、不改镜数与镜时。"),
        "_tiers": ("本岗口径：**只用 D16 的「字幕」类型行**承载画面文字；角标是常驻元素不占字幕带；"
                   "对白行时码不动（声音设计岗 D15 的口径）。"),
        "units": {UNIT: out_units},
    }

    out_p = os.path.join(ROOT, "scripts", "density_fills_U03.json")
    if args.dry_run:
        print(f"\n(dry-run) 未写入：{out_p}")
    else:
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"\n已写入：{out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
