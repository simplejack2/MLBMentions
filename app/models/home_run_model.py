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
        # Market prices park factors heavily — use small residual weight
        score += (ctx.hr_factor - 1.0) * 0.80
        score += ctx.home_offense.iso_delta * 0.60
        score += ctx.away_offense.iso_delta * 0.60
        # Pitcher HR/9: positive = more HRs allowed → more likely a HR occurs
        score += ctx.home_pitcher.hr9_delta * 0.50
        score += ctx.away_pitcher.hr9_delta * 0.50
        score += (ctx.run_factor - 1.0) * 0.30
        return score
