#!/usr/bin/env node
/**
 * selfcheck_D14.mjs —— D14 逐镜交接包**独立**自检
 *
 * 为什么独立于 validate.mjs：
 *   V11 只保证「镜号被覆盖、逐镜包存在且能过 schema、两边 deepDiff 零差异」；
 *   它**不**复核 D11 现盘逐镜四项是否逐字一致，也**不**复核字段集版本号与
 *   h3_prompt 实际字数。本脚本从 D11/D14 现盘重算一遍，用于交付前自查与留痕。
 *
 * 用法：
 *   node scripts/selfcheck_D14.mjs
 *
 * 退出码：0 = 全绿；1 = 有 error
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validate } from '../../../04_工具/lib/schema-engine.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');                     // 02_项目/双相潮主
const FACTORY = path.resolve(ROOT, '../..');                     // 短剧文档工厂
const UNIT = 'U01';
const PROMPT_BUDGET = 6500;

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const errors = [];
const notes = [];
const fail = (m) => errors.push(m);

/* ---------- 1. 读现盘 ---------- */
const d11 = readJson(path.join(ROOT, `units/${UNIT}/D11.json`));
const d14 = readJson(path.join(ROOT, `units/${UNIT}/D14.json`));
const schemas = readJson(path.join(FACTORY, '03_规格/schema.json'));
const pkgSchema = schemas.definitions.D14ShotPackage;

/** D11 现盘权威镜表：(ep, shot_id) → {gsn, scene_code, duration_sec} */
const d11Map = new Map();
for (const ep of d11.episodes) {
  for (const s of ep.shots) {
    d11Map.set(`${ep.ep}/${s.shot_id}`, {
      gsn: s.global_shot_no, scene_code: s.scene_code, duration_sec: s.duration_sec,
    });
  }
}

/* ---------- 2. 镜号覆盖：恰好覆盖，不多不少不缺 ---------- */
const d14Keys = new Set();
for (const sh of d14.shots) d14Keys.add(`${sh.ep}/${sh.shot_id}`);
if (d14Keys.size !== d14.shots.length) fail(`D14.shots 存在重复 (ep,shot_id)：${d14.shots.length} 条但去重后 ${d14Keys.size} 条`);
const missing = [...d11Map.keys()].filter((k) => !d14Keys.has(k));
const extra = [...d14Keys].filter((k) => !d11Map.has(k));
if (missing.length) fail(`D14 缺失 D11 镜位：${missing.join(', ')}`);
if (extra.length) fail(`D14 多出 D11 没有的镜位：${extra.join(', ')}`);
notes.push(`镜号覆盖：D11 ${d11Map.size} 镜 ↔ D14 ${d14Keys.size} 镜，缺 ${missing.length} / 多 ${extra.length}`);

/* ---------- 3. 顶层形状 ---------- */
const TOP_REQUIRED = ['doc_id', 'unit', 'version', 'status', 'shots', 'commands', 'check_results'];
for (const k of TOP_REQUIRED) if (!(k in d14)) fail(`D14 顶层缺字段 "${k}"`);
if (!Array.isArray(d14.commands) || d14.commands.some((c) => typeof c !== 'string')) {
  fail('D14.commands 必须是**字符串数组**');
}
if (!Array.isArray(d14.check_results)) fail('D14.check_results 必须是数组');
else {
  const bad = d14.check_results.filter((r) => typeof r !== 'object' || r === null || Array.isArray(r));
  if (bad.length) fail(`D14.check_results 含 ${bad.length} 个非对象元素`);
  const noShape = d14.check_results.filter((r) => !('check' in r) || !('result' in r) || !('note' in r));
  if (noShape.length) fail(`D14.check_results 有 ${noShape.length} 条缺 {check,result,note} 三键`);
  notes.push(`check_results：${d14.check_results.length} 条，全部为对象且含 {check,result,note}`);
}

/* ---------- 4. 逐镜：四项逐字一致 + 版本号 + 包存在 + schema + deepDiff + 字数 ---------- */
function deepDiff(a, b, p = '', out = []) {
  if (out.length > 50) return out;
  const ta = a === null ? 'null' : Array.isArray(a) ? 'array' : typeof a;
  const tb = b === null ? 'null' : Array.isArray(b) ? 'array' : typeof b;
  if (ta !== tb) { out.push(`${p}: 类型 ${ta} ≠ ${tb}`); return out; }
  if (ta === 'object') {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    for (const k of ka) if (!(k in b)) out.push(`${p}.${k}: D14 内联有 / 落盘包无`);
    for (const k of kb) if (!(k in a)) out.push(`${p}.${k}: 落盘包有 / D14 内联无`);
    for (const k of ka) if (k in b) deepDiff(a[k], b[k], `${p}.${k}`, out);
  } else if (ta === 'array') {
    if (a.length !== b.length) out.push(`${p}: 数组长度 ${a.length} ≠ ${b.length}`);
    for (let i = 0; i < Math.min(a.length, b.length); i++) deepDiff(a[i], b[i], `${p}[${i}]`, out);
  } else if (a !== b) {
    out.push(`${p}: ${JSON.stringify(a)} ≠ ${JSON.stringify(b)}`);
  }
  return out;
}

const ARTIFACTS = [
  'package.json', 'h3_prompt.txt', 'h3_prompt_budget.json', 'preflight.json',
  'render_contract.json', 'appearance.json', 'manifest.json', 'preview_video.mp4',
  'shot_spec.json', 'scene_spec.json', 'projection.json',
];

let charsMin = Infinity, charsMax = -Infinity;
const rows = [];

for (const sh of d14.shots) {
  const key = `${sh.ep}/${sh.shot_id}`;
  const name = `ep${String(sh.ep).padStart(2, '0')}_shot${String(sh.shot_id).padStart(2, '0')}`;
  const ref = d11Map.get(key);
  if (!ref) continue;

  // 4.1 逐镜四项与 D11 逐字一致
  for (const [k, v] of [['global_shot_no', ref.gsn], ['scene_code', ref.scene_code], ['duration_sec', ref.duration_sec]]) {
    if (sh[k] !== v) fail(`${name}: ${k} = ${JSON.stringify(sh[k])} ≠ D11 ${JSON.stringify(v)}`);
  }

  // 4.2 字段集版本号
  const cv = sh.render_contract?.schema_version, av = sh.appearance?.schema_version;
  if (cv !== 4) fail(`${name}: render_contract.schema_version = ${cv}（应为 4）`);
  if (av !== 6) fail(`${name}: appearance.schema_version = ${av}（应为 6）`);
  if (sh.render_contract?.watched_full_source !== true) fail(`${name}: render_contract.watched_full_source 非 true`);

  // 4.3 逐镜包文件真实存在 + 过 D14ShotPackage schema
  const pkgPath = path.join(ROOT, `units/${UNIT}`, sh.package_path);
  if (!fs.existsSync(pkgPath)) { fail(`${name}: package_path 不存在 → ${sh.package_path}`); continue; }
  const pkg = readJson(pkgPath);
  const r = validate(pkg, pkgSchema, schemas);
  if (!r.ok) fail(`${name}: package.json 未过 D14ShotPackage 校验 → ${r.errors.slice(0, 3).join(' | ')}`);

  // 4.4 D14 内联项与落盘包 deepDiff 零差异
  const diffs = deepDiff(sh, pkg, name);
  if (diffs.length) fail(`${name}: D14 内联项与落盘 package.json 有 ${diffs.length} 处差异 → ${diffs.slice(0, 3).join(' | ')}`);

  // 4.5 h3_prompt：文件存在 + 实测字数 == char_count ≤ 6500 + 三布尔为真
  const hp = sh.h3_prompt;
  const promptFile = path.join(ROOT, `units/${UNIT}`, hp.path);
  if (!fs.existsSync(promptFile)) fail(`${name}: h3_prompt.path 不存在 → ${hp.path}`);
  else {
    const len = fs.readFileSync(promptFile, 'utf8').length;
    if (len !== hp.char_count) fail(`${name}: h3_prompt 实测 ${len} 字 ≠ char_count ${hp.char_count}`);
    if (len > PROMPT_BUDGET) fail(`${name}: h3_prompt ${len} 字 > 预算 ${PROMPT_BUDGET}`);
    charsMin = Math.min(charsMin, len); charsMax = Math.max(charsMax, len);
  }
  for (const b of ['within_budget', 'protected_content_valid', 'ready_to_submit']) {
    if (hp[b] !== true) fail(`${name}: h3_prompt.${b} 非 true`);
  }

  // 4.6 配套产物齐全（含 preview_video 实跑证据非空）
  const dir = path.dirname(pkgPath);
  for (const f of ARTIFACTS) {
    const fp = path.join(dir, f);
    if (!fs.existsSync(fp)) fail(`${name}: 缺产物 ${f}`);
    else if (fs.statSync(fp).size === 0) fail(`${name}: 产物 ${f} 为空文件`);
  }

  rows.push({
    name, gsn: sh.global_shot_no, ep: sh.ep, shot_id: sh.shot_id,
    scene_code: sh.scene_code, duration_sec: sh.duration_sec,
    chars: hp.char_count, contract: cv, appearance: av,
    inv: sh.render_contract.source_inventory.length,
    ent: sh.render_contract.entities.length,
    anchors: sh.render_contract.anchors.length,
  });
}

/* ---------- 5. 输出 ---------- */
const W = 108;
console.log(`${'='.repeat(W)}`);
console.log('D14 逐镜交接包 · 独立自检');
console.log(`${'='.repeat(W)}`);
console.log(`D11 现盘：${d11.version} ${d11.status}｜${d11Map.size} 镜`);
console.log(`D14 现盘：${d14.version} ${d14.status}｜shots ${d14.shots.length}｜check_results ${d14.check_results.length}`);
console.log('-'.repeat(W));
console.log(
  '镜位'.padEnd(13) + 'gsn'.padEnd(5) + 'scene'.padEnd(8) + 'dur'.padEnd(5) +
  'chars'.padEnd(8) + 'ctr'.padEnd(5) + 'app'.padEnd(5) + 'inv'.padEnd(5) + 'ent'.padEnd(5) + 'anchors',
);
for (const r of rows) {
  console.log(
    r.name.padEnd(13) + String(r.gsn).padEnd(5) + r.scene_code.padEnd(8) +
    String(r.duration_sec).padEnd(5) + String(r.chars).padEnd(8) +
    String(r.contract).padEnd(5) + String(r.appearance).padEnd(5) +
    String(r.inv).padEnd(5) + String(r.ent).padEnd(5) + String(r.anchors),
  );
}
console.log('-'.repeat(W));
for (const n of notes) console.log(`· ${n}`);
if (rows.length) console.log(`· h3_prompt 字数区间：${charsMin} – ${charsMax}（预算 ${PROMPT_BUDGET}）`);
console.log(`· 每镜配套产物 ${ARTIFACTS.length} 类（含 preview_video.mp4 实跑证据），共 ${ARTIFACTS.length} × ${rows.length} 项`);
console.log('-'.repeat(W));
if (errors.length) {
  console.log(`■ 结果　error ${errors.length}`);
  for (const e of errors) console.log(`   ✗ ${e}`);
  process.exit(1);
}
console.log(`■ 结果　全部通过（0 error）｜${rows.length} 镜逐项核对`);
process.exit(0);
