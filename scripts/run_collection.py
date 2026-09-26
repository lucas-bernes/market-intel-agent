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
  - It ends with a compact one-line-per-target summary, also written to the
    GitHub Actions run page ($GITHUB_STEP_SUMMARY), so the outcome is readable
    without scrolling through the whole log.

Usage:
    python scripts/run_collection.py [path/to/targets.json]
"""

import json
import os
import sys
import traceback
from pathlib import Path

from market_intel.catalog import report_path, tracked_price_alerts
from market_intel.run_pipeline import run_pipeline, run_status_pipeline
from market_intel.verify import ExtractionRejected

DEFAULT_TARGETS_PATH = Path(__file__).resolve().parent.parent / "targets.json"

OK, NOTHING_NEW, FAILED = "ok", "no verified fields", "FAILED"


ALERTS: list[str] = []


def _run_target(label: str, action, key: str = "") -> tuple[str, str]:
    """Runs one target, prints its outcome, returns (status, detail)."""
    print(f"\n=== {label} ===")
    try:
        verified = action()
    except ExtractionRejected as error:
        print(f"  REJEITADO: {error}")
        return FAILED, f"rejected: {error}"
    except Exception as error:  # noqa: BLE001 - one bad target must not stop the run
        print("  ERRO inesperado:")
        traceback.print_exc()
        return FAILED, f"error: {type(error).__name__}: {error}"

    ALERTS.extend(tracked_price_alerts(key, verified))
    confirmed = ", ".join(verified.evidence) or "-"
    dropped = "; ".join(f"{field} ({reason})" for field, reason in verified.rejected.items())
    detail = f"confirmed: {confirmed}" + (f" | dropped: {dropped}" if dropped else "")
    return (OK if verified.evidence else NOTHING_NEW), detail


def _write_summary(results: list[tuple[str, str, str]]) -> None:
    print("\n=== summary ===")
    for label, status, detail in results:
        print(f"  {status:<18} {label:<28} {detail}")

    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["## Collection summary", "", "| Target | Status | Detail |", "|---|---|---|"]
    lines += [f"| {label} | {status} | {detail} |" for label, status, detail in results]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(targets_path: Path = DEFAULT_TARGETS_PATH) -> int:
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    ALERTS.clear()
    # A fresh report per job; scripts/scan_catalog.py appends its section to it later.
    report_path().unlink(missing_ok=True)

    results: list[tuple[str, str, str]] = []
    for target in targets.get("models", []):
        status, detail = _run_target(
            f"model {target['model_key']}",
            lambda t=target: run_pipeline(t["url"], t["model_key"], facts_only=True),
            key=target["model_key"],
        )
        results.append((target["model_key"], status, detail))

    for target in targets.get("provider_status", []):
        status, detail = _run_target(
            f"provider status {target['provider_key']}",
            lambda t=target: run_status_pipeline(t["status_url"], t["provider_name"], t["provider_key"], quiet=True),
        )
        results.append((target["provider_key"], status, detail))

    _write_summary(results)

    if ALERTS:
        print("\n=== alerts (tracked models) ===")
        print("\n".join(f"  {line}" for line in ALERTS))
        with report_path().open("a", encoding="utf-8") as handle:
            handle.write("## Tracked models: prices\n\n" + "\n".join(f"- {line}" for line in ALERTS) + "\n\n")

    failed =[label for label, status, _ in results if status == FAILED]
    print(f"\n{len(results) - len(failed)}/{len(results)} targets ran without a full rejection.")
    if failed:
        print(f"Targets that failed entirely (nothing was saved for them): {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    targets_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGETS_PATH
    sys.exit(main(targets_path))
