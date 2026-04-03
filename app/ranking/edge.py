"""Odds, probability, and edge helper functions."""

from __future__ import annotations


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability.

    Examples:
    -150 -> 0.60
    +200 -> 0.333333...
    """
    if odds == 0:
        raise ValueError("American odds cannot be 0")
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def implied_prob_to_american(probability: float) -> int:
    """Convert implied probability to American odds.

    This is mainly for display and sanity checks.
    """
    probability = clamp_probability(probability)
    if probability == 0.5:
        return 100
    if probability > 0.5:
        return round(-100.0 * probability / (1.0 - probability))
    return round(100.0 * (1.0 - probability) / probability)


def price_to_probability(price: float | None) -> float | None:
    """Convert a Kalshi-style YES price into probability.

    Accepts either:
    - a normalized decimal in [0, 1]
    - a cent-style number in [0, 100]
    """
    if price is None:
        return None
    price = float(price)
    if price < 0:
        raise ValueError("Price cannot be negative")
    if price <= 1:
        return clamp_probability(price)
    if price <= 100:
        return clamp_probability(price / 100.0)
    raise ValueError(f"Unexpected price scale: {price}")


def probability_to_price(probability: float) -> float:
    """Convert probability into normalized Kalshi YES price format [0, 1]."""
    return round(clamp_probability(probability), 6)


def compute_edge(model_probability: float, market_probability: float) -> float:
    """Return raw model edge above market implied probability."""
    return round(clamp_probability(model_probability) - clamp_probability(market_probability), 6)


def is_target_probability_band(
    probability: float,
    *,
    min_probability: float = 0.333333,
    max_probability: float = 0.60,
) -> bool:
    """Whether a market falls into the desired +200 through -150 band."""
    probability = clamp_probability(probability)
    return min_probability <= probability <= max_probability


def clamp_probability(probability: float) -> float:
    """Clamp a probability into [0, 1]."""
    return max(0.0, min(1.0, float(probability)))
