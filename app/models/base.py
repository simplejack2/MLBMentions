"""Abstract base class for all MLB mentions family models.

Each concrete model:
1. Declares a BASE_RATE (historical probability of the event per game).
2. Implements `_feature_score(ctx)` → a signed float representing how much
   this game's context pushes the probability above/below the base rate.
3. The base class converts everything through a sigmoid so the output is
   always a valid probability in (0, 1).

Model calibration
-----------------
The intercept (b0) is set to log_odds(BASE_RATE) so that a zero feature score
produces exactly BASE_RATE.  Feature weights are expressed in log-odds units:
  +0.30 ≈ moves probability up by ~7-8 pp from the base rate
  +0.69 ≈ doubles the odds
  -0.69 ≈ halves the odds
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.features.game_context import GameContext, log_odds, sigmoid


class FamilyModel(ABC):
    """Base class for a single-game, single-family probability model."""

    # Subclasses must set this to the historical per-game base rate.
    BASE_RATE: float = 0.50

    # Optional human-readable description of what the model estimates.
    DESCRIPTION: str = ""

    def predict(self, ctx: GameContext) -> float:
        """Return P(event occurs | game context) in (0, 1)."""
        b0 = log_odds(self.BASE_RATE)
        feature_score = self._feature_score(ctx)
        return round(sigmoid(b0 + feature_score), 6)

    @abstractmethod
    def _feature_score(self, ctx: GameContext) -> float:
        """Signed log-odds adjustment based on game context.

        Positive values push probability above BASE_RATE;
        negative values push it below.
        """
