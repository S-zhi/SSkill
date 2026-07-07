"""repo-issue-hunter 共享工具函数。

提供：仓库根目录 / .ci 路径定位、GitHub 仓库识别、issue 指纹计算、
去重记录的读取与追加。所有脚本共用，一般不单独调用。

只依赖标准库，行为幂等，绝不删除或覆盖已有数据（记录只追加）。
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from datetime import datetime, timezone


# ----------------------------------------------------------------------------
# 路径定位
# ----------------------------------------------------------------------------

def repo_root(start: str | None = None) -> str:
    """返回 git 仓库根目录；不在 git 仓库里则回退到当前目录。"""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start or os.getcwd(),
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return os.path.abspath(start or os.getcwd())


def ci_paths(root: str | None = None) -> dict:
    """返回 .ci 下各关键路径。不创建目录，仅计算路径。"""
    r = root or repo_root()
    ci = os.path.join(r, ".ci")
    return {
        "root": r,
        "ci": ci,
        "readme": os.path.join(ci, "README.md"),
        "config": os.path.join(ci, "config.json"),
        "graph_dir": os.path.join(ci, "graph"),
        "graph_marker": os.path.join(ci, "graph", "indexed.json"),
        "issues_dir": os.path.join(ci, "issues"),
        "created": os.path.join(ci, "issues", "created.jsonl"),
        "created_gz": os.path.join(ci, "issues", "created.jsonl.gz"),
    }


# ----------------------------------------------------------------------------
# GitHub 仓库识别
# ----------------------------------------------------------------------------

def detect_repo(root: str | None = None) -> str | None:
    """从 origin remote 解析 'owner/repo'，识别不出返回 None。"""
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root or repo_root(),
            capture_output=True, text=True, check=True,
        )
        url = out.stdout.strip()
    except Exception:
        return None
    # git@github.com:owner/repo.git  或  https://github.com/owner/repo(.git)
    m = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


# ----------------------------------------------------------------------------
# 指纹（去重核心）
# ----------------------------------------------------------------------------

_TAG_PREFIX = re.compile(r"^\s*【[^】]*】\s*")


def normalize_text(s: str) -> str:
    """归一化：去【】前缀、小写、去标点、压缩空白。保留 CJK 与字母数字。"""
    if not s:
        return ""
    s = _TAG_PREFIX.sub("", s)
    s = unicodedata.normalize("NFKC", s).lower()
    # 去掉标点/符号，保留字母数字与 CJK；其余转空格
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def fingerprint(title: str, body: str = "") -> str:
    """对标题(+可选正文)计算稳定指纹，取 sha256 前 16 位十六进制。

    默认只用标题——标题是 issue 的语义主键，正文改动不应破坏去重。
    传入 body 时把正文的归一化文本一并纳入，作为更严格的指纹。
    """
    basis = normalize_text(title)
    if body:
        basis += "\n" + normalize_text(body)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------------
# 去重记录读写
# ----------------------------------------------------------------------------

def load_records(root: str | None = None) -> list[dict]:
    """读取已创建 issue 的压缩记录；优先 jsonl，退回 .gz。缺失返回空列表。"""
    p = ci_paths(root)
    path, opener = None, open
    if os.path.exists(p["created"]):
        path, opener = p["created"], open
    elif os.path.exists(p["created_gz"]):
        path, opener = p["created_gz"], gzip.open

    if not path:
        return []

    records: list[dict] = []
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # 容错：跳过损坏行而非整体失败
                continue
    return records


def find_duplicate(title: str, body: str = "", root: str | None = None) -> dict | None:
    """按指纹在本地记录里查重，命中返回该记录，否则 None。"""
    fp = fingerprint(title, body)
    for rec in load_records(root):
        if rec.get("fp") == fp:
            return rec
    return None


def append_record(rec: dict, root: str | None = None, gzip_snapshot: bool = False) -> None:
    """把一条压缩记录追加到 created.jsonl（原子性以“追加单行”保证）。"""
    p = ci_paths(root)
    os.makedirs(p["issues_dir"], exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False)
    with open(p["created"], "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    if gzip_snapshot:
        _sync_gzip(root)


def _sync_gzip(root: str | None = None) -> None:
    """把 created.jsonl 完整快照写入 created.jsonl.gz。"""
    p = ci_paths(root)
    if not os.path.exists(p["created"]):
        return
    with open(p["created"], "rb") as src, gzip.open(p["created_gz"], "wb") as dst:
        dst.writelines(src)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_head(root: str | None = None) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root or repo_root(),
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None
