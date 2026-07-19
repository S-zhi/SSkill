"""
认知报告 PDF 排版回归测试。

对 tests/fixtures/ 下的每个样例跑一遍「Markdown -> build_pdf -> verify_pdf」，
覆盖文本较短、文本较长、长链接、连续英文、两页分页共 5 类场景（对应文件名前缀
01~05）。任一样例未通过 verify_pdf 的检查，整体判定 FAIL——这是 CSS/report-spec
改动后必须先跑绿、再交付真实报告的最后一道回归闸门。

用法：
  python3 scripts/run_regression.py                     # 用默认 CSS 跑全部样例
  python3 scripts/run_regression.py --css other.css     # 改动 CSS 后先在这里回归
  python3 scripts/run_regression.py --keep-output out/  # 保留生成的 PDF/JSON 供人工复查

退出码：0 = 全部样例通过；1 = 至少一个样例未通过。
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pdf  # noqa: E402
import verify_pdf  # noqa: E402

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(SKILL_DIR, "tests", "fixtures")
DEFAULT_CSS = os.path.join(SKILL_DIR, "assets", "report.css")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="认知报告 PDF 排版回归测试")
    p.add_argument("--css", default=DEFAULT_CSS, help="要回归验证的 CSS（默认 assets/report.css）")
    p.add_argument("--fixtures-dir", default=FIXTURES_DIR)
    p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--min-font-pt", type=float, default=9.5)
    p.add_argument("--min-line-ratio", type=float, default=1.45)
    p.add_argument(
        "--keep-output", nargs="?", const="__auto__", default=None,
        help="保留生成的 PDF/JSON；不给路径则用临时目录（会打印路径）",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    fixtures = sorted(glob.glob(os.path.join(args.fixtures_dir, "*.md")))
    if not fixtures:
        print(f"[错误] 没有在 {args.fixtures_dir} 找到任何 .md 样例", file=sys.stderr)
        return 1

    if args.keep_output:
        outdir = args.keep_output if args.keep_output != "__auto__" else tempfile.mkdtemp(prefix="insight-report-regression-")
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = tempfile.mkdtemp(prefix="insight-report-regression-")

    rows: list[tuple[str, bool, str]] = []

    for md_path in fixtures:
        name = os.path.splitext(os.path.basename(md_path))[0]
        pdf_path = os.path.join(outdir, f"{name}.pdf")
        json_path = os.path.join(outdir, f"{name}.verify.json")

        try:
            build_pdf.md_to_pdf(md_path, pdf_path, args.css)
        except Exception as e:  # noqa: BLE001
            rows.append((name, False, f"构建失败: {e}"))
            continue

        report = verify_pdf.run(
            pdf_path,
            md_path,
            max_pages=args.max_pages,
            min_font_pt=args.min_font_pt,
            min_line_ratio=args.min_line_ratio,
            overlap_area_ratio=0.15,
            bounds_tolerance=0.75,
        )
        with open(json_path, "w", encoding="utf-8") as f:
            import json as _json
            from dataclasses import asdict
            f.write(_json.dumps(asdict(report), ensure_ascii=False, indent=2))

        if report.passed:
            reason = f"pages={report.page_count}"
        else:
            fails = [i["message"] for i in report.issues if i["severity"] == "fail"]
            reason = "; ".join(fails[:3]) + (f"（共 {len(fails)} 项）" if len(fails) > 3 else "")
        rows.append((name, report.passed, reason))

    width = max(len(r[0]) for r in rows) + 2
    print(f"{'样例'.ljust(width)}结果   详情")
    print("-" * 70)
    all_ok = True
    for name, ok, reason in rows:
        all_ok = all_ok and ok
        print(f"{name.ljust(width)}{'PASS' if ok else 'FAIL'}   {reason}")
    print("-" * 70)
    print(f"输出目录: {outdir}")
    print("全部通过" if all_ok else "存在未通过的样例 —— 在这些修好之前，不要拿改动后的 CSS/spec 去生成真实报告")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
