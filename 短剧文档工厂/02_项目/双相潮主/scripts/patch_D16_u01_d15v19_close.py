#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01 审计字段收口：按 D15 U01 v1.9（11:36 落）刷新实测状态（分镜导演岗）

变化：声音设计 11:36 落 `units/U01/D15.json` v1.9 ——
  ① ep003 新增首句配音「比上一趟早。」at 0.5s／dur 1.5s（本岗 D16 已按该值登记，落定）；
  ② ep003 两条旧配音的 line_ref 由旧编号改指为「D09 ep3 #2」「D09 ep3 #3」；
  ③ 其余集首句 at_sec 未动（ep002 4.5／ep004 5.4／ep005 13.0／ep006 13.0／ep007 4.0／ep008 2.0）。

本脚本做（且只做）：
  ① ep003 的 `golden3s_first_line` 由「本批新增·待 D15 落锚」改为「达标」，并记 D15 实测值；
  ② ep003 的 `subtitle_sync_audit.synced_row_count` 1 → 3，并清空该集 `pending_d15_sync`；
  ③ 8 集的 `verified_against_d15` 版本指针 v1.7 → v1.9；6 集仍待前移的登记原样保留。

守卫：版本＝v1.17；只改上述字段（结构差异白名单）。
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'units', 'U01', 'D16.json')
GUARD = 'v1.17'
TO = 'v1.18'
D15V = 'v1.9'
CLOSE_EP = 3


def main():
    with open(P, 'r', encoding='utf-8') as f:
        d = json.load(f)
    if d.get('version') != GUARD:
        print('[NO-OP] D16 U01 version=%s ≠ 守卫 %s' % (d.get('version'), GUARD))
        return 0
    bak = os.path.join(ROOT, 'reports', '_bak_d16_u01_d15v19_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(P, os.path.join(bak, 'D16.json'))
    before = json.load(open(P, encoding='utf-8'))

    n = 0
    for e in d['episodes']:
        ss = e['subtitle_style']
        aud = ss['subtitle_sync_audit']
        aud['verified_against_d15'] = '%s（黄金 3 秒改版待落锚项见 pending_d15_sync）' % D15V
        n += 1
        if e['ep'] == CLOSE_EP:
            g3 = ss['golden3s_first_line']
            g3['status'] = '达标'
            g3.pop('planned_in_sec', None)
            g3.pop('planned_out_sec', None)
            g3.pop('budget_dur_sec', None)
            g3.pop('d15_pending', None)
            g3['d15_vo_at_sec'] = 0.5
            g3['d15_vo_dur_sec'] = 1.5
            g3['d15_line_ref'] = 'D09 ep3 #1'
            g3['note'] = ('D15 U01 v1.9 已落该句配音（at 0.5s／dur 1.5s），本表该行 0.5~2.0s 与之逐条相等；'
                          '首句以画外音入画，第 0 帧给青灰双生雾气。')
            aud['synced_row_count'] = 3
            aud.pop('pending_d15_sync', None)
            for r in aud.get('rows', []):
                if r.get('text') == '比上一趟早。':
                    r['d15_vo_at_sec'] = 0.5
                    r['d15_vo_dur_sec'] = 1.5
                    r['d15_line_ref'] = 'D09 ep3 #1'
                    r['action'] = '不动（D15 v1.9 落锚后逐条相等）'
                    r['verdict'] = '合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）'
                elif r.get('text') in ('九小时。', '腕子上这个，是它给的？'):
                    r['verdict'] = '合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）'
                    r['action'] = '不动（按 D15 v1.9 改指后的 line_ref 复核一致）'
            aud['verified_note'] = (aud.get('verified_note', '') +
                                    '｜【D15 U01 v1.9 落锚 · 2026-10-23】本集首句「比上一趟早。」已由 D15 '
                                    '新增配音（at 0.5s／dur 1.5s，line_ref「D09 ep3 #1」）承接，'
                                    '另两条旧配音的 line_ref 已由旧编号改指为「D09 ep3 #2」「D09 ep3 #3」；'
                                    '本表三行对白（0.5~2.0／16.4~17.7／30.5~33.2）与 D15 逐条严格相等，'
                                    '本集 pending_d15_sync 清空。')
    d['version'] = TO

    # 结构差异白名单
    illegal = []
    for e_b, e_a in zip(before['episodes'], d['episodes']):
        for k in e_b:
            if k == 'shots' or k in ('subtitle_style',):
                continue
            if e_b[k] != e_a.get(k):
                illegal.append(('ep%s' % e_b['ep'], k))
        for k_b, k_a in (('subtitle_style', 'subtitle_style'),):
            a, b = e_b[k_b], e_a[k_a]
            for sk in a:
                if sk in ('lines', 'golden3s_first_line', 'subtitle_sync_audit'):
                    continue
                if a[sk] != b.get(sk):
                    illegal.append(('ep%s' % e_b['ep'], 'subtitle_style.%s' % sk))
    if illegal:
        print('[ABORT] 结构差异越界：%s' % illegal)
        return 1

    with open(P, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('[OK] D16 U01 %s → %s：ep003 落锚收口，8 集 D15 版本指针刷新为 %s' % (GUARD, TO, D15V))
    print('备份：%s' % bak)
    return 0


if __name__ == '__main__':
    sys.exit(main())
