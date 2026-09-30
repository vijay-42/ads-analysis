#!/usr/bin/env python3
"""
Paid-Ads competitor refresh pipeline (Meta + Google).

  1. Read competitor list from ads_config.json
  2. Run the official Meta Ad Library actor (apify/facebook-ads-scraper)
     for every competitor Facebook page ID
  3. Run the Google Ads Transparency actor for every competitor's domain
  4. Normalise both into one ad list, tag destinations, remember when we
     first saw each ad (so the dashboard can show "new this week")
  5. Download Meta thumbnails locally (Facebook CDN links expire in days)
  6. Build the dashboard (ads_build.py -> index.html)

Usage
  APIFY_TOKEN=... python3 ads_refresh.py            # live run (GitHub Actions)
  python3 ads_refresh.py --from-files meta.json google.json [totals.json] [profiles.json]
                                                   # rebuild from saved raw datasets

Pure stdlib. Requires APIFY_TOKEN for a live run.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "ads_config.json"
DATA = ROOT / "data" / "ads"
THUMBS = ROOT / "thumbs" / "ads"

META_ACTOR = "apify~facebook-ads-scraper"   # official Apify actor
GOOGLE_ACTOR = "scrapesage~google-ads-transparency-scraper"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"

# Destination keywords -> label. Matched against ad text + landing URL.
DESTINATIONS = {
    "Shirdi": ["shirdi", "sai baba"],
    "Kashi / Varanasi": ["kashi", "varanasi", "banaras", "vishwanath"],
    "Ayodhya": ["ayodhya", "ram mandir", "ram lalla"],
    "Prayagraj": ["prayagraj", "allahabad", "triveni"],
    "Gaya / Bodhgaya": ["gaya", "bodhgaya", "bodh gaya"],
    "Jyotirlinga": ["jyotirling", "jyotirlinga", "jyothirlinga"],
    "Ujjain / Omkareshwar": ["ujjain", "mahakal", "omkareshwar", "indore"],
    "Char Dham / Kedarnath": ["char dham", "chardham", "kedarnath", "badrinath", "gangotri", "yamunotri", "do dham"],
    "Tirupati": ["tirupati", "tirumala", "balaji darshan"],
    "Puri / Odisha": ["puri", "jagannath", "konark", "bhubaneswar"],
    "Rameshwaram / Madurai": ["rameshwaram", "rameswaram", "madurai", "dhanushkodi", "kanyakumari"],
    "Mantralayam": ["mantralayam", "raghavendra"],
    "Gujarat / Dwarka": ["gujarat", "dwarka", "somnath", "statue of unity", "kutch"],
    "Nepal / Kailash": ["nepal", "muktinath", "pashupatinath", "kailash", "mansarovar"],
    "Vaishno Devi / Kashmir": ["vaishno", "kashmir", "srinagar", "amarnath"],
    "Kerala": ["kerala", "munnar", "alleppey", "guruvayur"],
    "Andaman": ["andaman", "port blair", "havelock"],
    "Kamakhya / North East": ["kamakhya", "guwahati", "meghalaya", "shillong", "tawang", "sikkim", "darjeeling"],
    "Himachal / Ladakh": ["manali", "shimla", "ladakh", "leh"],
    "International": ["dubai", "bali", "thailand", "vietnam", "singapore", "malaysia", "europe", "sri lanka",
                      "maldives", "japan", "turkey", "kazakhstan", "bhutan", "mauritius", "international"],
}


# ───────────────────────── Apify helpers ─────────────────────────

def _token():
    t = os.environ.get("APIFY_TOKEN")
    if not t and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("APIFY_TOKEN="):
                t = line.split("=", 1)[1].strip()
    if not t:
        sys.exit("ERROR: APIFY_TOKEN env var (or .env) required for a live run")
    return t


def _req(method, path, body=None, **params):
    qs = urllib.parse.urlencode({**params, "token": _token()})
    url = f"https://api.apify.com/v2/{path}?{qs}"
    data = json.dumps(body).encode() if body is not None else None
    for attempt, delay in enumerate([0, 2, 5, 10, 20, 40]):
        if delay:
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                print(f"  ! {path} -> HTTP {e.code}, retry {attempt + 1}")
                continue
            raise
        except urllib.error.URLError as e:
            print(f"  ! {path} -> {e}, retry {attempt + 1}")
    raise RuntimeError(f"Apify request failed: {path}")


def run_actor(actor, body, label, max_wait=900):
    run = _req("POST", f"acts/{actor}/runs", body)["data"]
    print(f"  [{label}] started run {run['id']}")
    start = time.time()
    while True:
        r = _req("GET", f"actor-runs/{run['id']}")["data"]
        if r["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            print(f"  [{label}] {r['status']} after {int(time.time() - start)}s")
            break
        if time.time() - start > max_wait:
            raise RuntimeError(f"{label} did not finish in {max_wait}s")
        time.sleep(8)
    if r["status"] != "SUCCEEDED":
        print(f"  [{label}] WARNING: run ended {r['status']} — using whatever it returned")
    return _req("GET", f"datasets/{r['defaultDatasetId']}/items", clean="true")


# ───────────────────────── normalise ─────────────────────────

def tag_destinations(*texts):
    blob = " ".join(t for t in texts if t).lower()
    return [label for label, kws in DESTINATIONS.items()
            if any(re.search(r"\b" + re.escape(k), blob) for k in kws)]


def _page_key(url):
    """facebook.com/SaiShishirTours.in/ -> saishishirtours.in"""
    if not url:
        return ""
    path = urllib.parse.urlparse(url).path.strip("/").lower()
    return path.split("/")[0]


def _days_between(a, b):
    try:
        da = datetime.fromisoformat(a.replace("Z", "+00:00")) if "T" in a else datetime.fromisoformat(a).replace(tzinfo=timezone.utc)
        db = datetime.fromisoformat(b.replace("Z", "+00:00")) if "T" in b else datetime.fromisoformat(b).replace(tzinfo=timezone.utc)
        return max(1, (db - da).days + 1)
    except Exception:
        return None


def _ts(v):
    """Official actor gives unix seconds; older actor gives ISO strings."""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, timezone.utc).date().isoformat()
    return str(v)[:10]


def _first(lst, *keys):
    for item in lst or []:
        for k in keys:
            if item.get(k):
                return item[k]
    return ""


# Script ranges -> language of the ad copy (no external library needed)
_SCRIPTS = [("Kannada", 0x0C80, 0x0CFF), ("Telugu", 0x0C00, 0x0C7F), ("Tamil", 0x0B80, 0x0BFF),
            ("Malayalam", 0x0D00, 0x0D7F), ("Gujarati", 0x0A80, 0x0AFF), ("Bengali", 0x0980, 0x09FF),
            ("Odia", 0x0B00, 0x0B7F), ("Hindi/Marathi", 0x0900, 0x097F)]


def detect_language(text):
    counts = {}
    for ch in text or "":
        o = ord(ch)
        for name, lo, hi in _SCRIPTS:
            if lo <= o <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    latin = sum(1 for ch in text or "" if ch.isascii() and ch.isalpha())
    if counts:
        top = max(counts, key=counts.get)
        return f"{top} + English" if latin > counts[top] * 0.6 else top
    return "English" if latin else "—"


_PRICE = re.compile(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]{2,}(?:\.\d+)?)\s*(k|/-)?", re.I)


def extract_prices(*texts):
    """₹ amounts mentioned in the ad copy -> sorted unique ints."""
    found = set()
    for t in texts:
        for m in _PRICE.finditer(t or ""):
            try:
                v = float(m.group(1).replace(",", ""))
                if (m.group(2) or "").lower() == "k":
                    v *= 1000
                if 500 <= v <= 2_000_000:  # ignore coupon codes / phone fragments
                    found.add(int(v))
            except ValueError:
                pass
    return sorted(found)


def nights_days(*texts):
    blob = " ".join(t or "" for t in texts)
    sep = r"\s*(?:[/&|,+-]|and)?\s*"
    m = re.search(r"(\d{1,2})\s*n(?:ights?)?" + sep + r"(\d{1,2})\s*d(?:ays?)?", blob, re.I)
    if m:
        return f"{m.group(1)}N/{m.group(2)}D"
    m = re.search(r"(\d{1,2})\s*d(?:ays?)?" + sep + r"(\d{1,2})\s*n(?:ights?)?", blob, re.I)
    return f"{m.group(2)}N/{m.group(1)}D" if m else ""


def lead_type(cta_type, cta_text, link):
    t = f"{cta_type} {cta_text} {link}".lower()
    if "whatsapp" in t:
        return "WhatsApp"
    if "call" in t or link.startswith("tel:"):
        return "Call"
    if "fb.me" in t or "sign_up" in t or "sign up" in t or "get_quote" in t or "get quote" in t:
        return "Lead form"
    if "install" in t or "play.google" in t or "apps.apple" in t or "onelink" in t:
        return "App install"
    if "message" in t or "messenger" in t:
        return "Messenger"
    return "Website" if link else "Other"


def _ts_full(v):
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return str(v or "")


def _ts(v):
    """Official actor gives unix seconds; older actor gives ISO strings."""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, timezone.utc).date().isoformat()
    return str(v)[:10]


def _first(lst, *keys):
    for item in lst or []:
        for k in keys:
            if item.get(k):
                return item[k]
    return ""


def normalise_meta(raw, comps, today):
    """apify/facebook-ads-scraper (official) output -> flat ad records with
    every metric the Ad Library exposes. Also tolerates the older flat schema."""
    by_id = {str(pid): c["id"] for c in comps for pid in (c.get("fbPageIds") or [])}
    by_page = {_page_key(c["fbPage"]): c["id"] for c in comps if c.get("fbPage")}
    out, seen, pages = [], set(), {}
    rank_counter = {}
    for a in raw:
        snap = a.get("snapshot") or {}
        page_id = str(a.get("pageId") or a.get("pageID") or snap.get("pageId") or "")
        cid = by_id.get(page_id) or by_page.get(_page_key(a.get("pageUrl") or snap.get("pageProfileUri")))
        if not cid:
            continue  # ad from a page we don't track
        aid = str(a.get("adArchiveId") or a.get("adArchiveID") or "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        # results arrive sorted by impressions (high -> low) per page, so the
        # position is Meta's own impression ranking for that advertiser
        rank_counter[page_id] = rank_counter.get(page_id, 0) + 1

        cards = snap.get("cards") or []
        text = ((snap.get("body") or {}).get("text") if isinstance(snap.get("body"), dict) else snap.get("body")) \
            or a.get("bodyText") or _first(cards, "body") or ""
        title = snap.get("title") or a.get("title") or _first(cards, "title") or ""
        if "{{" in title:  # catalogue (DPA) ads carry template placeholders
            title = _first(cards, "title") or "Catalogue ad"
        link = snap.get("linkUrl") or a.get("linkUrl") or _first(cards, "linkUrl") or ""
        image = (_first(snap.get("images"), "resizedImageUrl", "originalImageUrl")
                 or _first(snap.get("videos"), "videoPreviewImageUrl")
                 or _first(cards, "resizedImageUrl", "originalImageUrl", "videoPreviewImageUrl")
                 or (a.get("imageUrls") or [""])[0] or (a.get("videoPreviewUrls") or [""])[0])
        video = _first(snap.get("videos"), "videoSdUrl", "videoHdUrl") or (a.get("videoUrls") or [""])[0]
        start = _ts(a.get("startDate"))
        fmt = (snap.get("displayFormat") or a.get("displayFormat") or "UNKNOWN").upper()
        card_titles = " ".join(str(c.get("title") or "") + " " + str(c.get("body") or "") for c in cards)
        cta_type = snap.get("ctaType") or a.get("ctaType") or ""
        cta = snap.get("ctaText") or a.get("ctaText") or ""
        imp = a.get("impressionsWithIndex") or {}
        out.append({
            "id": "m" + aid,
            "src": "meta",
            "comp": cid,
            "advertiser": a.get("pageName") or snap.get("pageName"),
            "pageId": page_id,
            "libraryId": aid,
            "collationId": str(a.get("collationId") or ""),
            "format": fmt,
            "text": text,
            "title": title,
            "linkDesc": snap.get("linkDescription") or "",
            "caption": snap.get("caption") or "",
            "cta": cta,
            "ctaType": cta_type,
            "lead": lead_type(cta_type, cta, link),
            "link": link,
            "extraLinks": snap.get("extraLinks") or [],
            "start": start,
            "startTs": _ts_full(a.get("startDate")),
            "last": _ts(a.get("endDate")) or today,
            "endTs": _ts_full(a.get("endDate")),
            "days": _days_between(start, today) if start else None,
            "active": bool(a.get("isActive", True)),
            "placements": a.get("publisherPlatform") or a.get("platforms") or [],
            "image": image,
            "video": video,
            "cardList": [{"title": c.get("title") or "", "body": (c.get("body") or "")[:200],
                          "image": c.get("resizedImageUrl") or c.get("originalImageUrl") or c.get("videoPreviewImageUrl") or "",
                          "link": c.get("linkUrl") or "", "cta": c.get("ctaText") or ""} for c in cards[:10]],
            "extraImages": [x.get("resizedImageUrl") or x.get("originalImageUrl") for x in (snap.get("extraImages") or [])][:6],
            "cards": len(cards),
            "variants": a.get("collationCount") or 1,
            "impRank": rank_counter[page_id],
            "aiMedia": bool(a.get("containsDigitalCreatedMedia")),
            "categories": [c for c in (a.get("categories") or []) if c and c != "UNKNOWN"],
            # Disclosed by Meta only for EU-delivered or political ads; kept so
            # they show up automatically if Meta ever returns them.
            "spend": a.get("spend"),
            "reach": a.get("reachEstimate"),
            "impressions": imp.get("impressionsText"),
            "currency": a.get("currency") or "",
            "lang": detect_language(text + " " + title),
            "prices": extract_prices(text, title, card_titles, snap.get("linkDescription")),
            "duration": nights_days(text, title, card_titles),
            "url": a.get("adLibraryUrl") or f"https://www.facebook.com/ads/library/?id={aid}",
            "dest": tag_destinations(text, title, link, snap.get("linkDescription"), card_titles),
        })

        # page-level transparency facts
        info = ((a.get("pageInfo") or {}).get("page") or {})
        pinfo = pages.setdefault(cid, {"pageIds": set()})
        pinfo["pageIds"].add(page_id)
        if not pinfo.get("likes"):
            pinfo["likes"] = snap.get("pageLikeCount") or a.get("pageLikeCount")
        if not pinfo.get("profilePic"):
            pinfo["profilePic"] = snap.get("pageProfilePictureUrl") or ""
        if not pinfo.get("categories") and snap.get("pageCategories"):
            pinfo["categories"] = ", ".join(snap.get("pageCategories") or [])
        tinfo = info.get("pagesTransparencyInfo") or {}
        hist = tinfo.get("historyItems") or []
        if hist and not pinfo.get("created"):
            pinfo["created"] = next((h.get("eventTimeFormatted", "")[:10] for h in hist if h.get("itemType") == "CREATION"), "")
            pinfo["nameChanges"] = sum(1 for h in hist if h.get("itemType") == "NAME_CHANGE")
            pinfo["merges"] = sum(1 for h in hist if "MERGE" in (h.get("itemType") or ""))
            pinfo["history"] = [f"{h.get('eventTimeFormatted','')[:10]} {h.get('itemType','').replace('_',' ').lower()}" for h in hist][:8]
        admins = ((tinfo.get("adminLocations") or {}).get("adminCountryCounts") or [])
        if admins and not pinfo.get("admins"):
            pinfo["admins"] = ", ".join(f"{x['country']['isoName']} ({x['count']})" for x in admins if x.get("country"))
            pinfo["adminCount"] = sum(x.get("count", 0) for x in admins)
        owner = info.get("confirmedPageOwner") or {}
        if owner and not pinfo.get("owner"):
            addr = ((owner.get("information") or {}).get("address") or {})
            pinfo["owner"] = owner.get("name") or ""
            pinfo["ownerLocation"] = ", ".join(x for x in [addr.get("city"), addr.get("state"), addr.get("country")] if x)
            pinfo["ownerPhone"] = (owner.get("information") or {}).get("phoneNumber") or ""
        if not pinfo.get("about"):
            pinfo["about"] = ((info.get("about") or {}).get("text") or "")[:300]
    for p in pages.values():
        p["pageIds"] = sorted(p["pageIds"])
    return out, pages


def merge_totals(pages, totals_raw, comps):
    """onlyTotal run -> real number of live Meta ads per advertiser."""
    by_pid = {str(pid): c["id"] for c in comps for pid in (c.get("fbPageIds") or [])}
    for t in totals_raw:
        m = re.search(r"view_all_page_id=(\d+)", t.get("inputUrl") or "")
        cid = by_pid.get(m.group(1)) if m else None
        if cid and t.get("totalCount") is not None:
            p = pages.setdefault(cid, {"pageIds": []})
            p["metaTotal"] = p.get("metaTotal", 0) + int(t["totalCount"])


def merge_profiles(pages, prof_raw, comps):
    """isDetailsPerAd run (1 ad per page) -> Instagram + verification facts."""
    by_pid = {str(pid): c["id"] for c in comps for pid in (c.get("fbPageIds") or [])}
    for r in prof_raw:
        cid = by_pid.get(str(r.get("pageId") or ""))
        info = ((((r.get("ad_details") or {}).get("advertiser") or {}).get("ad_library_page_info")) or {})
        pi, sp = info.get("page_info") or {}, info.get("page_spend") or {}
        if not cid or not pi:
            continue
        p = pages.setdefault(cid, {"pageIds": []})
        # an advertiser can have several pages: keep the biggest numbers
        if (pi.get("ig_followers") or 0) > (p.get("igFollowers") or 0):
            p["igFollowers"] = pi.get("ig_followers")
            p["igUsername"] = pi.get("ig_username")
            p["igVerified"] = pi.get("ig_verification")
        if (pi.get("likes") or 0) > (p.get("likes") or 0):
            p["likes"] = pi.get("likes")
        if pi.get("page_verification") == "BLUE_VERIFIED" or not p.get("fbVerified"):
            p["fbVerified"] = pi.get("page_verification") == "BLUE_VERIFIED"
        p["category"] = p.get("category") or pi.get("page_category")
        p["weeklySpend"] = sp.get("current_week")  # null unless political
        p["political"] = bool(sp.get("is_political_page"))


def normalise_google(raw, comps, today):
    by_domain = {c["domain"].lower(): c["id"] for c in comps if c.get("domain")}
    out, seen = [], set()
    for a in raw:
        cid = by_domain.get((a.get("domain") or "").lower())
        if not cid:
            continue
        gid = a.get("creativeId")
        if not gid or gid in seen:
            continue
        seen.add(gid)
        last = (a.get("lastShown") or "")[:10]
        out.append({
            "id": "g" + gid,
            "src": "google",
            "comp": cid,
            "advertiser": a.get("advertiserName"),
            "format": (a.get("format") or "UNKNOWN").upper(),
            "text": "", "title": "", "cta": "",
            "link": "https://" + a.get("domain", ""),
            "start": (a.get("firstShown") or "")[:10],
            "last": last,
            "days": a.get("shownForDays"),
            # "live" = shown in the last 3 days
            "active": bool(last) and _days_between(last, today) is not None and _days_between(last, today) <= 3,
            "placements": ["GOOGLE"],
            "image": a.get("imageUrl") or "",
            "preview": a.get("previewUrl") or "",
            "w": a.get("width"), "h": a.get("height"),
            "video": "",
            "variants": 1,
            "url": a.get("adUrl") or "",
            "dest": [],
        })
    return out


# ───────────────────────── history + thumbs ─────────────────────────

def apply_history(ads, today):
    """Remember the date we first saw each ad -> powers 'new this week'."""
    hist_path = DATA / "history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {}
    first_run = not hist
    for a in ads:
        if a["id"] not in hist:
            hist[a["id"]] = today
        a["firstSeen"] = hist[a["id"]]
        # On the very first run everything is "seen today"; fall back to the
        # platform's own start date so the "new" badge stays meaningful.
        a["isNew"] = (not first_run and a["firstSeen"] == today) or \
                     (a["start"] and _days_between(a["start"], today) is not None and _days_between(a["start"], today) <= 7)
    hist_path.write_text(json.dumps(hist, indent=0))


def download_thumbs(ads):
    """Facebook CDN image links expire; keep a local copy. Google links are stable."""
    THUMBS.mkdir(parents=True, exist_ok=True)

    def grab(a):
        if a["src"] != "meta" or not a["image"]:
            return
        dest = THUMBS / f"{a['id']}.jpg"
        if not dest.exists():
            try:
                req = urllib.request.Request(a["image"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dest.write_bytes(r.read())
            except Exception as e:
                print(f"  ! thumb {a['id']}: {e}")
                return
        a["image"] = f"thumbs/ads/{dest.name}"

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(grab, ads))
    keep = {f"{a['id']}.jpg" for a in ads}
    for f in THUMBS.glob("*.jpg"):  # prune thumbs of ads no longer returned
        if f.name not in keep:
            f.unlink()


# ───────────────────────── main ─────────────────────────

def _load_items(paths):
    items = []
    for f in paths.split(","):
        d = json.loads(Path(f).read_text())
        items += d.get("items", d) if isinstance(d, dict) else d
    return items


def main():
    cfg = json.loads(CONFIG.read_text())
    comps = cfg["competitors"]
    region = cfg.get("region", "IN")
    lim = cfg.get("limits", {})
    today = datetime.now(timezone.utc).date().isoformat()
    DATA.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) >= 4 and sys.argv[1] == "--from-files":
        meta_raw = []
        for f in sys.argv[2].split(","):  # comma-separated list of Meta dumps
            d = json.loads(Path(f).read_text())
            meta_raw += d.get("items", d) if isinstance(d, dict) else d
        google_raw = []
        for f in sys.argv[3].split(","):  # comma-separated list of Google dumps
            d = json.loads(Path(f).read_text())
            google_raw += d.get("items", d) if isinstance(d, dict) else d
        totals_raw = _load_items(sys.argv[4]) if len(sys.argv) > 4 else []
        prof_raw = _load_items(sys.argv[5]) if len(sys.argv) > 5 else []
        offline = True
    else:
        offline = False
        page_ids = [pid for c in comps for pid in (c.get("fbPageIds") or [])]
        domains = [c["domain"] for c in comps if c.get("domain")]
        print(f"Meta: {len(page_ids)} pages · Google: {len(domains)} domains · region {region}")
        lib = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
               f"&country={region}&search_type=page&view_all_page_id=")
        urls = [{"url": lib + pid} for pid in page_ids]
        meta_raw = run_actor(META_ACTOR, {
            "startUrls": urls, "resultsLimit": lim.get("metaMaxAdsPerPage", 40),
            "sorting": "total_impressions", "includeAboutPage": True}, "meta ads") if page_ids else []
        # real number of live ads per page (not capped by resultsLimit)
        totals_raw = run_actor(META_ACTOR, {"startUrls": urls, "onlyTotal": True}, "meta totals") if page_ids else []
        # one ad per page with details -> Instagram followers / verification
        prof_raw = run_actor(META_ACTOR, {"startUrls": urls, "resultsLimit": 1, "isDetailsPerAd": True},
                             "meta profiles") if page_ids else []
        google_raw = run_actor(GOOGLE_ACTOR, {
            "domains": domains, "region": region,
            "maxAdsPerSearch": lim.get("googleMaxAdsPerDomain", 40)}, "google") if domains else []

    meta_ads, pages = normalise_meta(meta_raw, comps, today)
    merge_totals(pages, totals_raw, comps)
    merge_profiles(pages, prof_raw, comps)
    ads = meta_ads + normalise_google(google_raw, comps, today)
    apply_history(ads, today)
    if not offline:
        download_thumbs(ads)

    snapshot = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                "region": region, "self": cfg.get("self"), "competitors": comps, "pages": pages, "limits": lim, "ads": ads}
    (DATA / "ads.json").write_text(json.dumps(snapshot, ensure_ascii=False))
    print(f"Saved {len(ads)} ads ({sum(a['src'] == 'meta' for a in ads)} Meta, "
          f"{sum(a['src'] == 'google' for a in ads)} Google)")

    subprocess.run([sys.executable, str(ROOT / "ads_build.py")], check=True)


if __name__ == "__main__":
    main()
