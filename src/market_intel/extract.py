import json
import os
from typing import Optional, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from .schema import ModelComparison, ProviderComparison

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


def extract_model_comparison(raw_text: str) -> ModelComparison:
    return _extract(
        raw_text,
        ModelComparison,
        "extract_model_comparison",
        "Extrai dados de comparação de um modelo de IA a partir de um texto",
        "Extraia os dados de comparação do seguinte texto:",
    )


def extract_provider_comparison(raw_text: str) -> ProviderComparison:
    return _extract(
        raw_text,
        ProviderComparison,
        "extract_provider_comparison",
        "Extrai dados de comparação de um provedor de API de IA a partir de um texto",
        "Extraia os dados de comparação do provedor de API a partir do seguinte texto:",
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
