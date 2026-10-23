#!/usr/bin/env bash
# U01 预演片收尾守门：等上游 TTS 配额恢复 → 补 ep008_13 → 重拼 8 个 mp4。
#
# 背景：上游 TTS 服务整体限流（429），偶尔放行一次但后处理报内部错误。
# 本守门每 90 秒试一次，成功即：
#   ① 写回 results.json 记录（node_id）并下载 mp3 到 audio/
#   ② 跑 run_tts_serial.py（断点续跑，只补这一条）
#   ③ 跑 build_video_u01.py 重拼 8 个 mp4
# 失败则继续等，不动任何已完成的产物。
set -u
cd "$(dirname "$0")/../preview/U01_tts" || exit 1
LOG=../../reports/tts_gate.log
mkdir -p ../../reports

for i in $(seq 1 200); do
  TS=$(date +%H:%M:%S)
  R=$(mcode-tools connector call connector__matrix__batch_text_to_audio \
        --args-file _chunks/_one.json 2>/dev/null | tail -1)
  if echo "$R" | grep -q '"total_success":1'; then
    echo "[$TS] attempt $i: SUCCESS — 开始补齐" | tee -a "$LOG"
    echo "$R" > _chunks/_one_result.json
    python3 ../../scripts/run_tts_serial.py 2>&1 | tail -20 | tee -a "$LOG"
    if [ -f audio/ep008_13.mp3 ]; then
      echo "[$TS] ep008_13 已落盘，重拼 8 个 mp4" | tee -a "$LOG"
      python3 ../../scripts/build_video_u01.py 2>&1 | tail -20 | tee -a "$LOG"
      ls -l ../U01_video/*.mp4 | awk '{print $5, $9}' | tee -a "$LOG"
      echo "[$TS] DONE" | tee -a "$LOG"
      exit 0
    fi
    echo "[$TS] 合成返回成功但 mp3 未落盘，继续等" | tee -a "$LOG"
  else
    CODE=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);f=d.get('failed_items') or [{}];print(f[0].get('err_code',''))" 2>/dev/null)
    MSG=$(echo "$R" | python3 -c "import sys,json;d=json.load(sys.stdin);f=d.get('failed_items') or [{}];print(f[0].get('error_msg','')[:80])" 2>/dev/null)
    echo "[$TS] attempt $i: $CODE $MSG" | tee -a "$LOG"
  fi
  sleep 90
done
echo "[$(date +%H:%M:%S)] 守门超时退出（200 次未成功）" | tee -a "$LOG"
exit 1
