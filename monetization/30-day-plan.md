# NewsPulse — 30-Day Action Plan (Days 8–30, compounding phase)

Continues from `7-day-plan.md`. Assumes: site live, GSC+Bing verified, Adsterra (or fallback) running, Brevo list started, Gumroad products published. All free channels.

## Week 2 (Days 8–14) — distribution habits + India affiliates

**Daily habits forming (≤30 min/day total):**
- 1 Telegram channel post (top 3–5 headlines + link)
- 1 X post or thread (rotate category focus: India, tech, entertainment, sports)
- Check GSC once (not more): which queries are showing impressions?

**Tasks:**
- [ ] **Cuelinks approval follow-up** (applied Day 4). If approved: place their JS snippet or use "Link me" per-product links on any shopping-intent content. If rejected: reapply after site has About/Privacy pages live (that's the usual gap).
- [ ] **First "Week in 10 Headlines" original post** on NewsPulse (via site build / data the pipeline already produces — no copying, just curation + one line of editorial per headline). Cross-post the same content as newsletter #2. Write once, use twice.
- [ ] **Reddit soft-launch (1 subreddit only)**: find the one sub where "I built a free auto-updating news aggregator, 10 categories, zero ads-spam" is genuinely welcome (r/IndiaTech, r/developersIndia, or a niche hobby sub matching a category). Share as a project, not a link dump. Obey the sub's self-promo rules strictly.
- [ ] **Verify Monetag is live** (if applied Day 7): compare its fill/earnings against Adsterra on the same placements; keep the better one in the primary slot.
- [ ] **GSC performance pass #1**: list the 10 queries with impressions but position > 10. These are the categories/searches where category-page titles/descriptions deserve a tweak (via site-config or build templates — coordinate, don't hack `docs/`).

## Week 3 (Days 15–21) — email flywheel + first money decisions

- [ ] **Newsletter #3** with the first subscriber milestone note; add a "invite a friend" line (forwarding a good digest is organic growth).
- [ ] **Signup-form placement review**: if conversion is under 1% of visitors, move the form higher (hero-adjacent or after the first category block) and offer the free-teaser pack explicitly as the incentive.
- [ ] **Amazon Associates (amazon.in) decision gate:** if GSC shows ≥ 500 monthly visitors trending up, apply now (3-sales-in-180-days clock[33]); if not, defer to Day 30.
- [ ] **EarnKaro link test**: convert one genuine shopping-intent moment (e.g., a "best gadgets this month" original roundup post, if any exists) through an EarnKaro link and confirm tracking shows the click.
- [ ] **Content-moat item #2**: publish a per-category "trending this week" auto-roundup (pure data from the pipeline; no external content copied). These pages are Discover-fodder[36] and future-AdSense-fodder[43].

## Week 4 (Days 22–30) — measurement, first payout push, month-2 plan

- [ ] **Payout push:** check Adsterra/Monetag balance vs the $5 floor (at $1 RPM ≈ 5,000 impressions needed). If close, nudge impressions by sharing the two best-performing category pages socially (don't buy traffic — invalid-traffic forfeits[28]).
- [ ] **Store funnel check:** count clicks from footer Recommended cards (URL ref tags or build logs) vs Gumroad sales. If clicks exist but zero sales: the store's product pages need work (price framing, testimonials up top) — that's the AI-prompt-store repo's domain, note it there.
- [ ] **GSC coverage audit**: "Pages" report → find "Crawled – not indexed" or "Discovered – not indexed" clusters; usually thin category pages; fix via better interlinking in the build templates.
- [ ] **Social audit:** kill the channel with the worst engagement-per-30-minutes; double down on the best (typically Telegram for Indian audiences).
- [ ] **Month-1 numbers into payout-log.md** (visitors, impressions, RPM realized, subs, sales, affiliate income). Compare against playbook §6.5's honest targets ($6–20) and adjust month-2 targets from REAL RPM, not estimates.

## 30-day targets (honest, source-grounded)

| Metric | Target | Basis |
|---|---|---|
| Monthly visitors | 1,000–3,000 | Social + early search; aggregator SEO compounds slowly |
| Ad impressions | 2,000–6,000 (≈1–3 RPM-bearing pages/visit) | 2 slots/page cap |
| First ad payout | $5 hit or ~close (Adsterra/Monetag floor[1][2]) | $1–3 RPM range[1][3][7] |
| Email subscribers | 100–300 | 2% of visitors + direct pushes |
| Gumroad sales | 1–3 (net $7.90 each[22][23]) | Cross-sell CTR + bundle ladder |
| Amazon.in | Applied (only if traffic gate passed) | 180-day clock[33] |
| Original content | 2–4 curation posts | §4.6 moat; future AdSense/Discover groundwork[36][43] |

## Month-2 preview (what this playbook sets up)

1. Custom domain decision: if month-1 traffic ≥ ~2,000 visitors and growth is visible, a ~₹800–1,200/yr .com/.in is the single purchase that unlocks the AdSense path (§3.5) and improves GSC click-through. Until revenue exists to justify it, stay on github.io.
2. Newsletter cadence 2×/week once > 250 subs (Brevo cap 300/day is comfortable to ~1,200 subs[17]).
3. Second ad network A/B resolves into a permanent primary.
4. If Gumroad sales ≥ 5/month: set up Gumroad's affiliate program at 30% (the standard digital-product rate[38]) so others sell the prompt packs for you — flips NewsPulse's cross-sell from cost-free to leveraged.

## Standing weekly cadence (from Day 30 on)

- Mon: GSC + Bing + ad-network stats → payout-log.md (15 min)
- Tue: one original curation post (10-headline digest or trending roundup)
- Wed: newsletter send
- Thu: social audit — repost whichever category won the week
- Fri: one growth experiment (new sub, new pin board, new query-target tweak)

## Sources

[1] https://www.adpushup.com/blog/adsterra-review-factsheet-overview-payment-pros-and-cons — AdPushup Adsterra Review
[2] https://monetag.com/blog/monetag-payouts-update — Monetag Payouts Update
[3] https://groups.io/g/freelancer/topic/how_does_monetag_compare_to/115273568 — Monetag comparison groups.io
[7] https://monetag.com/blog/adsense-alternatives — Monetag AdSense Alternatives
[17] https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans — Brevo pricing plans official
[22] https://gumroad.com/pricing — Gumroad pricing
[23] https://checkthat.ai/brands/gumroad/pricing — checkthat Gumroad fees 2026
[28] https://adsterra.com/blog/set-up-publishers-dashboard — Adsterra publisher requirements
[33] https://affiliate-program.amazon.com/help/node/topic/G7MJTPEP9NC3YKMG — Amazon Associates dormancy 180 days
[36] https://docs.arcxp.com/en/products/general/faq--google-discover.html — Google Discover FAQ
[38] https://gumroad.com/help/article/333-affiliates-on-gumroad — Gumroad affiliates help
[43] https://adsenseaudit.net/guides/low-value-content-adsense — AdSense low value content guide
