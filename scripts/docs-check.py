#!/usr/bin/env python3
"""
docs-check.py — sanity-check the generated static site before it ships.

Runs after scripts/build_site.py, locally or in CI. It fails loudly on an
empty or obviously broken build so a bad deploy can never reach GitHub
Pages, and it warns about SEO gaps (missing sitemap/robots/feed/meta)
without blocking. Pure Python 3.11 stdlib — no dependencies, no pip.

Usage:
    python scripts/docs-check.py                 # check <repo>/docs
    python scripts/docs-check.py path/to/site    # check another folder
    python scripts/docs-check.py --strict        # sitemap.xml required

Exit codes:
    0  every required check passed (warnings allowed)
    1  at least one required check failed
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Some Windows consoles are not UTF-8; degrade gracefully instead of crashing.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

# --- tunables ---------------------------------------------------------------

MIN_INDEX_BYTES = 256  # an index.html smaller than this is almost certainly broken
MIN_LINKS = 3          # the landing page should link to at least a few stories
FEED_NAMES = ("rss.xml", "feed.xml", "atom.xml", "feeds.xml", "news.xml")

# --- patterns ---------------------------------------------------------------

HTML_MARKER = re.compile(r"<(!doctype|html)[\s>]", re.IGNORECASE)
TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_DESCRIPTION = re.compile(r"<meta(?=[^>]*name=[\"']description[\"'])[^>]*>", re.IGNORECASE)
LINK = re.compile(r"<a\s", re.IGNORECASE)
LOCAL_FILE_URL = re.compile(r"file://", re.IGNORECASE)
LOCAL_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
SITEMAP_ROOT = re.compile(r"<(urlset|sitemapindex)[\s>]", re.IGNORECASE)
SITEMAP_LOC = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE | re.DOTALL)
ROBOTS_SITEMAP = re.compile(r"^\s*sitemap\s*:", re.IGNORECASE | re.MULTILINE)


class Report:
    """Collects check results; the process exit code reflects failures."""

    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def ok(self, message: str) -> None:
        print("  [ OK ] " + message)

    def warn(self, message: str) -> None:
        self.warnings += 1
        print("  [WARN] " + message)

    def fail(self, message: str) -> None:
        self.failures += 1
        print("  [FAIL] " + message)

    def exit_code(self, docs: Path) -> int:
        if self.failures:
            print(
                f"\ndocs-check: {self.failures} failed check(s), "
                f"{self.warnings} warning(s) -> {docs} is NOT safe to deploy."
            )
            return 1
        print(
            f"\ndocs-check: all required checks passed "
            f"({self.warnings} warning(s)) -> {docs} is safe to deploy."
        )
        return 0


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            if unit == "B":
                return f"{n:.0f} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} MB"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sanity-check the generated static site before deploy.",
    )
    parser.add_argument(
        "docs_dir",
        nargs="?",
        default=None,
        help="site directory to check (default: <repo>/docs)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat a missing sitemap.xml as a failure (default: warning)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    docs = Path(args.docs_dir).resolve() if args.docs_dir else repo_root / "docs"

    print(f"docs-check: checking {docs}")
    report = Report()

    # -- 1. the build directory ---------------------------------------------
    if not docs.is_dir():
        report.fail(f"{docs} does not exist — did scripts/build_site.py run?")
        return report.exit_code(docs)
    files = [p for p in sorted(docs.rglob("*")) if p.is_file()]
    if not files:
        report.fail(f"{docs} is empty — the build produced no output.")
        return report.exit_code(docs)
    total_bytes = sum(p.stat().st_size for p in files)
    report.ok(f"build directory — {len(files)} file(s), {human_size(total_bytes)} total")

    # -- 2. index.html ------------------------------------------------------
    index = docs / "index.html"
    if not index.is_file():
        report.fail("docs/index.html is missing — there is nothing to serve.")
        return report.exit_code(docs)

    html = read_text(index)
    if index.stat().st_size < MIN_INDEX_BYTES:
        report.fail(
            f"index.html is only {index.stat().st_size} bytes "
            f"(minimum {MIN_INDEX_BYTES}) — the build looks broken."
        )
    else:
        report.ok(f"index.html present ({human_size(index.stat().st_size)})")

    if HTML_MARKER.search(html):
        report.ok("index.html looks like valid HTML")
    else:
        report.fail("index.html does not look like HTML (no <html>/<doctype> found).")

    links = len(LINK.findall(html))
    if links < MIN_LINKS:
        report.warn(f"index.html has only {links} <a> link(s) — expected a story listing.")
    else:
        report.ok(f"index.html links to {links} resource(s)")

    title = TITLE_TAG.search(html)
    if title and title.group(1).strip():
        report.ok(f"page title — {title.group(1).strip()[:60]!r}")
    else:
        report.warn("index.html has no non-empty <title> (bad for SEO).")

    if META_DESCRIPTION.search(html):
        report.ok("meta description present")
    else:
        report.warn("index.html has no meta description (bad for SEO).")

    local_kinds = []
    if LOCAL_FILE_URL.search(html):
        local_kinds.append("file:// URL")
    if LOCAL_WINDOWS_PATH.search(html):
        local_kinds.append("absolute Windows path")
    if local_kinds:
        report.fail("index.html contains local references: " + ", ".join(local_kinds))
    else:
        report.ok("no local file/path leftovers in index.html")

    # -- 3. sitemap.xml -----------------------------------------------------
    sitemap = docs / "sitemap.xml"
    if sitemap.is_file():
        xml = read_text(sitemap)
        locs = [loc.strip() for loc in SITEMAP_LOC.findall(xml)]
        if not SITEMAP_ROOT.search(xml) or not locs:
            report.fail(f"sitemap.xml exists but looks malformed ({len(locs)} <loc> entries).")
        elif not locs[0].lower().startswith(("http://", "https://")):
            report.fail("sitemap.xml contains non-absolute <loc> URLs (must start with http(s)://).")
        else:
            report.ok(f"sitemap.xml present — {len(locs)} URL(s)")
    elif args.strict:
        report.fail("sitemap.xml is missing (--strict mode).")
    else:
        report.warn("sitemap.xml not found — search engines won't be pinged.")

    # -- 4. robots.txt ------------------------------------------------------
    robots = docs / "robots.txt"
    if robots.is_file():
        if ROBOTS_SITEMAP.search(read_text(robots)):
            report.ok("robots.txt present and references the sitemap")
        else:
            report.warn("robots.txt present but has no 'Sitemap:' line.")
    else:
        report.warn("robots.txt not found (recommended for SEO).")

    # -- 5. feed files -----------------------------------------------------
    feeds = [name for name in FEED_NAMES if (docs / name).is_file()]
    if feeds:
        report.ok("feed file(s) — " + ", ".join(feeds))
    else:
        report.warn("no feed file found (expected one of: " + ", ".join(FEED_NAMES) + ").")

    return report.exit_code(docs)


if __name__ == "__main__":
    sys.exit(main())
