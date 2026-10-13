"""Tests for scripts/build_site.py — articles with no parseable date.

normalize_articles() already decides undated articles are possible: it counts
them, logs "WARN: N article(s) had no parseable date -> sorted last" and gives
them ts 0.0. But 0.0 is the Unix epoch, so the emitted page told Google the
story was published on 1970-01-01 (sitemap <lastmod> and JSON-LD
datePublished) and printed an empty datetime="" attribute. Omitting those is
correct; asserting a 1970 date is not.

Run: python -m unittest discover -s tests -v
"""
import datetime as dt
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_site",
                                               ROOT / "scripts" / "build_site.py")
build_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_site)

SITE_CONFIG = {
    "site_name": "NewsPulse",
    "tagline": "test",
    "description": "test description",
    "base_url": "https://example.com/news-pulse",
    "contact_email": "t@example.com",
    "data_file": "no-such-stats.json",       # keep the real repo out of the test
    "sample_data_file": "no-such-sample.json",
    "output_dir": "no-such-out",
    "categories": [{"slug": "tech", "label": "Tech", "color": "#1d4ed8"}],
}

STAMP = dt.datetime(2026, 9, 12, 3, 10, tzinfo=dt.timezone.utc)
STAMP_ISO = STAMP.isoformat()
STAMP_DATE = STAMP.date().isoformat()

DATED = {
    "id": "aaaaaaaaaaaaaaaa",
    "title": "Dated story",
    "link": "https://src.example/dated",
    "source": "Test Source",
    "source_slug": "test",
    "category": "tech",
    "published": STAMP_ISO,
    "published_ts": STAMP.timestamp(),
    "description": "has a date",
    "image": "",
}
UNDATED = {
    "id": "bbbbbbbbbbbbbbbb",
    "title": "Undated story",
    "link": "https://src.example/undated",
    "source": "Test Source",
    "source_slug": "test",
    "category": "tech",
    "published": None,
    "published_ts": None,
    "description": "feed gave us no usable date",
    "image": "",
}


def build(tmp):
    cfg_dir = pathlib.Path(tmp)
    cfg_path = cfg_dir / "site-config.json"
    cfg_path.write_text(json.dumps(SITE_CONFIG), encoding="utf-8")
    data_path = cfg_dir / "articles.json"
    data_path.write_text(json.dumps({"generated_at": "2026-09-12T04:00:00+00:00",
                                     "count": 2,
                                     "articles": [DATED, UNDATED]}),
                         encoding="utf-8")
    out = cfg_dir / "docs"
    rc = build_site.main(["--config", str(cfg_path), "--data", str(data_path),
                          "--out", str(out), "-q"])
    return rc, out


class UndatedHelperTests(unittest.TestCase):
    def test_iso_date_is_empty_for_undated(self):
        self.assertEqual(build_site.iso_date(0.0), "")
        self.assertEqual(build_site.iso_date(None), "")

    def test_iso_datetime_is_empty_for_undated(self):
        self.assertEqual(build_site.iso_datetime(0.0), "")
        self.assertEqual(build_site.iso_datetime(None), "")

    def test_real_timestamps_still_format(self):
        self.assertEqual(build_site.iso_date(STAMP.timestamp()), STAMP_DATE)
        self.assertEqual(build_site.iso_datetime(STAMP.timestamp()), STAMP_ISO)


class UndatedBuildTests(unittest.TestCase):
    def test_build_succeeds_with_an_undated_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = build(tmp)
            self.assertEqual(rc, 0)
            self.assertTrue((out / "sitemap.xml").is_file())

    def test_undated_article_never_gets_a_1970_lastmod(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out = build(tmp)
            sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
            self.assertNotIn("1970", sitemap)
            und = [b for b in sitemap.split("<url>")
                   if "/article/bbbbbbbbbbbbbbbb/" in b]
            self.assertEqual(len(und), 1, "undated article not listed once")
            self.assertNotIn("<lastmod>", und[0])
            dat = [b for b in sitemap.split("<url>")
                   if "/article/aaaaaaaaaaaaaaaa/" in b]
            self.assertEqual(len(dat), 1)
            self.assertIn("<lastmod>%s</lastmod>" % STAMP_DATE, dat[0])

    def test_undated_article_page_claims_no_1970_publication_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out = build(tmp)
            page = out / "article" / "bbbbbbbbbbbbbbbb" / "index.html"
            self.assertTrue(page.is_file(), "undated story page not built")
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("1970", html)
            self.assertNotIn('datetime=""', html)
            self.assertIn("date unknown", html)

    def test_rss_omits_pubdate_for_undated_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out = build(tmp)
            rss = (out / "rss.xml").read_text(encoding="utf-8")
            self.assertNotIn("1970", rss)


if __name__ == "__main__":
    unittest.main()
