"""Game-level schemas for MLB data."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TeamInfo(BaseModel):
    team_id: int
    name: str
    abbreviation: str | None = None
    league: str | None = None  # "AL" or "NL"


class VenueInfo(BaseModel):
    venue_id: int
    name: str
    city: str | None = None
    roof_type: str | None = None  # "open", "retractable", "dome"
    left_field_ft: int | None = None
    center_field_ft: int | None = None
    right_field_ft: int | None = None


class ProbablePitcher(BaseModel):
    player_id: int
    full_name: str
    hand: str | None = None  # "L" or "R"
    era: float | None = None
    whip: float | None = None
    k_per_9: float | None = None
    bb_per_9: float | None = None
    hr_per_9: float | None = None
    ground_ball_rate: float | None = None
    innings_pitched: float | None = None


class Game(BaseModel):
    model_config = ConfigDict(extra="allow")

    game_pk: int
    game_date: str
    status: str  # "Preview", "Pre-Game", "In Progress", "Final"
    home_team: TeamInfo
    away_team: TeamInfo
    venue: VenueInfo
    home_probable_pitcher: ProbablePitcher | None = None
    away_probable_pitcher: ProbablePitcher | None = None
    double_header: bool = False
    series_description: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def team_abbreviations(self) -> set[str]:
        """All team abbreviations involved in this game."""
        abbrs = set()
        if self.home_team.abbreviation:
            abbrs.add(self.home_team.abbreviation.upper())
        if self.away_team.abbreviation:
            abbrs.add(self.away_team.abbreviation.upper())
        return abbrs

    @property
    def team_names_lower(self) -> set[str]:
        """All team name tokens (lowercased) for fuzzy matching."""
        tokens: set[str] = set()
        for team in (self.home_team, self.away_team):
            for word in team.name.lower().split():
                if len(word) > 2:
                    tokens.add(word)
        return tokens
