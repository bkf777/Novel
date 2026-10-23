#!/usr/bin/env node
/**
 * D15 × D16 × D11 独立时码对账（**版本一律按盘读取，禁止在本头部硬编码版本号**）
 *
 * ⚠️ 头部版本戳纪律（企划合规 §三十六 登记的第 ③ 条）：本脚本曾硬编码「D15 v1.1 × D16 v1.5」，
 *    而下游连升数版后该戳即成**过期误导**（实跑按盘计算不受影响，但读者会据此误判）。
 *    ⇒ 本头部**不再写任何具体版本号**，实际版本由运行时首行输出
 *    「版本：D11 vX　D15 vY　D16 vZ」给出；引用结论时**必须连同该行版本一起引用**。
 *
 * 用途：独立复算「0 条越出本镜时间窗 / 0 条跨段间硬切 / 字幕与配音逐条同步」，
 *      并给出**带口径名**的余量值（三口径见下「余量口径收口」段）。
 *
 * 【单元参数化 · S12 纪律 · 2026-10-23】本脚本**按 `--unit` 取单元**，**禁止复制 `_u02` 之类的副本**
 *   —— 副本一旦分叉，两套判据会各自演化，下一位无从判断哪套是现役（U01-R19 已吃过「同一批数据
 *   被算成两个结论」的亏）。用法：
 *     node scripts/reconcile_D15_D16_timing.mjs --unit U01     # 默认 U01
 *     node scripts/reconcile_D15_D16_timing.mjs --unit U02
 *   单元的 D15 未落盘 → **明确报错并 exit 2**（不产出「0 条」式的空结论，Q49）。
 *
 * 【判据定义 —— 写死在此，避免下一位重数得出不同数字而误判为缺陷】
 *  判据 A「越窗」：对象的结束时刻 > 其所属镜位的时间窗结束时刻 → 越窗。
 *                 镜位时间窗由 D11 每集 shots[].duration_sec 顺序累加得到
 *                 （四段制，镜时严格等于 D07 段界），窗为左闭右开 [start, end)。
 *                 对象的所属镜位：配音取 D15 voice_over[].shot_id；
 *                 字幕取「in_sec 落入的镜窗」，落点恰在边界时归属后一镜。
 *  判据 B「跨切点」：对象区间 [in_sec, out_sec] 严格跨越某个 D16 硬切点 at_sec，
 *                 即存在 cut 使 in_sec < cut.at_sec < out_sec（端点重合不算跨越）。
 *  判据 C「余量」：余量 = 所属镜窗结束时刻 − 对象结束时刻；
 *                 **只对未越窗的对象取**，越窗对象余量记为负数。
 *                 「最小余量」= 全部对象余量的最小值（单列最小值的集、镜位、对象）。
 *  判据 D「同步」：D16 对白字幕 out_sec == 对应 D15 配音 (at_sec + dur_sec)，
 *                 按 (ep, 时间就近) 一一配对。
 *
 * 只读脚本：不写任何文件。
 */
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

// ══ 判据清单 ＋ 清单守卫（Q56② · U01-R33 · 企划合规 07:45 派单）════════════════
//   U01 侧**无构建脚本载体**（D11／D16 系补丁链产物），故判据的机械守卫落在这两个
//   **只读对账脚本**内 —— 与 U02 侧同构，但**不新建构建脚本**（S23 追加子句）。
//   ① **每条判据必须标注来源** —— 禁复制无来源条目（当初 U01 那条关没被 U02 继承即此根因）。
//   ② **清单条数必须 == 实际断言点数** —— 删一条断言即中止（exit 2），杜绝「判据被无声删改」。
//   ③ 本脚本**只读、不写任何文件** → Q64「写盘脚本须带版本守卫」**不适用**（本单无落盘脚本）；
//      其防的「旧口径静默回退」风险，在本形态下由**本清单守卫**承担。
//   ⚠️ 断言函数名**不得出现在本文件注释／字符串字面**（清单守卫按 token 计数，见下）。
const ASSERT_MANIFEST = [
  { id: "A1", criterion: "越窗 · D15 配音：对象结束时刻 > 所属镜窗结束 → 0 条", source: "D18 S18／台账 §四十五 判据 A；U01-R19 跨单元复制" },
  { id: "B1", criterion: "跨切点 · D15 配音：区间严格跨越段间硬切点 → 0 条", source: "D18 S18／台账 §四十五 判据 B；U01-R19 跨单元复制" },
  { id: "A2", criterion: "越窗 · D16 字幕行（排除全片常驻角标）→ 0 条", source: "D18 S18 判据 A；例外：角标为全片常驻元素（D16 v1.5 起）" },
  { id: "B2", criterion: "跨切点 · D16 字幕行（排除全片常驻角标）→ 0 条", source: "D18 S18 判据 B；例外同 A2" },
  { id: "D1", criterion: "同步 · D16 对白字幕 out_sec == D15 配音 (at_sec+dur_sec)，按 0.1s 网格 → 0 条不符", source: "D18 S18 判据 D；S22 网格口径（不做浮点位相等）" },
  { id: "A3", criterion: "越窗 · D15 sfx／foley（**设计预铺豁免**）→ 0 条", source: "D18 S21 预铺豁免裁定（预铺是设计如此，不算越窗／跨切）" },
  { id: "B3", criterion: "跨切点 · D15 sfx／foley（**设计预铺豁免**）→ 0 条", source: "D18 S21 预铺豁免裁定" },
  { id: "C1", criterion: "余量三口径（镜尾余量／起音间隙／镜首余量）最小值均可算且带口径名", source: "D18 Q46（三口径测不同的东西，不可互相替代）；台账 §六十三" },
  { id: "C2", criterion: "余量最小值 · D16 字幕行层可算", source: "D18 Q46；台账 §四十五" },
  { id: "C3", criterion: "余量最小值 · D15 sfx 层可算", source: "D18 Q46；台账 §四十五" },
  { id: "X1", criterion: "判据 B 的切点基线只取**段间**硬切点（counted_in_d17_cut_count=true），与 D16 逐集段间计数一致", source: "D18 D17 口径（U01-R13：段内并行交替点不算段间切点）" },
  { id: "X2", criterion: "字幕↔配音时间就近配对距离 ≤0.05s → 0 条超阈", source: "U01-R19 修（时间就近配对）" },
];

const assertFails = [];
const chk = (ok, id, msg) => { if (!ok) assertFails.push(`[${id}] ${msg}`); };

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
      + `Q56：新增/删除判据必须同步更新 ASSERT_MANIFEST（禁「跑到什么算什么」）。`);
    process.exit(2);
  }
  return [nDecl, nCall];
}
const [nManifest, nAssertPoints] = assert_manifest_guard();

const HERE = dirname(fileURLToPath(import.meta.url));
const P = (p) => resolve(HERE, "..", p);

// ── 单元参数（S12：禁副本，一律 --unit 参数化）──
const argv = process.argv.slice(2);
const unitIdx = argv.findIndex((a) => a === "--unit" || a === "-u");
const UNIT = (unitIdx >= 0 && argv[unitIdx + 1] ? argv[unitIdx + 1] : "U01").toUpperCase();
if (!/^U\d{2}$/.test(UNIT)) {
  console.error(`❌ --unit 取值非法：${UNIT}（应为 U01 这类形式）`);
  process.exit(2);
}
const up = (f) => resolve(HERE, "..", "units", UNIT, f);
for (const f of ["D11.json", "D15.json", "D16.json"]) {
  if (!existsSync(up(f))) {
    console.error(`❌ 单元 ${UNIT} 缺 ${f} —— 无法复算。`);
    console.error(`   D11/D16 是本岗交付物；D15 属声音设计。**D15 未落盘时不得产出「0 条」式的空结论**（Q49）。`);
    process.exit(2);
  }
}

const D11 = JSON.parse(readFileSync(up("D11.json"), "utf8"));
const D15 = JSON.parse(readFileSync(up("D15.json"), "utf8"));
const D16 = JSON.parse(readFileSync(up("D16.json"), "utf8"));

// ── 镜位时间窗 ──
const windows = {}; // ep -> [{shot_id, start, end}]
for (const e of D11.episodes) {
  let t = 0;
  windows[e.ep] = e.shots.map((s) => {
    const w = { shot_id: s.shot_id, start: t, end: t + s.duration_sec };
    t += s.duration_sec;
    return w;
  });
}
const winOf = (ep, shotId) => windows[ep].find((w) => w.shot_id === shotId);
const winContaining = (ep, t) => {
  const ws = windows[ep];
  for (const w of ws) if (t >= w.start && t < w.end) return w;
  return t >= ws[ws.length - 1].end ? ws[ws.length - 1] : ws[0];
};

// ── D16 硬切点 ──
// 判据 B「跨切点」只对**段间切点**成立 —— 即 counted_in_d17_cut_count=true 的条目。
// 「硬切（段内并行交替点）」（counted=false，ep2 的 31.5／34.0s）是同一段内两条画面的
// 交替，不是段落边界，音效跨它是并置关系而非越界，**不参与跨切判定**。
const hardCuts = {};
const preLeadCuts = {}; // 声音预铺切点（从 D16 transitions 的 audio_lead / sound_handling 解析）
// ⚠️ 提前量**逐集逐切点声明**，豁免判定一律取**该切点自己的声明值**（下方 `p.lead`），
//    **不使用任何全局常量** —— U01 ep8 声明 0.3s、其余 0.2s；U02 ep16 声明 0.3s、其余 0.2s。
//    （早期版本残留的 `PRE_LEAD_MAX = 0.2` 常量是死代码，已删除：留着会误导下一位以为存在全局上限。）
for (const e of D16.episodes) {
  hardCuts[e.ep] = e.cuts
    .filter((c) => c.counted_in_d17_cut_count === true)
    .map((c) => ({ at: c.at_sec, index: c.index, technique: c.technique }));
  // 预铺切点：transitions 里凡同时含「预铺」与「（XX.Xs）」的字符串，提取该切点秒数，
  // 并从**同一条字符串**解析其声明的提前量「提前 X.Xs」—— 提前量是**每集各自的声明值**
  // （ep1/2/4/5/6 为 0.2s，**ep8 为 0.3s**），不得用全局常量代替。
  const set = new Map();
  const walk = (v) => {
    if (typeof v === "string") {
      if (v.includes("预铺")) {
        const cutM = [...v.matchAll(/（\s*(\d+(?:\.\d+)?)\s*s\s*）/g)];
        const leadM = v.match(/提前\s*(\d+(?:\.\d+)?)\s*s/);
        const lead = leadM ? parseFloat(leadM[1]) : null;
        for (const m of cutM) {
          const cut = parseFloat(m[1]);
          // 同一切点若有多条声明，取**最大**提前量（最宽松，且与 D16 原文一致优先）
          const prev = set.get(cut);
          set.set(cut, prev === undefined ? lead : (prev === null ? lead : Math.max(prev, lead)));
        }
      }
    } else if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === "object") Object.values(v).forEach(walk);
  };
  walk(e.transitions);
  preLeadCuts[e.ep] = [...set.entries()].map(([cut, lead]) => ({ cut, lead })).sort((a, b) => a.cut - b.cut);
}

const R = (n) => Math.round(n * 10) / 10; // 消除二进制浮点尾差，按 0.1s 网格
const inGrid = (a, b) => Math.abs(R(a) - R(b)) < 1e-9;

// ══ 判据 A/B/C：D15 配音（条数按单元实际）══════════════════════════════════════
const voRows = [];
for (const e of D15.episodes) {
  for (const vo of e.voice_over) {
    const w = winOf(e.ep, vo.shot_id);
    const end = vo.at_sec + vo.dur_sec;
    const over = end > w.end + 1e-9;
    const crossed = hardCuts[e.ep].filter((c) => vo.at_sec < c.at - 1e-9 && c.at < end - 1e-9);
    voRows.push({
      ep: e.ep, shot: vo.shot_id, at: vo.at_sec, dur: vo.dur_sec, end,
      win: `${w.start}~${w.end}`, winStart: w.start, winEnd: w.end,
      over, crossed: crossed.map((c) => c.at),
      margin: R(w.end - end),
    });
  }
}

// ══ 判据 A/B/C：D16 字幕行（全部类型）══════════════════════════════
// 例外：`type=角标` 的行是 **全片常驻元素**（AI 生成角标 0~45s 贯穿全集），
//       按设计就不归属任何单一镜位、也不受切点约束，故**不参与镜窗/切点判定**。
//       （D16 v1.5 起新增此类行；不排除会得到 8 条伪「越窗」＋8 条伪「跨切点」。）
const FULLSPAN_TYPES = new Set(["角标"]);
const subRows = [];
for (const e of D16.episodes) {
  for (const s of e.subtitle_style.lines) {
    const w = winContaining(e.ep, s.in_sec);
    const fullspan = FULLSPAN_TYPES.has(s.type);
    const over = !fullspan && s.out_sec > w.end + 1e-9;
    const crossed = fullspan ? [] : hardCuts[e.ep].filter((c) => s.in_sec < c.at - 1e-9 && c.at < s.out_sec - 1e-9);
    subRows.push({
      ep: e.ep, seq: s.seq, type: s.type, in: s.in_sec, out: s.out_sec,
      win: `${w.start}~${w.end}`, shot: w.shot_id, fullspan,
      over, crossed: crossed.map((c) => c.at), margin: R(w.end - s.out_sec),
    });
  }
}

// ══ 判据 D：字幕 ↔ 配音逐条同步 ══════════════════════════════════════
const syncRows = [];
for (const e of D16.episodes) {
  const vos = D15.episodes.find((x) => x.ep === e.ep).voice_over;
  for (const s of e.subtitle_style.lines.filter((x) => x.type === "对白")) {
    // 时间就近配对
    let best = null, bestD = Infinity;
    for (const vo of vos) {
      const d = Math.abs(vo.at_sec - s.in_sec);
      if (d < bestD) { bestD = d; best = vo; }
    }
    const voEnd = best ? best.at_sec + best.dur_sec : null;
    syncRows.push({
      ep: e.ep, seq: s.seq, text: s.text,
      subOut: s.out_sec, voAt: best?.at_sec, voDur: best?.dur_sec, voEnd,
      pairDist: R(bestD),
      equal: voEnd !== null && inGrid(s.out_sec, voEnd),
    });
  }
}

// ── 报告 ──
const report = (name, rows, overKey = "over") => {
  const over = rows.filter((r) => r[overKey]);
  const crossed = rows.filter((r) => r.crossed.length);
  const minRow = rows.reduce((a, b) => (b.margin < a.margin ? b : a));
  return { name, total: rows.length, over, crossed, minRow };
};

const voRep = report("D15 配音", voRows);
const subScored = subRows.filter((r) => !r.fullspan);
const subRep = report("D16 字幕行（不含全片常驻角标）", subScored);

console.log(`版本：单元 ${UNIT}　D11 ${D11.version}　D15 ${D15.version}　D16 ${D16.version}`);
console.log("");
console.log("── 判据 A/B/C · D15 配音（源）" + "─".repeat(30));
console.log(`  对象总数：${voRep.total}`);
console.log(`  越出本镜时间窗：${voRep.over.length} 条`);
for (const r of voRep.over) console.log(`     ep${r.ep} 镜${r.shot}  ${r.at}+${r.dur}=${r.end}  镜窗 ${r.win}  余量 ${r.margin}`);
console.log(`  跨 D16 硬切点：${voRep.crossed.length} 条`);
for (const r of voRep.crossed) console.log(`     ep${r.ep} 镜${r.shot}  ${r.at}~${r.end}  跨 ${r.crossed}`);
console.log(`  最小余量：${voRep.minRow.margin}s  → ep${voRep.minRow.ep} 镜${voRep.minRow.shot}（配音 ${voRep.minRow.at}+${voRep.minRow.dur}=${voRep.minRow.end}，镜窗 ${voRep.minRow.win}）`);

// ══ 判据 A/B/C：D15 音效与拟音（sfx / foley）═════════════════════════
// 配音只覆盖对白层；D15 的 sfx/foley 同样带 at_sec/dur_sec 且必须落在所属镜窗内、
// 不得跨**段间**切点，故一并复算 —— 否则 D15 升版后「数值区零影响」的结论没有证据。
//
// 【声音预铺豁免】D16 各集 `transitions[].audio_lead` 明文声明了「声音预铺位」：
// 音效在切点前 ≤0.2s 侵入、为切点后的声底做听觉衔接，是**设计如此**，不算越窗/跨切。
// 豁免判定：对象起点落在某个预铺切点前 ≤PRE_LEAD_MAX，且终点越过该切点 → 判为设计预铺。
const sfxRows = [];
for (const e of D15.episodes) {
  for (const kind of ["sfx", "foley"]) {
    for (const it of e[kind] || []) {
      const w = winOf(e.ep, it.shot_id);
      if (!w) continue;
      const end = it.at_sec + it.dur_sec;
      const crossed = hardCuts[e.ep].filter((c) => it.at_sec < c.at - 1e-9 && c.at < end - 1e-9);
      // 预铺豁免：起点落在某预铺切点前、提前量 ≤ 该切点**声明值**、且终点越过该切点
      const leads = preLeadCuts[e.ep]
        .filter((p) => p.lead !== null &&
          it.at_sec <= p.cut + 1e-9 &&
          p.cut - it.at_sec <= p.lead + 0.05 + 1e-9 &&
          end > p.cut - 1e-9)
        .map((p) => `${p.cut}(声明提前 ${p.lead}s)`);
      const designPreLead = leads.length > 0;
      const overRaw = end > w.end + 1e-9;
      sfxRows.push({
        ep: e.ep, kind, shot: it.shot_id, at: it.at_sec, dur: it.dur_sec, end,
        win: `${w.start}~${w.end}`, event: it.event,
        over: overRaw && !designPreLead,
        overRaw, designPreLead, leads,
        crossed: (designPreLead ? [] : crossed).map((c) => c.at),
        margin: R(w.end - end),
      });
    }
  }
}

console.log("");
console.log("── 判据 A/B/C · D15 sfx ＋ foley（音效/拟音层）" + "─".repeat(20));
const sfxOver = sfxRows.filter((r) => r.over);
const sfxCross = sfxRows.filter((r) => r.crossed.length);
const sfxPre = sfxRows.filter((r) => r.designPreLead);
const sfxMin = sfxRows.reduce((a, b) => (b.margin < a.margin ? b : a));
console.log(`  对象总数：${sfxRows.length}（sfx ${D15.episodes.reduce((a, e) => a + e.sfx.length, 0)} ＋ foley ${D15.episodes.reduce((a, e) => a + e.foley.length, 0)}）`);
console.log(`  越出本镜时间窗：${sfxOver.length} 条`);
for (const r of sfxOver) console.log(`     ep${r.ep} ${r.kind} 镜${r.shot}  ${r.at}+${r.dur}=${r.end}  镜窗 ${r.win}  余量 ${r.margin}  ${r.event}`);
console.log(`  跨 D16 段间硬切点：${sfxCross.length} 条`);
for (const r of sfxCross) console.log(`     ep${r.ep} ${r.kind} 镜${r.shot}  ${r.at}~${r.end}  跨 ${r.crossed}`);
console.log(`  【设计预铺豁免】${sfxPre.length} 条（D16 明文声明的预铺位，跨切与越窗均为设计）：`);
for (const r of sfxPre) console.log(`     ep${r.ep} ${r.kind} 镜${r.shot}  ${r.at}~${r.end}  预铺切点 ${r.leads}  ${r.event}`);
console.log(`  最小余量：${sfxMin.margin}s  → ep${sfxMin.ep} ${sfxMin.kind} 镜${sfxMin.shot}`);

console.log("");
console.log("── 判据 A/B/C · D16 字幕行（派生）" + "─".repeat(26));
console.log(`  对象总数：${subRep.total}`);
console.log(`  越出本镜时间窗：${subRep.over.length} 条`);
for (const r of subRep.over) console.log(`     ep${r.ep} seq${r.seq}(${r.type}) ${r.in}~${r.out}  镜窗 ${r.win}  余量 ${r.margin}`);
console.log(`  跨 D16 硬切点：${subRep.crossed.length} 条`);
for (const r of subRep.crossed) console.log(`     ep${r.ep} seq${r.seq}(${r.type}) ${r.in}~${r.out}  跨 ${r.crossed}`);
console.log(`  最小余量：${subRep.minRow.margin}s  → ep${subRep.minRow.ep} seq${subRep.minRow.seq}(${subRep.minRow.type}) ${subRep.minRow.in}~${subRep.minRow.out}  镜窗 ${subRep.minRow.win}`);

console.log("");
console.log("── 判据 D · 字幕 ↔ 配音逐条同步" + "─".repeat(30));
const neq = syncRows.filter((r) => !r.equal);
console.log(`  对白字幕条数：${syncRows.length}（D15 配音 ${voRows.length} 条）`);
console.log(`  out_sec ≠ 配音 (at_sec+dur_sec)：${neq.length} 条`);
for (const r of neq) console.log(`     ep${r.ep} seq${r.seq} 「${r.text}」 子 ${r.subOut} vs 配 ${r.voAt}+${r.voDur}=${r.voEnd}（配对距离 ${r.pairDist}s）`);
const unmatched = syncRows.filter((r) => r.pairDist > 0.05);
console.log(`  配对距离 >0.05s 的行：${unmatched.length} 条`);

console.log("");
console.log("── 余量 Top5 最小（配音口径，用于交叉比对）" + "─".repeat(18));
for (const r of [...voRows].sort((a, b) => a.margin - b.margin).slice(0, 5)) {
  console.log(`  ${String(r.margin).padStart(6)}s  ep${r.ep} 镜${r.shot}  ${r.at}+${r.dur}=${r.end}  镜窗 ${r.win}`);
}

console.log("");
console.log("── 余量口径收口：同一批对象，三种合法但不同的余量定义" + "─".repeat(14));
// 口径 1「镜尾余量」＝ 所属镜窗结束 − 对象结束        → 配音余量最小 1.0s（ep1 镜1）
// 口径 2「起音间隙」＝ 配音起音 − 本镜起始硬切点      → 最小 0.5s（ep7 镜4）
// 口径 3「镜首余量」＝ 配音起音 − 所属镜窗开始        → 最小 0.0s（多条起音即镜起）
// **三者测的是不同的东西，数字不可互相替代**（曾出现 1.7／1.0／0.5 三个数并存）
const voEnds = voRows.map((r) => ({ ...r, gapToCut: null }));
for (const r of voEnds) {
  const cuts = hardCuts[r.ep].map((c) => c.at).sort((a, b) => a - b);
  const startCut = cuts.filter((c) => c <= r.winStart).pop();
  r.gapToCut = startCut === undefined ? null : R(r.at - startCut);
  r.headMargin = R(r.at - r.winStart);
}
const voMinTail = voRows.reduce((a, b) => (b.margin < a.margin ? b : a));
const withGap = voEnds.filter((r) => r.gapToCut !== null);
const voMinGap = withGap.reduce((a, b) => (b.gapToCut < a.gapToCut ? b : a));
const voMinHead = voEnds.reduce((a, b) => (b.headMargin < a.headMargin ? b : a));
console.log(`  口径1 镜尾余量（镜窗结束 − 配音结束）：最小 ${voMinTail.margin}s → ep${voMinTail.ep} 镜${voMinTail.shot}（${voMinTail.at}+${voMinTail.dur}=${voMinTail.end}，镜窗 ${voMinTail.win}）`);
console.log(`  口径2 起音间隙（配音起音 − 本镜起始硬切）：最小 ${voMinGap.gapToCut}s → ep${voMinGap.ep} 镜${voMinGap.shot}（起音 ${voMinGap.at}，起始切点 ${voMinGap.gapToCut === 0 ? "" : ""}${voMinGap.at - voMinGap.gapToCut}）`);
console.log(`  口径3 镜首余量（配音起音 − 镜窗开始）：  最小 ${voMinHead.headMargin}s → ep${voMinHead.ep} 镜${voMinHead.shot}（起音 ${voMinHead.at}，镜窗 ${voMinHead.win}）`);
// ⚠️ 本脚本**不硬编码任何单元的登记值** —— 旧版此处写死「U01 登记：口径1 1.0s／口径2 0.5s／口径3 0.0s」，
//    而 U01 的口径1 已在 §六十三 订正为 **0.6s 底**（D15 v1.4 收敛后实测）→ 硬编码会造成口径漂移。
//    登记值以各单元的 D18／台账章节为准；换单元时**重新读取该单元的登记值**再比对。
console.log(`  ↑ 三口径的最小值须与**该单元**在 D18／台账登记的值一致；换单元时以该单元的登记值为准（本脚本不硬编码登记值，避免口径漂移）。`);

console.log("");
console.log("── D16 硬切点计数（判据 B 的基线）" + "─".repeat(28));
let counted = 0, totalCuts = 0, techTally = {};
for (const e of D16.episodes) {
  e.cuts.forEach((c) => { techTally[c.technique] = (techTally[c.technique] || 0) + 1; });
  counted += e.cuts.filter((c) => c.counted_in_d17_cut_count === true).length;
  totalCuts += e.cuts.length;
  console.log(`  ep${e.ep}: 段间硬切 ${hardCuts[e.ep].length}（计入 D17 ${e.cuts.filter((c) => c.counted_in_d17_cut_count === true).length}）｜cuts 总条目 ${e.cuts.length}｜transitions ${e.transitions.length}｜预铺切点 ${preLeadCuts[e.ep].map((p) => `${p.cut}s/${p.lead ?? "未声明提前量"}s`).join(",") || "无"}`);
}
console.log(`  cuts 条目总计 ${totalCuts}｜计入 D17 ${counted}｜technique 分布 ${JSON.stringify(techTally)}`);

// ── 判据断言（清单 ${nManifest} 条 ＝ 实际断言点 ${nAssertPoints} 处，已由上方守卫机械核对）──
//   断言条件与既有违规计数**逐项对应**，不改变任何判据内容、时码或口径。
chk(voRep.over.length === 0, "A1", `D15 配音越窗 ${voRep.over.length} 条`);
chk(voRep.crossed.length === 0, "B1", `D15 配音跨段间硬切点 ${voRep.crossed.length} 条`);
chk(subRep.over.length === 0, "A2", `D16 字幕行越窗 ${subRep.over.length} 条`);
chk(subRep.crossed.length === 0, "B2", `D16 字幕行跨段间硬切点 ${subRep.crossed.length} 条`);
chk(neq.length === 0, "D1", `字幕 out_sec ≠ 配音 (at_sec+dur_sec) ${neq.length} 条`);
chk(sfxOver.length === 0, "A3", `D15 sfx／foley 越窗 ${sfxOver.length} 条（预铺豁免后）`);
chk(sfxCross.length === 0, "B3", `D15 sfx／foley 跨段间硬切点 ${sfxCross.length} 条（预铺豁免后）`);
chk(Number.isFinite(voMinTail?.margin) && Number.isFinite(voMinGap?.gapToCut) && Number.isFinite(voMinHead?.headMargin),
    "C1", "余量三口径（镜尾余量／起音间隙／镜首余量）最小值不可算");
chk(Number.isFinite(subRep.minRow?.margin), "C2", "D16 字幕行层余量最小值不可算");
chk(Number.isFinite(sfxMin?.margin), "C3", "D15 sfx 层余量最小值不可算");
chk(D16.episodes.every((e) => hardCuts[e.ep].length === e.cuts.filter((c) => c.counted_in_d17_cut_count === true).length),
    "X1", "判据 B 的切点基线与 D16 逐集段间硬切点计数不一致");
chk(unmatched.length === 0, "X2", `字幕↔配音配对距离 >0.05s 的行 ${unmatched.length} 条`);

const hardFail = voRep.over.length + voRep.crossed.length + subRep.over.length + subRep.crossed.length + neq.length + sfxOver.length + sfxCross.length;
const failTotal = hardFail + assertFails.length;
console.log("");
console.log(`── 判据清单断言（Q56② · U01-R33）：清单 ${nManifest} 条 ＝ 实际断言点 ${nAssertPoints} 处｜不通过 ${assertFails.length} 条`);
for (const f of assertFails) console.log(`   · ${f}`);
console.log(hardFail === 0
  ? "✅ 独立复算零违规：配音与字幕均 0 越窗 / 0 跨切点，字幕与配音逐条同步。"
  : `❌ 检出 ${hardFail} 项违规。`);
process.exit(failTotal === 0 ? 0 : 1);
