#!/usr/bin/env node
/**
 * D08 `shot_intent` × D11 `visual_facts` 覆盖核验（台本编剧岗自检脚本 · 2026-10-23 R-027）
 *
 * 为什么要有这个脚本：
 *   ① `shot_intent` 是交给 D11 逐镜反查的**契约**。下游说「23 条全落地」，
 *      本岗要能**独立复跑**复核，而不是采信转述 —— 校验器（validate.mjs）不覆盖这条轴。
 *   ② 下游 D11 每次升版，本岗核验必须**一律重跑**（团队铁律），所以要有可复跑脚本。
 *   ③ 顺带核 D11 `note` 里 `body[N]` 引文是否与 D08 现行 `shot_intent` 原文一致（失配＝待下游同步）。
 *
 * 口径：
 *   · `body[N]` 一律 **0-based**（= D08 JSON `episodes[].body[]` 数组下标 = D11/D16 note 的引用口径）。
 *   · 覆盖判定 = **D11 的 visual_facts 正面拍进了该条要求的内容**（不是「提到过」）。
 *   · 版本号**动态读取**，不钉死；脚本头注释里的版本快照仅供回溯，不作断言。
 *
 * 单元参数化（U02-R01 同款纪律 · 2026-10-23）：
 *   · `--unit <UNIT>` 决定读哪个单元的 D08／D11，**不硬编码 U01 路径**。
 *   · 映射表外置为 `shotintent_map_<UNIT>.mjs`（本岗维护）。映射文件不存在时
 *     **只跑 shot_intent 自身护栏**，跳过覆盖核验并明确提示，不假报「全绿」。
 *   · D11 尚未落盘的单元同理：跳过覆盖核验，护栏照跑。
 *
 * 用法：node scripts/check_D08_D11_shotintent.mjs [--unit U01]
 * 退出码：0 = 硬冲突 0；1 = 有硬冲突。
 */
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const P = (rel) => join(ROOT, rel);

const argv = process.argv.slice(2);
const unitIdx = argv.indexOf("--unit");
const UNIT = unitIdx !== -1 && argv[unitIdx + 1] && !argv[unitIdx + 1].startsWith("--")
  ? argv[unitIdx + 1]
  : "U01";

const D08 = JSON.parse(readFileSync(P(`units/${UNIT}/D08.json`), "utf8"));
const d11Path = P(`units/${UNIT}/D11.json`);
const D11 = existsSync(d11Path) ? JSON.parse(readFileSync(d11Path, "utf8")) : null;

// ── shot_intent → D11 承接镜位 + 该镜 visual_facts 必须正面出现的锚点 ──
//  映射表外置到 shotintent_map_<UNIT>.mjs（格式见该文件头注释）。
let MAP = [];
let mapNote = "";
const mapPath = join(dirname(fileURLToPath(import.meta.url)), `shotintent_map_${UNIT}.mjs`);
if (existsSync(mapPath)) {
  ({ MAP } = await import(mapPath));
} else {
  mapNote = `映射文件 shotintent_map_${UNIT}.mjs 不存在`;
}

const CAMERA_BAN = ["特写", "近景", "中景", "全景", "远景", "景深", "焦距", "机位", "运镜",
  "镜头", "视角", "构图", "长焦", "广角", "主观镜", "过肩", "俯拍", "仰拍", "平拍",
  "跟拍", "轨道", "摇臂", "镜头运动", "画面角度"];

const errors = [];
const warns = [];
const F = (ep, sid, tag, msg) => errors.push(`ep${ep} 镜${sid}: ${tag} —— ${msg}`);

const bodyOf = (ep) => D08.episodes.find((e) => e.ep === ep)?.body ?? [];
const shotOf = (ep, sid) =>
  D11?.episodes.find((e) => e.ep === ep)?.shots?.find((s) => s.shot_id === sid);

// ── 1. 覆盖核验：shot_intent 是否被 D11 visual_facts 正面拍到 ──
//    D11 未落盘 或 映射表未建立 → 跳过本节（不假报「全绿」），只跑第 2 节护栏。
let covered = 0;
const canCheckCoverage = Boolean(D11) && MAP.length > 0;
if (!canCheckCoverage) {
  const why = !D11 ? `D11 尚未落盘（units/${UNIT}/D11.json）` : mapNote;
  console.log(`⏭  跳过覆盖核验：${why}`);
}
for (const [ep, idx, sid, anchors] of (canCheckCoverage ? MAP : [])) {
  const b = bodyOf(ep)[idx];
  const s = shotOf(ep, sid);
  if (!b?.shot_intent) { F(ep, sid, "覆盖", `D08 ep${ep} body[${idx}] 无 shot_intent（0-based 口径）`); continue; }
  if (!s) { F(ep, sid, "覆盖", "D11 该集找不到此镜号"); continue; }
  const vf = String(s.visual_facts || "");
  const miss = anchors.filter((a) => !vf.includes(a));
  if (miss.length) {
    F(ep, sid, "覆盖", `body[${idx}] 要求「${b.shot_intent}」，但 visual_facts 缺锚点 ${JSON.stringify(miss)}`);
  } else {
    covered++;
    console.log(`  ✅ ep${ep} body[${idx}] → D11 镜${sid}（g${s.global_shot_no}）　${b.shot_intent}`);
  }
}

// ── 2. shot_intent 自身护栏：长度 / 越权镜头词 / 每集 ≥2 条 ──
for (const e of D08.episodes) {
  const n = e.body.filter((b) => b.shot_intent).length;
  if (n < 2) errors.push(`ep${e.ep}: shot_intent 仅 ${n} 条，少于每集最低 2 条`);
  for (const b of e.body) {
    if (!b.shot_intent) continue;
    if (b.shot_intent.length > 60) errors.push(`ep${e.ep}: shot_intent 超 60 字（${b.shot_intent.length}）`);
    for (const w of CAMERA_BAN) {
      if (b.shot_intent.includes(w)) errors.push(`ep${e.ep}: shot_intent 越权写镜头语言「${w}」`);
    }
  }
}

// ── 3. D11 note 的 body[N] 引文失配检测（纯引文对齐问题，报 warning）──
//    规则：note 里的 `body[N]` 必须在 D08 现行版本存在，且该条 shot_intent 或正文里
//    找得到 note 所引的「…」片段；找不到 = note 引的是旧措辞 → 待下游同步。
//
//    【Q65 · 2026-10-23 企划合规立规】本节判据**必须定位到有效引用位**，不得全文 grep 判成败：
//      ① 只取「**含该 body[N] 引用所在的 📌 段**」里的引文（按段定位），不用整条 note 的全部引文；
//      ② 抽取引文必须**括号配平** ——「」可**嵌套**（D08 现行 `shot_intent` 就有 **9 条**含嵌套，
//         如「…观众要能看清「2 小时 58 分」这个具体数值。」），朴素正则 `/「([^」]*)」/g`
//         会在内层 」 处截断 → 把正确引文误判成「失配」，进而产出**无据的催办**（Q65 所禁）；
//      ③ 判据无法定位（📌 段内抽不到可判引文）→ 标「**需人工判读**」，**不得**判「未同步」。
const BODYREF = /body\[(\d+)\]/g;
// 非全局副本：.test() 会推进全局正则的 lastIndex，不能直接复用 BODYREF。
const BODYREF_TEST = /body\[(\d+)\]/;
// 括号配平抽取「…」：遇「入栈、遇」出栈，depth 归 0 时取一段完整引文。
const balancedQuotes = (s) => {
  const out = [];
  let depth = 0, start = -1;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === "「") { if (depth === 0) start = i; depth++; }
    else if (c === "」") {
      depth--;
      if (depth === 0 && start >= 0) { out.push(s.slice(start + 1, i)); start = -1; }
    }
  }
  return out;
};
for (const e of (D11?.episodes ?? [])) {
  for (const s of e.shots ?? []) {
    const note = String(s.note || "");
    if (!note.includes("📌")) continue;
    // 【Q65① 的二次收紧 · 2026-10-23】有效引用位 = 从 📌 起到第一个段分隔标记为止。
    //   起因：Q65① 只要求「按 📌 段定位」，但本仓 D11 note 普遍把 📌 反查句与
    //   【引文订正】/【锚点订正】留痕段写在**同一串「｜」分隔的连续块**里 ——
    //   仅按 📌 切分仍会把**留痕段里的历史 body[N] 字面**当成活锚点 ⇒ 假阳性。
    //   实证：D11 U01 ep2 镜2 的留痕段引述「ep002 body[5]」，而活锚点已订正为 body[4]
    //   （分镜导演 12:4x 已改），活锚点判定全对，却被留痕字面误报「该条无 shot_intent」。
    const activeAll = note.slice(note.indexOf("📌"));
    const cut = activeAll.search(/[｜【]/);
    const activeSeg = cut >= 0 ? activeAll.slice(0, cut) : activeAll;
    const hasActiveRef = BODYREF_TEST.test(activeSeg);
    // 有效引用位里一个 body[N] 都没有 ⇒ 锚点只存在于留痕段 ⇒ 退回全 note 扫描，
    //   并显式标注「需人工判读」，**不得静默放过**（Q65③ / Q68：守卫须真能抓）。
    const scanScope = hasActiveRef ? activeSeg : note;
    if (!hasActiveRef) {
      warns.push(`ep${e.ep} 镜${s.shot_id}: 📌 有效引用位内未出现 body[N]（锚点只在留痕段）→ 需人工判读`);
    }
    for (const m of scanScope.matchAll(BODYREF)) {
      const idx = Number(m[1]);
      const b = bodyOf(e.ep)[idx];
      if (!b) { warns.push(`ep${e.ep} 镜${s.shot_id}: note 引用 body[${idx}]，D08 现版无此条目`); continue; }
      if (!b.shot_intent) { warns.push(`ep${e.ep} 镜${s.shot_id}: note 引用 body[${idx}]，该条无 shot_intent`); continue; }
      // 引文抽取范围 = 有效引用位（📌 段）；兜底情形退回按 📌 段定位。
      const seg = hasActiveRef
        ? activeSeg
        : (note.split("📌").slice(1).find((sg) => sg.includes(`body[${idx}]`)) ?? "");
      if (seg === "") {
        warns.push(`ep${e.ep} 镜${s.shot_id}: 判据无法定位有效引用位（📌 段内未找到 body[${idx}] 所在段）→ 需人工判读`);
        continue;
      }
      const quotes = balancedQuotes(seg).filter((q) => q.length >= 4);
      const hits = quotes.filter((q) => b.shot_intent.includes(q) || b.text.includes(q));
      if (!quotes.length) {
        warns.push(`ep${e.ep} 镜${s.shot_id}: 判据无法定位有效引用位（📌 段内未抽到可判引文）→ 需人工判读`);
      } else if (!hits.length) {
        warns.push(`ep${e.ep} 镜${s.shot_id}: note 的引文与 D08 现行 body[${idx}] 不匹配（引文可能已过期）→ 请下游更新引文`);
      }
    }
  }
}

console.log(`\n单元：${UNIT}　D08 版本：${D08.version}　D11 版本：${D11?.version ?? "（未落盘）"}　受检 shot_intent：${MAP.length} 条`);
console.log(`覆盖核验：${canCheckCoverage ? `${covered}/${MAP.length} 条被 D11 visual_facts 正面拍到` : "已跳过（D11 或映射表未就绪）"}`);
if (warns.length) {
  console.log(`\n⚠️ 引文/引用提示 ${warns.length} 条（不计入硬冲突，需下游同步）：`);
  for (const w of warns) console.log("   ·", w);
}
if (errors.length) {
  console.log(`\n❌ 硬冲突 ${errors.length} 条：`);
  for (const e of errors) console.log("   ·", e);
  process.exit(1);
}
console.log(`\n✅ 零硬冲突：${canCheckCoverage ? `${MAP.length} 条 shot_intent 全部被 D11 visual_facts 正面拍到` : "护栏全过（覆盖核验未执行）"}，且未越权写镜头语言。`);
