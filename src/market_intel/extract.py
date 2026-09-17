import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional

from .schema import ModelComparison

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEP_SEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    timeout=120.0,
)


def extract_model_comparison(raw_text: str) -> ModelComparison:
    schema = ModelComparison.model_json_schema()

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": f"Extraia os dados de comparação do seguinte texto:\n\n{raw_text}",
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_model_comparison",
                    "description": "Extrai dados de comparação de um modelo de IA a partir de um texto",
                    "parameters": schema,
                },
            }
        ],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_model_comparison"},
        },
    )

    tool_call = response.choices[0].message.tool_calls[0]
    dados = json.loads(tool_call.function.arguments)

    return ModelComparison(**dados)


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
    # Função separada (não reaproveita extract_model_comparison) porque o
    # texto de quality_notes não menciona o nome do modelo explicitamente —
    # exigir isso quebraria a extração. Aqui só pedimos o número.
    schema = _QualityScoreExtraction.model_json_schema()

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": f"Extraia a nota de qualidade geral do seguinte texto:\n\n{quality_notes}",
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_quality_score",
                    "description": "Extrai a nota numérica geral de qualidade mencionada no texto",
                    "parameters": schema,
                },
            }
        ],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_quality_score"},
        },
    )

    tool_call = response.choices[0].message.tool_calls[0]
    dados = json.loads(tool_call.function.arguments)

    return _QualityScoreExtraction(**dados).quality_score
