from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ModelComparison(BaseModel):
    model_name: str = Field(
        description=(
            "Official product name with its version, in title case (e.g. "
            "'Kling 3.0', 'Veo 3.1'). No endpoint/task suffixes such as "
            "'Image to Video', no platform prefixes like 'fal-ai/'."
        ),
    )
    provider: str = Field(
        description=(
            "The company that created the model (e.g. 'OpenAI', 'ByteDance', "
            "'Alibaba'), NOT the platform hosting it (fal.ai, Replicate...)."
        ),
    )
    price_per_second_usd: Optional[float] = None
    max_reference_images: Optional[int] = None
    prompt_max_chars: Optional[int] = Field(
        default=None,
        description=(
            "Maximum prompt length, in CHARACTERS, accepted by the model's "
            "API (not tokens). Null if not stated."
        ),
    )
    multi_shot_support: Optional[bool] = None
    quality_notes: Optional[str] = Field(
        default=None,
        description=(
            "Summary of what reviews/benchmarks say about output quality: "
            "realism, visual consistency across frames, and known "
            "hallucination/artifact issues (e.g. distorted hands, drift)."
        ),
    )
    quality_score: Optional[float] = Field(
        default=None,
        description=(
            "The overall/aggregate quality score explicitly stated in a "
            "review, normalized to a 0-10 scale (e.g. '8.26/10' -> 8.26). "
            "Null if no clear overall numeric score is given in the text — "
            "do not invent or average sub-scores into one."
        ),
    )
    notes: Optional[str] = None


class ModelComparisonOut(ModelComparison):
    # Só existe na saída da API, não durante a extração via LLM — é o
    # identificador estável usado como chave no banco (o antigo nome de
    # arquivo), útil pro frontend referenciar uma linha específica (ex: pro
    # clique que abre o detalhe de um modelo).
    model_config = ConfigDict(from_attributes=True)

    model_key: str


class ProviderComparison(BaseModel):
    provider_name: str
    pricing_notes: Optional[str] = Field(
        default=None,
        description=(
            "How this provider's pricing/markup for hosting AI models works, "
            "if publicly disclosed (e.g. pay-as-you-go, revenue share, "
            "flat markup over compute cost)."
        ),
    )
    uptime_pct: Optional[float] = Field(
        default=None,
        description=(
            "MEASURED API uptime percentage over the last 90 days, taken from "
            "the provider's official status page. Do NOT put marketing claims "
            "or SLA promises here (leave null); those belong in stability_notes."
        ),
    )
    pricing_summary: Optional[str] = Field(
        default=None,
        description=(
            "Objective pricing summary in at most 12 words, e.g. 'Pay-as-you-go, "
            "per-output; GPUs from $1.89/h'. No marketing language."
        ),
    )
    stability_summary: Optional[str] = Field(
        default=None,
        description=(
            "Objective reliability summary in at most 12 words, e.g. 'Claims "
            "99.99% uptime; no incident history disclosed'. No marketing language."
        ),
    )
    stability_notes: Optional[str] = Field(
        default=None,
        description=(
            "What reviews, status pages, or user reports say about this "
            "provider's reliability/stability — known outages, incident "
            "history, or reputation for being flaky vs. rock-solid."
        ),
    )
    notes: Optional[str] = None


class ProviderComparisonOut(ProviderComparison):
    model_config = ConfigDict(from_attributes=True)

    provider_key: str