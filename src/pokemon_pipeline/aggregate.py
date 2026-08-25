import json
from collections import defaultdict
from pathlib import Path


PROCESSED_DATA_DIR = Path("data/processed")
AGGREGATED_DATA_PATH = Path("data/aggregated/location_summary.json")


def load_processed_data(
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> list[dict]:
    """Load and combine records from all processed JSON files."""
    all_records = []

    if not processed_dir.exists():
        return all_records

    for file_path in sorted(processed_dir.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as file:
            records = json.load(file)

        if isinstance(records, list):
            all_records.extend(records)

    return all_records


def aggregate_by_location(records: list[dict]) -> list[dict]:
    """Group unique Pokemon names by location."""
    locations = defaultdict(
        lambda: {
            "region": None,
            "location_areas": set(),
            "pokemons": set(),
        }
    )

    for record in records:
        location = record.get("location")
        pokemon = record.get("pokemon")

        if not location or not pokemon:
            continue

        locations[location]["region"] = record.get("region")

        location_area = record.get("location_area")
        if location_area:
            locations[location]["location_areas"].add(location_area)

        locations[location]["pokemons"].add(pokemon)

    result = []

    for location, location_data in locations.items():
        pokemons = sorted(location_data["pokemons"])

        result.append(
            {
                "region": location_data["region"],
                "location": location,
                "location_areas": sorted(
                    location_data["location_areas"]
                ),
                "pokemon_count": len(pokemons),
                "pokemons": pokemons,
            }
        )

    return sorted(
        result,
        key=lambda item: (-item["pokemon_count"], item["location"]),
    )


def save_aggregated_data(
    aggregated_data: list[dict],
    output_path: Path = AGGREGATED_DATA_PATH,
) -> None:
    """Save aggregated results as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            aggregated_data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def main() -> None:
    records = load_processed_data()
    aggregated_data = aggregate_by_location(records)
    save_aggregated_data(aggregated_data)

    if not aggregated_data:
        print("No processed Pokemon data found.")
        return

    top_location = aggregated_data[0]

    print(f"Locations processed: {len(aggregated_data)}")
    print(
        "Location with most Pokémon: "
        f"{top_location['location']} "
        f"({top_location['pokemon_count']})"
    )
    print(f"Saved to: {AGGREGATED_DATA_PATH}")


if __name__ == "__main__":
    main()