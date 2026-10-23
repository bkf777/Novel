#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`patch_D16_U02_d15_version_history.py` 的沙箱负测器（分镜导演岗 · Q68 七腿）。

受检 7 条，全部在**沙箱副本**上跑，真盘 `units/U02/D16.json` 与 `units/U02/D15.json`
**逐字节不得被触碰**（腿 F 独立复核）。

⚠ 夹具自建（2026-10-23 订正）—— 初版自测器有真实缺陷，已修
------------------------------------------------------------------
初版 `make_sandbox()` 直接 `shutil.copy2` 真盘 D16 U02。落盘后真盘已由 v1.5 升到 **v1.6**，
沙箱因此带着 v1.6 进脚本 → **守卫①（版本锚定 v1.5）先触发 → 所有腿都走 `[NO-OP]`**：

| 腿 | 期望 | 初版实得（真盘已 v1.6 时） | 判定 |
|---|---|---|---|
| A 正常升版   | exit 0 / v1.6 / 8 键 | exit 0 / v1.6 / 8 键 | ❌ **假通过**（根本没走升版路径） |
| B 幂等复跑   | `[NO-OP]` / 字节不变 | `[NO-OP]` / 字节不变 | ⚠ **因错误的原因通过**（被守卫①而非幂等守卫挡下） |
| C 版本守卫   | `[NO-OP]` / 仍 v9.9 | 同 | ✅ 原因对（版本守卫） |
| D 半落拒绝   | exit 1 / `[ABORT]` | exit 0 / `[NO-OP]` | ❌ **真 FAIL** |
| E 证据不符拒绝 | exit 1 / `[ABORT]` | exit 0 / `[NO-OP]` | ❌ **真 FAIL** |
| F 沙箱隔离   | 真盘两文件指纹不变 | 同 | ✅ |

⇒ 「结果：4/6 通过」**不是生产脚本退化**，是**夹具随真盘漂移 → 守卫被旁路 → 断言空转**
（与 Q56/Q68「夹具已满足会使断言空转」同族，方向相反：不是夹具已满足，而是夹具**已越过锚点**）。
**此结论只在本文件修好后才成立；修前不得据「4/6」对生产脚本下任何判断。**

订正：夹具**自建于声明基线 v1.5**（由真盘反演：剥 8 处新增键 ＋ version 复位），
并与落盘前备份 `reports/_bak_U02_D16_d15hist_20261023-103234/D16.json` 做 **JSON 全等对账**（腿 G）。
实测反演结果与备份 **JSON 全等 = True**（备份缺失时退化为仅自证 version/键态，并在结果中标注）。
另给腿 A 加「**必须真的走写盘路径**（`[DONE]` ＋ `[EVIDENCE]`）」断言，杜绝再出现**因错误的原因通过**。

腿
----
A. 正常升版       ：v1.5 → v1.6，8 集各落 1 处 `d15_version_history`，exit 0，**且确实写了盘**
B. 幂等复跑       ：再跑一次 → `[NO-OP]` exit 0，**字节不变**
C. 版本守卫       ：盘面置 v9.9 → `[NO-OP]` exit 0，**字节不变**
D. 半落状态       ：仅 5 集已落 → `[ABORT]` exit 1，**字节不变**（半落不可续写）
E. 证据不符       ：沙箱 D15 sfx 改 65 → `[ABORT]` exit 1，**D16 字节不变**
F. 沙箱隔离       ：真盘两文件 SHA256 与开跑前一致
G. 夹具基线自证   ：沙箱 D16 ＝ v1.5、0/8 集带该键，且与落盘前备份 JSON 全等

用法
----
python3 scripts/selftest_D16_U02_d15_version_history.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "patch_D16_U02_d15_version_history.py")
UNIT = "U02"
KEY = "d15_version_history"
BASE_VERSION = "v1.5"
BAK_REL = os.path.join("reports", "_bak_U02_D16_d15hist_20261023-103234", "D16.json")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def canon(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def revert_to_baseline(d16):
    """把 D16 反演回声明基线 v1.5：剥 8 处新增键 ＋ version 复位。

    反演依据：本轮落盘的结构化 diff ＝「version 1 处 ＋ 新增键 8 处」，零其他改动，
    故反演可精确还原落盘前状态（由腿 G 与落盘前备份做 JSON 全等对账自证）。
    """
    d = json.loads(json.dumps(d16, ensure_ascii=False))
    d["version"] = BASE_VERSION
    for e in d.get("episodes") or []:
        a = (e.get("subtitle_style") or {}).get("subtitle_sync_audit") or {}
        a.pop(KEY, None)
    return d


def make_sandbox():
    """造一个含 units/U02/{D16,D15}.json 的沙箱项目副本。

    D16 夹具**自建于基线 v1.5**（不从真盘现况直接拷贝）—— 防夹具漂移旁路守卫。
    """
    sb = tempfile.mkdtemp(prefix="_sx_d16u02hist_")
    os.makedirs(os.path.join(sb, "units", UNIT))
    os.makedirs(os.path.join(sb, "reports"))
    for art in ("D16", "D15"):
        shutil.copy2(os.path.join(PROJ, "units", UNIT, f"{art}.json"),
                     os.path.join(sb, "units", UNIT, f"{art}.json"))
    p16 = os.path.join(sb, "units", UNIT, "D16.json")
    dump(p16, revert_to_baseline(load(p16)))
    return sb


def count_key(d16):
    return sum(1 for e in d16.get("episodes") or []
               if KEY in ((e.get("subtitle_style") or {}).get("subtitle_sync_audit") or {}))


def run(sb, extra=None):
    env = dict(os.environ)
    env["SXR_ROOT"] = sb
    cmd = [sys.executable, SCRIPT, "--project", sb, "--unit", UNIT] + (extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    real16 = os.path.join(PROJ, "units", UNIT, "D16.json")
    real15 = os.path.join(PROJ, "units", UNIT, "D15.json")
    sha16_before, sha15_before = sha(real16), sha(real15)
    live_ver = load(real16).get("version")
    results = []

    def rec(name, ok, detail):
        results.append((name, ok, detail))
        print(("  ✅ " if ok else "  ❌ ") + name + " — " + detail)

    print(f"◆ 真盘 D16 {UNIT} 当前 version={live_ver}｜夹具自建于基线 {BASE_VERSION}"
          f"（不随真盘漂移）｜真盘 SHA16 前16={sha16_before[:16]}")

    # ── 腿 G：夹具基线自证（先跑，防止后续腿建立在错误基线上）──
    sb_g = make_sandbox()
    p16g = os.path.join(sb_g, "units", UNIT, "D16.json")
    dg = load(p16g)
    ver_g, n_g = dg.get("version"), count_key(dg)
    bak = os.path.join(PROJ, BAK_REL)
    if os.path.isfile(bak):
        same = canon(load(bak)) == canon(dg)
        ok_g = (ver_g == BASE_VERSION and n_g == 0 and same)
        det_g = (f"夹具 version={ver_g}｜残留 `{KEY}` {n_g}/8 集｜"
                 f"与落盘前备份 JSON 全等={same}")
    else:
        same = None
        ok_g = (ver_g == BASE_VERSION and n_g == 0)
        det_g = (f"夹具 version={ver_g}｜残留 `{KEY}` {n_g}/8 集｜"
                 f"⚠ 备份缺失（{BAK_REL}），未做全等对账")
    rec("腿G 夹具基线自证", ok_g, det_g)
    shutil.rmtree(sb_g, ignore_errors=True)

    # ── 腿 A：正常升版 ──
    sb = make_sandbox()
    p16 = os.path.join(sb, "units", UNIT, "D16.json")
    rc, out = run(sb)
    d = load(p16)
    n = count_key(d)
    ok = (rc == 0 and d["version"] == "v1.6" and n == 8
          and "[DONE]" in out and "[EVIDENCE]" in out)
    rec("腿A 正常升版", ok,
        f"exit={rc} version={d['version']} 落键={n}/8 "
        f"走写盘路径('[DONE]'={'[DONE]' in out}, '[EVIDENCE]'={'[EVIDENCE]' in out})")

    # ── 腿 B：幂等复跑（字节不变）──
    b1 = sha(p16)
    rc2, out2 = run(sb)
    b2 = sha(p16)
    ok = (rc2 == 0 and "[NO-OP]" in out2 and b1 == b2)
    rec("腿B 幂等复跑", ok, f"exit={rc2} NO-OP={'[NO-OP]' in out2} 字节不变={b1 == b2}")

    # ── 腿 C：版本守卫（v9.9）──
    sb2 = make_sandbox()
    p16b = os.path.join(sb2, "units", UNIT, "D16.json")
    dd = load(p16b)
    dd["version"] = "v9.9"
    dump(p16b, dd)
    c1 = sha(p16b)
    rc3, out3 = run(sb2)
    c2 = sha(p16b)
    ok = (rc3 == 0 and "[NO-OP]" in out3 and c1 == c2 and load(p16b)["version"] == "v9.9")
    rec("腿C 版本守卫", ok,
        f"exit={rc3} NO-OP={'[NO-OP]' in out3} 字节不变={c1 == c2} "
        f"version 仍={load(p16b)['version']}")

    # ── 腿 D：半落状态（5 集已落）──
    sb3 = make_sandbox()
    p16c = os.path.join(sb3, "units", UNIT, "D16.json")
    dd = load(p16c)
    for e in dd["episodes"][:5]:
        e["subtitle_style"]["subtitle_sync_audit"][KEY] = {"x": 1}
    dump(p16c, dd)
    d1 = sha(p16c)
    rc4, out4 = run(sb3)
    d2 = sha(p16c)
    ok = (rc4 == 1 and "[ABORT]" in out4 and d1 == d2)
    rec("腿D 半落状态拒绝", ok,
        f"exit={rc4} ABORT={'[ABORT]' in out4} 字节不变={d1 == d2}")

    # ── 腿 E：证据不符（沙箱 D15 sfx 改 65）──
    sb4 = make_sandbox()
    p16d = os.path.join(sb4, "units", UNIT, "D16.json")
    p15d = os.path.join(sb4, "units", UNIT, "D15.json")
    dd = load(p15d)
    dd["episodes"][0]["sfx"] = dd["episodes"][0]["sfx"][:-1]  # sfx 66 → 65
    dump(p15d, dd)
    e1 = sha(p16d)
    rc5, out5 = run(sb4)
    e2 = sha(p16d)
    ok = (rc5 == 1 and "[ABORT]" in out5 and e1 == e2)
    rec("腿E v1.2 证据不符拒绝", ok,
        f"exit={rc5} ABORT={'[ABORT]' in out5} D16 字节不变={e1 == e2}")

    # ── 腿 F：沙箱隔离（真盘未被触碰）──
    sha16_after, sha15_after = sha(real16), sha(real15)
    ok = (sha16_after == sha16_before and sha15_after == sha15_before)
    rec("腿F 沙箱隔离", ok,
        f"D16 指纹一致={sha16_after == sha16_before} D15 指纹一致={sha15_after == sha15_before}")

    for sb_ in (sb, sb2, sb3, sb4):
        shutil.rmtree(sb_, ignore_errors=True)

    npass = sum(1 for _n, ok, _d in results if ok)
    print(f"\n结果：{npass}/{len(results)} 通过")
    if npass != len(results):
        sys.exit(1)
    print("[OK] 全部通过")


if __name__ == "__main__":
    main()
