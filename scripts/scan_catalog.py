"""Scan the public catalogs of the aggregator platforms and report what changed.

    python scripts/scan_catalog.py                  # scan every platform, write the report
    python scripts/scan_catalog.py --digest         # fal.ai endpoints we do not track, by family
    python scripts/scan_catalog.py --mark-notified  # after the report was sent (GitHub issue)

Needs only DATABASE_URL: no LLM, no Firecrawl, no API keys.

The report (markdown) goes to $CATALOG_REPORT (default: catalog_report.md) and is
APPENDED to, because scripts/run_collection.py may already have written the
tracked-model price alerts there in the same job. Events that were detected but not
yet reported (e.g. the issue step failed last time) are included again.

Exit code 1 if any platform could not be read: a source that broke must be seen,
not silently skipped.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from market_intel.catalog import (
    SOURCES,
    SourceError,
    build_report,
    mark_notified,
    pending_events,
    report_path,
    scan_platform,
    untracked_digest,
)

ROOT = Path(__file__).resolve().parent.parent
FAL_PREFIX, LLMS_SUFFIX = "https://fal.ai/models/", "/llms.txt"


def tracked_fal_ids() -> set[str]:
    targets = json.loads((ROOT / "targets.json").read_text(encoding="utf-8"))
    ids = set()
    for target in targets.get("models", []):
        url = target["url"]
        if url.startswith(FAL_PREFIX) and url.endswith(LLMS_SUFFIX):
            ids.add(url[len(FAL_PREFIX):-len(LLMS_SUFFIX)])
    return ids


def digest() -> int:
    rows = untracked_digest("fal", tracked_fal_ids())
    if not rows:
        print("Nothing to show: no fal.ai scan stored yet (run the scan first).")
        return 0
    print(f"fal.ai endpoints not tracked, by family ({sum(n for _, n, _ in rows)} endpoints in {len(rows)} families):")
    for family, count, newest in rows[:40]:
        print(f"  {count:>3}  {family:<32} newest {newest}")
    return 0


def _write_step_summary(errors: dict[str, str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path or not errors:
        return
    lines = ["## Catalog scan: sources that failed", ""] + [f"- **{p}**: {m}" for p, m in errors.items()]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def scan() -> int:
    errors: dict[str, str] = {}
    for platform, (fetch, minimum) in SOURCES.items():
        try:
            items = fetch()
            if len(items) < minimum:
                raise SourceError(f"only {len(items)} items, expected at least {minimum} (page or API changed?)")
            result = scan_platform(platform, items)
        except Exception as error:  # noqa: BLE001 - one broken source must not stop the others
            errors[platform] = f"{type(error).__name__}: {error}"
            print(f"  {platform:<10} FAILED  {errors[platform]}")
            continue
        kinds: dict[str, int] = {}
        for event in result.events:
            kinds[event["kind"]] = kinds.get(event["kind"], 0) + 1
        label = "baseline recorded" if result.baseline else "compared with the previous scan"
        print(f"  {platform:<10} {result.total:>4} endpoints, {label}; new events: {kinds or 'none'}")

    # The issue is for real news only. A broken source already turns the run red
    # (and GitHub emails that); putting it in the issue too would open one every day
    # for as long as the source stays down.
    report = build_report(pending_events(), {})
    _write_step_summary(errors)
    if report:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with report_path().open("a", encoding="utf-8") as handle:
            handle.write(f"## Catalog watch — {stamp}\n\n{report}\n")
        print(f"\nReport written to {report_path()}")
    else:
        print("\nNothing new to report.")
    return 1 if errors else 0


if __name__ == "__main__":
    if "--mark-notified" in sys.argv:
        print(f"{mark_notified()} events marked as notified")
        sys.exit(0)
    sys.exit(digest() if "--digest" in sys.argv else scan())
