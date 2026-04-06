"""Full ranking pipeline: model probability + edge computation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.features.game_context import GameContext
from app.models.registry import get_model
from app.ranking.edge import compute_edge, implied_prob_to_american
from app.schemas.game import Game
from app.schemas.market import Market

# Show any market where our model disagrees by ≥3 pp in either direction.
# Positive edge → bet YES.  Negative edge → bet NO.
MIN_ABS_EDGE = 0.03


@dataclass(slots=True)
class RankedRow:
    ticker: str
    title: str
    family: str
    market_probability: float
    model_probability: float
    edge: float
    bet: str          # "YES" or "NO"
    american_odds: int
    ask: float | None
    bid: float | None
    spread: float | None
    volume: float | None
    game_pk: int | None
    matchup: str


def build_ranked_board(
    enriched: list[tuple[Market, str, GameContext | None]],
) -> list[RankedRow]:
    """Build and sort the ranked board by absolute edge (best picks first)."""
    rows: list[RankedRow] = []

    for market, family, ctx in enriched:
        if market.implied_probability is None:
            continue

        model = get_model(family)
        if model is None:
            continue

        model_prob = (
            model.predict(ctx, market_prob=market.implied_probability)
            if ctx is not None
            else model.BASE_RATE
        )
        edge = compute_edge(model_prob, market.implied_probability)

        if abs(edge) < MIN_ABS_EDGE:
            continue

        rows.append(
            RankedRow(
                ticker=market.ticker,
                title=market.title,
                family=family,
                market_probability=market.implied_probability,
                model_probability=model_prob,
                edge=edge,
                bet="YES" if edge > 0 else "NO",
                american_odds=implied_prob_to_american(market.implied_probability),
                ask=market.yes_ask,
                bid=market.yes_bid,
                spread=market.spread,
                volume=market.volume,
                game_pk=ctx.game.game_pk if ctx else None,
                matchup=_matchup_str(ctx.game if ctx else None),
            )
        )

    # Sort: YES bets by edge desc, then NO bets by edge asc (most negative = best NO)
    rows.sort(key=lambda r: r.edge, reverse=True)
    return rows


def write_ranked_csv(rows: list[RankedRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "bet", "edge", "family", "market_probability", "model_probability",
        "american_odds", "matchup", "ticker", "title",
        "ask", "bid", "spread", "volume", "game_pk",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: getattr(row, f) for f in fieldnames})


def print_ranked_board(rows: list[RankedRow], limit: int = 20) -> None:
    if not rows:
        print("No picks above edge threshold.")
        return
    print(f"\n{'BET':>4} {'EDGE':>7}  {'FAMILY':<22} {'MKT%':>6} {'MDL%':>6} {'ODDS':>6}  MATCHUP")
    print("-" * 85)
    for row in rows[:limit]:
        sign = "+" if row.edge >= 0 else ""
        print(
            f"{row.bet:>4} {sign}{row.edge*100:.1f}%  {row.family:<22} "
            f"{row.market_probability*100:.1f}% {row.model_probability*100:.1f}% "
            f"{('+' if row.american_odds > 0 else '')}{row.american_odds:>6}  {row.matchup}"
        )


def _matchup_str(game: Game | None) -> str:
    if game is None:
        return "unknown"
    away = game.away_team.abbreviation or game.away_team.name
    home = game.home_team.abbreviation or game.home_team.name
    return f"{away} @ {home}"
