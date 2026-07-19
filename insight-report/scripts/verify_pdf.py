"""
认知报告 PDF 质检脚本：交付前的最后一道闸门。

三类检查，任一失败整体判定 FAIL：
  1. 结构检查（pypdf）    —— 页数在 [1, --max-pages]、没有空页、report.md 里的 ASR 摘录
                              （<div class="excerpt">…</div>）逐条完整出现在 PDF 文本里，
                              没有被截断/丢字。
  2. 版面检查（pdfplumber）—— 统计 overlap（文字块两两边界框相交，判定为视觉重叠）与
                              out_of_page（文字跑出页面可打印区域）；顺带核对最小字号是否
                              达标（默认 9.5pt），并对行距过密（< 1.45x 字号）做提示。
  3. 环境记录             —— 打印本次用的 PDF 渲染器（WeasyPrint）与关键依赖版本，写进
                              JSON 报告，方便复现问题时对齐环境（配合 env_report.py）。

用法：
  python3 verify_pdf.py report.pdf --md report.md
  python3 verify_pdf.py report.pdf --md report.md --max-pages 2 --min-font-pt 9.5 \
      --json report_verify.json

退出码：0 = 全部通过，可以交付；1 = 有检查失败，禁止交付；2 = 脚本自身出错（文件不存在等）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any


# ----------------------------------------------------------------------------
# 数据结构
# ----------------------------------------------------------------------------

@dataclass
class Issue:
    check: str
    severity: str  # "fail" | "warn"
    message: str
    page: int | None = None


@dataclass
class Report:
    pdf_path: str
    page_count: int = 0
    overlap: int = 0
    out_of_page: int = 0
    empty_pages: list[int] = field(default_factory=list)
    min_font_pt_found: float | None = None
    tight_line_spacing: int = 0
    asr_excerpts_total: int = 0
    asr_excerpts_missing: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    passed: bool = False

    def add(self, check: str, severity: str, message: str, page: int | None = None) -> None:
        self.issues.append(asdict(Issue(check, severity, message, page)))


# ----------------------------------------------------------------------------
# 版本记录（对应「固定并记录渲染器/字体/依赖版本」的记录部分，固定见 env_report.py）
# ----------------------------------------------------------------------------

def collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for mod_name, attr in (
        ("weasyprint", "__version__"),
        ("markdown", "__version__"),
        ("pdfplumber", "__version__"),
        ("pypdf", "__version__"),
    ):
        try:
            mod = __import__(mod_name)
            versions[mod_name] = getattr(mod, attr, "unknown")
        except Exception as e:  # noqa: BLE001
            versions[mod_name] = f"NOT INSTALLED ({e})"
    return versions


# ----------------------------------------------------------------------------
# 1. 结构检查（pypdf）
# ----------------------------------------------------------------------------

def extract_excerpts_from_md(md_text: str) -> list[str]:
    """抽出所有 <div class="excerpt">…</div> 块的纯文本，做完整性比对用。"""
    blocks = re.findall(
        r'<div\s+class="excerpt"\s*>(.*?)</div>', md_text, flags=re.S | re.I
    )
    return [normalize_text(b) for b in blocks if normalize_text(b)]


def normalize_text(text: str) -> str:
    # 去标签、去多余空白，中英文之间的换行/空格差异不应影响比对
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def check_structure(pdf_path: str, md_text: str | None, max_pages: int, report: Report) -> None:
    import pypdf

    reader = pypdf.PdfReader(pdf_path)
    report.page_count = len(reader.pages)

    if report.page_count < 1:
        report.add("structure", "fail", "PDF 页数为 0")
    elif report.page_count > max_pages:
        report.add(
            "structure", "fail",
            f"页数 {report.page_count} 超过上限 {max_pages}；"
            "不允许为了塞进页数上限继续压缩字号/行距，应精简正文内容",
        )

    full_text_parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        full_text_parts.append(text)
        if len(re.sub(r"\s+", "", text)) < 20:
            report.empty_pages.append(i)
            report.add("structure", "fail", "空页（可提取文本 < 20 个非空白字符）", page=i)

    if md_text is None:
        return

    full_text_norm = normalize_text("".join(full_text_parts))
    excerpts = extract_excerpts_from_md(md_text)
    report.asr_excerpts_total = len(excerpts)
    for idx, excerpt in enumerate(excerpts, start=1):
        # 用一个足够长的窗口做子串匹配；ASR 摘录本就应逐字保留，不做模糊匹配
        if excerpt not in full_text_norm:
            report.asr_excerpts_missing += 1
            report.add(
                "asr_completeness", "fail",
                f"第 {idx} 段 ASR 摘录未在 PDF 文本中完整找到（可能被截断/丢字/跨页断裂）",
            )


# ----------------------------------------------------------------------------
# 2. 版面检查（pdfplumber）
# ----------------------------------------------------------------------------

def _rects_overlap_area(a: dict, b: dict) -> float:
    """两个 {x0,x1,top,bottom} 矩形的相交面积，不相交返回 0。"""
    ix0 = max(a["x0"], b["x0"])
    ix1 = min(a["x1"], b["x1"])
    iy0 = max(a["top"], b["top"])
    iy1 = min(a["bottom"], b["bottom"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def check_layout(
    pdf_path: str,
    report: Report,
    min_font_pt: float,
    min_line_ratio: float,
    overlap_area_ratio: float,
    bounds_tolerance: float,
) -> None:
    import pdfplumber

    min_size_seen: float | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            chars = page.chars
            if not chars:
                continue

            # -- 最小字号 --
            page_min = min(c["size"] for c in chars)
            min_size_seen = page_min if min_size_seen is None else min(min_size_seen, page_min)
            undersized = [c for c in chars if c["size"] < min_font_pt - 0.05]
            if undersized:
                sizes = sorted({round(c["size"], 2) for c in undersized})
                report.add(
                    "min_font", "fail",
                    f"存在字号小于 {min_font_pt}pt 的文字，实际出现 {sizes}",
                    page=page_no,
                )

            # -- 越界（out_of_page）：允许极小的浮点误差 --
            for c in chars:
                if (
                    c["x0"] < -bounds_tolerance
                    or c["x1"] > page.width + bounds_tolerance
                    or c["top"] < -bounds_tolerance
                    or c["bottom"] > page.height + bounds_tolerance
                ):
                    report.out_of_page += 1
            if any(
                c["x0"] < -bounds_tolerance
                or c["x1"] > page.width + bounds_tolerance
                or c["top"] < -bounds_tolerance
                or c["bottom"] > page.height + bounds_tolerance
                for c in chars
            ):
                report.add("out_of_page", "fail", "存在文字超出页面可打印区域", page=page_no)

            # -- 重叠（overlap）：word 级别两两比对 --
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            n = len(words)
            page_overlaps = 0
            for i in range(n):
                wi = words[i]
                area_i = max(wi["x1"] - wi["x0"], 0.001) * max(wi["bottom"] - wi["top"], 0.001)
                for j in range(i + 1, n):
                    wj = words[j]
                    inter = _rects_overlap_area(wi, wj)
                    if inter <= 0:
                        continue
                    area_j = max(wj["x1"] - wj["x0"], 0.001) * max(wj["bottom"] - wj["top"], 0.001)
                    smaller = min(area_i, area_j)
                    if smaller > 0 and inter / smaller >= overlap_area_ratio:
                        page_overlaps += 1
                        report.add(
                            "overlap", "fail",
                            f'文字块重叠：「{wi["text"]}」与「{wj["text"]}」',
                            page=page_no,
                        )
            report.overlap += page_overlaps

            # -- 行距过密提示：先把 top 相近（同一视觉行内，字形上边界会有 1~2pt 的自然抖动）
            #    的字符聚成"行"，再比较相邻行的 top 间距 --
            chars_sorted = sorted(chars, key=lambda c: c["top"])
            line_cluster_tol = 2.0  # pt；小于此值视为同一行的字形抖动，不是真的新行
            clusters: list[list[dict]] = []
            for c in chars_sorted:
                if clusters and c["top"] - clusters[-1][-1]["top"] <= line_cluster_tol:
                    clusters[-1].append(c)
                else:
                    clusters.append([c])
            lines: dict[float, list[dict]] = {
                min(cl, key=lambda c: c["top"])["top"]: cl for cl in clusters
            }
            line_tops = sorted(lines.keys())
            for a, b in zip(line_tops, line_tops[1:]):
                chars_a = lines[a]
                size_a = max(c["size"] for c in chars_a)
                gap = b - a
                if gap < size_a * min_line_ratio - 0.3 and gap > 0.5:
                    # 排除标题/分隔等明显不同字号的场景：仅在两行字号一致时判定为"同段落内行距过密"
                    chars_b = lines[b]
                    size_b = max(c["size"] for c in chars_b)
                    if abs(size_a - size_b) < 0.1:
                        report.tight_line_spacing += 1
                        report.add(
                            "line_spacing", "fail",
                            f"相邻行间距 {gap:.2f}pt 小于 {min_line_ratio}x 字号"
                            f"（{size_a}pt * {min_line_ratio} = {size_a * min_line_ratio:.2f}pt），"
                            "违反「行距不得低于字号 1.45 倍」的硬性要求",
                            page=page_no,
                        )

    report.min_font_pt_found = min_size_seen


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def run(
    pdf_path: str,
    md_path: str | None,
    max_pages: int,
    min_font_pt: float,
    min_line_ratio: float,
    overlap_area_ratio: float,
    bounds_tolerance: float,
) -> Report:
    report = Report(pdf_path=pdf_path)
    report.versions = collect_versions()

    md_text = None
    if md_path:
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()

    check_structure(pdf_path, md_text, max_pages, report)
    check_layout(pdf_path, report, min_font_pt, min_line_ratio, overlap_area_ratio, bounds_tolerance)

    report.passed = not any(i["severity"] == "fail" for i in report.issues)
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="认知报告 PDF 质检（交付前必须全过）")
    p.add_argument("pdf_path", help="待检查的 PDF")
    p.add_argument("--md", dest="md_path", default=None, help="对应的 report.md（用于 ASR 完整性比对）")
    p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--min-font-pt", type=float, default=9.5)
    p.add_argument("--min-line-ratio", type=float, default=1.45)
    p.add_argument(
        "--overlap-area-ratio", type=float, default=0.15,
        help="两个文字块相交面积占较小块面积的比例超过此值才判定为重叠（默认 0.15，过滤掉字距/字距的轻微接触）",
    )
    p.add_argument("--bounds-tolerance", type=float, default=0.75, help="越界判定的容差（pt）")
    p.add_argument("--json", dest="json_path", default=None, help="把完整报告写到这个 JSON 文件")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(
            args.pdf_path,
            args.md_path,
            args.max_pages,
            args.min_font_pt,
            args.min_line_ratio,
            args.overlap_area_ratio,
            args.bounds_tolerance,
        )
    except FileNotFoundError as e:
        print(f"[错误] 文件不存在: {e}", file=sys.stderr)
        return 2

    payload = asdict(report)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)

    print("\n" + "=" * 60, file=sys.stderr)
    print(
        f"page_count={report.page_count} overlap={report.overlap} "
        f"out_of_page={report.out_of_page} empty_pages={report.empty_pages} "
        f"min_font_pt_found={report.min_font_pt_found} "
        f"asr_missing={report.asr_excerpts_missing}/{report.asr_excerpts_total} "
        f"tight_line_spacing={report.tight_line_spacing}",
        file=sys.stderr,
    )
    print("PASS" if report.passed else "FAIL — 禁止交付，先修 CSS/Markdown 再重跑", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
