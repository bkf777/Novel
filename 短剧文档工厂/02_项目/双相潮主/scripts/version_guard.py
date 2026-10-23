#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""version_guard.py —— 写盘版本守卫（**单元无关**，Q64 / Q68）

判定口径（Q64）：
  ① 写盘点必须先比版本：**磁盘版本更高 ⇒ 判「有他人已升版」⇒ 拒绝并中止**（exit≠0）；
  ② 守卫必须可旁路但需显式（``--force``），且旁路动作要**留痕**（谁在何时用 force 覆盖了谁）；
  ③ 守卫**不得写死单元** —— 本模块只认传入的路径与版本号，对任意 ``--unit`` 生效；
  ④ 正常升版 / 幂等重跑必须放行（防「守卫过宽导致升版被卡死」）。

可达性（Q68）：
  - 守卫函数**有定义**且**在写盘前被调用**；
  - 本模块**不自行 exit**，只返回判定，由调用方决定如何中止 —— 避免「上游守卫抢先 exit
    遮蔽下游守卫」这一已实证的失效模式；
  - 调用方不得在守卫之前放置会抢先退出的其他守卫。

版本比较：语义化 ``v<major>.<minor>``；字段缺失按 0 处理；非 ``v`` 前缀的串按 0.0.0 处理。
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from typing import Optional, Tuple

_VER_RE = re.compile(r"^v?(\d+)\.(\d+)")


def parse_version(v) -> Tuple[int, int]:
    """把 ``v1.2`` 解析成 ``(1, 2)``；无法解析时返回 ``(0, 0)``。"""
    if not isinstance(v, str):
        return (0, 0)
    m = _VER_RE.match(v.strip())
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def read_version(path) -> Optional[str]:
    """读磁盘产物的 ``version`` 字段；文件不存在或读不出则返回 None。"""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        v = data.get("version")
        return v if isinstance(v, str) else None
    return None


class VersionGuard:
    """写盘版本守卫。

    :param out_path:  目标产物路径（磁盘已存在则比版本，不存在则直接放行）
    :param target:    本次将写入的版本号（如 ``v1.0``）
    :param unit:      单元号（仅用于留痕，不参与判定）
    :param doc_id:    交付物编号（仅用于留痕）
    :param force:     True 时旁路放行并留痕
    :param log_path:  旁路留痕文件（默认 ``<project>/reports/force_overwrite_log.jsonl``）
    """

    def __init__(self, out_path, target: str, unit: str = "", doc_id: str = "",
                 log_path: Optional[str] = None):
        self.out_path = str(out_path)
        self.target = target
        self.unit = unit or ""
        self.doc_id = doc_id or ""
        self.log_path = log_path
        self.disk_version: Optional[str] = None
        self.blocked = False
        self.forced = False
        self.reason = ""

    # ---------- 判定 ----------
    def evaluate(self) -> bool:
        """返回 True = 可写；False = 应拒绝。不在此处 exit。"""
        self.disk_version = read_version(self.out_path)
        if self.disk_version is None:
            # 盘上无此产物（首次落盘）⇒ 放行
            self.reason = "盘上无产物，首次落盘，放行"
            self.blocked = False
            return True
        d_disk = parse_version(self.disk_version)
        d_target = parse_version(self.target)
        if d_disk > d_target:
            self.blocked = True
            self.reason = (f"磁盘版本 {self.disk_version} 高于脚本目标 {self.target}"
                           f" ⇒ 判「有他人已升版」⇒ 拒绝覆盖")
            return False
        self.reason = (f"磁盘版本 {self.disk_version} ≤ 目标 {self.target} ⇒ 放行"
                       + ("（幂等重跑）" if d_disk == d_target else "（正常升版）"))
        self.blocked = False
        return True

    # ---------- 留痕 ----------
    def _log_force(self) -> str:
        """把旁路动作写入留痕文件；返回留痕路径（失败则返回说明文本）。"""
        path = self.log_path
        if not path:
            path = os.path.join(os.path.dirname(os.path.abspath(self.out_path)),
                                "..", "..", "reports", "force_overwrite_log.jsonl")
        path = os.path.abspath(path)
        rec = {
            "at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "action": "force_overwrite",
            "doc_id": self.doc_id,
            "unit": self.unit,
            "out_path": self.out_path,
            "disk_version_overwritten": self.disk_version,
            "script_target_version": self.target,
            "note": "Q64 §② 旁路留痕：显式 --force 覆盖了磁盘上更高版本的产物",
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return path
        except OSError as e:
            return f"（留痕写入失败：{e}）"

    # ---------- 对外入口 ----------
    def check(self, force: bool = False) -> bool:
        """判定 + 旁路 + 留痕。返回 True = 可写。

        调用方**必须**在返回 False 时以非 0 退出码中止（推荐 exit 2）。
        """
        ok = self.evaluate()
        if ok:
            print(f"[version-guard] {self.doc_id or '产物'} {self.unit or ''}：{self.reason}")
            return True
        if force:
            self.forced = True
            log = self._log_force()
            print("!" * 78)
            print(f"[version-guard] ⚠️ --force 旁路放行：{self.reason}")
            print(f"[version-guard]   目标文件：{self.out_path}")
            print(f"[version-guard]   被覆盖的磁盘版本：{self.disk_version} → 本次写入：{self.target}")
            print(f"[version-guard]   留痕：{log}")
            print("!" * 78)
            return True
        print("!" * 78)
        print(f"[version-guard] ❌ 拒绝写入：{self.reason}")
        print(f"[version-guard]   目标文件：{self.out_path}")
        print(f"[version-guard]   若确需覆盖更高版本，请显式加 --force（旁路会留痕）。")
        print("!" * 78)
        return False
