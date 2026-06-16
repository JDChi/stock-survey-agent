---
name: fetch-eastmoney-reports
description: Use when fetching, downloading, indexing, or refreshing A-share company financial reports, annual reports, quarterly reports, half-year reports, or report PDFs from Eastmoney, 东方财富, 东财, 公告, 财报, 定期报告, 年报, 季报, 半年报.
---

# Fetch Eastmoney Reports

Use this skill to download A-share financial report PDFs through Eastmoney announcement mirrors, especially when official exchange PDF URLs are hard to fetch non-interactively.

## Workflow

1. Resolve the stock code and create/use `data/<stock_code>/`.
2. Run the bundled downloader from the project root:

```bash
python3 .agents/skills/fetch-eastmoney-reports/scripts/fetch_eastmoney_reports.py 600219 --stock-name 南山铝业
```

3. Verify downloaded files are real PDFs, not HTML challenge/error pages:

```bash
file data/<stock_code>/raw/*.pdf
```

4. Keep `data/<stock_code>/sources.md` with announcement codes, dates, and PDF URLs.
5. For formal research conclusions, cross-check material facts against the exchange, 巨潮资讯网, or company investor-relations page.

## Downloader Behavior

The script uses:

- Announcement API: `https://np-anotice-stock.eastmoney.com/api/security/ann`
- PDF pattern: `https://pdf.dfcfw.com/pdf/H2_<art_code>_1.pdf`

By default it downloads:

- latest full annual report, excluding `_摘要`, English, and ESG reports
- latest full quarterly report

Useful options:

```bash
python3 .agents/skills/fetch-eastmoney-reports/scripts/fetch_eastmoney_reports.py 600219 --stock-name 南山铝业 --dry-run
python3 .agents/skills/fetch-eastmoney-reports/scripts/fetch_eastmoney_reports.py 600219 --stock-name 南山铝业 --include-half
python3 .agents/skills/fetch-eastmoney-reports/scripts/fetch_eastmoney_reports.py 300750 --stock-name 宁德时代 --output-root data
```

## Output Contract

Store outputs under:

```text
data/<stock_code>/
  raw/
    <year>-annual-report.pdf
    <year>-q-report.pdf
  sources.md
```

Do not treat a successful HTTP request as success. Success requires the saved file to start with `%PDF-`.

## Common Failures

- Official exchange PDF links may return CDN/browser challenge HTML to `curl`; use Eastmoney as the download mirror and record the official source separately when available.
- Eastmoney keyword filters can be ignored by the API; fetch a large page and filter titles locally.
- Avoid `_摘要` files unless the user explicitly asks for report summaries.
