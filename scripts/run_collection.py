"""Scheduled collection: walks targets.json and updates facts only.

Meant to run unattended (GitHub Actions cron). Differences from a manual
`run_pipeline` call:
  - Only fixed, pre-checked URLs are used — never search (`find_review_text` /
    `find_provider_info`), since a mistargeted search result could silently
    corrupt a record with nobody reviewing it.
  - `facts_only=True`: free-text fields (quality_notes/notes) are never
    touched, so nothing gets appended and duplicated on every run.
  - Each target is isolated: one failing target does not stop the others.
  - The script exits 1 if any *target* was fully rejected or errored — a
    rejected *field* inside an otherwise-good target (logged as DESCARTADO)
    is normal and does not fail the run.

Usage:
    python scripts/run_collection.py [path/to/targets.json]
"""

import json
import sys
import traceback
from pathlib import Path

from market_intel.run_pipeline import run_pipeline, run_status_pipeline
from market_intel.verify import ExtractionRejected

DEFAULT_TARGETS_PATH = Path(__file__).resolve().parent.parent / "targets.json"


def _run_target(label: str, action) -> bool:
    """Runs one target, prints its outcome, returns True if it succeeded."""
    print(f"\n=== {label} ===")
    try:
        action()
        return True
    except ExtractionRejected as error:
        print(f"  REJEITADO: {error}")
        return False
    except Exception:
        print("  ERRO inesperado:")
        traceback.print_exc()
        return False


def main(targets_path: Path = DEFAULT_TARGETS_PATH) -> int:
    targets = json.loads(targets_path.read_text(encoding="utf-8"))

    results = []
    for target in targets.get("models", []):
        ok = _run_target(
            f"model {target['model_key']}",
            lambda t=target: run_pipeline(t["url"], t["model_key"], facts_only=True),
        )
        results.append((target["model_key"], ok))

    for target in targets.get("provider_status", []):
        ok = _run_target(
            f"provider status {target['provider_key']}",
            lambda t=target: run_status_pipeline(t["status_url"], t["provider_name"], t["provider_key"]),
        )
        results.append((target["provider_key"], ok))

    failed = [key for key, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} alvos OK.")
    if failed:
        print(f"Alvos com falha total (nada foi salvo para eles): {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    targets_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGETS_PATH
    sys.exit(main(targets_path))
