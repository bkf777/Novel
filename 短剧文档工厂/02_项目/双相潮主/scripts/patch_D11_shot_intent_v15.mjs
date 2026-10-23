#!/usr/bin/env node
/**
 * D11 v1.4 → v1.5：D08 v1.7 shot_intent 逐镜反查落盘
 *
 * 依据：台本编剧 D08 v1.7 新增 23 条 body[].shot_intent「必须被看见」层。
 * 本补丁只动 4 个镜位字段 + 版本号，其余字段（global_shot_no / scene_code /
 * duration_sec / shot_size / camera_angle / lens_mm / movement / dialogue / sfx /
 * needs_image / minor_present / quad_segment）一字段不动。
 *
 * ─────────────────────────────────────────────────────────────────
 * 治理改造（2026-10-23 10:2x，分镜导演岗）
 * ─────────────────────────────────────────────────────────────────
 * 企划合规 U02-R34 裁定：一次性 patch 脚本须自带「变更清单 ＋ 断言点清单」并于
 * **写盘前**校验（清单条数 ＝ 实际断言点数）；再执行必须幂等或 `[NO-OP]` exit 0，
 * **不得以「断言失败」表达「已演进、无需执行」**；写交付物 JSON 仍适用 Q64 版本守卫。
 *
 * 本脚本改造要点：
 *   ① 变更清单 ＝ CHANGE_MANIFEST（7 条，逐条声明改哪个对象的哪处、对应哪些断言点）；
 *      断言点清单 ＝ ASSERT_MANIFEST（16 条，逐条标来源、标阶段、标类别）。
 *   ② 版本冻结门：**盘上版本 ≠ 前提版本时一律不写盘**。
 *      —— 已执行过（＝目标版本）／已演进（超过目标版本）→ `[NO-OP]` exit 0；
 *      —— 早于前提版本 → exit 3（前置未落，不越序执行）。
 *      —— `--force` 可越门（Q64 逃生口；仅管版本序，内容差异不得靠它放行）。
 *   ③ 计数单位（Q57）：**一条断言点 ＝ 本脚本内恰好一处「断言登记语句」被求值一次**。
 *      循环内的逐项判定先聚合成一次求值再登记，避免同一 id 被登记多次。
 *      ⚠️ 本文件注释与字符串字面里不出现该登记语句的函数名（Q56 token 计数纪律）。
 *   ④ 守卫逻辑统一外置到 `scripts/_patch_guard.mjs`（任何岗可复用，无需改本文件）。
 *      退出码语义：0 成功/NO-OP｜1 内容断言不通过｜2 治理层拒绝（清单不一致）｜3 前置版本不满足。
 *
 * 纪律：逐处带命中数断言，对不上即中止不写盘；全部通过后一次性写回。
 */

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { createGuard } from "./_patch_guard.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(HERE, "../units/U01/D11.json");

const FROM_V = "v1.4";
const TO_V = "v1.5";
const SCRIPT_ID = "patch_D11_shot_intent_v15";

// ─────────────────────────────────────────────────────────────────
// 变更清单（结构化）：改什么 → 对应哪些断言点
// ─────────────────────────────────────────────────────────────────
const CHANGE_MANIFEST = [
  {
    id: "C01",
    target: "units/U01/D11.json · version",
    desc: "版本号 v1.4 → v1.5",
    assert_ids: ["A01", "A08", "A09", "A14", "A15"],
  },
  {
    id: "C02",
    target: "units/U01/D11.json · ep5 镜3 visual_facts",
    desc: "远景轮廓层入画霜白（对齐 D08 body[8]/[9] + shot_intent）",
    assert_ids: ["A02", "A09", "A15"],
  },
  {
    id: "C03",
    target: "units/U01/D11.json · ep5 镜3 note",
    desc: "追加 D08 v1.7 shot_intent 反查留痕（原合规裁决留痕保留）",
    assert_ids: ["A03", "A09", "A15"],
  },
  {
    id: "C04",
    target: "units/U01/D11.json · ep8 镜3 visual_facts",
    desc: "正面表达褪尽的斑痕可辨（对齐 D08 body[7] + shot_intent）",
    assert_ids: ["A04", "A09", "A15"],
  },
  {
    id: "C05",
    target: "units/U01/D11.json · ep8 镜3 note",
    desc: "追加 D08 v1.7 shot_intent 反查留痕",
    assert_ids: ["A05", "A09", "A15"],
  },
  {
    id: "C06",
    target: "units/U01/D11.json · ep2 镜2 note",
    desc: "追加 shot_intent 过程性要求的 D12 承接指向（正文不改）",
    assert_ids: ["A06", "A09", "A15"],
  },
  {
    id: "C07",
    target: "units/U01/D11.json · ep3 镜3 note",
    desc: "追加 shot_intent 构图约束的 D12 承接指向（正文不改）",
    assert_ids: ["A07", "A09", "A15"],
  },
];

// ─────────────────────────────────────────────────────────────────
// 断言点清单（结构化）：每条必标来源 / 阶段 / 类别
//   phase: pre = 写盘前｜post = 写后回读
//   kind : change = 绑定某一处改动｜structure = 整体结构未被破坏
// ─────────────────────────────────────────────────────────────────
const ASSERT_MANIFEST = [
  { id: "A01", phase: "pre", kind: "change", source: "变更清单 C01", desc: "补丁 #1 版本串在源文件恰好命中 1 次" },
  { id: "A02", phase: "pre", kind: "change", source: "变更清单 C02", desc: "补丁 #2 ep5 镜3 visual_facts 旧串恰好命中 1 次" },
  { id: "A03", phase: "pre", kind: "change", source: "变更清单 C03", desc: "补丁 #3 ep5 镜3 note 旧串恰好命中 1 次" },
  { id: "A04", phase: "pre", kind: "change", source: "变更清单 C04", desc: "补丁 #4 ep8 镜3 visual_facts 旧串恰好命中 1 次" },
  { id: "A05", phase: "pre", kind: "change", source: "变更清单 C05", desc: "补丁 #5 ep8 镜3 note 旧串恰好命中 1 次" },
  { id: "A06", phase: "pre", kind: "change", source: "变更清单 C06", desc: "补丁 #6 ep2 镜2 note 旧串恰好命中 1 次" },
  { id: "A07", phase: "pre", kind: "change", source: "变更清单 C07", desc: "补丁 #7 ep3 镜3 note 旧串恰好命中 1 次" },
  { id: "A08", phase: "pre", kind: "change", source: "变更清单 C01", desc: "写回内容的 version ＝ v1.5" },
  { id: "A09", phase: "pre", kind: "change", source: "变更清单 C01–C07", desc: "写回内容中 7 处新串各命中 1 次、7 处旧串各残留 0 次" },
  { id: "A10", phase: "pre", kind: "structure", source: "D11 模板结构约定（8 集 × 4 镜）", desc: "每集镜数 ＝ 4" },
  { id: "A11", phase: "pre", kind: "structure", source: "D11 模板结构约定（每集镜时 45.0s）", desc: "每集镜时求和 ＝ 45" },
  { id: "A12", phase: "pre", kind: "structure", source: "D11 模板结构约定（global_shot_no 严格递增）", desc: "global_shot_no 严格递增" },
  { id: "A13", phase: "pre", kind: "structure", source: "D11 模板结构约定（全集 32 镜）", desc: "总镜数 ＝ 32" },
  { id: "A14", phase: "post", kind: "change", source: "变更清单 C01", desc: "落盘后回读的 version ＝ v1.5" },
  { id: "A15", phase: "post", kind: "change", source: "变更清单 C01–C07", desc: "落盘后回读内容中 7 处新串各命中 1 次、7 处旧串各残留 0 次" },
  { id: "A16", phase: "post", kind: "structure", source: "D11 模板结构约定（重新读盘独立复算）", desc: "落盘后重新读盘解析，32 镜 / 4 镜每集 / 45s 每集 / 严格递增全部成立" },
];

/** [旧串, 新串] —— 旧串必须在文件中恰好命中 1 次 */
const PATCHES = [
  // ── 1. 版本号 ──────────────────────────────────────────────
  [
    '"version": "v1.4",',
    '"version": "v1.5",',
  ],

  // ── 2. ep5 shot3 visual_facts：远景轮廓层入画霜白 ────────────
  [
    '"visual_facts": "处置台在远景里亮起一圈白灯；处置区只余被处置者的剪影，轮廓被白灯边缘光勾出；处置区之外是钢板围栏与推土机的深色轮廓；右下角常驻白色角标：AI 生成。",',
    '"visual_facts": "处置台在远景里亮起一圈白灯；处置区只余被处置者的剪影，轮廓被白灯边缘光勾出，剪影是被束具缚住的形状；剪影周身覆着一层霜白，霜白自肩部向下漫开、边缘浮起一层冷白雾气，在远景里成块可辨；霜白里不见斑痕形状，霜白只作轮廓上的成块色块，不显皮肤纹理；面部与身体表面不可辨，镜头不落到人体细节；处置区之外是钢板围栏与推土机的深色轮廓；右下角常驻白色角标：AI 生成。",',
  ],

  // ── 3. ep5 shot3 note：追加 v1.7 反查留痕 ──────────────────
  [
    '"note": "⚠️ 上游裁决改写：D08 正文原有「手背覆着霜灰」「灰斑蔓延、边缘浮起白霜」属人体细节，与同文件合规增量段「被处置者只保留远景剪影与白灯轮廓，镜头不落到人体细节」及 D03 R03/L2/L4 冲突。按合规增量段执行，本镜不入画霜灰与灰斑蔓延；叶红衣「别管我。」在远景剪影内以气音交付，人物不可辨识面部。以上游合规裁决为准。"',
    '"note": "⚠️ 上游裁决改写（2026-10-22 原版）：D08 正文原有「手背覆着霜灰」「灰斑蔓延、边缘浮起白霜」属人体细节，与同文件合规增量段「被处置者只保留远景剪影与白灯轮廓，镜头不落到人体细节」及 D03 R03/L2/L4 冲突，按合规增量段执行，本镜不入画霜灰与灰斑蔓延。📌 D08 v1.7 shot_intent 反查修订（2026-10-23）：台本编剧新增镜头意图层，body[8]/[9] 写入「处置台底下，叶红衣被束具缚住，周身覆着一层霜白，远景只见轮廓」「霜白从她肩上向下漫开，边缘浮起一层白雾，不见斑痕形状」，shot_intent 要求「叶红衣周身的霜白必须被看见，观众要认出她，但只到轮廓为止」。按「远景体表色块 ≠ 人体细节／受苦特写」判定合规，本镜据此入画霜白与霜层冷白雾气；被缚束具形状与霜白成块可辨，是观众认出叶红衣的唯一依据；面部、身体表面与皮肤纹理仍不可辨，霜灰与灰斑仍不入画。叶红衣「别管我。」在远景剪影内以气音交付，人物面部不可辨识。以上游合规裁决为准。"',
  ],

  // ── 4. ep8 shot3 visual_facts：正面表达斑痕可辨 ─────────────
  [
    '"visual_facts": "获救的灰斑者沿钢板墙排成长队，队伍自画面纵深排开；队列末尾有人把袖子拉过手腕，褪尽的斑痕只在远景里呈现，看不到任何人的面部；队列里没人说话，钢板上的脚步一前一后；陆沉抬起右腕，黑白游龙纹在腕侧亮起，双色火焰贴着骨纹翻了一下；右下角常驻白色角标：AI 生成。",',
    '"visual_facts": "获救的灰斑者沿钢板墙排成长队，队伍自画面纵深排开；队列末尾有人把袖子拉过手腕，腕上褪尽的斑痕褪成一小块浅色，在远景里可辨，是队伍已被救下的可见证据；看不到任何人的面部，队列的脸一律不入镜；队列里没人说话，钢板上的脚步一前一后；陆沉抬起右腕，黑白游龙纹在腕侧亮起，双色火焰贴着骨纹翻了一下；右下角常驻白色角标：AI 生成。",',
  ],

  // ── 5. ep8 shot3 note：追加 v1.7 反查留痕 ──────────────────
  [
    '"note": "⚠️ 依 D08 合规增量段与 D03 L2/L4/L5：获救者的斑痕只在队列远景中呈现，不给单人面部与伤处特写，冲击由音效与队列规模承担；本镜已把 D08 正文的「露出褪尽的斑痕」改为远景化表述。"',
    '"note": "⚠️ 依 D08 合规增量段与 D03 L2/L4/L5：获救者的斑痕只在队列远景中呈现，不给单人面部与伤处特写，冲击由音效与队列规模承担。📌 D08 v1.7 shot_intent 反查修订（2026-10-23）：shot_intent 要求「褪尽的斑痕必须被看见，这是『救下来』的可见证据」，故本镜把斑痕从「只在远景里呈现」的被动表述改为正面可见——腕上褪尽的斑痕褪成一小块浅色、在远景里可辨；同时保持不给单人面部、不给伤处特写。「袖子拉过手腕」只写袖子越过腕部，斑痕仍留在远景画面里。以上游合规裁决为准。"',
  ],

  // ── 6. ep2 shot2 note：追加 shot_intent 过程性要求的 D12 承接指向（正文不改） ──
  [
    '"note": "本镜是 D07 段3 所述「A-2 段尾焊门收尾画面」的素材来源，与镜3 互为并行交叉剪辑配对。28.0~40.0s 段内画面在镜3（A-3 勘察）与本镜尾料之间交替，交替点见 D16 切点表；两镜时长按各自独占屏时间计，全集求和仍为 45.0s。"',
    '"note": "本镜是 D07 段3 所述「A-2 段尾焊门收尾画面」的素材来源，与镜3 互为并行交叉剪辑配对。28.0~40.0s 段内画面在镜3（A-3 勘察）与本镜尾料之间交替，交替点见 D16 切点表；两镜时长按各自独占屏时间计，全集求和仍为 45.0s。📌 D08 v1.7 shot_intent 反查（2026-10-23）：body[5] 要求「从焊缝成形到闸门合拢」的过程可见；本镜 visual_facts 已给出该过程的起点与终点（焊起简易闸门、焊花落在卷帘门），过程性的「焊缝逐渐成形」由 D12 卡 C-006 的 video_prompt 承接落实，D11 与 D12 口径一致，正文不改。"',
  ],

  // ── 7. ep3 shot3 note：追加 shot_intent 构图约束的 D12 承接指向（正文不改） ──
  [
    '"note": "骨纹为体表发光纹路＋轮廓光，不破体、不见皮下骨骼（D03 R05／D10 母题 M02）。归一度 0.5% 为 ep003 一纹初醒的锚点值（D05 T20）。火焰只有黑与白两色（D10 一致性规则「火焰唯一色」）。"',
    '"note": "骨纹为体表发光纹路＋轮廓光，不破体、不见皮下骨骼（D03 R05／D10 母题 M02）。归一度 0.5% 为 ep003 一纹初醒的锚点值（D05 T20）。火焰只有黑与白两色（D10 一致性规则「火焰唯一色」）。📌 D08 v1.7 shot_intent 反查（2026-10-23）：body[8] 要求骨纹第一次亮起「必须给到独立可辨的视觉呈现，不与人体同框混作」；本镜为 85mm 近景＋主观视角、视野只收腕部与手背，骨纹独占画面主体，D12 卡 C-011 的 image_prompt 已锁定「右腕特写」，构图口径一致，正文不改。"',
  ],
];

/** 补丁序号 → 断言点 id 的显式映射（与 ASSERT_MANIFEST 逐条对应） */
const PATCH_ASSERT_IDS = ["A01", "A02", "A03", "A04", "A05", "A06", "A07"];

const G = createGuard({
  scriptId: SCRIPT_ID,
  targetPath: TARGET,
  fromVersion: FROM_V,
  toVersion: TO_V,
  changeManifest: CHANGE_MANIFEST,
  assertManifest: ASSERT_MANIFEST,
});

// ── 版本冻结门（不满足即结束进程，绝不进入写盘路径）──
G.freeze();

const src = readFileSync(TARGET, "utf8");

// ── 断言阶段：任何一处命中数 ≠ 1 即中止，不写盘 ──
// 循环内逐项判定 → 每项各自登记一条断言点（id 互不相同，不违反双射）
const hitCounts = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const oldStr = PATCHES[i][0];
  const count = src.split(oldStr).length - 1;
  hitCounts.push(count);
  G.assertPoint(
    PATCH_ASSERT_IDS[i],
    count === 1,
    `补丁 #${i + 1} 命中 ${count} 次（应为 1）。旧串前 80 字：${oldStr.slice(0, 80)}`,
  );
}

// ── 写回内容计算（尚未落盘）──
let out = src;
for (const [oldStr, newStr] of PATCHES) out = out.replace(oldStr, newStr);

const parsed = JSON.parse(out);
G.assertPoint("A08", parsed.version === TO_V, `写回后 version ＝ ${parsed.version}（应为 ${TO_V}）`);

// 聚合校验：7 处新串各命中 1 次、旧串各残留 0 次
const residue = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const [oldStr, newStr] = PATCHES[i];
  if (out.split(newStr).length - 1 !== 1) residue.push(`补丁 #${i + 1} 新串命中数异常`);
  if (out.split(oldStr).length - 1 !== 0) residue.push(`补丁 #${i + 1} 旧串仍有残留`);
}
G.assertPoint("A09", residue.length === 0, residue.join("；"));

// ── 结构复核（写盘前，从写回内容独立复算）──
// 四类问题**各自独立收集**，互不串台（用子串分流会让「总镜数」误触发「每集镜数」断言）
const countIssues = [];   // 每集镜数
const sumIssues = [];     // 每集镜时求和
const incIssues = [];     // global_shot_no 严格递增
const totalIssues = [];   // 全集总镜数
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
G.assertPoint("A10", countIssues.length === 0, countIssues.join("；"));
G.assertPoint("A11", sumIssues.length === 0, sumIssues.join("；"));
G.assertPoint("A12", incIssues.length === 0, incIssues.join("；"));
G.assertPoint("A13", totalIssues.length === 0, totalIssues.join("；"));

// ── 写盘前收口：清单双射校验 + 失败汇总（不通过则不写盘）──
G.finishPre();

writeFileSync(TARGET, out, "utf8");

// ── 写后回读 ──
const back = readFileSync(TARGET, "utf8");
const backParsed = JSON.parse(back);
G.assertPoint("A14", backParsed.version === TO_V, `回读 version ＝ ${backParsed.version}（应为 ${TO_V}）`);

const backResidue = [];
for (let i = 0; i < PATCHES.length; i += 1) {
  const [oldStr, newStr] = PATCHES[i];
  if (back.split(newStr).length - 1 !== 1) backResidue.push(`补丁 #${i + 1} 新串命中数异常`);
  if (back.split(oldStr).length - 1 !== 0) backResidue.push(`补丁 #${i + 1} 旧串仍有残留`);
}
G.assertPoint("A15", backResidue.length === 0, backResidue.join("；"));

// 回读后**独立复算**结构（不复用写盘前的判定结果）
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
G.assertPoint("A16", backIssues.length === 0, backIssues.join("；"));

G.finishPost();

console.log(`✅ D11 ${FROM_V} → ${TO_V} 落盘：${PATCHES.length} 处补丁，32 镜 / 每集 4 镜 / 每集镜时 45.0s / global_shot_no 1→${backPrev} 全部复核通过。`);
console.log(`   文件：${TARGET}`);
console.log(`   字节：${Buffer.byteLength(back, "utf8")}`);
console.log(`   变更清单 ${CHANGE_MANIFEST.length} 条；断言点清单 ${ASSERT_MANIFEST.length} 条（写盘前 ${ASSERT_MANIFEST.filter((a) => a.phase === "pre").length} 条 ＋ 写后 ${ASSERT_MANIFEST.filter((a) => a.phase === "post").length} 条），实际登记 ${ASSERT_MANIFEST.length} 处，双射成立。`);
