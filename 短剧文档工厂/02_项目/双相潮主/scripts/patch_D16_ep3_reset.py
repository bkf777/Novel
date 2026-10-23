#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01 ep003 对白行复位（被 sync_D16_dialogue_to_D15.py 按旧 line_ref 错配后的修复）· 分镜导演岗

事故经过
--------
2026-10-23 11:2x 并发补位批次运行 `scripts/sync_D16_dialogue_to_D15.py`（--unit U01）。
该脚本按「D16 对白行文本 → D09 同文行 idx → D15 该 idx 的 voice_over」配对；
但 **D15 U01 v1.7 的 `line_ref` 仍指 D08 v1.13 插入新首句之前的旧编号**
（D08 v1.13 在 body[1] 插入「比上一趟早。」后，D09 ep003 的 idx 整体后移一位）：

  旧编号（D15 现值）   at/dur      实际台词（现行 D09）
  D09 ep3 #1          16.4/1.3    九小时。            ← 现为 D09 ep3 #2
  D09 ep3 #2          30.5/2.7    腕子上这个，是它给的？ ← 现为 D09 ep3 #3

⇒ 脚本把「九小时。」错配到 30.5~33.2（实为「腕子上这个」的配音），
   又因重叠自检「后行让位」把「腕子上这个」推到 33.2~34.4（dur 被压到 1.2s）。

本脚本把两行按 **D15 现有配音实测时长对应的原时码**复位，并把错误引文改掉：
  「九小时。」                16.4~17.7（dur 1.3）
  「腕子上这个，是它给的？」  30.5~33.2（dur 2.7）

⛔ 根治条件（声音设计岗）：D15 U01 v1.7 的 ep003 两条 `line_ref` 须改指
   「D09 ep3 #2」「D09 ep3 #3」，并为新首句「比上一趟早。」新增一条 at 0.5s 的 voice_over；
   改指前**禁止**再跑 `sync_D16_dialogue_to_D15.py`，否则同样错配会复现。

守卫：版本＝v1.16；内容指纹＝「九小时。」「腕子上这个，是它给的？」两行存在且时码为错配值；
只改这两行的 in_sec／out_sec／note；结构差异白名单＝(ep3, seq4/seq5, in_sec/out_sec/note)。
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'units', 'U01', 'D16.json')
GUARD = 'v1.16'
TO = 'v1.17'

FIX = {
    '九小时。': (16.4, 17.7,
                 '【黄金 3 秒改版 · 2026-10-23 · 复位】本行时码已按 D15 U01 v1.7 现有配音复位为 '
                 '16.4~17.7s（dur 1.3s）。⚠️ D15 的 line_ref 仍指 D08 插入新首句前的旧编号'
                 '（现应为「D09 ep3 #2」），声音设计岗改指前禁止再跑 sync_D16_dialogue_to_D15.py，'
                 '否则本行会被错配到 30.5s。'),
    '腕子上这个，是它给的？': (30.5, 33.2,
                 '【黄金 3 秒改版 · 2026-10-23 · 复位】本行时码已按 D15 U01 v1.7 现有配音复位为 '
                 '30.5~33.2s（dur 2.7s）。⚠️ D15 的 line_ref 仍指旧编号（现应为「D09 ep3 #3」），'
                 '此前被同步脚本按旧编号错配并让位压到 33.2~34.4s，现已复位。'),
}


def main():
    with open(P, 'r', encoding='utf-8') as f:
        d = json.load(f)
    if d.get('version') != GUARD:
        print('[NO-OP] D16 U01 version=%s ≠ 守卫 %s' % (d.get('version'), GUARD))
        return 0
    bak = os.path.join(ROOT, 'reports', '_bak_d16_ep3_reset_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(P, os.path.join(bak, 'D16.json'))

    hit = 0
    for e in d['episodes']:
        if e['ep'] != 3:
            continue
        for l in e['subtitle_style']['lines']:
            if l.get('type') != '对白':
                continue
            for text, (i_s, o_s, note) in FIX.items():
                if l.get('text') != text:
                    continue
                l['in_sec'] = i_s
                l['out_sec'] = o_s
                l['note'] = note
                hit += 1
    if hit != len(FIX):
        print('[ABORT] 复位命中 %d/%d' % (hit, len(FIX)))
        return 1
    d['version'] = TO
    with open(P, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('[OK] D16 U01 %s → %s，复位 %d 行' % (GUARD, TO, hit))
    print('备份：%s' % bak)
    return 0


if __name__ == '__main__':
    sys.exit(main())
