#!/usr/bin/env python3
"""Phase 5/6：用 GitHub 官方接口创建 issue，成功后压缩记录到 .ci。

鉴权优先级：已登录的 `gh` CLI  ->  环境变量 GITHUB_TOKEN 走 REST。
创建前做双重去重：本地 .ci 指纹 + 远端同名 issue 检索。

用法：
  # 空跑：做完所有检查、打印将创建什么，但不调用 API、不写记录
  python create_issue.py --dry-run --type bug \
      --title "【Bug Request】…" --body-file /tmp/issue1.md

  # 真正创建（去掉 --dry-run），需已获用户确认
  python create_issue.py --type feature \
      --title "【Feature】…" --body-file /tmp/issue2.md --label enhancement

参数：
  --type {bug,feature}   决定默认标签（bug->bug, feature->enhancement）
  --title / --body / --body-file
  --repo owner/name      覆盖自动识别的仓库
  --label L              追加标签，可重复
  --dry-run              只检查不创建
  --gzip                 额外产出 created.jsonl.gz 压缩快照

退出码：0 成功创建 / 2 因去重跳过 / 4 鉴权或参数错误 / 5 API 失败。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cihelpers import (  # noqa: E402
    append_record, ci_paths, detect_repo, fingerprint, find_duplicate,
    normalize_text, now_iso, repo_root,
)

DEFAULT_LABELS = {"bug": ["bug"], "feature": ["enhancement"]}
API_ROOT = "https://api.github.com"


# ----------------------------------------------------------------------------
# 输入
# ----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="create a GitHub issue via official API")
    ap.add_argument("--type", choices=["bug", "feature"], required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--repo", help="owner/name; default: auto from origin / .ci config")
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--gzip", action="store_true")
    return ap.parse_args()


def read_body(args) -> str:
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            return f.read()
    return args.body or ""


def resolve_repo(args, root: str) -> str | None:
    if args.repo:
        return args.repo
    # .ci/config.json 覆盖
    cfg = ci_paths(root)["config"]
    if os.path.exists(cfg):
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                r = json.load(f).get("repo")
                if r:
                    return r
        except Exception:
            pass
    return detect_repo(root)


def resolve_labels(args) -> list[str]:
    labels = list(DEFAULT_LABELS.get(args.type, []))
    for lb in args.label:
        if lb not in labels:
            labels.append(lb)
    return labels


# ----------------------------------------------------------------------------
# 鉴权探测
# ----------------------------------------------------------------------------

def gh_available() -> bool:
    if not shutil.which("gh"):
        return False
    try:
        return subprocess.run(["gh", "auth", "status"],
                              capture_output=True, text=True).returncode == 0
    except Exception:
        return False


def token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


# ----------------------------------------------------------------------------
# 远端去重
# ----------------------------------------------------------------------------

def remote_duplicate(repo: str, title: str, use_gh: bool) -> dict | None:
    """检索远端是否已有同名 issue（open/closed）。查不动就返回 None（不阻塞）。"""
    norm = normalize_text(title)
    if use_gh:
        try:
            out = subprocess.run(
                ["gh", "issue", "list", "--repo", repo, "--state", "all",
                 "--search", f"in:title {title}", "--json", "number,title,url", "--limit", "20"],
                capture_output=True, text=True, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                for it in json.loads(out.stdout):
                    if normalize_text(it.get("title", "")) == norm:
                        return {"number": it.get("number"), "url": it.get("url"),
                                "title": it.get("title")}
        except Exception:
            return None
        return None
    # REST 检索
    tk = token()
    if not tk:
        return None
    q = f'repo:{repo} in:title type:issue "{title}"'
    url = f"{API_ROOT}/search/issues?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers=_rest_headers(tk))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for it in data.get("items", []):
            if normalize_text(it.get("title", "")) == norm:
                return {"number": it.get("number"), "url": it.get("html_url"),
                        "title": it.get("title")}
    except Exception:
        return None
    return None


# ----------------------------------------------------------------------------
# 创建
# ----------------------------------------------------------------------------

def _rest_headers(tk: str) -> dict:
    return {
        "Authorization": f"Bearer {tk}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-issue-hunter",
        "Content-Type": "application/json",
    }


def create_via_gh(repo: str, title: str, body: str, labels: list[str]) -> dict:
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for lb in labels:
        cmd += ["--label", lb]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {out.stderr.strip() or out.stdout.strip()}")
    url = out.stdout.strip().splitlines()[-1].strip()
    number = None
    if "/issues/" in url:
        try:
            number = int(url.rsplit("/", 1)[-1])
        except ValueError:
            number = None
    return {"number": number, "url": url}


def create_via_rest(repo: str, title: str, body: str, labels: list[str]) -> dict:
    tk = token()
    if not tk:
        raise RuntimeError("no GITHUB_TOKEN and gh not available")
    url = f"{API_ROOT}/repos/{repo}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": labels}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=_rest_headers(tk), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"REST create failed: HTTP {e.code} {detail}") from e
    return {"number": data.get("number"), "url": data.get("html_url")}


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    root = repo_root()
    body = read_body(args)
    repo = resolve_repo(args, root)
    labels = resolve_labels(args)
    fp = fingerprint(args.title)
    use_gh = gh_available()
    have_auth = use_gh or bool(token())

    plan = {
        "repo": repo,
        "type": args.type,
        "title": args.title,
        "labels": labels,
        "fingerprint": fp,
        "auth": "gh" if use_gh else ("token" if token() else None),
        "body_preview": (body[:400] + ("…" if len(body) > 400 else "")),
    }

    if not repo:
        plan["error"] = "cannot resolve repo (no origin remote); pass --repo owner/name"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 4

    # 去重（本地 + 远端）
    local_dup = find_duplicate(args.title)
    plan["local_duplicate"] = local_dup
    remote_dup = remote_duplicate(repo, args.title, use_gh) if have_auth else None
    plan["remote_duplicate"] = remote_dup

    if local_dup or remote_dup:
        plan["result"] = "skipped_duplicate"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 2

    if args.dry_run:
        plan["result"] = "dry_run_ok" if have_auth else "dry_run_no_auth"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if have_auth else 4

    if not have_auth:
        plan["error"] = "no auth: run `gh auth login` or set GITHUB_TOKEN"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 4

    # 真正创建
    try:
        created = create_via_gh(repo, args.title, body, labels) if use_gh \
            else create_via_rest(repo, args.title, body, labels)
    except Exception as e:
        plan["result"] = "api_error"
        plan["error"] = str(e)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 5

    # 压缩记录到 .ci（幂等：追加一行指纹记录）
    rec = {
        "fp": fp,
        "type": args.type,
        "title": args.title,
        "number": created.get("number"),
        "url": created.get("url"),
        "at": now_iso(),
    }
    append_record(rec, root=root, gzip_snapshot=args.gzip)

    plan["result"] = "created"
    plan["issue"] = {"number": created.get("number"), "url": created.get("url")}
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
