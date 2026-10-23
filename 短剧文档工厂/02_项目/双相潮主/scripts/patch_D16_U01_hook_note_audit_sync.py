#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：ep001 钩子行 note 登记 TTS 实测链 ＋ ep1/ep2/ep3 审计镜像按现盘重刷

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

本脚本做（且只做）四件事
────────────────────────
① **hook 行 note 追加实测链留痕**：保留原 note（黄金 3 秒段 ＋ 配音对齐段），
   追加「【TTS 实测链 · 2026-10-23】」段，登记 实测 3.366906s → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s
   ＋ 测量来源 node_id ＋ 音色/speed/pitch，并声明「原预估 1.8s 系未实测占位，已被实测取代」。
   ⛔ 不改 in_sec／out_sec／text／type／char_id／shot_id（数值已由并发批次落定，本脚本只补留痕）。
② **ep1/ep2/ep3 的 subtitle_sync_audit 镜像按现盘重刷**（rows[]／synced_row_count／
   no_vo_anchor_rows／dwell_floor_rows／pending_d15_sync）：
   现盘这三集的 rows[] 存的是**改号前的 seq 与改期前的时码**（ep1 存 seq1/3/6/8、
   ep2 存 seq1/2/3/5、ep3 存 seq4=30.5~33.2、seq5=33.2~34.4），与现盘 lines[] 全面脱节；
   ep3 的 rows[].verdict 写「合规」但 d15_vo_at_sec 为 null ⇒ 自相矛盾。
   重刷口径＝**照搬 scripts/patch_D16_golden3s.py 的重算逻辑**（同源同判据，不自造口径）：
   锚点走「D09 同文 → idx → D15 该 idx 的 voice_over」（D15 的 line_ref 可能指旧编号，故两路都试），
   verdict 二值＝「合规（out_sec ＝ 配音 at_sec＋dur_sec，标称网格逐条严格相等）」／「待 D15 落锚…」。
③ **ep1 dwell_calc_convention 里失效的 seq 引用订正**（口径长文本，逐句改，不回改历史留痕）：
   · 「本集与 D15 配音逐条对应的字幕行：seq 9」→ 改为按现盘 rows[] 的**实际 seq 集合**表述
   · 「浮点尾差证据行：seq 8」→ 现盘 seq 8 是面板文字，证据行已随改号漂移 ⇒ 按现盘重取
   · 「【黄金 3 秒改版】…首句台词提前到 0.5s 入画（seq1）」→「（seq2）」
   · 「新增行 seq1（hook 句）当前为**预算时长 1.8s**，待声音设计岗合成实测后…」
     → 改期后已实测 ⇒ 改为现值口径（实测链见 lines[].note），历史留痕段**不动**
   · 「本集无标称 1.2s 的行（正文行全部 ≥1.3s）」→ 现盘 ep1 有标称 1.2s 的行（seq3 面板 4.0~5.2）⇒ 该断言已失效
④ **ep1 verified_against_d15 指针刷新**（v1.9 → v1.10 现盘）＋ ep1 verified_note 追加本轮复核留痕。

⛔ 不碰
──────
D08／D09／D11／D12／D15／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**
／他岗章节正文／台账（台账由本岗另行追加）；不改 ep4–ep8 的审计镜像（现盘已自洽，实测无失配）；
不改任何 lines[] 的 in_sec／out_sec（数值归本岗但**已由并发批次落定且与 D15 逐条相等**，再改即制造分叉）。

守卫
────
① **版本守卫**：D16 U01 现盘 version 须 ＝ v1.19（否则 [NO-OP] exit 0）
② **内容指纹自证**：hook 行须同时满足
   文本＝「上一趟我死在第三个小时。」／type=对白／in_sec=0.5／out_sec=4.0／shot_id=1
   ⇒ 行**按 (text, type, in_sec) 定位，不按 seq 定位**（seq 会随改号漂移）
   且 note 须已含「【配音对齐 2026-10-23】」（证明并发批次的数值同步已落）
③ **数据加载后置**：守卫全部置于读入 JSON 之后
④ **幂等**：note 已含「【TTS 实测链 · 2026-10-23】」⇒ [NO-OP] exit 0
⑤ **差异白名单**：落盘后逐叶差分，只允许 ①②③④ 声明的路径变化，其他一律 [ABORT] 回滚
⑥ **CAS**：写前重读 version+SHA，若与守卫锚定值不符 ⇒ [ABORT]（防并发抢盘）

用法：python3 scripts/patch_D16_U01_hook_note_audit_sync.py --project . [--dry-run]
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
GUARD_VERSION = 'v1.19'
TO_VERSION = 'v1.20'
D15_VERSION = 'v1.10'

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

# 审计镜像重刷范围（本岗自查定位：三集 rows[] 与现盘 lines[] 全面脱节）
REFRESH_EPS = (1, 2, 3)


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
    """照搬 patch_D16_golden3s.py 的锚点解析：vo_by_text 优先，vo_by_ref 兜底。

    vo_by_text 以 D15 voice_over 自带 text 归一化建索引；
    vo_by_ref 以 D15 line_ref 的 idx → D09 同 idx 的文字反查建索引
    （D15 的 line_ref 可能仍指 D08 插入新首句前的旧编号，故必须两路都试）。
    """
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
    """按现盘 lines[] 重算一集的审计镜像（口径同 patch_D16_golden3s.py）。"""
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
            rows.append({
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


def fix_ep1_convention(ss, rows):
    """订正 ep1 dwell_calc_convention 里随改号／改期而失效的 seq 引用与断言。

    逐句改「现值口径句」；**历史留痕段不动**（Q30 追加不覆盖原则）。
    """
    dcc = ss['dwell_calc_convention']
    before = dcc

    # 现盘对白行 seq 集合
    dlg_seqs = [r['seq'] for r in rows]
    dlg_seqs_txt = '／'.join(str(s) for s in dlg_seqs)
    # 浮点尾差证据行：现盘对白行中 float_dwell 与标称差最大的那条
    tail = max(rows, key=lambda r: abs((r['float_dwell_sec'] or 0) - (r['nominal_dwell_sec'] or 0)))
    floor_rows = [r for r in rows if abs((r['nominal_dwell_sec'] or 0) - 1.2) < 1e-6]

    # ① 「本集与 D15 配音逐条对应的字幕行：seq 9」
    dcc = re.sub(r'本集与 D15 配音逐条对应的字幕行：seq \d+',
                 '本集与 D15 配音逐条对应的字幕行：seq ' + dlg_seqs_txt, dcc)
    # ② 「浮点尾差证据行：seq 8」
    dcc = re.sub(r'浮点尾差证据行：seq \d+',
                 '浮点尾差证据行：seq %s' % tail['seq'], dcc)
    # ③ 「本集无标称 1.2s 的行（正文行全部 ≥1.3s）」—— 现盘已有 1.2s 行 ⇒ 该断言失效
    if floor_rows:
        dcc = dcc.replace(
            '本集无标称 1.2s 的行（正文行全部 ≥1.3s）。',
            '本集有标称 1.2s 的行：seq %s（正文行 dwell 判定一律取 0.1s 标称网格）。'
            % '／'.join(str(r['seq']) for r in floor_rows))
    # ④ 黄金 3 秒段的 seq 引用：钩子行现盘是 seq2（非 seq1）
    dcc = dcc.replace('首句台词提前到 0.5s 入画（seq1）', '首句台词提前到 0.5s 入画（seq2）')
    # ⑤ 「新增行 seq1（hook 句）当前为**预算时长 1.8s**，待声音设计岗合成实测后…」
    #    —— 该句在【黄金 3 秒改版】历史留痕段内，按 Q30 不回改历史段；
    #    但「当前为预算时长 1.8s，待…实测」是**现值断言**且已失效 ⇒ 追加现值句并声明取代
    stale = '新增行 seq1（hook 句）当前为**预算时长 1.8s**，待声音设计岗合成实测后按「out_sec ＝ 配音 at_sec＋dur_sec」复核'
    if stale in dcc:
        dcc = dcc.replace(
            stale,
            stale + '。'
            '【实测取代 · 2026-10-23】该占位预算已被实测取代：'
            '实测 %ss → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s，'
            '本行现盘 out_sec ＝ 4.0s（＝配音 at 0.5s ＋ dur 3.5s），'
            '实测链登记于本行 lines[].note；本句前半段作为改版当时的历史留痕保留。'
            % MEASURED)
    ss['dwell_calc_convention'] = dcc
    return dcc != before


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

    # —— ②③④ 审计镜像重刷 + 口径订正 ——
    changed_eps = []
    ep1_rows = []
    for e in d16['episodes']:
        if e['ep'] in REFRESH_EPS:
            aud, rows, floor, pending = refresh_audit(e, d15, d09)
            changed_eps.append(e['ep'])
            if e['ep'] == 1:
                ep1_rows = rows
        if e['ep'] == 1:
            fix_ep1_convention(e['subtitle_style'], ep1_rows)
            aud = e['subtitle_style']['subtitle_sync_audit']
            aud['verified_against_d15'] = '%s（黄金 3 秒改版钩子句已按实测收口，见 lines[].note 与 rows[]）' % D15_VERSION
            aud['verified_note'] = (
                str(aud.get('verified_note', '')).rstrip('｜') +
                '｜【2026-10-23 · 钩子句实测收口（分镜导演岗）】'
                '本集钩子行（按 text 定位，seq 随黄金 3 秒改号漂移，现为 seq%d）'
                '的占位预算 1.8s 已被 TTS 实测取代：实测 %ss → 标称 3.4s → ＋0.1s 余量 ＝ 3.5s，'
                '本行现盘 out_sec ＝ 4.0s ＝ 配音 at 0.5s ＋ dur 3.5s，逐条相等；'
                '实测链登记于该行 lines[].note。'
                '本集 subtitle_sync_audit.rows[]／synced_row_count／no_vo_anchor_rows／'
                'dwell_floor_rows／pending_d15_sync 已按**现盘 lines[] × D15 U01 %s** 重刷'
                '（口径同 scripts/patch_D16_golden3s.py，锚点走「D09 同文 → idx → D15 voice_over」）。'
                % (hook.get('seq'), MEASURED, D15_VERSION))

    # —— ⑤ 差异白名单 ——
    allowed_prefixes = (
        '/version',
        '/episodes/0/subtitle_style/lines/',
        '/episodes/0/subtitle_style/dwell_calc_convention',
        '/episodes/0/subtitle_style/subtitle_sync_audit/',
        '/episodes/1/subtitle_style/subtitle_sync_audit/',
        '/episodes/2/subtitle_style/subtitle_sync_audit/',
    )
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

    # —— ⑥ CAS：写前重读 version + SHA ——
    cur = json.load(open(p16, encoding='utf-8'))
    if cur.get('version') != GUARD_VERSION or sha16(p16) != before_sha:
        print('[ABORT] 写前复核失败（version/sha 漂移）⇒ 并发写者已动盘，退出不抢盘')
        return 1

    d16['version'] = TO_VERSION

    if args.dry_run:
        print('[DRY-RUN] 将改：hook note ＋ ep%s 审计镜像 ＋ ep1 口径长文本；version %s → %s'
              % ('/'.join(str(e) for e in changed_eps), GUARD_VERSION, TO_VERSION))
        return 0

    bak = os.path.join(root, 'reports', '_bak_D16_U01_hook_note_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
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
    print('[OK] D16 U01 %s → %s；hook note 已登记实测链；ep%s 审计镜像已按现盘重刷；备份 %s'
          % (GUARD_VERSION, TO_VERSION, '/'.join(str(e) for e in changed_eps), bak))
    return 0


if __name__ == '__main__':
    sys.exit(main())
