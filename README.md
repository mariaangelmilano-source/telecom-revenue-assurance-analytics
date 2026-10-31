# Telecom Revenue Assurance Analytics

End-to-end revenue assurance lab for a **fictional** mobile operator, *Andina Telecom*: synthetic usage and billing data, a SQL **usage-vs-billed reconciliation**, and a **concentration and materiality analysis** that ranks where the money is leaking.

> All data is synthetic and generated with a fixed seed. Names, plans, prices and volumes are invented. No real operator data, systems or figures are used.

## The business problem

Telecom operators lose revenue between the network and the invoice: usage that never gets billed, rates that are not updated after a tariff change, discounts applied twice, active lines that never receive a bill. Revenue assurance teams have to find those gaps, size them and decide which ones to fix first.

Counting cases is not enough: a handful of accounts usually concentrates most of the exposure. This project moves the analysis **from case volume to financial impact**.

## What it does

```
generate.py ──► subscribers, usage (3 months), plans with a mid-period tariff change, bills
                + 4 injected leakage patterns with ground truth
      │
      ▼
sql/reconciliation.sql  (SQLite)
      expected charge = fee + usage × correct rate − discount
      vs. billed charge → leakage per subscriber-month + leak class
      │
      ▼
analysis.py
      • precision / recall against the injected ground truth
      • Pareto concentration: how many accounts explain 80% of the exposure
      • exposure bands by percentile (P50, P80, P95, P99)
      • materiality threshold and KPIs by leak type and by plan
      │
      ▼
reports/summary.md  +  reports/exceptions.csv (ranked work queue)
```

Leakage patterns injected:

| Pattern | What happens |
|---|---|
| `unbilled_usage` | Part of the data usage never reaches the bill |
| `stale_tariff` | The old rate is still applied after the tariff change |
| `duplicate_discount` | The discount is applied twice |
| `active_not_billed` | An active subscriber gets no bill that month |

## Run it

```bash
pip install -r requirements.txt
python -m ra_lab --subscribers 20000 --seed 42
pytest -q
```

## Sample results (seed 42, 20,000 subscribers)

- Revenue at risk detected: **USD 11,111** (0.71% of billed revenue)
- **470 accounts — 26.9% of the leaking accounts — explain 80% of the exposure**
- Accounts above the USD 25 materiality threshold hold 39.8% of the exposure
- `active_not_billed` is only 15% of the cases but 63% of the money: the queue should start there, not with the most frequent pattern.

Full output: [`reports/summary.md`](reports/summary.md).

Detection scores 100% precision and recall here because the scenario is controlled: every leak is injected by the generator with a known signature. On real data the same reconciliation would need tolerance tuning, reference-data checks and investigation of false positives.

## Design notes

- Reconciliation logic lives in plain SQL so it can be moved to SQL Server, Postgres or a warehouse with minimal changes.
- Leak classification follows a precedence order (missing bill → wrong rate → missing usage → excess discount), the way an analyst would triage a case.
- Heavy-tailed (lognormal) usage reproduces the concentration seen in real customer bases.

## What I'd add in production

- Incremental loads and data-quality tests (dbt), orchestration (Airflow) and a Power BI dashboard on top of the exceptions table.
- Tariff certification checks run automatically before each billing cycle.
- Trend monitoring and alerting by leak type.

## Author

**María Ángel Milano** — Data & BI, revenue assurance in telecom · Electrical Engineer (UCV) · M.Sc. Business Intelligence (UNIR) · [LinkedIn](https://linkedin.com/in/maria-angel-milano)
