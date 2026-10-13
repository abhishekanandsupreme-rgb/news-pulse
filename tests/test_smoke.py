"""End-to-end smoke tests for scripts/build_site.py's data fallback chain.

Replaces two filler assertions ("assertTrue(True)", "the repo folder exists"),
which could never fail and therefore proved nothing.

The chain that matters (load_articles, build_site.py:300-345): the real
snapshot wins even when it holds zero articles, and a corrupt real snapshot is
a hard BuildError rather than a quiet downgrade to sample stories -- otherwise
a CI run where every feed failed would publish fabricated headlines and pass
the deploy gate. The sample fixture is only for a checkout where no snapshot
exists yet.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_site",
                                               ROOT / "scripts" / "build_site.py")
build_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_site)

SAMPLE_FIXTURE = ROOT / "data" / "sample-articles.json"

SITE_CONFIG = {
    "site_name": "NewsPulse",
    "tagline": "smoke",
    "description": "smoke test description",
    "base_url": "https://example.com/news-pulse",
    "contact_email": "t@example.com",
    "data_file": "no-stats-here.json",
    "sample_data_file": "no-sample-here.json",
    "output_dir": "no-out-here",
    "categories": [{"slug": "tech", "label": "Tech", "color": "#1d4ed8"}],
}


def payload(articles):
    return json.dumps({"generated_at": "2026-09-12T04:00:00+00:00",
                       "count": len(articles), "articles": articles},
                      ensure_ascii=False)


def article(i, title):
    return {"id": "%016x" % i, "title": title,
            "link": "https://src.example/%d" % i, "source": "Src",
            "source_slug": "src", "category": "tech",
            "published": "2026-09-12T03:10:00+00:00",
            "published_ts": 1789000000.0 + i, "description": "d", "image": ""}


class ChainTests(unittest.TestCase):
    """load_articles() in isolation -- the branch decisions, no filesystem build."""

    def cfg(self, tmp):
        return build_site.Config(SITE_CONFIG, pathlib.Path(tmp))

    def call(self, tmp, data=None, sample=None):
        cfg = self.cfg(tmp)
        return build_site.load_articles(cfg, data, sample, lambda m: None)

    def test_real_snapshot_is_the_truth_even_when_empty(self):
        """A fetch where every feed failed must produce an honest empty site:
        the real snapshot wins (labelled "live") and the sample fixture's
        stories never leak in."""
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / "articles.json"
            data.write_text(payload([]), encoding="utf-8")
            arts, label, _ = self.call(
                tmp, str(data), str(SAMPLE_FIXTURE))
            self.assertEqual(arts, [])
            self.assertEqual(label, "live")
            self.assertNotEqual(label, "sample")

    def test_corrupt_real_snapshot_refuses_to_fall_back_to_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / "articles.json"
            data.write_text("{ this is not json", encoding="utf-8")
            with self.assertRaises(build_site.BuildError) as ctx:
                self.call(tmp, str(data), str(SAMPLE_FIXTURE))
            self.assertIn("sample", str(ctx.exception).lower())

    def test_snapshot_without_articles_list_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / "articles.json"
            data.write_text(json.dumps({"count": 0}), encoding="utf-8")
            with self.assertRaises(build_site.BuildError):
                self.call(tmp, str(data), str(SAMPLE_FIXTURE))

    def test_sample_fixture_used_only_when_no_snapshot_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            arts, label, _ = self.call(
                tmp, str(pathlib.Path(tmp) / "absent.json"), str(SAMPLE_FIXTURE))
            self.assertEqual(label, "sample")
            self.assertTrue(arts, "sample fixture produced no articles")

    def test_no_snapshot_and_no_sample_builds_the_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            arts, label, _ = self.call(
                tmp, str(pathlib.Path(tmp) / "absent.json"),
                str(pathlib.Path(tmp) / "no-sample.json"))
            self.assertEqual((arts, label), ([], "empty"))

    def test_empty_sample_file_does_not_count_as_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = pathlib.Path(tmp) / "sample.json"
            sample.write_text(payload([]), encoding="utf-8")
            arts, label, _ = self.call(
                tmp, str(pathlib.Path(tmp) / "absent.json"), str(sample))
            self.assertEqual((arts, label), ([], "empty"))


class BuildSmokeTests(unittest.TestCase):
    """Full build from the repo's own sample fixture, then the CI gate."""

    def test_sample_build_is_deployable_by_docs_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = pathlib.Path(tmp) / "site-config.json"
            cfg_path.write_text(json.dumps(SITE_CONFIG), encoding="utf-8")
            out = pathlib.Path(tmp) / "docs"
            rc = build_site.main([
                "--config", str(cfg_path),
                "--data", str(pathlib.Path(tmp) / "absent.json"),
                "--sample-data", str(SAMPLE_FIXTURE),
                "--out", str(out), "-q"])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / "sitemap.xml").is_file())
            gate = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "docs-check.py"),
                 str(out), "--strict"],
                capture_output=True, text=True)
            self.assertEqual(gate.returncode, 0,
                             "docs-check rejected a sample-data build:\n"
                             + (gate.stdout or "") + (gate.stderr or ""))

    def test_repo_sample_fixture_ids_are_builder_safe(self):
        """make_sample_data.py must emit ids the 16-hex gate accepts, or the
        onboarding path ships a site with zero story pages."""
        raw = json.loads(SAMPLE_FIXTURE.read_text(encoding="utf-8"))
        arts = raw["articles"]
        self.assertTrue(arts)
        kept = build_site.normalize_articles(arts, lambda m: None)
        self.assertEqual(len(kept), len(arts),
                         "sample fixture articles were silently dropped")


if __name__ == "__main__":
    unittest.main()
