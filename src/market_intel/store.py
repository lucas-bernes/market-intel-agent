from pathlib import Path
from .schema import ModelComparison


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
    # anterior, possivelmente de outra fonte), mescla em vez de sobrescrever:
    # cada campo novo que veio preenchido (não-None) substitui o antigo;
    # campos que a fonte atual não mencionou (vieram None) mantêm o valor
    # que já estava salvo, em vez de apagá-lo.
    if file_path.exists():
        existing = ModelComparison.model_validate_json(file_path.read_text(encoding="utf-8"))
        merged = existing.model_dump()
        for field, value in comparison.model_dump().items():
            if value is not None:
                merged[field] = value
        comparison = ModelComparison(**merged)

    # Converte o objeto em texto JSON e escreve no arquivo.
    file_path.write_text(comparison.model_dump_json(), encoding="utf-8")