"""Home run probability model.

Base rate: ~88% per game (at least one HR hit in ~88% of MLB games).

Key drivers: park HR factor, offensive ISO/power, pitcher HR/9 rate.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class HomeRunModel(FamilyModel):
    BASE_RATE = 0.88
    DESCRIPTION = "P(at least one HR | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        score += (ctx.hr_factor - 1.0) * 2.50
        score += ctx.home_offense.iso_delta * 0.70
        score += ctx.away_offense.iso_delta * 0.70
        score += ctx.home_pitcher.hr9_delta * 0.55
        score += ctx.away_pitcher.hr9_delta * 0.55
        score += (ctx.run_factor - 1.0) * 1.00
        return score
