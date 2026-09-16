from pathlib import Path
from .schema import ModelComparison

# Campos de fato: tratamos a primeira fonte que preencheu como confiável e
# não deixamos uma fonte seguinte (ex: um blog de review) sobrescrever com
# um número diferente — evita que preço/specs "flutuem" dependendo da ordem
# em que as páginas foram processadas.
PROTECTED_FIELDS = {
    "price_per_second_usd",
    "max_reference_images",
    "prompt_window_tokens",
    "multi_shot_support",
}

# Campos de texto livre: aqui o oposto faz sentido — várias fontes podem
# trazer ângulos diferentes sobre qualidade, então acumulamos em vez de
# descartar a informação antiga.
APPENDABLE_FIELDS = {"quality_notes", "notes"}


def save_model_comparison(comparison: ModelComparison, model_key: str) -> None:
    # Path(__file__) = caminho deste próprio arquivo (store.py).
    # Cada .parent sobe uma pasta, até chegar na raiz do projeto.
    project_root = Path(__file__).parent.parent.parent

    # Junta a raiz do projeto com "data/models" — o caminho da pasta de destino.
    models_dir = project_root / "data" / "models"

    # Garante que essa pasta existe antes de tentar salvar algo nela.
    models_dir.mkdir(parents=True, exist_ok=True)

    # O nome do arquivo agora vem do model_key escolhido por quem chama a
    # função — não mais do comparison.model_name, que o LLM extrai de forma
    # diferente a cada fonte ("Kling 3.0" vs "Kling 3.0 (VIDEO 3.0)"), o que
    # criava entradas duplicadas em vez de mesclar dados do mesmo modelo.
    safe_key = model_key.lower().replace(" ", "-").replace("/", "-")
    file_path = models_dir / f"{safe_key}.json"

    # Se já existe um registro salvo pra esse modelo (de uma extração
    # anterior, possivelmente de outra fonte), mescla em vez de sobrescrever,
    # com uma regra diferente por tipo de campo:
    if file_path.exists():
        existing = ModelComparison.model_validate_json(file_path.read_text(encoding="utf-8"))
        merged = existing.model_dump()
        for field, value in comparison.model_dump().items():
            if value is None:
                continue  # fonte atual não mencionou isso, mantém o que já tinha

            if field in PROTECTED_FIELDS and merged.get(field) is not None:
                continue  # já temos um valor de fato pra esse campo, não sobrescreve

            if field in APPENDABLE_FIELDS and merged.get(field):
                merged[field] = f"{merged[field]}\n\n---\n\n{value}"
                continue

            merged[field] = value
        comparison = ModelComparison(**merged)

    # Converte o objeto em texto JSON e escreve no arquivo.
    file_path.write_text(comparison.model_dump_json(), encoding="utf-8")