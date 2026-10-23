#!/usr/bin/env node
/**
 * V12「白模构图一致性」负测
 *
 * 纪律（章程 v2.5）：判据改宽改严必先补负测证明**非恒真**。
 * 本文件为 `04_工具/lib/rules.mjs` 的 V12 提供 9 条腿：
 *   ① 基线合格夹具必须 0 error
 *   ② 每一类真违规必须**报得出**
 *   ③ 每一条反证腿必须**报不出**（证明判据不是瞎报）
 *
 * 用法：
 *   node 04_工具/test_white_model_framing.mjs
 *   node 04_工具/test_white_model_framing.mjs --project 02_项目/双相潮主   # 顺带跑真盘
 *
 * 退出码：0 = 全过；1 = 有腿失败
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { RULES } from './lib/rules.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FACTORY_ROOT = path.resolve(__dirname, '..');
const RULES_JSON = JSON.parse(fs.readFileSync(path.join(FACTORY_ROOT, '03_规格', 'rules.json'), 'utf8'));
const V12 = RULES.find((r) => r.id === 'V12');
if (!V12) {
  console.error('未找到 V12 规则');
  process.exit(2);
}

/* ---------- 夹具构造 ---------- */

function shot(shot_id, shot_size, visual_facts = '角色在画面中') {
  return {
    shot_id,
    global_shot_no: shot_id,
    scene_code: 'X-1',
    shot_size,
    camera_angle: '平视',
    lens_mm: 35,
    movement: 'static',
    duration_sec: 11,
    visual_facts,
    dialogue: '',
    sfx: '',
    needs_image: false,
    minor_present: false,
    quad_segment: 1,
    note: '',
  };
}

function makeD11(shots) {
  return {
    doc_id: 'D11',
    unit: 'T01',
    version: '1.0',
    status: 'draft',
    episodes: [
      {
        ep: 1,
        duration_sec: 45,
        duration_sum_sec: 45,
        shots,
        continuity: [],
      },
    ],
  };
}

function obj(kind, name, height, extra = {}) {
  return {
    in_frame: true,
    visible_percent: { center_x: 50, center_y: 50, width: height, height },
    depth_m: 2,
    world_dimensions: [1, 1, 1],
    ...extra,
  };
}

function proj(ep, shot_id, frameObjects) {
  return {
    shot_dir: `ep${ep}_shot${shot_id}`,
    ep,
    shot_id,
    scene_code: 'X-1',
    fps: 24,
    frame_start: 1,
    frame_end: frameObjects.length,
    resolution_px: [1080, 1920],
    aspect: '9:16',
    camera: {},
    frames: frameObjects.map((objects, i) => ({
      time_seconds: i,
      frame: i + 1,
      camera: {},
      objects,
    })),
  };
}

/**
 * 建临时工程：units/T01/D11.json + units/T01/D14_shots/<dir>/projection.json
 * shots: [{ dir, ep, shot_id, frameObjects }]
 */
function buildFixture(shots, d11Shots) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'wm-fixture-'));
  const unitDir = path.join(root, 'units', 'T01');
  fs.mkdirSync(path.join(unitDir, 'D14_shots'), { recursive: true });
  fs.writeFileSync(path.join(unitDir, 'D11.json'), JSON.stringify(makeD11(d11Shots), null, 2));
  for (const s of shots) {
    const dir = path.join(unitDir, 'D14_shots', s.dir);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'projection.json'), JSON.stringify(proj(s.ep, s.shot_id, s.frameObjects), null, 2));
  }
  return { root, unitDir };
}

function runV12(unitDir, d11) {
  const ctx = {
    project: {},
    projectDir: path.dirname(path.dirname(unitDir)),
    unitDir,
    unit: 'T01',
    files: { D11: d11 },
    schemas: {},
    rules: RULES_JSON,
  };
  return V12.run(ctx);
}

/* ---------- 断言 ---------- */
let pass = 0;
let fail = 0;
const failures = [];

function expect(legName, cond, detail) {
  if (cond) {
    pass++;
    console.log(`  \x1b[32m✓\x1b[0m ${legName}`);
  } else {
    fail++;
    failures.push(`${legName} —— ${detail}`);
    console.log(`  \x1b[31m✗\x1b[0m ${legName}  \x1b[2m${detail}\x1b[0m`);
  }
}

/* ---------- 腿 ---------- */

console.log('\n\x1b[1m■ V12 白模构图一致性 · 负测\x1b[0m');

// L0 基线：合格夹具必须 0 error
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50), 'X-1_EXT_Room': obj('EXT', 'X-1_EXT_Room', 40) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L0 基线：主体占幅 50%（中景 [35,65]）且为画面最大对象 → 0 error',
    r.errors.length === 0, `实际 ${r.errors.length} 条：${r.errors.join(' | ')}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L1 W1：角色完全不在画幅 → 必报
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_EXT_Room': obj('EXT', 'X-1_EXT_Room', 100) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L1 W1 角色完全不在画幅 → 必报',
    r.errors.some((e) => e.includes('W1')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L2 W2：占幅越界 → 必报
{
  const d11Shots = [shot(1, '特写')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 30) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L2 W2 特写却只有 30% 占幅 → 必报',
    r.errors.some((e) => e.includes('W2')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L3 W3：画面最大对象是环境 → 必报
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 40), 'X-1_EXT_Wall': obj('EXT', 'X-1_EXT_Wall', 90) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L3 W3 环境外壳占 90% 压过角色 → 必报',
    r.errors.some((e) => e.includes('W3')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L4 空镜豁免：D11 明写空镜 → 不报
{
  const d11Shots = [shot(1, '远景', '空镜，街巷无人')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_EXT_Street': obj('EXT', 'X-1_EXT_Street', 100) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L4 反证：D11 明写空镜 → 不报 W1/W2/W3',
    r.errors.length === 0, `实际 ${r.errors.length} 条：${r.errors.join(' | ')}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L5 W4：姿态翻滚 → 必报
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50, { rotation_euler_deg: [0, -90, 0] }) },
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50, { rotation_euler_deg: [0, 0, 0] }) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L5 W4 相邻帧旋转跳变 90° → 必报',
    r.errors.some((e) => e.includes('W4')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L6 W5：非法姿态词 → 必报
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50, { pose: 'flying' }) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L6 W5 姿态「flying」不在词表 → 必报',
    r.errors.some((e) => e.includes('W5')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L7 反证：未知景别值 → 只 warning，不报 error
{
  const d11Shots = [shot(1, '微距')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L7 反证：未知景别「微距」→ 不报 error（只提示未覆盖）',
    !r.errors.some((e) => e.includes('W2')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L8 反证：主体在画幅内、占幅合法，但环境件更大 → 只报 W3，不误报 W1/W2
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 45), 'X-1_EXT_Room': obj('EXT', 'X-1_EXT_Room', 60) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  expect('L8 反证：只报 W3，不误报 W1/W2',
    r.errors.length === 1 && r.errors[0].includes('W3') && !r.errors[0].includes('W1') && !r.errors[0].includes('W2'),
    `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

// L9 反证：多帧里主体占幅取**全局最大**（后一帧更小不得把前帧覆盖掉）
{
  const d11Shots = [shot(1, '中景')];
  const fx = buildFixture(
    [{ dir: 'ep01_shot01', ep: 1, shot_id: 1, frameObjects: [
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 50), 'X-1_EXT_Room': obj('EXT', 'X-1_EXT_Room', 30) },
      { 'X-1_CHAR_Hero_01': obj('CHAR', 'X-1_CHAR_Hero_01', 10), 'X-1_EXT_Room': obj('EXT', 'X-1_EXT_Room', 95) },
    ] }],
    d11Shots,
  );
  const r = runV12(fx.unitDir, makeD11(d11Shots));
  // 主体全局最大 50%（合法中景）；但第 2 帧环境件占 95% ⇒ 仍应报 W3
  expect('L9 反证：主体占幅取全局 max（50% 非 10%），不因后一帧变小而误判越界',
    !r.errors.some((e) => e.includes('W2')), `实际错误：${r.errors.join(' | ') || '（无）'}`);
  fs.rmSync(fx.root, { recursive: true, force: true });
}

console.log(`\n\x1b[1m■ 结果\x1b[0m  通过 ${pass}/${pass + fail}` + (fail ? `  \x1b[31m失败 ${fail}\x1b[0m` : '  \x1b[32m全过\x1b[0m'));
if (fail) {
  console.log('\n失败明细：');
  for (const f of failures) console.log(`  · ${f}`);
  process.exit(1);
}
process.exit(0);
