"""Synthetic data for a fictional operator, "Andina Telecom".

Everything here is invented: plans, prices, volumes and customers. The generator
injects four known revenue-leakage patterns and keeps the ground truth, so the
reconciliation can be scored for precision and recall.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS = ["2026-01", "2026-02", "2026-03"]
TARIFF_CHANGE_MONTH = "2026-02"  # new rates apply from this month on

PLANS = pd.DataFrame(
    [
        # plan_id, name, monthly fee, data $/GB, voice $/min, sms $/msg (old -> new rates)
        ("P10", "Andina Basic", 8.0, 1.20, 0.040, 0.020, 1.40, 0.045, 0.020),
        ("P20", "Andina Plus", 15.0, 0.90, 0.030, 0.015, 1.05, 0.035, 0.015),
        ("P30", "Andina Max", 25.0, 0.60, 0.020, 0.010, 0.70, 0.025, 0.010),
        ("B50", "Andina Business", 45.0, 0.45, 0.015, 0.008, 0.50, 0.018, 0.008),
    ],
    columns=["plan_id", "plan_name", "monthly_fee",
             "data_rate_old", "voice_rate_old", "sms_rate_old",
             "data_rate_new", "voice_rate_new", "sms_rate_new"],
)

LEAK_TYPES = ("unbilled_usage", "stale_tariff", "duplicate_discount", "active_not_billed")


@dataclass
class Dataset:
    plans: pd.DataFrame
    subscribers: pd.DataFrame
    usage: pd.DataFrame
    bills: pd.DataFrame
    truth: pd.DataFrame  # one row per injected leak: subscriber_id, month, leak_type


def _rates(plans: pd.DataFrame, month: str) -> pd.DataFrame:
    suffix = "new" if month >= TARIFF_CHANGE_MONTH else "old"
    out = plans[["plan_id", "monthly_fee"]].copy()
    for svc in ("data", "voice", "sms"):
        out[f"{svc}_rate"] = plans[f"{svc}_rate_{suffix}"]
    return out


def generate(n_subscribers: int = 20_000, seed: int = 42, leak_rate: float = 0.03) -> Dataset:
    rng = np.random.default_rng(seed)

    plan_ids = rng.choice(PLANS.plan_id, size=n_subscribers, p=[0.45, 0.30, 0.17, 0.08])
    subscribers = pd.DataFrame({
        "subscriber_id": [f"S{i:06d}" for i in range(1, n_subscribers + 1)],
        "plan_id": plan_ids,
        "segment": np.where(plan_ids == "B50", "business", "consumer"),
        "discount_pct": rng.choice([0.0, 0.05, 0.10], size=n_subscribers, p=[0.7, 0.2, 0.1]),
        "status": "active",
    })

    # Heavy-tailed usage (lognormal): a few accounts consume a lot, as in real networks.
    rows = []
    biz = (subscribers.segment == "business").to_numpy()
    for month in MONTHS:
        scale = np.where(biz, 3.0, 1.0)
        rows.append(pd.DataFrame({
            "subscriber_id": subscribers.subscriber_id,
            "month": month,
            "data_gb": np.round(rng.lognormal(1.2, 0.9, n_subscribers) * scale, 3),
            "voice_min": np.round(rng.lognormal(4.5, 0.8, n_subscribers) * scale, 1),
            "sms": rng.poisson(30, n_subscribers) * scale.astype(int),
        }))
    usage = pd.concat(rows, ignore_index=True)

    # Correct bill = fee + rated usage - discount.
    bills = []
    for month in MONTHS:
        u = usage[usage.month == month].merge(subscribers, on="subscriber_id").merge(_rates(PLANS, month), on="plan_id")
        rated = u.data_gb * u.data_rate + u.voice_min * u.voice_rate + u.sms * u.sms_rate
        gross = u.monthly_fee + rated
        bills.append(pd.DataFrame({
            "subscriber_id": u.subscriber_id, "month": month,
            "fee_billed": u.monthly_fee,
            "data_gb_billed": u.data_gb, "voice_min_billed": u.voice_min, "sms_billed": u.sms,
            "data_rate_applied": u.data_rate, "voice_rate_applied": u.voice_rate, "sms_rate_applied": u.sms_rate,
            "discount_applied": np.round(gross * u.discount_pct, 2),
        }))
    bills = pd.concat(bills, ignore_index=True)

    # Inject leaks on a random sample of subscriber-months, at most one leak per row.
    n_leaks = int(len(bills) * leak_rate)
    idx = rng.choice(bills.index, size=n_leaks, replace=False)
    kinds = rng.choice(LEAK_TYPES, size=n_leaks, p=[0.35, 0.30, 0.20, 0.15])
    truth, drop = [], []
    old = _rates(PLANS, "2026-01").set_index("plan_id")
    plan_of = subscribers.set_index("subscriber_id").plan_id
    for i, kind in zip(idx, kinds):
        row = bills.loc[i]
        if kind == "stale_tariff" and row.month < TARIFF_CHANGE_MONTH:
            kind = "unbilled_usage"  # stale tariff only exists after the change
        if kind == "unbilled_usage":
            share = rng.uniform(0.3, 1.0)  # part of the data usage never reached the bill
            bills.at[i, "data_gb_billed"] = round(row.data_gb_billed * (1 - share), 3)
        elif kind == "stale_tariff":
            p = old.loc[plan_of[row.subscriber_id]]
            bills.at[i, "data_rate_applied"] = p.data_rate
            bills.at[i, "voice_rate_applied"] = p.voice_rate
        elif kind == "duplicate_discount":
            bills.at[i, "discount_applied"] = row.discount_applied * 2 if row.discount_applied > 0 else round(
                (row.fee_billed) * 0.10, 2)
        elif kind == "active_not_billed":
            drop.append(i)
        truth.append((row.subscriber_id, row.month, kind))
    bills = bills.drop(index=drop).reset_index(drop=True)

    return Dataset(PLANS.copy(), subscribers, usage, bills,
                   pd.DataFrame(truth, columns=["subscriber_id", "month", "leak_type"]))
