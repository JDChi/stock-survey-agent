import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("fetch_eastmoney_reports.py")


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_eastmoney_reports", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EastmoneyReportTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.sample = [
            {
                "art_code": "AN202604271821619950",
                "notice_date": "2026-04-28 00:00:00",
                "title": "南山铝业:山东南山铝业股份有限公司2026年第一季度报告",
            },
            {
                "art_code": "AN202603261820768986",
                "notice_date": "2026-03-27 00:00:00",
                "title": "南山铝业:山东南山铝业股份有限公司2025年度报告",
            },
            {
                "art_code": "AN202604011820957436",
                "notice_date": "2026-04-02 00:00:00",
                "title": "洛阳钼业:H股市场公告-洛阳钼业2025年年度报告(H股)",
            },
            {
                "art_code": "AN202603261820768975",
                "notice_date": "2026-03-27 00:00:00",
                "title": "南山铝业:山东南山铝业股份有限公司2025年度报告_摘要",
            },
        ]

    def test_selects_latest_annual_and_quarter_without_abstract(self):
        reports = self.mod.select_reports(self.sample)
        self.assertEqual(reports["annual"]["art_code"], "AN202603261820768986")
        self.assertEqual(reports["quarter"]["art_code"], "AN202604271821619950")
        self.assertNotIn("摘要", reports["annual"]["title"])

    def test_builds_eastmoney_pdf_url(self):
        url = self.mod.eastmoney_pdf_url("AN202603261820768986")
        self.assertEqual(url, "https://pdf.dfcfw.com/pdf/H2_AN202603261820768986_1.pdf")

    def test_writes_sources_with_official_urls(self):
        reports = self.mod.select_reports(self.sample)
        reports["annual"]["local_file"] = "raw/2025-annual-report.pdf"
        reports["annual"]["eastmoney_pdf"] = self.mod.eastmoney_pdf_url(reports["annual"]["art_code"])
        reports["annual"]["official_pdf"] = "https://www.sse.com.cn/example-annual.pdf"
        reports["quarter"]["local_file"] = "raw/2026-q1-report.pdf"
        reports["quarter"]["eastmoney_pdf"] = self.mod.eastmoney_pdf_url(reports["quarter"]["art_code"])
        reports["quarter"]["official_pdf"] = "https://www.sse.com.cn/example-q1.pdf"

        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "sources.md"
            self.mod.write_sources(out, "600219", "南山铝业", reports)
            text = out.read_text(encoding="utf-8")

        self.assertIn("南山铝业（600219）资料来源", text)
        self.assertIn("AN202603261820768986", text)
        self.assertIn("https://www.sse.com.cn/example-q1.pdf", text)

    def test_rejects_non_pdf_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.pdf"
            path.write_text("<html>not a pdf</html>", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.mod.ensure_pdf(path)


if __name__ == "__main__":
    unittest.main()
