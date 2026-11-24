from datetime import datetime, timezone

from scraper.cities import City, resolve_city
from scraper.transform import OUTPUT_COLUMNS, transform_live_traffic

JAKARTA = City("IDN_jakarta_new", "Jakarta", "Indonesia", "IDN")


def _payload():
    return {
        "region": {"id": "IDN_jakarta_new", "timezone": "Asia/Jakarta"},
        "data": [
            {
                "updateTime": 1794936585000,
                "trafficIndexLive": 6,
                "trafficIndexHistoric": 0,
                "relTravelTimeLive": 100,
                "relTravelTimeHistoric": 83,
                "jamsCount": 3,
                "jamsLength": 3.2,
                "jamsDelay": 29.7,
                "date": "2026-11-18",
                "hour": 0,
            },
            {
                "updateTime": 1794967185000,
                "trafficIndexLive": 69,
                "trafficIndexHistoric": 39,
                "relTravelTimeLive": 181,
                "relTravelTimeHistoric": 149,
                "jamsCount": 132,
                "jamsLength": 90.1,
                "jamsDelay": 645.8,
                "date": "2026-11-18",
                "hour": 8,
            },
        ],
    }


def test_transform_matches_dataset_schema_and_values():
    frame = transform_live_traffic(_payload(), JAKARTA)

    assert list(frame.columns) == OUTPUT_COLUMNS
    assert len(frame) == 2

    first = frame.iloc[0]
    assert first["Country"] == "Indonesia"
    assert first["City"] == "Jakarta"
    assert first["UpdateTimeUTC"] == "2026-11-17 17:29:45"
    assert first["UpdateTimeUTCWeekAgo"] == "2026-11-10 17:29:45"
    assert first["TrafficIndexLive"] == 6
    assert first["TrafficIndexWeekAgo"] == 0
    assert first["JamsDelay"] == 29.7
    assert first["JamsLengthInKms"] == 3.2
    assert first["JamsCount"] == 3


def test_travel_time_and_delay_are_computed_from_relative_travel_time():
    frame = transform_live_traffic(_payload(), JAKARTA)

    first = frame.iloc[0]
    assert first["TravelTimeLivePer10KmsMins"] == 16.67
    assert first["TravelTimeHistoricPer10KmsMins"] == 13.83
    assert first["MinsDelay"] == 2.84

    second = frame.iloc[1]
    assert second["TravelTimeLivePer10KmsMins"] == 30.17
    assert second["TravelTimeHistoricPer10KmsMins"] == 24.83
    assert second["MinsDelay"] == 5.34


def test_transform_deduplicates_by_city_and_timestamp():
    payload = _payload()
    payload["data"].append(dict(payload["data"][0], jamsCount=99))

    frame = transform_live_traffic(payload, JAKARTA)

    assert len(frame) == 2
    assert frame.iloc[0]["JamsCount"] == 99


def test_resolve_city_known_and_fallback():
    assert resolve_city("IDN_jakarta_new").city == "Jakarta"
    assert resolve_city("IDN_jakarta_new").country == "Indonesia"

    fallback = resolve_city("MYS_kuala-lumpur_new")
    assert fallback.city == "Kuala Lumpur"
    assert fallback.country == "MYS"


def test_update_time_uses_utc():
    frame = transform_live_traffic(_payload(), JAKARTA)
    parsed = datetime.strptime(frame.iloc[0]["UpdateTimeUTC"], "%Y-%m-%d %H:%M:%S")
    assert parsed.replace(tzinfo=timezone.utc).timestamp() * 1000 == 1794936585000
