/**
 * V1–V13 硬校验规则集
 * 每条规则导出 { id, name, scope, run(ctx) -> {errors:[], warnings:[]} }
 *
 * ctx = {
 *   project,        // project.json 全量
 *   projectDir,     // 项目目录绝对路径（V11 解析逐镜交接包文件用）
 *   unitDir,        // 当前单元目录绝对路径（units/<UNIT>）
 *   unit,           // 当前单元 id（如 U01）
 *   files,          // { D01: obj, D06: obj, ... } 当前上下文可见的全部交付物 JSON
 *   schemas,        // schema.json 全量
 *   rules,          // rules.json 配置（阈值、词表等）
 * }
 */

import fs from 'node:fs';
import path from 'node:path';
import { validate } from './schema-engine.mjs';

const ok = (errors = [], warnings = []) => ({ errors, warnings });

/* ---------- 单元必交交付物：缺件判定（Q109 · 唯一实现点） ----------
 *
 * 背景：Chief 12:01 裁决书 Q109 —— 「缺件 → 仍计 PASS」是代码根因。
 * 旧行为里缺件只进 warnings，规则行仍显示 PASS，于是「12/12 通过 error 0」
 * 是**跳过式全绿**（假绿），风险面一次都没被真正检查过。
 *
 * ⚠ Q110②「同一规则只许有一处实现」—— 本函数是**唯一实现点**，
 *   V1 与 V11 两处缺件判定都必须调用它，禁止各写一份。
 *   清单真源＝03_规格/rules.json → unit_required_deliverables.deliverables
 *   （真源再往上＝《团队章程》§三·五 第 1 条「单元内 10 份交付物 JSON 齐全」）。
 */
function missingRequiredDeliverables(ctx) {
  const cfg = ctx.rules?.unit_required_deliverables;
  if (!cfg || !Array.isArray(cfg.deliverables)) return { missing: [], isError: false };
  const missing = cfg.deliverables.filter((d) => !ctx.files[d]);
  return { missing, isError: cfg.missing_is_error !== false };
}

/** 把缺件渲染成规则行里的条目：error 或 warning。 */
function missingDeliverableLines(ctx) {
  const { missing, isError } = missingRequiredDeliverables(ctx);
  const lines = missing.map((d) => `${d}: 本次上下文中不存在，单元必交交付物缺件`);
  return { missing, isError, lines };
}

/* ---------- 工具 ---------- */

function epOf(d) { return d.ep; }
function byEp(list) {
  const m = new Map();
  for (const e of list || []) m.set(e.ep, e);
  return m;
}
function textOfBody(body = []) {
  return body.map((b) => `${b.text || ''}${b.sfx || ''}`).join('\n');
}
function allText(node, acc = []) {
  if (node === null || node === undefined) return acc;
  if (typeof node === 'string') { acc.push(node); return acc; }
  if (Array.isArray(node)) { node.forEach((n) => allText(n, acc)); return acc; }
  if (typeof node === 'object') { Object.values(node).forEach((v) => allText(v, acc)); return acc; }
  return acc;
}
/**
 * 按「文档顶层字段名」排除后取全文文本。
 * 用途：合规清单（D03）与质检闸门（D18）的职责就是逐词声明作废写法，
 * 全文扫描时必须跳过这些字段，否则合规清单本身永远过不了检。
 * skipKeys 只在顶层生效（depth=0），深层同名键不豁免。
 */
function allTextExceptTop(node, skipKeys = [], acc = [], depth = 0) {
  if (node === null || node === undefined) return acc;
  if (typeof node === 'string') { acc.push(node); return acc; }
  if (Array.isArray(node)) { node.forEach((n) => allTextExceptTop(n, skipKeys, acc, depth + 1)); return acc; }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (depth === 0 && skipKeys.includes(k)) continue;
      allTextExceptTop(v, skipKeys, acc, depth + 1);
    }
    return acc;
  }
  return acc;
}

/**
 * 路径级豁免：在指定路径处跳过整棵子树，其余部分照常扫描。
 * 支持两种写法：
 *   1) 顶层键名（与 allTextExceptTop 同义）："negatives"
 *   2) 精确路径："cards[].negatives" —— 匹配 cards 数组下任意元素的 negatives 字段
 * 路径中 [] 表示"数组下任意一层"，用 . 分隔层级。
 */
function allTextExceptPaths(node, skipPaths = [], acc = [], path = []) {
  if (node === null || node === undefined) return acc;
  if (typeof node === 'string') { acc.push(node); return acc; }
  if (Array.isArray(node)) {
    node.forEach((n, i) => allTextExceptPaths(n, skipPaths, acc, [...path, `[]`]));
    return acc;
  }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      const childPath = [...path, k];
      if (matchesSkipPath(childPath, skipPaths)) continue;
      allTextExceptPaths(v, skipPaths, acc, childPath);
    }
    return acc;
  }
  return acc;
}

function matchesSkipPath(path, skipPaths) {
  if (!skipPaths || !skipPaths.length) return false;
  // 把路径归一化为 "a[].b" 形式
  const normalized = path
    .reduce((acc, seg) => {
      if (seg === '[]') {
        // 数组标记直接贴在前一个键后面：cards + [] -> cards[]
        return acc.length ? [...acc.slice(0, -1), `${acc[acc.length - 1]}[]`] : ['[]'];
      }
      return [...acc, seg];
    }, [])
    .join('.');
  for (const raw of skipPaths) {
    if (typeof raw !== 'string') continue;
    const p = raw.trim();
    if (!p) continue;
    if (p === normalized) return true;
    // 豁免路径指向的是数组节点时，其下元素（…[]）一并豁免
    if (normalized === `${p}[]`) return true;
    // 豁免路径指向数组元素层（…[]）时，数组节点本身也视为豁免
    if (p.endsWith('[]') && normalized === p.slice(0, -2)) return true;
    // 顶层键名写法（无点号）视为匹配该键任意深度
    if (!p.includes('.') && !p.includes('[') && path[path.length - 1] === p) return true;
  }
  return false;
}
function countWords(s) {
  // 中文按字计，英文/数字按词计
  const cjk = (s.match(/[一-鿿]/g) || []).length;
  const words = (s.match(/[A-Za-z0-9]+/g) || []).length;
  return cjk + words;
}

/* ---------- V1 字段/枚举 ---------- */

const V1 = {
  id: 'V1',
  name: '字段完整性与枚举合法性',
  scope: 'all',
  run(ctx) {
    const errors = [];
    const warnings = [];
    // Q109：单元必交交付物缺件 → 计 error（不再只 warning），避免「跳过式全绿」。
    // ⚠ 判据实现只有一处：missingRequiredDeliverables()（见文件头），此处不得另写一份。
    {
      const { missing, isError, lines } = missingDeliverableLines(ctx);
      if (missing.length) {
        if (isError) errors.push(...lines);
        else warnings.push(...lines.map((l) => `${l}（跳过）`));
      }
    }
    for (const [docId, schema] of Object.entries(ctx.schemas)) {
      // ⚠️ 只遍历交付物 schema（`D01`–`D18`）—— `ctx.schemas` 是整份 schema.json，
      //    其中 `title`／`$schema`／`$id`／`definitions` 等是 **JSON Schema 元数据**，
      //    不是交付物 doc id。此前只跳过 `$` 前缀与 `definitions`，
      //    导致 `title` 被当成缺失交付物 → **每次跑固定产出 1 条误报**（全项目 3 条），
      //    且该噪声会淹没真实 warning。企划合规 2026-10-23 07:35 修正（OPS-17）。
      if (!/^D\d{2}$/.test(docId)) continue;
      const data = ctx.files[docId];
      if (!data) {
        warnings.push(`${docId}: 本次上下文中不存在，跳过（若该交付物本次应产出则属遗漏）`);
        continue;
      }
      const r = validate(data, schema, ctx.schemas);
      for (const e of r.errors) errors.push(`${docId} ${e}`);
    }
    return ok(errors, warnings);
  },
};

/* ---------- V2 跨文件引用完整性 ---------- */

const V2 = {
  id: 'V2',
  name: '跨文件引用完整性',
  scope: 'all',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const { D04, D05, D06, D07, D08, D11, D12, D13, D15 } = ctx.files;

    const charIds = new Set((D04?.characters || []).map((c) => c.id));
    const minorIds = new Set((D04?.characters || []).filter((c) => c.minor).map((c) => c.id));
    const locations = new Set((D05?.locations || []).map((l) => l.name));

    // D06 角色引用
    for (const ep of D06?.episodes || []) {
      for (const cid of ep.characters || []) {
        if (!charIds.has(cid)) errors.push(`D06 ep${ep.ep}: 角色 "${cid}" 在 D04 中不存在`);
      }
      for (const loc of ep.locations || []) {
        if (locations.size && !locations.has(loc)) {
          warnings.push(`D06 ep${ep.ep}: 地点 "${loc}" 不在 D05 地点表中`);
        }
      }
    }
    // D07 在场角色 + 承接回答闭合
    const d06map = byEp(D06?.episodes);
    for (const ep of D07?.episodes || []) {
      for (const pc of ep.present_characters || []) {
        if (!charIds.has(pc.char_id)) {
          errors.push(`D07 ep${ep.ep}: 在场角色 "${pc.char_id}" 在 D04 中不存在`);
          continue;
        }
        // minor 标记必须与 D04 一致
        if (minorIds.has(pc.char_id) && pc.minor !== true) {
          errors.push(`D07 ep${ep.ep}: 角色 ${pc.char_id} 在 D04 标为未成年，present_characters.minor 必须为 true`);
        }
        if (!minorIds.has(pc.char_id) && pc.minor === true) {
          errors.push(`D07 ep${ep.ep}: 角色 ${pc.char_id} 在 D04 非未成年，present_characters.minor 不应为 true`);
        }
      }
      const prev = d06map.get(ep.ep - 1);
      if (prev && !String(ep.carry_over || '').trim()) {
        errors.push(`D07 ep${ep.ep}: 承接项为空（上一集 ep${prev.ep} 存在钩子）`);
      }
      if (!String(ep.answer || '').trim()) {
        errors.push(`D07 ep${ep.ep}: 回答项为空`);
      }
      if (!String(ep.cost || '').trim()) {
        errors.push(`D07 ep${ep.ep}: 「代价」为空（每集必填）`);
      }
    }
    // D08 角色引用 + 字数
    const d07map = byEp(D07?.episodes);
    for (const ep of D08?.episodes || []) {
      for (const cid of ep.present_characters || []) {
        if (!charIds.has(cid)) errors.push(`D08 ep${ep.ep}: 角色 "${cid}" 在 D04 中不存在`);
      }
      const d07 = d07map.get(ep.ep);
      if (d07) {
        const d07Set = new Set((d07.present_characters || []).map((p) => p.char_id));
        for (const cid of ep.present_characters || []) {
          if (!d07Set.has(cid)) {
            errors.push(`D08 ep${ep.ep}: 角色 "${cid}" 不在 D07 ep${ep.ep} 的在场名单里`);
          }
        }
      }
    }
    // D11 场景码引用 D13
    const sceneCodes = new Set((D13?.scenes || []).map((s) => s.scene_code));
    for (const ep of D11?.episodes || []) {
      for (const s of ep.shots || []) {
        if (sceneCodes.size && !sceneCodes.has(s.scene_code)) {
          errors.push(`D11 ep${ep.ep} 镜${s.shot_id}: 场景码 "${s.scene_code}" 不在 D13 场景表中`);
        }
      }
    }
    // D12 引用 D11 镜号
    const shotKeys = new Set();
    for (const ep of D11?.episodes || []) for (const s of ep.shots || []) shotKeys.add(`${ep.ep}#${s.shot_id}`);
    for (const c of D12?.cards || []) {
      if (shotKeys.size && !shotKeys.has(`${c.ep}#${c.shot_id}`)) {
        errors.push(`D12 卡片 ${c.card_id}: 引用 ep${c.ep} 镜${c.shot_id}，D11 中不存在`);
      }
      for (const cid of c.consistency_refs?.char_ids || []) {
        if (!charIds.has(cid)) errors.push(`D12 卡片 ${c.card_id}: 角色 "${cid}" 在 D04 中不存在`);
      }
    }
    // D15 引用
    for (const ep of D15?.episodes || []) {
      for (const v of ep.voice_over || []) {
        if (v.char_id && !charIds.has(v.char_id)) {
          errors.push(`D15 ep${ep.ep}: 配音角色 "${v.char_id}" 在 D04 中不存在`);
        }
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V3 镜号连续唯一 ---------- */

const V3 = {
  id: 'V3',
  name: '镜号连续与唯一',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const seenGlobal = new Set();
    for (const ep of ctx.files.D11?.episodes || []) {
      let expect = 1;
      const localSeen = new Set();
      for (const s of ep.shots || []) {
        if (s.shot_id !== expect) {
          errors.push(`D11 ep${ep.ep}: 镜号应连续，第 ${expect} 位出现 ${s.shot_id}`);
          expect = s.shot_id;
        }
        expect += 1;
        if (localSeen.has(s.shot_id)) errors.push(`D11 ep${ep.ep}: 镜号 ${s.shot_id} 重复`);
        localSeen.add(s.shot_id);
        if (seenGlobal.has(s.global_shot_no)) {
          errors.push(`D11 ep${ep.ep}: 全局镜号 ${s.global_shot_no} 重复（镜号须全局唯一）`);
        }
        seenGlobal.add(s.global_shot_no);
      }
    }
    // 全局镜号应单调递增
    const all = [];
    for (const ep of ctx.files.D11?.episodes || []) for (const s of ep.shots || []) all.push(s.global_shot_no);
    for (let i = 1; i < all.length; i += 1) {
      if (all[i] <= all[i - 1]) {
        errors.push(`D11: 全局镜号非单调递增（第 ${i + 1} 个为 ${all[i]}，前一个是 ${all[i - 1]}）`);
        break;
      }
    }
    if (!all.length) warnings.push('D11: 未提供镜位');
    return ok(errors, warnings);
  },
};

/* ---------- V4 时长求和 + 四段制 ---------- */

const V4 = {
  id: 'V4',
  name: '时长求和与四段制边界',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const eps = ctx.files.D11?.episodes || [];
    const epsMap = byEp(eps);
    for (const ep of eps) {
      const sum = (ep.shots || []).reduce((a, s) => a + (Number(s.duration_sec) || 0), 0);
      if (Math.abs(sum - ep.duration_sec) > 0.05) {
        errors.push(`D11 ep${ep.ep}: 镜位时长合计 ${sum.toFixed(2)}s ≠ 集时长 ${ep.duration_sec}s`);
      }
      if (ep.duration_sum_sec !== undefined && Math.abs(ep.duration_sum_sec - sum) > 0.05) {
        errors.push(`D11 ep${ep.ep}: duration_sum_sec=${ep.duration_sum_sec} 与实际求和 ${sum.toFixed(2)} 不符`);
      }
    }
    // D07 四段制
    for (const ep of ctx.files.D07?.episodes || []) {
      const segs = ep.quad_segments || [];
      if (segs.length !== 4) {
        errors.push(`D07 ep${ep.ep}: 四段制必须有 4 段，实际 ${segs.length} 段`);
        continue;
      }
      let cursor = 0;
      for (const [i, s] of segs.entries()) {
        if (s.index !== i + 1) errors.push(`D07 ep${ep.ep}: 段序号应递增，段${i + 1} 标为 ${s.index}`);
        if (Math.abs(s.start_sec - cursor) > 0.05) {
          errors.push(`D07 ep${ep.ep}: 段${i + 1} 起点 ${s.start_sec} 与上一段终点 ${cursor} 不接续`);
        }
        if (s.end_sec <= s.start_sec) errors.push(`D07 ep${ep.ep}: 段${i + 1} 时间区间非法`);
        cursor = s.end_sec;
      }
      const total = cursor;
      const d11ep = epsMap.get(ep.ep);
      const target = d11ep?.duration_sec ?? ep.duration_sum_sec;
      if (target !== undefined && Math.abs(total - target) > 0.05) {
        errors.push(`D07 ep${ep.ep}: 四段合计 ${total}s ≠ 集时长 ${target}s`);
      }
      // D07 场景时长之和
      const sceneSum = (ep.scenes || []).reduce((a, s) => a + (Number(s.duration_sec) || 0), 0);
      if (ep.duration_sum_sec !== undefined && Math.abs(sceneSum - ep.duration_sum_sec) > 0.05) {
        errors.push(`D07 ep${ep.ep}: 场景时长合计 ${sceneSum}s ≠ duration_sum_sec ${ep.duration_sum_sec}`);
      }
      // 段与镜位对齐
      if (d11ep) {
        for (const s of d11ep.shots || []) {
          if (s.quad_segment === undefined) {
            warnings.push(`D11 ep${ep.ep} 镜${s.shot_id}: 未标注 quad_segment，无法验证四段归属`);
            continue;
          }
          if (s.quad_segment < 1 || s.quad_segment > 4) {
            errors.push(`D11 ep${ep.ep} 镜${s.shot_id}: quad_segment=${s.quad_segment} 越界（1~4）`);
          }
        }
      }
    }
    // D11 四段制存在性
    for (const ep of eps) {
      const segs = new Set((ep.shots || []).map((s) => s.quad_segment).filter((x) => x !== undefined));
      if (segs.size && segs.size !== 4) {
        errors.push(`D11 ep${ep.ep}: 镜位只覆盖 ${segs.size} 个四段（应覆盖 4 段）`);
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V5 术语收口一致性 ---------- */

const V5 = {
  id: 'V5',
  name: '术语收口与禁用同义写法',
  scope: 'all',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const glossary = ctx.files.D05?.glossary || [];
    const termMap = new Map(glossary.map((g) => [g.term, g]));
    if (!glossary.length) {
      warnings.push('D05: 术语表为空，无法执行术语收口检查');
    }
    for (const g of glossary) {
      if (!g.definition || !String(g.definition).trim()) {
        errors.push(`D05 术语 "${g.term}": 缺少收口定义`);
      }
      if (!Array.isArray(g.forbidden_synonyms)) {
        errors.push(`D05 术语 "${g.term}": forbidden_synonyms 必须为数组（可为空数组）`);
      }
    }
    // 全文扫描禁用同义词
    // 字段级豁免：见 03_规格/rules.json 的 term_scan_exempt。
    // D03（合规清单）与 D18（质检闸门）必须逐词声明作废写法，扫描时跳过这些字段。
    const exemptions = ctx.rules?.term_scan_exempt || {};
    for (const [docId, data] of Object.entries(ctx.files)) {
      if (docId === 'D05' || !data) continue;
      const skipKeys = Array.isArray(exemptions[docId]) ? exemptions[docId] : [];
      const text = skipKeys.length
        ? allTextExceptPaths(data, skipKeys).join('\n')
        : allText(data).join('\n');
      for (const g of glossary) {
        for (const bad of g.forbidden_synonyms || []) {
          if (bad && text.includes(bad)) {
            errors.push(`${docId}: 出现禁用同义写法 "${bad}"（术语 "${g.term}" 应收口为 "${g.term}"）`);
          }
        }
      }
    }

    // ★ manifest ↔ D05/D04 交叉校验（防 manifest 漂移）
    // project.json 是工厂级速查表。若上游合规收口改了正式名（例：焚化坑→归废处置线），
    // manifest 必须同步，否则出现「D05 已作废旧名、manifest 仍用旧名」的跨文档口径分叉。
    const proj = ctx.project || {};
    for (const pair of proj.terminology?.forbidden_synonym_pairs || []) {
      const g = termMap.get(pair.canonical);
      if (!g) {
        errors.push(
          `project.json.terminology: 术语 "${pair.canonical}" 在 D05.glossary 中不存在（manifest 落后于 D05 收口，需同步）`,
        );
        continue;
      }
      const missing = (pair.banned || []).filter((b) => !(g.forbidden_synonyms || []).includes(b));
      if (missing.length) {
        errors.push(
          `project.json.terminology: "${pair.canonical}" 的禁用写法 [${missing.join(', ')}] 未收进 D05.glossary`,
        );
      }
    }
    const d05Locations = new Set((ctx.files.D05?.locations || []).map((l) => l.name));
    const d05Factions = new Set((ctx.files.D05?.factions || []).map((f) => f.name));
    for (const loc of proj.locations || []) {
      if (d05Locations.size && !d05Locations.has(loc)) {
        errors.push(`project.json.locations: "${loc}" 不在 D05 地点表中（manifest 落后于 D05，需同步）`);
      }
    }
    for (const fac of proj.factions || []) {
      if (d05Factions.size && !d05Factions.has(fac)) {
        errors.push(`project.json.factions: "${fac}" 不在 D05 势力表中（manifest 落后于 D05，需同步）`);
      }
    }
    for (const l of d05Locations) {
      if ((proj.locations || []).length && !(proj.locations || []).includes(l)) {
        warnings.push(`project.json.locations: D05 的 "${l}" 未登记进 manifest，建议补登记`);
      }
    }
    for (const f of d05Factions) {
      if ((proj.factions || []).length && !(proj.factions || []).includes(f)) {
        warnings.push(`project.json.factions: D05 的 "${f}" 未登记进 manifest，建议补登记`);
      }
    }
    const d04Chars = new Map((ctx.files.D04?.characters || []).map((c) => [c.id, c]));
    for (const c of proj.characters || []) {
      const inD04 = d04Chars.get(c.id);
      if (!inD04) {
        warnings.push(`project.json.characters: ${c.id} ${c.name} 尚未写入 D04（人物档案未落盘）`);
        continue;
      }
      if (c.age !== null && c.age !== undefined && inD04.age !== c.age) {
        errors.push(`project.json.characters: ${c.id} 年龄 ${c.age} 与 D04 的 ${inD04.age} 不一致`);
      }
      if (c.minor !== undefined && inD04.minor !== undefined && c.minor !== inD04.minor) {
        errors.push(`project.json.characters: ${c.id} minor=${c.minor} 与 D04 的 ${inD04.minor} 不一致`);
      }
    }

    // ★ 术语「首用集前禁用」判定（V5 内扩展 · 不新增规则编号）
    // 判据来源：03_规格/rules.json 的 `term_first_use` 轴；内容依据是 D05 词条的 `first_use_ep`
    // 与 definition 里的显式禁用区间（例：「ep013–ep040 台词与字幕不得出现「律条」三字（画面描述可用）」）。
    // ⚠️ 受检面与不检面**必须分列**：
    //    `dialogue`（台词面）＝ D11 `shots[].dialogue` ＋ D08 `body[].text`（**仅 type=dialogue**）
    //                                  ＋ D09 `lines[].text`（台词表台词面 · **2026-10-23 企划合规依 D18 `U01-R66` 明派补入**）；
    //    `subtitle`（字幕面）＝ D16 `subtitle_style.lines[].text`；
    //    **画面描述面不查**（D08 `type=action`／D11 `visual_facts`／D12 `image_prompt`）—— D05 明文允许。
    // ⚠️ **禁用写法面（自造档位修饰语等字面禁用同义词）不在此轴**，走 D05 词条的 `forbidden_synonyms`。
    const tfu = ctx.rules?.term_first_use || [];
    const epNum = (v) => {
      const m = String(v ?? '').match(/(\d+)/);
      return m ? parseInt(m[1], 10) : null;
    };
    for (const entry of tfu) {
      const term = entry?.term;
      const from = entry?.first_use_ep;
      const to = entry?.forbidden_until_ep;
      if (!term || !Number.isInteger(from) || !Number.isInteger(to)) continue;
      const faces = Array.isArray(entry.forbidden_faces) ? entry.forbidden_faces : ['dialogue', 'subtitle'];
      const inRange = (ep) => ep !== null && ep >= from && ep <= to;
      const hits = [];
      if (faces.includes('dialogue')) {
        for (const e of ctx.files.D11?.episodes || []) {
          const ep = epNum(e.ep);
          if (!inRange(ep)) continue;
          for (const s of e.shots || []) {
            const d = s.dialogue;
            const vals = Array.isArray(d) ? d : (d ? [d] : []);
            for (const t of vals) {
              const txt = typeof t === 'string' ? t : (t?.text || t?.line || '');
              if (String(txt).includes(term)) {
                hits.push(`D11 ep${ep} 镜${s.shot_id} 台词面`);
              }
            }
          }
        }
        for (const e of ctx.files.D08?.episodes || []) {
          const ep = epNum(e.ep);
          if (!inRange(ep)) continue;
          for (const b of e.body || []) {
            if (b.type === 'dialogue' && String(b.text || '').includes(term)) {
              hits.push(`D08 ep${ep} 台词面 body`);
            }
          }
        }
        // D09 `lines[].text`（台词表台词面 · 台词真源）—— **2026-10-23 企划合规依 D18 `U01-R66` 明派补入**
        // ⚠️ 只扫 `text`（台词字面）；**不扫** `tone`／`subtext`（编剧注解，不是台词面，D05 明文允许「画面描述可用」）
        // ⚠️ 不扫 `voice_cards[].forbidden_words[]`（那是「台词禁出现该词」的**禁止性声明**，扫它等于自伤）
        for (const l of ctx.files.D09?.lines || []) {
          const ep = epNum(l.ep);
          if (!inRange(ep)) continue;
          if (String(l.text || '').includes(term)) {
            hits.push(`D09 ep${ep} 台词表 idx${l.idx ?? '?'}`);
          }
        }
      }
      if (faces.includes('subtitle')) {
        for (const e of ctx.files.D16?.episodes || []) {
          const ep = epNum(e.ep);
          if (!inRange(ep)) continue;
          for (const l of e.subtitle_style?.lines || []) {
            if (String(l.text || '').includes(term)) {
              hits.push(`D16 ep${ep} 字幕 seq${l.seq}`);
            }
          }
        }
      }
      for (const h of hits) {
        errors.push(
          `术语首用集前禁用：${h} 出现「${term}」` +
          `（D05 规定 ep${from}–ep${to} 的台词面与字幕面不得出现该词；画面描述面不受限）`,
        );
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V6 禁词 + minor_present 判定 ---------- */

const V6 = {
  id: 'V6',
  name: '禁词扫描与贬称未成年一票否决',
  scope: 'all',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const forbidden = ctx.rules?.forbidden_words || [];
    const derogatory = ctx.rules?.derogatory_terms || [];
    const minorIds = new Set((ctx.files.D04?.characters || []).filter((c) => c.minor).map((c) => c.id));

    // 未成年角色的 id 与姓名（用于判定贬称指向谁）
    const minorMeta = (ctx.files.D04?.characters || []).filter((c) => c.minor);
    const minorNames = new Set(minorMeta.map((c) => c.name).filter(Boolean));
    const d07map = byEp(ctx.files.D07?.episodes);

    // D11 镜头：禁词扫描 + minor_present 与 D07 在场名单交叉核对
    for (const ep of ctx.files.D11?.episodes || []) {
      const d07 = d07map.get(ep.ep);
      const minorInScene = new Set(
        (d07?.present_characters || []).filter((pc) => pc.minor).map((pc) => pc.char_id),
      );
      for (const s of ep.shots || []) {
        const text = `${s.visual_facts || ''} ${s.dialogue || ''} ${s.sfx || ''}`;
        for (const w of forbidden) {
          if (text.includes(w)) {
            errors.push(`D11 ep${ep.ep} 镜${s.shot_id}: 命中禁词 "${w}"`);
          }
        }
        if (typeof s.minor_present !== 'boolean') {
          errors.push(`D11 ep${ep.ep} 镜${s.shot_id}: minor_present 必须为布尔值`);
          continue;
        }
        if (s.minor_present && minorInScene.size === 0) {
          errors.push(
            `D11 ep${ep.ep} 镜${s.shot_id}: minor_present=true，但 D07 ep${ep.ep} 在场名单中无未成年角色`,
          );
        }
        if (!s.minor_present && minorInScene.size > 0) {
          warnings.push(
            `D11 ep${ep.ep} 镜${s.shot_id}: 本集有未成年角色在场（${[...minorInScene].join(',')}），请确认该镜 minor_present 是否应为 true`,
          );
        }
      }
    }

    // ★ TOOL-02（2026-10-23 Chief 落地）：D08 剧本正文 + D09 对白行/口头禅 纳入 forbidden_words 扫描。
    //   背景：V6 原本只扫 D11 的 visual_facts/dialogue/sfx。台词是**内容源头**——剧本里写错词，
    //   要到下游 D11 才被拦，返工发生在最后一环。补上源头扫描。
    //   扫描面按**显式字段**取，不做「整份文档减去豁免」：
    //     扫 —— D08 episodes[].body[].text（正文）、episodes[].body[].emotion（情绪提示）、D09 lines[].text、voice_cards[].catchphrases
    //     不扫 —— D08 episodes[].compliance_notes、episodes[].body[].compliance_reason（**裁决/规则留痕**，
    //            逐字引用 D03 红线原文以说明「当时查到什么」，属正当留痕；
    //            与 D03.red_lines / D18.global_checks 同类，已在 rules.json 的 term_scan_exempt.D08 登记）
    {
      for (const ep of ctx.files.D08?.episodes || []) {
        for (const line of ep.body || []) {
          const text = `${line.text || ''} ${line.emotion || ''}`;
          for (const w of forbidden) {
            if (text.includes(w)) {
              errors.push(`D08 ep${ep.ep} 剧本正文: 命中禁词 "${w}"（台词是内容源头，须在剧本层改正）`);
            }
          }
        }
      }
      for (const l of ctx.files.D09?.lines || []) {
        for (const w of forbidden) {
          if ((l.text || '').includes(w)) {
            errors.push(`D09 ep${l.ep} 对白行: 命中禁词 "${w}"`);
          }
        }
      }
      for (const c of ctx.files.D09?.voice_cards || []) {
        for (const cp of c.catchphrases || []) {
          for (const w of forbidden) {
            if (String(cp).includes(w)) {
              errors.push(`D09 角色 ${c.char_id} 口头禅: 命中禁词 "${w}"`);
            }
          }
        }
      }
    }

    // D08 台词：贬称指向未成年角色 → 一票否决（Q14=C）
    for (const ep of ctx.files.D08?.episodes || []) {
      const minorsPresent = (ep.present_characters || []).filter((c) => minorIds.has(c));
      for (const line of ep.body || []) {
        if (line.type !== 'dialogue') continue;
        const text = line.text || '';
        for (const d of derogatory) {
          if (!text.includes(d)) continue;
          // 台词指向谁：靠 D09 潜台词判定。
          //   ① 潜台词点名未成年角色（id 或姓名）→ 指向未成年 → 一票否决
          //   ② 有潜台词但没点名 → 不指向未成年 → 放行
          //   ③ 缺 D09 或潜台词为空 → 无法判定，保守从严 → 一票否决
          const d09line = (ctx.files.D09?.lines || []).find(
            (l) => l.ep === ep.ep && l.char_id === line.char_id && (l.text || '') === text,
          ) || (ctx.files.D09?.lines || []).find(
            (l) => l.ep === ep.ep && l.char_id === line.char_id && (l.text || '').includes(text),
          );
          const subtext = (d09line?.subtext || '').trim();
          const namesMinor = [...minorIds].some((id) => subtext.includes(id)) ||
            [...minorNames].some((nm) => subtext.includes(nm));
          let targetsMinor;
          if (!subtext) {
            targetsMinor = true; // 无法判定 → 从严
            errors.push(
              `D08 ep${ep.ep}: 台词命中贬称 "${d}" 且无 D09 潜台词可判定指向对象 → 从严一票否决（本集未成年在场：${minorsPresent.join(',') || '无'}）`,
            );
            continue;
          }
          targetsMinor = namesMinor;
          if (targetsMinor) {
            errors.push(
              `D08 ep${ep.ep}: 台词命中贬称 "${d}" 且指向未成年角色（潜台词：${subtext}）→ 一票否决`,
            );
          }
        }
      }
    }
    // D09 语气卡禁词
    for (const card of ctx.files.D09?.voice_cards || []) {
      for (const d of derogatory) {
        if ((card.forbidden_words || []).includes(d) === false && minorIds.has(card.char_id)) {
          warnings.push(`D09 角色 ${card.char_id}: 为未成年角色，建议把 "${d}" 列入 forbidden_words`);
        }
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V7 D12 角色描述 ⊆ D10 锚点表 ---------- */

/* 「局部特写·无可见锚点」豁免 —— 企划合规 2026-10-23 06:5x 裁定 **S25**（来源：视觉设定 06:2x–06:4x 台账 §九十 §3
   「手部-only 三镜（ep011 镜1 图纸／ep013 镜3 律条／ep015 镜3 频谱）」请总控裁定「角色在画框内但无可见锚点」的统一写法）。
   口径（**两条轴，必须同时成立**）：
     ① `char_ids` ＝ 该角色**在场且可被指认**（D11 明写苏清辞的手/指尖/掌心在画框内 → 登记 SQC **成立**）；
     ② `char_descriptions` ＝ 该角色**在本镜可见的外观锚点**（服装/发型/眉眼/脸…）→ 手部-only 特写**无可写锚点**，
        **有意留空成立**，不视为漏填。
   ⚠️ D12 schema 的 `cards[].items` 是 `additionalProperties: false` → **不能加字段标注**，故判据只能落在校验器侧。
   ⚠️ **双向判据（防假绿，Q60）**：只豁免「**角色名附近仅出现局部身体词、且完全不出现任何外观描写词**」这一类；
     「prompt 里写了角色外观却没登记描述」的**真漏填必须仍然报 warning** —— 否测见 `scripts/negtest_v7_local_only.mjs`。
   受检下限（Q49）：仅当 `ids.length && !descs.length` 时进入本分支；受检 0 条时不产生任何结论。 */
const V7_LOCAL_BODY_RE = /(手|指尖|掌心|指腹|指节|手掌|手背|袖口|手腕)/;
const V7_APPEARANCE_RE =
  /(风衣|白大褂|唐装|长衫|衬衫|制服|衣|服装|服饰|发型|挽发|柳叶眉|眉|发丝|头发|脸|面孔|侧脸|眼|眸|目光|唇|肤色|身形|体型|肩|腰|身段|身姿)/;

/** 取 D10 锚点表里的角色中文名（anchor_text 逗号前那段） */
function v7CharName(anchor) {
  return String(anchor?.anchor_text || '').split(/[，,；;]/)[0].trim();
}

/** 判定某角色在某一卡是否属「局部特写·无可见锚点」 */
function v7IsLocalOnly(card, cid, anchors) {
  const a = anchors.get(cid);
  const name = v7CharName(a);
  if (!name) return false;                       // 拿不到角色名 → 不豁免（保守）
  const prompt = `${card.image_prompt || ''} ${card.video_prompt || ''}`;
  const i = prompt.indexOf(name);
  if (i < 0) return false;                       // 角色名根本没出现 → 不豁免（更可能是漏登记）
  const win = prompt.slice(Math.max(0, i - 20), i + 45);
  if (V7_APPEARANCE_RE.test(win)) return false;  // 附近有外观描写 → 真漏填，保留 warning
  if (!V7_LOCAL_BODY_RE.test(win)) return false; // 附近连局部身体描写都没有 → 保留 warning
  return true;
}

const V7 = {
  id: 'V7',
  name: 'D12 角色描述必须出自 D10 锚点表',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const anchors = new Map((ctx.files.D10?.character_anchors || []).map((a) => [a.char_id, a]));
    if (!anchors.size) {
      warnings.push('D10: 无角色锚点表，跳过 V7');
      return ok(errors, warnings);
    }
    for (const card of ctx.files.D12?.cards || []) {
      const descs = card.char_descriptions || [];
      const ids = card.consistency_refs?.char_ids || [];
      if (ids.length && !descs.length) {
        // 「局部特写·无可见锚点」豁免（S25）：该卡所有声明角色都只是局部身体入画 → 有意留空，不报
        const localOnly = ids.every((cid) => v7IsLocalOnly(card, cid, anchors));
        if (!localOnly) {
          warnings.push(`D12 卡片 ${card.card_id}: 声明了角色 ${ids.join(',')} 但未填 char_descriptions，无法验证锚点闭合`);
        }
      }
      for (const cid of ids) {
        const a = anchors.get(cid);
        if (!a) {
          errors.push(`D12 卡片 ${card.card_id}: D10 中无角色 "${cid}" 的锚点`);
          continue;
        }
        // 该角色的描述必须在锚点文本/标记中出现
        const haystack = `${a.anchor_text || ''} ${(a.markers || []).join(' ')}`;
        const related = descs.filter((d) => haystack.includes(d) || (a.markers || []).some((m) => d.includes(m)));
        if (descs.length && !related.length) {
          errors.push(
            `D12 卡片 ${card.card_id}: 角色 ${cid} 的描述未匹配 D10 锚点表（anchors: ${haystack.slice(0, 80)}…）`,
          );
        }
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V8 单元钩子链闭合 ---------- */

const V8 = {
  id: 'V8',
  name: '单元钩子链闭合',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const eps = ctx.files.D06?.episodes || [];
    const sorted = [...eps].sort((a, b) => a.ep - b.ep);
    if (!sorted.length) {
      warnings.push('D06: 无分集数据，跳过钩子链检查');
      return ok(errors, warnings);
    }
    for (let i = 1; i < sorted.length; i += 1) {
      const prev = sorted[i - 1];
      const cur = sorted[i];
      if (!String(cur.hook_in || '').trim()) {
        errors.push(`D06 ep${cur.ep}: hook_in 为空（须承接 ep${prev.ep} 的 hook_out）`);
      }
      if (!String(prev.hook_out || '').trim()) {
        errors.push(`D06 ep${prev.ep}: hook_out 为空`);
      }
    }
    // 单元首集 hook_in 应与单元定义首钩子对齐（project.units[].first_hook）
    const unitDef = (ctx.project?.units || []).find((u) => u.id === ctx.unit);
    if (unitDef?.first_hook && sorted.length) {
      const first = sorted[0];
      if (first.hook_in && !String(first.hook_in).includes(String(unitDef.first_hook).slice(0, 6))) {
        warnings.push(
          `D06 ep${first.ep}: hook_in 与单元定义 first_hook「${unitDef.first_hook}」措辞差异较大，请人工确认`,
        );
      }
    }
    // 单元末集 hook_out 应与单元定义末钩子对齐
    if (unitDef?.last_hook && sorted.length) {
      const last = sorted[sorted.length - 1];
      if (last.hook_out && !String(last.hook_out).includes(String(unitDef.last_hook).slice(0, 6))) {
        warnings.push(
          `D06 ep${last.ep}: hook_out 与单元定义 last_hook「${unitDef.last_hook}」措辞差异较大，请人工确认`,
        );
      }
    }
    // 集号连续
    for (let i = 1; i < sorted.length; i += 1) {
      if (sorted[i].ep !== sorted[i - 1].ep + 1) {
        errors.push(`D06: 集号不连续，ep${sorted[i - 1].ep} 之后是 ep${sorted[i].ep}`);
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V9 字数两档 ---------- */

const V9 = {
  id: 'V9',
  name: '字数基础档与合规增量档',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const min = ctx.rules?.word_count?.base_min ?? 180;
    const max = ctx.rules?.word_count?.base_max ?? 240;
    const totalMax = ctx.rules?.word_count?.total_max ?? 330;
    for (const ep of ctx.files.D08?.episodes || []) {
      let base = 0;
      let add = 0;
      for (const b of ep.body || []) {
        const n = countWords(b.text || '');
        if (b.compliance_added) add += n;
        else base += n;
      }
      const declared = ep.word_count || {};
      if (declared.base !== undefined && declared.base !== base) {
        errors.push(`D08 ep${ep.ep}: word_count.base 声明 ${declared.base}，实际计算 ${base}`);
      }
      if (declared.compliance_add !== undefined && declared.compliance_add !== add) {
        errors.push(`D08 ep${ep.ep}: word_count.compliance_add 声明 ${declared.compliance_add}，实际 ${add}`);
      }
      if (declared.total !== undefined && declared.total !== base + add) {
        errors.push(`D08 ep${ep.ep}: word_count.total 声明 ${declared.total}，实际 ${base + add}`);
      }
      if (base < min) errors.push(`D08 ep${ep.ep}: 基础字数 ${base} < 下限 ${min}`);
      if (base > max) errors.push(`D08 ep${ep.ep}: 基础字数 ${base} > 上限 ${max}`);
      if (base + add > totalMax) {
        errors.push(`D08 ep${ep.ep}: 总字数 ${base + add} > 硬上限 ${totalMax}`);
      }
      // 标了 compliance_added 却没写理由
      for (const b of ep.body || []) {
        if (b.compliance_added && !String(b.compliance_reason || '').trim()) {
          errors.push(`D08 ep${ep.ep}: 标记 compliance_added 的段落缺少 compliance_reason`);
        }
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V10 伏笔埋收 + 爽点密度 ---------- */

const V10 = {
  id: 'V10',
  name: '伏笔埋收与爽点密度',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const eps = [...(ctx.files.D06?.episodes || [])].sort((a, b) => a.ep - b.ep);
    if (!eps.length) return ok(errors, warnings);

    // 伏笔：同一 F 编号的 plant 与 payoff 必须能在全剧范围内找到
    const allForeshadows = [];
    for (const ep of eps) {
      const f = ep.foreshadow;
      if (!f) continue;
      if (f.plant) allForeshadows.push({ ep: ep.ep, kind: 'plant', id: f.plant });
      if (f.payoff) allForeshadows.push({ ep: ep.ep, kind: 'payoff', id: f.payoff });
    }
    const ids = new Set(allForeshadows.map((f) => f.id));
    for (const id of ids) {
      const plants = allForeshadows.filter((f) => f.id === id && f.kind === 'plant');
      const pays = allForeshadows.filter((f) => f.id === id && f.kind === 'payoff');
      if (plants.length && !pays.length) {
        const pend = eps.find((e) => e.foreshadow?.plant === id)?.foreshadow?.pending_unit;
        if (pend) warnings.push(`伏笔 ${id}: 已埋于本单元，回收登记在 ${pend}（跨单元回收，需在目标单元复核）`);
        else warnings.push(`伏笔 ${id}: 已埋未收，且未登记 pending_unit`);
      }
      for (const p of plants) {
        for (const y of pays) {
          if (y.ep < p.ep) errors.push(`伏笔 ${id}: 回收（ep${y.ep}）早于埋设（ep${p.ep}）`);
        }
      }
    }

    // 爽点密度：每 8 集至少 N 个爽点
    const minPer = ctx.rules?.density?.min_shock_points_per_unit ?? 3;
    const shock = eps.filter((e) => (e.beats || []).includes('爽点')).length;
    if (shock < minPer) {
      errors.push(`D06 ${ctx.unit}: 爽点仅 ${shock} 个 < 下限 ${minPer}/单元`);
    }
    // 转折：单元内必须有
    if (!eps.some((e) => (e.beats || []).includes('转折'))) {
      warnings.push(`D06 ${ctx.unit}: 单元内无「转折」beat，建议复核节奏`);
    }
    return ok(errors, warnings);
  },
};

/* ---------- V11 D14 逐镜覆盖与逐镜包一致性 ---------- */

/**
 * 结构化深比较：返回两对象的差异路径列表（忽略键顺序与数组顺序敏感性）。
 * 用于核对「落盘逐镜包」与「D14 内联项」是否同形。
 */
function deepDiff(a, b, path = '', out = [], limit = 200) {
  if (out.length >= limit) return out;
  const isObj = (v) => v && typeof v === 'object' && !Array.isArray(v);
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b)) {
      out.push(`${path || '<root>'}: 数组/非数组不一致`);
      return out;
    }
    if (a.length !== b.length) {
      out.push(`${path || '<root>'}: 数组长度 ${a.length} ≠ ${b.length}`);
      return out;
    }
    for (let i = 0; i < a.length; i++) deepDiff(a[i], b[i], `${path}[${i}]`, out, limit);
    return out;
  }
  if (isObj(a) && isObj(b)) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of keys) {
      if (!(k in a)) { out.push(`${path}.${k}: 仅落盘包有`); continue; }
      if (!(k in b)) { out.push(`${path}.${k}: 仅内联项有`); continue; }
      deepDiff(a[k], b[k], path ? `${path}.${k}` : k, out, limit);
    }
    return out;
  }
  if (a !== b) {
    const brief = (v) => (typeof v === 'string' && v.length > 40 ? `${v.slice(0, 40)}…` : String(v));
    out.push(`${path || '<root>'}: ${brief(a)} ≠ ${brief(b)}`);
  }
  return out;
}

/**
 * 解析逐镜交接包文件路径。
 * package_path 是相对路径：先相对单元目录（units/<UNIT>/），再相对项目根；绝对路径按原样解析。
 * @returns {string|null} 命中的文件绝对路径；未命中返回 null
 */
function resolvePackagePath(ctx, rel) {
  if (!rel || typeof rel !== 'string') return null;
  const candidates = [];
  if (path.isAbsolute(rel)) candidates.push(rel);
  for (const base of [ctx.unitDir, ctx.projectDir]) {
    if (base) candidates.push(path.resolve(base, rel));
  }
  for (const c of candidates) {
    try {
      if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
    } catch { /* 路径非法则跳过 */ }
  }
  return null;
}

const V11 = {
  id: 'V11',
  name: 'D14 逐镜覆盖与逐镜包一致性',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const D14 = ctx.files.D14;
    if (!D14) {
      // D14 尚未产出 → 跳过逐镜覆盖检查。
      // ⚠ 缺件本身已由 V1 的 missingRequiredDeliverables() 统一计 error（Q109·唯一实现点），
      //    此处**不再重复计一次缺件**，只说明「本规则因缺件而无法执行」。
      warnings.push('D14: 本次上下文中不存在，跳过逐镜覆盖检查（缺件已由单元必交清单统一计 error）');
      return ok(errors, warnings);
    }
    const D11 = ctx.files.D11;
    if (!D11) {
      warnings.push('D11: 不存在，无法校验 D14 逐镜覆盖');
      return ok(errors, warnings);
    }
    const cfg = ctx.rules?.d14_shot_coverage || {};
    const requireFile = cfg.require_package_file !== false;
    const validatePkg = cfg.validate_package_schema !== false;

    // D11 镜头真源
    const src = new Map();
    for (const ep of D11.episodes || []) {
      for (const s of ep.shots || []) src.set(`${ep.ep}#${s.shot_id}`, s);
    }
    if (!src.size) {
      warnings.push('D11: 无镜位数据，跳过 D14 覆盖检查');
      return ok(errors, warnings);
    }

    // D14 逐镜索引（同一 (ep, shot_id) 不得重复）
    const seen = new Map();
    for (const sh of D14.shots || []) {
      const key = `${sh.ep}#${sh.shot_id}`;
      if (seen.has(key)) {
        errors.push(`D14: 镜头 ${key} 在 shots[] 中重复出现`);
        continue;
      }
      seen.set(key, sh);
    }

    // 覆盖：缺失 / 多余 —— 「假覆盖」的核心防线，报 error 不报 warning
    for (const key of src.keys()) {
      if (!seen.has(key)) errors.push(`D14: 缺少镜头 ${key} 的交接包（D11 有此镜，D14 未覆盖）`);
    }
    for (const key of seen.keys()) {
      if (!src.has(key)) errors.push(`D14: 多出镜头 ${key}（D11 中不存在此镜）`);
    }

    // 逐镜字段一致性 + 逐镜包真实存在
    const pkgSchema = ctx.schemas?.definitions?.D14ShotPackage;
    for (const [key, sh] of seen) {
      const s = src.get(key);
      if (!s) continue;
      if (sh.global_shot_no !== s.global_shot_no) {
        errors.push(`D14 ${key}: global_shot_no ${sh.global_shot_no} ≠ D11 的 ${s.global_shot_no}`);
      }
      if (sh.scene_code !== s.scene_code) {
        errors.push(`D14 ${key}: scene_code "${sh.scene_code}" ≠ D11 的 "${s.scene_code}"`);
      }
      if (Math.abs(Number(sh.duration_sec) - Number(s.duration_sec)) > 0.001) {
        errors.push(`D14 ${key}: duration_sec ${sh.duration_sec} ≠ D11 的 ${s.duration_sec}`);
      }
      if (!requireFile) continue;
      const abs = resolvePackagePath(ctx, sh.package_path);
      if (!abs) {
        errors.push(
          `D14 ${key}: 逐镜交接包文件不存在（package_path="${sh.package_path}"，相对 ${ctx.unitDir || 'units/<UNIT>/'} 解析，其次相对项目根）`,
        );
        continue;
      }
      if (!validatePkg || !pkgSchema) continue;
      let data = null;
      try {
        data = JSON.parse(fs.readFileSync(abs, 'utf8'));
      } catch (e) {
        errors.push(`D14 ${key}: 逐镜交接包不是合法 JSON（${abs}）：${e.message}`);
        continue;
      }
      const r = validate(data, pkgSchema, ctx.schemas);
      for (const e of r.errors) errors.push(`D14 ${key}: 逐镜交接包未通过 D14ShotPackage 校验（${abs}） ${e}`);
      // 落盘包与 D14 内联项必须**同形**：D14 是逐镜包的生成快照，
      // 两边不一致就说明有人只改了其中一份，审计会读到假合同。
      const diffs = deepDiff(sh, data);
      if (diffs.length) {
        errors.push(
          `D14 ${key}: 落盘包与 D14 内联内容不一致（${diffs.slice(0, 4).join('；')}${diffs.length > 4 ? ` …共 ${diffs.length} 处` : ''}）`,
        );
      }
      // 落盘包自身的镜头身份也要对上 D11，不能只校验内联项
      if (data.global_shot_no !== s.global_shot_no) {
        errors.push(`D14 ${key}: 落盘包 global_shot_no ${data.global_shot_no} ≠ D11 的 ${s.global_shot_no}`);
      }
      if (data.scene_code !== s.scene_code) {
        errors.push(`D14 ${key}: 落盘包 scene_code "${data.scene_code}" ≠ D11 的 "${s.scene_code}"`);
      }
      if (Math.abs(Number(data.duration_sec) - Number(s.duration_sec)) > 0.001) {
        errors.push(`D14 ${key}: 落盘包 duration_sec ${data.duration_sec} ≠ D11 的 ${s.duration_sec}`);
      }
    }
    return ok(errors, warnings);
  },
};

/* ---------- V12 白模构图一致性 ---------- */
/**
 * 背景（2026-10-23 · Q94）：工厂此前**没有任何一条规则**把 D11 的 `shot_size`
 * 与白模投影的实测占幅绑定 —— 实测 U01/U02 共 64 镜几何严重失真，却一路校验全绿：
 *   · 24 镜（37.5%）角色代理体完全不在画幅内
 *   · 画面最大对象是角色的仅 10 镜（15.6%），EXT 外壳 33 镜
 *   · 特写实测占幅中位仅 42%（应 70–95%）、全景占 90%（应 5–20%）
 * 根因在白模层（姿态词表 / 代理体可读性 / 取景），但**没有任何闸门能发现**。
 * 本规则把「D11 声明的景别」与「白模投影实测占幅」绑起来，成为白模交付的硬闸。
 *
 * 判据：
 *   W1 角色在画幅内（非空镜）        —— 角色存在性
 *   W2 主体占画幅高 ∈ shot_size 区间   —— 景别映射
 *   W3 画面最大对象必须是角色（非空镜） —— 主体是否让位给环境
 *   W4 无姿态翻滚（相邻采样帧旋转跳变） —— 需投影含 rotation_euler_deg
 *   W5 姿态词表合法                   —— 需投影含 pose
 *
 * 阈值真源：`03_规格/rules.json` → `white_model_framing`（改那里即改阈值，不改代码）。
 */
const WM_KINDS = ['CHAR', 'PROP', 'LGT', 'FX', 'EXT'];
function wmKindOf(name) {
  for (const k of WM_KINDS) if (name.includes(k)) return k;
  return 'OTHER';
}
/** 欧拉角差归一化到 [-180,180]，避免 ±180 环绕造出假跳变 */
function wmAngleDelta(a, b) {
  let d = Math.abs(Number(a) - Number(b)) % 360;
  if (d > 180) d = 360 - d;
  return d;
}

const V12 = {
  id: 'V12',
  name: '白模构图一致性（D11 景别 ↔ 投影占幅）',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const cfg = ctx.rules?.white_model_framing || {};
    if (cfg.enabled === false) {
      warnings.push('V12: rules.json 的 white_model_framing.enabled=false，已跳过白模构图检查');
      return ok(errors, warnings);
    }
    const bands = cfg.shot_size_bands || {};
    const maxJump = Number(cfg.max_rotation_jump_deg ?? 30);
    const requireLargest = cfg.require_subject_is_largest !== false;
    const vocab = Array.isArray(cfg.pose_vocabulary) ? cfg.pose_vocabulary : null;
    const emptyRe = cfg.empty_shot_pattern ? new RegExp(cfg.empty_shot_pattern) : null;

    const D11 = ctx.files.D11;
    if (!D11) {
      warnings.push('V12: D11 不存在，无法把景别与白模占幅对账');
      return ok(errors, warnings);
    }
    const shotsRoot = ctx.unitDir ? path.join(ctx.unitDir, 'D14_shots') : null;
    if (!shotsRoot || !fs.existsSync(shotsRoot)) {
      warnings.push('V12: 本单元尚无 D14_shots 白模投影，跳过构图检查（若本单元应产出白模属遗漏）');
      return ok(errors, warnings);
    }
    const src = new Map();
    for (const ep of D11.episodes || []) {
      for (const s of ep.shots || []) src.set(`${ep.ep}#${s.shot_id}`, s);
    }
    if (!src.size) {
      warnings.push('V12: D11 无镜位数据，跳过构图检查');
      return ok(errors, warnings);
    }

    let checked = 0;
    let shotsWithRotation = 0;
    let shotsWithPose = 0;
    const exemptions = [];
    const unknownSize = new Set();

    for (const dir of fs.readdirSync(shotsRoot).sort()) {
      const pj = path.join(shotsRoot, dir, 'projection.json');
      if (!fs.existsSync(pj)) continue;
      let proj;
      try {
        proj = JSON.parse(fs.readFileSync(pj, 'utf8'));
      } catch (e) {
        errors.push(`V12 ${dir}: projection.json 不是合法 JSON：${e.message}`);
        continue;
      }
      const key = `${proj.ep}#${proj.shot_id}`;
      const shot = src.get(key);
      if (!shot) {
        warnings.push(`V12 ${dir}: D11 中不存在镜头 ${key}，跳过（无法对账景别）`);
        continue;
      }
      checked++;

      let subjectMax = 0;
      let largest = null;
      const rotSeq = new Map();
      const poses = new Set();
      for (const fr of proj.frames || []) {
        for (const [name, o] of Object.entries(fr.objects || {})) {
          if (!o || !o.in_frame) continue;
          const h = Number(o.visible_percent?.height ?? 0);
          if (!largest || h > largest.h) largest = { name, h, kind: wmKindOf(name) };
          if (wmKindOf(name) !== 'CHAR') continue;
          if (h > subjectMax) subjectMax = h;
          if (Array.isArray(o.rotation_euler_deg)) {
            if (!rotSeq.has(name)) rotSeq.set(name, []);
            rotSeq.get(name).push(o.rotation_euler_deg);
          }
          if (typeof o.pose === 'string') poses.add(o.pose);
        }
      }

      // 空镜豁免：D11 画面事实明写空镜时，跳过 W1/W2/W3
      const facts = String(shot.visual_facts || '');
      if (emptyRe && emptyRe.test(facts)) {
        exemptions.push(`${dir}（D11 画面事实明写空镜）`);
        continue;
      }

      const bad = [];
      // W1 角色在画幅内
      if (!(subjectMax > 0)) bad.push(`W1 角色完全不在画幅内（占幅 0%）`);
      // W2 景别占幅区间
      const size = shot.shot_size;
      const band = bands[size];
      if (!band) {
        unknownSize.add(String(size));
      } else if (subjectMax > 0 && (subjectMax < band[0] || subjectMax > band[1])) {
        bad.push(`W2 主体占幅 ${subjectMax.toFixed(1)}% 落在「${size}」区间 [${band[0]}, ${band[1]}] 之外`);
      }
      // W3 画面最大对象
      if (!largest) {
        bad.push('W3 画幅内没有任何可见对象');
      } else if (requireLargest && largest.kind !== 'CHAR') {
        bad.push(`W3 画面最大对象是 ${largest.kind}「${largest.name}」（占幅 ${largest.h.toFixed(1)}%），主体让位给环境`);
      }
      // W4 姿态翻滚
      if (rotSeq.size) {
        shotsWithRotation++;
        for (const [name, seq] of rotSeq) {
          for (let i = 1; i < seq.length; i++) {
            let jump = 0;
            for (let k = 0; k < 3; k++) jump = Math.max(jump, wmAngleDelta(seq[i][k], seq[i - 1][k]));
            if (jump > maxJump) {
              bad.push(`W4 角色「${name}」在第 ${i} 个采样帧间旋转跳变 ${jump.toFixed(1)}°（上限 ${maxJump}°）`);
              break;
            }
          }
        }
      }
      // W5 姿态词表
      if (poses.size) {
        shotsWithPose++;
        if (vocab) {
          for (const p of poses) {
            if (!vocab.includes(p)) bad.push(`W5 姿态「${p}」不在白模姿态词表内（允许：${vocab.join('/')}）`);
          }
        }
      }
      if (bad.length) errors.push(`V12 ${dir}（ep${proj.ep} shot${proj.shot_id}，${size}）：${bad.join('；')}`);
    }

    if (exemptions.length) {
      warnings.push(`V12: 空镜豁免 ${exemptions.length} 镜 —— ${exemptions.join('、')}`);
    }
    if (unknownSize.size) {
      warnings.push(`V12: 未知景别值 ${[...unknownSize].join('/')}，rules.json 的 white_model_framing.shot_size_bands 未覆盖，未判 W2`);
    }
    if (!shotsWithRotation) {
      warnings.push('V12: 白模投影未提供 rotation_euler_deg 字段，无法判定姿态翻滚（W4），建议白模构建器补该字段');
    }
    if (!shotsWithPose) {
      warnings.push('V12: 白模投影未提供 pose 字段，无法判定姿态词表合法性（W5），建议白模构建器补该字段');
    }
    warnings.push(`V12: 已对账 ${checked} 镜（${path.basename(shotsRoot)}）`);
    return ok(errors, warnings);
  },
};

/**
 * V13 画外音结构化一致性（D15 `voice_over[]` ↔ D11 镜次台词）
 *
 * 判据（Q108 · 2026-10-23 总控明派 · 企划合规 R-028h-r2 落地）：
 *   V13-a  `at_sec ≤ golden_window_sec` 的 VO，若说话人实体不在该时刻画幅内
 *          （`speaker_in_frame === false`）⇒ 必须 `vo_type="offscreen"`，否则 **error**。
 *   V13-b  `vo_type="onscreen"` 但对应镜次 `dialogue` 为空 ⇒ **error**。
 *   V13-c  （**反证腿**）`vo_type="offscreen"` 且镜次无 dialogue ⇒ **必须不报错**。
 *
 * 口径（Q104① 收口，2026-10-23 企划合规裁定）：
 *   `speaker_in_frame` 判的是「**说话人的身体实体**（含局部身体／剪影／背影）是否出现在
 *   该时刻画幅内」，**不是**「脸是否在画」、也不是「身份是否露」。
 *   ⇒ 三档映射：**身份不出画** ⇒ `speaker_in_frame=true` ＋ `vo_type=onscreen`；
 *     **人物不出画** ⇒ `speaker_in_frame=false` ＋ `vo_type=offscreen`；
 *     **主观声**（Q104③：画幅内无其任何形象）⇒ `speaker_in_frame=false` ＋ `vo_type=offscreen`。
 *   ⇒ 该映射下 V13-b 自洽：声明 onscreen（实体在画）的台词必须由该镜 `dialogue` 承载。
 *
 * 字段缺失策略：**缺失不判 error**（存量三单元 D15 的 `voice_over[]` 无这两个字段，
 *   判 error 即全红且属规则缺陷）；仅在金三秒窗口内聚合成**一条** warning 提示补字段。
 *   （Q104② 要求「三处字面同措辞」是文档级纪律，本规则不重复实现字面比对。）
 *
 * 阈值与取值真源：`03_规格/rules.json` → `voice_over_structure`（⛔ 禁在脚本里硬编码，Q110④）。
 * 本规则**只读 D15 一处判定面**；D16 `golden3s_first_line` 是**同步面**（字段规格表 D16 段
 * 要求与 D15 逐字一致），⛔ 不在此重复判定（同一规则只许一处实现，Q110②）。
 */
const V13 = {
  id: 'V13',
  name: '画外音结构化一致性（D15 voice_over ↔ D11 镜次台词）',
  scope: 'unit',
  run(ctx) {
    const errors = [];
    const warnings = [];
    const cfg = ctx.rules?.voice_over_structure || {};
    if (cfg.enabled === false) {
      warnings.push('V13: rules.json 的 voice_over_structure.enabled=false，已跳过画外音结构化检查');
      return ok(errors, warnings);
    }
    const golden = Number(cfg.golden_window_sec ?? 1.5);
    const voTypeField = cfg.vo_type_field || 'vo_type';
    const sifField = cfg.speaker_in_frame_field || 'speaker_in_frame';
    const atField = cfg.at_field || 'at_sec';

    const D15 = ctx.files.D15;
    if (!D15) {
      warnings.push('V13: D15 不存在，无法检查画外音结构化字段');
      return ok(errors, warnings);
    }
    const D11 = ctx.files.D11;
    if (!D11) {
      warnings.push('V13: D11 不存在，无法对账镜次台词（V13-b 未判），仅判 V13-a');
    }
    const shotMap = new Map();
    if (D11) {
      for (const ep of D11.episodes || []) {
        for (const s of ep.shots || []) shotMap.set(`${ep.ep}#${s.shot_id}`, s);
      }
    }

    let voCount = 0;
    let goldenMissing = 0;
    let released = 0;   // V13-c 反证腿计数（声明 offscreen 且镜次无台词 ⇒ 放行）
    let onscreenChecked = 0;
    const missingRefs = [];

    for (const ep of D15.episodes || []) {
      for (const vo of ep.voice_over || []) {
        voCount++;
        const ref = vo.line_ref || `idx${vo.idx ?? '?'}`;
        const at = Number(vo[atField]);
        const voType = vo[voTypeField];
        const sif = vo[sifField];
        const hasType = typeof voType === 'string';
        const hasSif = typeof sif === 'boolean';
        const inGolden = Number.isFinite(at) && at <= golden;

        // ── V13-a：金三秒窗口内说话人不在画幅内 ⇒ 必须声明 offscreen ──
        if (inGolden && hasSif && sif === false && voType !== 'offscreen') {
          errors.push(
            `V13 D15 ep${ep.ep} ${ref}：说话人不在该时刻画幅内（${sifField}=false）` +
            `但 ${voTypeField}=${JSON.stringify(voType)}（${atField}=${at} ≤ ${golden}s）` +
            `，必须为 "offscreen"`
          );
        }

        // ── V13-b：声明 onscreen ⇒ 对应镜次必须有台词承载 ──
        if (voType === 'onscreen') {
          const shot = shotMap.get(`${ep.ep}#${vo.shot_id}`);
          if (!shot) {
            warnings.push(`V13 D15 ep${ep.ep} ${ref}：D11 中找不到镜次 ${ep.ep}#${vo.shot_id}，V13-b 未判`);
          } else if (!String(shot.dialogue ?? '').trim()) {
            onscreenChecked++;
            errors.push(
              `V13 D15 ep${ep.ep} ${ref}（shot_id=${vo.shot_id}）：声明 ${voTypeField}="onscreen"` +
              `，但 D11 对应镜次 dialogue 为空`
            );
          }
        }

        // ── V13-c（反证腿）：声明 offscreen 且镜次无台词 ⇒ 必须放行（不产生 error） ──
        if (voType === 'offscreen') {
          const shot = shotMap.get(`${ep.ep}#${vo.shot_id}`);
          if (shot && !String(shot.dialogue ?? '').trim()) released++;
        }

        // ── 字段缺失：只在金三秒窗口内聚合提示，不判 error ──
        if (inGolden && (!hasType || !hasSif)) {
          goldenMissing++;
          if (missingRefs.length < 12) missingRefs.push(`ep${ep.ep}/shot${vo.shot_id}@${at}s`);
        }
      }
    }

    if (goldenMissing) {
      warnings.push(
        `V13: D15 有 ${goldenMissing} 条画外音落在金三秒窗口（${atField} ≤ ${golden}s）` +
        `但未声明 ${voTypeField}／${sifField}，V13-a／V13-b 未判（缺失不判 error）；` +
        `建议补齐字段后复跑（样例：${missingRefs.join('、')}）`
      );
    }
    warnings.push(
      `V13: 已检查画外音 ${voCount} 条（onscreen 对账 ${onscreenChecked} 条，` +
      `V13-c 反证腿放行 ${released} 条）`
    );
    return ok(errors, warnings);
  },
};

export const RULES = [V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13];
export const RULE_INDEX = Object.fromEntries(RULES.map((r) => [r.id, r]));
