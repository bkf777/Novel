#!/usr/bin/env bash
# Q94 幂等证据：同一白模产物 → 两次**独立**运行全链（fill→check→prompt→assemble）
#   → 比对 units/<U>/D14.json 的 sha256。
# 每次运行都使用**白模工作区的独立副本**与**项目副本**，避免任何复用/中间态污染。
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
BASE=/tmp/q94_idem
VER=v1.8
mkdir -p "$BASE"

for U in U01 U02 U03; do
   W="/tmp/dcc-smoke/prod/$(echo "$U" | tr 'A-Z' 'a-z')"
  [ -d "$W" ] || { echo "[SKIP] $U 无工作区 $W"; continue; }
  for R in 1 2; do
    B="$BASE/$U/run$R"
    rm -rf "$B"; mkdir -p "$B/proj/units/$U"
    cp -a "$ROOT/scripts" "$B/proj/"
    cp -a "$ROOT/units/$U/D11.json" "$ROOT/units/$U/D13.json" "$B/proj/units/$U/" 2>/dev/null
    mkdir -p "$B/proj/03_规格" && cp -a "$ROOT/03_规格/." "$B/proj/03_规格/" 2>/dev/null
    cp -a "$W" "$B/work"
  done

  for R in 1 2; do
    B="$BASE/$U/run$R"
    echo "=== [$U] run$R ==="
    python3 "$B/proj/scripts/fill_D14_contracts.py" --unit "$U" --work "$B/work" >"$B/fill.log" 2>&1
    echo "  fill_exit=$?"
    python3 "$B/proj/scripts/d14_pipeline.py" check --root "$B/work" >"$B/check.log" 2>&1
    echo "  check_exit=$?"
    python3 "$B/proj/scripts/d14_pipeline.py" prompt --root "$B/work" >"$B/prompt.log" 2>&1
    echo "  prompt_exit=$?"
    python3 "$B/proj/scripts/assemble_D14.py" --unit "$U" --project "$B/proj" --work "$B/work" --version "$VER" >"$B/assemble.log" 2>&1
    echo "  assemble_exit=$?"
  done

  A="$BASE/$U/run1/proj/units/$U/D14.json"
  Bf="$BASE/$U/run2/proj/units/$U/D14.json"
  if [ -f "$A" ] && [ -f "$Bf" ]; then
    sa=$(shasum -a 256 "$A" | cut -d' ' -f1)
    sb=$(shasum -a 256 "$Bf" | cut -d' ' -f1)
    ba=$(stat -f%z "$A"); bb=$(stat -f%z "$Bf")
    if [ "$sa" = "$sb" ]; then
      echo "[IDEM-OK] $U  sha256 一致 = $sa  bytes=$ba/$bb"
    else
      echo "[IDEM-FAIL] $U  sha256 不一致 run1=$sa($ba) run2=$sb($bb)"
      diff <(python3 -c "import json,sys;print(json.dumps(json.load(open('$A')),ensure_ascii=False,sort_keys=True,indent=1))") \
           <(python3 -c "import json,sys;print(json.dumps(json.load(open('$Bf')),ensure_ascii=False,sort_keys=True,indent=1))") \
           | head -40
    fi
  else
    echo "[IDEM-FAIL] $U 产物缺失 run1=$([ -f "$A" ] && echo ok || echo miss) run2=$([ -f "$Bf" ] && echo ok || echo miss)"
  fi
done
echo "IDEM_ALL_DONE"
