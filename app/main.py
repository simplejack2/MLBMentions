"""Starter pipeline entrypoint for the MLB mentions model."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.config import SETTINGS
from app.data_sources.kalshi_client import KalshiClient
from app.parsers.market_family_classifier import classify_market_family
from app.ranking.edge import is_target_probability_band
from app.schemas.market import Market


@dataclass(slots=True)
class BoardRow:
    ticker: str
    title: str
    family: str
    probability: float
    ask: float | None
    bid: float | None
    spread: float | None
    volume: float | None
    starter_score: float


def main() -> None:
    client = KalshiClient(
        base_url=SETTINGS.kalshi_base_url,
        timeout=SETTINGS.kalshi_request_timeout,
    )

    markets = client.get_normalized_open_markets()
    board = build_candidate_board(markets)
    write_board_csv(board, SETTINGS.output_dir / "starter_board.csv")
    print_board(board)


def build_candidate_board(markets: list[Market]) -> list[BoardRow]:
    """Build a starter candidate board from normalized markets.

    This first pass is intentionally simple:
    - keep MLB-like supported families
    - keep only target price band
    - compute a lightweight starter score for inspection
    """
    board: list[BoardRow] = []

    for market in markets:
        classification = classify_market_family(market.title, market.rules_primary)
        if not classification.family:
            continue
        if market.implied_probability is None:
            continue
        if not is_target_probability_band(
            market.implied_probability,
            min_probability=SETTINGS.target_min_probability,
            max_probability=SETTINGS.target_max_probability,
        ):
            continue

        starter_score = compute_starter_score(market, classification.family)
        board.append(
            BoardRow(
                ticker=market.ticker,
                title=market.title,
                family=classification.family,
                probability=market.implied_probability,
                ask=market.yes_ask,
                bid=market.yes_bid,
                spread=market.spread,
                volume=market.volume,
                starter_score=starter_score,
            )
        )

    board.sort(key=lambda row: row.starter_score, reverse=True)
    return board


def compute_starter_score(market: Market, family: str) -> float:
    """Very lightweight sort score for the starter scaffold.

    This is *not* the real model. It just creates a stable board ordering until
    family-specific probability models are added.
    """
    family_bonus = {
        "bunt": 1.00,
        "bases_loaded": 0.95,
        "grand_slam": 0.90,
        "triple": 0.85,
        "challenge": 0.80,
        "venue": 0.70,
        "narrative": 0.60,
        "subjective_highlight": 0.55,
    }.get(family, 0.50)

    spread_penalty = 0.0
    if market.spread is not None:
        spread_penalty = min(market.spread, 0.25)

    volume_bonus = 0.0
    if market.volume is not None:
        volume_bonus = min(float(market.volume) / 100000.0, 0.20)

    probability_center_bonus = 1.0 - abs((market.implied_probability or 0.0) - 0.45)
    return round(family_bonus + volume_bonus + probability_center_bonus - spread_penalty, 6)


def write_board_csv(board: list[BoardRow], output_path: Path) -> None:
    """Write the starter board to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ticker",
                "title",
                "family",
                "probability",
                "ask",
                "bid",
                "spread",
                "volume",
                "starter_score",
            ],
        )
        writer.writeheader()
        for row in board:
            writer.writerow(row.__dict__)


def print_board(board: list[BoardRow], limit: int = 15) -> None:
    """Print a readable preview of the current candidate board."""
    if not board:
        print("No eligible MLB mentions markets found in the target band.")
        return

    print(f"Found {len(board)} eligible markets. Top {min(limit, len(board))}:\n")
    for row in board[:limit]:
        prob_pct = f"{row.probability * 100:.1f}%"
        print(
            f"{row.starter_score:>5.3f} | {row.family:<20} | {prob_pct:<6} | {row.ticker:<25} | {row.title}"
        )


if __name__ == "__main__":
    main()
