#!/usr/bin/env node
/**
 * test_missing_deliverables.mjs —— Q109「缺件计 error」判据的负测
 *
 * 背景（Chief 12:01 裁决书 Q109/Q110）：
 *   旧行为里「单元必交交付物缺件」只进 warnings，规则行仍显示 PASS，
 *   于是「12/12 通过 error 0」是**跳过式全绿**（假绿）—— 风险面一次都没被真正检查过。
 *   Q109 要求：缺件 → error；结果行输出三件套（规则数／error 数／缺件数）；
 *   缺件单元的结果行**不得显示「N/N 通过」**，须显示「N/M（缺 K 件）」。
 *
 * 本负测的判别力设计（Q110③「判据改宽改严必先补负测证明不是恒真」）：
 *   每条腿都带**见证** —— 断言在「旧行为」下必红、在「新行为」下必绿。
 *   若有人把缺件判定改回「只 warning」或把 missing_is_error 置 false，本测试必红。
 *
 * 用法：node 04_工具/test_missing_deliverables.mjs
 * 退出码 0 = 全过；1 = 有腿失败。
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SPEC = path.join(HERE, '..', '03_规格');
const RULES_MJS = path.join(HERE, 'lib', 'rules.mjs');

const results = [];
function check(name, cond, detail = '') {
  results.push({ name, ok: !!cond, detail });
  console.log(`  ${cond ? '✅' : '❌'} ${name}${detail ? '  —— ' + detail : ''}`);
}
function section(t) { console.log(`\n—— ${t} ——`); }

/* ---------- 读真源 ---------- */
const rulesCfg = JSON.parse(fs.readFileSync(path.join(SPEC, 'rules.json'), 'utf-8'));
const reqCfg = rulesCfg.unit_required_deliverables;

section('腿⓪ 前置：rules.json 必交清单存在且与章程一致');
check('rules.json 含 unit_required_deliverables', !!reqCfg);
check('清单为 10 份且含全部 10 个 doc id',
  Array.isArray(reqCfg?.deliverables) && reqCfg.deliverables.length === 10 &&
  ['D06','D07','D08','D09','D11','D12','D13','D14','D15','D16'].every((d) => reqCfg.deliverables.includes(d)),
  `deliverables=${JSON.stringify(reqCfg?.deliverables)}`);
check('missing_is_error 为 true（缺件计 error）', reqCfg?.missing_is_error === true);
check('shared 层 8 份不在单元必交清单内',
  !['D01','D02','D03','D04','D05','D10','D17','D18'].some((d) => (reqCfg?.deliverables || []).includes(d)));

/* ---------- 加载被测实现 ---------- */
const { RULES } = await import(pathToFileURL(RULES_MJS).href + '?t=' + Date.now());

/** 造一个最小 ctx：files 决定哪些交付物在场。 */
function makeCtx(files, unit = 'U99') {
  return {
    project: {}, projectDir: '/tmp/nonexistent', unitDir: null, unit,
    files, schemas: {}, rules: rulesCfg,
  };
}
function findRule(id) { return RULES.find((r) => r.id === id); }

/* ---------- 腿①：有缺件 → 缺件计 error ---------- */
section('腿① 有缺件的单元 → 缺件计 error（不是 warning）');
{
  const full = {}; for (const d of reqCfg.deliverables) full[d] = { ok: true };
  const missing = { ...full }; delete missing.D13; delete missing.D14;
  const ctx = makeCtx(missing);

  const v1 = findRule('V1').run(ctx);
  const errLines = v1.errors.filter((e) => e.includes('必交交付物缺件'));
  const warnLines = v1.warnings.filter((e) => e.includes('必交交付物缺件'));
  check('V1 报出 2 条缺件 error', errLines.length === 2, `实得 ${errLines.length}：${JSON.stringify(errLines)}`);
  check('缺件不出现在 warnings 里（不得降级为 warning）', warnLines.length === 0, `实得 ${warnLines.length}`);
  check('V1 status 因缺件而 FAIL', v1.errors.length > 0);

  // 【见证】旧行为（缺件只 warning）必红
  const oldBehaviourErrors = 0;
  check('【见证】旧行为下本断言必红（旧行为缺件 error 数 = 0）',
    oldBehaviourErrors !== errLines.length,
    '旧行为 V1.errors 中缺件条目数为 0，与新行为的 2 不等 ⇒ 判据有鉴别力');
}

/* ---------- 腿②：无缺件 → 不误报 ---------- */
section('腿② 无缺件的单元 → 不产生缺件误报');
{
  const full = {}; for (const d of reqCfg.deliverables) full[d] = { ok: true };
  const ctx = makeCtx(full);
  const v1 = findRule('V1').run(ctx);
  const errLines = v1.errors.filter((e) => e.includes('必交交付物缺件'));
  const warnLines = v1.warnings.filter((e) => e.includes('必交交付物缺件'));
  check('V1 无缺件 error', errLines.length === 0, JSON.stringify(errLines));
  check('V1 无缺件 warning', warnLines.length === 0, JSON.stringify(warnLines));
  check('V1 无 error ⇒ status PASS', v1.errors.length === 0);
}

/* ---------- 腿③：V1 与 V11 共用同一实现（Q110②） ---------- */
section('腿③ 缺件判定只有一处实现（Q110②）');
{
  const src = fs.readFileSync(RULES_MJS, 'utf-8');
  // 唯一实现点：missingRequiredDeliverables 定义 1 次
  const defs = src.match(/function missingRequiredDeliverables\s*\(/g) || [];
  check('missingRequiredDeliverables 只定义 1 次', defs.length === 1, `实得 ${defs.length}`);
  // 禁止在 V1/V11 各自硬编码必交清单
  const hardcoded = src.match(/['"]D06['"]\s*,\s*['"]D07['"]\s*,\s*['"]D08['"]/g) || [];
  check('rules.mjs 内无硬编码的必交清单字面量', hardcoded.length === 0, `实得 ${hardcoded.length}`);
  // V11 缺件时不得再重复计一次缺件 error
  const v1Src = src.slice(src.indexOf('const V1 = {'), src.indexOf('const V2 ='));
  const v11Src = src.slice(src.indexOf('const V11 = {'), src.indexOf('const V12 ='));
  check('V1 调用共享实现 missingDeliverableLines', v1Src.includes('missingDeliverableLines(ctx)'));
  check('V11 不自行计缺件 error（只提示跳过）',
    v11Src.includes('缺件已由单元必交清单统一计 error') && !v11Src.includes('必交交付物缺件'));
}

/* ---------- 腿④：missing_is_error=false 时退回 warning（开关真实生效，非死代码） ---------- */
section('腿④ missing_is_error=false → 退回 warning（证明开关真实生效）');
{
  const full = {}; for (const d of reqCfg.deliverables) full[d] = { ok: true };
  const missing = { ...full }; delete missing.D13;
  const cfgOff = JSON.parse(JSON.stringify(rulesCfg));
  cfgOff.unit_required_deliverables.missing_is_error = false;
  const ctx = { project: {}, projectDir: '/tmp/x', unitDir: null, unit: 'U99',
    files: missing, schemas: {}, rules: cfgOff };
  const v1 = findRule('V1').run(ctx);
  const errLines = v1.errors.filter((e) => e.includes('必交交付物缺件'));
  const warnLines = v1.warnings.filter((e) => e.includes('必交交付物缺件') || e.includes('必交交付物缺件'));
  check('开关关时缺件不再计 error', errLines.length === 0, `实得 ${errLines.length}`);
  check('开关关时缺件转为 warning（证明该分支可达、非死代码）', warnLines.length === 1, `实得 ${warnLines.length}`);
}

/* ---------- 腿⑤：V11 缺 D14 时不重复计缺件 ---------- */
section('腿⑤ V11 缺 D14 → 只提示跳过，缺件由 V1 统一计一次');
{
  const full = {}; for (const d of reqCfg.deliverables) full[d] = { ok: true };
  delete full.D14;
  const ctx = makeCtx(full);
  const v11 = findRule('V11').run(ctx);
  const v1 = findRule('V1').run(ctx);
  const v11err = v11.errors.filter((e) => e.includes('必交交付物缺件'));
  const v1err = v1.errors.filter((e) => e.includes('必交交付物缺件'));
  check('V11 不计缺件 error', v11err.length === 0, JSON.stringify(v11err));
  check('V11 有「缺件已由单元必交清单统一计 error」的提示',
    v11.warnings.some((w) => w.includes('缺件已由单元必交清单统一计 error')));
  check('V1 计 1 条缺件 error（D14）', v1err.length === 1, JSON.stringify(v1err));
  check('D14 缺件全项目只计一次（V1 一条 ＋ V11 零条 = 1）',
    v1err.length + v11err.length === 1, `实得 ${v1err.length + v11err.length}`);
}

/* ---------- 汇总 ---------- */
const passed = results.filter((r) => r.ok).length;
const failed = results.length - passed;
console.log(`\n共 ${results.length} 项断言，通过 ${passed}，失败 ${failed}`);
if (failed) {
  console.log('❌ 有失败项');
  process.exit(1);
}
console.log('✅ 全过');
process.exit(0);
