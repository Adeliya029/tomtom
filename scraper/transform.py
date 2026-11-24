"""Transform TomTom live-traffic snapshots into the project dataset schema."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from .cities import City

OUTPUT_COLUMNS = [
    "Country",
    "City",
    "UpdateTimeUTC",
    "JamsDelay",
    "TrafficIndexLive",
    "JamsLengthInKms",
    "JamsCount",
    "TrafficIndexWeekAgo",
    "UpdateTimeUTCWeekAgo",
    "TravelTimeLivePer10KmsMins",
    "TravelTimeHistoricPer10KmsMins",
    "MinsDelay",
]

WEEK = timedelta(days=7)
TRIP_LENGTH_KM = 10.0
_SQL_TIMESTAMP = "%Y-%m-%d %H:%M:%S"


def _to_datetime(epoch_ms: int | float | None) -> datetime | None:
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(float(epoch_ms) / 1000.0, tz=timezone.utc)


def _format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime(_SQL_TIMESTAMP)


def _travel_minutes(rel_travel_time: float | None) -> float | None:
    """relTravelTime is seconds per km, so scale it to a 10 km trip."""
    if rel_travel_time is None:
        return None
    return round(float(rel_travel_time) * TRIP_LENGTH_KM / 60.0, 2)


def _minus(live: float | None, historic: float | None) -> float | None:
    if live is None or historic is None:
        return None
    return round(live - historic, 2)


def _to_record(item: dict, city: City) -> dict:
    update_time = _to_datetime(item.get("updateTime"))
    live_minutes = _travel_minutes(item.get("relTravelTimeLive"))
    historic_minutes = _travel_minutes(item.get("relTravelTimeHistoric"))

    return {
        "Country": city.country,
        "City": city.city,
        "UpdateTimeUTC": _format_utc(update_time),
        "JamsDelay": item.get("jamsDelay"),
        "TrafficIndexLive": item.get("trafficIndexLive"),
        "JamsLengthInKms": item.get("jamsLength"),
        "JamsCount": item.get("jamsCount"),
        "TrafficIndexWeekAgo": item.get("trafficIndexHistoric"),
        "UpdateTimeUTCWeekAgo": _format_utc(
            update_time - WEEK if update_time is not None else None
        ),
        "TravelTimeLivePer10KmsMins": live_minutes,
        "TravelTimeHistoricPer10KmsMins": historic_minutes,
        "MinsDelay": _minus(live_minutes, historic_minutes),
    }


def transform_live_traffic(payload: dict, city: City) -> pd.DataFrame:
    rows = [_to_record(item, city) for item in payload.get("data", []) if isinstance(item, dict)]
    frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if frame.empty:
        return frame

    frame = frame.dropna(subset=["UpdateTimeUTC"])
    frame = frame.drop_duplicates(
        subset=["Country", "City", "UpdateTimeUTC"], keep="last"
    )
    return frame.sort_values("UpdateTimeUTC").reset_index(drop=True)
