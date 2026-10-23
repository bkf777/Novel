#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS 批量执行器：带 429 退避重试、断点续跑（已成功条目不重复请求）。
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "preview", "U01_tts")
CHUNK_DIR = os.path.join(OUT, "_chunks")
RESULT = os.path.join(OUT, "results.json")
TOOL = "connector__matrix__batch_text_to_audio"

MAX_RETRY = 8
SLEEP_BASE = 4


def load_done():
    if os.path.exists(RESULT):
        return json.load(open(RESULT, encoding="utf-8"))
    return {}


def save_done(done):
    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=1)


def call(reqs):
    p = os.path.join(CHUNK_DIR, "_cur.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"requests": reqs}, f, ensure_ascii=False)
    r = subprocess.run(
        ["mcode-tools", "connector", "call", TOOL, "--args-file", p],
        capture_output=True, text=True,
    )
    out = r.stdout
    i = out.find("{")
    if i < 0:
        return None, (r.stderr or out)[-400:]
    try:
        return json.loads(out[i:]), None
    except Exception as e:
        return None, f"parse fail: {e} :: {out[-300:]}"


def main():
    chunks = sorted(f for f in os.listdir(CHUNK_DIR) if f.startswith("batch_") and f.endswith(".json"))
    done = load_done()

    for cf in chunks:
        reqs = json.load(open(os.path.join(CHUNK_DIR, cf), encoding="utf-8"))["requests"]
        pending = [r for r in reqs if r["output_file"] not in done]
        if not pending:
            print(f"[skip] {cf} 全部已完成", flush=True)
            continue
        print(f"[run ] {cf} 待处理 {len(pending)}/{len(reqs)}", flush=True)

        attempt = 0
        queue = list(pending)
        while queue and attempt < MAX_RETRY:
            attempt += 1
            res, err = call(queue)
            if res is None:
                print(f"       ! {err}", flush=True)
                time.sleep(SLEEP_BASE * attempt)
                continue
            for it in res.get("success_items", []):
                done[it["file_name"]] = {"node_id": it["node_id"], "file_name": it["file_name"]}
            failed_idx = {f["index"] for f in res.get("failed_items", [])}
            if failed_idx:
                time.sleep(SLEEP_BASE * attempt)
            queue = [r for i, r in enumerate(queue) if i in failed_idx]
            save_done(done)
            print(f"       ok={len(res.get('success_items',[]))} fail={len(failed_idx)} retry_left={len(queue)}", flush=True)

        if queue:
            print(f"       ! {cf} 仍有 {len(queue)} 条失败，标记待补", flush=True)
            for r in queue:
                done.setdefault(r["output_file"], {"node_id": None, "file_name": r["output_file"], "pending": True})
            save_done(done)

    save_done(done)
    real = sum(1 for v in done.values() if v.get("node_id"))
    pend = sum(1 for v in done.values() if not v.get("node_id"))
    print(f"\n完成: 成功 {real} 条, 待补 {pend} 条", flush=True)


if __name__ == "__main__":
    main()
