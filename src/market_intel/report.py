from pathlib import Path
from .schema import ModelComparison


def generate_report() -> None:
    project_root = Path(__file__).parent.parent.parent
    models_dir = project_root / "data" / "models"

    if not models_dir.exists():
        print("Nenhum modelo encontrado em data/models/.")
        return

    comparisons = [
        ModelComparison.model_validate_json(file_path.read_text())
        for file_path in models_dir.iterdir()
        if file_path.suffix == ".json"
    ]

    if not comparisons:
        print("Nenhum modelo encontrado em data/models/.")
        return

    header = f"{'Model':<20} {'Provider':<12} {'$/s':>8} {'Ref imgs':>9} {'Prompt tok':>11} {'Multi-shot':>11}"
    print(header)
    print("-" * len(header))
    for c in comparisons:
        print(
            f"{c.model_name:<20} {c.provider:<12} {c.price_per_second_usd:>8.2f} "
            f"{c.max_reference_images:>9} {c.prompt_window_tokens:>11} {str(c.multi_shot_support):>11}"
        )


if __name__ == "__main__":
    generate_report()
