import pytest

from market_intel.schema import ModelComparison, ProviderComparison
from market_intel.store import (
    _sanitize_key,
    load_all_comparisons,
    load_all_providers,
    save_model_comparison,
    save_provider_comparison,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Kling 3.0", "kling-3.0"),
        ("fal-ai/flux/dev", "fal-ai-flux-dev"),
        ("seedance-2.5-(image-to-video)", "seedance-2.5-image-to-video"),
        ("  Weird   Name!!  ", "weird-name"),
    ],
)
def test_sanitize_key(raw, expected):
    assert _sanitize_key(raw) == expected


def test_save_creates_new_record():
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", price_per_second_usd=0.11),
        "kling-3.0",
    )

    [saved] = load_all_comparisons()
    assert saved.model_name == "Kling 3.0"
    assert saved.price_per_second_usd == 0.11


def test_protected_fields_are_not_overwritten_by_later_sources():
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", price_per_second_usd=0.11),
        "kling-3.0",
    )
    # Uma segunda fonte (ex: review que achou o modelo errado) tenta trocar tudo.
    save_model_comparison(
        ModelComparison(model_name="Outro Modelo", provider="Outra Empresa", price_per_second_usd=9.99),
        "kling-3.0",
    )

    [saved] = load_all_comparisons()
    assert saved.model_name == "Kling 3.0"
    assert saved.provider == "Kling AI"
    assert saved.price_per_second_usd == 0.11


def test_protected_field_is_filled_when_previously_empty():
    save_model_comparison(ModelComparison(model_name="Kling 3.0", provider="Kling AI"), "kling-3.0")
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", max_reference_images=4),
        "kling-3.0",
    )

    [saved] = load_all_comparisons()
    assert saved.max_reference_images == 4


def test_free_text_fields_accumulate():
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", quality_notes="Review A"),
        "kling-3.0",
    )
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", quality_notes="Review B"),
        "kling-3.0",
    )

    [saved] = load_all_comparisons()
    assert "Review A" in saved.quality_notes
    assert "Review B" in saved.quality_notes


def test_none_values_do_not_erase_existing_data():
    save_model_comparison(
        ModelComparison(model_name="Kling 3.0", provider="Kling AI", quality_notes="Review A"),
        "kling-3.0",
    )
    save_model_comparison(ModelComparison(model_name="Kling 3.0", provider="Kling AI"), "kling-3.0")

    [saved] = load_all_comparisons()
    assert saved.quality_notes == "Review A"


def test_providers_use_the_same_merge_rules():
    save_provider_comparison(
        ProviderComparison(provider_name="fal.ai", uptime_pct=99.99, pricing_notes="Pay as you go"),
        "fal-ai",
    )
    save_provider_comparison(
        ProviderComparison(provider_name="Groq", uptime_pct=50.0, pricing_notes="Per token"),
        "fal-ai",
    )

    [saved] = load_all_providers()
    assert saved.provider_name == "fal.ai"
    assert saved.uptime_pct == 99.99
    assert "Pay as you go" in saved.pricing_notes
    assert "Per token" in saved.pricing_notes
