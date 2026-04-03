"""Full pipeline entrypoint for the MLB mentions model.

Pipeline stages
---------------
1. Fetch open Kalshi markets → classify into MLB families → filter to price band
2. Fetch today's MLB schedule (game dates, teams, venue, probable pitchers)
3. Enrich each pitcher with season stats from the MLB Stats API
4. Enrich each team with season hitting stats
5. Build GameContext for every game
6. Match each Kalshi market to its game
7. Run the appropriate family model → model probability
8. Compute edge = model_probability - market_implied_probability
9. Filter to positive-edge markets → rank → print + CSV
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import SETTINGS
from app.data_sources.kalshi_client import KalshiClient
from app.data_sources.mlb_client import MLBClient, MLBAPIError
from app.features.game_context import GameContext, build_game_context
from app.parsers.game_matcher import match_market_to_game
from app.parsers.market_family_classifier import classify_market_family
from app.ranking.edge import is_target_probability_band
from app.ranking.ranker import build_ranked_board, print_ranked_board, write_ranked_csv
from app.schemas.game import Game
from app.schemas.market import Market
from app.schemas.player import HittingStats, PitchingStats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main() -> None:
    # ------------------------------------------------------------------ #
    # Stage 1: Kalshi markets                                              #
    # ------------------------------------------------------------------ #
    log.info("Fetching Kalshi open markets …")
    kalshi = KalshiClient(
        base_url=SETTINGS.kalshi_base_url,
        timeout=SETTINGS.kalshi_request_timeout,
    )
    try:
        all_markets = kalshi.get_normalized_open_markets()
    except Exception as exc:
        log.error("Failed to fetch Kalshi markets: %s", exc)
        sys.exit(1)
    log.info("  %d total open markets", len(all_markets))

    candidate_markets = _filter_markets(all_markets)
    log.info("  %d markets pass family + price band filter", len(candidate_markets))

    if not candidate_markets:
        print("No eligible MLB mentions markets found.")
        return

    # ------------------------------------------------------------------ #
    # Stage 2: MLB schedule                                                #
    # ------------------------------------------------------------------ #
    log.info("Fetching today's MLB schedule …")
    mlb = MLBClient(timeout=30)
    try:
        games = mlb.get_schedule()
    except MLBAPIError as exc:
        log.warning("MLB schedule fetch failed (%s) — proceeding without game context", exc)
        games = []
    log.info("  %d games on today's schedule", len(games))

    # ------------------------------------------------------------------ #
    # Stage 3 & 4: Enrich pitchers + teams                                #
    # ------------------------------------------------------------------ #
    pitcher_stats: dict[int, PitchingStats | None] = {}
    team_hitting: dict[int, HittingStats | None] = {}

    if games:
        log.info("Enriching pitcher and team stats …")
        _enrich_all(mlb, games, pitcher_stats, team_hitting)

    # ------------------------------------------------------------------ #
    # Stage 5: Build GameContexts                                          #
    # ------------------------------------------------------------------ #
    game_contexts: dict[int, GameContext] = {}
    for game in games:
        home_pitch = pitcher_stats.get(
            game.home_probable_pitcher.player_id if game.home_probable_pitcher else -1
        )
        away_pitch = pitcher_stats.get(
            game.away_probable_pitcher.player_id if game.away_probable_pitcher else -1
        )
        home_hit = team_hitting.get(game.home_team.team_id)
        away_hit = team_hitting.get(game.away_team.team_id)

        ctx = build_game_context(
            game,
            home_pitching=home_pitch,
            away_pitching=away_pitch,
            home_hitting=home_hit,
            away_hitting=away_hit,
        )
        game_contexts[game.game_pk] = ctx

    # ------------------------------------------------------------------ #
    # Stage 6 & 7: Match markets → game context                           #
    # ------------------------------------------------------------------ #
    enriched: list[tuple[Market, str, GameContext | None]] = []
    unmatched = 0

    for market, family in candidate_markets:
        matched_game: Game | None = match_market_to_game(market, games) if games else None
        ctx: GameContext | None = None
        if matched_game:
            ctx = game_contexts.get(matched_game.game_pk)
        else:
            unmatched += 1
        enriched.append((market, family, ctx))

    if unmatched and games:
        log.info("  %d markets could not be matched to a specific game", unmatched)

    # ------------------------------------------------------------------ #
    # Stage 8 & 9: Score, rank, output                                    #
    # ------------------------------------------------------------------ #
    log.info("Running models and computing edge …")
    board = build_ranked_board(enriched)
    log.info("  %d markets with positive edge (≥ 2%%)", len(board))

    output_path = SETTINGS.output_dir / "ranked_board.csv"
    write_ranked_csv(board, output_path)
    log.info("  CSV written to %s", output_path)

    print_ranked_board(board)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _filter_markets(markets: list[Market]) -> list[tuple[Market, str]]:
    """Classify and filter markets to supported families + price band."""
    result: list[tuple[Market, str]] = []
    for market in markets:
        if market.implied_probability is None:
            continue
        if not is_target_probability_band(
            market.implied_probability,
            min_probability=SETTINGS.target_min_probability,
            max_probability=SETTINGS.target_max_probability,
        ):
            continue
        classification = classify_market_family(market.title, market.rules_primary)
        if not classification.family:
            continue
        result.append((market, classification.family))
    return result


def _enrich_all(
    mlb: MLBClient,
    games: list[Game],
    pitcher_stats: dict[int, PitchingStats | None],
    team_hitting: dict[int, HittingStats | None],
) -> None:
    """Populate pitcher_stats and team_hitting in-place."""
    seen_pitchers: set[int] = set()
    seen_teams: set[int] = set()

    for game in games:
        for pp in (game.home_probable_pitcher, game.away_probable_pitcher):
            if pp and pp.player_id not in seen_pitchers:
                seen_pitchers.add(pp.player_id)
                stats = mlb.get_pitching_stats(pp.player_id)
                pitcher_stats[pp.player_id] = stats
                if stats:
                    log.debug("  Pitcher %s: ERA=%.2f WHIP=%.2f", pp.full_name, stats.era or 0, stats.whip or 0)

        for team in (game.home_team, game.away_team):
            if team.team_id not in seen_teams:
                seen_teams.add(team.team_id)
                hitting = mlb.get_team_hitting_stats(team.team_id)
                team_hitting[team.team_id] = hitting


if __name__ == "__main__":
    main()
