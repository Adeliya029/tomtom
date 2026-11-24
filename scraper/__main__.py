"""CLI entrypoint: python -m scraper."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .cities import resolve_cities
from .client import TomTomError, TrafficIndexClient
from .config import Settings, load_settings
from .storage import ResultStorage
from .transform import transform_live_traffic

LOGGER = logging.getLogger("scraper")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape TomTom Traffic Index live data and store it as CSV/JSON."
    )
    parser.add_argument(
        "--regions",
        help="Comma separated TomTom region ids, e.g. IDN_jakarta_new,IDN_bandung_new",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Directory for raw/processed output (default: DATA_DIR or ./data)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Fetch and transform but do not write any file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args(argv)


def _override(settings: Settings, args: argparse.Namespace) -> Settings:
    regions = settings.regions
    if args.regions:
        parsed = tuple(
            dict.fromkeys(part.strip() for part in args.regions.split(",") if part.strip())
        )
        if not parsed:
            raise ValueError("--regions did not contain any region id")
        regions = parsed
    data_dir = args.data_dir or settings.data_dir
    return Settings(
        base_url=settings.base_url,
        regions=regions,
        data_dir=data_dir,
        timeout=settings.timeout,
        retries=settings.retries,
        request_delay=settings.request_delay,
        user_agent=settings.user_agent,
        api_key=settings.api_key,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    settings = _override(load_settings(), args)
    cities = resolve_cities(settings.regions)

    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%SZ")
    client = TrafficIndexClient(settings)
    storage = ResultStorage(settings.data_dir)

    LOGGER.info(
        "run %s started for %d region(s), data dir %s",
        run_id,
        len(cities),
        settings.data_dir,
    )

    frames: list[pd.DataFrame] = []
    failures = 0

    for index, city in enumerate(cities):
        if index:
            time.sleep(settings.request_delay)
        try:
            payload = client.fetch_live_traffic(city.region_id)
            if not args.no_save:
                raw_path = storage.save_raw(payload, city, run_id, started_at)
                LOGGER.info("saved raw payload to %s", raw_path)
            frame = transform_live_traffic(payload, city)
            if frame.empty:
                raise TomTomError(f"no usable rows for {city.region_id}")
            latest = frame.iloc[-1]
            LOGGER.info(
                "%s (%s): %d rows, latest %s, index=%s jams=%s",
                city.city,
                city.region_id,
                len(frame),
                latest["UpdateTimeUTC"],
                latest["TrafficIndexLive"],
                latest["JamsCount"],
            )
            frames.append(frame)
        except (TomTomError, ValueError, OSError) as exc:
            failures += 1
            LOGGER.exception("failed to ingest %s: %s", city.region_id, exc)

    if not frames:
        LOGGER.error("no data was ingested")
        return 1

    combined = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["Country", "City", "UpdateTimeUTC"], keep="last")
        .sort_values(["Country", "City", "UpdateTimeUTC"])
        .reset_index(drop=True)
    )

    if not args.no_save:
        processed_path = storage.save_processed(combined, run_id, started_at)
        LOGGER.info("saved %d processed rows to %s", len(combined), processed_path)
    else:
        LOGGER.info("--no-save enabled; %d processed rows were not written", len(combined))

    print(
        f"run_id={run_id} regions={len(cities)} failed={failures} rows={len(combined)}"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
