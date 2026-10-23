#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_D08_unit.py —— D08 交付物的**结构化版本 diff**（可复跑资产）

用途：回答「某次 D08 改版**恰改了几处**」——逐叶子路径比对旧版与现行版，
      输出差异条数与差异路径。**不靠字节数/文件大小推断**（尺寸相同不构成
      内容相同的证据）。

方法（真盘零写入）：
  1. 在临时目录建**最小沙箱**：复制 `03_规格/`、`shared/D04.json`+`D05.json`、
     `units/<UNIT>/D06.json`+`D07.json`、`scripts/build_D08.py`+
     `scripts/d08_content_<UNIT>.py`；
  2. 在沙箱内把内容源里的**新措辞回退为旧措辞**、版本号回退为旧版本；
  3. 沙箱内跑 `build_D08.py` 重建旧版产物（**先实证版本守卫**：磁盘放现行版
     时应「拒绝覆盖 + exit 1 + SHA256 前后一致」，再删掉磁盘文件重建）；
  4. 逐叶子路径比对「沙箱重建旧版」与「真盘现行版」。

用法：
  python3 scripts/diff_D08_unit.py --unit U02 \
      --new-text "一枚律条被推上交易台，纹路压着冷光。" \
      --old-text "一枚低阶律条被推上交易台，纹路压着冷光。" \
      --old-version v1.3

  --new-text   内容源中**现行**的措辞（须在内容源中恰好命中 1 处）
  --old-text   回退目标措辞
  --old-version 回退目标版本号
  --keep-sandbox 保留沙箱（默认删除）

退出码：0＝diff 完成；1＝参数/锚点错误或守卫实证失败；2＝沙箱重建失败。
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile

FACTORY_MARK = "03_规格"

def find_factory_root(start):
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(d, FACTORY_MARK)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise SystemExit(f"❌ 找不到含 {FACTORY_MARK} 的工厂根目录")

def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, o

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--new-text", required=True)
    ap.add_argument("--old-text", required=True)
    ap.add_argument("--old-version", required=True)
    ap.add_argument("--keep-sandbox", action="store_true")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    factory = find_factory_root(here)
    proj = os.path.join(factory, "02_项目", "双相潮主")
    unit = args.unit

    live_d08 = os.path.join(proj, "units", unit, "D08.json")
    live_content = os.path.join(proj, "scripts", f"d08_content_{unit}.py")
    if not os.path.exists(live_d08):
        raise SystemExit(f"❌ 真盘产物不存在：{live_d08}")

    sb = tempfile.mkdtemp(prefix=f"diff_D08_{unit}_")
    sproj = os.path.join(sb, "02_项目", "双相潮主")
    os.makedirs(os.path.join(sproj, "units", unit))
    os.makedirs(os.path.join(sproj, "shared"))
    os.makedirs(os.path.join(sproj, "scripts"))
    shutil.copytree(os.path.join(factory, FACTORY_MARK), os.path.join(sb, FACTORY_MARK))
    for f in ("D04.json", "D05.json"):
        shutil.copy(os.path.join(proj, "shared", f), os.path.join(sproj, "shared", f))
    for f in ("D06.json", "D07.json"):
        shutil.copy(os.path.join(proj, "units", unit, f), os.path.join(sproj, "units", unit, f))
    shutil.copy(os.path.join(proj, "scripts", "build_D08.py"), os.path.join(sproj, "scripts"))
    shutil.copy(live_content, os.path.join(sproj, "scripts"))

    # ── 回退内容源 ────────────────────────────────────────────────
    cp = os.path.join(sproj, "scripts", f"d08_content_{unit}.py")
    src = open(cp, encoding="utf-8").read()
    n_anchor = src.count(args.new_text)
    if n_anchor != 1:
        raise SystemExit(f"❌ 锚点命中 {n_anchor} 处，必须恰好 1（新措辞）")
    src = src.replace(args.new_text, args.old_text)
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', src, re.M)
    if not m:
        raise SystemExit("❌ 内容源未找到 VERSION")
    src = src.replace(f'VERSION = "{m.group(1)}"', f'VERSION = "{args.old_version}"', 1)
    open(cp, "w", encoding="utf-8").write(src)
    print(f"✅ 沙箱内容源已回退：新措辞 → 旧措辞（1 处）｜VERSION {m.group(1)} → {args.old_version}")

    # ── 步骤 A：版本守卫实证（磁盘放现行版 → 应拒绝覆盖）────────────
    s_d08 = os.path.join(sproj, "units", unit, "D08.json")
    shutil.copy(live_d08, s_d08)
    before = sha256(s_d08)
    r = subprocess.run([sys.executable, "scripts/build_D08.py", "--project", ".", "--unit", unit],
                       cwd=sproj, capture_output=True, text=True)
    after = sha256(s_d08)
    guard_ok = (r.returncode != 0 and before == after)
    print(f"🔒 版本守卫实证：磁盘为现行版 + 脚本写旧版 → exit={r.returncode}｜"
          f"SHA256 前后{'一致' if before == after else '不一致'}｜"
          f"{'✅ 拒绝覆盖且磁盘零改写' if guard_ok else '❌ 守卫未生效'}")
    if not guard_ok:
        print(r.stdout[-600:]); print(r.stderr[-600:])
        return 1

    # ── 步骤 B：重建旧版 ──────────────────────────────────────────
    os.remove(s_d08)
    r = subprocess.run([sys.executable, "scripts/build_D08.py", "--project", ".", "--unit", unit],
                       cwd=sproj, capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ 沙箱重建失败："); print(r.stdout[-1500:]); print(r.stderr[-800:]); return 2
    print("✅ 沙箱重建旧版完成")

    # ── 步骤 C：逐叶子结构化 diff ─────────────────────────────────
    old = json.load(open(s_d08, encoding="utf-8"))
    new = json.load(open(live_d08, encoding="utf-8"))
    a, b = dict(leaves(old)), dict(leaves(new))
    ka, kb = set(a), set(b)
    only_old, only_new = sorted(ka - kb), sorted(kb - ka)
    chg = sorted(k for k in ka & kb if a[k] != b[k])
    total = len(only_old) + len(only_new) + len(chg)
    print()
    print("=" * 68)
    print(f"结构化 diff：沙箱重建 {args.old_version}  vs  真盘现行 {new.get('version')}")
    print(f"  叶子路径数 旧 {len(ka)} / 新 {len(kb)}｜仅旧有 {len(only_old)}｜仅新有 {len(only_new)}｜值不同 {len(chg)}")
    print(f"  ⇒ 全量差异条数 = {total}")
    print("=" * 68)
    for k in chg:
        print(f"  ~ {k}\n      旧: {a[k]!r}\n      新: {b[k]!r}")
    for k in only_old:
        print(f"  - 仅旧有: {k} = {a[k]!r}")
    for k in only_new:
        print(f"  + 仅新有: {k} = {b[k]!r}")
    print()
    print("  注：`version` 与 `word_count.*` 属**派生量/元数据**，与内容改动分开计；")
    print("      真正的**内容改动条数**＝ 上表中 `body`/`shot_intent`/`compliance_notes` 等路径的差异数。")

    if not args.keep_sandbox:
        shutil.rmtree(sb, ignore_errors=True)
        print(f"\n（沙箱已清理：{sb}）")
    else:
        print(f"\n（沙箱保留：{sb}）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
