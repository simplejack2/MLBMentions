"""Family-model registry.

Maps each supported market family to its model instance.
Import `get_model` to look up a model by family name.
"""

from __future__ import annotations

from app.models.base import FamilyModel
from app.models.bases_loaded_model import BasesLoadedModel
from app.models.bunt_model import BuntModel
from app.models.challenge_model import ChallengeModel
from app.models.generic_mlb_model import GenericMLBModel
from app.models.grand_slam_model import GrandSlamModel
from app.models.hit_model import HitModel
from app.models.home_run_model import HomeRunModel
from app.models.narrative_model import NarrativeModel
from app.models.no_hitter_model import NoHitterModel
from app.models.stolen_base_model import StolenBaseModel
from app.models.strikeout_model import StrikeoutModel
from app.models.subjective_highlight_model import SubjectiveHighlightModel
from app.models.triple_model import TripleModel
from app.models.venue_model import VenueModel

_REGISTRY: dict[str, FamilyModel] = {
    # Original families
    "bunt": BuntModel(),
    "bases_loaded": BasesLoadedModel(),
    "grand_slam": GrandSlamModel(),
    "triple": TripleModel(),
    "challenge": ChallengeModel(),
    "venue": VenueModel(),
    "narrative": NarrativeModel(),
    "subjective_highlight": SubjectiveHighlightModel(),
    # Extended families matching real Kalshi market titles
    "home_run": HomeRunModel(),
    "strikeout": StrikeoutModel(),
    "no_hitter": NoHitterModel(),
    "stolen_base": StolenBaseModel(),
    "hit": HitModel(),
    "generic_mlb": GenericMLBModel(),
}


def get_model(family: str) -> FamilyModel | None:
    """Return the model for `family`, or None if unsupported."""
    return _REGISTRY.get(family)


def supported_families() -> list[str]:
    return list(_REGISTRY.keys())
