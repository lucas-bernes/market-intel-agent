import sys
from pathlib import Path

from .extract import extract_model_comparison
from .store import save_model_comparison
from .report import generate_report


def run_pipeline(raw_text: str) -> None:
    comparison = extract_model_comparison(raw_text)
    save_model_comparison(comparison)
    generate_report()


if __name__ == "__main__":
    file_path = Path(sys.argv[1])
    raw_text = file_path.read_text()
    run_pipeline(raw_text)
