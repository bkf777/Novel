#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 · 黄金 3 秒改版（U01 ep002–008 ／ U02 ep009–016）· 分镜导演岗

为什么做
--------
用户裁决「短剧要有黄金 3 秒、不能像小说铺陈」在 U01 ep001 已落地（片头四行撤出正文区、
改由片尾 43~45s 承担；首句 0.5s 入画），但**其余 15 集仍是旧口径**：
0.0~2.0s 正文区压着「剧名／节目编号／〔待平台给出〕／〔待定〕署名／AI 标识」四行，
既含半成品信息，又把最贵的 2 秒占掉；而台本编剧 11:19 落 D08/D09 v1.11/v1.7（U01）、
v1.7/v1.3（U02）后，ep003／ep012／ep016 各多了一句首句台词，须在剪辑层落位。

本脚本做（且只做）四件事
------------------------
① **片头四行撤出**：15 集统一改为「正文区无片头文字层」＋ 四行整体移至片尾 43~45s 标题层
   （对齐 U01 ep001 v1.13 已落口径），`title_card.head` / `tail` / `compliance` 同步改写。
② **3 句新首句落位**：ep003「比上一趟早。」／ep012「贡献是谁定的。」／ep016「十四天，今晚到。」
   各按 0.5s 入画入表（画外音，首句预算 1.5s，待 D15 落锚复核）。
③ **连带重排**：ep012 商既衡行 0.4→2.4s（让位给陆沉首句，D15 待 re-time）；
   ep016 两行面板文字 1.0~2.8／2.8~4.6 → 2.2~4.0／4.0~5.8（让位，无配音锚点，纯字幕层）。
④ **审计字段重算**：`subtitle_sync_audit.synced_row_count` / `dwell_floor_rows` / `rows[]`
   全部按新行集重算，并新增 `pending_d15_sync`（待声音设计落锚清单）＋ `golden3s_first_line`
   （黄金 3 秒首句时码口径）＋ `sync_records` 事件条目。

不碰
----
D08／D09／D11／D12／D13／D14／D15／D18／项目索引；不改 `cuts` / `transitions`（四段制与镜时零改动）；
**U01 ep001 不在本脚本改动面内**（并发补位批次正在同步其 D16↔D15，本岗只补登记 golden3s 字段）。

⛔ 落盘后必须先改 D15 再跑 `scripts/sync_D16_dialogue_to_D15.py`
   —— D15 U01 ep3／U02 ep12／U02 ep16 的 `line_ref` 仍指 D08 改写前的旧 idx，
   该脚本按「D09 同文 → idx → D15 VO」配对，会把新首句行错配到 16.4s／0.4s／12.4s。

不生成图片/视频/音频，不合成 TTS/BGM，不提交 H3 付费生成，不投流上架。
"""
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {'U01': os.path.join(ROOT, 'units', 'U01', 'D16.json'),
         'U02': os.path.join(ROOT, 'units', 'U02', 'D16.json')}
D15F = {'U01': os.path.join(ROOT, 'units', 'U01', 'D15.json'),
        'U02': os.path.join(ROOT, 'units', 'U02', 'D15.json')}
GUARD = {'U01': 'v1.15', 'U02': 'v1.6'}
TO = {'U01': 'v1.16', 'U02': 'v1.7'}

# 本批改动面（ep 列表）：U01 跳过 ep001（并发批次在办）
SCOPE = {'U01': [2, 3, 4, 5, 6, 7, 8], 'U02': [9, 10, 11, 12, 13, 14, 15, 16]}

TAIL_CONTENT = '节目编号：〔待平台给出〕　编剧：〔待定〕　导演：〔待定〕　《双相潮主》　本片由人工智能生成'
TAIL_NOTE = '片头四行（剧名／编号位／署名／AI 标识）自本版起统一移至片尾；编号不可自编（D03 §7.3）'
AI_DISCLOSURE = ('AI 生成标识义务由**全片右下角常驻角标「AI 生成」**（本集各镜 visual_facts 逐镜声明、'
                 'D12 对应卡 negatives 逐卡声明）＋**片尾字幕「本片由人工智能生成」**承担；'
                 '片头不再重复大字（D03 R09 要求的是常驻明显位置标识，角标已在；'
                 '片头大字既重复又占掉最贵的 2 秒）')
CHECKLIST = '剧名／编号位／署名／AI 标识 四项**齐备但统一在片尾 43~45s 呈现**'
HEAD_BASIS = ('短剧黄金 3 秒：第 0 帧必须是「已经出事的画面」，不能是环境铺陈，也不能是字幕板；'
              '四行片头原本占掉 0~2s，且含「〔待平台给出〕」「〔待定〕」等半成品信息，劝退观众。')
TRACE = ('【黄金 3 秒改版 · 2026-10-23】本集片头四行（剧名／节目编号／署名／AI 标识）从 0.0~2.0s '
         '正文区**全部撤出**，改由片尾 43~45s 标题层承担；正文区字幕行整体重排（seq 重编）；'
         '首句入画时码见本表 `golden3s_first_line`。')

# 新首句（0.5s 入画，画外音，预算 1.5s）
HOOK = {
    ('U01', 3): {'text': '比上一趟早。', 'char_id': 'LC', 'in': 0.5, 'out': 2.0, 'shot_id': 1,
                 'si': '本集首句台词，以画外音在开场镜入画：重生信息前置，灰雾提前即本集钩子。'},
    ('U02', 12): {'text': '贡献是谁定的。', 'char_id': 'LC', 'in': 0.5, 'out': 2.0, 'shot_id': 1,
                  'si': '本集首句台词，以画外音在开场镜入画：把全服公告变成对他的审判。'},
    ('U02', 16): {'text': '十四天，今晚到。', 'char_id': 'LC', 'in': 0.5, 'out': 2.0, 'shot_id': 1,
                  'si': '本集首句台词，以画外音在开场镜入画：开场即把期限与火绑在一起。'},
}

# 连带重排（ep → 行的匹配前缀 → (in, out)）
RESEAT = {
    ('U02', 12): [('请把人数换算成成本', 2.4, 7.1)],
    ('U02', 16): [('归档大限日：十四天大限', 2.2, 4.0), ('逾期未处理的灰斑开始异化', 4.0, 5.8)],
}


def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def dump(p, d):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')


def norm(s):
    return re.sub(r'[「」『』"\'（）()\s]', '', str(s or ''))


def vo_index(d15, ep):
    """ep → {D09 idx: (at, dur, line_ref)}"""
    d09 = load(os.path.join(ROOT, 'units', 'U01' if False else '', 'x')) if False else None
    return {}


def first_vo(d15, ep):
    vos = [v for v in next(e for e in d15['episodes'] if e['ep'] == ep).get('voice_over', [])]
    if not vos:
        return None
    return min(vos, key=lambda v: v.get('at_sec', 0))


def main():
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bak = os.path.join(ROOT, 'reports', '_bak_d16_golden3s_%s' % stamp)
    os.makedirs(bak, exist_ok=True)
    report = []

    for unit in ('U01', 'U02'):
        path = FILES[unit]
        d16 = load(path)
        if d16.get('version') != GUARD[unit]:
            print('[NO-OP] %s D16 version=%s ≠ 守卫 %s（盘面已演进，不写盘）'
                  % (unit, d16.get('version'), GUARD[unit]))
            continue
        d15 = load(D15F[unit])
        d15v = d15.get('version')
        shutil.copy2(path, os.path.join(bak, '%s_D16.json' % unit))
        before = load(path)

        for e in d16['episodes']:
            ep = e['ep']
            if ep not in SCOPE[unit]:
                continue
            tc = e['title_card']
            ss = e['subtitle_style']
            lines = ss.get('lines', [])

            # ① 撤片头四行
            head_rows = [l for l in lines if l.get('type') == '片头']
            if head_rows:
                lines = [l for l in lines if l.get('type') != '片头']
            # 片尾行：补「节目编号」＋ note
            for l in lines:
                if l.get('type') == '片尾':
                    l['text'] = TAIL_CONTENT
                    l['note'] = TAIL_NOTE
            # ② 新首句行
            hook = HOOK.get((unit, ep))
            if hook:
                lines.insert(0, {
                    'seq': 0, 'type': '对白', 'char_id': hook['char_id'], 'text': hook['text'],
                    'in_sec': hook['in'], 'out_sec': hook['out'], 'shot_id': hook['shot_id'],
                    'note': ('【黄金 3 秒】首句台词，第 %.1fs 入画（画外音，不出画）；预算时长 %.1fs，'
                             '待声音设计岗 TTS 实测后按「out_sec ＝ 配音 at_sec＋dur_sec」复核。'
                             'D08 shot_intent：%s' % (hook['in'], hook['out'] - hook['in'], hook['si']))
                })
            # ③ 连带重排
            for prefix, i_s, o_s in RESEAT.get((unit, ep), []):
                hit = 0
                for l in lines:
                    if l.get('type') in ('角标', '片尾', '片头'):
                        continue
                    if norm(l.get('text')).startswith(norm(prefix)):
                        l['in_sec'] = i_s
                        l['out_sec'] = o_s
                        l['note'] = (l.get('note', '') +
                                     '｜【黄金 3 秒改版】本行让位给首句台词后移，'
                                     '目标时码 %.1f~%.1fs；D15 现值仍为旧锚点，待声音设计岗 re-time。'
                                     % (i_s, o_s)).strip('｜')
                        hit += 1
                if hit != 1:
                    print('[ABORT] %s ep%s 重排行「%s」命中 %d 次' % (unit, ep, prefix, hit))
                    return 1
            # seq 重编
            for i, l in enumerate(lines, start=1):
                l['seq'] = i
            ss['lines'] = lines

            # ① title_card 改写
            ff = tc.get('head', {}).get('first_frame', '')
            ff = ff.replace('，不是黑场', '，非黑场').replace('，非黑场', '，非黑场')
            if not ff.endswith('无文字层'):
                ff = ff + '、无文字层'
            tc['head'] = {
                'in_sec': 0, 'out_sec': 0,
                'form': ('**不做片头文字层**——剧名／节目编号／编剧导演署名／AI 标识四行全部撤出正文区，'
                         '改由片尾 43~45s 标题层承担；第 0 帧直接给画面本身'),
                'layout': '无。画面上部带区（画面高度 6%~20%）在本集不承载任何文字',
                'fade': '无文字层，故无淡入淡出；画面本身无淡入淡出',
                'first_frame': ff,
                'basis': HEAD_BASIS,
            }
            tail = tc.setdefault('tail', {})
            tail['content'] = TAIL_CONTENT
            comp = tc.setdefault('compliance', {})
            comp['ai_disclosure'] = AI_DISCLOSURE
            comp['title_items_checklist'] = CHECKLIST

            # ④ 审计字段重算
            audit = ss.setdefault('subtitle_sync_audit', {})
            vo_by_ep = {}
            for e15 in d15['episodes']:
                if e15['ep'] != ep:
                    continue
                for v in e15.get('voice_over', []):
                    vo_by_ep.setdefault(norm(v.get('text') or ''), []).append(v)
            # 用 line_ref → D09 idx 反查文字（D15 的 line_ref 可能是旧编号，故两路都试）
            d09 = load(os.path.join(ROOT, 'units', unit, 'D09.json'))
            d09map = {l['idx']: norm(l.get('text')) for l in d09['lines'] if l['ep'] == ep}
            vo_by_ref = {}
            for e15 in d15['episodes']:
                if e15['ep'] != ep:
                    continue
                for v in e15.get('voice_over', []):
                    ref = v.get('line_ref') or ''
                    m = re.search(r'#(\d+)$', ref)
                    if m:
                        vo_by_ref[norm(d09map.get(int(m.group(1)), ''))] = v
            vo_by_text = {}
            for e15 in d15['episodes']:
                if e15['ep'] != ep:
                    continue
                for v in e15.get('voice_over', []):
                    vo_by_text.setdefault(norm(v.get('text') or ''), v)

            def anchor_for(text):
                k = norm(text)
                v = vo_by_text.get(k)
                if v is None:
                    v = vo_by_ref.get(k)
                return v

            synced = 0
            no_vo = 0
            floor = []
            rows = []
            pending = []
            for l in lines:
                t = l.get('type')
                if t == '对白':
                    a = anchor_for(l.get('text'))
                    in_s = round(float(l['in_sec']), 1)
                    out_s = round(float(l['out_sec']), 1)
                    if a is not None and in_s == round(float(a['at_sec']), 1) \
                            and abs(out_s - (float(a['at_sec']) + float(a['dur_sec']))) < 1e-6:
                        synced += 1
                        verdict = '合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）'
                    else:
                        verdict = '待 D15 落锚（本行时码为黄金 3 秒目标值，尚未与 D15 锚点对齐）'
                        pending.append({
                            'text': l.get('text'), 'type': '对白', 'shot_id': l.get('shot_id'),
                            'row_in_sec': in_s, 'row_out_sec': out_s,
                            'd15_current_anchor': (None if a is None else
                                                   {'at_sec': a['at_sec'], 'dur_sec': a['dur_sec'],
                                                    'line_ref': a.get('line_ref')}),
                            'action': '待声音设计岗落 D15 后由本岗按实测复核',
                        })
                    dwell = round(out_s - in_s, 1)
                    entry = {
                        'seq': l.get('seq'), 'type': '对白', 'text': l.get('text'),
                        'char_id': l.get('char_id'), 'shot_id': l.get('shot_id'),
                        'in_sec': in_s, 'out_sec': out_s,
                        'nominal_dwell_sec': dwell, 'float_dwell_sec': out_s - in_s,
                        'd15_vo_at_sec': (a['at_sec'] if a else None),
                        'd15_vo_dur_sec': (a['dur_sec'] if a else None),
                        'd15_line_ref': (a.get('line_ref') if a else None),
                        'action': ('不动' if a and verdict.startswith('合规') else '本批新增/改期，待 D15 落锚'),
                        'verdict': verdict,
                        'note': l.get('note', ''),
                    }
                    rows.append(entry)
                    if abs(dwell - 1.2) < 1e-6:
                        floor.append({'seq': l.get('seq'), 'text': l.get('text'),
                                      'in_sec': in_s, 'out_sec': out_s,
                                      'nominal_dwell_sec': 1.2, 'float_dwell_sec': out_s - in_s})
                elif t == '面板文字':
                    no_vo += 1
            audit['synced_row_count'] = synced
            audit['no_vo_anchor_rows'] = no_vo
            if floor:
                audit['dwell_floor_rows'] = floor
            else:
                audit.pop('dwell_floor_rows', None)
            audit['rows'] = rows
            if pending:
                audit['pending_d15_sync'] = pending
            else:
                audit.pop('pending_d15_sync', None)
            audit['verified_against_d15'] = '%s（含黄金 3 秒改版待落锚项，见 pending_d15_sync）' % d15v
            audit['verified_note'] = (audit.get('verified_note', '') +
                                      '｜【黄金 3 秒改版 · 2026-10-23】本集片头四行撤出正文区，'
                                      '改由片尾 43~45s 标题层承担；首句台词行按 0.5s 入画登记为预算值，'
                                      '待声音设计岗 D15 落锚后按实测复核。')

            # golden3s_first_line
            fv = first_vo(d15, ep)
            hook = HOOK.get((unit, ep))
            if hook:
                g3 = {'target': '首句台词 ≤1.5s 入画（短剧黄金 3 秒）', 'status': '本批新增 · 待 D15 落锚',
                      'text': hook['text'], 'planned_in_sec': hook['in'], 'planned_out_sec': hook['out'],
                      'budget_dur_sec': round(hook['out'] - hook['in'], 1),
                      'delivery': '画外音（人物不出画，首帧给最强符号）',
                      'd15_pending': ('声音设计岗需为该句新增 voice_over（at_sec 0.5、dur_sec 按实测），'
                                      '并按新 D09 编号修正本集既有 line_ref。')}
            elif fv and fv.get('at_sec', 99) <= 1.5:
                g3 = {'target': '首句台词 ≤1.5s 入画（短剧黄金 3 秒）', 'status': '达标',
                      'd15_vo_at_sec': fv.get('at_sec'), 'd15_vo_dur_sec': fv.get('dur_sec'),
                      'd15_line_ref': fv.get('line_ref')}
            else:
                g3 = {'target': '首句台词 ≤1.5s 入画（短剧黄金 3 秒）', 'status': '待 D15 前移',
                      'current_d15_vo_at_sec': fv.get('at_sec') if fv else None,
                      'current_d15_line_ref': fv.get('line_ref') if fv else None,
                      'target_at_sec': 0.5,
                      'd15_pending': ('声音设计岗需把本集首句配音 at_sec 前移至 0.5s（dur 不变），'
                                      '本岗随后按实测同步本表该行。')}
            ss['golden3s_first_line'] = g3
            # 口径留痕
            ss['dwell_calc_convention'] = ss.get('dwell_calc_convention', '') + '｜' + TRACE
            audit.setdefault('sync_records', []).append({
                'date': '2026-10-23', 'event': '黄金 3 秒改版（片头四行撤出正文区 → 片尾 43~45s 标题层）',
                'basis': '用户裁决「短剧要有黄金 3 秒」＋ D08/D09 v1.11/v1.7（U01）、v1.7/v1.3（U02）新增首句台词',
                'interval_rule': 'Q51 左闭右开；out_sec == 下一条 in_sec 视为相接，不算重叠',
                'changes': ['title_card.head 改为「不做片头文字层」', 'title_card.tail 补 content（四行合并）',
                            'compliance.ai_disclosure 改口径（角标＋片尾承担 AI 标识）',
                            'subtitle_style.lines 删 4 条片头行并重编 seq',
                            '新增 golden3s_first_line ＋ pending_d15_sync'],
                'not_changed': ['cuts / transitions 四段制与镜时零改动', '角标行与片尾行时码零改动',
                                'D11 景别/机位/镜时零改动（景别是 V12 白模构图闸基准，不得漂移）'],
                'applied_by': '分镜导演（bot_1855d6ce9cdd）',
            })
            report.append('%s ep%s：片头四行撤出；首句行 %s' % (
                unit, ep, '新增 0.5s（待 D15 落锚）' if hook else
                ('达标 %.1fs' % fv['at_sec'] if fv and fv.get('at_sec', 99) <= 1.5 else
                 '待 D15 前移（现 %.1fs）' % (fv['at_sec'] if fv else -1))))

        d16['version'] = TO[unit]
        dump(path, d16)
        print('[OK] %s D16 %s → %s' % (unit, GUARD[unit], TO[unit]))

    print('备份目录：%s' % bak)
    for r in report:
        print('  · %s' % r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
