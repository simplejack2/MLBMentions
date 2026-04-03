"""Triple probability model.

Base rate: ~38% per game (a triple occurs in roughly 38% of MLB games).

Key drivers:
- Park triple factor (large outfields, artificial turf)
- Team speed (stolen-base rate as proxy)
- Pitcher fly-ball rate (fly-ball pitchers create more balls hit to deep outfield)
- Away-team speed (visiting speedsters are also relevant)
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class TripleModel(FamilyModel):
    BASE_RATE = 0.38
    DESCRIPTION = "P(triple hit | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Park triple factor is the single strongest signal
        score += (ctx.triple_factor - 1.0) * 3.50

        # Fast teams hit more triples
        score += ctx.home_offense.speed_score * 0.65
        score += ctx.away_offense.speed_score * 0.65

        # Team's historical triple rate (if available via triple_rate_delta)
        score += ctx.home_offense.triple_rate_delta * 1.20
        score += ctx.away_offense.triple_rate_delta * 1.20

        # Fly-ball pitchers give up more deep drives (potential triples)
        # GB rate below average (negative delta) → more fly balls
        score -= (ctx.home_pitcher.gb_rate - 0.44) * 0.80
        score -= (ctx.away_pitcher.gb_rate - 0.44) * 0.80

        return score
