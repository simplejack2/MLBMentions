"""Hit model — P(player multi-hit game or hit-related prop | game).

Base rate: ~55% (used for individual hit props; team context adjusts).

Key drivers: team AVG/OBP, pitcher WHIP (hits allowed), park run factor.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class HitModel(FamilyModel):
    BASE_RATE = 0.55
    DESCRIPTION = "P(hit prop resolves YES | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # Better offense → more hits
        score += ctx.home_offense.ops_delta * 0.50
        score += ctx.away_offense.ops_delta * 0.50
        # Better WHIP pitcher → fewer hits allowed → reduces batter hit probability
        score -= ctx.home_pitcher.whip_delta * 0.40
        score -= ctx.away_pitcher.whip_delta * 0.40
        # Run-friendly parks also produce more hits
        score += (ctx.run_factor - 1.0) * 0.30
        return score
