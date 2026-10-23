#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D16 U01：D15 版本活戳刷新（v1.12 → v1.13）＋ 口径长文本现值断言同步 ＋ 复核留痕追加

来件（声音设计 06:4x 派单 `task_80f96d3b8320`「D16 两侧活戳更新」）
──────────────────────────────────────────────────────────────
派单原文给的是 06:4x 时的坐标：
  · U01 D16（v1.10）21 处「D15 v1.4」→「指 v1.6」
  · U02 D16（v1.3）52 处 →「指 D15 U02 v1.1」
⚠️ **派单坐标已全面过期**，本脚本按现盘重扫后划定真实范围：
  · U01：D16 现 **v1.22**、D15 现 **v1.13**（派单时的 v1.10／v1.6 均已过 7／7 版）
  · U02：D16 现 **v1.8**、D15 现 **v1.3**；**U02 的 52 处已由并行实例在其 v1.5→v1.8 落盘中闭合**
    （8 集 `verified_against_d15` 现值 ＝ **v1.3** ＝ D15 U02 现行版本 ⇒ 无需本岗再动）
    ⇒ 本脚本**只处理 U01**，不碰 U02（避免与并行实例抢同一文件）。

本脚本做（且只做）三件事
────────────────────────
① **先复核、再改戳**（对应派单的「改戳不改码」）：
   以 D15 U01 **v1.13** 现盘 × D09 U01 现盘，对 U01 全部 8 集重算
   `subtitle_sync_audit.rows[]`（口径复用 `patch_D16_U01_audit_mirror_and_hook_note.py`
   的 `refresh_audit`，与 `patch_D16_golden3s.py` 同源），
   与盘上现值逐字段比对**数值与锚点面**（seq/text/char_id/shot_id/in_sec/out_sec/
   nominal_dwell_sec/d15_vo_at_sec/d15_vo_dur_sec/d15_line_ref/verdict）；
   **只要有一处数值或锚点失配 ⇒ [ABORT] 不写盘**（戳不得领先于实测）。
   本步保证「v1.13 已复核」这句话是真的，再谈改戳。
② **活戳刷新（14 处）**：
   · 8 集 `subtitle_sync_audit.verified_against_d15`：版本前缀 `v1.12` → `v1.13`
     （**只换版本前缀**，括注口径原文不动）
   · `dwell_calc_convention` 里 3 处「D15 现行为 **v1.6**」→ 「**v1.13**」
   · `dwell_calc_convention` 里 3 处「现值仍为 D15 **v1.6** 现行预算」→ 「**v1.13**」
③ **留痕追加**：每集 `verified_note` 末尾追加「【D15 版本活戳刷新 · 2026-10-23 · 分镜导演岗】」段，
   记录刷戳依据（复核过 D15 v1.13、数值面零失配）与「历史留痕字面一律保留」的边界声明。

⛔ **不动**（历史留痕，按 Q30／S11 只追加不重写；派单亦明文划界）
   · 「D15 U01 活戳刷新 v1.4 → v1.6」（描述一次已发生的刷新动作 ＝ 事件）
   · 「「D15 现行为 **v1.4**」→「v1.6」」（引述历史字面作示例）
   · 「D15 v1.3 相对 v1.2 的数值区…」（一次具体复算的对比叙述）
   · 「D15 v1.1 已把 11 条贴边配音…」「D15 已升至 v1.2…」（事件叙述／闭合戳）
   · 「D15 新 dur_sec 待声音设计落 v1.4 后复核」（当时的待办表述）
   · U02 侧全部（已闭合，见上）

⛔ 不碰
──────
D08／D09／D11／D12／D15／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**
／U02 任何文件／任何 `in_sec`／`out_sec`／`dur_sec`／`shot_id`／`text`／`lines[]`／他岗章节正文。

守卫
────
① **版本守卫**：D16 U01 ＝ v1.23（否则 [NO-OP] exit 0）
② **D15 版本守卫**：D15 U01 ＝ v1.13（否则 [NO-OP] exit 0）
③ **数据加载后置**；④ **幂等**（已是 v1.13 ⇒ [NO-OP] exit 0）
⑤ **差异白名单**（只允许 version ＋ 8 集 `subtitle_sync_audit/` ＋ 8 集 `dwell_calc_convention`）
⑥ **CAS**：写前重读 version+SHA；⑦ **写后回读校验**

用法：python3 scripts/patch_D16_U01_d15stamp_refresh_v113.py --project . [--dry-run]
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD_VERSION = 'v1.23'
TO_VERSION = 'v1.24'
D15_VERSION = 'v1.13'
OLD_STAMP = 'v1.12'
NEW_STAMP = 'v1.13'

STAMP_SUFFIX = (
    '｜【D15 版本活戳刷新 · 2026-10-23 · 分镜导演岗】'
    '本集 `verified_against_d15` 的版本前缀由 **%s** 刷为 **%s**。'
    '依据：承声音设计 06:4x 派单（`task_80f96d3b8320`「D16 两侧活戳更新」）——'
    '该派单坐标为 06:4x 时的 U01 D16 v1.10／D15 U01 v1.6，现盘已分别推进至 v1.22／v1.13，'
    '故按**现盘**重扫后划定真实范围（派单给的 21／52 处坐标均已过期）。'
    '本岗先按 D15 U01 **%s** 现盘 × D09 U01 现盘重算本集审计镜像，'
    '与盘上现值逐字段比对**数值与锚点面**（seq／text／char_id／shot_id／in_sec／out_sec／'
    'nominal_dwell_sec／d15_vo_at_sec／d15_vo_dur_sec／d15_line_ref／verdict）'
    '**零失配**，确认「已按 %s 复核」为真，再改戳；'
    '故本轮**只改版本戳，不改任何 in_sec／out_sec／dur_sec／text／shot_id**（改戳不改码）。'
    '⚠️ 边界：**历史留痕字面一律原文保留**（只追加不重写），'
    '包括「D15 U01 活戳刷新 v1.4 → v1.6」（描述一次已发生的刷新动作）、'
    '「「D15 现行为 **v1.4**」→「v1.6」」（引述历史字面作示例）、'
    '「D15 v1.3 相对 v1.2 的数值区…」（一次具体复算的对比叙述）、'
    '「D15 v1.1 已把…」「D15 已升至 v1.2…」（事件叙述／闭合戳）、'
    '「D15 新 dur_sec 待声音设计落 v1.4 后复核」（当时的待办表述）——'
    '这些指的都是**当时发生了什么**，不是「现行版本是多少」，故不改写；'
    '「现行版本」这一现值断言只在 `verified_against_d15` 与本集口径长文本的'
    '「D15 现行为」「现值仍为 D15」两处刷新。'
    % (OLD_STAMP, NEW_STAMP, NEW_STAMP, NEW_STAMP)
)

# 数值与锚点面：改戳前必须逐字段零失配
COMPARE_FIELDS = ('seq', 'type', 'text', 'char_id', 'shot_id', 'in_sec', 'out_sec',
                   'nominal_dwell_sec', 'd15_vo_at_sec', 'd15_vo_dur_sec',
                   'd15_line_ref', 'verdict')


def load_mod():
    p = os.path.join(ROOT, 'scripts', 'patch_D16_U01_audit_mirror_and_hook_note.py')
    spec = importlib.util.spec_from_file_location('d16audit', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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

    m = load_mod()

    # —— 数据加载 ——
    d16 = json.load(open(p16, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))
    d09 = json.load(open(p09, encoding='utf-8'))

    # —— 守卫 ——
    if d16.get('version') != GUARD_VERSION:
        print('[NO-OP] D16 U01 version=%s ≠ 守卫 %s（磁盘已演进，退出不抢盘）'
              % (d16.get('version'), GUARD_VERSION))
        return 0
    if d15.get('version') != D15_VERSION:
        print('[NO-OP] D15 U01 version=%s ≠ 期望 %s（上游已动，退出）'
              % (d15.get('version'), D15_VERSION))
        return 0

    # 幂等：已是 v1.13 前缀 ⇒ 不重复刷
    stamps = [e['subtitle_style']['subtitle_sync_audit'].get('verified_against_d15')
              for e in d16['episodes']]
    if all(s and s.startswith(NEW_STAMP) for s in stamps):
        print('[NO-OP] 8 集 `verified_against_d15` 已是 %s 前缀 ⇒ 幂等退出' % NEW_STAMP)
        return 0

    # —— ① 先复核：以 D15 v1.13 重算 8 集镜像，数值与锚点面须零失配 ——
    diffs = []
    for e in d16['episodes']:
        ep = e['ep']
        disk_rows = e['subtitle_style']['subtitle_sync_audit'].get('rows', [])
        _aud, rows, _f, _p = m.refresh_audit(e, d15, d09)
        if len(disk_rows) != len(rows):
            diffs.append('ep%d 行数 %d ≠ 重算 %d' % (ep, len(disk_rows), len(rows)))
            continue
        for a, b in zip(disk_rows, rows):
            for k in COMPARE_FIELDS:
                if a.get(k) != b.get(k):
                    diffs.append('ep%d seq%s %s: 盘上=%r 重算=%r'
                                 % (ep, a.get('seq'), k, a.get(k), b.get(k)))
    if diffs:
        print('[ABORT] 以 D15 %s 重算镜像与盘上现值有 %d 处数值/锚点失配 ⇒ 不得改戳，退出'
              % (D15_VERSION, len(diffs)))
        for x in diffs[:8]:
            print('   ', x)
        return 1

    before = copy.deepcopy(d16)
    before_sha = sha16(p16)

    # —— ② 活戳刷新 ——
    stamp_fixed = 0
    dcc_fixed = 0
    for e in d16['episodes']:
        aud = e['subtitle_style']['subtitle_sync_audit']
        v = aud.get('verified_against_d15')
        if isinstance(v, str) and v.startswith(OLD_STAMP):
            aud['verified_against_d15'] = NEW_STAMP + v[len(OLD_STAMP):]
            stamp_fixed += 1
        # 口径长文本的现值断言（只动这两类「现行版本」表述）
        dcc = e['subtitle_style'].get('dwell_calc_convention', '')
        new_dcc = dcc.replace('D15 现行为 **v1.6**', 'D15 现行为 **%s**' % NEW_STAMP)
        new_dcc = new_dcc.replace('现值仍为 D15 **v1.6** 现行预算',
                                  '现值仍为 D15 **%s** 现行预算' % NEW_STAMP)
        if new_dcc != dcc:
            e['subtitle_style']['dwell_calc_convention'] = new_dcc
            dcc_fixed += 1
        # ③ 留痕追加
        if '【D15 版本活戳刷新 · 2026-10-23 · 分镜导演岗】' not in str(aud.get('verified_note', '')):
            aud['verified_note'] = str(aud.get('verified_note', '')).rstrip('｜') + STAMP_SUFFIX

    # —— ④ 差异白名单 ——
    allowed = ['/version']
    allowed += ['/episodes/%d/subtitle_style/subtitle_sync_audit/' % i for i in range(0, 8)]
    allowed += ['/episodes/%d/subtitle_style/dwell_calc_convention' % i for i in range(0, 8)]
    a = dict(m.flat(before))
    b = dict(m.flat(d16))
    bad = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if not any(k.startswith(pfx) for pfx in allowed):
                bad.append(k)
    if bad:
        print('[ABORT] 差异白名单外变更 %d 处，首 5：%s' % (len(bad), bad[:5]))
        return 1

    # —— ⑤ CAS ——
    cur = json.load(open(p16, encoding='utf-8'))
    if cur.get('version') != GUARD_VERSION or sha16(p16) != before_sha:
        print('[ABORT] 写前复核失败（version/sha 漂移）⇒ 并发写者已动盘，退出不抢盘')
        return 1

    d16['version'] = TO_VERSION

    if args.dry_run:
        print('[DRY-RUN] 将改：verified_against_d15 %d 处 ＋ 口径现值断言 %d 处 ＋ 8 集留痕；'
              'version %s → %s' % (stamp_fixed, dcc_fixed, GUARD_VERSION, TO_VERSION))
        return 0

    bak = os.path.join(root, 'reports', '_bak_D16_U01_d15stamp_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p16, os.path.join(bak, 'D16.json'))
    tmp = p16 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d16, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p16)

    after = json.load(open(p16, encoding='utf-8'))
    if after.get('version') != TO_VERSION:
        print('[ABORT] 写后 version 校验失败')
        return 1
    st = [x['subtitle_style']['subtitle_sync_audit'].get('verified_against_d15')
          for x in after['episodes']]
    if not all(s and s.startswith(NEW_STAMP) for s in st):
        print('[ABORT] 写后活戳校验失败')
        return 1
    print('[OK] D16 U01 %s → %s；活戳 %d 处刷为 %s；口径现值断言 %d 处同步；'
          '8 集留痕已追加；数值/锚点面复核零失配；备份 %s'
          % (GUARD_VERSION, TO_VERSION, stamp_fixed, NEW_STAMP, dcc_fixed, bak))
    return 0


if __name__ == '__main__':
    sys.exit(main())
