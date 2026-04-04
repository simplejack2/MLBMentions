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
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.data_sources.kalshi_client import KalshiClient
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
    # Debug: dump a sample of raw Kalshi titles so we can tune the        #
    # classifier against what Kalshi actually publishes.                  #
    # ------------------------------------------------------------------ #
    try:
        from app.config import SETTINGS
        kalshi = KalshiClient(base_url=SETTINGS.kalshi_base_url, timeout=20)
        raw_markets = kalshi.get_open_markets(limit=200, max_pages=1)
        sample = [m.get("title") or m.get("subtitle") or "" for m in raw_markets[:120]]
        debug_path = DOCS_DIR / "debug_titles.json"
        debug_path.write_text(json.dumps(sample, indent=2), encoding="utf-8")
        print(f"  Wrote {debug_path} ({len(sample)} titles)")
    except Exception as exc:
        print(f"  Debug dump skipped: {exc}")

    print("Done.")


if __name__ == "__main__":
    main()
