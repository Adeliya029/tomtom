"""Local storage for raw payloads and processed datasets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .cities import City


class ResultStorage:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)

    def _raw_dir(self, city: City, moment: datetime) -> Path:
        return (
            self.data_dir
            / "raw"
            / "traffic_index"
            / city.region_id
            / moment.strftime("%Y-%m-%d")
        )

    def _processed_dir(self, moment: datetime) -> Path:
        return (
            self.data_dir
            / "processed"
            / "traffic_index"
            / moment.strftime("%Y-%m-%d")
        )

    def save_raw(
        self,
        payload: dict,
        city: City,
        run_id: str,
        fetched_at: datetime,
    ) -> Path:
        directory = self._raw_dir(city, fetched_at)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{run_id}.json"
        document = {
            "meta": {
                "region_id": city.region_id,
                "city": city.city,
                "country": city.country,
                "run_id": run_id,
                "fetched_at": fetched_at.astimezone(timezone.utc).isoformat(),
                "source": f"https://www.tomtom.com/traffic-index/api/live-traffic.json?city={city.region_id}",
            },
            "payload": payload,
        }
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def save_processed(self, frame: pd.DataFrame, run_id: str, saved_at: datetime) -> Path:
        directory = self._processed_dir(saved_at)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{run_id}.csv"
        frame.to_csv(path, index=False)

        latest = self.data_dir / "processed" / "traffic_index" / "latest.csv"
        latest.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(latest, index=False)
        return path
