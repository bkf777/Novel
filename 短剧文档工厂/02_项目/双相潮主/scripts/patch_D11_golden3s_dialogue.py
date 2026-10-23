#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D11 · 黄金 3 秒改版落盘（U01 ep003 / U02 ep012 / U02 ep016）· 分镜导演岗

起因
----
台本编剧 2026-10-23 11:19:04 落 D08/D09 v1.11/v1.7（U01）、v1.5/v1.3（U02）：
  ① 新增黄金 3 秒首句台词（ep003「比上一趟早。」／ep012「贡献是谁定的。」／ep016「十四天，今晚到。」）；
  ② ep003 骨纹措辞收口为「第一次亮起」（对齐 D05 T20）；
  ③ 合规增量段移出 body ⇒ **body 数组重排**，D11 note 的 `body[N]` 引文整体漂移。

本脚本做（且只做）三件事
------------------------
A. **D11 承接新台词**：3 句新首句写进对应镜位 `dialogue`（本岗字段）。
B. **骨纹措辞收口**：U01 ep003 镜3 `visual_facts`「浮出第一道」→「第一次亮起」。
C. **引文 idx 重刷**：U02 5 处漂移一次校正（内容指纹自证，不靠 idx 猜）。

不碰
----
D08／D09／D12／D13／D14／D15／D16／D18／项目索引／他岗章节；不改任何 `shot_size`／
`camera_angle`／`lens_mm`／`movement`（**D11 景别是 V12 白模构图闸基准，基准不得漂移**）。

守卫（缺一不可）
----------------
① 版本守卫：盘面 D11 U01 ＝ v1.11、D11 U02 ＝ v1.7，否则 `[NO-OP]` exit 0。
② 内容指纹自证：每处替换的旧串必须精确且唯一命中。
③ 结构差异白名单：只允许 `.version` 与白名单内 (ep, shot_id, field) 变动，越界 `[ABORT]`。
④ 幂等：目标串已存在 → 跳过。
⑤ 备份先行：整份复制到 `reports/_bak_d11_golden3s_<时间戳>/`。

不生成图片/视频/音频，不合成 TTS/BGM，不提交 H3 付费生成，不投流上架。
"""
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {'U01': os.path.join(ROOT, 'units', 'U01', 'D11.json'),
         'U02': os.path.join(ROOT, 'units', 'U02', 'D11.json')}
GUARD = {'U01': 'v1.11', 'U02': 'v1.7'}
TO = {'U01': 'v1.12', 'U02': 'v1.8'}

# (ep, shot_id, field, mode, old, new)
EDITS = {
    'U01': [
        (3, 1, 'dialogue', 'replace', '', '陆沉「比上一趟早。」'),
        (3, 1, 'note', 'append', '',
         '📌 D08 v1.11 shot_intent 反查（2026-10-23 · 黄金 3 秒改版）：body[1] 要求'
         '「这句对照必须在第 1 秒被听见：重生信息前置到开场，灰雾提前本身就是本集钩子。」；'
         '本镜第 0 帧即最强符号（青灰双生雾气自地缝涌出＝异化本身），陆沉这句以**画外音**压在'
         '雾气铺开的第一秒入画；镜1 窗 0~12s 内不与任何其他台词重叠（下一条对白「九小时。」在 '
         '16.4s、属镜2）。⚠️ 画外音 ⇒ 陆沉不在本镜画幅内：D12 提示词卡不得把陆沉写进本镜 '
         'image_prompt，D15 按画外音／主观声处理。景别与机位不动（镜1 是 D11 景别基准，白模按此重建）。'),
        (3, 3, 'visual_facts', 'replace',
         '陆沉右手腕骨浮出第一道黑白游龙纹，', '陆沉右手腕的黑白游龙纹第一次亮起，'),
        (3, 3, 'note', 'append', '',
         '⚠️ 措辞收口（2026-10-23 · 黄金 3 秒改版）：D08 v1.11 载明的骨纹条目（idx 9）与 D05 T20 '
         '已收口为「**第一次亮起**」（全剧骨纹由「可见未激活」转为「激活」的唯一一次亮起），'
         '本镜原文「浮出第一道」作废，正文已改。D12 卡 C-011 的 image_prompt 仍写「浮出第一道」，'
         '属他岗文件，已报视觉设定同步。'),
    ],
    'U02': [
        (12, 1, 'dialogue', 'replace',
         '商既衡「请把人数换算成成本。配额按贡献发，不是按人头发。」',
         '陆沉「贡献是谁定的。」／商既衡「请把人数换算成成本。配额按贡献发，不是按人头发。」'),
        (12, 1, 'note', 'replace',
         '📌 D08 shot_intent 反查（2026-10-23）：body[2] 要求「公告第二栏的原文必须被看清',
         '📌 D08 v1.5 shot_intent 反查（2026-10-23 · 黄金 3 秒改版）：body[1] 要求'
         '「这句质疑必须与公告出现同帧——它把「全服公告」从背景变成对他的审判。」；'
         '本镜第 0 帧即全服公告投影（最强符号＝制度把活人写进成本表），陆沉这句以**画外音**压在'
         '公告首行亮起的第一秒入画；镜1 窗 0~13s。⚠️ 画外音 ⇒ 陆沉不在本镜画幅内：'
         'D12 不得把陆沉写进本镜 image_prompt，D15 按画外音／主观声处理。'
         '📌 D08 v1.5 shot_intent 反查（2026-10-23）：body[3] 要求「公告第二栏的原文必须被看清'),
        (12, 2, 'note', 'replace',
         'body[6] 要求「被清走的人回头看厂门这个动作必须被看见',
         'body[7] 要求「被清走的人回头看厂门这个动作必须被看见'),
        (12, 4, 'note', 'replace',
         'body[10] 要求「归一度读数 1.2% 必须可读',
         'body[11] 要求「归一度读数 1.2% 必须可读'),
        (16, 1, 'dialogue', 'replace', '', '陆沉「十四天，今晚到。」'),
        (16, 1, 'note', 'append', '',
         '📌 D08 v1.5 shot_intent 反查（2026-10-23 · 黄金 3 秒改版）：body[1] 要求'
         '「这句必须与面板大限提醒同帧，第 1 秒就把「期限」与「火」绑在一起。」；'
         '本镜第 0 帧即全城面板大限提醒（最强符号＝十四天大限），陆沉这句以**画外音**压在'
         '面板首行亮起的第一秒入画；镜1 窗 0~12s。⚠️ 画外音 ⇒ 陆沉不在本镜画幅内：'
         'D12 不得把陆沉写进本镜 image_prompt，D15 按画外音／主观声处理。'),
        (16, 4, 'note', 'replace',
         'body[8] 要求「厂门暗处的影刃必须被看见',
         'body[9] 要求「厂门暗处的影刃必须被看见'),
        (16, 4, 'note', 'replace',
         'body[11] 要求「白日转黑与天幕压下的瞬间必须被看见',
         'body[12] 要求「白日转黑与天幕压下的瞬间必须被看见'),
        (16, 4, 'note', 'replace',
         'body[12] 要求「归一度读数 1.4% 必须可读',
         'body[13] 要求「归一度读数 1.4% 必须可读'),
    ],
}

ALLOWED = set()
for unit, edits in EDITS.items():
    for (ep, shot_id, field, mode, old, new) in edits:
        ALLOWED.add((unit, ep, shot_id, field))


def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def dump(p, d):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bak = os.path.join(ROOT, 'reports', '_bak_d11_golden3s_%s' % stamp)
    os.makedirs(bak, exist_ok=True)
    changed = []
    for unit in ('U01', 'U02'):
        path = FILES[unit]
        d = load(path)
        if d.get('version') != GUARD[unit]:
            print('[NO-OP] %s D11 version=%s ≠ 守卫 %s（盘面已演进，不写盘）'
                  % (unit, d.get('version'), GUARD[unit]))
            continue
        shutil.copy2(path, os.path.join(bak, '%s_D11.json' % unit))
        before = load(path)
        eps = {e['ep']: e for e in d['episodes']}
        for (ep_no, shot_id, field, mode, old, new) in EDITS[unit]:
            s = None
            for x in eps[ep_no]['shots']:
                if x['shot_id'] == shot_id:
                    s = x
                    break
            if s is None:
                print('[ABORT] %s ep%s 镜%s 不存在' % (unit, ep_no, shot_id))
                return 1
            cur = s.get(field, '')
            if mode == 'append':
                if new in cur:
                    print('  · 幂等 %s ep%s 镜%s %s append 已存在' % (unit, ep_no, shot_id, field))
                    continue
                s[field] = cur + new
            else:
                if cur == new:
                    print('  · 幂等 %s ep%s 镜%s %s 已是目标值' % (unit, ep_no, shot_id, field))
                    continue
                if old:
                    if old not in cur:
                        print('[ABORT] %s ep%s 镜%s %s 旧串未命中：%r' % (unit, ep_no, shot_id, field, old[:48]))
                        return 1
                    if cur.count(old) != 1:
                        print('[ABORT] %s ep%s 镜%s %s 旧串非唯一命中' % (unit, ep_no, shot_id, field))
                        return 1
                    s[field] = cur.replace(old, new)
                else:
                    if cur:
                        print('[ABORT] %s ep%s 镜%s %s 原值非空，拒绝覆盖：%r'
                              % (unit, ep_no, shot_id, field, cur[:48]))
                        return 1
                    s[field] = new
            changed.append('%s ep%s 镜%s %s %s' % (unit, ep_no, shot_id, field, mode))
        # 结构差异白名单
        diff = []
        for e_b, e_a in zip(before['episodes'], d['episodes']):
            for k in e_b:
                if k == 'shots':
                    continue
                if e_b[k] != e_a.get(k):
                    diff.append((e_b['ep'], None, k))
            for s_b, s_a in zip(e_b['shots'], e_a['shots']):
                for k in s_b:
                    if s_b[k] != s_a.get(k):
                        diff.append((e_b['ep'], s_b['shot_id'], k))
        illegal = [x for x in diff if (unit, x[0], x[1], x[2]) not in ALLOWED]
        if illegal:
            print('[ABORT] 结构差异越界：%s' % illegal)
            return 1
        d['version'] = TO[unit]
        dump(path, d)
        print('[OK] %s D11 %s → %s（变更 %d 处，差异 %d 处全在白名单内）'
              % (unit, GUARD[unit], TO[unit], len([c for c in changed if c.startswith(unit)]), len(diff)))
    print('备份目录：%s' % bak)
    for c in changed:
        print('  · %s' % c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
