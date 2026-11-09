"""Project configuration: models, regions, and API settings.

PRE-REGISTRATION NOTE
The SNOW_STATES / WARM_REGION definitions below are fixed before analysis.
Do not edit them after looking at results. Any change must be logged in
README.md (Data > Region definitions) with the date and reason.
"""

# ---------------------------------------------------------------------------
# eBay Browse API
# ---------------------------------------------------------------------------
OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
ITEM_URL = "https://api.ebay.com/buy/browse/v1/item/{item_id}"

MARKETPLACE_ID = "EBAY_MOTORS_US"
CATEGORY_ID = "6024"          # eBay Motors > Motorcycles (confirm against category tree)
USED_CONDITION_ID = "3000"    # "Used"
PAGE_LIMIT = 200              # max allowed by the search endpoint

# Politeness settings
MIN_SECONDS_BETWEEN_CALLS = 1.0
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 2.0    # 2, 4, 8, 16, 32 s on 429 / 5xx
MAX_CALLS_PER_RUN = 300
REQUEST_TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Models: search query -> canonical model label and displacement class
# ---------------------------------------------------------------------------
MODELS = {
    "yamaha r1":          {"model": "Yamaha R1",           "cc_class": "1000cc"},
    "yamaha r6":          {"model": "Yamaha R6",           "cc_class": "600cc"},
    "yamaha r7":          {"model": "Yamaha R7",           "cc_class": "600cc"},
    "honda cbr600rr":     {"model": "Honda CBR600RR",      "cc_class": "600cc"},
    "honda cbr1000rr":    {"model": "Honda CBR1000RR",     "cc_class": "1000cc"},
    "kawasaki zx-6r":     {"model": "Kawasaki ZX-6R",      "cc_class": "600cc"},
    "kawasaki zx-10r":    {"model": "Kawasaki ZX-10R",     "cc_class": "1000cc"},
    "suzuki gsx-r600":    {"model": "Suzuki GSX-R600",     "cc_class": "600cc"},
    "suzuki gsx-r750":    {"model": "Suzuki GSX-R750",     "cc_class": "600cc"},  # grouped with middleweights
    "ducati panigale v2": {"model": "Ducati Panigale V2",  "cc_class": "1000cc"},  # 955cc, grouped with liter bikes
    "bmw s1000rr":        {"model": "BMW S1000RR",         "cc_class": "1000cc"},
    "aprilia rsv4":       {"model": "Aprilia RSV4",        "cc_class": "1000cc"},
}

# ---------------------------------------------------------------------------
# Regions (pre-registered)
# ---------------------------------------------------------------------------
# Snow states: riding season effectively ends by December.
SNOW_STATES = {
    "AK", "CO", "ID", "IA", "ME", "MI", "MN", "MT", "NE",
    "NH", "NY", "ND", "SD", "VT", "WI", "WY",
}
# Warm region: riding is year-round. California counts only for
# southern-California ZIP3 prefixes (900-935).
WARM_STATES = {"FL", "AZ", "TX"}
SOCAL_ZIP3_RANGE = (900, 935)
