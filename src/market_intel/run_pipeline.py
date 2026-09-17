import sys

from .sources import fetch_raw_text, find_provider_info, find_review_text
from .extract import extract_model_comparison, extract_provider_comparison
from .store import save_model_comparison, save_provider_comparison
from .report import generate_report, generate_provider_report


def run_pipeline(url: str, model_key: str) -> None:
    raw_text = fetch_raw_text(url)
    comparison = extract_model_comparison(raw_text)
    save_model_comparison(comparison, model_key)
    generate_report()


def run_quality_pipeline(model_name: str, model_key: str) -> None:
    raw_text = find_review_text(model_name)
    comparison = extract_model_comparison(raw_text)
    save_model_comparison(comparison, model_key)
    generate_report()


def run_provider_pipeline(provider_name: str, provider_key: str) -> None:
    raw_text = find_provider_info(provider_name)
    comparison = extract_provider_comparison(raw_text)
    save_provider_comparison(comparison, provider_key)
    generate_provider_report()


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "url":
        run_pipeline(sys.argv[2], sys.argv[3])
    elif mode == "quality":
        run_quality_pipeline(sys.argv[2], sys.argv[3])
    elif mode == "provider":
        run_provider_pipeline(sys.argv[2], sys.argv[3])
    else:
        print("Uso: python -m market_intel.run_pipeline url <URL> <model_key>")
        print("  ou: python -m market_intel.run_pipeline quality <nome-do-modelo> <model_key>")
        print("  ou: python -m market_intel.run_pipeline provider <nome-do-provedor> <provider_key>")
