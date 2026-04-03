"""Manager challenge / replay review probability model.

Base rate: ~58% per game (at least one challenge in ~58% of MLB games).

Key drivers:
- Close games (low run environment or pitcher-dominant matchups) → more close plays
- Speed on base (stolen base attempts, close tag plays → more opportunities to challenge)
- High-strikeout environments have fewer balls in play and fewer challengeable plays

Note: we don't have team-specific challenge tendency data here, so we rely on
game-context proxies.  A future calibration pass with Retrosheet data could add
per-manager challenge rate as a feature.
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class ChallengeModel(FamilyModel):
    BASE_RATE = 0.58
    DESCRIPTION = "P(manager challenge / replay review | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Pitcher-dominated games (low run environment) = tighter margins
        # = more reason to challenge close calls
        score -= (ctx.run_factor - 1.0) * 0.90

        # Good pitchers → lower-scoring, closer games, more scrutiny of calls
        score += ctx.avg_era_delta * 0.40

        # Speedy teams create more close plays (SB attempts, advances)
        score += ctx.home_offense.speed_score * 0.50
        score += ctx.away_offense.speed_score * 0.50

        # High strikeout pitchers → fewer balls in play → fewer challengeable plays
        score -= ctx.home_pitcher.k9_delta * 0.25
        score -= ctx.away_pitcher.k9_delta * 0.25

        return score
