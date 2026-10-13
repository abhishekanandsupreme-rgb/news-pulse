"""Characterization tests for scripts/fetch_feeds.parse_date().

These lock in behaviour that the live feeds already depend on, rather than
asking for new behaviour. Measured 2026-10-06 against the live feed set: 37 of
the 38 configured feeds parsed (google-gaming raised a parse ValueError), and
the 188 date strings they emitted all carry either a GMT/UTC/Z marker or an
explicit numeric offset. No feed emitted a naive timestamp, and none emitted a
parenthesised zone name, so the "assume UTC" fallback below is a documented
convention that current data never exercises -- not a live source of wrong
dates. The parenthesised case is pinned here so that if a feed ever starts
emitting one, the assumed-UTC result is a decision on record instead of a
silent surprise.

Run: python -m unittest discover -s tests -v
"""
import datetime as dt
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_feeds",
                                               ROOT / "scripts" / "fetch_feeds.py")
fetch_feeds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_feeds)

UTC = dt.timezone.utc


def as_utc(d):
    return d.astimezone(UTC)


class ParseDateTests(unittest.TestCase):
    def test_rfc822_gmt(self):
        d = fetch_feeds.parse_date("Sat, 12 Sep 2026 03:10:00 GMT")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))

    def test_rfc822_numeric_offset_is_applied_not_dropped(self):
        # 05:30 ahead of UTC, so the instant is 5h30m earlier in UTC.
        d = fetch_feeds.parse_date("Sat, 12 Sep 2026 03:10:00 +0530")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 11, 21, 40, tzinfo=UTC))

    def test_rfc822_named_offset(self):
        d = fetch_feeds.parse_date("Sat, 12 Sep 2026 03:10:00 +00:00")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))

    def test_atom_iso_with_z(self):
        d = fetch_feeds.parse_date("2026-09-12T03:10:00Z")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))

    def test_atom_iso_with_offset(self):
        d = fetch_feeds.parse_date("2026-09-12T08:40:00+05:30")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))

    def test_result_is_always_timezone_aware(self):
        for raw in ("Sat, 12 Sep 2026 03:10:00 GMT", "2026-09-12T03:10:00Z",
                    "Sat, 12 Sep 2026 03:10:00 +0530", "12 Sep 2026 03:10"):
            self.assertIsNotNone(fetch_feeds.parse_date(raw).tzinfo, raw)

    def test_unparseable_and_empty_input_yield_none(self):
        self.assertIsNone(fetch_feeds.parse_date(""))
        self.assertIsNone(fetch_feeds.parse_date(None))
        self.assertIsNone(fetch_feeds.parse_date("not a date at all"))

    def test_naive_input_is_read_as_utc_by_convention(self):
        """No live feed does this; if one starts, the timestamp is the wall-clock
        time treated as UTC (so a +05:30 feed would read 5h30m late)."""
        d = fetch_feeds.parse_date("12 Sep 2026 03:10")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))

    def test_parenthesised_zone_name_is_stripped_then_read_as_utc(self):
        """Windows/.NET style zone names arrive in parentheses. The name is
        dropped before parsing, so the offset is not applied -- pinned so the
        behaviour is visible rather than guessed at."""
        d = fetch_feeds.parse_date("Sat, 12 Sep 2026 03:10:00 (India Standard Time)")
        self.assertEqual(as_utc(d), dt.datetime(2026, 9, 12, 3, 10, tzinfo=UTC))


if __name__ == "__main__":
    unittest.main()
