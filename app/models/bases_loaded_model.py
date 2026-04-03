"""Bases-loaded probability model.

Base rate: ~72% per game (bases loaded occurs in ~72% of MLB games).

Key drivers:
- Overall run environment / offensive quality
- Walk-prone or WHIP-heavy pitchers fill bases via free passes
- High-OPS offenses reach base more often
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class BasesLoadedModel(FamilyModel):
    BASE_RATE = 0.72
    DESCRIPTION = "P(bases loaded at any point | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Run environment: higher-scoring parks = more traffic on bases
        score += (ctx.run_factor - 1.0) * 2.50

        # Pitchers with high BB/9 put runners on freely → easier to load bases
        score += ctx.home_pitcher.bb9_delta * 0.55
        score += ctx.away_pitcher.bb9_delta * 0.55

        # High WHIP starters (hits + walks per inning)
        score += ctx.home_pitcher.whip_delta * 0.45
        score += ctx.away_pitcher.whip_delta * 0.45

        # Offensive OBP proxy (OPS delta carries OBP signal)
        score += ctx.home_offense.ops_delta * 0.50
        score += ctx.away_offense.ops_delta * 0.50

        return score
