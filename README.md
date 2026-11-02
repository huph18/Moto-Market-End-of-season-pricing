# Moto Market Research: End-of-Season Sportbike Pricing

*INFO 4617 · Huy Phan · CU Boulder*

## Research Question

Do asking prices for used sportbikes on eBay Motors drop as riding season ends (late October to mid-December 2026), and is that drop bigger for sellers in snow states than for sellers in warm states? Riders often say "wait until winter, people dump their bikes," but it's rarely checked against real data. This project tests that claim by collecting a daily snapshot of active eBay Motors listings for about 12 popular sportbike models from Oct 27 to Dec 13, 2026, through the official eBay Browse API. I then compare price trends, same-listing price cuts, supply, and time-to-delisting between a pre-registered set of snow states (e.g., CO, MN, MI, NY) and warm states (e.g., FL, AZ, TX, southern CA). I expect snow-state prices to fall roughly 3–8% by mid-December while warm-state prices hold steady; finding no regional difference, or rising prices, would be just as informative.

## Data

<!-- TODO: Describe the final dataset once collection is complete. -->

- **Source:** eBay Browse API (`item_summary/search` and `item/{item_id}`), marketplace `EBAY_MOTORS_US`, Motorcycles category
- **Collection window:** _TBD_
- **Snapshots collected:** _TBD_
- **Unique listings / listing-days:** _TBD_
- **Models covered:** _TBD_
- **Fields retained:** _TBD_
- **Snow vs. warm state definitions:** _TBD (link to pre-registered list)_
- **Privacy handling:** _TBD (seller info dropped at ingest, postal code → state, aggregates only)_
- **Known gaps / missed runs:** _TBD_

## Methods

<!-- TODO: Fill in details and any deviations from the proposal. -->

1. **Weekly median asking price by region** — _TBD_
2. **Same-listing price cuts** — _TBD_
3. **Supply over time** — _TBD_
4. **Time until delisting** — _TBD_
5. **Regression** (log price ~ model + year + mileage + region + week + region × week) — _TBD_

**Limitations:** _TBD_

## Findings

<!-- TODO: Add results, charts, and interpretation after analysis. -->

_TBD_

## How to Reproduce

<!-- TODO: Confirm commands and file names before submission. -->

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd <repo-name>
   ```
2. **Set up the environment** — _TBD (Python version, `requirements.txt`)_
3. **Configure credentials** — _TBD (`.env` with eBay app keys; never committed)_
4. **Set up the database** — _TBD (PostgreSQL schema / migration steps)_
5. **Run the daily collector** — _TBD (script name, scheduling)_
6. **Run the analysis** — _TBD (notebook or script, expected outputs)_

> Note: Raw listing data is deleted after analysis per the eBay API License Agreement; only weekly aggregates are kept in this repo.
