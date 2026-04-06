"""Classify Kalshi market titles into MLB market family buckets."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.constants import FAMILY_KEYWORDS, MLB_HINTS, SUPPORTED_FAMILIES, VENUE_KEYWORDS


@dataclass(slots=True, frozen=True)
class ClassificationResult:
    family: str | None
    is_mlb_like: bool
    reason: str


def classify_market_family(title: str, rules_text: str | None = None) -> ClassificationResult:
    """Classify a market title into one of the supported family buckets.

    Uses deterministic keyword rules — auditable and easy to tune.
    A market must contain a BASEBALL-SPECIFIC term from MLB_HINTS to be
    considered MLB at all; generic city/team names that overlap with other
    sports are intentionally excluded from that gate.
    """
    haystack = _normalize(" ".join(filter(None, [title, rules_text or ""])))

    if not _looks_like_mlb(haystack):
        return ClassificationResult(family=None, is_mlb_like=False, reason="No baseball-specific hints found")

    for family, keywords in FAMILY_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return ClassificationResult(family=family, is_mlb_like=True, reason=f"Matched {family} keywords")

    if _looks_like_venue_market(haystack):
        return ClassificationResult(family="venue", is_mlb_like=True, reason="Matched venue keywords")

    return ClassificationResult(family="generic_mlb", is_mlb_like=True, reason="MLB-like market, generic model")


def is_supported_market(title: str, rules_text: str | None = None) -> bool:
    result = classify_market_family(title, rules_text)
    return bool(result.is_mlb_like and result.family in SUPPORTED_FAMILIES)


def _looks_like_mlb(haystack: str) -> bool:
    return any(hint in haystack for hint in MLB_HINTS)


def _looks_like_venue_market(haystack: str) -> bool:
    return any(kw in haystack for kw in VENUE_KEYWORDS)


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
