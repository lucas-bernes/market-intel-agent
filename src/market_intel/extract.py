import json
import os

from dotenv import load_dotenv
from openai import OpenAI

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
