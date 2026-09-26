from datetime import date

import pytest
from fastapi.testclient import TestClient

from market_intel import run_pipeline as rp
from market_intel.api import app
from market_intel.schema import FieldEvidence, ModelComparison, ModelExtraction
from market_intel.store import (
    load_all_comparisons,
    load_evidence,
    load_history,
    save_model_comparison,
    set_discontinued,
)
from market_intel.verify import ExtractionRejected, find_discontinuation

QUOTE = "For every second of 720p video you generated, you will be charged $0.3034/second"
PAGE = "# Seedance 2.0\n\n" + QUOTE + " and for 1080p you will be charged $0.682/second."


def _extraction(name="Seedance 2.0", with_price=True):
    return ModelExtraction(
        model_name=name,
        provider="ByteDance",
        price_per_second_usd=0.3034 if with_price else None,
        evidence=[FieldEvidence(field="price_per_second_usd", quote=QUOTE)] if with_price else [],
    )


def _script_llm(monkeypatch, extractions):
    """Makes the pipeline read PAGE and get the given extractions, one per call."""
    calls = []

    def fake_extract(_raw):
        calls.append(1)
        return extractions[min(len(calls), len(extractions)) - 1]

    monkeypatch.setattr(rp, "fetch_raw_text", lambda _url: PAGE)
    monkeypatch.setattr(rp, "extract_model_comparison", fake_extract)
    return calls


def _seed_verified_price():
    save_model_comparison(
        ModelComparison(model_name="Seedance 2.0", provider="ByteDance", price_per_second_usd=0.3034),
        "seedance-2.0", source_url="https://example.com", evidence={"price_per_second_usd": QUOTE},
    )


# ---- retry ------------------------------------------------------------------

def test_retries_when_a_previously_verified_field_does_not_come_back(monkeypatch):
    _seed_verified_price()
    calls = _script_llm(monkeypatch, [_extraction(with_price=False), _extraction()])

    verified = rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == 2
    assert "price_per_second_usd" in verified.evidence


def test_does_not_retry_when_everything_expected_came_back(monkeypatch):
    _seed_verified_price()
    calls = _script_llm(monkeypatch, [_extraction()])

    rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == 1


def test_does_not_go_fishing_for_fields_that_were_never_verified(monkeypatch):
    # No prior evidence: an empty answer is accepted at once, no extra calls.
    calls = _script_llm(monkeypatch, [_extraction(with_price=False)])

    verified = rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == 1
    assert verified.evidence == {}


def test_gives_up_after_max_attempts_without_failing_the_run(monkeypatch):
    _seed_verified_price()
    calls = _script_llm(monkeypatch, [_extraction(with_price=False)])

    verified = rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == rp.MAX_ATTEMPTS
    assert verified.evidence == {}
    # The previous verified value and its evidence are untouched.
    assert load_evidence()[("model", "seedance-2.0")]["price_per_second_usd"]["quote"] == QUOTE
    assert load_all_comparisons()[0].price_per_second_usd == 0.3034


def test_retries_a_rejected_target_and_recovers(monkeypatch):
    calls = _script_llm(monkeypatch, [_extraction(name="Seedance 1.0"), _extraction()])

    verified = rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == 2
    assert "price_per_second_usd" in verified.evidence


def test_still_raises_when_every_attempt_is_rejected(monkeypatch):
    calls = _script_llm(monkeypatch, [_extraction(name="Seedance 1.0")])

    with pytest.raises(ExtractionRejected):
        rp.run_pipeline("https://example.com", "seedance-2.0", facts_only=True)

    assert len(calls) == rp.MAX_ATTEMPTS


# ---- discontinuation detection ----------------------------------------------

@pytest.mark.parametrize(
    "text, today, expected",
    [
        ("This endpoint is deprecated This model is no longer supported.", date(2026, 9, 26), True),
        ("This endpoint will be shut down on September 24, 2026.", date(2026, 9, 26), True),
        # Same sentence before the date: only an announcement, the model is still available.
        ("This endpoint will be shut down on September 24, 2026.", date(2026, 9, 1), False),
        ("This endpoint will be deprecated on August 15, 2026. Migrate to LTX-2.3", date(2026, 9, 26), False),
        ("Realistic sunset tones, no background music. The model is great.", date(2026, 9, 26), False),
        ("This product has been discontinued.", date(2026, 9, 26), True),
        # Real false positive: an ACTIVE model whose page says its client library is deprecated.
        ("Note: @fal-ai/serverless-client is deprecated.", date(2026, 9, 26), False),
        ("The v1 SDK is no longer supported.", date(2026, 9, 26), False),
    ],
)
def test_find_discontinuation(text, today, expected):
    assert (find_discontinuation(text, today=today) is not None) is expected


def test_find_discontinuation_returns_the_matching_sentence():
    text = "Pricing is $0.1/s. This model is no longer supported. See docs."
    assert find_discontinuation(text, today=date(2026, 9, 26)) == "This model is no longer supported."


# ---- marking a model as discontinued -----------------------------------------

def test_set_discontinued_records_flag_evidence_and_history():
    save_model_comparison(ModelComparison(model_name="Sora 2", provider="OpenAI", price_per_second_usd=0.1), "sora-2")

    assert set_discontinued("sora-2", True, "This model is no longer supported.", "https://example.com") is True
    assert set_discontinued("sora-2", True, "again", "https://example.com") is False  # idempotent

    ev = load_evidence()[("model", "sora-2")]["discontinued"]
    assert ev["quote"] == "This model is no longer supported."
    history = load_history(entity_type="model", field="discontinued")
    assert [(h["old_value"], h["new_value"]) for h in history] == [(None, "True")]

    assert set_discontinued("sora-2", False) is True
    assert "discontinued" not in load_evidence().get(("model", "sora-2"), {})


def test_set_discontinued_unknown_model_raises():
    with pytest.raises(KeyError):
        set_discontinued("nope", True, "q", "u")


def test_api_exposes_discontinued_and_its_evidence():
    save_model_comparison(ModelComparison(model_name="Sora 2", provider="OpenAI"), "sora-2")
    save_model_comparison(ModelComparison(model_name="Veo 3.1", provider="Google"), "veo-3.1")
    set_discontinued("sora-2", True, "This model is no longer supported.", "https://example.com")

    by_key = {m["model_key"]: m for m in TestClient(app).get("/api/models").json()}

    assert by_key["sora-2"]["discontinued"] is True
    assert by_key["sora-2"]["evidence"]["discontinued"]["quote"] == "This model is no longer supported."
    assert by_key["veo-3.1"]["discontinued"] is None


def test_discontinued_command_marks_only_with_a_real_statement(monkeypatch):
    save_model_comparison(ModelComparison(model_name="Sora 2", provider="OpenAI"), "sora-2")

    monkeypatch.setattr(rp, "fetch_page_text", lambda _u: "Sora 2 pricing is $0.1/s. Great model.")
    with pytest.raises(ExtractionRejected):
        rp.run_discontinued_pipeline("sora-2", "https://example.com")

    monkeypatch.setattr(rp, "fetch_page_text", lambda _u: "This model is no longer supported.")  # never names Sora 2
    with pytest.raises(ExtractionRejected):
        rp.run_discontinued_pipeline("sora-2", "https://example.com")

    monkeypatch.setattr(rp, "fetch_page_text", lambda _u: "Sora 2. This endpoint is deprecated. This model is no longer supported.")
    rp.run_discontinued_pipeline("sora-2", "https://example.com")
    assert TestClient(app).get("/api/models").json()[0]["discontinued"] is True
