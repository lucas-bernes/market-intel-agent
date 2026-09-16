from .store import load_all_comparisons

MODEL_WIDTH = 24
PROVIDER_WIDTH = 16


def _truncate(text: str, width: int) -> str:
    # Corta textos longos (nomes de modelo variam muito de tamanho) em vez
    # de deixar eles "empurrarem" as colunas seguintes pra direita.
    return text if len(text) <= width else text[: width - 3] + "..."


def generate_report() -> None:
    comparisons = load_all_comparisons()

    if not comparisons:
        print("Nenhum modelo encontrado em data/models/.")
        return

    header = (
        f"{'Model':<{MODEL_WIDTH}} {'Provider':<{PROVIDER_WIDTH}} "
        f"{'$/s':>8} {'Ref imgs':>9} {'Prompt tok':>11} {'Multi-shot':>11}"
    )
    print(header)
    print("-" * len(header))
    for c in comparisons:
        # Campos podem ser None (a página de origem não mencionava aquele
        # dado) — mostramos "N/A" em vez de fingir que o valor é 0/False.
        price = "N/A" if c.price_per_second_usd is None else f"{c.price_per_second_usd:.2f}"
        ref_imgs = "N/A" if c.max_reference_images is None else str(c.max_reference_images)
        prompt_tok = "N/A" if c.prompt_window_tokens is None else str(c.prompt_window_tokens)
        multi_shot = "N/A" if c.multi_shot_support is None else str(c.multi_shot_support)
        model_name = _truncate(c.model_name, MODEL_WIDTH)
        provider = _truncate(c.provider, PROVIDER_WIDTH)

        print(
            f"{model_name:<{MODEL_WIDTH}} {provider:<{PROVIDER_WIDTH}} {price:>8} "
            f"{ref_imgs:>9} {prompt_tok:>11} {multi_shot:>11}"
        )

    # Seção separada pra qualidade: é texto longo (resumo de reviews), não
    # cabe numa coluna de tabela sem virar ilegível ou cortado demais.
    with_quality = [c for c in comparisons if c.quality_notes]
    if with_quality:
        print()
        print("Quality notes:")
        print("-" * len(header))
        for c in with_quality:
            print(f"\n{c.model_name}:")
            print(f"  {c.quality_notes}")


if __name__ == "__main__":
    generate_report()
