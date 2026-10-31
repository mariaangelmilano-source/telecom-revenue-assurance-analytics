# Revenue assurance summary — Andina Telecom (synthetic)

Subscribers: 20,000 · Months: 3 · Seed: 42

## Headline KPIs
- Revenue billed: USD 1,561,110.92
- Revenue at risk detected: USD 11,111.27 (0.712% of billed)
- Leaking accounts: 1,748
- Concentration: 470 accounts (26.9% of leaking accounts) explain 80% of exposure
- Material accounts (≥ USD 25): 121, holding 39.8% of exposure

## Detection quality vs. injected ground truth
- Flagged: 1,800 · Injected: 1,800 · Precision: 100.00% · Recall: 100.00%

## Leakage by type
| leak_class         |   count |     sum |
|:-------------------|--------:|--------:|
| active_not_billed  |     264 | 6953.85 |
| duplicate_discount |     365 |  635.7  |
| stale_tariff       |     366 |  553.68 |
| unbilled_usage     |     805 | 2968.04 |

## Leakage by plan
| plan_id   |   leakage_usd |
|:----------|--------------:|
| P10       |       4362.43 |
| P20       |       2961.65 |
| P30       |       2027.93 |
| B50       |       1759.26 |

## Exposure bands (percentiles of leakage per account)
| leakage   |   accounts |   exposure |   share_of_exposure |
|:----------|-----------:|-----------:|--------------------:|
| P0-50     |        875 |     971.49 |                0.09 |
| P50-80    |        523 |    1965.1  |                0.18 |
| P80-95    |        262 |    4636.17 |                0.42 |
| P95-99    |         71 |    2512.88 |                0.23 |
| P99-100   |         17 |    1025.63 |                0.09 |
