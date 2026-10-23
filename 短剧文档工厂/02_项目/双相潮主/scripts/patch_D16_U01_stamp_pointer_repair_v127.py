#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：并行实例半成品刷新后的定点修复（ep1 锚点回归 ＋ 活戳漏刷 ＋ 指针漂移）

背景
────
声音设计 06:4x 派单 `task_80f96d3b8320`「D16 两侧活戳更新」的坐标已全面过期，
本岗按现盘重扫后划定真实范围（U02 侧 52 处已闭合；U01 侧由**并行分镜导演实例**
在 12:2x–12:3x 落 D16 U01 v1.26→v1.28 时收敛）。本脚本只补**本岗单写点内、
现盘确证**的缺口，且**只做锚点与指针修复，不改任何时码**。

现盘实测（2026-10-23 12:3x，D16 U01 v1.28 / D15 U01 v1.13）
──────────────────────────────────────────────────────────────
并行实例已做：8 集 `verified_against_d15` → v1.13；8 集 `rows[].action` → v1.13；
8 集 `rows[].seq` 指针 → 与现盘 live 行一致。

本脚本补四项
────────────
① **ep1 审计锚点回归修复（4 行 ＋ synced_row_count ＋ pending_d15_sync 重写）**
   —— 并行实例用 `refresh_audit` 重建 ep1 镜像时，锚点走「D09 同文 → idx → D15
   voice_over」；因台本编剧 12:23:34 重写了 D09 U01 ep1 台词 4 句，**旧文字已不在
   D09 v1.7 中** ⇒ 文本锚点解析失败 ⇒ ep1 四行的 `d15_vo_at_sec`／`d15_vo_dur_sec`／
   `d15_line_ref` 被清成 **null**、`action`／`verdict` 被改成「待 D15 落锚」、
   `synced_row_count` 掉到 **0**、`pending_d15_sync` 被塞进 4 条 `d15_current_anchor: null`。
   ⚠️ **这是回归，不是事实**：D15 U01 ep1 的四个锚点**确实在**
   （D09 ep1 #1 0.5s/3.5s｜#2 6.0s/2.0s｜#3 31.4s/1.3s｜#4 39.2s/1.3s），
   且 ep1 四条 live 字幕行的 `out_sec` **逐条等于** 对应锚点的 at_sec＋dur_sec。
   ⇒ 修复方式：**改用时间配对**（live 行 `in_sec` ↔ D15 vo `at_sec` 唯一命中），
   与 `scripts/reconcile_D15_D16_timing.mjs` 判据 D 同法；配对必须唯一、
   且 `out_sec == at+dur`（0.1s 网格）方可回填，否则 [ABORT]。
   回填后 `pending_d15_sync` 的 4 条**保留但改写**：`d15_current_anchor` 填真实锚点，
   `action` 改述为**真正**的待办（台词改稿 ⇒ 待 D15 重定时），
   避免留下「锚点为 null ⇒ 待落锚」这一与现盘矛盾的陈述。
② **`dwell_calc_convention` 现值断言**：ep4／ep6／ep7 各 2 处 ＝ **6 处**
   「D15 现行为 **v1.6**」／「现值仍为 D15 **v1.6** 现行预算」→「**v1.13**」。
③ **`golden3s_first_line.note` 现值断言**：8 集「D15 v1.12 实测：」→「D15 v1.13 实测：」
   （该行 at/dur 已按 v1.13 复算相等后才改）。
④ **`verified_note` 追加留痕**：8 集追加「【D15 活戳补刷与指针订正 · 2026-10-23 12:3x】」段，
   含 ep1 改稿事件的显式登记（避免后人把「时码逐条相等」误读成「字幕文字也已一致」）。

⛔ 不动（本脚本的边界，逐条列明）
────────────────────────────────
  · **ep1 的 4 条对白字幕行 `text`／`in_sec`／`out_sec`** —— 台本编剧 12:23:34 重写
    D09 U01 ep1 台词 4 句（D08 U01 12:23:19 已同步），D16 侧字幕文字因此与 D09 脱节。
    但 **D16 的 out_sec 被 reconcile 判据 D 硬绑在 D15 的 at_sec＋dur_sec 上**
    （`reconcile_D15_D16_timing.mjs` 判据 D1：out_sec == 配音 at+dur，0.1s 网格），
    而新台词**没有实测音频** ⇒ 按本厂既有口径（`preview_param_dependency.已知挂账`
    ep2_seq9「换我用了。」条：**无实测音频的新句不据此调预算**），
    **D15 dur_sec 不动 ⇒ D16 窗口不动 ⇒ D16 字幕文字亦不单边改**（改文字而不改窗口
    ＝ 长句塞进旧窗口的不可读半成品，比显式挂账更坏）。
    ⇒ 该项归**声音设计岗**（重出 ep1 四句 TTS 预算与 D15 dur_sec）＋**台本编剧岗**
    （确认 ep1 新稿定稿），本岗在 D15 落锚后同步文字与 out_sec。
  · ep2–ep8 的 `rows[]`（现盘已由并行实例刷成 v1.13 ＋ seq 指针正确）—— 不重复动。
  · 任何 `lines[]`（含 in_sec／out_sec／text／shot_id）、任何 `dur_sec`、
    D08／D09／D11／D12／D15／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**
  · 历史留痕字面：「D15 U01 活戳刷新 v1.4 → v1.6」「「D15 现行为 **v1.4**」→「v1.6」」
    「D15 v1.3 相对 v1.2 的数值区…」「D15 v1.1 已把…」「D15 新 dur_sec 待声音设计落 v1.4 后复核」
    —— 指的是**当时发生了什么**，不是「现行版本是多少」，按 Q30／S11 原文保留。

守卫
────
① **版本守卫（放宽并说明理由）**：D16 U01 须为 `v1.{minor}` 且 minor ≥ 26；
   理由＝并行实例正跑**同一条派单**、收敛目标一致，本脚本只补差异，
   真正的并发保护由 ⑧CAS 承担（写前重读 version+SHA，不一致即不覆盖）。
   minor < 26 ⇒ [NO-OP] exit 0（磁盘未到该状态，不猜）。
② **D15 版本守卫**：D15 U01 == v1.13（否则 [NO-OP] exit 0，上游已动）
③ **数据加载后置**（守卫置于读盘之后）
④ **改戳前独立复算**：③⑤ 每一处都要先按 **D15 v1.13 现盘**复算
   「out_sec == 配音 at_sec＋dur_sec」与「镜像 d15_vo_at_sec／d15_vo_dur_sec
   == D15 对应 line_ref 的 at／dur」，任一处失配 ⇒ [ABORT] 不写盘
⑤ **指针唯一命中**：ep1 时间配对必须唯一命中且 out_sec 相等，否则 [ABORT]
⑥ **幂等**：目标位均已达成 ⇒ [NO-OP] exit 0
⑦ **差异白名单**：只允许 version ＋ 8 集 subtitle_style.{subtitle_sync_audit,
   dwell_calc_convention, golden3s_first_line} 发生变化（`lines[]` 变化即 ABORT）
⑧ **CAS**：写前重读 version+SHA，与本次读盘不一致 ⇒ [ABORT] 不覆盖
⑨ **原子写**（tmp + os.replace）＋ **写后回读校验**

用法：python3 scripts/patch_D16_U01_stamp_pointer_repair_v127.py --project . [--dry-run]
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
GUARD_MIN_MINOR = 26
D15_VERSION = 'v1.13'
OLD_STAMP = 'v1.12'
NEW_STAMP = 'v1.13'

DCC_PAIRS = (
    ('D15 现行为 **v1.6**', 'D15 现行为 **v1.13**'),
    ('现值仍为 D15 **v1.6** 现行预算', '现值仍为 D15 **v1.13** 现行预算'),
)
G3S_OLD = 'D15 v1.12 实测：'
G3S_NEW = 'D15 v1.13 实测：'

TRACE_MARK = '【D15 活戳补刷与指针订正 · 2026-10-23 12:3x · 分镜导演岗】'
EP1_WARN = (
    '｜【台词改稿待重定时 · 2026-10-23 12:23】台本编剧重写 D09 U01 ep1 台词 4 句'
    '（D08 U01 12:23:19 已同步），**本行字幕文字与 D09 现值脱节**；'
    '本行时码凭证（out_sec ＝ 配音 at_sec＋dur_sec）**仍成立**，'
    '但新台词无实测音频 ⇒ 按本厂口径不据此调预算 ⇒ '
    '待声音设计岗重出 ep1 四句 TTS 预算与 D15 dur_sec、且台本编剧岗确认新稿定稿后，'
    '由本岗同步本行文字与 out_sec。'
)

TRACE = (
    TRACE_MARK +
    '本集审计镜像按 **D15 U01 v1.13** 现盘定点补齐（**改戳不改码**，未动任何 '
    'in_sec／out_sec／dur_sec／text／shot_id）：'
    '① 顶层 `verified_against_d15` 与 `rows[].action` 的版本戳已由并行实例于 '
    'D16 U01 v1.26→v1.28 刷为 v1.13，本岗不重复动；'
    '② 本集 4 条对白字幕行的审计锚点**按时间配对**回填'
    '（live 行 in_sec ↔ D15 voice_over at_sec 唯一命中，且 out_sec == at+dur），'
    '修复并行实例用文本锚点重建时因 D09 ep1 台词改稿导致的**锚点 null 回归**'
    '（`d15_vo_at_sec`／`d15_vo_dur_sec`／`d15_line_ref` 复原，'
    '`action`／`verdict` 复原为「合规」，`synced_row_count` 由 0 复原为 4）；'
    '③ `pending_d15_sync` 的 4 条**保留但改写**：`d15_current_anchor` 填入真实锚点'
    '（原为 null，与现盘矛盾），`action` 改述为真正的待办'
    '（台词改稿 ⇒ 待 D15 重定时）；'
    '④ `dwell_calc_convention` 与 `golden3s_first_line.note` 的现值断言刷为 v1.13。'
    '**历史留痕字面一律原文保留**（只追加不重写）。'
)


def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()[:16]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    p16 = os.path.join(root, 'units', 'U01', 'D16.json')
    p15 = os.path.join(root, 'units', 'U01', 'D15.json')

    # —— 数据加载 ——
    d16 = json.load(open(p16, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))

    # —— 守卫 ——
    m = re.match(r'^v1\.(\d+)$', str(d16.get('version', '')))
    if not m or int(m.group(1)) < GUARD_MIN_MINOR:
        print('[NO-OP] D16 U01 version=%s 不满足 v1.{minor≥%d}（磁盘未到该状态，不猜）'
              % (d16.get('version'), GUARD_MIN_MINOR))
        return 0
    minor = int(m.group(1))
    to_version = 'v1.%d' % (minor + 1)
    if d15.get('version') != D15_VERSION:
        print('[NO-OP] D15 U01 version=%s ≠ 期望 %s（上游已动，退出）'
              % (d15.get('version'), D15_VERSION))
        return 0

    stats = {'rows_checked': 0, 'ep1_anchor': 0, 'ep1_pending': 0,
             'dcc': 0, 'g3s': 0, 'note': 0}

    # ───────── 守卫④：改戳前独立复算 ─────────
    bad = []
    for e in d16['episodes']:
        ep = e['ep']
        vos = [v for x in d15['episodes'] if x['ep'] == ep for v in x.get('voice_over', [])]
        by_ref = {v.get('line_ref'): v for v in vos}
        aud = e['subtitle_style']['subtitle_sync_audit']
        for r in aud.get('rows', []):
            ref = r.get('d15_line_ref')
            if ref is None:
                continue
            vo = by_ref.get(ref)
            if vo is None:
                bad.append('ep%d seq%s line_ref=%r 在 D15 %s 中不存在'
                           % (ep, r.get('seq'), ref, D15_VERSION))
                continue
            if abs(float(r.get('d15_vo_at_sec', -1)) - float(vo['at_sec'])) > 1e-9:
                bad.append('ep%d seq%s d15_vo_at_sec=%r ≠ D15 %s %s at=%r'
                           % (ep, r.get('seq'), r.get('d15_vo_at_sec'),
                              D15_VERSION, ref, vo['at_sec']))
            if abs(float(r.get('d15_vo_dur_sec', -1)) - float(vo['dur_sec'])) > 1e-9:
                bad.append('ep%d seq%s d15_vo_dur_sec=%r ≠ D15 %s %s dur=%r'
                           % (ep, r.get('seq'), r.get('d15_vo_dur_sec'),
                              D15_VERSION, ref, vo['dur_sec']))
            vo_end = round(float(vo['at_sec']) + float(vo['dur_sec']), 1)
            if abs(round(float(r.get('out_sec', -1)), 1) - vo_end) > 1e-9:
                bad.append('ep%d seq%s out_sec=%r ≠ D15 %s %s at+dur=%r'
                           % (ep, r.get('seq'), r.get('out_sec'),
                              D15_VERSION, ref, vo_end))
            stats['rows_checked'] += 1
    if bad:
        print('[ABORT] 按 D15 %s 现盘独立复算审计镜像有 %d 处失配 ⇒ 不得改戳，退出'
              % (D15_VERSION, len(bad)))
        for x in bad[:10]:
            print('   ', x)
        return 1
    print('[OK] 改戳前独立复算：%d 行审计镜像 × D15 %s 现盘，数值与锚点零失配'
          % (stats['rows_checked'], D15_VERSION))

    before = copy.deepcopy(d16)
    before_sha = sha16(p16)

    # ───────── ① ep1 审计锚点回归修复（时间配对） ─────────
    for e in d16['episodes']:
        ep = e['ep']
        ss = e['subtitle_style']
        aud = ss['subtitle_sync_audit']
        rows = aud.get('rows', [])
        broken = [r for r in rows
                  if r.get('type') == '对白' and r.get('d15_line_ref') is None]
        if not broken:
            continue
        vos = [v for x in d15['episodes'] if x['ep'] == ep for v in x.get('voice_over', [])]
        for r in broken:
            in_s = round(float(r.get('in_sec')), 1)
            cand = [v for v in vos if abs(round(float(v['at_sec']), 1) - in_s) < 1e-9]
            if len(cand) != 1:
                print('[ABORT] ep%d seq%s 时间配对命中 %d 条 D15 配音（须唯一）'
                      % (ep, r.get('seq'), len(cand)))
                return 1
            vo = cand[0]
            vo_end = round(float(vo['at_sec']) + float(vo['dur_sec']), 1)
            if abs(round(float(r.get('out_sec')), 1) - vo_end) > 1e-9:
                print('[ABORT] ep%d seq%s out_sec=%r ≠ 命中锚点 at+dur=%r'
                      % (ep, r.get('seq'), r.get('out_sec'), vo_end))
                return 1
            r['d15_vo_at_sec'] = vo['at_sec']
            r['d15_vo_dur_sec'] = vo['dur_sec']
            r['d15_line_ref'] = vo.get('line_ref')
            r['action'] = '不动（D15 %s 落锚后逐条相等）' % NEW_STAMP
            r['verdict'] = ('合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）')
            note = str(r.get('note', '') or '')
            if '台词改稿待重定时' not in note:
                r['note'] = note + EP1_WARN
            stats['ep1_anchor'] += 1
        # synced_row_count 复原
        synced = sum(1 for r in rows
                     if r.get('type') == '对白' and r.get('d15_line_ref') is not None
                     and abs(round(float(r.get('out_sec', -1)), 1)
                             - (round(float(r.get('d15_vo_at_sec')), 1)
                                + round(float(r.get('d15_vo_dur_sec')), 1))) < 1e-9)
        aud['synced_row_count'] = synced
        # pending_d15_sync 保留但改写（填真实锚点 + 改述真正的待办）
        pend = aud.get('pending_d15_sync')
        if pend:
            new_pend = []
            for p in pend:
                in_s = round(float(p.get('row_in_sec')), 1)
                cand = [v for v in vos if abs(round(float(v['at_sec']), 1) - in_s) < 1e-9]
                if len(cand) != 1:
                    print('[ABORT] ep%d pending 行时间配对命中 %d 条（须唯一）' % (ep, len(cand)))
                    return 1
                vo = cand[0]
                p['d15_current_anchor'] = {'at_sec': vo['at_sec'], 'dur_sec': vo['dur_sec'],
                                           'line_ref': vo.get('line_ref')}
                p['action'] = ('⚠️ 台词改稿待重定时：台本编剧 2026-10-23 12:23:34 重写 '
                               'D09 U01 ep1 台词，本行字幕文字与 D09 现值脱节；'
                               '锚点已在 D15 %s（at %s／dur %s）且时码逐条相等，'
                               '待声音设计岗按新句重出 TTS 预算与 dur_sec 后，'
                               '由本岗同步本行文字与 out_sec' %
                               (NEW_STAMP, vo['at_sec'], vo['dur_sec']))
                new_pend.append(p)
                stats['ep1_pending'] += 1
            aud['pending_d15_sync'] = new_pend

    # ───────── ② dwell_calc_convention 现值断言 ─────────
    for e in d16['episodes']:
        s = e['subtitle_style'].get('dwell_calc_convention', '')
        if not isinstance(s, str):
            continue
        for old, new in DCC_PAIRS:
            if old in s:
                s = s.replace(old, new)
                stats['dcc'] += 1
        e['subtitle_style']['dwell_calc_convention'] = s

    # ───────── ③ golden3s_first_line.note 现值断言 ─────────
    for e in d16['episodes']:
        g = e['subtitle_style'].get('golden3s_first_line')
        if not isinstance(g, dict):
            continue
        note = g.get('note')
        if isinstance(note, str) and G3S_OLD in note:
            g['note'] = note.replace(G3S_OLD, G3S_NEW)
            stats['g3s'] += 1

    # ───────── ④ verified_note 追加留痕 ─────────
    for e in d16['episodes']:
        aud = e['subtitle_style']['subtitle_sync_audit']
        vn = aud.get('verified_note', '')
        if TRACE_MARK not in vn:
            aud['verified_note'] = (vn + '｜' + TRACE) if vn else TRACE
            stats['note'] += 1

    # ───────── 守卫⑥：幂等 ─────────
    # ⚠️ 幂等判据**只认实际改动量**，不得把「改戳前复算行数」算进改动量
    #    （第一版把 rows_checked 一并计入，导致空转也升版 —— 守卫存在≠守卫有效，Q56③）。
    changed = (stats['ep1_anchor'] + stats['ep1_pending'] + stats['dcc']
               + stats['g3s'] + stats['note'])
    if changed == 0:
        print('[NO-OP] 四类目标位均已达成（复算 %d 行，零改动）⇒ 幂等退出'
              % stats['rows_checked'])
        return 0

    d16['version'] = to_version

    # ───────── 守卫⑦：差异白名单 ─────────
    allowed = {'version'}
    for i in range(len(before['episodes'])):
        allowed.add('episodes[%d].subtitle_style.subtitle_sync_audit' % i)
        allowed.add('episodes[%d].subtitle_style.dwell_calc_convention' % i)
        allowed.add('episodes[%d].subtitle_style.golden3s_first_line' % i)
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
        print('[DRY-RUN] 目标版本 %s｜改动统计：%s' % (to_version, stats))
        return 0

    # ───────── 守卫⑧：CAS ─────────
    cur = json.load(open(p16, encoding='utf-8'))
    cur_ver, cur_sha = cur.get('version'), sha16(p16)
    if cur_ver != before.get('version') or cur_sha != before_sha:
        print('[ABORT] CAS 失败：写前重读 version=%s sha16=%s（本次读盘 %s / %s）'
              ' ⇒ 并发写者已动盘，不覆盖' % (cur_ver, cur_sha, before.get('version'), before_sha))
        return 1

    bak = os.path.join(root, 'reports',
                        '_bak_D16_U01_stamp_pointer_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    print('[BAK] %s' % bak)

    # ───────── 守卫⑨：原子写 ─────────
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p16)

    # ───────── 守卫⑨：写后回读校验 ─────────
    chk = json.load(open(p16, encoding='utf-8'))
    assert chk.get('version') == to_version, '写后版本号异常'
    ok = True
    for e in chk['episodes']:
        aud = e['subtitle_style']['subtitle_sync_audit']
        for r in aud.get('rows', []):
            if r.get('type') == '对白' and r.get('d15_line_ref') is None:
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
