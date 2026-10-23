#!/usr/bin/env node
/**
 * D11 v1.6 → v1.7：ep2 镜2 的 note 跨文件引文同步（D08 v1.7 旧措辞 → v1.8 新措辞）
 *
 * 起因：台本编剧独立复核 D11 的 23 条 shot_intent 覆盖后，**自查出自己 1 条越界条款**——
 *   ep002 body[5] 正文原文仅「侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。」，
 *   而其 D08 v1.7 的 shot_intent 写了「**从焊缝成形到闸门合拢**」——
 *   「闸门合拢」这一动作**正文里并不存在**，属写 SI 时凭空添加、超出该条目正文已存在的事实。
 *   台本编剧已自行订正（D08 v1.8，新措辞「侧门焊死这一步必须被完整看见：焊缝成形的全过程
 *   要交代清楚，这道门是本集『占位』的关键。」，43 字）并登记（台账 §二十八）。
 *
 * 本岗需做的：**D11 ep2 镜2（g6）的 note 里逐字引用了旧措辞**，与 D08 v1.8 失配
 *   （失配项已由台本编剧在台账登记）。按其要求：**只改 note 引文并升版，visual_facts 一字未动**
 *   —— D11 正文兑现的「焊起简易闸门＋焊花落在卷帘门」与新措辞「焊缝成形的全过程要交代清楚」
 *   完全一致（过程性的「焊缝逐渐成形」由 D12 卡 C-006 的 video_prompt 承接）。
 *
 * ─────────────────────────────────────────────────────────────────
 * 治理改造（2026-10-23 10:2x，分镜导演岗）—— 企划合规 U02-R34 裁定
 * ─────────────────────────────────────────────────────────────────
 *   ① 变更清单 ＝ CHANGE_MANIFEST（2 条）；断言点清单 ＝ ASSERT_MANIFEST（17 条，逐条标来源）。
 *   ② 版本冻结门：盘上版本 ≠ 前提版本时一律不写盘；已执行过／已演进 → `[NO-OP]` exit 0；
 *      早于前提版本 → exit 3（前置未落，不越序执行）。`--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 *
 * 纪律：逐处带命中数断言，对不上即中止不写盘；写回后复核 JSON 可解析、
 *      **除本 note 外 D11 全库零变化**、32 镜/4 段/45s 结构不变。
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D11.json");

const FROM_V = "v1.6";
const TO_V = "v1.7";
const SCRIPT_ID = "patch_D11_v17_ep2_note_sync";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D11.json · version",
    desc: "版本号 v1.6 → v1.7",
    assert_ids: ["A01", "A04", "A05", "A15", "A16"],
  },
  {
    id: "C02",
    target: "units/U01/D11.json · ep2 镜2 note",
    desc: "note 内 D08 引文由 v1.7 旧措辞同步为 v1.8 现行措辞（visual_facts 一字未动；旧措辞在订正段保留唯一留痕引用）",
    assert_ids: ["A02", "A03", "A05", "A06", "A07", "A08", "A09", "A10", "A16"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C01", desc: "补丁 #1 版本串在源文件恰好命中 1 次" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "补丁 #2 ep2 镜2 note 旧串在源文件恰好命中 1 次" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C02", desc: "旧措辞「从焊缝成形到闸门合拢」在源文件全文恰好出现 1 次" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C01", desc: "写回内容的 version ＝ v1.7" },
  { id: "A05", phase: "pre", kind: "change", source: "变更清单 C01／C02", desc: "写回内容中 2 处新串各命中 1 次、2 处旧串各残留 0 次" },
  { id: "A06", phase: "pre", kind: "change", source: "变更清单 C02", desc: "写回内容中旧措辞残留计数 ＝ 1（即订正段内唯一留痕引用）" },
  { id: "A07", phase: "pre", kind: "change", source: "变更清单 C02", desc: "新 note 的 body[5] 引文段可解析" },
  { id: "A08", phase: "pre", kind: "change", source: "变更清单 C02", desc: "新 note 的引文主体不含旧措辞" },
  { id: "A09", phase: "pre", kind: "change", source: "变更清单 C02", desc: "新 note 逐字引用 D08 v1.8 现行措辞" },
  { id: "A10", phase: "pre", kind: "change", source: "变更清单 C02", desc: "除 ep2 镜2 的 note 外，D11 全库零字段变化（含镜键集合一致）" },
  { id: "A11", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜）", desc: "每集镜数 ＝ 4" },
  { id: "A12", phase: "pre", kind: "structure", source: "D11 模板结构约定（每集镜时 45.0s）", desc: "每集镜时求和 ＝ 45" },
  { id: "A13", phase: "pre", kind: "structure", source: "D11 模板结构约定（global_shot_no 严格递增）", desc: "global_shot_no 严格递增" },
  { id: "A14", phase: "pre", kind: "structure", source: "D11 模板结构约定（全集 32 镜）", desc: "总镜数 ＝ 32" },
  { id: "A15", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.7" },
  { id: "A16", phase: "post", kind: "change", source: "变更清单 C02", desc: "落盘后回读内容中旧措辞残留计数 ＝ 1" },
  { id: "A17", phase: "post", kind: "structure", source: "D11 模板结构约定（重新读盘独立复算）", desc: "落盘后重新读盘解析，32 镜 / 4 镜每集 / 45s 每集 / 严格递增全部成立" },
];

const OLD_NOTE =
  "本镜是 D07 段3 所述「A-2 段尾焊门收尾画面」的素材来源，与镜3 互为并行交叉剪辑配对。" +
  "28.0~40.0s 段内画面在镜3（A-3 勘察）与本镜尾料之间交替，交替点见 D16 切点表；" +
  "两镜时长按各自独占屏时间计，全集求和仍为 45.0s。" +
  "📌 D08 v1.7 shot_intent 反查（2026-10-23）：body[5] 要求「从焊缝成形到闸门合拢」的过程可见；" +
  "本镜 visual_facts 已给出该过程的起点与终点（焊起简易闸门、焊花落在卷帘门），" +
  "过程性的「焊缝逐渐成形」由 D12 卡 C-006 的 video_prompt 承接落实，D11 与 D12 口径一致，正文不改。";

const NEW_NOTE =
  "本镜是 D07 段3 所述「A-2 段尾焊门收尾画面」的素材来源，与镜3 互为并行交叉剪辑配对。" +
  "28.0~40.0s 段内画面在镜3（A-3 勘察）与本镜尾料之间交替，交替点见 D16 切点表；" +
  "两镜时长按各自独占屏时间计，全集求和仍为 45.0s。" +
  "📌 D08 shot_intent 反查（2026-10-23）：body[5] 要求「侧门焊死这一步必须被完整看见：" +
  "焊缝成形的全过程要交代清楚，这道门是本集『占位』的关键」；" +
  "本镜 visual_facts 已给出该过程（焊起简易闸门、焊花落在卷帘门），" +
  "过程性的「焊缝逐渐成形」由 D12 卡 C-006 的 video_prompt 承接落实，D11 与 D12 口径一致，正文不改。" +
  "【引文订正 2026-10-23】本条原引 D08 v1.7 措辞「从焊缝成形到闸门合拢」——" +
  "其中「闸门合拢」系该版 shot_intent **超出该条目正文已存在事实**之处" +
  "（ep002 body[5] 正文原文仅「侧门内侧焊起一道简易闸门，焊花溅在卷帘门上。」，并无「合拢」动作）；" +
  "台本编剧已自查订正并落 D08 v1.8（台账 §二十八）。本岗据此同步引文，**visual_facts 一字未动**。";

const PATCHES = [
  ['"version": "v1.6",', '"version": "v1.7",'],
  [`"note": ${JSON.stringify(OLD_NOTE)}`, `"note": ${JSON.stringify(NEW_NOTE)}`],
];

/** 补丁序号 → 断言点 id 的显式映射 */
const PATCH_ASSERT_IDS = ["A01", "A02"];

/** 旧措辞短句（订正段留痕引用的唯一合法出现位置） */
const OLD_PHRASE = "从焊缝成形到闸门合拢";
/** D08 v1.8 现行措辞（新 note 必须逐字引用） */
const NEW_PHRASE = "侧门焊死这一步必须被完整看见：焊缝成形的全过程要交代清楚";

const G = createGuard({
  scriptId: SCRIPT_ID,
  targetPath: TARGET,
  fromVersion: FROM_V,
  toVersion: TO_V,
  changeManifest: CHANGE_MANIFEST,
  assertManifest: ASSERT_MANIFEST,
});

// ── 版本冻结门 ──
G.freeze();

const src = readFileSync(TARGET, "utf8");

// ── 断言阶段：逐处命中数 ──
for (let i = 0; i < PATCHES.length; i += 1) {
  const oldStr = PATCHES[i][0];
  const count = src.split(oldStr).length - 1;
  G.assertPoint(
    PATCH_ASSERT_IDS[i],
    count === 1,
    `补丁 #${i + 1} 命中 ${count} 次（应为 1）。旧串前 90 字：${oldStr.slice(0, 90)}`,
  );
}

// ── 写回前：确认全库只有这一处引用旧措辞 ──
const srcOldPhraseCount = (src.match(new RegExp(OLD_PHRASE, "g")) || []).length;
G.assertPoint("A03", srcOldPhraseCount === 1, `旧措辞「${OLD_PHRASE}」在 D11 全文出现 ${srcOldPhraseCount} 次（应为 1）`);

// ── 写回 ──
let out = src;
for (const [oldStr, newStr] of PATCHES) out = out.replace(oldStr, newStr);

const parsed = JSON.parse(out);
G.assertPoint("A04", parsed.version === TO_V, `写回后 version ＝ ${parsed.version}（应为 ${TO_V}）`);

const residue = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const [oldStr, newStr] = PATCHES[i];
  if (out.split(oldStr).length - 1 !== 0) residue.push(`补丁 #${i + 1} 旧串仍有残留`);
  if (out.split(newStr).length - 1 !== 1) residue.push(`补丁 #${i + 1} 新串命中数异常`);
}
G.assertPoint("A05", residue.length === 0, residue.join("；"));

// ── 旧措辞的**留痕引用**（说明「原本是什么」）是新 note 的有意设计，不算残留；
//    真正要禁的是：旧措辞不得再出现在**作为 D08 现行措辞的引文主体**中。
const outOldPhraseCount = (out.match(new RegExp(OLD_PHRASE, "g")) || []).length;
G.assertPoint("A06", outOldPhraseCount === 1, `写回后旧措辞残留计数 ${outOldPhraseCount}（应为 1，即订正段内唯一留痕）`);

const quoteMatch = NEW_NOTE.match(/body\[5\] 要求「([^」]*)」/);
G.assertPoint("A07", !!quoteMatch, "新 note 未找到 body[5] 引文段");
G.assertPoint("A08", !!quoteMatch && !quoteMatch[1].includes(OLD_PHRASE), `引文主体仍含旧措辞「${OLD_PHRASE}」`);
G.assertPoint("A09", NEW_NOTE.includes(NEW_PHRASE), "新 note 未逐字引用 D08 v1.8 现行措辞");

// ── 除该 note 外零变化核验：逐镜比对 visual_facts / dialogue / sfx / 其余字段 ──
const before = JSON.parse(src);
const bMap = new Map();
const aMap = new Map();
for (const e of before.episodes) for (const s of e.shots) bMap.set(`${e.ep}#${s.shot_id}`, s);
for (const e of parsed.episodes) for (const s of e.shots) aMap.set(`${e.ep}#${s.shot_id}`, s);
const diffs = [];
for (const k of bMap.keys()) if (!aMap.has(k)) diffs.push(`写回后缺失镜位 ${k}`);
for (const k of aMap.keys()) if (!bMap.has(k)) diffs.push(`写回后多出镜位 ${k}`);
for (const [k, b] of bMap) {
  const a = aMap.get(k);
  if (!a) continue;
  const bKeys = Object.keys(b).sort();
  const aKeys = Object.keys(a).sort();
  if (bKeys.join("|") !== aKeys.join("|")) diffs.push(`${k} 字段集合不一致`);
  for (const f of bKeys) {
    if (f === "note") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) diffs.push(`${k}.${f}`);
  }
  if (k === "2#2") continue;
  if (JSON.stringify(b.note) !== JSON.stringify(a.note)) diffs.push(`${k}.note`);
}
G.assertPoint("A10", diffs.length === 0, `除 ep2 镜2 的 note 外还有字段变化：${diffs.join(", ")}`);

// ── 结构复核（写盘前，四类问题各自独立收集，互不串台）──
const countIssues = [];
const sumIssues = [];
const incIssues = [];
const totalIssues = [];
let total = 0;
let prev = 0;
for (const e of parsed.episodes) {
  const sum = e.shots.reduce((a, s) => a + s.duration_sec, 0);
  if (sum !== 45) sumIssues.push(`ep${e.ep} 镜时求和 ${sum} ≠ 45`);
  if (e.shots.length !== 4) countIssues.push(`ep${e.ep} 镜数 ${e.shots.length} ≠ 4`);
  for (const s of e.shots) {
    if (s.global_shot_no <= prev) incIssues.push(`global_shot_no 非严格递增（${s.global_shot_no}）`);
    prev = s.global_shot_no;
    total += 1;
  }
}
if (total !== 32) totalIssues.push(`总镜数 ${total} ≠ 32`);
G.assertPoint("A11", countIssues.length === 0, countIssues.join("；"));
G.assertPoint("A12", sumIssues.length === 0, sumIssues.join("；"));
G.assertPoint("A13", incIssues.length === 0, incIssues.join("；"));
G.assertPoint("A14", totalIssues.length === 0, totalIssues.join("；"));

// ── 写盘前收口 ──
G.finishPre();

writeFileSync(TARGET, out, "utf8");

// ── 写后回读 ──
const back = readFileSync(TARGET, "utf8");
const backParsed = JSON.parse(back);
G.assertPoint("A15", backParsed.version === TO_V, `回读 version ＝ ${backParsed.version}（应为 ${TO_V}）`);

const backOldPhraseCount = (back.match(new RegExp(OLD_PHRASE, "g")) || []).length;
G.assertPoint("A16", backOldPhraseCount === 1, `回读后旧措辞残留计数 ${backOldPhraseCount}（应为 1）`);

const backIssues = [];
let backTotal = 0;
let backPrev = 0;
for (const e of backParsed.episodes) {
  const sum = e.shots.reduce((a, s) => a + s.duration_sec, 0);
  if (sum !== 45) backIssues.push(`ep${e.ep} 镜时求和 ${sum} ≠ 45`);
  if (e.shots.length !== 4) backIssues.push(`ep${e.ep} 镜数 ${e.shots.length} ≠ 4`);
  for (const s of e.shots) {
    if (s.global_shot_no <= backPrev) backIssues.push(`global_shot_no 非严格递增（${s.global_shot_no}）`);
    backPrev = s.global_shot_no;
    backTotal += 1;
  }
}
if (backTotal !== 32) backIssues.push(`总镜数 ${backTotal} ≠ 32`);
G.assertPoint("A17", backIssues.length === 0, backIssues.join("；"));

G.finishPost();

const s22 = backParsed.episodes.find((e) => e.ep === 2).shots.find((s) => s.shot_id === 2);
console.log(`✅ D11 ${FROM_V} → ${TO_V} 落盘：1 处 note 引文同步 ＋ 版本号；其余 31 镜与 ep2 镜2 的其余字段全部零变化。`);
console.log(`   结构复核：32 镜 / 每集 4 镜 / 每集镜时 45.0s / global_shot_no 1→${backPrev} 全部通过。`);
console.log(`   新 note：${s22.note}`);
console.log(`   字节：${Buffer.byteLength(back, "utf8")}`);
console.log(`   变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条（写盘前 ${ASSERT_MANIFEST.filter((a) => a.phase === "pre").length} 条 ＋ 写后 ${ASSERT_MANIFEST.filter((a) => a.phase === "post").length} 条），实际登记 ${ASSERT_MANIFEST.length} 处，双射成立。`);
