#!/usr/bin/env node
/**
 * D16 v1.6 → v1.7：U01-R15 落地（badge_avoid 统一可计算口径）＋ 版本戳校到 D15 v1.3
 *
 * 背景：
 *  ① U01-R15（企划合规 02:38 登记，低优先、不拦锁）：`subtitle_style.badge_avoid`
 *     的描述口径是**粗口径** —— ep1 写「对白字幕区（画面下 1/4）与 AI 角标区
 *     （基线 72%~78% 画面高度）不得重叠」，而「下 1/4」＝75%~100% 自顶，与角标带
 *     **字面交叠 75%~78%**（宽 3.0% 画面高），读起来像自相矛盾；
 *     ep2–ep8 则写「对白字幕区与右下角 AI 角标区不得重叠」，**过于笼统、不可计算**。
 *     本岗按同文件 `position` 与 `size` 实算：字幕基线距底 ≥15% 画面高 → 基线自顶 85%；
 *     字号「画面宽度 6%~7%」= 65~76px → 文字顶约 **81.0%~81.6%** 自顶；角标下沿 78%
 *     → 实算间距 **3.0%~3.6% 画面高**，**摆放不冲突，问题在描述不在摆放**。
 *     ⇒ 8 集统一改为**可计算口径**（不给「下 1/4」，不给无区间的笼统表述）。
 *  ② 版本戳校准：`subtitle_sync_audit.verified_against_d15` 仍戳 v1.2，而磁盘 D15 已是 v1.3
 *     （D18 Q39：数值必须带版本号，下游升版即须重跑）。本岗已按 D15 v1.3 × D16 v1.6 ×
 *     D11 v1.6 复算 108 个对象（voice_over 28 ＋ sfx/foley 80）：0 越窗 / 0 跨段间硬切、
 *     28 条对白字幕与配音逐条严格相等 ⇒ 升戳至 v1.3。
 *     **`sync_basis` 是事件溯源陈述，本轮一字不动**（S11 定的分工）。
 *
 * 纪律：按结构改 ＋ **差异白名单**（越界改动即中止不写盘）；写回后复核
 *      JSON 可解析、时码层零变化、32 镜/4 段/45s 结构不变。
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D16.json");

const NEW_BADGE_AVOID =
  "对白字幕区＝字幕文字顶以下区域（基线距底 ≥15% 画面高 → 基线自顶 85%；" +
  "字号 65~76px → 文字顶约 81%~81.6% 自顶）；AI 角标带＝72%~78% 自顶；" +
  "两区间须留 ≥2% 画面高间距（U01 实测 3.0%~3.6%）。角标在字幕行上方。";

const NEW_POSITION = "底部上移 ≥15% 画面高度（1080×1920 下字幕基线距底 ≥288px），水平居中";

const NEW_VERIFIED_NOTE =
  "本次复核所依据的 D15 版本（数值必须带版本号，判据同 D18 Q39）。" +
  "D15 v1.3 相对 v1.2 的数值区（voice_over/sfx/foley/bgm_curve）变更**未产生任何可观测差异**：" +
  "本岗按 D15 v1.3 × D16 v1.6 × D11 v1.6 复算 108 个对象（voice_over 28 ＋ sfx/foley 80）" +
  "→ 0 越出本镜时间窗 / 0 跨段间硬切、28 条对白字幕与配音 out_sec 逐条严格相等；" +
  "余量三口径 1.0s（ep1 镜1）／0.5s（ep7 镜4）／0.5s（ep7 镜4），" +
  "与企划合规 02:38 基于 v1.2 的复算结论逐项一致（v1.1→v1.2 数值区逐字节一致已有据）。" +
  "故 v1.1 事件溯源与 11 行同步结论零失效。";

const src = readFileSync(TARGET, "utf8");
const before = JSON.parse(src);

// ── 幂等守卫：一次性脚本，只在 v1.6 上执行 ──
// 2026-10-23 补：本脚本白名单含 lines / dwell_calc_convention / subtitle_sync_audit.rows 且
// after.version 硬写 v1.7 → 若在更新的版本上重跑，会把 D16 整块回退（含 U01-R18 终表 9 行）。
// 故加版本守卫：版本已演进 → no-op 退出 0，绝不写盘。
if (before.version !== "v1.6") {
  console.log(`[NO-OP] D16 当前 version=${before.version}（≠ v1.6）：`
    + `本脚本为一次性 v1.6→v1.7 收口脚本，已演进则不写盘（防整块回退）。`);
  process.exit(0);
}

// ── 差异白名单：允许被改动的字段路径 ──
const ALLOWED = new Set([
  "version",
  "episodes[].subtitle_style.badge_avoid",
  "episodes[].subtitle_style.position",
  "episodes[].subtitle_style.subtitle_sync_audit.verified_against_d15",
  "episodes[].subtitle_style.subtitle_sync_audit.verified_note",
]);

// ── 快照：用于事后比对哪些路径变了 ──
const snap = (o) => {
  const m = new Map();
  m.set("version", o.version);
  o.episodes.forEach((e) => {
    const p = `episodes[${e.ep}].subtitle_style`;
    const st = e.subtitle_style;
    m.set(`${p}.badge_avoid`, JSON.stringify(st.badge_avoid));
    m.set(`${p}.position`, JSON.stringify(st.position));
    m.set(`${p}.subtitle_sync_audit.verified_against_d15`, JSON.stringify(st.subtitle_sync_audit.verified_against_d15));
    m.set(`${p}.subtitle_sync_audit.verified_note`, JSON.stringify(st.subtitle_sync_audit.verified_note));
    m.set(`${p}.subtitle_sync_audit.sync_basis`, JSON.stringify(st.subtitle_sync_audit.sync_basis));
    // 时码层快照（必须零变化）
    m.set(`${p}.lines`, JSON.stringify(st.lines));
    m.set(`${p}.dwell_calc_convention`, JSON.stringify(st.dwell_calc_convention));
    m.set(`${p}.sync_rule`, JSON.stringify(st.sync_rule));
    m.set(`${p}.font`, JSON.stringify(st.font));
    m.set(`${p}.size`, JSON.stringify(st.size));
    m.set(`${p}.max_chars_per_line`, JSON.stringify(st.max_chars_per_line));
    m.set(`${p}.min_dwell_sec`, JSON.stringify(st.min_dwell_sec));
    m.set(`${p}.terminology_rule`, JSON.stringify(st.terminology_rule));
    m.set(`${p}.ai_badge`, JSON.stringify(st.ai_badge));
    m.set(`${p}.subtitle_sync_audit.rows`, JSON.stringify(st.subtitle_sync_audit.rows));
    m.set(`${p}.subtitle_sync_audit.synced_row_count`, JSON.stringify(st.subtitle_sync_audit.synced_row_count));
    m.set(`${p}.subtitle_sync_audit.no_vo_anchor_rows`, JSON.stringify(st.subtitle_sync_audit.no_vo_anchor_rows));
    // 切点层快照（必须零变化）
    m.set(`episodes[${e.ep}].cuts`, JSON.stringify(e.cuts));
    m.set(`episodes[${e.ep}].transitions`, JSON.stringify(e.transitions));
    m.set(`episodes[${e.ep}].title_card`, JSON.stringify(e.title_card));
    m.set(`episodes[${e.ep}].paywall_point`, JSON.stringify(e.paywall_point));
  });
  return m;
};

const snapBefore = snap(before);

// ── 改动 ──
const after = JSON.parse(src);
after.version = "v1.7";
for (const e of after.episodes) {
  const st = e.subtitle_style;
  st.badge_avoid = NEW_BADGE_AVOID;
  st.position = NEW_POSITION;
  st.subtitle_sync_audit.verified_against_d15 = "v1.3";
  st.subtitle_sync_audit.verified_note = NEW_VERIFIED_NOTE;
}

// ── 差异白名单校验：逐路径比对，命中非白名单路径即中止 ──
const snapAfter = snap(after);
const changed = [];
for (const [k, v] of snapAfter) {
  if (snapBefore.get(k) !== v) changed.push(k);
}
const norm = (k) =>
  k.replace(/^episodes\[\d+\]/, "episodes[]")
   .replace(/\.subtitle_sync_audit\.(verified_against_d15|verified_note|sync_basis|rows|synced_row_count|no_vo_anchor_rows)$/, ".subtitle_sync_audit.$1");
const offenders = changed.filter((k) => !ALLOWED.has(norm(k)));
if (offenders.length) {
  console.error(`❌ 中止：改动了白名单外字段 ${offenders.length} 处：`);
  for (const o of offenders.slice(0, 20)) console.error("   - " + o);
  process.exit(1);
}

// ── 时码层与切点层零变化硬校验 ──
for (const e of after.episodes) {
  const st = e.subtitle_style;
  for (const line of st.lines) {
    if (typeof line.in_sec !== "number" || typeof line.out_sec !== "number") {
      console.error(`❌ 中止：ep${e.ep} 字幕行时码字段异常。`);
      process.exit(1);
    }
  }
  if (!Array.isArray(e.cuts) || !Array.isArray(e.transitions)) {
    console.error(`❌ 中止：ep${e.ep} cuts/transitions 必须是数组。`);
    process.exit(1);
  }
  if (!st.subtitle_sync_audit || !st.subtitle_sync_audit.sync_basis) {
    console.error(`❌ 中止：ep${e.ep} subtitle_sync_audit.sync_basis 缺失（S11 溯源字段不得丢）。`);
    process.exit(1);
  }
}

// ── 切点计数不得变化 ──
const cnt = (o) => o.episodes.reduce((a, e) => a + e.cuts.filter((c) => c.counted_in_d17_cut_count === true).length, 0);
const tot = (o) => o.episodes.reduce((a, e) => a + e.cuts.length, 0);
if (cnt(before) !== cnt(after) || tot(before) !== tot(after)) {
  console.error("❌ 中止：切点计数发生变化。");
  process.exit(1);
}

const out = JSON.stringify(after, null, 2) + "\n";
JSON.parse(out); // 可解析

writeFileSync(TARGET, out, "utf8");

console.log(`✅ D16 v1.6 → v1.7 落盘`);
console.log(`   改动字段路径 ${changed.length} 处（全部在白名单内）：`);
for (const k of changed) console.log("     - " + k);
console.log(`   切点计数不变：计入 D17 ${cnt(after)}｜cuts 条目 ${tot(after)}`);
console.log(`   时码层 / 切点层 / title_card / paywall_point / sync_basis / rows 全部零变化`);
console.log(`   字节：${Buffer.byteLength(out, "utf8")}`);
