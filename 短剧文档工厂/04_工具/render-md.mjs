#!/usr/bin/env node
/**
 * render-md.mjs —— JSON 真源 → Markdown 单向渲染器
 *
 * 用法：
 *   node render-md.mjs --project <项目目录> [--unit U01] [--out <渲染目录>]
 *
 * 铁律：**单向**。JSON 是真源，MD 是产物。
 *       绝不做 MD→JSON 反向同步；人工改 MD 会在下次渲染被覆盖。
 *
 * 退出码：0 成功；2 参数/IO 错误
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FACTORY_ROOT = path.resolve(__dirname, '..');

const argv = process.argv.slice(2);
function arg(name, def = null) {
  const i = argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}
const projectDir = arg('project');
const onlyUnit = arg('unit');
const outDirArg = arg('out');

if (!projectDir || projectDir === true) {
  console.error('用法：node render-md.mjs --project <项目目录> [--unit U01] [--out <渲染目录>]');
  process.exit(2);
}
const PROJECT = path.resolve(projectDir);
if (!fs.existsSync(PROJECT)) {
  console.error(`项目目录不存在：${PROJECT}`);
  process.exit(2);
}
const OUT_ROOT = outDirArg && outDirArg !== true
  ? path.resolve(outDirArg)
  : path.join(PROJECT, 'render');

/* ---------- 渲染原语 ---------- */

const BANNER = (title, sub) => [
  `# ${title}`,
  '',
  `> ${sub}`,
  '> ⚠️ **本文件由 `render-md.mjs` 从 JSON 真源自动渲染，请勿手工编辑**；改动请改 JSON 后重新渲染。',
  '> 生成命令：`node 短剧文档工厂/04_工具/render-md.mjs --project <项目目录>`',
  '',
  '---',
  '',
].join('\n');

const table = (headers, rows) => {
  if (!rows.length) return '_（无）_\n';
  const esc = (v) => String(v ?? '').replace(/\|/g, '\\|').replace(/\n/g, '<br>');
  const out = [
    `| ${headers.join(' | ')} |`,
    `|${headers.map(() => '---').join('|')}|`,
  ];
  for (const r of rows) out.push(`| ${r.map(esc).join(' | ')} |`);
  return out.join('\n') + '\n';
};

const h2 = (t) => `\n## ${t}\n\n`;
const h3 = (t) => `\n### ${t}\n\n`;
const h4 = (t) => `\n#### ${t}\n\n`;
const p = (t) => `${t}\n\n`;
const ul = (arr) => (arr && arr.length ? arr.map((x) => `- ${x}`).join('\n') + '\n\n' : '_（无）_\n\n');
const obj = (o) => (o && Object.keys(o).length
  ? '```json\n' + JSON.stringify(o, null, 2) + '\n```\n\n'
  : '_（无）_\n\n');

/* ---------- 跨交付物读取缓存（渲染期填充，供跨文档视图使用） ---------- */
const SHARED = {};   // shared/Dxx.json
const UNITS = {};    // UNITS[unitId][docId] = data

/* ---------- 跨文档派生工具 ---------- */

// 从自由文本里抽出《办法》/ D03 的 R 条款编号（如 "D03 R09：..." → ["R09"]）
const ruleIdsIn = (text) => {
  if (!text) return [];
  const m = String(text).match(/R\d{1,2}/g);
  return m ? [...new Set(m)] : [];
};

// 从 D11 的 dialogue 字段里抽出台词原文（"叶承钧「理由不在审核范围内。」／陆沉「我不杀你。」"）
const quotedIn = (text) => {
  if (!text) return [];
  const m = String(text).match(/[「『"“](.+?)[」』"”]/g);
  return m ? m.map((s) => s.replace(/^[「『"“]|[」』"”]$/g, '')) : [];
};

// D08 body 条目 → 镜头意图映射。
// 两级结构：
//   byText : `${ep}|${body 文本去引号}` → { seq, intent, type, text }（同 ep 同文本去重）
//   byShot : `${ep}|${shot_id}`        → [intent, ...]（一条意图只归一个镜，总数守恒）
// 说明：shot_intent 实际挂在 action / subtitle / 对白 各类 body 上（U01 对白类 0 条），
// 因此不能只按引号台词匹配，必须回落到 D11 画面事实的子串匹配。
function buildShotIntentIndex(d08) {
  const byText = new Map();
  for (const e of (d08?.episodes || [])) {
    let seq = 0;
    for (const b of (e.body || [])) {
      seq += 1;
      if (!b.shot_intent) continue;
      const raw = String(b.text || '').replace(/^[「『"“]|[」』"”]$/g, '').trim();
      if (!raw) continue;
      const key = `${e.ep}|${raw}`;
      if (!byText.has(key)) byText.set(key, { seq, intent: b.shot_intent, type: b.type, text: raw });
    }
  }
  return byText;
}

// body 原文与画面事实的最长公共连续片段（12 字起逐步收窄到 4 字）
// 只做确定性子串匹配，不做模糊猜测。
function longestSharedFragment(bodyText, facts, maxSize = 12, minSize = 4) {
  const t = String(bodyText || '').trim();
  if (t.length < minSize) return null;
  for (let size = Math.min(maxSize, t.length); size >= minSize; size--) {
    for (let st = 0; st + size <= t.length; st++) {
      const cand = t.slice(st, st + size);
      if (facts.includes(cand)) return cand;
    }
  }
  return null;
}

// 意图 → 镜位 贪心分配：每条 shot_intent 只归一个镜（归到画面事实匹配最强的那个），
// 避免同一条意图因画面事实措辞相近被计入多个镜，导致总数失真。
function buildShotIntentByShot(intentIdx, d11) {
  const byShot = new Map();
  const shots = [];
  for (const e of (d11?.episodes || [])) {
    for (const s of (e.shots || [])) {
      shots.push({ ep: e.ep, shot_id: s.shot_id, facts: String(s.visual_facts || ''), dialogue: s.dialogue || '' });
    }
  }
  for (const [key, rec] of intentIdx) {
    const ep = Number(key.split('|')[0]);
    // ① 对白原文精确命中优先
    let placed = false;
    for (const sh of shots) {
      if (sh.ep !== ep) continue;
      for (const q of quotedIn(sh.dialogue)) {
        if (`${ep}|${q}` === key) {
          const k = `${ep}|${sh.shot_id}`;
          if (!byShot.has(k)) byShot.set(k, []);
          byShot.get(k).push(rec.intent);
          placed = true;
          break;
        }
      }
      if (placed) break;
    }
    if (placed) continue;
    // ② 画面事实子串匹配，取匹配片段最长的镜
    let best = null; let bestLen = 0;
    for (const sh of shots) {
      if (sh.ep !== ep) continue;
      const frag = longestSharedFragment(rec.text, sh.facts);
      if (frag && frag.length > bestLen) { best = sh; bestLen = frag.length; }
    }
    if (best) {
      const k = `${ep}|${best.shot_id}`;
      if (!byShot.has(k)) byShot.set(k, []);
      byShot.get(k).push(rec.intent);
    }
  }
  return byShot;
}

function shotIntentForShot(byShot, ep, shot) {
  if (!byShot || byShot.size === 0) return '—';
  const hits = byShot.get(`${ep}|${shot?.shot_id}`) || [];
  return hits.length ? [...new Set(hits)].join('；') : '—';
}

const DOC_TITLE = {
  D01: 'D01 · 创意接单卡', D02: 'D02 · 项目企划书', D03: 'D03 · 合规与过审清单',
  D04: 'D04 · 人物设定档案', D05: 'D05 · 世界观与设定圣经', D06: 'D06 · 分集大纲',
  D07: 'D07 · 逐集施工卡', D08: 'D08 · 分集剧本', D09: 'D09 · 对白表与角色语气卡',
  D10: 'D10 · 视觉圣经', D11: 'D11 · 分镜脚本', D12: 'D12 · AI 提示词卡库',
  D13: 'D13 · 场景白模说明书', D14: 'D14 · 白模→H3 交接包', D15: 'D15 · 声音设计表',
  D16: 'D16 · 剪辑节奏表', D17: 'D17 · AI 生产排期与成本', D18: 'D18 · 交付与质检清单',
};

/* ---------- 各交付物渲染器 ---------- */

const renderers = {
  D01: (d) => BANNER(DOC_TITLE.D01, `负责人：企划合规｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、Logline') + p(d.logline) +
    (d.premise ? h2('二、前提') + p(d.premise) : '') +
    h2('三、商务参数') +
    table(['项', '值'], [
      ['题材', (d.genre || []).join(' / ')],
      ['平台', d.platform],
      ['集数', d.episode_count],
      ['单集时长', `${d.episode_duration_sec}s`],
      ['单元规模', `${d.unit_size} 集/单元`],
      ['目标受众', d.audience],
    ]) +
    h2('四、不可触碰底线') + ul(d.hard_boundaries) +
    h2('五、变现与卡点') +
    table(['项', '值'], [
      ['模式', d.commercial?.monetization_model],
      ['卡点集', (d.commercial?.paywall_points || []).join(', ') || '—'],
      ['用户已确认', d.commercial?.confirmed_by_user ? '是' : '否'],
    ]) +
    h2('六、待确认缺口') +
    table(['ID', '问题', '状态', '建议', '责任方'],
      (d.gaps || []).map((g) => [g.id, g.question, g.status, g.proposal || g.resolution || '—', g.owner])) +
    (d.facts_source?.length ? h2('七、事实来源') + ul(d.facts_source) : ''),

  D02: (d) => BANNER(DOC_TITLE.D02, `负责人：企划合规｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、定位') + p(d.positioning) +
    h2('二、卖点矩阵') + ul(d.selling_points) +
    h2('三、节奏模型') + p(d.rhythm_model) +
    h2('四、变现路径') + p(d.monetization) +
    h2('五、风险') + ul(d.risks) +
    (d.compliance_dependency ? h2('六、合规依赖') + p(d.compliance_dependency) : ''),

  D03: (d) => BANNER(DOC_TITLE.D03, `负责人：企划合规｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、尺度口径') + p(`**${d.scale_policy}**　｜　AI 标识义务：${d.ai_disclosure}`) +
    h2('二、红线清单') +
    table(['ID', '触发', '禁止', '替代表述', '等级'],
      (d.red_lines || []).map((r) => [r.id, r.trigger, r.forbid, r.rewrite_rule, r.severity])) +
    h2('三、贬称规则（仅未成年）') +
    p(`minor_only = ${d.derogation_rule?.minor_only}；禁贬称：${(d.derogation_rule?.terms || []).join('、')}`) +
    (d.derogation_rule?.note ? p(d.derogation_rule.note) : '') +
    h2('四、名词替换表') +
    table(['原词', '替换为'], (d.word_replacements || []).map((r) => [r.from, r.to])) +
    (d.beat_risk_map?.length ? h2('五、beat 级高危锚点') + table(['beat', '风险', '处理'],
      d.beat_risk_map.map((b) => [b.beat || b.beat_id || '—', b.risk || '—', b.handling || '—'])) : '') +
    h2('六、上游优先级') + p('上游合规裁决 > 派活指令。本文件落盘后，下游只引用不重新发明。'),

  D04: (d) => BANNER(DOC_TITLE.D04, `负责人：故事架构｜版本：${d.version}｜状态：${d.status}`) +
    h2('〇、角色总表') +
    table(['ID', '姓名', '角色', '年龄', '年龄段', '身份', '未成年'],
      (d.characters || []).map((c) => [c.id, c.name, c.role, c.age, c.age_band, c.identity, c.minor ? '⚠️是' : '否'])) +
    (d.characters || []).map((c) =>
      h3(`${c.id} · ${c.name}（${c.age}岁 / ${c.age_band}）`) +
      table(['字段', '内容'], [
        ['身份', c.identity],
        ['外貌-脸', c.appearance?.face],
        ['外貌-体型', c.appearance?.body],
        ['外貌-发型', c.appearance?.hair],
        ['外貌-声线', c.appearance?.voice],
        ['外貌-标志物', (c.appearance?.markers || []).join('、')],
        ['外貌-服装', c.appearance?.costume || '—'],
        ['性格标签', (c.personality_tags || []).join('、')],
        ['欲望', c.desire], ['恐惧', c.fear], ['秘密', c.secret], ['弧光', c.arc],
        ['口头禅', c.catchphrase || '—'],
        ['参考图', c.ref_image || `无（${c.ref_image_status || '不生成参考图'}）`],
      ]) +
      (Object.keys(c.relations || {}).length ? h3('关系') + table(['对象', '关系'], Object.entries(c.relations)) : '')
    ).join('\n'),

  D05: (d) => BANNER(DOC_TITLE.D05, `负责人：故事架构｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、世界观') + obj(d.world) +
    h2('二、力量体系') + obj(d.power_system) +
    h2('三、资源') + obj(d.resources) +
    h2('四、场景') + obj(d.locations) +
    h2('五、势力') + obj(d.factions) +
    h2('六、术语收口表（唯一真源）') +
    table(['术语', '收口定义', '禁用同义写法'],
      (d.glossary || []).map((g) => [g.term, g.definition, (g.forbidden_synonyms || []).join('、') || '—'])) +
    h2('七、时间线') + obj(d.timelines) +
    (d.motifs?.length ? h2('八、视觉母题') + obj(d.motifs) : ''),

  D06: (d) => BANNER(DOC_TITLE.D06, `负责人：故事架构｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('〇、分集总表') +
    table(['集', '集名', 'beat', '时长', '情绪目标', '钩子出'],
      (d.episodes || []).map((e) => [`ep${String(e.ep).padStart(3, '0')}`, e.title,
        (e.beats || []).join('/'), `${e.duration_sec}s`, e.emotion_goal, e.hook_out])) +
    (d.episodes || []).map((e) =>
      h3(`ep${String(e.ep).padStart(3, '0')} · ${e.title}`) +
      p(`**梗概**：${e.logline}`) +
      table(['字段', '内容'], [
        ['承接（hook_in）', e.hook_in],
        ['钩子（hook_out）', e.hook_out],
        ['必须发生', (e.must_happen || []).join('；')],
        ['地点', (e.locations || []).join('、')],
        ['角色', (e.characters || []).join('、')],
        ['伏笔', e.foreshadow ? `埋 ${e.foreshadow.plant || '—'} / 收 ${e.foreshadow.payoff || '—'}` : '—'],
      ])
    ).join('\n'),

  D07: (d) => BANNER(DOC_TITLE.D07, `负责人：故事架构｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    (d.episodes || []).map((e) =>
      h2(`ep${String(e.ep).padStart(3, '0')} · 故事时间：${e.story_time}`) +
      table(['字段', '内容'], [
        ['在场角色', (e.present_characters || []).map((c) => `${c.char_id}（${c.role}${c.minor ? '｜未成年' : ''}）`).join('、')],
        ['承接', e.carry_over],
        ['回答', e.answer],
        ['必须发生', (e.must_happen || []).join('；')],
        ['**代价**', e.cost],
        ['情绪目标', e.emotion_goal],
        ['时长合计', `${e.duration_sum_sec}s`],
      ]) +
      h3('场景与时长') +
      table(['场景码', '地点', '时间', '时长'],
        (e.scenes || []).map((s) => [s.code, s.location, s.time, `${s.duration_sec}s`])) +
      h3('四段制（45s 固定 4 段，边界连续）') +
      table(['段', '名称', '区间', '模式', '说明'],
        (e.quad_segments || []).map((s) => [s.index, s.name, `${s.start_sec}~${s.end_sec}s`, s.mode, s.note || '—'])) +
      (e.scene_needs?.length ? h3('场景需求（给白模）') + obj(e.scene_needs) : '') +
      (e.open_questions?.length ? h3('开放问题') + obj(e.open_questions) : '')
    ).join('\n'),

  D08: (d) => BANNER(DOC_TITLE.D08, `负责人：台本编剧｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('〇、合规逐条销账（对 D03 R 清单）') +
    p('本表由 D03 `red_lines` 与本单元 `compliance_notes` 自动对照生成：**「本单元落地」列有内容＝已销账**；为空＝本单元未触发该条，**不等于漏项**，但需在审读时确认。') +
    table(['R 编号', '触发', '禁止', '替代表述', '本单元落地（compliance_notes）', '销账'],
      (SHARED.D03?.red_lines || []).map((r) => {
        const notes = (d.episodes || []).flatMap((e) =>
          (e.compliance_notes || []).filter((n) => ruleIdsIn(n).includes(r.id)));
        const uniq = [...new Set(notes)];
        return [r.id, r.trigger || '—', r.forbid || '—', r.rewrite_rule || '—',
          uniq.length ? ul(uniq).trim() : '—', uniq.length ? '✅ 已销账' : '⚪ 未触发'];
      })) +
    (d.episodes || []).map((e) =>
      h2(`ep${String(e.ep).padStart(3, '0')} · ${e.title}`) +
      table(['项', '内容'], [
        ['时长', `${e.duration_sec}s`],
        ['场景标题', e.scene_heading],
        ['在场角色', (e.present_characters || []).join('、')],
        ['字数（基础/合规增量/总）', `${e.word_count?.base}/${e.word_count?.compliance_add}/${e.word_count?.total}`],
      ]) +
      h3('正文') +
      table(['类型', '角色', '内容', '情绪', '音效', '镜头意图（交 D11 反查）', '合规增量'],
        (e.body || []).map((b) => [
          b.type, b.char_id || '—', b.text, b.emotion || '—', b.sfx || '—',
          b.shot_intent || '—',
          b.compliance_added ? `✅ ${b.compliance_reason || ''}` : '—',
        ])) +
      ((e.body || []).some((b) => b.shot_intent)
        ? h3('镜头意图清单') +
          p('每一句都是「**这一条没被镜头拍到，这集就废了**」的那件事；不含景别/焦距/机位/运镜（那些归 D10 `camera_language` 与 D11）。') +
          table(['序', '类型', '正文', '镜头意图'],
            (e.body || []).map((b, i) => ({ b, i })).filter((x) => x.b.shot_intent)
              .map((x) => [x.i + 1, x.b.type, x.b.text, x.b.shot_intent]))
        : '') +
      (e.compliance_notes?.length ? h3('合规改造要点') + ul(e.compliance_notes) : '')
    ).join('\n'),

  D09: (d) => BANNER(DOC_TITLE.D09, `负责人：台本编剧｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、逐句对白') +
    table(['集', '序', '角色', '台词', '语气', '潜台词'],
      (d.lines || []).map((l) => [`ep${String(l.ep).padStart(3, '0')}`, l.idx, l.char_id, l.text, l.tone, l.subtext || '—'])) +
    h2('二、角色语气卡') +
    (d.voice_cards || []).map((c) =>
      h3(c.char_id) +
      ul(c.tone_rules) +
      (c.catchphrases?.length ? p(`**口头禅**：${c.catchphrases.join('、')}`) : '') +
      (c.forbidden_words?.length ? p(`**禁语**：${c.forbidden_words.join('、')}`) : '')
    ).join('\n'),

  D10: (d) => BANNER(DOC_TITLE.D10, `负责人：视觉设定｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、风格分层') +
    table(['层', '口径'], [['人物（写实）', d.style?.realism_layer], ['特效/异化（风格化）', d.style?.stylization_layer]]) +
    (d.style?.aspect_ratio ? p(`画幅：${d.style.aspect_ratio}`) : '') +
    h2('二、色板') + obj(d.palette) +
    h2('三、材质') + obj(d.materials) +
    h2('四、灯光') + obj(d.lighting) +
    h2('五、镜头语言') + obj(d.camera_language) +
    h2('六、角色锚点表（V7 校验依据）') +
    table(['角色', '锚点文本', '标志物', '负向词', '参考图路由'],
      (d.character_anchors || []).map((a) => [a.char_id, a.anchor_text,
        (a.markers || []).join('、'), (a.negatives || []).join('、'), a.ref_image_route || '—'])) +
    (d.anchor_source_of_truth ? p(`锚点真源：${d.anchor_source_of_truth}`) : '') +
    h2('七、视觉母题') + obj(d.motifs) +
    h2('八、全局负向词') + ul(d.negatives) +
    h2('九、一致性规则') + ul(d.consistency_rules),

  D11: (d) => {
    const cl = SHARED.D10?.camera_language || {};
    const intentByShot = buildShotIntentByShot(buildShotIntentIndex(UNITS[d.unit]?.D08), d);
    const intentOf = (ep, shot) => shotIntentForShot(intentByShot, ep, shot);
    return BANNER(DOC_TITLE.D11, `负责人：分镜导演｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('〇、镜头语言总纲（承 D10 `camera_language`）') +
    p('**本表每镜的 `景别 / 机位 / 焦距 / 运镜` 均按下列总纲执行**；单镜若要例外，须在该镜 `note` 里写明依据与回指规则。') +
    table(['项', '口径'],
      Object.entries(cl).map(([k, v]) => [k, Array.isArray(v) ? v.join('、') : String(v)])) +
    (d.episodes || []).map((e) =>
      h2(`ep${String(e.ep).padStart(3, '0')}｜总时长 ${e.duration_sec}s｜镜位合计 ${e.duration_sum_sec}s`) +
      table(['镜号', '全局号', '场景', '景别', '机位', '焦距', '运镜', '时长', '画面（可见事实）', '台词', '音效', '剧本镜头意图', '段', '需出图', '未成年在场'],
        (e.shots || []).map((s) => [s.shot_id, s.global_shot_no, s.scene_code, s.shot_size,
          s.camera_angle, `${s.lens_mm}mm`, s.movement, `${s.duration_sec}s`, s.visual_facts,
          s.dialogue || '—', s.sfx || '—', intentOf(e.ep, s),
          s.quad_segment ?? '—',
          s.needs_image ? '✅' : '—', s.minor_present ? '⚠️' : '—'])) +
      (e.continuity?.length ? h3('连续性锚点') + obj(e.continuity) : '')
    ).join('\n');
  },

  D12: (d) => BANNER(DOC_TITLE.D12, `负责人：视觉设定｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('〇、卡片总表') +
    table(['卡号', '集', '镜', '来源', '角色', '母题'],
      (d.cards || []).map((c) => [c.card_id, `ep${String(c.ep).padStart(3, '0')}`, c.shot_id,
        c.source || '—', (c.consistency_refs?.char_ids || []).join('、'),
        (c.consistency_refs?.motifs || []).join('、')])) +
    (d.cards || []).map((c) =>
      h3(`${c.card_id}（ep${String(c.ep).padStart(3, '0')} 镜${c.shot_id}）`) +
      p(`**图像提示词**：${c.image_prompt}`) +
      (c.video_prompt ? p(`**视频提示词**：${c.video_prompt}`) : '') +
      p(`**负向词**：${(c.negatives || []).join('、')}`) +
      table(['参数', '值'], [
        ['模型', c.params?.model], ['画幅', c.params?.aspect], ['seed 策略', c.params?.seed_strategy],
        ['步数', c.params?.steps ?? '—'], ['引导', c.params?.guidance ?? '—'], ['时长', c.params?.duration_sec ?? '—'],
      ]) +
      (c.char_descriptions?.length ? p(`**角色描述（须出自 D10 锚点）**：${c.char_descriptions.join('；')}`) : '')
    ).join('\n'),

  D13: (d) => BANNER(DOC_TITLE.D13, `负责人：白模场景师｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    (d.scenes || []).map((s) =>
      h2(`${s.scene_code}（ep${String(s.ep).padStart(3, '0')}）`) +
      p(`**平面**：${s.plan}`) +
      h3('道具') + obj(s.props) +
      h3('出入点') + obj(s.entrances) +
      h3('机位') + obj(s.camera_positions) +
      h3('视线') + obj(s.sightlines) +
      h3('尺度限制') + ul(s.scale_limits) +
      (s.lighting_setup?.length ? h3('灯光布置') + obj(s.lighting_setup) : '')
    ).join('\n'),

  D14: (d) => BANNER(DOC_TITLE.D14, `负责人：白模场景师｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、逐镜交接包索引') +
    table(
      ['镜号', '集', '场次码', '时长(s)', '字符数', '预算内', '可提交'],
      (d.shots || []).map((s) => [
        `#${s.global_shot_no}`,
        `ep${s.ep}`,
        s.scene_code,
        s.duration_sec,
        s.h3_prompt?.char_count,
        String(s.h3_prompt?.within_budget),
        String(s.h3_prompt?.ready_to_submit),
      ])
    ) +
    h2('二、执行命令') +
    '```bash\n' + (d.commands || []).join('\n') + '\n```\n\n' +
    h2('三、逐镜明细') +
    (d.shots || []).map((s) =>
      h3(`ep${String(s.ep).padStart(3, '0')} 镜${s.shot_id}｜${s.scene_code}｜${s.duration_sec}s`) +
      h4('H3 prompt 校验状态') +
      table(['项', '值'], [
        ['文件', s.h3_prompt?.path],
        ['字符数', `${s.h3_prompt?.char_count} / 6500`],
        ['within_budget', String(s.h3_prompt?.within_budget)],
        ['protected_content_valid', String(s.h3_prompt?.protected_content_valid)],
        ['ready_to_submit', String(s.h3_prompt?.ready_to_submit)],
        ['交接包', s.package_path],
      ]) +
      h4('Render Contract') + obj(s.render_contract) +
      h4('Appearance') + obj(s.appearance) +
      h4('Preflight') + obj(s.preflight)
    ).join('\n') +
    h2('四、校验结果') + obj(d.check_results),

  D15: (d) => BANNER(DOC_TITLE.D15, `负责人：声音设计｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    (d.episodes || []).map((e) =>
      h2(`ep${String(e.ep).padStart(3, '0')}`) +
      h3('BGM 情绪曲线') + obj(e.bgm_curve) +
      h3('音效') + obj(e.sfx) +
      h3('拟音') + obj(e.foley) +
      (e.voice_over?.length ? h3('配音') + obj(e.voice_over) : '') +
      h3('混音规则') + ul(e.mix_notes)
    ).join('\n'),

  D16: (d) => BANNER(DOC_TITLE.D16, `负责人：分镜导演｜单元：${d.unit}｜版本：${d.version}｜状态：${d.status}`) +
    (d.episodes || []).map((e) =>
      h2(`ep${String(e.ep).padStart(3, '0')}`) +
      h3('切点') + obj(e.cuts) +
      h3('转场') + obj(e.transitions) +
      h3('字幕样式') + obj(e.subtitle_style) +
      h3('片头片尾') + obj(e.title_card) +
      h3('付费卡点') + obj(e.paywall_point)
    ).join('\n'),

  D17: (d) => BANNER(DOC_TITLE.D17, `负责人：企划合规｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、各单元产能') + obj(d.units) +
    h2('二、合计') + obj(d.totals) +
    (d.parallel_plan ? h2('三、并行计划') + obj(d.parallel_plan) : '') +
    h2('四、外包点') + obj(d.external_outsourcing),

  D18: (d) => BANNER(DOC_TITLE.D18, `负责人：企划合规｜版本：${d.version}｜状态：${d.status}`) +
    h2('一、单元检查') + obj(d.unit_checks) +
    h2('二、全局检查') + obj(d.global_checks) +
    h2('三、开放问题') + obj(d.open_issues),
};

/* ---------- 遍历渲染 ---------- */

fs.mkdirSync(OUT_ROOT, { recursive: true });
const rendered = [];

function renderOne(docId, data, outPath) {
  const fn = renderers[docId];
  if (!fn) {
    console.warn(`⚠️ 无渲染器：${docId}（跳过）`);
    return;
  }
  const md = fn(data);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, md, 'utf8');
  rendered.push({ doc: docId, path: path.relative(PROJECT, outPath), bytes: Buffer.byteLength(md) });
}

// 共享层
const sharedDir = path.join(PROJECT, 'shared');
if (fs.existsSync(sharedDir)) {
  for (const f of fs.readdirSync(sharedDir).filter((x) => x.endsWith('.json')).sort()) {
    const docId = path.basename(f, '.json');
    const data = JSON.parse(fs.readFileSync(path.join(sharedDir, f), 'utf8'));
    SHARED[docId] = data;
    renderOne(docId, data, path.join(OUT_ROOT, `${docId}.md`));
  }
}
// 单元层
const unitsRoot = path.join(PROJECT, 'units');
if (fs.existsSync(unitsRoot)) {
  const unitIds = (onlyUnit && onlyUnit !== true)
    ? [onlyUnit]
    : fs.readdirSync(unitsRoot).filter((d) => fs.statSync(path.join(unitsRoot, d)).isDirectory()).sort();
  for (const uid of unitIds) {
    const ud = path.join(unitsRoot, uid);
    if (!fs.existsSync(ud)) continue;
    UNITS[uid] = UNITS[uid] || {};
    // 先读全该单元的 JSON 缓存（供跨文档视图用），再渲染
    for (const f of fs.readdirSync(ud).filter((x) => x.endsWith('.json')).sort()) {
      const docId = path.basename(f, '.json');
      UNITS[uid][docId] = JSON.parse(fs.readFileSync(path.join(ud, f), 'utf8'));
    }
    for (const f of fs.readdirSync(ud).filter((x) => x.endsWith('.json')).sort()) {
      const docId = path.basename(f, '.json');
      renderOne(docId, UNITS[uid][docId], path.join(OUT_ROOT, 'units', uid, `${docId}.md`));
    }
  }
}

console.log(`✅ 渲染 ${rendered.length} 份 → ${path.relative(process.cwd(), OUT_ROOT)}`);
for (const r of rendered) console.log(`   ${r.doc.padEnd(4)} ${String(r.bytes).padStart(7)}B  ${r.path}`);
process.exit(0);
