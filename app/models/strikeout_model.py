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
        score += ctx.home_pitcher.k9_delta * 0.80
        score += ctx.away_pitcher.k9_delta * 0.80
        # High-K offenses (paradoxically) make high-K totals more likely
        score += ctx.home_offense.strikeout_rate * 0.50 if hasattr(ctx.home_offense, "strikeout_rate") else 0.0
        score -= (ctx.run_factor - 1.0) * 0.40  # hitter parks suppress K totals slightly
        return score
