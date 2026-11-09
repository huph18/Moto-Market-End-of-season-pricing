# Data Dictionary

Produced by `clean.py`. One row = one listing on one snapshot day ("listing-day").

| File | In repo? | Rows |
|---|---|---|
| `data/clean/listing_days.csv` | No (git-ignored) | One per listing per snapshot |
| `data/clean/listings.csv` | No (git-ignored) | One per unique listing |
| `data/sample/listing_days_sample.csv` | **Yes** | All snapshot rows for 50 randomly chosen listings (seed 4617), de-identified |

## `listing_days` (and the sample)

| Field | Type | Meaning |
|---|---|---|
| `item_id` | string | eBay item ID. **Full dataset only.** In the sample it is replaced by `listing_id`. |
| `listing_id` | string | **Sample only.** First 12 hex characters of SHA-256(salt + item_id). Stable within a run; cannot be linked back to an eBay listing without the private salt. |
| `snapshot_date` | date | Day the listing was observed as active (America/Denver date of the collection run). |
| `week_start` | date | Monday of the week containing `snapshot_date`. Weekly analyses group on this. |
| `model` | string | Canonical model, one of 12 (e.g. `Yamaha R1`). Assigned from the title and required to match the model that was searched. |
| `cc_class` | string | `600cc` or `1000cc`. GSX-R750 is grouped with 600cc; Panigale V2 (955cc) with 1000cc. |
| `model_year` | integer, nullable | Model year. From eBay's "Year" item aspect, else the first 4-digit year in the title. Blank if missing or earlier than the model's first US year (e.g. a "1999" RSV4). |
| `mileage` | integer, nullable | Odometer miles. From eBay's "Mileage" aspect, else parsed from the title ("12,400 miles", "4k mi"). Blank if missing or over 150,000. **Rounded to the nearest 500 in the sample.** |
| `asking_price` | float (USD) | Fixed "Buy It Now" asking price that day. Not a sale price. |
| `prev_price` | float (USD), nullable | Same listing's `asking_price` on its previous snapshot. Blank on its first snapshot. |
| `price_change_pct` | float, nullable | `(asking_price / prev_price − 1) × 100`. |
| `price_cut` | boolean | True if the price fell since the previous snapshot. |
| `state` | string | Two-letter US state, derived from the first three digits of eBay's masked postal code. The postal code itself is never stored. |
| `region` | string | Pre-registered group: `snow`, `warm`, `other`, or `unknown`. See `config.py`. |
| `listed_date` | date | Date the seller created the listing (eBay `itemCreationDate`). |
| `title` | string | Listing title. **Full dataset only**; used for parsing, never published. |

## `listings` (one row per listing)

| Field | Meaning |
|---|---|
| `item_id`, `model`, `cc_class`, `model_year`, `mileage`, `state`, `region`, `listed_date` | As above, taken from the listing's first snapshot. |
| `first_seen` / `last_seen` | First and last snapshot dates the listing appeared. |
| `snapshots_seen` | Number of snapshots it appeared in. |
| `days_observed` | `last_seen − first_seen + 1`. |
| `first_price` / `last_price` | Asking price at first and last sighting. |
| `n_price_cuts` | Number of snapshot-to-snapshot price drops. |
| `total_change_pct` | `(last_price / first_price − 1) × 100`. |
| `delisted` | True if the listing stopped appearing before the final snapshot. **"Delisted" ≠ sold**: the seller may have sold it elsewhere, ended it, or relisted it. |

## Region definitions (pre-registered in `config.py`)

- **Snow:** AK, CO, IA, ID, ME, MI, MN, MT, ND, NE, NH, NY, SD, VT, WI, WY
- **Warm:** AZ, FL, TX, and California ZIP3 prefixes 900–935 (southern CA)
- **Other:** every other state, including northern/central California
- **Unknown:** postal code missing or unusable

## Cleaning rules (applied in this order; counts in `output/cleaning_report.txt`)

1. Drop duplicate (item, snapshot) rows.
2. Keep US listings priced in USD.
3. Drop auction-only listings. Their price field is the current bid, not an asking price.
4. Drop non-rideable listings by title (for parts, salvage, no title, toys/diecast). Upgrade words like "exhaust" are kept because real bike titles use them.
5. Keep only titles that match exactly one model, and it must be the model searched (an "R6" returned by the "yamaha r1" search is dropped).
6. Keep asking prices between $1,500 and $60,000.
7. Parse model year and mileage, blanking impossible values (rows are kept).
