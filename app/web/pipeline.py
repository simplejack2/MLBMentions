"""Pipeline runner with in-memory caching for the web dashboard.

Cached results live for CACHE_TTL_SECONDS.  Call `get_board()` from route
handlers; it returns a cached PipelineResult if still fresh, otherwise
re-runs the full pipeline.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

from app.config import SETTINGS
from app.data_sources.kalshi_client import KalshiClient
from app.data_sources.mlb_client import MLBClient, MLBAPIError
from app.features.game_context import GameContext, build_game_context
from app.parsers.game_matcher import match_market_to_game
from app.parsers.market_family_classifier import classify_market_family
from app.ranking.ranker import RankedRow, build_ranked_board, write_ranked_csv
from app.schemas.game import Game
from app.schemas.market import Market
from app.schemas.player import HittingStats, PitchingStats

log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class PipelineResult:
    rows: list[RankedRow]
    games: list[Game]
    total_markets_fetched: int
    candidate_markets: int
    run_at: datetime.datetime
    error: str | None = None

    @property
    def fresh_until(self) -> datetime.datetime:
        return self.run_at + datetime.timedelta(seconds=CACHE_TTL_SECONDS)

    @property
    def age_seconds(self) -> float:
        return (datetime.datetime.now() - self.run_at).total_seconds()


_cache: PipelineResult | None = None


def get_board(force_refresh: bool = False) -> PipelineResult:
    """Return a (possibly cached) PipelineResult."""
    global _cache
    if not force_refresh and _cache is not None and _cache.age_seconds < CACHE_TTL_SECONDS:
        return _cache
    _cache = _run_pipeline()
    return _cache


def _run_pipeline() -> PipelineResult:
    run_at = datetime.datetime.now()
    log.info("Running full pipeline …")

    # --- Kalshi ---
    # Individual MLB markets (KXMLB*) live as parlay legs in the open-market
    # feed, not as top-level markets.  get_normalized_mlb_markets() extracts
    # their event tickers from the parlay mve_selected_legs and fetches them.
    kalshi = KalshiClient(
        base_url=SETTINGS.kalshi_base_url,
        timeout=SETTINGS.kalshi_request_timeout,
    )
    try:
        all_markets = kalshi.get_normalized_mlb_markets()
    except Exception as exc:
        log.error("Kalshi fetch failed: %s", exc)
        return PipelineResult(rows=[], games=[], total_markets_fetched=0,
                              candidate_markets=0, run_at=run_at, error=str(exc))

    candidate_markets = _filter_markets(all_markets)

    # --- MLB schedule ---
    mlb = MLBClient(timeout=30)
    try:
        games = mlb.get_schedule()
    except MLBAPIError as exc:
        log.warning("MLB schedule failed: %s", exc)
        games = []

    # --- Enrich stats ---
    pitcher_stats: dict[int, PitchingStats | None] = {}
    team_hitting: dict[int, HittingStats | None] = {}
    if games:
        _enrich_all(mlb, games, pitcher_stats, team_hitting)

    # --- Build contexts ---
    game_contexts: dict[int, GameContext] = {}
    for game in games:
        home_pitch = pitcher_stats.get(
            game.home_probable_pitcher.player_id if game.home_probable_pitcher else -1
        )
        away_pitch = pitcher_stats.get(
            game.away_probable_pitcher.player_id if game.away_probable_pitcher else -1
        )
        ctx = build_game_context(
            game,
            home_pitching=home_pitch,
            away_pitching=away_pitch,
            home_hitting=team_hitting.get(game.home_team.team_id),
            away_hitting=team_hitting.get(game.away_team.team_id),
        )
        game_contexts[game.game_pk] = ctx

    # --- Match + rank ---
    enriched: list[tuple[Market, str, GameContext | None]] = []
    for market, family in candidate_markets:
        matched = match_market_to_game(market, games) if games else None
        ctx = game_contexts.get(matched.game_pk) if matched else None
        enriched.append((market, family, ctx))

    board = build_ranked_board(enriched)

    # Write CSV as a side-effect
    try:
        write_ranked_csv(board, SETTINGS.output_dir / "ranked_board.csv")
    except Exception:
        pass

    log.info("Pipeline complete: %d ranked rows", len(board))
    return PipelineResult(
        rows=board,
        games=games,
        total_markets_fetched=len(all_markets),
        candidate_markets=len(candidate_markets),
        run_at=run_at,
    )


def _filter_markets(markets: list[Market]) -> list[tuple[Market, str]]:
    """Filter individual KXMLB markets to those with a price and a family.

    Since get_normalized_mlb_markets() already restricts to KXMLB event
    tickers, every market here is an MLB game market.  We just need:
    1. A valid implied probability (price > 0).
    2. A family classification (keyword match or fallback to generic_mlb
       for run-total / run-line markets whose titles may not have keywords).
    """
    result: list[tuple[Market, str]] = []
    for market in markets:
        if market.implied_probability is None:
            continue

        # Prefer keyword-based family; fall back to structural detection.
        classification = classify_market_family(market.title, market.rules_primary)
        family = classification.family

        # KXMLB event ticker encodes market type: KXMLBTOTAL → run_total,
        # KXMLBSPREAD → run_line, others → generic_mlb.
        if not family:
            family = _family_from_event_ticker(market.event_ticker or market.ticker)

        result.append((market, family))

    return result


def _family_from_event_ticker(ticker: str) -> str:
    """Derive a market family from a KXMLB event ticker prefix."""
    t = ticker.upper()
    if "KXMLBTOTAL" in t:
        return "run_total"
    if "KXMLBSPREAD" in t:
        return "run_line"
    if "KXMLBHR" in t:
        return "home_run"
    if "KXMLBSO" in t or "KXMLBK" in t:
        return "strikeout"
    if "KXMLBHIT" in t:
        return "hit"
    if "KXMLBSB" in t:
        return "stolen_base"
    return "generic_mlb"


def _enrich_all(
    mlb: MLBClient,
    games: list[Game],
    pitcher_stats: dict[int, PitchingStats | None],
    team_hitting: dict[int, HittingStats | None],
) -> None:
    seen_pitchers: set[int] = set()
    seen_teams: set[int] = set()
    for game in games:
        for pp in (game.home_probable_pitcher, game.away_probable_pitcher):
            if pp and pp.player_id not in seen_pitchers:
                seen_pitchers.add(pp.player_id)
                pitcher_stats[pp.player_id] = mlb.get_pitching_stats(pp.player_id)
        for team in (game.home_team, game.away_team):
            if team.team_id not in seen_teams:
                seen_teams.add(team.team_id)
                team_hitting[team.team_id] = mlb.get_team_hitting_stats(team.team_id)
