"""No-hitter / perfect game probability model.

Base rate: ~1.5% per game (extremely rare events).

Key drivers: elite pitcher ERA/K9, weak opposing offense, pitcher's park.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class NoHitterModel(FamilyModel):
    BASE_RATE = 0.015
    DESCRIPTION = "P(no-hitter or perfect game | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # Elite starters with high K rates have the best shot
        score += ctx.home_pitcher.era_delta * 1.20
        score += ctx.away_pitcher.era_delta * 1.20
        score += ctx.home_pitcher.k9_delta * 0.90
        score += ctx.away_pitcher.k9_delta * 0.90
        # Pitcher parks suppress hits
        score -= (ctx.hr_factor - 1.0) * 1.50
        score -= (ctx.run_factor - 1.0) * 1.50
        return score
