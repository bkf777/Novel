#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：行级活戳口径统一到 D15 现版本（自适配版 · 随 D15 升版重跑即可）

背景
────
声音设计 13:17:48 落 **D15 U01 v1.14**；并行分镜导演实例 13:45:25 落 **D16 U01 v1.35**，
把 8 集顶层 `verified_against_d15` 刷为 v1.14 ⇒ **但行级口径两分**（本脚本的缺口）：
  · `rows[].action`：**22 条**仍写「不动（D15 **v1.13** 落锚后逐条相等）」（ep3–ep8）
  · `rows[].action`：**8 条**写「不动（D15 **现值** 落锚后逐条相等）」（ep1/ep2，**无版本号**）
    ⇒ 行级「逐条相等」是针对**某一具体 D15 版**的断言，**不写版本号即不可追溯**。
  · `dwell_calc_convention` 现值断言 6 处（ep4/6/7）仍为 **v1.13**
  · `golden3s_first_line.note` 8 集仍为「D15 **v1.13** 实测：」
⇒ 顶层 v1.14 与行级 v1.13／无版本号并存 ⇒ 口径分叉。

本脚本做（且只做）一件事
────────────────────────
把 **行级活戳口径统一到 D15 U01 的现版本**（本脚本运行时从 D15 现盘取，不写死）：
  ① `rows[].action`：v1.13 → 现版本；「D15 现值」→ 现版本（两分合一，8 集同措辞）
  ② `dwell_calc_convention` 现值断言：「D15 现行为 **vX**」「现值仍为 D15 **vX** 现行预算」→ 现版本
  ③ `golden3s_first_line.note`：「D15 vX 实测：」→ 现版本
  ④ 8 集 `verified_note` 追加「【行级活戳口径统一 · …】」段
**只改版本戳，不改任何 in_sec／out_sec／dur_sec／text／shot_id／seq。**

守卫
────
① **D15 现版本守卫**：D15 U01 的 version ＝ 本脚本取到的「现版本」；
   且 D16 8 集顶层 `verified_against_d15` 的版本前缀 **必须等于**该现版本
   （否则说明顶层已被别人刷成别的版 ⇒ 本脚本的行级口径可能不是同一版 ⇒ [ABORT]）
② **改戳前独立复算**：逐行用 D15 现盘复算「out_sec == 配音 at_sec＋dur_sec」
   （按该行 `d15_line_ref` 取 D15 voice_over），**任一处失配 ⇒ [ABORT] 不写盘**
③ **幂等**：四类目标位均已达成 ⇒ [NO-OP] exit 0（结构级比对，不靠计数）
④ **差异白名单**：只允许 version ＋ 8 集 `subtitle_sync_audit` /
   `dwell_calc_convention` / `golden3s_first_line`
⑤ **CAS**（写前重读 version+SHA）⑥ **原子写** ⑦ **写后回读校验**
⑧ **D16 版本守卫**：D16 U01 为 `v1.{minor}` 且 minor ≥ 35（否则 [NO-OP] exit 0）

用法：python3 scripts/patch_D16_U01_row_stamp_realign.py --project . [--dry-run]
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
GUARD_MIN_MINOR = 35

TRACE_MARK = '【行级活戳口径统一 · 2026-10-23 14:0x · 分镜导演岗】'


def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    p16 = os.path.join(root, 'units', 'U01', 'D16.json')
    p15 = os.path.join(root, 'units', 'U01', 'D15.json')

    d16 = json.load(open(p16, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))

    m = re.match(r'^v1\.(\d+)$', str(d16.get('version', '')))
    if not m or int(m.group(1)) < GUARD_MIN_MINOR:
        print('[NO-OP] D16 U01 version=%s 不满足 v1.{minor≥%d}'
              % (d16.get('version'), GUARD_MIN_MINOR))
        return 0
    minor = int(m.group(1))
    to_version = 'v1.%d' % (minor + 1)

    NEW = d15.get('version')          # 现版本（运行时取，不写死）
    if not re.match(r'^v1\.\d+$', str(NEW)):
        print('[ABORT] D15 U01 version=%r 非 v1.x ⇒ 退出' % NEW)
        return 1

    # —— 守卫①：D16 顶层戳必须已等于 D15 现版本 ——
    for e in d16['episodes']:
        top = str(e['subtitle_style']['subtitle_sync_audit'].get('verified_against_d15', ''))
        if not top.startswith(NEW):
            print('[ABORT] ep%s 顶层 `verified_against_d15`=%r 未以 D15 现版本 %s 开头'
                  ' ⇒ 行级与顶层可能不是同一版，拒绝统一' % (e['ep'], top[:20], NEW))
            return 1

    # —— 守卫②：改戳前独立复算 ——
    vos = {e['ep']: {v.get('line_ref'): v for v in e.get('voice_over', [])}
           for e in d15['episodes']}
    bad = []
    for e in d16['episodes']:
        ep = e['ep']
        for r in e['subtitle_style']['subtitle_sync_audit'].get('rows', []):
            ref = r.get('d15_line_ref')
            if ref is None:
                bad.append('ep%d seq%s 无 d15_line_ref' % (ep, r.get('seq')))
                continue
            vo = vos[ep].get(ref)
            if vo is None:
                bad.append('ep%d seq%s line_ref=%r 不在 D15 %s' % (ep, r.get('seq'), ref, NEW))
                continue
            vo_end = round(float(vo['at_sec']) + float(vo['dur_sec']), 1)
            if abs(round(float(r.get('out_sec', -1)), 1) - vo_end) > 1e-9:
                bad.append('ep%d seq%s out_sec=%r ≠ D15 %s %s at+dur=%r'
                           % (ep, r.get('seq'), r.get('out_sec'), NEW, ref, vo_end))
    if bad:
        print('[ABORT] 按 D15 %s 现盘独立复算有 %d 处失配 ⇒ 不得改戳，退出' % (NEW, len(bad)))
        for x in bad[:10]:
            print('   ', x)
        return 1
    print('[OK] 改戳前独立复算：按 D15 %s 现盘逐行「out_sec == at+dur」零失配' % NEW)

    before = copy.deepcopy(d16)
    before_sha = sha16(p16)
    stats = {'action': 0, 'dcc': 0, 'g3s': 0, 'note': 0}

    trace = (
        TRACE_MARK +
        '本集行级活戳口径统一到 **D15 U01 %s**（现版本，运行时从 D15 现盘取，不写死）：'
        '① `rows[].action` 统一为「不动（D15 %s 落锚后逐条相等）」——'
        '此前行级存在**两分**（部分集写旧版号、部分集写「D15 现值」而无版本号）；'
        '「逐条相等」是针对**某一具体 D15 版**的断言，**不写版本号即不可追溯** ⇒ 统一带版本号。'
        '② `dwell_calc_convention` 的现值断言「D15 现行为」「现值仍为 D15」刷为 %s。'
        '③ `golden3s_first_line.note` 的「D15 实测」刷为 %s。'
        '④ 顶层 `verified_against_d15` 已由并行实例刷为 %s，本岗不重复动。'
        '**改戳不改码**：本轮**未改任何 in_sec／out_sec／dur_sec／text／shot_id／seq**；'
        '改戳前已按 D15 %s 现盘逐行独立复算「out_sec == 配音 at_sec＋dur_sec」，**零失配**。'
        '**历史留痕字面一律原文保留**（只追加不重写）。'
        '**后续维护**：D15 每升一版，行级戳需重刷 —— 可直接重跑本脚本（自适配现版本，幂等）。'
        % (NEW, NEW, NEW, NEW, NEW, NEW)
    )

    # —— ① rows[].action ——
    for e in d16['episodes']:
        for r in e['subtitle_style']['subtitle_sync_audit'].get('rows', []):
            act = r.get('action', '')
            new = act
            new = re.sub(r'不动（D15 v1\.\d+ 落锚后逐条相等）',
                         '不动（D15 %s 落锚后逐条相等）' % NEW, new)
            new = new.replace('不动（D15 现值落锚后逐条相等）',
                               '不动（D15 %s 落锚后逐条相等）' % NEW)
            if new != act:
                r['action'] = new
                stats['action'] += 1

    # —— ② dwell_calc_convention 现值断言 ——
    for e in d16['episodes']:
        s = e['subtitle_style'].get('dwell_calc_convention', '')
        if not isinstance(s, str):
            continue
        s2 = re.sub(r'(D15 现行为 )\*\*v1\.\d+\*\*', r'\g<1>**%s**' % NEW, s)
        s2 = re.sub(r'(现值仍为 D15 )\*\*v1\.\d+\*\*', r'\g<1>**%s**' % NEW, s2)
        if s2 != s:
            e['subtitle_style']['dwell_calc_convention'] = s2
            stats['dcc'] += 1

    # —— ③ golden3s_first_line.note ——
    for e in d16['episodes']:
        g = e['subtitle_style'].get('golden3s_first_line')
        if not isinstance(g, dict):
            continue
        note = g.get('note')
        if isinstance(note, str):
            n2 = re.sub(r'(D15 )v1\.\d+( 实测：)', r'\g<1>%s\g<2>' % NEW, note)
            if n2 != note:
                g['note'] = n2
                stats['g3s'] += 1

    # —— ④ verified_note 追加 ——
    for e in d16['episodes']:
        aud = e['subtitle_style']['subtitle_sync_audit']
        vn = aud.get('verified_note', '')
        if TRACE_MARK not in vn:
            aud['verified_note'] = (vn + '｜' + trace) if vn else trace
            stats['note'] += 1

    # —— 守卫③：幂等（结构级比对）——
    probe = copy.deepcopy(d16)
    probe['version'] = before['version']
    if json.dumps(probe, ensure_ascii=False, sort_keys=True) == \
            json.dumps(before, ensure_ascii=False, sort_keys=True):
        print('[NO-OP] 行级活戳口径已与 D15 %s 现版本一致（结构级比对无实质差异）⇒ 幂等退出' % NEW)
        return 0

    d16['version'] = to_version

    # —— 守卫④：差异白名单 ——
    allowed = {'version'}
    for i in range(len(before['episodes'])):
        allowed.add('episodes[%d].subtitle_sync_audit' % i)
        allowed.add('episodes[%d].dwell_calc_convention' % i)
        allowed.add('episodes[%d].golden3s_first_line' % i)

    def flat(o, path=''):
        out = {}
        if isinstance(o, dict):
            for k, v in o.items():
                out.update(flat(v, ('%s.%s' % (path, k)) if path else str(k)))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                out.update(flat(v, '%s[%d]' % (path, i)))
        else:
            out[path] = o
        return out

    fb, fa = flat(before), flat(d16)
    for k in sorted(set(fb) | set(fa)):
        if fb.get(k) != fa.get(k):
            if k in allowed:
                continue
            if k.startswith('episodes[') and any(k.startswith(a) for a in allowed):
                continue
            print('[ABORT] 差异白名单外发生变更：%s' % k)
            print('       before=%r' % (fb.get(k),))
            print('       after =%r' % (fa.get(k),))
            return 1

    if args.dry_run:
        print('[DRY-RUN] 目标版本 %s｜D15 现版本 %s｜改动统计：%s' % (to_version, NEW, stats))
        return 0

    # —— 守卫⑤：CAS ——
    cur = json.load(open(p16, encoding='utf-8'))
    if cur.get('version') != before.get('version') or sha16(p16) != before_sha:
        print('[ABORT] CAS 失败：写前重读 version=%s sha16=%s（本次读盘 %s / %s）'
              ' ⇒ 并发写者已动盘，不覆盖'
              % (cur.get('version'), sha16(p16), before.get('version'), before_sha))
        return 1

    bak = os.path.join(root, 'reports',
                        '_bak_D16_U01_row_stamp_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    print('[BAK] %s' % bak)

    # —— 守卫⑥：原子写 ——
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p16)

    # —— 守卫⑦：写后回读 ——
    chk = json.load(open(p16, encoding='utf-8'))
    assert chk.get('version') == to_version
    ok = True
    for e in chk['episodes']:
        aud = e['subtitle_style']['subtitle_sync_audit']
        for r in aud.get('rows', []):
            if ('D15 %s 落锚' % NEW) not in r.get('action', ''):
                ok = False
        if TRACE_MARK not in aud.get('verified_note', ''):
            ok = False
    if not ok:
        print('[WARN] 写后回读发现未达成项，请人工复核')
        return 1
    print('[OK] 写盘完成 → %s（%d B｜sha16 %s）'
          % (to_version, os.path.getsize(p16), sha16(p16)))
    print('     改动统计：%s' % stats)
    return 0


if __name__ == '__main__':
    sys.exit(main())
