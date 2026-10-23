#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_dispatch_status_0500.py —— 派单状态措辞订准（企划合规 2026-10-23 05:00）

背景
----
本岗 04:45 起草了「合并返修单」三单（声音设计 / 分镜导演 / 视觉设定），
但 **minimax-bot 的派单工具此刻整体不可用**（dispatch_tasks / cancel_tasks / list_team 均返回
「这个 Bot 正在多个聊天里回复，暂时无法确认工具调用属于哪个聊天」）→ **未生成 task_id**。
按**群聊纪律**（需要别人出力时在回复里 @名字 点名）与**章程 §七·九**（明派须在 D18 登记，
未登记视为未明派），**群内 @点名 ＋ D18 登记即构成有效明派**。

故本脚本把台账里「已派单」这类**在事实层面不准确**的措辞改准：
  · 区分「已派单（有 task_id）」与「已明派（群内 @点名，task_id 待补）」；
  · 记录 batch_2fd55abc2d82 三单的真实执行状态（③ 已落盘、① ② 未执行）；
  · 记录合并单取代关系。

用法：python3 scripts/patch_dispatch_status_0500.py --project 02_项目/双相潮主 [--dry-run]
"""
import argparse
import json
import os
import sys

NOW = "2026-10-23 05:00"


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    factory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    proj = args.project if os.path.isabs(args.project) else os.path.join(factory, args.project)
    if not os.path.isdir(proj):
        proj = os.path.join(os.getcwd(), args.project)

    p18 = os.path.join(proj, "shared", "D18.json")
    raw = read(p18)
    d18 = json.loads(raw)

    if d18.get("version") != "v1.44":
        sys.exit(f"[ABORT] D18 version={d18.get('version')}，期望 v1.44；不写盘。")
    oi = {o["id"]: o for o in d18["open_issues"]}
    if "U01-R18" not in oi or "U01-R20" not in oi:
        sys.exit("[ABORT] open_issues 缺 U01-R18 / U01-R20；不写盘。")

    # ---- U01-R18：派单状态改准 ----
    old_status = oi["U01-R18"].get("status", "")
    if "batch_2fd55abc2d82" not in old_status:
        sys.exit("[ABORT] U01-R18.status 不含 batch_2fd55abc2d82；不写盘。")
    oi["U01-R18"]["status"] = (
        "已登记·已派返修单（batch_2fd55abc2d82）·04:45 分流订正·**终表已明派（合并单取代 batch 的① ②）**"
    )
    if "派单通道状态" not in oi["U01-R18"]["resolution"]:
        oi["U01-R18"]["resolution"] = oi["U01-R18"]["resolution"].rstrip() + (
            "　**派单通道状态（2026-10-23 05:00）**：batch_2fd55abc2d82 三单的真实执行情况 —— "
            "③（台本编剧 ep2#4 压缩）**已执行落盘**（D08 v1.9／D09 v1.5）；"
            "①（声音设计 D15 9 条）与②（分镜导演 D16 9 行）**未执行**（磁盘实况：D15 仍 v1.3、9 条 `dur_sec` "
            "0/9 达标；D16 仍 v1.7、ep1 seq6 `out_sec` 仍 12.0）→ 二者**已被 04:45 的合并终表取代**。"
            "**合并单（终表数值）于 05:00 以群内 @点名 明派**（章程 §七·九：明派须在 D18 登记，本条即登记）；"
            "**因 minimax-bot 派单工具此刻整体不可用**（dispatch_tasks／cancel_tasks／list_team 均返回"
            "「这个 Bot 正在多个聊天里回复」），**task_id 暂缺**，工具恢复后由本岗补登记。"
            "**本条不因工具不可用而降级**：明派内容、数值、验收判据均已在本 D18 与台账中固化。"
        )

    # ---- U01-R20：措辞改准 ----
    oi["U01-R20"]["status"] = (
        "已登记·已复核·唯一残留**已明派**（群内 @点名 ＋ 派单工具暂不可用，task_id 待补）"
    )

    # ---- 新增 U01-R21：合并返修单（终表）登记 ----
    if "U01-R21" in oi:
        sys.exit("[ABORT] open_issues 已含 U01-R21，不重复登记；不写盘。")
    d18["open_issues"].append({
        "id": "U01-R21",
        "issue": "**U01-R18 合并返修单（终表数值）明派三岗，因派单工具不可用未生成 task_id** —— "
                 "① 声音设计：D15 9 条 `dur_sec` 上调（8 条取「实测标称+0.1」消贴边、ep8#4 只能贴边）＋ "
                 "口径文本同步 ＋ **重合成 ep2#4 一条**（文案已改为「换我用了。」，盘上音频仍是旧句，"
                 "items.json 必须同步重生成否则比对脚本 unmatched）＋ 复跑只读比对至 **ERR=0**；"
                 "② 分镜导演：D16 9 行 `out_sec` 同步（终表）＋ **ep2 seq9 字幕文字同步**（out_sec 保持 43.0，"
                 "因 D15 的 ep2#4 预算保持 1.8 → 同步口径成立）＋ `sync_rule` 补写区间口径 ＋ "
                 "`subtitle_sync_audit` 按 S11 追加 ＋ D11 ep2 镜4 dialogue 同步；"
                 "③ 视觉设定：D12 ep5 镜3 negatives 的 `no smoke from humans` → `no burning, no smoke`"
                 "（全库仅此 1 处、仅 1 张卡，**不触发 D13/D14 重建**）。"
                 "**三岗文件互不重叠，可并行**（D15／D16+D11／D12）。",
        "owner": "声音设计 ＋ 分镜导演 ＋ 视觉设定（企划合规派活与验收）",
        "blocks": "**拦 U01-R18 的闭环**（10 条破坏项必须清零）；**不拦 U01 单元锁**（U01 已锁且已核验）",
        "priority": "高",
        "status": "已明派（群内 @点名）·派单工具暂不可用·task_id 待补·落盘待收",
        "resolution": "**2026-10-23 05:00 企划合规明派并登记**："
                      "**① 派单通道** —— minimax-bot 派单工具（dispatch_tasks／cancel_tasks／list_team）此刻整体返回"
                      "「这个 Bot 正在多个聊天里回复，暂时无法确认工具调用属于哪个聊天」→ **未生成 task_id**；"
                      "按**群聊纪律**（需要别人出力时在回复里 @名字 点名）与**章程 §七·九**（明派须在 D18 登记，"
                      "未登记视为未明派），**群内 @点名 ＋ 本条登记即构成有效明派**，工具恢复后补登记 task_id。"
                      "**② 终表数值**（取代 batch_2fd55abc2d82 的① ② 两单，后者未执行）：\n"
                      "| 配音条目 | 镜位 | at_sec | 实测标称 | D15 新 `dur_sec` | D16 seq | D16 新 `out_sec` |\n"
                      "|---|---|---|---|---|---|---|\n"
                      "| D09 ep1 #1 | ep1 镜1 | 10.4 | 1.9 | **2.0** | seq6 | **12.4** |\n"
                      "| D09 ep2 #2 | ep2 镜2 | 19.0 | 2.8 | **2.9** | seq6 | **21.9** |\n"
                      "| D09 ep2 #3 | ep2 镜3 | 35.0 | 1.7 | **1.8** | seq7 | **36.8** |\n"
                      "| D09 ep3 #2 | ep3 镜3 | 30.5 | 2.6 | **2.7** | seq8 | **33.2** |\n"
                      "| D09 ep5 #1 | ep5 镜2 | 13.0 | 2.7 | **2.8** | seq5 | **15.8** |\n"
                      "| D09 ep5 #2 | ep5 镜2 | 17.4 | 2.7 | **2.8** | seq6 | **20.2** |\n"
                      "| D09 ep5 #4 | ep5 镜4 | 40.0 | 1.6 | **1.7** | seq8 | **41.7** |\n"
                      "| D09 ep8 #1 | ep8 镜1 | 2.0 | 2.2 | **2.3** | seq5 | **4.3** |\n"
                      "| D09 ep8 #4 | ep8 镜4 | 38.6 | 2.8 | **2.8** | seq8 | **41.4** |\n"
                      "**ep8#4 例外说明**：+0.1 会与下一条面板文字 in 41.4 **重叠 0.1s** → 不可用；"
                      "out 41.4 与其**恰好相接**，按 **Q51** 左闭右开不算重叠，故只能贴边。"
                      "**③ ep2#4 预算保持 1.8**（新句实测约 1.1s，预算仍成立）→ D16 ep2 seq9 `out_sec` 保持 43.0，"
                      "同步口径（out_sec ＝ at_sec + dur_sec）成立，与片尾 43.0 相接不重叠。"
                      "**④ 验收**：三岗各自贴 error 数；声音设计须报比对报告 error/warn/ok 三数与报告路径；"
                      "企划合规在收到三岗回报后复核并核销 U01-R18 与本条。",
        "detected_by": "企划合规 2026-10-23 04:45–05:00（U01-R18 第二波派单与终表数值定稿）",
    })

    d18["version"] = "v1.45"
    body = json.dumps(d18, ensure_ascii=False, indent=2)
    out = body + "\n" if raw.endswith("\n") else body

    if "已明派" not in out or "U01-R21" not in out:
        sys.exit("[ABORT] 序列化后自检失败；不写盘。")

    if args.dry_run:
        print("[DRY-RUN] 未写盘")
        print("[PLAN] D18 v1.44→v1.45（U01-R18 status/派单通道说明 ＋ U01-R20 措辞 ＋ 新增 U01-R21 合并返修单登记）")
        return

    write(p18, out)
    print("[DONE] 派单状态措辞订准完成")
    print(f"   shared/D18.json：v1.44 → {d18['version']}（gc {len(d18['global_checks'])}、oi {len(d18['open_issues'])}）")


if __name__ == "__main__":
    main()
