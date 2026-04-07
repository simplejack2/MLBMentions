"""Grand slam probability model.

Base rate: ~12% per game (roughly one grand slam per 8-9 games league-wide).

Key drivers:
- Park HR factor (home park boosts HR environment)
- Offensive power of both teams (ISO / SLG above average)
- Pitcher HR/9 rate (homer-prone pitchers raise probability)
- Run environment (high-scoring parks create more traffic = more bases-loaded HR chances)
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class GrandSlamModel(FamilyModel):
    BASE_RATE = 0.12
    DESCRIPTION = "P(grand slam hit | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Park HR factor — market prices most of this; use residual weight
        score += (ctx.hr_factor - 1.0) * 1.00

        # Offensive power: ISO delta > 0 = above-average power lineup
        score += ctx.home_offense.iso_delta * 0.60
        score += ctx.away_offense.iso_delta * 0.60

        # Pitcher HR/9: positive delta means more HR allowed → more slams
        score += ctx.home_pitcher.hr9_delta * 0.50
        score += ctx.away_pitcher.hr9_delta * 0.50

        # Walk-prone starters put more runners on base → bases loaded more often
        score += ctx.home_pitcher.bb9_delta * 0.30
        score += ctx.away_pitcher.bb9_delta * 0.30
        # Patient offenses draw more walks → more baserunners → more bases-loaded chances
        score += ctx.home_offense.walk_rate_delta * 0.25
        score += ctx.away_offense.walk_rate_delta * 0.25

        # General run environment — residual only
        score += (ctx.run_factor - 1.0) * 0.50

        return score
