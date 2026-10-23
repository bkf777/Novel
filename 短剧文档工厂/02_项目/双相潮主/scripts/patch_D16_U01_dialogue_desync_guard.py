#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：台词改稿脱节守卫（通用版 —— 任意集的对白字幕行与 D09 现值脱节时登记挂账）

背景
────
台本编剧于 2026-10-23 12:2x–12:3x **逐集强化《双相潮主》U01 的黄金 3 秒首句**，
重写了 D09 U01 的台词正文（D08 U01 同步）：
  · ep1（12:23:34）4 句全改：#1「上一趟……我被叶家推入深坑，死在第三个小时。」
    #2「两小时五十八分……叶承钧，这一趟该换你了。」#3「物资不带。先要命，再要账。」
    #4「城西机械厂。」
  · ep2（12:33:13）3 句改：#1「门撬开了。这一世，老子来当关门人。」
    #2「前门焊死。叶家和灰潮，谁都别想轻易踏进来。」
    #3「后方管廊直通处置深坑……伏击和退路，我全占了。」（#4 未改）
⇒ D16 U01 的对白字幕行 **文字** 随之与 D09 脱节（**7 行**：ep1 4 行＋ep2 3 行）。

为什么本脚本**只登记挂账、不改文字也不改时码**
──────────────────────────────────────────
· **D16 的 out_sec 被 reconcile 判据 D 硬绑在 D15 的 at_sec＋dur_sec 上**
  （`scripts/reconcile_D15_D16_timing.mjs` 判据 D1：out_sec == 配音 at+dur，0.1s 网格），
  而新台词**没有实测音频** ⇒ 按本厂既有口径（`preview_param_dependency.已知挂账`
  ep2_seq9「换我用了。」条：**无实测音频的新句不据此调预算**），
  **D15 dur_sec 不动 ⇒ D16 窗口不动 ⇒ D16 字幕文字亦不单边改**
  （改文字而不改窗口＝长句塞进旧窗口的不可读半成品，比显式挂账更坏）。
· 故本脚本只做三件**不改内容**的事：
  ① **审计镜像的行级锚点自证**：对脱节行按 **时间配对**
     （live 行 `in_sec` ↔ D15 voice_over `at_sec` 唯一命中，且
     `out_sec == at_sec＋dur_sec`）复核并保留其时码凭证，
     并把 `pending_d15_sync` 的 `d15_current_anchor` 填成**真实锚点**
     （此前并行实例的重建把 ep1 写成 null，与现盘矛盾）；
  ② **行级 ⚠️ 挂账标记**：在脱节行的 live `note` 与审计行 `note` 末尾追加
     「台词改稿待重定时」说明，使任何读到该行的人都能立刻看到文字与 D09 不一致；
  ③ **`verified_note` 追加段**：按集登记脱节行数与上游改稿事实（只追加不重写）。

⛔ 不动
──────
· 任何 `lines[]` 的 `in_sec`／`out_sec`／`text`／`seq`／`type`／`shot_id`／`char_id`
  —— **只允许在脱节行的 `note` 末尾追加文字**；
· 审计行的 `in_sec`／`out_sec`／`nominal_dwell_sec`／`float_dwell_sec`／`shot_id`／
  `char_id`／`type`／`seq`；
· `golden3s_first_line` 的 `d15_vo_at_sec`／`d15_vo_dur_sec`／`target_at_sec`／`status`；
· D08／D09／D11／D12／D15／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**。

守卫
────
① **版本守卫**：D16 U01 为 `v1.{minor}` 且 minor ≥ 29（否则 [NO-OP] exit 0）
② **D15／D09 版本守卫**：D15 U01 == v1.13；D09 U01 须存在（上游已动 ⇒ 退出）
③ **锚点唯一命中**：每条脱节行的时间配对必须唯一命中且 out_sec == at+dur，
   否则 [ABORT] 不写盘
④ **幂等**：每集 `verified_note` 已含本轮标记 ⇒ 该集跳过
⑤ **结构级差异断言**（不是路径白名单）：
   · episodes 顶层除 `subtitle_style` 外逐键相等；
   · `subtitle_style` 除 {lines, subtitle_sync_audit, golden3s_first_line,
     dwell_calc_convention} 外逐键相等；
   · `lines` 长度不变，逐行除 `note` 外逐键相等；
   · 审计行除 {d15_vo_at_sec, d15_vo_dur_sec, d15_line_ref, action, verdict, note}
     外逐键相等；
   · `golden3s_first_line` 除 {text, note} 外逐键相等；
   ⇒ 任一条不成立即 [ABORT]
⑥ **CAS**（写前重读 version+SHA）⑦ **原子写** ⑧ **写后回读校验**

用法：python3 scripts/patch_D16_U01_dialogue_desync_guard.py --project . [--dry-run]
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
GUARD_MIN_MINOR = 29
D15_VERSION = 'v1.13'

PEND_ACTION = (
    '⚠️ 台词改稿待重定时：台本编剧 2026-10-23 重写 D09 U01 ep{ep} 台词，'
    '本行字幕文字与 D09 现值脱节；锚点已在 D15 {d15v}（at {at}／dur {dur}）'
    '且时码逐条相等，待声音设计岗按新句重出 TTS 预算与 dur_sec、'
    '且台本编剧岗确认新稿定稿后，由本岗同步本行文字与 out_sec'
)


def sq(t):
    return str(t or '').replace('「', '').replace('」', '').strip()


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
    p09 = os.path.join(root, 'units', 'U01', 'D09.json')

    d16 = json.load(open(p16, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))
    d09 = json.load(open(p09, encoding='utf-8'))

    # —— 守卫①/② ——
    m = re.match(r'^v1\.(\d+)$', str(d16.get('version', '')))
    if not m or int(m.group(1)) < GUARD_MIN_MINOR:
        print('[NO-OP] D16 U01 version=%s 不满足 v1.{minor≥%d}'
              % (d16.get('version'), GUARD_MIN_MINOR))
        return 0
    if d15.get('version') != D15_VERSION:
        print('[NO-OP] D15 U01 version=%s ≠ 期望 %s（上游已动，退出）'
              % (d15.get('version'), D15_VERSION))
        return 0
    minor = int(m.group(1))
    to_version = 'v1.%d' % (minor + 1)

    d09_texts = {}
    for l in d09.get('lines', []):
        d09_texts.setdefault(l['ep'], set()).add(sq(l.get('text')))

    d09_stamp = '%s（%d B｜mtime %s）' % (
        d09.get('version'), os.path.getsize(p09),
        time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p09))))

    before = copy.deepcopy(d16)
    before_sha = sha16(p16)
    stats = {'episodes': [], 'rows': 0, 'live_note': 0, 'audit_note': 0,
             'pending': 0, 'g3s_text': 0}

    for e in d16['episodes']:
        ep = e['ep']
        ss = e['subtitle_style']
        aud = ss['subtitle_sync_audit']
        lines = ss.get('lines', [])
        desync = [l for l in lines
                  if l.get('type') == '对白' and sq(l.get('text')) not in d09_texts.get(ep, set())]
        if not desync:
            continue
        vos = [v for x in d15['episodes'] if x['ep'] == ep for v in x.get('voice_over', [])]

        # 脱节行的目标文字（D09 现值，按行序对应）
        d09_order = [sq(l.get('text')) for l in d09.get('lines', []) if l.get('ep') == ep]

        for lrow in desync:
            in_s = round(float(lrow.get('in_sec')), 1)
            cand = [v for v in vos if abs(round(float(v['at_sec']), 1) - in_s) < 1e-9]
            if len(cand) != 1:
                print('[ABORT] ep%d seq%s 时间配对命中 %d 条 D15 配音（须唯一）'
                      % (ep, lrow.get('seq'), len(cand)))
                return 1
            vo = cand[0]
            vo_end = round(float(vo['at_sec']) + float(vo['dur_sec']), 1)
            if abs(round(float(lrow.get('out_sec')), 1) - vo_end) > 1e-9:
                print('[ABORT] ep%d seq%s out_sec=%r ≠ 命中锚点 at+dur=%r'
                      % (ep, lrow.get('seq'), lrow.get('out_sec'), vo_end))
                return 1

            # 审计行（按 seq 定位；seq 指针已由前序补丁校准）
            arow = next((r for r in aud.get('rows', [])
                         if r.get('seq') == lrow.get('seq') and r.get('type') == '对白'), None)
            if arow is None:
                print('[ABORT] ep%d 审计镜像中找不到 seq%s 的对白行' % (ep, lrow.get('seq')))
                return 1
            arow['d15_vo_at_sec'] = vo['at_sec']
            arow['d15_vo_dur_sec'] = vo['dur_sec']
            arow['d15_line_ref'] = vo.get('line_ref')
            arow['action'] = '不动（D15 %s 落锚后逐条相等）' % D15_VERSION
            arow['verdict'] = '合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）'
            warn = ('｜【台词改稿待重定时 · 2026-10-23 12:3x · 分镜导演岗】'
                    '台本编剧重写 D09 U01 ep%d 台词，本行字幕**文字**与 D09 现值脱节；'
                    '本行时码凭证（out_sec ＝ 配音 at_sec＋dur_sec）仍成立，'
                    '但新台词无实测音频 ⇒ 按本厂口径不据此调预算 ⇒ '
                    '待声音设计岗重出本句 TTS 预算与 D15 dur_sec、'
                    '且台本编剧岗确认新稿定稿后，由本岗同步本行文字与 out_sec。' % ep)
            if '台词改稿待重定时' not in str(arow.get('note', '') or ''):
                arow['note'] = str(arow.get('note', '') or '') + warn
                stats['audit_note'] += 1
            if '台词改稿待重定时' not in str(lrow.get('note', '') or ''):
                lrow['note'] = str(lrow.get('note', '') or '') + warn
                stats['live_note'] += 1
            stats['rows'] += 1

            # pending_d15_sync：按 row_in_sec 定位/新建，填真实锚点
            pend = aud.setdefault('pending_d15_sync', [])
            pe = next((p for p in pend if abs(round(float(p.get('row_in_sec', -1)), 1) - in_s) < 1e-9), None)
            if pe is None:
                pe = {'text': lrow.get('text'), 'type': '对白', 'shot_id': lrow.get('shot_id'),
                      'row_in_sec': in_s, 'row_out_sec': round(float(lrow.get('out_sec')), 1)}
                pend.append(pe)
            pe['d15_current_anchor'] = {'at_sec': vo['at_sec'], 'dur_sec': vo['dur_sec'],
                                        'line_ref': vo.get('line_ref')}
            pe['action'] = PEND_ACTION.format(ep=ep, d15v=D15_VERSION,
                                              at=vo['at_sec'], dur=vo['dur_sec'])
            stats['pending'] += 1

        # synced_row_count 复原为「时码逐条相等」的行数
        rows = aud.get('rows', [])
        aud['synced_row_count'] = sum(
            1 for r in rows
            if r.get('type') == '对白' and r.get('d15_line_ref') is not None
            and abs(round(float(r.get('out_sec', -1)), 1)
                    - (round(float(r.get('d15_vo_at_sec')), 1)
                       + round(float(r.get('d15_vo_dur_sec')), 1))) < 1e-9)

        # golden3s_first_line.text：若首句脱节，登记新稿首句（不改 status/时码）
        g = ss.get('golden3s_first_line')
        if isinstance(g, dict) and desync and d09_order:
            new_first = d09_order[0]
            if sq(g.get('text')) != new_first:
                g['text'] = '「%s」' % new_first
                stats['g3s_text'] += 1
                if '台词改稿待重定时' not in str(g.get('note', '') or ''):
                    g['note'] = (str(g.get('note', '') or '') +
                                 '｜【台词改稿待重定时 · 2026-10-23 12:3x · 分镜导演岗】'
                                 '本集首句已被台本编剧改写为「%s」，本表 `text` 已同步新稿；'
                                 '**时长与入画时码未动**（待 D15 重出预算后由本岗同步）。' % new_first)

        # verified_note 追加
        mark = '【台词改稿脱节登记 · 2026-10-23 12:3x · 分镜导演岗】ep%d' % ep
        vn = aud.get('verified_note', '')
        if mark not in vn:
            aud['verified_note'] = (vn + '｜' + mark + '：本集有 %d 条对白字幕行的**文字**'
                                    '与 D09 U01 现值脱节（台本编剧 2026-10-23 12:2x–12:3x '
                                    '重写本集台词，D08 U01 已同步）；D09 现盘＝%s。'
                                    '本轮**未改任何文字与时码**：D16 的 out_sec 被 reconcile '
                                    '判据 D 硬绑在 D15 的 at_sec＋dur_sec，而新台词无实测音频 ⇒ '
                                    '按本厂口径不据此调预算 ⇒ D15 dur_sec 不动、D16 窗口不动、'
                                    '字幕文字不单边改（改文字而不改窗口＝长句塞进旧窗口的'
                                    '不可读半成品，比显式挂账更坏）。'
                                    '脱节行的时码凭证已按**时间配对**复核并保留，'
                                    '`pending_d15_sync` 填入真实锚点（原为 null，与现盘矛盾）；'
                                    '待声音设计岗重出 TTS 预算与 D15 dur_sec、'
                                    '且台本编剧岗确认新稿定稿后，由本岗同步文字与 out_sec。'
                                    % (len(desync), d09_stamp))
        stats['episodes'].append(ep)

    if not stats['episodes']:
        print('[NO-OP] 8 集对白字幕行与 D09 现值零脱节 ⇒ 幂等退出')
        return 0

    # —— 守卫④：幂等（**结构级比对**，不靠计数）——
    # ⚠️ 第一版把「pending 条数」当改动量，导致每轮空转也升版 —— 守卫存在≠守卫有效。
    # 改法：把应用后的结构（**除 version 外**）与写前结构逐键比对，
    #       完全相等即视为「目标位已达成」，直接 NO-OP，不写盘、不升版。
    probe = copy.deepcopy(d16)
    probe['version'] = before['version']
    if json.dumps(probe, ensure_ascii=False, sort_keys=True) == \
            json.dumps(before, ensure_ascii=False, sort_keys=True):
        print('[NO-OP] 脱节登记已全部达成（结构级比对无实质差异）⇒ 幂等退出，不写盘')
        return 0

    d16['version'] = to_version

    # —— 守卫⑤：结构级差异断言 ——
    for i, (be, ae) in enumerate(zip(before['episodes'], d16['episodes'])):
        bss, ass = be['subtitle_style'], ae['subtitle_style']
        for k in set(bss) | set(ass):
            if k in ('lines', 'subtitle_sync_audit', 'golden3s_first_line',
                     'dwell_calc_convention'):
                continue
            if bss.get(k) != ass.get(k):
                print('[ABORT] ep%d subtitle_style.%s 发生变化' % (i + 1, k))
                return 1
        bl, al = bss.get('lines', []), ass.get('lines', [])
        if len(bl) != len(al):
            print('[ABORT] ep%d lines 长度变化 %d → %d' % (i + 1, len(bl), len(al)))
            return 1
        for j, (b, a) in enumerate(zip(bl, al)):
            for k in set(b) | set(a):
                if k == 'note':
                    continue
                if b.get(k) != a.get(k):
                    print('[ABORT] ep%d lines[%d].%s 发生变化（%r → %r）'
                          % (i + 1, j, k, b.get(k), a.get(k)))
                    return 1
        ba, aa = bss.get('subtitle_sync_audit', {}), ass.get('subtitle_sync_audit', {})
        for k in set(ba) | set(aa):
            if k in ('rows', 'verified_note', 'pending_d15_sync', 'synced_row_count'):
                continue
            if ba.get(k) != aa.get(k):
                print('[ABORT] ep%d subtitle_sync_audit.%s 发生变化' % (i + 1, k))
                return 1
        br, ar = ba.get('rows', []), aa.get('rows', [])
        if len(br) != len(ar):
            print('[ABORT] ep%d 审计 rows 长度变化' % (i + 1))
            return 1
        for j, (b, a) in enumerate(zip(br, ar)):
            for k in set(b) | set(a):
                if k in ('d15_vo_at_sec', 'd15_vo_dur_sec', 'd15_line_ref',
                         'action', 'verdict', 'note'):
                    continue
                if b.get(k) != a.get(k):
                    print('[ABORT] ep%d audit.rows[%d].%s 发生变化（%r → %r）'
                          % (i + 1, j, k, b.get(k), a.get(k)))
                    return 1
        bg, ag = bss.get('golden3s_first_line', {}), ass.get('golden3s_first_line', {})
        for k in set(bg) | set(ag):
            if k in ('text', 'note'):
                continue
            if bg.get(k) != ag.get(k):
                print('[ABORT] ep%d golden3s_first_line.%s 发生变化' % (i + 1, k))
                return 1
    for k in set(before) | set(d16):
        if k in ('version', 'episodes'):
            continue
        if before.get(k) != d16.get(k):
            print('[ABORT] 顶层字段 %s 发生变化' % k)
            return 1

    if args.dry_run:
        print('[DRY-RUN] 目标版本 %s｜脱节集 %s｜%s'
              % (to_version, stats['episodes'], stats))
        return 0

    # —— 守卫⑥：CAS ——
    cur = json.load(open(p16, encoding='utf-8'))
    if cur.get('version') != before.get('version') or sha16(p16) != before_sha:
        print('[ABORT] CAS 失败：写前重读 version=%s sha16=%s（本次读盘 %s / %s）'
              % (cur.get('version'), sha16(p16), before.get('version'), before_sha))
        return 1

    bak = os.path.join(root, 'reports',
                        '_bak_D16_U01_desync_guard_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    print('[BAK] %s' % bak)

    # —— 守卫⑦：原子写 ——
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p16)

    chk = json.load(open(p16, encoding='utf-8'))
    assert chk.get('version') == to_version
    print('[OK] 写盘完成 → %s（%d B｜sha16 %s）'
          % (to_version, os.path.getsize(p16), sha16(p16)))
    print('     改动统计：%s' % stats)
    return 0


if __name__ == '__main__':
    sys.exit(main())
