"""Full ranking pipeline: model probability + edge computation.

RankedRow extends BoardRow with:
- model_probability: what the family model thinks the true probability is
- edge: model_probability - market_implied_probability
- matched_game: the MLB game this market was matched to (or None)

Rows are ranked by edge descending (highest positive edge first).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.features.game_context import GameContext
from app.models.registry import get_model
from app.ranking.edge import compute_edge, implied_prob_to_american
from app.schemas.game import Game
from app.schemas.market import Market

# Minimum edge required to include a row in the final output.
MIN_EDGE = 0.02


@dataclass(slots=True)
class RankedRow:
    ticker: str
    title: str
    family: str
    market_probability: float
    model_probability: float
    edge: float
    american_odds: int
    ask: float | None
    bid: float | None
    spread: float | None
    volume: float | None
    game_pk: int | None
    matchup: str  # e.g. "NYY @ BOS"


def build_ranked_board(
    enriched: list[tuple[Market, str, GameContext | None]],
) -> list[RankedRow]:
    """Build and sort the ranked board.

    Parameters
    ----------
    enriched:
        List of (market, family, game_context_or_None) tuples.
        The caller is responsible for filtering to valid families and
        probability band before passing here.
    """
    rows: list[RankedRow] = []

    for market, family, ctx in enriched:
        if market.implied_probability is None:
            continue

        model = get_model(family)
        if model is None:
            continue

        if ctx is not None:
            model_prob = model.predict(ctx)
        else:
            # No game context available: fall back to model's base rate
            model_prob = model.BASE_RATE

        edge = compute_edge(model_prob, market.implied_probability)
        if edge < MIN_EDGE:
            continue

        matchup = _matchup_str(ctx.game if ctx else None)

        rows.append(
            RankedRow(
                ticker=market.ticker,
                title=market.title,
                family=family,
                market_probability=market.implied_probability,
                model_probability=model_prob,
                edge=edge,
                american_odds=implied_prob_to_american(market.implied_probability),
                ask=market.yes_ask,
                bid=market.yes_bid,
                spread=market.spread,
                volume=market.volume,
                game_pk=ctx.game.game_pk if ctx else None,
                matchup=matchup,
            )
        )

    rows.sort(key=lambda r: r.edge, reverse=True)
    return rows


def write_ranked_csv(rows: list[RankedRow], output_path: Path) -> None:
    """Write the ranked board to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "edge",
        "family",
        "market_probability",
        "model_probability",
        "american_odds",
        "matchup",
        "ticker",
        "title",
        "ask",
        "bid",
        "spread",
        "volume",
        "game_pk",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: getattr(row, f) for f in fieldnames})


def print_ranked_board(rows: list[RankedRow], limit: int = 20) -> None:
    """Print a formatted ranked board to stdout."""
    if not rows:
        print("No markets with positive edge found.")
        return

    print(
        f"\n{'EDGE':>6}  {'FAMILY':<22} {'MKT%':>6} {'MDL%':>6} "
        f"{'ODDS':>6}  {'MATCHUP':<20} TICKER"
    )
    print("-" * 90)
    for row in rows[:limit]:
        mkt_pct = f"{row.market_probability * 100:.1f}%"
        mdl_pct = f"{row.model_probability * 100:.1f}%"
        edge_pct = f"+{row.edge * 100:.1f}%"
        odds_str = f"+{row.american_odds}" if row.american_odds > 0 else str(row.american_odds)
        print(
            f"{edge_pct:>6}  {row.family:<22} {mkt_pct:>6} {mdl_pct:>6} "
            f"{odds_str:>6}  {row.matchup:<20} {row.ticker}"
        )

    total = len(rows)
    shown = min(limit, total)
    if total > shown:
        print(f"\n  … {total - shown} more rows in CSV output.")


def _matchup_str(game: Game | None) -> str:
    if game is None:
        return "unknown"
    away = game.away_team.abbreviation or game.away_team.name
    home = game.home_team.abbreviation or game.home_team.name
    return f"{away} @ {home}"
