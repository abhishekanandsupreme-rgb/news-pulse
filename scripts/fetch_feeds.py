#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsPulse -- zero-dependency RSS/Atom news + entertainment aggregator.

Fetches every feed in config/feeds.json using ONLY the Python standard
library (no pip, no third-party packages), normalises entries into one
schema, dedupes them, and writes the two data files consumed by the site
builder:

    data/articles.json    every article, newest first
    data/stats.json       per-feed / per-category counts, errors, run history

SUPPORTED FEED FORMATS
    RSS 2.0, RSS 1.0/RDF and Atom, parsed namespace-agnostically by local
    tag name; gzip responses are decoded; malformed XML is rescued when
    possible (bad entities, stray ampersands, illegal control bytes).

USAGE
    python scripts/fetch_feeds.py                  # normal run (cron-friendly)
    python scripts/fetch_feeds.py --limit 10       # cap items per feed
    python scripts/fetch_feeds.py --timeout 20     # per-request timeout
    flags: --config PATH  --data-dir PATH  --limit N  --timeout S
           --retries N   --quiet (no output at all)  --help

EXIT CODES
    0   at least one feed parsed (files written)
    1   every feed failed
    2   bad arguments / unreadable config

Idempotent: safe to re-run any number of times; stats history keeps the
last 30 run summaries. Writes are atomic (tmp file + os.replace).
"""

import os
import re
import sys
import gzip
import json
import hashlib
import datetime as dt
import html as html_lib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# --------------------------------------------------------------------------
# Paths & defaults
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(BASE_DIR, "config", "feeds.json")
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULTS = {
    "timeout_seconds": 10,
    "max_items_per_feed": 25,
    "description_max_chars": 500,
    "retries": 1,                      # extra attempts after the first try
}

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 NewsPulseBot/1.0 "
    "(zero-dependency RSS aggregator)"
)

# --------------------------------------------------------------------------
# Regexes / tables
# --------------------------------------------------------------------------

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
IMG_RE = re.compile(r"<img[^>]+?src=[\"']([^\"']+)[\"']", re.I)
TOKEN_RE = re.compile(r"[a-z]+")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# WordPress feeds append "The post X appeared first on Y." -- drop it.
WP_FOOTER_RE = re.compile(
    r"\s*(the post|this post|this article|this content)[^.]*"
    r"(appeared first on|originally appeared on|is republished from)[^.]*\.?\s*$",
    re.I)

MONTHS = {m.lower(): i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"), 1)}

TZ_ALIASES = {
    "GMT": "+0000", "UT": "+0000", "UTC": "+0000", "Z": "+0000",
    "BST": "+0100", "IST": "+0530", "CET": "+0100", "CEST": "+0200",
    "EET": "+0200", "EEST": "+0300", "MSK": "+0300", "JST": "+0900",
    "KST": "+0900", "HKT": "+0800", "SGT": "+0800",
    "EST": "-0500", "EDT": "-0400", "CST": "-0600", "CDT": "-0500",
    "MST": "-0700", "MDT": "-0600", "PST": "-0800", "PDT": "-0700",
    "AKST": "-0900", "AKDT": "-0800", "HST": "-1000",
    "AEST": "+1000", "AEDT": "+1100", "ACST": "+0930", "NZST": "+1200",
    "NZDT": "+1300", "BRT": "-0300", "BRST": "-0200",
}

RFC822_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M %z",
    "%a, %d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M:%S %z",
    "%d %b %Y %H:%M:%S",
    "%d %b %Y",
    "%a %b %d %H:%M:%S %z %Y",   # 'Fri Sep 11 08:00:00 +0530 2026'
    "%a %b %d %H:%M:%S %Y",      # 'Fri Sep 11 08:00:00 2026'
)

BAD_ENTITIES = {
    "&nbsp;": " ", "&mdash;": " - ", "&ndash;": " - ", "&hellip;": "...",
    "&lsquo;": "'", "&rsquo;": "'", "&ldquo;": '"', "&rdquo;": '"',
    "&middot;": "*", "&bull;": "*", "&copy;": "(c)", "&trade;": "(tm)",
    "&reg;": "(r)", "&pound;": "GBP ", "&euro;": "EUR ", "&sect;": "s",
    "&deg;": " deg", "&para;": "p", "&dagger;": "+", "&laquo;": '"',
    "&raquo;": '"', "&times;": "x", "&divide;": "/", "&frac12;": "1/2",
}

STOPWORDS = frozenset("""
a an the and or but if then than that this these those with without for from
into onto over under after before during while about against between through
above below up down out off again further once here there when where why how
all any both each few more most other some such no nor not only own same so
too very can will just should shall now has have had was were are is am been
being his her hers theirs they them their our ours your yours you we us who
whom which what says said saying amid new newest top best first last two
three may might get gets make makes made take takes took video watch live
update updates news report reports latest full list its it at be by he she
on as of in to do does did per via one also because could would must i me
my won
""".split())

# --------------------------------------------------------------------------
# Small text helpers
# --------------------------------------------------------------------------


def strip_html(text):
    """HTML fragment -> plain text (entities decoded, tags removed)."""
    if not text:
        return ""
    out = html_lib.unescape(html_lib.unescape(str(text)))
    out = TAG_RE.sub(" ", out)
    return WS_RE.sub(" ", out).strip()


def clip(text, limit):
    """Hard-clip text at a word boundary, appending an ellipsis."""
    text = (text or "").strip()
    if limit and len(text) > limit:
        head = text[:limit]
        if " " in head:
            head = head[: head.rfind(" ")]
        text = (head.strip() or text[:limit].strip()) + " ..."
    return text


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]


# --------------------------------------------------------------------------
# Date parsing (RFC 822 for RSS, ISO 8601 for Atom)
# --------------------------------------------------------------------------


def parse_date(raw):
    """Best-effort date string -> aware UTC datetime (or None)."""
    if not raw:
        return None
    s = WS_RE.sub(" ", str(raw)).strip()
    if not s:
        return None

    # --- ISO 8601 (Atom <published>/<updated>) ---------------------------
    iso = s[:-1] + "+00:00" if s.endswith(("Z", "z")) else s
    try:
        d = dt.datetime.fromisoformat(iso)
        return d.astimezone(dt.timezone.utc) if d.tzinfo else d.replace(
            tzinfo=dt.timezone.utc)
    except ValueError:
        pass

    # --- RFC 822 (RSS <pubDate>) -----------------------------------------
    t = re.sub(r"\s*\([^)]*\)\s*$", "", s)      # drop '(India Standard Time)'
    for alias in sorted(TZ_ALIASES, key=len, reverse=True):
        t = re.sub(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(alias),
                   TZ_ALIASES[alias], t)
    for fmt in RFC822_FORMATS:
        try:
            d = dt.datetime.strptime(t, fmt)
        except ValueError:
            continue
        return d.astimezone(dt.timezone.utc) if d.tzinfo else d.replace(
            tzinfo=dt.timezone.utc)

    # --- manual fallback: '12 Sep 2026 10:30' etc. -----------------------
    m = re.match(r"(?:[A-Za-z]{3},?\s+)?(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})"
                 r"(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?", t)
    if m and m.group(2).lower()[:3] in MONTHS:
        day, mon, year, hh, mm, ss = m.groups()
        year_i = int(year)
        if year_i < 100:
            year_i += 2000 if year_i < 70 else 1900
        try:
            return dt.datetime(year_i, MONTHS[mon[:3].lower()], int(day),
                               int(hh or 0), int(mm or 0), int(ss or 0),
                               tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------
# HTTP fetching
# --------------------------------------------------------------------------


class FeedHTTPError(Exception):
    """Non-retryable HTTP status (4xx/5xx) returned for a feed."""

    def __init__(self, code, url):
        super().__init__("HTTP %s for %s" % (code, url))
        self.code = code


def http_get(url, timeout_s, user_agent, attempts):
    """GET a URL, transparently decoding gzip. Retries transport errors."""
    last_err = None
    for _ in range(max(1, attempts)):
        req = urllib.request.Request(url, headers={
            "User-Agent": user_agent,
            "Accept": ("application/rss+xml, application/atom+xml, "
                       "application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"),
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read()
                status = getattr(resp, "status", None) or resp.getcode()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
            if "gzip" in enc or raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass          # mislabelled body; try parsing as-is
            return raw, status
        except urllib.error.HTTPError as e:
            raise FeedHTTPError(e.code, url) from e   # 4xx: don't retry
        except Exception as e:                          # URLError, timeout...
            last_err = e
    raise last_err


# --------------------------------------------------------------------------
# XML parsing
# --------------------------------------------------------------------------


UNBOUND_PREFIX_RE = re.compile(r"<\s*([A-Za-z_][-A-Za-z0-9_.]*):")
DECLARED_NS_RE = re.compile(r"xmlns:([A-Za-z_][-A-Za-z0-9_.]*)\s*=")


def fix_unbound_prefixes(text):
    """Inject xmlns declarations for prefixes the feed forgot to declare.

    Some real feeds (e.g. A.V. Club) use <media:thumbnail>, <sy:updatePeriod>
    ... without ever declaring those namespaces. We patch the root start tag
    with dummy URNs -- harmless because every tag is read by local name.
    """
    used = set(UNBOUND_PREFIX_RE.findall(text))
    used |= set(re.findall(r"\s([A-Za-z_][-A-Za-z0-9_.]*):[\w.-]+="
                           r"[\"'][^\"']*/", text))          # rdf:about="..."
    declared = set(DECLARED_NS_RE.findall(text))
    missing = sorted(p for p in used - declared
                     if p not in ("http", "https", "xml", "xmlns"))
    if not missing:
        return text
    inject = "".join(' xmlns:%s="urn:news-pulse:%s"' % (p, p)
                     for p in missing)
    body = text[text.find("?>") + 2:] if text.startswith("<?xml") else text
    m = re.search(r"<\s*([A-Za-z_][-A-Za-z0-9_.]*)(?=[\s/>])", body)
    if not m:                       # no root element found; give up cleanly
        return text
    pos = (text.find("?>") + 2 if text.startswith("<?xml") else 0) \
        + m.start(1) + len(m.group(1))
    return text[:pos] + inject + text[pos:]


def parse_xml(raw):
    """ET.fromstring with a rescue pass for sloppy real-world feeds."""
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        pass
    text = raw.decode("utf-8", "replace")
    text = re.sub("[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # illegal in XML
    for ent, rep in BAD_ENTITIES.items():
        text = text.replace(ent, rep)
    # neutralise stray unescaped ampersands, keep real entities intact
    text = re.sub(r"&(?![a-zA-Z#][a-zA-Z0-9]{1,10};)", "&amp;", text)
    text = fix_unbound_prefixes(text)
    try:
        return ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as e:
        raise ValueError(
            "feed is not well-formed XML even after cleanup: %s" % e) from e


def localname(tag):
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def child(el, *names):
    for c in el:
        if localname(c.tag) in names:
            return c
    return None


def text_of(el, *names):
    c = child(el, *names)
    return (c.text or "").strip() if c is not None else ""


# --------------------------------------------------------------------------
# Item field extraction (RSS 2.0, RSS 1.0/RDF and Atom)
# --------------------------------------------------------------------------


def extract_link(item):
    rss_link = atom_alt = atom_other = guid = ""
    for c in item:
        lt = localname(c.tag)
        if lt == "link":
            href = (c.get("href") or "").strip()
            rel = (c.get("rel") or "").strip().lower()
            txt = (c.text or "").strip()
            if href and rel in ("", "alternate"):
                atom_alt = atom_alt or href
            elif href:
                atom_other = atom_other or href
            if txt:
                rss_link = rss_link or txt
        elif lt == "guid":
            g = (c.text or "").strip()
            if g[:4].lower() == "http":
                guid = guid or g
    return atom_alt or rss_link or atom_other or guid


def extract_description(item):
    c = child(item, "description", "summary")     # RSS / Atom
    if c is not None and c.text:
        return c.text
    c = child(item, "content")                    # Atom full content
    if c is not None and c.text:
        return c.text
    for d in item.iter():                          # content:encoded
        if localname(d.tag) == "encoded" and d.text:
            return d.text
    return ""


def _is_image_url(url):
    return url.split("?")[0].lower().endswith(IMG_EXT)


def extract_image(item, desc_html):
    # media:thumbnail / media:content / enclosure / first <img> in body
    for el in item.iter():
        lt = localname(el.tag)
        url = (el.get("url") or "").strip()
        typ = (el.get("type") or "").strip().lower()
        if not url.startswith("http"):
            continue
        if lt == "thumbnail":
            return url
        if lt in ("content", "enclosure") and (
                typ.startswith("image") or _is_image_url(url)):
            return url
    m = IMG_RE.search(desc_html or "")
    if m:
        u = html_lib.unescape(m.group(1)).strip()
        if u.startswith("http"):
            return u
    return ""


def item_to_article(item, feed, desc_max):
    """One <item>/<entry> -> article dict, or None if unusable."""
    title = strip_html(text_of(item, "title"))
    link = extract_link(item)
    if not title or not link.startswith("http"):
        return None
    if feed.get("strip_source_suffix"):          # Google News 'Title - Pub'
        parts = title.split(" - ")
        if len(parts) > 1 and 2 <= len(parts[-1].strip()) <= 40:
            title = " - ".join(parts[:-1]).strip() or title

    desc_html = extract_description(item)
    plain = WP_FOOTER_RE.sub("", strip_html(desc_html)).strip()
    description = clip(plain, desc_max)

    published_dt = parse_date(
        text_of(item, "pubdate", "published", "updated", "date", "issued"))
    return {
        "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
        "title": title,
        "link": link,
        "description": description,
        "published": (published_dt.astimezone(dt.timezone.utc).isoformat()
                      if published_dt else None),
        "published_ts": published_dt.timestamp() if published_dt else None,
        "source": feed["name"],
        "source_slug": feed["slug"],
        "category": feed["category"],
        "image": extract_image(item, desc_html),
    }


# --------------------------------------------------------------------------
# Trending keywords (from titles)
# --------------------------------------------------------------------------


def trending_keywords(articles, top=15):
    counts = {}
    for art in articles:
        for word in TOKEN_RE.findall(art["title"].lower()):
            if len(word) < 4 or word in STOPWORDS:
                continue
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return [{"word": w, "count": c} for w, c in ranked]


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------


def write_json(path, obj):
    """Atomic JSON write (tmp file + replace) so readers never see halves."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    opts = {"config": DEFAULT_CONFIG, "data-dir": DEFAULT_DATA_DIR,
            "limit": None, "timeout": None, "retries": None, "quiet": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--config", "--data-dir", "--limit", "--timeout",
                 "--retries") and i + 1 < len(argv):
            opts[a.lstrip("-")] = argv[i + 1]
            i += 2
        elif a in ("-q", "--quiet"):
            opts["quiet"] = True
            i += 1
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print("unknown argument: %s\n\n%s" % (a, __doc__), file=sys.stderr)
            return 2

    # ---- config -----------------------------------------------------------
    try:
        with open(opts["config"], "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception as e:
        print("ERROR: cannot read config %s -> %s" % (opts["config"], e),
              file=sys.stderr)
        return 2
    settings = dict(DEFAULTS)
    settings.update(cfg.get("settings") or {})
    try:
        if opts["timeout"] is not None:
            settings["timeout_seconds"] = max(3.0, float(opts["timeout"]))
        if opts["retries"] is not None:
            settings["retries"] = max(0, int(opts["retries"]))
        if opts["limit"] is not None:
            settings["max_items_per_feed"] = max(1, int(opts["limit"]))
    except ValueError:
        print("ERROR: --limit/--timeout/--retries expect numbers",
              file=sys.stderr)
        return 2
    feeds = cfg.get("feeds") or []
    if not isinstance(feeds, list) or not feeds:
        print("ERROR: config has no feeds list", file=sys.stderr)
        return 2

    log = print if not opts["quiet"] else (lambda *a, **k: None)
    log("[news-pulse] fetching %d feeds ..." % len(feeds))

    # ---- fetch every feed --------------------------------------------------
    started = dt.datetime.now(dt.timezone.utc)
    articles, per_feed, failures = [], [], []
    seen_links, seen_titles = set(), {}

    for feed in feeds:
        url = (feed.get("url") or "").strip()
        name = (feed.get("name") or url or "unnamed feed").strip()
        slug = (feed.get("slug") or slugify(name) or "feed")
        category = (feed.get("category") or "news").strip().lower()
        rec = {"slug": slug, "name": name, "url": url, "category": category,
               "ok": False, "http_status": None, "articles": 0, "error": None}
        per_feed.append(rec)
        if not url:
            rec["error"] = "config error: missing url"
            failures.append(dict(rec))
            log("  FAIL  %-30s %-14s %s"
                % (name[:30], category[:14], rec["error"]))
            continue
        try:
            timeout_s = float(feed.get("timeout_seconds")
                              or settings["timeout_seconds"])
            ua = feed.get("user_agent") or settings.get("user_agent") \
                or DEFAULT_UA
            raw, status = http_get(url, timeout_s, ua,
                                   int(settings["retries"]) + 1)
            rec["http_status"] = status
            root = parse_xml(raw)
            items = [el for el in root.iter()
                     if localname(el.tag) in ("item", "entry")]
            if items and not feed.get("name"):
                channel = next(
                    (e for e in root.iter() if localname(e.tag) == "channel"),
                    next((e for e in root.iter() if localname(e.tag) == "feed"),
                         root))
                t = strip_html(text_of(channel, "title"))
                if t:
                    name = t
                    rec["name"] = name
            norm_feed = {"name": name, "slug": slug, "category": category,
                         "strip_source_suffix": bool(
                             feed.get("strip_source_suffix"))}
            cap = int(feed.get("max_items") or settings["max_items_per_feed"])
            src_titles = seen_titles.setdefault(slug, set())
            got = 0
            for it in items:
                if got >= cap:
                    break
                art = item_to_article(it, norm_feed,
                                      int(settings["description_max_chars"]))
                if not art:
                    continue
                key_link = art["link"]
                key_title = art["title"].lower()
                if key_link in seen_links or key_title in src_titles:
                    continue
                seen_links.add(key_link)
                src_titles.add(key_title)
                articles.append(art)
                got += 1
            rec["ok"] = True
            rec["articles"] = got
            if not items:
                rec["error"] = "parsed, but no <item>/<entry> elements"
            log("  OK    %-30s %-14s %3d %s"
                % (name[:30], category[:14], got, rec["error"] or ""))
        except FeedHTTPError as e:
            rec["error"] = "HTTP %s" % e.code
            rec["http_status"] = e.code
            failures.append(dict(rec))
            log("  FAIL  %-30s %-14s %s"
                % (name[:30], category[:14], rec["error"]))
        except Exception as e:
            rec["error"] = clip("%s: %s" % (type(e).__name__, e), 200)
            failures.append(dict(rec))
            log("  FAIL  %-30s %-14s %s"
                % (name[:30], category[:14], rec["error"]))

    # ---- aggregate & write -------------------------------------------------
    articles.sort(key=lambda a: a["published_ts"] or 0.0, reverse=True)
    categories = {}
    for a in articles:
        categories[a["category"]] = categories.get(a["category"], 0) + 1
    finished = dt.datetime.now(dt.timezone.utc)
    duration = round((finished - started).total_seconds(), 2)
    feeds_ok = len(per_feed) - len(failures)

    articles_path = os.path.join(opts["data-dir"], "articles.json")
    stats_path = os.path.join(opts["data-dir"], "stats.json")
    write_json(articles_path, {
        "generated_at": finished.isoformat(),
        "count": len(articles),
        "articles": articles,
    })

    history = []
    try:
        with open(stats_path, "r", encoding="utf-8") as fh:
            history = (json.load(fh) or {}).get("history") or []
    except Exception:
        history = []
    if not isinstance(history, list):
        history = []
    history.append({"last_run": finished.isoformat(),
                    "duration_seconds": duration,
                    "feeds_ok": feeds_ok,
                    "feeds_failed": len(failures),
                    "articles": len(articles)})
    write_json(stats_path, {
        "version": 1,
        "last_run": finished.isoformat(),
        "duration_seconds": duration,
        "config": {
            "config_file": os.path.abspath(opts["config"]),
            "timeout_seconds": settings["timeout_seconds"],
            "max_items_per_feed": settings["max_items_per_feed"],
            "description_max_chars": settings["description_max_chars"],
            "retries": settings["retries"],
            "user_agent": settings.get("user_agent") or DEFAULT_UA,
        },
        "totals": {"feeds": len(feeds), "feeds_ok": feeds_ok,
                   "feeds_failed": len(failures), "articles": len(articles)},
        "categories": categories,
        "sources": per_feed,
        "failures": failures,
        "trending_keywords": trending_keywords(articles),
        "history": history[-30:],
    })

    log("[news-pulse] %d articles (%s) from %d/%d feeds in %.1fs"
        % (len(articles),
           ", ".join("%s %d" % kv for kv in sorted(categories.items())),
           feeds_ok, len(feeds), duration))
    log("[news-pulse] wrote %s (%.0f KB)"
        % (articles_path, os.path.getsize(articles_path) / 1024.0))
    log("[news-pulse] wrote %s (%d ok, %d failed)"
        % (stats_path, feeds_ok, len(failures)))
    if articles:
        log("[news-pulse] newest: %s -- %s (%s)"
            % (articles[0]["source"], articles[0]["title"][:80],
               articles[0]["published"] or "no date"))
    return 0 if feeds_ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
