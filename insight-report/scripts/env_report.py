"""
记录本次生成报告所用的 PDF 渲染环境：渲染器/依赖版本 + 字体可用性 + pdftoppm 版本。

对应「固定并记录 PDF 渲染器、字体和依赖版本」的要求——固定靠 requirements.txt 里的
精确版本号，记录靠这个脚本：每次生成报告前跑一遍，把实际装的版本和 requirements.txt
里锁的版本对比，不一致就提醒；同时探测中文字体和 pdftoppm 是否可用，缺了当场说清楚，
而不是等渲染出乱码/黑块才去查。

用法：
  python3 scripts/env_report.py                     # 打印到 stdout
  python3 scripts/env_report.py --append-log .report-env.log   # 同时追加一条记录到日志
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS_PATH = os.path.join(SKILL_DIR, "requirements.txt")

# CSS 里声明的字体回退链（见 assets/report.css），按优先级探测
FONT_CANDIDATES = [
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Noto Serif CJK SC",
    "Noto Serif CJK JP",
    "PingFang SC",
    "Microsoft YaHei",
    "WenQuanYi Micro Hei",
]

PINNED_PACKAGES = ["markdown", "weasyprint", "pydyf", "pdfplumber", "pypdf"]


def read_pinned_versions() -> dict[str, str]:
    pinned: dict[str, str] = {}
    if not os.path.exists(REQUIREMENTS_PATH):
        return pinned
    with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "==" not in line:
                continue
            name, _, version = line.partition("==")
            pinned[name.strip().lower()] = version.strip()
    return pinned


def installed_versions() -> dict[str, str]:
    installed: dict[str, str] = {}
    for name in PINNED_PACKAGES:
        try:
            mod = __import__(name)
            installed[name] = getattr(mod, "__version__", "unknown")
        except Exception as e:  # noqa: BLE001
            installed[name] = f"NOT INSTALLED ({e})"
    return installed


def check_version_drift(pinned: dict[str, str], installed: dict[str, str]) -> list[str]:
    warnings = []
    for name in PINNED_PACKAGES:
        want = pinned.get(name.lower())
        have = installed.get(name)
        if want and have and want != have and not str(have).startswith("NOT INSTALLED"):
            warnings.append(f"{name}: requirements.txt 锁定 {want}，实际装的是 {have}")
        if have and str(have).startswith("NOT INSTALLED"):
            warnings.append(f"{name}: 未安装 —— pip install -r requirements.txt")
    return warnings


def check_fonts() -> dict[str, bool]:
    fc_list = shutil.which("fc-list")
    if not fc_list:
        return {}
    try:
        out = subprocess.run([fc_list], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return {}
    found = {}
    low = out.lower()
    for name in FONT_CANDIDATES:
        found[name] = name.lower() in low
    return found


def check_pdftoppm() -> str | None:
    path = shutil.which("pdftoppm")
    if not path:
        return None
    try:
        out = subprocess.run(["pdftoppm", "-v"], capture_output=True, text=True, timeout=10)
        # pdftoppm -v 把版本打在 stderr，格式类似 "pdftoppm version 24.02.0"
        text = (out.stderr or out.stdout or "").splitlines()
        return text[0] if text else "installed (version unknown)"
    except Exception as e:  # noqa: BLE001
        return f"installed but 'pdftoppm -v' failed: {e}"


def main() -> int:
    p = argparse.ArgumentParser(description="记录 PDF 渲染环境（版本 + 字体 + pdftoppm）")
    p.add_argument("--append-log", default=None, help="追加一条 JSON 行到这个日志文件")
    args = p.parse_args()

    pinned = read_pinned_versions()
    installed = installed_versions()
    drift = check_version_drift(pinned, installed)
    fonts = check_fonts()
    pdftoppm_version = check_pdftoppm()

    record = {
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "renderer": "weasyprint",
        "pinned_versions": pinned,
        "installed_versions": installed,
        "version_drift": drift,
        "fonts_found": fonts,
        "pdftoppm": pdftoppm_version,
    }

    print(json.dumps(record, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60, file=sys.stderr)
    if drift:
        print("[版本漂移] 以下依赖和 requirements.txt 锁定的版本不一致：", file=sys.stderr)
        for w in drift:
            print(f"  - {w}", file=sys.stderr)
    else:
        print("[版本] 全部依赖与 requirements.txt 锁定版本一致。", file=sys.stderr)

    if fonts:
        missing_fonts = [k for k, v in fonts.items() if not v]
        if len(missing_fonts) == len(fonts):
            print(
                "[字体][警告] CSS 声明的中文字体一个都没探测到，中文很可能渲染成方块/乱码，"
                "生成报告前先装字体。", file=sys.stderr,
            )
        elif missing_fonts:
            print(f"[字体] 缺失: {missing_fonts}（回退链里的其他字体仍可用，但建议装全）", file=sys.stderr)
        else:
            print("[字体] CSS 声明的中文字体全部可用。", file=sys.stderr)
    else:
        print("[字体][警告] 没有 fc-list，无法探测字体是否安装，生成后务必用 pdftoppm 渲染图肉眼核对中文是否正常显示。", file=sys.stderr)

    if pdftoppm_version:
        print(f"[pdftoppm] {pdftoppm_version}", file=sys.stderr)
    else:
        print("[pdftoppm][警告] 未安装，无法做 Step 7 的整页渲染视觉核查，见 references/report-spec.md 安装指引。", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if args.append_log:
        with open(args.append_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[已追加日志] {args.append_log}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
