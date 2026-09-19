import json
import os
from typing import Optional, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from .schema import ModelExtraction, ProviderExtraction

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEP_SEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    timeout=120.0,
)

T = TypeVar("T", bound=BaseModel)


def _extract(raw_text: str, schema_cls: type[T], tool_name: str, description: str, instruction: str) -> T:
    # Função genérica de extração via tool use forçado — usada por todas as
    # variantes abaixo, mudando só o schema, o nome da tool e a instrução.
    # Extrair isso pra um lugar só evita repetir a mesma mecânica 3x.
    schema = schema_cls.model_json_schema()

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": f"{instruction}\n\n{raw_text}"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": schema,
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": tool_name}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    dados = json.loads(tool_call.function.arguments)

    return schema_cls(**dados)


# Regra anexada a toda extração de fatos: qualidade > cobertura. Um campo
# vazio é aceitável; um campo errado não é.
_ACCURACY_RULES = (
    "Accuracy rules: extract only what the text states about the model/provider "
    "named in it. Use null for anything not explicitly stated — never infer, "
    "convert units, compute or guess. Every numeric/boolean fact needs a "
    "verbatim quote in `evidence`."
)


def extract_model_comparison(raw_text: str) -> ModelExtraction:
    return _extract(
        raw_text,
        ModelExtraction,
        "extract_model_comparison",
        "Extrai dados de comparação de um modelo de IA a partir de um texto",
        f"Extraia os dados de comparação do seguinte texto. {_ACCURACY_RULES}",
    )


def extract_provider_comparison(raw_text: str) -> ProviderExtraction:
    return _extract(
        raw_text,
        ProviderExtraction,
        "extract_provider_comparison",
        "Extrai dados de comparação de um provedor de API de IA a partir de um texto",
        f"Extraia os dados de comparação do provedor de API a partir do seguinte texto. {_ACCURACY_RULES}",
    )


class _StatusUptime(BaseModel):
    api_uptime_pct: Optional[float] = Field(
        default=None,
        description=(
            "Measured uptime percentage over the period shown on this status "
            "page, for the provider's main inference/model API component ONLY "
            "(never the website, dashboard or docs). If several API components "
            "are listed, use the LOWEST of them. Null if the page shows no "
            "uptime percentage for an API component."
        ),
    )
    component_used: Optional[str] = Field(
        default=None,
        description="Name of the status-page component the number came from.",
    )
    evidence_quote: Optional[str] = Field(
        default=None,
        description=(
            "The line copied VERBATIM from the page that shows the uptime "
            "percentage for that component (must contain the number). Null "
            "if api_uptime_pct is null."
        ),
    )


def extract_status_uptime(status_page_text: str) -> _StatusUptime:
    return _extract(
        status_page_text,
        _StatusUptime,
        "extract_status_uptime",
        "Extrai o uptime medido do componente de API a partir de uma página de status",
        "Extraia o uptime medido da API a partir da seguinte página de status:",
    )


class _QualityScoreExtraction(BaseModel):
    quality_score: Optional[float] = Field(
        default=None,
        description=(
            "The overall/aggregate quality score explicitly stated in the "
            "text, normalized to a 0-10 scale. Null if no clear overall "
            "numeric score is given — do not invent or average sub-scores."
        ),
    )


def extract_quality_score(quality_notes: str) -> Optional[float]:
    # Não reaproveita _extract com ModelComparison porque o texto de
    # quality_notes não menciona o nome do modelo explicitamente — exigir
    # isso quebraria a extração. Aqui só pedimos o número.
    result = _extract(
        quality_notes,
        _QualityScoreExtraction,
        "extract_quality_score",
        "Extrai a nota numérica geral de qualidade mencionada no texto",
        "Extraia a nota de qualidade geral do seguinte texto:",
    )
    return result.quality_score
