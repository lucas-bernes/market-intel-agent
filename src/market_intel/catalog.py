"""Watching aggregator catalogs: new / gone / repriced / promotional endpoints.

Every source below is public and needs no account or API key (Replicate,
WaveSpeed and Together were left out because their APIs answer 401 without one).
Nothing here uses an LLM or Firecrawl: it is plain HTTP plus deterministic parsing.

A daily scan turns each catalog into `CatalogItem`s and compares them with what the
previous scan stored. Differences become events; a human decides what to do with
them (an endpoint is never added to the ranking automatically, since each one needs
a decision: which model_key, which tier, which region, which resolution).

Safeguards, because a silent API hiccup must never look like "everything vanished":
  - a source that returns implausibly few items is rejected (SourceError), not diffed;
  - an endpoint is only reported "gone" after GONE_AFTER consecutive misses;
  - the first scan of a platform is a baseline: it records, but reports nothing.
"""

import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from .db import CatalogEntryRecord, CatalogEventRecord, SessionLocal
from .promo import find_promo, promo_detail, stale_hint

GONE_AFTER = 3  # consecutive scans without seeing an endpoint before it is "gone"
MIN_KEPT_RATIO = 0.5  # fewer than this fraction of the known items => reject the scan

_UA = {"User-Agent": "Mozilla/5.0"}


class SourceError(Exception):
    """A source answered, but not with a catalog we can trust. Nothing is diffed."""


@dataclass
class CatalogItem:
    endpoint_id: str
    title: str
    family: Optional[str] = None
    published_at: Optional[str] = None
    price_text: Optional[str] = None
    deprecated: bool = False  # the platform itself says so (flag, or a scheduled shutdown)
    note: Optional[str] = None


# ---- promotional language: see promo.py (shared with the verifier) ----------


# ---- helpers ----------------------------------------------------------------

def _http(url: str, limit: int = 8_000_000) -> str:
    request = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read(limit).decode("utf-8", errors="replace")


def _unflight(text: str) -> str:
    # Next.js embeds its data as JSON inside a JS string, so quotes arrive escaped.
    return text.replace('\\"', '"').replace("\\\\", "\\")


def _clean_price(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = text.replace("**", "").replace("$$", "$")
    text = " ".join(text.split())
    return text or None


def _truthy(value) -> bool:
    return str(value).strip().lower() == "true"


def _first(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None


def _balanced(text: str, start: int) -> str:
    """The JSON object/array starting at text[start] (which must be '{' or '['), string-aware."""
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth, in_string, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValueError("unbalanced JSON")


# ---- sources ----------------------------------------------------------------

def fetch_fal() -> list[CatalogItem]:
    """fal.ai's public model listing (paged JSON), image-to-video category."""
    items: list[CatalogItem] = []
    for page in range(1, 51):
        data = json.loads(_http(f"https://fal.ai/api/models?categories=image-to-video&page={page}"))
        for row in data["items"]:
            items.append(CatalogItem(
                endpoint_id=row["id"],
                title=row.get("title") or row["id"],
                family=row.get("modelFamily"),
                published_at=row.get("date"),
                price_text=_clean_price(row.get("pricingInfoOverride")),
                deprecated=_truthy(row.get("deprecated")) or _truthy(row.get("removed")),
            ))
        if page >= int(data.get("pages") or 1):
            break
    return items


def fetch_runware() -> list[CatalogItem]:
    """Runware's model page embeds one JSON object per model (status, shutdown date, price)."""
    page = _unflight(_http("https://runware.ai/models"))
    found: dict[str, CatalogItem] = {}
    for chunk in page.split('"air":"')[1:]:
        capabilities = _first(r'"capabilities":\[(.*?)\]', chunk) or ""
        if "io:image-to-video" not in capabilities:
            continue
        air = chunk.split('"', 1)[0]
        status = _first(r'"status":"(.*?)"', chunk) or ""
        deactivates = _first(r'"deactivatesAt":"(.*?)"', chunk)
        note = f"status: {status}" + (f", deactivates {deactivates[:10]}" if deactivates else "")
        found.setdefault(air, CatalogItem(
            endpoint_id=air,
            title=_first(r'"name":"(.*?)"', chunk) or air,
            family=_first(r'"creator":"(.*?)"', chunk),
            published_at=_first(r'"releasedAt":"(.*?)"', chunk),
            price_text=_clean_price(_first(r'"pricingOverview":"(.*?)"', chunk)),
            deprecated=status == "deprecated" or bool(deactivates),
            note=note,
        ))
    return list(found.values())


# Whole words only: "dream" used to match inside "Seedream", an IMAGE model.
_PIAPI_VIDEO = re.compile(
    r"\b(?:video|kling|luma|dream machine|hailuo|hunyuan|wan|seedance|sora|veo|pixverse|vidu)\b", re.IGNORECASE
)


def fetch_piapi() -> list[CatalogItem]:
    """PiAPI embeds its price tables (Kling and others) in the pricing page."""
    page = _unflight(_http("https://piapi.ai/pricing")).replace("$$", "$")
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'"group":"([^"]+)","link":', page)]
    items: dict[str, CatalogItem] = {}

    def add(group: str, name: str, price: str) -> None:
        if not _PIAPI_VIDEO.search(f"{group} {name}"):
            return
        endpoint_id = f"{group}/{name}"
        items.setdefault(endpoint_id, CatalogItem(endpoint_id=endpoint_id, title=f"{group} {name}", family=group,
                                                  price_text=_clean_price(price)))

    for index, (begin, group) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(page)
        section = page[begin:end]
        for match in re.finditer(r'"matrix":\{', section):
            try:
                matrix = json.loads(_balanced(section, match.end() - 1))
            except ValueError:
                continue
            for row in matrix.get("rows", []):
                for column, value in zip(matrix.get("columns", []), row.get("values", [])):
                    if value and any(ch.isdigit() for ch in str(value)):
                        add(group, f"{matrix.get('title', '')} {column} {row.get('label', '')}".strip(), str(value))
        for match in re.finditer(r'"label":"([^"]+)","lines":(\[.*?\])', section):
            for line in json.loads(match.group(2)):
                if "$" in line:
                    name, price = line.split("$", 1)
                    add(group, f"{match.group(1)} {name.strip()}", "$" + price)
    return list(items.values())


def fetch_aimlapi() -> list[CatalogItem]:
    """AIMLAPI's public model list; the video-generation entries, with release dates."""
    data = json.loads(_http("https://api.aimlapi.com/models", limit=20_000_000))
    items = []
    for row in data.get("data", []):
        if "video-generations" not in str(row.get("type")):
            continue
        info = row.get("info") or {}
        items.append(CatalogItem(
            endpoint_id=row["id"], title=info.get("name") or row["id"],
            family=info.get("developer"), published_at=info.get("releasedAt"),
        ))
    return items


_REPLICATE_NOT_MODELS = {
    "collections", "docs", "blog", "pricing", "explore", "changelog", "account", "playground", "about", "terms",
    "privacy", "support", "login", "signup", "guides", "home", "streaming", "opensource", "careers", "brand",
    "status", "auth", "api", "static", "assets", "cdn-cgi",
}


def fetch_replicate() -> list[CatalogItem]:
    """Replicate's public image-to-video collection (names only; the listing shows no price)."""
    page = _http("https://replicate.com/collections/image-to-video")
    slugs = sorted(set(re.findall(r'href="/([a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*)"', page)))
    return [
        CatalogItem(endpoint_id=slug, title=slug, family=slug.split("/")[0])
        for slug in slugs if slug.split("/")[0] not in _REPLICATE_NOT_MODELS
    ]


# platform -> (fetcher, minimum plausible number of items)
SOURCES: dict[str, tuple[Callable[[], list[CatalogItem]], int]] = {
    "fal": (fetch_fal, 100),
    "runware": (fetch_runware, 15),
    "piapi": (fetch_piapi, 5),
    "aimlapi": (fetch_aimlapi, 100),
    "replicate": (fetch_replicate, 15),
}


# ---- diff ---------------------------------------------------------------------

_MONEY = re.compile(r"\$\s*(\d+(?:\.\d+)?)")


def price_change_pct(old: Optional[str], new: Optional[str]) -> Optional[float]:
    """Largest % change between the dollar amounts of two price texts.

    0.0 = same amounts (only the wording changed); None = the amounts are not
    comparable one-to-one (a different number of prices, or a price appeared/vanished).
    """
    old_amounts = [float(x) for x in _MONEY.findall(old or "")]
    new_amounts = [float(x) for x in _MONEY.findall(new or "")]
    if old_amounts == new_amounts:
        return 0.0
    if not old_amounts or len(old_amounts) != len(new_amounts):
        return None
    return max(abs(n - o) / o * 100 for o, n in zip(old_amounts, new_amounts) if o) if any(old_amounts) else None


@dataclass
class ScanResult:
    platform: str
    total: int
    baseline: bool
    events: list[dict] = field(default_factory=list)


def scan_platform(platform: str, items: list[CatalogItem], now: Optional[datetime] = None) -> ScanResult:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as session:
        rows = {r.endpoint_id: r for r in session.query(CatalogEntryRecord).filter_by(platform=platform)}
        baseline = not rows

        known_alive = [r for r in rows.values() if r.status != "gone"]
        if known_alive and len(items) < MIN_KEPT_RATIO * len(known_alive):
            raise SourceError(
                f"{platform}: only {len(items)} items now vs {len(known_alive)} known; "
                "not diffing (looks like a broken page/API, not a mass removal)"
            )

        events: list[dict] = []

        def emit(item_id: str, title: str, kind: str, detail: Optional[str] = None) -> None:
            events.append({"platform": platform, "endpoint_id": item_id, "title": title, "kind": kind, "detail": detail})
            session.add(CatalogEventRecord(platform=platform, endpoint_id=item_id, title=title, kind=kind,
                                           detail=detail, detected_at=now))

        seen = set()
        for item in items:
            seen.add(item.endpoint_id)
            status = "deprecated" if item.deprecated else "active"
            row = rows.get(item.endpoint_id)

            if row is None:
                session.add(CatalogEntryRecord(
                    platform=platform, endpoint_id=item.endpoint_id, title=item.title, family=item.family,
                    published_at=item.published_at, price_text=item.price_text, note=item.note, status=status,
                    missing_scans=0, first_seen_at=now, last_seen_at=now,
                ))
                if not baseline:
                    emit(item.endpoint_id, item.title, "new", " | ".join(
                        x for x in (item.family, (item.published_at or "")[:10], item.price_text) if x))
                # Promotions are reported even on the baseline scan: they are time-limited,
                # so waiting for the "next change" would mean hearing about them too late.
                promo = find_promo(item.price_text)
                if promo:
                    emit(item.endpoint_id, item.title, "promo", promo_detail(item.price_text, promo))
                continue

            if row.status == "gone":
                emit(item.endpoint_id, item.title, "returned", "listed again after being gone")
            if status == "deprecated" and row.status != "deprecated":
                emit(item.endpoint_id, item.title, "deprecated", item.note or "flagged deprecated by the platform")

            old_price = row.price_text
            if item.price_text and old_price != item.price_text:
                pct = price_change_pct(old_price, item.price_text)
                promo = find_promo(item.price_text) if not find_promo(old_price) else None
                if promo:
                    emit(item.endpoint_id, item.title, "promo", promo_detail(item.price_text, promo))
                elif pct != 0.0:
                    change = "" if pct is None else f" ({pct:+.0f}% at most)"
                    emit(item.endpoint_id, item.title, "price_changed", f"{old_price or '-'} -> {item.price_text}{change}")

            row.title, row.family, row.published_at = item.title, item.family, item.published_at
            row.price_text = item.price_text or row.price_text
            row.note, row.status, row.missing_scans, row.last_seen_at = item.note, status, 0, now

        for endpoint_id, row in rows.items():
            if endpoint_id in seen or row.status == "gone":
                continue
            row.missing_scans += 1
            if row.missing_scans >= GONE_AFTER:
                row.status = "gone"
                emit(endpoint_id, row.title, "gone", f"missing from {GONE_AFTER} consecutive scans")

        session.commit()
        return ScanResult(platform=platform, total=len(items), baseline=baseline, events=events)


# ---- report -------------------------------------------------------------------

_KIND_TITLES = {
    "gone": "Gone from the catalog",
    "deprecated": "Deprecated / scheduled to shut down",
    "promo": "Promotional pricing",
    "price_changed": "Price changed",
    "new": "New endpoints",
    "returned": "Returned",
}
MAX_PER_GROUP = 25


def build_report(events: list[dict], errors: dict[str, str]) -> str:
    """Markdown for the GitHub issue; empty string when there is nothing to report."""
    if not events and not errors:
        return ""
    lines = []
    for platform, message in errors.items():
        lines += [f"**Source problem — {platform}:** {message}", ""]
    for kind, title in _KIND_TITLES.items():
        group = [e for e in events if e["kind"] == kind]
        if not group:
            continue
        lines.append(f"### {title} ({len(group)})")
        for event in group[:MAX_PER_GROUP]:
            detail = f" — {event['detail']}" if event.get("detail") else ""
            lines.append(f"- `{event['platform']}` **{event['title']}** (`{event['endpoint_id']}`){detail}")
        if len(group) > MAX_PER_GROUP:
            lines.append(f"- … and {len(group) - MAX_PER_GROUP} more (see the `catalog_events` table)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def mark_notified(now: Optional[datetime] = None) -> int:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as session:
        rows = session.query(CatalogEventRecord).filter(CatalogEventRecord.notified_at.is_(None)).all()
        for row in rows:
            row.notified_at = now
        session.commit()
        return len(rows)


def pending_events() -> list[dict]:
    """Events detected but not yet sent to the issue (a failed issue step is retried next run)."""
    with SessionLocal() as session:
        rows = (
            session.query(CatalogEventRecord)
            .filter(CatalogEventRecord.notified_at.is_(None))
            .order_by(CatalogEventRecord.detected_at, CatalogEventRecord.id)
            .all()
        )
        return [
            {"platform": r.platform, "endpoint_id": r.endpoint_id, "title": r.title, "kind": r.kind, "detail": r.detail}
            for r in rows
        ]


def untracked_digest(platform: str, tracked_ids: set[str]) -> list[tuple[str, int, str]]:
    """(family, endpoints, newest endpoint date) of active endpoints we do not track, most endpoints first."""
    with SessionLocal() as session:
        rows = session.query(CatalogEntryRecord).filter_by(platform=platform).filter(
            CatalogEntryRecord.status != "gone").all()
    families: dict[str, list] = {}
    for row in rows:
        if row.endpoint_id.lower() in {t.lower() for t in tracked_ids}:
            continue
        families.setdefault(row.family or "(no family)", []).append(row)
    return sorted(
        ((name, len(group), max((r.published_at or "")[:10] for r in group)) for name, group in families.items()),
        key=lambda item: (-item[1], item[0]),
    )


__all__ = [
    "CatalogItem", "SourceError", "ScanResult", "SOURCES", "find_promo", "stale_hint", "promo_detail",
    "price_change_pct", "scan_platform",
    "build_report", "mark_notified", "pending_events", "untracked_digest",
]


# ---- tracked models: price alerts ---------------------------------------------

PRICE_ALERT_PCT = 10.0


def report_path():
    """Where the markdown report for the GitHub issue is written (shared by both scripts)."""
    from pathlib import Path
    import os

    return Path(os.environ.get("CATALOG_REPORT", "catalog_report.md"))


def tracked_price_alerts(key: str, verified) -> list[str]:
    """Alert lines for one tracked model after a collection run.

    A list-price move of PRICE_ALERT_PCT or more (a price cut, an increase, or an
    extraction that slipped past the checks) and any promotional price get a line,
    so a human looks at them instead of finding out from the chart.
    """
    lines = []
    if verified.promo:
        lines.append(f"`{key}`: promotional price detected, {verified.promo[0]} $/s — {verified.promo[1][:200]}")
    for field_name, old, new in verified.changes:
        if field_name != "price_per_second_usd" or not old or new is None:
            continue
        pct = (new - old) / old * 100
        if abs(pct) >= PRICE_ALERT_PCT:
            lines.append(f"`{key}`: list price {old} -> {new} $/s ({pct:+.0f}%)")
    return lines
