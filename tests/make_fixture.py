"""Build a SYNTHETIC raw-data fixture for testing clean.py offline.

Nothing here is real eBay data. It mimics the shape of what collect.py writes
so the cleaning step can be tested without API access. It includes deliberate
edge cases: duplicates, auction-only, non-USD, a parts bike, a wrong-model
title, outlier prices, an impossible model year, a listing that cuts its
price, and one that gets delisted.

    python tests/make_fixture.py   # writes tests/fixtures/raw/
"""

import datetime as dt
import gzip
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures" / "raw"

BASE = [  # (id, query, title, price, state, region, listed)
    ("v1|1001|0", "yamaha r1", "2019 Yamaha YZF-R1 low miles", 13500, "CO", "snow", "2026-10-01"),
    ("v1|1002|0", "yamaha r1", "2015 Yamaha R1 12,400 miles", 9800, "FL", "warm", "2026-10-10"),
    ("v1|1003|0", "yamaha r6", "2017 Yamaha YZF-R6 track ready", 8900, "MN", "snow", "2026-09-20"),
    ("v1|1004|0", "kawasaki zx-6r", "2020 Kawasaki Ninja ZX-6R 636", 8700, "AZ", "warm", "2026-10-20"),
    ("v1|1005|0", "bmw s1000rr", "2021 BMW S1000RR M package 4k miles", 19900, "NY", "snow", "2026-10-05"),
    ("v1|1006|0", "aprilia rsv4", "Aprilia RSV4 RR", 14200, "TX", "warm", "2026-10-15"),
    ("v1|1007|0", "honda cbr600rr", "2013 Honda CBR600RR", 6400, "OH", "other", "2026-10-12"),
    # edge cases that should be removed
    ("v1|2001|0", "yamaha r1", "2008 Yamaha R1 for parts", 2500, "MI", "snow", "2026-10-01"),
    ("v1|2002|0", "yamaha r1", "2018 Yamaha R6 clean title", 9000, "CO", "snow", "2026-10-01"),
    ("v1|2003|0", "suzuki gsx-r600", "2011 Suzuki GSX-R600", 450, "FL", "warm", "2026-10-01"),
    ("v1|2004|0", "ducati panigale v2", "2021 Ducati Panigale V2", 999999, "TX", "warm", "2026-10-01"),
]
CUTTER = "v1|1001|0"      # cuts its price from day 3 on
DELISTED = "v1|1002|0"    # disappears after day 2


def row(item_id, query, title, price, state, region, listed, day,
        buying=("FIXED_PRICE",), currency="USD"):
    return {
        "itemId": item_id, "title": title, "condition": "Used",
        "conditionId": "3000", "buyingOptions": list(buying),
        "itemCreationDate": f"{listed}T12:00:00.000Z",
        "price_value": str(price), "price_currency": currency,
        "current_bid_value": None, "country": "US",
        "state": state, "region": region, "query": query, "snapshot_date": day,
    }


def main():
    snaps = OUT / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    start = dt.date(2026, 10, 27)
    for d in range(4):
        day = (start + dt.timedelta(days=d)).isoformat()
        rows = []
        for item_id, q, title, price, state, region, listed in BASE:
            if item_id == DELISTED and d >= 2:
                continue
            if item_id == CUTTER and d >= 2:
                price = 12900
            rows.append(row(item_id, q, title, price, state, region, listed, day))
        rows.append(dict(rows[0]))  # duplicate listing-day
        rows.append(row("v1|3001|0", "yamaha r7", "2022 Yamaha R7", 7500,
                        "CA", "warm", "2026-10-25", day, buying=("AUCTION",)))
        rows.append(row("v1|3002|0", "kawasaki zx-10r", "2016 Kawasaki ZX-10R", 9000,
                        "WA", "other", "2026-10-25", day, currency="CAD"))
        with gzip.open(snaps / f"{day}.jsonl.gz", "wt") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    details = [
        {"itemId": "v1|1001|0", "year": "2019", "mileage": "6,200", "make": "Yamaha", "model": "YZF-R1"},
        {"itemId": "v1|1003|0", "year": "2017", "mileage": "18000", "make": "Yamaha", "model": "YZF-R6"},
        {"itemId": "v1|1006|0", "year": "1999", "mileage": "3100", "make": "Aprilia", "model": "RSV4"},
    ]
    with (OUT / "details.jsonl").open("w") as f:
        for r in details:
            f.write(json.dumps(r) + "\n")
    print(f"wrote synthetic fixture to {OUT}")


if __name__ == "__main__":
    main()
