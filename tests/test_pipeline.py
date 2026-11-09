"""Offline tests for geo.py and clean.py using the synthetic fixture.

    python tests/make_fixture.py && python -m pytest -q tests
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import clean  # noqa: E402
from collect import sanitize_summary  # noqa: E402
from geo import locate  # noqa: E402

RAW = ROOT / "tests" / "fixtures" / "raw"


def run():
    raw = clean.load_snapshots(RAW)
    tidy, steps = clean.clean(raw, clean.load_details(RAW))
    return tidy, steps


def test_geo_regions():
    assert locate("802**") == ("CO", "snow")
    assert locate("331**") == ("FL", "warm")
    assert locate("921**") == ("CA", "warm")    # San Diego: southern CA
    assert locate("941**") == ("CA", "other")   # San Francisco: not southern CA
    assert locate("441**") == ("OH", "other")
    assert locate(None) == (None, "unknown")


def test_ingest_drops_personal_fields():
    item = {
        "itemId": "v1|1|0", "title": "2019 Yamaha R1", "price": {"value": "1", "currency": "USD"},
        "seller": {"username": "someone", "feedbackScore": 99},
        "image": {"imageUrl": "https://example.com/x.jpg"},
        "itemWebUrl": "https://example.com/item",
        "itemLocation": {"postalCode": "802**", "country": "US"},
    }
    out = sanitize_summary(item, "yamaha r1", "2026-11-01")
    assert "seller" not in out and "image" not in out and "itemWebUrl" not in out
    assert "postalCode" not in str(out) and "802" not in str(out)
    assert out["state"] == "CO" and out["region"] == "snow"


def test_only_valid_listings_survive():
    tidy, _ = run()
    assert set(tidy["item_id"]) == {f"v1|100{i}|0" for i in range(1, 8)}
    assert not tidy.duplicated(["item_id", "snapshot_date"]).any()


def test_price_cut_and_delisting():
    tidy, _ = run()
    cutter = tidy[tidy["item_id"] == "v1|1001|0"].sort_values("snapshot_date")
    assert cutter["price_cut"].tolist() == [False, False, True, False]
    listings = clean.summarize_listings(tidy)
    delisted = listings.set_index("item_id")["delisted"]
    assert delisted["v1|1002|0"] and not delisted["v1|1001|0"]


def test_year_and_mileage_parsing():
    tidy, _ = run()
    first = tidy.drop_duplicates("item_id").set_index("item_id")
    assert first.loc["v1|1001|0", "mileage"] == 6200          # from item details
    assert first.loc["v1|1002|0", "mileage"] == 12400         # from title
    assert first.loc["v1|1005|0", "mileage"] == 4000          # "4k miles"
    assert pd.isna(first.loc["v1|1006|0", "model_year"])      # 1999 RSV4 is impossible


def test_sample_is_deidentified():
    tidy, _ = run()
    sample = clean.make_sample(tidy, salt="test")
    assert "title" not in sample.columns and "item_id" not in sample.columns
    assert sample["listing_id"].str.len().eq(12).all()
    assert (sample["mileage"].dropna() % 500 == 0).all()
