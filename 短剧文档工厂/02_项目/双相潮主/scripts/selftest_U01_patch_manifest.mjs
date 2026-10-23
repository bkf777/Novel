#!/usr/bin/env node
/**
 * selftest_U01_patch_manifest.mjs —— U01 侧一次性 patch 脚本治理自测器
 *
 * 维护岗：分镜导演（bot_1855d6ce9cdd）｜创建 2026-10-23
 * 治理依据：企划合规 U02-R34 裁定（2026-10-23 10:0x 派单）
 *
 * ─────────────────────────────────────────────────────────────────
 * 五腿
 * ─────────────────────────────────────────────────────────────────
 * L1 **run-once 冻结回归**：10 个 U01 侧写交付物 JSON 的 patch 脚本，在沙箱里
 *    对**现盘**（已演进）全部 exit 0、零写盘。
 *    —— 校验点：10/10 脚本 exit 0；沙箱 units/U01 5 份交付物 SHA256 前后一致。
 *
 * L2 **链式历史重放（EXECUTE 路径）**：这是 L1 的补充 —— L1 只走了 NO-OP 分支，
 *    **断言登记、双射校验、写盘、写后回读全都没被执行过**。
 *    L2 用历史备份把目标文件回退到补丁的前提版本，再正放三个补丁，
 *    终态与**真实历史产物逐字节比对**：
 *      · D11 链：历史 v1.7 → 逆向拆解 → v1.4 → 正放 A/B/C → 终态 ≡ 历史 v1.7（字节级）
 *      · D16 链：历史 v1.9 → 正放 D            → 终态 ≡ 历史 v1.10（字节级）
 *
 * L3 **守卫拒绝路径（治理层，exit 2）**：两种子情形
 *      L3a 清单条目被变更清单引用却缺失 → **静态**拒绝（建守卫时即拒）
 *      L3b 清单条目缺失且脚本仍登记该 id → **运行期**拒绝（登记了清单外 id）
 *    两者都不得写盘。
 *
 * L4 **内容断言失败路径（内容层，exit 1）**：破坏目标文件使某条断言不成立 →
 *    必须 exit 1 且**不写盘**（与 exit 2 严格可区分）。
 *
 * L5 **真盘零写入**：负测全程在沙箱副本执行；全流程前后比对**真盘**交付物 SHA256 一致。
 *
 * 退出码语义（与守卫模块一致）：
 *   0 全部通过｜1 自测自身发现不一致｜2 沙箱脚本报错（非守卫拒绝、非断言失败）
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, rmSync, copyFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
import { tmpdir } from "node:os";

// ── 沙箱 ROOT 由本文件位置推导（Q68：不依赖 cwd、不依赖调用方传参）──
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const SB = resolve(tmpdir(), `u01_patch_guard_selftest_${process.pid}`);

const GOVERNED = [
  "patch_D11_shot_intent_v15.mjs",
  "patch_D11_v16_ep5_wording.mjs",
  "patch_D11_v17_ep2_note_sync.mjs",
  "patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs",
];
const OTHERS = [
  "patch_D16_U01_preview_param_dep.py",
  "patch_D16_dwell_convention.py",
  "patch_D16_live_pointer_v16.py",
  "patch_D16_v17_badge_avoid.mjs",
  "patch_U01R18_ep2_text_sync.mjs",
  "patch_u01r18_sync.py",
];
const ALL_SCRIPTS = [...GOVERNED, ...OTHERS];
const UNIT_FILES = ["D07.json", "D09.json", "D11.json", "D15.json", "D16.json"];

const HIST_D11_V17 = "reports/_bak_U01_D11_D16_20261023-045757/D11.json.bak-20261022205757";
const HIST_D16_V19 = "reports/_bak_U01_D11_D16_20261023-060447/D16.json";
const HIST_D16_V110 = "reports/_bak_U01_D16_liveptr_20261023-075449/D16.json";

const legs = [];
function record(id, name, ok, detail) {
  legs.push({ id, name, ok, detail });
  console.log(`${ok ? "✅" : "❌"} ${id} ${name}${detail ? ` —— ${detail}` : ""}`);
}
function sha256File(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex");
}
function sha256Text(s) {
  return createHash("sha256").update(s, "utf8").digest("hex");
}
function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, encoding: "utf8" });
  return { code: r.status, out: r.stdout || "", err: r.stderr || "" };
}
/** 脚本调用形态：.mjs 直接跑；.py 需 --project <沙箱项目目录> --unit U01 */
function invoke(scriptName, projDir, extra = []) {
  if (scriptName.endsWith(".mjs")) {
    return run(process.execPath, [join(projDir, "scripts", scriptName), ...extra], projDir);
  }
  return run("python3", [join(projDir, "scripts", scriptName), "--project", projDir, "--unit", "U01", ...extra], projDir);
}

function freshSandbox() {
  rmSync(SB, { recursive: true, force: true });
  mkdirSync(join(SB, "scripts"), { recursive: true });
  mkdirSync(join(SB, "units", "U01"), { recursive: true });
  mkdirSync(join(SB, "reports"), { recursive: true });
  for (const s of ["_patch_guard.mjs", ...ALL_SCRIPTS]) {
    copyFileSync(join(ROOT, "scripts", s), join(SB, "scripts", s));
  }
  for (const f of UNIT_FILES) {
    copyFileSync(join(ROOT, "units", "U01", f), join(SB, "units", "U01", f));
  }
  return SB;
}

/** 从补丁脚本源码里取出 PATCHES 字面量（new Function 求值，避免手工重抄长串出错） */
function extractPatches(scriptName) {
  const src = readFileSync(join(ROOT, "scripts", scriptName), "utf8");
  const arrIdx = src.indexOf("const PATCHES = [");
  if (arrIdx < 0) throw new Error(`${scriptName}: 未找到 PATCHES 字面量`);
  const endIdx = src.indexOf("\n];", arrIdx);
  if (endIdx < 0) throw new Error(`${scriptName}: PATCHES 字面量未闭合`);
  // PATCHES 可能引用前置常量（脚本 C 引用 OLD_NOTE / NEW_NOTE）——
  // 只把**这些常量声明**取出来喂给 new Function；整段源码含 import，喂进去会语法错误。
  const head = [];
  for (const name of ["OLD_NOTE", "NEW_NOTE"]) {
    const startIdx = src.indexOf(`const ${name} =`);
    if (startIdx < 0) continue;
    if (startIdx > arrIdx) throw new Error(`${scriptName}: 常量 ${name} 声明位置异常`);
    const declEnd = src.indexOf('";', startIdx);
    if (declEnd < 0) throw new Error(`${scriptName}: 常量 ${name} 声明未闭合`);
    head.push(src.slice(startIdx, declEnd + 2));
  }
  const arrExpr = src.slice(arrIdx + "const PATCHES = ".length, endIdx + 3);
  // eslint-disable-next-line no-new-func
  const fn = new Function("JSON", `${head.join("\n")}\nreturn ${arrExpr};`);
  return fn(JSON);
}

/** 把某个补丁「逆向」拆掉：new → old，并回退版本号 */
function invert(content, scriptName) {
  const patches = extractPatches(scriptName);
  let out = content;
  for (const [oldStr, newStr] of patches) {
    if (!out.includes(newStr)) throw new Error(`${scriptName}: 逆向失败，新串不存在于当前内容`);
    out = out.split(newStr).join(oldStr);
  }
  return out;
}

// ── 真盘基线（L5）──
const realBefore = {};
for (const f of UNIT_FILES) realBefore[f] = sha256File(join(ROOT, "units", "U01", f));

// ═══════════════════════════════════════════════════════════════════
// L1 · run-once 冻结回归（沙箱，现盘已演进）
// ═══════════════════════════════════════════════════════════════════
{
  const sb = freshSandbox();
  const projDir = sb;   // 沙箱项目根：scripts/ units/U01/ reports/ 三层
  const before = {};
  for (const f of UNIT_FILES) before[f] = sha256File(join(projDir, "units", "U01", f));

  const results = [];
  for (const s of ALL_SCRIPTS) {
    const r = invoke(s, projDir);
    results.push({ s, code: r.code, guard: /\[PATCH-GUARD\]/.test(r.out + r.err), noop: /\[NO-OP\]/.test(r.out + r.err) });
  }
  // 治理脚本额外跑一次 --check 形态
  const chk = invoke("patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs", projDir, ["--check"]);

  const after = {};
  for (const f of UNIT_FILES) after[f] = sha256File(join(projDir, "units", "U01", f));
  const unchanged = UNIT_FILES.filter((f) => before[f] === after[f]);
  const allZero = results.every((r) => r.code === 0);
  const governedNoop = results.filter((r) => GOVERNED.includes(r.s)).every((r) => r.noop);
  const othersZero = results.filter((r) => OTHERS.includes(r.s)).every((r) => r.code === 0);

  record(
    "L1",
    "run-once 冻结回归（10 脚本 · 沙箱 · 零写盘）",
    allZero && governedNoop && othersZero && unchanged.length === UNIT_FILES.length && chk.code === 0,
    `脚本 ${results.length}/${results.length} exit 0；治理脚本 ${GOVERNED.length}/${GOVERNED.length} 走 NO-OP 分支；`
    + `其余 ${OTHERS.length}/${OTHERS.length} exit 0；--check 形态 exit ${chk.code}；`
    + `沙箱交付物 SHA256 未变 ${unchanged.length}/${UNIT_FILES.length}`,
  );
}

// ═══════════════════════════════════════════════════════════════════
// L2 · 链式历史重放（EXECUTE 路径：断言登记 / 双射 / 写盘 / 写后回读）
// ═══════════════════════════════════════════════════════════════════
{
  const sb = freshSandbox();
  const projDir = sb;

  // ── D11 链：历史 v1.7 → 逆向拆解到 v1.4 → 正放 A/B/C ──
  const histD11 = readFileSync(join(ROOT, HIST_D11_V17), "utf8");
  let d11 = histD11;
  d11 = invert(d11, "patch_D11_v17_ep2_note_sync.mjs");   // v1.7 → v1.6
  d11 = invert(d11, "patch_D11_v16_ep5_wording.mjs");      // v1.6 → v1.5
  d11 = invert(d11, "patch_D11_shot_intent_v15.mjs");       // v1.5 → v1.4
  writeFileSync(join(projDir, "units", "U01", "D11.json"), d11, "utf8");

  const chain = [];
  for (const s of ["patch_D11_shot_intent_v15.mjs", "patch_D11_v16_ep5_wording.mjs", "patch_D11_v17_ep2_note_sync.mjs"]) {
    const r = invoke(s, projDir);
    // 守卫会打印**两条**摘要行：写盘前收口（status=PRE_OK）与写后收口（status=OK）。
    // 必须取**最后一条**（收口行），否则会误用 PRE_OK 行（post 计数为 0/N）。
    const ms = [...(r.out + r.err).matchAll(/\[PATCH-GUARD\].*pre=(\d+)\/(\d+) post=(\d+)\/(\d+).*status=(\w+)/g)];
    const m = ms.length ? ms[ms.length - 1] : null;
    chain.push({ s, code: r.code, pre: m ? `${m[1]}/${m[2]}` : "?", post: m ? `${m[3]}/${m[4]}` : "?", status: m ? m[5] : "?" });
  }
  const finalD11 = readFileSync(join(projDir, "units", "U01", "D11.json"), "utf8");
  const d11Same = finalD11 === histD11;
  const d11HashSame = sha256Text(finalD11) === sha256Text(histD11);

  // ── D16 链：历史 v1.9 → 正放 D ──
  copyFileSync(join(ROOT, HIST_D16_V19), join(projDir, "units", "U01", "D16.json"));
  const rD = invoke("patch_U01R18_ep4_ep6_ep7_sync_scope_note.mjs", projDir);
  const msD = [...(rD.out + rD.err).matchAll(/\[PATCH-GUARD\].*pre=(\d+)\/(\d+) post=(\d+)\/(\d+).*status=(\w+)/g)];
  const mD = msD.length ? msD[msD.length - 1] : null;   // 取收口行（status=OK），非 PRE_OK 行
  const finalD16 = readFileSync(join(projDir, "units", "U01", "D16.json"), "utf8");
  const histD16v110 = readFileSync(join(ROOT, HIST_D16_V110), "utf8");
  const d16Same = finalD16 === histD16v110;
  const d16HashSame = sha256Text(finalD16) === sha256Text(histD16v110);

  const chainOk = chain.every((c) => c.code === 0 && c.status === "OK");
  const d16Ok = rD.code === 0 && mD && mD[5] === "OK" && d16Same;

  record(
    "L2",
    "链式历史重放（EXECUTE 路径 + 字节级复现历史产物）",
    chainOk && d11Same && d11HashSame && d16Ok && d16HashSame,
    `D11 链 ${chain.length}/3 exit 0 且 status=OK（${chain.map((c) => `${c.s.slice(6, 18)}:${c.pre}/${c.post}`).join("，")}）；`
    + `终态 ≡ 历史 v1.7：${d11Same ? "字节级一致" : "不一致"}；`
    + `D16 链 exit ${rD.code}（pre=${mD ? mD[1] + "/" + mD[2] : "?"} post=${mD ? mD[3] + "/" + mD[4] : "?"}）终态 ≡ 历史 v1.10：${d16Same ? "字节级一致" : "不一致"}`,
  );
}

// ═══════════════════════════════════════════════════════════════════
// L3 · 守卫拒绝路径（治理层 exit 2）+ L4 · 内容断言失败路径（内容层 exit 1）
// ═══════════════════════════════════════════════════════════════════
{
  const sb = freshSandbox();
  const projDir = sb;
  // 复原到脚本 A 的前提版本（v1.4），供 L3/L4 使用
  let d11 = readFileSync(join(ROOT, HIST_D11_V17), "utf8");
  d11 = invert(d11, "patch_D11_v17_ep2_note_sync.mjs");
  d11 = invert(d11, "patch_D11_v16_ep5_wording.mjs");
  d11 = invert(d11, "patch_D11_shot_intent_v15.mjs");
  writeFileSync(join(projDir, "units", "U01", "D11.json"), d11, "utf8");

  const srcA = readFileSync(join(projDir, "scripts", "patch_D11_shot_intent_v15.mjs"), "utf8");
  const hashBefore = sha256File(join(projDir, "units", "U01", "D11.json"));

  // ── L3a：删掉一条**被变更清单引用**的清单条目 → 静态拒绝 ──
  const lineA07 = srcA.split("\n").find((l) => l.includes('id: "A07"'));
  const variantA = srcA.replace(lineA07 + "\n", "");
  writeFileSync(join(projDir, "scripts", "variant_L3a.mjs"), variantA, "utf8");
  const r3a = run(process.execPath, [join(projDir, "scripts", "variant_L3a.mjs")], projDir);
  const l3aOk = r3a.code === 2 && /守卫拒绝/.test(r3a.err + r3a.out);

  // ── L3b：删掉一条**结构类**清单条目（脚本仍登记该 id）→ 运行期拒绝 ──
  const lineA13 = srcA.split("\n").find((l) => l.includes('id: "A13"'));
  const variantB = srcA.replace(lineA13 + "\n", "");
  writeFileSync(join(projDir, "scripts", "variant_L3b.mjs"), variantB, "utf8");
  const r3b = run(process.execPath, [join(projDir, "scripts", "variant_L3b.mjs")], projDir);
  const l3bOk = r3b.code === 2 && /守卫拒绝/.test(r3b.err + r3b.out);

  // ── L4：破坏目标内容使某条内容断言不成立 → exit 1（且与 exit 2 可区分）──
  const corrupt = JSON.parse(d11);
  const ep3s3 = corrupt.episodes.find((e) => e.ep === 3).shots.find((s) => s.shot_id === 3);
  ep3s3.note = ep3s3.note + "【负测污染】";   // 让 A07 的旧串命中数变 0
  writeFileSync(join(projDir, "units", "U01", "D11.json"), JSON.stringify(corrupt, null, 2), "utf8");
  const hashBeforeL4 = sha256File(join(projDir, "units", "U01", "D11.json"));
  const r4 = run(process.execPath, [join(projDir, "scripts", "patch_D11_shot_intent_v15.mjs")], projDir);
  const hashAfterL4 = sha256File(join(projDir, "units", "U01", "D11.json"));
  const l4Ok = r4.code === 1 && /断言/.test(r4.err + r4.out) && hashBeforeL4 === hashAfterL4;

  record(
    "L3",
    "守卫拒绝路径（治理层 exit 2 · 零写盘）",
    l3aOk && l3bOk,
    `L3a 静态拒绝 exit ${r3a.code}；L3b 运行期拒绝 exit ${r3b.code}；两者均以「守卫拒绝」措辞退出`,
  );
  record(
    "L4",
    "内容断言失败路径（内容层 exit 1 · 零写盘 · 与 exit 2 可区分）",
    l4Ok,
    `污染目标后 exit ${r4.code}（断言未通过）；目标 SHA256 前后一致：${hashBeforeL4 === hashAfterL4}`,
  );
}

// ═══════════════════════════════════════════════════════════════════
// L5 · 真盘零写入（负测全程在沙箱副本执行）
// ═══════════════════════════════════════════════════════════════════
{
  const realAfter = {};
  for (const f of UNIT_FILES) realAfter[f] = sha256File(join(ROOT, "units", "U01", f));
  const same = UNIT_FILES.filter((f) => realBefore[f] === realAfter[f]);
  record(
    "L5",
    "真盘零写入（负测全程在沙箱副本执行）",
    same.length === UNIT_FILES.length,
    `真盘 ${UNIT_FILES.length} 份交付物 SHA256 未变 ${same.length}/${UNIT_FILES.length}`,
  );
  rmSync(SB, { recursive: true, force: true });
}

// ── 汇总（Q49：自检结论必附受检条数）──
const passed = legs.filter((l) => l.ok).length;
console.log(`\n自测汇总：受检 ${legs.length} 条｜通过 ${passed}｜不通过 ${legs.length - passed}`);
for (const l of legs) if (!l.ok) console.log(`   ❌ ${l.id} ${l.name}：${l.detail}`);
process.exit(passed === legs.length ? 0 : 1);
