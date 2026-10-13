"""Tests for scripts/fetch_feeds.py — cross-feed duplicate suppression.

main() dedups titles per source slug, so the same headline arriving from a
second feed is kept twice. Measured 2026-10-06 on data/articles.json (680
articles): 4 such pairs, and in every pair the second copy was a
<news.google.com/rss/articles/...> redirect wrapper around the publisher's own
article already in the set. The fix drops the wrapper and keeps the direct
link; two different outlets running the same headline are both kept, because
that is coverage, not duplication.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import unittest

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_feeds",
                                               ROOT / "scripts" / "fetch_feeds.py")
fetch_feeds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_feeds)


def art(title, link, slug):
    return {"title": title, "link": link, "source_slug": slug,
            "source": slug, "category": "tech"}


GOOGLE = "https://news.google.com/rss/articles/CBMixAAAA?oc=5"
DIRECT = "https://techcrunch.com/2026/09/12/anthropic-ceo-outlines-plan/"
STORY = "Anthropic CEO outlines plan to slow AI development"


class DropWrappedDuplicatesTests(unittest.TestCase):
    def test_wrapper_dropped_when_publisher_also_has_the_story(self):
        arts = [art(STORY, DIRECT, "techcrunch"),
                art(STORY, GOOGLE, "google-business-india")]
        kept = fetch_feeds.drop_wrapped_duplicates(arts)
        self.assertEqual([a["link"] for a in kept], [DIRECT])

    def test_wrapper_kept_when_no_direct_copy_exists(self):
        arts = [art("Only on Google News", GOOGLE, "google-news-india")]
        kept = fetch_feeds.drop_wrapped_duplicates(arts)
        self.assertEqual([a["link"] for a in kept], [GOOGLE])

    def test_two_direct_outlets_with_same_headline_are_both_kept(self):
        arts = [art("Breaking: rate decision",
                    "https://www.reuters.com/markets/rate-decision", "reuters"),
                art("Breaking: rate decision",
                    "https://in.reuters.com/markets/rate-decision", "reuters-india")]
        kept = fetch_feeds.drop_wrapped_duplicates(arts)
        self.assertEqual(len(kept), 2)

    def test_result_is_independent_of_feed_order(self):
        arts = [art(STORY, GOOGLE, "google-business-india"),
                art("Unrelated", "https://example.com/1", "x"),
                art("  " + STORY.lower() + "  ", DIRECT, "techcrunch")]
        kept = fetch_feeds.drop_wrapped_duplicates(arts)
        self.assertNotIn(GOOGLE, [a["link"] for a in kept])
        self.assertEqual([a["link"] for a in kept],
                         ["https://example.com/1", DIRECT])

    def test_original_list_is_not_mutated(self):
        arts = [art(STORY, DIRECT, "techcrunch"),
                art(STORY, GOOGLE, "google-business-india")]
        fetch_feeds.drop_wrapped_duplicates(arts)
        self.assertEqual(len(arts), 2)


if __name__ == "__main__":
    unittest.main()
