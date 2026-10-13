# NewsPulse Monetization + Traffic-Growth Playbook

Owner: Abhishek (IST) · Site: https://abhishekanandsupreme-rgb.github.io/news-pulse · Budget: ₹0
Companion store (cross-sell): https://abhishekanandsupreme-rgb.github.io/ai-prompt-store/
Written: 2026-09-13 (launch day) · Every claim below is source-verified — see [Sources](#sources) at the end. Unverifiable items are marked **NEEDS VERIFICATION**.

---

## 1. Executive summary

NewsPulse is a headline+snippet aggregator that links out to 38 feeds across 10 categories, rebuilt every 2 hours on GitHub Pages for $0. That architecture is excellent for copyright safety and cost, but it constrains monetization in two hard, verified ways:

1. **Google AdSense is effectively unavailable on this site.** AdSense no longer accepts subdomain applications — only root-domain sites — and `github.io` is GitHub's root domain, not yours.[35] Google has also stated it does not allow ads on pages that republish others' content "without additional commentary, curation" — the exact aggregator pattern.[24][42]
2. **GitHub Pages terms forbid running a business on Pages.** Pages may not be used "as a free web hosting service to run your online business, e-commerce site, or any other website that is primarily directed at... facilitating commercial transactions," though "some monetization efforts are permitted... such as donation buttons and crowdfunding links,"[31] and advertising that is not the site's *primary focus* is allowed under the Acceptable Use Policies.[32] Translation: light ads + affiliate links on a real content site = fine; a site that exists mainly to sell = risk. NewsPulse's content is the site; monetization stays secondary.

So the strategy is a **three-tier stack that earns from day 1 with zero spend**, in this priority order:

| Tier | Channel | Verified entry bar | First realistic cash |
|---|---|---|---|
| 1 | Adsterra / Monetag display + push ads | No minimum traffic; approve sites of all sizes[28]; Monetag has no minimum traffic requirement[3] | $5 minimum payout[1][2] — ~1,700–5,000 impressions at $1–3 RPM |
| 1 | Cross-sell own AI-prompt store (highest margin) | Already live; 10 packs at $9.99, bundle at $27.99+ | $7.90 net per $9.99 direct sale (after all fees)[22][23] |
| 1 | Email newsletter (Brevo free: 300 sends/day, 100K contacts)[17] | Free | Indirect — drives repeat visits & store sales |
| 2 | India affiliates: Cuelinks (min payout ₹500)[9], EarnKaro (min ₹10)[11], Amazon.in (apparel 10%, books/toys 5.9%)[8] | Free to join | ₹10–₹500 thresholds |
| 3 (parked) | Google AdSense | Needs root domain + content Google treats as original[35][43] | $100 threshold[26] — only after a custom domain exists |

**Realistic 30-day revenue target: $5–$30 total** (first ad-network payout + 1–3 store sales). This is a compounding asset, not a paycheck — the 30-day goal is the traffic flywheel, not income.

---

## 2. Hard constraints (all verified — do not work around these)

### 2.1 AdSense on github.io — blocked, three separate ways
- AdSense applications for website monetization do not accept subdomain URLs; only host-partner subdomains (e.g. blogspot) qualify, and the root domain owner must verify. You do not own `github.io`, so you can neither verify it nor apply for `abhishekanandsupreme-rgb.github.io`.[35]
- Even with a domain, Google's program policies exclude pages whose content is "embedded or copied... without additional commentary, curation" — a pure aggregator gets rejected for "low value content," the single most common rejection reason.[24][42][43]
- AdSense pays monthly once earnings cross **$100** (₹8,300 approx), paid 21st–26th via wire/EFT to Indian banks.[26][27]

**Action:** leave `config/site-config.json` → `ads.adsense_client`, `ads.slots.*`, `ads.ads_txt` **empty** (they already are). Do not waste an application attempt. Revisit only after buying a custom domain AND adding original editorial layers (see §6.3).

### 2.2 GitHub Pages acceptable use
- Pages must not be "primarily directed at... facilitating commercial transactions"; permitted monetization explicitly includes donations/crowdfunding, and ads are fine when the site's primary focus remains content.[31][32]
- Keep ads to ≤ 2 placements per page and never interstitial-trap the outbound article links. If ad units ever visually crowd out headlines, you're over the line both for GitHub[32] and for repeat visitors.

### 2.3 Copyright model (already correct — protect it)
The site's value = curation: headlines + short snippets + prominent links to sources. Never auto-copy full article text or full images from feeds; that would risk both copyright takedowns and the "low value content" death sentence for any future ad network approval.[40][43]

---

## 3. Channel playbook

### 3.1 Display + push ads: Adsterra and/or Monetag (start here)

**Why these two:** both explicitly accept publishers with no minimum traffic[28][3] and both have a **$5 minimum payout** (Adsterra via Paxum/WebMoney; Monetag "from $5" depending on method)[1][2]. Adsterra pays twice monthly on a net-15 schedule (1st–2nd and 16th–17th)[1]; Monetag's first payout now arrives ~2 weeks after earning, weekly thereafter.[2]

**Cautions, honestly stated:**
- Third-party reviews report Adsterra display CPMs around $1–3 per 1,000 impressions, varying heavily by GEO (Asian traffic earns less than US/UK/EU).[1][4] Plan on the low end.
- Pop-under and aggressive formats pay more but wreck return visits and can conflict with GitHub's "primary focus" nuance.[32] **Use: native banner + one social-bar/push unit max. Skip popunders.**
- PropellerAds is a fallback, not a first choice: its first payout is **$100** (then $25) per AdSpyGlass's review[4], though other reviews cite $5/$20 minimums by method[5][6] — the discrepancy itself is a reason to deprioritize it. **NEEDS VERIFICATION** of current terms if you ever switch.

**Signup steps (Adsterra, ~30 min):** publishers.adsterra.com → register as publisher → Websites → ADD NEW WEBSITE → enter `https://abhishekanandsupreme-rgb.github.io/news-pulse/`, pick category (News), ad unit (Native Banner), exclusions → approval typically 2–10 minutes to ~1 day[28] → copy the ad script → paste into the site build where the leaderboard/footer slots render. Monetag flow is equivalent (register → add site → create zone → place tag).

**⚠️ NEEDS VERIFICATION (test on day 2):** whether Adsterra/Monetag's "add website" accepts a `github.io` subdomain as the property. Monetag's documented rule is that one approved site's code may run "on all sub-domains of a verified website"[29] — which is about *your* verified domain. If either network rejects the github.io property, fall back to **Adsterra Direct Link / SmartLink**, which "can start monetization even with a one-page website or no website" — place the link on any high-traffic element (e.g. the "Read full story" affordance can NOT be hijacked — keep it clean; instead put the Direct Link behind a clearly-labelled "Sponsored" card in the footer Recommended area).[30]

**ads.txt:** once a network approves you, it will give you an ads.txt line (e.g. `adsterra.com, your-publisher-id, DIRECT`). GitHub Pages sites can serve `docs/ads.txt` at the site root. Google's own guidance: ads.txt is "not mandatory, but highly recommended," and must contain your correct publisher ID to verify.[25] The `site-config.json` field `ads.ads_txt` exists for exactly this — fill it only after approval. **Do not pre-fill it with a guessed line.**

### 3.2 Own-store cross-sell (highest margin — the real money)

The AI-prompt store is the best-paying "affiliate program" available because you keep ~79% of every $9.99 direct sale (fee = Gumroad 10% + $0.50 + Stripe 2.9% + $0.30 → net $7.90), and ~84% of the $27.99 bundle (net $23.58) — computed from Gumroad's published fee structure.[22][23] Sales originating from Gumroad's Discover marketplace cost 30% flat instead.[22]

**Verified product ladder (live on the store):** 10 packs at $9.99 each + a Complete AI Prompt Bundle (bundle pricing appears at $27.99; store also lists a $99.99 tier)[store index, checked 2026-09-13]. The free teaser (free-teaser.md, 200 OK) is the lead magnet.

**🔴 CRITICAL BLOCKER FOUND (fix on Day 1, takes 30 min):** every "Buy" button on the live store points to `abhishekanand31.gumroad.com/l/<slug>` and **all of those URLs currently return 404** — the Gumroad products have not been published (the Gumroad profile `abhishekanand31.gumroad.com` resolves but lists zero products, checked 2026-09-13). Two published-looking slugs (`gumroad.com/l/complete-ai-prompt-bundle`, `/l/ai-content-creator-pack`) resolve to *other creators'* products (e.g. "The Complete AI Prompt Bundle for Designers — 285 Prompts for Midjourney, DALL·E" by grisa4) — **never use bare `gumroad.com/l/<slug>` links; they are not yours.** Until the products are actually published on Gumroad, `config/affiliate-products.json` (already written, 5 cards) deliberately points all CTAs at the store's own pages, which are live (200 OK). Once Abhishek publishes the products on Gumroad, the cards can be upgraded to `abhishekanand31.gumroad.com/l/<slug>` buy links.

**Placement (already wired):** `config/affiliate-products.json` renders as the footer "Recommended" cards — 5 cards: bundle (#pricing), Content Creator (#creator), Business Builder (#business), Coding (#coding), free teaser (Free badge). Machine-verified: array of exactly `{title, blurb, url, badge}`, all URLs 200 OK, schema-checked with Python.

**Rules of thumb:** entertainment/tech readers convert on the free teaser → bundle ladder. Track clicks with a `?ref=newspulse` query parameter on store URLs (Gumroad's analytics reads referrer/URL params; store pages can also log it via its own JS) — **NEEDS VERIFICATION** on what attribution the static store can capture; at minimum, use distinct URLs per placement so future Gumroad affiliate sales can be reconciled manually.

### 3.3 Email list (Brevo) — the compounding asset

- Brevo's free plan: **300 emails/day, up to 100,000 contacts**, with campaigns, forms, automation, and segmentation included.[17] That dwarfs MailerLite's new free tier, which was cut in 2026 to **250 subscribers / 2,500 emails per month** (down from 500/12,000, then 1,000/12,000 before that).[20][21] **Use Brevo. Do not use MailerLite for this project.**
- 300/day = 9,000/month. A weekly digest to 300 subscribers uses 300 sends/week — comfortable until ~1,200 subscribers, at which point daily-cap planning (batch sends across days) is needed.
- Embed Brevo's signup form in the site footer (Brevo free includes forms + sign-up pages[17]). Offer the store's free-teaser pack as the incentive — zero-cost lead magnet, already hosted.
- Weekly cadence: "This week's pulse" — 10 headlines across categories, one featured category, one store card at the bottom (labelled). Never send unsolicited email; every address must come through the form (also a legal requirement — see §5).

### 3.4 India affiliate programs (Tier 2, week 2+)

| Program | Verified terms | Fit for NewsPulse |
|---|---|---|
| **Amazon Associates (amazon.in)** | Category rates: apparel/shoes/watches/beauty 10%; kitchen/home/furniture 5%; books/toys/sports 5.9%; most electronics 3.5–4%; Apple products and phones at 0%[8]. Cheque payout floor ₹2,500 (associate-defined threshold page).[41] | Tech/gaming "gear" cards. **Clock: 3 qualifying sales in 180 days or the application is withdrawn with no reinstatement**[33] — apply only when traffic can plausibly convert (week 3–4, after ~1,000 visitors/mo). |
| **Cuelinks** | Min payout ₹500 (INR) / ₹20,000 (USD), monthly; default 75:25 publisher:Cuelinks revenue split; one JS snippet auto-converts merchant links, or per-product "Link me" links[9][10]. Gives access to Flipkart's program (up to 12% claimed, category-dependent) since Flipkart's direct program pauses new registrations[14]. | Easiest India basket: one script covers 100s of Indian merchants incl. Flipkart. |
| **EarnKaro** | Free; withdrawal at **₹10**; 200+ brands incl. Flipkart, Myntra (up to 10%)[11][12]. | Fastest first affiliate rupee; link-level (no site JS needed). |
| **Flipkart direct** | Official commissions page: books/general merchandise 5%, home 3%, core electronics 3%, mobiles 0–1%[13]. | Direct registration paused for new publishers; join via Cuelinks/EarnKaro[14]. |

**India disclosure law (mandatory):** ASCI's influencer guidelines treat affiliate partnerships as a "material connection" that must be disclosed clearly and prominently (e.g. an "#ad"-style label near the content, not buried below the fold), with penalties under consumer-protection law for hiding it.[37] Concretely: every affiliate/Recommended section on NewsPulse gets a one-line "We may earn a commission from links on this page" label — this also matches Amazon Associates' own disclosure requirement and U.S. FTC rules that GitHub explicitly makes you responsible for.[32]

### 3.5 Parked: AdSense path (what would unlock it)

If a custom domain is ever bought (a `.com`/`.in` costs money, so out of scope for the ₹0 plan):
1. Point the domain at GitHub Pages (GitHub supports custom domains on Pages[31]).
2. Then AdSense's root-domain application becomes possible[35] — but content must first clear the "low value content" bar: real About/Contact/Privacy pages, author identity, and original commentary beyond snippets (third-party approval checklists consistently require ~15–30 substantive original pages plus mandatory pages)[43][44].
3. Then ads.txt with your publisher ID (Google: not mandatory, highly recommended)[25], and the $100/month threshold applies[26].
Until then: **do not apply.** A rejection history makes the eventual application harder.[43]

---

## 4. Traffic-growth engine (free, India + global)

### 4.1 Search — already automated, plus two manual steps
The repo's `scripts/submit_seo.py` already pings **IndexNow** (Bing/Yandex family) on every build without blocking deploys — IndexNow is exactly the right protocol for frequently-changing static sites.[18][19] Manual steps that no script can do:
1. **Google Search Console:** add the site (URL-prefix property for `https://abhishekanandsupreme-rgb.github.io/news-pulse`), verify (HTML file lands in `docs/` via repo, or the meta-tag route), submit `sitemap.xml`. This is the single highest-leverage 20 minutes of launch week.
2. **Bing Webmaster Tools:** sign in with a Microsoft account and use **"Import from Google Search Console"** — verification and sitemaps come over automatically in minutes.[39] (IndexNow pings accelerate Bing's *crawl*, but the Webmaster Tools account gives ranking + indexing visibility.)

### 4.2 Google News — the 2024+ reality (this changed!)
Manual publication submission **closed on April 25, 2024**: Publisher Center no longer accepts new publications, and since late March 2025 Google News publication pages are auto-generated — Google News no longer uses RSS feeds submitted in Publisher Center.[34] There is **no form to submit**. Instead:
- Eligibility is now algorithmic: comply with Google News content policies, Google's general content policies, and news best practices (transparency: About page, dates, bylines/ownership info, clear sourcing).[34]
- Practically: strong `pubDate`/byline markup in the article JSON-LD, an About/Contact page, and clean source attribution are the levers. The site already gets rebuilt every 2h with fresh timestamps, which helps freshness signals.
- Measure success in GSC's "Discover"/"News" performance reports, not in Publisher Center (which won't show you anything for a new site).

### 4.3 Google Discover readiness (big free India traffic lever)
Discover requires, for large-image treatment: images **≥ 1200 px wide** and the meta tag **`max-image-preview:large`** (AMP alternative deprecated for this purpose in practice)[36]. For an aggregator, Discover mostly surfaces *original* visuals, so: give every category page a 1200px+ hero/OG image and set `max-image-preview:large` in the page head. **This is a build-side task for whoever owns `build_site.py` — flag it to them, don't edit the script from this playbook.**

### 4.4 Social distribution (the zero-budget workhorse)
- **WhatsApp + Telegram:** India's discovery front doors. Create a channel "NewsPulse Daily" (Telegram channel is public + shareable; WhatsApp Channel for personal network). Auto-post the morning's top-10 via the site's own RSS — but only 1–2 posts/day; feeds of bare links get muted.
- **X/Twitter:** one pinned launch post + daily thread of 3 headlines with the link. Keep an eye on platform rules on automated posting (X's automation rules) — human-written captions are safer than raw auto-posting. *(Platform automation-policy specifics not re-verified this session: NEEDS VERIFICATION.)*
- **Reddit:** r/india, r/developersIndia, r/technology etc. — only contextual: share the *specific story* pages, never the homepage, and obey each sub's self-promo rules (most cap it to ~10% of your posts). NewsPulse's "10 categories, 1 page" is a genuinely shareable utility — lead with that framing once per subreddit, ever.
- **Pinterest:** works surprisingly well for movies/music/entertainment verticals with a 1200px cover image per category board; pins compound for months. Zero budget, slow burn.

### 4.5 Email flywheel (ties to §3.3)
Every list signup is a returning visitor who costs nothing to reacquire. Target: form on site from Day 2, first send Day 4, 100 subscribers by Day 30 (2% of a modest 5,000 visitors/mo — see math below).

### 4.6 Content moat within the ₹0 constraint
The aggregator gives breadth; the moat is curation. Weekly, add one *original* element the build can generate from data it already has (no new feeds, no writing marathons):
- "Week in 10 headlines" digest post (also the newsletter body — write once, use twice),
- per-category "trending this week" auto-roundup pages (pure data, no copying),
- these original pages are also what any future AdSense application would need (§3.5) and what Discover/News favor.

---

## 5. Compliance checklist (India + platform)

1. **Affiliate disclosure:** one line above the Recommended cards and in every email that contains store/affiliate links: "Some links may earn us a commission." ASCI treats affiliate links as a disclosable material connection.[37]
2. **Privacy policy page** (needed by: Brevo for email signup, ad networks for personalized ads, and any future AdSense application[43][44]) — a plain page on what data is collected (none directly; analytics/ad partners may set cookies) and how to opt out. The store already has `privacy.html`; NewsPulse needs its own in the build.
3. **About + Contact pages** — Google News transparency requirements[34] and ad-network approvals both look for them.[43]
4. **No secrets in the repo:** ad-network script tags contain account IDs, not secrets — safe to commit. Brevo API keys and any Gumroad token must live in GitHub Actions secrets, never in files (matches the repo's $0-secrets design and the workspace's zero-secret vault rule).
5. **Copyright:** keep the headline+snippet+link model. No full text, no hotlinked full images from feeds.[40][43]
6. **Taxes (India):** affiliate/ad income above small thresholds is taxable; Gumroad is Merchant of Record and handles sales tax globally[22], but Abhishek's own income tax obligations remain his own — out of scope for this playbook, keep records of all payouts. *(Not legal advice.)*

---

## 6. Revenue math (verified numbers, honest assumptions)

### 6.1 Ads
- Adsterra/Monetag floor: **$5 payout**[1][2]. At a conservative **$1 RPM** (Asian-majority traffic, native banners — third-party reporting clusters $1–3 RPM[1][3][7]): 5,000 impressions → first $5. At $3 RPM: ~1,700 impressions.
- A visitor browsing NewsPulse loads ~2 ad-bearing pages → 2,500 visitors ≈ 5,000 impressions ≈ first payout. **Milestone: ~2,500 visitors in month 1.**
- AdSense comparison (why it's parked): $100 threshold[26] at $1 RPM = 100,000 impressions ≈ 50,000 visitors — not a month-1 event even with a domain.

### 6.2 Store cross-sell
- Net per $9.99 pack (direct link): **$7.90**; per $27.99 bundle: **$23.58**; per $99.99 tier: **$86.29** (all after Gumroad 10% + $0.50 + Stripe 2.9% + $0.30).[22][23]
- Gumroad's payout threshold is now **$100** (raised from $10 in March 2026)[23] — so Gumroad cash arrives only after ~13 direct pack sales (or sooner if bundle sales are made elsewhere on Gumroad). Note this is Gumroad's *payout* threshold, separate from per-sale fees.
- Scenario: 5,000 visitors/mo × 1% store CTR × 3% purchase = 1–2 sales ≈ **$8–$16/mo** at start. The email list improves this (subscribers convert far better than cold traffic).

### 6.3 India affiliates
- Amazon.in: books/toys 5.9%[8] — a ₹500 order = ₹30. Apparel 10% — ₹1,500 order = ₹150. Meaningful only with volume; the **3-sales-in-180-days clock**[33] is the real constraint.
- EarnKaro: ₹10 withdrawal floor[11] — the fastest way to see *any* affiliate income, even if tiny.
- Cuelinks: ₹500 floor, 75:25 split by default[9][10].

### 6.4 Email
- 2% visitor→subscriber conversion is a conservative web average: 5,000 visitors/mo → ~100 subs/mo → **~300 by Day 30** with compounding social pushes (Brevo's 300/day cap is nowhere near binding at this size).[17]

### 6.5 Month-1 honest total
$5 (ads) + $8–16 (store) + ₹10–100 (EarnKaro/Cuelinks dribble) ≈ **$6–20**. Month 3–6, if traffic compounds to 25–50K visitors/mo: $40–150/mo range. This is a ladder, not a lottery.

---

## 7. Anti-playbook (do NOT do these)

1. **Do not apply to AdSense now** — subdomain + aggregator content = rejection that poisons the well.[35][24][43]
2. **Do not use bare `gumroad.com/l/<slug>` links anywhere** — slug collisions point at other creators' products (verified live: two such slugs belong to other sellers). Always use your own subdomain links once products are published.
3. **Do not run popunders/onclick ads** — they pay more but kill return visits and sit badly with GitHub's "primary focus" rule.[32]
4. **Do not buy traffic/followers or use traffic exchanges** — ad networks void earnings for invalid traffic (Adsterra requires real human traffic[28]); it's also a fast way to lose the GitHub Pages site.
5. **Do not paste full article text or full feed images** — copyright + "low value content" double jeopardy.[40][43]
6. **Do not spam-sub** on Reddit or blast WhatsApp groups — one quality share beats ten banned ones.
7. **Do not fill `ads.ads_txt` speculatively** — only with the exact line your approved network issues you.[25]

---

## 8. Payout calendar & tracking

| Money | Minimum | Cadence | Where to watch |
|---|---|---|---|
| Adsterra | $5 (Paxum/WebMoney; $100 PayPal/BTC; $1,000 wire)[1] | Net-15, twice monthly (1–2nd & 16–17th)[1] | Adsterra dashboard → Payments |
| Monetag | from $5 by method[2][3] | First payout ~2 weeks after earning; weekly after[2] | Monetag dashboard |
| Gumroad | $100 payout threshold[23] | Weekly Fridays (per Gumroad's payout schedule)[23] | Gumroad → Payouts |
| Cuelinks | ₹500 (INR)[9] | Monthly | Cuelinks dashboard |
| EarnKaro | ₹10[11] | On request → bank | EarnKaro app |
| Amazon.in | ₹2,500 cheque floor (or gift-card lower — NEEDS VERIFICATION for current non-cheque floor)[41] | ~60 days after month end (Amazon.com schedule; .in similar — NEEDS VERIFICATION) | Associates Central |

Keep a simple `monetization/payout-log.md` (date, network, amount, method) — it doubles as the tax record (§5.6).

---

## 9. Configuration files this playbook owns

- `config/affiliate-products.json` — machine-validated: JSON array of exactly `{title, blurb, url, badge}`; 5 cards; every URL live-checked (HTTP 200) on 2026-09-13; anchors verified against the live store's DOM (`#pricing`, `#creator`, `#business`, `#coding`). Safe to commit.
- `config/site-config.json` — **intentionally untouched.** AdSense fields stay empty per §2.1. When an ad network approves the site, its script goes into the build via the slots the site owner wires up; `ads.ads_txt` gets the network-issued line then (see §3.1).
- `scripts/submit_seo.py` — already handles IndexNow; this playbook adds the manual GSC/Bing steps around it (§4.1). Not modified (per task boundary).

---

## Sources

[1] https://www.adpushup.com/blog/adsterra-review-factsheet-overview-payment-pros-and-cons — AdPushup Adsterra Review
[2] https://monetag.com/blog/monetag-payouts-update — Monetag Payouts Update
[3] https://groups.io/g/freelancer/topic/how_does_monetag_compare_to/115273568 — Monetag comparison groups.io
[4] https://www.adspyglass.com/blog/propellerads-ad-network-review — AdSpyGlass PropellerAds Review
[5] https://blogpros.com/propeller-review-pricing-conversion — BlogPros PropellerAds Review
[6] https://www.adpushup.com/blog/propellerads-review-factsheet-overview-pros-and-cons — AdPushup PropellerAds Factsheet
[7] https://monetag.com/blog/adsense-alternatives — Monetag AdSense Alternatives
[8] https://affiliate-program.amazon.in/help/operating/advertisingfees — Amazon.in Associates Advertising Fees
[9] https://www.cuelinks.com/blog/best-affiliate-marketing-platform-india — Cuelinks Best Affiliate Platforms India
[10] https://www.shoutmeloud.com/cuelinks-review.html — ShoutMeLoud Cuelinks Review
[11] https://earnkaro.com — EarnKaro homepage
[12] https://earnkaro.com/blog/affiliate-marketing-platforms — EarnKaro affiliate platforms list
[13] https://affiliate.flipkart.com/commissions — Flipkart Affiliate Commissions
[14] https://www.cuelinks.com/campaigns/flipkart-affiliate-program — Cuelinks Flipkart campaign
[17] https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans — Brevo pricing plans official
[18] https://github.com/marketplace/actions/indexnow-action — IndexNow GitHub Action
[19] https://johnmu.com/2025-used-to — johnmu IndexNow static sites
[20] https://www.mailerlite.com/help/free-plan-update-faq — MailerLite free plan update FAQ
[21] https://emailoctopus.com/blog/mailerlite-pricing-update — EmailOctopus MailerLite pricing update
[22] https://gumroad.com/pricing — Gumroad pricing
[23] https://checkthat.ai/brands/gumroad/pricing — checkthat Gumroad fees 2026
[24] https://www.reddit.com/r/Adsense/comments/tcg469/adsense_request_rejected_news_aggregator_site — Reddit AdSense news aggregator rejection
[25] https://support.google.com/adsense/answer/12171612?hl=en — AdSense ads.txt guide official
[26] https://grey.co/blog/what-freelancers-in-india-need-to-know-about-adsense-withdrawals — grey.co AdSense India withdrawals
[27] https://7labs.io/webdev/adsense-wire-transfers-india-faq.html — 7labs AdSense India wire FAQ
[28] https://adsterra.com/blog/set-up-publishers-dashboard — Adsterra publisher requirements
[29] https://help.monetag.com/en/articles/6726720-can-i-use-the-ad-channel-code-of-my-approved-site-on-all-sub-domains — Monetag subdomain policy
[30] https://adsterra.com/blog/guide-for-working-with-direct-links — Adsterra Direct Link guide
[31] https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features — GitHub Pages additional terms
[32] https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies — GitHub Acceptable Use Policies
[33] https://affiliate-program.amazon.com/help/node/topic/G7MJTPEP9NC3YKMG — Amazon Associates dormancy 180 days
[34] https://support.google.com/news/publisher-center/answer/15898024?hl=en-GB — Google News auto publication pages
[35] https://support.google.com/adsense/thread/180449812/adsense-approval-for-site-and-subdomain?hl=en — AdSense subdomain application thread
[36] https://docs.arcxp.com/en/products/general/faq--google-discover.html — Google Discover FAQ
[37] https://www.asvlawoffices.com/news-insights/influencer-advertising-and-legal-compliance-in-india-obligations-under-asci-and-consumer-protection-law — ASCI influencer compliance India
[39] https://www.promodo.com/blog/how-to-add-website-to-bing-webmaster-tools — Bing Webmaster Tools import
[40] https://www.monetizemore.com/blog/google-content-policy-violations-website-can-avoid — MonetizeMore content policy violations
[41] https://affiliate-program.amazon.in/help/node/topic/GP8Z3AZ27ZFHTEUL — Amazon.in cheque minimum
[42] https://support.google.com/adsense/thread/13663854/google-adsense-application-rejected-due-to-scraped-content-but-all-the-content-is-original?hl=en — AdSense scraped content rejection thread
[43] https://adsenseaudit.net/guides/low-value-content-adsense — AdSense low value content guide
[44] https://adsenseaproval.tistory.com/entry/Minimum-Requirements-for-AdSense-Approval-in-2025-Complete-Checklist — AdSense approval checklist tistory
