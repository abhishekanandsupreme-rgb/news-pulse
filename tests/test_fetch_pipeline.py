"""End-to-end tests for scripts/fetch_feeds.py main() with the network stubbed.

Covers the wiring that the unit-level dedup test cannot see: the dedup pass has
to run *before* articles.json is written and before per-source counts and
category totals are reported, otherwise data/stats.json claims articles the
site never renders.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_feeds",
                                               ROOT / "scripts" / "fetch_feeds.py")
fetch_feeds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_feeds)

STORY = "Anthropic CEO outlines plan to slow AI development"
GOOGLE_ONLY = "Sensex closes at record high on banking earnings"
PUBLISHER_LINK = "https://techcrunch.com/2026/09/12/anthropic-ceo-outlines/"
WRAPPER_LINK = "https://news.google.com/rss/articles/CBMiAAAA?oc=5"
WRAPPER_LINK_2 = "https://news.google.com/rss/articles/CBMiBBBB?oc=5"


def rss(channel_title, items):
    body = "".join(
        "<item><title>%s</title><link>%s</link><guid isPermaLink=\"false\">%s</guid>"
        "<pubDate>Sat, 12 Sep 2026 03:10:00 +0000</pubDate>"
        "<description>Some summary text.</description></item>"
        % (t, l, l) for t, l in items)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0"><channel><title>%s</title>%s</channel></rss>'
            % (channel_title, body)).encode("utf-8")


FEED_XML = {
    "https://example.com/techcrunch.xml": rss(
        "TechCrunch", [(STORY, PUBLISHER_LINK)]),
    "https://example.com/google-india.xml": rss(
        "Google News India", [(STORY, WRAPPER_LINK),
                              (GOOGLE_ONLY, WRAPPER_LINK_2)]),
}

CONFIG = {
    "settings": {"max_items_per_feed": 25, "timeout_seconds": 5, "retries": 0},
    "feeds": [
        {"name": "TechCrunch", "slug": "techcrunch", "category": "tech",
         "url": "https://example.com/techcrunch.xml"},
        {"name": "Google News India", "slug": "google-news-india",
         "category": "india", "url": "https://example.com/google-india.xml",
         "strip_source_suffix": True},
    ],
}


class DisplayPathTests(unittest.TestCase):
    """Committed metadata must not carry a machine absolute path: data/stats.json
    is version-controlled, and an absolute config path leaks the developer's
    home directory (and makes every local run diff against CI)."""

    def test_path_inside_the_repo_becomes_repo_relative_posix(self):
        base = os.path.join("C:", os.sep + "repo")
        got = fetch_feeds.display_path(
            os.path.join(base, "config", "feeds.json"), base)
        self.assertEqual(got, "config/feeds.json")

    def test_path_outside_the_repo_keeps_only_the_file_name(self):
        base = os.path.join("C:", os.sep + "repo")
        got = fetch_feeds.display_path(
            os.path.join(os.sep + "tmp", "feeds.json"), base)
        self.assertEqual(got, "feeds.json")

    def test_result_never_contains_a_path_separator_to_the_home_dir(self):
        base = os.path.join("C:", os.sep + "Users", "asus", "repo")
        got = fetch_feeds.display_path(
            os.path.join(os.path.expanduser("~"), "other", "feeds.json"), base)
        self.assertNotIn("\\", got)
        self.assertNotIn("Users", got)
        self.assertNotIn(":", got)


class FetchPipelineTests(unittest.TestCase):
    def setUp(self):
        self._real_http_get = fetch_feeds.http_get
        fetch_feeds.http_get = lambda url, timeout_s, ua, attempts: (
            FEED_XML[url], 200)

    def tearDown(self):
        fetch_feeds.http_get = self._real_http_get

    def fetch(self, tmp):
        cfg_path = pathlib.Path(tmp) / "feeds.json"
        cfg_path.write_text(json.dumps(CONFIG), encoding="utf-8")
        data_dir = pathlib.Path(tmp) / "data"
        rc = fetch_feeds.main(["--config", str(cfg_path),
                               "--data-dir", str(data_dir), "-q"])
        self.assertEqual(rc, 0)
        articles = json.loads(
            (data_dir / "articles.json").read_text(encoding="utf-8"))
        stats = json.loads(
            (data_dir / "stats.json").read_text(encoding="utf-8"))
        return articles, stats

    def test_wrapper_copy_never_reaches_articles_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles, _ = self.fetch(tmp)
            links = [a["link"] for a in articles["articles"]]
            self.assertEqual(sorted(links), sorted([PUBLISHER_LINK,
                                                    WRAPPER_LINK_2]))
            self.assertEqual(articles["count"], 2)

    def test_per_source_counts_agree_with_the_written_articles(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles, stats = self.fetch(tmp)
            by_slug = {s["slug"]: s["articles"] for s in stats["sources"]}
            self.assertEqual(by_slug["google-news-india"], 1)
            self.assertEqual(by_slug["techcrunch"], 1)
            self.assertEqual(sum(by_slug.values()), articles["count"])
            self.assertEqual(stats["totals"]["articles"], articles["count"])

    def test_category_totals_exclude_the_dropped_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles, stats = self.fetch(tmp)
            self.assertEqual(stats["categories"], {"tech": 1, "india": 1})
            self.assertEqual(sum(stats["categories"].values()),
                             len(articles["articles"]))


    def test_stats_json_records_no_machine_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, stats = self.fetch(tmp)
            text = json.dumps(stats)
            recorded = stats["config"]["config_file"]
            self.assertEqual(recorded, "feeds.json")
            self.assertNotIn(os.path.dirname(os.path.abspath(tmp)), text)
            self.assertNotIn("\\", text)


class ParseXmlDiagnosticsTests(unittest.TestCase):
    """A blocked feed and a corrupt feed need different responses from a
    maintainer, but both used to surface as the same XML syntax error.
    Measured 2026-10-06: ESPN answers 202 with a zero-byte body and
    news.google.com's invalid topic path answers 200 with 1.6 MB of HTML, and
    the CI log said "no element found: line 1, column 0" for both.
    """

    def _message(self, raw):
        try:
            fetch_feeds.parse_xml(raw)
        except ValueError as exc:
            return str(exc)
        self.fail("expected ValueError for %r" % raw[:30])

    def test_empty_body_is_reported_as_empty(self):
        self.assertIn("empty", self._message(b"").lower())

    def test_html_body_is_reported_as_html_not_xml(self):
        body = b"<!doctype html><html lang=en><head><title>Go away</title></head><body>x</body></html>"
        msg = self._message(body)
        self.assertIn("html", msg.lower())
        self.assertNotIn("empty", msg.lower())

    def test_genuinely_malformed_xml_is_still_called_out_as_malformed(self):
        msg = self._message(b"<rss><channel><title>oops</channel>")
        low = msg.lower()
        self.assertIn("xml", low)
        self.assertNotIn("html", low)
        self.assertNotIn("empty", low)


class WriteJsonLineEndingsTests(unittest.TestCase):
    """write_json output is committed to the repo by CI. On Windows the default
    text-mode write turns every LF into CRLF, so a locally produced
    articles.json/stats.json differs from CI's on every single line -- a real
    run here produced 516 CR bytes against an LF blob at HEAD."""

    def test_output_is_lf_only_and_newline_terminated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            fetch_feeds.write_json(path, {"items": [1, 2], "note": "café"})
            raw = open(path, "rb").read()
            self.assertEqual(raw.count(b"\r"), 0)
            self.assertEqual(raw[-1:], b"\n")
            self.assertEqual(json.loads(raw.decode("utf-8"))["note"], "café")


if __name__ == "__main__":
    unittest.main()
