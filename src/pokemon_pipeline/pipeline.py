"""Run the multi-location data pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pokemon_pipeline.aggregate import (
    AGGREGATED_DATA_PATH,
    aggregate_by_location,
    load_processed_data,
    save_aggregated_data,
)
from pokemon_pipeline.api import PokeAPIClient
from pokemon_pipeline.extract import ExtractionError, extract_location_area
from pokemon_pipeline.storage import save_json
from pokemon_pipeline.transform import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    transform_file,
)
from pokemon_pipeline.validate import validate_transformed_records


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the pipeline runner."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract, transform, validate, and aggregate "
            "one or more PokéAPI location areas."
        )
    )
    parser.add_argument(
        "location_areas",
        nargs="+",
        help=(
            "PokéAPI location-area names, e.g. "
            "canalave-city-area eterna-forest-area"
        ),
    )
    return parser


def run_pipeline(
    location_areas: list[str],
    raw_dir: Path = RAW_DATA_DIR,
    processed_dir: Path = PROCESSED_DATA_DIR,
    aggregated_path: Path = AGGREGATED_DATA_PATH,
) -> list[dict]:
    """Run the data pipeline for all requested location areas."""
    area_names = [
        area.strip().lower()
        for area in location_areas
    ]

    if not area_names or any(not area for area in area_names):
        raise ValueError("At least one location area is required")

    total_pokemon = 0

    with PokeAPIClient() as client:
        for area_name in area_names:
            payload = extract_location_area(client, area_name)

            raw_path = save_json(
                payload,
                raw_dir / f"{area_name}.json",
            )

            processed_path, pokemon_count = transform_file(
                raw_path,
                processed_dir,
            )

            with processed_path.open("r", encoding="utf-8") as file:
                records = json.load(file)

            validate_transformed_records(records)
            total_pokemon += pokemon_count

            print(
                f"Completed {area_name}: "
                f"{pokemon_count} Pokémon processed."
            )

    records = load_processed_data(processed_dir)
    aggregated_data = aggregate_by_location(records)
    save_aggregated_data(aggregated_data, aggregated_path)

    print(
        f"Pipeline completed: {len(area_names)} location area(s), "
        f"{total_pokemon} Pokémon processed."
    )
    print(f"Aggregated locations: {len(aggregated_data)}")
    print(f"Saved to: {aggregated_path}")

    return aggregated_data


def main() -> None:
    """Run the pipeline from command-line arguments."""
    args = build_parser().parse_args()

    try:
        run_pipeline(args.location_areas)
    except (ExtractionError, ValueError, OSError) as exc:
        raise SystemExit(f"Pipeline failed: {exc}") from exc


if __name__ == "__main__":
    main()
