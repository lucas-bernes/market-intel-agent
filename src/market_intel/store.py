from pathlib import Path
from .schema import ModelComparison


def save_model_comparison(comparison: ModelComparison) -> None:
    # Path(__file__) = caminho deste próprio arquivo (store.py).
    # Cada .parent sobe uma pasta, até chegar na raiz do projeto.
    project_root = Path(__file__).parent.parent.parent

    # Junta a raiz do projeto com "data/models" — o caminho da pasta de destino.
    models_dir = project_root / "data" / "models"

    # Garante que essa pasta existe antes de tentar salvar algo nela.
    models_dir.mkdir(parents=True, exist_ok=True)

    # Transforma "Kling 3.0" em "kling-3.0", pra usar como nome de arquivo.
    safe_name = comparison.model_name.lower().replace(" ", "-")
    file_path = models_dir / f"{safe_name}.json"

    # Converte o objeto em texto JSON e escreve no arquivo.
    file_path.write_text(comparison.model_dump_json())