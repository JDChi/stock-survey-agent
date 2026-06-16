#!/usr/bin/env python3
"""Download A-share financial reports from Eastmoney announcement mirrors."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime


API_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
PDF_URL = "https://pdf.dfcfw.com/pdf/H2_{art_code}_1.pdf"


def eastmoney_pdf_url(art_code: str) -> str:
    return PDF_URL.format(art_code=art_code)


def notice_sort_key(item: dict) -> str:
    return item.get("notice_date") or item.get("display_time") or item.get("sort_date") or ""


def is_full_report(title: str) -> bool:
    rejected = ("摘要", "英文", "English", "环境、社会及公司治理", "ESG", "H股", "港股")
    return not any(word in title for word in rejected)


def select_reports(items: list[dict]) -> dict[str, dict]:
    annual = []
    quarter = []
    half = []

    for item in items:
        title = item.get("title") or item.get("title_ch") or item.get("title_en") or ""
        if not is_full_report(title):
            continue
        enriched = dict(item)
        enriched["title"] = title

        if "年度报告" in title:
            annual.append(enriched)
        elif "半年度报告" in title:
            half.append(enriched)
        elif "季度报告" in title:
            quarter.append(enriched)

    selected = {}
    if annual:
        selected["annual"] = sorted(annual, key=notice_sort_key, reverse=True)[0]
    if quarter:
        selected["quarter"] = sorted(quarter, key=notice_sort_key, reverse=True)[0]
    if half:
        selected["half"] = sorted(half, key=notice_sort_key, reverse=True)[0]
    return selected


def fetch_announcements(stock_code: str, page_size: int, pages: int) -> list[dict]:
    items = []
    for page_index in range(1, pages + 1):
        params = {
            "sr": "-1",
            "page_size": str(page_size),
            "page_index": str(page_index),
            "ann_type": "A",
            "client_source": "web",
            "stock_list": stock_code,
        }
        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
                "Referer": f"https://data.eastmoney.com/notices/stock/{stock_code}.html",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("success") != 1:
            raise RuntimeError(f"Eastmoney API failed: {payload}")
        batch = payload.get("data", {}).get("list", [])
        items.extend(batch)
        if len(batch) < page_size:
            break
    return items


def slug_for_report(kind: str, item: dict) -> str:
    title = item["title"]
    year_match = re.search(r"(20\d{2})", title)
    year = year_match.group(1) if year_match else item.get("notice_date", "")[:4]
    if kind == "annual":
        return f"{year}-annual-report.pdf"
    if kind == "half":
        return f"{year}-half-year-report.pdf"
    return f"{year}-q-report.pdf"


def download(url: str, output_path: pathlib.Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        output_path.write_bytes(resp.read())
    ensure_pdf(output_path)


def ensure_pdf(path: pathlib.Path) -> None:
    with path.open("rb") as f:
        head = f.read(5)
    if head != b"%PDF-":
        raise ValueError(f"{path} is not a PDF")


def write_sources(path: pathlib.Path, stock_code: str, stock_name: str, reports: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {stock_name}（{stock_code}）资料来源",
        "",
        f"- 获取日期：{datetime.now().strftime('%Y-%m-%d')}",
        "- 下载通道：东方财富公告 PDF 镜像",
        f"- 公告索引：https://data.eastmoney.com/notices/stock/{stock_code}.html",
        "",
        "## 已下载文件",
        "",
    ]

    labels = {
        "annual": "年度报告",
        "quarter": "季度报告",
        "half": "半年度报告",
    }
    for kind in ("annual", "quarter", "half"):
        item = reports.get(kind)
        if not item:
            continue
        lines.extend(
            [
                f"### {labels[kind]}",
                "",
                f"- 本地文件：`{item['local_file']}`",
                f"- 公告标题：{item['title']}",
                f"- 公告日期：{str(item.get('notice_date', ''))[:10]}",
                f"- 东方财富公告代码：`{item['art_code']}`",
                f"- 东方财富 PDF：{item['eastmoney_pdf']}",
            ]
        )
        if item.get("official_pdf"):
            lines.append(f"- 官方 PDF：{item['official_pdf']}")
        lines.append("")

    lines.extend(
        [
            "## 使用说明",
            "",
            "- 东方财富 PDF 静态地址适合作为自动下载通道。",
            "- 做正式研究引用时，仍应优先回到交易所、巨潮或公司公告原文核对。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_code", help="A-share stock code, for example 600219")
    parser.add_argument("--stock-name", default="", help="Optional display name")
    parser.add_argument("--output-root", default="data", help="Directory that contains per-stock folders")
    parser.add_argument("--page-size", type=int, default=120)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument(
        "--include-half",
        action="store_true",
        help="Also download the latest half-year report when found",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print selected reports without downloading")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    stock_name = args.stock_name or args.stock_code
    stock_dir = pathlib.Path(args.output_root) / args.stock_code
    raw_dir = stock_dir / "raw"

    items = fetch_announcements(args.stock_code, args.page_size, args.pages)
    reports = select_reports(items)
    wanted = ["annual", "quarter"]
    if args.include_half:
        wanted.append("half")
    reports = {kind: reports[kind] for kind in wanted if kind in reports}

    if not reports:
        raise SystemExit(f"No financial reports found for {args.stock_code}")

    for kind, item in reports.items():
        pdf_url = eastmoney_pdf_url(item["art_code"])
        local_file = f"raw/{slug_for_report(kind, item)}"
        item["eastmoney_pdf"] = pdf_url
        item["local_file"] = local_file
        if args.dry_run:
            print(f"{kind}\t{item['art_code']}\t{item['title']}\t{pdf_url}")
        else:
            download(pdf_url, stock_dir / local_file)

    if not args.dry_run:
        write_sources(stock_dir / "sources.md", args.stock_code, stock_name, reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
