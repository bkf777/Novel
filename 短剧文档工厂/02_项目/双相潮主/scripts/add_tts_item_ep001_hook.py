#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登记 ep001_hook TTS 资产 → preview/U01_tts/items.json ＋ preview/U01_tts/results.json

内容源（不是手改 JSON）：
  · 文本／语气 ＝ units/U01/D09.json 的 ep1 #1（「上一趟我死在第三个小时。」／tone「喘息未平，气声压低，像从牙缝里挤出来」）
  · 同源核对 ＝ units/U01/D08.json 的 ep1 body[2]（同句 dialogue）
  · 音色参数 ＝ items.json 的 ep001_05（voice_id male-qn-badao／speed 0.95／pitch -1，Chief 明派「沿用、不新造音色」）
  · 音频      ＝ matrix TTS（connector__matrix__synthesize_speech，node_id 455361723802011）→ audio/ep001_hook.mp3
  · dur       ＝ ffprobe format=duration 实测（不取缓存字段）

幂等：已存在则逐字段校验并 [NO-OP]；格式保真：写前先验证 round-trip 与原文件逐字节一致。
"""
import json, os, subprocess, hashlib, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "preview", "U01_tts")
AUDIO = os.path.join(OUT, "audio")
ITEMS = os.path.join(OUT, "items.json")
RESULTS = os.path.join(OUT, "results.json")

HOOK_ID = "ep001_hook"
MP3 = os.path.join(AUDIO, HOOK_ID + ".mp3")
NODE_ID = "455361723802011"
TEXT = "「上一趟我死在第三个小时。」"
D09_REF = "D09 ep1 #1"
VOICE = {"voice_id": "male-qn-badao", "emotion": "angry", "speed": 0.95, "pitch": -1, "role": "LC"}


def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def dumps(obj):
    """沿用既有序列化格式：ensure_ascii=False + indent=2 + 无末尾换行（由格式探针实测确定）"""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def match_format(raw, obj):
    """格式探针：找出能逐字节复现原文的 (indent, 末尾换行) 组合；找不到即中止"""
    for indent in (2, 1, 4, None):
        for tail in ("", "\n"):
            cand = json.dumps(obj, ensure_ascii=False, indent=indent) + tail
            if cand == raw:
                return indent, tail
    return None, None


def atomic_write(path, text):
    tmp = path + ".tmp.%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    # ── 守卫 1：音频在位且非空 ──
    assert os.path.exists(MP3) and os.path.getsize(MP3) > 1000, "hook 音频缺失或过小：%s" % MP3
    dur = dur_of(MP3)
    assert dur > 0, "ffprobe 实测时长异常：%r" % dur

    # ── 守卫 2：内容源核对（D09 ep1 #1 与 D08 ep1 body[2] 同句）──
    d09 = json.load(open(os.path.join(ROOT, "units", "U01", "D09.json"), encoding="utf-8"))
    d09line = [l for l in d09["lines"] if l.get("ep") == 1 and l.get("idx") == 1]
    assert d09line, "D09 ep1 #1 不存在"
    assert d09line[0]["text"] == TEXT, "D09 ep1 #1 文本与本单文本不一致：%r" % d09line[0]["text"]
    assert d09line[0]["tone"] == "喘息未平，气声压低，像从牙缝里挤出来", "D09 ep1 #1 tone 与单据情绪描述不一致"

    entry = {
        "id": HOOK_ID, "ep": 1, "kind": "dialogue", "text": TEXT,
        "voice_id": VOICE["voice_id"], "emotion": VOICE["emotion"],
        "speed": VOICE["speed"], "pitch": VOICE["pitch"], "role": VOICE["role"],
        "audio": MP3, "dur": dur, "role_prev": VOICE["role"],
    }

    # ── items.json ──
    raw = open(ITEMS, encoding="utf-8").read()
    items = json.loads(raw)
    assert isinstance(items, list), "items.json 顶层应为 list"
    # 格式保真：round-trip 必须与原文逐字节一致
    ind, tail = match_format(raw, items)
    assert ind is not None, "items.json 格式探针失败：round-trip 无法逐字节复现原文，中止"
    print("[1] items.json 格式保真校验通过（indent=%s, 末尾换行=%r，%d 条）" % (ind, tail, len(items)))

    exist = [i for i in items if i.get("id") == HOOK_ID]
    if exist:
        assert exist[0] == entry, "已存在条目与预期不一致，\n现: %s\n期: %s" % (exist[0], entry)
        print("[2] ep001_hook 已存在且逐字段一致 → [NO-OP]")
    else:
        pos = next((i for i, x in enumerate(items) if x.get("ep") == 1), len(items))
        items.insert(pos, entry)
        atomic_write(ITEMS, dumps(items))
        print("[2] ep001_hook 已插入 items.json（位置 %d，ep001 组之首）" % pos)

    # ── results.json ──
    rawr = open(RESULTS, encoding="utf-8").read()
    res = json.loads(rawr)
    assert isinstance(res, dict), "results.json 顶层应为 dict"
    indr, tailr = match_format(rawr, res)
    assert indr is not None, "results.json 格式探针失败：round-trip 无法逐字节复现原文，中止"
    print("[1b] results.json 格式保真校验通过（indent=%s, 末尾换行=%r，%d 键）" % (indr, tailr, len(res)))
    key = HOOK_ID + ".mp3"
    want = {"node_id": NODE_ID, "file_name": key}
    if key in res:
        assert res[key] == want, "results.json 已有条目与预期不一致：%s" % res[key]
        print("[3] results.json 已含该键且一致 → [NO-OP]")
    else:
        res[key] = want
        atomic_write(RESULTS, dumps(res))
        print("[3] results.json 已补记录 %s → %s" % (key, want))

    # ── 写后断言 ──
    items2 = json.load(open(ITEMS, encoding="utf-8"))
    res2 = json.load(open(RESULTS, encoding="utf-8"))
    assert len(items2) == len(items), "items 条目数异常"
    got = [x for x in items2 if x.get("id") == HOOK_ID]
    assert len(got) == 1 and got[0]["dur"] == dur, "items 内 hook 条目异常"
    assert res2.get(key) == want, "results 内 hook 记录异常"
    assert os.path.exists(got[0]["audio"]) and os.path.getsize(got[0]["audio"]) > 1000, "hook 音频不在位"
    print("[4] 写后断言全过：items %d 条｜results %d 键｜hook dur=%.6f" % (len(items2), len(res2), dur))
    print("    items sha16=%s" % hashlib.sha256(open(ITEMS, 'rb').read()).hexdigest()[:16])
    print("    results sha16=%s" % hashlib.sha256(open(RESULTS, 'rb').read()).hexdigest()[:16])
    print("    源核对：D09 ep1 #1 ＝%s" % d09line[0]["text"])


if __name__ == "__main__":
    main()
