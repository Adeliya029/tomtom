"""City registry and region-id resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    region_id: str
    city: str
    country: str
    country_code: str


COUNTRY_NAMES = {
    "IDN": "Indonesia",
}

CITY_REGISTRY = {
    "IDN_bandung_new": City("IDN_bandung_new", "Bandung", "Indonesia", "IDN"),
    "IDN_jakarta_new": City("IDN_jakarta_new", "Jakarta", "Indonesia", "IDN"),
    "IDN_medan_new": City("IDN_medan_new", "Medan", "Indonesia", "IDN"),
    "IDN_palembang_new": City("IDN_palembang_new", "Palembang", "Indonesia", "IDN"),
    "IDN_surabaya_new": City("IDN_surabaya_new", "Surabaya", "Indonesia", "IDN"),
}

DEFAULT_REGION_IDS = ("IDN_jakarta_new",)


def resolve_city(region_id: str) -> City:
    """Return known metadata or derive a readable label from the region id."""
    region_id = region_id.strip()
    if not region_id:
        raise ValueError("region id must not be empty")

    if region_id in CITY_REGISTRY:
        return CITY_REGISTRY[region_id]

    country_code, _, slug = region_id.partition("_")
    slug = re.sub(r"_new$", "", slug or region_id)
    city = slug.replace("-", " ").title() or region_id
    country = COUNTRY_NAMES.get(country_code, country_code)
    return City(region_id, city, country, country_code)


def resolve_cities(region_ids: tuple[str, ...] | list[str]) -> list[City]:
    return [resolve_city(region_id) for region_id in region_ids]
