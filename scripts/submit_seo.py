#!/usr/bin/env python3
"""
submit_seo.py - free SEO submission toolkit for NewsPulse (stdlib only, Python 3.8+).

Commands (all free, no paid APIs):
  init        Generate an IndexNow key + key file, print hosting instructions.
  crawl       Crawl the live site (same-host links only) and save a URL list.
  sitemap     Build a sitemap.xml (max 50,000 URLs per file - sitemaps.org).
  newsmap     Build a Google News sitemap (max 1,000 URLs, last 48h items).
  robots      Print a robots.txt snippet (with Sitemap: line).
  submit      Submit URLs to IndexNow (Bing + participating engines).
  verify      Check key file + sitemap are reachable on the live site.

What it deliberately does NOT do (verified facts, 2026-09):
  * NO Google sitemap "ping" - /ping?sitemap= was deprecated by Google in
    June 2023 and now returns 404. Submit via Search Console instead.
  * NO Google Indexing API calls - that API is only for JobPosting /
    BroadcastEvent pages; other use violates Google's spam policies.
  * NO Google News / Publisher Center submission - manual submission was
    removed (fully automatic since March 2025); eligibility is algorithmic.

IndexNow facts used (from indexnow.org/documentation, verified 2026-09):
  * GET  https://<engine>/indexnow?url=<url>&key=<key>          single URL
  * POST https://<engine>/indexnow  {"host","key","urlList"}    up to 10,000 URLs
  * Key: 8-128 chars of [a-zA-Z0-9-], hosted as UTF-8 text file {key}.txt.
  * keyLocation must be given when the key file is NOT at the host root -
    required for GitHub Pages project sites such as
    https://user.github.io/news-pulse/  (Option 2 in the official docs).

Usage examples:
  python scripts/submit_seo.py init
  python scripts/submit_seo.py crawl
  python scripts/submit_seo.py sitemap --urls urls.txt --out sitemap.xml
  python scripts/submit_seo.py submit --urls urls.txt
  python scripts/submit_seo.py verify
  python scripts/submit_seo.py newsmap --items-json data/articles.json
Run `python scripts/submit_seo.py <command> --help` for per-command options.
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser

DEFAULT_SITE = "https://abhishekanandsupreme-rgb.github.io/news-pulse/"
DEFAULT_ENGINE = "https://api.indexnow.org"
HERE = os.path.dirname(os.path.abspath(__file__))
KEYFILE_DIR = os.path.join(HERE, "..", "public")
USER_AGENT = (
    "Mozilla/5.0 (compatible; NewsPulseSEOSubmitter/1.0; "
    "+https://abhishekanandsupreme-rgb.github.io/news-pulse/)"
)

# ---------------------------------------------------------------- helpers


def log(msg):
    print(msg, flush=True)


def die(msg, code=1):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(code)


def http_get(url, timeout=15):
    """GET a URL, return (status_code, bytes_body) without raising on HTTP errors."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if e.fp else b"")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e).encode("utf-8", "replace")


def http_post_json(url, payload, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if e.fp else b"")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e).encode("utf-8", "replace")


def site_host(site_url):
    return urllib.parse.urlsplit(site_url).netloc


def site_path_prefix(site_url):
    """Path prefix for GitHub Pages project sites ('' or '/news-pulse')."""
    path = urllib.parse.urlsplit(site_url).path or "/"
    m = re.match(r"^/([^/]+)/?$", path)
    return "/" + m.group(1) if m else ""


def normalize_site(site_url):
    """Ensure scheme, strip trailing index.html, keep trailing slash on dirs."""
    p = urllib.parse.urlsplit(site_url)
    if not p.scheme:
        p = p._replace(scheme="https")
    path = p.path or ""
    if path.endswith("index.html"):
        path = path[: -len("index.html")]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, "", ""))


def read_url_list(path):
    """Read one-URL-per-line file; '#' comments and blank lines skipped."""
    if not os.path.isfile(path):
        die("URL list not found: %s" % path)
    urls, seen = [], set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line not in seen:
                seen.add(line)
                urls.append(line)
    return urls


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    log("wrote %s (%d bytes)" % (path, len(text.encode("utf-8"))))


# ----------------------------------------------------------- state file


def state_path(args):
    return os.path.abspath(args.state)


def write_state(args, state):
    os.makedirs(os.path.dirname(state_path(args)) or ".", exist_ok=True)
    with open(state_path(args), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    log("state saved -> %s" % state_path(args))


def load_state(args):
    if os.path.isfile(state_path(args)):
        try:
            with open(state_path(args), "r", encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            return {}
    return {}


def resolve_key(args):
    """Key from --key, or from saved state, else die."""
    if args.key:
        return args.key.strip()
    st = load_state(args)
    if st.get("indexnow_key"):
        return st["indexnow_key"]
    die("No IndexNow key. Run `submit_seo.py init` or pass --key <KEY>.")


# ------------------------------------------------------------------ init


def cmd_init(args):
    """Generate an IndexNow key + key file, print hosting instructions."""
    key = uuid.uuid4().hex  # 32 hex chars, within the allowed [a-zA-Z0-9-] set
    out_dir = os.path.abspath(args.key_dir)
    key_file = os.path.join(out_dir, key + ".txt")
    os.makedirs(out_dir, exist_ok=True)
    with open(key_file, "w", encoding="utf-8", newline="") as f:
        f.write(key)
    log("IndexNow key generated: %s" % key)
    log("Key file written     : %s" % key_file)
    log("")
    site = normalize_site(args.site)
    prefix = site_path_prefix(site)
    log("NEXT STEPS (do these in the news-pulse repo, then push):")
    log("  1. Copy the key file into the folder served as the site root,")
    log("     e.g.  news-pulse/public/%s.txt  (or wherever index.html lives)." % key)
    log("  2. Commit & push. GitHub Pages will serve it at your site URL.")
    if prefix:
        log("     Your site is a GitHub Pages PROJECT site (path %s/)." % prefix)
        log("     Because the key file is NOT at the host root, every submission")
        log("     must pass keyLocation (this script does that automatically).")
        key_location = site.rstrip("/") + "/%s.txt" % key
    else:
        key_location = "https://%s/%s.txt" % (site_host(site), key)
    log("  3. After deploy, confirm the key file loads:")
    log("       %s" % key_location)
    log("     (or run: python scripts/submit_seo.py verify)")
    log("  4. Keep the key secret-ish; only you and the search engines should know it.")
    write_state(args, {"indexnow_key": key, "key_location": key_location})
    return 0


# --------------------------------------------------------------- submit


def indexnow_submit(engine, key, urls, site_url, key_location=None, dry=False):
    """Submit URLs. GET for a single URL, batch POST (10k chunks) otherwise."""
    host = site_host(site_url)
    if dry:
        payload = {
            "host": host,
            "key": key,
            "keyLocation": key_location,
            "urlList": urls[:3] + (["...(%d total)" % len(urls)] if len(urls) > 3 else []),
        }
        log("[dry-run] would POST %s" % (engine.rstrip("/") + "/indexnow"))
        log("[dry-run] payload=%s" % json.dumps(payload))
        return [("DRY", "dry-run (nothing was sent)", len(urls), 0)]
    if len(urls) == 1:
        q = urllib.parse.urlencode({"url": urls[0], "key": key})
        if key_location:
            q += "&keyLocation=" + urllib.parse.quote(key_location, safe="")
        status, body = http_get(engine.rstrip("/") + "/indexnow?" + q)
        return [(status, body.decode("utf-8", "replace"), 1, 0)]
    results = []
    for i in range(0, len(urls), 10000):  # API hard limit: 10,000 URLs per POST
        chunk = urls[i : i + 10000]
        payload = {"host": host, "key": key, "urlList": chunk}
        if key_location:
            payload["keyLocation"] = key_location
        status, body = http_post_json(engine.rstrip("/") + "/indexnow", payload)
        results.append((status, body.decode("utf-8", "replace"), len(chunk), i))
    return results


def cmd_submit(args):
    key = resolve_key(args)
    site = normalize_site(args.site)
    key_location = args.key_location
    if not key_location:
        key_location = load_state(args).get("key_location")
    if not key_location:
        prefix = site_path_prefix(site)
        if prefix:  # project site -> key file lives under the project path
            key_location = site.rstrip("/") + "/%s.txt" % key
        # host-root sites need no keyLocation (Option 1)
    urls = []
    if args.urls:
        urls = read_url_list(args.urls)
    elif args.url:
        urls = [args.url]
    if not urls:
        die("Nothing to submit. Pass --urls <file> or --url <url>.")
    host = site_host(site)
    bad = [u for u in urls if urllib.parse.urlsplit(u).netloc != host]
    if bad:
        log("WARNING: dropped %d URL(s) on a different host (%s) - IndexNow "
            "rejects them (HTTP 422). Example: %s" % (len(bad), host, bad[0]))
        urls = [u for u in urls if urllib.parse.urlsplit(u).netloc == host]
    if not urls:
        die("No URLs left on host %s." % host)
    log("Submitting %d URL(s) to %s (host=%s)" % (len(urls), args.engine, host))
    if key_location:
        log("keyLocation=%s" % key_location)
    results = indexnow_submit(
        args.engine, key, urls, site, key_location=key_location, dry=args.dry_run
    )
    ok = True
    for status, body, count, offset in results:
        if status == "DRY":
            log("  [DRY-RUN] %d URL(s) would be submitted (nothing was sent)" % count)
            continue
        tag = "OK" if status == 200 else ("RECEIVED/PENDING" if status == 202 else "FAIL")
        extra = "" if status in (200, 202) else " - " + body[:160]
        log("  [%s] HTTP %s - %d URL(s) @offset %d%s" % (tag, status, count, offset, extra))
        if status is None:
            log("  (network error - see message above; nothing was submitted)")
        if status not in (200, 202):
            ok = False
    log("")
    log("Interpreting responses (per indexnow.org):")
    log("  200 = accepted | 202 = received, key validation pending")
    log("  400 = bad key/file | 422 = URL not on this host / schema mismatch")
    log("  429 = too many submissions (potential spam) - slow down")
    log("NOTE: 200 only means 'received', not an indexing or ranking promise.")
    log("Google is NOT notified by IndexNow - submit the sitemap once in Google")
    log("Search Console, then keep <lastmod> accurate in sitemap.xml.")
    return 0 if ok else 2


# ---------------------------------------------------------------- crawl


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def cmd_crawl(args):
    """Same-origin, bounded crawl of the live site -> URL list file."""
    site = normalize_site(args.site)
    prefix = site.rstrip("/")
    to_visit, seen, found = [site], set(), []
    while to_visit and len(seen) < args.max_pages:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        status, body = http_get(url)
        if status != 200 or not body:
            log("  [%s] %s" % (status, url))
            continue
        log("  [200] %s" % url)
        found.append(url)
        if b"<html" not in body[:1024].lower():
            continue
        p = LinkExtractor()
        try:
            p.feed(body.decode("utf-8", "replace"))
        except Exception:
            continue
        for href in p.links:
            u = urllib.parse.urldefrag(urllib.parse.urljoin(url, href))[0]
            if u.startswith(("mailto:", "javascript:", "tel:")):
                continue
            if not u.startswith("http"):
                continue
            if urllib.parse.urlsplit(u).netloc != site_host(site):
                continue  # external link-outs are never followed
            if u == site or u == prefix or u.startswith(prefix + "/"):
                if u not in seen and u not in to_visit:
                    to_visit.append(u)
    if not found:
        die("Crawl found no live pages. Is the site deployed? (First tried %s)" % site)
    out = args.out or "urls.txt"
    write_text(
        out,
        "# NewsPulse URL list - regenerate with: submit_seo.py crawl\n" + "\n".join(found) + "\n",
    )
    log("")
    log("Found %d page(s). URL list saved to %s" % (len(found), out))
    log("Next: submit_seo.py sitemap --urls %s --out sitemap.xml" % out)
    return 0


# ------------------------------------------------------------- sitemaps


def urls_from_file_or_args(args):
    urls = []
    if getattr(args, "urls", None):
        urls.extend(read_url_list(args.urls))
    for u in getattr(args, "url", None) or []:
        urls.append(u)
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def xml_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cmd_sitemap(args):
    """Build a plain sitemap.xml. Splits at 50,000 URLs (sitemaps.org limit)."""
    urls = urls_from_file_or_args(args)
    if not urls:
        die("No URLs. Pass --urls <file> (e.g. from `crawl`) and/or --url.")
    lastmod = getattr(args, "lastmod", None)
    if lastmod and not re.match(r"^\d{4}-\d{2}-\d{2}$", lastmod):
        die("--lastmod must be YYYY-MM-DD (Google only trusts accurate lastmod).")
    parts = [urls[i : i + 50000] for i in range(0, len(urls), 50000)]
    outs = []
    for idx, part in enumerate(parts):
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for u in part:
            lines.append("  <url>")
            lines.append("    <loc>%s</loc>" % xml_escape(u))
            if lastmod:
                lines.append("    <lastmod>%s</lastmod>" % lastmod)
            lines.append("  </url>")
        lines.append("</urlset>")
        out = args.out if len(parts) == 1 else re.sub(r"(\.xml)$", "-%d\\1" % (idx + 1), args.out)
        write_text(out, "\n".join(lines) + "\n")
        outs.append(out)
    log("")
    log("Sitemap written: %s (%d URL(s))." % (", ".join(outs), len(urls)))
    log("NOTE: <lastmod> is only respected when ACCURATE - Google ignores it")
    log("otherwise, and ignores <changefreq>/<priority> entirely.")
    log("Google: submit once in Search Console (the old /ping?sitemap= endpoint")
    log("is dead - 404 since 2023).")
    return 0


def cmd_robots(args):
    site = normalize_site(args.site)
    sitemap_url = args.sitemap or (site.rstrip("/") + "/sitemap.xml")
    txt = "User-agent: *\nAllow: /\n\nSitemap: %s\n" % sitemap_url
    if args.out:
        write_text(args.out, txt)
        log("robots.txt written to %s - copy it to your site root." % args.out)
    else:
        print(txt, end="")
    log("(Keep any existing robots rules; just ensure the Sitemap: line exists.)")
    return 0


DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
)


def cmd_newsmap(args):
    """
    Build a Google News sitemap from a JSON items file.

    Accepts a JSON array of objects, {"items": [...]}, or JSONL.
    Each object needs a URL (url|link|article_url|source_url) and a
    publication date (published|date|pubDate|published_at; ISO 8601 or RFC 822).
    Google News sitemap rules: max 1,000 URLs, articles from the last 48 hours.
    """
    if not args.items_json:
        die("Pass --items-json <file> (data export with article URLs + dates).")
    if not os.path.isfile(args.items_json):
        die("Items file not found: %s" % args.items_json)
    raw = open(args.items_json, "r", encoding="utf-8").read().strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            items = parsed
        else:
            items = parsed.get("items") or parsed.get("articles") or []
    except ValueError:
        items = []
        for line in raw.splitlines():
            if line.strip():
                items.append(json.loads(line))

    def pick(d, keys):
        for k in keys:
            if isinstance(d, dict) and d.get(k):
                return d[k]
        return None

    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=48)
    entries = []
    for it in items:
        if not isinstance(it, dict):
            continue
        u = pick(it, ("url", "link", "article_url", "source_url"))
        d = pick(it, ("published", "date", "pubDate", "published_at", "pubdate"))
        if not u:
            continue
        when = None
        if d:
            for fmt in DATE_FORMATS:
                try:
                    when = _dt.datetime.strptime(str(d).strip(), fmt)
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=_dt.timezone.utc)
                    break
                except ValueError:
                    continue
        entries.append((u, when))
    fresh = [(u, w) for u, w in entries if w is None or w >= cutoff]
    stale = len(entries) - len(fresh)
    if stale:
        log("Skipped %d item(s) older than 48h (Google News sitemap rule)." % stale)
    if not fresh:
        log("No items dated within the last 48 hours - writing empty news sitemap.")
    fresh = fresh[:1000]  # hard limit: 1,000 URLs per news sitemap
    titles = {}
    for it in items:
        if isinstance(it, dict):
            u = pick(it, ("url", "link", "article_url", "source_url"))
            if u:
                titles[u] = str(pick(it, ("title", "name", "headline")) or "")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]
    for u, w in fresh:
        lines.append("  <url>")
        lines.append("    <loc>%s</loc>" % xml_escape(u))
        if w:
            lines.append("    <news:news>")
            lines.append("      <news:publication>")
            lines.append("        <news:name>NewsPulse</news:name>")
            lines.append("        <news:language>en</news:language>")
            lines.append("      </news:publication>")
            lines.append(
                "      <news:publication_date>%s</news:publication_date>"
                % w.strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            if titles.get(u):
                lines.append("      <news:title>%s</news:title>" % xml_escape(titles[u]))
            lines.append("    </news:news>")
        lines.append("  </url>")
    lines.append("</urlset>")
    write_text(args.out or "news-sitemap.xml", "\n".join(lines) + "\n")
    log("News sitemap written (%d URLs). Rules honored: <=1,000 URLs, <=48h old." % len(fresh))
    log("Caveat: Google News wants ORIGINAL reporting on your pages; a pure")
    log("link-out aggregator is unlikely to be eligible. Treat this as future")
    log("work for editorial pages you write yourself.")
    return 0


# -------------------------------------------------------------- verify


def cmd_verify(args):
    """Check key file + sitemap are reachable on the live site."""
    site = normalize_site(args.site)
    ok = True
    key = args.key or resolve_key(args)
    st = load_state(args)
    key_location = args.key_location or st.get("key_location")
    if not key_location:
        prefix = site_path_prefix(site)
        if prefix:
            key_location = site.rstrip("/") + "/%s.txt" % key
        else:
            key_location = "https://%s/%s.txt" % (site_host(site), key)
    log("Checking site root : %s" % site)
    s, _ = http_get(site)
    if s == 200:
        log("  -> OK")
    else:
        log("  -> HTTP %s (site not live yet? deploy first)" % s)
        ok = False
    log("Checking key file  : %s" % key_location)
    s, b = http_get(key_location)
    if s == 200 and b.decode("utf-8", "replace").strip() == key:
        log("  -> OK (contains key)")
    else:
        ok = False
        log("  -> HTTP %s - key file missing or content mismatch." % s)
        log("     Fix: copy the key file into your site-root folder, push, wait")
        log("     for GitHub Pages to rebuild (usually <2 min), re-run verify.")
    sitemap_url = args.sitemap or (site.rstrip("/") + "/sitemap.xml")
    log("Checking sitemap   : %s" % sitemap_url)
    s, b = http_get(sitemap_url)
    if s == 200 and b"<urlset" in b:
        log("  -> OK")
    else:
        log("  -> HTTP %s (run `sitemap` and deploy it if missing)" % s)
        ok = False
    log("")
    if ok:
        log("ALL CHECKS PASSED - ready to submit URLs to IndexNow.")
    else:
        log("Some checks failed. Fix the items above, then re-run.")
    return 0 if ok else 2


# ---------------------------------------------------------------- main


def build_parser():
    p = argparse.ArgumentParser(
        prog="submit_seo.py",
        description="Free SEO submission toolkit for NewsPulse: IndexNow, "
                    "sitemaps, robots, verification. Stdlib only.",
    )
    p.add_argument(
        "--site",
        default=DEFAULT_SITE,
        help="site origin incl. project path (default: %(default)s)",
    )
    p.add_argument(
        "--state",
        default=os.path.join(HERE, "submit_seo.state.json"),
        help=argparse.SUPPRESS,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="generate IndexNow key + key file")
    sp.add_argument("--key-dir", default=KEYFILE_DIR)
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("crawl", help="crawl live site -> urls.txt")
    sp.add_argument("--out", default="urls.txt")
    sp.add_argument("--max-pages", type=int, default=200)
    sp.set_defaults(fn=cmd_crawl)

    sp = sub.add_parser("sitemap", help="build sitemap.xml from a URL list")
    sp.add_argument("--urls", help="file with one URL per line")
    sp.add_argument("--url", action="append", help="single URL (repeatable)")
    sp.add_argument("--out", default="sitemap.xml")
    sp.add_argument("--lastmod", help="YYYY-MM-DD; use ONLY if genuinely accurate")
    sp.set_defaults(fn=cmd_sitemap)

    sp = sub.add_parser("newsmap", help="build Google News sitemap (<=1000, 48h)")
    sp.add_argument("--items-json", required=True)
    sp.add_argument("--out", default="news-sitemap.xml")
    sp.set_defaults(fn=cmd_newsmap)

    sp = sub.add_parser("robots", help="print robots.txt snippet")
    sp.add_argument("--sitemap")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_robots)

    sp = sub.add_parser("submit", help="submit URLs to IndexNow")
    sp.add_argument("--urls", help="file with one URL per line")
    sp.add_argument("--url", help="single URL")
    sp.add_argument(
        "--engine",
        default=DEFAULT_ENGINE,
        help="IndexNow endpoint (default %(default)s; also https://www.bing.com/indexnow)",
    )
    sp.add_argument("--key", help="IndexNow key (else from state)")
    sp.add_argument("--key-location", help="URL of {key}.txt if not at host root")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(fn=cmd_submit)

    sp = sub.add_parser("verify", help="check key file + sitemap live")
    sp.add_argument("--key", help="IndexNow key (else from state)")
    sp.add_argument("--key-location")
    sp.add_argument("--sitemap")
    sp.set_defaults(fn=cmd_verify)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
