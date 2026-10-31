import pandas as pd
import pytest

from ra_lab.analysis import exposure_bands, pareto_share, reconcile, score, summarize
from ra_lab.generate import LEAK_TYPES, generate


@pytest.fixture(scope="module")
def ds():
    return generate(n_subscribers=2_000, seed=7)


@pytest.fixture(scope="module")
def recon(ds):
    return reconcile(ds)


def test_generator_is_deterministic():
    a, b = generate(500, seed=1), generate(500, seed=1)
    pd.testing.assert_frame_equal(a.bills, b.bills)
    pd.testing.assert_frame_equal(a.truth, b.truth)


def test_every_leak_type_is_injected(ds):
    assert set(ds.truth.leak_type) == set(LEAK_TYPES)


def test_clean_rows_reconcile_to_zero(recon, ds):
    keys = set(zip(ds.truth.subscriber_id, ds.truth.month))
    clean = recon[[k not in keys for k in zip(recon.subscriber_id, recon.month)]]
    assert (clean.leak_class == "ok").all()
    assert clean.leakage.abs().max() <= 0.02  # rounding only


def test_reconciliation_recovers_injected_leaks(recon, ds):
    q = score(recon, ds.truth)
    assert q["recall"] >= 0.95
    assert q["precision"] >= 0.95


def test_leakage_is_positive_for_flagged_rows(recon):
    flagged = recon[recon.leak_class != "ok"]
    assert (flagged.leakage > 0).all()


def test_pareto_share_on_toy_data():
    n, share = pareto_share(pd.Series([80, 10, 5, 5]))
    assert n == 1 and share == 0.25


def test_exposure_bands_sum_to_total():
    s = pd.Series(range(1, 101), dtype=float)
    bands = exposure_bands(s)
    assert bands.exposure.sum() == pytest.approx(s.sum())
    assert bands.share_of_exposure.sum() == pytest.approx(1.0, abs=1e-3)


def test_summary_kpis(recon):
    s = summarize(recon, materiality=25)
    assert s["revenue_at_risk"] > 0
    assert 0 < s["share_of_leaking_accounts_for_80pct"] < 1
