"""Convert a (partial) US postal code to a state and pre-registered region.

eBay's Browse API returns a partially masked postal code (e.g. "802**").
Only the first three digits (ZIP3) are needed to identify the state.
The postal code itself is discarded after conversion; only state and
region are stored.
"""

from config import SNOW_STATES, WARM_STATES, SOCAL_ZIP3_RANGE

# (start, end, state), inclusive ZIP3 ranges. Single-prefix exceptions are
# listed first so they win over the broader range that contains them.
_ZIP3_RANGES = [
    (55, 55, "MA"), (201, 201, "VA"), (569, 569, "DC"), (733, 733, "TX"),
    (885, 885, "TX"),
    (5, 5, "NY"), (6, 9, "PR"), (10, 27, "MA"), (28, 29, "RI"),
    (30, 38, "NH"), (39, 49, "ME"), (50, 59, "VT"), (60, 69, "CT"),
    (70, 89, "NJ"), (100, 149, "NY"), (150, 196, "PA"), (197, 199, "DE"),
    (200, 205, "DC"), (206, 219, "MD"), (220, 246, "VA"), (247, 268, "WV"),
    (270, 289, "NC"), (290, 299, "SC"), (300, 319, "GA"), (320, 349, "FL"),
    (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (398, 399, "GA"),
    (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"),
    (500, 528, "IA"), (530, 549, "WI"), (550, 567, "MN"), (570, 577, "SD"),
    (580, 588, "ND"), (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"),
    (660, 679, "KS"), (680, 693, "NE"), (700, 714, "LA"), (716, 729, "AR"),
    (730, 749, "OK"), (750, 799, "TX"), (800, 816, "CO"), (820, 831, "WY"),
    (832, 838, "ID"), (840, 847, "UT"), (850, 865, "AZ"), (870, 884, "NM"),
    (889, 898, "NV"), (900, 961, "CA"), (967, 968, "HI"), (970, 979, "OR"),
    (980, 994, "WA"), (995, 999, "AK"),
]


def zip3_of(postal_code):
    """Return the ZIP3 prefix as an int, or None if unusable."""
    if not postal_code:
        return None
    digits = str(postal_code).strip()[:3]
    if len(digits) < 3 or not digits.isdigit():
        return None
    return int(digits)


def state_from_zip3(zip3):
    if zip3 is None:
        return None
    for start, end, state in _ZIP3_RANGES:
        if start <= zip3 <= end:
            return state
    return None


def region_for(state, zip3):
    """Return 'snow', 'warm', or 'other' using the pre-registered groups."""
    if state in SNOW_STATES:
        return "snow"
    if state in WARM_STATES:
        return "warm"
    if state == "CA" and zip3 is not None:
        lo, hi = SOCAL_ZIP3_RANGE
        return "warm" if lo <= zip3 <= hi else "other"
    return "other"


def locate(postal_code):
    """postal code -> (state, region). The postal code is not returned."""
    z = zip3_of(postal_code)
    state = state_from_zip3(z)
    return state, region_for(state, z) if state else "unknown"
