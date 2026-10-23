#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 三处引文同步到 D08 现行 shot_intent 原文（分镜导演岗）

起因：D08 终版（U01 v1.13／U02 v1.7，11:27）把新首句的 shot_intent 改写为
「本集首句台词，以画外音在开场镜入画：…」，与本岗 11:28 落盘时引用的旧措辞不同
⇒ D11 note 的引文与现行 D08 不一致（check_D08_D11_shotintent.mjs 报「引文与现行 body[N] 不匹配」）。

本脚本只改 3 处 note 的引文文字（不改动 D11 任何镜头参数、不改 dialogue/visual_facts）。
守卫：D11 U01 ＝ v1.12、D11 U02 ＝ v1.8；旧串指纹唯一命中；结构差异白名单＝note。
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {'U01': os.path.join(ROOT, 'units', 'U01', 'D11.json'),
         'U02': os.path.join(ROOT, 'units', 'U02', 'D11.json')}
GUARD = {'U01': 'v1.12', 'U02': 'v1.8'}
TO = {'U01': 'v1.13', 'U02': 'v1.9'}

# (ep, shot_id, old 引文片段, new 引文片段)
EDITS = {
    'U01': [
        (3, 1, '「这句对照必须在第 1 秒被听见：重生信息前置到开场，灰雾提前本身就是本集钩子。」',
         '「本集首句台词，以画外音在开场镜入画：重生信息前置，灰雾提前即本集钩子。秒码由 D15/D16 承接。」'),
    ],
    'U02': [
        (12, 1, '「这句质疑必须与公告出现同帧——它把「全服公告」从背景变成对他的审判。」',
         '「本集首句台词，以画外音在开场镜入画：把全服公告变成对他的审判。画面内不给发言人。」'),
        (16, 1, '「这句必须与面板大限提醒同帧，第 1 秒就把「期限」与「火」绑在一起。」',
         '「本集首句台词，以画外音在开场镜入画：开场即把期限与火绑在一起。画面内不出陆沉。」'),
    ],
}


def main():
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bak = os.path.join(ROOT, 'reports', '_bak_d11_si_sync_%s' % stamp)
    os.makedirs(bak, exist_ok=True)
    for unit in ('U01', 'U02'):
        p = FILES[unit]
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if d.get('version') != GUARD[unit]:
            print('[NO-OP] %s D11 version=%s ≠ 守卫 %s' % (unit, d.get('version'), GUARD[unit]))
            continue
        shutil.copy2(p, os.path.join(bak, '%s_D11.json' % unit))
        n = 0
        for (ep_no, shot_id, old, new) in EDITS[unit]:
            hit = 0
            for e in d['episodes']:
                if e['ep'] != ep_no:
                    continue
                for s in e['shots']:
                    if s['shot_id'] != shot_id:
                        continue
                    note = s.get('note', '')
                    if old not in note:
                        print('[ABORT] %s ep%s 镜%s 引文指纹未命中' % (unit, ep_no, shot_id))
                        return 1
                    if note.count(old) != 1:
                        print('[ABORT] %s ep%s 镜%s 引文指纹非唯一' % (unit, ep_no, shot_id))
                        return 1
                    s['note'] = note.replace(old, new)
                    hit += 1
            if hit != 1:
                print('[ABORT] %s ep%s 镜%s 命中 %d 次' % (unit, ep_no, shot_id, hit))
                return 1
            n += 1
        d['version'] = TO[unit]
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('[OK] %s D11 %s → %s（引文同步 %d 处）' % (unit, GUARD[unit], TO[unit], n))
    print('备份：%s' % bak)
    return 0


if __name__ == '__main__':
    sys.exit(main())
