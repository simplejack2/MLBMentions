"""Direct HTTP client for Kalshi public market data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.schemas.market import Market
from app.ranking.edge import clamp_probability, price_to_probability


class KalshiAPIError(RuntimeError):
    """Raised when Kalshi returns an unexpected response."""


@dataclass(slots=True)
class KalshiClient:
    """Minimal client for public Kalshi market data.

    This starter intentionally uses direct HTTP calls for public data instead of
    the authenticated SDK so the first scaffold stays easy to run.
    """

    base_url: str
    timeout: int = 20

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise KalshiAPIError(f"Unexpected payload type from {url}: {type(payload)!r}")
        return payload

    def get_open_markets(self, *, limit: int = 200, max_pages: int = 5) -> list[dict[str, Any]]:
        """Fetch open markets using Kalshi's paginated markets endpoint.

        This method is defensive about response shape because Kalshi's public API
        has evolved over time and can include cursor-based pagination.
        """
        all_markets: list[dict[str, Any]] = []
        cursor: str | None = None

        for _ in range(max_pages):
            params: dict[str, Any] = {"limit": limit, "status": "open"}
            if cursor:
                params["cursor"] = cursor

            payload = self._get("markets", params=params)
            page_markets = payload.get("markets", [])
            if not isinstance(page_markets, list):
                raise KalshiAPIError("Expected 'markets' to be a list in markets response")

            all_markets.extend(page_markets)
            cursor = payload.get("cursor") or payload.get("next_cursor")
            if not cursor:
                break

        return all_markets

    def get_market_by_ticker(self, ticker: str) -> dict[str, Any]:
        """Fetch one market by ticker."""
        return self._get(f"markets/{ticker}")

    def get_orderbook(self, ticker: str) -> dict[str, Any]:
        """Fetch orderbook data for a single market.

        The public API also supports multi-market orderbooks, but a single-market
        method is the simplest starter interface.
        """
        return self._get(f"markets/{ticker}/orderbook")

    def normalize_market(self, raw: dict[str, Any]) -> Market:
        """Normalize a raw Kalshi market payload into the local Market schema."""
        title = str(raw.get("title") or raw.get("subtitle") or raw.get("ticker") or "")

        yes_ask = _extract_first_number(
            raw,
            "yes_ask",
            "yes_ask_dollars",
            "yes_ask_price",
            "ask",
            "ask_price",
        )
        yes_bid = _extract_first_number(
            raw,
            "yes_bid",
            "yes_bid_dollars",
            "yes_bid_price",
            "bid",
            "bid_price",
        )
        last_price = _extract_first_number(
            raw,
            "last_price",
            "last_price_dollars",
            "yes_price",
            "yes_price_dollars",
        )
        yes_mid = None
        if yes_bid is not None and yes_ask is not None:
            yes_mid = round((yes_bid + yes_ask) / 2.0, 6)

        price = next((value for value in (yes_mid, yes_ask, yes_bid, last_price) if value is not None), None)
        implied_probability = clamp_probability(price_to_probability(price)) if price is not None else None

        return Market(
            ticker=str(raw.get("ticker") or ""),
            title=title,
            subtitle=_extract_text(raw, "subtitle", "market_title", "question"),
            event_ticker=_extract_text(raw, "event_ticker"),
            series_ticker=_extract_text(raw, "series_ticker"),
            rules_primary=_extract_text(raw, "rules_primary", "rules", "description"),
            yes_ask=yes_ask,
            yes_bid=yes_bid,
            yes_mid=yes_mid,
            last_price=last_price,
            implied_probability=implied_probability,
            volume=_extract_first_number(raw, "volume", "volume_dollars", "open_interest"),
            status=_extract_text(raw, "status"),
            close_time=_extract_text(raw, "close_time", "close_date"),
            raw=raw,
        )

    def get_normalized_open_markets(self, *, limit: int = 200, max_pages: int = 5) -> list[Market]:
        """Fetch and normalize open markets."""
        return [self.normalize_market(raw) for raw in self.get_open_markets(limit=limit, max_pages=max_pages)]


def _extract_first_number(raw: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        # Convert cent-style prices like 45 -> 0.45 when appropriate.
        if value > 1:
            if value <= 100:
                return round(value / 100.0, 6)
        return round(value, 6)
    return None


def _extract_text(raw: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
