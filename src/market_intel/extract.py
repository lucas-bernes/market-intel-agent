import anthropic
from .schema import ModelComparison


def extract_model_comparison(raw_text: str) -> ModelComparison:
    client = anthropic.Anthropic()

    # Pega a "forma" do ModelComparison como JSON Schema, pra API saber
    # exatamente quais campos e tipos ela precisa preencher.
    schema = ModelComparison.model_json_schema()

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        # Isso não é uma ação real (não executa nada) — é só um "formulário"
        # que forçamos o modelo a preencher em vez de responder com texto livre.
        tools=[
            {
                "name": "extract_model_comparison",
                "description": "Extrai dados de comparação de um modelo de IA a partir de um texto",
                "input_schema": schema,
            }
        ],
        # Forçado (não "auto"): sem isso, o modelo poderia responder só com
        # texto solto em vez de preencher o formulário.
        tool_choice={"type": "tool", "name": "extract_model_comparison"},
        messages=[
            {
                "role": "user",
                "content": f"Extraia os dados de comparação do seguinte texto:\n\n{raw_text}",
            }
        ],
    )

    # response.content é uma lista de blocos (podem vir texto + tool_use
    # misturados em outros cenários) — por isso filtramos pelo tipo certo
    # em vez de simplesmente pegar response.content[0].
    tool_block = next(b for b in response.content if b.type == "tool_use")
    dados = tool_block.input  # já vem como dict Python, sem parsing manual

    # **dados "abre" o dict em argumentos nomeados: equivale a escrever
    # ModelComparison(model_name=..., price_per_second_usd=..., ...) na mão.
    # É aqui que a validação de tipos do Pydantic acontece de fato.
    return ModelComparison(**dados)
