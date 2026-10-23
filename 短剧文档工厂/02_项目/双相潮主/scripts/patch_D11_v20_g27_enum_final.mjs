#!/usr/bin/env node
/**
 * D11 U01 v1.9 → v1.10：g27（ep7 镜3）机位视点口径 —— 枚举合规终态锁定 ＋ 锁后追加式登记复验
 *
 * ── 为什么有这一版（总控 10:4x 派单的背景与本岗的实测结论）────────────────────
 * 总控来单的事实前提是「现盘 D11 U01 v1.9（mtime 10:24:16）的 camera_angle ＝ 自由文本
 * 「近似 POV（视点代表位）」，U01 破 V1（error 1），要求属主回滚或改正」。
 * 本岗 10:44 复跑实况：**该快照已过期** ——
 *   · 10:24:16 的那次落盘是本岗**首次**写入尝试（备份目录 `_bak_D11_U01_v19_g27_20261023-102416/`
 *     由本岗 v19 脚本在写盘前生成，内容为 v1.8｜50,322 B｜sha c832f5b5353d43ae）；
 *   · 该次写入因把 camera_angle 写成非枚举自由文本而破 V1，**本岗随即回滚**
 *     （第二次备份 `_bak_D11_U01_v19_g27_note_20261023-102822/D11.json` 与前者**同字节同 sha**）；
 *   · 10:28:22 已按 **schema 合规形态**重新落盘：camera_angle 保持闭枚举合法值「主观视角」，
 *     几何事实与「近似 POV（视点代表位）」语义落进 **note**（自由文本字段）；
 *   · 现盘＝ v1.9｜50,876 B｜mtime 10:28:22｜sha 7b631b745c43afb2；
 *     本岗 10:44 实跑 `validate --unit U01` → **11/11｜error 0**（V1 已 PASS）。
 * ⇒ 但**「v1.9」这个版本号已对应过两个不同字节态**（非法枚举态 / 合规态），
 *   任何只凭版本号比对的下游都会踩到歧义 ⇒ 本脚本把终态锁进 **v1.10**，
 *   并按 **Q87 A 路径**（U01 已于 2026-10-23 01:28 锁定）做**追加式登记复验**：
 *   **不重落锁**（D11 自身 status 字段与 D18 的 locked_at／locked_by／lock_state 一律不重写），
 *   只在**目标镜位的 note 末尾追加**一段合规复验留痕（Q30／S11：只追加、不改写）。
 *
 * ── 本脚本改什么（变更清单＝2 条）────────────────────────────────────────────
 *   C01  `units/U01/D11.json` · version ：v1.9 → v1.10
 *   C02  `units/U01/D11.json` · ep7 镜3（g27）· note ：**末尾追加**一段
 *        「枚举合规复验」留痕（原文 343 字符逐字保留，只增不改）
 *   ⇒ **camera_angle 一律不动**（保持「主观视角」）；全库其余 31 镜零变化。
 *
 * ── 治理要点（与 U02-R34 裁定一致）──────────────────────────────────────────
 *   ① 变更清单 ＝ CHANGE_MANIFEST（2 条）；断言点清单 ＝ ASSERT_MANIFEST（20 条，逐条标来源）。
 *   ② 版本冻结门：盘上 ＝ 前提版本 → 执行；＝ 目标版本 → `[NO-OP]` exit 0；
 *      盘上已**演进**（版本高于目标）→ `[NO-OP]` exit 0（**不回退**，避 D18 Q82 的静默回退）；
 *      盘上早于前提版本 → exit 3（前置未落，不越序）。`--force` 为 Q64 逃生口。
 *   ③ 计数单位（Q57）：一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`。
 *      退出码：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝｜3 前置版本不满足。
 */

import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D11.json");

const FROM_V = "v1.9";
const TO_V = "v1.10";
const SCRIPT_ID = "patch_D11_v20_g27_enum_final";

/** 目标镜位三元组唯一定位 */
const TARGET_EP = 7;
const TARGET_SHOT = 3;
const TARGET_GSN = 27;

/** `03_规格/schema.json` 的 cameraAngle 七选一闭枚举（V1 判据真源） */
const ANGLE_ENUM_VALUES = ["平视", "俯视", "仰视", "顶视", "过肩", "主观视角", "客观跟拍"];
/** 本镜的 camera_angle 合法值（0.35 m 离轴不改变其角度词表归类） */
const ANGLE_ENUM = "主观视角";

/** 目标镜位 note 的原文前缀（v1.9 之前就有的那段，逐字不改写 —— S11） */
const ORIG_NOTE =
  "骨纹为体表表现，不破体、不见皮下骨骼（D07 scene_needs／D10 母题 M02）。"
  + "归一度读数本集仍为 0.5%——一纹权柄上限 30 秒的单体近身焚斑不推读数（D05 T20）。";

/** 追加段必须逐字含有的若干项（各自标来源，见断言点清单） */
const REQUIRED_IN_APPEND = [
  "camera_angle ＝「主观视角」（schema 七选一闭枚举合法值）",
  "白模层几何分离 0.35 m 的事实已知悉，枚举口径不变",
  "本条 note 为该镜视点口径真源",
  "locked_at／locked_by／lock_state 一律不重写",
];

/** note 末尾追加段（只追加，不改写原文 —— S11／Q30） */
const NOTE_APPEND =
  "📌 枚举合规复验（2026-10-23 10:5x，D11 属主；U01 已于 01:28 锁定，本段为锁后**追加式登记复验**，"
  + "locked_at／locked_by／lock_state 一律不重写）：本镜 camera_angle ＝「主观视角」（schema 七选一闭枚举合法值）"
  + "——本轮一度写成自由文本「近似 POV（视点代表位）」，因该取值不在 03_规格/schema.json 的 cameraAngle 枚举内"
  + "（硬闸 V1 判 error 1、U01 10/11），已回滚并按 schema 合规形态落地："
  + "白模层几何分离 0.35 m 的事实已知悉，枚举口径不变；"
  + "几何事实与「近似 POV（视点代表位）」语义以本条 note 为该镜视点口径真源。";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D11.json · version",
    desc: "版本号 v1.9 → v1.10（终态锁进无歧义版本号；「v1.9」曾对应过非法枚举态与合规态两个字节态）",
    assert_ids: ["A04", "A09", "A17"],
  },
  {
    id: "C02",
    target: "units/U01/D11.json · ep7 镜3（g27）note",
    desc: "末尾追加「枚举合规复验」留痕段（原文 343 字符逐字保留，只增不改 —— S11／Q30）；"
      + "camera_angle 保持闭枚举合法值「主观视角」不变",
    assert_ids: [
      "A01", "A02", "A03", "A06", "A10", "A11", "A12", "A13", "A14", "A15",
      "A16", "A18", "A19", "A20",
    ],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化；条数必须与实际登记点数一一对应 —— 双射）
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C02（唯一定位）", desc: "全库恰有 1 个镜位同时满足 ep＝7／shot_id＝3／global_shot_no＝27" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "目标镜位改前 camera_angle ＝「主观视角」" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C02（原文只追加不改写）", desc: "目标镜位改前 note 以原文为前缀、且含 v1.9 的语义标注与 0.35 m 依据" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C01", desc: "改前 version ＝ v1.9" },
  { id: "A05", phase: "pre", kind: "structure", source: "硬闸 V1 判据（cameraAngle 闭枚举）", desc: "改前全库每镜 camera_angle 均属 schema 七选一闭枚举（**V1 判据自证**）" },
  { id: "A06", phase: "pre", kind: "change", source: "变更清单 C02（防误伤同值镜头）", desc: "改前全库「主观视角」镜位数 ＝ 5" },
  { id: "A07", phase: "pre", kind: "structure", source: "硬闸 V1 判据（不得残留自由文本）", desc: "改前全库无任何 camera_angle 含「POV」等自由文本取值" },
  { id: "A08", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜／每集 45.0s／gsn 严格递增／共 32 镜）", desc: "结构四项改前全部成立" },
  { id: "A09", phase: "pre", kind: "change", source: "变更清单 C01", desc: "写回内容的 version ＝ v1.10" },
  { id: "A10", phase: "pre", kind: "change", source: "变更清单 C02（schema 合规）", desc: "改后目标镜位 camera_angle **未变**（仍为「主观视角」，未写入非法枚举值）" },
  { id: "A11", phase: "pre", kind: "change", source: "变更清单 C02（S11 只追加不重写）", desc: "改后目标镜位 note ＝ 原文 ＋ 追加段（以原文为前缀、长度只增）" },
  { id: "A12", phase: "pre", kind: "change", source: "变更清单 C02（总控派单指定留痕措辞）", desc: "追加段逐字含「白模层几何分离 0.35 m 的事实已知悉，枚举口径不变」" },
  { id: "A13", phase: "pre", kind: "change", source: "变更清单 C02（裁定语义标注要求）", desc: "追加段逐字含「本条 note 为该镜视点口径真源」" },
  { id: "A14", phase: "pre", kind: "change", source: "变更清单 C02（schema 合规声明）", desc: "追加段逐字含「camera_angle ＝「主观视角」（schema 七选一闭枚举合法值）」" },
  { id: "A15", phase: "pre", kind: "change", source: "变更清单 C02（Q87 A 路径）", desc: "追加段逐字含「locked_at／locked_by／lock_state 一律不重写」" },
  { id: "A16", phase: "pre", kind: "change", source: "变更清单 C02（防误伤）", desc: "除目标镜位 note 与顶层 version 外，全库逐镜逐字段零变化（含字段集合一致）" },
  { id: "A17", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.10" },
  { id: "A18", phase: "post", kind: "change", source: "变更清单 C02", desc: "落盘后回读目标镜位 note 以原文为前缀、长度只增、逐字含全部必需项" },
  { id: "A19", phase: "post", kind: "change", source: "变更清单 C02（回读独立复算；硬闸 V1 判据）", desc: "落盘后重新读盘：全库每镜 camera_angle 仍属七选一闭枚举，且无自由文本残留" },
  { id: "A20", phase: "post", kind: "change", source: "变更清单 C02（回读独立复算）", desc: "落盘后回读：除目标镜位 note 与顶层 version 外，全库逐镜逐字段零变化" },
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
G.assertPoint("A03",
  typeof target.note === "string"
  && target.note.startsWith(ORIG_NOTE)
  && target.note.includes("近似 POV（视点代表位）")
  && target.note.includes("机位与角色眼位分离 0.35 m")
  && target.note.includes("本条 note 为口径真源"),
  "目标镜位改前 note 不是「原文 ＋ v1.9 语义标注」形态");
G.assertPoint("A04", before.version === FROM_V, `改前 version ＝ ${before.version}（应为 ${FROM_V}）`);

// ── 全库 camera_angle 合法性（V1 判据自证）──
const allAngles = [];
for (const e of before.episodes) for (const s of e.shots) allAngles.push(s.camera_angle);
const badAngles = allAngles.filter((a) => !ANGLE_ENUM_VALUES.includes(a));
G.assertPoint("A05", badAngles.length === 0,
  `改前全库有 ${badAngles.length} 个 camera_angle 不属七选一闭枚举：${badAngles.join("｜")}`);
const freeTextAngles = allAngles.filter((a) => typeof a === "string" && a.includes("POV"));
G.assertPoint("A07", freeTextAngles.length === 0,
  `改前全库存在含「POV」的自由文本 camera_angle：${freeTextAngles.join("｜")}`);
const countAngle = (doc, val) => {
  let n = 0;
  for (const e of doc.episodes) for (const s of e.shots) if (s.camera_angle === val) n += 1;
  return n;
};
G.assertPoint("A06", countAngle(before, ANGLE_ENUM) === 5,
  `改前全库「${ANGLE_ENUM}」镜位数 ＝ ${countAngle(before, ANGLE_ENUM)}（应为 5）`);

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

// ── 构造改后内容（**只改顶层 version ＋ 目标镜位 note 末尾追加**；camera_angle 一律不动）──
const after = JSON.parse(src);
const t2 = after.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
const noteBefore = t2.note;
t2.note = `${noteBefore}${NOTE_APPEND}`;
after.version = TO_V;

G.assertPoint("A09", after.version === TO_V, `写回后 version ＝ ${after.version}（应为 ${TO_V}）`);
G.assertPoint("A10", t2.camera_angle === ANGLE_ENUM,
  `改后目标镜位 camera_angle ＝ ${t2.camera_angle}（应为 ${ANGLE_ENUM}，不得写入非法枚举值）`);
G.assertPoint("A11", t2.note.startsWith(noteBefore) && t2.note.length > noteBefore.length,
  "改后 note 不是「原文 ＋ 追加」形态");
G.assertPoint("A12", t2.note.includes(REQUIRED_IN_APPEND[1]),
  `追加段缺指定留痕措辞：${REQUIRED_IN_APPEND[1]}`);
G.assertPoint("A13", t2.note.includes(REQUIRED_IN_APPEND[2]), "追加段缺「本条 note 为该镜视点口径真源」");
G.assertPoint("A14", t2.note.includes(REQUIRED_IN_APPEND[0]), "追加段缺 schema 合规声明");
G.assertPoint("A15", t2.note.includes(REQUIRED_IN_APPEND[3]), "追加段缺 Q87 A 路径（不重落锁）声明");

// ── 全库零变化核验（除目标镜位 note 与顶层 version）──
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
G.assertPoint("A16", diffs.length === 0, `除目标镜位 note 外还有字段变化：${diffs.join(", ")}`);

// ── 写盘前收口（pre 阶段双射校验：清单条数 == 实际断言点数；不通过即拒绝写盘）──
G.finishPre();

// ── 写盘前备份（备份统一落 reports/_bak_*，不在 units/ 内写备份）──
const now = new Date();
const p2 = (n) => String(n).padStart(2, "0");
const ts = `${now.getFullYear()}${p2(now.getMonth() + 1)}${p2(now.getDate())}-`
  + `${p2(now.getHours())}${p2(now.getMinutes())}${p2(now.getSeconds())}`;
const bakDir = resolve(HERE, `../reports/_bak_D11_U01_v20_g27_enum_${ts}`);
mkdirSync(bakDir, { recursive: true });
copyFileSync(TARGET, resolve(bakDir, "D11.json"));
console.log(`   · 备份 → reports/_bak_D11_U01_v20_g27_enum_${ts}/D11.json`);

// ── 落盘（序列化格式与现盘逐字节一致：2 空格缩进 ＋ 末尾换行）──
writeFileSync(TARGET, `${JSON.stringify(after, null, 2)}\n`, "utf8");

// ── 写后回读独立复算 ──
const reread = JSON.parse(readFileSync(TARGET, "utf8"));
G.assertPoint("A17", reread.version === TO_V, `落盘后回读 version ＝ ${reread.version}（应为 ${TO_V}）`);
const rt = reread.episodes.find((e) => e.ep === TARGET_EP).shots.find((s) => s.shot_id === TARGET_SHOT);
G.assertPoint("A18",
  rt.note.startsWith(noteBefore) && rt.note.length > noteBefore.length
  && REQUIRED_IN_APPEND.every((x) => rt.note.includes(x))
  && rt.camera_angle === ANGLE_ENUM,
  "落盘后回读的目标镜位不满足「原文前缀 ＋ 只增 ＋ 必需项齐全 ＋ 枚举合法」");
const rereadAngles = [];
for (const e of reread.episodes) for (const s of e.shots) rereadAngles.push(s.camera_angle);
const rereadBad = rereadAngles.filter((a) => !ANGLE_ENUM_VALUES.includes(a));
const rereadFree = rereadAngles.filter((a) => typeof a === "string" && a.includes("POV"));
G.assertPoint("A19", rereadBad.length === 0 && rereadFree.length === 0,
  `落盘后回读仍有非法/自由文本 camera_angle：${[...rereadBad, ...rereadFree].join("｜")}`);
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
    if (isTarget && f === "note") continue;
    if (JSON.stringify(b[f]) !== JSON.stringify(a[f])) rdiffs.push(`${k}.${f}`);
  }
}
G.assertPoint("A20", rdiffs.length === 0, `落盘后回读发现额外字段变化：${rdiffs.join(", ")}`);

// ── 写后收口（post 阶段双射校验）──
G.finishPost();

console.log(`✅ D11 U01 ${FROM_V} → ${TO_V} 落盘完成（camera_angle 保持「${ANGLE_ENUM}」，note 追加合规复验留痕）`);
