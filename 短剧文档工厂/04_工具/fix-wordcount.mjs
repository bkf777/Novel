#!/usr/bin/env node
/**
 * fix-wordcount.mjs —— 自动重算 D08 的 word_count，消除字数口径争议
 *
 * 用法：
 *   node fix-wordcount.mjs --project <项目目录> --unit U01 [--write]
 *
 * 口径（与 validate.mjs 的 V9 完全一致）：
 *   字数 = 汉字数 + 英文/数字单词数；标点与空白不计。
 *   base = 不含 compliance_added 段落的字数合计
 *   compliance_add = 含 compliance_added 段落的字数合计
 *   total = base + compliance_add
 *
 * 不带 --write 时只打印计算结果与差异（试算）。
 */

import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
function arg(name, def = null) {
  const i = argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}
const projectDir = arg('project');
const unit = arg('unit');
const write = argv.includes('--write');

if (!projectDir || projectDir === true) {
  console.error('用法：node fix-wordcount.mjs --project <项目目录> --unit U01 [--write]');
  process.exit(2);
}
const PROJECT = path.resolve(projectDir);

export function countWords(s) {
  const cjk = (s.match(/[\u4e00-\u9fff]/g) || []).length;
  const words = (s.match(/[A-Za-z0-9]+/g) || []).length;
  return cjk + words;
}

const target = path.join(PROJECT, 'units', unit, 'D08.json');
if (!fs.existsSync(target)) {
  console.error(`找不到 ${target}`);
  process.exit(2);
}
const data = JSON.parse(fs.readFileSync(target, 'utf8'));

let changed = 0;
for (const ep of data.episodes || []) {
  let base = 0;
  let add = 0;
  for (const b of ep.body || []) {
    const n = countWords(b.text || '');
    if (b.compliance_added) add += n;
    else base += n;
  }
  const total = base + add;
  const before = JSON.stringify(ep.word_count || {});
  const after = JSON.stringify({ base, compliance_add: add, total });
  if (before !== after) {
    changed += 1;
    console.log(`  ep${ep.ep}: ${before}  →  ${after}`);
    ep.word_count = { base, compliance_add: add, total };
  }
}

const min = 180;
const max = 240;
const totalMax = 330;
for (const ep of data.episodes || []) {
  const w = ep.word_count;
  const flags = [];
  if (w.base < min) flags.push(`基础字数 ${w.base} < ${min}`);
  if (w.base > max) flags.push(`基础字数 ${w.base} > ${max}`);
  if (w.total > totalMax) flags.push(`总量 ${w.total} > ${totalMax}`);
  if (flags.length) console.log(`  ⚠️ ep${ep.ep}: ${flags.join('；')}`);
}

if (write) {
  fs.writeFileSync(target, JSON.stringify(data, null, 2), 'utf8');
  console.log(`✅ 已写回 ${target}（修正 ${changed} 集）`);
} else {
  console.log(changed ? `（试算完成，${changed} 集有差异；加 --write 才落盘）` : '（已一致，无需改动）');
}
process.exit(0);
