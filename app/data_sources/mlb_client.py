"""MLB Stats API client for game schedules, rosters, and player stats.

Uses the free public MLB Stats API (no auth required).
Base URL: https://statsapi.mlb.com/api/v1
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

import requests

from app.schemas.game import Game, ProbablePitcher, TeamInfo, VenueInfo
from app.schemas.player import HittingStats, PitchingStats, Player

log = logging.getLogger(__name__)

MLB_STATS_BASE = "https://statsapi.mlb.com/api/v1"
_CURRENT_SEASON = datetime.date.today().year


class MLBAPIError(RuntimeError):
    """Raised on unexpected MLB Stats API responses."""


@dataclass
class MLBClient:
    """Client for the public MLB Stats API."""

    base_url: str = MLB_STATS_BASE
    timeout: int = 20
    _session: requests.Session = field(
        default_factory=requests.Session, init=False, repr=False
    )

    # ------------------------------------------------------------------ #
    # Low-level request                                                    #
    # ------------------------------------------------------------------ #

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise MLBAPIError(f"MLB API request failed: {url} — {exc}") from exc

    # ------------------------------------------------------------------ #
    # Schedule                                                             #
    # ------------------------------------------------------------------ #

    def get_schedule(self, date: datetime.date | None = None) -> list[Game]:
        """Return normalized Game objects for the given date (default: today)."""
        date_str = (date or datetime.date.today()).strftime("%Y-%m-%d")
        data = self._get(
            "schedule",
            params={
                "sportId": 1,
                "date": date_str,
                "hydrate": "probablePitcher,team,venue,linescore,seriesStatus",
            },
        )
        games: list[Game] = []
        for date_entry in data.get("dates", []):
            for raw_game in date_entry.get("games", []):
                game = self._normalize_game(raw_game)
                if game:
                    games.append(game)
        return games

    # ------------------------------------------------------------------ #
    # Lineups                                                              #
    # ------------------------------------------------------------------ #

    def get_lineups(self, game_pk: int) -> dict[str, list[int]]:
        """Return {'home': [player_ids], 'away': [player_ids]} from live feed.

        Returns empty lists if the lineup is not yet posted.
        """
        try:
            data = self._get(f"game/{game_pk}/feed/live")
        except MLBAPIError:
            return {"home": [], "away": []}

        lineups: dict[str, list[int]] = {"home": [], "away": []}
        boxscore = data.get("liveData", {}).get("boxscore", {})
        for side in ("home", "away"):
            team_data = boxscore.get("teams", {}).get(side, {})
            batting_order = team_data.get("battingOrder", [])
            lineups[side] = [int(pid) for pid in batting_order if pid]
        return lineups

    # ------------------------------------------------------------------ #
    # Player data                                                          #
    # ------------------------------------------------------------------ #

    def get_player(self, player_id: int) -> Player | None:
        """Fetch basic player info."""
        try:
            data = self._get(f"people/{player_id}")
        except MLBAPIError:
            return None
        people = data.get("people", [])
        if not people:
            return None
        p = people[0]
        return Player(
            player_id=player_id,
            full_name=p.get("fullName", ""),
            position=p.get("primaryPosition", {}).get("abbreviation"),
            batting_side=p.get("batSide", {}).get("code"),
            pitching_hand=p.get("pitchHand", {}).get("code"),
            active=p.get("active", True),
        )

    def get_hitting_stats(
        self, player_id: int, season: int | None = None
    ) -> HittingStats | None:
        """Fetch season hitting stats for a player."""
        season = season or _CURRENT_SEASON
        try:
            data = self._get(
                f"people/{player_id}/stats",
                params={"stats": "season", "group": "hitting", "season": season},
            )
        except MLBAPIError:
            return None

        splits = _first_splits(data)
        if not splits:
            return None
        s = splits.get("stat", {})

        pa = _int(s, "plateAppearances") or 0
        so = _int(s, "strikeOuts") or 0
        bb = _int(s, "baseOnBalls") or 0
        sb = _int(s, "stolenBases") or 0
        sba = _int(s, "stolenBaseAttempts") or sb
        avg = _float(s, "avg")
        slg = _float(s, "slg")

        return HittingStats(
            games=_int(s, "gamesPlayed"),
            plate_appearances=pa or None,
            at_bats=_int(s, "atBats"),
            avg=avg,
            obp=_float(s, "obp"),
            slg=slg,
            ops=_float(s, "ops"),
            hr=_int(s, "homeRuns"),
            triples=_int(s, "triples"),
            doubles=_int(s, "doubles"),
            rbi=_int(s, "rbi"),
            stolen_bases=sb or None,
            stolen_base_attempts=sba or None,
            strikeout_rate=round(so / pa, 4) if pa > 0 else None,
            walk_rate=round(bb / pa, 4) if pa > 0 else None,
            iso=round(slg - avg, 4) if slg is not None and avg is not None else None,
        )

    def get_pitching_stats(
        self, player_id: int, season: int | None = None
    ) -> PitchingStats | None:
        """Fetch season pitching stats for a player."""
        season = season or _CURRENT_SEASON
        try:
            data = self._get(
                f"people/{player_id}/stats",
                params={"stats": "season", "group": "pitching", "season": season},
            )
        except MLBAPIError:
            return None

        splits = _first_splits(data)
        if not splits:
            return None
        s = splits.get("stat", {})
        return PitchingStats(
            games=_int(s, "gamesPitched"),
            games_started=_int(s, "gamesStarted"),
            innings_pitched=_float(s, "inningsPitched"),
            era=_float(s, "era"),
            whip=_float(s, "whip"),
            k_per_9=_float(s, "strikeoutsPer9Inn"),
            bb_per_9=_float(s, "walksPer9Inn"),
            hr_per_9=_float(s, "homeRunsPer9"),
        )

    def enrich_pitcher(self, pitcher: ProbablePitcher, season: int | None = None) -> ProbablePitcher:
        """Return a copy of `pitcher` with season stats filled in."""
        stats = self.get_pitching_stats(pitcher.player_id, season)
        if stats is None:
            return pitcher
        return pitcher.model_copy(
            update={
                "era": stats.era,
                "whip": stats.whip,
                "k_per_9": stats.k_per_9,
                "bb_per_9": stats.bb_per_9,
                "hr_per_9": stats.hr_per_9,
                "ground_ball_rate": stats.ground_ball_rate,
                "innings_pitched": stats.innings_pitched,
            }
        )

    def get_team_hitting_stats(self, team_id: int, season: int | None = None) -> HittingStats | None:
        """Fetch aggregate season hitting stats for a team."""
        season = season or _CURRENT_SEASON
        try:
            data = self._get(
                f"teams/{team_id}/stats",
                params={"stats": "season", "group": "hitting", "season": season, "sportId": 1},
            )
        except MLBAPIError:
            return None

        splits = _first_splits(data)
        if not splits:
            return None
        s = splits.get("stat", {})

        pa = _int(s, "plateAppearances") or 0
        so = _int(s, "strikeOuts") or 0
        bb = _int(s, "baseOnBalls") or 0
        sb = _int(s, "stolenBases") or 0
        avg = _float(s, "avg")
        slg = _float(s, "slg")

        return HittingStats(
            games=_int(s, "gamesPlayed"),
            plate_appearances=pa or None,
            avg=avg,
            obp=_float(s, "obp"),
            slg=slg,
            ops=_float(s, "ops"),
            hr=_int(s, "homeRuns"),
            triples=_int(s, "triples"),
            stolen_bases=sb or None,
            strikeout_rate=round(so / pa, 4) if pa > 0 else None,
            walk_rate=round(bb / pa, 4) if pa > 0 else None,
            iso=round(slg - avg, 4) if slg is not None and avg is not None else None,
        )

    # ------------------------------------------------------------------ #
    # Normalization helpers                                                #
    # ------------------------------------------------------------------ #

    def _normalize_game(self, raw: dict[str, Any]) -> Game | None:
        try:
            game_pk = raw["gamePk"]
        except KeyError:
            return None

        status = raw.get("status", {}).get("abstractGameState", "Preview")
        game_date = (raw.get("officialDate") or raw.get("gameDate", ""))[:10]

        teams = raw.get("teams", {})
        home_raw = teams.get("home", {})
        away_raw = teams.get("away", {})
        venue_raw = raw.get("venue", {})

        home_team = _normalize_team(home_raw.get("team", {}))
        away_team = _normalize_team(away_raw.get("team", {}))
        if not home_team or not away_team:
            return None

        venue = _normalize_venue(venue_raw)

        home_pp = _normalize_pitcher(home_raw.get("probablePitcher"))
        away_pp = _normalize_pitcher(away_raw.get("probablePitcher"))

        return Game(
            game_pk=game_pk,
            game_date=game_date,
            status=status,
            home_team=home_team,
            away_team=away_team,
            venue=venue,
            home_probable_pitcher=home_pp,
            away_probable_pitcher=away_pp,
            double_header=raw.get("doubleHeader", "N") != "N",
            series_description=raw.get("seriesDescription"),
            raw=raw,
        )


# ------------------------------------------------------------------ #
# Module-level helpers                                                 #
# ------------------------------------------------------------------ #

def _normalize_team(raw: dict[str, Any]) -> TeamInfo | None:
    team_id = raw.get("id")
    if not team_id:
        return None
    return TeamInfo(
        team_id=team_id,
        name=raw.get("name", ""),
        abbreviation=raw.get("abbreviation"),
        league=raw.get("league", {}).get("name"),
    )


def _normalize_venue(raw: dict[str, Any]) -> VenueInfo:
    return VenueInfo(
        venue_id=raw.get("id", 0),
        name=raw.get("name", ""),
    )


def _normalize_pitcher(raw: dict[str, Any] | None) -> ProbablePitcher | None:
    if not raw:
        return None
    player_id = raw.get("id")
    if not player_id:
        return None
    return ProbablePitcher(
        player_id=player_id,
        full_name=raw.get("fullName", ""),
    )


def _first_splits(data: dict[str, Any]) -> dict[str, Any] | None:
    stats = data.get("stats", [])
    if not stats:
        return None
    splits = stats[0].get("splits", [])
    return splits[0] if splits else None


def _float(d: dict[str, Any], key: str) -> float | None:
    v = d.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(d: dict[str, Any], key: str) -> int | None:
    v = d.get(key)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
