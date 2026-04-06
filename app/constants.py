"""Project-wide constants and keyword maps."""

from __future__ import annotations

SUPPORTED_FAMILIES = {
    "bunt",
    "bases_loaded",
    "grand_slam",
    "triple",
    "challenge",
    "venue",
    "narrative",
    "subjective_highlight",
    "home_run",
    "strikeout",
    "no_hitter",
    "stolen_base",
    "hit",
    "generic_mlb",
}

# Terms that are unambiguously baseball — used to gate MLB detection.
# Deliberately excludes team nicknames that overlap with other sports
# (e.g. "rangers"→NHL, "giants"→NFL, "cardinals"→NFL, "angels", "reds").
MLB_HINTS = (
    # Explicit labels Kalshi uses
    "mlb",
    "baseball",
    # Baseball-only play terminology
    "inning",
    "ballpark",
    "ball park",
    "pitcher",
    "batter",
    "home run",
    "homer",
    "grand slam",
    "bases loaded",
    "bunt",
    "bunted",
    "sac bunt",
    "strikeout",
    "strike out",
    "no-hitter",
    "no hitter",
    "perfect game",
    "stolen base",
    "at bat",
    "walk off",
    "rbi",
    "earned run",
    "double play",
    "extra innings",
    "hit by pitch",
    "shutout",
    # Team names that are unambiguous enough to serve as MLB hints.
    # Excluded: "rangers" (NHL NY Rangers), "giants" (NFL NY Giants),
    # "cardinals" (NFL AZ Cardinals).
    "yankees",
    "red sox",
    "dodgers",
    "cubs",
    "mets",
    "braves",
    "astros",
    "mariners",
    "padres",
    "brewers",
    "rockies",
    "marlins",
    "guardians",
    "white sox",
    "orioles",
    "rays",
    "blue jays",
    "diamondbacks",
    "phillies",
    "nationals",
    "royals",
    "tigers",
    "twins",
    "pirates",
    "athletics",
    "angels",
)

VENUE_KEYWORDS = (
    "ball park",
    "ballpark",
    "field",
    "stadium",
    "park",
)

FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "grand_slam": (
        "grand slam",
        "grand-slam",
    ),
    "bases_loaded": (
        "bases loaded",
        "bases are loaded",
        "load the bases",
    ),
    "bunt": (
        "bunt",
        "bunted",
        "sac bunt",
        "sacrifice bunt",
    ),
    "triple": (
        "triple",
    ),
    "challenge": (
        "challenge",
        "challenged",
        "replay review",
        "replay",
        "overturned",
    ),
    "narrative": (
        "mvp",
        "cy young",
        "rookie of the year",
        "all-star",
        "all star",
        "hall of fame",
    ),
    "subjective_highlight": (
        "what a catch",
        "great catch",
        "incredible catch",
        "web gem",
        "diving catch",
        "robbed",
    ),
    "home_run": (
        "home run",
        "homer",
        "go yard",
        "homers",
        "hit a home run",
        "hit home run",
    ),
    "strikeout": (
        "strikeout",
        "strike out",
        "struck out",
        "strikeouts",
        "punch out",
    ),
    "no_hitter": (
        "no-hitter",
        "no hitter",
        "perfect game",
        "no hit",
    ),
    "stolen_base": (
        "stolen base",
        "steal",
        "steals",
        "stolen",
    ),
    "hit": (
        "get a hit",
        "record a hit",
        "multi-hit",
        "multi hit",
        "hits in the game",
    ),
}
