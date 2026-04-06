"""Generate a static docs/index.html from a live pipeline run.

Called by the GitHub Actions workflow on a cron schedule so that
https://simplejack2.github.io/MLBMentions/ always shows fresh picks
without needing a running server.

Usage:
    python -m app.static_gen
"""

from __future__ import annotations

import datetime
import json
import sys
from collections import Counter
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import SETTINGS
from app.data_sources.kalshi_client import KalshiClient
from app.parsers.market_family_classifier import classify_market_family
from app.web.pipeline import _run_pipeline

DOCS_DIR = Path(__file__).parent.parent / "docs"
TEMPLATES_DIR = Path(__file__).parent / "web" / "templates"


def main() -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] Running pipeline …")
    result = _run_pipeline()

    if result.error:
        print(f"  !! Pipeline error: {result.error}", file=sys.stderr)

    print(
        f"  {result.total_markets_fetched} markets fetched, "
        f"{result.candidate_markets} in band, "
        f"{len(result.rows)} ranked picks, "
        f"{len(result.games)} games today"
    )

    DOCS_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ #
    # Render HTML                                                          #
    # ------------------------------------------------------------------ #
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    tmpl = env.get_template("index.html")
    html = tmpl.render(result=result, now=datetime.datetime.now(), static_mode=True)

    html_path = DOCS_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  Wrote {html_path} ({len(html):,} bytes)")

    # ------------------------------------------------------------------ #
    # Write JSON side-car for programmatic access                         #
    # ------------------------------------------------------------------ #
    board_data = {
        "run_at": result.run_at.isoformat(),
        "total_markets_fetched": result.total_markets_fetched,
        "candidate_markets": result.candidate_markets,
        "games_today": len(result.games),
        "ranked_picks": len(result.rows),
        "error": result.error,
        "rows": [
            {
                "edge": row.edge,
                "family": row.family,
                "market_probability": row.market_probability,
                "model_probability": row.model_probability,
                "american_odds": row.american_odds,
                "matchup": row.matchup,
                "ticker": row.ticker,
                "title": row.title,
                "ask": row.ask,
                "bid": row.bid,
                "spread": row.spread,
                "volume": row.volume,
            }
            for row in result.rows
        ],
    }
    json_path = DOCS_DIR / "board.json"
    json_path.write_text(json.dumps(board_data, indent=2), encoding="utf-8")
    print(f"  Wrote {json_path}")

    # ------------------------------------------------------------------ #
    # Diagnostics: fetch raw markets and analyze why 0 MLB candidates     #
    # are being found.  Written to debug_titles.json so we can inspect    #
    # the actual Kalshi payload and tune the classifier.                  #
    # ------------------------------------------------------------------ #
    _write_diagnostics()

    print("Done.")


def _write_diagnostics() -> None:
    """Fetch all open markets and emit a diagnostic report."""
    try:
        kalshi = KalshiClient(base_url=SETTINGS.kalshi_base_url, timeout=20)
        raw_markets = kalshi.get_open_markets(limit=200, max_pages=5)
    except Exception as exc:
        print(f"  Diagnostics skipped (fetch failed): {exc}")
        return

    no_price = 0
    has_price = 0
    ticker_mlb = 0
    keyword_mlb = 0
    series_counter: Counter[str] = Counter()
    event_prefix_counter: Counter[str] = Counter()
    sample_all: list[dict] = []
    sample_mlb: list[dict] = []

    for m in raw_markets:
        title = m.get("title") or m.get("subtitle") or ""
        series = m.get("series_ticker") or ""
        event = m.get("event_ticker") or ""
        ticker = m.get("ticker") or ""
        rules = m.get("rules_primary") or m.get("rules") or m.get("description") or ""

        # Price presence check
        has_ask = m.get("yes_ask") or m.get("ask") or m.get("yes_ask_price")
        has_bid = m.get("yes_bid") or m.get("bid") or m.get("yes_bid_price")
        has_last = m.get("last_price") or m.get("yes_price")
        priced = bool(has_ask or has_bid or has_last)
        if priced:
            has_price += 1
        else:
            no_price += 1

        # Series / event counters
        if series:
            series_counter[series] += 1
        event_prefix = event[:12] if event else "(none)"
        event_prefix_counter[event_prefix] += 1

        entry = {
            "title": title,
            "series_ticker": series,
            "event_ticker": event,
            "ticker": ticker,
            "priced": priced,
            "yes_ask": m.get("yes_ask"),
            "yes_bid": m.get("yes_bid"),
            "last_price": m.get("last_price"),
        }
        sample_all.append(entry)

        # Ticker-based MLB check
        is_ticker_mlb = any("mlb" in (f or "").lower() for f in (series, event, ticker))
        if is_ticker_mlb:
            ticker_mlb += 1
            sample_mlb.append({**entry, "detected_by": "ticker"})
            continue

        # Keyword-based MLB check
        clf = classify_market_family(title, rules)
        if clf.family:
            keyword_mlb += 1
            sample_mlb.append({**entry, "detected_by": f"keyword:{clf.family}"})

    diag = {
        "generated_at": datetime.datetime.now().isoformat(),
        "total_raw": len(raw_markets),
        "priced": has_price,
        "no_price": no_price,
        "ticker_mlb": ticker_mlb,
        "keyword_mlb": keyword_mlb,
        "top_series_tickers": series_counter.most_common(30),
        "top_event_prefixes": event_prefix_counter.most_common(30),
        "mlb_candidates": sample_mlb,
        "first_50_markets": sample_all[:50],
    }

    debug_path = DOCS_DIR / "debug_titles.json"
    debug_path.write_text(json.dumps(diag, indent=2), encoding="utf-8")
    print(
        f"  Diagnostics: {has_price} priced, {no_price} unpriced, "
        f"{ticker_mlb} ticker-MLB, {keyword_mlb} keyword-MLB "
        f"→ {debug_path}"
    )


if __name__ == "__main__":
    main()
