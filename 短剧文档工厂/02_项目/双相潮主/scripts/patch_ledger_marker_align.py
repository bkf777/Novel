# -*- coding: utf-8 -*-
"""把 D18 台账的「条目 id ↔ marker 编号」收口为同源，并加落盘前自检。

背景（2026-10-23 13:30 总控实测）：
  open_issues 里 marker 编号取的是**脚本内 spec 序号**，而条目 id 取的是**空闲号分配位**，
  两个命名空间不同源 ⇒ 实际出现 4 条错位：
      id U01-R60  挂 marker【U01-R58-EP001-FOUR-FREEZES-RULING】
      id U01-R61  挂 marker【U01-R59-SAMPLING-WINDOW-ERROR】
      id U01-R62  挂 marker【U01-R60-D11-DIALOGUE-LAG】
      id U01-R63  挂 marker【U01-R61-V13-MINGPAI】
  ⇒ 拿着「U01-R62」去查表会查到错的那一条 ⇒ 同名不同物。

本补丁做四件事：
  ① 把 4 条历史条目的 marker 编号改成与其 id 同号（**产物侧由注册脚本在写盘前统一改**，
     **脚本侧同步改 spec marker**，两侧一起改 ⇒ 幂等检测继续成立）；
  ② 新条目改为**声明式 id**（spec 写明 id，注册脚本优先用声明 id；声明 id 被占则**报错中止**
     而不是静默改号），marker 与 id 同号；
  ③ 注册脚本加**落盘前自检**：任一条目的 marker 编号与自身 id 编号不一致 ⇒ 中止写盘；
  ④ 修正本轮新增两条的编号与正文交叉引用。

⛔ 本补丁只改注册脚本（spec 侧），不碰 D18.json —— 产物侧由注册脚本负责。
⛔ 注入的中文字符串内一律用「」，⛔ 不得用 ASCII 双引号。
"""
import ast
import io
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "register_d18_v135_ep002_regression.py")


def sub_once(s, old, new, label):
    assert s.count(old) == 1, "锚点异常：%s（命中 %d 次）" % (label, s.count(old))
    return s.replace(old, new)


def main():
    with io.open(P, "r", encoding="utf-8") as f:
        s = f.read()

    # ── ① 4 条历史 spec 的 marker 编号改与其最终 id 同号 ────────────────────
    s = sub_once(s, '"marker": "【U01-R58-EP001-FOUR-FREEZES-RULING】",',
                 '"marker": "【U01-R60-EP001-FOUR-FREEZES-RULING】",', "R58 marker")
    s = sub_once(s, '"marker": "【U01-R59-SAMPLING-WINDOW-ERROR】",',
                 '"marker": "【U01-R61-SAMPLING-WINDOW-ERROR】",', "R59 marker")
    s = sub_once(s, '"marker": "【U01-R60-D11-DIALOGUE-LAG】",',
                 '"marker": "【U01-R62-D11-DIALOGUE-LAG】",', "R60 marker")
    s = sub_once(s, '"marker": "【U01-R61-V13-MINGPAI】",',
                 '"marker": "【U01-R63-V13-MINGPAI】",', "R61 marker")

    # ── ② 新条目 R62/R63 改声明式 id（U01-R64/U01-R65），marker 同步 ──────────
    s = sub_once(s, '''    "id": "U01-R62",
    "marker": "【U01-R62-D15-DUR-STALE】",''',
                 '''    "id": "U01-R64",
    "marker": "【U01-R64-D15-DUR-STALE】",''', "R62 id")
    s = sub_once(s, '''    "id": "U01-R63",
    "marker": "【U01-R63-D16-EP001-DIALOGUE-CLIPPED】",''',
                 '''    "id": "U01-R65",
    "marker": "【U01-R65-D16-EP001-DIALOGUE-CLIPPED】",''', "R63 id")

    # ── ②b 本轮正文里的交叉引用同步改号 ────────────────────────────────────
    # 实测：脚本里 "U01-R62"/"U01-R63" 的**全部**出现都在本轮注入块内
    # （其余历史 spec 的 marker 是 R58/R59/R60/R61，不受影响）；
    # 上面的 id/marker 显式替换已先把两条新 spec 的 id/marker 改成 R64/R65，
    # ⇒ 此处对**余下的正文引用**做批量同号替换。
    _before = s.count("U01-R62") + s.count("U01-R63")
    s = s.replace("U01-R62", "U01-R64").replace("U01-R63", "U01-R65")
    print(f"   · 正文引用改号：{_before} 处 U01-R62/R63 → U01-R64/R65")

    # ── ③ 注册脚本：声明式 id ＋ marker 产物侧对齐 ＋ 落盘前自检 ──────────────
    old_alloc = '''        while f"U01-R{rn}" in existing_oids:
            rn += 1
        oid = f"U01-R{rn}"
        rn += 1
        existing_oids.add(oid)'''
    new_alloc = '''        # 声明式 id 优先：spec 写明的 id 若空闲就用它；若已被占 ⇒ **报错中止**
        # （⛔ 不再静默改号 —— 静默改号是本轮 U01-R58~R61 四条 marker/id 错位的根因）。
        declared = spec.get("id")
        if declared:
            if declared in existing_oids:
                print(f"❌ spec {spec.get('id')} 声明的 id {declared} 已被占用 ⇒ "
                      f"中止：请改 spec 的 id 与 marker 编号（marker 编号必须与 id 同号）")
                return 2
            oid = declared
        else:
            while f"U01-R{rn}" in existing_oids:
                rn += 1
            oid = f"U01-R{rn}"
            rn += 1
        existing_oids.add(oid)'''
    s = sub_once(s, old_alloc, new_alloc, "id 分配块")

    # ③b marker 产物侧对齐（把条目里 marker 的编号改成与条目 id 同号）
    anchor = "def backfill_markers(d, specs, section, field):"
    align_fn = '''def align_marker_ids(d):
    """把 open_issues 条目里 marker 的**编号**改成与该条目 **id 编号**同号。

    根因：marker 编号取的是脚本内 spec 序号，id 取的是空闲号分配位，两者不同源。
    本函数在**写盘前**统一以 id 为准改写产物侧 marker；
    spec 侧 marker 由同一次补丁同步改过 ⇒ 幂等检测（has_marker）继续成立。
    幂等：已是同号的条目不动。
    """
    fixed = 0
    for e in d.get("open_issues", []):
        eid = e.get("id") or ""
        m = re.match(r"^(U\\d\\d-R\\d+)$", eid)
        if not m:
            continue
        for k, v in list(e.items()):
            if not isinstance(v, str):
                continue
            def _fix(mo):
                nonlocal fixed
                old_num, rest = mo.group(1), mo.group(2)
                if old_num == eid[5:]:
                    return mo.group(0)
                fixed += 1
                return "【U01-R%s-%s】" % (eid[5:], rest)
            nv = re.sub(r"【U01-R(\\d+)-([^】]+)】", _fix, v)
            if nv != v:
                e[k] = nv
    return fixed


def assert_marker_ids_aligned(d):
    """落盘前自检：任一条目的 marker 编号与自身 id 编号不一致 ⇒ 中止写盘。"""
    bad = []
    for e in d.get("open_issues", []):
        eid = e.get("id") or ""
        m = re.match(r"^(U\\d\\d-R(\\d+))$", eid)
        if not m:
            continue
        for mk in re.findall(r"【U01-R(\\d+)-[^】]+】", json.dumps(e, ensure_ascii=False)):
            if mk != m.group(2):
                bad.append((eid, mk))
    for c in d.get("global_checks", []):
        cid = c.get("id") or ""
        if not re.match(r"^Q\\d+$", cid):
            continue
        for mk in re.findall(r"【Q(\\d+)-[^】]+】", json.dumps(c, ensure_ascii=False)):
            if mk != cid[1:]:
                bad.append((cid, mk))
    if bad:
        for eid, mk in bad:
            print(f"❌ marker 编号与 id 不同号：条目 id={eid} 挂 marker 编号 {mk}")
        print("❌ 中止写盘：须先把 marker 编号改到与 id 同号（或改用无编号 marker）")
        return False
    return True


'''
    s = sub_once(s, anchor, align_fn + anchor, "backfill_markers 锚点")

    # ③c 在 main() 的写盘前调用对齐与自检
    old_guard = '''    os.makedirs(BAK, exist_ok=True)'''
    new_guard = '''    # ── ⑥ marker 编号与 id 同号：对齐 ＋ 落盘前自检（不通过则中止写盘） ──
    n_align = align_marker_ids(d)
    print(f"   ⛭ marker 编号对齐：{n_align} 处 marker 编号改到与条目 id 同号")
    if not assert_marker_ids_aligned(d):
        return 2

    os.makedirs(BAK, exist_ok=True)'''
    s = sub_once(s, old_guard, new_guard, "写盘前锚点")

    ast.parse(s)
    with io.open(P, "w", encoding="utf-8") as f:
        f.write(s)
    print("✅ 已收口 marker↔id 同源 ＋ 声明式 id ＋ 落盘前自检，语法 OK")
    print("   字节数 =", len(s.encode("utf-8")))


if __name__ == "__main__":
    main()
