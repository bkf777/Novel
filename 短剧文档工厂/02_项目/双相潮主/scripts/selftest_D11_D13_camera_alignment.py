#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""沙箱负测自测器：`check_D11_D13_camera_alignment.py` 的判据有效性检验（Q67／Q68）。

【为什么要有】
  该校验器只用于**发现**「白模分离完成后 D11 该改、还没改」的状态。
  若判据恒真或误报，则它的「零冲突」结论毫无信息量（Q67：恒真断言零信息量）。
  ⇒ 必须证明：① 判据能抓到真缺陷；② 判据不会把非缺陷判成硬失败；
     ③ 判据在**真实落盘措辞**上同样有效（不能只在简化夹具上有效）。

【纪律】
  · **负测只在沙箱副本做**（Q68）：临时目录内复制 units/U01/D11.json 与 D13.json，
    沙箱结构与真盘一致（<tmp>/units/U01/{D11,D13}.json）；
  · **真盘零写入**：自测前后对真盘 6 份交付物做 SHA256 比对；
  · **区分「守卫拒绝」与「沙箱脚本报错」**（Q73）：断言看的是**校验器输出文本**
    与**退出码**，不是 Python 栈回溯；
  · **每腿独立沙箱**（首版即踩此坑：L2 删掉的机位残留到 L3/L4，导致两腿假红）。

【⚠️ 夹具形态必须 == 真实落盘形态（本版新增的核心纪律）】
  首版旧判据自测「全绿」，但**真盘上判据是坏的**：旧版把「视点代表位」与
  「眼位重合／角色视点」并入同一键组 pov_d13，于是白模真落地
  「机位与角色眼位分离 0.35 m … 视线自**视点代表位**…本镜为近似 POV」时
  pov_d13 仍为真 → 误判「分离前一致」→ **该报的「待同步」没报**。
  旧夹具之所以没暴露：它把 notes 写成**简化措辞**「机位与角色眼位分离 0.35 m
  （…），视线下俯约 35° 指向右腕」—— **不含「视点代表位」**，与真实落盘形态不同。
  ⇒ **夹具写成「另一种说法」会掩盖真实措辞的缺陷**。
  ⇒ 本版：L3/L4 直接用**真盘 g27 notes 的逐字原文**作夹具；
     并新增 L5/L6 两条**真实落盘形态回归腿**，专门盯这一类假绿。

【腿】
  L1 基线：现盘沙箱副本 → exit 0、硬失败 0、受检 32 组、
           待同步（B2）1 处、分离前一致（B3）4 处、已分离·非 POV（B5）1 处、
           口径不对称（B6）1 处、计数自证「32 ＝ 32」
  L2 判据 A 有区分力：沙箱删 D13 一条机位 → **exit 1** 且输出含「配对缺失」
  L3 判据 B「待同步」有区分力：沙箱把 D13 ep7/镜3 改成**真实落盘措辞**（分离 0.35 m
     ＋ 视点代表位 ＋ 已不是严格 POV）→ 输出含「待同步」且 **exit 0**
  L4 判据 B 收敛：同一沙箱再把 D11 ep7/镜3 camera_angle 改成「近似 POV（视点代表位）」
     → 「待同步」消失、转为「已按裁定标注」，且 exit 0
  L5 **真实落盘形态回归**：直接用**真盘 g27 的 notes 逐字原文**（不改一个字）灌进沙箱
     → 校验器必须仍判「待同步」⇒ 证明判据不依赖夹具措辞
  L6 **措辞区分力（防旧缺陷复发）**：把 g27 notes 改成**与真实措辞同义但不含
     「视点代表位」**的简化版 → 判据**仍**须报「待同步」⇒ 证明判据不靠关键词表硬套，
     而是真正读「是否已分离」这条语义轴
  L7 真盘零写入：自测前后真盘 6 份交付物 SHA256 逐字节一致

用法：python3 scripts/selftest_D11_D13_camera_alignment.py [--project .]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_D11_D13_camera_alignment.py")
WATCH = ["units/U01/D11.json", "units/U01/D13.json", "units/U02/D11.json",
         "units/U02/D13.json", "units/U01/D16.json", "units/U02/D16.json"]

# 真盘 g27（ep007/镜3 = global_shot_no 27）白模 v1.1 落盘 notes 的**逐字原文**。
# 取自 units/U01/D13.json（v1.1, 09:28）camera_positions[global_shot_no=27].notes。
# ⚠️ 引用它是为了让夹具形态 == 真实落盘形态；**不得**改成简化措辞（会掩盖判据缺陷）。
REAL_G27_NOTES = (
    "机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量）；"
    "机位落在眼位北侧 0.35 m、与眼位等高，视线自视点代表位向下约 62° 指向右腕；"
    "分离后已不是严格 POV，本镜为近似 POV（视点代表位）；面板占位板在其视线上方"
)
# 同义但**不含「视点代表位」**的简化措辞 —— 用于 L6 证明判据读的是语义轴而非关键词表
SIMPLIFIED_G27_NOTES = (
    "机位与角色眼位分离 0.35 m（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量），"
    "视线下俯约 62° 指向右腕"
)
# D11 g27 的**未标注态** note —— D11 v1.8 的真实落盘原文（2026-10-23 10:2x 落 v1.9 之前的值）。
# ⚠️ L3/L5/L6 必须**显式钉住**这个前提，**不能依赖基线状态**：
#   真盘 D11 已按 U02-R07 在 note 追加了「近似 POV（视点代表位）」标注，
#   若夹具不自带「未标注」前提，这三腿会随真盘演进而**恒真/恒假**（假绿）。
#   ⇒ 夹具必须自带前提（与「夹具形态 == 真实落盘形态」同源的一条纪律）。
PRE_LABEL_NOTE = (
    "骨纹为体表表现，不破体、不见皮下骨骼（D07 scene_needs／D10 母题 M02）。"
    "归一度读数本集仍为 0.5%——一纹权柄上限 30 秒的单体近身焚斑不推读数（D05 T20）。"
)
# 已标注态追加段（生产实际落点：D11 note；camera_angle 是闭枚举装不下这个口径）
LABELED_SUFFIX = (
    "📌 机位视点口径订正：白模 D13 v1.1 已将本镜机位与角色眼位分离 0.35 m"
    "（角色代理体最大截面半径 0.25 m ＋ 0.10 m 余量），故本镜已不是严格 POV，"
    "按 U02-R07 附语义要求标注为近似 POV（视点代表位）。"
)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_checker(project, unit="U01"):
    p = subprocess.run([sys.executable, CHECKER, "--project", project, "--unit", unit],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def make_sandbox(project, tmp):
    dst = os.path.join(tmp, "units", "U01")
    os.makedirs(dst, exist_ok=True)
    for name in ("D11.json", "D13.json"):
        shutil.copy2(os.path.join(project, "units", "U01", name), os.path.join(dst, name))
    return tmp


def load_sb(tmp, name):
    with open(os.path.join(tmp, "units", "U01", name), "r", encoding="utf-8") as f:
        return json.load(f)


def save_sb(tmp, name, obj):
    with open(os.path.join(tmp, "units", "U01", name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def find_cam(d13, ep, gsn):
    for sc in d13.get("scenes", []):
        if sc.get("ep") != ep:
            continue
        for cp in sc.get("camera_positions", []) or []:
            if cp.get("global_shot_no") == gsn:
                return sc, cp
    return None, None


def set_d11_angle(d11, ep, shot_id, angle):
    for e in d11.get("episodes", []):
        if e.get("ep") != ep:
            continue
        for s in e.get("shots", []):
            if s.get("shot_id") == shot_id:
                s["camera_angle"] = angle
                return True
    return False


def set_d11_note(d11, ep, shot_id, note):
    """把 D11 某镜的 note 置为指定值（用于显式钉住夹具前提）。"""
    for e in d11.get("episodes", []):
        if e.get("ep") != ep:
            continue
        for s in e.get("shots", []):
            if s.get("shot_id") == shot_id:
                s["note"] = note
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    args = ap.parse_args()
    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cands = [args.project, os.path.join(factory, args.project),
             os.path.join(os.getcwd(), args.project), os.path.abspath(args.project)]
    proj = None
    for c in cands:
        if os.path.isfile(os.path.join(c, "units", "U01", "D11.json")):
            proj = os.path.abspath(c)
            break
    if proj is None:
        sys.exit(f"[ABORT] 未找到 units/U01/D11.json，候选：{cands}")

    before = {w: sha(os.path.join(proj, w)) for w in WATCH}

    results = []   # (腿号, 断言描述, 是否通过, 证据)

    sandboxes = []

    def fresh():
        """每条腿一个**全新**沙箱副本 —— 避免上一腿的夹具变更污染下一腿。"""
        d = tempfile.mkdtemp(prefix="d11d13_sbx_")
        sandboxes.append(d)
        return make_sandbox(proj, d)

    try:
        # ── L1 基线 ───────────────────────────────────────────────
        rc, out = run_checker(fresh())
        ok = (rc == 0 and "硬失败 0 ＋ 已分类 32 ＝ 32" in out
              and "待同步（B2）0 处" in out and "已按裁定标注（B1）1 处" in out
              and "分离前一致（B3）4 处" in out
              and "已分离·非 POV（B5）1 处" in out
              and "口径不对称（B6·非缺陷）1 处" in out)
        results.append(("L1", "基线：现盘副本 → exit 0／受检 32／硬失败 0／待同步 0／已按裁定标注 1／分离前一致 4／已分离·非POV 1／不对称 1／计数自证 32=32",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L2 判据 A：删一条机位 → 必须硬失败 ─────────────────────
        tmp2 = fresh()
        d13 = load_sb(tmp2, "D13.json")
        victim = None
        for sc in d13.get("scenes", []):
            if sc.get("ep") == 1 and sc.get("camera_positions"):
                victim = sc["camera_positions"].pop(0)
                break
        save_sb(tmp2, "D13.json", d13)
        rc, out = run_checker(tmp2)
        ok = (rc == 1 and "配对缺失" in out)
        results.append(("L2", f"判据 A 有区分力：删 D13 机位 gsn={victim.get('global_shot_no') if victim else '?'} → exit 1 且含「配对缺失」",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L3 判据 B：白模分离后 D11 仍写严格 POV → 待同步提示 ───
        #    夹具用**真实落盘措辞**（含「视点代表位」），不得简化
        tmp3 = fresh()
        d13 = load_sb(tmp3, "D13.json")
        sc, cp = find_cam(d13, 7, 27)          # D11 U01 ep007/镜3 = gsn 27（g27）
        cp["notes"] = REAL_G27_NOTES
        save_sb(tmp3, "D13.json", d13)
        d11 = load_sb(tmp3, "D11.json")
        pinned = set_d11_note(d11, 7, 3, PRE_LABEL_NOTE)   # 显式钉住「未标注」前提
        save_sb(tmp3, "D11.json", d11)
        rc, out = run_checker(tmp3)
        ok = (pinned and rc == 0 and "[待同步]" in out and "近似 POV（视点代表位）" in out)
        results.append(("L3", "判据 B「待同步」有区分力：D13 g27 改真实落盘措辞（分离 0.35 m ＋ 视点代表位）＋ D11 显式钉住未标注态 → 提示待同步且 exit 0",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L4a 判据 B 收敛：**标注落在 note**（生产实际路径）→ 待同步消失 ─
        tmp4a = fresh()
        d13 = load_sb(tmp4a, "D13.json")
        sc, cp = find_cam(d13, 7, 27)
        cp["notes"] = REAL_G27_NOTES
        save_sb(tmp4a, "D13.json", d13)
        d11 = load_sb(tmp4a, "D11.json")
        hit = set_d11_note(d11, 7, 3, PRE_LABEL_NOTE + LABELED_SUFFIX)
        save_sb(tmp4a, "D11.json", d11)
        rc, out = run_checker(tmp4a)
        ok = (hit and rc == 0 and "[待同步]" not in out and "已按裁定标注（B1）1 处" in out)
        results.append(("L4a", "判据 B 收敛（生产路径）：D11 g27 的 note 追加「近似 POV（视点代表位）」标注 → 待同步消失、转「已按裁定标注」",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L4b 同上，但标注落在 camera_angle → 证明两处命中都算「已按裁定标注」──
        tmp4b = fresh()
        d13 = load_sb(tmp4b, "D13.json")
        sc, cp = find_cam(d13, 7, 27)
        cp["notes"] = REAL_G27_NOTES
        save_sb(tmp4b, "D13.json", d13)
        d11 = load_sb(tmp4b, "D11.json")
        set_d11_note(d11, 7, 3, PRE_LABEL_NOTE)          # note 保持未标注，排除干扰
        hit = set_d11_angle(d11, 7, 3, "近似 POV（视点代表位）")
        save_sb(tmp4b, "D11.json", d11)
        rc, out = run_checker(tmp4b)
        ok = (hit and rc == 0 and "[待同步]" not in out and "已按裁定标注（B1）1 处" in out)
        results.append(("L4b", "判据 B 收敛（另一落点）：D11 g27 的 camera_angle 写「近似 POV（视点代表位）」→ 同样转「已按裁定标注」（两处命中都算已标注）",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L5 真实落盘形态回归：真盘 notes 逐字不改一字 ───────────
        #    证明判据在**真实措辞**上有效，而不是只在简化夹具上有效
        tmp5 = fresh()
        d13 = load_sb(tmp5, "D13.json")
        sc, cp = find_cam(d13, 7, 27)
        real = cp.get("notes") or ""
        cp["notes"] = real               # 原样回填，不做任何改写
        save_sb(tmp5, "D13.json", d13)
        d11 = load_sb(tmp5, "D11.json")
        pinned = set_d11_note(d11, 7, 3, PRE_LABEL_NOTE)   # 显式钉住「未标注」前提
        save_sb(tmp5, "D11.json", d11)
        rc, out = run_checker(tmp5)
        ok = (pinned and rc == 0 and "[待同步]" in out and real == REAL_G27_NOTES)
        results.append(("L5", f"真实落盘形态回归：真盘 g27 notes 逐字灌入 ＋ D11 钉住未标注态（与预期原文一致={real == REAL_G27_NOTES}）→ 仍须报「待同步」",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)

        # ── L6 措辞区分力：同义简化措辞也须报「待同步」 ────────────
        #    反向证明判据读的是「是否已分离」这条语义轴，而不是靠关键词表硬套
        tmp6 = fresh()
        d13 = load_sb(tmp6, "D13.json")
        sc, cp = find_cam(d13, 7, 27)
        cp["notes"] = SIMPLIFIED_G27_NOTES
        save_sb(tmp6, "D13.json", d13)
        d11 = load_sb(tmp6, "D11.json")
        pinned = set_d11_note(d11, 7, 3, PRE_LABEL_NOTE)   # 显式钉住「未标注」前提
        save_sb(tmp6, "D11.json", d11)
        rc, out = run_checker(tmp6)
        ok = (pinned and rc == 0 and "[待同步]" in out and "视点代表位" not in cp["notes"])
        results.append(("L6", "措辞区分力：g27 改同义但无「视点代表位」的简化措辞 ＋ D11 钉住未标注态 → 仍须报「待同步」（判据读语义轴而非关键词）",
                        ok, f"exit={rc}"))
        if not ok:
            print(out)
    finally:
        for d in sandboxes:
            shutil.rmtree(d, ignore_errors=True)

    # ── L7 真盘零写入 ───────────────────────────────────────────
    after = {w: sha(os.path.join(proj, w)) for w in WATCH}
    unchanged = [w for w in WATCH if before[w] == after[w]]
    ok = len(unchanged) == len(WATCH)
    results.append(("L7", f"真盘零写入：{len(WATCH)} 份交付物 SHA256 前后逐字节一致",
                    ok, f"一致 {len(unchanged)}/{len(WATCH)}"))

    passed = sum(1 for r in results if r[2])
    print("\n■ 自测断言明细")
    for leg, desc, ok, ev in results:
        print(f"   {'✅' if ok else '❌'} {leg}：{desc}｜{ev}")
    print(f"\n■ 结果：受检 {len(results)} 条｜通过 {passed}｜不通过 {len(results) - passed}")
    if passed != len(results):
        sys.exit(1)
    print("✅ D11↔D13 机位/视点校验器判据有效性检验全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
