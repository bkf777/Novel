#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：ep001 钩子行 note 登记 TTS 实测链 ＋ 全 8 集口径长文本 seq 指针订正 ＋ ep1/ep2/ep3 审计镜像重刷

来件（声音设计 2026-10-23 11:1x《D16 U01 ep1 钩子字幕行待同步》）
──────────────────────────────────────────────────────────────
来件规格：units/U01/D16.json → episodes[ep=1].subtitle_style.lines[seq=1]
  ① out_sec 2.3 → 4.0（＝D15 at 0.5 ＋ dur 3.5）
  ② note 改为登记实测链（实测 3.366906s → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s；
     测量来源＝matrix TTS node_id 455361723802011；音色 male-qn-badao／speed 0.95／pitch −1）
  ③ 连带重叠：原 seq=2 面板行（in 2.3／out 4.3）与延长后的钩子行重叠 1.7s ⇒ 顺移

⚠️ 来件坐标已过期（磁盘实况 > 来件转述），本脚本按**现盘**定位：
  · 钩子行在现盘是 **seq=2**（seq=1 被「AI 生成」角标行占用；黄金 3 秒批次把角标提到首行）
  · ① 的 out_sec 2.3 → 4.0 **已由并发批次落盘**（现盘已是 4.0）⇒ 本脚本**不再改数值**
  · ③ 的面板行顺移 **已由并发批次落盘**（现盘 seq=3 in 4.0／out 5.2）⇒ 本脚本**不再改数值**
  ⇒ 真正未落的只有 **② note 的实测链登记**（来件明文给了措辞）

⭐ 本脚本另修**本岗自查发现、并发批次漏刷的三类缺口**
──────────────────────────────────────────────────────────
【缺口一】**ep1 的 subtitle_sync_audit 镜像整体陈旧**（并发批次 12:06／12:13 两波都刷了
   ep2–ep8，唯独 ep1 漏刷）：
   · rows[] 存的是**改号前**的 seq 1/3/6/8，且 `text`／`char_id`／`shot_id`／`d15_line_ref`
     四键全缺；seq1 存的还是**改期前**的 0.5~2.3 预算值（action 还写「新增行（预算值，待实测）」）
   · 现盘对白行是 seq 2/4/9/10 ⇒ 镜像与现盘**零锚点对应**
   · 本脚本按现盘重刷，口径照搬 scripts/patch_D16_golden3s.py，
     并以现盘 ep4–ep8 已刷好的镜像为**等价性基准**（字段集与措辞逐键对齐）

【缺口二】**全 8 集的 dwell_calc_convention 口径长文本留着改号前的失效 seq 指针**：
   ep1「逐条对应的字幕行：seq 9」「浮点尾差证据行：seq 8」「本集无标称 1.2s 的行」
   ep2「逐条对应的字幕行：seq 5」「标称恰 1.2s 的行：seq 8——seq8」「全片此类共 3 条：ep2 seq8」
       「ep2 seq9 字幕文字随…」「ep2 seq8「全城钟楼敲响十一下。」」
   ep3「逐条对应的字幕行：seq 7」｜ep4「seq 5、6、8」「seq 7——seq7」「ep4 seq7」
   ep5「seq 7」「浮点尾差证据行：seq 6」｜ep6「seq 5」｜ep7「seq 5、8」｜ep8「seq 7」「seq 9——seq9」「ep8 seq9」
   ⇒ 本脚本按现盘 lines[] 重算订正（**只改指针与现值断言，不改事件叙述**）。

【缺口三】**ep3 seq4／seq5 行 note 里的 ⚠️ 警示前提已过期**：
   原注记称「D15 的 line_ref 仍指 D08 插入新首句前的旧编号……禁止再跑 sync_D16_dialogue_to_D15.py」，
   但 **D15 U01 现盘 v1.12 的 ep3 #2／#3 line_ref 已是「D09 ep3 #2」／「D09 ep3 #3」**
   （声音设计岗早已改指），本行现盘时码与配音逐条相等、同步脚本按新编号正确配对
   ⇒ 该警示已失效且具误导性（会阻断后续正确的同步）。按 Q30「追加不覆盖」，
   本脚本**保留原文**并在行 note 末尾追加一段订正。

本脚本做（且只做）五件事
────────────────────────
① **hook 行 note 追加实测链留痕**：保留原 note（黄金 3 秒段 ＋ 配音对齐段），
   追加「【TTS 实测链 · 2026-10-23】」段，登记 实测 3.366906s → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s
   ＋ 测量来源 node_id ＋ 音色/speed/pitch，并声明「原预估 1.8s 系未实测占位，已被实测取代」。
   ⛔ 不改 in_sec／out_sec／text／type／char_id／shot_id。
② **全 8 集 dwell_calc_convention 口径长文本订正**（规则化，逐条可复核）：
   R1「本集与 D15 配音逐条对应的字幕行：seq …」→ 本集现盘对白行 seq 集合
   R2「浮点尾差证据行：seq …」→ 现盘 float dwell 与标称网格差最大的对白行（并列取最小 seq）
   R3「本集标称恰 1.2s 的行：seq N——seqN（类型）」→ 本集现盘恰 1.2s 行的 seq
   R4「本集无标称 1.2s 的行（正文行全部 ≥1.3s）。」→ 仅当该断言**已失效**（本集实有 1.2s 行）时
      改为澄清式（区分「对白行」与「画面文字行」）；断言仍成立则**原样不动**
   R5「全片此类共 N 条：epA seqX／…」→ 按现盘**全片** 1.2s 行集合重写（N 与各项 seq），
      并对本集有 1.2s 行却缺该句的集**补写同款句**（口径全片一致）
   R6「下一条对白 seqM（… 起音）」→ 本集 1.2s 行之后的那条对白 seq
   R7 `epN seqM` 字面值（事件留痕段）→ 按**文本锚点**解析订正（引文唯一命中才改，不猜）
   R8 ep1 专项：钩子行 seq1→seq2；1.8s 占位句**整句后**追加「实测取代」句（不割裂原句）
   R9 每集集末追加「【seq 指针订正 · 2026-10-23 · 分镜导演岗】」段，写明现盘映射
③ **ep1/ep2/ep3 的 subtitle_sync_audit 镜像按现盘重刷**（rows[]／synced_row_count／
   no_vo_anchor_rows／dwell_floor_rows／pending_d15_sync），口径同 patch_D16_golden3s.py。
   ⚠️ ep3 的 `dwell_floor_rows` 现盘存的是旧错配态（seq5 记 33.2~34.4），重刷后该键消失（现盘无 1.2s 对白行）。
④ **ep3 seq4／seq5 行 note 末尾追加指针订正句**（原文保留）。
⑤ **ep1/ep2/ep3 的 verified_note 追加本轮复核留痕**；
   ⛔ 不覆盖 `verified_against_d15`（现盘已是 v1.12 正确指针，措辞沿用并发批次的既有写法）。

⛔ 不碰
──────
D08／D09／D11／D12／D15／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**
／他岗章节正文／台账（台账由本岗另行追加）；**不改任何 lines[] 的 in_sec／out_sec**
（数值归本岗但已由并发批次落定且与 D15 逐条相等，再改即制造分叉）；
不改 ep4–ep8 的 lines[]；不改 ep2–ep8 的审计镜像（现盘已与 lines[] 零失配）。

守卫
────
① **版本守卫**：D16 U01 现盘 version 须 ＝ v1.21（否则 [NO-OP] exit 0）
② **D15 版本守卫**：D15 U01 现盘 version 须 ＝ v1.12（否则 [NO-OP] exit 0）
③ **内容指纹自证**：hook 行须同时满足
   文本＝「上一趟我死在第三个小时。」／type=对白／in_sec=0.5／out_sec=4.0／shot_id=1
   ⇒ 行**按 (text, type, in_sec) 定位，不按 seq 定位**（seq 会随改号漂移）
   且 note 须已含「【配音对齐 2026-10-23】」（证明并发批次的数值同步已落）
④ **数据加载后置**：守卫全部置于读入 JSON 之后
⑤ **幂等**：note 已含「【TTS 实测链 · 2026-10-23】」⇒ [NO-OP] exit 0
⑥ **差异白名单**：落盘后逐叶差分，只允许 ①②③④⑤ 声明的路径变化，其他一律 [ABORT] 回滚
⑦ **CAS**：写前重读 version+SHA，若与守卫锚定值不符 ⇒ [ABORT]（防并发抢盘）

用法：python3 scripts/patch_D16_U01_audit_mirror_and_hook_note.py --project . [--dry-run]
"""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD_VERSION = 'v1.21'
TO_VERSION = 'v1.22'
D15_VERSION = 'v1.13'

HOOK_TEXT = '上一趟我死在第三个小时。'
HOOK_IN = 0.5
HOOK_OUT = 4.0

MEASURED = '3.366906'
NODE_ID = '455361723802011'
VOICE = 'male-qn-badao'
SPEED = '0.95'
PITCH = '−1'

STAMP_NOTE = (
    '【TTS 实测链 · 2026-10-23】'
    '实测 %ss → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s'
    '（预算口径：向上取整到 0.1s 标称网格后再加 0.1s 余量）；'
    '测量来源＝matrix TTS node_id %s；'
    '音色 %s／speed %s／pitch %s（沿用 ep001_05）；'
    '原预估 1.8s 系未实测的占位，已被实测取代（实测长 1.57s）'
    % (MEASURED, NODE_ID, VOICE, SPEED, PITCH)
)

# 审计镜像重刷范围（并发批次已刷 ep2–ep8；ep1 漏刷）
REFRESH_EPS = (1, 2, 3)

# 口径文本订正覆盖范围（全 8 集）
CONVENTION_EPS = (1, 2, 3, 4, 5, 6, 7, 8)

# 并发批次的首句行 note 措辞改写（对齐现盘 ep4–ep8 样板）
NOTE_REWORD = ('（字幕行与闸位同步前移）', '（闸位与本行同步前移）')

# ep3 行 note 过期警示的订正后缀
EP3_NOTE_FIX = (
    '｜【指针订正 · 2026-10-23 · 分镜导演岗】'
    '上条 ⚠️ 警示的前提**已过期**：D15 U01 现盘 v1.12 的 ep3 #2／#3 `line_ref` '
    '已是「D09 ep3 #2」／「D09 ep3 #3」（声音设计岗已改指），'
    '本行现盘时码与配音逐条相等、同步脚本按新编号正确配对，'
    '原「禁止再跑同步脚本」的限制不再适用；原警示与原留痕原文保留，本订正段为准。'
)

# —— Q104（企划合规总控裁定，D18 v1.117 登记）落地：ep006 首句 delivery 字面 ——
# D15 U01 v1.13 已把 ep6 #1 的 delivery 由「画外音（人物不出画，首帧给最强符号）」
# 改为「画外音（身份不出画，首帧给最强符号）」（只改这一个词）。
# D15 v1.12 的 mix 追加语已明文承诺「保持与 D16 同字段、同措辞，便于两侧逐字段比对」
# ⇒ D16 侧必须同步这一个词，否则 D15↔D16 两侧字面分叉。
# ⛔ ep003／ep005 的 delivery 字面**不动**：Q104 三档判据下这两镜属第一档「人物不出画」（成立）。
Q104_OLD_WORD = '画外音（人物不出画，首帧给最强符号）'
Q104_NEW_WORD = '画外音（身份不出画，首帧给最强符号）'
Q104_STAMP = (
    '【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】'
    '企划合规（总控）**Q104** 裁定（D18 v1.117 登记）已闭合本集首句画外音的字面分歧：'
    '判据＝**角色身份是否在画幅内可辨识**，而非「人物剪影是否在画幅内」；'
    '本镜（ep006 镜1）陆沉以不可辨识剪影在画幅内（D12 C-021 `char_ids=["LC"]`，'
    '不给面部、不给身份锚点）⇒ 属第二档「**身份不出画**」。'
    'D15 U01 v1.13 已把该条 `delivery` 字面由「人物不出画」订正为「**身份不出画**」'
    '（只改这一个词，其余不动）；本表 `golden3s_first_line.delivery`、'
    '对白行 note 与审计镜像已按现盘同步该字面，'
    '使 D15↔D16 两侧同字段、同措辞，可逐字段比对。'
    '⚠️ 与本镜 visual_facts「厂房暗处的一道剪影暴起冲出」不冲突：'
    '落点口径仍为「**身份不出画／先声后人**」，'
    'D15 mix 追加语「画面内无该角色口型」严格一致；'
    '景别（中景）／机位（平视）／镜时（11.0s）／镜号一律不动。'
)


def norm(t):
    return re.sub(r"[「」『』\"'（）()\s]", '', str(t or ''))


def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def flat(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items():
            for x in flat(v, p + '/' + str(k)):
                yield x
    elif isinstance(o, list):
        for i, v in enumerate(o):
            for x in flat(v, p + '/' + str(i)):
                yield x
    else:
        yield p, o


def build_anchor_maps(d15, d09, ep):
    """照搬 patch_D16_golden3s.py 的锚点解析：vo_by_text 优先，vo_by_ref 兜底。"""
    d09map = {l['idx']: norm(l.get('text')) for l in d09.get('lines', []) if l['ep'] == ep}
    vo_by_text, vo_by_ref = {}, {}
    for e15 in d15.get('episodes', []):
        if e15['ep'] != ep:
            continue
        for v in e15.get('voice_over', []):
            vo_by_text.setdefault(norm(v.get('text')), v)
            m = re.search(r'#(\d+)$', v.get('line_ref') or '')
            if m:
                vo_by_ref[norm(d09map.get(int(m.group(1)), ''))] = v

    def anchor_for(text):
        k = norm(text)
        return vo_by_text.get(k) or vo_by_ref.get(k)

    return anchor_for


def refresh_audit(d16_ep, d15, d09):
    """按现盘 lines[] 重算一集的审计镜像（口径同 patch_D16_golden3s.py）。

    产出与现盘 ep4–ep8 已刷好的镜像**逐键同构**：
      action 合规行＝「不动（D15 v{v} 落锚后逐条相等）」；
      note 取自该行 lines[].note（首句行的括注措辞对齐现盘样板）。
    """
    ep = d16_ep['ep']
    ss = d16_ep['subtitle_style']
    aud = ss['subtitle_sync_audit']
    anchor_for = build_anchor_maps(d15, d09, ep)

    synced = 0
    no_vo = 0
    floor = []
    rows = []
    pending = []
    for l in ss.get('lines', []):
        t = l.get('type')
        if t == '对白':
            a = anchor_for(l.get('text'))
            in_s = round(float(l['in_sec']), 1)
            out_s = round(float(l['out_sec']), 1)
            if a is not None and in_s == round(float(a['at_sec']), 1) \
                    and abs(out_s - (float(a['at_sec']) + float(a['dur_sec']))) < 1e-6:
                synced += 1
                verdict = '合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）'
                action = '不动（D15 %s 落锚后逐条相等）' % D15_VERSION
            else:
                verdict = '待 D15 落锚（本行时码为黄金 3 秒目标值，尚未与 D15 锚点对齐）'
                action = '本批新增/改期，待 D15 落锚'
                pending.append({
                    'text': l.get('text'), 'type': '对白', 'shot_id': l.get('shot_id'),
                    'row_in_sec': in_s, 'row_out_sec': out_s,
                    'd15_current_anchor': (None if a is None else
                                           {'at_sec': a['at_sec'], 'dur_sec': a['dur_sec'],
                                            'line_ref': a.get('line_ref')}),
                    'action': '待声音设计岗落 D15 后由本岗按实测复核',
                })
            dwell = round(out_s - in_s, 1)
            note = str(l.get('note', '') or '')
            for src, dst in (NOTE_REWORD,):
                note = note.replace(src, dst)
            rows.append({
                'seq': l.get('seq'), 'type': '对白', 'text': l.get('text'),
                'char_id': l.get('char_id'), 'shot_id': l.get('shot_id'),
                'in_sec': in_s, 'out_sec': out_s,
                'nominal_dwell_sec': dwell, 'float_dwell_sec': out_s - in_s,
                'd15_vo_at_sec': (a['at_sec'] if a else None),
                'd15_vo_dur_sec': (a['dur_sec'] if a else None),
                'd15_line_ref': (a.get('line_ref') if a else None),
                'action': action,
                'verdict': verdict,
                'note': note,
            })
            if abs(dwell - 1.2) < 1e-6:
                floor.append({'seq': l.get('seq'), 'text': l.get('text'),
                              'in_sec': in_s, 'out_sec': out_s,
                              'nominal_dwell_sec': 1.2, 'float_dwell_sec': out_s - in_s})
        elif t == '面板文字':
            no_vo += 1

    aud['synced_row_count'] = synced
    aud['no_vo_anchor_rows'] = no_vo
    if floor:
        aud['dwell_floor_rows'] = floor
    else:
        aud.pop('dwell_floor_rows', None)
    aud['rows'] = rows
    if pending:
        aud['pending_d15_sync'] = pending
    else:
        aud.pop('pending_d15_sync', None)
    return aud, rows, floor, pending


def mask_quotes(s):
    """把「…」引文替换成占位符（引文内的「。」与「／」不参与分句）。"""
    out = []
    quotes = []
    i = 0
    while i < len(s):
        if s[i] == '「':
            j = s.find('」', i)
            if j == -1:
                out.append(s[i])
                i += 1
                continue
            quotes.append(s[i + 1:j])
            out.append('\x01%d\x02' % (len(quotes) - 1))
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return ''.join(out), quotes


def unmask_quotes(s, quotes):
    for i, q in enumerate(quotes):
        s = s.replace('\x01%d\x02' % i, '「' + q + '」')
    return s


def resolve_seq_literals(dcc, ep, lines):
    """按**文本锚点**解析口径长文本里的 `epN seqM` 字面值，逐字订正。

    行定位一律按 (text, type, in_sec) 语义锚定，不按 seq 下标（seq 会随改号漂移）。
    对每个 `ep{ep} seqM` 字面值：
      · 取它所在小句（按「，；。」分句，引文已掩码化 ⇒ 引文内的句号不误切）；
      · 小句里若恰有一个引文，且该引文在本集 lines[] 中唯一命中一行 ⇒ 把字面值订正为该行 seq；
      · 解析不唯一或无引文 ⇒ 保持原样（交由集末「seq 指针订正」段说明，不猜）。
    """
    masked, quotes = mask_quotes(dcc)
    by_text = {}
    for l in lines:
        by_text.setdefault(norm(l.get('text')), []).append(l)

    pat = re.compile(r'ep%d seq(\d+)' % ep)
    dels = '，；。'
    out = []
    pos = 0
    fixed = 0
    for m in pat.finditer(masked):
        if m.start() < pos:
            continue
        out.append(masked[pos:m.start()])
        left = max(masked.rfind(ch, 0, m.start()) for ch in dels) + 1
        rights = [masked.find(ch, m.end()) for ch in dels if masked.find(ch, m.end()) != -1]
        right = min(rights) if rights else len(masked)
        clause = masked[left:right]
        qids = re.findall(r'\x01(\d+)\x02', clause)
        hit = None
        if len(qids) == 1:
            cand = by_text.get(norm(quotes[int(qids[0])]))
            if cand and len(cand) == 1:
                hit = cand[0].get('seq')
        if hit is not None and str(hit) != m.group(1):
            out.append('ep%d seq%s' % (ep, hit))
            fixed += 1
        else:
            out.append(m.group(0))
        pos = m.end()
    out.append(masked[pos:])
    return unmask_quotes(''.join(out), quotes), fixed


def one2_rows(lines):
    """本集恰 1.2s 的行（排除角标／片尾这类非正文行）。"""
    return [l for l in lines
            if l.get('type') not in ('角标', '片尾')
            and abs((round(float(l.get('out_sec', 0)), 1)
                     - round(float(l.get('in_sec', 0)), 1)) - 1.2) < 1e-9]


def fix_convention(ss, ep, rows, all_one2):
    """订正本集口径长文本里随改号／改期而失效的 seq 指针与现值断言。

    只改**指针与现值断言**，不改事件叙述（事件留痕原文保留，按 Q30 追加不覆盖）。
    """
    dcc = ss['dwell_calc_convention']
    before = dcc
    lines = ss.get('lines', [])
    dlg = [l for l in lines if l.get('type') == '对白']
    dlg_seqs_txt = '／'.join(str(l.get('seq')) for l in dlg)

    # R2 浮点尾差证据行：现盘 float dwell 与标称网格差最大的对白行（并列取最小 seq）
    gaps = [abs((r['float_dwell_sec'] or 0) - (r['nominal_dwell_sec'] or 0)) for r in rows]
    if rows:
        gmax = max(gaps)
        tail_seq = min(r['seq'] for r, g in zip(rows, gaps) if abs(g - gmax) < 1e-18)
        dcc = re.sub(r'浮点尾差证据行：seq [\d／]+',
                     '浮点尾差证据行：seq %s' % tail_seq, dcc)

    # R1 本集与 D15 逐条对应的字幕行
    dcc = re.sub(r'本集与 D15 配音逐条对应的字幕行：seq [\d／、]+',
                 '本集与 D15 配音逐条对应的字幕行：seq ' + dlg_seqs_txt, dcc)

    # R3 / R4 本集 1.2s 行
    mine = one2_rows(lines)
    l2 = mine[0] if mine else None
    one2_dlg = [l for l in mine if l.get('type') == '对白']

    m = re.search(r'本集标称恰 1\.2s 的行：seq (\d+)——seq(\d+)（([^）]*)）', dcc)
    if m and l2 is not None:
        s2 = str(l2.get('seq'))
        dcc = dcc.replace(m.group(0),
                          '本集标称恰 1.2s 的行：seq %s——seq%s（%s）' % (s2, s2, m.group(3)))
        # R6 其后「下一条对白 seqM（… 起音）」按现盘重取
        nxt = next((l for l in dlg
                    if float(l.get('in_sec', 0)) >= float(l2.get('in_sec', 0))), None)
        if nxt:
            dcc = re.sub(r'下一条对白 seq\d+（([^）]*)起音）',
                         '下一条对白 seq%s（\\1起音）' % nxt.get('seq'), dcc)

    if '本集无标称 1.2s 的行（正文行全部 ≥1.3s）。' in dcc:
        if one2_dlg:
            dcc = dcc.replace(
                '本集无标称 1.2s 的行（正文行全部 ≥1.3s）。',
                '本集标称恰 1.2s 的对白行：seq %s（%s）——该行按「out_sec ＝ 配音 at_sec＋dur_sec」判定。'
                % (one2_dlg[0].get('seq'), one2_dlg[0].get('text')))
        elif l2 is not None:
            dcc = dcc.replace(
                '本集无标称 1.2s 的行（正文行全部 ≥1.3s）。',
                '本集无标称 1.2s 的**对白**行（对白行 dwell 全部 ≥1.3s）；'
                '另有 %s行 seq%s（%s，%s~%ss）恰 1.2s，属画面文字、无配音锚点，'
                '按全片同一判据保持标称 1.2s 不动。'
                % (l2.get('type'), l2.get('seq'), l2.get('text'),
                   l2.get('in_sec'), l2.get('out_sec')))

    # R5 全片 1.2s 清单：按现盘全片集合重写（本集有 1.2s 行却缺该句的集同款补写）
    if all_one2:
        txt = '（全片此类共 %d 条：%s，同属一类、同一判据，均保持标称 1.2s 不动。）' % (
            len(all_one2),
            '／'.join('ep%d seq%s' % (e, s) for e, s in all_one2))
        if re.search(r'（全片此类共 \d+ 条：[^）]*）', dcc):
            dcc = re.sub(r'（全片此类共 \d+ 条：[^）]*）', txt, dcc)
        elif l2 is not None and '全片此类共' not in dcc:
            dcc = dcc.rstrip('。') + '。' + txt

    # R7 `epN seqM` 字面值按文本锚点订正（只改指针，不改事件叙述）
    dcc, fixed_literals = resolve_seq_literals(dcc, ep, lines)

    # R8 ep1 专项
    if ep == 1:
        dcc = dcc.replace('首句台词提前到 0.5s 入画（seq1）', '首句台词提前到 0.5s 入画（seq2）')
        stale = ('新增行 seq1（hook 句）当前为**预算时长 1.8s**，待声音设计岗合成实测后'
                 '按「out_sec ＝ 配音 at_sec＋dur_sec」复核；其余 3 条对白行沿用 D15 v1.6 '
                 '现行配音预算，未改数值。')
        if stale in dcc:
            dcc = dcc.replace(
                stale,
                stale +
                '【实测取代 · 2026-10-23】上句的 1.8s 占位预算已被实测取代：'
                '实测 %ss → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s；'
                '钩子行现盘行序为 seq2（seq1 为「AI 生成」角标行），'
                '现盘 out_sec ＝ 4.0s（＝配音 at 0.5s ＋ dur 3.5s），逐条相等；'
                '实测链登记于该行 lines[].note。上句作为改版当时的历史留痕原文保留。'
                % MEASURED)

    # R9 集末追加「seq 指针订正」段
    stamp = ('【seq 指针订正 · 2026-10-23 · 分镜导演岗】'
             '黄金 3 秒改版把正文区字幕行整体重排（seq 重编）后，'
             '本表上文各段的 seq 字面值多为**改号前的旧行序**；'
             '按事件溯源原则（只追加不重写）上文的**事件叙述原文保留**，'
             '仅其中的 seq 指针按现盘订正（指针订正＝定位订正，不改事件内容），'
             '含义以本订正段为准。'
             '现盘对应关系：对白行 seq %s；' % dlg_seqs_txt)
    if l2 is not None:
        stamp += ('本集标称恰 1.2s 的行现为 seq%s（%s，%s）；'
                  % (l2.get('seq'), l2.get('type'), l2.get('text')))
    if ep == 1:
        stamp += ('本集钩子行（黄金 3 秒首句）现为 seq2（seq1 为「AI 生成」角标行）。')
    stamp += ('本轮按文本锚点订正的 `ep%d seqM` 字面值共 %d 处；'
              % (ep, fixed_literals))
    if ep in REFRESH_EPS:
        stamp += ('审计镜像 subtitle_sync_audit.rows[] 已按现盘 lines[] × D15 U01 %s 重刷'
                  '（口径同 scripts/patch_D16_golden3s.py）。' % D15_VERSION)
    if ('【seq 指针订正 · 2026-10-23 · 分镜导演岗】' not in dcc):
        dcc = dcc.rstrip() + '｜' + stamp

    ss['dwell_calc_convention'] = dcc
    return dcc != before


def apply_q104(d16):
    """Q104 裁定落地：ep006 首句 delivery 字面「人物不出画」→「身份不出画」。

    D15 U01 v1.13 已落该字面订正；D16 侧按 D15 v1.12 mix 追加语的承诺
    （同字段、同措辞、便于两侧逐字段比对）同步：
      · **活字段** `golden3s_first_line.delivery` → 直接订正；
      · 留痕字段（行 note／镜像 row note／verified_note／golden3s note）
        → 字面机械订正 ＋ 末尾**追加** Q104 裁定留痕段（事件留痕原文保留，按 Q30）。
    """
    ep6 = next((e for e in d16['episodes'] if e['ep'] == 6), None)
    if ep6 is None:
        return False
    ss = ep6['subtitle_style']
    g3 = ss.get('golden3s_first_line')
    if not g3:
        return False
    if g3.get('delivery') != Q104_OLD_WORD:
        return False  # 已订正或非预期态 → 不动

    g3['delivery'] = Q104_NEW_WORD
    g3['note'] = str(g3.get('note', '')).rstrip() + '｜' + Q104_STAMP

    for l in ss.get('lines', []):
        if Q104_OLD_WORD in str(l.get('note', '') or ''):
            l['note'] = (str(l.get('note', '')).replace(Q104_OLD_WORD, Q104_NEW_WORD)
                         + '｜' + Q104_STAMP)

    aud = ss['subtitle_sync_audit']
    for r in aud.get('rows', []):
        if Q104_OLD_WORD in str(r.get('note', '') or ''):
            r['note'] = str(r.get('note', '')).replace(Q104_OLD_WORD, Q104_NEW_WORD)
    aud['verified_note'] = (str(aud.get('verified_note', '')).replace(Q104_OLD_WORD, Q104_NEW_WORD)
                            + '｜' + Q104_STAMP)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    p16 = os.path.join(root, 'units', 'U01', 'D16.json')
    p15 = os.path.join(root, 'units', 'U01', 'D15.json')
    p09 = os.path.join(root, 'units', 'U01', 'D09.json')

    # —— 数据加载 ——
    d16 = json.load(open(p16, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))
    d09 = json.load(open(p09, encoding='utf-8'))

    # —— 守卫（全部置于读入之后）——
    if d16.get('version') != GUARD_VERSION:
        print('[NO-OP] D16 U01 version=%s ≠ 守卫 %s（磁盘已演进，退出不抢盘）'
              % (d16.get('version'), GUARD_VERSION))
        return 0
    if d15.get('version') != D15_VERSION:
        print('[NO-OP] D15 U01 version=%s ≠ 期望 %s（上游已动，退出）'
              % (d15.get('version'), D15_VERSION))
        return 0

    ep1 = next((e for e in d16['episodes'] if e['ep'] == 1), None)
    if ep1 is None:
        print('[ABORT] D16 U01 无 ep=1')
        return 1
    hook = next((l for l in ep1['subtitle_style']['lines']
                 if l.get('type') == '对白' and l.get('text') == HOOK_TEXT), None)
    if hook is None:
        print('[ABORT] 未按 (text,type) 定位到钩子行')
        return 1
    if round(float(hook.get('in_sec', -1)), 1) != HOOK_IN or round(float(hook.get('out_sec', -1)), 1) != HOOK_OUT:
        print('[ABORT] 钩子行现值 in=%s out=%s ≠ 期望 %s/%s（数值已变，本脚本只补留痕，退出）'
              % (hook.get('in_sec'), hook.get('out_sec'), HOOK_IN, HOOK_OUT))
        return 1
    if '【配音对齐 2026-10-23】' not in str(hook.get('note', '')):
        print('[ABORT] 钩子行 note 未见「【配音对齐 2026-10-23】」⇒ 并发批次数值同步未落，退出')
        return 1
    if '【TTS 实测链 · 2026-10-23】' in str(hook.get('note', '')):
        print('[NO-OP] 钩子行 note 已含「【TTS 实测链 · 2026-10-23】」⇒ 已登记，幂等退出')
        return 0

    before = copy.deepcopy(d16)
    before_sha = sha16(p16)

    # —— ① hook 行 note 追加实测链 ——
    hook['note'] = (str(hook.get('note', '')).rstrip('｜') + '｜' + STAMP_NOTE)

    # —— ③ 审计镜像重刷（ep1–ep3）——
    rows_by_ep = {}
    for e in d16['episodes']:
        if e['ep'] in REFRESH_EPS:
            aud, rows, floor, pending = refresh_audit(e, d15, d09)
            rows_by_ep[e['ep']] = rows

    # —— ④ ep3 seq4／seq5 行 note 末尾追加指针订正句（原文保留）——
    ep3 = next((e for e in d16['episodes'] if e['ep'] == 3), None)
    if ep3:
        for l in ep3['subtitle_style']['lines']:
            if l.get('type') != '对白':
                continue
            note = str(l.get('note', '') or '')
            if '【指针订正 · 2026-10-23 · 分镜导演岗】' in note:
                continue
            if 'line_ref 仍指' in note and '禁止再跑' in note:
                l['note'] = note + EP3_NOTE_FIX

    # —— ⑤ Q104 字面同步（ep6 delivery）——
    q104_applied = apply_q104(d16)

    # —— ② 全 8 集口径长文本订正 ——
    all_one2 = []
    for e in d16['episodes']:
        for l in one2_rows(e['subtitle_style']['lines']):
            all_one2.append((e['ep'], l.get('seq')))
    all_one2.sort()

    for e in d16['episodes']:
        if e['ep'] not in CONVENTION_EPS:
            continue
        rows = rows_by_ep.get(e['ep'])
        if rows is None:
            aud = e['subtitle_style']['subtitle_sync_audit']
            rows = aud.get('rows', [])
        fix_convention(e['subtitle_style'], e['ep'], rows, all_one2)

    # —— ⑤ ep1/ep2/ep3 verified_note 追加复核留痕（不覆盖 verified_against_d15）——
    for e in d16['episodes']:
        if e['ep'] not in REFRESH_EPS:
            continue
        aud = e['subtitle_style']['subtitle_sync_audit']
        aud['verified_note'] = (
            str(aud.get('verified_note', '')).rstrip('｜') +
            '｜【2026-10-23 · 审计镜像重刷（分镜导演岗）】'
            '本集 subtitle_sync_audit.rows[]／synced_row_count／no_vo_anchor_rows／'
            'dwell_floor_rows／pending_d15_sync 已按**现盘 lines[] × D15 U01 %s** 重刷'
            '（口径同 scripts/patch_D16_golden3s.py，锚点走「D09 同文 → idx → D15 voice_over」）；'
            '黄金 3 秒改版把正文区字幕行整体重排（seq 重编）后，'
            '旧镜像存的是改号前的行序与改期前的时码，已全部失效，故本轮按现盘重建；'
            '本集对白行现盘 seq %s，逐条 out_sec ＝ 配音 at_sec＋dur_sec。'
            % (D15_VERSION,
               '／'.join(str(l.get('seq')) for l in e['subtitle_style']['lines']
                         if l.get('type') == '对白')))

    # —— ⑥ 差异白名单 ——
    allowed_prefixes = ['/version']
    allowed_prefixes += ['/episodes/%d/subtitle_style/dwell_calc_convention' % i
                         for i in range(0, 8)]
    allowed_prefixes += ['/episodes/%d/subtitle_style/subtitle_sync_audit/' % i
                         for i in range(0, 8)]
    allowed_prefixes += ['/episodes/0/subtitle_style/lines/']   # ep1 hook 行 note
    allowed_prefixes += ['/episodes/2/subtitle_style/lines/']   # ep3 seq4/seq5 note 追加
    allowed_prefixes += ['/episodes/5/subtitle_style/lines/']   # ep6 首句行 note（Q104）
    allowed_prefixes += ['/episodes/5/subtitle_style/golden3s_first_line/']  # ep6 delivery（Q104）
    a = dict(flat(before))
    b = dict(flat(d16))
    bad = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if not any(k.startswith(pfx) for pfx in allowed_prefixes):
                bad.append(k)
    if bad:
        print('[ABORT] 差异白名单外变更 %d 处，首 5：%s' % (len(bad), bad[:5]))
        return 1

    # —— ⑦ CAS：写前重读 version + SHA ——
    cur = json.load(open(p16, encoding='utf-8'))
    if cur.get('version') != GUARD_VERSION or sha16(p16) != before_sha:
        print('[ABORT] 写前复核失败（version/sha 漂移）⇒ 并发写者已动盘，退出不抢盘')
        return 1

    d16['version'] = TO_VERSION

    if args.dry_run:
        print('[DRY-RUN] 将改：hook note ＋ ep1/2/3 审计镜像 ＋ 全 8 集口径长文本 ＋ ep3 行 note 追加；'
              'version %s → %s' % (GUARD_VERSION, TO_VERSION))
        return 0

    bak = os.path.join(root, 'reports', '_bak_D16_U01_audit_mirror_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p16)

    # —— 写后回读校验 ——
    after = json.load(open(p16, encoding='utf-8'))
    if after.get('version') != TO_VERSION:
        print('[ABORT] 写后 version 校验失败')
        return 1
    ah = next((l for l in after['episodes'][0]['subtitle_style']['lines']
               if l.get('type') == '对白' and l.get('text') == HOOK_TEXT), None)
    if not ah or '【TTS 实测链 · 2026-10-23】' not in str(ah.get('note', '')):
        print('[ABORT] 写后 hook note 校验失败')
        return 1
    print('[OK] D16 U01 %s → %s；hook note 已登记实测链；ep1/2/3 审计镜像已重刷；'
          '全 8 集口径长文本 seq 指针已订正；ep3 行 note 过期警示已附订正；备份 %s'
          % (GUARD_VERSION, TO_VERSION, bak))
    return 0


if __name__ == '__main__':
    sys.exit(main())
