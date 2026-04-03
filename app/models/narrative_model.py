"""Narrative (MVP, Cy Young, award race) mention probability model.

Base rate: ~42% per game for narrative keywords during broadcast.

Narrative markets ask whether terms like "MVP", "Cy Young", "Rookie of the Year",
or "All-Star" will be mentioned during a specific broadcast.

Key drivers:
- Exceptional pitching (Cy Young contender) → more award discussion
- High-OPS / standout hitters in the lineup → MVP conversation
- Run environment: blowouts often trigger award commentary on the winner's side
- Early vs late season (late season increases award urgency — not modelled
  directly here, but proxied via how dominant the pitching context is)
"""

from __future__ import annotations

from app.features.game_context import GameContext
from app.models.base import FamilyModel

# Well above-average ERA delta threshold to classify as "ace / CY Young candidate"
_ACE_ERA_THRESHOLD = 0.30  # ERA more than 30% better than league average


class NarrativeModel(FamilyModel):
    BASE_RATE = 0.42
    DESCRIPTION = "P(award narrative mention — MVP/Cy Young/ROTY | game)"

    def _feature_score(self, ctx: GameContext) -> float:
        score = 0.0

        # Ace starters drive Cy Young discussion
        if ctx.home_pitcher.era_delta > _ACE_ERA_THRESHOLD and ctx.home_pitcher.is_reliable:
            score += 0.55
        if ctx.away_pitcher.era_delta > _ACE_ERA_THRESHOLD and ctx.away_pitcher.is_reliable:
            score += 0.55

        # High strikeout starters get noticed (K/9 is a storyline)
        score += ctx.home_pitcher.k9_delta * 0.30
        score += ctx.away_pitcher.k9_delta * 0.30

        # Powerful offenses → MVP conversation
        score += ctx.home_offense.iso_delta * 0.40
        score += ctx.away_offense.iso_delta * 0.40

        # High-run environments (exciting games) generate more commentary
        score += (ctx.run_factor - 1.0) * 0.50

        return score
