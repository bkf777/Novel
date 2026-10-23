#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 U01：ep006 镜1 的画外音字面分歧按 Q104 裁定闭合（追加留痕，不改历史叙述）

背景
────
D11 U01 v1.14 的 ep006 镜1 note 里有一段本岗自记的 ⚠️：
  「⚠️ **口径差异（登记待总控裁决，不自行改判）**：D15 v1.11 该条 delivery 写「人物不出画」，
    但本镜 visual_facts 是「厂房暗处的一道剪影暴起冲出」，陆沉**以不可辨识剪影在画幅内**
    （D12 C-021：`char_ids=["LC"]`、不给面部、不给身份锚点）。
    ……若总控要求字面达成「人物不出画」，须改写本镜 visual_facts 并重出 D12 C-021 与 D14 白模
    （景别/机位/镜时不动，只改画面内容），该动作超出本岗本轮授权。」

该 ⚠️ 的**待裁状态已过期**：企划合规（总控）**Q104** 裁定（D18 v1.117 登记）已闭合：
  · 判据＝**角色身份是否在画幅内可辨识**，而不是「人物剪影是否在画幅内」；
  · 三档判据下 ep006 镜1 属**第二档「身份不出画」**（陆沉在画幅内、但身份不可辨识）；
  · D15 U01 **v1.13** 已把 ep6 #1 的 `delivery` 字面由「画外音（人物不出画，首帧给最强符号）」
    订正为「画外音（**身份不出画**，首帧给最强符号）」（只改这一个词）；
  · D16 U01 **v1.22** 已同步该字面（D15↔D16 两侧同字段、同措辞）。

⇒ 因此本段 ⚠️ 里「登记待总控裁决」「须重出 D12 C-021 与 D14 白模」这两项**均已不再适用**：
  裁定结果是「身份不出画」而非「人物不出画」，**画面内容无须改写** ⇒
  D12 C-021 与 D14 白模**无需重出**（景别（中景）／机位（平视）／镜时（11.0s）／镜号一律不动）。

本脚本做（且只做）一件事
────────────────────────
在 **ep006 镜1 的 note 末尾追加**一段「【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】」：
说明待裁状态已闭合、判据口径、两侧同步现状、以及「画面内容无须改写、D12/D14 无需重出」的结论。
⛔ **原 note 全文原文保留**（按 Q30「事件溯源只追加不重写」）——本岗不改写历史叙述。

⛔ 不碰
──────
D08／D09／D12／D15／D16／D18／project.json／00_项目索引.md／03_规格/**／04_工具/**
／ep003／ep005 的镜1 note（Q104 三档判据下这两镜属第一档「人物不出画」，字面成立、不动）
／任何 shot 的 `dialogue`／`visual_facts`／`shot_size`／`camera_angle`／`duration_sec`／`shot_id`
／D12 提示词卡／D14 白模／台账（台账由本岗另行追加）。

守卫
────
① **版本守卫**：D11 U01 现盘 version 须 ＝ v1.14（否则 [NO-OP] exit 0）
② **D15 版本守卫**：D15 U01 现盘 version 须 ＝ v1.13（否则 [NO-OP] exit 0）
③ **内容指纹自证**：ep006 镜1 的 note 须同时含
   「口径差异（登记待总控裁决，不自行改判）」与「人物不出画」⇒ 证明待裁态原文仍在
④ **数据加载后置**：守卫全部置于读入 JSON 之后
⑤ **幂等**：note 已含「【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】」⇒ [NO-OP] exit 0
⑥ **差异白名单**：落盘后逐叶差分，只允许 /version 与 /episodes/5/shots/0/note 变化
⑦ **CAS**：写前重读 version+SHA，若与守卫锚定值不符 ⇒ [ABORT]（防并发抢盘）

用法：python3 scripts/patch_D11_U01_ep6_q104_close.py --project . [--dry-run]
"""
import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD_VERSION = 'v1.14'
TO_VERSION = 'v1.15'
D15_VERSION = 'v1.13'

TARGET_EP = 6
TARGET_SHOT = 1

Q104_STAMP = (
    '📌【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】'
    '上段 ⚠️ 的**「登记待总控裁决」状态已过期**：企划合规（总控）**Q104** 裁定'
    '（D18 v1.117 登记）已闭合该分歧。裁定要点：'
    '① 判据＝**角色身份是否在画幅内可辨识**，而不是「人物剪影是否在画幅内」；'
    '② 三档判据下本镜（ep006 镜1）属**第二档「身份不出画」** —— '
    '陆沉**在画幅内**（D12 C-021：`char_ids=["LC"]`、`char_descriptions=["黑色战术风衣"]`），'
    '但不给面部、不给身份锚点，身份不可辨识；'
    '③ D15 U01 **v1.13** 已把本集首句 `delivery` 字面由「画外音（人物不出画，首帧给最强符号）」'
    '订正为「画外音（**身份不出画**，首帧给最强符号）」（只改这一个词，其余不动）；'
    'D16 U01 **v1.22** 已同步该字面 ⇒ D15↔D16 两侧同字段、同措辞，可逐字段比对；'
    '④ 因此**画面内容无须改写**：上段所述「若总控要求字面达成『人物不出画』，'
    '须改写本镜 visual_facts 并重出 D12 C-021 与 D14 白模」的前提**不成立** —— '
    '裁定结果是「身份不出画」而非「人物不出画」⇒ **D12 C-021 与 D14 白模无需重出**。'
    '本镜落点口径仍为「**身份不出画／先声后人**」，与 D15 mix 追加语「画面内无该角色口型」严格一致；'
    '景别（中景）／机位（平视）／镜时（11.0s）／镜号一律不动 —— 镜1 是 V12 白模构图轴基准。'
    '原 ⚠️ 与原留痕原文保留（事件溯源只追加不重写），本段为现行口径。'
)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    root = os.path.abspath(args.project)
    p11 = os.path.join(root, 'units', 'U01', 'D11.json')
    p15 = os.path.join(root, 'units', 'U01', 'D15.json')

    # —— 数据加载 ——
    d11 = json.load(open(p11, encoding='utf-8'))
    d15 = json.load(open(p15, encoding='utf-8'))

    # —— 守卫（全部置于读入之后）——
    if d11.get('version') != GUARD_VERSION:
        print('[NO-OP] D11 U01 version=%s ≠ 守卫 %s（磁盘已演进，退出不抢盘）'
              % (d11.get('version'), GUARD_VERSION))
        return 0
    if d15.get('version') != D15_VERSION:
        print('[NO-OP] D15 U01 version=%s ≠ 期望 %s（上游已动，退出）'
              % (d15.get('version'), D15_VERSION))
        return 0

    ep = next((e for e in d11['episodes'] if e['ep'] == TARGET_EP), None)
    if ep is None:
        print('[ABORT] D11 U01 无 ep=%d' % TARGET_EP)
        return 1
    shot = next((s for s in ep.get('shots', []) if s.get('shot_id') == TARGET_SHOT), None)
    if shot is None:
        print('[ABORT] ep%d 无 shot_id=%d' % (TARGET_EP, TARGET_SHOT))
        return 1
    note = str(shot.get('note', '') or '')
    if '口径差异（登记待总控裁决，不自行改判）' not in note:
        print('[ABORT] ep%d 镜%d note 未见「口径差异（登记待总控裁决，不自行改判）」⇒ '
              '现盘形态与守卫锚定不符，退出' % (TARGET_EP, TARGET_SHOT))
        return 1
    if '人物不出画' not in note:
        print('[ABORT] ep%d 镜%d note 未见「人物不出画」⇒ 现盘形态与守卫锚定不符，退出'
              % (TARGET_EP, TARGET_SHOT))
        return 1
    if '【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】' in note:
        print('[NO-OP] ep%d 镜%d note 已含 Q104 裁定留痕 ⇒ 幂等退出' % (TARGET_EP, TARGET_SHOT))
        return 0

    before = copy.deepcopy(d11)
    before_sha = sha16(p11)

    # —— 追加 Q104 裁定留痕（原 note 全文保留）——
    shot['note'] = note.rstrip() + '｜' + Q104_STAMP

    # —— 差异白名单 ——
    allowed = ('/version',
               '/episodes/%d/shots/%d/note' % (TARGET_EP - 1, TARGET_SHOT - 1))
    a = dict(flat(before))
    b = dict(flat(d11))
    bad = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if not any(k == pfx or k.startswith(pfx + '/') for pfx in allowed):
                bad.append(k)
    if bad:
        print('[ABORT] 差异白名单外变更 %d 处，首 5：%s' % (len(bad), bad[:5]))
        return 1

    # —— CAS：写前重读 version + SHA ——
    cur = json.load(open(p11, encoding='utf-8'))
    if cur.get('version') != GUARD_VERSION or sha16(p11) != before_sha:
        print('[ABORT] 写前复核失败（version/sha 漂移）⇒ 并发写者已动盘，退出不抢盘')
        return 1

    d11['version'] = TO_VERSION

    if args.dry_run:
        print('[DRY-RUN] 将改：ep%d 镜%d note 追加 Q104 裁定留痕；version %s → %s'
              % (TARGET_EP, TARGET_SHOT, GUARD_VERSION, TO_VERSION))
        return 0

    bak = os.path.join(root, 'reports', '_bak_D11_U01_q104_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p11, os.path.join(bak, 'D11.json'))
    tmp = p11 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d11, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p11)

    # —— 写后回读校验 ——
    after = json.load(open(p11, encoding='utf-8'))
    if after.get('version') != TO_VERSION:
        print('[ABORT] 写后 version 校验失败')
        return 1
    ae = next(e for e in after['episodes'] if e['ep'] == TARGET_EP)
    ash = next(s for s in ae['shots'] if s.get('shot_id') == TARGET_SHOT)
    if '【Q104 裁定落地 · 2026-10-23 · 分镜导演岗】' not in str(ash.get('note', '')):
        print('[ABORT] 写后 note 校验失败')
        return 1
    print('[OK] D11 U01 %s → %s；ep%d 镜%d note 已追加 Q104 裁定留痕（原留痕保留）；备份 %s'
          % (GUARD_VERSION, TO_VERSION, TARGET_EP, TARGET_SHOT, bak))
    return 0


if __name__ == '__main__':
    sys.exit(main())
