#!/usr/bin/env python3
"""计算 issue 指纹，并可选地在本地 .ci 记录里查重。

用法：
  python fingerprint.py --title "【Bug Request】…"
  python fingerprint.py --title "…" --body-file /tmp/issue.md --check
  python fingerprint.py --title "…" --check      # 只看是否已建过

--check 时若命中本地记录，退出码为 3（方便脚本判断）；未命中为 0。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cihelpers import fingerprint, find_duplicate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="compute issue fingerprint / check dedup")
    ap.add_argument("--title", required=True)
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--check", action="store_true", help="check against local .ci records")
    args = ap.parse_args()

    body = args.body or ""
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()

    fp = fingerprint(args.title, body)
    result = {"fingerprint": fp}

    if args.check:
        dup = find_duplicate(args.title, body)
        result["duplicate"] = dup is not None
        result["match"] = dup
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if dup else 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
