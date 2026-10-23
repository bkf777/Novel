# -*- coding: utf-8 -*-
"""把 2026-10-23 13:27 这一轮的 D18 登记内容注入 register_d18_v135_ep002_regression.py。

内容：
  ① Q131（global_check）—— 派单受理 ≠ 落地；核销必须以「条目级 diff ＋ sha256」为准
  ② R62/R63（open_issue）—— D15 U01 8 条 dur 仍是旧稿字数 / D16 ep001 4 条对白行截短
  ③ STATUS_PATCHES —— 订正 U01-R56 / U01-R61 / U01-R53 的状态与留痕
  ④ WAVE2 —— R-028x 波次台账（5 单重投，batch_da355fda6573）

⛔ 本补丁只改注册脚本，不碰 D18.json（写盘由注册脚本负责，且注册脚本自带并发守卫与备份）。
⛔ 注入的中文字符串内一律用「」，⛔ 不得用 ASCII 双引号。
"""
import ast
import io
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "register_d18_v135_ep002_regression.py")

BLOCK = '''
# ═══════════════════════════════════════════════════════════════════════
# 2026-10-23 13:27 总控轮追加（Q131 / R62 / R63 / 状态订正 / R-028x 波次）
# ═══════════════════════════════════════════════════════════════════════
M_Q131 = "【Q131-DISPATCH-NOT-DELIVERED】"

Q131_SPEC = {
    "marker": M_Q131,
    "match": "派单受理（入队/回执）不等于该单已落地",
    "rule": (
        "**派单被受理 ≠ 该单已落地 —— 核销一个派单必须三条同时成立** —— "
        "① **条目级 diff** 显示派单要求的改动确实出现在目标交付物里（⛔ 仅看文件 mtime 变了不算）；"
        "② **sha256 与派单时的基线不同**（⛔ **字节数相同不构成变化证据**）；"
        "③ 属主回执与磁盘实况**逐条互证**（回执里声称改了的，逐条在磁盘上找得到）。"
        "三条缺一 ⇒ 只能写「**已派未落地**」，⛔ 不得写「已完成／已回执／已解决」；"
        "⛔ 派单通道返回 batch_id／task_id／回执，**只说明入队**，不是完成信号。"
    ),
    "detail": (
        "**① 事实（总控 13:18–13:28 独立实测，逐条 sha256 ＋ 条目级 diff）** —— "
        "上一波 R-028 的五单**全部「已受理但未落地」**："
        "**R-028a**（声音设计 D15 8 条 dur）：D15 U01 13:17 被重写，但 **sha256 与 13:13 备份完全相同**"
        "（0233b28c7096f2ad）⇒ 零变化；而 13:13 那次真实变化（v1.13→v1.14，+16,258 B）"
        "经条目级 diff 证明内容是**声音设计的另一件活**（ep8 sfx 重复登记合并 ＋ mix_notes 增补），"
        "**与本单的 8 条 dur 重算无关**；"
        "**R-028b**（分镜导演 D16 ep001 字幕行）：D16 U01 自 12:54 起 sha16 9bd51c623304dbe9 未变；"
        "**R-028g**（分镜导演 D11 dialogue）：D11 U01 自 12:39 起 sha 未变；"
        "**R-028h**（企划合规 V13）：`03_规格/rules.json` 中 **V13 计数＝0**、"
        "`03_规格/schema.json` 中 **vo_type／speaker_in_frame 均不存在** ⇒ V13 未落地；"
        "**R-028e**（白模 V12 ＋ U03 D14）：**部分落地**（V12 由 U01 25／U02 29 条降到 U01 7／U02 6 条，"
        "D14 U01/U02 于 13:21 被重写且 40 秒二次采样稳定），但 **U03 D14 仍缺件**。"
        "**② 三条教训** —— "
        "① **「这个文件被写过」不等于「本单被写过」** —— 必须做条目级 diff 才能把「别的活」与「本单的活」分开；"
        "② **同尺寸不同内容是常态** —— 13:17 与 13:13 两版 D15 字节数**完全相同**（231,555 B）而内容零差，"
        "**Q129 的「尺寸相同 ⇒ 零变化」假阴性在本轮再次命中**；"
        "③ **派单通道返回成功只说明入队** —— 真正完成的信号只有一个：**磁盘上出现了预期的条目级变化**。"
        "**③ 处置** —— 总控于 13:27 以**新 request_id** 重投五单（batch_da355fda6573），"
        "并把五单的真实状态在台账与 open_issues 中登记为「**已派未落地（首派未落地·已重投）**」。"
    ),
    "status": "生效（核销三件套：条目级 diff ＋ sha256 变化 ＋ 回执互证；缺一即写「已派未落地」）",
    "scope": "全部派活的核销与登记口径",
    "source": "总控/验收裁决人 2026-10-23 13:18–13:28 逐条 sha256 ＋ 条目级 diff 实测",
}

NEW_GLOBALS.append(Q131_SPEC)

R62 = {
    "id": "U01-R62",
    "marker": "【U01-R62-D15-DUR-STALE】",
    "match": "D15 U01 ep001+ep002 8 条 dur_sec 仍是旧稿字数对应的值",
    "issue": (
        "**D15 U01 ep001＋ep002 共 8 条 `voice_over.dur_sec` 仍按旧稿台词的字数设定，"
        "与台词真源 D09 v1.9 现盘脱节** —— 本岗 13:18–13:22 逐条实测，"
        "其中 **5 条（ep1 #2／#3、ep2 #1／#2／#3）会导致字幕被切断或留白**"
        "（字幕 `out_sec` ＝ 配音 `at_sec`＋`dur_sec`）。"
    ),
    "owner": "声音设计 bot_0a60d9bbd4fe（D15 U01 属主）",
    "blocks": "不拦 U01 既有锁；但**拦「U01 字幕与配音已对齐」的结论**；"
              "U03 起不得重犯（改稿后必须重定配音并回灌时码）",
    "priority": "中",
    "status": "已派未落地（首派 R-028a r3 未落地；13:27 重投 R-028a-r2，request_id r028x-batch-20261023-1328，task_c05411dfb523）",
    "detected_by": "总控（验收裁决人）13:18–13:22 独立实测 —— 逐条 dur ↔ D09 台词字数 ↔ D15 mix_notes 旧稿文本 三向互证",
    "note": (
        "**① 8 条逐条对照（本岗实测）** —— "
        "ep1 #1「上一趟我死在第三小时。」11 字，现 dur **3.5**（实为旧 21 字稿而设）；"
        "ep1 #2「两小时五十八分。账我来算。」13 字，现 dur **2.0**（实为旧 8 字稿，实测1.873→标称1.9→+0.1）；"
        "ep1 #3「东西不带。先要命。」9 字，现 dur **1.3**（旧 13 字稿）；"
        "ep1 #4「城西机械厂。」6 字，现 dur **1.3**（贴边余量 1.2→1.3）；"
        "ep2 #1「门撬开了。这一世，我当关门人。」15 字，现 dur **1.3**（旧 5 字稿）；"
        "ep2 #2「前门焊死。叶家和灰潮，谁都别想进来。」18 字，现 dur **2.9**（旧 11 字稿，实测2.771→2.8→+0.1）；"
        "ep2 #3「处置深坑在后面，退路我占。」13 字，现 dur **1.8**（旧 7 字稿，实测1.601→1.7→+0.1）；"
        "ep2 #4「换我用了。」5 字，现 dur **1.8**（本就不属变更，维持）。"
        "**② 根因** —— 配音时长是按**旧稿台词字数**算的；台词改稿只改了 D09／D08，**D15 侧未重定**。"
        "**③ 失配的三重证据（互相独立）** —— ① D15 的 `mix_notes` 里仍写着旧稿台词"
        "（「两小时五十八分。」「侧门焊死，谁都进不来。」「这条路先记下。」「门我撬了。」）；"
        "② **TTS 产物同源未更新**（`preview/U01_tts/items.json` 仍是旧文本，如「上一趟我死在第三个小时。」）；"
        "③ 13:17 那次重写与 13:13 备份 **sha256 完全相同** ⇒ 零变化（Q131）。"
        "**④ 处置口径** —— 先重定配音（D15），再回灌时长（D16）；"
        "⛔ **不得为迁就旧 D15 时长而截短台词**（Q124）；⛔ 不得改台词文本（台词属主在剧本层）；"
        "⛔ **不得改 D16**（out_sec 回灌是分镜导演的活，单写点纪律）；"
        "⛔ 若 TTS 服务不可用，按「字数→时长」**预算口径**重算并**明确标注「预算值·非实测」**，"
        "⛔ 不得把预算值写成实测值。"
    ),
}

R63 = {
    "id": "U01-R63",
    "marker": "【U01-R63-D16-EP001-DIALOGUE-CLIPPED】",
    "match": "D16 U01 ep001 4 条对白字幕行文字截短 ＋ golden3s_first_line.text 滞后",
    "issue": (
        "**D16 U01 ep001 的 4 条「对白」字幕行文字与台词真源 D09 v1.9 不逐字相等"
        "（3 条缺字、1 条缺前缀），另 `subtitle_style.golden3s_first_line.text` 亦滞后** —— "
        "本岗 13:20–13:25 现盘逐行复核坐实；这是 U01-R56 在现盘的**同源复现**（首派未落地）。"
    ),
    "owner": "分镜导演 bot_1855d6ce9cdd（D16 U01 属主）",
    "blocks": "不拦 U01 既有锁；但**拦「U01 字幕与剧本已对齐」的结论**；"
              "黄金 3 秒首句闸位的 `text` 与真源不符 ⇒ 该闸位结论不可引用",
    "priority": "中",
    "status": "已派未落地（首派 R-028b r3 未落地；13:27 重投 R-028b-r2，request_id r028x-batch-20261023-1328，task_3790665468ba）",
    "detected_by": "总控（验收裁决人）13:20–13:25 独立实测 —— 逐行取 D16 subtitle_style.lines 与 D09 lines 对照",
    "note": (
        "**① 4 条逐行对照（现盘 → 应为）** —— "
        "seq 2「上一趟我死在第三个小时。」→「上一趟我死在第三小时。」（0.5→4.0，shot 1）；"
        "seq 4「两小时五十八分。」→「两小时五十八分。账我来算。」（6.0→8.0，shot 1）；"
        "seq 14「东西不带。」→「东西不带。先要命。」（31.4→32.7，shot 3）；"
        "seq 17「机械厂。」→「城西机械厂。」（39.2→40.5，shot 4）；"
        "`golden3s_first_line.text`「上一趟……我被叶家推入深坑，死在第三个小时。」→「上一趟我死在第三小时。」。"
        "**② 本轮范围收紧（重要）** —— 本单**只改这 4 条 text 字面 ＋ golden3s_first_line.text**，"
        "⛔ **不动任何 `in_sec`／`out_sec`／`at_sec`／`d15_vo_dur_sec`**："
        "Q124 的顺序是「**先重定配音、后回灌时长**」，而 D15 新 dur 尚未就绪（见 U01-R62），"
        "此时回灌时码等于臆造；**时长回灌是收到 D15 新 dur 后的独立一单**。"
        "**③ seq 10 的裁定（Q125 默认回退正文 ⇒ D16 不动）** —— "
        "ep001 seq 10「比上一趟少 6 分钟」（面板文字，21.4–24.0）曾被判为孤儿字幕"
        "（D08 删了该条而 D16 仍渲染）；总控裁定＝**默认回退正文**，"
        "由台本编剧恢复 D08 ep001 的「面板底部红字：比上一趟少 6 分钟。」"
        "⇒ **D16 本行保持原值，不属本单范围**。"
        "**④ 与 U01-R56 的关系** —— 同源同批（U01-R56 是首轮上报，本条是现盘复现与范围收紧），"
        "⛔ 两者不得被当作两个独立缺陷重复派工。"
    ),
}

STATUS_PATCHES = [
    {
        "id": "U01-R56",
        "marker": "【U01-R56-20261023-1327-RECHECK】",
        "status": "已派未落地（首派通道受阻未投递；13:27 以 R-028b-r2 重投，task_3790665468ba；现盘复现见 U01-R63）",
        "note_append": (
            " ｜ **【2026-10-23 13:27 总控复检 · 追加式，原结论保留】** —— "
            "本条首派因通道受阻（BUSY ×2 ＋ 群讨论占用）未投递；13:27 总控独立复核**现盘仍未回正**"
            "（D16 U01 sha16 9bd51c623304dbe9 自 12:54 未变），"
            "**现盘逐行实测的 4 条明细与范围收紧已单独登记为 U01-R63**；"
            "⛔ 本条与 U01-R63 是**同源同批**，不得被当作两个独立缺陷重复派工。"
        ),
    },
    {
        "id": "U01-R61",
        "marker": "【U01-R61-20261023-1327-NOT-LANDED】",
        "status": "已明派·已重投待落地回执（首派 q108-v13-mingpai-20261023-1313 未落地；13:27 重投 R-028h-r2，task_725bb12085db）",
        "note_append": (
            " ｜ **【2026-10-23 13:27 总控独立核对 · 追加式】** —— "
            "**V13 确认尚未落地**：`03_规格/rules.json` 中 V13 计数＝0；"
            "`03_规格/schema.json` 中 `vo_type` 与 `speaker_in_frame` **均不存在**；"
            "⇒ 首派未落地。13:27 已以**新 request_id** 重投（R-028h-r2 / task_725bb12085db），"
            "执行约束不变（⛔ 不改 V1–V12 语义、⛔ U01 先试跑、⛔ V13-c 反证腿必交、"
            "⛔ schema `additionalProperties:false` 前置影响评估必做）。"
            "**本条为总控明派；若 Chief 认为应由他先拍板，可即时撤销**（落地清单已固化在 U03-R52）。"
        ),
    },
    {
        "id": "U01-R53",
        "marker": "【U01-R53-20261023-1327-D15-HALF-SYNC】",
        "status": "已登记·已派单待回执（其中「D15/D16 下游半同步失配」一项已独立登记为 U01-R62，本条聚焦字数越档）",
        "note_append": (
            " ｜ **【2026-10-23 13:27 总控拆条 · 追加式，原条保留】** —— "
            "本条原 note 里的「D15／D16 下游半同步失配」经 13:18–13:22 独立实测"
            "**已可独立成条**（D15 8 条 dur 逐条对照表 ＋ mix_notes 旧稿文本 ＋ TTS 未更新 三重证据），"
            "⇒ **已拆出为 U01-R62**（属主＝声音设计）**与 U01-R63**（属主＝分镜导演）；"
            "本条聚焦 **D08 字数越档**本身。⛔ 拆条不改变本条的任何结论。"
        ),
    },
]

WAVE2 = {
    "wave": "R-028x",
    "at": "2026-10-23 13:27",
    "items": [
        {
            "id": "R-028e-r2",
            "to": "白模场景师 bot_e3df82ceee20",
            "scope": (
                "**白模 V12 剩余 13 条归零（U01 7 条 ＋ U02 6 条）＋ U03 D14 补件（32 镜）** —— "
                "首派 R-028e 部分落地（V12 由 U01 25／U02 29 降到 7／6，D14 U01/U02 于 13:21 重写），"
                "但 **U03 D14 仍缺件**、13 条仍未归零。"
                "唯一修复方向：**D14 投影取景对齐 D11 景别**（⛔ 不得反向改 D11）；"
                "⛔ 逐帧必须用该帧自己的旋转矩阵算占幅、⛔ 不得直接填数伪造投影、"
                "⛔ 不得改／放宽 `03_规格/rules.json` 的 `white_model_framing`；"
                "⛔ 只写 D14。回执须贴三单元 validate 结果行 ＋ 13 条逐条复算占幅 ＋ U03 的 sha256 与 32 镜覆盖证明。"
            ),
            "request_id": "r028x-batch-20261023-1328",
            "task_id": "task_4316155b7227",
            "state": "已派·待回执（batch_da355fda6573，13:27 queued）",
        },
        {
            "id": "R-028a-r2",
            "to": "声音设计 bot_0a60d9bbd4fe",
            "scope": (
                "**D15 U01 ep001＋ep002 8 条 `dur_sec` 按新台词重算 ＋ TTS 同批重出** —— "
                "首派 R-028a 未落地（13:17 那次重写与 13:13 备份 **sha256 完全相同** ⇒ 零变化）。"
                "派单附 8 条逐行「现盘 dur ↔ 新台词字数 ↔ 旧稿字数」对照表 ＋ 失配三重证据；"
                "⛔ 不得为迁就旧时长截短台词（Q124）、⛔ 不得改台词文本、⛔ 不得改 D16；"
                "⛔ 若 TTS 不可用须按预算口径重算并标注「预算值·非实测」。"
            ),
            "request_id": "r028x-batch-20261023-1328",
            "task_id": "task_c05411dfb523",
            "state": "已派·待回执（batch_da355fda6573，13:27 queued）",
        },
        {
            "id": "R-028g-r2",
            "to": "分镜导演 bot_1855d6ce9cdd",
            "scope": (
                "**D11 U01 `dialogue` 5 字段 7 句逐字回正** —— 首派 R-028g 未落地"
                "（D11 U01 自 12:39 起 sha 未变）。派单附 5 字段 7 句旧→新对照 ＋ "
                "**关键澄清：叶承钧是 D04 注册角色、在 ep005/ep006 合法活跃，⛔ 不得抹掉，只有 ep001 shot1 那句是残留**；"
                "⛔ 只改 `dialogue` 字面、⛔ 不得改景别与镜时码（⇒ 对 V12 零影响）、⛔ 不得截短台词。"
            ),
            "request_id": "r028x-batch-20261023-1328",
            "task_id": "task_ea2d16ae3a58",
            "state": "已派·待回执（batch_da355fda6573，13:27 queued）",
        },
        {
            "id": "R-028b-r2",
            "to": "分镜导演 bot_1855d6ce9cdd",
            "scope": (
                "**D16 U01 ep001 4 条对白字幕行文字回正 ＋ `golden3s_first_line.text` 同步** —— "
                "首派 R-028b 未落地（D16 U01 自 12:54 起 sha 未变）。"
                "**本单范围收紧：⛔ 不动任何 `in_sec`／`out_sec`／`at_sec`／`d15_vo_dur_sec`** —— "
                "Q124 顺序＝先重定配音、后回灌时长，D15 新 dur 未就绪时回灌等于臆造；"
                "⛔ 不得删改既有「台词改稿待重定时」审计留痕；⛔ seq 10 按 Q125 裁定保持原值。"
            ),
            "request_id": "r028x-batch-20261023-1328",
            "task_id": "task_3790665468ba",
            "state": "已派·待回执（batch_da355fda6573，13:27 queued）",
        },
        {
            "id": "R-028h-r2",
            "to": "企划合规 bot_19406286feaf",
            "scope": (
                "**V13 / Q108 总控明派落地执行（U01 先试跑）** —— 首派未落地"
                "（`03_规格/rules.json` V13 计数＝0；`03_规格/schema.json` 无 `vo_type`／`speaker_in_frame`）。"
                "落地清单＝① rules.json 增 V13 三判定（含反证腿 V13-c）② schema.json 增 vo_type／speaker_in_frame "
                "③ 字段规格表 §四 增 V13／V14 行 ④ D15／D16 新字段行；"
                "⛔ 不得改 V1–V12 语义、⛔ U01 先试跑、⛔ V13-c 反证腿必交（实跑拒绝路径 ＋ 断言磁盘零变化）、"
                "⛔ schema `additionalProperties:false` 前置影响评估必做；"
                "同单送达 Q127／Q128 两项总控裁定。"
            ),
            "request_id": "r028x-batch-20261023-1328",
            "task_id": "task_725bb12085db",
            "state": "已派·待回执（batch_da355fda6573，13:27 queued）",
        },
    ],
}
'''


def main():
    with io.open(P, "r", encoding="utf-8") as f:
        s = f.read()

    # ① 注入块（插在 def find_oissue 之前）
    anchor = "def find_oissue(d, oid):"
    assert s.count(anchor) == 1, "find_oissue 锚点异常"
    s = s.replace(anchor, BLOCK.strip() + "\n\n\n" + anchor)

    # ② open_issues 注册元组扩项（R62/R63）
    old = "for spec in (R53, R54, R55, R56, R57, R58, R59, R60, R61):"
    new = "for spec in (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63):"
    assert s.count(old) == 1, "open_issues 注册元组锚点异常"
    s = s.replace(old, new)

    old2 = ('n_bf += backfill_markers(d, (R53, R54, R55, R56, R57, R58, R59, R60, R61), '
            '"open_issues", "note")')
    new2 = ('n_bf += backfill_markers(d, (R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63), '
            '"open_issues", "note")')
    assert s.count(old2) == 1, "backfill_markers 锚点异常"
    s = s.replace(old2, new2)

    # ③ 状态订正块（插在台账波次写入之前）
    anchor3 = "    # ── ④ 派活波次（幂等：wave 已存在则跳过） ──────────────────────────────"
    assert s.count(anchor3) == 1, "派活波次锚点异常"
    patch_block = '''    # ── ③′ 既有 open_issue 状态订正（追加式，原文保留；幂等：marker 已存在则跳过） ──
    for sp in STATUS_PATCHES:
        ent = next((o for o in d.get("open_issues", []) if o.get("id") == sp["id"]), None)
        if ent is None:
            print(f"   ⏭  {sp['id']} 不存在，跳过状态订正")
            continue
        if sp["marker"] in (ent.get("note") or "") + (ent.get("status") or ""):
            skipped.append(sp["marker"])
            print(f"   ⏭  {sp['marker']} 已在产物条目内，跳过")
            continue
        ent["note"] = (ent.get("note") or "") + sp["note_append"]
        ent["status"] = sp["status"]
        added.append(f"{sp['id']}.status")
        print(f"   ✏️  状态订正 {sp['id']} ＋ 追加留痕")

'''
    s = s.replace(anchor3, patch_block + anchor3)

    # ④ 第二波次台账写入（插在第一波次块之后）
    anchor4 = ("    # ── ⑤ U01 D08 指针归位 ＋ 验收线更正（追加式，原文保留） "
               "────────────────")
    assert s.count(anchor4) == 1, "⑤ 锚点异常"
    wave2_block = '''    # ── ④′ 第二派活波次 R-028x（幂等：wave 已存在则按 item id 增量 upsert） ──
    w2_existed = any(w.get("wave") == WAVE2["wave"] for w in ledger)
    if w2_existed:
        w2 = next(x for x in ledger if x.get("wave") == WAVE2["wave"])
        have2 = {i.get("id") for i in w2.get("items", [])}
        for spec in WAVE2["items"]:
            cur = next((i for i in w2.get("items", []) if i.get("id") == spec["id"]), None)
            if cur is None:
                w2.setdefault("items", []).append(spec)
                added.append(f"{WAVE2['wave']}.{spec['id']}")
                print(f"   ➕ 台账补录 {WAVE2['wave']}.{spec['id']} → {spec['to']}")
                continue
            for k in ("note", "state", "scope", "request_id", "task_id"):
                if k in spec and cur.get(k) != spec[k]:
                    cur[k] = spec[k]
                    added.append(f"{WAVE2['wave']}.{spec['id']}.{k}")
                    print(f"   ✏️ 台账更新 {WAVE2['wave']}.{spec['id']}.{k}")
        skipped.append(f"wave {WAVE2['wave']}")
        print(f"   ⏭  波次 {WAVE2['wave']} 已存在 ⇒ 走增量 upsert（不整波覆盖）")
    else:
        ledger.append(WAVE2)
        for i in WAVE2["items"]:
            print(f"   ➕ 派活 {WAVE2['wave']}.{i['id']} → {i['to']}")

'''
    s = s.replace(anchor4, wave2_block + anchor4)

    ast.parse(s)
    with io.open(P, "w", encoding="utf-8") as f:
        f.write(s)
    print("✅ 已注入 Q131 / R62 / R63 / STATUS_PATCHES / WAVE2，语法 OK")
    print("   字节数 =", len(s.encode("utf-8")))


if __name__ == "__main__":
    main()
