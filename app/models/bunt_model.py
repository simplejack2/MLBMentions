"""Bunt probability model.

Base rate: ~48% per game (bunt attempted or discussed in ~half of games).

Context: The universal DH (adopted in 2022) eliminated pitcher bunt spots,
making sacrifice bunts rarer.  But bunt hits, drag bunts, and bunt discussions
still occur — especially with speedy hitters or in late, tight games.

Key drivers:
- Team stolen-base rate (proxy for team speed / aggressive baserunning culture)
- Pitcher strikeout rate (high K rate can make offensive managers more aggressive
  with contact-play alternatives)
- Run environment (low-scoring games more likely to feature small-ball tactics)
- Park triple factor (large parks that reward speed also encourage small-ball)
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class BuntModel(FamilyModel):
    BASE_RATE = 0.48
    DESCRIPTION = "P(bunt attempted or mentioned | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Team speed: stolen-base culture correlates with bunt tendency
        score += ctx.home_offense.speed_score * 0.55
        score += ctx.away_offense.speed_score * 0.55

        # High-strikeout pitchers → batters more likely to try contact plays
        score += ctx.home_pitcher.k9_delta * 0.20
        score += ctx.away_pitcher.k9_delta * 0.20

        # Low-scoring environment encourages small ball
        score -= (ctx.run_factor - 1.0) * 0.80

        # Large/speed-oriented parks slightly favour small-ball plays
        score += (ctx.triple_factor - 1.0) * 0.40

        return score
