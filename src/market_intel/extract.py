import anthropic
from .schema import ModelComparison


def extract_model_comparison(raw_text: str) -> ModelComparison:
    client = anthropic.Anthropic()

    # Get ModelComparison's "shape" as a JSON Schema, so the API knows
    # exactly which fields and types it needs to fill in.
    schema = ModelComparison.model_json_schema()

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        # This isn't a real action (nothing gets executed) — it's just a
        # "form" we force the model to fill instead of replying with free text.
        tools=[
            {
                "name": "extract_model_comparison",
                "description": "Extrai dados de comparação de um modelo de IA a partir de um texto",
                "input_schema": schema,
            }
        ],
        # Forced (not "auto"): without this, the model could reply with
        # plain text instead of filling in the form.
        tool_choice={"type": "tool", "name": "extract_model_comparison"},
        messages=[
            {
                "role": "user",
                "content": f"Extraia os dados de comparação do seguinte texto:\n\n{raw_text}",
            }
        ],
    )

    # response.content is a list of blocks (text + tool_use can come mixed
    # together in other scenarios) — so we filter by type instead of just
    # grabbing response.content[0].
    tool_block = next(b for b in response.content if b.type == "tool_use")
    dados = tool_block.input  # already a plain Python dict, no manual parsing

    # **dados "unpacks" the dict into named arguments: equivalent to writing
    # ModelComparison(model_name=..., price_per_second_usd=..., ...) by hand.
    # This is where Pydantic's type validation actually happens.
    return ModelComparison(**dados)
