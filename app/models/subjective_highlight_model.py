"""Subjective highlight (great catch, web gem) probability model.

Base rate: ~35% per game for broadcast exclamations like "what a catch",
"web gem", "incredible catch".

Key drivers:
- Fly-ball heavy pitching environments create more catchable-but-difficult plays
- Fast, athletic outfielders (speed score proxy) make more spectacular plays
- High-strikeout pitchers have fewer balls in play → fewer catch opportunities
- Large parks (centre-field depth) reward outfield range
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class SubjectiveHighlightModel(FamilyModel):
    BASE_RATE = 0.35
    DESCRIPTION = "P(subjective highlight catch / web gem mentioned | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Fly-ball pitchers → more outfield chances → more highlight opportunities
        # GB rate below league avg (0.44) = more fly balls
        score -= (ctx.home_pitcher.gb_rate - 0.44) * 1.20
        score -= (ctx.away_pitcher.gb_rate - 0.44) * 1.20

        # Fewer strikeouts → more balls in play → more defensive opportunities
        score -= ctx.home_pitcher.k9_delta * 0.30
        score -= ctx.away_pitcher.k9_delta * 0.30

        # Speed on the field (outfielder speed proxy via team speed score)
        score += ctx.home_offense.speed_score * 0.45
        score += ctx.away_offense.speed_score * 0.45

        # Large parks favour outfield highlight plays
        score += (ctx.triple_factor - 1.0) * 0.80

        return score
