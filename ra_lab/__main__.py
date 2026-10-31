"""python -m ra_lab --subscribers 20000 --seed 42"""
from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import reconcile, score, summarize
from .generate import generate


def main() -> None:
    ap = argparse.ArgumentParser(description="Telecom revenue assurance lab (synthetic data)")
    ap.add_argument("--subscribers", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--materiality", type=float, default=25.0, help="USD per account over the period")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    ds = generate(args.subscribers, args.seed)
    recon = reconcile(ds)
    s = summarize(recon, args.materiality)
    q = score(recon, ds.truth)

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    recon[recon.leak_class != "ok"].sort_values("leakage", ascending=False).to_csv(out / "exceptions.csv", index=False)

    lines = [
        "# Revenue assurance summary — Andina Telecom (synthetic)",
        "",
        f"Subscribers: {args.subscribers:,} · Months: 3 · Seed: {args.seed}",
        "",
        "## Headline KPIs",
        f"- Revenue billed: USD {s['revenue_billed']:,.2f}",
        f"- Revenue at risk detected: USD {s['revenue_at_risk']:,.2f} ({s['leakage_pct_of_billed']}% of billed)",
        f"- Leaking accounts: {s['accounts_leaking']:,}",
        f"- Concentration: {s['accounts_for_80pct']:,} accounts "
        f"({s['share_of_leaking_accounts_for_80pct']:.1%} of leaking accounts) explain 80% of exposure",
        f"- Material accounts (≥ USD {args.materiality:.0f}): {s['material_accounts']:,}, "
        f"holding {s['material_exposure_share']:.1%} of exposure",
        "",
        "## Detection quality vs. injected ground truth",
        f"- Flagged: {q['flagged']:,} · Injected: {q['injected']:,} · "
        f"Precision: {q['precision']:.2%} · Recall: {q['recall']:.2%}",
        "",
        "## Leakage by type",
        s["by_type"].to_markdown(),
        "",
        "## Leakage by plan",
        s["by_plan"].to_frame("leakage_usd").to_markdown(),
        "",
        "## Exposure bands (percentiles of leakage per account)",
        s["bands"].round(2).to_markdown(),
        "",
    ]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
