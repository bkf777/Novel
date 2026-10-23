#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""register_d18_1229.py —— D18 登记（本轮 12:29~12:4x）

登记三条全局口径 ＋ 一波派活：
  Q116  `density_fills_*.json` 降级为「**从 D16 现盘反推的派生物**」——
        真源是 D16 本身；清单由反推脚本再生 ⇒ 清单被重写/覆盖**不再导致产物不可重建**
        （这是对 Q114「次选路径」的进一步收紧：把「清单丢失＝产物不可重建」降级为可恢复）。
  Q117  字幕密度**全线达标实测**（Q100 的验收）—— 16 集超阈 0、最长空窗 2.40s、
        平均空窗总 6.53s（改前 32.01s）。
  Q118  **D16 U01 单写点归属裁定**（回应分镜导演 12:3x 第五节的裁定请求）。

口径（承 D18 Q99「被他人并发升版后的续写口径」与 OPS-10「写盘前复核」）：
  · 以**现盘**为基线叠加本岗新条目，不以旧快照全文写回；
  · 写盘前复核 version／size／sha16／mtime，与读盘时不一致即中止；
  · 版本号由现盘 version 读出后 +1；
  · **D18 的 id 空间是全厂共享的** —— 登记前先读现盘 id 集合取空闲号，
    条目 id 已存在则跳过（幂等），绝不静默丢弃。
用法：python3 scripts/register_d18_1229.py [--dry-run]
"""
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "shared", "D18.json")
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = os.path.join(ROOT, "reports", f"_bak_d18_1229_{STAMP}")

MARK = "【Q116-DENS-DERIVED】"  # 幂等标记：出现在 rule 里即视为已登记

Q116 = {
    "marker": MARK,
    "scope": "scripts/density_fills_U01.json ＋ scripts/density_fills_U02.json（D16 字幕密度链路）",
    "rule": (
        "**`density_fills_*.json` 的地位裁定：它是「从 D16 现盘反推出来的派生物」，不是真源** —— "
        "① **真源＝D16 现盘**（`episodes[].subtitle_style.lines[]`）；"
        "② **清单由反推脚本再生**：`scripts/rebuild_density_fills_U01_mavis.py --unit <U01|U02>` "
        "按「行 text × 该镜 D11 visual_facts 的最长公共连续子串（≥4 字）作 anchor」回填，"
        "改写型行走脚本内人工锚点表，求不出即**如实报告不伪造**；"
        "③ **因此「清单被重写／被覆盖」不再是灾难** —— 锚点可从 D16 × D11 完全重建，"
        "**这把 Q114 次选路径里的「清单丢失＝产物不可重建」降级为「清单丢失＝跑一次反推即恢复」**；"
        "④ **新增字幕行的唯一入口＝先落 D16**（D16 属主写），清单随之反推再生 —— "
        "**禁止**把清单当内容源去争抢写（这正是本轮 D16 U01 四次并发写的根因）。"
    ),
    "detail": (
        "**① 根因（本岗 12:3x 现盘实测）** —— `densify_subtitles.py` 落盘只写 "
        "`text / in_sec / out_sec / shot_id / note`，**不写 anchor**；anchor 只活在清单里 ⇒ "
        "清单一旦被并发重写/覆盖，**盘上字幕行整体与内容源脱钩**（Q114 已立规）。"
        "**② 本岗已做的三件事** —— ① 把 `rebuild_density_fills_U01_mavis.py` 改造为 **支持 `--unit`**，"
        "U01／U02 通用（原先写死 U01）；② **U01 清单从现盘反推重建 8 集/90 条、U02 重建 8 集/111 条**，"
        "锚点全部回填、逐条与 (in_sec,out_sec,shot_id) 对齐（脚本自带写后回读自检，不一致即不写盘）；"
        "③ **densify 复跑双单元均幂等空转**（U01／U02 各条「已存在且一致，跳过」，exit 0，零写盘）"
        "⇒ 清单 ⇄ 盘面重新对齐。"
        "**③ 本岗的一次自曝（诚实登记）** —— 12:29 本岗在并发窗口内**直接覆盖过 "
        "`scripts/density_fills_U02.json`**（该文件原属分镜导演 12:2x 的执行清单），"
        "造成 U02 盘上 111 条字幕行一度失去锚点；**已由上述反推重建完整恢复，交付物零损失**"
        "（真源 D16 v1.9 全程未被本岗改写一个字节）。"
        "**④ 本条与 Q114 的关系** —— Q114 给的是「首选＝锚点入 JSON 结构化字段；次选＝清单备份＋校验」；"
        "本条在**不改工具落盘格式**的前提下把次选路径收紧成「**清单＝可再生派生物**」，"
        "属对 Q114 的补充（**不是冲突**：Q114 的首选路径仍是最优解，本条是现状下的兜底）。"
    ),
    "status": "生效（清单已按现盘反推重建；densify 双单元幂等空转）",
    "source": "Chief 2026-10-23 12:3x 现盘实测 ＋ 反推重建实跑",
}

Q117 = {
    "marker": "【Q117-DENS-ALLDONE】",
    "scope": "U01（ep001-008）＋ U02（ep009-016）共 16 集",
    "rule": (
        "**字幕密度下限（Q100）全线达标实测 —— 16 集「超阈 0 集」** —— "
        "① 口径＝`scripts/audit_dead_time.py`（镜内无字幕空窗，角标不计入；阈值 4.0s/6.0s）；"
        "② **改前**：16/16 集超阈，**全集最长空窗 14.00s**、**平均空窗总 32.01s**"
        "（45 秒里约 71% 的时间屏幕没有任何字幕/读数）；"
        "③ **改后**：**超阈 0 集**、**全集最长空窗 2.40s**、**平均空窗总 6.53s**"
        "（**降幅 80%**；U01 30.81→7.19s、U02 33.20→5.91s）；"
        "④ 典型集：EP003 10.0→1.0s、EP004 12.0→1.7s、EP007 12.0→1.6s、EP013 11.3→2.1s、"
        "EP015 13.0→1.0s、EP016 12.0→0.9s。"
    ),
    "detail": (
        "**① 做法＝「画面里的字」，不是加台词** —— 全程**对白行一条未加**（D09 语气卡对陆沉写死"
        "「每集不超过 4 句」，寡言是角色设计）；新增的全部是字幕板／面板读数／场景标识，"
        "**内容全部取自该镜 D11 `visual_facts` 已写明的事实**，锚点逐字校验、不新增画面、不编数字。"
        "**② 不动的** —— 镜数、镜时、D14 白模与逐镜交接包、D08 正文与字数档、D09 台词与潜台词、"
        "D12 提示词、D15 混音曲线 ⇒ **V11 不受影响，不重跑 Blender**。"
        "**③ 黄金 3 秒同步达标** —— 16 集 `golden3s_first_line.status` 实测**全部＝「达标」**，"
        "首句 `d15_vo_at_sec` ＝ 0.4~0.5s（ep003／ep005／ep006／ep012／ep016 五集说话人不在镜1，"
        "按 ep003 先例做**画外音**并写明 `delivery`）。"
        "**④ 预演片已同步重建** —— `preview/U01_storyboard/EP001..008.mp4` ＋ "
        "`preview/U02_storyboard/EP009..016.mp4`（各 45.0s），每集字幕行 14~21 条"
        "（改前 10~14 条）；并修掉一处**边界帧重影**——ffmpeg 的 `between(t,a,b)` 是**双端闭区间**，"
        "在「上一行 out_sec＝下一行 in_sec」的边界帧上两行同时渲染 ⇒ 抽帧审计会撞上假象；"
        "已改为 **`gte(t,t0)*lt(t,t1)` 左闭右开**，与 D16 的区间判定口径一致。"
        "**⑤ 复现命令** —— `python3 scripts/audit_dead_time.py --md 00_给你看的/体检_短剧垃圾时间_16集.md`"
    ),
    "status": "生效（16 集超阈 0；Q100 由「样板」推进到「全线达标」）",
    "source": "Chief 2026-10-23 12:3x ＋ 分镜导演 12:3x 双线实测互证",
}

Q118 = {
    "marker": "【Q118-D16-SINGLEWRITER】",
    "scope": "units/U01/D16.json（及 D11/D16 同类集内结构交付物）",
    "rule": (
        "**D16 U01 单写点归属裁定：分镜导演 bot_1855d6ce9cdd（D11/D16 属主）** —— "
        "① **唯一写者＝分镜导演**（依《团队章程》§三·五 与 docfactory.owners 的交付物→Bot 映射）；"
        "② **Chief 本岗不再直写 D16**（此前数轮以「补位」名义并发写 D16，"
        "造成 v1.23→v1.28 的四轮并发，本条据此收回该口子）；"
        "③ **并发实例一律「只读 ＋ 告警」** —— 需要改 D16 时：出**预警件**（含现盘 version/size/sha16/mtime "
        "＋ 逐条差异）交属主改，**不得直接落盘**；"
        "④ **写前并发守卫（version/size/sha16/mtime 复核）保持为所有 D16 写入工具的强制项**，"
        "不一致即中止、不得覆盖对方字节。"
    ),
    "detail": (
        "**① 事实** —— 本轮 D16 U01 发生 **4 次并发写**（v1.23→v1.28）：并发实例三轮（12:13／12:20／12:31）"
        "＋ 分镜导演三轮（12:24／12:26／12:30），每次都走了守卫、**未覆盖对方字节**；"
        "但「两方都在写同一个单写点」本身是**流程缺陷**，不是靠守卫能长期兜住的。"
        "**② 分镜导演的裁定请求（12:3x 回执第五节）已在本条答复** —— 后续一轮由**分镜导演收口**；"
        "本岗在 D16 上的动作止于「只读核对 ＋ 告警」。"
        "**③ 与 Q114／Q115／Q116 的关系** —— Q114 治「锚点丢失」、Q115 治「审计块行号错位」、"
        "Q116 治「清单被当内容源争抢写」，本条治「两个写者同时落盘」⇒ **四条同源："
        "都是『同一个真源被多方写』在不同层面的表现**，建议后续按「一个真源一个写者」"
        "统一治理，不再逐条打补丁。"
    ),
    "status": "生效（裁定已下；后续 D16 U01 一轮由分镜导演收口）",
    "source": "分镜导演 2026-10-23 12:3x 回执第五节（请求裁定）＋ Chief 同日裁定",
}

NEW_GLOBALS = [Q116, Q117, Q118]

# ── 派活波次 ────────────────────────────────────────────────────────────────
WAVE = {
    "wave": "R-027",
    "at": "2026-10-23 12:4x",
    "items": [
        {
            "id": "R-027a",
            "to": "台本编剧 bot_d90c96b11c8e",
            "scope": ("D08 U01 `word_count` **反复被清零** —— 12:23 重建至 v1.13 时漏填、12:31 与 12:32:48 "
                      "两次重建再次清零（现盘 base/total 全 0）⇒ validate V9 18 条 error"
                      "（ep1 实际 312 字、ep2 279 字等）。**要求：改 `scripts/build_D08_U01.py` 生成源后重跑落盘，"
                      "勿手改 D08.json**；落盘前自检 `word_count` 与正文实际字数一致。"
                      "另：**ep1 正文 312 字 > D08 上限 240** 需在正文层解决（压缩或走合规增量档），"
                      "不要靠改 word_count 声明值绕过。"),
            "request_id": "sxcz-d08-wordcount-027a",
            "state": "已派（待回执）",
        },
        {
            "id": "R-027b",
            "to": "声音设计 bot_0a60d9bbd4fe",
            "scope": ("**U03 D15 缺件** —— `03_规格/rules.json` 的 `unit_required_deliverables` 含 D15 且 "
                      "`missing_is_error=true`（Q109）⇒ U03 validate V1 报 3 条缺件 error（D13/D14/D15）。"
                      "请产出 `units/U03/D15.json`（ep017-024 的配音/混音曲线），"
                      "与 U01/U02 的 D15 字段口径一致（voice_over 带 line_ref/at_sec/dur_sec）。"),
            "request_id": "sxcz-u03-d15-027b",
            "state": "已派（待回执）",
        },
        {
            "id": "R-027c",
            "to": "白模场景师 bot_e3df82ceee20",
            "scope": ("**U03 D13/D14 缺件**（承接 R-026c「U03 D13/D14 开工」）—— U03 validate V1 报缺件 error。"
                      "同时提醒：U01 V12 白模构图 **27 条 error 仍未收口**（白模未按 D11 新景别重建 ＋ W3 判据缺陷），"
                      "U02 另有 32 条；请一并给进度与收口时点。"),
            "request_id": "sxcz-u03-d13d14-027c",
            "state": "已派（待回执）",
        },
        {
            "id": "R-027d",
            "to": "分镜导演 bot_1855d6ce9cdd",
            "scope": ("① **D16 U01 单写点裁定已下（Q118）：后续一轮由你收口**，本岗不再直写 D16；"
                      "② **Q114/Q115 已由企划合规立规**：锚点落盘（首选结构化字段入 JSON）＋ "
                      "审计块 `rows[].seq` 同轮刷新（`scripts/refresh_D16_U01_audit_mavis.py`）"
                      "⇒ 请在每次插行后同轮跑刷新；"
                      "③ **Q116 已立规**：`density_fills_*.json` 降级为「从 D16 现盘反推的派生物」，"
                      "**新增字幕行请直接落 D16**，清单由 `rebuild_density_fills_U01_mavis.py --unit <U>` 反推再生，"
                      "**不要再把清单当内容源与本岗争抢写**；"
                      "④ **黄金 3 秒 16 集已全线达标**（首句 0.4~0.5s），你回执中的「剩 5 集」已过期。"),
            "request_id": "sxcz-d16-singlewriter-027d",
            "state": "已派（待回执）",
        },
    ],
}


def fingerprint(p):
    b = open(p, "rb").read()
    o = json.loads(b.decode("utf-8"))
    return {
        "version": o.get("version"),
        "size": len(b),
        "sha16": hashlib.sha256(b).hexdigest()[:16],
        "mtime": os.path.getmtime(p),
    }


def bump(o):
    import re
    v = re.sub(r"^v+", "v", str(o.get("version", "v1.0")))
    o["version"] = f"{v.split('.')[0]}.{int(v.split('.')[1]) + 1}"


def main():
    fp0 = fingerprint(P)
    d = json.load(open(P, encoding="utf-8"))
    print(f"   基线：D18 v{fp0['version']} sha16={fp0['sha16']} "
          f"size={fp0['size']} mtime={fp0['mtime']}")

    # ── ① 幂等：标记已在则跳过 ────────────────────────────────────────────
    existing_marks = set()
    for c in d.get("global_checks", []):
        for v in c.values():
            if isinstance(v, str) and "【Q1" in v:
                for m in ("【Q116-DENS-DERIVED】", "【Q117-DENS-ALLDONE】", "【Q118-D16-SINGLEWRITER】"):
                    if m in v:
                        existing_marks.add(m)
    existing_qids = {c.get("id") for c in d.get("global_checks", [])}
    used_nums = [int(q[1:]) for q in existing_qids if isinstance(q, str) and q.startswith("Q") and q[1:].isdigit()]
    nxt = max(used_nums or [0]) + 1

    added, skipped = [], []
    for spec in NEW_GLOBALS:
        if spec["marker"] in existing_marks:
            skipped.append(spec["marker"])
            continue
        while f"Q{nxt}" in existing_qids:
            nxt += 1
        qid = f"Q{nxt}"
        nxt += 1
        existing_qids.add(qid)
        entry = {
            "id": qid,
            "rule": spec["rule"],
            "detail": spec["detail"],
            "status": spec["status"],
            "scope": spec["scope"],
            "source": spec["source"],
        }
        d.setdefault("global_checks", []).append(entry)
        added.append(f"{qid}（{spec['marker']}）")
        print(f"   ➕ 登记 {qid}  {spec['marker']}")
    for m in skipped:
        print(f"   ⏭  已存在，跳过 {m}")

    # ── ② 派活波次（幂等：wave+id 已存在则跳过） ──────────────────────────
    u1 = next((u for u in d.get("unit_checks", []) if u.get("unit") == "U01"), None)
    if u1 is None:
        print("❌ D18.unit_checks 里找不到 U01，中止")
        return 2
    ledger = u1.setdefault("dispatch_ledger", [])
    have = {(w.get("wave"), i.get("id")) for w in ledger for i in w.get("items", [])}
    wave_existed = any(w.get("wave") == WAVE["wave"] for w in ledger)
    if wave_existed:
        print(f"   ⏭  波次 {WAVE['wave']} 已存在，不重复追加")
    else:
        ledger.append({"wave": WAVE["wave"], "at": WAVE["at"], "items": WAVE["items"]})
        for i in WAVE["items"]:
            print(f"   ➕ 派活 {i['id']} → {i['to']}")

    if not added and not wave_existed:
        print("✅ 无新增，不写盘")
        return 0

    if DRY:
        print("（--dry-run：未写盘）")
        return 0

    # ── ③ 写前并发复核 ────────────────────────────────────────────────────
    now = fingerprint(P)
    if now != fp0:
        print(f"❌ 并发守卫：D18.json 在读盘后被改动（读盘时 {fp0} → 现在 {now}）"
              f" ⇒ 放弃本次写盘，请重新核对基线后再跑。")
        return 2

    os.makedirs(BAK, exist_ok=True)
    shutil.copy2(P, os.path.join(BAK, "D18.json"))
    bump(d)
    with open(P, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

    back = json.load(open(P, encoding="utf-8"))
    ids = [c.get("id") for c in back["global_checks"]]
    dup = len(ids) != len(set(ids))
    print(f"✅ 已写 D18（v{back.get('version')}）｜全局条目 {len(ids)} 条"
          f"{'｜⚠ 有重复 id' if dup else '｜id 无重复'}"
          f"｜新增 {len(added)} 条｜备份 {os.path.relpath(BAK, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
