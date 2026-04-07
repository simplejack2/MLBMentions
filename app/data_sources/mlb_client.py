"""MLB Stats API client for game schedules and player/team stats.

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
from app.schemas.player import HittingStats, PitchingStats

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

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise MLBAPIError(f"MLB API request failed: {url} — {exc}") from exc

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

    def get_pitching_stats(self, player_id: int, season: int | None = None) -> PitchingStats | None:
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
        return _parse_pitching_stats(s)

    def get_pitching_stats_recent(self, player_id: int, games: int = 15) -> PitchingStats | None:
        """Fetch last-N-games pitching stats for a player."""
        try:
            data = self._get(
                f"people/{player_id}/stats",
                params={"stats": "lastXGames", "group": "pitching", "gamesPeriod": games},
            )
        except MLBAPIError:
            return None

        splits = _first_splits(data)
        if not splits:
            return None
        return _parse_pitching_stats(splits.get("stat", {}))

    def get_pitching_stats_blended(self, player_id: int) -> PitchingStats | None:
        """Season stats (70%) blended with last-15-game form (30%).

        Falls back to season-only if recent stats are unavailable or if the
        pitcher has fewer than 20 IP (too early for meaningful blending).
        """
        season = self.get_pitching_stats(player_id)
        if season is None:
            return None
        if (season.innings_pitched or 0.0) < 20.0:
            return season
        recent = self.get_pitching_stats_recent(player_id)
        if recent is None or (recent.innings_pitched or 0.0) < 3.0:
            return season
        return _blend_pitching(season, recent, recent_weight=0.30)

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

        return Game(
            game_pk=game_pk,
            game_date=game_date,
            status=status,
            home_team=home_team,
            away_team=away_team,
            venue=_normalize_venue(venue_raw),
            home_probable_pitcher=_normalize_pitcher(home_raw.get("probablePitcher")),
            away_probable_pitcher=_normalize_pitcher(away_raw.get("probablePitcher")),
            double_header=raw.get("doubleHeader", "N") != "N",
            series_description=raw.get("seriesDescription"),
            raw=raw,
        )


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


def _parse_pitching_stats(s: dict[str, Any]) -> PitchingStats:
    """Build a PitchingStats from a raw MLB Stats API stat dict."""
    go = _int(s, "groundOuts") or 0
    ao = _int(s, "airOuts") or 0
    gb_rate = round(go / (go + ao), 4) if (go + ao) > 0 else None
    return PitchingStats(
        games=_int(s, "gamesPitched"),
        games_started=_int(s, "gamesStarted"),
        innings_pitched=_float(s, "inningsPitched"),
        era=_float(s, "era"),
        whip=_float(s, "whip"),
        k_per_9=_float(s, "strikeoutsPer9Inn"),
        bb_per_9=_float(s, "walksPer9Inn"),
        hr_per_9=_float(s, "homeRunsPer9"),
        ground_ball_rate=gb_rate,
    )


def _blend_pitching(
    season: PitchingStats, recent: PitchingStats, recent_weight: float
) -> PitchingStats:
    """Weighted blend of two PitchingStats (e.g. 70% season, 30% recent form)."""
    w_r = recent_weight
    w_s = 1.0 - recent_weight

    def _b(a: float | None, b: float | None) -> float | None:
        if a is None and b is None:
            return None
        if b is None:
            return a
        if a is None:
            return b
        return round(w_s * a + w_r * b, 4)

    return PitchingStats(
        games=season.games,
        games_started=season.games_started,
        innings_pitched=season.innings_pitched,  # keep season IP for reliability scaling
        era=_b(season.era, recent.era),
        whip=_b(season.whip, recent.whip),
        k_per_9=_b(season.k_per_9, recent.k_per_9),
        bb_per_9=_b(season.bb_per_9, recent.bb_per_9),
        hr_per_9=_b(season.hr_per_9, recent.hr_per_9),
        ground_ball_rate=_b(season.ground_ball_rate, recent.ground_ball_rate),
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
