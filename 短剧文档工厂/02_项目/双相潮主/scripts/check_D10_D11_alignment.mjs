#!/usr/bin/env node
/**
 * D10 v1.6 × D11 v1.5 全口径程序化核查（台本编剧 R-027 反查的 D10 侧正式核查项）
 *
 * 目的：D08 v1.7 shot_intent 要求核对「与 D10/D11 既有口径是否冲突」。
 * 本脚本对 D11 全部 32 镜逐镜验证 D10 camera_language 的每一条硬约束，
 * 重点覆盖本轮改动所在的 ep5 镜3 / ep8 镜3。
 *
 * 只读脚本：不写任何文件。
 *
 * 【2026-10-23 修】打印行双 v 缺陷：第 156 行原为 `D10 v${D10.version} × D11 v${D11.version}`，
 * 而 version 字段本身已带 `v` → 实印 `D10 vv1.11 × D11 vv1.8`。
 * 根因在**脚本**（非人工转述环节），owner＝分镜导演（脚本属主）。
 * 修法＝**归一化 helper `vtag()`**（源串带不带 v 都输出恰好一个 v），
 * 而非单纯删 `v` —— 后者只是把「模板硬编码前缀」的隐患留在原地。
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const P = (p) => resolve(HERE, "..", p);

const D10 = JSON.parse(readFileSync(P("shared/D10.json"), "utf8"));
const D11 = JSON.parse(readFileSync(P("units/U01/D11.json"), "utf8"));
const cl = D10.camera_language;

// ── 版本号归一化（双 v 缺陷族修复，2026-10-23）──
// 源串 `D10.version`／`D11.version` 本身已带 `v`（现盘 v1.11／v1.8），
// 打印模板若再硬拼 `v` 前缀即产出 `vv1.11`（同 §一百二十四.8 的 `vv1.87` 同源缺陷）。
// 故统一收敛为「恰好一个 v」，不依赖源串是否带前缀。
const vtag = (x) => { const s = String(x); return /^v/i.test(s) ? s : "v" + s; };

const shots = [];
for (const e of D11.episodes) for (const s of e.shots) shots.push({ ep: e.ep, ...s });

const fails = [];
const notes = [];
const F = (ep, sid, rule, why) => fails.push(`ep${ep} 镜${sid} 【${rule}】${why}`);

// ── 1. shot_size 必须在 D10 shot_size_ladder 内（D10 未列「大特写」） ──
for (const s of shots) {
  if (!cl.shot_size_ladder.includes(s.shot_size)) {
    F(s.ep, s.shot_id, "shot_size_ladder",
      `「${s.shot_size}」不在 D10 ${JSON.stringify(cl.shot_size_ladder)}（D10 ladder 共 ${cl.shot_size_ladder.length} 档，未列大特写）`);
  }
}

// ── 2. lens 只用 D10 允许的 24/35/50/85 ──
for (const s of shots) {
  if (![24, 35, 50, 85].includes(s.lens_mm)) {
    F(s.ep, s.shot_id, "lens", `lens_mm=${s.lens_mm} 不在 D10 允许的 24/35/50/85`);
  }
}

// ── 3. banned：贴脸突发惊吓 / 人体内部细节特写 → 近景及更近的镜头不得贴脸 ──
for (const s of shots) {
  const close = ["近景", "特写", "大特写"].includes(s.shot_size);
  if (close && s.camera_angle === "主观视角" && s.shot_size === "特写") {
    // 特写＋主观视角：检查是否为数据界面而非人体
    const isUI = /面板|界面|读数|播报|刊头/.test(s.visual_facts);
    if (!isUI) F(s.ep, s.shot_id, "banned", "特写＋主观视角且非数据界面，存在贴脸风险");
  }
}

// ── 4. banned：运动相机式「贴地」跟拍导致「主体出框」 ──
//   D11 JSON 无「机位高度」字段，「贴地」不可程序化判定，故拆成两部分：
//   4a 可判定：跟/移类运镜且 visual_facts 明写贴地机位或主体出框 → 硬失败
//   4b 不可判定：客观跟拍 + 跟/移 → 降级为人工复核项，交人工确认机位高度
for (const s of shots) {
  if (["跟", "移"].includes(s.movement)) {
    if (/贴地|出框|运动相机/.test(s.visual_facts)) {
      F(s.ep, s.shot_id, "banned", `跟/移类运镜且画面写明贴地或出框：${s.shot_size}/${s.lens_mm}mm`);
    }
    if (s.camera_angle === "客观跟拍") {
      notes.push(`ep${s.ep} 镜${s.shot_id} 客观跟拍 + ${s.movement}（${s.shot_size}/${s.lens_mm}mm）：D10 banned 限定「贴地」，D11 无机位高度字段，需人工确认机位高度非贴地`);
    }
  }
}

// ── 5. banned：长时间静止无信息镜 → 固定机位镜必须有足量画面信息 ──
const FIXED_MIN_FACTS = 3;
for (const s of shots) {
  if (s.movement === "固定") {
    const facts = s.visual_facts.split(/[；;]/).filter((x) => x.trim().length > 0).length;
    if (facts < FIXED_MIN_FACTS) {
      F(s.ep, s.shot_id, "banned", `固定机位但仅 ${facts} 项画面事实（阈值 ${FIXED_MIN_FACTS}），疑似无信息镜`);
    }
  }
}

// ── 6. shot_size_rule：特写只给道具与数据界面 ──
for (const s of shots) {
  if (s.shot_size === "特写") {
    const ok = /面板|界面|读数|播报|刊头|屏|字/.test(s.visual_facts) ||
               /钢钎|钎身|道具|器|具/.test(s.visual_facts);
    if (!ok) F(s.ep, s.shot_id, "shot_size_rule", "特写镜既非数据界面也非道具");
    else notes.push(`ep${s.ep} 镜${s.shot_id} 特写 → ${/面板|界面|读数|播报|刊头|屏|字/.test(s.visual_facts) ? "数据界面类" : "道具类"}，符合 shot_size_rule`);
  }
}

// ── 7. shot_size_rule：大特写不用于人体痛苦表情 ──
for (const s of shots) {
  if (s.shot_size === "大特写" && /痛苦|表情|惨|痛/.test(s.visual_facts)) {
    F(s.ep, s.shot_id, "shot_size_rule", "大特写用于人体痛苦表情");
  }
}

// ── 8. rhythm：4 镜/集、镜时严格等于 D07 段界、每集 45s ──
for (const e of D11.episodes) {
  if (e.shots.length !== 4) F(e.ep, "-", "rhythm", `镜数 ${e.shots.length} ≠ 4`);
  const sum = e.shots.reduce((a, s) => a + s.duration_sec, 0);
  if (sum !== 45) F(e.ep, "-", "rhythm", `镜时求和 ${sum} ≠ 45`);
  if (e.duration_sum_sec !== 45) F(e.ep, "-", "rhythm", `duration_sum_sec ${e.duration_sum_sec} ≠ 45`);
  // 镜时严格等于段界：quad_segment 递增且 1→4
  const segs = e.shots.map((s) => s.quad_segment);
  if (segs.join(",") !== "1,2,3,4") F(e.ep, "-", "rhythm", `quad_segment 序列 ${segs.join(",")} ≠ 1,2,3,4`);
}

// ── 9. safe_area：AI 生成角标常驻声明（每镜） ──
for (const s of shots) {
  if (!s.visual_facts.includes("AI 生成")) {
    F(s.ep, s.shot_id, "safe_area", "visual_facts 未声明右下角常驻「AI 生成」角标");
  }
}

// ── 10. 本轮改动的两镜专项：霜白/斑痕不得触 banned「人体内部细节特写」 ──
//   D11 的 visual_facts 允许否定式表述（"看不到任何人的面部"），故必须区分肯定／否定语境：
//   命中词前 8 字内若出现否定词，则该处是「不呈现」的意思，不算冲突。
const s53 = shots.find((s) => s.ep === 5 && s.shot_id === 3);
const s83 = shots.find((s) => s.ep === 8 && s.shot_id === 3);
const BODY_DETAIL = /皮肤纹理|毛孔|血管|肌理|骨骼|皮下|创口|创面|伤口|血肉|器官/;
const NEG = /不|无|不可辨|不见|不给|没有|未/;
const bodyDetailHits = (text) => {
  const out = [];
  let m;
  const re = new RegExp(BODY_DETAIL.source, "g");
  while ((m = re.exec(text)) !== null) {
    const before = text.slice(Math.max(0, m.index - 8), m.index);
    if (!NEG.test(before)) out.push({ word: m[0], ctx: text.slice(Math.max(0, m.index - 12), m.index + 12) });
  }
  return out;
};
for (const [s, label] of [[s53, "ep5 镜3"], [s83, "ep8 镜3"]]) {
  const hits = bodyDetailHits(s.visual_facts);
  if (hits.length) {
    F(s.ep, s.shot_id, "banned", `${label} 肯定语境出现人体内部细节词：${hits.map((h) => `${h.word}(…${h.ctx}…)`).join("、")}`);
  }
  if (s.shot_size !== "远景") {
    F(s.ep, s.shot_id, "shot_size_rule", `${label} 非远景（${s.shot_size}），与「只到轮廓」口径不符`);
  }
  if (!/面部|脸/.test(s.visual_facts)) {
    F(s.ep, s.shot_id, "banned", `${label} 未写明「面部不可辨」，远景遮挡口径缺项`);
  }
}

// ── 11. 远景镜不得出现可辨识面部 ──
for (const s of shots) {
  if (s.shot_size === "远景" && !/看不到|不可辨|一律不入|不给.*面部|面部不可辨/.test(s.visual_facts)) {
    notes.push(`ep${s.ep} 镜${s.shot_id} 远景未写「面部不可辨」表述（人工复核项，非硬失败）`);
  }
}

console.log(`D10 版本：${vtag(D10.version)}　D11 版本：${vtag(D11.version)}　受检镜数：${shots.length}`);
console.log(`D10 camera_language 逐条核查：shot_size_ladder / lens / banned×3 / shot_size_rule×3 / rhythm×3 / safe_area / 本轮改动专项×2`);
console.log("");
if (fails.length === 0) {
  console.log(`✅ 零冲突：D10 ${vtag(D10.version)} × D11 ${vtag(D11.version)} 全口径核查通过，无任何硬冲突。`);
} else {
  console.log(`❌ 检出 ${fails.length} 项冲突：`);
  for (const f of fails) console.log("   - " + f);
}
if (notes.length) {
  console.log(`\n人工复核项 ${notes.length} 条：`);
  for (const n of notes) console.log("   · " + n);
}
process.exit(fails.length === 0 ? 0 : 1);
