#!/usr/bin/env node
/**
 * U01-R18 返修单②（D16 侧）· 补项 —— ep4／ep6／ep7 停留口径加注「本轮同步范围」＋ D16 v1.9 → **v1.10**
 *
 * 背景（上游派单与现状）
 * ----------------------
 * 企划合规 2026-10-23 04:45「U01-R18 返修单 ② / D16 侧」要求三件事：
 *   ① 9 行对白字幕 out_sec 按表更新；② 口径文本同步（`dwell_calc_convention` 须反映 D15 **v1.4** 的同步，
 *      **ep4/ep6/ep7 若表述仍指 v1.1 需加注本轮同步范围**；`verified_against_d15` → v1.4；
 *      `sync_basis` **追加**不覆盖；`sync_rule` 补区间口径）；③ 修 `reconcile_tts_actual_vs_d15_budget.mjs`
 *      （A3 候选集改全部正文行 ＋ 片尾标题卡单独检查 ＋ 脚本头写死区间口径）。
 *
 * **①②③ 的现况（按磁盘核销，不重做）**：
 *   ① 9 行已落，但**现值是 U01-R18 终表口径**（预算取实测 TTS 标称 **+0.1s**），
 *      与本单 04:45 所抄的 04:35 复算表（取实测标称）**每行差 +0.1s**（ep8 seq8 相同）。
 *      终表是**更晚的上游裁决** → 现值正确，**不得回退**（回退会使 8/9 行 `out_sec` ≠ D15 v1.4 `dur_sec`，
 *      判据 D 立刻失效）。本脚本以断言方式把这条锁住。
 *   ② `sync_rule`（8 集全含左闭右开 ＋ 片尾标题卡单独检查）、`verified_against_d15`＝v1.4、
 *      `sync_basis` 追加终表事件、`sync_records`（8 集各 1 条）**已全部在位**；
 *      ep1/ep2/ep3/ep5/ep8 的 `dwell_calc_convention` **已含终表注**。
 *      → **本集唯一剩余项**：ep4／ep6／ep7 的 `dwell_calc_convention` 仍止于
 *      「已随 D15 v1.1 收敛同步」＋【上游闭合戳（v1.2）】，**未加注本轮同步范围**。
 *   ③ 脚本三项修复已由 **U01-R19** 落地（头部左闭右开口径、`BODY_EXCLUDE` 全正文行、片尾标题卡单独检查）。
 *
 * 改动面（**只追加口径文本，零时码改动**）
 * ------------------------------------------
 *   `units/U01/D16.json`：ep4／ep6／ep7 三集的 `subtitle_style.dwell_calc_convention`
 *     **末尾追加**一段「【U01-R18 终表同步范围（2026-10-23）】…」；`version`：v1.9 → v1.10。
 *   **不动**：任何 `in_sec`／`out_sec`／`text`／镜数／切点／`sync_rule`／`verified_against_d15`／
 *     `sync_basis`／`sync_records`／其余 5 集的 `dwell_calc_convention`。
 *   **不改写历史留痕**（S11：事件溯源字段只追加不重写）—— v1.1 收敛事件与 v1.2 闭合戳原文保留。
 *
 * ─────────────────────────────────────────────────────────────────
 * 治理改造（2026-10-23 10:2x，分镜导演岗）—— 企划合规 U02-R34 裁定
 * ─────────────────────────────────────────────────────────────────
 *   ① 变更清单 ＝ CHANGE_MANIFEST（4 条）；断言点清单 ＝ ASSERT_MANIFEST（9 条，逐条标来源）。
 *   ② 版本冻结门（原脚本把版本守卫塞在断言桶里，**已演进时以断言失败表达** —— 正是 U02-R34 点名的问题）：
 *      盘上版本 ≠ 前提版本时一律不写盘；已执行过／已演进 → `[NO-OP]` exit 0；
 *      早于前提版本 → exit 3（前置未落，不越序执行）。`--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 *
 * 用法
 * ----
 *   node scripts/patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs --check   # 只校验不写盘
 *   node scripts/patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs             # 写盘（先备份到 reports/_bak_*）
 */

import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const P = (p) => resolve(HERE, "..", p);
const J = (p) => JSON.parse(readFileSync(P(p), "utf8"));
const CHECK = process.argv.includes("--check");

const FROM_V = "v1.9";
const TO_V = "v1.10";
const SCRIPT_ID = "patch_U01R18_ep4_ep6_ep7_sync_scope_note";
const D16_PATH = "units/U01/D16.json";
const TARGET_EPS = [4, 6, 7];       // 需加注本轮同步范围的三集
const ALREADY_EPS = [1, 2, 3, 5, 8]; // 已含终表注，不得重复追加
const MARK = "【U01-R18 终表同步范围（2026-10-23）】";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D16.json · version",
    desc: "版本号 v1.9 → v1.10",
    assert_ids: ["A06"],
  },
  {
    id: "C02",
    target: "units/U01/D16.json · ep4 subtitle_style.dwell_calc_convention",
    desc: "末尾追加「U01-R18 终表同步范围」口径段（只追加，不改写历史留痕）",
    assert_ids: ["A03", "A05", "A07", "A08"],
  },
  {
    id: "C03",
    target: "units/U01/D16.json · ep6 subtitle_style.dwell_calc_convention",
    desc: "末尾追加「U01-R18 终表同步范围」口径段（只追加，不改写历史留痕）",
    assert_ids: ["A03", "A05", "A07", "A08"],
  },
  {
    id: "C04",
    target: "units/U01/D16.json · ep7 subtitle_style.dwell_calc_convention",
    desc: "末尾追加「U01-R18 终表同步范围」口径段（只追加，不改写历史留痕）",
    assert_ids: ["A03", "A05", "A07", "A08"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "structure", source: "U01-R18 判据 D 口径（28 条对白行全集）", desc: "判据 D 受检对白行数 ＝ 28" },
  { id: "A02", phase: "pre", kind: "structure", source: "U01-R18 终表口径（D15 v1.4 配音锚点）", desc: "每条对白行都能在 D15 找到对应配音锚点，且 out_sec ＝ 锚点 at_sec+dur_sec（0 条不符）" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C02／C03／C04", desc: "待追加集数 ＝ 3（ep4/ep6/ep7）" },
  { id: "A04", phase: "pre", kind: "structure", source: "U01-R18 终表口径（ep1/2/3/5/8 已含终表注）", desc: "ep1/2/3/5/8 的 dwell_calc_convention 均已含「U01-R18 终表」注" },
  { id: "A05", phase: "pre", kind: "change", source: "变更清单 C02／C03／C04", desc: "目标 3 集当前均不含追加标记（防重复追加）" },
  { id: "A06", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.10" },
  { id: "A07", phase: "post", kind: "change", source: "变更清单 C02／C03／C04", desc: "落盘后回读 3 集均含追加段落" },
  { id: "A08", phase: "post", kind: "change", source: "变更清单 C02／C03／C04（S11 只追加不重写）", desc: "落盘后回读 3 段均为「原文＋追加」形态" },
  { id: "A09", phase: "post", kind: "structure", source: "写盘前深拷贝快照 PRE（防假验证）", desc: "剔除 3 段与 version 后，其余字段与写盘前快照逐字相同（时码 0 变化）" },
];

const G = createGuard({
  scriptId: SCRIPT_ID,
  targetPath: P(D16_PATH),
  fromVersion: FROM_V,
  toVersion: TO_V,
  changeManifest: CHANGE_MANIFEST,
  assertManifest: ASSERT_MANIFEST,
});

// ── 版本冻结门（不满足即结束进程，绝不进入写盘路径）──
G.freeze();

const D15 = J("units/U01/D15.json");
const D16 = J(D16_PATH);
/** 写盘前的**深拷贝快照** —— 回读比对必须拿它当基准。
 *  ⚠️ 若拿「写盘后再读的文件」比自己，时码变化恒为 0，回读就是**假验证**。
 *    本快照在**任何改动之前**取得，是唯一合法的比对基准。*/
const PRE = JSON.parse(JSON.stringify(D16));

// ── 1) 判据 D 断言：28 条对白行 out_sec ＝ D15 v1.4 的 at_sec+dur_sec（锁「不回退」）──
const voMissing = [];
const outMismatch = [];
let checked = 0;
for (const e of D16.episodes) {
  const vos = D15.episodes.find((x) => x.ep === e.ep).voice_over || [];
  for (const l of e.subtitle_style.lines) {
    if (l.type !== "对白") continue;
    const vo = vos.find((v) => Math.abs(v.at_sec - l.in_sec) < 1e-6 && v.char_id === l.char_id);
    if (!vo) { voMissing.push(`ep${e.ep} seq${l.seq}：D15 无对应配音锚点`); continue; }
    checked += 1;
    if (Math.abs((vo.at_sec + vo.dur_sec) - l.out_sec) > 1e-9) {
      outMismatch.push(`ep${e.ep} seq${l.seq}：out_sec ${l.out_sec} ≠ D15 v1.4 配音 at_sec+dur_sec `
        + `${(vo.at_sec + vo.dur_sec).toFixed(1)} —— 终表口径被破坏（疑似按 04:45 旧表回退）`);
    }
  }
}
G.assertPoint("A01", checked === 28, `判据 D 受检 ${checked} 条 ≠ 28 条（>0 且＝28 方成立）`);
G.assertPoint("A02", voMissing.length === 0 && outMismatch.length === 0,
  [...voMissing, ...outMismatch].join("；"));

// ── 2) 命中数断言：恰好 3 集待追加；另 5 集已含终表注 ──
let hit = 0;
const alreadyMissing = [];
const dupMark = [];
for (const e of D16.episodes) {
  const dc = e.subtitle_style.dwell_calc_convention || "";
  const hasMark = dc.includes(MARK);
  if (TARGET_EPS.includes(e.ep)) {
    if (hasMark) dupMark.push(`ep${e.ep}：已含「${MARK}」段落 → 重复追加，疑似已执行过本补丁`);
    else hit += 1;
  } else if (ALREADY_EPS.includes(e.ep)) {
    if (!dc.includes("U01-R18 终表")) {
      alreadyMissing.push(`ep${e.ep}：应已含 U01-R18 终表注，实测缺失（上游已落，本脚本不补）`);
    }
  }
}
G.assertPoint("A03", hit === TARGET_EPS.length, `待追加集数 ${hit} ≠ ${TARGET_EPS.length}（ep4/ep6/ep7）`);
G.assertPoint("A04", alreadyMissing.length === 0, alreadyMissing.join("；"));
G.assertPoint("A05", dupMark.length === 0, dupMark.join("；"));

// ── 写盘前收口 ──
G.finishPre();

// ── 3) 生成追加文本（**只追加**）──
function note(ep) {
  return `【U01-R18 终表同步范围（2026-10-23）】本轮 U01-R18 终表 9 行覆盖 `
    + `**ep1／ep2／ep3／ep5／ep8**（预算取实测 TTS 标称 **+0.1s**，避免贴边零余量）；`
    + `**本集（ep${ep}）不在该 9 行内**，本集对白字幕行 out_sec 本轮**未变**，`
    + `现值仍为 D15 **v1.4** 现行预算（out_sec ＝ 配音 at_sec＋dur_sec，28/28 逐条相等）。`
    + `上文「已随 D15 v1.1 的 dur_sec 收敛同步」与【上游闭合戳】段均为 **v1.1／v1.2 时点的历史留痕**，`
    + `按 S11「事件溯源只追加不重写」**原文保留**；D15 现行为 **v1.4**，`
    + `本轮同步范围与余量三口径见 subtitle_sync_audit。`;
}

for (const e of D16.episodes) {
  if (!TARGET_EPS.includes(e.ep)) continue;
  const ss = e.subtitle_style;
  ss.dwell_calc_convention = `${ss.dwell_calc_convention}${note(e.ep)}`;
}
D16.version = TO_V;

/**
 * 写后阶段断言（回读对象 doc）。stageLabel 用于区分「写盘前模拟（--check）」与「写后回读」。
 * 同一进程内只会调用一次 —— 断言点 id 不可重复登记。
 */
function runPostAssertions(doc, stageLabel) {
  G.assertPoint("A06", doc.version === TO_V, `${stageLabel} version ＝ ${doc.version}（应为 ${TO_V}）`);

  const missingMark = [];
  const notAppend = [];
  for (const e of doc.episodes) {
    if (!TARGET_EPS.includes(e.ep)) continue;
    const dc = e.subtitle_style.dwell_calc_convention || "";
    if (!dc.includes(MARK)) missingMark.push(`ep${e.ep} ${stageLabel}缺追加段落`);
    const preDc = PRE.episodes.find((x) => x.ep === e.ep).subtitle_style.dwell_calc_convention || "";
    if (!(dc.startsWith(preDc) && dc.length > preDc.length)) {
      notAppend.push(`ep${e.ep}：口径文本不是「原文＋追加」形态（疑为改写而非追加，违反 S11）`);
    }
  }
  G.assertPoint("A07", missingMark.length === 0, missingMark.join("；"));
  G.assertPoint("A08", notAppend.length === 0, notAppend.join("；"));

  // 深度比对：把**本次补丁允许改动的两处**从「前」「后」两份里都剔除 ——
  //   ① 3 个目标集的 dwell_calc_convention（口径文本追加）
  //   ② 顶层 version（v1.9 → v1.10）
  // 剩余结构必须**完全相同**（任何时码／文本／切点／其他口径字段被动过都会被抓出来）。
  const strip = (d) => {
    const c = JSON.parse(JSON.stringify(d));
    delete c.version;
    for (const e of c.episodes) {
      if (TARGET_EPS.includes(e.ep)) delete e.subtitle_style.dwell_calc_convention;
    }
    return JSON.stringify(c);
  };
  G.assertPoint("A09", strip(doc) === strip(PRE),
    `${stageLabel}：剔除 3 集口径文本后，其余字段与写盘前快照**不完全相同**（有字段被动过）`);
}

if (CHECK) {
  // --check：只校验不写盘。写后阶段以**内存态对象**模拟复核（同样登记全部断言点，双射成立）。
  runPostAssertions(D16, "写盘前模拟");
  G.finishPost();
  console.log("✅ 全部断言通过（--check：只校验，不写盘）：");
  console.log(`   · 版本门：盘上 ${FROM_V} → ${TO_V}`);
  console.log(`   · 判据 D 受检 ${checked} 条对白行，逐条 out_sec ＝ D15 v1.4 的 at_sec+dur_sec，0 条不符`);
  console.log(`   · 待追加 ${hit} 集（ep4/ep6/ep7）的 dwell_calc_convention；另 5 集已含终表注，不重复追加`);
  console.log("   · 只追加口径文本：任何 in_sec／out_sec／text／sync_rule／sync_basis／sync_records 均不动");
  console.log(`   · 变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条，实际登记 ${ASSERT_MANIFEST.length} 处，双射成立`);
  process.exit(0);
}

// ── 4) 备份 → 写盘 → 回读（备份落 reports/_bak_*，不在 units/ 里堆备份件）──
// 备份目录用**本地时**（与本岗既有 `reports/_bak_U01_D11_D16_<本地时间戳>/` 约定一致；
// toISOString() 是 UTC，会与既有目录名差一个日期）。
const now = new Date();
const p2 = (n) => String(n).padStart(2, "0");
const stamp = `${now.getFullYear()}${p2(now.getMonth() + 1)}${p2(now.getDate())}-${p2(now.getHours())}${p2(now.getMinutes())}${p2(now.getSeconds())}`;
const bakDir = P(`reports/_bak_U01_D11_D16_${stamp}`);
if (!existsSync(bakDir)) mkdirSync(bakDir, { recursive: true });
const bak = resolve(bakDir, "D16.json");
copyFileSync(P(D16_PATH), bak);
console.log(`   · 备份 → reports/_bak_U01_D11_D16_${stamp}/D16.json`);

writeFileSync(P(D16_PATH), JSON.stringify(D16, null, 2), "utf8");

// ── 5) 写后回读 ──
const after = J(D16_PATH);
runPostAssertions(after, "写后回读");
G.finishPost();

console.log("✅ 写后回读通过：版本正确、3 段为「原文＋追加」形态；剔除这 3 段后其余字段与写盘前快照**完全相同**（时码 0 变化）");
console.log(`✅ 落盘：${D16_PATH}  ${TO_V}  ${existsSync(P(D16_PATH)) ? readFileSync(P(D16_PATH)).length : 0} B`);
console.log(`   变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条（写盘前 ${ASSERT_MANIFEST.filter((a) => a.phase === "pre").length} 条 ＋ 写后 ${ASSERT_MANIFEST.filter((a) => a.phase === "post").length} 条），实际登记 ${ASSERT_MANIFEST.length} 处，双射成立。`);
