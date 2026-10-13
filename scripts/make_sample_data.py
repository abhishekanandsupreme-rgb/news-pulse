#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_sample_data.py -- generate data/sample-articles.json offline.

A tiny, dependency-free fallback dataset shaped EXACTLY like the real
data/articles.json contract produced by scripts/fetch_feeds.py:

    {"generated_at": <ISO8601 UTC>, "count": N, "articles": [ ... ]}

Each article: {id (16-hex sha1-style), title, link, source, source_slug,
category, published (ISO8601 UTC), published_ts (epoch), description
(plain text, <=500 chars), image (url or null)}.

Use cases:
  * smoke-testing scripts/build_site.py with no network at all;
  * keeping CI green on a fresh clone before the first real fetch;
  * demoing the site layout offline.

The content is clearly-labelled realistic filler ("Sample Wire"); ids are
deterministic sha1[:16] of the link, so runs are reproducible and any
sample-built site is honestly banner-marked by build_site.py.

Usage:
    python scripts/make_sample_data.py                 # default 36 stories
    python scripts/make_sample_data.py --count 80
    python scripts/make_sample_data.py --out PATH --seed 7
Exit codes: 0 ok, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc

# (category, source name, source_slug, template with {i})
WIRES = [
    ("world", "Sample Wire World", "sample-world",
     "Global summit reaches agreement on {topic} as delegates wrap week-long talks"),
    ("india", "Sample Wire India", "sample-india",
     "India announces new {topic} initiative ahead of the winter session"),
    ("tech", "Sample Wire Tech", "sample-tech",
     "Open-source project ships major release with faster {topic} pipeline"),
    ("business", "Sample Wire Business", "sample-business",
     "Markets steady as analysts weigh the latest {topic} numbers"),
    ("sports", "Sample Wire Sports", "sample-sports",
     "Championship thriller ends in overtime after a late {topic} surge"),
    ("gaming", "Sample Wire Gaming", "sample-gaming",
     "Indie darling sweeps awards night; {topic} expansion announced"),
    ("music", "Sample Wire Music", "sample-music",
     "Surprise album drop tops charts; {topic} tour dates sell out"),
    ("movies", "Sample Wire Movies", "sample-movies",
     "Festival favourite secures wide release; critics praise its {topic}"),
    ("science", "Sample Wire Science", "sample-science",
     "Telescope survey reveals fresh clues about {topic} in early galaxies"),
    ("entertainment", "Sample Wire Entertainment", "sample-ent",
     "Streaming renewal confirmed for the breakout {topic} series"),
]

TOPICS = ["climate", "transit", "rendering", "inflation", "comeback",
          "storytelling", "vinyl", "soundtrack", "debut", "second season"]

# Local, deterministic placeholder art bundled by build_site.py? No -- the
# sample data deliberately uses image=None for ~40% of items so the gradient
# placeholder path is exercised; the rest get picsum-free sample URLs that
# are never fetched by the builder (images are lazy-loaded client-side).
SAMPLE_IMAGE = "https://example.com/sample-assets/news-{i:02d}.jpg"


def build(count: int, seed: int) -> list:
    articles = []
    now = dt.datetime(2026, 9, 12, 20, 0, 0, tzinfo=UTC)  # deterministic clock
    for i in range(count):
        cat, source, slug, template = WIRES[i % len(WIRES)]
        topic = TOPICS[i % len(TOPICS)]
        title = template.format(topic=topic)
        link = "https://example.com/sample/%s/%04d" % (cat, i)
        published = now - dt.timedelta(minutes=25 * i)
        has_image = (i % 5) != 4                     # ~20% null images
        articles.append({
            "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
            "title": title,
            "link": link,
            "source": source,
            "source_slug": slug,
            "category": cat,
            "published": published.isoformat(),
            "published_ts": published.timestamp(),
            "description": (
                "Sample item %d from %s: a short, clearly-labelled filler "
                "summary about %s used for offline layout testing. It mirrors "
                "the real schema exactly so scripts/build_site.py cannot tell "
                "the difference between this and live data." % (i, source, topic)),
            "image": (SAMPLE_IMAGE.format(i=i % 8) if has_image else None),
        })
    articles.sort(key=lambda a: a["published_ts"], reverse=True)
    return articles


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        prog="make_sample_data.py",
        description="Generate the offline sample dataset for build_site.py.")
    parser.add_argument("--count", type=int, default=36,
                        help="how many sample stories (default 36)")
    parser.add_argument("--out", default=None,
                        help="output JSON path (default: config sample_data_file)")
    parser.add_argument("--seed", type=int, default=0,
                        help="unused deterministic knob (kept for stable CLI)")
    args = parser.parse_args(argv)

    count = max(1, args.count)

    # default path from config, so the fallback always matches the contract
    out = Path(args.out) if args.out else BASE_DIR / "data" / "sample-articles.json"
    if not out.is_absolute():
        out = BASE_DIR / out
    out = out.resolve()

    articles = build(count, args.seed)
    payload = {
        "generated_at": articles[0]["published"],  # newest item's time
        "count": len(articles),
        "articles": articles,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    import os
    os.replace(tmp, out)

    print("sample data: wrote %d article(s) -> %s" % (len(articles), out))
    print("  categories: %s"
          % ", ".join(sorted({a["category"] for a in articles})))
    print("  null images: %d (gradient placeholder path exercised)"
          % sum(1 for a in articles if not a["image"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
