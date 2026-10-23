#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 U01：ep002 镜2 的 `body[5]` 锚点订正（D08 改稿导致 D08↔D11 落镜契约断裂）

起因
────
台本编剧于 2026-10-23 12:3x 重写 D08 U01 **ep002 的 body**（**15 条 → 13 条**，
结构变化：原 body[5] 的 action「侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。」
被并入新 body[4]「卷帘门彻底轰然下坠锁死，内侧焊起简易闸门，薪火橙焊花溅落卷帘门上。」，
原 body[5] 位置改为 **dialogue**「前门焊死。叶家和灰潮，谁都别想轻易踏进一步。」）。
⇒ D11 U01 ep002 镜2 note 里的 **「📌 D08 shot_intent 反查：body[5] 要求…」** 锚点
**已指错对象**（body[5] 现在是台词，不是承载该 shot_intent 的条目）。

本岗独立取证（不采信转述）
──────────────────────────
· D08 U01 现盘 ep002 body 逐条点算：**带 shot_intent 的条目 ＝ body[4]／body[8]／body[10]**
  （改稿前为 body[5]／body[9]／body[11]），
  其 shot_intent 原文亦已改写：
    body[4]「侧门内侧焊死与闸门成形必须看清，这是据点防守的关键。」
    body[8]「后方排渣管廊连通处置线外圈必须看清，这是后路与伏击动线。」
    body[10]「钟楼方向与第一声钟响必须在画面里有出处，确认十一下非凭空响起。」
· D11 U01 ep002 镜2 的 `visual_facts` 现值仍为
  「大跨厂房内侧，卷帘门彻底轰然下坠锁死，**侧门内侧焊起简易闸门**，薪火橙（#E07B39）
  **焊花瞬时溅落卷帘门**；……」⇒ **画面事实未变**，故只需把锚点改指 body[4]、
  并把引用的 shot_intent 原文刷新为现值。
· D12 U01 卡 **C-006**（ep002 shot2）现值仍含「侧门内侧焊起简易闸门，焊花瞬时溅落卷帘门」
  与 video_prompt「**闸门焊缝逐渐成形**」⇒ D11 note 中
  「过程性的『焊缝逐渐成形』由 D12 卡 C-006 的 video_prompt 承接落实」**仍然成立**。
· 覆盖轴复核（`scripts/shotintent_map_U01.mjs` 表）：现带 SI 的 idx 集合与表内 idx 集合
  **仅 ep2 不一致**（现 4/8/10 vs 表内 5/9/11），ep1／ep3–ep8 全部一致。

本脚本做（且只做）一件事
────────────────────────
把 D11 U01 ep002 镜2 note 里那一条 shot_intent 反查句的**锚点与引文**订正为现值：
  旧：「body[5] 要求「侧门焊死这一步必须被完整看见：焊缝成形的全过程要交代清楚，
       这道门是本集『占位』的关键」」
  新：「body[4] 要求「侧门内侧焊死与闸门成形必须看清，这是据点防守的关键。」」
并在 note 末尾**追加**一段锚点订正留痕（原锚点与原引文原文保留在本段内）。

⛔ 不动
──────
· 本镜 `visual_facts`／`dialogue`／`sfx`／`duration_sec`／`shot_size` 等**任何正文字段**；
· 同 note 中【引文订正 2026-10-23】段（记录 D08 v1.7→v1.8 的一次历史订正）—— 原文保留；
· D11 其余任何集／镜的任何字段；D08／D09／D12／D15／D16／D18／03_规格/**／04_工具/**。

守卫
────
① **版本守卫**：D11 U01 为 `v1.{minor}` 且 minor ≥ 16（否则 [NO-OP] exit 0）
② **前提自证**：D08 U01 现盘 ep002 body[4] 必须带 shot_intent 且其原文含
   「侧门内侧焊死与闸门成形必须看清」，且 body[5] 必须是 dialogue
   —— **不满足即 [ABORT] 不写盘**（不按未复核的前提改锚点）
③ **幂等**：note 已含订正留痕标记 ⇒ [NO-OP] exit 0
④ **差异白名单**：只允许 version ＋ `episodes[1].shots[1].note`
⑤ **CAS** ⑥ **原子写** ⑦ **写后回读校验**

用法：python3 scripts/patch_D11_U01_ep2_bodyidx_repoint.py --project . [--dry-run]
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
GUARD_MIN_MINOR = 16

OLD_FRAG = ('body[5] 要求「侧门焊死这一步必须被完整看见：焊缝成形的全过程要交代清楚，'
            '这道门是本集『占位』的关键」')
NEW_FRAG = ('body[4] 要求「侧门内侧焊死与闸门成形必须看清，这是据点防守的关键。」')
TRACE_MARK = '【锚点订正 · 2026-10-23 12:4x · 分镜导演岗】'
TRACE = (
    TRACE_MARK +
    '上方「📌 D08 shot_intent 反查」句的**锚点与引文已订正为现值**：'
    '台本编剧于 2026-10-23 12:3x 重写 D08 U01 **ep002 的 body（15 条 → 13 条）**——'
    '原 body[5] 的 action「侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。」被并入'
    '新 body[4]「卷帘门彻底轰然下坠锁死，内侧焊起简易闸门，薪火橙焊花溅落卷帘门上。」，'
    '原 body[5] 位置改为 dialogue「前门焊死。叶家和灰潮，谁都别想轻易踏进一步。」'
    '⇒ 原锚点「body[5]」**已指错对象**，本岗据此改指 **body[4]**，'
    '并把所引 shot_intent 原文刷新为现值'
    '「侧门内侧焊死与闸门成形必须看清，这是据点防守的关键。」'
    '（改稿前原文为「侧门焊死这一步必须被完整看见：焊缝成形的全过程要交代清楚，'
    '这道门是本集『占位』的关键」——**留痕原文保留**于本段，未删改。）'
    '**本镜正文一字未动**：现盘 `visual_facts` 仍为「……侧门内侧焊起简易闸门，'
    '薪火橙（#E07B39）焊花瞬时溅落卷帘门；……」，'
    'D12 U01 卡 C-006（ep002 shot2）现值仍含「闸门焊缝逐渐成形」⇒ '
    '「过程性的『焊缝逐渐成形』由 D12 卡 C-006 的 video_prompt 承接落实」**仍然成立**。'
    '**覆盖轴复核**：`scripts/shotintent_map_U01.mjs` 的 idx 集合与现带 shot_intent 的 '
    'idx 集合，现仅 ep2 不一致（现 4／8／10 vs 表内 5／9／11），ep1／ep3–ep8 全部一致；'
    '本岗已同步更新该表的三行（**表体已随现盘重挂，详见表内注释**）。'
    '**另一项仍挂账（本岗不代改）**：D08 新 body[4] 写的是「**内侧**焊起简易闸门」，'
    '而本镜 `visual_facts` 与 D12 C-006 写的是「**侧门内侧**焊起简易闸门」'
    '⇒ 差一个「侧门」前缀，属他岗正文（台本编剧 D08／视觉设定 D12），'
    '本岗只登记不判改，本镜正文亦未因此改动。'
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
    p08 = os.path.join(root, 'units', 'U01', 'D08.json')

    d11 = json.load(open(p11, encoding='utf-8'))
    d08 = json.load(open(p08, encoding='utf-8'))

    # —— 守卫① ——
    m = re.match(r'^v1\.(\d+)$', str(d11.get('version', '')))
    if not m or int(m.group(1)) < GUARD_MIN_MINOR:
        print('[NO-OP] D11 U01 version=%s 不满足 v1.{minor≥%d}'
              % (d11.get('version'), GUARD_MIN_MINOR))
        return 0
    minor = int(m.group(1))
    to_version = 'v1.%d' % (minor + 1)

    # —— 守卫②：前提自证 ——
    ep2 = [e for e in d08.get('episodes', []) if e.get('ep') == 2]
    if not ep2:
        print('[ABORT] D08 U01 无 ep002')
        return 1
    body = ep2[0].get('body', [])
    if len(body) != 13:
        print('[ABORT] D08 U01 ep002 body 现为 %d 条（≠ 13）⇒ 前提已变，不改锚点，退出'
              % len(body))
        return 1
    si4 = str(body[4].get('shot_intent', '') or '')
    if '侧门内侧焊死与闸门成形必须看清' not in si4:
        print('[ABORT] D08 U01 ep002 body[4] 的 shot_intent 不含预期现值 ⇒ 前提不成立')
        return 1
    if body[5].get('type') != 'dialogue':
        print('[ABORT] D08 U01 ep002 body[5] 现为 %r（非 dialogue）⇒ 前提不成立'
              % body[5].get('type'))
        return 1
    print('[OK] 前提自证：D08 U01 ep002 body 13 条｜body[4] 带 shot_intent（现值命中）'
          '｜body[5] 现为 dialogue')

    # 定位 ep2 镜2
    ep2_d11 = [e for e in d11.get('episodes', []) if e.get('ep') == 2]
    if not ep2_d11:
        print('[ABORT] D11 U01 无 ep002')
        return 1
    shots = ep2_d11[0].get('shots', [])
    s2 = next((s for s in shots if s.get('shot_id') == 2), None)
    if s2 is None:
        print('[ABORT] D11 U01 ep002 无镜2')
        return 1
    note = s2.get('note', '')

    # —— 守卫③：幂等 ——
    if TRACE_MARK in note:
        print('[NO-OP] ep002 镜2 note 已含锚点订正留痕 ⇒ 幂等退出')
        return 0
    if OLD_FRAG not in note:
        print('[ABORT] ep002 镜2 note 未命中待订正的原句（字面已变）⇒ 不猜，退出')
        return 1

    before = copy.deepcopy(d11)
    before_sha = sha16(p11)

    new_note = note.replace(OLD_FRAG, NEW_FRAG) + '｜' + TRACE
    s2['note'] = new_note
    d11['version'] = to_version

    # —— 守卫④：差异白名单 ——
    allowed = {'version', 'episodes[1].shots[1].note'}

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
            print('       before=%r' % (fb.get(k),))
            print('       after =%r' % (fa.get(k),))
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
                        '_bak_D11_U01_ep2_bodyidx_%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(bak, exist_ok=True)
    shutil.copy2(p11, os.path.join(bak, 'D11.json'))
    print('[BAK] %s' % bak)

    # —— 守卫⑥：原子写 ——
    tmp = p11 + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d11, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p11)

    # —— 守卫⑦：写后回读 ——
    chk = json.load(open(p11, encoding='utf-8'))
    assert chk.get('version') == to_version
    n2 = None
    for e in chk['episodes']:
        if e.get('ep') == 2:
            for s in e['shots']:
                if s.get('shot_id') == 2:
                    n2 = s.get('note', '')
    if not n2 or TRACE_MARK not in n2 or NEW_FRAG not in n2:
        print('[WARN] 写后回读未达成，请人工复核')
        return 1
    print('[OK] 写盘完成 → %s（%d B｜sha16 %s）'
          % (to_version, os.path.getsize(p11), sha16(p11)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
