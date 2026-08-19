"""Command-line interface for the extraction stage."""

from __future__ import annotations

import argparse
from pathlib import Path

from pokemon_pipeline.api import PokeAPIClient
from pokemon_pipeline.extract import ExtractionError, extract_location_area
from pokemon_pipeline.storage import save_json

DEFAULT_OUTPUT_DIR = Path("data/raw")


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract raw location-area data from PokéAPI."
    )
    parser.add_argument(
        "location_area",
        help="PokéAPI location-area name, e.g. canalave-city-area",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for raw JSON output (default: data/raw)",
    )
    return parser


def main() -> None:
    """Run the extraction command."""
    args = build_parser().parse_args()
    area_name = args.location_area.strip().lower()
    output_path = args.output_dir / f"{area_name}.json"

    try:
        with PokeAPIClient() as client:
            payload = extract_location_area(client, area_name)
        save_json(payload, output_path)
    except (ExtractionError, ValueError) as exc:
        raise SystemExit(f"Extraction failed: {exc}") from exc

    pokemon_count = len(payload["pokemon"])
    print(f"Extraction completed: {pokemon_count} Pokémon retrieved.")
    print(f"Saved to: {output_path}")
