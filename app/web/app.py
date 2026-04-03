"""FastAPI web dashboard for the MLB mentions model.

Run with:
    python -m app.web
  or
    uvicorn app.web.app:app --reload
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.web.pipeline import get_board, PipelineResult

log = logging.getLogger(__name__)

app = FastAPI(title="MLB Mentions Model", docs_url=None, redoc_url=None)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    result = get_board()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": result, "now": datetime.datetime.now()},
    )


@app.get("/refresh")
async def refresh():
    """Force a pipeline re-run and redirect to the dashboard."""
    get_board(force_refresh=True)
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/board")
async def api_board():
    """JSON endpoint — same data as the dashboard."""
    result = get_board()
    return JSONResponse(
        content={
            "run_at": result.run_at.isoformat(),
            "total_markets_fetched": result.total_markets_fetched,
            "candidate_markets": result.candidate_markets,
            "games": len(result.games),
            "ranked_rows": len(result.rows),
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
    )
