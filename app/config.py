"""Application configuration for the MLB mentions model scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    kalshi_base_url: str = os.getenv(
        "KALSHI_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2"
    )
    kalshi_request_timeout: int = int(os.getenv("KALSHI_REQUEST_TIMEOUT", "20"))
    target_min_american: int = int(os.getenv("TARGET_MIN_AMERICAN", "-150"))
    target_max_american: int = int(os.getenv("TARGET_MAX_AMERICAN", "200"))
    target_min_probability: float = float(os.getenv("TARGET_MIN_PROBABILITY", "0.333333"))
    target_max_probability: float = float(os.getenv("TARGET_MAX_PROBABILITY", "0.60"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))


SETTINGS = Settings()
