#!/usr/bin/env node
/**
 * validate.mjs —— AI短剧文档工厂 · 每出口硬校验器
 *
 * 用法：
 *   node validate.mjs --project <项目目录> [--unit U01] [--doc D07] [--json]
 *   node validate.mjs --project 02_项目/双相潮主 --unit U01
 *
 * 退出码：0 = 全绿；1 = 有 error；2 = 参数/IO 错误
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { RULES } from './lib/rules.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FACTORY_ROOT = path.resolve(__dirname, '..');

/* ---------- 参数 ---------- */
const argv = process.argv.slice(2);
function arg(name, def = null) {
  const i = argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}
const projectDir = arg('project');
const onlyUnit = arg('unit');
const onlyDoc = arg('doc');
const asJson = argv.includes('--json');
const strict = argv.includes('--strict');

if (!projectDir || projectDir === true) {
  console.error('用法：node validate.mjs --project <项目目录> [--unit U01] [--doc D07] [--json] [--strict]');
  process.exit(2);
}
const PROJECT = path.resolve(projectDir);
if (!fs.existsSync(PROJECT)) {
  console.error(`项目目录不存在：${PROJECT}`);
  process.exit(2);
}

/* ---------- 读取规格 ---------- */
const SPEC_DIR = path.join(FACTORY_ROOT, '03_规格');
const schemas = JSON.parse(fs.readFileSync(path.join(SPEC_DIR, 'schema.json'), 'utf8'));
const rulesCfg = fs.existsSync(path.join(SPEC_DIR, 'rules.json'))
  ? JSON.parse(fs.readFileSync(path.join(SPEC_DIR, 'rules.json'), 'utf8'))
  : {};

/* ---------- 读取项目真源 ---------- */
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}
const project = readJson(path.join(PROJECT, 'project.json')) || {};

/* ---------- 汇总可见交付物 ---------- */
// 共享层（项目级）：shared/ 下 D01~D05、D10、D17、D18
// 单元层：units/<UNIT>/ 下 D06~D09、D11~D16
function collectFiles(unit) {
  const files = {};
  const sharedDir = path.join(PROJECT, 'shared');
  if (fs.existsSync(sharedDir)) {
    for (const f of fs.readdirSync(sharedDir)) {
      if (!f.endsWith('.json')) continue;
      const id = path.basename(f, '.json');
      const obj = readJson(path.join(sharedDir, f));
      if (obj) files[id] = obj;
    }
  }
  const unitsRoot = path.join(PROJECT, 'units');
  const unitIds = unit
    ? [unit]
    : (fs.existsSync(unitsRoot) ? fs.readdirSync(unitsRoot).filter((d) => fs.statSync(path.join(unitsRoot, d)).isDirectory()).sort() : []);
  for (const uid of unitIds) {
    const ud = path.join(unitsRoot, uid);
    if (!fs.existsSync(ud)) continue;
    for (const f of fs.readdirSync(ud)) {
      if (!f.endsWith('.json')) continue;
      const id = path.basename(f, '.json');
      const obj = readJson(path.join(ud, f));
      if (obj) files[id] = obj;
    }
  }
  return { files, unitIds };
}

/* ---------- 逐单元汇总（v1.1 · 2026-10-23 04:45 企划合规修复） ----------
 * ⚠️ 历史缺陷（已修）：旧实现 `collectFiles(null)` 把**所有单元压进同一张以 doc_id 为键的扁平表**，
 *   后遍历单元覆盖先遍历单元；而 `ctx.unit` 又恒取 `unitIds[0]`、`ctx.unitDir` 也指向该单元。
 *   结果：无 `--unit` 的「全项目跑」既不是全项目校验、也不是单单元校验，而是**混装校验** ——
 *   D11 取自最后一个单元、D13/D14 取自另一个单元 → 报出大量跨单元错配（实测 error 128）；
 *   更危险的方向是：一旦后一个单元产出了同名交付物，V11 会用「后单元的 D11」校验「后单元的 D14」而通过，
 *   **先单元的 D11×D14 组合从此不再被校验却报绿**（假绿）。
 * 本实现：**每个单元各自独立 collectFiles(unit) → 各自独立跑规则**，禁止跨单元合并。
 *   共享层文档在每个单元轮次都会被检查（语义＝每个单元都验证一遍共享层），
 *   错误按单元分节呈现，summary 为各单元合计。**单单元（--unit X）路径行为逐字节不变。 */
const unitsRoot = path.join(PROJECT, 'units');
const allUnitIds = fs.existsSync(unitsRoot)
  ? fs.readdirSync(unitsRoot)
      .filter((d) => fs.statSync(path.join(unitsRoot, d)).isDirectory())
      .sort()
  : [];
const singleUnit = onlyUnit && onlyUnit !== true ? onlyUnit : null;
const runUnits = singleUnit ? [singleUnit] : allUnitIds;

if (!runUnits.length) {
  console.error('未找到任何交付物 JSON。目录结构应为：');
  console.error('  <项目>/project.json');
  console.error('  <项目>/shared/D01.json …');
  console.error('  <项目>/units/U01/D06.json …');
  process.exit(2);
}

/* ---------- 跑规则（单单元作用域） ---------- */
function runRulesFor(files, activeUnit) {
  const rules = [];
  const summary = { errors: 0, warnings: 0, passed: 0, failed: 0, missing: 0 };
  // Q109：缺件数（三件套的第三项）—— 真源＝rules.json → unit_required_deliverables
  // ⚠ 判据实现只有一处（在 rules.mjs 的 missingRequiredDeliverables），此处只做**计数与展示**，
  //   不得在此另写一份清单（Q110②）。
  {
    const req = rulesCfg?.unit_required_deliverables?.deliverables;
    if (Array.isArray(req)) {
      summary.missing = req.filter((d) => !files[d]).length;
    }
  }
  for (const rule of RULES) {
    const ctx = {
      project,
      projectDir: PROJECT,
      unitDir: activeUnit ? path.join(PROJECT, 'units', activeUnit) : null,
      unit: activeUnit,
      files,
      schemas,
      rules: rulesCfg,
    };
    let res;
    try {
      res = rule.run(ctx);
    } catch (e) {
      res = { errors: [`规则执行异常：${e.message}`], warnings: [] };
    }
    rules.push({
      id: rule.id,
      name: rule.name,
      scope: rule.scope,
      errors: res.errors,
      warnings: res.warnings,
      status: res.errors.length ? 'FAIL' : 'PASS',
    });
    summary.errors += res.errors.length;
    summary.warnings += res.warnings.length;
    if (res.errors.length) summary.failed += 1;
    else summary.passed += 1;
  }
  return { rules, summary };
}

const unitReports = [];
for (const uid of runUnits) {
  const { files } = collectFiles(uid);
  const scoped = {};
  for (const k of Object.keys(files)) {
    if (onlyDoc && onlyDoc !== true && k !== onlyDoc) continue;
    scoped[k] = files[k];
  }
  if (!Object.keys(scoped).length) {
    unitReports.push({
      unit: uid,
      report: {
        project: path.basename(PROJECT),
        unit: uid,
        checked_at: new Date().toISOString(),
        docs: [],
        rules: [],
        summary: { errors: 0, warnings: 0, passed: 0, failed: 0, missing: 0 },
      },
      empty: true,
    });
    continue;
  }
  const { rules, summary } = runRulesFor(scoped, uid);
  // Q109 补记：单元内实交份数（与 shared 层分开统计）——「交付物 N 份」含 shared，
  //   不能当作单元齐全度（collectFiles 无条件并入 shared 全部 JSON）。
  const unitDocsCount = (() => {
    const ud = path.join(PROJECT, 'units', uid);
    if (!fs.existsSync(ud)) return 0;
    return fs.readdirSync(ud).filter((f) => f.endsWith('.json')).length;
  })();
  unitReports.push({
    unit: uid,
    report: {
      project: path.basename(PROJECT),
      unit: uid,
      checked_at: new Date().toISOString(),
      docs: Object.keys(scoped).sort(),
      unitDocsCount,
      rules,
      summary,
    },
    empty: false,
  });
}

if (unitReports.every((u) => u.empty)) {
  console.error('未找到任何交付物 JSON。目录结构应为：');
  console.error('  <项目>/project.json');
  console.error('  <项目>/shared/D01.json …');
  console.error('  <项目>/units/U01/D06.json …');
  process.exit(2);
}

/* ---------- 汇总报告 ---------- */
const isMulti = unitReports.length > 1;
const report = isMulti
  ? {
      project: path.basename(PROJECT),
      unit: unitReports.map((u) => u.unit),
      checked_at: new Date().toISOString(),
      docs: [...new Set(unitReports.flatMap((u) => u.report.docs))].sort(),
      units: unitReports.map((u) => ({
        unit: u.unit,
        docs: u.report.docs.length,
        summary: u.report.summary,
      })),
      rules: unitReports.flatMap((u) => u.report.rules.map((r) => ({ unit: u.unit, ...r }))),
      summary: unitReports.reduce(
        (acc, u) => ({
          errors: acc.errors + u.report.summary.errors,
          warnings: acc.warnings + u.report.summary.warnings,
          passed: acc.passed + u.report.summary.passed,
          failed: acc.failed + u.report.summary.failed,
          missing: acc.missing + (u.report.summary.missing || 0),
        }),
        { errors: 0, warnings: 0, passed: 0, failed: 0, missing: 0 },
      ),
    }
  : unitReports[0].report;

/* ---------- 输出 ---------- */
const C = { g: '\x1b[32m', r: '\x1b[31m', y: '\x1b[33m', d: '\x1b[2m', b: '\x1b[1m', x: '\x1b[0m' };
function printUnitReport(u) {
  const r = u.report;
  // ⚠ 「交付物 N 份」是 **shared 层 + 单元内** 的合计（collectFiles 会无条件并入 shared 全部 JSON），
  //   **不等于该单元有 N 份**。Q109 补记：单元内实交份数单列，避免这个数字被误读为「单元齐全度」。
  const unitDocs = u.report.docs?.length ?? 0;
  const sharedCount = unitDocs - (u.report.unitDocsCount ?? unitDocs);
  console.log(`${C.b}${C.d}■ 校验报告${C.x} ${r.project} ${JSON.stringify(r.unit)}  交付物 ${r.docs.length} 份` +
    `（含 shared ${Math.max(0, sharedCount)} 份 ＋ 本单元 ${u.report.unitDocsCount ?? '?'} 份）`);
  for (const rule of r.rules) {
    const mark = rule.status === 'PASS' ? `${C.g}PASS${C.x}` : `${C.r}FAIL${C.x}`;
    console.log(`  ${mark}  ${rule.id} ${rule.name}  ${C.d}(${rule.scope})${C.x}`);
    for (const e of rule.errors) console.log(`        ${C.r}✗${C.x} ${e}`);
    for (const w of rule.warnings) console.log(`        ${C.y}!${C.x} ${w}`);
  }
  const s = r.summary;
  // Q109②③：结果行强制输出三件套（规则数／error 数／缺件数）；
  // 缺件单元**不得显示「N/N 通过」**，须显示「N/M（缺 K 件）」—— 避免「跳过式全绿」被读成真绿。
  const ruleTxt = s.missing > 0
    ? `${s.passed}/${s.passed + s.failed}（缺 ${s.missing} 件）`
    : `${s.passed}/${s.passed + s.failed}`;
  console.log(
    `${C.b}■ 结果${C.x}  通过 ${ruleTxt} 规则  ` +
    `${s.errors ? C.r : C.g}error ${s.errors}${C.x}  ${s.warnings ? C.y : C.d}warning ${s.warnings}${C.x}  ` +
    `${s.missing ? C.r : C.d}缺件 ${s.missing}${C.x}`,
  );
}

if (asJson) {
  console.log(JSON.stringify(report, null, 2));
} else {
  if (isMulti) {
    console.log(`${C.b}${C.d}■ 全项目校验（逐单元独立校验，不跨单元合并）${C.x}  单元 ${JSON.stringify(report.unit)}`);
    for (const u of unitReports) {
      console.log('');
      printUnitReport(u);
    }
    const s = report.summary;
    console.log('');
    console.log(
      `${C.b}■ 合计${C.x}  单元 ${report.units.length} 个  规则 ${s.passed}/${s.passed + s.failed} 通过  ` +
      `${s.errors ? C.r : C.g}error ${s.errors}${C.x}  ${s.warnings ? C.y : C.d}warning ${s.warnings}${C.x}`,
    );
  } else {
    printUnitReport(unitReports[0]);
  }
}

// 写入报告文件
const reportDir = path.join(PROJECT, 'reports');
fs.mkdirSync(reportDir, { recursive: true });
if (isMulti) {
  // 逐单元报告（与 `--unit <UNIT>` 同名同格式，便于各岗按单元引用）
  for (const u of unitReports) {
    fs.writeFileSync(
      path.join(reportDir, `validate-${u.unit}.json`),
      JSON.stringify(u.report, null, 2),
      'utf8',
    );
  }
  // 聚合报告
  fs.writeFileSync(
    path.join(reportDir, 'validate.json'),
    JSON.stringify(report, null, 2),
    'utf8',
  );
} else {
  fs.writeFileSync(
    path.join(reportDir, `validate-${unitReports[0].unit}.json`),
    JSON.stringify(report, null, 2),
    'utf8',
  );
}

process.exit(report.summary.errors > 0 ? 1 : 0);
