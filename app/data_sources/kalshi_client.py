"""Direct HTTP client for Kalshi public market data.

Architecture note
-----------------
Kalshi's open markets feed consists almost entirely of KXMV multi-sport parlay
markets. Individual MLB game markets (run totals, run lines, player props) are
referenced as *legs* inside those parlays via the `mve_selected_legs` field,
with event tickers of the form:

    KXMLBTOTAL-26APR062040HOUCOL   (run-total event for HOU @ COL)
    KXMLBSPREAD-26APR061907LADTOR  (run-line event for LAD @ TOR)

`get_mlb_markets()` extracts those event tickers from the parlay feed and
then fetches the individual KXMLB markets directly, which ARE priced.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from app.ranking.edge import clamp_probability, price_to_probability
from app.schemas.market import Market

log = logging.getLogger(__name__)


class KalshiAPIError(RuntimeError):
    """Raised when Kalshi returns an unexpected response."""


@dataclass(slots=True)
class KalshiClient:
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

    # ------------------------------------------------------------------
    # Raw fetchers
    # ------------------------------------------------------------------

    def get_open_markets(self, *, limit: int = 200, max_pages: int = 5) -> list[dict[str, Any]]:
        """Fetch open/active markets with cursor pagination."""
        all_markets: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(max_pages):
            params: dict[str, Any] = {"limit": limit, "status": "open"}
            if cursor:
                params["cursor"] = cursor
            payload = self._get("markets", params=params)
            page = payload.get("markets", [])
            if not isinstance(page, list):
                raise KalshiAPIError("Expected 'markets' list in response")
            all_markets.extend(page)
            cursor = payload.get("cursor") or payload.get("next_cursor")
            if not cursor:
                break
        return all_markets

    def get_markets_for_event(self, event_ticker: str) -> list[dict[str, Any]]:
        """Fetch all open markets for a single event ticker."""
        try:
            payload = self._get("markets", params={
                "event_ticker": event_ticker,
                "status": "open",
                "limit": 200,
            })
            return payload.get("markets", [])
        except Exception as exc:
            log.debug("Failed to fetch event %s: %s", event_ticker, exc)
            return []

    # ------------------------------------------------------------------
    # MLB-specific fetch
    # ------------------------------------------------------------------

    def get_mlb_markets(self, *, parlay_pages: int = 5) -> list[dict[str, Any]]:
        """Return individual MLB game markets (KXMLB*) discovered from parlay legs.

        Strategy
        --------
        1. Fetch the open parlay feed (KXMV markets).
        2. Scan every ``mve_selected_legs`` entry for legs whose event_ticker
           starts with ``KXMLB`` — these are individual MLB game markets.
        3. Collect unique event tickers, then fetch each event's markets.
        4. Return the de-duplicated individual KXMLB market records.
        """
        raw_parlays = self.get_open_markets(limit=200, max_pages=parlay_pages)
        mlb_event_tickers = _extract_mlb_event_tickers(raw_parlays)
        log.info("Found %d unique KXMLB event tickers from %d parlays",
                 len(mlb_event_tickers), len(raw_parlays))

        seen: set[str] = set()
        mlb_markets: list[dict[str, Any]] = []
        for event_ticker in sorted(mlb_event_tickers):
            for m in self.get_markets_for_event(event_ticker):
                ticker = m.get("ticker", "")
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    mlb_markets.append(m)

        log.info("Fetched %d individual MLB markets", len(mlb_markets))
        return mlb_markets

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def normalize_market(self, raw: dict[str, Any]) -> Market:
        """Normalize a raw Kalshi market payload into the local Market schema."""
        title = str(raw.get("title") or raw.get("subtitle") or raw.get("ticker") or "")

        yes_ask = _extract_first_number(raw, "yes_ask", "yes_ask_dollars", "yes_ask_price", "ask")
        yes_bid = _extract_first_number(raw, "yes_bid", "yes_bid_dollars", "yes_bid_price", "bid")
        last_price = _extract_first_number(raw, "last_price", "last_price_dollars", "yes_price")

        yes_mid = None
        if yes_bid is not None and yes_ask is not None:
            yes_mid = round((yes_bid + yes_ask) / 2.0, 6)

        price = next((v for v in (yes_mid, yes_ask, yes_bid, last_price) if v is not None), None)
        # Treat a price of exactly 0 as unpriced (no market maker yet)
        implied_probability = (
            clamp_probability(price_to_probability(price))
            if price is not None and price > 0
            else None
        )

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
            volume=_extract_first_number(raw, "volume", "volume_fp", "volume_dollars", "open_interest"),
            status=_extract_text(raw, "status"),
            close_time=_extract_text(raw, "close_time", "close_date"),
            raw=raw,
        )

    def get_normalized_mlb_markets(self, *, parlay_pages: int = 5) -> list[Market]:
        """Fetch, normalize, and return individual MLB game markets."""
        return [self.normalize_market(raw) for raw in self.get_mlb_markets(parlay_pages=parlay_pages)]


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _extract_mlb_event_tickers(raw_markets: list[dict[str, Any]]) -> set[str]:
    """Collect all unique KXMLB event tickers from KXMV parlay leg data."""
    event_tickers: set[str] = set()
    for m in raw_markets:
        for leg in m.get("mve_selected_legs", []):
            et = leg.get("event_ticker", "")
            if et.upper().startswith("KXMLB"):
                event_tickers.add(et)
        # Also check the custom_strike dict for Associated Events
        cs = m.get("custom_strike") or {}
        for et in str(cs.get("Associated Events", "")).split(","):
            et = et.strip()
            if et.upper().startswith("KXMLB"):
                event_tickers.add(et)
    return event_tickers


def _extract_first_number(raw: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        # 0 means "not set / no market maker" for Kalshi price fields — skip it
        # so a zero bid doesn't corrupt the yes_mid midpoint calculation
        if value <= 0:
            continue
        # Kalshi dollar-format: "0.4500" → 0.45 (already a probability)
        # Cent-format: 45.0 → 0.45
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
