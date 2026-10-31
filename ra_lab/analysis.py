"""Reconciliation, scoring and concentration / materiality analysis."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from .generate import MONTHS, Dataset, _rates

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_sqlite(ds: Dataset) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    ds.subscribers.to_sql("subscribers", con, index=False)
    ds.usage.to_sql("usage", con, index=False)
    ds.bills.to_sql("bills", con, index=False)
    rates = pd.concat([_rates(ds.plans, m).assign(month=m) for m in MONTHS], ignore_index=True)
    rates.to_sql("rates", con, index=False)
    return con


def reconcile(ds: Dataset) -> pd.DataFrame:
    con = load_sqlite(ds)
    query = (SQL_DIR / "reconciliation.sql").read_text(encoding="utf-8")
    return pd.read_sql_query(query, con)


def score(recon: pd.DataFrame, truth: pd.DataFrame) -> dict:
    """Precision / recall of the leak classes against the injected ground truth."""
    flagged = recon[recon.leak_class != "ok"][["subscriber_id", "month", "leak_class"]]
    merged = flagged.merge(truth, on=["subscriber_id", "month"], how="outer", indicator=True)
    tp = int(((merged._merge == "both") & (merged.leak_class == merged.leak_type)).sum())
    return {
        "flagged": len(flagged),
        "injected": len(truth),
        "precision": round(tp / len(flagged), 4) if len(flagged) else 0.0,
        "recall": round(tp / len(truth), 4) if len(truth) else 0.0,
    }


def pareto_share(values: pd.Series, target: float = 0.8) -> tuple[int, float]:
    """How many accounts (and what share of flagged accounts) explain `target` of the total."""
    v = values.sort_values(ascending=False).to_numpy()
    if v.sum() <= 0:
        return 0, 0.0
    cum = np.cumsum(v) / v.sum()
    n = int(np.searchsorted(cum, target) + 1)
    return n, n / len(v)


def exposure_bands(leaks: pd.Series) -> pd.DataFrame:
    """Segment leaking accounts by percentile bands of exposure."""
    q = leaks.quantile([0.5, 0.8, 0.95, 0.99]).to_list()
    edges = [0, *q, np.inf]
    labels = ["P0-50", "P50-80", "P80-95", "P95-99", "P99-100"]
    bands = pd.cut(leaks, bins=edges, labels=labels, include_lowest=True, duplicates="drop")
    out = leaks.groupby(bands, observed=True).agg(accounts="count", exposure="sum")
    out["share_of_exposure"] = (out.exposure / out.exposure.sum()).round(4)
    return out


def summarize(recon: pd.DataFrame, materiality: float = 25.0) -> dict:
    leaking = recon[recon.leakage > 0.01]
    by_account = leaking.groupby("subscriber_id").leakage.sum()
    n80, share80 = pareto_share(by_account)
    material = by_account[by_account >= materiality]
    billed_total = recon.net_billed.sum()
    return {
        "revenue_billed": round(billed_total, 2),
        "revenue_at_risk": round(leaking.leakage.sum(), 2),
        "leakage_pct_of_billed": round(leaking.leakage.sum() / billed_total * 100, 3),
        "accounts_leaking": int(by_account.size),
        "accounts_for_80pct": n80,
        "share_of_leaking_accounts_for_80pct": round(share80, 4),
        "material_accounts": int(material.size),
        "material_exposure_share": round(material.sum() / by_account.sum(), 4) if by_account.sum() else 0.0,
        "by_type": leaking.groupby("leak_class").leakage.agg(["count", "sum"]).round(2),
        "by_plan": leaking.groupby("plan_id").leakage.sum().round(2).sort_values(ascending=False),
        "bands": exposure_bands(by_account),
    }
