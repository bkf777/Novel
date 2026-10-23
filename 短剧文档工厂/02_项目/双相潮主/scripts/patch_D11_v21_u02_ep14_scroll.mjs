#!/usr/bin/env node
/**
 * D11 U02 v1.6 → v1.7：ep14 镜3（gsn 55）visual_facts 补回正文动作「滚过」
 *
 * ── 来件与定性（台本编剧 09:2x 来函，2026-10-23）──────────────────────────────
 * 台本编剧实测发现：D11 U02 **ep14 镜3** 的 `visual_facts` 写的是「成本条目**停在最后一栏**」，
 * 而 D08 U02 `ep14 body[3]` 正文是「委员会屏幕亮起，冷金底色上**滚过**一列成本条目。」、
 * `body[4]` 才是「成本模型在屏幕上**停住**，最后一栏数字没有合上。」
 * ⇒ `body[3]` 的「滚过」动作在 D11 层被并写成「停住」。
 * 该行**无 `shot_intent`**（台本编剧契约未要求拍它）⇒ 台本编剧侧 D08 无失配，
 * 来函判为「D11 覆盖层问题，归本岗处置」。
 *
 * ── 本岗的独立复现与定性（不采信转述，按磁盘实测）────────────────────────────
 * · 磁盘复现：全库 `visual_facts` 含「滚过」＝ **0**（该动作在 D11 层**完全缺失**，非「写到了别处」）；
 *   「一列成本条目停在最后一栏」全库**仅** ep14 镜3 一处命中。
 * · 目标镜位三元组唯一定位：ep＝14／shot_id＝3／global_shot_no＝55。
 * · **契约层面**：`body[4]` 带 `shot_intent`（要求「最后一栏没有合上必须被看见」），
 *   而 D11 U02 ep14 镜3 的 `note` **已记录**该 body[4] 的反查留痕
 *   （「本镜 visual_facts 已正面拍到（锚点：最后一栏数字没有合上、机械厂那一行后面没有人落笔）」）
 *   ⇒ **现行契约（D08 shot_intent ↔ D11 visual_facts）已满足**。
 * · `body[3]`（滚过）既无 `shot_intent`、也不在 Q53 轴①／轴②任一契约范围内
 *   ⇒ D11 未逐字表达「滚过」是**覆盖度缺口**，**不是契约违反、不是失配**。
 * · ⇒ 裁定：**改正覆盖度缺口**（把 D08 的过程动作显式写回镜头表），**不新建契约**。
 *   「D11 是否对无 shot_intent 的正文 action 行负有普遍覆盖义务」属**需裁定的口径问题**，
 *   本岗已就此提请企划合规裁定（若立为通用契约，全 8 集所有无 shot_intent 的 action 行
 *   都要上镜，其中大量是环境/氛围/合规行——如「AI 生成」角标、「屏幕只作信息面」这类
 *   **非画面事实**，逐条上镜会失真 ⇒ 本岗建议**不立通用契约**）。
 *
 * ── 改法（变更清单＝2 条）───────────────────────────────────────────────────
 *   C01  `units/U02/D11.json` · version ：v1.6 → v1.7
 *   C02  `units/U02/D11.json` · ep14 镜3（g55）· visual_facts ：
 *        「…冷金底色上一列成本条目**停在最后一栏**，最后一栏数字没有合上…」
 *        → 「…冷金底色上一列成本条目**先滚过，停在最后一栏**，最后一栏数字没有合上…」
 *        （**只在本句内补回源正文的动作词**；body[4] 的可见性锚点「最后一栏数字没有合上」逐字保留）
 *   ⇒ **其余 31 镜逐字段零变化**；全库 `camera_angle` 不动；`note` 不动。
 *
 * ── 治理要点（与本岗 U02-R34 批次一致）──────────────────────────────────────
 *   ① 变更清单 ＝ CHANGE_MANIFEST（2 条）；断言点清单 ＝ ASSERT_MANIFEST（14 条，逐条标来源）。
 *   ② 版本冻结门：盘上 ＝ 前提 → 执行；＝ 目标 → `[NO-OP]` exit 0；
 *      盘上已**演进** → `[NO-OP]` exit 0（**不回退**，避 D18 Q82 的静默回退）；早于前提 → exit 3。
 *      `--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 *   ⑤ **源文本锚定断言**：写盘前读 D08 U02，逐字核 `ep14 body[3]` 含「滚过」、
 *      `body[4]` 含「停住」且带 `shot_intent` —— 证明本改写**有正文依据**，
 *      且未与 body[4] 的可见性要求相冲。
 */

import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U02/D11.json");
const SOURCE_D08 = resolve(HERE, "../units/U02/D08.json");

const FROM_V = "v1.6";
const TO_V = "v1.7";
const SCRIPT_ID = "patch_D11_v21_u02_ep14_scroll";

/** 目标镜位三元组唯一定位 */
const TARGET_EP = 14;
const TARGET_SHOT = 3;
const TARGET_GSN = 55;

/** `03_规格/schema.json` 的 cameraAngle 七选一闭枚举（V1 判据真源） */
const ANGLE_ENUM_VALUES = ["平视", "俯视", "仰视", "顶视", "过肩", "主观视角", "客观跟拍"];

/** 改前串 → 改后串（只在本句内补回源正文的动作词） */
const OLD_FRAG = "一列成本条目停在最后一栏";
const NEW_FRAG = "一列成本条目先滚过，停在最后一栏";
/** body[4] 的可见性锚点，改后必须逐字保留 */
const KEEP_ANCHOR = "最后一栏数字没有合上";
/** 源正文动作词（改后必须出现） */
const SOURCE_ACTION = "滚过";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U02/D11.json · version",
    desc: "版本号 v1.6 → v1.7（覆盖度补强后重新锁进无歧义版本号）",
    assert_ids: ["A04", "A09"],
  },
  {
    id: "C02",
    target: "units/U02/D11.json · ep14 镜3（gsn 55）· visual_facts",
    desc: "把 D08 ep14 body[3] 的过程动作「滚过」显式写回镜头表："
      + "「一列成本条目停在最后一栏」→「一列成本条目先滚过，停在最后一栏」；"
      + "body[4] 的可见性锚点「最后一栏数字没有合上」逐字保留；其余 31 镜零变化",
    assert_ids: ["A01", "A02", "A03", "A05", "A06", "A10", "A11", "A12", "A14", "A15"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化；条数必须与实际登记点数一一对应 —— 双射）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C02（唯一定位）", desc: "全库恰有 1 个镜位同时满足 ep＝14／shot_id＝3／global_shot_no＝55" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "改前目标 visual_facts 逐字含旧串「一列成本条目停在最后一栏」＋ 锚点「最后一栏数字没有合上」" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C02（缺口自证）", desc: "改前目标 visual_facts **不含**「滚过」⇒ 该动作在 D11 层确实缺失" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C01", desc: "改前 version ＝ v1.6" },
  { id: "A05", phase: "pre", kind: "change", source: "变更清单 C02（防误伤）", desc: "旧串在全库 visual_facts 中**仅**目标镜 1 处命中" },
  { id: "A06", phase: "pre", kind: "change", source: "源文本锚定（D08 U02 ep14 body[3]／body[4]）", desc: "D08 U02 ep14 body[3] 含「滚过」、body[4] 含「停住」且带 shot_intent ⇒ 改写有正文依据且不与 body[4] 可见性要求相冲" },
  { id: "A07", phase: "pre", kind: "structure", source: "硬闸 V1 判据（cameraAngle 闭枚举）", desc: "改前全库每镜 camera_angle 均属 schema 七选一闭枚举（**V1 判据自证**）" },
  { id: "A08", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜／每集 45.0s／gsn 严格递增／共 32 镜）", desc: "结构四项改前全部成立" },
  { id: "A09", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.7" },
  { id: "A10", phase: "post", kind: "change", source: "变更清单 C02", desc: "落盘后目标 visual_facts 逐字含新串「一列成本条目先滚过，停在最后一栏」**且**仍含锚点「最后一栏数字没有合上」" },
  { id: "A11", phase: "post", kind: "change", source: "变更清单 C02（改写生效、非双写）", desc: "落盘后目标 visual_facts **不再**逐字含旧串「一列成本条目停在最后一栏」" },
  { id: "A12", phase: "post", kind: "change", source: "变更清单 C02（回读独立复算）", desc: "落盘后回读：除目标镜 visual_facts 外，全库逐镜逐字段零变化（含字段集合一致）" },
  { id: "A13", phase: "post", kind: "structure", source: "D11 模板结构约定 ＋ 硬闸 V1 判据（重新读盘独立复算）", desc: "落盘后重新读盘：结构四项 ＋ camera_angle 合法全部成立" },
  { id: "A14", phase: "post", kind: "change", source: "变更清单 C02（留痕不得被误删）", desc: "落盘后目标镜 `note` 的 body[4] shot_intent 反查留痕仍在（未被误改/误删）" },
  { id: "A15", phase: "pre", kind: "change", source: "变更清单 C02（写盘前自检）", desc: "写盘前构造出的改后内容：除目标镜 visual_facts 外，全库逐镜逐字段零变化（含字段集合一致）" },
];

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
const before = JSON.parse(src);

// ── 唯一定位目标镜位 ──
const hits = [];
for (const e of before.episodes) {
  for (const s of e.shots) {
    if (e.ep === TARGET_EP && s.shot_id === TARGET_SHOT && s.global_shot_no === TARGET_GSN) hits.push(s);
  }
}
G.assertPoint("A01", hits.length === 1, `目标镜位三元组命中 ${hits.length} 个（应为 1）`);
const target = hits[0];

const vfBefore = String(target.visual_facts || "");
G.assertPoint("A02", vfBefore.includes(OLD_FRAG) && vfBefore.includes(KEEP_ANCHOR),
  "改前目标 visual_facts 缺旧串或缺 body[4] 可见性锚点");
G.assertPoint("A03", !vfBefore.includes(SOURCE_ACTION),
  "改前目标 visual_facts 已含「滚过」⇒ 本补丁的前提不成立（可能已执行过或已被他人补写）");
G.assertPoint("A04", before.version === FROM_V, `改前 version ＝ ${before.version}（应为 ${FROM_V}）`);

// ── 全库旧串唯一性（防误伤）──
const oldFracShots = [];
for (const e of before.episodes) {
  for (const s of e.shots) if (String(s.visual_facts || "").includes(OLD_FRAG)) oldFracShots.push(`${e.ep}#${s.shot_id}`);
}
G.assertPoint("A05", oldFracShots.length === 1 && oldFracShots[0] === `${TARGET_EP}#${TARGET_SHOT}`,
  `旧串在全库命中 ${oldFracShots.length} 处（${oldFracShots.join("、")}），应为仅目标镜 1 处`);

// ── 源文本锚定：读 D08 U02，核 body[3]／body[4] ──
let d08 = null;
let d08Issue = "";
try {
  d08 = JSON.parse(readFileSync(SOURCE_D08, "utf8"));
  const ep14 = (d08.episodes || []).find((e) => e.ep === TARGET_EP);
  const body = (ep14 && ep14.body) || [];
  const b3 = body[3] || {};
  const b4 = body[4] || {};
  const b3Has = String(b3.text || "").includes(SOURCE_ACTION);
  const b4Has = String(b4.text || "").includes("停住");
  const b4Intent = !!b4.shot_intent;
  if (!b3Has) d08Issue = `D08 ep14 body[3] 文本不含「${SOURCE_ACTION}」`;
  else if (!b4Has) d08Issue = "D08 ep14 body[4] 文本不含「停住」";
  else if (!b4Intent) d08Issue = "D08 ep14 body[4] 已无 shot_intent（源结构变了，须复核本补丁前提）";
} catch (e) {
  d08Issue = `读 D08 U02 失败：${e.message}`;
}
G.assertPoint("A06", d08Issue === "", `源文本锚定不成立：${d08Issue}`);

// ── 全库 camera_angle 合法性（V1 判据自证）──
const allAngles = [];
for (const e of before.episodes) for (const s of e.shots) allAngles.push(s.camera_angle);
const badAngles = allAngles.filter((a) => !ANGLE_ENUM_VALUES.includes(a));
G.assertPoint("A07", badAngles.length === 0,
  `改前全库有 ${badAngles.length} 个 camera_angle 不属七选一闭枚举：${badAngles.join("｜")}`);

// ── 结构复核（改前，四类问题各自独立收集，互不串台）──
const countIssues = [];
const sumIssues = [];
const incIssues = [];
const totalIssues = [];
let total = 0;
let prev = 0;
for (const e of before.episodes) {
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
G.assertPoint("A08",
  countIssues.length === 0 && sumIssues.length === 0 && incIssues.length === 0 && totalIssues.length === 0,
  [...countIssues, ...sumIssues, ...incIssues, ...totalIssues].join("；"));

// ── 构造改后内容（**只改顶层 version ＋ 目标镜 visual_facts 一处**）──
const after = JSON.parse(src);
const t2 = after.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
const noteBefore = t2.note;
t2.visual_facts = String(t2.visual_facts).replace(OLD_FRAG, NEW_FRAG);
after.version = TO_V;

// ── 全库零变化核验（除目标镜 visual_facts 与顶层 version）──
const bMap = new Map();
const aMap = new Map();
for (const e of before.episodes) for (const s of e.shots) bMap.set(`${e.ep}#${s.shot_id}`, s);
for (const e of after.episodes) for (const s of e.shots) aMap.set(`${e.ep}#${s.shot_id}`, s);
const diffs = [];
for (const k of bMap.keys()) if (!aMap.has(k)) diffs.push(`改后缺失镜位 ${k}`);
for (const k of aMap.keys()) if (!bMap.has(k)) diffs.push(`改后多出镜位 ${k}`);
for (const [k, b] of bMap) {
  const a = aMap.get(k);
  if (!a) continue;
  const isTarget = k === `${TARGET_EP}#${TARGET_SHOT}`;
  const bKeys = Object.keys(b).sort();
  const aKeys = Object.keys(a).sort();
  if (bKeys.join("|") !== aKeys.join("|")) diffs.push(`${k} 字段集合不一致`);
  for (const f of bKeys) {
    if (isTarget && f === "visual_facts") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) diffs.push(`${k}.${f}`);
  }
}
G.assertPoint("A15", diffs.length === 0, `除目标镜 visual_facts 外还有字段变化：${diffs.join(", ")}`);

// ── 写盘前收口（pre 阶段双射校验；不通过即拒绝写盘）──
G.finishPre();

// ── 写盘前备份（备份统一落 reports/_bak_*，不在 units/ 内写备份）──
const now = new Date();
const p2 = (n) => String(n).padStart(2, "0");
const ts = `${now.getFullYear()}${p2(now.getMonth() + 1)}${p2(now.getDate())}-`
  + `${p2(now.getHours())}${p2(now.getMinutes())}${p2(now.getSeconds())}`;
const bakDir = resolve(HERE, `../reports/_bak_D11_U02_v21_ep14_scroll_${ts}`);
mkdirSync(bakDir, { recursive: true });
copyFileSync(TARGET, resolve(bakDir, "D11.json"));
console.log(`   · 备份 → reports/_bak_D11_U02_v21_ep14_scroll_${ts}/D11.json`);

// ── 落盘（序列化格式与现盘逐字节一致：2 空格缩进 ＋ 末尾换行）──
writeFileSync(TARGET, `${JSON.stringify(after, null, 2)}\n`, "utf8");

// ── 写后回读独立复算 ──
const reread = JSON.parse(readFileSync(TARGET, "utf8"));
G.assertPoint("A09", reread.version === TO_V, `落盘后回读 version ＝ ${reread.version}（应为 ${TO_V}）`);
const rt = reread.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
const vfAfter = String(rt.visual_facts || "");
G.assertPoint("A10", vfAfter.includes(NEW_FRAG) && vfAfter.includes(KEEP_ANCHOR),
  "落盘后目标 visual_facts 缺新串或缺 body[4] 可见性锚点");
G.assertPoint("A11", !vfAfter.includes(OLD_FRAG),
  "落盘后目标 visual_facts 仍逐字含旧串 ⇒ 改写未生效（或双写）");
const rMap = new Map();
for (const e of reread.episodes) for (const s of e.shots) rMap.set(`${e.ep}#${s.shot_id}`, s);
const rdiffs = [];
for (const [k, b] of bMap) {
  const a = rMap.get(k);
  if (!a) { rdiffs.push(`回读缺失镜位 ${k}`); continue; }
  const isTarget = k === `${TARGET_EP}#${TARGET_SHOT}`;
  const bKeys = Object.keys(b).sort();
  const aKeys = Object.keys(a).sort();
  if (bKeys.join("|") !== aKeys.join("|")) rdiffs.push(`${k} 字段集合不一致`);
  for (const f of bKeys) {
    if (isTarget && f === "visual_facts") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) rdiffs.push(`${k}.${f}`);
  }
}
G.assertPoint("A14", String(rt.note || "") === String(noteBefore)
  && String(rt.note || "").includes("shot_intent"),
  "落盘后目标镜 note 的 body[4] shot_intent 反查留痕被改动或丢失");
G.assertPoint("A12", rdiffs.length === 0, `落盘后回读发现额外字段变化：${rdiffs.join(", ")}`);
const rCount = [];
const rSum = [];
const rInc = [];
const rTotal = [];
let rTot = 0;
let rPrev = 0;
for (const e of reread.episodes) {
  const sum = e.shots.reduce((a, s) => a + s.duration_sec, 0);
  if (sum !== 45) rSum.push(`ep${e.ep} 镜时求和 ${sum} ≠ 45`);
  if (e.shots.length !== 4) rCount.push(`ep${e.ep} 镜数 ${e.shots.length} ≠ 4`);
  for (const s of e.shots) {
    if (s.global_shot_no <= rPrev) rInc.push(`global_shot_no 非严格递增（${s.global_shot_no}）`);
    rPrev = s.global_shot_no;
    rTot += 1;
  }
}
if (rTot !== 32) rTotal.push(`总镜数 ${rTot} ≠ 32`);
const rAngles = [];
for (const e of reread.episodes) for (const s of e.shots) rAngles.push(s.camera_angle);
const rBad = rAngles.filter((a) => !ANGLE_ENUM_VALUES.includes(a));
G.assertPoint("A13",
  rCount.length === 0 && rSum.length === 0 && rInc.length === 0 && rTotal.length === 0 && rBad.length === 0,
  [...rCount, ...rSum, ...rInc, ...rTotal, ...rBad.length ? `camera_angle 非法 ${rBad.join("｜")}` : ""].join("；"));

// ── 写后收口（post 阶段双射校验）──
G.finishPost();

console.log(`✅ D11 U02 ${FROM_V} → ${TO_V} 落盘完成（ep14 镜3 visual_facts 补回源正文动作「滚过」；其余 31 镜零变化）`);
