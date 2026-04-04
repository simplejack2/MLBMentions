"""Helpers for classifying MLB mentions markets into model families."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.constants import FAMILY_KEYWORDS, MLB_HINTS, SUPPORTED_FAMILIES, VENUE_KEYWORDS
from app.schemas.market import Market


@dataclass(slots=True, frozen=True)
class ClassificationResult:
    family: str | None
    is_mlb_like: bool
    reason: str


def classify_market_family(title: str, rules_text: str | None = None) -> ClassificationResult:
    """Classify a market title into one of the supported family buckets.

    This starter intentionally uses deterministic keyword rules. They are easy to
    audit and easy to replace later with a richer classifier.
    """
    haystack = _normalize(" ".join(filter(None, [title, rules_text or ""])))
    is_mlb_like = _looks_like_mlb(haystack)

    if not is_mlb_like:
        return ClassificationResult(family=None, is_mlb_like=False, reason="No MLB/baseball hints found")

    for family, keywords in FAMILY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return ClassificationResult(family=family, is_mlb_like=True, reason=f"Matched {family} keywords")

    if _looks_like_venue_market(haystack):
        return ClassificationResult(family="venue", is_mlb_like=True, reason="Matched venue keywords")

    # Any MLB-like market gets the generic fallback so it reaches the model
    return ClassificationResult(family="generic_mlb", is_mlb_like=True, reason="MLB-like market, generic model")


def annotate_market_family(market: Market) -> Market:
    """Return a copy of the market with `market_family` populated."""
    result = classify_market_family(market.title, market.rules_primary)
    market.market_family = result.family
    return market


def is_supported_market(market: Market) -> bool:
    """Whether a market is MLB-like and belongs to a supported family."""
    result = classify_market_family(market.title, market.rules_primary)
    return bool(result.is_mlb_like and result.family in SUPPORTED_FAMILIES)


def _looks_like_mlb(haystack: str) -> bool:
    return any(hint in haystack for hint in MLB_HINTS)


def _looks_like_venue_market(haystack: str) -> bool:
    return any(keyword in haystack for keyword in VENUE_KEYWORDS)


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
