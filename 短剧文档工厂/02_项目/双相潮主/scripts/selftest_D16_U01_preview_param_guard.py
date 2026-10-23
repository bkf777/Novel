#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙箱自测器：验证 scripts/patch_D16_U01_preview_param_dep.py 的守卫有效性（Q68／Q73）。

四腿实跑（全部在沙箱副本内，真盘零写入）
----------------------------------------
| 腿 | 场景 | 期望 |
|---|---|---|
| A | 正常升版（沙箱盘 v1.11，锚定一致） | exit 0；产物含声明；时码数值 0 改动；A6 判别力检验 |
| B | 幂等重跑（A 的产物再跑一次） | exit 0；产物字节与 A 完全一致；输出含 [NO-OP] |
| C | 伪造高版本（沙箱盘改 v9.9） | **exit≠0**；磁盘字节未被改写；无 traceback |
| D | 伪造高版本 ＋ `--force` | exit 0；放行且版本 **minor 递增**为 v9.10（不回落 v1.12、不降 major） |

守卫有效性四件套的判别力要求
--------------------------
C 腿若误放行（exit 0 且盘被改写）→ 版本守卫无效；
D 腿若被拒 → `--force` 逃生口失效；
D 腿若把版本写成 v1.12（低于原 v9.9）→ 逃生口造成版本回退，判不合格。

分层守卫的执行顺序（教训：上游守卫抢先 exit 会把下游守卫的合法路径挡死）
--------------------------------------------------------------------
B 腿是这条教训的检验点：若「版本守卫」排在「内容态幂等守卫」之前，则本脚本自己写出的
v1.12 在第二次运行时会���版本守卫当成「他人升版」而拒写（exit 1），
幂等路径被遮蔽、字节一致性无从检验。故**幂等判定必须前置**。

真盘零写入的证法
----------------
测试前后对**真盘** `units/U01/D16.json` 与 `units/U02/D16.json` 做 SHA256 比对，
必须逐字节一致。

沙箱构造：**「内容未应用」的前态**（不是现盘）
----------------------------------------------------
沙箱根由 `__file__` 推导（不依赖 cwd、不依赖环境变量）→ 复制真盘 `units/U01/D16.json`
与 `units/U01/D15.json` 到沙箱；脚本以 `--project <沙箱>` 调用。

⚠️ **夹具必须是「声明尚未应用」的前态**，不能直接用现盘。现盘 v1.12 **已含**声明与
`preview_param_dependency`，脚本的内容态幂等守卫会先行 `[NO-OP]` → 后果有二：
  ① **腿 A 空转**：A2「8/8 含声明」、A4「version=v1.12」、A5「数值零改动」全部被
     「夹具已满足」蒙过 —— 「正常升版」能力**从未被真正检验**；
  ② **腿 C/D 的版本守卫路径不可达**：C 腿期望 exit≠0、D 腿期望 --force 放行，
     但内容态守卫抢先 exit 0 → 两条腿必然判红。
⇒ 修法：`make_sandbox()` 复制后**精确逆向**出前态（剥 `verified_note` 末段声明 ＋
删 `preview_param_dependency` 键 ＋ 删该条 `sync_records` ＋ 版本置回 v1.11），
并对每条腿**加一条夹具自检**（8 集 verified_note 必须 0/8 含 MARK），
使「夹具已满足 ⇒ 该腿空转」这一类假阳性**在结构上不可能再发生**。

判别力补充：腿 D 的 --force 放行必须**真的改到内容**（声明由无到有）才成立；
若内容本就满足而仅升版本，那是项目明令禁止的**空版本跳**，不构成「逃生口有效」的证据。

受检条数
--------
21 条（A 腿 7 条 ／ B 腿 3 条 ／ C 腿 5 条 ／ D 腿 4 条 ／ 真盘零写入 2 条），实跑输出
「受检 N 条 / 通过 N 条」。

边界
----
只读真盘、只在沙箱内写盘；不生成图片/视频/音频，不提交 H3 付费生成，不投流上架。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "patch_D16_U01_preview_param_dep.py")
# 真盘根：scripts/ 的上上级 = 项目目录；再上两级 = 工厂目录
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_D16_U01 = os.path.join(PROJ, "units", "U01", "D16.json")
REAL_D16_U02 = os.path.join(PROJ, "units", "U02", "D16.json")

# 声明标记（与被测脚本的 MARK 同源）：内容态幂等守卫的判据
MARK = "预演参数依赖声明"
# 声明段在 verified_note 末尾的起始前缀（S11 只追加 → 截断即可精确逆向）
DECL_START = "｜2026-10-23 预演参数依赖声明"
# 该次落盘新增的结构化字段
NEW_FIELD = "preview_param_dependency"

results = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" —— {detail}" if detail else ""))
    return bool(ok)


def revert_to_prepatch(p_d16, version):
    """把沙箱 D16 精确逆向回「声明尚未应用」的前态。

    逆向三处（与被测脚本的写入严格一一对应）：
      ① `verified_note` 末段声明（自 DECL_START 起截断 —— S11 只追加，前缀即原串）
      ② 新增结构化字段 `preview_param_dependency`
      ③ 本次落盘追加的那条 `sync_records`（按 event 匹配，不按序号，避免误删他人条目）
    再把 version 置为指定值。
    """
    doc = json.load(open(p_d16, encoding="utf-8"))
    for e in doc.get("episodes", []):
        a = e["subtitle_style"]["subtitle_sync_audit"]
        vn = a.get("verified_note", "")
        i = vn.find(DECL_START)
        if i >= 0:
            a["verified_note"] = vn[:i]
        a.pop(NEW_FIELD, None)
        recs = a.get("sync_records")
        if isinstance(recs, list):
            a["sync_records"] = [r for r in recs
                                 if MARK not in str(r.get("event", ""))]
    doc["version"] = version
    json.dump(doc, open(p_d16, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def fixture_is_prepatch(p_d16):
    """夹具自检：8 集 verified_note **必须 0/8** 含 MARK —— 否则该腿会空转。"""
    doc = json.load(open(p_d16, encoding="utf-8"))
    n = sum(1 for e in doc.get("episodes", [])
            if MARK in e["subtitle_style"]["subtitle_sync_audit"].get("verified_note", ""))
    return n == 0, n


def make_sandbox(tag, version="v1.11"):
    root = tempfile.mkdtemp(prefix=f"_sandbox_{tag}_")
    u01 = os.path.join(root, "units", "U01")
    os.makedirs(u01, exist_ok=True)
    p_d16 = os.path.join(u01, "D16.json")
    shutil.copy2(REAL_D16_U01, p_d16)
    shutil.copy2(os.path.join(PROJ, "units", "U01", "D15.json"),
                 os.path.join(u01, "D15.json"))
    revert_to_prepatch(p_d16, version)   # ← 关键：夹具是「前态」，不是现盘
    return root, p_d16


def run(root, extra=()):
    cmd = [sys.executable, SCRIPT, "--project", root, "--unit", "U01"] + list(extra)
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def nums(obj, path="", out=None):
    """收集所有数值叶子 (路径, 值)。

    注意：新增的 `preview_param_dependency` 结构化字段内含 3 个**证据数值**
    （items_json_dur 3.41746／ffprobe_dur 2.800／差 0.617），它们是声明陈旧条目的
    佐证、不是时码数值。故比对时须排除该字段前缀（见 strip_new_field）。
    """
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            nums(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            nums(v, f"{path}[{i}]", out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append((path, obj))
    return out


def strip_new_field(pairs):
    """剔除新增结构化字段下的数值叶子（该字段本轮新增，其证据数值不算时码改动）。"""
    return [(p, v) for p, v in pairs if f".{NEW_FIELD}" not in p]


def main():
    if not os.path.isfile(SCRIPT):
        sys.exit(f"[ABORT] 找不到被测脚本：{SCRIPT}")
    if not os.path.isfile(REAL_D16_U01):
        sys.exit(f"[ABORT] 找不到真盘 D16 U01：{REAL_D16_U01}")

    print(f"[SANDBOX] 被测脚本：{SCRIPT}")
    print(f"[SANDBOX] 真盘 D16 U01：{REAL_D16_U01}（{os.path.getsize(REAL_D16_U01)} B）")

    # 真盘 SHA256 基线
    real_before_u01 = sha(REAL_D16_U01)
    real_before_u02 = sha(REAL_D16_U02)

    sandboxes = []

    # ── 腿 A：正常升版 ──
    print("\n── 腿 A：正常升版（沙箱盘 v1.11） ──")
    root_a, p_a = make_sandbox("A")
    sandboxes.append(root_a)
    base = json.load(open(p_a, encoding="utf-8"))
    base_nums = strip_new_field(nums(base))
    ok_pre, n_pre = fixture_is_prepatch(p_a)
    check("A0 夹具有效：8 集 verified_note 0/8 含声明（前态，否则本腿空转）",
          ok_pre, f"命中 {n_pre}/8")
    rc, out, err = run(root_a)
    print(out.strip()[:600])
    if err.strip():
        print("STDERR:", err.strip()[:400])
    check("A1 exit 0", rc == 0, f"rc={rc}")
    a_after = json.load(open(p_a, encoding="utf-8"))
    notes = [e["subtitle_style"]["subtitle_sync_audit"]["verified_note"] for e in a_after["episodes"]]
    check("A2 8/8 集 verified_note 含「预演参数依赖声明」",
          sum(1 for s in notes if "预演参数依赖声明" in s) == 8,
          f"命中 {sum(1 for s in notes if '预演参数依赖声明' in s)}/8")
    check("A3 8/8 集新增结构化字段 preview_param_dependency",
          sum(1 for e in a_after["episodes"]
              if "preview_param_dependency" in e["subtitle_style"]["subtitle_sync_audit"]) == 8)
    check("A4 version v1.11 → v1.12", a_after.get("version") == "v1.12", a_after.get("version"))
    after_nums = strip_new_field(nums(a_after))
    check("A5 时码数值字段逐条无差异（剔除新增字段的证据数值）",
          base_nums == after_nums,
          f"{len(base_nums)} 个数值叶子，差异 {sum(1 for x, y in zip(base_nums, after_nums) if x != y)}")
    # 判别力检验：若时码真被改动，A5 必须能抓到（否则该判据零信息量）
    probe = json.loads(json.dumps(a_after))
    probe["episodes"][0]["subtitle_style"]["lines"][0]["out_sec"] = 999
    check("A6 判别力：篡改一处 out_sec 后 A5 判据应报错",
          strip_new_field(nums(probe)) != after_nums)
    a_bytes = open(p_a, "rb").read()

    # ── 腿 B：幂等重跑 ──
    print("\n── 腿 B：幂等重跑（A 产物再跑一次） ──")
    rc_b, out_b, err_b = run(root_a)
    if err_b.strip():
        print("STDERR:", err_b.strip()[:300])
    b_bytes = open(p_a, "rb").read()
    check("B1 exit 0", rc_b == 0, f"rc={rc_b}")
    check("B2 产物字节与 A 完全一致（幂等）", b_bytes == a_bytes,
          f"{len(a_bytes)} B vs {len(b_bytes)} B")
    check("B3 输出含 [NO-OP]", "[NO-OP]" in out_b)

    # ── 腿 C：伪造高版本 → 拒绝 ──
    print("\n── 腿 C：伪造高版本（沙箱盘改 v9.9） → 应拒绝且磁盘不改 ──")
    root_c, p_c = make_sandbox("C", version="v9.9")
    sandboxes.append(root_c)
    ok_pre, n_pre = fixture_is_prepatch(p_c)
    check("C0 夹具有效：前态 0/8 含声明（否则版本守卫路径不可达）",
          ok_pre, f"命中 {n_pre}/8")
    c_before = open(p_c, "rb").read()
    rc_c, out_c, err_c = run(root_c)
    if out_c.strip():
        print(out_c.strip()[:400])
    if err_c.strip():
        print("STDERR:", err_c.strip()[:300])
    c_after = open(p_c, "rb").read()
    check("C1 exit≠0（版本守卫拒绝）", rc_c != 0, f"rc={rc_c}")
    check("C2 磁盘字节未被改写", c_before == c_after)
    check("C3 拒绝原因可辨（stderr 含「版本守卫」）",
          "版本守卫" in (out_c + err_c))
    check("C4 无 traceback（区别「守卫拒绝」与「脚本报错」）",
          "Traceback" not in (out_c + err_c))

    # ── 腿 D：伪造高版本 ＋ --force → 放行且版本递增 ──
    print("\n── 腿 D：伪造高版本 ＋ --force → 应放行且版本递增不回落 ──")
    root_d, p_d = make_sandbox("D", version="v9.9")
    sandboxes.append(root_d)
    ok_pre, n_pre = fixture_is_prepatch(p_d)
    check("D0 夹具有效：前态 0/8 含声明（否则 --force 路径不可达）",
          ok_pre, f"命中 {n_pre}/8")
    rc_d, out_d, err_d = run(root_d, extra=("--force",))
    if out_d.strip():
        print(out_d.strip()[:500])
    if err_d.strip():
        print("STDERR:", err_d.strip()[:300])
    d_after = json.load(open(p_d, encoding="utf-8"))
    check("D1 exit 0（--force 逃生口放行）", rc_d == 0, f"rc={rc_d}")
    check("D2 版本 minor 递增为 v9.10（不回落 v1.12、不降 major）",
          d_after.get("version") == "v9.10", d_after.get("version"))
    check("D3 8/8 集仍含声明（内容层照常执行）",
          sum(1 for e in d_after["episodes"]
              if "预演参数依赖声明" in e["subtitle_style"]["subtitle_sync_audit"]["verified_note"]) == 8)

    # ── 真盘零写入 ──
    print("\n── 真盘零写入核对 ──")
    real_after_u01 = sha(REAL_D16_U01)
    real_after_u02 = sha(REAL_D16_U02)
    check("E1 真盘 D16 U01 SHA256 前后一致", real_before_u01 == real_after_u01,
          f"{real_before_u01[:16]}… → {real_after_u01[:16]}…")
    check("E2 真盘 D16 U02 SHA256 前后一致", real_before_u02 == real_after_u02,
          f"{real_before_u02[:16]}… → {real_after_u02[:16]}…")

    # 清理沙箱
    for r in sandboxes:
        shutil.rmtree(r, ignore_errors=True)

    passed = sum(1 for _n, ok, _d in results if ok)
    total = len(results)
    print("\n" + "=" * 62)
    print(f"受检 {total} 条 / 通过 {passed} 条 / 不通过 {total - passed} 条")
    for n, ok, d in results:
        if not ok:
            print(f"  ❌ {n} —— {d}")
    print("=" * 62)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
