# ads-analysis

Sai Shishir Tours — Paid Ads Radar (Meta + Google competitor ads).


Weekly competitor paid-ads tracker for Sai Shishir Tours. Same pipeline as the
Instagram Outlier Lab: **Apify → Python → static `index.html` → GitHub Actions → Vercel**.

## What it shows
- **Metric coverage panel**: every metric the Apify actor advertises, marked Available, Via proxy or Not disclosed for India
- **Advertiser transparency**: business behind the page, category, admin count and countries, page created, name changes, About text
- **Ad mix**: per advertiser, split by placement (FB/IG/Messenger/WhatsApp/Threads/AN), lead capture (form/WhatsApp/website/app/call), language, format and trip length
- **Offers and prices**: ₹ prices and nights/days quoted in ad copy
- **Ad details popup**: every field for an ad: IDs, timestamps, placements, button, links, all carousel cards, video, impression rank, AI-media label, spend/reach/impressions (marked not disclosed)
- **CSV export** of whatever the feed is filtered to
- **KPIs**: live competitor ads, new in the last 7 days, longest-running competitor ad, our own live ads
- **Scorecard**: Meta live, Google live, new ads, longest run, format mix, top destinations for each advertiser (our row is highlighted)
- **Destination heat-map**: which pilgrimage and holiday destinations each competitor is pushing on Meta
- **Ad feed**: every live creative, filterable by source, advertiser, format, destination and "new only", plus search; each ad links to the Meta Ad Library or Google Transparency Center

## Meta runs per refresh
1. **Ads**: up to 40 per page, sorted by impressions (Meta's own order is used as a "most seen" rank), with page About info
2. **Totals**: `onlyTotal`, giving the real number of live ads per page
3. **Profiles**: 1 ad per page with `isDetailsPerAd`, giving Instagram handle/followers and verification

## Apify actors
| Source | Actor | Cost (approx.) |
|---|---|---|
| Meta (FB/IG/WhatsApp/Threads) | `apify/facebook-ads-scraper` (official), by page ID, with page About info | $0.005 per ad |
| Google (Search/YouTube/Display) | `scrapesage/google-ads-transparency-scraper` | $0.002 per ad |

13 advertisers at 40 ads per page is about 300 Meta ads + 400 Google ads per run, roughly $2.30 per weekly run and about $10 a month. Lower `limits` in `ads_config.json` to spend less.

## Files
| File | Purpose |
|---|---|
| `ads_config.json` | Competitor list: name, website domain (Google), Facebook page URL + page ID + search name (Meta) |
| `ads_refresh.py` | Runs both actors, normalises, tags destinations, tracks first-seen dates, downloads Meta thumbnails, builds |
| `ads_build.py` | Renders `index.html` from `data/ads/ads.json` |
| `data/ads/ads.json` | Latest snapshot (committed so Vercel serves it) |
| `data/ads/history.json` | First date each ad was seen, used for "new this week" |
| `thumbs/ads/` | Local copies of Meta ad images (Facebook links expire in a few days) |
| `.github/workflows/refresh.yml` | Weekly cron, Mondays 7:00 AM IST (paid-ads pipeline) |

## Adding a competitor
Add an entry to `ads_config.json`:
- `domain`: their website, for Google ads. Take it from the landing-page URL of any ad they run.
- `fbPageIds`: numeric Facebook page ID(s), for Meta ads. The page ID is shown on any of their ads in the Meta Ad Library. A brand can have more than one page (Thrillophilia has two).
- `tier`: `local` or `national`. Drives the "Compare against" switch.
Leave the Facebook fields blank if they don't advertise on Meta.

## Run it
```bash
APIFY_TOKEN=xxxx python3 ads_refresh.py       # live pull + rebuild
python3 ads_build.py                           # rebuild page from saved data only
python3 -m http.server 8000                    # preview at http://localhost:8000
```

## Deploy (one time)
```bash
git init && git add . && git commit -m "Paid Ads Radar"
gh repo create sst-paid-ads --private --source=. --push
gh secret set APIFY_TOKEN                      # paste the Apify token
vercel --prod                                  # link to Vercel; auto-deploys on every push afterwards
```

## Known limits
- Google Transparency gives text ads only as a picture of the ad, so headlines aren't searchable text and Google ads aren't tagged with destinations. Next step is to switch on "full creative details" (+$0.003/ad) or read the text from the images.
- Meta doesn't publish spend, reach or impressions for Indian commercial ads, only for EU and political ads. This was tested with the official actor's extra-details option: `spend`, `reachEstimate` and `impressionsIndex` all came back empty.
- The original Instagram reel files (`build.py`, `refresh.py`, `serve.py` …) are left untouched but are not used by this dashboard.
