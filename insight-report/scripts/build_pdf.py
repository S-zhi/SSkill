"""
把认知报告 Markdown 转成 1~2 页的 PDF。

流程：Markdown --(python-markdown)--> HTML --(weasyprint + report.css)--> PDF

用法：
  python build_pdf.py report.md report.pdf
  python build_pdf.py report.md report.pdf --css /path/to/report.css

依赖：pip install markdown weasyprint
系统需安装 Noto Sans/Serif CJK 字体（大多数 Claude 环境已自带）。
"""

import argparse
import os
import sys

import markdown
from weasyprint import HTML

DEFAULT_CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "report.css")

HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><style>{css}</style></head>
<body>{body}</body>
</html>"""


def md_to_pdf(md_path: str, pdf_path: str, css_path: str) -> None:
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # 保留原始 HTML（评级方块等），支持表格、围栏引用、软换行
    body = markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists", "nl2br", "tables"],
    )

    css = ""
    if css_path and os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
    else:
        print(f"[警告] 未找到 CSS: {css_path}，使用无样式输出", file=sys.stderr)

    html = HTML_SHELL.format(css=css, body=body)
    HTML(string=html).write_pdf(pdf_path)
    print(f"[完成] PDF 已生成: {pdf_path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="认知报告 Markdown -> PDF")
    p.add_argument("md_path", help="输入 Markdown 文件")
    p.add_argument("pdf_path", help="输出 PDF 文件")
    p.add_argument("--css", default=DEFAULT_CSS, help="CSS 样式文件路径")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    md_to_pdf(args.md_path, args.pdf_path, args.css)
