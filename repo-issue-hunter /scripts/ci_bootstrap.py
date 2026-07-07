#!/usr/bin/env python3
"""Phase 0：初始化并读取 .ci 文件夹，输出当前状态。

- .ci 不存在则创建骨架（README / config 模板 / graph、issues 子目录）。
- 已存在则只读，不覆盖任何数据。
- 以 JSON 打印：仓库、是否已建图、已创建 issue 列表（类型/标题/编号/URL）。

供 Skill 在触发时第一步运行，建立“已知状态”基线。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cihelpers import (  # noqa: E402
    ci_paths, detect_repo, git_head, load_records, now_iso, repo_root,
)

README_TEXT = """# .ci — repo-issue-hunter 状态存储

本文件夹由 repo-issue-hunter Skill 维护，记录：
- `graph/indexed.json`：GitNexus 建图标记（避免重复建图）。
- `issues/created.jsonl`：已创建 issue 的压缩指纹记录（避免重复建单）。

请勿手动编辑 `issues/` 下的记录文件——它是去重的真相来源。
详见 Skill 的 references/ci-folder.md。
"""

CONFIG_TEMPLATE = {
    "repo": None,                 # 覆盖自动识别的 owner/repo；null 表示自动
    "labels": {"bug": ["bug"], "feature": ["enhancement"]},
    "max_issues_per_run": 5,
}


def ensure_scaffold(paths: dict) -> bool:
    """确保 .ci 骨架存在。返回是否为本次新建。"""
    created = not os.path.exists(paths["ci"])
    os.makedirs(paths["graph_dir"], exist_ok=True)
    os.makedirs(paths["issues_dir"], exist_ok=True)
    if not os.path.exists(paths["readme"]):
        with open(paths["readme"], "w", encoding="utf-8") as f:
            f.write(README_TEXT)
    if not os.path.exists(paths["config"]):
        with open(paths["config"], "w", encoding="utf-8") as f:
            json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=2)
    return created


def read_graph_marker(paths: dict) -> dict | None:
    if not os.path.exists(paths["graph_marker"]):
        return None
    try:
        with open(paths["graph_marker"], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main() -> int:
    root = repo_root()
    paths = ci_paths(root)
    newly_created = ensure_scaffold(paths)

    records = load_records(root)
    marker = read_graph_marker(paths)
    head = git_head(root)

    state = {
        "repo_root": root,
        "repo": detect_repo(root),
        "ci_ready": True,
        "ci_newly_created": newly_created,
        "checked_at": now_iso(),
        "graph": {
            "indexed": marker is not None,
            "indexed_head": (marker or {}).get("head"),
            "current_head": head,
            "fresh": bool(marker and head and marker.get("head") == head),
        },
        "created_issues": [
            {
                "type": r.get("type"),
                "title": r.get("title"),
                "number": r.get("number"),
                "url": r.get("url"),
            }
            for r in records
        ],
        "created_count": len(records),
    }
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
