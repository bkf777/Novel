#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS 串行执行器：单条逐个请求，429 退避重试，断点续跑。

上游对并发敏感（批量 8-10 条必然 429），必须严格串行 + 间隔。
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "preview", "U01_tts")
CHUNK_DIR = os.path.join(OUT, "_chunks")
RESULT = os.path.join(OUT, "results.json")
TOOL = "connector__matrix__batch_text_to_audio"

GAP = 2.5          # 串行请求间隔（秒）
MAX_RETRY = 40     # 单条最大重试
BACKOFF = 8.0      # 429 退避基数


def load_done():
    return json.load(open(RESULT, encoding="utf-8")) if os.path.exists(RESULT) else {}


def save_done(d):
    with open(RESULT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def call_one(req):
    p = os.path.join(CHUNK_DIR, "_one.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"requests": [req]}, f, ensure_ascii=False)
    r = subprocess.run(["mcode-tools", "connector", "call", TOOL, "--args-file", p],
                       capture_output=True, text=True)
    out = r.stdout
    i = out.find("{")
    if i < 0:
        return None, (r.stderr or out)[-200:]
    try:
        return json.loads(out[i:]), None
    except Exception as e:
        return None, f"parse:{e}"


def main():
    items = json.load(open(os.path.join(OUT, "items.json"), encoding="utf-8"))
    done = load_done()

    todo = [it for it in items if (it["id"] + ".mp3") not in done
            or not done.get(it["id"] + ".mp3", {}).get("node_id")]
    print(f"待处理 {len(todo)} / 共 {len(items)}", flush=True)

    for n, it in enumerate(todo, 1):
        fn = it["id"] + ".mp3"
        req = {
            "text": it["text"],
            "voice_id": it["voice_id"],
            "emotion": it["emotion"],
            "speed": it["speed"],
            "pitch": it["pitch"],
            "output_file": fn,
        }
        attempt = 0
        while attempt < MAX_RETRY:
            attempt += 1
            res, err = call_one(req)
            if res is None:
                print(f"  [{n}/{len(todo)}] {fn} ERR {err}", flush=True)
                time.sleep(BACKOFF * min(attempt, 6))
                continue
            if res.get("success_items"):
                done[fn] = {"node_id": res["success_items"][0]["node_id"], "file_name": fn}
                save_done(done)
                print(f"  [{n}/{len(todo)}] {fn} ✓ (try {attempt})", flush=True)
                break
            code = res.get("code")
            wait = BACKOFF * min(attempt, 8)
            print(f"  [{n}/{len(todo)}] {fn} 429/code={code} → sleep {wait:.0f}s (try {attempt})", flush=True)
            time.sleep(wait)
        else:
            print(f"  [{n}/{len(todo)}] {fn} ✗ 最终失败", flush=True)
            done.setdefault(fn, {"node_id": None, "file_name": fn, "pending": True})
            save_done(done)
        time.sleep(GAP)

    save_done(done)
    ok = sum(1 for v in done.values() if v.get("node_id"))
    print(f"\n成功 {ok} / {len(items)}", flush=True)


if __name__ == "__main__":
    main()
