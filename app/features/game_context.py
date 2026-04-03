"""Assemble per-game feature context used by all family models.

GameContext is the single object passed into every model. It aggregates:
- Park factors for the venue
- Probable pitcher stats (both starters)
- Team-level hitting stats (both teams)
- Optional lineup-level aggregates

All numeric features are normalised to a [-1, +1] or [0, 1] range where
practical so that model weight magnitudes are directly comparable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.features.park_factors import get_hr_factor, get_run_factor, get_triple_factor
from app.schemas.game import Game, ProbablePitcher
from app.schemas.player import HittingStats, PitchingStats

# ------------------------------------------------------------------ #
# League-average reference values (2022-2024 combined)               #
# ------------------------------------------------------------------ #
_LG_ERA = 4.20
_LG_WHIP = 1.28
_LG_K9 = 8.80
_LG_BB9 = 3.20
_LG_HR9 = 1.20
_LG_OPS = 0.715
_LG_SLG = 0.405
_LG_ISO = 0.155
_LG_SB_RATE = 0.055     # SB / PA
_LG_TRIPLE_RATE = 0.004  # 3B / PA
_LG_HR_RATE = 0.032      # HR / PA


@dataclass
class PitcherContext:
    """Normalised pitching features for one starter."""

    era_delta: float = 0.0       # (lg_avg - ERA) / lg_avg  (positive = better pitcher)
    whip_delta: float = 0.0      # (lg_avg - WHIP) / lg_avg
    k9_delta: float = 0.0        # (K/9 - lg_avg) / lg_avg
    bb9_delta: float = 0.0       # (BB/9 - lg_avg) / lg_avg (positive = more walks)
    hr9_delta: float = 0.0       # (HR/9 - lg_avg) / lg_avg (positive = more HRs allowed)
    gb_rate: float = 0.45        # ground-ball rate (raw; lg avg ~0.44)
    innings_pitched: float = 0.0  # raw, for reliability weighting
    is_reliable: bool = False


@dataclass
class OffenseContext:
    """Normalised team hitting features."""

    ops_delta: float = 0.0       # (OPS - lg_avg) / lg_avg
    slg_delta: float = 0.0
    iso_delta: float = 0.0       # power
    speed_score: float = 0.0     # (SB_rate - lg_avg) / lg_avg  (positive = faster)
    triple_rate_delta: float = 0.0
    hr_rate_delta: float = 0.0


@dataclass
class GameContext:
    """All features for one specific game."""

    game: Game

    # Park
    hr_factor: float = 1.0
    triple_factor: float = 1.0
    run_factor: float = 1.0

    # Pitchers
    home_pitcher: PitcherContext = field(default_factory=PitcherContext)
    away_pitcher: PitcherContext = field(default_factory=PitcherContext)

    # Offenses
    home_offense: OffenseContext = field(default_factory=OffenseContext)
    away_offense: OffenseContext = field(default_factory=OffenseContext)

    # Derived convenience values
    avg_era_delta: float = 0.0    # average ERA quality across both starters
    total_offense: float = 0.0    # average OPS delta across both offenses

    @property
    def home_abbr(self) -> str:
        return self.game.home_team.abbreviation or ""

    @property
    def away_abbr(self) -> str:
        return self.game.away_team.abbreviation or ""


# ------------------------------------------------------------------ #
# Factory                                                              #
# ------------------------------------------------------------------ #

def build_game_context(
    game: Game,
    home_pitching: PitchingStats | None = None,
    away_pitching: PitchingStats | None = None,
    home_hitting: HittingStats | None = None,
    away_hitting: HittingStats | None = None,
) -> GameContext:
    """Build a GameContext from a Game and optional enrichment data."""
    home_abbr = game.home_team.abbreviation or ""

    ctx = GameContext(
        game=game,
        hr_factor=get_hr_factor(home_abbr),
        triple_factor=get_triple_factor(home_abbr),
        run_factor=get_run_factor(home_abbr),
    )

    # Enrich pitcher contexts — fall back to probable pitcher stub if no stats
    home_pp = game.home_probable_pitcher
    away_pp = game.away_probable_pitcher

    ctx.home_pitcher = _build_pitcher_ctx(home_pp, home_pitching)
    ctx.away_pitcher = _build_pitcher_ctx(away_pp, away_pitching)

    ctx.home_offense = _build_offense_ctx(home_hitting)
    ctx.away_offense = _build_offense_ctx(away_hitting)

    ctx.avg_era_delta = (ctx.home_pitcher.era_delta + ctx.away_pitcher.era_delta) / 2
    ctx.total_offense = (ctx.home_offense.ops_delta + ctx.away_offense.ops_delta) / 2

    return ctx


def _build_pitcher_ctx(
    pp: ProbablePitcher | None,
    stats: PitchingStats | None,
) -> PitcherContext:
    # Use stats if available, otherwise fall back to pitcher stub fields
    era = (stats.era if stats else None) or (pp.era if pp else None)
    whip = (stats.whip if stats else None) or (pp.whip if pp else None)
    k9 = (stats.k_per_9 if stats else None) or (pp.k_per_9 if pp else None)
    bb9 = (stats.bb_per_9 if stats else None) or (pp.bb_per_9 if pp else None)
    hr9 = (stats.hr_per_9 if stats else None) or (pp.hr_per_9 if pp else None)
    gb = (stats.ground_ball_rate if stats else None) or (pp.ground_ball_rate if pp else None)
    ip = (stats.innings_pitched if stats else None) or (pp.innings_pitched if pp else None)

    return PitcherContext(
        era_delta=_delta(era, _LG_ERA, _LG_ERA, invert=True),
        whip_delta=_delta(whip, _LG_WHIP, _LG_WHIP, invert=True),
        k9_delta=_delta(k9, _LG_K9, _LG_K9),
        bb9_delta=_delta(bb9, _LG_BB9, _LG_BB9),
        hr9_delta=_delta(hr9, _LG_HR9, _LG_HR9),
        gb_rate=gb if gb is not None else 0.44,
        innings_pitched=ip or 0.0,
        is_reliable=(ip or 0.0) >= 20.0,
    )


def _build_offense_ctx(stats: HittingStats | None) -> OffenseContext:
    if stats is None:
        return OffenseContext()
    return OffenseContext(
        ops_delta=_delta(stats.ops, _LG_OPS, _LG_OPS),
        slg_delta=_delta(stats.slg, _LG_SLG, _LG_SLG),
        iso_delta=_delta(stats.iso, _LG_ISO, _LG_ISO),
        speed_score=_delta(stats.hr_rate, _LG_SB_RATE, _LG_SB_RATE),
        triple_rate_delta=_delta(stats.triple_rate, _LG_TRIPLE_RATE, _LG_TRIPLE_RATE),
        hr_rate_delta=_delta(stats.hr_rate, _LG_HR_RATE, _LG_HR_RATE),
    )


def _delta(value: float | None, reference: float, scale: float, invert: bool = False) -> float:
    """Normalised delta: (value - reference) / scale, optionally inverted."""
    if value is None or scale == 0:
        return 0.0
    d = (value - reference) / scale
    return -d if invert else d


def sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def log_odds(p: float) -> float:
    """Convert a probability to log-odds (logit)."""
    p = max(1e-9, min(1 - 1e-9, p))
    return math.log(p / (1.0 - p))
