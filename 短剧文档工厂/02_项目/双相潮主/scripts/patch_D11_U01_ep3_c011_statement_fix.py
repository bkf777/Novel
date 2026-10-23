#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 U01：ep003 镜3 note 的过时现值陈述订正（企划合规 U01-R47 ① 派单）

来件
────
企划合规（总控）D18 `open_issues` **U01-R47 ①**（12:2x 裁定 · 提示级）：
> `units/U01/D11.json` ep003 镜3 的 note 里写着「**D12 卡 C-011 的 image_prompt
> 仍写「浮出第一道」，属他岗文件，已报视觉设定同步**」⇒ 本岗 12:2x 现盘核实：
> C-011 现值已是「皮肤表面第一次亮起一道黑白游龙纹…」，全卡不含「浮出第一道」
> ⇒ 该留痕陈述**已不成立**（留痕本身保留，指向的现状已变），
> **请分镜导演岗更新这句陈述**，否则台账里会留一条与现盘矛盾的指认。

本岗独立复核（不采信转述，本脚本内自行取证）
────────────────────────────────────────────
· D12 U01 **v1.9** 全卡 JSON 文本中「浮出第一道」出现 **0 次**；
  「第一次亮起」出现 1 次；
· C-011（ep3／shot3）`image_prompt` 现值首句＝
  「近景，主观视角，85mm 固定机位，9:16 竖屏。**右腕特写：皮肤表面第一次亮起一道
  黑白游龙纹**，纹路由腕侧向手背延开……」
⇒ **来件转述属实**，该陈述确已过时。

本脚本做（且只做）一件事
────────────────────────
把 ep003 镜3 note 的**末句现值断言**订正为现值：
  旧：「D12 卡 C-011 的 image_prompt 仍写「浮出第一道」，属他岗文件，已报视觉设定同步。」
  新：「D12 卡 C-011 的 image_prompt **现值已是**「右腕特写：皮肤表面第一次亮起一道
       黑白游龙纹……」（D12 U01 v1.9 全卡不含「浮出第一道」），与本镜正文口径一致，
       **跨岗同步已闭合**。」
并在 note 末尾**追加**一段订正留痕（原句原文保留在留痕中，指向的现状已变）。

⛔ 不动
──────
· note 中另一处「本镜原文「浮出第一道」作废，正文已改」—— 那是**有效留痕**
  （记录本镜正文的改稿动作），按 Q30／S11 原文保留（企划合规 U01-R47 ② 已明确：
  两处命中均为留痕位，唯一要处理的是末句陈述）。
· 本镜任何正文字段（visual_facts／dialogue／sfx／duration_sec／shot_size 等）——
  本脚本**只改 note 这一个字符串**。
· 任何其他集／其他镜的任何字段；D08／D09／D12／D15／D16／D18／03_规格/**／04_工具/**。

守卫
────
① **版本守卫**：D11 U01 为 `v1.{minor}` 且 minor ≥ 15（否则 [NO-OP] exit 0）
② **前提自证守卫**：D12 U01 现盘必须满足「全卡 0 处『浮出第一道』」且
   「C-011 的 image_prompt 含『第一次亮起』」—— **不满足即 [ABORT] 不写盘**
   （不能按一条未经复核的转述去改现值断言）
③ **幂等**：note 已含订正留痕标记 ⇒ [NO-OP] exit 0
④ **差异白名单**：只允许 version ＋ `episodes[2].shots[2].note`
⑤ **CAS**：写前重读 version+SHA，不一致 ⇒ [ABORT] 不覆盖
⑥ **原子写** ＋ **写后回读校验**

用法：python3 scripts/patch_D11_U01_ep3_c011_statement_fix.py --project . [--dry-run]
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
GUARD_MIN_MINOR = 15

OLD_SENT = ('D12 卡 C-011 的 image_prompt 仍写「浮出第一道」，属他岗文件，'
            '已报视觉设定同步。')
NEW_SENT = ('D12 卡 C-011 的 image_prompt **现值已是**「右腕特写：皮肤表面第一次亮起一道'
            '黑白游龙纹……」（D12 U01 v1.9 全卡不含「浮出第一道」），与本镜正文口径一致，'
            '**跨岗同步已闭合**。')
TRACE_MARK = '【陈述订正 · 2026-10-23 12:3x · 分镜导演岗】'
TRACE = (
    TRACE_MARK +
    '本句原表述为「D12 卡 C-011 的 image_prompt 仍写「浮出第一道」，属他岗文件，'
    '已报视觉设定同步。」——承企划合规（总控）D18 `open_issues` **U01-R47 ①** 派单核实，'
    '本岗**按现盘独立复核**（不采信转述）：D12 U01 **v1.9** 全卡 JSON 文本中'
    '「浮出第一道」出现 **0 次**、「第一次亮起」出现 1 次，'
    'C-011（ep3／shot3）`image_prompt` 现值首句为'
    '「近景，主观视角，85mm 固定机位，9:16 竖屏。右腕特写：皮肤表面第一次亮起一道'
    '黑白游龙纹……」⇒ 原句所指的现状已变、该陈述**不再成立**，故按现值订正。'
    '**留痕原文保留**（原句字面保留在本段内，不删改）；'
    '同 note 中另一处「本镜原文「浮出第一道」作废，正文已改」为**有效留痕**'
    '（记录本镜正文的改稿动作），按 Q30／S11 原文保留，未动。'
    '本轮**未改本镜任何正文字段**，只改本 note 的末句现值断言并追加本段。'
)


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
    p11 = os.path.join(root, 'units', 'U01', 'D11.json')
    p12 = os.path.join(root, 'units', 'U01', 'D12.json')

    # —— 数据加载 ——
    d11 = json.load(open(p11, encoding='utf-8'))
    d12 = json.load(open(p12, encoding='utf-8'))

    # —— 守卫①：版本 ——
    m = re.match(r'^v1\.(\d+)$', str(d11.get('version', '')))
    if not m or int(m.group(1)) < GUARD_MIN_MINOR:
        print('[NO-OP] D11 U01 version=%s 不满足 v1.{minor≥%d}'
              % (d11.get('version'), GUARD_MIN_MINOR))
        return 0
    minor = int(m.group(1))
    to_version = 'v1.%d' % (minor + 1)

    # —— 守卫②：前提自证（不采信转述）——
    blob = json.dumps(d12, ensure_ascii=False)
    if '浮出第一道' in blob:
        print('[ABORT] D12 U01 现盘仍含「浮出第一道」⇒ 来件前提不成立，不改陈述，退出')
        return 1
    c011 = None
    for c in d12.get('cards', []):
        if c.get('card_id') == 'C-011':
            c011 = c
            break
    if c011 is None or '第一次亮起' not in str(c011.get('image_prompt', '')):
        print('[ABORT] D12 U01 C-011 缺失或 image_prompt 不含「第一次亮起」⇒ 前提不成立')
        return 1
    print('[OK] 前提自证：D12 U01 %s 全卡 0 处「浮出第一道」，C-011 image_prompt 含「第一次亮起」'
          % d12.get('version'))

    # 定位 ep3 镜3 的 note
    note_holder = None
    for e in d11.get('episodes', []):
        if e.get('ep') != 3:
            continue
        for s in e.get('shots', []):
            if s.get('shot_id') == 3:
                note_holder = s
    if note_holder is None:
        print('[ABORT] 未找到 D11 U01 ep003 镜3')
        return 1
    note = note_holder.get('note', '')

    # —— 守卫③：幂等 ——
    if TRACE_MARK in note:
        print('[NO-OP] ep003 镜3 note 已含订正留痕标记 ⇒ 幂等退出')
        return 0
    if OLD_SENT not in note:
        print('[ABORT] ep003 镜3 note 未命中待订正的原句（字面已变）⇒ 不猜，退出')
        return 1

    before = copy.deepcopy(d11)
    before_sha = sha16(p11)

    new_note = note.replace(OLD_SENT, NEW_SENT)
    new_note = new_note + '｜' + TRACE
    note_holder['note'] = new_note
    d11['version'] = to_version

    # —— 守卫④：差异白名单 ——
    allowed = {'version', 'episodes[2].shots[2].note'}

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

    fb, fa = flat(before), flat(d11)
    for k in sorted(set(fb) | set(fa)):
        if fb.get(k) != fa.get(k) and k not in allowed:
            print('[ABORT] 差异白名单外发生变更：%s' % k)
            return 1

    if args.dry_run:
        print('[DRY-RUN] 目标版本 %s｜note %d → %d 字符'
              % (to_version, len(note), len(new_note)))
        return 0

    # —— 守卫⑤：CAS ——
    cur = json.load(open(p11, encoding='utf-8'))
    if cur.get('version') != before.get('version') or sha16(p11) != before_sha:
        print('[ABORT] CAS 失败：写前重读 version=%s sha16=%s（本次读盘 %s / %s）'
              % (cur.get('version'), sha16(p11), before.get('version'), before_sha))
        return 1

    bak = os.path.join(root, 'reports',
                        '_bak_D11_U01_c011_statement_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p11, os.path.join(bak, 'D11.json'))
    print('[BAK] %s' % bak)

    # —— 守卫⑥：原子写 ——
    tmp = p11 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d11, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p11)

    chk = json.load(open(p11, encoding='utf-8'))
    assert chk.get('version') == to_version
    n2 = None
    for e in chk['episodes']:
        if e.get('ep') == 3:
            for s in e['shots']:
                if s.get('shot_id') == 3:
                    n2 = s.get('note', '')
    if not n2 or TRACE_MARK not in n2 or NEW_SENT not in n2:
        print('[WARN] 写后回读未达成，请人工复核')
        return 1
    print('[OK] 写盘完成 → %s（%d B｜sha16 %s）'
          % (to_version, os.path.getsize(p11), sha16(p11)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
