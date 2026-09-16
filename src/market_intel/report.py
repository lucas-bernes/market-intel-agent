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
        # Campos podem ser None (a página de origem não mencionava aquele
        # dado) — mostramos "N/A" em vez de fingir que o valor é 0/False.
        price = "N/A" if c.price_per_second_usd is None else f"{c.price_per_second_usd:.2f}"
        ref_imgs = "N/A" if c.max_reference_images is None else str(c.max_reference_images)
        prompt_tok = "N/A" if c.prompt_window_tokens is None else str(c.prompt_window_tokens)
        multi_shot = "N/A" if c.multi_shot_support is None else str(c.multi_shot_support)

        print(
            f"{c.model_name:<20} {c.provider:<12} {price:>8} "
            f"{ref_imgs:>9} {prompt_tok:>11} {multi_shot:>11}"
        )


if __name__ == "__main__":
    generate_report()
