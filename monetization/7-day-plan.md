# NewsPulse — 7-Day Launch Action Plan (Days 1–7, all free)

Every task below is 15–60 minutes. Times are IST. Tick the checkbox when the *verified outcome* exists (a URL, an account, a live page) — not when you "did the thing."

Prereq check (Day 0): live site at https://abhishekanandsupreme-rgb.github.io/news-pulse/ returning 200 — it returned 404 during the writing of this plan (launch pending). If still 404 on Day 1, first fix the deploy (README's troubleshooting table), because every task below assumes a live site.

## Day 1 (launch day) — site live + the Gumroad fix

- [ ] **Verify site is live** (https://abhishekanandsupreme-rgb.github.io/news-pulse/ → 200) and the latest Actions run is green.
- [ ] **🔴 Publish the 10 products on Gumroad** (the store's biggest money leak — every Buy button on the live store currently 404s; verified 2026-09-13). For each of the 10 packs in `C:/Users/asus/ai-prompt-store/GUMROAD-LISTINGS.md`: gumroad.com → Products → New → paste name/description/price ($9.99) → upload `products/<slug>/prompts.md` → Publish. Test ONE link end-to-end with a real checkout (then refund) before moving on.
- [ ] **Fix store buy-links**: after publishing, confirm `https://abhishekanand31.gumroad.com/l/ai-content-creator-pack` (etc.) returns 200. If Gumroad assigned different slugs, update the store HTML's hrefs. **Never** switch to bare `gumroad.com/l/<slug>` links — those slugs collide with other creators (verified live).
- [ ] **Share launch**: one post on X + one WhatsApp status + one Telegram channel post with the site link. (5 min each; done is better than perfect.)

## Day 2 — search engines + ad network application

- [ ] **Google Search Console**: search.google.com/search-console → Add property → URL prefix → `https://abhishekanandsupreme-rgb.github.io/news-pulse` → verify via HTML file/meta tag (coordinate with the site build so the tag lands in `docs/`) → Sitemaps → submit `sitemap.xml`. Outcome: GSC property exists, sitemap status "Success"/"Could not fetch → investigate".
- [ ] **Bing Webmaster Tools**: bing.com/webmasters → sign in (Microsoft account) → "Import from Google Search Console" → pick the property → import. Verification + sitemap come over automatically (verified process[39]). Outcome: site listed with green verification.
- [ ] **Apply: Adsterra publisher account** → add site `https://abhishekanandsupreme-rgb.github.io/news-pulse/` (category News, Native Banner unit). Approval is typically minutes-to-a-day[28]. If the property is rejected for being a subdomain, escalate to the Direct Link route (playbook §3.1) and note it in `monetization/payout-log.md`.
- [ ] **Brevo**: create free account (brevo.com) → verify sender (use demosupreme001@gmail.com or a from-name) → create a signup form → hand the embed code to the site build for the footer. Outcome: form live on site, sends a test confirmation email.

## Day 3 — ads live + first SEO signals

- [ ] **Place the ad script** once Adsterra approves: leaderboard + footer slots only (≤2 per page). If the site build's slots aren't wired yet, coordinate — do not hand-hack the generated `docs/` (it's rebuilt every 2h).
- [ ] **ads.txt**: copy the exact line Adsterra issues into `site-config.json` → `ads.ads_txt` (or `docs/ads.txt` per the build's convention). Never guess the format.[25]
- [ ] **GSC URL inspection**: request indexing for the homepage + 3 category pages (GSC → URL Inspection → Request indexing). Do a handful/day; don't bulk-submit hundreds.
- [ ] **IndexNow sanity check**: confirm the last Actions run's SEO step logged a successful ping (it's `continue-on-error`, so check its log line explicitly).

## Day 4 — first newsletter + India affiliate signups

- [ ] **EarnKaro**: earnkaro.com → sign up free → grab your profile/share links. ₹10 withdrawal floor = the fastest first affiliate rupee[11].
- [ ] **Cuelinks**: cuelinks.com → publisher signup (needs PAN + bank details + a site — the live NewsPulse URL works). Note: approval typically takes days; start now. ₹500 payout floor, monthly.[9][10]
- [ ] **Write issue #1 of "This Week's Pulse"** in Brevo (10 headlines across categories, one featured category, one labelled store card). Send to whatever tiny list exists + your own email as a live test. Outcome: a sent campaign you can screenshot.

## Day 5 — social infrastructure

- [ ] **Telegram channel** "NewsPulse Daily" → public link (t.me/...) → post today's top 5 with the site link. Add the channel link to the site footer (via site build) and to all social bios.
- [ ] **WhatsApp Channel**: create, share once to your personal network with a one-line pitch ("I built a free auto-updating news page — check it").
- [ ] **X/Twitter**: pin a launch tweet describing the 10 categories + auto-update-every-2-hours hook. Post one "today's top 3" thread.
- [ ] **Optional (30 min)**: Pinterest business account; one board per big category (movies, music, tech, gaming) with 1200px covers. Slow-burn channel; skip if time-constrained.

## Day 6 — compliance + measurement

- [ ] **Privacy Policy + About + Contact pages** on NewsPulse (via site build): needed by ad networks, Brevo, Google News transparency, and any future AdSense attempt.[34][43] The AI-prompt store has a `privacy.html` you can adapt, but NewsPulse needs its own (different data flows).
- [ ] **Affiliate disclosure line** above the footer Recommended cards: "Some links on this page may earn us a commission." (ASCI requirement[37] + Amazon/network rules.)
- [ ] **Create the tracking sheet** `monetization/payout-log.md` (columns: date, channel, event, amount, status) + add daily-visit recording: GSC/Bing performance reports weekly, not obsessively daily.

## Day 7 — week-1 review + plan week 2

- [ ] **Numbers review (30 min, write it down in payout-log.md):** GSC impressions/clicks, Bing similar, ad impressions (Adsterra), email subs, store card clicks (if the build logs them), Telegram/X post engagement.
- [ ] **Fix the biggest leak** the numbers reveal (usually: GSC "Discovered – not indexed" → request indexing for key pages; or a dead signup form).
- [ ] **Apply to Monetag** as a second ad network (or PropellerAds third — mind the $100 first-payout gotcha[4]) once Adsterra's real-time stats tell you which formats fill. Two networks = A/B demand.
- [ ] **Decide the Amazon.in application timing** (playbook §3.4): only when monthly visitors plausibly clear a few hundred — the 180-day/3-sale clock[33] must start when you can win it.

## Day-1 emergency fallback

If the site is still 404 after the Day-1 morning check: work the Gumroad publishing + store-link fix FIRST (it's independent of NewsPulse and is the highest-value 90 minutes available), then return to the deploy with the README troubleshooting table.

## Sources

[4] https://www.adspyglass.com/blog/propellerads-ad-network-review — AdSpyGlass PropellerAds Review
[9] https://www.cuelinks.com/blog/best-affiliate-marketing-platform-india — Cuelinks Best Affiliate Platforms India
[10] https://www.shoutmeloud.com/cuelinks-review.html — ShoutMeLoud Cuelinks Review
[11] https://earnkaro.com — EarnKaro homepage
[25] https://support.google.com/adsense/answer/12171612?hl=en — AdSense ads.txt guide official
[28] https://adsterra.com/blog/set-up-publishers-dashboard — Adsterra publisher requirements
[33] https://affiliate-program.amazon.com/help/node/topic/G7MJTPEP9NC3YKMG — Amazon Associates dormancy 180 days
[34] https://support.google.com/news/publisher-center/answer/15898024?hl=en-GB — Google News auto publication pages
[37] https://www.asvlawoffices.com/news-insights/influencer-advertising-and-legal-compliance-in-india-obligations-under-asci-and-consumer-protection-law — ASCI influencer compliance India
[39] https://www.promodo.com/blog/how-to-add-website-to-bing-webmaster-tools — Bing Webmaster Tools import
[43] https://adsenseaudit.net/guides/low-value-content-adsense — AdSense low value content guide
