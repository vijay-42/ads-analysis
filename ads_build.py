#!/usr/bin/env python3
"""
Paid-Ads Radar — dashboard renderer.

Reads data/ads/ads.json (written by ads_refresh.py) and writes a single,
self-contained index.html: KPI row, competitor scorecard, destination
heat-map and a filterable ad feed (Meta + Google).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "ads" / "ads.json"
OUT = ROOT / "index.html"

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paid Ads Radar</title>
<meta name="robots" content="noindex">
<style>
:root{
  --bg:#f6f5f2;--bg-2:#ffffff;--bg-3:#efede8;--fg:#1b1a17;--fg-dim:#5e5b54;--fg-faint:#8d897f;
  --border:rgba(0,0,0,.09);--accent:#e8651f;--accent-2:#d9345a;--self:#1f7a5a;--self-bg:rgba(31,122,90,.08);
  --meta:#2f5fd0;--google:#1a8a4a;--new:#d9345a;
  --h0:#f4ece6;--h1:#f6c9a8;--h2:#ef9a5d;--h3:#e2702c;--h4:#b24d12;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0b0b0e;--bg-2:#15151b;--bg-3:#1f1f27;--fg:#f3f3f5;--fg-dim:rgba(243,243,245,.62);--fg-faint:rgba(243,243,245,.38);
  --border:rgba(255,255,255,.09);--accent:#ff8a3d;--accent-2:#ff4f7b;--self:#4fd1a1;--self-bg:rgba(79,209,161,.09);
  --meta:#7fa2ff;--google:#5fd08e;--new:#ff4f7b;
  --h0:#1d1a19;--h1:#4a2c1a;--h2:#80431c;--h3:#c0621f;--h4:#ff8a3d;
}}
:root[data-theme="dark"]{
  --bg:#0b0b0e;--bg-2:#15151b;--bg-3:#1f1f27;--fg:#f3f3f5;--fg-dim:rgba(243,243,245,.62);--fg-faint:rgba(243,243,245,.38);
  --border:rgba(255,255,255,.09);--accent:#ff8a3d;--accent-2:#ff4f7b;--self:#4fd1a1;--self-bg:rgba(79,209,161,.09);
  --meta:#7fa2ff;--google:#5fd08e;--new:#ff4f7b;
  --h0:#1d1a19;--h1:#4a2c1a;--h2:#80431c;--h3:#c0621f;--h4:#ff8a3d;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:1280px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:22px}
.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--fg-faint)}
h1{margin:4px 0 0;font-size:28px;letter-spacing:-.02em;font-weight:650}
h1 span{background:linear-gradient(90deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.meta-line{color:var(--fg-dim);font-size:13px}
h2{font-size:15px;margin:34px 0 4px;font-weight:650}
.sub{color:var(--fg-faint);font-size:12.5px;margin:0 0 12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{background:var(--bg-2);border:1px solid var(--border);border-radius:14px;padding:16px 18px}
.kpi .l{font-size:12px;color:var(--fg-dim)}
.kpi .v{font-size:30px;font-weight:650;letter-spacing:-.02em;margin-top:2px;font-variant-numeric:tabular-nums}
.kpi .d{font-size:12px;color:var(--fg-faint);margin-top:2px}
.card{background:var(--bg-2);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap;font-size:13px}
th{font-size:11.5px;font-weight:600;color:var(--fg-faint);text-transform:uppercase;letter-spacing:.05em;background:var(--bg-3);cursor:pointer;user-select:none}
th.num,td.num{text-align:right}
tr:last-child td{border-bottom:0}
tr.self td{background:var(--self-bg)}
tr.self td:first-child{box-shadow:inset 3px 0 0 var(--self)}
.you{font-size:10.5px;font-weight:700;color:var(--self);border:1px solid var(--self);border-radius:5px;padding:0 5px;margin-left:6px}
.muted{color:var(--fg-faint)}
.dests{white-space:normal;min-width:220px;color:var(--fg-dim);font-size:12.5px}
.mix{display:inline-flex;height:8px;width:90px;border-radius:4px;overflow:hidden;gap:2px;vertical-align:middle;background:var(--bg-2)}
.mix i{display:block;height:100%}
.hm td{text-align:center;min-width:64px;padding:8px 6px}
.hm td:first-child{text-align:left}
.hm .cell{display:block;border-radius:6px;padding:6px 0;font-weight:600;font-size:12.5px}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px}
.seg{display:inline-flex;flex-wrap:wrap;max-width:100%;background:var(--bg-3);border-radius:10px;padding:3px}
.seg button{border:0;background:none;color:var(--fg-dim);padding:6px 12px;border-radius:8px;font:inherit;font-size:13px;cursor:pointer}
.seg button.on{background:var(--bg-2);color:var(--fg);box-shadow:0 1px 2px rgba(0,0,0,.12)}
select,input[type=search]{font:inherit;font-size:13px;background:var(--bg-2);color:var(--fg);border:1px solid var(--border);border-radius:10px;padding:7px 10px}
input[type=search]{min-width:200px;flex:1 1 200px;max-width:320px}
label.tg{display:inline-flex;gap:6px;align-items:center;font-size:13px;color:var(--fg-dim);cursor:pointer}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.chip{border:1px solid var(--border);background:var(--bg-2);color:var(--fg-dim);border-radius:999px;padding:5px 11px;font:inherit;font-size:12.5px;cursor:pointer}
.chip.on{border-color:var(--accent);color:var(--fg);background:color-mix(in srgb,var(--accent) 12%,var(--bg-2))}
.chip b{font-weight:600;margin-left:4px;color:var(--fg-faint)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.ad{background:var(--bg-2);border:1px solid var(--border);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.ad.selfad{border-color:var(--self)}
.thumb{aspect-ratio:1/1;background:var(--bg-3);display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.thumb img{width:100%;height:100%;object-fit:cover}
.thumb.g img{object-fit:contain;background:#fff}
.thumb .ph{color:var(--fg-faint);font-size:12px;padding:20px;text-align:center}
.badges{position:absolute;top:8px;left:8px;right:8px;display:flex;gap:5px;flex-wrap:wrap}
.b{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:6px;background:rgba(0,0,0,.66);color:#fff;letter-spacing:.02em}
.b.new{background:var(--new)}
.body{padding:12px 14px 14px;display:flex;flex-direction:column;gap:6px;flex:1}
.who{font-weight:600;font-size:13px;display:flex;justify-content:space-between;gap:8px}
.src{font-size:11px;font-weight:700}
.src.meta{color:var(--meta)}.src.google{color:var(--google)}
.txt{color:var(--fg-dim);font-size:12.5px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;white-space:pre-line}
.txt.open{-webkit-line-clamp:unset}
.row{display:flex;flex-wrap:wrap;gap:6px;font-size:11.5px;color:var(--fg-faint)}
.pill{border:1px solid var(--border);border-radius:6px;padding:1px 6px}
.foot{margin-top:auto;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px 8px;font-size:12px;padding-top:6px}
.foot a,.foot .cta{white-space:nowrap}
.foot a{color:var(--accent);text-decoration:none;font-weight:600}
.cta{background:var(--bg-3);border-radius:6px;padding:2px 8px;color:var(--fg);font-weight:600}
.more{border:0;background:none;color:var(--fg-faint);font:inherit;font-size:12px;cursor:pointer;padding:0;text-align:left}
.empty{padding:40px;text-align:center;color:var(--fg-faint)}
.loadmore{display:block;margin:18px auto 0;font:inherit;background:var(--bg-2);color:var(--fg);border:1px solid var(--border);border-radius:10px;padding:9px 18px;cursor:pointer}
.note{font-size:12px;color:var(--fg-faint);margin-top:28px;border-top:1px solid var(--border);padding-top:14px}
details.cov{background:var(--bg-2);border:1px solid var(--border);border-radius:14px;padding:12px 16px;margin-top:14px}
details.cov summary{cursor:pointer;font-weight:600;font-size:13.5px}
.covgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:8px 18px;margin-top:12px}
.covit{font-size:12.5px;color:var(--fg-dim);display:flex;gap:8px;align-items:flex-start}
.st{font-size:10.5px;font-weight:700;border-radius:5px;padding:1px 6px;white-space:nowrap;flex:none}
.st.ok{background:color-mix(in srgb,var(--google) 16%,transparent);color:var(--google)}
.st.no{background:color-mix(in srgb,var(--fg-faint) 18%,transparent);color:var(--fg-dim)}
.st.proxy{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent)}
.vf{color:var(--meta);font-size:11px;margin-left:4px}
td.wrap{white-space:normal;min-width:180px;font-size:12.5px;color:var(--fg-dim)}
.mixcell{display:block;border-radius:6px;padding:5px 0;font-weight:600;font-size:12px;text-align:center}
dialog{border:1px solid var(--border);border-radius:16px;background:var(--bg-2);color:var(--fg);padding:0;width:min(860px,94vw);max-height:90vh}
dialog::backdrop{background:rgba(0,0,0,.55)}
.dlg-h{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg-2)}
.dlg-b{padding:16px 18px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:18px}
.dlg-b img,.dlg-b video{width:100%;border-radius:10px;background:var(--bg-3)}
.kv{display:grid;grid-template-columns:130px 1fr;gap:6px 10px;font-size:12.5px}
.kv dt{color:var(--fg-faint)}.kv dd{margin:0;word-break:break-word}
.cardrow{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;margin-top:10px}
.cardrow figure{margin:0;flex:0 0 130px;font-size:11.5px;color:var(--fg-dim)}
.cardrow img{width:130px;height:130px;object-fit:cover;border-radius:8px}
.btn{font:inherit;font-size:12.5px;background:var(--bg-2);color:var(--fg);border:1px solid var(--border);border-radius:10px;padding:7px 12px;cursor:pointer}
.linkbtn{border:0;background:none;color:var(--accent);font:inherit;font-weight:600;cursor:pointer;padding:0}
@media (max-width:700px){.dlg-b{grid-template-columns:1fr}}
.theme{font:inherit;font-size:12px;background:var(--bg-2);color:var(--fg-dim);border:1px solid var(--border);border-radius:8px;padding:5px 10px;cursor:pointer}
@media (max-width:600px){.wrap{padding:20px 16px 48px}h1{font-size:23px}.kpi .v{font-size:25px}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <div class="eyebrow">Sai Shishir Tours · Competitor intelligence</div>
      <h1>Paid Ads <span>Radar</span></h1>
      <div class="meta-line" id="updated"></div>
    </div>
    <button class="theme" id="theme">Toggle theme</button>
  </header>

  <div class="filters" style="margin-bottom:16px">
    <span class="muted" style="font-size:12.5px">Compare against</span>
    <div class="seg" id="tierSeg"><button data-v="all" class="on">All competitors</button><button data-v="local">Local pilgrimage players</button><button data-v="national">National brands</button></div>
  </div>
  <section class="kpis" id="kpis"></section>
  <details class="cov"><summary>Metric coverage: what the Meta Ad Library gives us for Indian ads</summary><div class="covgrid" id="cov"></div></details>

  <h2>Competitor scorecard</h2>
  <p class="sub">Live ads right now. The Meta figure is Meta's own total; details are analysed for up to 40 ads per page. Google counts ads shown in the last 3 days (“40+” means the pull limit was reached). Longest-running ads are usually the ones that make money. Click a column to sort.</p>
  <div class="card scroll"><table id="score"></table></div>

  <h2>Advertiser transparency</h2>
  <p class="sub">Who is behind each page, from Meta's "About" and page-transparency data. Hover a row to see the page's name-change history.</p>
  <div class="card scroll"><table id="trans"></table></div>

  <h2>Ad mix: where, how and in what language they advertise</h2>
  <p class="sub">Share of each advertiser's live Meta ads. Placements are the Meta apps an ad runs on. Lead capture is what the ad's button does. Language is read from the script, so Kannada written in English letters counts as English.</p>
  <div class="filters"><div class="seg" id="mixSeg">
    <button data-v="placements" class="on">Placements</button><button data-v="lead">Lead capture</button><button data-v="lang">Language</button><button data-v="format">Creative format</button><button data-v="duration">Trip length</button>
  </div></div>
  <div class="card scroll"><table class="hm" id="mix"></table></div>

  <h2>Offers and prices seen in ads</h2>
  <p class="sub">₹ prices and trip lengths quoted in live Meta ad copy, cheapest first. Only ads that state a price are shown. Automatic hotel catalogue ads are left out.</p>
  <div class="card scroll"><table id="offers"></table></div>

  <h2>Which destinations competitors are pushing</h2>
  <p class="sub">Live Meta ads per destination, read from the ad text and landing link. Google only shares its ads as images, so they aren't counted here.</p>
  <div class="card scroll"><table class="hm" id="heat"></table></div>

  <h2>Ad feed</h2>
  <p class="sub">Every live creative. Click “View” to open it in the Meta Ad Library or Google Ads Transparency Center.</p>
  <div class="filters">
    <div class="seg" id="srcSeg">
      <button data-v="all" class="on">All</button><button data-v="meta">Meta</button><button data-v="google">Google</button>
    </div>
    <select id="fmt"><option value="">All formats</option></select>
    <select id="dest"><option value="">All destinations</option></select>
    <select id="sort">
      <option value="newest">Newest first</option>
      <option value="longest">Longest running</option>
      <option value="rank">Most seen (Meta impression rank)</option>
    </select>
    <label class="tg"><input type="checkbox" id="newOnly"> New in last 7 days</label>
    <select id="lead"><option value="">All lead types</option></select>
    <input type="search" id="q" placeholder="Search ad text…">
    <button class="btn" id="csv">Export CSV</button>
  </div>
  <div class="chips" id="chips"></div>
  <div class="grid" id="feed"></div>
  <button class="loadmore" id="more" hidden>Show more</button>

  <p class="note">Data: Meta Ad Library and Google Ads Transparency Center, pulled through Apify. Meta publishes reach and spend only for EU-delivered and political ads, so Indian travel ads show neither. See "Metric coverage" at the top. <span id="regionNote"></span></p>
</div>

<dialog id="dlg"><div class="dlg-h"><strong id="dlgT"></strong><button class="btn" onclick="this.closest('dialog').close()">Close</button></div><div class="dlg-b" id="dlgB"></div></dialog>
<script>
const DATA = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ALL_COMPS = DATA.competitors, byId = Object.fromEntries(ALL_COMPS.map(c => [c.id, c]));
const PAGES = DATA.pages || {};
let TIER = "all";
try { TIER = new URLSearchParams(location.search).get("tier") || "all"; } catch(e){}
const inTier = c => TIER === "all" || c.tier === TIER || c.id === DATA.self;
const comps = ALL_COMPS.filter(inTier);
const ads = DATA.ads.filter(a => a.active && inTier(byId[a.comp]));
document.querySelectorAll("#tierSeg button").forEach(b => { b.classList.toggle("on", b.dataset.v === TIER);
  b.onclick = () => { const u = new URL(location.href); u.searchParams.set("tier", b.dataset.v); location.href = u.toString(); }; });
const SELF = DATA.self;
const LIM = DATA.limits || {};
// counts that hit the per-page / per-domain pull limit are shown as "40+"
const capped = (n, src, c) => { const cap = src === "g" ? LIM.googleMaxAdsPerDomain : (LIM.metaMaxAdsPerPage||0) * ((c&&c.fbPageIds||[]).length||1);
  return cap && n >= cap ? `<span title="Pull limit reached, so they run at least this many">${n}+</span>` : n; };
const fmtK = n => n >= 1e6 ? (n/1e6).toFixed(1)+"M" : n >= 1e3 ? Math.round(n/1e3)+"K" : String(n);
const fmtDate = d => d ? new Date(d + (d.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-IN", {day:"numeric", month:"short", year:"numeric"}) : "";

// theme toggle (per-viewer, safe if storage blocked)
(() => { let t = null; try { t = localStorage.getItem("adsTheme"); } catch(e){}
  if (t) document.documentElement.dataset.theme = t;
  $("#theme").onclick = () => { const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const nx = cur === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = nx;
    try { localStorage.setItem("adsTheme", nx); } catch(e){} };
})();

$("#updated").textContent = `Updated ${new Date(DATA.generated).toLocaleString("en-IN", {dateStyle:"medium", timeStyle:"short"})} · Region ${DATA.region} · ${ALL_COMPS.length - 1} competitors tracked`;

// ── KPIs ──
const compAds = ads.filter(a => a.comp !== SELF);
const metaN = compAds.filter(a => a.src === "meta").length, googleN = compAds.length - metaN;
const plural = (n, w) => `${n.toLocaleString("en-IN")} ${w}${n === 1 ? "" : "s"}`;
const newN = ads.filter(a => a.isNew && a.comp !== SELF).length;
const longest = ads.filter(a => a.comp !== SELF && a.days).sort((a,b) => b.days - a.days)[0];
const selfN = ads.filter(a => a.comp === SELF).length;
// real live-ad totals from Meta (not capped by the weekly pull limit)
const metaTotalOf = c => (PAGES[c.id]||{}).metaTotal ?? ads.filter(a=>a.comp===c.id&&a.src==="meta").length;
const compMetaTotal = comps.filter(c=>c.id!==SELF).reduce((s,c)=>s+metaTotalOf(c),0);
const kpi = (l, v, d) => `<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div><div class="d">${d}</div></div>`;
$("#kpis").innerHTML =
  kpi("Live competitor Meta ads", compMetaTotal.toLocaleString("en-IN"), `real total from Meta · ${metaN} analysed in detail · ${googleN} Google ads sampled`) +
  kpi("New in last 7 days", newN, "competitor ads that started recently") +
  kpi("Longest-running competitor ad", longest ? plural(longest.days, "day") : "—", longest ? esc(byId[longest.comp].name) + " · " + (longest.src === "google" ? "Google" : "Meta") + " · since " + fmtDate(longest.start) : "") +
  kpi("Our live ads", selfN, `${ads.filter(a=>a.comp===SELF&&a.src==="meta").length} Meta · ${ads.filter(a=>a.comp===SELF&&a.src==="google").length} Google`);

// ── Metric coverage (every metric the Apify actor advertises) ──
const anyV = f => DATA.ads.some(a => a.src==="meta" && f(a));
const COV = [
  ["Ads (creatives, copy, CTA, links)", "ok", "Every live ad: text, headline, button, landing link"],
  ["Publishers / placements", "ok", "Facebook, Instagram, Messenger, WhatsApp, Threads, Audience Network"],
  ["Images, videos, carousels", "ok", "Open an ad's Details to see all cards and play videos"],
  ["IDs", "ok", "Library ID, collation ID, page ID for each ad"],
  ["Timestamps", "ok", "Start and last-seen time, days running"],
  ["Total live ads per page", "ok", "Real count from Meta, not limited by our pull"],
  ["Advertiser transparency", "ok", "Business name and country, admin countries, page created, name changes"],
  ["Instagram and page stats", "ok", "Page likes, Instagram followers, verification"],
  ["Language of the ad", "ok", "Worked out from the script used in the ad copy"],
  ["Prices in ads", "proxy", "₹ amounts read from the ad copy. Meta's product-price add-on returns nothing for travel pages."],
  ["Impressions", anyV(a=>a.impressions) ? "ok" : "proxy", anyV(a=>a.impressions) ? "Reported by Meta" : "Not disclosed for India. We use Meta's own 'sort by impressions' order as a rank (#1 = most seen)."],
  ["Reach estimates", anyV(a=>a.reach) ? "ok" : "no", "Meta publishes reach only for ads shown in the EU"],
  ["Spend", anyV(a=>a.spend) ? "ok" : "no", "Meta publishes spend only for political/social-issue ads"],
  ["Product info (e-commerce add-on)", "no", "Tested: travel package pages aren't product pages, so nothing comes back"],
];
const ST = {ok:["Available","ok"], no:["Not disclosed for India","no"], proxy:["Via proxy","proxy"]};
$("#cov").innerHTML = COV.map(([m,s,d]) => `<div class="covit"><span class="st ${ST[s][1]}">${ST[s][0]}</span><span><strong style="color:var(--fg)">${m}</strong><br>${d}</span></div>`).join("");

// ── Scorecard ──
const FMT_COL = {TEXT:"var(--fg-faint)", IMAGE:"var(--accent)", VIDEO:"var(--accent-2)", DCO:"var(--meta)", CAROUSEL:"var(--google)"};
const rows = comps.map(c => {
  const mine = ads.filter(a => a.comp === c.id);
  const fm = {}; mine.forEach(a => fm[a.format] = (fm[a.format]||0) + 1);
  const dc = {}; mine.forEach(a => a.dest.forEach(d => dc[d] = (dc[d]||0) + 1));
  const top = Object.entries(dc).sort((a,b) => b[1]-a[1]).slice(0,3).map(([d,n]) => `${d} (${n})`).join(", ");
  const lr = mine.filter(a => a.days).sort((a,b) => b.days - a.days)[0];
  return {c, meta: mine.filter(a=>a.src==="meta").length, google: mine.filter(a=>a.src==="google").length,
          total: mine.length, nw: mine.filter(a=>a.isNew).length, longest: lr ? lr.days : 0, fm, top,
          noFb: !(c.fbPageIds||[]).length, likes: (PAGES[c.id]||{}).likes || 0, page: PAGES[c.id] || {},
          metaTotal: metaTotalOf(c), ig: (PAGES[c.id]||{}).igFollowers || 0};
});
let sortKey = "metaTotal", sortDir = -1;
function drawScore(){
  const r = [...rows].sort((a,b) => sortKey === "name" ? a.c.name.localeCompare(b.c.name) * -sortDir : (a[sortKey]-b[sortKey]) * sortDir);
  const H = [["name","Advertiser",""],["likes","FB page likes","num"],["ig","Instagram followers","num"],["metaTotal","Meta live (real total)","num"],["google","Google live","num"],["nw","New 7d","num"],["longest","Longest run","num"],[null,"Format mix",""],[null,"Top destinations",""]];
  $("#score").innerHTML = `<thead><tr>${H.map(([k,l,c]) => `<th class="${c}" ${k?`data-k="${k}"`:""}>${l}${k===sortKey?(sortDir<0?" ↓":" ↑"):""}</th>`).join("")}</tr></thead><tbody>` +
    r.map(x => {
      const tot = Object.values(x.fm).reduce((s,n)=>s+n,0) || 1;
      const mix = Object.entries(x.fm).map(([f,n]) => `<i title="${f}: ${n}" style="width:${n/tot*100}%;background:${FMT_COL[f]||"var(--fg-faint)"}"></i>`).join("");
      const fmTitle = Object.entries(x.fm).map(([f,n]) => `${f.toLowerCase()} ${n}`).join(" · ");
      return `<tr class="${x.c.id===SELF?"self":""}"><td><strong>${esc(x.c.name)}</strong>${x.page.fbVerified?'<span class="vf" title="Meta blue-verified page">✔ verified</span>':""}${x.c.id===SELF?'<span class="you">YOU</span>':""}<div class="muted" style="font-size:11.5px">${esc(x.c.domain||"")}${x.c.tier==="national"?' · national':''}</div></td>
        <td class="num" title="${esc(x.page.about||"")}${x.page.created?"\nFB page created "+x.page.created:""}${x.page.admins?"\nAdmins: "+esc(x.page.admins):""}">${x.likes ? fmtK(x.likes) : '<span class="muted">—</span>'}${x.page.created?`<div class="muted" style="font-size:11px">since ${x.page.created.slice(0,4)}</div>`:""}</td>
        <td class="num">${x.ig ? fmtK(x.ig) : '<span class="muted">—</span>'}${x.page.igUsername?`<div class="muted" style="font-size:11px">@${esc(x.page.igUsername)}</div>`:""}</td>
        <td class="num">${x.noFb ? '<span class="muted" title="No Facebook page configured">n/a</span>' : `<strong>${x.metaTotal.toLocaleString("en-IN")}</strong>`}${!x.noFb && x.metaTotal > x.meta ? `<div class="muted" style="font-size:11px">${x.meta} analysed</div>`:""}</td>
        <td class="num">${capped(x.google,"g")}</td>
        <td class="num">${x.nw || '<span class="muted">0</span>'}</td>
        <td class="num">${x.longest ? x.longest.toLocaleString("en-IN")+" d" : "—"}</td>
        <td title="${fmTitle}"><span class="mix">${mix}</span> <span class="muted" style="font-size:11.5px">${fmTitle}</span></td>
        <td class="dests">${x.top || '<span class="muted">—</span>'}</td></tr>`;
    }).join("") + "</tbody>";
  document.querySelectorAll("#score th[data-k]").forEach(th => th.onclick = () => {
    const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : -1; sortKey = k; drawScore(); });
}
drawScore();

// ── Advertiser transparency ──
$("#trans").innerHTML = `<thead><tr><th>Advertiser</th><th>Business behind the page</th><th>Category</th><th class="num">Page admins</th><th>Admin countries</th><th>Page created</th><th class="num">Name changes</th><th>About</th></tr></thead><tbody>` +
  comps.filter(c => (c.fbPageIds||[]).length).map(c => { const p = PAGES[c.id] || {};
    return `<tr class="${c.id===SELF?"self":""}" title="${esc((p.history||[]).join("\n"))}"><td><strong>${esc(c.name)}</strong>${p.fbVerified?'<span class="vf">✔</span>':""}<div class="muted" style="font-size:11px">${(p.pageIds||c.fbPageIds).length} page${(p.pageIds||c.fbPageIds).length>1?"s":""}</div></td>
      <td class="wrap">${p.owner ? esc(p.owner) + (p.ownerLocation?`<div class="muted" style="font-size:11px">${esc(p.ownerLocation)}${p.ownerPhone?" · "+esc(p.ownerPhone):""}</div>`:"") : '<span class="muted">Not disclosed</span>'}</td>
      <td class="wrap">${esc(p.category || p.categories || "—")}</td>
      <td class="num">${p.adminCount ?? "—"}</td><td class="wrap">${esc(p.admins || "—")}</td>
      <td>${p.created || "—"}</td><td class="num">${p.nameChanges ?? "—"}${p.merges?` · ${p.merges} merges`:""}</td>
      <td class="wrap" style="min-width:260px;max-width:340px">${esc((p.about||"").replace(/\s+/g," ").slice(0,120))}${(p.about||"").length>120?"…":""}</td></tr>`; }).join("") + "</tbody>";

// ── Ad mix ──
const MIXK = {
  placements: a => (a.placements||[]).map(p => ({FACEBOOK:"Facebook",INSTAGRAM:"Instagram",MESSENGER:"Messenger",WHATSAPP:"WhatsApp",THREADS:"Threads",AUDIENCE_NETWORK:"Audience Network"}[p] || p)),
  lead: a => [a.lead || "Other"], lang: a => (a.lang || "—").split(" + "), format: a => [a.format], duration: a => a.duration ? [a.duration] : [],
};
// languages that always get a row (key markets), even when no ad uses them yet
const PIN = { lang: ["English", "Kannada", "Hindi/Marathi", "Telugu", "Tamil"] };
function drawMix(kind){
  const mAds = ads.filter(a => a.src === "meta"), mc = comps.filter(c => mAds.some(a => a.comp === c.id));
  const cnt = {}; mAds.forEach(a => MIXK[kind](a).forEach(k => cnt[k] = (cnt[k]||0)+1));
  const pinned = PIN[kind] || [];
  const keys = [...pinned, ...Object.keys(cnt).filter(k => !pinned.includes(k)).sort((a,b) => cnt[b]-cnt[a])].slice(0, 12);
  $("#mix").innerHTML = keys.length ? `<thead><tr><th>${{placements:"Placement",lead:"Lead capture",lang:"Language",format:"Format",duration:"Trip length"}[kind]}</th>${mc.map(c=>`<th>${esc(c.name.split(" (")[0])}</th>`).join("")}</tr></thead><tbody>` +
    keys.map(k => `<tr><td><strong>${esc(k)}</strong></td>${mc.map(c => { const tot = mAds.filter(a=>a.comp===c.id).length || 1;
      const n = mAds.filter(a => a.comp===c.id && MIXK[kind](a).includes(k)).length, pct = Math.round(n/tot*100), s = n ? Math.min(4, 1 + Math.floor(pct/25)) : 0;
      return `<td title="${esc(c.name)} · ${esc(k)}: ${n} of ${tot} ads"><span class="mixcell" style="background:var(--h${s});color:${s>=3?"#fff":"var(--fg"+(n?"":"-faint")+")"}">${n?pct+"%":"·"}</span></td>`; }).join("")}</tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="empty">Nothing found for this breakdown.</td></tr></tbody>`;
}
document.querySelectorAll("#mixSeg button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#mixSeg button").forEach(x => x.classList.toggle("on", x===b)); drawMix(b.dataset.v); });
drawMix("placements");

// ── Offers & prices ──
// catalogue (DPA) ads are auto-generated hotel deals, not tour packages: keep them out
const offerAds = ads.filter(a => a.src==="meta" && a.format !== "DPA" && (a.prices||[]).length).sort((a,b) => a.prices[0]-b.prices[0]);
const inr = n => "₹" + n.toLocaleString("en-IN");
$("#offers").innerHTML = offerAds.length ? `<thead><tr><th>Advertiser</th><th class="num">From price</th><th>Trip length</th><th>Destination</th><th>Offer (headline)</th><th>Lead capture</th><th></th></tr></thead><tbody>` +
  offerAds.slice(0, 60).map(a => `<tr class="${a.comp===SELF?"self":""}"><td><strong>${esc(byId[a.comp].name)}</strong></td><td class="num"><strong>${inr(a.prices[0])}</strong>${a.prices.length>1?`<div class="muted" style="font-size:11px">also ${a.prices.slice(1,3).map(inr).join(", ")}</div>`:""}</td>
    <td>${a.duration || "—"}</td><td class="wrap">${esc(a.dest.join(", ") || "—")}</td><td class="wrap" style="max-width:340px">${esc(a.title || (a.text||"").slice(0,90))}</td><td>${esc(a.lead)}</td>
    <td><button class="linkbtn" data-ad="${a.id}">Details</button></td></tr>`).join("") + "</tbody>"
  : `<tbody><tr><td class="empty">No prices mentioned in live ad copy.</td></tr></tbody>`;

// ── Destination heat-map (Meta text only) ──
const metaAds = ads.filter(a => a.src === "meta");
const destTotals = {}; metaAds.forEach(a => a.dest.forEach(d => destTotals[d] = (destTotals[d]||0)+1));
const dests = Object.keys(destTotals).sort((a,b) => destTotals[b]-destTotals[a]);
const hmComps = comps.filter(c => metaAds.some(a => a.comp === c.id));
let hmMax = 1; const cellN = (c,d) => metaAds.filter(a => a.comp===c && a.dest.includes(d)).length;
hmComps.forEach(c => dests.forEach(d => hmMax = Math.max(hmMax, cellN(c.id,d))));
const step = n => n === 0 ? 0 : Math.min(4, 1 + Math.floor((n/hmMax) * 3.999));
$("#heat").innerHTML = dests.length ? `<thead><tr><th>Destination</th>${hmComps.map(c=>`<th>${esc(c.name.split(" (")[0])}</th>`).join("")}</tr></thead><tbody>` +
  dests.map(d => `<tr><td><strong>${esc(d)}</strong></td>${hmComps.map(c => { const n = cellN(c.id,d), s = step(n);
    return `<td title="${esc(c.name)} · ${esc(d)}: ${n} live ad${n===1?"":"s"}"><span class="cell" style="background:var(--h${s});color:${s>=3?"#fff":"var(--fg"+(n?"":"-faint")+")"}">${n||"·"}</span></td>`; }).join("")}</tr>`).join("") + "</tbody>"
  : `<tbody><tr><td class="empty">No destination keywords found in live Meta ads.</td></tr></tbody>`;

// ── Feed ──
const st = {src:"all", comp:new Set(), fmt:"", dest:"", lead:"", sort:"newest", newOnly:false, q:"", show:36};
[...new Set(ads.filter(a=>a.lead).map(a=>a.lead))].sort().forEach(f => $("#lead").insertAdjacentHTML("beforeend", `<option>${esc(f)}</option>`));
$("#lead").onchange = e => { st.lead = e.target.value; st.show = 36; drawFeed(); };
[...new Set(ads.map(a=>a.format))].sort().forEach(f => $("#fmt").insertAdjacentHTML("beforeend", `<option>${f}</option>`));
dests.forEach(d => $("#dest").insertAdjacentHTML("beforeend", `<option>${esc(d)}</option>`));
function drawChips(){
  $("#chips").innerHTML = comps.map(c => { const n = ads.filter(a=>a.comp===c.id && (st.src==="all"||a.src===st.src)).length;
    return `<button class="chip ${st.comp.has(c.id)?"on":""}" data-c="${c.id}">${esc(c.name)}<b>${n}</b></button>`; }).join("");
  document.querySelectorAll(".chip").forEach(b => b.onclick = () => { const id = b.dataset.c;
    st.comp.has(id) ? st.comp.delete(id) : st.comp.add(id); st.show = 36; drawChips(); drawFeed(); });
}
function card(a){
  const c = byId[a.comp], g = a.src === "google";
  const img = a.image ? `<img loading="lazy" src="${esc(a.image)}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'ph',textContent:'Preview expired. Open the ad to view it.'}))">`
                      : `<div class="ph">${g ? "Video or HTML ad. Open it in Google to view." : "No preview"}</div>`;
  const place = g ? "" : (a.placements||[]).map(p => p.replace("AUDIENCE_NETWORK","AN").toLowerCase()).join(" · ");
  const long = (a.text||"").length > 180;
  return `<article class="ad ${a.comp===SELF?"selfad":""}">
    <div class="thumb ${g?"g":""}">${img}<div class="badges">${a.isNew?'<span class="b new">NEW</span>':""}<span class="b">${esc(a.format)}</span>${a.days?`<span class="b">${plural(a.days,"day")}</span>`:""}${a.variants>1?`<span class="b">${a.variants} versions</span>`:""}${a.impRank&&a.impRank<=3?`<span class="b" title="Meta ranks this among the advertiser's most-seen ads">Top ${a.impRank} seen</span>`:""}${a.aiMedia?'<span class="b">AI media</span>':""}</div></div>
    <div class="body">
      <div class="who"><span>${esc(c.name)}${a.comp===SELF?' <span class="you">YOU</span>':""}</span><span class="src ${a.src}">${g?"GOOGLE":"META"}</span></div>
      ${a.title?`<div style="font-weight:600;font-size:13px">${esc(a.title)}</div>`:""}
      ${a.text?`<div class="txt">${esc(a.text)}</div>${long?'<button class="more">Show more</button>':""}`:""}
      <div class="row">${a.dest.map(d=>`<span class="pill">${esc(d)}</span>`).join("")}${place?`<span>${esc(place)}</span>`:""}</div>
      ${g?`<div class="row"><span>Last shown ${fmtDate(a.last)}</span>${a.w?`<span>· ${a.w}×${a.h}</span>`:""}</div>`:""}
      <div class="foot"><span class="muted">Since ${fmtDate(a.start)}</span>${a.cta?`<span class="cta">${esc(a.cta)}</span>`:""}${g?"":`<button class="linkbtn" data-ad="${a.id}">Details</button>`}<a href="${esc(a.url)}" target="_blank" rel="noopener">View ↗</a></div>
    </div></article>`;
}
function filtered(){
  const q = st.q.toLowerCase();
  let r = ads.filter(a => (st.src==="all"||a.src===st.src) && (!st.comp.size||st.comp.has(a.comp)) && (!st.fmt||a.format===st.fmt)
    && (!st.dest||a.dest.includes(st.dest)) && (!st.newOnly||a.isNew) && (!st.lead||a.lead===st.lead)
    && (!q || (a.text+" "+a.title+" "+byId[a.comp].name).toLowerCase().includes(q)));
  if (st.sort === "rank") return r.sort((a,b)=>(a.impRank||999)-(b.impRank||999));
  return st.sort === "longest" ? r.sort((a,b)=>(b.days||0)-(a.days||0)) : r.sort((a,b)=>(b.start||"").localeCompare(a.start||""));
}
function drawFeed(){
  const r = filtered();
  $("#feed").innerHTML = r.length ? r.slice(0, st.show).map(card).join("") : `<div class="empty" style="grid-column:1/-1">No ads match these filters.</div>`;
  $("#more").hidden = r.length <= st.show; $("#more").textContent = `Show more (${r.length - st.show} left)`;
  document.querySelectorAll(".more").forEach(b => b.onclick = () => { const t = b.previousElementSibling; t.classList.toggle("open"); b.textContent = t.classList.contains("open") ? "Show less" : "Show more"; });
}
document.querySelectorAll("#srcSeg button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#srcSeg button").forEach(x => x.classList.toggle("on", x===b)); st.src = b.dataset.v; st.show = 36; drawChips(); drawFeed(); });
$("#fmt").onchange = e => { st.fmt = e.target.value; st.show = 36; drawFeed(); };
$("#dest").onchange = e => { st.dest = e.target.value; st.show = 36; drawFeed(); };
$("#sort").onchange = e => { st.sort = e.target.value; drawFeed(); };
$("#newOnly").onchange = e => { st.newOnly = e.target.checked; st.show = 36; drawFeed(); };
$("#q").oninput = e => { st.q = e.target.value; st.show = 36; drawFeed(); };
$("#more").onclick = () => { st.show += 36; drawFeed(); };
drawChips(); drawFeed();

// ── Ad details dialog: every field we have for the ad ──
const byAd = Object.fromEntries(DATA.ads.map(a => [a.id, a]));
const nd = '<span class="muted">Not disclosed by Meta for India</span>';
function showAd(id){
  const a = byAd[id]; if (!a) return; const c = byId[a.comp];
  const media = a.video ? `<video src="${esc(a.video)}" poster="${esc(a.image)}" controls preload="none"></video>` : (a.image ? `<img src="${esc(a.image)}" alt="">` : "");
  const cards = (a.cardList||[]).length ? `<div class="cardrow">${a.cardList.map(k => `<figure>${k.image?`<img src="${esc(k.image)}" alt="" loading="lazy">`:""}<figcaption><strong>${esc(k.title)}</strong><br>${esc(k.body.slice(0,80))}</figcaption></figure>`).join("")}</div>` : "";
  const extra = (a.extraImages||[]).length ? `<div class="cardrow">${a.extraImages.map(u => `<figure><img src="${esc(u)}" alt="" loading="lazy"></figure>`).join("")}</div>` : "";
  const kv = [["Advertiser", esc(c.name) + (a.advertiser && a.advertiser!==c.name ? ` <span class="muted">(${esc(a.advertiser)})</span>`:"")],
    ["Library ID", `<a href="${esc(a.url)}" target="_blank" rel="noopener" style="color:var(--accent)">${esc(a.libraryId)}</a>`], ["Collation ID", esc(a.collationId||"—")], ["Page ID", esc(a.pageId||"—")],
    ["Status", a.active ? "Active" : "Inactive"], ["Started", esc(a.startTs||a.start)], ["Last seen", esc(a.endTs||a.last)], ["Days running", a.days ?? "—"],
    ["Format", esc(a.format) + (a.cards?` · ${a.cards} cards`:"")], ["Versions", a.variants], ["Impression rank", a.impRank ? `#${a.impRank} of this advertiser's live ads (Meta sort)` : "—"],
    ["Impressions", a.impressions ? esc(a.impressions) : nd], ["Reach", a.reach ? esc(JSON.stringify(a.reach)) : nd], ["Spend", a.spend ? esc(JSON.stringify(a.spend)) + " " + esc(a.currency) : nd],
    ["Placements", esc((a.placements||[]).join(", ") || "—")], ["Button", esc(a.cta||"—") + (a.ctaType?` <span class="muted">(${esc(a.ctaType)})</span>`:"")], ["Lead capture", esc(a.lead)],
    ["Landing link", a.link ? `<a href="${esc(a.link)}" target="_blank" rel="noopener nofollow" style="color:var(--accent)">${esc(a.link.slice(0,70))}${a.link.length>70?"…":""}</a>` : "—"],
    ["Display link", esc(a.caption||"—")], ["Other links", esc((a.extraLinks||[]).join(", ") || "—")],
    ["Language", esc(a.lang)], ["Prices in copy", (a.prices||[]).length ? a.prices.map(inr).join(", ") : "—"], ["Trip length", esc(a.duration||"—")],
    ["Destinations", esc(a.dest.join(", ") || "—")], ["AI-generated media", a.aiMedia ? "Yes (Meta label)" : "No"]];
  $("#dlgT").textContent = `${c.name}: ${a.title || "Ad " + a.libraryId}`;
  $("#dlgB").innerHTML = `<div>${media}${cards}${extra}${a.text?`<p style="white-space:pre-line;font-size:13px;color:var(--fg-dim)">${esc(a.text)}</p>`:""}${a.linkDesc?`<p class="muted" style="font-size:12px">${esc(a.linkDesc)}</p>`:""}</div>
    <dl class="kv">${kv.map(([k,v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
  $("#dlg").showModal();
}
document.addEventListener("click", e => { const b = e.target.closest("[data-ad]"); if (b) showAd(b.dataset.ad); });

// ── CSV export of the current feed filter ──
$("#csv").onclick = () => {
  const cols = ["advertiser","src","libraryId","format","title","text","cta","lead","link","start","last","days","placements","lang","prices","duration","dest","impRank","variants","aiMedia","url"];
  const q = v => `"${String(Array.isArray(v) ? v.join(" | ") : (v ?? "")).replace(/"/g,'""')}"`;
  const rowsCsv = filtered().map(a => cols.map(k => q(k==="advertiser" ? byId[a.comp].name : a[k])).join(","));
  const blob = new Blob(["\ufeff" + [cols.join(","), ...rowsCsv].join("\n")], {type:"text/csv"});
  const u = URL.createObjectURL(blob), l = Object.assign(document.createElement("a"), {href:u, download:`paid-ads-${new Date().toISOString().slice(0,10)}.csv`});
  document.body.appendChild(l); l.click(); l.remove(); setTimeout(() => URL.revokeObjectURL(u), 1000);
};
</script>
</body>
</html>
"""


def main():
    if not SRC.exists():
        raise SystemExit("data/ads/ads.json not found. Run ads_refresh.py first.")
    data = json.loads(SRC.read_text())
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__DATA__", payload))
    live = sum(1 for a in data["ads"] if a.get("active"))
    print(f"Built {OUT.name}: {live} live ads across {len(data['competitors'])} advertisers")


if __name__ == "__main__":
    main()
