"""Print configured regions with carbon intensities from Electricity Maps CSV exports."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # allow running from any directory
from demo.paths import CONFIG  # noqa: E402


TIMESTAMP_COLUMNS = ("datetimeutc", "datetime", "timestamputc", "timestamp", "timeutc", "time")
INTENSITY_COLUMNS = (
    "carbonintensityavg",
    "carbonintensity",
    "carbonintensitygco2eqkwhdirect",
    "carbonintensitygco2eqkwh",
    "carbonintensityproductionavg",
)


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lstrip("\ufeff").lower())


def parse_utc_hour(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("hour must be an ISO-8601 UTC timestamp, e.g. 2026-10-14T12:00:00Z") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("hour must include a UTC timezone, for example the trailing Z")
    if parsed.minute or parsed.second or parsed.microsecond:
        raise ValueError("hour must be aligned to the start of an hour (minutes and seconds must be zero)")
    return parsed.astimezone(timezone.utc)


def find_column(headers: list[str], candidates: tuple[str, ...], description: str) -> str:
    normalized = {normalize_header(header): header for header in headers}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    raise ValueError(f"CSV is missing a recognized {description} column; found: {', '.join(headers)}")


def parse_row_hour(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_intensity(csv_path: Path, target_hour: datetime) -> int:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"{csv_path}: CSV is empty or has no header")
        timestamp_column = find_column(reader.fieldnames, TIMESTAMP_COLUMNS, "UTC timestamp")
        intensity_column = find_column(reader.fieldnames, INTENSITY_COLUMNS, "carbon-intensity")
        matches = [row for row in reader if parse_row_hour(row[timestamp_column]) == target_hour]

    if not matches:
        raise ValueError(f"{csv_path}: no row found for {target_hour.isoformat()}")
    if len(matches) > 1:
        raise ValueError(f"{csv_path}: multiple rows found for {target_hour.isoformat()}")
    try:
        intensity = Decimal(matches[0][intensity_column].strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"{csv_path}: carbon intensity is not a number") from exc
    if not intensity.is_finite() or intensity < 0:
        raise ValueError(f"{csv_path}: carbon intensity must be a finite, non-negative number")
    return int(intensity.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_region_file(value: str) -> tuple[str, Path]:
    name, separator, filename = value.partition("=")
    if not separator or not name.strip() or not filename.strip():
        raise argparse.ArgumentTypeError("use NAME=CSV_PATH")
    return name.strip(), Path(filename.strip())


def build_region_block(config_path: Path, hour: datetime, region_files: list[tuple[str, Path]]) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    regions = config.get("regions")
    if not isinstance(regions, list):
        raise ValueError(f"{config_path}: expected a top-level regions list")

    supplied: dict[str, Path] = {}
    for name, filename in region_files:
        if name in supplied:
            raise ValueError(f"duplicate CSV supplied for region {name!r}")
        supplied[name] = filename

    configured_names = {region["name"] for region in regions}
    unknown_names = supplied.keys() - configured_names
    missing_names = configured_names - supplied.keys()
    if unknown_names:
        raise ValueError(f"regions not present in {config_path}: {', '.join(sorted(unknown_names))}")
    if missing_names:
        raise ValueError(f"provide one --region NAME=CSV_PATH for every configured region; missing: {', '.join(sorted(missing_names))}")

    updated_regions = []
    for region in regions:
        updated = dict(region)
        updated["ci_g_per_kwh"] = read_intensity(supplied[region["name"]], hour)
        updated_regions.append(updated)
    return {"regions": updated_regions}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a pasteable regions: YAML block with carbon intensities from Electricity Maps CSVs."
    )
    parser.add_argument("--hour", required=True, help="UTC hour, e.g. 2026-10-14T12:00:00Z")
    parser.add_argument("--region", required=True, action="append", type=parse_region_file,
                        metavar="NAME=CSV_PATH", help="one CSV per configured region (repeat this option)")
    parser.add_argument("--config", type=Path, default=CONFIG,
                        help="config whose region names and non-carbon settings are preserved")
    args = parser.parse_args()

    try:
        block = build_region_block(args.config, parse_utc_hour(args.hour), args.region)
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    sys.stdout.write(yaml.safe_dump(block, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())