"""Tests for scripts/build_site.py — affiliate strip (spec: monetization/README.md §3).

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_site",
                                               ROOT / "scripts" / "build_site.py")
build_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_site)


def make_builder(tmp, products="absent"):
    cfg = build_site.Config({"base_url": "https://example.com/news-pulse"},
                            Path(tmp))
    if products != "absent":
        cdir = Path(tmp) / "config"
        cdir.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(products, ensure_ascii=False)
                   if products != "broken" else "{not json")
        (cdir / "affiliate-products.json").write_text(payload, encoding="utf-8")
    builder = build_site.SiteBuilder(cfg, [], {}, "empty", "", lambda msg: None)
    return builder, cfg


class AffiliateStripTests(unittest.TestCase):
    def test_missing_file_renders_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp)
            self.assertEqual(b.affiliate_strip(cfg), "")

    def test_broken_file_renders_nothing_not_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp, products="broken")
            self.assertEqual(b.affiliate_strip(cfg), "")

    def test_valid_products_render_cards(self):
        products = [
            {"title": "AI Prompt Pack", "blurb": "500 prompts.",
             "url": "https://store.example/#pricing", "badge": "Popular"},
            {"title": "Free Teaser", "blurb": "Starter set.",
             "url": "https://store.example/#free", "badge": ""},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp, products=products)
            html = b.affiliate_strip(cfg)
            self.assertIn("AI Prompt Pack", html)
            self.assertIn("500 prompts.", html)
            self.assertIn('href="https://store.example/#pricing"', html)
            self.assertIn("Popular", html)
            self.assertIn('rel="noopener', html)
            self.assertEqual(html.count('class="aff-card"'), 2)

    def test_escapes_titles_and_urls(self):
        products = [{"title": "<script>alert(1)</script>",
                     "blurb": 'quote" test',
                     "url": "https://ok.example/?a=1&b=2",
                     "badge": "xss<img>"}]
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp, products=products)
            html = b.affiliate_strip(cfg)
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("&lt;img&gt;", html)

    def test_rejects_non_http_urls_and_titleless_entries(self):
        products = [
            {"title": "javascript:", "blurb": "", "url": "javascript:alert(1)"},
            {"title": "", "blurb": "", "url": "https://ok.example/"},
            {"title": "data uri", "blurb": "", "url": "data:text/html,<h1>x</h1>"},
            {"title": "Good", "blurb": "", "url": "https://good.example/"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp, products=products)
            html = b.affiliate_strip(cfg)
            self.assertNotIn("javascript", html)
            self.assertNotIn("data:text/html", html)
            self.assertEqual(html.count('class="aff-card"'), 1)
            self.assertIn("Good", html)

    def test_disclosure_present(self):
        products = [{"title": "T", "blurb": "", "url": "https://e.example/",
                     "badge": ""}]
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(tmp, products=products)
            html = b.affiliate_strip(cfg)
            self.assertIn("commission", html.lower())

    def test_list_wrapped_dict_payload_also_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, cfg = make_builder(
                tmp, products={"products": [
                    {"title": "T", "blurb": "", "url": "https://e.example/",
                     "badge": ""}]})
            self.assertEqual(b.affiliate_strip(cfg).count('class="aff-card"'), 1)
