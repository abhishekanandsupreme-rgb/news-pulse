#!/usr/bin/env python3
"""
build_site.py — Generates the NewsPulse static site into docs/

Pure Python 3.11 stdlib.
Reads:
  - config/site-config.json
  - data/articles.json
  - public/ (copied to docs/)

Outputs into docs/:
  - index.html (Homepage)
  - category/<category_slug>.html (Category pages)
  - article/<article_slug>.html (Article permalinks)
  - sitemap.xml
  - robots.txt
  - rss.xml
  - assets/ (CSS/JS files)
  - copied files from public/
"""

import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = REPO_ROOT / "config" / "site-config.json"
ARTICLES_FILE = REPO_ROOT / "data" / "articles.json"
PUBLIC_DIR = REPO_ROOT / "public"
DOCS_DIR = REPO_ROOT / "docs"


def load_json(path: Path):
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def escape(text: str) -> str:
    return html.escape(str(text or ""))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]


def generate_css() -> str:
    return """/* NewsPulse Modern Responsive Styles */
:root {
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --border-color: #e2e8f0;
  --primary-color: #2563eb;
  --primary-hover: #1d4ed8;
  --font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  --container-max: 1200px;
}

[data-theme="dark"] {
  --bg-color: #0f172a;
  --card-bg: #1e293b;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --border-color: #334155;
  --primary-color: #3b82f6;
  --primary-hover: #60a5fa;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--bg-color);
  color: var(--text-primary);
  font-family: var(--font-family);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

a { color: inherit; text-decoration: none; }
a:hover { color: var(--primary-color); }

header {
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.logo-group { display: flex; align-items: center; gap: 0.75rem; }
.logo-title { font-size: 1.5rem; font-weight: 800; color: var(--primary-color); }
.logo-tagline { font-size: 0.875rem; color: var(--text-secondary); }

nav { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
nav a {
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.35rem 0.65rem;
  border-radius: 0.375rem;
  color: var(--text-secondary);
  transition: all 0.2s;
}
nav a:hover, nav a.active {
  color: var(--primary-color);
  background: var(--bg-color);
}

.theme-toggle {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.35rem 0.75rem;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.85rem;
}

main {
  max-width: var(--container-max);
  margin: 2rem auto;
  padding: 0 1rem;
  flex: 1;
  width: 100%;
}

.hero-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

@media (max-width: 868px) {
  .hero-section { grid-template-columns: 1fr; }
}

.hero-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}

.hero-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.hero-card img {
  width: 100%;
  height: 280px;
  object-fit: cover;
}

.hero-content {
  padding: 1.5rem;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #fff;
  margin-bottom: 0.5rem;
}

.hero-title { font-size: 1.75rem; line-height: 1.3; margin-bottom: 0.75rem; font-weight: 700; }
.hero-desc { color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.95rem; }
.meta { font-size: 0.8rem; color: var(--text-secondary); display: flex; gap: 0.75rem; flex-wrap: wrap; }

.side-grid { display: flex; flex-direction: column; gap: 1rem; }
.small-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  padding: 1rem;
  transition: transform 0.2s;
}
.small-card:hover { transform: translateY(-2px); }
.small-card h3 { font-size: 1rem; margin-bottom: 0.5rem; line-height: 1.4; }

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--primary-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}

.card img {
  width: 100%;
  height: 180px;
  object-fit: cover;
}

.card-body {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  line-height: 1.35;
}

.card-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
  flex: 1;
}

footer {
  background: var(--card-bg);
  border-top: 1px solid var(--border-color);
  padding: 2rem 1rem;
  margin-top: auto;
}

.footer-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.footer-links { display: flex; gap: 1rem; }

.article-single {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  padding: 2rem;
  max-width: 800px;
  margin: 0 auto;
}

.article-single img {
  width: 100%;
  max-height: 400px;
  object-fit: cover;
  border-radius: 0.5rem;
  margin: 1.5rem 0;
}

.article-single h1 {
  font-size: 2rem;
  line-height: 1.3;
  margin-bottom: 1rem;
}

.article-body {
  font-size: 1.1rem;
  line-height: 1.7;
  margin-bottom: 2rem;
}

.btn-primary {
  display: inline-block;
  background: var(--primary-color);
  color: #fff;
  padding: 0.6rem 1.2rem;
  border-radius: 0.375rem;
  font-weight: 600;
  transition: background 0.2s;
}
.btn-primary:hover {
  background: var(--primary-hover);
  color: #fff;
}
"""


def generate_js() -> str:
    return """// Theme toggle logic
(function() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;
  const currentTheme = localStorage.getItem('theme') || 'light';
  if (currentTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    toggleBtn.textContent = '☀️ Light';
  } else {
    toggleBtn.textContent = '🌙 Dark';
  }

  toggleBtn.addEventListener('click', () => {
    let theme = document.documentElement.getAttribute('data-theme');
    if (theme === 'dark') {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('theme', 'light');
      toggleBtn.textContent = '🌙 Dark';
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
      toggleBtn.textContent = '☀️ Light';
    }
  });
})();
"""


def render_header(site_config: dict, current_slug: str = "", root_path: str = ".") -> str:
    site_name = escape(site_config.get("site_name", "NewsPulse"))
    tagline = escape(site_config.get("tagline", ""))
    categories = site_config.get("categories", [])

    nav_links = [f'<a href="{root_path}/index.html" class="{"active" if current_slug == "home" else ""}">Home</a>']
    for cat in categories:
        slug = cat["slug"]
        label = escape(cat["label"])
        active_cls = "active" if current_slug == slug else ""
        nav_links.append(f'<a href="{root_path}/category/{slug}.html" class="{active_cls}">{label}</a>')

    return f"""<header>
  <div class="header-inner">
    <div class="logo-group">
      <a href="{root_path}/index.html" class="logo-title">{site_name}</a>
      <span class="logo-tagline">{tagline}</span>
    </div>
    <nav>
      {''.join(nav_links)}
      <button id="theme-toggle" class="theme-toggle">🌙 Dark</button>
    </nav>
  </div>
</header>"""


def render_footer(site_config: dict, root_path: str = ".") -> str:
    site_name = escape(site_config.get("site_name", "NewsPulse"))
    now_year = datetime.now(timezone.utc).year
    return f"""<footer>
  <div class="footer-inner">
    <div>&copy; {now_year} {site_name}. All rights reserved. Self-updating news aggregator.</div>
    <div class="footer-links">
      <a href="{root_path}/rss.xml">RSS Feed</a>
      <a href="{root_path}/sitemap.xml">Sitemap</a>
    </div>
  </div>
</footer>"""


def render_page_html(
    title: str,
    description: str,
    content: str,
    site_config: dict,
    current_slug: str = "",
    canonical_url: str = "",
    root_path: str = ".",
) -> str:
    site_name = escape(site_config.get("site_name", "NewsPulse"))
    full_title = f"{title} | {site_name}" if title != site_name else site_name
    canonical_attr = f'<link rel="canonical" href="{canonical_url}" />' if canonical_url else ""

    return f"""<!DOCTYPE html>
<html lang="{site_config.get('language', 'en')}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(full_title)}</title>
  <meta name="description" content="{escape(description)}">
  {canonical_attr}
  <link rel="alternate" type="application/rss+xml" title="{site_name} RSS Feed" href="{root_path}/rss.xml" />
  <link rel="stylesheet" href="{root_path}/assets/style.css">
</head>
<body>
  {render_header(site_config, current_slug, root_path)}
  <main>
    {content}
  </main>
  {render_footer(site_config, root_path)}
  <script src="{root_path}/assets/main.js"></script>
</body>
</html>"""


def get_cat_color(cat_slug: str, categories: list) -> str:
    for cat in categories:
        if cat["slug"] == cat_slug:
            return cat.get("color", "#2563eb")
    return "#2563eb"


def render_card(article: dict, site_config: dict, root_path: str = ".") -> str:
    categories = site_config.get("categories", [])
    title = escape(article.get("title", ""))
    desc = escape(article.get("summary", article.get("description", "")))
    cat_slug = article.get("category", "world")
    cat_color = get_cat_color(cat_slug, categories)
    article_slug = article.get("slug", "")
    article_url = f"{root_path}/article/{article_slug}.html" if article_slug else article.get("link", "#")
    source_name = escape(article.get("source", article.get("feed_name", "News")))
    pub_date = article.get("published_formatted", article.get("published", ""))

    img_html = ""
    img_url = article.get("image_url") or article.get("image")
    if img_url:
        img_html = f'<img src="{escape(img_url)}" alt="{title}" loading="lazy" />'

    return f"""<article class="card">
  {img_html}
  <div class="card-body">
    <div>
      <span class="badge" style="background-color: {cat_color}">{escape(cat_slug)}</span>
    </div>
    <h3 class="card-title"><a href="{article_url}">{title}</a></h3>
    <p class="card-desc">{desc[:180]}{'...' if len(desc) > 180 else ''}</p>
    <div class="meta">
      <span>{source_name}</span>
      {f'<span>• {escape(pub_date)}</span>' if pub_date else ''}
    </div>
  </div>
</article>"""


def build_homepage(articles: list, site_config: dict, root_path: str = ".") -> str:
    categories = site_config.get("categories", [])

    if not articles:
        return "<h2>No articles found.</h2>"

    hero = articles[0]
    secondary = articles[1:5]
    latest = articles[5:29]

    # Hero rendering
    hero_title = escape(hero.get("title", ""))
    hero_desc = escape(hero.get("summary", hero.get("description", "")))
    hero_cat = hero.get("category", "world")
    hero_color = get_cat_color(hero_cat, categories)
    hero_slug = hero.get("slug", "")
    hero_url = f"{root_path}/article/{hero_slug}.html" if hero_slug else hero.get("link", "#")
    hero_source = escape(hero.get("source", hero.get("feed_name", "News")))
    hero_date = hero.get("published_formatted", hero.get("published", ""))

    hero_img = ""
    img_url = hero.get("image_url") or hero.get("image")
    if img_url:
        hero_img = f'<img src="{escape(img_url)}" alt="{hero_title}" />'

    hero_html = f"""<div class="hero-section">
  <div class="hero-card">
    {hero_img}
    <div class="hero-content">
      <span class="badge" style="background-color: {hero_color}">{escape(hero_cat)}</span>
      <h2 class="hero-title"><a href="{hero_url}">{hero_title}</a></h2>
      <p class="hero-desc">{hero_desc[:250]}{'...' if len(hero_desc) > 250 else ''}</p>
      <div class="meta">
        <span>{hero_source}</span>
        {f'<span>• {escape(hero_date)}</span>' if hero_date else ''}
      </div>
    </div>
  </div>
  <div class="side-grid">
    {''.join([
        f'''<div class="small-card">
          <span class="badge" style="background-color: {get_cat_color(sec.get('category', ''), categories)}">{escape(sec.get('category', ''))}</span>
          <h3><a href="{f"{root_path}/article/{sec.get('slug')}.html" if sec.get('slug') else sec.get('link', '#')}">{escape(sec.get('title', ''))}</a></h3>
          <div class="meta"><span>{escape(sec.get('source', sec.get('feed_name', '')))}</span></div>
        </div>''' for sec in secondary
    ])}
  </div>
</div>"""

    # Latest news grid
    latest_html = f"""<section>
  <div class="section-title">
    <span>Latest Headlines</span>
  </div>
  <div class="articles-grid">
    {''.join([render_card(a, site_config, root_path) for a in latest])}
  </div>
</section>"""

    return hero_html + latest_html


def build_category_page(cat: dict, articles: list, site_config: dict, root_path: str = "..") -> str:
    cat_slug = cat["slug"]
    cat_label = escape(cat["label"])
    cat_articles = [a for a in articles if a.get("category") == cat_slug]

    if not cat_articles:
        return f'<div class="section-title"><span>{cat_label}</span></div><p>No articles available in this category yet.</p>'

    cards_html = "".join([render_card(a, site_config, root_path) for a in cat_articles])
    return f"""<section>
  <div class="section-title">
    <span>Category: {cat_label} ({len(cat_articles)})</span>
  </div>
  <div class="articles-grid">
    {cards_html}
  </div>
</section>"""


def build_article_page(article: dict, site_config: dict) -> str:
    categories = site_config.get("categories", [])
    title = escape(article.get("title", ""))
    desc = escape(article.get("summary", article.get("description", "")))
    cat_slug = article.get("category", "world")
    cat_color = get_cat_color(cat_slug, categories)
    source_name = escape(article.get("source", article.get("feed_name", "Source")))
    original_link = article.get("link", "#")
    pub_date = article.get("published_formatted", article.get("published", ""))

    img_html = ""
    img_url = article.get("image_url") or article.get("image")
    if img_url:
        img_html = f'<img src="{escape(img_url)}" alt="{title}" />'

    return f"""<article class="article-single">
  <span class="badge" style="background-color: {cat_color}">{escape(cat_slug)}</span>
  <h1>{title}</h1>
  <div class="meta" style="margin-bottom: 1rem;">
    <span>By {source_name}</span>
    {f'<span>• {escape(pub_date)}</span>' if pub_date else ''}
  </div>
  {img_html}
  <div class="article-body">
    <p>{desc}</p>
  </div>
  <div style="margin-top: 2rem;">
    <a href="{escape(original_link)}" target="_blank" rel="noopener noreferrer" class="btn-primary">Read full story on {source_name} &rarr;</a>
  </div>
</article>"""


def generate_sitemap(urls: list, site_config: dict) -> str:
    sitemap_items = []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for url in urls:
        sitemap_items.append(
            f"  <url>\n    <loc>{escape(url)}</loc>\n    <lastmod>{now_iso}</lastmod>\n  </url>"
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{'\n'.join(sitemap_items)}
</urlset>"""


def generate_robots(base_url: str) -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {base_url.rstrip('/')}/sitemap.xml
"""


def generate_rss(articles: list, site_config: dict) -> str:
    site_name = escape(site_config.get("site_name", "NewsPulse"))
    tagline = escape(site_config.get("tagline", ""))
    base_url = site_config.get("base_url", "").rstrip("/")

    items = []
    for a in articles[:30]:
        title = escape(a.get("title", ""))
        link = escape(f"{base_url}/article/{a.get('slug')}.html" if a.get("slug") else a.get("link", ""))
        desc = escape(a.get("summary", a.get("description", "")))
        pub_date = a.get("published_formatted", a.get("published", ""))

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{desc}</description>
      <guid>{link}</guid>
      {f'<pubDate>{pub_date}</pubDate>' if pub_date else ''}
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{site_name}</title>
    <link>{base_url}/</link>
    <description>{tagline}</description>
{'\n'.join(items)}
  </channel>
</rss>"""


def main():
    print("[build_site] Starting static site build...")

    site_config = load_json(CONFIG_FILE)
    articles_data = load_json(ARTICLES_FILE)

    articles = []
    if isinstance(articles_data, list):
        articles = articles_data
    elif isinstance(articles_data, dict):
        articles = articles_data.get("articles", [])

    base_url = site_config.get("base_url", "https://abhishekanandsupreme-rgb.github.io/news-pulse").rstrip("/")

    # Ensure clean output dir
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Assets dir
    assets_dir = DOCS_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "style.css").write_text(generate_css(), encoding="utf-8")
    (assets_dir / "main.js").write_text(generate_js(), encoding="utf-8")

    # Copy files from public/ to docs/
    if PUBLIC_DIR.is_dir():
        for item in PUBLIC_DIR.iterdir():
            if item.is_file():
                shutil.copy(item, DOCS_DIR / item.name)

    urls_for_sitemap = [f"{base_url}/"]

    # Ensure all articles have a slug
    for art in articles:
        if "slug" not in art:
            title_slug = slugify(art.get("title", ""))
            art["slug"] = f"{art.get('id', 'art')}-{title_slug}"

    # 1. Homepage
    home_content = build_homepage(articles, site_config, root_path=".")
    home_html = render_page_html(
        title=site_config.get("site_name", "NewsPulse"),
        description=site_config.get("description", ""),
        content=home_content,
        site_config=site_config,
        current_slug="home",
        canonical_url=f"{base_url}/",
        root_path=".",
    )
    (DOCS_DIR / "index.html").write_text(home_html, encoding="utf-8")

    # 2. Categories
    category_dir = DOCS_DIR / "category"
    category_dir.mkdir(parents=True, exist_ok=True)

    for cat in site_config.get("categories", []):
        cat_slug = cat["slug"]
        cat_url = f"{base_url}/category/{cat_slug}.html"
        urls_for_sitemap.append(cat_url)

        cat_content = build_category_page(cat, articles, site_config, root_path="..")
        cat_html = render_page_html(
            title=f"{cat['label']} News",
            description=f"Latest news and updates in {cat['label']}.",
            content=cat_content,
            site_config=site_config,
            current_slug=cat_slug,
            canonical_url=cat_url,
            root_path="..",
        )
        (category_dir / f"{cat_slug}.html").write_text(cat_html, encoding="utf-8")

    # 3. Articles
    article_dir = DOCS_DIR / "article"
    article_dir.mkdir(parents=True, exist_ok=True)

    for art in articles:
        slug = art["slug"]
        art_url = f"{base_url}/article/{slug}.html"
        urls_for_sitemap.append(art_url)

        art_content = build_article_page(art, site_config)
        art_html = render_page_html(
            title=art.get("title", "Article"),
            description=art.get("summary", art.get("description", ""))[:160],
            content=art_content,
            site_config=site_config,
            canonical_url=art_url,
            root_path="..",
        )
        (article_dir / f"{slug}.html").write_text(art_html, encoding="utf-8")

    # 4. Sitemap & Robots & RSS
    (DOCS_DIR / "sitemap.xml").write_text(generate_sitemap(urls_for_sitemap, site_config), encoding="utf-8")
    (DOCS_DIR / "robots.txt").write_text(generate_robots(base_url), encoding="utf-8")
    (DOCS_DIR / "rss.xml").write_text(generate_rss(articles, site_config), encoding="utf-8")

    print(f"[build_site] Build complete! Site generated in {DOCS_DIR} with {len(urls_for_sitemap)} pages/URLs.")


if __name__ == "__main__":
    main()
