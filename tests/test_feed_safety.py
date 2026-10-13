"""Tests for scripts/fetch_feeds.py — resource-exhaustion guards on untrusted input.

Verified on this interpreter (Python 3.11.9 / expat 2.6.0): a 296-byte document
with five nested <!ENTITY> definitions expanded to 100,000 characters with no
error, i.e. CPython's ElementTree does not cap entity amplification here.
http_get also read the whole body with no ceiling, and decompressed gzip before
any size check, so a small compressed payload could expand without limit.

Measured against the live feed set on 2026-10-06: 36 fetchable feeds, largest
body 354 KB (av-club), and NONE of them declare <!ENTITY> -- so refusing entity
declarations costs no content.
"""
import gzip
import importlib.util
import io
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_feeds",
                                               ROOT / "scripts" / "fetch_feeds.py")
fetch_feeds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_feeds)

GOOD_RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
            b'<item><title>Headline</title>'
            b'<link>https://x.example/1</link></item></channel></rss>')

# 5 levels x10 amplification: a few hundred bytes of input, 100 KB of expansion.
ENTITY_BOMB = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY e1 "0123456789">'
for _n in range(2, 6):
    ENTITY_BOMB += ('<!ENTITY e%d "' % _n).encode() + ("&e%d;" % (_n - 1)).encode() * 10 + b'">'
ENTITY_BOMB += b"]><rss>&e5;</rss>"


class FakeResponse:
    """Minimal stand-in for the object urlopen returns."""

    def __init__(self, chunks, encoding=None, status=200):
        self._buf = io.BytesIO(b"".join(chunks))
        self._chunks = chunks
        self._pos = 0
        self.status = status
        self.headers = {"Content-Encoding": encoding} if encoding else {}

    def read(self, size=-1):
        if size is None or size < 0:
            data = self._buf.read()
        else:
            data = self._buf.read(size)
        return data

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class StubUrlopen:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def __call__(self, req, timeout=None):
        self.calls += 1
        return self.response


class EntityExpansionTests(unittest.TestCase):
    def test_entity_declarations_are_refused_before_parsing(self):
        with self.assertRaises(ValueError) as ctx:
            fetch_feeds.parse_xml(ENTITY_BOMB)
        self.assertIn("entit", str(ctx.exception).lower())

    def test_refusal_happens_even_though_the_bomb_would_parse(self):
        # Guards against re-ordering the check after ET.fromstring: the payload
        # is well-formed, so a check placed after parsing would let it expand.
        self.assertTrue(fetch_feeds.ENTITY_DECL_RE.search(ENTITY_BOMB))

    def test_ordinary_feed_still_parses(self):
        root = fetch_feeds.parse_xml(GOOD_RSS)
        items = [el for el in root.iter()
                 if fetch_feeds.localname(el.tag) == "item"]
        self.assertEqual(len(items), 1)

    def test_entity_reference_in_content_is_not_a_declaration(self):
        """A feed may *use* a predefined entity; only <!ENTITY> definitions are
        refused, otherwise ordinary escaped ampersands would break ingestion."""
        body = GOOD_RSS.replace(b"<title>Headline</title>",
                                b"<title>A &amp; B</title>")
        root = fetch_feeds.parse_xml(body)
        self.assertEqual(len([1 for el in root.iter()
                              if fetch_feeds.localname(el.tag) == "item"]), 1)


class ResponseSizeTests(unittest.TestCase):
    def setUp(self):
        self._real_urlopen = fetch_feeds.urllib.request.urlopen

    def tearDown(self):
        fetch_feeds.urllib.request.urlopen = self._real_urlopen

    def _get(self, response):
        fetch_feeds.urllib.request.urlopen = StubUrlopen(response)
        return fetch_feeds.http_get("https://x.example/feed", 5, "ua", 1)

    def test_oversized_body_is_refused(self):
        limit = fetch_feeds.MAX_FEED_BYTES
        chunks = [b"x" * (1 << 20)] * (limit // (1 << 20) + 2)
        with self.assertRaises(ValueError) as ctx:
            self._get(FakeResponse(chunks))
        self.assertIn("size", str(ctx.exception).lower())

    def test_normal_sized_body_passes_through(self):
        raw, status = self._get(FakeResponse([GOOD_RSS]))
        self.assertEqual(status, 200)
        self.assertEqual(raw, GOOD_RSS)

    def test_gzip_bomb_is_measured_decompressed(self):
        """The ceiling must apply after inflation -- a compressed payload is
        exactly where a size check on the raw bytes stops being useful."""
        payload = b"0" * (fetch_feeds.MAX_FEED_BYTES + 1024)
        with self.assertRaises(ValueError) as ctx:
            self._get(FakeResponse([gzip.compress(payload)], encoding="gzip"))
        self.assertIn("size", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
