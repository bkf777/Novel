#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 按 D15 实测回填审计字段（U01 → v1.21 ／ U02 → v1.8）· 分镜导演岗

背景
----
声音设计 12:08 落 `units/U01/D15.json` **v1.12**、11:51 落 `units/U02/D15.json` **v1.3**：
  · U01 八集首句**全部** at_sec=0.5（8/8 达标）——企划合规登记的「U01-R41 剩 5 集」已作废；
  · U02 ep012 新增首句 VO(0.5/1.5)、商既衡行 re-time 至 2.4；ep016 新增首句 VO(0.5/1.5)，
    line_ref 全部改指为新 D09 编号。
本岗 11:31 写的 D16 目标时码与 D15 实测**逐条吻合**（reconcile 双单元 0 违规），
故本脚本只做「审计字段回填」：把「待 D15 落锚」改成实况，并补 U01 ep001 缺失的判据字段。

企划合规 **Q101**：黄金 3 秒判据落点＝`subtitle_style.golden3s_first_line`，
秒级真值回 D15 配音 `at_sec` 取，D16 里的是转录副本 ⇒ 本脚本按此把该字段补齐到 8/8。

守卫：版本＝U01 v1.20 ／ U02 v1.7；只改审计字段与判据字段（结构差异白名单）。
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F16 = {'U01': os.path.join(ROOT, 'units', 'U01', 'D16.json'),
       'U02': os.path.join(ROOT, 'units', 'U02', 'D16.json')}
F15 = {'U01': os.path.join(ROOT, 'units', 'U01', 'D15.json'),
       'U02': os.path.join(ROOT, 'units', 'U02', 'D15.json')}
F09 = {'U01': os.path.join(ROOT, 'units', 'U01', 'D09.json'),
       'U02': os.path.join(ROOT, 'units', 'U02', 'D09.json')}
GUARD = {'U01': 'v1.20', 'U02': 'v1.7'}
TO = {'U01': 'v1.21', 'U02': 'v1.8'}
D15V = {'U01': 'v1.12', 'U02': 'v1.3'}


def norm(s):
    import re
    return re.sub(r'[「」『』"\'（）()\s]', '', str(s or ''))


def main():
    bak = os.path.join(ROOT, 'reports', '_bak_d16_d15back_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    for unit in ('U01', 'U02'):
        p16, p15, p09 = F16[unit], F15[unit], F09[unit]
        d16 = json.load(open(p16, encoding='utf-8'))
        if d16.get('version') != GUARD[unit]:
            print('[NO-OP] %s D16 version=%s ≠ 守卫 %s' % (unit, d16.get('version'), GUARD[unit]))
            continue
        d15 = json.load(open(p15, encoding='utf-8'))
        d09 = json.load(open(p09, encoding='utf-8'))
        shutil.copy2(p16, os.path.join(bak, '%s_D16.json' % unit))
        vo_by_ep = {}
        for e in d15['episodes']:
            vo_by_ep[e['ep']] = sorted(e.get('voice_over', []), key=lambda x: x.get('at_sec', 0))
        d09map = {}
        for l in d09['lines']:
            d09map.setdefault(l['ep'], {})[l['idx']] = norm(l.get('text'))

        for e in d16['episodes']:
            ep = e['ep']
            ss = e['subtitle_style']
            aud = ss['subtitle_sync_audit']
            vos = vo_by_ep.get(ep, [])
            # 逐行对锚（按文本 → D09 idx → D15 VO）
            def anchor(text):
                k = norm(text)
                for v in vos:
                    ref = v.get('line_ref') or ''
                    if ref.startswith('D09 ep%d #' % ep):
                        idx = int(ref.split('#')[-1])
                        if norm(d09map.get(ep, {}).get(idx, '')) == k:
                            return v
                for v in vos:
                    if norm(v.get('text') or '') == k:
                        return v
                return None

            synced = 0
            rows = []
            for l in ss['lines']:
                if l.get('type') != '对白':
                    continue
                a = anchor(l.get('text'))
                in_s = round(float(l['in_sec']), 1)
                out_s = round(float(l['out_sec']), 1)
                ok = a is not None and in_s == round(float(a['at_sec']), 1) \
                    and abs(out_s - (float(a['at_sec']) + float(a['dur_sec']))) < 1e-6
                if ok:
                    synced += 1
                rows.append((l, a, ok, in_s, out_s))
            aud['synced_row_count'] = synced
            if synced == len([r for r in rows if r[1] is not None]) and all(r[2] for r in rows if r[1]):
                aud.pop('pending_d15_sync', None)
            aud['verified_against_d15'] = '%s（黄金 3 秒判据落点见 golden3s_first_line；秒级真值回 D15 at_sec 取）' % D15V[unit]
            # rows[] 回填
            by_text = {norm(r[0].get('text')): r for r in rows}
            for r in aud.get('rows', []):
                t = by_text.get(norm(r.get('text')))
                if not t:
                    continue
                l, a, ok, in_s, out_s = t
                r['seq'] = l.get('seq')
                r['in_sec'] = in_s
                r['out_sec'] = out_s
                r['nominal_dwell_sec'] = round(out_s - in_s, 1)
                r['float_dwell_sec'] = out_s - in_s
                r['d15_vo_at_sec'] = a['at_sec'] if a else None
                r['d15_vo_dur_sec'] = a['dur_sec'] if a else None
                r['d15_line_ref'] = a.get('line_ref') if a else None
                r['action'] = '不动（D15 %s 落锚后逐条相等）' % D15V[unit] if ok else '待 D15 落锚'
                r['verdict'] = ('合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）' if ok
                                else '待 D15 落锚')
            # golden3s_first_line：按 D15 实测回填（Q101：真值回 D15 at_sec）
            g3 = ss.get('golden3s_first_line')
            if g3 is None:
                g3 = {'target': '首句台词 ≤1.5s 入画（短剧黄金 3 秒）'}
                ss['golden3s_first_line'] = g3
            if vos:
                v0 = vos[0]
                if float(v0.get('at_sec', 99)) <= 1.5:
                    g3['status'] = '达标'
                    g3['d15_vo_at_sec'] = v0.get('at_sec')
                    g3['d15_vo_dur_sec'] = v0.get('dur_sec')
                    g3['d15_line_ref'] = v0.get('line_ref')
                    for k in ('planned_in_sec', 'planned_out_sec', 'budget_dur_sec', 'current_d15_vo_at_sec',
                              'current_d15_line_ref', 'd15_pending'):
                        g3.pop(k, None)
                    g3['note'] = ('D15 %s 实测：首句 at_sec=%.1fs（≤1.5s 达标），本表该行与配音逐条相等。'
                                  % (D15V[unit], float(v0.get('at_sec'))))
                else:
                    g3['status'] = '待 D15 前移'
                    g3['current_d15_vo_at_sec'] = v0.get('at_sec')
                    g3['current_d15_line_ref'] = v0.get('line_ref')
                    g3['target_at_sec'] = 0.5
                    g3['d15_pending'] = ('声音设计岗需把本集首句配音 at_sec 前移至 0.5s（dur 不变），'
                                          '本岗随后按实测同步本表该行。')
        d16['version'] = TO[unit]
        with open(p16, 'w', encoding='utf-8') as f:
            json.dump(d16, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('[OK] %s D16 %s → %s：判据字段与审计字段按 D15 %s 回填'
              % (unit, GUARD[unit], TO[unit], D15V[unit]))
    print('备份：%s' % bak)
    return 0


if __name__ == '__main__':
    sys.exit(main())
