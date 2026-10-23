#!/usr/bin/env node
/**
 * U01-R18 ep2#4 台词文案下游同步 —— D11 v1.7 → v1.8 ＋ D16 v1.7 → v1.8
 *
 * 背景（真源链）
 * --------------
 * 台本编剧 2026-10-23 04:25–04:45（台账 §五十三）把 U01 ep2#4 的台词缩为「**换我用了。**」，
 * 并落盘 `units/U01/D08.json` **v1.9** ＋ `units/U01/D09.json` **v1.5**（台词真源）。
 * 本岗 `units/U01/D11.json` v1.7 镜4 的 `dialogue` 与 `units/U01/D16.json` v1.7 ep2 seq9 的
 * 字幕 `text` **仍引用已被上游删除的旧文案**「两小时五十八分……换我用了。」
 * → 属「上游改台词、派生副本腐烂」（Q34：下游改写落盘后，先回刷下游再回报）。
 *
 * 改动面（**只动文本，零结构性改动**）
 * ------------------------------------
 *   D11 U01：ep2 镜4 `dialogue` ＝ 「陆沉「两小时五十八分……换我用了。」」 → 「陆沉「换我用了。」」
 *   D16 U01：ep2 seq9（type=对白）`text` ＝ 同上旧文案 → 「换我用了。」
 *   ＋ 两份的 `version`：v1.7 → v1.8
 *   ＋ D16 `subtitle_sync_audit.verified_note` **追加**一句留痕（原文不改写，只加）
 *
 * **不动**：`out_sec`（仍 43.0）、`in_sec`、`visual_facts`、镜数、镜时、`global_shot_no`、
 *   机位/景别/焦距/运镜、`scene_code`、`sfx`、其余 31 镜、其余 7 集的每一行。
 *
 * 为什么 `out_sec` 不动（不预支未落盘的事实）
 * -----------------------------------------
 * D16 ep2 seq9 的 out_sec 43.0 ＝ 配音 at_sec 41.2 ＋ D15 `voice_over[3].dur_sec` **1.8**
 * （D15 U01 现为 v1.3）。本轮**未变更 D15**，故 out_sec 43.0 与现有预算自洽。
 * §五十三 已记：新文案 4 字，实测预估 ~1.1s < 预算 1.8s → **契约成立**；
 * 「是否下调 D15 该行预算」由声音设计定 → 若下调，本岗须随方案 A 一起再调 out_sec。
 * → 本轮**不宣称**「已与新配音核对」；配音实测未回填前，out_sec 不动（Q39／Q49）。
 *
 * 用法
 * ----
 * node scripts/patch_U01R18_ep2_text_sync.mjs --check   # 只校验不写盘
 * node scripts/patch_U01R18_ep2_text_sync.mjs             # 写盘（先备份）
 */
import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const P = (p) => resolve(HERE, "..", p);
const J = (p) => JSON.parse(readFileSync(P(p), "utf8"));
const CHECK = process.argv.includes("--check");
// ── 版本号归一化（双 v 缺陷族修复，2026-10-23）──
// version 字段自带 `v`，打印模板再硬拼 `v` 即产出 `vv1.x`（同源缺陷）。
const vtag = (x) => { const s = String(x); return /^v/i.test(s) ? s : "v" + s; };



const errors = [];
const chk = (cond, msg) => { if (!cond) errors.push(msg); };

const D09 = J("units/U01/D09.json");
const D11 = J("units/U01/D11.json");
const D16 = J("units/U01/D16.json");

// ── 版本守卫（Q64 防回退，2026-10-23 补）──
// 本脚本是一次性补丁，前提是 D11 U01 ＝ v1.7 ＋ D16 U01 ＝ v1.7。
// 原实现**只有 --check（不写盘）而无版本守卫**：若在已演进盘面（如 D16 U01 现为 v1.12）
// 被误跑，会把 D16 硬写回 `v1.8` —— **版本回退**且重复追加 verified_note 留痕。
// 故加守卫：盘面版本 ≠ 前提 → `[NO-OP]` exit 0，**绝不写盘**。
// ⚠️ 位置纪律：守卫必须在 D11／D16 **加载之后**（误插在加载之前 → ReferenceError，
//    exit=1 带栈回溯 —— 那是「脚本报错」不是「守卫拒绝」，Q73 要求二者分开计数）。
const EXPECT_D11 = "v1.7";
const EXPECT_D16 = "v1.7";
if (D11.version !== EXPECT_D11 || D16.version !== EXPECT_D16) {
  console.log(`[NO-OP] 盘面版本与本脚本前提不一致：D11 U01 ${D11.version}（前提 ${EXPECT_D11}）／` +
              `D16 U01 ${D16.version}（前提 ${EXPECT_D16}）—— 本脚本为一次性 v1.7→v1.8 补丁，` +
              `已演进则不写盘（防版本回退与重复追加留痕）。`);
  process.exit(0);
}

const OLD_TEXT = "两小时五十八分……换我用了。";
const NEW_TEXT = "换我用了。";
const OLD_D11 = `陆沉「${OLD_TEXT}」`;
const NEW_D11 = `陆沉「${NEW_TEXT}」`;

// ── 1) 真源：D09 U01 ep2 第 4 条 ──
const d09line = (D09.lines || []).find((l) => l.ep === 2 && l.idx === 4);
chk(!!d09line, "D09 U01 缺 ep2 idx4");
chk(!!d09line && d09line.text === `「${NEW_TEXT}」`,
  `D09 U01 ep2#4 台词不是「${NEW_TEXT}」→ 实际：${d09line && d09line.text}`);
chk(!!d09line && d09line.char_id === "LC", "D09 U01 ep2#4 char_id 不是 LC");

// ── 2) 定位目标行，并断言旧文案命中数恰好 1（对不上即中止，不写盘）──
const e11 = D11.episodes.find((e) => e.ep === 2);
const shot4 = e11.shots.find((s) => s.shot_id === 4);
chk(!!shot4, "D11 U01 缺 ep2 镜4");
chk(shot4 && shot4.dialogue === OLD_D11,
  `D11 U01 ep2 镜4 dialogue 不是预期旧文案 → 实际：${shot4 && shot4.dialogue}`);
chk(shot4 && !shot4.visual_facts.includes(NEW_TEXT),
  "D11 U01 ep2 镜4 visual_facts 含「换我用了」——画面层不应含该句，若命中须停下复核");

const e16 = D16.episodes.find((e) => e.ep === 2);
const seq9 = e16.subtitle_style.lines.find((l) => l.seq === 9);
chk(!!seq9, "D16 U01 缺 ep2 seq9");
chk(seq9 && seq9.type === "对白", `D16 U01 ep2 seq9 type 不是「对白」→ ${seq9 && seq9.type}`);
chk(seq9 && seq9.text === OLD_TEXT,
  `D16 U01 ep2 seq9 text 不是预期旧文案 → 实际：${seq9 && seq9.text}`);

// 全库旧文案命中数（防止漏改 / 多改）
const countIn = (obj, needle) => JSON.stringify(obj).split(needle).length - 1;
chk(countIn(D11, OLD_TEXT) === 1, `D11 U01 旧文案命中 ${countIn(D11, OLD_TEXT)} 处（应恰好 1）`);
chk(countIn(D16, OLD_TEXT) === 1, `D16 U01 旧文案命中 ${countIn(D16, OLD_TEXT)} 处（应恰好 1）`);

// ── 3) 不变量快照（改前）──
const inv = (d11) => {
  const shots = d11.episodes.flatMap((e) => e.shots);
  return {
    shots: shots.length,
    per_ep: d11.episodes.map((e) => e.shots.length).join(","),
    dur_sum: d11.episodes.map((e) => e.shots.reduce((a, s) => a + s.duration_sec, 0).toFixed(1)).join(","),
    gsno: shots.map((s) => s.global_shot_no).join(","),
    geo: shots.map((s) => `${s.scene_code}|${s.shot_size}|${s.camera_angle}|${s.lens_mm}|${s.movement}`).join(";"),
  };
};
const inv11Before = inv(D11);
const inv16Before = {
  lines: D16.episodes.map((e) => e.subtitle_style.lines.length).join(","),
  cuts: D16.episodes.map((e) => e.cuts.length).join(","),
  inout: D16.episodes.map((e) => e.subtitle_style.lines.map((l) => `${l.seq}:${l.in_sec}>${l.out_sec}`).join("|")).join(";"),
  keys: D16.episodes.map((e) => Object.keys(e.subtitle_style).sort().join(",")).join(";"),
};

// ── 4) 改写（内存副本）──
const d11n = structuredClone(D11);
const d16n = structuredClone(D16);
const s11 = d11n.episodes.find((e) => e.ep === 2).shots.find((s) => s.shot_id === 4);
s11.dialogue = NEW_D11;
d11n.version = "v1.8";

const s16 = d16n.episodes.find((e) => e.ep === 2).subtitle_style.lines.find((l) => l.seq === 9);
s16.text = NEW_TEXT;
d16n.version = "v1.8";
// 审计留痕：**只追加，不改写原文**
const aud = d16n.episodes.find((e) => e.ep === 2).subtitle_style.subtitle_sync_audit;
aud.verified_note = (aud.verified_note || "") +
  " 【留痕 2026-10-23 · U01-R18 ep2#4 文案同步】本集 ep2 seq9 的台词文案已随台本编剧 D08 v1.9／D09 v1.5 改为「换我用了。」；" +
  "**out_sec 43.0 未动**（仍＝配音 at_sec 41.2 ＋ D15 v1.3 该行 dur_sec 1.8，本轮未变更 D15）；" +
  "**新配音尚未重合成 → 本条与配音的实测一致性未核（受检 0 条，不作任何余量结论）**；" +
  "若声音设计下调该行预算或实测超出 1.8s，本岗须随方案 A 再调 out_sec（届时另升版本）。";

// ── 5) 改后复核：除白名单外全库逐字段零变化 ──
const inv11After = inv(d11n);
chk(inv11After.shots === inv11Before.shots, "D11 镜数变化");
chk(inv11After.per_ep === inv11Before.per_ep, "D11 每集镜数分布变化");
chk(inv11After.dur_sum === inv11Before.dur_sum, "D11 每集镜时和变化");
chk(inv11After.gsno === inv11Before.gsno, "D11 global_shot_no 序列变化");
chk(inv11After.geo === inv11Before.geo, "D11 机位字段（scene_code/景别/角度/焦距/运镜）变化");

const inv16After = {
  lines: d16n.episodes.map((e) => e.subtitle_style.lines.length).join(","),
  cuts: d16n.episodes.map((e) => e.cuts.length).join(","),
  inout: d16n.episodes.map((e) => e.subtitle_style.lines.map((l) => `${l.seq}:${l.in_sec}>${l.out_sec}`).join("|")).join(";"),
  keys: d16n.episodes.map((e) => Object.keys(e.subtitle_style).sort().join(",")).join(";"),
};
for (const k of Object.keys(inv16Before)) {
  chk(inv16After[k] === inv16Before[k], `D16 ${k} 变化（字幕行数/切点数/时码/字段集均不应变）`);
}
// D16 逐集逐行比对：除 ep2 seq9 的 text 外，其余行逐字段全等
for (const e of D16.episodes) {
  const before = D16.episodes.find((x) => x.ep === e.ep).subtitle_style.lines;
  const after = e.subtitle_style.lines;
  for (let i = 0; i < before.length; i++) {
    const b = { ...before[i] }, a = { ...after[i] };
    if (e.ep === 2 && before[i].seq === 9) { delete b.text; delete a.text; }
    chk(JSON.stringify(a) === JSON.stringify(b),
      `D16 ep${e.ep} seq${before[i].seq} 非目标行发生变化`);
  }
  // cuts / transitions / title_card / paywall_point 全等
  const eb = D16.episodes.find((x) => x.ep === e.ep);
  for (const k of ["cuts", "transitions", "title_card", "paywall_point"]) {
    chk(JSON.stringify(e[k]) === JSON.stringify(eb[k]), `D16 ep${e.ep} ${k} 发生变化`);
  }
}
// D11 逐镜比对：除 ep2 镜4 的 dialogue 外全等
for (const e of d11n.episodes) {
  const eb = D11.episodes.find((x) => x.ep === e.ep);
  for (let i = 0; i < eb.shots.length; i++) {
    const b = { ...eb.shots[i] }, a = { ...e.shots[i] };
    if (e.ep === 2 && eb.shots[i].shot_id === 4) { delete b.dialogue; delete a.dialogue; }
    chk(JSON.stringify(a) === JSON.stringify(b), `D11 ep${e.ep} 镜${eb.shots[i].shot_id} 非目标字段发生变化`);
  }
  chk(JSON.stringify(e.quad_segment ?? null) === JSON.stringify(eb.quad_segment ?? null),
    `D11 ep${e.ep} 顶层字段变化`);
}

// ── 6) 新文案必须与 D09 真源逐字一致（收口判据）──
const nowText = d16n.episodes.find((e) => e.ep === 2).subtitle_style.lines.find((l) => l.seq === 9).text;
const nowD11 = d11n.episodes.find((e) => e.ep === 2).shots.find((s) => s.shot_id === 4).dialogue;
chk(nowText === d09line.text.replace(/[「」]/g, ""), "D16 ep2 seq9 新文案 ≠ D09 真源");
chk(nowD11 === `陆沉「${d09line.text.replace(/[「」]/g, "")}」`, "D11 ep2 镜4 新文案 ≠ D09 真源");

if (errors.length) {
  console.error(`\n❌ 中止（${errors.length} 项断言未过，不写盘）：`);
  errors.forEach((e) => console.error("   ·", e));
  process.exit(1);
}

console.log("✅ 全部断言通过：");
console.log(`   · 真源核对：D09 U01 ${vtag(D09.version)} ep2#4 ＝ 「${d09line.text}」（char_id ${d09line.char_id}）`);
console.log(`   · D11 U01 ${vtag(D11.version)} → ${vtag(d11n.version)}：ep2 镜4 dialogue 「${OLD_D11}」→「${NEW_D11}」`);
console.log(`   · D16 U01 ${vtag(D16.version)} → ${vtag(d16n.version)}：ep2 seq9（对白）text 同步；out_sec 43.0 未动（待 D15 v1.4 与新配音实测）`);
console.log(`   · 零变化复核：32 镜／每集 4 镜／每集镜时和／global_shot_no 1→32／机位字段 全部不变；D16 8 集字幕行与切点、时码、字段集全部不变`);
console.log(`   · 受检条数：旧文案命中 D11 ${countIn(D11, OLD_TEXT)} 处 ＋ D16 ${countIn(D16, OLD_TEXT)} 处（各恰好 1）→ 已全部替换为新文案`);

if (CHECK) { console.log("（--check：只校验，不写盘）"); process.exit(0); }

// 备份：**不落在交付目录**（SSOT 交付目录只应放交付物 —— 台账 §五十六 U02-R10 同源要求），
// 统一进 reports/_bak_U01_D11_D16_<本地时间戳>/，避免在 units/ 里堆备份件。
const now = new Date();
const p2 = (n) => String(n).padStart(2, "0");
const stamp = `${now.getFullYear()}${p2(now.getMonth() + 1)}${p2(now.getDate())}-${p2(now.getHours())}${p2(now.getMinutes())}${p2(now.getSeconds())}`;
const bakDir = P(`reports/_bak_U01_D11_D16_${stamp}`);
if (!CHECK) {
  if (!existsSync(bakDir)) mkdirSync(bakDir, { recursive: true });
  for (const p of ["units/U01/D11.json", "units/U01/D16.json"]) {
    const bak = resolve(bakDir, p.split("/").pop() + `.bak-${stamp}`);
    copyFileSync(P(p), bak);
    console.log(`   · 备份 → reports/_bak_U01_D11_D16_${stamp}/${p.split("/").pop()}.bak-${stamp}`);
  }
  for (const [p, obj] of [["units/U01/D11.json", d11n], ["units/U01/D16.json", d16n]]) {
    writeFileSync(P(p), JSON.stringify(obj, null, 2) + "\n", "utf8");
    console.log(`✅ 落盘：${p}  ${obj.version}`);
  }
}
