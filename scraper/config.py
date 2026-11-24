"""Environment based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .cities import DEFAULT_REGION_IDS

load_dotenv()

DEFAULT_BASE_URL = "https://www.tomtom.com"
DEFAULT_USER_AGENT = (
    "airsense-tomtom-ingest/0.1 (+https://github.com/Adeliya029/tomtom)"
)


@dataclass(frozen=True)
class Settings:
    base_url: str
    regions: tuple[str, ...]
    data_dir: Path
    timeout: float
    retries: int
    request_delay: float
    user_agent: str
    api_key: str | None = None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def load_settings() -> Settings:
    raw_regions = os.getenv("TOMTOM_REGIONS", ",".join(DEFAULT_REGION_IDS))
    regions = tuple(
        dict.fromkeys(region.strip() for region in raw_regions.split(",") if region.strip())
    )
    if not regions:
        raise ValueError("TOMTOM_REGIONS must contain at least one region id")

    return Settings(
        base_url=os.getenv("TOMTOM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        regions=regions,
        data_dir=Path(os.getenv("DATA_DIR", "./data")),
        timeout=_env_float("TOMTOM_TIMEOUT", 30.0),
        retries=max(1, _env_int("TOMTOM_RETRIES", 3)),
        request_delay=max(0.0, _env_float("TOMTOM_REQUEST_DELAY_SECONDS", 1.0)),
        user_agent=os.getenv("TOMTOM_USER_AGENT", DEFAULT_USER_AGENT),
        api_key=os.getenv("TOMTOM_API_KEY") or None,
    )
