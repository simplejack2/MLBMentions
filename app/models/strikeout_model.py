"""Strikeout model — P(notable strikeout event or milestone | game).

Base rate: ~65% (high-K games or double-digit Ks by a starter happen often).

Key drivers: pitcher K/9, opposing team strikeout rate.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class StrikeoutModel(FamilyModel):
    BASE_RATE = 0.65
    DESCRIPTION = "P(strikeout milestone or high-K game | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # Pitcher K/9: each starter's strikeout rate above average
        score += ctx.home_pitcher.k9_delta * 0.70
        score += ctx.away_pitcher.k9_delta * 0.70
        # High-K offenses make high-K totals more likely (K-prone hitters vs. any starter)
        score += ctx.home_offense.strikeout_rate_delta * 0.40
        score += ctx.away_offense.strikeout_rate_delta * 0.40
        # Hitter parks suppress K totals slightly (batters are more aggressive)
        score -= (ctx.run_factor - 1.0) * 0.30
        return score
