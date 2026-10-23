#!/usr/bin/env node
/**
 * _patch_guard.mjs —— 一次性补丁脚本的**通用守卫模块**
 *
 * 维护岗：分镜导演（bot_1855d6ce9cdd）｜创建 2026-10-23
 * 任何岗均可 import 复用；复用方**不需要修改本文件**。
 *
 * 治理依据：企划合规 U02-R34 裁定（2026-10-23 10:0x 派单）
 *   ① 每个一次性 patch 脚本自带「变更清单 ＋ 断言点清单」，并于**写盘前**校验；
 *      校验口径＝**清单条数 == 实际断言点数**。
 *   ② run-once 冻结：再执行必须幂等或 `[NO-OP]` exit 0，
 *      **不得以「断言失败」表达「已演进、无需执行」**。
 *   ③ 写交付物 JSON 的一次性脚本仍适用 Q64 版本守卫（带 `--force` 逃生口）。
 *
 * ─────────────────────────────────────────────────────────────────
 * 三条能力
 * ─────────────────────────────────────────────────────────────────
 * 1) **版本冻结门**（`freeze()`）
 *    盘上版本 == 前提版本 → 允许执行；
 *    盘上版本 == 目标版本 → `[NO-OP]`（已执行过）exit 0；
 *    盘上版本 >  目标版本 → `[NO-OP]`（已演进）exit 0；
 *    盘上版本 <  前提版本 → exit 3（前置未落，**不越序执行**）。
 *    `--force` 可越过本门（Q64 逃生口；仅版本序，内容差异不得靠它放行）。
 *
 * 2) **清单 ↔ 断言点双射校验**（`finishPre()` / `finishPost()`）
 *    每条断言点必须**恰好被登记一次**，且**登记的 id 必须在清单内**。
 *    少一条、多一条、重复登记、登记了清单外的 id —— 一律 exit 2。
 *    （比「静态数 token」更强：静态计数能被注释／字面量干扰，双射不能。）
 *
 * 3) **结构化留痕**（stdout 机器可读摘要行 `[PATCH-GUARD] ...`）
 *    供自测器逐条回读校验，不必依赖人眼读日志。
 *
 * ─────────────────────────────────────────────────────────────────
 * 退出码语义（**三者必须可区分**，见 Q68）
 * ─────────────────────────────────────────────────────────────────
 *   0 ＝ 成功，或冻结门判定为 `[NO-OP]`
 *   1 ＝ **内容层断言不通过**（改动没达成预期）
 *   2 ＝ **治理层拒绝**（清单结构不一致／id 越界／重复登记）—— 属脚本自身缺陷
 *   3 ＝ **前置版本不满足**（盘上版本早于前提，前置补丁未落）
 *
 * ─────────────────────────────────────────────────────────────────
 * 计数单位定义（Q57：**先定义单位，再数**）
 * ─────────────────────────────────────────────────────────────────
 *   **一条断言点 ＝ 补丁脚本内恰好一处「断言登记语句」被求值一次**。
 *   脚本内以 `G.assertPoint(id, cond, msg)` 的形式登记；
 *   `id` 与断言点清单中的条目一一对应。
 *   循环内的逐项判定**必须先聚合成一次求值**再登记（否则同 id 会被登记多次 → 双射破裂）。
 *   ⚠️ 被治理脚本的注释与字符串字面里**不得出现该登记语句的函数名**
 *      （否则静态 token 计数会被注释／字面量污染 —— Q56）。
 *      本模块自身的注释刻意不写该函数名，定义处出现一次是不可避免且正确的。
 *
 * ─────────────────────────────────────────────────────────────────
 * 清单结构约定
 * ─────────────────────────────────────────────────────────────────
 *   变更清单条目：{ id, target, desc, assert_ids: [断言点 id, ...] }
 *     · assert_ids 只能引用 kind="change" 的断言点；
 *     · 每条 kind="change" 的断言点**至少被一条变更条目引用**（不许有孤儿断言）；
 *     · kind="structure" 的断言点**不得**被变更条目引用（结构复核不绑定具体改动）。
 *   断言点清单条目：{ id, phase: "pre"|"post", kind: "change"|"structure", source, desc }
 *     · `source` 必填（Q56②：断言清单须逐条标来源）。
 *     · phase="pre" 的条目必须在**写盘前**全部登记完毕；
 *       phase="post" 的条目是写后回读校验。
 */

import { readFileSync } from "node:fs";

export const EXIT_OK = 0;
export const EXIT_ASSERT = 1;
export const EXIT_MANIFEST = 2;
export const EXIT_PRECOND = 3;

/** 版本号解析：只认 "v<主>.<次>"，其余返回 null */
export function parseVersion(v) {
  const m = /^v(\d+)\.(\d+)$/.exec(String(v ?? "").trim());
  return m ? [Number(m[1]), Number(m[2])] : null;
}

/** 版本比较：返回 -1 / 0 / 1；任一不可解析返回 null */
export function cmpVersion(a, b) {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  if (!pa || !pb) return null;
  for (let i = 0; i < 2; i += 1) {
    if (pa[i] !== pb[i]) return pa[i] < pb[i] ? -1 : 1;
  }
  return 0;
}

function manifestReject(scriptId, reasons) {
  console.error(`❌ 守卫拒绝（清单/结构层，exit ${EXIT_MANIFEST}）：${scriptId}`);
  for (const r of reasons) console.error("   ·", r);
  process.exit(EXIT_MANIFEST);
}

/**
 * 建立守卫实例。
 * @param {object} cfg
 * @param {string} cfg.scriptId      脚本标识（用于日志）
 * @param {string} cfg.targetPath    目标交付物 JSON 的绝对路径
 * @param {string} cfg.fromVersion   前提版本
 * @param {string} cfg.toVersion     目标版本
 * @param {Array}  cfg.changeManifest 变更清单
 * @param {Array}  cfg.assertManifest 断言点清单
 * @param {Array}  [cfg.argv]        命令行参数（默认 process.argv）
 */
export function createGuard(cfg) {
  const {
    scriptId,
    targetPath,
    fromVersion,
    toVersion,
    changeManifest = [],
    assertManifest = [],
    argv = process.argv,
  } = cfg;

  const FORCE = argv.includes("--force");

  // ── 静态结构校验（守卫层）：清单自身不一致即拒绝执行 ──
  const problems = [];
  const byId = new Map();

  if (!Array.isArray(changeManifest) || changeManifest.length === 0) {
    problems.push("变更清单为空");
  }
  if (!Array.isArray(assertManifest) || assertManifest.length === 0) {
    problems.push("断言点清单为空");
  }

  for (const a of assertManifest) {
    if (!a || typeof a !== "object") { problems.push("断言点清单存在非对象条目"); continue; }
    if (!a.id) { problems.push("断言点条目缺 id"); continue; }
    if (byId.has(a.id)) { problems.push(`断言点 id 重复：${a.id}`); continue; }
    if (a.phase !== "pre" && a.phase !== "post") {
      problems.push(`断言点 ${a.id} 的 phase 非法（须为 pre/post）：${a.phase}`);
    }
    if (a.kind !== "change" && a.kind !== "structure") {
      problems.push(`断言点 ${a.id} 的 kind 非法（须为 change/structure）：${a.kind}`);
    }
    if (!a.source) { problems.push(`断言点 ${a.id} 未标来源（Q56②）`); }
    if (!a.desc) { problems.push(`断言点 ${a.id} 缺描述`); }
    byId.set(a.id, a);
  }

  const changeIds = new Set();
  for (const c of changeManifest) {
    if (!c || typeof c !== "object") { problems.push("变更清单存在非对象条目"); continue; }
    if (!c.id) { problems.push("变更条目缺 id"); continue; }
    if (changeIds.has(c.id)) { problems.push(`变更 id 重复：${c.id}`); continue; }
    changeIds.add(c.id);
    if (!c.target) problems.push(`变更 ${c.id} 缺 target（改哪份文件的哪个对象）`);
    if (!c.desc) problems.push(`变更 ${c.id} 缺 desc`);
    if (!Array.isArray(c.assert_ids) || c.assert_ids.length === 0) {
      problems.push(`变更 ${c.id} 未声明任何断言点`);
      continue;
    }
    for (const aid of c.assert_ids) {
      const a = byId.get(aid);
      if (!a) { problems.push(`变更 ${c.id} 引用了清单外的断言点 id：${aid}`); continue; }
      if (a.kind !== "change") {
        problems.push(`变更 ${c.id} 引用了 kind="${a.kind}" 的断言点 ${aid}（只允许引用 kind="change"）`);
      }
    }
  }

  // 孤儿断言：kind="change" 的断言点必须被至少一条变更条目引用
  const referenced = new Set();
  for (const c of changeManifest) {
    if (Array.isArray(c && c.assert_ids)) for (const aid of c.assert_ids) referenced.add(aid);
  }
  for (const a of assertManifest) {
    if (a && a.kind === "change" && !referenced.has(a.id)) {
      problems.push(`断言点 ${a.id} 属 kind="change" 但未被任何变更条目引用（孤儿断言）`);
    }
  }

  if (problems.length) manifestReject(scriptId, problems);

  // ── 运行期状态 ──
  const evaluated = new Map();   // id -> {ok, msg}
  let phase = "pre";
  let closed = false;

  function summary(extra) {
    const preIds = assertManifest.filter((a) => a.phase === "pre").map((a) => a.id);
    const postIds = assertManifest.filter((a) => a.phase === "post").map((a) => a.id);
    const preEval = preIds.filter((id) => evaluated.has(id)).length;
    const postEval = postIds.filter((id) => evaluated.has(id)).length;
    const preFail = preIds.filter((id) => evaluated.get(id) && !evaluated.get(id).ok).length;
    const postFail = postIds.filter((id) => evaluated.get(id) && !evaluated.get(id).ok).length;
    const line = [
      "[PATCH-GUARD]",
      `script=${scriptId}`,
      `target=${targetPath.split("/").slice(-2).join("/")}`,
      `change_manifest=${changeManifest.length}`,
      `assert_manifest=${assertManifest.length}`,
      `pre=${preEval}/${preIds.length}`,
      `post=${postEval}/${postIds.length}`,
      `fail_pre=${preFail}`,
      `fail_post=${postFail}`,
      extra || "",
    ].filter(Boolean).join(" ");
    console.log(line);
  }

  const guard = {
    /** 版本冻结门：判定为 NO-OP / 前置不满足时**直接结束进程**，后续代码不执行。 */
    freeze() {
      let disk;
      try {
        disk = JSON.parse(readFileSync(targetPath, "utf8")).version;
      } catch (e) {
        console.error(`❌ 守卫拒绝（无法读取目标版本，exit ${EXIT_MANIFEST}）：${targetPath}`);
        console.error("   ·", e.message);
        process.exit(EXIT_MANIFEST);
      }
      if (FORCE) {
        console.log(`[PATCH-GUARD] script=${scriptId} --force 已启用：跳过版本冻结门（盘上 ${disk}，本脚本 ${fromVersion}→${toVersion}）`);
        return { status: "FORCE", disk };
      }
      if (disk === fromVersion) {
        console.log(`[PATCH-GUARD] script=${scriptId} 版本门：盘上 ${disk} ＝ 前提 ${fromVersion} → 允许执行（目标 ${toVersion}）`);
        return { status: "EXECUTE", disk };
      }
      if (disk === toVersion) {
        console.log(`[NO-OP] ${scriptId}：盘上版本 ${disk} ＝ 本脚本目标版本 ${toVersion} —— 本补丁已执行过，不重复写盘（run-once 冻结，exit 0）。`);
        summary("status=NO-OP_ALREADY");
        process.exit(EXIT_OK);
      }
      const c = cmpVersion(disk, toVersion);
      if (c !== null && c > 0) {
        console.log(`[NO-OP] ${scriptId}：盘上版本 ${disk} 已超过本脚本目标版本 ${toVersion} —— 本补丁已过时（已演进），不写盘（run-once 冻结，exit 0）。`);
        summary("status=NO-OP_EVOLVED");
        process.exit(EXIT_OK);
      }
      const cf = cmpVersion(disk, fromVersion);
      if (cf !== null && cf < 0) {
        console.error(`❌ 前置版本不满足（exit ${EXIT_PRECOND}）：${scriptId} 盘上版本 ${disk} 早于本脚本前提 ${fromVersion} —— 前置补丁未落，不越序执行。`);
        summary("status=BLOCKED_OUT_OF_ORDER");
        process.exit(EXIT_PRECOND);
      }
      console.error(`❌ 守卫拒绝（盘上版本 ${disk} 无法与 ${fromVersion}/${toVersion} 比较，exit ${EXIT_MANIFEST}）`);
      summary("status=BLOCKED_UNPARSABLE");
      process.exit(EXIT_MANIFEST);
    },

    /**
     * 登记一条断言点。cond 为真表示通过；msg 为不通过时的说明。
     * id 必须在清单内、phase 必须与当前阶段一致、同一 id 不得重复登记。
     */
    assertPoint(id, cond, msg) {
      const a = byId.get(id);
      if (!a) {
        console.error(`❌ 守卫拒绝（登记了清单外的断言点 id：${id}，exit ${EXIT_MANIFEST}）`);
        process.exit(EXIT_MANIFEST);
      }
      if (a.phase !== phase) {
        console.error(`❌ 守卫拒绝（断言点 ${id} 声明 phase="${a.phase}"，当前阶段 phase="${phase}"，exit ${EXIT_MANIFEST}）`);
        process.exit(EXIT_MANIFEST);
      }
      if (evaluated.has(id)) {
        console.error(`❌ 守卫拒绝（断言点 ${id} 被重复登记，exit ${EXIT_MANIFEST}）`);
        process.exit(EXIT_MANIFEST);
      }
      evaluated.set(id, { ok: !!cond, msg: msg || "" });
      return !!cond;
    },

    /** 写盘前收口：pre 阶段双射校验 + 失败汇总。 */
    finishPre() {
      const preIds = assertManifest.filter((a) => a.phase === "pre").map((a) => a.id);
      const missing = preIds.filter((id) => !evaluated.has(id));
      if (missing.length) {
        console.error(`❌ 守卫拒绝（写盘前清单校验未过，exit ${EXIT_MANIFEST}）：${scriptId}`);
        console.error(`   · 断言点清单 ${assertManifest.length} 条，其中 pre 阶段 ${preIds.length} 条；实际登记 ${evaluated.size} 条`);
        console.error(`   · pre 阶段未被登记的断言点（${missing.length} 条）：${missing.join(", ")}`);
        console.error("   · ⇒ 清单条数 ≠ 实际断言点数，拒绝写盘。");
        summary("status=MANIFEST_MISMATCH");
        process.exit(EXIT_MANIFEST);
      }
      const failed = preIds.filter((id) => !evaluated.get(id).ok);
      if (failed.length) {
        console.error(`❌ 中止（${failed.length} 条断言不通过，不写盘，exit ${EXIT_ASSERT}）：${scriptId}`);
        for (const id of failed) console.error("   ·", id, "—", evaluated.get(id).msg);
        summary("status=ASSERT_FAILED");
        process.exit(EXIT_ASSERT);
      }
      closed = true;
      phase = "post";
      summary("status=PRE_OK");
      return true;
    },

    /** 写盘后收口：post 阶段双射校验 + 失败汇总。 */
    finishPost() {
      if (!closed) {
        console.error(`❌ 守卫拒绝（未经过写盘前收口就进入写后阶段，exit ${EXIT_MANIFEST}）：${scriptId}`);
        process.exit(EXIT_MANIFEST);
      }
      const postIds = assertManifest.filter((a) => a.phase === "post").map((a) => a.id);
      const missing = postIds.filter((id) => !evaluated.has(id));
      if (missing.length) {
        console.error(`❌ 守卫拒绝（写后清单校验未过，exit ${EXIT_MANIFEST}）：${scriptId}`);
        console.error(`   · post 阶段未被登记的断言点（${missing.length} 条）：${missing.join(", ")}`);
        summary("status=MANIFEST_MISMATCH");
        process.exit(EXIT_MANIFEST);
      }
      const failed = postIds.filter((id) => !evaluated.get(id).ok);
      if (failed.length) {
        console.error(`❌ 写后回读失败（${failed.length} 条断言不通过，exit ${EXIT_ASSERT}）：${scriptId}`);
        for (const id of failed) console.error("   ·", id, "—", evaluated.get(id).msg);
        summary("status=POST_ASSERT_FAILED");
        process.exit(EXIT_ASSERT);
      }
      summary("status=OK");
      return true;
    },

    /** 仅供自测器/日志使用：取已登记的断言点结果快照 */
    snapshot() {
      return {
        scriptId,
        changeManifest,
        assertManifest,
        evaluated: [...evaluated.entries()].map(([id, r]) => ({ id, ok: r.ok, msg: r.msg })),
      };
    },
  };

  return guard;
}
