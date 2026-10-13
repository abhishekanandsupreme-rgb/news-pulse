#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py -- NewsPulse static site generator (Python 3.11 stdlib only).

Turns data/articles.json (+ data/stats.json for trending keywords and
config/site-config.json for branding/ads) into a complete, SEO-ready,
ad-slot-ready multi-page news magazine in docs/:

    index.html                    homepage: hero, trending strip, latest,
                                  per-category blocks
    article/<id>/index.html      one page per story (the long-tail SEO)
    category/<slug>/…             per-category hubs, paginated
    latest/…                      every story, paginated
    about/index.html              about / editorial policy / contact
    404.html                      GitHub Pages not-found page
    assets/style.css              the single stylesheet (no JS, no CDNs)
    sitemap.xml                   every page URL, absolute, accurate lastmod
    robots.txt                    allow-all + "Sitemap:" line
    rss.xml                       latest N stories pointing at OUR pages
    <indexnow-key>.txt            copied from public/ (engines verify it)
    ads.txt                       only when configured (non-empty) in config
    .nojekyll                     Pages artifact safety

Design constraints honored:
  * Zero third-party dependencies; no network access at build time.
  * Deterministic: every timestamp comes from the data snapshot, never
    from the wall clock, so rebuilding the same input yields the same
    bytes (CI-friendly, cache-friendly).
  * Null images render as per-category gradient placeholders -- never an
    external placeholder service.
  * Ads: when config ads.adsense_client + slot ids are set, real AdSense
    units are emitted; otherwise clearly-labelled reserved slots are.

Data fallback chain (first match wins):
  1. --data / config data_file  (the real fetched snapshot)
  2. --sample-data / config sample_data_file  (offline dev/CI fallback)
  3. empty state (a valid, honest "no stories yet" site)
A *present but unparseable* real data file is a hard error -- the site
must never silently ship stale or fake news.

Usage:
    python scripts/build_site.py                # normal CI run
    python scripts/build_site.py --quiet
    python scripts/build_site.py --data data/sample-articles.json --out DIR
    Flags: --config --data --sample-data --out --quiet
    Relative paths resolve against the repo root, not the current dir.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import shutil
import sys
import time
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Tunables / fallbacks (config keys override these)
# ---------------------------------------------------------------------------

DEFAULTS = {
    "site_name": "NewsPulse",
    "tagline": "Your daily pulse on news, tech and entertainment",
    "description": "An automated news magazine.",
    "base_url": "",
    "contact_email": "",
    "language": "en",
    "data_file": "data/articles.json",
    "sample_data_file": "data/sample-articles.json",
    "output_dir": "docs",
    "articles_per_page": 12,
    "trending_count": 10,
    "related_count": 6,
    "feed_items": 50,
}

FRONT_DEFAULTS = {
    "hero": 1,
    "secondary": 4,
    "latest_rows": 12,
    "per_category": 3,
    "category_blocks": True,
}

FALLBACK_COLOR = "#475569"          # unknown-category accent
KEYFILE_DIR = "public"              # IndexNow key files live here
PRESERVE_FILES = ("CNAME",)         # survive the docs/ wipe (Pages custom domain)
AFFILIATE_FILE = "config/affiliate-products.json"

ID_SAFE_RE = re.compile(r"^[0-9a-f]{16}$")
SLUG_SAFE_RE = re.compile(r"^[a-z0-9-]+$")
WS_RE = re.compile(r"\s+")

UTC = dt.timezone.utc


# ---------------------------------------------------------------------------
# Small text / format helpers
# ---------------------------------------------------------------------------


def esc(text) -> str:
    """HTML-escape for element text AND attributes."""
    return html.escape(str(text if text is not None else ""), quote=True)


def xesc(text) -> str:
    """XML-escape for text nodes (sitemap, rss)."""
    return (html.escape(str(text if text is not None else ""), quote=False)
            .replace('"', "&quot;"))


def clip(text: str, limit: int) -> str:
    """Word-boundary clip with ellipsis (meta descriptions etc.)."""
    text = WS_RE.sub(" ", str(text or "")).strip()
    if limit and len(text) > limit:
        head = text[:limit]
        if " " in head:
            head = head[: head.rfind(" ")]
        text = (head.strip() or text[:limit].strip()) + " …"
    return text


def shade(hex_color: str, factor: float = 0.45) -> str:
    """Darken a #rrggbb color for gradient endpoints."""
    h = (hex_color or FALLBACK_COLOR).lstrip("#")
    if len(h) != 6:
        h = FALLBACK_COLOR.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * factor))) for c in (r, g, b))


def gradient(color: str) -> str:
    return "linear-gradient(135deg, %s 0%%, %s 100%%)" % (color, shade(color))


def fmt_datetime(ts) -> str:
    """epoch -> '13 Sep 2026, 03:10 UTC'."""
    if not ts:
        return "date unknown"
    return dt.datetime.fromtimestamp(float(ts), UTC).strftime("%d %b %Y, %H:%M UTC")


def fmt_date_short(ts) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(float(ts), UTC).strftime("%d %b %Y")


def rel_time(ts, now_ts) -> str:
    if not ts:
        return ""
    delta = now_ts - float(ts)
    if delta < 0:
        return "just now"
    mins = int(delta // 60)
    if mins < 60:
        return "%dm ago" % max(mins, 1)
    hours = mins // 60
    if hours < 24:
        return "%dh ago" % hours
    days = hours // 24
    if days < 7:
        return "%dd ago" % days
    return fmt_date_short(ts)


def rfc822(ts) -> str:
    return email.utils.format_datetime(dt.datetime.fromtimestamp(float(ts), UTC))


def iso_date(ts) -> str:
    """Date for sitemap <lastmod>. Undated stories return "" so the entry is
    omitted instead of claiming the Unix epoch."""
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(float(ts), UTC).date().isoformat()


def iso_datetime(ts) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(float(ts), UTC).isoformat()


def time_attr(art) -> str:
    """The datetime attribute only when a real timestamp is known: an empty
    attribute is invalid HTML and an epoch stamp contradicts the
    'date unknown' text rendered beside it."""
    stamp = art["published"] or iso_datetime(art["published_ts"])
    return ' datetime="%s"' % esc(stamp) if stamp else ""


def chunked(seq, size):
    size = max(1, int(size or 1))
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def jsonld_safe(obj) -> str:
    """Serialize JSON-LD so it can never break out of its <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# Config & data loading
# ---------------------------------------------------------------------------


def deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class BuildError(Exception):
    pass


class Config:
    """site-config.json with defaults filled in + derived helpers."""

    def __init__(self, raw: dict, repo: Path):
        merged = deep_merge(DEFAULTS, raw or {})
        self.repo = repo
        self.site_name = str(merged["site_name"])
        self.tagline = str(merged["tagline"])
        self.description = str(merged["description"])
        self.base_url = str(merged["base_url"]).rstrip("/")
        self.contact_email = str(merged["contact_email"])
        self.language = str(merged["language"] or "en")
        self.articles_per_page = int(merged["articles_per_page"] or 12)
        self.trending_count = int(merged["trending_count"] or 10)
        self.related_count = int(merged["related_count"] or 6)
        self.feed_items = int(merged["feed_items"] or 50)

        front = deep_merge(FRONT_DEFAULTS, merged.get("front_page") or {})
        self.front = front

        # ordered slug -> {label, color}
        self.categories = {}
        for cat in merged.get("categories") or []:
            slug = str(cat.get("slug") or "").strip().lower()
            if SLUG_SAFE_RE.match(slug):
                self.categories[slug] = {
                    "label": str(cat.get("label") or slug.title()),
                    "color": str(cat.get("color") or FALLBACK_COLOR),
                }

        ads = merged.get("ads") or {}
        self.ads_client = str(ads.get("adsense_client") or "").strip()
        slots = ads.get("slots") or {}
        self.ad_slots = {name: str(v or "").strip()
                         for name, v in slots.items()}
        self.ads_txt = str(ads.get("ads_txt") or "").strip()

        self.data_file = str(merged["data_file"])
        self.sample_data_file = str(merged["sample_data_file"])
        self.output_dir = str(merged["output_dir"])

        # URL plumbing -----------------------------------------------------
        self.prefix = urllib.parse.urlsplit(self.base_url).path.rstrip("/")
        if not self.base_url:
            raise BuildError("site-config.json needs a base_url")

    def label(self, slug: str) -> str:
        cat = self.categories.get(slug)
        return cat["label"] if cat else slug.replace("-", " ").title()

    def color(self, slug: str) -> str:
        cat = self.categories.get(slug)
        return cat["color"] if cat else FALLBACK_COLOR

    def site(self, path: str) -> str:
        """Root-relative URL for internal links ('/news-pulse/latest/')."""
        return (self.prefix + path) if path.startswith("/") else (self.prefix + "/" + path)

    def abs(self, path: str) -> str:
        """Absolute URL for canonical/og/sitemap ('https://…/latest/')."""
        return self.base_url + (path if path.startswith("/") else "/" + path)


def load_articles(cfg: Config, data_override, sample_override, log):
    """Return (articles, source_label). See the fallback chain in the module
    docstring: real file -> sample file -> empty state."""
    data_path = Path(data_override) if data_override else cfg.repo / cfg.data_file
    sample_path = (Path(sample_override) if sample_override
                   else cfg.repo / cfg.sample_data_file)

    # If the real data file EXISTS and parses, its content is the truth --
    # even an empty snapshot builds an honest empty-state site (a fresh
    # fetch where every feed failed must never silently fall back to
    # sample stories). The sample file is only for a checkout where the
    # real snapshot has not been produced yet.
    if data_path.is_file():
        try:
            raw = load_json(data_path)
        except (ValueError, OSError) as exc:
            raise BuildError(
                "real data file %s exists but cannot be parsed (%s) -- "
                "refusing to fall back to sample data; the live site must "
                "never silently show stale or fake news." % (data_path, exc)) from exc
        arts = raw.get("articles") if isinstance(raw, dict) else None
        if isinstance(arts, list):
            log("loaded %d article(s) from %s" % (len(arts), data_path.name))
            return normalize_articles(arts, log), "live", (raw.get("generated_at") or "")
        raise BuildError(
            "real data file %s is valid JSON but has no 'articles' list -- "
            "refusing to fall back to sample data." % data_path)

    if data_path.exists():
        log("WARN: %s exists but is not a regular file -- trying sample data"
            % data_path)

    if sample_path.is_file():
        try:
            raw = load_json(sample_path)
            arts = raw.get("articles") if isinstance(raw, dict) else None
            if isinstance(arts, list) and arts:
                log("note: real data missing/empty -> built from SAMPLE data (%s)"
                    % sample_path.name)
                return (normalize_articles(arts, log), "sample",
                        (raw.get("generated_at") or ""))
        except (ValueError, OSError) as exc:
            log("note: sample data unreadable (%s) -- ignoring it" % exc)

    log("note: no usable data -> building an EMPTY-STATE site (valid but thin)")
    return [], "empty", ""


def normalize_articles(arts, log) -> list:
    """Validate/sort/dedupe into the shape the templates rely on."""
    seen_ids, out, bad_ids, undated = set(), [], 0, 0
    for art in arts:
        if not isinstance(art, dict):
            continue
        title = WS_RE.sub(" ", str(art.get("title") or "")).strip()
        link = str(art.get("link") or "").strip()
        if not title or not link:
            continue
        aid = str(art.get("id") or "").strip().lower()
        if not ID_SAFE_RE.match(aid):
            bad_ids += 1
            continue
        if aid in seen_ids:
            continue
        seen_ids.add(aid)

        ts = art.get("published_ts")
        try:
            ts = float(ts) if ts is not None else None
        except (TypeError, ValueError):
            ts = None
        if ts is None:
            pub = str(art.get("published") or "")
            try:
                parsed = dt.datetime.fromisoformat(pub.replace("Z", "+00:00"))
                ts = parsed.timestamp() if parsed.tzinfo else parsed.replace(
                    tzinfo=UTC).timestamp()
            except ValueError:
                ts = None
        if ts is None:
            undated += 1
            ts = 0.0

        image = str(art.get("image") or "").strip()
        if not image.startswith(("http://", "https://", "data:")):
            image = ""

        out.append({
            "id": aid,
            "title": title,
            "link": link if link.startswith(("http://", "https://")) else "",
            "source": WS_RE.sub(" ", str(art.get("source") or "Unknown source")).strip(),
            "source_slug": str(art.get("source_slug") or "").strip(),
            "category": str(art.get("category") or "").strip().lower(),
            "published": str(art.get("published") or ""),
            "published_ts": ts,
            "description": WS_RE.sub(" ", str(art.get("description") or "")).strip(),
            "image": image,
        })
    out.sort(key=lambda a: (-a["published_ts"], a["id"]))
    if bad_ids:
        log("WARN: skipped %d article(s) with malformed ids" % bad_ids)
    if undated:
        log("WARN: %d article(s) had no parseable date -> sorted last" % undated)
    return out


def load_stats(cfg: Config) -> dict:
    path = cfg.repo / "data" / "stats.json"
    try:
        raw = load_json(path)
        return raw if isinstance(raw, dict) else {}
    except (ValueError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Output directory handling
# ---------------------------------------------------------------------------


def prepare_output(cfg: Config, out_override, log) -> Path:
    out = Path(out_override) if out_override else cfg.repo / cfg.output_dir
    if not out.is_absolute():
        out = (cfg.repo / out).resolve()
    out = out.resolve()

    # Safety: never wipe the repo root, the user home, or a drive root.
    repo = cfg.repo.resolve()
    dangerous = {repo, Path.home().resolve()}
    if out in dangerous or out.parent == out:
        raise BuildError("refusing to use %s as the output directory" % out)

    preserved = {}
    if out.is_dir():
        for name in PRESERVE_FILES:
            candidate = out / name
            if candidate.is_file():
                preserved[name] = candidate.read_text(encoding="utf-8", errors="replace")
        log("clearing previous build in %s" % out)
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_bytes(b"")
    for name, content in preserved.items():
        (out / name).write_text(content, encoding="utf-8", newline="\n")
        log("preserved %s from previous build" % name)
    return out


# ---------------------------------------------------------------------------
# Ad slots
# ---------------------------------------------------------------------------


def ad_head(cfg: Config) -> str:
    """AdSense loader goes in <head> once, only when configured."""
    if not cfg.ads_client:
        return ""
    return ('<script async src="https://pagead2.googlesyndication.com/'
            'pagead/js/adsbygoogle.js?client=%s" crossorigin="anonymous">'
            '</script>') % esc(cfg.ads_client)


def ad_slot(cfg: Config, name: str) -> str:
    """One reserved ad position. Real <ins> when configured; an honest,
    clearly-styled placeholder otherwise (never a fake ad)."""
    slot_id = cfg.ad_slots.get(name, "")
    if cfg.ads_client and slot_id:
        return (
            '<ins class="adsbygoogle ad ad--%s" style="display:block" '
            'data-ad-client="%s" data-ad-slot="%s" '
            'data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>'
        ) % (esc(name), esc(cfg.ads_client), esc(slot_id))
    return (
        '<div class="ad ad--%s" data-ad-slot="%s" aria-label="advertisement space">'
        '<span class="ad-tag">Advertisement</span>'
        '<span class="ad-note">reserved %s slot</span></div>'
    ) % (esc(name), esc(name), esc(name))


# ---------------------------------------------------------------------------
# Site builder
# ---------------------------------------------------------------------------


class SiteBuilder:
    def __init__(self, cfg: Config, articles: list, stats: dict,
                 data_source: str, generated_at: str, log):
        self.cfg = cfg
        self.articles = articles
        self.stats = stats
        self.data_source = data_source
        self.generated_at = generated_at
        self.log = log

        self.by_category = {}
        for art in articles:
            self.by_category.setdefault(art["category"], []).append(art)
        # newest-first is guaranteed by normalize_articles' sort
        self.newest_ts = articles[0]["published_ts"] if articles else None
        self.updated_text = (fmt_datetime(self.newest_ts)
                             if self.newest_ts else "awaiting first fetch")
        self.sitemap = []          # [(url_path, lastmod_date_or_None)]
        self.counts = {"article": 0, "category": 0, "latest": 0}

    # -- affiliate strip ------------------------------------------------------

    def affiliate_strip(self, cfg: Config) -> str:
        """'Recommended' product cards from AFFILIATE_FILE; renders nothing when
        the file is absent, unparseable, or has no http(s) entries."""
        path = cfg.repo / AFFILIATE_FILE
        if not path.is_file():
            return ""
        try:
            raw = load_json(path)
        except (ValueError, OSError) as exc:
            self.log("note: affiliate products file unreadable (%s) -- skipping" % exc)
            return ""
        items = raw if isinstance(raw, list) else (
            raw.get("products") if isinstance(raw, dict) else None)
        cards = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url.lower().startswith(("https://", "http://")):
                continue
            blurb = clip(str(item.get("blurb") or ""), 140)
            badge = str(item.get("badge") or "").strip() or "Recommended"
            cards.append(
                '<a class="aff-card" href="%s" target="_blank" '
                'rel="noopener sponsored"><span class="aff-badge">%s</span>'
                '<span class="aff-title">%s</span>'
                '<span class="aff-blurb">%s</span></a>'
                % (esc(url), esc(badge), esc(title), esc(blurb)))
        if not cards:
            return ""
        return (
            '<aside class="aff-strip"><div class="wrap">'
            '<h2 class="aff-head">Recommended</h2>'
            '<p class="aff-disclose">Some links on this page are to our own '
            'products and may earn us a commission.</p>'
            '<div class="aff-cards">%s</div></div></aside>' % "".join(cards))

    # -- URL helpers --------------------------------------------------------

    def article_url(self, art) -> str:
        return "/article/%s/" % art["id"]

    def article_out(self, art) -> Path:
        return self.out / "article" / art["id"] / "index.html"

    def section_page(self, base_path: str, page: int) -> str:
        return base_path if page <= 1 else "%spage/%d/" % (base_path, page)

    # -- small components ----------------------------------------------------

    def badge(self, art, link: bool = True) -> str:
        slug = art["category"]
        label = esc(self.cfg.label(slug))
        style = "background:%s" % esc(self.cfg.color(slug))
        if link and slug in self.cfg.categories:
            return ('<a class="badge" style="%s" href="%s">%s</a>'
                    % (style, esc(self.cfg.site("/category/%s/" % slug)), label))
        return '<span class="badge" style="%s">%s</span>' % (style, label)

    def media(self, art, cls: str = "", eager: bool = False) -> str:
        """Image or an in-house gradient placeholder (no external services)."""
        color = self.cfg.color(art["category"])
        label = esc(self.cfg.label(art["category"]))
        cls = ("card-media %s" % cls).strip()
        if art["image"]:
            return ('<img class="%s" src="%s" alt="%s" %sdecoding="async" '
                    'width="640" height="360">'
                    % (cls, esc(art["image"]), esc(clip(art["title"], 120)),
                       "" if eager else 'loading="lazy" '))
        return ('<div class="%s ph" style="background:%s" aria-hidden="true">'
                '<span>%s</span></div>' % (cls, gradient(color), label))

    def byline(self, art) -> str:
        return ('<span class="src">%s</span>'
                '<span class="dot" aria-hidden="true">·</span>'
                '<time class="ago"%s>%s</time>'
                % (esc(art["source"]),
                   time_attr(art),
                   esc(rel_time(art["published_ts"], self.newest_ts or 0)
                       or "recently")))

    def card(self, art) -> str:
        return (
            '<article class="card">\n'
            '  <a class="card-media-link" href="%s">%s</a>\n'
            '  <div class="card-body">\n'
            '    <div class="card-meta">%s</div>\n'
            '    <h3 class="card-title"><a href="%s">%s</a></h3>\n'
            '    <p class="card-desc">%s</p>\n'
            '    <p class="card-byline">%s</p>\n'
            '  </div>\n'
            '</article>'
            % (esc(self.cfg.site(self.article_url(art))),
               self.media(art),
               self.badge(art) + self.byline(art),
               esc(self.cfg.site(self.article_url(art))),
               esc(art["title"]),
               esc(clip(art["description"] or art["title"], 180)),
               self.byline(art)))

    def mini(self, art) -> str:
        return ('<li class="mini"><a href="%s">%s</a>'
                '<span class="mini-meta">%s · %s</span></li>'
                % (esc(self.cfg.site(self.article_url(art))),
                   esc(clip(art["title"], 110)),
                   esc(art["source"]),
                   esc(rel_time(art["published_ts"], self.newest_ts or 0)
                       or fmt_date_short(art["published_ts"]))))

    def hero(self, art) -> str:
        color = self.cfg.color(art["category"])
        return (
            '<article class="hero" style="--hero:%s">'
            '<a class="hero-media" href="%s">%s</a>'
            '<div class="hero-body">'
            '<div class="card-meta">%s</div>'
            '<h2 class="hero-title"><a href="%s">%s</a></h2>'
            '<p class="hero-desc">%s</p>'
            '<p class="card-byline">%s</p>'
            '</div></article>'
            % (esc(color),
               esc(self.cfg.site(self.article_url(art))),
               self.media(art, cls="hero-img", eager=True),
               self.badge(art) + self.byline(art),
               esc(self.cfg.site(self.article_url(art))),
               esc(art["title"]),
               esc(clip(art["description"] or art["title"], 260)),
               self.byline(art)))

    def trending_strip(self) -> str:
        """Chips from data/stats.json trending_keywords; skipped gracefully."""
        if not self.articles or self.data_source != "live":
            return ""    # no stories, or sample/offline build -> no strip
        words = self.stats.get("trending_keywords") or []
        words = [w for w in words if isinstance(w, dict) and w.get("word")][:self.cfg.trending_count]
        if not words:
            return ""
        chips = []
        for item in words:
            word = WS_RE.sub(" ", str(item.get("word") or "")).strip()
            if not word:
                continue
            count = item.get("count", "")
            slug = word.lower()
            if slug in self.cfg.categories:
                href = self.cfg.site("/category/%s/" % slug)
            else:
                href = self.cfg.site("/latest/")
            chips.append('<a class="chip" href="%s">#%s<sup>%s</sup></a>'
                         % (esc(href), esc(word), esc(count)))
        return ('<section class="trending" aria-label="Trending keywords">'
                '<h2 class="trending-label">Trending now</h2>'
                '<div class="chips">%s</div></section>' % "".join(chips))

    def pagination(self, base_path: str, page: int, total: int) -> str:
        if total <= 1:
            return ""
        window = {1, 2, total - 1, total, page - 1, page, page + 1}
        window = {p for p in window if 1 <= p <= total}
        parts, prev_p = [], None
        for p in sorted(window):
            if prev_p is not None and p - prev_p > 1:
                parts.append('<span class="ell" aria-hidden="true">…</span>')
            current = ' aria-current="page"' if p == page else ""
            parts.append('<a class="page%s" href="%s"%s>%d</a>'
                         % (" pg-cur" if p == page else "",
                            esc(self.cfg.site(self.section_page(base_path, p))),
                            current, p))
            prev_p = p
        nav = []
        if page > 1:
            nav.append('<a class="page pg-prev" rel="prev" href="%s">&larr; Newer</a>'
                       % esc(self.cfg.site(self.section_page(base_path, page - 1))))
        nav.extend(parts)
        if page < total:
            nav.append('<a class="page pg-next" rel="next" href="%s">Older &rarr;</a>'
                       % esc(self.cfg.site(self.section_page(base_path, page + 1))))
        return ('<nav class="pagination" aria-label="Pagination">%s</nav>'
                % "".join(nav))

    def section_head(self, title: str, color: str, href: str | None = None,
                     more: str = "View all") -> str:
        h = '<h2 class="section-title"><span class="bar" style="background:%s"></span>%s</h2>'
        if href:
            h = ('<h2 class="section-title"><span class="bar" style="background:%s"></span>'
                 '<a href="%s">%s</a></h2><a class="more" href="%s">%s &rarr;</a>')
            return h % (esc(color), esc(href), esc(title), esc(href), esc(more))
        return h % (esc(color), esc(title))

    def demo_banner(self) -> str:
        if self.data_source == "sample":
            return ('<div class="demo-banner" role="note">Demo build: offline '
                    'sample data (data/sample-articles.json), not live news.</div>')
        return ""

    # -- page shell -----------------------------------------------------------

    def shell(self, *, title: str, desc: str, canonical: str, body: str,
              active: str = "", jsonld=(), og_type: str = "website",
              og_image: str = "", og_title: str | None = None,
              crumbs: str = "") -> str:
        cfg = self.cfg
        title = clip(title, 300)
        desc = clip(desc, 300)
        og_image = og_image if og_image.startswith(("http://", "https://")) else ""
        image_meta = ""
        if og_image:
            image_meta = ('<meta property="og:image" content="%s">'
                          '<meta name="twitter:image" content="%s">'
                          % (esc(og_image), esc(og_image)))
        ld = "".join('<script type="application/ld+json">%s</script>' % jsonld_safe(obj)
                     for obj in jsonld)
        crumbs = ('<nav class="crumbs" aria-label="Breadcrumb">%s</nav>' % crumbs
                  if crumbs else "")
        cats_nav = "".join(
            '<a href="%s"%s>%s</a>'
            % (esc(cfg.site("/category/%s/" % slug)),
               ' aria-current="page"' if active == slug else "",
               esc(cat["label"]))
            for slug, cat in cfg.categories.items()
            if slug in self.by_category)
        return """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="generator" content="NewsPulse build_site.py">
<meta name="theme-color" content="#0f172a">
<link rel="canonical" href="{canonical}">
<meta property="og:site_name" content="{site_name}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
{image_meta}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<link rel="alternate" type="application/rss+xml" title="{site_name} RSS" href="{rss}">
<link rel="stylesheet" href="{css}">
<link rel="icon" href="{icon}">
{adsense}
{jsonld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="wrap head-in">
    <div class="brand-row">
      <a class="brand" href="{home}"><span class="pulse-dot" aria-hidden="true"></span>{site_name}</a>
      <p class="tagline">{tagline}</p>
    </div>
    <nav class="nav" aria-label="Sections">
      <a href="{home}"{cur_home}>Home</a>
      <a href="{latest}"{cur_latest}>Latest</a>
      {cats_nav}
      <a href="{about}">About</a>
    </nav>
  </div>
</header>
{banner}
{leaderboard}
<main id="main" class="wrap">
{crumbs}
{body}
</main>
{footad}
{affiliate_cards}
<footer class="site-foot">
  <div class="wrap foot-grid">
    <div class="foot-col foot-about">
      <p class="foot-brand"><span class="pulse-dot" aria-hidden="true"></span>{site_name}</p>
      <p>{foot_desc}</p>
      <p class="foot-updated">Updated {updated}. Headlines &copy; their original sources; aggregated from public RSS feeds.</p>
    </div>
    <nav class="foot-col" aria-label="Sections">
      <h3>Sections</h3>
      {foot_cats}
    </nav>
    <nav class="foot-col" aria-label="Site">
      <h3>Site</h3>
      <a href="{home}">Home</a>
      <a href="{latest}">Latest stories</a>
      <a href="{about}">About &amp; contact</a>
      <a href="{rss}">RSS feed</a>
      <a href="{sitemap}">Sitemap</a>
    </nav>
    <div class="foot-col">
      <h3>Contact</h3>
      <a href="mailto:{email}">{email}</a>
      <p class="foot-note">Automated aggregator. No accounts, no tracking, no paywall.</p>
    </div>
  </div>
  <div class="wrap foot-bottom">
    <p>&copy; {year} {site_name} &mdash; built automatically every 2 hours.</p>
  </div>
</footer>
</body>
</html>
""".format(
            lang=esc(cfg.language),
            title=esc(title),
            desc=esc(desc),
            canonical=esc(canonical),
            site_name=esc(cfg.site_name),
            og_type=esc(og_type),
            og_title=esc(og_title if og_title is not None else title),
            image_meta=image_meta,
            rss=esc(cfg.abs("/rss.xml")),
            css=esc(cfg.site("/assets/style.css")),
            icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230f172a'/%3E%3Ccircle cx='32' cy='32' r='11' fill='%23ef4444'%3E%3Canimate attributeName='r' values='9;14;9' dur='1.6s' repeatCount='indefinite'/%3E%3C/circle%3E%3C/svg%3E",
            adsense=ad_head(cfg),
            jsonld=ld,
            banner=self.demo_banner(),
            leaderboard=ad_slot(cfg, "leaderboard"),
            footad=ad_slot(cfg, "footer"),
            affiliate_cards=self.affiliate_strip(cfg),
            home=esc(cfg.site("/")),
            latest=esc(cfg.site("/latest/")),
            about=esc(cfg.site("/about/")),
            cur_home=' aria-current="page"' if active == "home" else "",
            cur_latest=' aria-current="page"' if active == "latest" else "",
            cats_nav=cats_nav,
            crumbs=crumbs,
            body=body,
            tagline=esc(cfg.tagline),
            foot_desc=esc(clip(cfg.description, 220)),
            updated=esc(self.updated_text),
            foot_cats="".join(
                '<a href="%s">%s</a>' % (esc(cfg.site("/category/%s/" % slug)),
                                         esc(cat["label"]))
                for slug, cat in cfg.categories.items()
                if slug in self.by_category),
            sitemap=esc(cfg.abs("/sitemap.xml")),
            email=esc(cfg.contact_email or "noreply@newspulse.example"),
            year=esc((dt.datetime.fromtimestamp(self.newest_ts, UTC).strftime("%Y")
                      if self.newest_ts else
                      (self.generated_at or "")[:4] or "2026")),
        )

    def write(self, path: Path, html_text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_text, encoding="utf-8", newline="\n")

    # -- page builders ----------------------------------------------------------

    def build_home(self) -> None:
        cfg, front, arts = self.cfg, self.cfg.front, self.articles
        body = []
        body.append(self.trending_strip())

        if arts:
            i = 0
            hero_n = max(0, int(front.get("hero", 1)))
            sec_n = max(0, int(front.get("secondary", 4)))
            hero = arts[i:i + hero_n]
            i += len(hero)
            secondary = arts[i:i + sec_n]
            i += len(secondary)

            if hero:
                body.append('<section class="hero-grid" aria-label="Top stories">')
                body.append(self.hero(hero[0]))
                if secondary:
                    body.append('<div class="hero-side">')
                    body.extend(self.card(a) for a in secondary)
                    body.append("</div>")
                body.append("</section>")

            body.append('<div class="ad-wrap">%s</div>' % ad_slot(cfg, "in_article"))

            latest_n = max(0, int(front.get("latest_rows", 12)))
            latest = [a for a in arts[i:i + latest_n]]
            if latest:
                body.append('<section class="section" aria-label="Latest stories">')
                body.append(self.section_head("Latest stories", "#111827",
                                               cfg.site("/latest/"), "View all"))
                body.append('<div class="grid-cards">')
                body.extend(self.card(a) for a in latest)
                body.append("</div></section>")

            if front.get("category_blocks", True):
                per_cat = max(1, int(front.get("per_category", 3)))
                for slug in cfg.categories:
                    items = self.by_category.get(slug, [])
                    if not items:
                        continue
                    body.append('<section class="section" aria-label="%s">'
                                % esc(cfg.label(slug)))
                    body.append(self.section_head(cfg.label(slug), cfg.color(slug),
                                                  cfg.site("/category/%s/" % slug)))
                    body.append('<div class="grid-cards">')
                    body.extend(self.card(a) for a in items[:per_cat])
                    body.append("</div></section>")
        else:
            body.append(
                '<section class="empty-state">'
                '<h2>No stories yet</h2>'
                '<p>The news pipeline has not produced any stories in this snapshot. '
                'The next scheduled fetch will refill this page automatically.</p>'
                '<p><a class="cta" href="%s">About how NewsPulse works</a></p>'
                "</section>" % esc(cfg.site("/about/")))

        page = self.shell(
            title="%s — %s" % (cfg.site_name, clip(cfg.tagline, 80)),
            desc=cfg.description,
            canonical=cfg.abs("/"),
            body="\n".join(body),
            active="home",
            og_type="website",
            jsonld=[{
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": cfg.site_name,
                "url": cfg.abs("/"),
                "description": clip(cfg.description, 300),
                "inLanguage": cfg.language,
            }],
        )
        self.write(self.out / "index.html", page)
        self.sitemap.append(("/", iso_date(self.newest_ts) if self.newest_ts else None))

    def build_listing(self, base_path: str, out_dir: Path, title: str, desc: str,
                      items: list, color: str, active: str, kind: str,
                      crumb_label: str = "") -> None:
        """Shared paginated listing renderer (latest + category hubs)."""
        cfg = self.cfg
        pages = chunked(items, cfg.articles_per_page)
        for idx, page_items in enumerate(pages, start=1):
            head = self.section_head(title, color)
            cards = '<div class="grid-cards">%s</div>' % "".join(
                self.card(a) for a in page_items)
            pagi = self.pagination(base_path, idx, len(pages))
            count_note = ('<p class="count-note">%d stories · page %d of %d · '
                          'updated %s</p>'
                          % (len(items), idx, len(pages), esc(self.updated_text)))
            body = ('<section class="section listing" aria-label="%s">%s%s%s%s</section>'
                    % (esc(title), head, count_note, cards, pagi))
            crumbs = ""
            if crumb_label:
                crumbs = ('<a href="%s">Home</a> <span aria-hidden="true">›</span> '
                          '<span>%s</span>'
                          % (esc(cfg.site("/")), esc(crumb_label)))
            page_html = self.shell(
                title=("%s — %s" % (title, cfg.site_name)) if idx == 1
                else ("Page %d — %s — %s" % (idx, title, cfg.site_name)),
                desc=desc,
                canonical=cfg.abs(self.section_page(base_path, idx)),
                body=body,
                active=active,
                crumbs=crumbs,
                jsonld=[{
                    "@context": "https://schema.org",
                    "@type": "CollectionPage",
                    "name": title,
                    "url": cfg.abs(self.section_page(base_path, idx)),
                    "description": clip(desc, 300),
                    "inLanguage": cfg.language,
                }],
            )
            out = out_dir if idx == 1 else out_dir / "page" / str(idx)
            self.write(out / "index.html", page_html)
            lastmod = max((a["published_ts"] for a in page_items), default=None)
            self.sitemap.append((self.section_page(base_path, idx),
                                iso_date(lastmod) if lastmod else None))
            self.counts[kind] = self.counts.get(kind, 0) + 1

    def build_latest(self) -> None:
        cfg = self.cfg
        self.build_listing(
            "/latest/", self.out / "latest", "Latest stories",
            "All the latest headlines aggregated by %s across world news, India, "
            "tech, business, sports, gaming, music, movies, science and entertainment."
            % cfg.site_name,
            self.articles, "#111827", "latest", "latest", "Latest stories")

    def build_categories(self) -> None:
        cfg = self.cfg
        for slug, cat in cfg.categories.items():
            items = self.by_category.get(slug, [])
            if not items:
                continue
            sources = sorted({a["source"] for a in items})[:5]
            desc = ("The latest %s headlines and stories on %s, aggregated from "
                    "trusted sources%s. %d %s stories right now."
                    % (cat["label"].lower(), cfg.site_name,
                       (" incl. " + ", ".join(sources)) if sources else "",
                       len(items), cat["label"]))
            self.build_listing(
                "/category/%s/" % slug, self.out / "category" / slug,
                "%s news" % cat["label"], desc, items, cat["color"],
                slug, "category", cat["label"])

    def build_article(self, art) -> None:
        cfg = self.cfg
        slug = art["category"]
        label = cfg.label(slug)
        color = cfg.color(slug)
        desc = clip(art["description"] or art["title"], 300)

        # related: same category first, then global newest, never self
        pool = [a for a in self.by_category.get(slug, []) if a["id"] != art["id"]]
        if len(pool) < cfg.related_count:
            extra = [a for a in self.articles
                     if a["id"] != art["id"] and a["id"] not in
                     {x["id"] for x in pool}]
            pool = pool + extra
        related = pool[:cfg.related_count]

        cat_href = cfg.site("/category/%s/" % slug) if slug in cfg.categories else ""
        crumbs = ('<a href="%s">Home</a> <span aria-hidden="true">›</span> '
                  '%s<span aria-hidden="true"> › </span><span>%s</span>'
                  % (esc(cfg.site("/")),
                     ('<a href="%s">%s</a>' % (esc(cat_href), esc(label)))
                     if cat_href else esc(label),
                     esc(clip(art["title"], 60))))

        body_desc = art["description"] or ("This story was aggregated from %s's "
                                           "public feed. Read the full report at "
                                           "the source." % art["source"])
        cta = ""
        if art["link"]:
            cta = ('<a class="cta" style="background:%s" rel="noopener" '
                   'target="_blank" href="%s">Read the full story at %s &rarr;</a>'
                   % (esc(color), esc(art["link"]), esc(clip(art["source"], 40))))

        story = (
            '<div class="story-grid">'
            '<article class="story">'
            '<header class="story-head">'
            '<div class="card-meta">%s</div>'
            '<h1 class="story-title">%s</h1>'
            '<p class="byline"><span class="src">%s</span>'
            '<span class="dot" aria-hidden="true">·</span>'
            '<time%s>%s</time>'
            '<span class="dot" aria-hidden="true">·</span>'
            '<span class="ago">%s</span></p>'
            '</header>'
            '<div class="story-media">%s</div>'
            '<div class="story-body">'
            '<p class="lede">%s</p>'
            '<p class="story-more">%s</p>'
            '%s'
            '<p class="credit">Headline and summary aggregated automatically from '
            '<strong>%s</strong>&rsquo;s public RSS feed. The full article and its '
            'copyright remain with the publisher.</p>'
            '</div>'
            '<div class="ad-wrap">%s</div>'
            '</article>'
            '<aside class="story-side">'
            '<h2 class="section-title"><span class="bar" style="background:%s"></span>'
            'Related in %s</h2>'
            '<ul class="minis">%s</ul>'
            '<div class="ad-wrap ad-wrap--side">%s</div>'
            '</aside>'
            '</div>'
            % (self.badge(art),
               esc(art["title"]),
               esc(art["source"]),
               time_attr(art),
               esc(fmt_datetime(art["published_ts"])),
               esc(rel_time(art["published_ts"], self.newest_ts or 0) or "recently"),
               self.media(art, cls="story-img", eager=True),
               esc(body_desc),
               esc("Quick summary — %s is tracking this story across public feeds. "
                   "The excerpt above is the publisher's own summary; the complete "
                   "report, quotes and media are on the source site."
                   % cfg.site_name),
               cta,
               esc(art["source"]),
               ad_slot(cfg, "in_article"),
               esc(color),
               esc(label),
               "".join(self.mini(a) for a in related),
               ad_slot(cfg, "sidebar")))

        jsonld = [{
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": clip(art["title"], 110),
            "description": desc,
            "url": cfg.abs(self.article_url(art)),
            "mainEntityOfPage": cfg.abs(self.article_url(art)),
            "datePublished": (art["published"] or iso_datetime(art["published_ts"])
                              or None),
            "dateModified": (art["published"] or iso_datetime(art["published_ts"])
                             or None),
            "image": art["image"] if art["image"].startswith("http") else None,
            "articleSection": label,
            "inLanguage": cfg.language,
            "isAccessibleForFree": True,
            "author": {"@type": "Organization", "name": art["source"]},
            "publisher": {"@type": "Organization", "name": cfg.site_name,
                          "url": cfg.abs("/")},
        }, {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home",
                 "item": cfg.abs("/")},
                {"@type": "ListItem", "position": 2, "name": label,
                 "item": (cfg.abs("/category/%s/" % slug) if cat_href else None)},
                {"@type": "ListItem", "position": 3,
                 "name": clip(art["title"], 60)},
            ],
        }]
        jsonld = [{k: v for k, v in obj.items() if v is not None} for obj in jsonld]

        page = self.shell(
            title="%s | %s" % (clip(art["title"], 120), cfg.site_name),
            desc=desc,
            canonical=cfg.abs(self.article_url(art)),
            body=story,
            active=slug,
            crumbs=crumbs,
            og_type="article",
            og_image=art["image"],
            jsonld=jsonld)
        self.write(self.article_out(art), page)
        self.sitemap.append((self.article_url(art),
                             iso_date(art["published_ts"])))
        self.counts["article"] += 1

    def build_about(self) -> None:
        cfg = self.cfg
        n_sources = len({a["source"] for a in self.articles})
        n_stories = len(self.articles)
        cats = ", ".join(cat["label"] for cat in cfg.categories.values())
        body = (
            '<section class="prose">'
            '<h1>About %s</h1>'
            '<p class="lede">%s</p>'
            '<p>%s is a zero-budget, automated news magazine. Every two hours a '
            'pipeline fetches public RSS and Atom feeds, builds this static site, '
            'and republishes nothing but headlines and short summaries — every '
            'story links to its original publisher.</p>'
            '<p>Right now the front page is built from <strong>%d stories</strong> '
            'across <strong>%d sources</strong> in %d sections: %s.</p>'
            '<h2>How it works</h2>'
            '<ol class="how">'
            '<li><strong>Fetch</strong> — scheduled jobs pull the latest items from '
            'each feed.</li>'
            '<li><strong>Build</strong> — this page you are reading is generated '
            'from that snapshot; there is no server, no database, no tracking.</li>'
            '<li><strong>Publish</strong> — search engines are pinged via '
            '<a rel="noopener" target="_blank" href="https://www.indexnow.org/">'
            'IndexNow</a>, and the site is redeployed.</li>'
            '</ol>'
            '<h2>Editorial policy</h2>'
            '<p>Selection is algorithmic, not editorial. Headlines and summaries '
            'belong to their publishers; %s claims no ownership. If you are a '
            'publisher and want your feed removed, email the address below and it '
            'will be dropped from the next build.</p>'
            '<h2>Contact</h2>'
            '<p>Corrections, takedowns and feedback: '
            '<a class="cta" href="mailto:%s">%s</a></p>'
            '<h2>Machine-readable</h2>'
            '<p>Everything is also available as <a href="%s">RSS</a> and a full '
            '<a href="%s">sitemap</a>.</p>'
            '</section>'
            % (esc(cfg.site_name),
               esc(cfg.tagline),
               esc(cfg.site_name),
               n_stories, n_sources, len(cfg.categories), esc(cats),
               esc(cfg.site_name),
               esc(cfg.contact_email or "the address in the footer"),
               esc(cfg.contact_email or "email us"),
               esc(cfg.site("/rss.xml")),
               esc(cfg.site("/sitemap.xml"))))
        page = self.shell(
            title="About %s — how the news pipeline works" % cfg.site_name,
            desc="What %s is, how its fully automated fetch-build-publish pipeline "
                 "works, its editorial policy and how to contact it."
                 % cfg.site_name,
            canonical=cfg.abs("/about/"),
            body=body,
            active="about",
            jsonld=[{
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": "About %s" % cfg.site_name,
                "url": cfg.abs("/about/"),
                "inLanguage": cfg.language,
            }])
        self.write(self.out / "about" / "index.html", page)
        self.sitemap.append(("/about/", iso_date(self.newest_ts)
                             if self.newest_ts else None))

    def build_404(self) -> None:
        cfg = self.cfg
        cats = "".join('<a href="%s">%s</a>'
                       % (esc(cfg.site("/category/%s/" % slug)), esc(cat["label"]))
                       for slug, cat in cfg.categories.items()
                       if slug in self.by_category)
        body = (
            '<section class="empty-state">'
            '<p class="nf-404">404</p>'
            '<h2>That page has scrolled away</h2>'
            '<p>Old story pages are recycled as the news moves on. Try one of '
            'these instead:</p>'
            '<div class="nf-links">'
            '<a class="cta" href="%s">Home</a>'
            '<a class="cta" href="%s">Latest stories</a>'
            '<a class="cta" href="%s">About</a>'
            "</div>"
            '<nav class="nf-cats" aria-label="Sections">%s</nav>'
            "</section>"
            % (esc(cfg.site("/")), esc(cfg.site("/latest/")),
               esc(cfg.site("/about/")), cats))
        page = self.shell(
            title="Page not found — %s" % cfg.site_name,
            desc="The page you asked for no longer exists on %s."
                 % cfg.site_name,
            canonical="",  # 404s must not be canonicalized
            body=body)
        page = page.replace('<link rel="canonical" href="">', "")
        page = page.replace(
            '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',
            '<meta name="robots" content="noindex, follow">')
        self.write(self.out / "404.html", page)

    # -- feeds / seo / static ----------------------------------------------------

    def build_rss(self) -> None:
        cfg = self.cfg
        build_date = None
        if self.newest_ts:
            build_date = rfc822(self.newest_ts)
        else:                                    # fall back to the snapshot's own stamp
            try:
                build_date = rfc822(dt.datetime.fromisoformat(
                    (self.generated_at or "").replace("Z", "+00:00")
                ).timestamp())
            except ValueError:
                pass
        items = []
        for art in self.articles[:cfg.feed_items]:
            url = cfg.abs(self.article_url(art))
            desc = clip(art["description"] or art["title"], 500)
            pub_line = ("<pubDate>%s</pubDate>" % rfc822(art["published_ts"])
                        if art["published_ts"] else "")
            items.append(
                "<item>\n"
                "<title>%s</title>\n"
                "<link>%s</link>\n"
                '<guid isPermaLink="true">%s</guid>\n'
                "%s\n"
                "<description>%s (via %s)</description>\n"
                "<category>%s</category>\n"
                "</item>"
                % (xesc(art["title"]), xesc(url), xesc(url), pub_line,
                   xesc(desc), xesc(art["source"]),
                   xesc(cfg.label(art["category"]))))
        rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
            "<channel>\n"
            "<title>%s</title>\n"
            "<link>%s</link>\n"
            "<description>%s</description>\n"
            "<language>%s</language>\n"
            "%s"
            "<ttl>120</ttl>\n"
            "<docs>https://www.rssboard.org/rss-specification</docs>\n"
            '<atom:link href="%s" rel="self" type="application/rss+xml"/>\n'
            "%s\n"
            "</channel>\n"
            "</rss>\n"
            % (xesc(cfg.site_name), xesc(cfg.abs("/")), xesc(cfg.description),
               xesc(cfg.language),
               ("<lastBuildDate>%s</lastBuildDate>\n" % build_date) if build_date else "",
               xesc(cfg.abs("/rss.xml")),
               "\n".join(items)))
        self.write(self.out / "rss.xml", rss)

    def build_sitemap(self) -> None:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for path, lastmod in self.sitemap:
            lines.append("<url>")
            lines.append("  <loc>%s</loc>" % xesc(self.cfg.abs(path)))
            if lastmod:
                lines.append("  <lastmod>%s</lastmod>" % lastmod)
            lines.append("</url>")
        lines.append("</urlset>")
        self.write(self.out / "sitemap.xml", "\n".join(lines) + "\n")

    def build_robots(self) -> None:
        self.write(self.out / "robots.txt",
                   "User-agent: *\nAllow: /\n\nSitemap: %s\n"
                   % (self.cfg.abs("/sitemap.xml")))

    def copy_extras(self) -> None:
        cfg = self.cfg
        # IndexNow key file(s): engines verify them at the site root path.
        key_dir = cfg.repo / KEYFILE_DIR
        copied = []
        if key_dir.is_dir():
            for key_file in sorted(key_dir.glob("*.txt")):
                shutil.copyfile(key_file, self.out / key_file.name)
                copied.append(key_file.name)
        if copied:
            self.log("copied IndexNow key file(s): %s" % ", ".join(copied))
        else:
            self.log("WARN: no key file found in %s (IndexNow verification "
                    "will fail until one is added)" % key_dir)
        if cfg.ads_txt:
            self.write(self.out / "ads.txt", cfg.ads_txt + "\n")
            self.log("wrote ads.txt (%d bytes)" % len(cfg.ads_txt))

    def write_css(self, css: str) -> None:
        self.write(self.out / "assets" / "style.css", css)

    # -- orchestration --------------------------------------------------------

    def build_all(self, out: Path, css: str) -> None:
        self.out = out
        started = time.perf_counter()
        self.write_css(css)
        self.build_home()
        self.build_latest()
        self.build_categories()
        for art in self.articles:
            self.build_article(art)
        self.build_about()
        self.build_404()
        self.build_rss()
        self.build_sitemap()
        self.build_robots()
        self.copy_extras()
        self.elapsed = time.perf_counter() - started
        return self


# ---------------------------------------------------------------------------
# Stylesheet (single file, no external fonts/CDNs)
# ---------------------------------------------------------------------------

STYLE_CSS = """/* NewsPulse — generated by scripts/build_site.py. No frameworks, no CDNs. */
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f5f6f8; --surface:#ffffff; --ink:#111827; --muted:#5b6472;
  --line:#e3e6ea; --accent:#ef4444; --soft:#eef0f3;
  --radius:12px; --shadow:0 1px 2px rgba(16,24,40,.06),0 4px 14px rgba(16,24,40,.06);
}
@media (prefers-color-scheme:dark){
  :root{ --bg:#0b0f14; --surface:#141a21; --ink:#e8ecf1; --muted:#98a2b3;
         --line:#232b34; --soft:#1b222b; --shadow:0 1px 2px rgba(0,0,0,.4); }
  img{filter:brightness(.92)}
}
html{scroll-behavior:smooth}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
     background:var(--bg);color:var(--ink);line-height:1.55;-webkit-text-size-adjust:100%}
a{color:inherit;text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:2px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.wrap{max-width:1180px;margin-inline:auto;padding-inline:clamp(14px,3vw,28px)}
.skip{position:absolute;left:-9999px;top:0;background:var(--ink);color:var(--surface);
      padding:8px 14px;border-radius:0 0 8px 0;z-index:99}
.skip:focus{left:0}

/* header */
.site-head{position:sticky;top:0;z-index:20;background:var(--surface);
  border-bottom:1px solid var(--line);box-shadow:var(--shadow)}
.head-in{display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline;justify-content:space-between;
  padding-block:12px}
.brand-row{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.brand{font-size:1.5rem;font-weight:800;letter-spacing:-.02em;display:inline-flex;align-items:center;gap:8px}
.brand:hover{text-decoration:none}
.pulse-dot{width:11px;height:11px;border-radius:50%;background:var(--accent);display:inline-block;
  animation:pulse 1.6s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(239,68,68,.5)}70%{box-shadow:0 0 0 9px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
.tagline{margin:0;color:var(--muted);font-size:.9rem}
.nav{display:flex;flex-wrap:wrap;gap:2px 14px;font-size:.95rem}
.nav a{color:var(--muted);padding:4px 2px;border-bottom:2px solid transparent}
.nav a:hover{color:var(--ink);text-decoration:none}
.nav a[aria-current="page"]{color:var(--ink);font-weight:700;border-bottom-color:var(--accent)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* ads */
.ad{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;
  margin:14px auto;max-width:1180px;border:1px dashed var(--line);border-radius:8px;
  background:var(--soft);color:var(--muted);min-height:96px;text-align:center;padding:10px}
.ad--leaderboard{min-height:100px}
.ad--footer{min-height:80px;margin-bottom:0}
.ad-tag{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;opacity:.8}
.ad-note{font-size:.78rem;opacity:.7}
.ad-wrap{margin:18px 0}
.adsbygoogle{display:block}

/* trending */
.trending{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:18px 0 6px}
.trending-label{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--surface);border:1px solid var(--line);border-radius:999px;
  padding:4px 12px;font-size:.88rem;font-weight:600}
.chip:hover{border-color:var(--accent);text-decoration:none}
.chip sup{color:var(--muted);font-weight:400;font-size:.7em;margin-left:2px}

/* hero */
.hero-grid{display:grid;grid-template-columns:1.7fr 1fr;gap:18px;margin-top:10px}
@media (max-width:900px){.hero-grid{grid-template-columns:1fr}}
.hero-side{display:grid;gap:14px;align-content:start}
.hero{--hero:#111827;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);display:grid;grid-template-rows:auto 1fr}
.hero-media{display:block}
.hero-media .card-media,.hero-media img{aspect-ratio:16/9;width:100%;height:100%;object-fit:cover;display:block;border-radius:0}
.hero-body{padding:16px 18px 18px}
.hero-title{font-size:clamp(1.3rem,2.6vw,1.9rem);line-height:1.25;margin:8px 0 10px;letter-spacing:-.01em}
.hero-desc{color:var(--muted);margin:0 0 10px;font-size:1.02rem}

/* cards */
.section{margin:26px 0}
.section-title{display:flex;align-items:center;gap:10px;font-size:1.25rem;margin:0 0 4px;
  justify-content:space-between}
.section-title .bar{display:inline-block;width:6px;height:22px;border-radius:3px;flex:0 0 auto}
.section-title a{color:inherit}
.section-head-row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.more{font-size:.9rem;font-weight:600;color:var(--muted);white-space:nowrap}
.grid-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;
  margin-top:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column;
  transition:transform .15s ease,box-shadow .15s ease}
.card:hover{transform:translateY(-3px)}
.card-media-link{display:block;overflow:hidden}
.card-media{aspect-ratio:16/9;width:100%;object-fit:cover;display:block}
.ph{display:flex;align-items:center;justify-content:center}
.ph span{color:rgba(255,255,255,.92);font-weight:800;letter-spacing:.18em;
  text-transform:uppercase;font-size:.9rem;text-shadow:0 1px 2px rgba(0,0,0,.25)}
.card-body{padding:12px 14px 14px;display:flex;flex-direction:column;gap:8px;flex:1}
.card-meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:.8rem;color:var(--muted)}
.badge{color:#fff;font-size:.72rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;padding:3px 9px;border-radius:999px;white-space:nowrap}
.badge:hover{text-decoration:none;filter:brightness(1.1)}
.card-title{font-size:1.02rem;line-height:1.35;margin:0;display:-webkit-box;
  -webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card-desc{margin:0;color:var(--muted);font-size:.9rem;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-byline{margin:0;font-size:.8rem;color:var(--muted)}
.dot{opacity:.6}
.ago{color:var(--muted)}

/* listing pages */
.count-note{color:var(--muted);font-size:.88rem;margin:6px 0 0}
.crumbs{font-size:.85rem;color:var(--muted);margin:12px 0 0}
.crumbs a{color:var(--muted)}
.crumbs a:hover{color:var(--ink)}

/* pagination */
.pagination{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:22px 0 6px}
.page{min-width:40px;padding:8px 12px;text-align:center;border:1px solid var(--line);
  border-radius:8px;background:var(--surface);font-weight:600;font-size:.92rem}
.page:hover{border-color:var(--ink);text-decoration:none}
.pg-cur{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.ell{align-self:center;color:var(--muted);padding-inline:2px}

/* story page */
.story-grid{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:28px;margin-top:14px}
@media (max-width:960px){.story-grid{grid-template-columns:1fr}}
.story-head h1{font-size:clamp(1.5rem,3.4vw,2.3rem);line-height:1.2;letter-spacing:-.015em;margin:10px 0}
.byline{color:var(--muted);font-size:.92rem;margin:0 0 14px}
.story-media{margin:0 0 18px;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}
.story-img{width:100%;max-height:520px;object-fit:cover;display:block;aspect-ratio:16/9}
.story-body{font-size:1.04rem}
.lede{font-size:1.18rem;line-height:1.6;margin:0 0 14px}
.story-more{color:var(--muted);font-size:.95rem}
.cta{display:inline-block;background:var(--ink);color:#fff;font-weight:700;padding:11px 18px;
  border-radius:10px;margin:10px 0;font-size:.98rem}
.cta:hover{text-decoration:none;filter:brightness(1.15)}
.credit{color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);padding-top:12px;margin-top:18px}
.story-side{display:flex;flex-direction:column;gap:16px}
.story-side .section-title{font-size:1.1rem}
@media (min-width:961px){.story-side{position:sticky;top:76px;align-self:start}}
.minis{list-style:none;margin:0;padding:0}
.mini{padding:10px 0;border-bottom:1px solid var(--line)}
.mini:last-child{border-bottom:0}
.mini a{font-weight:600;font-size:.95rem;line-height:1.4}
.mini-meta{display:block;color:var(--muted);font-size:.78rem;margin-top:3px}
.ad-wrap--side .ad{min-height:250px}

/* about */
.prose{max-width:760px;margin-inline:auto;padding-block:10px}
.prose h1{letter-spacing:-.02em;margin-bottom:6px}
.prose h2{margin-top:28px;font-size:1.25rem}
.how{padding-left:1.2rem}
.how li{margin:8px 0}

/* empty / 404 */
.empty-state{text-align:center;padding:70px 12px;max-width:640px;margin-inline:auto}
.empty-state h2{font-size:1.6rem;margin:6px 0}
.empty-state p{color:var(--muted)}
.nf-404{font-size:4.4rem;font-weight:900;color:var(--line);margin:0;letter-spacing:-.04em}
.nf-links{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:16px 0}
.nf-cats{display:flex;gap:6px 14px;flex-wrap:wrap;justify-content:center;color:var(--muted)}
.demo-banner{background:#fffbeb;border-bottom:1px solid #fde68a;color:#92400e;
  text-align:center;font-size:.88rem;padding:8px 12px}
@media (prefers-color-scheme:dark){.demo-banner{background:#2a2110;border-color:#5b4708;color:#fbbf24}}

/* footer */
.site-foot{background:var(--ink);color:#d7dde5;margin-top:40px}
.foot-grid{display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;gap:26px;padding-block:34px}
@media (max-width:900px){.foot-grid{grid-template-columns:1fr 1fr}}
@media (max-width:560px){.foot-grid{grid-template-columns:1fr}}
.foot-brand{font-weight:800;font-size:1.2rem;display:flex;align-items:center;gap:8px;margin:0 0 8px}
.foot-col h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.12em;margin:0 0 10px;color:#aab4c0}
.foot-col p{font-size:.9rem;margin:0 0 8px}
.foot-col a{display:block;font-size:.92rem;margin-bottom:8px;color:#c6ced9}
.foot-col a:hover{color:#fff}
.foot-about p{font-size:.88rem;color:#aab4c0}
.foot-updated{font-size:.8rem;color:#8b95a3}
.foot-note{font-size:.8rem;color:#8b95a3}
.foot-bottom{border-top:1px solid rgba(255,255,255,.12);padding-block:16px}
.foot-bottom p{margin:0;font-size:.82rem;color:#8b95a3}
.aff-strip{border-top:1px solid var(--line);background:var(--soft);margin-top:32px;padding-block:22px}
.aff-head{margin:0 0 2px;font-size:1.05rem}
.aff-disclose{margin:0 0 12px;color:var(--muted);font-size:.82rem}
.aff-cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.aff-card{display:block;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;box-shadow:var(--shadow)}
.aff-card:hover{border-color:var(--accent)}
.aff-badge{display:inline-block;background:var(--accent);color:#fff;border-radius:999px;padding:1px 9px;font-size:.72rem;font-weight:600}
.aff-title{display:block;font-weight:650;margin:7px 0 3px}
.aff-blurb{display:block;color:var(--muted);font-size:.86rem}
"""


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        prog="build_site.py",
        description="Generate the NewsPulse static site (stdlib only).")
    parser.add_argument("--config", default=None,
                        help="site config JSON (default: config/site-config.json)")
    parser.add_argument("--data", default=None,
                        help="articles JSON (default: config data_file)")
    parser.add_argument("--sample-data", default=None,
                        help="fallback sample articles JSON (default: config "
                             "sample_data_file)")
    parser.add_argument("--out", default=None,
                        help="output directory (default: config output_dir)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="only print warnings and errors")
    args = parser.parse_args(argv)

    def resolve(path_arg, cfg_path):
        p = Path(path_arg) if path_arg else cfg_path
        return p if p.is_absolute() else (BASE_DIR / p)

    def log(msg):
        if not args.quiet:
            print(msg, flush=True)

    def warn(msg):
        print("WARN: " + msg, file=sys.stderr, flush=True)

    try:
        config_path = resolve(args.config, BASE_DIR / "config" / "site-config.json")
        cfg = Config(load_json(config_path), BASE_DIR)
    except (OSError, ValueError, BuildError) as exc:
        print("ERROR: cannot load site config (%s): %s" % (config_path, exc),
              file=sys.stderr, flush=True)
        return 1

    started = time.perf_counter()

    def data_log(msg):
        (warn if msg.startswith("WARN") else log)(msg)

    try:
        articles, source_label, generated_at = load_articles(
            cfg, args.data, args.sample_data, data_log)
    except BuildError as exc:
        print("ERROR: %s" % exc, file=sys.stderr, flush=True)
        return 1

    stats = load_stats(cfg)
    out = prepare_output(cfg, args.out, log)

    builder = SiteBuilder(cfg, articles, stats, source_label, generated_at, log)
    builder.build_all(out, STYLE_CSS)

    files = [p for p in out.rglob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)
    no_image = sum(1 for a in articles if not a["image"])
    log("")

    print("=" * 66)
    print("NewsPulse build OK  (%s data, %.1fs)"
          % (source_label, time.perf_counter() - started))
    print("  output      : %s" % out)
    print("  files       : %d (%.1f MB total)" % (len(files), total_bytes / 1e6))
    print("  articles    : %d story pages" % builder.counts["article"])
    print("  categories  : %d hub pages" % builder.counts["category"])
    print("  latest      : %d paginated pages" % builder.counts["latest"])
    print("  sitemap     : %d URLs" % len(builder.sitemap))
    print("  rss         : %d items" % min(len(articles), cfg.feed_items))
    print("  trending    : %s"
          % ("%d keyword chips" % min(
              len(stats.get("trending_keywords") or []), cfg.trending_count)
             if (source_label == "live" and articles
                 and stats.get("trending_keywords"))
             else "skipped (%s)" % ("no stats file" if not stats.get("trending_keywords")
                                    else "not a live build")))
    if no_image and articles:
        print("  images      : %d/%d have art; %d use gradient placeholders"
              % (len(articles) - no_image, len(articles), no_image))
    print("  key file    : %s"
          % ("copied" if (out / "2f2b4da5a93242c38df8ee1bbcb4bceb.txt").is_file()
             else "MISSING (check public/)"))
    print("  ads         : %s"
          % ("AdSense ON (%s)" % cfg.ads_client if cfg.ads_client
             else "slots reserved, AdSense not configured"))
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
