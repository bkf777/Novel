# -*- coding: utf-8 -*-
"""纠正 patch_ledger_marker_align.py 的批量替换副作用，并把 marker 对齐前移到读盘后。

上一版补丁用「全局批量替换 U01-R62/R63 → U01-R64/R65」改正文引用，
副作用是**误伤了 spec R60／R61 两条历史 spec 的 marker**（它们本该是 R62/R63）；
且 `align_marker_ids` 被放在写盘前 ⇒ 幂等跳过检查发生在对齐之前 ⇒ 判据失配。

本补丁做四件事：
  ① 把 6 条 spec 的 id 与 marker 一次性钉死为「同号且互不冲突」：
       R58 → U01-R60 / 【U01-R60-EP001-FOUR-FREEZES-RULING】
       R59 → U01-R61 / 【U01-R61-SAMPLING-WINDOW-ERROR】
       R60 → U01-R62 / 【U01-R62-D11-DIALOGUE-LAG】
       R61 → U01-R63 / 【U01-R63-V13-MINGPAI】
       R62 → U01-R64 / 【U01-R64-D15-DUR-STALE】
       R63 → U01-R65 / 【U01-R65-D16-EP001-DIALOGUE-CLIPPED】
  ② `align_marker_ids` 前移到 main() 读盘后（幂等跳过检查之前）——
     **对齐必须先于判定**，否则产物侧 marker 与 spec 侧对不上。
  ③ 对齐与自检的**前缀按条目 id 取**（不再硬编码 U01-R），
     ⛔ 修掉 U02/U03 条目会被错改成 U01-R 的隐患。
  ④ 落盘前自检保持不变（marker 编号 ≠ id 编号 ⇒ 中止写盘）。

⛔ 只改注册脚本（spec 侧）；D18.json 由注册脚本负责写。
⛔ 注入的中文字符串内一律用「」，⛔ 不得用 ASCII 双引号。
"""
import ast
import io
import os
import re

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "register_d18_v135_ep002_regression.py")


def sub_once(s, old, new, label):
    assert s.count(old) == 1, "锚点异常：%s（命中 %d 次）" % (label, s.count(old))
    return s.replace(old, new)


NEW_ALIGN = '''def align_marker_ids(d):
    """把 open_issues 条目里 marker 的**编号**改成与该条目 **id 编号**同号。

    根因：marker 编号取的是脚本内 spec 序号，id 取的是空闲号分配位，两者不同源
    （实测 U01-R58~R61 四条 spec 被分配到 U01-R60~U01-R63，编号整体错位 2 位）。
    本函数在**读盘后立刻**以 id 为准改写产物侧 marker；
    spec 侧 marker 由同一次补丁同步钉死 ⇒ 幂等检测（has_marker）继续成立。
    幂等：已是同号的条目不动。前缀按条目 id 取（U01-R／U02-R／U03-R），不硬编码。
    """
    fixed = 0
    pat = re.compile(r"【(U\\d\\d-R\\d+)-([^】]+)】")
    for e in d.get("open_issues", []):
        eid = e.get("id") or ""
        if not re.match(r"^U\\d\\d-R\\d+$", eid):
            continue
        prefix = eid[:5]
        num = eid[5:]
        for k, v in list(e.items()):
            if not isinstance(v, str):
                continue

            def _fix(mo, _prefix=prefix, _num=num, _cnt=None):
                if mo.group(1)[5:] == _num and mo.group(1)[:5] == _prefix:
                    return mo.group(0)
                fixed += 1
                return "【%s%s-%s】" % (_prefix, _num, mo.group(2))

            nv = pat.sub(_fix, v)
            if nv != v:
                e[k] = nv
    return fixed
'''


def main():
    with io.open(P, "r", encoding="utf-8") as f:
        s = f.read()

    # ── ① 六条 spec 的 id / marker 钉死 ───────────────────────────────────
    pairs = [
        ('    "id": "U01-R58",\n    "marker": "【U01-R60-EP001-FOUR-FREEZES-RULING】",',
         '    "id": "U01-R60",\n    "marker": "【U01-R60-EP001-FOUR-FREEZES-RULING】",', "R58"),
        ('    "id": "U01-R59",\n    "marker": "【U01-R61-SAMPLING-WINDOW-ERROR】",',
         '    "id": "U01-R61",\n    "marker": "【U01-R61-SAMPLING-WINDOW-ERROR】",', "R59"),
        ('    "id": "U01-R60",\n    "marker": "【U01-R64-D11-DIALOGUE-LAG】",',
         '    "id": "U01-R62",\n    "marker": "【U01-R62-D11-DIALOGUE-LAG】",', "R60"),
        ('    "id": "U01-R61",\n    "marker": "【U01-R65-V13-MINGPAI】",',
         '    "id": "U01-R63",\n    "marker": "【U01-R63-V13-MINGPAI】",', "R61"),
    ]
    for old, new, lbl in pairs:
        s = sub_once(s, old, new, lbl)

    # ── ② 整段替换 align_marker_ids ───────────────────────────────────────
    i = s.find("def align_marker_ids(d):")
    assert i > 0, "align_marker_ids 起点未找到"
    j = s.find("\ndef assert_marker_ids_aligned(d):", i)
    assert j > i, "align_marker_ids 终点未找到"
    s = s[:i] + NEW_ALIGN.rstrip() + "\n\n" + s[j + 1:]

    # ── ②b 自检函数泛化前缀 ────────────────────────────────────────────────
    old_chk = '''        for mk in re.findall(r"【U01-R(\\d+)-[^】]+】", json.dumps(e, ensure_ascii=False)):
            if mk != m.group(2):
                bad.append((eid, mk))'''
    new_chk = '''        for mk in re.findall(r"【(U\\d\\d-R(\\d+))-[^】]+】",
                             json.dumps(e, ensure_ascii=False)):
            if mk[1] != m.group(2):
                bad.append((eid, mk[1]))'''
    s = sub_once(s, old_chk, new_chk, "自检正则")

    # ── ③ 对齐前移：读盘后立刻对齐（必须先于幂等跳过检查） ────────────────
    old_head = '''    print(f"   基线：D18 v{fp0['version']} sha16={fp0['sha16']} "
          f"size={fp0['size']} mtime={fp0['mtime']}")
'''
    new_head = '''    print(f"   基线：D18 v{fp0['version']} sha16={fp0['sha16']} "
          f"size={fp0['size']} mtime={fp0['mtime']}")

    # marker 编号对齐必须**先于**幂等跳过检查：产物侧 marker 先归位，
    # 才谈得上「spec marker 是否已落进产物条目」的判定。
    n_align0 = align_marker_ids(d)
    if n_align0:
        print(f"   ⛭ marker 编号对齐（读盘后立刻）：{n_align0} 处改到与条目 id 同号")
'''
    s = sub_once(s, old_head, new_head, "main 头部")

    # ── ④ 写盘前复核块 ────────────────────────────────────────────────────
    old_pre = '''    n_align = align_marker_ids(d)
    print(f"   ⛭ marker 编号对齐：{n_align} 处 marker 编号改到与条目 id 同号")
    if not assert_marker_ids_aligned(d):
        return 2'''
    new_pre = '''    n_align = align_marker_ids(d)
    if n_align:
        print(f"   ⛭ marker 编号对齐（写盘前复核）：{n_align} 处")
    if not assert_marker_ids_aligned(d):
        return 2'''
    s = sub_once(s, old_pre, new_pre, "写盘前对齐块")

    ast.parse(s)
    with io.open(P, "w", encoding="utf-8") as f:
        f.write(s)
    print("✅ 纠正完成：6 条 spec id/marker 同号 ＋ 对齐前移 ＋ 前缀泛化，语法 OK")
    print("   字节数 =", len(s.encode("utf-8")))


if __name__ == "__main__":
    main()
