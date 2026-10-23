#!/usr/bin/env bash
# Q94 白模重建：D14 链（preflight → 合同 → check → prompt → assemble）
# 用法：bash scripts/run_d14_chain.sh U01
set -euo pipefail
cd "$(dirname "$0")/.."
U="${1:?用法: run_d14_chain.sh <U01|U02>}"
W="/tmp/dcc-smoke/$(echo "$U" | tr 'A-Z' 'a-z')"
echo "=== [$U] 工作区 $W ==="
python3 scripts/d14_pipeline.py preflight --root "$W" | tail -5
python3 scripts/fill_D14_contracts.py --unit "$U" --work "$W" | tail -5
python3 scripts/d14_pipeline.py check --root "$W" | tail -5
python3 scripts/d14_pipeline.py prompt --root "$W" | tail -40
python3 scripts/assemble_D14.py --unit "$U" --work "$W" --version v1.6 | tail -10
