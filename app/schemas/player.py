"""Player-level schemas for MLB data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HittingStats(BaseModel):
    """Season hitting stats for a player or team."""

    games: int | None = None
    plate_appearances: int | None = None
    at_bats: int | None = None
    avg: float | None = None
    obp: float | None = None
    slg: float | None = None
    ops: float | None = None
    hr: int | None = None
    triples: int | None = None
    doubles: int | None = None
    rbi: int | None = None
    stolen_bases: int | None = None
    stolen_base_attempts: int | None = None
    strikeout_rate: float | None = None  # SO / PA
    walk_rate: float | None = None       # BB / PA
    iso: float | None = None             # SLG - AVG (isolated power)

    @property
    def stolen_base_rate(self) -> float | None:
        """Stolen bases per plate appearance (speed proxy)."""
        if self.stolen_bases is None or not self.plate_appearances:
            return None
        return round(self.stolen_bases / self.plate_appearances, 4)

    @property
    def hr_rate(self) -> float | None:
        """Home runs per plate appearance."""
        if self.hr is None or not self.plate_appearances:
            return None
        return round(self.hr / self.plate_appearances, 4)

    @property
    def triple_rate(self) -> float | None:
        """Triples per plate appearance."""
        if self.triples is None or not self.plate_appearances:
            return None
        return round(self.triples / self.plate_appearances, 4)


class PitchingStats(BaseModel):
    """Season pitching stats."""

    games: int | None = None
    games_started: int | None = None
    innings_pitched: float | None = None
    era: float | None = None
    whip: float | None = None
    k_per_9: float | None = None
    bb_per_9: float | None = None
    hr_per_9: float | None = None
    ground_ball_rate: float | None = None

    @property
    def is_reliable(self) -> bool:
        return (self.innings_pitched or 0.0) >= 20.0


class Player(BaseModel):
    model_config = ConfigDict(extra="allow")

    player_id: int
    full_name: str
    position: str | None = None
    batting_side: str | None = None
    pitching_hand: str | None = None
    hitting: HittingStats | None = None
    pitching: PitchingStats | None = None
    active: bool = True
