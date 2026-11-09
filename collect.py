"""Daily snapshot collector for active used-sportbike listings on eBay Motors.

Uses the official eBay Browse API (OAuth2 client-credentials flow), not
web scraping. Run once per day, e.g. from cron:

    17 6 * * *  cd /path/to/moto-market-research && .venv/bin/python collect.py

Politeness:
  * Identifies itself with a User-Agent naming the project and a contact email.
  * Waits at least MIN_SECONDS_BETWEEN_CALLS between every request.
  * Backs off exponentially on HTTP 429 and 5xx, honoring Retry-After.
  * Stops at MAX_CALLS_PER_RUN calls.
  * Calls the item-detail endpoint only for listings it has not seen before.

Privacy (enforced at ingest, before anything touches disk):
  * Only whitelisted fields are kept. Seller username/feedback, images,
    and listing URLs are never written.
  * The partial postal code is converted to state + region, then discarded.

Output (all git-ignored; see README > Data):
  data/raw/snapshots/YYYY-MM-DD.jsonl.gz   one line per listing seen that day
  data/raw/details.jsonl                   year/mileage aspects, one line per new listing
  data/logs/runs.csv                       one line per run (for gap tracking)
"""

import argparse
import base64
import csv
import datetime as dt
import gzip
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

import config
from geo import locate

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
SNAP_DIR = RAW_DIR / "snapshots"
DETAILS_PATH = RAW_DIR / "details.jsonl"
RUN_LOG = ROOT / "data" / "logs" / "runs.csv"

# Fields kept from item summaries. Everything else is dropped at ingest.
SUMMARY_FIELDS = ["itemId", "title", "condition", "conditionId",
                  "buyingOptions", "itemCreationDate"]
# Aspect names (from item detail localizedAspects) worth keeping.
DETAIL_ASPECTS = {"Year": "year", "Mileage": "mileage",
                  "Make": "make", "Model": "model"}

log = logging.getLogger("collect")


class CallBudgetExceeded(RuntimeError):
    pass


class PoliteClient:
    """requests wrapper that rate-limits, retries, and counts calls."""

    def __init__(self, client_id, client_secret, contact_email):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"MotoMarket-research/1.0 (CU Boulder INFO 4617; {contact_email})",
            "X-EBAY-C-MARKETPLACE-ID": config.MARKETPLACE_ID,
            "Accept": "application/json",
        })
        self.calls = 0
        self._last_call = 0.0
        self._token = None
        self._token_expires = 0.0

    # -- internals ---------------------------------------------------------
    def _wait_turn(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < config.MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(config.MIN_SECONDS_BETWEEN_CALLS - elapsed)

    def _request(self, method, url, **kwargs):
        for attempt in range(config.MAX_RETRIES + 1):
            if self.calls >= config.MAX_CALLS_PER_RUN:
                raise CallBudgetExceeded(f"hit {config.MAX_CALLS_PER_RUN}-call cap")
            self._wait_turn()
            self.calls += 1
            self._last_call = time.monotonic()
            try:
                resp = self.session.request(
                    method, url, timeout=config.REQUEST_TIMEOUT_SECONDS, **kwargs)
            except requests.RequestException as exc:
                wait = config.BACKOFF_BASE_SECONDS * 2 ** attempt
                log.warning("network error %s; retrying in %.0fs", exc, wait)
                time.sleep(wait)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After")
                wait = (float(retry_after) if retry_after and retry_after.isdigit()
                        else config.BACKOFF_BASE_SECONDS * 2 ** attempt)
                log.warning("HTTP %s on %s; backing off %.0fs",
                            resp.status_code, url, wait)
                time.sleep(wait)
                continue
            return resp
        resp.raise_for_status()
        return resp

    # -- auth --------------------------------------------------------------
    def _bearer(self):
        if self._token and time.monotonic() < self._token_expires - 60:
            return self._token
        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = self._request(
            "POST", config.OAUTH_URL,
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": config.OAUTH_SCOPE},
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires = time.monotonic() + int(body.get("expires_in", 7200))
        return self._token

    def get(self, url, params=None):
        resp = self._request("GET", url, params=params,
                             headers={"Authorization": f"Bearer {self._bearer()}"})
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Ingest-time privacy filtering
# ---------------------------------------------------------------------------
def sanitize_summary(item, query, snapshot_date):
    """Whitelist fields; convert postal code to state/region; drop the rest."""
    row = {k: item.get(k) for k in SUMMARY_FIELDS}
    price = item.get("price") or {}
    row["price_value"] = price.get("value")
    row["price_currency"] = price.get("currency")
    # Auctions report the current bid here instead of an asking price.
    bid = item.get("currentBidPrice") or {}
    row["current_bid_value"] = bid.get("value")
    loc = item.get("itemLocation") or {}
    row["country"] = loc.get("country")
    row["state"], row["region"] = locate(loc.get("postalCode"))
    row["query"] = query
    row["snapshot_date"] = snapshot_date
    return row


def sanitize_detail(item_id, detail):
    row = {"itemId": item_id}
    for aspect in detail.get("localizedAspects") or []:
        key = DETAIL_ASPECTS.get(aspect.get("name"))
        if key:
            row[key] = aspect.get("value")
    return row


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
def search_all(client, query):
    """Yield every item summary for one query, following pagination."""
    offset = 0
    while True:
        body = client.get(config.SEARCH_URL, params={
            "q": query,
            "category_ids": config.CATEGORY_ID,
            "filter": f"conditionIds:{{{config.USED_CONDITION_ID}}},itemLocationCountry:US",
            "limit": config.PAGE_LIMIT,
            "offset": offset,
        })
        items = body.get("itemSummaries") or []
        yield from items
        offset += len(items)
        if not items or offset >= int(body.get("total", 0)):
            break


def load_seen_detail_ids():
    if not DETAILS_PATH.exists():
        return set()
    with DETAILS_PATH.open() as f:
        return {json.loads(line)["itemId"] for line in f if line.strip()}


def log_run(snapshot_date, status, n_listings, n_details, calls, note=""):
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not RUN_LOG.exists()
    with RUN_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_at_utc", "snapshot_date", "status", "listings",
                        "new_details", "api_calls", "note"])
        w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    snapshot_date, status, n_listings, n_details, calls, note])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true",
                    help="overwrite today's snapshot if it already exists")
    ap.add_argument("--models", nargs="*",
                    help="subset of search queries from config.MODELS")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(ROOT / ".env")
    try:
        client = PoliteClient(os.environ["EBAY_CLIENT_ID"],
                              os.environ["EBAY_CLIENT_SECRET"],
                              os.environ["CONTACT_EMAIL"])
    except KeyError as missing:
        sys.exit(f"Missing {missing} in .env (see .env.example)")

    snapshot_date = dt.date.today().isoformat()
    out_path = SNAP_DIR / f"{snapshot_date}.jsonl.gz"
    if out_path.exists() and not args.force:
        log.info("snapshot %s already exists; use --force to redo", out_path.name)
        return

    queries = args.models or list(config.MODELS)
    seen_details = load_seen_detail_ids()
    rows, seen_today, new_details = [], set(), []
    status, note = "ok", ""

    try:
        for query in queries:
            n_before = len(rows)
            for item in search_all(client, query):
                item_id = item.get("itemId")
                if not item_id or item_id in seen_today:
                    continue          # same listing returned by two queries
                seen_today.add(item_id)
                rows.append(sanitize_summary(item, query, snapshot_date))
            log.info("%-20s %4d listings", query, len(rows) - n_before)

        # Detail calls use whatever budget is left. On the first few days there
        # are more new listings than budget; the backlog is filled on later
        # runs, and clean.py falls back to parsing year/mileage from titles.
        backlog = [r["itemId"] for r in rows if r["itemId"] not in seen_details]
        try:
            for item_id in backlog:
                try:
                    detail = client.get(config.ITEM_URL.format(item_id=item_id))
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 404:
                        continue      # listing ended between search and detail call
                    raise
                new_details.append(sanitize_detail(item_id, detail))
                seen_details.add(item_id)
        except CallBudgetExceeded:
            note = f"detail backlog: {len(backlog) - len(new_details)} left for next run"
            log.info(note)
    except CallBudgetExceeded as exc:
        status, note = "partial", str(exc)
        log.warning("%s; saving what was collected", exc)
    except requests.HTTPError as exc:
        status, note = "error", str(exc)
        log.error("aborting: %s", exc)

    if rows:
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        with gzip.open(out_path, "wt") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
    if new_details:
        with DETAILS_PATH.open("a") as f:
            for row in new_details:
                f.write(json.dumps(row) + "\n")

    log_run(snapshot_date, status, len(rows), len(new_details), client.calls, note)
    log.info("saved %d listings, %d new details, %d API calls (%s)",
             len(rows), len(new_details), client.calls, status)
    if status == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
