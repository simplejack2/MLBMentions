"""Family-model registry.

Maps each supported market family to its model instance.
Import `get_model` to look up a model by family name.
"""

from __future__ import annotations

from app.models.base import FamilyModel
from app.models.bases_loaded_model import BasesLoadedModel
from app.models.bunt_model import BuntModel
from app.models.challenge_model import ChallengeModel
from app.models.grand_slam_model import GrandSlamModel
from app.models.narrative_model import NarrativeModel
from app.models.subjective_highlight_model import SubjectiveHighlightModel
from app.models.triple_model import TripleModel
from app.models.venue_model import VenueModel

_REGISTRY: dict[str, FamilyModel] = {
    "bunt": BuntModel(),
    "bases_loaded": BasesLoadedModel(),
    "grand_slam": GrandSlamModel(),
    "triple": TripleModel(),
    "challenge": ChallengeModel(),
    "venue": VenueModel(),
    "narrative": NarrativeModel(),
    "subjective_highlight": SubjectiveHighlightModel(),
}


def get_model(family: str) -> FamilyModel | None:
    """Return the model for `family`, or None if unsupported."""
    return _REGISTRY.get(family)


def supported_families() -> list[str]:
    return list(_REGISTRY.keys())
