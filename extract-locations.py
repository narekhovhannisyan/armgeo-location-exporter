#!/usr/bin/env python3
"""Extract tours and locations with coordinates from armgeo.am."""

import json
import re
import time
import urllib.request
from html import unescape

BASE = "https://www.armgeo.am/en/wp-json/wp/v2"

TOUR_CAT_IDS = [
    277, 323, 692, 322, 739, 658, 371, 337, 687, 232, 512, 693, 242,
    608, 233, 599, 378, 367, 361, 701, 684, 725,
]
LOC_CAT_IDS = [190, 313, 694, 712]

CAT_META = {
    277: {"name": "1 Day Tours", "slug": "daily-tours", "group": "tour"},
    323: {"name": "2 Day Hikes", "slug": "2-day-tours", "group": "tour"},
    692: {"name": "2 Day Tours", "slug": "two-day-excursions-en-2", "group": "tour"},
    322: {"name": "3 Day Hikes", "slug": "3-day-tours", "group": "tour"},
    739: {"name": "3 Day Tours", "slug": "3-day-tours-en", "group": "tour"},
    658: {"name": "Caving", "slug": "caving", "group": "tour"},
    371: {"name": "Cultural Tours", "slug": "cultural-tours", "group": "tour"},
    337: {"name": "Cycling Tours", "slug": "cycling-tours", "group": "tour"},
    687: {"name": "Gastronomic Tours", "slug": "gastronomical-tours-en", "group": "tour"},
    232: {"name": "Hiking & Climbing", "slug": "hiking-climbing", "group": "tour"},
    512: {"name": "Hiking in National Parks", "slug": "hiking-in-national-parks", "group": "tour"},
    693: {"name": "Horseback Riding", "slug": "horseback-riding-tours-en-2", "group": "tour"},
    242: {"name": "Jeeping", "slug": "jeeping", "group": "tour"},
    684: {"name": "Multi-Day Tours", "slug": "multi-day-hikes-en", "group": "tour"},
    608: {"name": "Paragliding", "slug": "paragliding-in-armenia", "group": "tour"},
    233: {"name": "Photo Tours", "slug": "photo-tours", "group": "tour"},
    599: {"name": "SUP Tours", "slug": "sup-tours", "group": "tour"},
    378: {"name": "Wine Tours", "slug": "wine-tours", "group": "tour"},
    367: {"name": "Winter Hikes", "slug": "winter-hikes", "group": "tour"},
    361: {"name": "Yoga Tours", "slug": "yoga-tours", "group": "tour"},
    701: {"name": "Winter Tours", "slug": "winter-tours-in-armenia-en", "group": "tour"},
    725: {"name": "Outgoing Tours", "slug": "outgoing-tours-en", "group": "tour"},
    190: {"name": "Mountains", "slug": "mountains-en", "group": "location"},
    313: {"name": "Armenian Highland", "slug": "armenian-highland-en", "group": "location"},
    694: {"name": "Hydrography", "slug": "hydrography-of-armenia-en", "group": "location"},
    712: {"name": "Fortresses", "slug": "fortresses", "group": "location"},
}

GROUP_ORDER = {
    "location": ["Mountains", "Armenian Highland", "Hydrography", "Fortresses", "Other"],
    "tour": None,  # alphabetical
    "both": None,
}

APOSTROPHE_VARIANTS = (
    "\u2019", "\u2018", "\u2032", "\u00b4", "&#8217;", "&#39;", "′", "’", "‘",
)


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arm-geo-extractor/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode(errors="replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def strip_tags(s):
    s = unescape(s)
    for ch in APOSTROPHE_VARIANTS:
        s = s.replace(ch, "'")
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def dms_to_decimal(degrees, minutes, seconds=None):
    return round(float(degrees) + float(minutes) / 60 + float(seconds or 0) / 3600, 6)


def parse_coords(text):
    text = strip_tags(text)

    m = re.search(
        r"(?:Coordinates?|Կոորդինատները?)\s*[:՝\-]+\s*"
        r"([0-9]{1,2}(?:\.[0-9]+)?)\s*,\s*([0-9]{1,2}(?:\.[0-9]+)?)",
        text,
        re.I,
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(
        r"(?:Coordinates?|Կոորդինատները?)\s*[:՝\-]+\s*"
        r"(\d{1,2})°\s*(\d{1,2}(?:\.\d+)?)'\s*(\d{1,2}(?:\.\d+)?)?\s*,\s*"
        r"(\d{1,2})°\s*(\d{1,2}(?:\.\d+)?)'\s*(\d{1,2}(?:\.\d+)?)?",
        text,
        re.I,
    )
    if m:
        return (
            dms_to_decimal(m.group(1), m.group(2), m.group(3)),
            dms_to_decimal(m.group(4), m.group(5), m.group(6)),
        )

    return None, None


def hy_url_from_page(html, en_url):
    m = re.search(r'hreflang="hy"\s+href="([^"]+)"', html)
    if m:
        return m.group(1)
    return en_url.replace("/en/", "/", 1)


def extract_location(html):
    text = strip_tags(html)
    m = re.search(
        r"Location\s*[:\-]+\s*([^|]+?)"
        r"(?:\s*(?:Driving|Trail|Length|Elevation|Difficulty|Distance|Number|Price|The best)|$)",
        text,
        re.I,
    )
    return m.group(1).strip(" .-")[:120] if m else None


def pick_category(category_ids, kind):
    known = [cid for cid in category_ids if cid in CAT_META]
    if not known:
        return {"id": None, "name": "Other", "slug": "other", "group": kind}

    loc_cats = [c for c in known if CAT_META[c]["group"] == "location"]
    tour_cats = [c for c in known if CAT_META[c]["group"] == "tour"]

    if kind == "location" and loc_cats:
        cid = loc_cats[0]
    elif kind == "tour" and tour_cats:
        cid = tour_cats[0]
    elif loc_cats:
        cid = loc_cats[0]
    elif tour_cats:
        cid = tour_cats[0]
    else:
        cid = known[0]

    meta = CAT_META[cid]
    return {"id": cid, "name": meta["name"], "slug": meta["slug"], "group": meta["group"]}


def get_posts(cat_ids):
    seen = {}
    for cat_id in cat_ids:
        page = 1
        while True:
            url = (
                f"{BASE}/posts?categories={cat_id}&per_page=100&page={page}"
                "&_fields=id,title,link,content,categories"
            )
            batch = json.loads(fetch(url))
            if not batch:
                break
            for post in batch:
                seen[post["id"]] = post
            if len(batch) < 100:
                break
            page += 1
            time.sleep(0.2)
    return list(seen.values())


def build_item(post, tour_ids, loc_ids):
    title = strip_tags(post["title"]["rendered"])
    url = post["link"]
    content = post.get("content", {}).get("rendered", "")
    category_ids = post.get("categories", [])

    lat, lng = parse_coords(content)
    page_html = content
    if lat is None:
        try:
            time.sleep(0.12)
            page_html = fetch(url)
            lat, lng = parse_coords(page_html)
        except Exception as exc:
            print(f"WARN {url}: {exc}")
            page_html = content

    if lat is None and page_html:
        try:
            time.sleep(0.12)
            hy_url = hy_url_from_page(page_html, url)
            if hy_url != url:
                hy_html = fetch(hy_url)
                lat, lng = parse_coords(hy_html)
                if lat is not None:
                    page_html = hy_html
        except Exception as exc:
            print(f"WARN hy {url}: {exc}")

    if lat is not None:
        content = page_html

    if post["id"] in tour_ids and post["id"] in loc_ids:
        kind = "both"
    elif post["id"] in loc_ids:
        kind = "location"
    else:
        kind = "tour"

    cat = pick_category(category_ids, kind)
    raw = None
    if lat is not None:
        m = re.search(
            r"(?:Coordinates?|Կոորդինատները?)\s*[:՝\-]+\s*.{5,50}",
            strip_tags(content),
            re.I,
        )
        raw = m.group(0).split(":", 1)[-1].strip() if m else f"{lat}, {lng}"

    return {
        "title": title,
        "url": url,
        "type": kind,
        "category": cat["name"],
        "categorySlug": cat["slug"],
        "region": extract_location(content),
        "coordinatesRaw": raw,
        "lat": lat,
        "lng": lng,
    }


def group_items(items):
    buckets = {}
    for item in items:
        key = (item["type"], item["category"])
        buckets.setdefault(key, []).append(item)

    def sort_key(key):
        kind, cat_name = key
        kind_order = {"location": 0, "both": 1, "tour": 2}.get(kind, 9)
        loc_order = GROUP_ORDER["location"]
        if kind == "location" and cat_name in loc_order:
            cat_order = loc_order.index(cat_name)
        elif kind == "location":
            cat_order = 99
        else:
            cat_order = 0
        return (kind_order, cat_order, cat_name.lower())

    groups = []
    for (kind, cat_name) in sorted(buckets.keys(), key=sort_key):
        group_items_list = sorted(buckets[(kind, cat_name)], key=lambda x: x["title"].lower())
        with_coords = sum(1 for x in group_items_list if x["lat"] is not None)
        groups.append({
            "type": kind,
            "category": cat_name,
            "categorySlug": group_items_list[0]["categorySlug"],
            "count": len(group_items_list),
            "withCoordinates": with_coords,
            "items": group_items_list,
        })
    return groups


def build_output(items):
    with_coords = sum(1 for x in items if x["lat"] is not None)
    by_type = {}
    for item in items:
        by_type[item["type"]] = by_type.get(item["type"], 0) + 1

    return {
        "source": "https://www.armgeo.am/en/",
        "summary": {
            "total": len(items),
            "withCoordinates": with_coords,
            "byType": by_type,
            "groupCount": len(group_items(items)),
        },
        "groups": group_items(items),
    }


def flatten_existing(data):
    flat = data.get("locations") or []
    for group in data.get("groups", []):
        flat.extend(group.get("items", []))
    return flat


def regroup_existing(path="locations.json"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    flat = flatten_existing(data)
    print("Loading category map from API...")
    posts = get_posts(TOUR_CAT_IDS + LOC_CAT_IDS)
    cats_by_url = {p["link"]: p.get("categories", []) for p in posts}

    items = []
    for item in flat:
        kind = item.get("type", "tour")
        cat_ids = cats_by_url.get(item["url"], [])
        cat = pick_category(cat_ids, kind)
        items.append({
            "title": item["title"],
            "url": item["url"],
            "type": kind,
            "category": cat["name"],
            "categorySlug": cat["slug"],
            "region": item.get("region") or item.get("location"),
            "coordinatesRaw": item.get("coordinatesRaw"),
            "lat": item.get("lat"),
            "lng": item.get("lng"),
        })

    return build_output(items)


def print_summary(out):
    print(json.dumps(out["summary"], indent=2))
    print("groups:")
    for g in out["groups"]:
        print(f"  [{g['type']}] {g['category']}: {g['count']} ({g['withCoordinates']} with coords)")


def write_viewer(out, path="index.html"):
    from build_viewer import build_html
    build_html(out, path)
    print(f"Wrote {path}")


def extract_all():
    tours = get_posts(TOUR_CAT_IDS)
    locations = get_posts(LOC_CAT_IDS)
    tour_ids = {p["id"] for p in tours}
    loc_ids = {p["id"] for p in locations}
    all_posts = {p["id"]: p for p in tours + locations}

    items = []
    for i, post in enumerate(all_posts.values()):
        items.append(build_item(post, tour_ids, loc_ids))
        if (i + 1) % 50 == 0:
            print(f"processed {i + 1}/{len(all_posts)}")

    return build_output(items)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract and group armgeo.am locations")
    parser.add_argument(
        "--group-only",
        action="store_true",
        help="Re-group existing locations.json without re-scraping (fast)",
    )
    parser.add_argument(
        "-o", "--output", default="locations.json", help="Output file path"
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip generating index.html viewer",
    )
    args = parser.parse_args()

    if args.group_only:
        out = regroup_existing(args.output)
    else:
        out = extract_all()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print_summary(out)

    if not args.no_html:
        html_path = "index.html" if args.output == "locations.json" else args.output.replace(".json", ".html")
        write_viewer(out, html_path)


if __name__ == "__main__":
    main()
