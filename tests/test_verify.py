import pytest

from market_intel.schema import FieldEvidence, ModelExtraction, ProviderExtraction
from market_intel.verify import (
    ExtractionRejected,
    check_field,
    normalize,
    same_model,
    verify_model_extraction,
    verify_provider_extraction,
    verify_uptime,
)

PAGE = """
# Seedance 2.0 Image to Video
For every second of 720p video you generated, you will be charged **$0.3034/second**.
Your request will cost $0.014 per 1000 tokens for 480p.
The prompt supports up to 1,500 characters.
Overall score: 8.4/10
"""


def _extraction(**kwargs):
    evidence = kwargs.pop("evidence", [])
    return ModelExtraction(
        model_name=kwargs.pop("model_name", "Seedance 2.0"),
        provider="ByteDance",
        evidence=[FieldEvidence(field=f, quote=q) for f, q in evidence],
        **kwargs,
    )


def test_accepts_field_with_real_quote_and_matching_number():
    ext = _extraction(
        price_per_second_usd=0.3034,
        evidence=[("price_per_second_usd", "you will be charged $0.3034/second")],
    )
    result = verify_model_extraction(ext, PAGE, "seedance-2.0")
    assert result.comparison.price_per_second_usd == 0.3034
    assert "price_per_second_usd" in result.evidence
    assert result.rejected == {}


def test_rejects_invented_quote():
    ext = _extraction(
        price_per_second_usd=0.30,
        evidence=[("price_per_second_usd", "costs $0.30 per second flat")],
    )
    result = verify_model_extraction(ext, PAGE, "seedance-2.0")
    assert result.comparison.price_per_second_usd is None
    assert "não encontrada" in result.rejected["price_per_second_usd"]


def test_rejects_number_not_in_quote():
    # Citação real, mas o LLM "calculou" outro valor a partir dela.
    ext = _extraction(
        price_per_second_usd=0.35,
        evidence=[("price_per_second_usd", "you will be charged $0.3034/second")],
    )
    result = verify_model_extraction(ext, PAGE, "seedance-2.0")
    assert result.comparison.price_per_second_usd is None
    assert "número" in result.rejected["price_per_second_usd"]


def test_rejects_per_token_price_read_as_per_second():
    ext = _extraction(
        price_per_second_usd=0.014,
        evidence=[("price_per_second_usd", "$0.014 per 1000 tokens for 480p")],
    )
    result = verify_model_extraction(ext, PAGE, "seedance-2.0")
    assert result.comparison.price_per_second_usd is None


def test_rejects_field_without_evidence():
    result = verify_model_extraction(_extraction(prompt_max_chars=1500), PAGE, "seedance-2.0")
    assert result.comparison.prompt_max_chars is None
    assert result.rejected["prompt_max_chars"] == "sem citação"


def test_thousands_separator_and_chars_keyword():
    ext = _extraction(
        prompt_max_chars=1500,
        evidence=[("prompt_max_chars", "The prompt supports up to 1,500 characters.")],
    )
    assert verify_model_extraction(ext, PAGE, "seedance-2.0").comparison.prompt_max_chars == 1500


def test_out_of_range_is_rejected():
    raw = normalize("Price: $50/second")
    assert "faixa" in check_field("price_per_second_usd", 50.0, "Price: $50/second", raw)


def test_quality_score_scale_conversion():
    raw = normalize("Total: 84/100 overall score")
    assert check_field("quality_score", 8.4, "Total: 84/100 overall score", raw) is None
    assert check_field("quality_score", 9.9, "Total: 84/100 overall score", raw) is not None


def test_wrong_target_rejects_whole_extraction():
    # Pedimos Seedance 2.0, a página/extração trouxe Seedance 1.0.
    with pytest.raises(ExtractionRejected):
        verify_model_extraction(_extraction(model_name="Seedance 1.0"), PAGE, "seedance-2.0")


def test_target_missing_from_text_rejects():
    with pytest.raises(ExtractionRejected):
        verify_model_extraction(_extraction(), "página sobre outro assunto", "seedance-2.0")


@pytest.mark.parametrize(
    "expected, actual, ok",
    [
        ("seedance-2.0", "Seedance 2.0", True),
        ("minimax-hailuo-2.3", "MiniMax Hailuo 2.3", True),
        ("sora-2", "Sora 2 Pro", False),  # variante = outro produto
        ("kling-3.0", "Kling 2.1", False),
        ("seedance-2.5-image-to-video", "Seedance 2.5", True),
    ],
)
def test_same_model(expected, actual, ok):
    assert same_model(expected, actual) is ok


def test_provider_wrong_target_is_rejected():
    ext = ProviderExtraction(provider_name="Groq")
    with pytest.raises(ExtractionRejected):
        verify_provider_extraction(ext, "Groq is fast. Baseten is mentioned once.", "Baseten")


def test_provider_uptime_needs_quote():
    page = "fal.ai API 99.97% uptime over 90 days"
    ext = ProviderExtraction(
        provider_name="fal.ai", uptime_pct=99.97,
        evidence=[FieldEvidence(field="uptime_pct", quote="API 99.97% uptime over 90 days")],
    )
    assert verify_provider_extraction(ext, page, "fal-ai").comparison.uptime_pct == 99.97


def test_verify_uptime_rejects_bad_quote():
    result = verify_uptime(99.9, "99.9% uptime", "fal.ai status page 99.5% uptime", "fal.ai")
    assert result.comparison.uptime_pct is None
    assert "uptime_pct" in result.rejected
