#!/usr/bin/env node
/**
 * D11 v1.5 → v1.6：ep5 镜3 一处措辞精修
 *
 * 起因：v1.5 落盘后跑 scripts/check_D10_D11_alignment.mjs（D10 v1.6 × D11 全口径核查），
 * 检出 ep5 镜3 的 visual_facts 含「皮肤纹理」一词。人工判定为**真实歧义**：
 *   - 该句是**否定式**（「不显皮肤纹理」＝看不到皮肤纹理），合规意图正确；
 *   - 但 D11 的 visual_facts 是**画面事实字段**，不是渲染约束字段；
 *     「不显皮肤纹理」是约束语言，且含「皮肤纹理」这个正向词，
 *     下游（D12 视觉设定的 negatives／D14 白模）若直接取用该措辞，
 *     可能被反向解读为「可以显出一点皮肤纹理」。
 *   - 约束本身由同句后半「面部与身体表面不可辨，镜头不落到人体细节」完整承载，
 *     删掉冗余的「不显皮肤纹理」**不损失任何约束信息**。
 *
 * 处置：删除「，不显皮肤纹理」5 字，其余一字不动；版本号 v1.5 → v1.6。
 *
 * ─────────────────────────────────────────────────────────────────
 * 治理改造（2026-10-23 10:2x，分镜导演岗）—— 企划合规 U02-R34 裁定
 * ─────────────────────────────────────────────────────────────────
 *   ① 变更清单 ＝ CHANGE_MANIFEST（2 条）；断言点清单 ＝ ASSERT_MANIFEST（11 条，逐条标来源）。
 *   ② 版本冻结门：盘上版本 ≠ 前提版本时一律不写盘；已执行过／已演进 → `[NO-OP]` exit 0；
 *      早于前提版本 → exit 3（前置未落，不越序执行）。`--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 *
 * 纪律：命中数断言 ＝ 1，对不上即中止不写盘；写回后复核 JSON 可解析 + 结构不变。
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D11.json");

const FROM_V = "v1.5";
const TO_V = "v1.6";
const SCRIPT_ID = "patch_D11_v16_ep5_wording";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D11.json · version",
    desc: "版本号 v1.5 → v1.6",
    assert_ids: ["A01", "A03", "A04", "A09", "A10"],
  },
  {
    id: "C02",
    target: "units/U01/D11.json · ep5 镜3 visual_facts",
    desc: "删除约束性措辞「，不显皮肤纹理」（约束已由同句后半「面部与身体表面不可辨」承载）",
    assert_ids: ["A02", "A04", "A10"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C01", desc: "补丁 #1 版本串在源文件恰好命中 1 次" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "补丁 #2 措辞旧串在源文件恰好命中 1 次" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C01", desc: "写回内容的 version ＝ v1.6" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C01／C02", desc: "写回内容中 2 处新串各命中 1 次、2 处旧串各残留 0 次" },
  { id: "A05", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜）", desc: "每集镜数 ＝ 4" },
  { id: "A06", phase: "pre", kind: "structure", source: "D11 模板结构约定（每集镜时 45.0s）", desc: "每集镜时求和 ＝ 45" },
  { id: "A07", phase: "pre", kind: "structure", source: "D11 模板结构约定（global_shot_no 严格递增）", desc: "global_shot_no 严格递增" },
  { id: "A08", phase: "pre", kind: "structure", source: "D11 模板结构约定（全集 32 镜）", desc: "总镜数 ＝ 32" },
  { id: "A09", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.6" },
  { id: "A10", phase: "post", kind: "change", source: "变更清单 C01／C02", desc: "落盘后回读内容中 2 处新串各命中 1 次、2 处旧串各残留 0 次" },
  { id: "A11", phase: "post", kind: "structure", source: "D11 模板结构约定（重新读盘独立复算）", desc: "落盘后重新读盘解析，32 镜 / 4 镜每集 / 45s 每集 / 严格递增全部成立" },
];

const PATCHES = [
  [
    '"version": "v1.5",',
    '"version": "v1.6",',
  ],
  [
    '霜白只作轮廓上的成块色块，不显皮肤纹理；',
    '霜白只作轮廓上的成块色块；',
  ],
];

/** 补丁序号 → 断言点 id 的显式映射 */
const PATCH_ASSERT_IDS = ["A01", "A02"];

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

// ── 断言阶段 ──
for (let i = 0; i < PATCHES.length; i += 1) {
  const oldStr = PATCHES[i][0];
  const count = src.split(oldStr).length - 1;
  G.assertPoint(
    PATCH_ASSERT_IDS[i],
    count === 1,
    `补丁 #${i + 1} 命中 ${count} 次（应为 1）。未写盘。`,
  );
}

let out = src;
for (const [oldStr, newStr] of PATCHES) out = out.replace(oldStr, newStr);

const parsed = JSON.parse(out);
G.assertPoint("A03", parsed.version === TO_V, `写回后 version ＝ ${parsed.version}（应为 ${TO_V}）`);

const residue = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const [oldStr, newStr] = PATCHES[i];
  if (out.split(oldStr).length - 1 !== 0) residue.push(`补丁 #${i + 1} 旧串仍有残留`);
  if (out.split(newStr).length - 1 !== 1) residue.push(`补丁 #${i + 1} 新串命中数异常`);
}
G.assertPoint("A04", residue.length === 0, residue.join("；"));

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
G.assertPoint("A05", countIssues.length === 0, countIssues.join("；"));
G.assertPoint("A06", sumIssues.length === 0, sumIssues.join("；"));
G.assertPoint("A07", incIssues.length === 0, incIssues.join("；"));
G.assertPoint("A08", totalIssues.length === 0, totalIssues.join("；"));

// ── 写盘前收口 ──
G.finishPre();

writeFileSync(TARGET, out, "utf8");

// ── 写后回读 ──
const back = readFileSync(TARGET, "utf8");
const backParsed = JSON.parse(back);
G.assertPoint("A09", backParsed.version === TO_V, `回读 version ＝ ${backParsed.version}（应为 ${TO_V}）`);

const backResidue = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const [oldStr, newStr] = PATCHES[i];
  if (back.split(oldStr).length - 1 !== 0) backResidue.push(`补丁 #${i + 1} 旧串仍有残留`);
  if (back.split(newStr).length - 1 !== 1) backResidue.push(`补丁 #${i + 1} 新串命中数异常`);
}
G.assertPoint("A10", backResidue.length === 0, backResidue.join("；"));

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
G.assertPoint("A11", backIssues.length === 0, backIssues.join("；"));

G.finishPost();

const s53 = backParsed.episodes.find((e) => e.ep === 5).shots.find((s) => s.shot_id === 3);
console.log(`✅ D11 ${FROM_V} → ${TO_V} 落盘：${PATCHES.length} 处补丁，结构复核通过（32 镜 / 每集 4 镜 / 每集镜时 45.0s / global_shot_no 1→${backPrev}）。`);
console.log(`   ep5 镜3 新 visual_facts：${s53.visual_facts}`);
console.log(`   字节：${Buffer.byteLength(back, "utf8")}`);
console.log(`   变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条（写盘前 ${ASSERT_MANIFEST.filter((a) => a.phase === "pre").length} 条 ＋ 写后 ${ASSERT_MANIFEST.filter((a) => a.phase === "post").length} 条），实际登记 ${ASSERT_MANIFEST.length} 处，双射成立。`);
