"""Generic MLB model — fallback for any MLB market that doesn't match a
specific family.

Base rate: 0.50 (no prior information; market price is best estimate).
Features nudge the probability based on overall game context.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class GenericMLBModel(FamilyModel):
    BASE_RATE = 0.50
    DESCRIPTION = "Generic MLB market — run environment and matchup quality"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        score += ctx.total_offense * 0.40
        score += (ctx.run_factor - 1.0) * 0.60
        score += ctx.avg_era_delta * 0.30
        return score
