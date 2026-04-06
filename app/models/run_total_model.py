"""Run-total model for KXMLBTOTAL markets (Over N runs in a game).

Base rate of 0.50 — the market line is set near 50% so our prior is neutral.
Features shift probability based on the run-scoring environment.

Positive score → more likely to go OVER (high-scoring park, weak pitching,
                 strong offense).
Negative score → more likely to go UNDER.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class RunTotalModel(FamilyModel):
    BASE_RATE = 0.50
    DESCRIPTION = "P(over N runs | game) — run-scoring environment"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # Park run environment is the strongest signal
        score += (ctx.run_factor - 1.0) * 2.00
        # Both offenses' overall quality
        score += ctx.home_offense.ops_delta * 0.80
        score += ctx.away_offense.ops_delta * 0.80
        # Pitcher quality suppresses scoring
        score += ctx.home_pitcher.era_delta * 0.60   # era_delta positive = better pitcher = fewer runs
        score += ctx.away_pitcher.era_delta * 0.60
        # HR park factor loosely correlates with high-scoring games
        score += (ctx.hr_factor - 1.0) * 0.50
        return score
