#!/usr/bin/env node
/**
 * V7「局部特写·无可见锚点」豁免 —— 负测（企划合规 2026-10-23 06:5x 裁定 S25）
 *
 * 目的：证明本次放宽**只**针对「纯局部身体描写」这一类，
 *       「prompt 里写了角色外观却没登记 char_descriptions」的真漏填**仍会被 warning 拦下**（防假绿，Q60）。
 *
 * 受检条数：5 条构造用例（每条独立判定）—— 结论必须附受检条数（Q49）。
 * 退出码：0 = 全部判据成立；1 = 有用例不成立（豁免过宽或过窄）。
 */
import { RULES } from '../lib/rules.mjs';

const V7 = RULES.find((r) => r.id === 'V7');
if (!V7) {
  console.error('FAIL: 找不到 V7 规则');
  process.exit(1);
}

const ANCHORS = [
  {
    char_id: 'SQC',
    anchor_text: '苏清辞，25 岁成年女性，娇小体型；知性温婉的柳叶眉；挽发；声线清亮傲娇；身穿白色科研风衣；怀抱数据板，板面文字层一律中文。',
    markers: ['白色科研风衣', '数据板', '挽发', '柳叶眉'],
  },
];

const mkCard = (id, image_prompt, video_prompt = '') => ({
  card_id: id,
  ep: 11,
  shot_id: 1,
  image_prompt,
  video_prompt,
  negatives: [],
  params: {},
  consistency_refs: { char_ids: ['SQC'], motifs: [], palette: [] },
  char_descriptions: [],
  source: 'both',
});

const CASES = [
  {
    name: '① 真实 C-109（纯指尖入画，无任何外观描写）',
    expect: 0,
    card: mkCard('C-109', '特写，俯视，50mm，固定，9:16 竖屏。钢桌上摊开一张防御图纸；苏清辞的指尖点过每一项标注；纸面墨迹未干，角落有一块水渍。'),
  },
  {
    name: '② 真实 C-119（纯手部入画）',
    expect: 0,
    card: mkCard('C-119', '特写，俯视，50mm，固定，9:16 竖屏。一枚律条被推上交易台；苏清辞的手摸过纹路，指腹在纹路上停住；台面上只有这一枚实物。'),
  },
  {
    name: '③ 真漏填：prompt 写了角色外观却未填 char_descriptions（必须仍报 warning）',
    expect: 1,
    card: mkCard('C-900', '中景，平视，35mm 固定机位，9:16 竖屏。苏清辞身穿白色科研风衣站在钢桌前，柳叶眉微蹙。'),
  },
  {
    name: '④ 角色名根本没出现在 prompt 里（更可能是漏登记，必须仍报 warning）',
    expect: 1,
    card: mkCard('C-901', '特写，俯视，50mm 固定机位。钢桌上摊开一张防御图纸，一只手指点过每一项标注。'),
  },
  {
    name: '⑤ 边界：局部特写但附近出现外观词（必须仍报 warning）',
    expect: 1,
    card: mkCard('C-902', '特写，俯视，50mm 固定机位。苏清辞的指尖点过图纸，袖口的白大褂边缘入画。'),
  },
];

const run = (card) => {
  const ctx = { files: { D10: { character_anchors: ANCHORS }, D12: { cards: [card] } } };
  const r = V7.run(ctx);
  return { w: r.warnings.length, e: r.errors.length, warnings: r.warnings };
};

let failed = 0;
console.log(`受检条数：${CASES.length} 条构造用例\n`);
for (const c of CASES) {
  const r = run(c.card);
  const ok = r.w === c.expect;
  if (!ok) failed += 1;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${c.name}`);
  console.log(`     期望 warning ${c.expect} ／ 实际 ${r.w}（error ${r.e}）`);
  if (r.warnings.length) console.log(`     ${r.warnings[0]}`);
}

console.log(`\n结论：${CASES.length - failed}/${CASES.length} 条成立`);
if (failed) {
  console.log('FAIL: 判据不成立 —— 豁免过宽（假绿）或过窄。');
  process.exit(1);
}
console.log('PASS: 豁免仅限「纯局部身体描写」；真漏填与角色名缺失仍被 warning 拦下（防假绿，Q60）。');
process.exit(0);
