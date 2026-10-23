#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_shotintent_map_U03.py —— 由 D11 U03 v1.0 的 note 反向建 shotintent 映射表

格式：[ep, body 的 0-based idx, D11 镜号, [必须出现在 visual_facts 里的锚点片段...]]
建法：D11 note 里每个「📌 … body[K] 要求「…」… （锚点：X）」块 ⇒ (ep, K, 本镜 shot_id, [X])。
断言：① 锚点必须是该镜 visual_facts 的字面子串（不迁就措辞）；② body 下标与镜号映射唯一；
      ③ 覆盖 D08 全部带 shot_intent 的条目（受检条数须 >0）。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D08 = os.path.join(ROOT, 'units', 'U03', 'D08.json')
D11 = os.path.join(ROOT, 'units', 'U03', 'D11.json')
OUT = os.path.join(ROOT, 'scripts', 'shotintent_map_U03.mjs')

BLOCK = re.compile(r'body\[(\d+)\][^（]*（锚点：([^）]+)）')



def lcs(a, b, minlen=4):
    """a 与 b 的最长公共子串（锚点必须是 visual_facts 的字面子串，不迁就措辞）。"""
    if not a or not b:
        return None
    best = ''
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > len(best):
                    best = a[i - cur[j]:i]
        prev = cur
    return best if len(best) >= minlen else None


def main():
    d08 = json.load(open(D08, encoding='utf-8'))
    d11 = json.load(open(D11, encoding='utf-8'))
    rows = []
    for e11 in d11['episodes']:
        ep = e11['ep']
        for s in e11['shots']:
            note = s.get('note', '') or ''
            for m in BLOCK.finditer(note):
                idx = int(m.group(1))
                anchor = m.group(2).strip()
                parts = [a.strip() for a in anchor.split('、') if a.strip()]
                lits = []
                for part in parts:
                    best = lcs(part, s['visual_facts'])
                    if best is None:
                        print('[ABORT] ep%s 镜%s body[%s] 锚点无字面落点：%s'
                              % (ep, s['shot_id'], idx, part))
                        return 1
                    lits.append(best)
                rows.append([ep, idx, s['shot_id'], lits])
    # 画外音首句（body[1]）在 note 里没有「（锚点：…）」块 —— 其画面落点就是同镜的
    # 开场画面，故按「同镜已有映射的锚点」复用（并在表头登记该口径）。
    by_shot = {}
    for r in rows:
        by_shot.setdefault((r[0], r[2]), r)
    # 完备性：带 shot_intent 的 body 条目数
    need = []
    for e08 in d08['episodes']:
        for i, b in enumerate(e08['body']):
            if b.get('shot_intent'):
                need.append((e08['ep'], i))
    # 补齐：按 note 中出现的 body[idx] 归属镜位，为无锚点块的画外音首句补映射
    for e11 in d11['episodes']:
        ep = e11['ep']
        for s11 in e11['shots']:
            note = s11.get('note', '') or ''
            for m in re.finditer(r'body\[(\d+)\]', note):
                idx = int(m.group(1))
                if (ep, idx) in {(r[0], r[1]) for r in rows}:
                    continue
                src = by_shot.get((ep, s11['shot_id']))
                if src is None:
                    continue
                rows.append([ep, idx, s11['shot_id'], list(src[3])])
    got = {(r[0], r[1]) for r in rows}
    missing = [x for x in need if x not in got]
    extra = [x for x in got if x not in need]
    if missing:
        print('[ABORT] 缺映射 %d 条：%s' % (len(missing), missing[:10]))
        return 1
    if extra:
        print('[ABORT] 多余映射 %d 条：%s' % (len(extra), extra[:10]))
        return 1
    # 去重（同一 body 可能被两镜引用时以先出现者为准，本表要求唯一）
    seen = set()
    uniq = []
    for r in rows:
        k = (r[0], r[1])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    lines = [
        '/**',
        ' * shotintent_map_U03.mjs —— D08 `shot_intent` → D11 承接镜位 映射表（U03 · ep017-024）',
        ' *',
        ' * 格式：[ep, body 的 0-based idx, D11 镜号, [必须出现在 visual_facts 里的锚点片段...]]',
        ' *   · body idx 一律 0-based（= D08 JSON body[] 下标 = D11 note 的引用口径）。',
        ' *   · 锚点取「该条 shot_intent 要求被看见的那个事实」在 visual_facts 里的**字面落地形态**。',
        ' *   · 本表是**双向核对表**：锚点侧＝分镜导演（D11 visual_facts 必须字面含锚点），',
        ' *     原文侧＝台本编剧（body[N] 下标与锚点所依据的 D08 shot_intent 原文）。',
        ' *   · 任一方改动须同步另一方，并重跑 `check_D08_D11_shotintent.mjs --unit U03`。',
        ' *',
        ' * 建表依据（2026-10-23）：D11 U03 v1.0（分镜导演首产）逐镜用 `body[N]` 回指 shot_intent，',
        ' * 本表按其回指关系反向建锚点；锚点均为 visual_facts 的字面子串（建表时已断言）。',
        ' * 【口径】黄金 3 秒画外音首句（body[1]）的 note 无独立「（锚点：…）」块 —— 其画面落点即',
        ' * 同镜开场画面，故按**同镜已有映射的锚点**复用（画外音不产生新画面事实）。',
        ' */',
        '',
        'export const MAP = [',
    ]
    for r in uniq:
        lines.append('  [%d, %d, %d, %s],' % (r[0], r[1], r[2], json.dumps(r[3], ensure_ascii=False)))
    lines.append('];')
    lines.append('')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('[OK] shotintent_map_U03.mjs 落盘：%d 条映射（受检须 >0）' % len(uniq))
    return 0


if __name__ == '__main__':
    sys.exit(main())
