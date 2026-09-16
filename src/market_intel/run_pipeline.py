import sys

from .sources import fetch_raw_text
from .extract import extract_model_comparison
from .store import save_model_comparison
from .report import generate_report


def run_pipeline(url: str, model_key: str) -> None:
    raw_text = fetch_raw_text(url)
    comparison = extract_model_comparison(raw_text)
    save_model_comparison(comparison, model_key)
    generate_report()


if __name__ == "__main__":
    run_pipeline(sys.argv[1], sys.argv[2])
