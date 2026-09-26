from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ModelComparison(BaseModel):
    model_name: str = Field(
        description=(
            "Official product name with its version, in title case (e.g. "
            "'Kling 3.0', 'Veo 3.1'). No endpoint/task suffixes such as "
            "'Image to Video', no platform prefixes like 'fal-ai/', and no "
            "pricing-tier/quality suffixes such as 'Pro', 'Standard', 'Fast' "
            "or 'Turbo' even if the page title includes one."
        ),
    )
    provider: str = Field(
        description=(
            "The company that created the model (e.g. 'OpenAI', 'ByteDance', "
            "'Alibaba'), NOT the platform hosting it (fal.ai, Replicate...)."
        ),
    )
    price_per_second_usd: Optional[float] = Field(
        default=None,
        description=(
            "Price in USD per second of generated video at 720p, the reference "
            "resolution used to compare models. If the text lists one price per "
            "resolution, use the 720p one and quote that sentence. If it only "
            "lists other resolutions, or a price per video/image/token instead of "
            "per second, leave null."
        ),
    )
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


class FieldEvidence(BaseModel):
    # Uma "prova" por campo: a frase COPIADA do texto que justifica o valor.
    # O código (verify.py) confere depois se a frase existe mesmo no texto e
    # se o número está nela — o LLM não é confiável sozinho.
    field: str = Field(description="Exact name of the field this quote supports, e.g. 'price_per_second_usd'.")
    quote: str = Field(
        description=(
            "Sentence or table row copied VERBATIM (character for character) "
            "from the text, containing the value. Never paraphrase or compute."
        ),
    )


_EVIDENCE_RULES = (
    "For EVERY non-null value among {fields}, add one item with the field name "
    "and a verbatim quote from the text that states that value. If you cannot "
    "quote it word for word, leave the field null — do not derive, convert, "
    "average or guess values. Silence in the text means null, never false/0."
)


class ModelExtraction(ModelComparison):
    # Só existe na etapa de extração: ModelComparison continua sendo o formato
    # que é salvo no banco e servido pela API.
    evidence: list[FieldEvidence] = Field(
        default_factory=list,
        description=_EVIDENCE_RULES.format(
            fields="price_per_second_usd, max_reference_images, prompt_max_chars, multi_shot_support, quality_score"
        ),
    )


class HistoryEntryOut(BaseModel):
    # Uma mudança de valor já confirmada — a "prova" de cada uma é a mesma
    # regra de verify.py, aplicada no momento em que ela foi salva.
    entity_type: str
    entity_key: str
    field: str
    old_value: Optional[str] = None
    new_value: str
    source_url: Optional[str] = None
    changed_at: str


class EvidenceOut(BaseModel):
    quote: str
    source_url: Optional[str] = None
    collected_at: str


class ModelComparisonOut(ModelComparison):
    # Só existe na saída da API, não durante a extração via LLM — é o
    # identificador estável usado como chave no banco (o antigo nome de
    # arquivo), útil pro frontend referenciar uma linha específica (ex: pro
    # clique que abre o detalhe de um modelo).
    model_config = ConfigDict(from_attributes=True)

    model_key: str
    # Só existe na saída: quem marca é store.set_discontinued, nunca a extração.
    discontinued: Optional[bool] = None
    # Só saída: quem preenche é store.set_promo. Fora do ranking, com selo na tela.
    promo_price_per_second_usd: Optional[float] = None
    # Prova de cada campo verificado; campo ausente aqui = sem evidência.
    evidence: dict[str, EvidenceOut] = Field(default_factory=dict)


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
            "99.99% uptime; no incident history disclosed'. No marketing language. "
            "Do NOT state the measured uptime percentage: it lives in uptime_pct, "
            "is refreshed daily, and a number written here would go stale."
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


class ProviderExtraction(ProviderComparison):
    evidence: list[FieldEvidence] = Field(
        default_factory=list,
        description=_EVIDENCE_RULES.format(fields="uptime_pct"),
    )


class ProviderComparisonOut(ProviderComparison):
    model_config = ConfigDict(from_attributes=True)

    provider_key: str
    evidence: dict[str, EvidenceOut] = Field(default_factory=dict)