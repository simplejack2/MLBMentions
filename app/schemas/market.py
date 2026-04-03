"""Normalized market schema for Kalshi market data."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Market(BaseModel):
    """Normalized representation of a Kalshi market.

    The raw API payload contains more fields than this starter needs.
    This schema keeps the fields that matter for the first filtering and
    scoring pass.
    """

    model_config = ConfigDict(extra="allow")

    ticker: str
    title: str
    subtitle: str | None = None
    event_ticker: str | None = None
    series_ticker: str | None = None
    rules_primary: str | None = None
    yes_ask: float | None = None
    yes_bid: float | None = None
    yes_mid: float | None = None
    last_price: float | None = None
    implied_probability: float | None = None
    volume: float | None = None
    status: str | None = None
    close_time: str | None = None
    market_family: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def display_price(self) -> float | None:
        """Preferred price for board display and filtering.

        Preference order:
        1. midpoint of bid/ask if both exist
        2. ask price
        3. bid price
        4. last traded price
        """
        for value in (self.yes_mid, self.yes_ask, self.yes_bid, self.last_price):
            if value is not None:
                return value
        return None

    @property
    def spread(self) -> float | None:
        """Return bid/ask spread if both are available."""
        if self.yes_ask is None or self.yes_bid is None:
            return None
        return round(self.yes_ask - self.yes_bid, 6)
