"""Run-line model for KXMLBSPREAD markets (Team wins by N+ runs).

Base rate of 0.35 — run-line favorites win by the required margin roughly
35% of the time in an average game; the market sets the line so we start neutral.

Positive score → favored team more likely to cover.
Negative score → underdog more likely to stay within.

Note: without knowing which team is favored from the ticker alone, we use
overall game context signals (park, pitcher differential, offense differential).
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel


class RunLineModel(FamilyModel):
    BASE_RATE = 0.35
    DESCRIPTION = "P(team covers run line | game context)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0
        # Pitcher quality differential — better home pitcher → home team more likely to cover
        score += (ctx.home_pitcher.era_delta - ctx.away_pitcher.era_delta) * 0.70
        score += (ctx.home_pitcher.k9_delta - ctx.away_pitcher.k9_delta) * 0.40
        # Offense differential
        score += (ctx.home_offense.ops_delta - ctx.away_offense.ops_delta) * 0.60
        # Run environment — high-scoring parks produce larger margins occasionally
        score += (ctx.run_factor - 1.0) * 0.50
        return score
