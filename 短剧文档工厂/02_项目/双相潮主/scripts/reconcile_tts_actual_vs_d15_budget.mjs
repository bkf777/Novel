#!/usr/bin/env node
/**
 * D15 预算 vs 实测 TTS 时长 —— 独立复算 ＋ **方案 A 模拟**
 *
 * 背景：声音设计 §四十五 实测 U01 预演音频（120 条，其中对白 28 条），
 *      报「**10/28 条实证打破字幕—配音契约**」，并提请方案 A：
 *      「把 10 条 D15 预算上调到实测标称值，**并由分镜导演同步 D16 对应 10 行 out_sec**」，
 *      声称「新增越窗 0、跨切点 0、与下一句起音重叠 0」。
 *      D16 是本岗产物，故本岗**独立复算**：实测值自己 ffprobe 取，不采信他岗报告。
 *
 * 【区间口径 · 2026-10-23 修 U01-R19 写死】
 *   全部区间判定一律取 **左闭右开 [in, out)** —— 即 **相接不算重叠**：
 *   本行 out == 下一行 in 属「恰好相接」，不判冲突；只有 out > 下一行 in 才判重叠。
 *   本口径与 D18 Q51 裁决一致，与 `scripts/apply_d15_d16_sync.py` 同步（该脚本原用 `>=`，
 *   会把「相接」误判为重叠，已一并订正为 `>` —— 同一条数据此前能被算成两个结论）。
 *
 * 【判据定义】（与 §四十五 同口径，便于逐项对照；数值一律带口径名）
 *  预算     = D15 voice_over[].dur_sec（标称 0.1s 网格）
 *  契约上限 = 配音 at_sec + 预算（＝ D16 对白字幕 out_sec）
 *  实测     = **ffprobe format=duration**（只信实测，不信 items.json 的 dur 缓存字段）
 *  归一     = ceil(actual × 10) / 10（0.1s 标称网格**向上**取整；浮点尾差不作不合格依据）
 *  破坏     = 实测标称 > 预算；贴边 = 实测标称 == 预算；合规 = 实测标称 < 预算
 *  字幕提前 = 实际配音止 − 字幕出点（>0 表示字幕在配音说完前消失）
 *
 *  【方案 A 模拟】把 D15 预算与 D16 out_sec 同步改为「实测标称」后，检查：
 *   A1 新 out_sec 是否越出所属镜位时间窗
 *   A2 新 out_sec 是否跨 D16 段间硬切点
 *   A3 新 out_sec 是否与**下一条正文行**（对白／字幕／面板文字）起音重叠
 *      —— **候选集＝全部正文行**（排除 片头／片尾／角标），按 in_sec 排序（U01-R19 修）；
 *      **片尾标题卡单独检查**（其 position 为「底部字幕区，叠在最后一镜末段上」，与对白同带）；
 *   A4 新字幕停留是否仍 ≥1.2s（D16 min_dwell_sec 下限）
 *
 * 只读脚本：不写任何文件。
 */
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

// ══ 判据清单 ＋ 清单守卫（Q56② · U01-R33 · 企划合规 07:45 派单）════════════════
//   与同单元的 `reconcile_D15_D16_timing.mjs` 同构：**不新建构建脚本**（S23 追加子句），
//   守卫直接落在**只读对账脚本**内。
//   ① **每条判据必须标注来源** —— 禁复制无来源条目（当初 U01 那条关没被 U02 继承即此根因）。
//   ② **清单条数必须 == 实际断言点数** —— 删一条断言即中止（exit 2），杜绝「判据被无声删改」。
//   ③ 本脚本**只读、不写任何文件**（见文件头）→ Q64「写盘脚本须带版本守卫」**不适用**
//      （本单无落盘脚本）；其防的「旧口径静默回退」风险，在本形态下由**本清单守卫**承担。
//   ⚠️ 断言函数名**不得出现在本文件注释／字符串字面**（清单守卫按 token 计数，见下）。
const ASSERT_MANIFEST = [
  { id: "T1", criterion: "映射完整：items↔字幕↔配音 三向映射无失败项（未匹配＝0）", source: "台账 §四十五（声音设计实测）／U01-R19" },
  { id: "T2", criterion: "每条对白字幕行**有且仅有一条**归属路径（已实测／旧音频／未匹配），四类计数之和 == 对白字幕总数", source: "U01-R19（ep2#4 旧音频待重合成：不算映射失败、也不计入合规）" },
  { id: "T3", criterion: "实测时长取 ffprobe format=duration（不信 items.json 的 dur 缓存字段），实测值逐行可算", source: "台账 §四十五「只信实测，不信 items.json 的 dur 缓存字段」" },
  { id: "T4", criterion: "归一＝ceil(actual×10)/10（0.1s 标称网格**向上**取整），逐行可复算", source: "D18 S22（浮点尾差不作不合格依据）" },
  { id: "T5", criterion: "破坏＋贴边＋合规 三分**互斥且完备**地覆盖全部实测行", source: "台账 §四十五 判据定义（破坏＝实测标称>预算；贴边＝==；合规＝<）" },
  { id: "A1", criterion: "方案 A 模拟：新 out_sec 不越出所属镜位时间窗", source: "U01-R19 方案 A 模拟四判据" },
  { id: "A2", criterion: "方案 A 模拟：新 out_sec 不跨 D16 段间硬切点", source: "U01-R19 方案 A 模拟四判据" },
  { id: "A3a", criterion: "方案 A 模拟：新 out_sec 不与**下一条正文行**起音重叠（候选集＝全部正文行，排除片头／片尾／角标）", source: "U01-R19 修（候选集口径）" },
  { id: "A3b", criterion: "方案 A 模拟：新 out_sec 不与**下一条配音**起音重叠（声音层，独立于字幕行）", source: "台账 §四十五" },
  { id: "A3c", criterion: "方案 A 模拟：新 out_sec 不与**片尾标题卡**冲突（片尾与对白同在底部字幕区）", source: "U01-R19 修（片尾此前从未进入检查视野）" },
  { id: "A4", criterion: "方案 A 模拟：新字幕停留仍 ≥1.2s（D16 min_dwell_sec 下限）", source: "D16 min_dwell_sec＝1.2（D18 S22 网格口径）" },
  { id: "X1", criterion: "区间口径＝左闭右开 [in, out)：**恰好相接不算重叠**", source: "D18 Q51 裁决（与 apply_d15_d16_sync.py 同步订正为 > ）" },
];

const assertFails = [];
const assertLog = [];   // 每条判据的实测结论（通过与否 ＋ 受检数值），供逐条审计
const chk = (ok, id, msg) => { assertLog.push({ id, ok, msg }); if (!ok) assertFails.push(`[${id}] ${msg}`); };

function assert_manifest_guard() {
  // 计数刻意避开在源码里出现连续的断言函数名（用拼接），否则本函数自己会被数进去。
  const src = readFileSync(fileURLToPath(import.meta.url), "utf8");
  const token = "ch" + "k(";
  // 【Q74】计数前必须**剔除注释** —— 否则「把一条判据注释掉」这一最常见的
  //   静默删改手法不会改变 token 计数，守卫会继续谎报「清单 N 条 ＝ 实际断言点
  //   N 处」而该判据实际已死（Q67：恒真判据零信息量；Q56③ 的本意即防无声删改）。
  //   实测（沙箱）：删整行 → 守卫 exit 2；注释掉该行 → 旧实现**未察觉**仍放行。
  //   注：`hardFail` 独立于断言清单计算，故真实违规仍会被 exit 1 拦下，
  //   本条修的是**可审计性**（守卫不再谎报在跑的断言点条数），不是放行缺口。
  //   安全前提：脚本内无字符串字面含行注释分隔符（已实测），故按行截断安全。
  //   ⚠️ 分隔符用 charCode 构造，源码里不写字面块注释起始符（避免自指，见补丁脚本头）。
  const SL = String.fromCharCode(47, 42);
  const SR = String.fromCharCode(42, 47);
  const blockRe = new RegExp(SL.replace("*", "\\*") + "[\\s\\S]*?" + SR.replace("*", "\\*"), "g");
  const noBlock = src.replace(blockRe, (m) => m.replace(/[^\n]/g, " "));
  const codeOnly = noBlock
    .split("\n")
    .map((ln) => { const i = ln.indexOf("//"); return i >= 0 ? ln.slice(0, i) : ln; })
    .join("\n");
  const nCall = codeOnly.split(token).length - 1;
  const nDecl = ASSERT_MANIFEST.length;
  if (nCall !== nDecl) {
    console.error(`❌ 中止：判据清单 ${nDecl} 条 ≠ 实际断言点 ${nCall} 处 —— `
      + `Q56：新增/删除判据必须同步更新 ASSERT_MANIFEST（禁「跑到什么才算什么」）。`);
    process.exit(2);
  }
  return [nDecl, nCall];
}
const [nManifest, nAssertPoints] = assert_manifest_guard();

// 逐条判据的审计回执：**已评估条数**与清单条数一并打印（Q49：受检 0 条不成立）。
function reportAsserts() {
  console.log("");
  console.log(`── 判据清单断言（Q56② · U01-R33）：清单 ${nManifest} 条 ＝ 实际断言点 ${nAssertPoints} 处`
    + `｜已评估 ${assertLog.length} 条｜不通过 ${assertFails.length} 条`);
  for (const r of assertLog) console.log(`   ${r.ok ? "✅" : "❌"} ${r.id}　${r.msg}`);
}

const HERE = dirname(fileURLToPath(import.meta.url));
const P = (p) => resolve(HERE, "..", p);
const J = (p) => JSON.parse(readFileSync(P(p), "utf8"));

const D11 = J("units/U01/D11.json");
const D15 = J("units/U01/D15.json");
const D16 = J("units/U01/D16.json");
const ITEMS = J("preview/U01_tts/items.json");

const R = (n) => Math.round(n * 10) / 10;
const CEIL10 = (n) => Math.ceil(n * 10 - 1e-9) / 10;

// ── 区间口径（左闭右开 [in, out)）：**相接不算重叠** ──
//   全脚本**只有这一个判定函数** —— 字幕行／配音／片尾三处重叠判定都走它。
//   收敛成单一函数，X1 的边界探针才能真正验到生产代码路径
//   （若判定散落各处，探针只能验一份与生产无关的副本 → 恒真、零信息量）。
const overlaps = (outSec, nextIn) => outSec > nextIn + 1e-9;

// ── 镜位时间窗（D11 累加；四段制） ──
const windows = {};
for (const e of D11.episodes) {
  let t = 0;
  windows[e.ep] = e.shots.map((s) => { const w = { shot_id: s.shot_id, start: t, end: t + s.duration_sec }; t += s.duration_sec; return w; });
}
const winOf = (ep, sid) => windows[ep].find((w) => w.shot_id === sid);

// ── D16 段间硬切点（counted_in_d17_cut_count=true；段内并行交替点不算段间切点） ──
const hardCuts = {};
for (const e of D16.episodes) {
  hardCuts[e.ep] = e.cuts.filter((c) => c.counted_in_d17_cut_count === true).map((c) => c.at_sec).sort((a, b) => a - b);
}

// ── D16 字幕行全集（U01-R19 修）：正文行（排除 片头／片尾／角标）＋ 片尾标题卡 ──
//   A3 的重叠候选集必须是**全部正文行**，不能只取「对白」——
//   否则「字幕」「面板文字」行被漏检，片尾标题卡也进不了检查视野，
//   「零破口」结论对含片尾／面板文字／字幕的行不可信。
const BODY_EXCLUDE = new Set(["片头", "片尾", "角标"]);
const bodyRows = {};   // ep → 正文行（按 in_sec 升序）
const tailCards = {};  // ep → 片尾标题卡行
for (const e of D16.episodes) {
  const all = e.subtitle_style.lines || [];
  bodyRows[e.ep] = all.filter((l) => !BODY_EXCLUDE.has(l.type)).sort((a, b) => a.in_sec - b.in_sec);
  tailCards[e.ep] = all.filter((l) => l.type === "片尾");
}

// ── 三向映射：items(dialogue) ↔ D16 对白字幕 ↔ D15 配音 ──
const norm = (s) => String(s || "").replace(/[「」“”]/g, "").trim();

// ── 已标注「旧音频待出片阶段重合成」的条目（items.json 内 stale_audio=true） ──
//   这些条目是**旧台词版本**的音频：上游（企划合规 U01-R18 终表）已把台词压缩为新句，
//   但资产重合成属出片阶段动作、**不在本岗边界内**（不合成 TTS/BGM）。
//   故它们**不算映射失败**，但也**不得混入「合规」统计** —— 单独登记、受检条数随行。
//   判据：items 条目的 `stale_new_text`（新句）与字幕行文本归一化后相等。
const staleByNewText = new Map();
for (const it of ITEMS) {
  if (it.kind === "dialogue" && it.stale_audio) {
    staleByNewText.set(`${it.ep}||${norm(it.stale_new_text)}`, it);
  }
}

const rows = [];
const unmatched = { items: [], sub: [], vo: [], stale: [] };
let ffprobeOk = 0;   // ffprobe 成功取到实测时长的行数（T3 判据的实测依据，不靠"看起来跑了"）

for (const e of D16.episodes) {
  const subs = e.subtitle_style.lines.filter((l) => l.type === "对白");
  const vos = D15.episodes.find((x) => x.ep === e.ep).voice_over;
  for (const sub of subs) {
    const vo = vos.find((v) => Math.abs(v.at_sec - sub.in_sec) < 1e-6 && v.char_id === sub.char_id);
    if (!vo) { unmatched.sub.push(`ep${e.ep} seq${sub.seq}`); continue; }
    const it = ITEMS.find((i) => i.kind === "dialogue" && i.ep === e.ep && norm(i.text) === norm(sub.text));
    if (!it) {
      const stale = staleByNewText.get(`${e.ep}||${norm(sub.text)}`);
      if (stale) {
        unmatched.stale.push({
          ep: e.ep, seq: sub.seq, text: sub.text,
          stale_item_id: stale.id, stale_old_text: stale.text,
          stale_reason: stale.stale_reason, stale_upstream: stale.stale_upstream,
          stale_action: stale.stale_action,
        });
        continue;
      }
      unmatched.items.push(`ep${e.ep} seq${sub.seq}「${sub.text}」`);
      continue;
    }
    // ffprobe 实测
    let actual = null;
    try {
      const out = execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", it.audio], { encoding: "utf8" }).trim();
      actual = parseFloat(out);
    } catch (err) {
      console.error(`❌ ffprobe 失败：${it.audio}`);
      process.exit(1);
    }
    ffprobeOk += 1;
    rows.push({
      ep: e.ep, seq: sub.seq, char: sub.char_id, text: sub.text,
      shot: sub.shot_id, at: vo.at_sec, budget: vo.dur_sec,
      subIn: sub.in_sec, subOut: sub.out_sec,
      itemsDur: it.dur, actual, actualNominal: CEIL10(actual),
      audio: it.audio.replace(/^.*preview/, "preview"),
    });
  }
}
const voTotal = D15.episodes.reduce((a, e) => a + e.voice_over.length, 0);

// ── 判据断言 T1／T2（**必须在下方「映射失败即中止」之前求值**）──
//   T1 三向映射无失败项；T2 每条对白字幕行**有且仅有一条**归属路径，四类计数之和 == 对白字幕总数。
//   为什么放前面：若放在中止点之后，映射一旦失败，这两条判据就**永远得不到评估**
//   → 受检条数会随数据漂移，判据等于形同虚设。
//   四类归属路径：① 已实测（rows）② 旧音频待重合成（stale）③ 未匹配-缺配音锚点（unmatched.sub）
//                  ④ 未匹配-无音频条目（unmatched.items）
const totalSubDialogue = D16.episodes.reduce(
  (a, e) => a + e.subtitle_style.lines.filter((l) => l.type === "对白").length, 0);
const classTotal = rows.length + unmatched.stale.length + unmatched.sub.length + unmatched.items.length;
chk(unmatched.items.length === 0 && unmatched.sub.length === 0,
    "T1", `三向映射失败项：items ${unmatched.items.length} 条 / 字幕 ${unmatched.sub.length} 条`);
chk(classTotal === totalSubDialogue,
    "T2", `归属四类计数之和 ${classTotal}（已实测 ${rows.length} / 旧音频 ${unmatched.stale.length} / 未匹配-缺配音 ${unmatched.sub.length} / 未匹配-无音频条目 ${unmatched.items.length}）＝ 对白字幕总数 ${totalSubDialogue}`);

if (unmatched.items.length || unmatched.sub.length) {
  console.error(`❌ 映射失败：items ${unmatched.items.length} 条 / 字幕 ${unmatched.sub.length} 条`);
  unmatched.items.forEach((x) => console.error("   - " + x));
  reportAsserts();
  process.exit(1);
}

const broken = rows.filter((r) => r.actualNominal > r.budget + 1e-9);
const edge = rows.filter((r) => Math.abs(r.actualNominal - r.budget) < 1e-9);
const ok = rows.filter((r) => r.actualNominal < r.budget - 1e-9);

// ── 判据断言 T3／T4／T5（实测取值、归一算法、三分完备性）──
//   T3 实测取 ffprobe format=duration（不信 items.json 的 dur 缓存字段），逐行可算；
//   T4 归一＝ceil(actual×10)/10（向上取整），逐行可复算；
//   T5 破坏＋贴边＋合规 三分互斥且完备。
const durMismatch = rows.filter((r) => Math.abs(r.itemsDur - r.actual) > 0.01).length;
const brokenSet = new Set(broken), edgeSet = new Set(edge), okSet = new Set(ok);
const classSum = broken.length + edge.length + ok.length;
const classNotOne = rows.filter((r) =>
  Number(brokenSet.has(r)) + Number(edgeSet.has(r)) + Number(okSet.has(r)) !== 1).length;
const t4Mismatch = rows.filter((r) => {
  const expect = Math.ceil(r.actual * 10 - 1e-9) / 10;
  const onGrid = Math.abs(r.actualNominal * 10 - Math.round(r.actualNominal * 10)) < 1e-9;
  return Math.abs(r.actualNominal - expect) > 1e-12 || !onGrid || r.actualNominal < r.actual - 1e-9;
}).length;
chk(rows.length > 0 && ffprobeOk === rows.length && rows.every((r) => Number.isFinite(r.actual) && r.actual > 0),
    "T3", `实测取值：ffprobe 成功 ${ffprobeOk} / 受检 ${rows.length} 条；items.json dur 与实测不一致 ${durMismatch} 条（缓存字段不作依据）`);
chk(t4Mismatch === 0,
    "T4", `归一 ceil(actual×10)/10 逐行复算不一致 ${t4Mismatch} 条`);
chk(classSum === rows.length && classNotOne === 0,
    "T5", `破坏 ${broken.length} / 贴边 ${edge.length} / 合规 ${ok.length} ＝ 受检 ${rows.length} 条；非恰好归一类 ${classNotOne} 条`);

console.log(`版本：D11 ${D11.version}　D15 ${D15.version}　D16 ${D16.version}　（items ${ITEMS.length} 条，对白实测可核 ${rows.length} 条，D15 配音 ${voTotal} 条）`);
console.log("");
console.log("── 独立复算：实测 TTS 时长 vs D15 预算 ──");
console.log(`  契约破坏（实测标称 > 预算）：**${broken.length}** 条`);
console.log(`  贴边零余量（==）：${edge.length} 条`);
console.log(`  合规（<）：${ok.length} 条`);
console.log(`  items.json 的 dur 与 ffprobe 实测不一致：${durMismatch} 条`);
if (unmatched.stale.length) {
  console.log(`  旧音频待出片阶段重合成（**不计入合规、不算映射失败**）：**${unmatched.stale.length}** 条`);
  for (const s of unmatched.stale) {
    console.log(`     ep${s.ep} seq${s.seq}「${s.text}」← 旧句「${s.stale_old_text}」`
      + `（${s.stale_reason ?? "（无标注理由）"}；上游：${s.stale_upstream ?? "（无）"}）`);
  }
}
console.log("");
console.log("  破坏明细（字幕提前量 = 实际配音止 − 字幕出点，>0 即字幕先消失）：");
for (const r of broken) {
  const voiceEnd = r.at + r.actual;
  console.log(`    ep${r.ep} seq${r.seq} 「${r.text}」 预算 ${r.budget} → 实测 ${r.actual.toFixed(3)}(标称 ${r.actualNominal})  字幕出点 ${r.subOut}  实际配音止 ${voiceEnd.toFixed(3)}  提前 ${(voiceEnd - r.subOut).toFixed(3)}s`);
}

// ══ 方案 A 模拟：仅对「破坏项」上调预算，并同步 D16 out_sec ══
// 口径修正（自查）：方案 A **只动破坏项**（实测标称 > 预算者上调）；
// 其余条数预算不动、out_sec 保持原值 —— 若误将全部受检条按实测重算，
// 会把「实测标称 < 预算」的合规条也改短，产出伪「停留 <1.2s」（假破口）。
// ⚠️ 条数一律**现读**（Q49：受检 0 条的结论一律不成立）——
//    旧版此处硬编码「10 条／18 条／28 条」；D15 升至 v1.4 后破坏项已归零，硬编码会与实况脱节。
console.log("");
console.log(`── 方案 A 模拟（**仅 ${broken.length} 条破坏项**上调预算并同步 out_sec；其余 ${rows.length - broken.length} 条不动）──`);
const brokenKeys = new Set(broken.map((b) => `${b.ep}#${b.seq}`));
const sim = [];
for (const r of rows) {
  const isBroken = brokenKeys.has(`${r.ep}#${r.seq}`);
  const newBudget = isBroken ? r.actualNominal : r.budget;
  const newOut = isBroken ? R(r.at + newBudget) : r.subOut; // 未破坏项 out_sec 保持原值
  const w = winOf(r.ep, r.shot);
  const over = newOut > w.end + 1e-9;
  const crossed = hardCuts[r.ep].filter((c) => r.at < c - 1e-9 && c < newOut - 1e-9);
  const dwell = R(newOut - r.subIn);
  const dwellOK = dwell >= 1.2 - 1e-9;
  // 与下一条**正文行**起音的重叠
  //   候选集＝全部正文行（对白／字幕／面板文字；排除 片头／片尾／角标），按 in_sec 排序（U01-R19 修）
  //   区间口径＝左闭右开 [in, out)：相接（out == 下一行 in）不算重叠
  const nextBody = bodyRows[r.ep]
    .filter((x) => x.seq !== r.seq && x.in_sec >= r.subIn - 1e-9)
    .sort((a, b) => a.in_sec - b.in_sec)[0];
  const overlapSub = nextBody ? overlaps(newOut, nextBody.in_sec) : false;
  // 与下一条配音起音的重叠（声音层，独立于字幕行）
  const vosNext = D15.episodes.find((x) => x.ep === r.ep).voice_over
    .filter((v) => v.at_sec > r.at + 1e-9).sort((a, b) => a.at_sec - b.at_sec)[0];
  const overlapVo = vosNext ? overlaps(newOut, vosNext.at_sec) : false;
  // 与**片尾标题卡**的冲突（单独检查）
  //   片尾 position ＝「底部字幕区（画面高度 80%~90%），叠在最后一镜末段上」→ 与对白**同带**，
  //   故 newOut > 片尾.in_sec 即为真实视觉冲突（U01-R19 修：此前片尾从未进入检查视野）
  const tail = tailCards[r.ep][0];
  const overlapTail = tail ? overlaps(newOut, tail.in_sec) : false;
  sim.push({ ...r, isBroken, newBudget, newOut, over, crossed, dwell, dwellOK,
             overlapSub, overlapVo, overlapTail,
             nextAt: nextBody?.in_sec, nextSeq: nextBody?.seq, nextType: nextBody?.type,
             voNextAt: vosNext?.at_sec, tailIn: tail?.in_sec });
}
const sOver = sim.filter((s) => s.over);
const sCross = sim.filter((s) => s.crossed.length);
const sOvSub = sim.filter((s) => s.overlapSub);
const sOvVo = sim.filter((s) => s.overlapVo);
const sOvTail = sim.filter((s) => s.overlapTail);
const sDwell = sim.filter((s) => !s.dwellOK);

// ── 判据断言 A1／A2／A3a／A3b／A3c／A4／X1（方案 A 模拟 ＋ 区间口径边界）──
//   X1 的边界探针直接打在上方生产用的 overlaps() 上：相接（out == next in）须判**不重叠**，
//   超出须判重叠。若把 overlaps 改回 `>=`，探针立刻失败 → 这条判据有区分力，不是恒真。
const touchingPairs = sim.filter((s) => s.nextAt !== undefined && Math.abs(s.newOut - s.nextAt) <= 1e-9).length;
const touchingFlagged = sim.filter((s) => s.nextAt !== undefined
  && Math.abs(s.newOut - s.nextAt) <= 1e-9 && s.overlapSub).length;
chk(sOver.length === 0, "A1", `方案 A 新出点越出所属镜窗 ${sOver.length} 条`);
chk(sCross.length === 0, "A2", `方案 A 新出点跨 D16 段间硬切点 ${sCross.length} 条`);
chk(sOvSub.length === 0, "A3a", `方案 A 新出点与下一条正文行起音重叠 ${sOvSub.length} 条`);
chk(sOvVo.length === 0, "A3b", `方案 A 新出点与下一条配音起音重叠 ${sOvVo.length} 条`);
chk(sOvTail.length === 0, "A3c", `方案 A 新出点与片尾标题卡冲突 ${sOvTail.length} 条`);
chk(sDwell.length === 0, "A4", `方案 A 新字幕停留 <1.2s ${sDwell.length} 条`);
chk(overlaps(10, 10) === false && overlaps(10.0001, 10) === true && touchingFlagged === 0,
    "X1", `区间口径左闭右开：实盘相接 ${touchingPairs} 对（被误判重叠 ${touchingFlagged} 对）；边界探针 相接=不重叠／超出=重叠`);
console.log(`  A1 新 out_sec 越出镜窗：**${sOver.length}** 条`);
for (const s of sOver) console.log(`     ep${s.ep} seq${s.seq}  ${s.at}+${s.newBudget}=${s.newOut}  镜窗 ${winOf(s.ep, s.shot).start}~${winOf(s.ep, s.shot).end}`);
console.log(`  A2 新 out_sec 跨段间硬切点：**${sCross.length}** 条`);
for (const s of sCross) console.log(`     ep${s.ep} seq${s.seq}  ${s.at}~${s.newOut}  跨 ${s.crossed}`);
console.log(`  A3 新 out_sec 与下一条起音重叠：正文行 **${sOvSub.length}** 条 / 配音 **${sOvVo.length}** 条 / 片尾标题卡 **${sOvTail.length}** 条`);
for (const s of sOvSub) console.log(`     ep${s.ep} seq${s.seq} 新出点 ${s.newOut} > 下一正文行起音 ${s.nextAt}（seq${s.nextSeq}·${s.nextType}）`);
for (const s of sOvVo) console.log(`     ep${s.ep} seq${s.seq} 新出点 ${s.newOut} > 下一配音起音 ${s.voNextAt}`);
for (const s of sOvTail) console.log(`     ep${s.ep} seq${s.seq} 新出点 ${s.newOut} > 片尾标题卡 in ${s.tailIn}（同在底部字幕区＝真实视觉冲突）`);
console.log(`  A4 新字幕停留 <1.2s：**${sDwell.length}** 条`);
for (const s of sDwell) console.log(`     ep${s.ep} seq${s.seq}  ${s.subIn}~${s.newOut}  停留 ${s.dwell}s`);
// 最小间隔
const gaps = sim.filter((s) => s.nextAt !== undefined).map((s) => ({ ...s, gap: R(s.nextAt - s.newOut) })).sort((a, b) => a.gap - b.gap);
console.log(`  新出点到下一正文行起音的最小间隔：${gaps[0].gap}s（ep${gaps[0].ep} seq${gaps[0].seq}）`);
const gapsVo = sim.filter((s) => s.voNextAt !== undefined).map((s) => ({ ...s, gap: R(s.voNextAt - s.newOut) })).sort((a, b) => a.gap - b.gap);
console.log(`  新出点到下一配音起音的最小间隔：${gapsVo[0].gap}s（ep${gapsVo[0].ep} seq${gapsVo[0].seq}）`);
// 仅对破坏条目调预算时的最小间隔
const brokenGaps = sim.filter((s) => broken.some((b) => b.ep === s.ep && b.seq === s.seq) && s.nextAt !== undefined).map((s) => ({ ...s, gap: R(s.nextAt - s.newOut) })).sort((a, b) => a.gap - b.gap);
if (brokenGaps.length) console.log(`  仅 ${broken.length} 条破坏项调整后的最小间隔：${brokenGaps[0].gap}s（ep${brokenGaps[0].ep} seq${brokenGaps[0].seq}）`);

// ══ 方案 B 可行性测算：要让实测 ≤ 预算，需把 TTS 语速提到多少 ══
console.log("");
console.log("── 方案 B 测算（成片端调 TTS 语速；当前预演 speed 见 items）──");
for (const r of broken) {
  const it = ITEMS.find((i) => i.audio === r.audio.replace(/^preview/, P("preview/U01_tts").replace(/.*/, "") + "preview") || i.kind === "dialogue" && i.ep === r.ep && norm(i.text) === norm(r.text));
  const sp = it ? it.speed : null;
  const need = r.actual / r.budget;
  console.log(`    ep${r.ep} seq${r.seq} 预算 ${r.budget}s 实测 ${r.actual.toFixed(3)}s  需提速比 ${need.toFixed(3)}×  当前 speed=${sp ?? "?"}  达标 speed≈${(sp * need).toFixed(3)}`);
}

const simFail = sOver.length + sCross.length + sOvSub.length + sOvVo.length + sOvTail.length + sDwell.length;
console.log("");
console.log(simFail === 0
  ? `✅ 方案 A 模拟零破口：越窗 0 / 跨切点 0 / 重叠 0（含片尾标题卡）／停留<1.2s 0 —— ${broken.length} 条可安全同步。`
  : `❌ 方案 A 模拟检出 ${simFail} 项破口。`);
console.log(`  （A3 候选集：全部正文行 ${Object.values(bodyRows).reduce((a, b) => a + b.length, 0)} 条，排除 片头／片尾／角标；片尾标题卡 ${Object.values(tailCards).reduce((a, b) => a + b.length, 0)} 张单独检查）`);
reportAsserts();
process.exit(simFail === 0 && assertFails.length === 0 ? 0 : 1);
