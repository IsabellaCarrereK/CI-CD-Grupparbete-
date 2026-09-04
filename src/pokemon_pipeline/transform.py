import json
from pathlib import Path

RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")


def transform_payload(data: dict) -> list[dict]:
    """Transform one raw location-area payload into Pokemon records."""
    region = data["location"]["region"]["name"]
    location = data["location"]["name"]
    location_area = data["location_area"]["name"]
    pokemon_data = data["pokemon"]

    transformed_data = []

    for pokemon_name, pokemon_info in pokemon_data.items():
        types = [
            type_info["type"]["name"]
            for type_info in pokemon_info["types"]
        ]

        abilities = [
            ability_entry["ability"]["name"]
            for ability_entry in pokemon_info.get("abilities", [])
            if isinstance(ability_entry, dict)
            and isinstance(ability_entry.get("ability"), dict)
            and isinstance(ability_entry["ability"].get("name"), str)
        ]

        transformed_data.append(
            {
                "region": region,
                "location": location,
                "location_area": location_area,
                "pokemon": pokemon_name,
                "types": types,
                "abilities": abilities,
            }
        )

    return transformed_data


def transform_file(
    raw_path: Path,
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> tuple[Path, int]:
    """Transform one raw JSON file and write its processed counterpart."""
    with raw_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    transformed_data = transform_payload(data)

    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / raw_path.name

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            transformed_data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path, len(transformed_data)


def transform_all(
    raw_dir: Path = RAW_DATA_DIR,
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> list[tuple[Path, int]]:
    """Transform every raw location-area JSON file."""
    raw_files = sorted(raw_dir.glob("*.json"))

    if not raw_files:
        raise FileNotFoundError(
            f"No raw JSON files found in {raw_dir}"
        )

    return [
        transform_file(raw_path, processed_dir)
        for raw_path in raw_files
    ]


def main() -> None:
    try:
        results = transform_all()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    total_pokemon = sum(count for _, count in results)

    for output_path, pokemon_count in results:
        print(
            f"Transformed {output_path.name}: "
            f"{pokemon_count} Pokémon processed."
        )

    print(
        f"Transformation completed: {len(results)} location area(s), "
        f"{total_pokemon} Pokémon processed."
    )
    print(f"Saved to: {PROCESSED_DATA_DIR}")


if __name__ == "__main__":
    main()