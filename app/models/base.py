"""Abstract base class for all MLB mentions family models.

Market-relative prediction
--------------------------
The key design principle: `predict()` accepts an optional `market_prob`
argument.  When provided, the market's own implied probability is used as the
prior (intercept) instead of the hardcoded BASE_RATE.

Why this matters
----------------
Kalshi serves many different market types at very different probability levels:
  - "Total over 6.5 runs" → market ~55%
  - "Player hits 2+ HRs"  → market ~2%
  - "Team wins by 1.5+"   → market ~35%

A hardcoded BASE_RATE of 0.88 ("at least one HR per game") applied to a
player-specific 2+ HR prop produces 86+ pp of spurious edge. Using the market
price as the prior means features can only push the probability ±% based on
how much better/worse than average the specific matchup looks — never blowing
up because the wrong base rate was hardcoded.

BASE_RATE is retained as a fallback for when no market price is available (e.g.
model testing, or a market with no price that somehow reaches the ranker).

Feature weight interpretation
------------------------------
  +0.30 ≈ moves probability up by ~7-8 pp from the prior
  +0.69 ≈ doubles the odds
  -0.69 ≈ halves the odds
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.features.game_context import GameContext, log_odds, sigmoid


class FamilyModel(ABC):
    """Base class for a single-game, single-family probability model."""

    # Historical per-game base rate — used ONLY when no market price is
    # available.  In live use, the market's implied probability is the prior.
    BASE_RATE: float = 0.50

    DESCRIPTION: str = ""

    def predict(self, ctx: GameContext, market_prob: float | None = None) -> float:
        """Return model-adjusted probability in (0, 1).

        When `market_prob` is supplied it is used as the prior so that feature
        adjustments are relative to what the market already believes, not to
        our hardcoded BASE_RATE.  This prevents base-rate mismatch from
        generating huge spurious edge.
        """
        prior = market_prob if market_prob is not None else self.BASE_RATE
        b0 = log_odds(prior)
        feature_score = self._feature_score(ctx)
        return round(sigmoid(b0 + feature_score), 6)

    @abstractmethod
    def _feature_score(self, ctx: GameContext) -> float:
        """Signed log-odds adjustment based on game context.

        Positive → push probability above prior.
        Negative → push probability below prior.
        """
