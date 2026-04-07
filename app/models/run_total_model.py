"""Run-total model for KXMLBTOTAL markets (Over N runs in a game).

Market-relative design
----------------------
The model's BASE_RATE is 0.50 but in live use the market's own implied
probability is used as the prior (see FamilyModel.predict()).  The market
already incorporates park factors when it sets the run-total line, so we use
small feature weights to capture residual game-context signals rather than
re-applying park factors at full strength.

Positive score → lean OVER (above-average offense, weaker pitching).
Negative score → lean UNDER (elite pitching, pitcher's park residual).
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class RunTotalModel(FamilyModel):
    BASE_RATE = 0.50
    DESCRIPTION = "P(over N runs | game) — residual context signal"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # More offense → more runs → OVER
        score += ctx.home_offense.ops_delta * 0.40
        score += ctx.away_offense.ops_delta * 0.40
        # Better pitching → fewer runs → UNDER (era_delta positive = better pitcher)
        score -= ctx.home_pitcher.era_delta * 0.25
        score -= ctx.away_pitcher.era_delta * 0.25
        # High K/9 → fewer baserunners → lean UNDER
        score -= ctx.home_pitcher.k9_delta * 0.15
        score -= ctx.away_pitcher.k9_delta * 0.15
        # Walk-prone pitchers → more baserunners → lean OVER
        score += ctx.home_pitcher.bb9_delta * 0.15
        score += ctx.away_pitcher.bb9_delta * 0.15
        # Residual park signal (market prices most of this already — keep weights small)
        score += (ctx.run_factor - 1.0) * 0.30
        score += (ctx.hr_factor - 1.0) * 0.15
        return score
