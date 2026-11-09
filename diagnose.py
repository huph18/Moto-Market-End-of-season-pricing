"""Find out which search filter is shrinking the result counts.

Runs a few searches with filters removed one at a time and prints eBay's
reported `total` for each. Uses about 15 API calls. Saves nothing.

    python diagnose.py
"""

import os
from collections import Counter

from dotenv import load_dotenv

import config
from collect import ROOT, PoliteClient

QUERIES = ["yamaha r1", "aprilia rsv4"]
COND = f"conditionIds:{{{config.USED_CONDITION_ID}}}"
COUNTRY = "itemLocationCountry:US"

VARIANTS = {
    "current (cat + used + US)": {"category_ids": config.CATEGORY_ID, "filter": f"{COND},{COUNTRY}"},
    "no condition filter":       {"category_ids": config.CATEGORY_ID, "filter": COUNTRY},
    "no country filter":         {"category_ids": config.CATEGORY_ID, "filter": COND},
    "category only":             {"category_ids": config.CATEGORY_ID},
    "keyword only":              {},
}


def main():
    load_dotenv(ROOT / ".env")
    client = PoliteClient(os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"],
                          os.environ["CONTACT_EMAIL"])
    for q in QUERIES:
        print(f"\n=== {q} ===")
        for label, params in VARIANTS.items():
            body = client.get(config.SEARCH_URL, params={"q": q, "limit": 50, **params})
            items = body.get("itemSummaries") or []
            opts = Counter(o for i in items for o in i.get("buyingOptions", []))
            cats = Counter(i.get("categories", [{}])[0].get("categoryName", "?") for i in items)
            print(f"{label:28s} total={body.get('total', 0):>6}   "
                  f"buying={dict(opts)}   top categories={cats.most_common(2)}")
    print(f"\n{client.calls} API calls used")


if __name__ == "__main__":
    main()
