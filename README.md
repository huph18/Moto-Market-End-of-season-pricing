# Moto Market Research: End-of-Season Sportbike Pricing

*INFO 4617 · Huy Phan · CU Boulder*

## Research Question

Do asking prices for used sportbikes on eBay Motors drop as riding season ends (late October to mid-December 2026), and is that drop bigger for sellers in snow states than for sellers in warm states? Riders often say "wait until winter, people dump their bikes," but it's rarely checked against real data. This project tests that claim by collecting a daily snapshot of active eBay Motors listings for about 12 popular sportbike models from Oct 27 to Dec 13, 2026, through the official eBay Browse API. I then compare price trends, same-listing price cuts, supply, and time-to-delisting between a pre-registered set of snow states (e.g., CO, MN, MI, NY) and warm states (e.g., FL, AZ, TX, southern CA). I expect snow-state prices to fall roughly 3–8% by mid-December while warm-state prices hold steady; finding no regional difference, or rising prices, would be just as informative.

## Data

### Source

- **eBay Browse API**, accessed with my own registered developer app (OAuth2 client-credentials flow). No web scraping; eBay's `robots.txt` disallows crawling listing pages, so everything goes through the documented API.
  - `GET /buy/browse/v1/item_summary/search`: active listings per model (category 6024 Motorcycles, condition Used, located in the US)
  - `GET /buy/browse/v1/item/{item_id}`: model year and mileage, called once per new listing
  - Marketplace header `X-EBAY-C-MARKETPLACE-ID: EBAY_MOTORS_US`
- **Models (12):** Yamaha R1, R6, R7; Honda CBR600RR, CBR1000RR; Kawasaki ZX-6R, ZX-10R; Suzuki GSX-R600, GSX-R750; Ducati Panigale V2; BMW S1000RR; Aprilia RSV4

### Collection

- **Window:** Oct 27 – Dec 13, 2026, one snapshot per day (`collect.py`, run daily by cron)
- **Snapshots collected:** **[fill from `output/cleaning_report.txt`]**; missed days are listed in that report and in `data/logs/runs.csv`
- **Records:**
  - Raw listing-days: **[fill]**
  - Clean listing-days: **[fill]**
  - Unique listings: **[fill]** (snow **[ ]**, warm **[ ]**, other **[ ]**)
- **Polite requests:** a User-Agent naming the project and a contact address; at least 1 second between calls; exponential backoff on HTTP 429/5xx (honoring `Retry-After`); a hard cap of 300 calls per run; detail calls only for listings not seen before.

### Cleaning

`clean.py` turns the daily snapshots into a tidy table with one row per listing per day. It keeps fixed-price US listings in USD, drops parts bikes and salvage, requires the title to match the model searched, keeps prices from $1,500 to $60,000, parses model year and mileage, and computes price changes between snapshots. The row count after each step is written to [`output/cleaning_report.txt`](output/cleaning_report.txt). Every field is defined in [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md).

### What's in this repo

| Path | What it is |
|---|---|
| `data/sample/listing_days_sample.csv` | De-identified sample: every snapshot row for 50 randomly chosen listings (seed 4617) |
| `data/DATA_DICTIONARY.md` | Each field, its type, and its meaning; the region definitions; the cleaning rules |
| `output/cleaning_report.txt` | Output of the cleaning step, with counts at each stage |

### What isn't in this repo, and why

| Left out | Why |
|---|---|
| **Full raw snapshots** (`data/raw/`) | **Terms of service.** The eBay API License Agreement allows copies of API data only as long as needed and requires deleting data for listings that are no longer public (§3.1(b), §8.1(b)(1)). It also restricts deriving and redistributing pricing data (§8.1(d)(i), §9.3). Redistributing the full dataset would go beyond academic analysis. The raw files are deleted after the analysis is done. |
| **Full cleaned tables** (`data/clean/`) | Same terms-of-service reasons. They also contain eBay item IDs and listing titles, which point back to specific sellers' listings. |
| **Listing titles and eBay item IDs** (also removed from the sample) | **Privacy.** A title or item ID leads straight to a seller's live listing. The sample uses a salted hash in place of the ID, has no titles, and rounds mileage to the nearest 500. |
| **Seller usernames, feedback, photos, listing URLs, postal codes** | **Privacy.** Never written to disk at all. `collect.py` keeps only a whitelist of fields, and the masked postal code is converted to a state and discarded at ingest. |
| **API keys** (`.env`) | **Security.** Credentials live in a git-ignored `.env`; `.env.example` shows the required variables. |
| Run logs (`data/logs/`) | Operational only; missed days are summarized in the cleaning report instead. |

*Size isn't the main reason for these exclusions. The full data is roughly 70k–140k listing-days, which is only a few MB compressed.*

**Sample caveat:** the proposal said no individual listings would be published. The sample is a compromise required by the assignment: it has no titles, IDs, or seller information, and it covers only 50 listings. I asked eBay developer support for written permission for academic use. If they decline, I will remove the sample and keep only aggregates.

## Methods

<!-- TODO: Fill in details and any deviations from the proposal. -->

1. **Weekly median asking price by region** — _TBD_
2. **Same-listing price cuts** — _TBD_
3. **Supply over time** — _TBD_
4. **Time until delisting** — _TBD_
5. **Regression** (log price ~ model + year + mileage + region + week + region × week) — _TBD_

**Deviation from proposal:** raw snapshots are stored as compressed JSON Lines files rather than in PostgreSQL. Anyone can reproduce the pipeline without setting up a database.

**Limitations:** _TBD_

## Findings

<!-- TODO: Add results, charts, and interpretation after analysis. -->

_TBD_

## How to Reproduce

1. **Clone the repo and install dependencies** (Python 3.10+)
   ```bash
   git clone <repo-url>
   cd moto-market-research
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Check the pipeline offline** (no eBay account needed). This builds a small synthetic fixture and tests the privacy filter, regions, cleaning rules, and price-cut logic:
   ```bash
   python tests/make_fixture.py
   python -m pytest -q tests
   ```
3. **Add credentials:** copy `.env.example` to `.env` and fill in your eBay app ID and secret, a contact email, and a random `SAMPLE_SALT`.
4. **Collect daily.** Run once by hand, then schedule it:
   ```bash
   python collect.py
   # cron: 17 6 * * *  cd /path/to/moto-market-research && .venv/bin/python collect.py
   ```
5. **Clean.** This writes `data/clean/`, `data/sample/`, and `output/cleaning_report.txt`:
   ```bash
   python clean.py
   ```
6. **Analyze:** _TBD (notebook or script, expected outputs)_

> Because the raw data can't be shared (see "What isn't in this repo"), exact numbers can only be reproduced by collecting your own snapshots over the same window. The code, the cleaning report, and the sample let a reader check every step of the method.
