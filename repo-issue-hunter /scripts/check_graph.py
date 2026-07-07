#!/usr/bin/env python3
"""Phase 1：判断 GitNexus 图谱是否需要重建，或在建图后写入标记。

用法：
  python check_graph.py           # 判断：输出 skip / rebuild + 原因
  python check_graph.py --mark    # 建图成功后调用：把当前 HEAD 写入标记

判断逻辑：
  - 无标记            -> rebuild（从没建过）
  - 标记 head == HEAD -> skip（图谱新鲜，直接复用）
  - 标记 head != HEAD -> rebuild（代码变了，图谱可能过期）
本脚本自己不运行 gitnexus；建图由 Skill 执行 `npx gitnexus analyze`。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cihelpers import ci_paths, git_head, now_iso, repo_root  # noqa: E402


def gitnexus_installed() -> bool:
    """gitnexus 是否可用：全局命令在 PATH，或本机有 npx 可临时拉起。"""
    if shutil.which("gitnexus"):
        return True
    # 有 npx 时可 `npx gitnexus`，视为可用（首次会联网下载）
    return bool(shutil.which("npx"))


def gitnexus_version() -> str:
    for args in (["gitnexus", "--version"], ["npx", "gitnexus", "--version"]):
        try:
            out = subprocess.run(args, capture_output=True, text=True, timeout=20)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip().splitlines()[0]
        except Exception:
            continue
    return "unknown"


def read_marker(paths: dict) -> dict | None:
    if not os.path.exists(paths["graph_marker"]):
        return None
    try:
        with open(paths["graph_marker"], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def do_mark(root: str, paths: dict) -> int:
    os.makedirs(paths["graph_dir"], exist_ok=True)
    marker = {
        "head": git_head(root),
        "indexed_at": now_iso(),
        "gitnexus_version": gitnexus_version(),
    }
    with open(paths["graph_marker"], "w", encoding="utf-8") as f:
        json.dump(marker, f, ensure_ascii=False, indent=2)
    print(json.dumps({"action": "marked", "marker": marker}, ensure_ascii=False, indent=2))
    return 0


def do_check(root: str, paths: dict) -> int:
    marker = read_marker(paths)
    head = git_head(root)
    if marker is None:
        decision, reason = "rebuild", "no existing graph marker"
    elif head and marker.get("head") == head:
        decision, reason = "skip", "graph is fresh (HEAD unchanged since last index)"
    else:
        decision, reason = "rebuild", "HEAD changed since last index; graph may be stale"
    installed = gitnexus_installed()
    out = {
        "decision": decision,
        "reason": reason,
        "marker_head": (marker or {}).get("head"),
        "current_head": head,
        "gitnexus_installed": installed,
    }
    if not installed:
        out["hint"] = "gitnexus/npx not found — see references/setup-gitnexus.md to install, or use the fallback"
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    root = repo_root()
    paths = ci_paths(root)
    if "--mark" in sys.argv[1:]:
        return do_mark(root, paths)
    return do_check(root, paths)


if __name__ == "__main__":
    raise SystemExit(main())
