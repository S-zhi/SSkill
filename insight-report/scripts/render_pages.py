"""
用 pdftoppm 把 PDF 的每一页渲染成 PNG，供人（Claude）逐页肉眼核查。

结构性检查（overlap/out_of_page/空页/ASR 完整性）交给 verify_pdf.py；
这个脚本只负责"生成图"——覆盖、裁切、黑块、乱码、表格断裂这类"看一眼就知道"但
脚本很难可靠判定的问题，必须由渲染出的图片人工核查，不能省略这一步。

用法：
  python3 scripts/render_pages.py report.pdf                    # 输出到 ./render/
  python3 scripts/render_pages.py report.pdf --outdir /tmp/x --dpi 150

退出码：0 = 渲染成功（不代表视觉核查通过，核查仍要人做）；
        2 = pdftoppm 不存在或渲染失败；3 = 生成的图片数量和 PDF 实际页数对不上。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

INSTALL_HINT = """\
[错误] 找不到 pdftoppm（属于 poppler-utils / poppler，是渲染 PDF 页面为图片必需的工具）。

按你的操作系统安装：
  macOS   : brew install poppler
  Linux   : sudo apt install -y poppler-utils   # Debian/Ubuntu
            sudo dnf install -y poppler-utils   # Fedora/RHEL
            sudo pacman -S poppler              # Arch
  Windows : winget install --id oschwartz10612.Poppler
            # 或 choco install poppler
            # 或从 https://github.com/oschwartz10612/poppler-windows/releases 下载后把 bin/ 加入 PATH

装完用 `pdftoppm -v` 验证，再重跑本脚本。这一步不能跳过——Step 7 的整页视觉核查
（覆盖/裁切/黑块/乱码/表格断裂）依赖这里生成的图片，没有图就没法做视觉核查，
也就不满足交付前必须全过的检查闸门。
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="用 pdftoppm 把 PDF 逐页渲染为 PNG")
    p.add_argument("pdf_path")
    p.add_argument("--outdir", default="render", help="输出目录（默认 ./render）")
    p.add_argument("--dpi", type=int, default=150, help="渲染分辨率（默认 150，足够肉眼核查用）")
    p.add_argument("--prefix", default="page", help="输出文件名前缀（默认 page，产出 page-1.png ...）")
    return p.parse_args()


def expected_page_count(pdf_path: str) -> int | None:
    try:
        import pypdf

        return len(pypdf.PdfReader(pdf_path).pages)
    except Exception:
        return None


def main() -> int:
    args = parse_args()

    if not shutil.which("pdftoppm"):
        print(INSTALL_HINT, file=sys.stderr)
        return 2

    if not os.path.exists(args.pdf_path):
        print(f"[错误] 文件不存在: {args.pdf_path}", file=sys.stderr)
        return 2

    os.makedirs(args.outdir, exist_ok=True)
    out_prefix = os.path.join(args.outdir, args.prefix)

    cmd = ["pdftoppm", "-r", str(args.dpi), "-png", args.pdf_path, out_prefix]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[错误] pdftoppm 渲染失败: {result.stderr.strip()}", file=sys.stderr)
        return 2

    produced = sorted(
        f for f in os.listdir(args.outdir)
        if f.startswith(args.prefix) and f.endswith(".png")
    )
    if not produced:
        print("[错误] pdftoppm 没有报错，但没有产出任何 PNG，排查 PDF 是否损坏", file=sys.stderr)
        return 2

    expected = expected_page_count(args.pdf_path)
    if expected is not None and len(produced) != expected:
        print(
            f"[错误] 渲染出 {len(produced)} 张图，但 PDF 实际有 {expected} 页，数量对不上，"
            "先查是不是有页面渲染失败/被跳过",
            file=sys.stderr,
        )
        return 3

    print(f"渲染完成，共 {len(produced)} 张图，输出目录: {args.outdir}")
    for name in produced:
        print(f"  - {os.path.join(args.outdir, name)}")
    print(
        "\n接下来必须逐张用 Read 工具查看这些图片，肉眼核查：文字/区块有没有互相覆盖、"
        "有没有被裁切、有没有异常黑块、中文有没有变成方块/乱码、表格有没有被断成两半。"
        "任何一张有问题都不能交付，回去改 report.md / report.css 再重新走一遍构建+质检。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
