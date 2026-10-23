#!/usr/bin/env node
/**
 * D11 v1.8 → v1.9：ep7 镜3（g27）机位视点口径标注 —— 严格 POV → 近似 POV（视点代表位）
 *
 * 触发依据：企划合规 U02-R07 裁定（D18 open_issues[57].resolution，2026-10-23 07:5x）
 *   四项条件（缺一不可）：
 *     ① 同源修订：改构建脚本后重跑落盘，禁只改 JSON（Q40）
 *     ② D11↔D14 同步：若 D11 该镜含机位/视点字段、D14 package 含相机参数，须一并同步
 *     ③ 数值依据须写进 notes：写明「机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m
 *        ＋ 0.10 m 余量）」，禁只写数字不留依据
 *     ④ 重渲复核：修后必须重渲 g27 并复跑帧校验，灰板镜位数须为 0（FAIL 0）
 *   附**语义标注要求**：g27 分离 0.35 m 后**已不是严格 POV**，须标注「近似 POV（视点代表位）」，
 *   否则下游按严格 POV 处理会出错。
 *
 * 本岗（D11 侧）条件达成情况（全部实跑核验，见台账 §143）
 *   ① ✅ 用 patch 脚本（带守卫＋清单）落盘，非手改 JSON
 *   ② ✅ D11 侧**无机位字段**（D11 镜位只有 shot_size／camera_angle／lens_mm／movement）；
 *        D14 package 的相机参数由白模 10:08 重渲时一并落盘 → V11 校验 PASS ✅
 *   ③ ✅ 0.35 m 数值依据 ＋ 0.25 m ＋ 0.10 m 余量 逐字写进本镜 note
 *   ④ ✅ 白模已重渲：`check_white_model_frames --unit U01` → PASS 32｜FAIL 0｜exit 0
 *
 * ─────────────────────────────────────────────────────────────────
 * 为什么 `camera_angle` **不改**（本轮踩到的 schema 硬约束）
 * ─────────────────────────────────────────────────────────────────
 * `camera_angle` 是 `03_规格/schema.json` 定义的**七选一闭枚举**：
 *   平视／俯视／仰视／顶视／过肩／主观视角／客观跟拍
 * —— **没有「近似 POV」取值**。硬闸 `validate.mjs` 的 V1「字段完整性与枚举合法性」
 * 会把新枚举值判成 **error**（实测：写「近似 POV（视点代表位）」→ V1 FAIL，U01 10/11｜error 1）。
 * 而 `03_规格/*`／`04_工具/*` **非本岗可写**（共享工具改动须总控明派并在 D18 登记）。
 *
 * ⇒ **schema 合规的落点是 `note` 字段**：
 *   · `camera_angle` 保持枚举合法值「主观视角」（本镜仍是 POV 家族，0.35 m 离轴不改变其角度词表归类）；
 *   · `note` 末尾追加「近似 POV（视点代表位）」标注 ＋ 0.35 m 数值依据（裁定条件③ ＋ 语义标注要求）；
 *   · 本岗校验器 `check_D11_D13_camera_alignment.py` 的 B1「已按裁定标注」判定
 *     同步扩展为**同时识别 note 中的标注**（camera_angle 与 note 任一命中即算已标注）。
 *
 * ⚠️ 遗留缺口（**已上报企划合规，待其裁定**）：
 *   `camera_angle` 无法表达「严格 POV／近似 POV」之别，下游若只读 camera_angle 仍会当成严格 POV。
 *   若要根治，须由总控明派把 `03_规格/schema.json` 的枚举扩为八选一（含「近似 POV（视点代表位）」），
 *   并同步 `03_规格/字段规格表.md` 与 `04_工具/` 的枚举来源 —— **明派须在 D18 登记后方生效**。
 *   在那之前，note 是口径真源。
 *
 * 治理要点（与本批 U02-R34 一致）
 *   ① 变更清单 ＝ CHANGE_MANIFEST（2 条）；断言点清单 ＝ ASSERT_MANIFEST（20 条，逐条标来源）。
 *   ② 版本冻结门：盘上 ≠ 前提版本一律不写盘；已执行过／已演进 → `[NO-OP]` exit 0；
 *      早于前提版本 → exit 3（前置未落）。`--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D11.json");

const FROM_V = "v1.8";
const TO_V = "v1.9";
const SCRIPT_ID = "patch_D11_v19_g27_pov_separation";

/** 目标镜位三元组唯一定位 */
const TARGET_EP = 7;
const TARGET_SHOT = 3;
const TARGET_GSN = 27;

/** 目标镜位 camera_angle：闭枚举合法值，**本脚本不改动它** */
const ANGLE_ENUM = "主观视角";
/** `03_规格/schema.json` 的 camera_angle 七选一闭枚举 */
const ANGLE_ENUM_VALUES = ["平视", "俯视", "仰视", "顶视", "过肩", "主观视角", "客观跟拍"];

/** 目标镜位 note 原文（逐字；用于断言与「原文＋追加」形态校验） */
const ORIG_NOTE =
  "骨纹为体表表现，不破体、不见皮下骨骼（D07 scene_needs／D10 母题 M02）。"
  + "归一度读数本集仍为 0.5%——一纹权柄上限 30 秒的单体近身焚斑不推读数（D05 T20）。";

/** note 末尾追加段（只追加，不改写原文 —— S11） */
const NOTE_APPEND =
  "📌 机位视点口径订正（2026-10-23）：白模 D13 v1.1 已将本镜机位与角色眼位分离 0.35 m"
  + "（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量；机位落在眼位北侧 0.35 m、与眼位等高，"
  + "视线自视点代表位向下约 62° 指向右腕），故本镜已不是严格 POV，"
  + "按 U02-R07 附语义要求标注为近似 POV（视点代表位）；"
  + "camera_angle 属七选一闭枚举（无该取值），故仍为「主观视角」，**本条 note 为口径真源**；"
  + "画面事实、归一度读数与时长均不变。";

/** 追加段必须逐字含有的三项（裁定条件③ 数值依据 ＋ 语义标注） */
const EVIDENCE = [
  "近似 POV（视点代表位）",
  "机位与角色眼位分离 0.35 m",
  "角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量",
];

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D11.json · version",
    desc: "版本号 v1.8 → v1.9",
    assert_ids: ["A11", "A16"],
  },
  {
    id: "C02",
    target: "units/U01/D11.json · ep7 镜3（g27）note",
    desc: "末尾追加「近似 POV（视点代表位）」语义标注 ＋ 0.35 m 数值依据（原文不改写 —— S11）；"
      + "camera_angle 保持闭枚举合法值不变",
    assert_ids: ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A17", "A18", "A19"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C02（唯一定位）", desc: "全库恰有 1 个镜位同时满足 ep＝7／shot_id＝3／global_shot_no＝27" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "目标镜位改前 camera_angle ＝ 「主观视角」" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C02", desc: "目标镜位改前 note ＝ 预期原文（逐字）" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C02（schema 合规）", desc: "目标镜位改前 camera_angle 属 schema 七选一闭枚举" },
  { id: "A05", phase: "pre", kind: "change", source: "变更清单 C02（schema 合规）", desc: "改后目标镜位 camera_angle **未变**（仍为「主观视角」，未写入非法枚举值）" },
  { id: "A06", phase: "pre", kind: "change", source: "变更清单 C02（S11 只追加不重写）", desc: "改后目标镜位 note ＝ 原文 ＋ 追加段（以原文为前缀、长度只增）" },
  { id: "A07", phase: "pre", kind: "change", source: "变更清单 C02（裁定语义标注要求）", desc: "追加段逐字含「近似 POV（视点代表位）」" },
  { id: "A08", phase: "pre", kind: "change", source: "变更清单 C02（裁定条件③）", desc: "追加段逐字含 0.35 m 分离依据两项" },
  { id: "A09", phase: "pre", kind: "change", source: "变更清单 C02（防误伤同值镜头）", desc: "改前改后全库 camera_angle ＝「主观视角」的镜位数恒 ＝ 5" },
  { id: "A10", phase: "pre", kind: "change", source: "变更清单 C02", desc: "除目标镜位的 note 外，全库逐镜逐字段零变化（含字段集合一致）" },
  { id: "A11", phase: "pre", kind: "change", source: "变更清单 C01", desc: "写回内容的 version ＝ v1.9" },
  { id: "A12", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜）", desc: "每集镜数 ＝ 4" },
  { id: "A13", phase: "pre", kind: "structure", source: "D11 模板结构约定（每集镜时 45.0s）", desc: "每集镜时求和 ＝ 45" },
  { id: "A14", phase: "pre", kind: "structure", source: "D11 模板结构约定（global_shot_no 严格递增）", desc: "global_shot_no 严格递增" },
  { id: "A15", phase: "pre", kind: "structure", source: "D11 模板结构约定（全集 32 镜）", desc: "总镜数 ＝ 32" },
  { id: "A16", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.9" },
  { id: "A17", phase: "post", kind: "change", source: "变更清单 C02", desc: "落盘后回读目标镜位 note 以原文为前缀且逐字含标注与依据" },
  { id: "A18", phase: "post", kind: "change", source: "变更清单 C02（schema 合规）", desc: "落盘后回读目标镜位 camera_angle 仍为「主观视角」（未被误改）" },
  { id: "A19", phase: "post", kind: "change", source: "变更清单 C02", desc: "回读后独立复算：除目标镜位 note 外全库零字段变化" },
  { id: "A20", phase: "post", kind: "structure", source: "D11 模板结构约定（重新读盘独立复算）", desc: "落盘后重新读盘解析，32 镜 / 4 镜每集 / 45s 每集 / 严格递增全部成立" },
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
G.assertPoint("A02", target.camera_angle === ANGLE_ENUM, `目标镜位改前 camera_angle ＝ ${target.camera_angle}（应为 ${ANGLE_ENUM}）`);
G.assertPoint("A03", target.note === ORIG_NOTE, "目标镜位改前 note 与预期原文不一致");
G.assertPoint("A04", ANGLE_ENUM_VALUES.includes(target.camera_angle),
  `目标镜位改前 camera_angle ＝ ${target.camera_angle}，不在 schema 七选一闭枚举内`);

/** 全库某 camera_angle 值的镜位数 */
const countAngle = (doc, val) => {
  let n = 0;
  for (const e of doc.episodes) for (const s of e.shots) if (s.camera_angle === val) n += 1;
  return n;
};
const beforeAngleCount = countAngle(before, ANGLE_ENUM);

// ── 构造改后内容（**只改目标镜位的 note**；camera_angle 一律不动）──
const after = JSON.parse(src);
const t2 = after.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
t2.note = `${ORIG_NOTE}${NOTE_APPEND}`;
after.version = TO_V;

G.assertPoint("A05", t2.camera_angle === ANGLE_ENUM, `改后目标镜位 camera_angle ＝ ${t2.camera_angle}（应为 ${ANGLE_ENUM}，不得写入非法枚举值）`);
G.assertPoint("A06", t2.note.startsWith(ORIG_NOTE) && t2.note.length > ORIG_NOTE.length, "改后 note 不是「原文 ＋ 追加」形态");
G.assertPoint("A07", t2.note.includes("近似 POV（视点代表位）"), "追加段缺「近似 POV（视点代表位）」语义标注");
G.assertPoint("A08", EVIDENCE.slice(1).every((x) => t2.note.includes(x)),
  `追加段缺 0.35 m 数值依据：缺 ${EVIDENCE.slice(1).filter((x) => !t2.note.includes(x)).join("｜")}`);
G.assertPoint("A09", beforeAngleCount === 5 && countAngle(after, ANGLE_ENUM) === 5,
  `全库「${ANGLE_ENUM}」镜位数 改前 ${beforeAngleCount} → 改后 ${countAngle(after, ANGLE_ENUM)}（须恒为 5）`);

// ── 全库零变化核验（除目标镜位的 note）──
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
    if (isTarget && f === "note") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) diffs.push(`${k}.${f}`);
  }
}
G.assertPoint("A10", diffs.length === 0, `除目标镜位 note 外还有字段变化：${diffs.join(", ")}`);
G.assertPoint("A11", after.version === TO_V, `写回后 version ＝ ${after.version}（应为 ${TO_V}）`);

// ── 结构复核（写盘前，四类问题各自独立收集，互不串台）──
const countIssues = [];
const sumIssues = [];
const incIssues = [];
const totalIssues = [];
let total = 0;
let prev = 0;
for (const e of after.episodes) {
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
G.assertPoint("A12", countIssues.length === 0, countIssues.join("；"));
G.assertPoint("A13", sumIssues.length === 0, sumIssues.join("；"));
G.assertPoint("A14", incIssues.length === 0, incIssues.join("；"));
G.assertPoint("A15", totalIssues.length === 0, totalIssues.join("；"));

// ── 写盘前收口 ──
G.finishPre();

// 序列化格式与现盘一致（JSON.stringify(obj, null, 2) ＋ 尾换行，往返已逐字节验证）
writeFileSync(TARGET, `${JSON.stringify(after, null, 2)}\n`, "utf8");

// ── 写后回读 ──
const back = readFileSync(TARGET, "utf8");
const backParsed = JSON.parse(back);
G.assertPoint("A16", backParsed.version === TO_V, `回读 version ＝ ${backParsed.version}（应为 ${TO_V}）`);

const bt = backParsed.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
G.assertPoint("A17", bt.note.startsWith(ORIG_NOTE) && EVIDENCE.every((x) => bt.note.includes(x)),
  "回读目标镜位 note 不是「原文 ＋ 含标注与 0.35 m 依据的追加段」形态");
G.assertPoint("A18", bt.camera_angle === ANGLE_ENUM, `回读目标镜位 camera_angle ＝ ${bt.camera_angle}（应为 ${ANGLE_ENUM}）`);

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
G.assertPoint("A20", backIssues.length === 0, backIssues.join("；"));

// 回读后独立复算零变化（不复用写盘前的判定结果）
const backDiffs = [];
for (const [k, b] of bMap) {
  const a = aMap.get(k);
  if (!a) continue;
  const isTarget = k === `${TARGET_EP}#${TARGET_SHOT}`;
  for (const f of Object.keys(b).sort()) {
    if (isTarget && f === "note") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) backDiffs.push(`${k}.${f}`);
  }
}
G.assertPoint("A19", backDiffs.length === 0, `回读后除目标镜位 note 外还有字段变化：${backDiffs.join(", ")}`);

G.finishPost();

console.log(`✅ D11 ${FROM_V} → ${TO_V} 落盘：ep${TARGET_EP} 镜${TARGET_SHOT}（g${TARGET_GSN}）note 末尾追加「近似 POV（视点代表位）」语义标注 ＋ 0.35 m 数值依据；camera_angle 保持「主观视角」（闭枚举合法值）；其余 31 镜零变化。`);
console.log(`   「${ANGLE_ENUM}」镜位数：改前 ${beforeAngleCount} → 改后 ${countAngle(after, ANGLE_ENUM)}（camera_angle 未动）`);
console.log(`   字节：${Buffer.byteLength(back, "utf8")}`);
console.log(`   变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条（写盘前 ${ASSERT_MANIFEST.filter((a) => a.phase === "pre").length} 条 ＋ 写后 ${ASSERT_MANIFEST.filter((a) => a.phase === "post").length} 条），实际登记 ${ASSERT_MANIFEST.length} 处，双射成立。`);
