"""Turn raw daily snapshots into a tidy, analysis-ready dataset.

Input  (git-ignored):  data/raw/snapshots/*.jsonl.gz, data/raw/details.jsonl
Output (git-ignored):  data/clean/listing_days.csv   one row per listing per snapshot
                       data/clean/listings.csv       one row per listing
Output (committed):    data/sample/listing_days_sample.csv   de-identified sample
                       output/cleaning_report.txt            step-by-step counts

Usage:
    python clean.py                       # uses data/raw
    python clean.py --raw tests/fixtures/raw --out /tmp/check   # test run
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

import config

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Rules (documented in data/DATA_DICTIONARY.md)
# ---------------------------------------------------------------------------
PRICE_MIN, PRICE_MAX = 1_500, 60_000       # below = parts/scams, above = typos
MILEAGE_MAX = 150_000
SAMPLE_LISTINGS = 50
SAMPLE_SEED = 4617

# Title patterns that identify each model. The listing is kept only if its
# title matches the model it was searched for (and no other model).
MODEL_PATTERNS = {
    "Yamaha R1":          r"\b(?:yzf[\s-]?)?r1m?\b",
    "Yamaha R6":          r"\b(?:yzf[\s-]?)?r6s?\b",
    "Yamaha R7":          r"\b(?:yzf[\s-]?)?r7\b",
    "Honda CBR600RR":     r"\bcbr[\s-]?600[\s-]?rr\b",
    "Honda CBR1000RR":    r"\bcbr[\s-]?1000[\s-]?rr(?:-?r)?\b",
    "Kawasaki ZX-6R":     r"\bzx[\s-]?6r\b|\bzx[\s-]?636\b|\bninja\s?636\b",
    "Kawasaki ZX-10R":    r"\bzx[\s-]?10rr?\b",
    "Suzuki GSX-R600":    r"\bgsx[\s-]?r[\s-]?600\b",
    "Suzuki GSX-R750":    r"\bgsx[\s-]?r[\s-]?750\b",
    "Ducati Panigale V2": r"\bpanigale\s?v2\b",
    "BMW S1000RR":        r"\bs[\s-]?1000[\s-]?rr\b",
    "Aprilia RSV4":       r"\brsv[\s-]?4\b",
}
# First model year sold in the US; earlier parsed years are treated as errors.
FIRST_MODEL_YEAR = {
    "Yamaha R1": 1998, "Yamaha R6": 1999, "Yamaha R7": 2021,
    "Honda CBR600RR": 2003, "Honda CBR1000RR": 2004,
    "Kawasaki ZX-6R": 1995, "Kawasaki ZX-10R": 2004,
    "Suzuki GSX-R600": 1997, "Suzuki GSX-R750": 1985,
    "Ducati Panigale V2": 2020, "BMW S1000RR": 2010, "Aprilia RSV4": 2009,
}
# Category 6024 already limits results to whole vehicles, so this only catches
# listings that are not a rideable bike. Words like "exhaust" or "wheels" are
# NOT excluded: real bike titles often list upgrades ("full Akrapovic exhaust").
NOT_A_BIKE = re.compile(
    r"\b(?:for\sparts|parts?\s(?:bike|only)|project\sbike|engine\sonly|motor\sonly|"
    r"frame\sonly|title\sonly|no\stitle|salvage|rolling\schassis|"
    r"diecast|die-cast|1:12|toy|model\skit)\b",
    re.I,
)
YEAR_RE = re.compile(r"\b(19[89]\d|20[0-2]\d)\b")
MILES_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+(?:\.\d)?)\s?(k)?\s?(?:mi|miles)\b", re.I)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_snapshots(raw_dir):
    frames = []
    for path in sorted((raw_dir / "snapshots").glob("*.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            frames.append(pd.DataFrame(json.loads(l) for l in f if l.strip()))
    if not frames:
        raise SystemExit(f"No snapshots found in {raw_dir / 'snapshots'}")
    return pd.concat(frames, ignore_index=True)


def load_details(raw_dir):
    path = raw_dir / "details.jsonl"
    if not path.exists():
        return pd.DataFrame(columns=["itemId", "year", "mileage"])
    with path.open() as f:
        d = pd.DataFrame(json.loads(l) for l in f if l.strip())
    return d.drop_duplicates("itemId", keep="last")


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------
def match_model(title):
    t = str(title).lower()
    hits = [m for m, pat in MODEL_PATTERNS.items() if re.search(pat, t)]
    return hits[0] if len(hits) == 1 else None


def parse_year(value):
    m = YEAR_RE.search(str(value)) if pd.notna(value) else None
    return int(m.group(1)) if m else np.nan


def parse_mileage_aspect(value):
    if pd.isna(value):
        return np.nan
    digits = re.sub(r"[^\d]", "", str(value))
    return float(digits) if digits else np.nan


def parse_mileage_title(title):
    m = MILES_RE.search(str(title))
    if not m:
        return np.nan
    n = float(m.group(1).replace(",", ""))
    return n * 1000 if m.group(2) else n


# ---------------------------------------------------------------------------
# Cleaning pipeline
# ---------------------------------------------------------------------------
def clean(raw, details):
    steps = []

    def record(label, frame):
        steps.append((label, len(frame)))
        return frame

    df = record("raw listing-days loaded", raw.copy())

    df = df.drop_duplicates(["itemId", "snapshot_date"])
    df = record("after removing duplicate listing-days", df)

    df = df[(df["price_currency"] == "USD") & (df["country"] == "US")]
    df = record("after keeping US listings priced in USD", df)

    opts = df["buyingOptions"].apply(lambda o: o if isinstance(o, list) else [])
    df = df[opts.apply(lambda o: "FIXED_PRICE" in o)]
    df = record("after dropping auction-only listings (bid, not asking price)", df)

    df = df[~df["title"].str.contains(NOT_A_BIKE, na=False)]
    df = record("after dropping non-rideable listings (parts bikes, salvage, toys)", df)

    df["model"] = df["title"].apply(match_model)
    searched = df["query"].map(lambda q: config.MODELS[q]["model"])
    df = df[df["model"].notna() & (df["model"] == searched)]
    df = record("after requiring title to match the searched model", df)

    df["asking_price"] = pd.to_numeric(df["price_value"], errors="coerce")
    df = df[df["asking_price"].between(PRICE_MIN, PRICE_MAX)]
    df = record(f"after keeping prices ${PRICE_MIN:,}-${PRICE_MAX:,}", df)

    # Year and mileage: item-detail aspects first, title as fallback.
    df = df.merge(details[["itemId", "year", "mileage"]].rename(
        columns={"year": "year_aspect", "mileage": "mileage_aspect"}),
        on="itemId", how="left")
    df["model_year"] = df["year_aspect"].apply(parse_year)
    df["model_year"] = df["model_year"].fillna(df["title"].apply(parse_year))
    first_year = df["model"].map(FIRST_MODEL_YEAR)
    bad_year = (df["model_year"] < first_year) | (df["model_year"] > 2027)
    df.loc[bad_year, "model_year"] = np.nan

    df["mileage"] = df["mileage_aspect"].apply(parse_mileage_aspect)
    df["mileage"] = df["mileage"].fillna(df["title"].apply(parse_mileage_title))
    df.loc[df["mileage"] > MILEAGE_MAX, "mileage"] = np.nan

    # Derived fields
    df["cc_class"] = df["query"].map(lambda q: config.MODELS[q]["cc_class"])
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df["week_start"] = (df["snapshot_date"]
                        - pd.to_timedelta(df["snapshot_date"].dt.day_of_week, unit="D"))
    df["listed_date"] = pd.to_datetime(df["itemCreationDate"], utc=True,
                                       errors="coerce").dt.tz_localize(None).dt.normalize()

    df = df.sort_values(["itemId", "snapshot_date"])
    g = df.groupby("itemId")["asking_price"]
    df["prev_price"] = g.shift(1)
    df["price_change_pct"] = (df["asking_price"] / df["prev_price"] - 1) * 100
    df["price_cut"] = df["price_change_pct"] < 0

    tidy = df[[
        "itemId", "snapshot_date", "week_start", "model", "cc_class",
        "model_year", "mileage", "asking_price", "prev_price",
        "price_change_pct", "price_cut", "state", "region", "listed_date",
        "title",
    ]].rename(columns={"itemId": "item_id"}).reset_index(drop=True)
    tidy["model_year"] = tidy["model_year"].astype("Int64")
    tidy["mileage"] = tidy["mileage"].round().astype("Int64")
    return tidy, steps


def summarize_listings(tidy):
    last_snapshot = tidy["snapshot_date"].max()
    g = tidy.groupby("item_id")
    listings = g.agg(
        model=("model", "first"), cc_class=("cc_class", "first"),
        model_year=("model_year", "first"), mileage=("mileage", "first"),
        state=("state", "first"), region=("region", "first"),
        listed_date=("listed_date", "first"),
        first_seen=("snapshot_date", "min"), last_seen=("snapshot_date", "max"),
        snapshots_seen=("snapshot_date", "nunique"),
        first_price=("asking_price", "first"), last_price=("asking_price", "last"),
        n_price_cuts=("price_cut", "sum"),
    ).reset_index()
    listings["total_change_pct"] = (listings["last_price"]
                                    / listings["first_price"] - 1) * 100
    listings["delisted"] = listings["last_seen"] < last_snapshot
    listings["days_observed"] = (listings["last_seen"] - listings["first_seen"]).dt.days + 1
    return listings


def make_sample(tidy, salt):
    """De-identified sample: hashed IDs, no titles, rounded mileage."""
    rng = np.random.default_rng(SAMPLE_SEED)
    ids = tidy["item_id"].unique()
    chosen = rng.choice(ids, size=min(SAMPLE_LISTINGS, len(ids)), replace=False)
    s = tidy[tidy["item_id"].isin(chosen)].drop(columns=["title"]).copy()
    s.insert(0, "listing_id", s.pop("item_id").map(
        lambda i: hashlib.sha256(f"{salt}{i}".encode()).hexdigest()[:12]))
    s["mileage"] = (s["mileage"] / 500).round().astype("Int64") * 500
    return s.sort_values(["listing_id", "snapshot_date"])


def write_report(path, steps, tidy, listings, raw):
    dates = sorted(tidy["snapshot_date"].dt.date.unique())
    expected = pd.date_range(raw["snapshot_date"].min(), raw["snapshot_date"].max())
    missing = sorted(set(expected.date) - set(pd.to_datetime(raw["snapshot_date"]).dt.date))
    lines = ["CLEANING REPORT", "=" * 60, "", "Row counts by step (listing-days):"]
    prev = None
    for label, n in steps:
        drop = "" if prev is None else f"   (-{prev - n:,})"
        lines.append(f"  {n:>9,}  {label}{drop}")
        prev = n
    lines += [
        "",
        f"Snapshots:            {len(dates)} ({dates[0]} to {dates[-1]})",
        f"Missing snapshot days: {', '.join(map(str, missing)) or 'none'}",
        f"Unique listings:      {tidy['item_id'].nunique():,}",
        f"Listing-days:         {len(tidy):,}",
        f"Model year known:     {tidy['model_year'].notna().mean():.0%} of listing-days",
        f"Mileage known:        {tidy['mileage'].notna().mean():.0%} of listing-days",
        f"Listing-days with a price cut: {int(tidy['price_cut'].sum()):,}",
        "",
        "Unique listings by region:",
        listings["region"].value_counts().to_string(),
        "",
        "Unique listings by model and region:",
        pd.crosstab(listings["model"], listings["region"], margins=True).to_string(),
        "",
    ]
    path.write_text("\n".join(lines))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT,
                    help="project root to write data/clean, data/sample, output/ under")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    salt = os.environ.get("SAMPLE_SALT")
    if not salt:
        salt = secrets.token_hex(16)
        print("note: SAMPLE_SALT not set; sample IDs will change each run\n")

    raw = load_snapshots(args.raw)
    tidy, steps = clean(raw, load_details(args.raw))
    listings = summarize_listings(tidy)

    for sub in ("data/clean", "data/sample", "output"):
        (args.out / sub).mkdir(parents=True, exist_ok=True)
    tidy.to_csv(args.out / "data/clean/listing_days.csv", index=False)
    listings.to_csv(args.out / "data/clean/listings.csv", index=False)
    make_sample(tidy, salt).to_csv(
        args.out / "data/sample/listing_days_sample.csv", index=False)
    print(write_report(args.out / "output/cleaning_report.txt",
                       steps, tidy, listings, raw))


if __name__ == "__main__":
    main()
