# Moto Market Research Proposal: End-of-Season Sportbike Pricing

**Author:** Huy Phan · **Date:** Oct 25, 2026

## 1. Research question

**Do asking prices for used sportbikes on eBay Motors drop as riding season ends (late October to mid-December 2026), and is that drop bigger for sellers in snow states than for sellers in warm states?**

This question comes straight out of my current project, Moto Market, an all-in-one motorcycle resource for fair market value. While building it, I kept hearing the same advice from other riders: "wait until winter, people dump their bikes." Everyone seems to believe it, but I have never seen anyone actually check. The question is empirical because I can answer it with real listing data from eBay, and it is falsifiable because the answer could be no drop at all, a small drop, a big one, or even prices going up.

### Who would care

The people who would care the most are budget and first-time buyers, like the CU motorcycle club members I surveyed earlier for Moto Market. In that survey, first-timers compared the fewest listings and skipped pricing guides, so knowing when to buy could save them real money. Sellers would also care, since it tells them whether to sell now, drop their price, or just store the bike until spring. Lastly, small dealers and flippers could use it to time when they buy trade-ins.

### What I expect, and what would surprise me

I expect asking prices in snow states like Colorado, Minnesota, Michigan, and New York to drop around 3–8% by mid-December. In warm states like Florida, Arizona, Texas, and southern California, I expect prices to stay about the same, since riding season never really ends there.

What would surprise me is if there were no difference between the two regions at all. That would mean eBay's nationwide reach basically cancels out local seasons. It would also surprise me if prices went up, which could happen if the cheaper bikes sell or get pulled first and only the more expensive listings are left.

## 2. Data source and method

I will be using the official eBay Browse API, which I already have set up for Moto Market, and pulling a snapshot of listings once a day for about seven weeks into my existing PostgreSQL database.

### Source

The main endpoint is the search endpoint, `GET https://api.ebay.com/buy/browse/v1/item_summary/search`, which returns active listings that match a keyword and category. For details like model year and mileage, I will use the item endpoint, `GET https://api.ebay.com/buy/browse/v1/item/{item_id}`. Every request includes the header `X-EBAY-C-MARKETPLACE-ID: EBAY_MOTORS_US` and is filtered to the Motorcycles category (category ID 6024, which I still need to confirm against eBay's category tree). The documentation is here: [eBay Browse API overview](https://developer.ebay.com/api-docs/buy/browse/overview.html).

### How I will get it

I am collecting the data through eBay's documented REST API, not by scraping their website. I log in using the OAuth2 client-credentials flow with my own registered eBay developer app, and a scheduled Python script will grab one snapshot every day. The methods I am using come from the course chapters on **APIs and authentication** and on **collecting data over time**. *(Chapter numbers to be filled in.)*

### Scope

| Item | Plan |
| --- | --- |
| Records | Active US used-motorcycle listings for about 12 popular sportbikes: Yamaha R1, R6, R7; Honda CBR600RR, CBR1000RR; Kawasaki ZX-6R, ZX-10R; Suzuki GSX-R600, GSX-R750; Ducati Panigale V2; BMW S1000RR; Aprilia RSV4 |
| Size per snapshot | About 1,500–3,000 listings (to be checked after the first full pull) |
| Time window | Oct 27 – Dec 13, 2026 |
| Frequency | One snapshot per day, about 48 snapshots total |
| Total rows | Roughly 70,000–140,000 listing-days, or about 4,000–6,000 unique listings |
| API calls | About 50–150 search calls a day, plus one detail call for each new listing. This is well under the default Browse API limit. |

For each listing I will keep the `itemId`, `title`, `price.value` and `price.currency`, `condition`, `buyingOptions`, `itemCreationDate`, the state from `itemLocation.postalCode`, the snapshot date, and the model year and mileage I parse out. Before I collect anything, I will write down a fixed list of which states count as **snow states** and which count as **warm states**, so I can't change the groups later to fit the results.

### Analysis

To answer the question, I plan to look at the data a few different ways:

1. **Weekly median asking price by region.** A line chart with one line for snow states and one for warm states, also split by 600cc and 1000cc bikes.
2. **Price cuts on the same listing.** How many listings drop their price between snapshots, and by how much. In my opinion this is the strongest signal, because it shows what sellers are actually doing instead of just which bikes happen to be listed.
3. **Supply over time.** How many active listings there are in each region every week.
4. **Time until a listing disappears.** How many days a listing stays up, compared by region. I will call this "delisted" instead of "sold," since the API can't tell me whether a bike actually sold.
5. **A controlled comparison.** A simple regression of log price on model, year, mileage, region, week, and a region × week interaction. That interaction term is what really answers my question.

## 3. Ethics and feasibility

I believe this collection is allowed, since everything goes through eBay's official API with my own registered developer account. I also drop any seller information the moment it comes in, and I have a backup plan if my main risk, not having enough listings, turns out to be a problem.

### Terms of service and robots.txt

eBay's robots.txt blocks most automated crawling of its listing pages. That is exactly why I am not scraping eBay's website at all and am only using the API. Using the API is covered by the [eBay API License Agreement](https://developer.ebay.com/join/api-license-agreement) and the Browse API's call limits. *Before submitting: confirm what the agreement says about how long API data can be stored and how eBay content can be displayed, and summarize it here in one or two sentences.*

This is an academic, non-commercial project, and the only things I will publish are aggregate numbers like medians, counts, and regression results. I won't republish any listing text, photos, or individual listings.

To stay within eBay's limits, I will:

- Authenticate with my own app keys, so eBay always knows who is making the requests.
- Send a User-Agent header that names the project and includes my contact email.
- Wait at least 1 second between calls.
- Back off and retry if I get an HTTP 429 (rate limited) or a 5xx error.
- Keep it to about 300 calls a day at most, which is a small fraction of the default limit.
- Only request details for listings I haven't seen before.

My API keys stay in an environment file that is excluded from git. I learned this one the hard way on Moto Market after accidentally committing my credentials once, so they will never be committed again.

### Personal information

The API response does include some personal details: seller usernames, feedback scores, item photos, and partial postal codes. Here is how I will handle each one:

- **Seller username and feedback:** dropped as soon as the data comes in and never saved to the database.
- **Photos and image links:** not saved.
- **Location:** I convert the postal code to a US state and then throw away the postal code.
- **Listing titles:** kept only so I can pull out the model, year, and mileage. They won't be published.
- **Results:** aggregates only, so no chart or table will ever point back to one specific listing or seller.

### One record, retrieved

This is the request I will run with a fresh OAuth token:

```python
import requests

r = requests.get(
    "https://api.ebay.com/buy/browse/v1/item_summary/search",
    params={"q": "yamaha r1", "category_ids": "6024", "limit": 1},
    headers={
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_MOTORS_US",
        "User-Agent": "MotoMarket-research (CU Boulder; <your email>)",
    },
)
print(r.status_code)
print(r.json()["itemSummaries"][0])
```

- [ ] Run the request and paste the status code (expected: 200) and the returned record here, or attach a screenshot. Blank out the `seller` block before pasting.
- [ ] Confirm the fields used: `itemId`, `title`, `price.value`, `condition`, `buyingOptions`, `itemCreationDate`, `itemLocation.postalCode`.

### Biggest risk and fallback

The biggest risk to finishing is not having enough listings. Some models might only have 15 or 20 active listings at a time, which is too few to split by region. If that happens, I will group the models into 600cc and 1000cc classes, and if that still isn't enough, I will drop the regional split and just compare national prices week to week.

Another limitation is that the Browse API only shows asking prices, not what bikes actually sold for, and a listing disappearing doesn't always mean it sold. I will be upfront about this in my write-up and lean on the same-listing price cuts, since those show real seller behavior.

Seven weeks might also not be long enough to see the full seasonal effect. If the data ends up flat or too noisy, my fallback is to switch to a question I can answer with a single snapshot: how much asking prices drop per model year, by brand. To avoid gaps from a failed run, I will log every run and look at the data by week instead of by day, so one missed day doesn't matter.

Lastly, if eBay changes my access or tightens its limits, I can narrow the scope to 3–4 models, or use [NHTSA's public recall data](https://www.nhtsa.gov/nhtsa-datasets-and-apis) as a second source to ask whether recalled models get listed more often.

## Sources

- [eBay Browse API overview](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [eBay API License Agreement](https://developer.ebay.com/join/api-license-agreement)
- [NHTSA datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis), the fallback source
- [Moto Market repository](https://github.com/phanhuy18/Moto-market)
