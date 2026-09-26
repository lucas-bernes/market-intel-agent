"""Promotional-price language, shared by the catalog watcher and the verifier.

Kept free of database imports on purpose: verify.py must stay pure.
"""

import re
from datetime import datetime, timezone
from typing import Optional

# Words that mean "this price is temporary". "volume discount" is NOT a promotion
# (permanent, tiered), so "discount" alone is deliberately absent.
PROMO_RE = re.compile(
    r"\b(?:promo(?:tion(?:al)?)?|limited[- ]time|special (?:offer|pricing|price)|"
    r"introductory|launch (?:price|pricing|offer)|early[- ]bird|"
    r"\d{1,3}\s?% off|(?:on )?sale|(?:until|through|ends?) (?:[A-Z][a-z]+ \d{1,2}|\d{4}-\d{2}-\d{2}))\b",
    re.IGNORECASE,
)

_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
           "november", "december"]
_MONTH_YEAR = re.compile(r"\b(" + "|".join(m.capitalize() for m in _MONTHS) + r") (\d{4})\b")


def find_promo(text: Optional[str]) -> Optional[str]:
    """Returns the promotional phrase found in the text, or None."""
    match = PROMO_RE.search(text or "")
    return match.group(0) if match else None


def stale_hint(text: Optional[str], today=None) -> Optional[str]:
    """A promo text that names a month already over ("20% off for February 2026") is probably expired."""
    today = today or datetime.now(timezone.utc).date()
    for month, year in _MONTH_YEAR.findall(text or ""):
        if (int(year), _MONTHS.index(month.lower()) + 1) < (today.year, today.month):
            return f"mentions {month} {year}, may be expired"
    return None


def promo_detail(text: Optional[str], phrase: str) -> str:
    hint = stale_hint(text)
    return f'"{phrase}"' + (f" ({hint})" if hint else "") + f": {text}"
