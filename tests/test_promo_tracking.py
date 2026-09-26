import pytest
from fastapi.testclient import TestClient

from market_intel import run_pipeline as rp
from market_intel.api import app
from market_intel.catalog import tracked_price_alerts
from market_intel.schema import FieldEvidence, ModelComparison, ModelExtraction
from market_intel.store import (
    load_all_comparisons,
    load_evidence,
    load_history,
    save_model_comparison,
    set_promo,
)
from market_intel.verify import Verified, promo_near, verify_model_extraction

LIST_QUOTE = "For every second of video you generate you will be charged $0.10"
PROMO_QUOTE = "For every second of video you generate you will be charged $0.05"
LIST_PAGE = "# Hailuo 3\n\n" + LIST_QUOTE + " per second.\n"
PROMO_PAGE = (
    "# Hailuo 3\n\n" + PROMO_QUOTE + " per second. Note: these are promotional launch rates, "
    "50% off for a limited time. The discount ends September 30, after which the price is $0.10 per second.\n"
)


def _extraction(price, quote):
    return ModelExtraction(
        model_name="Hailuo 3", provider="MiniMax", price_per_second_usd=price,
        evidence=[FieldEvidence(field="price_per_second_usd", quote=quote)],
    )


# ---- verifier ------------------------------------------------------------------

def test_promo_near_finds_the_cue_next_to_the_quote_and_ignores_the_rest_of_the_page():
    far = "x " * 400  # promo wording far from the price is not about this price
    assert promo_near(PROMO_PAGE, PROMO_QUOTE) is not None
    assert promo_near(LIST_PAGE + far + " 50% off for a limited time", LIST_QUOTE) is None
    assert promo_near(LIST_PAGE, "a quote that is not on the page") is None


def test_a_promotional_price_becomes_promo_and_leaves_the_list_price_alone():
    verified = verify_model_extraction(_extraction(0.05, PROMO_QUOTE), PROMO_PAGE, "hailuo-3")

    assert verified.promo[0] == 0.05 and "promo cue" in verified.promo[1]
    assert verified.comparison.price_per_second_usd is None
    assert "price_per_second_usd" not in verified.evidence


def test_a_normal_price_is_not_promo():
    verified = verify_model_extraction(_extraction(0.10, LIST_QUOTE), LIST_PAGE, "hailuo-3")

    assert verified.promo is None and verified.comparison.price_per_second_usd == 0.10


# ---- store ---------------------------------------------------------------------

def test_set_promo_sets_updates_and_clears_with_evidence_and_history():
    save_model_comparison(ModelComparison(model_name="Hailuo 3", provider="MiniMax", price_per_second_usd=0.10), "hailuo-3")

    assert set_promo("hailuo-3", 0.05, "50% off for a limited time", "https://example.com") is True
    assert set_promo("hailuo-3", 0.05, "50% off for a limited time", "https://example.com") is False  # unchanged
    assert load_evidence()[("model", "hailuo-3")]["promo_price_per_second_usd"]["quote"] == "50% off for a limited time"

    assert set_promo("hailuo-3", None) is True
    assert "promo_price_per_second_usd" not in load_evidence().get(("model", "hailuo-3"), {})
    history = load_history(entity_type="model", field="promo_price_per_second_usd")
    assert [(h["old_value"], h["new_value"]) for h in history] == [(None, "0.05"), ("0.05", "None")]
    assert load_all_comparisons()[0].price_per_second_usd == 0.10  # the list price never moved


def test_set_promo_unknown_model_raises():
    with pytest.raises(KeyError):
        set_promo("nope", 0.1)


# ---- pipeline ------------------------------------------------------------------

def _run(monkeypatch, page, extraction):
    calls = []
    monkeypatch.setattr(rp, "fetch_raw_text", lambda _u: page)
    monkeypatch.setattr(rp, "extract_model_comparison", lambda _r: calls.append(1) or extraction)
    return rp.run_pipeline("https://example.com", "hailuo-3", facts_only=True), calls


def test_promo_flow_keeps_the_list_price_shows_the_badge_and_clears_it_when_it_ends(monkeypatch):
    _run(monkeypatch, LIST_PAGE, _extraction(0.10, LIST_QUOTE))

    _run(monkeypatch, PROMO_PAGE, _extraction(0.05, PROMO_QUOTE))
    [record] = TestClient(app).get("/api/models").json()
    assert record["price_per_second_usd"] == 0.10 and record["promo_price_per_second_usd"] == 0.05

    _run(monkeypatch, LIST_PAGE, _extraction(0.10, LIST_QUOTE))  # the promotion is over
    [record] = TestClient(app).get("/api/models").json()
    assert record["price_per_second_usd"] == 0.10 and record["promo_price_per_second_usd"] is None


def test_a_promo_price_counts_as_confirmed_so_it_is_not_retried(monkeypatch):
    _run(monkeypatch, LIST_PAGE, _extraction(0.10, LIST_QUOTE))  # a verified list price exists now

    _verified, calls = _run(monkeypatch, PROMO_PAGE, _extraction(0.05, PROMO_QUOTE))

    assert len(calls) == 1


# ---- alerts on tracked models ----------------------------------------------------

def test_alerts_for_big_moves_and_promos_only():
    big = Verified(comparison=None, changes=[("price_per_second_usd", 0.10, 0.05)])
    small = Verified(comparison=None, changes=[("price_per_second_usd", 0.10, 0.105)])
    first = Verified(comparison=None, changes=[("price_per_second_usd", None, 0.10)])
    other = Verified(comparison=None, changes=[("max_reference_images", 2, 9)])
    promo = Verified(comparison=None, promo=(0.05, "50% off for a limited time"))

    assert "-50%" in tracked_price_alerts("k", big)[0]
    assert tracked_price_alerts("k", small) == []
    assert tracked_price_alerts("k", first) == []   # a first value is not a change
    assert tracked_price_alerts("k", other) == []
    assert "promotional" in tracked_price_alerts("k", promo)[0]
