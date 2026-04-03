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
}

MLB_HINTS = (
    "mlb",
    "baseball",
    "inning",
    "ballpark",
    "pitcher",
    "batter",
    "home run",
    "grand slam",
    "bases loaded",
    "bunt",
    "bunted",
    "triple",
    "challenge",
    "mvp",
    "catch",
)

VENUE_KEYWORDS = (
    "ball park",
    "ballpark",
    "field",
    "stadium",
    "park",
)

FAMILY_KEYWORDS = {
    "grand_slam": ("grand slam",),
    "bases_loaded": ("bases loaded",),
    "bunt": ("bunt", "bunted", "sac bunt", "sacrifice bunt"),
    "triple": ("triple",),
    "challenge": ("challenge", "challenged", "replay review", "replay"),
    "narrative": ("mvp", "cy young", "rookie of the year", "all-star"),
    "subjective_highlight": (
        "what a catch",
        "great catch",
        "incredible catch",
        "web gem",
    ),
}
