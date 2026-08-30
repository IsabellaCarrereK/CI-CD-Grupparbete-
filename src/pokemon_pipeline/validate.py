import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["region", "location", "location_area", "pokemon", "types"]


def validate_transformed_records(records):
    # Check that the whole dataset is a list and not empty.
    if not isinstance(records, list):
        raise ValueError("Records must be a list")
    if len(records) == 0:
        raise ValueError("No records found")

    seen_pokemon = set()

    for i, record in enumerate(records):
        # Each row should be a dictionary with the expected fields.
        if not isinstance(record, dict):
            raise ValueError(f"Record {i} is not a dictionary")

        # Check that all required fields exist and are not empty.
        for field in REQUIRED_FIELDS:
            if field not in record:
                raise ValueError(f"Missing field '{field}' in record {i}")
            if record[field] is None:
                raise ValueError(f"Null value in field '{field}' in record {i}")
            if isinstance(record[field], str) and record[field].strip() == "":
                raise ValueError(f"Empty value in field '{field}' in record {i}")

        # String fields should contain real text.
        if not isinstance(record["region"], str) or not record["region"].strip():
            raise ValueError(f"Invalid region in record {i}")
        if not isinstance(record["location"], str) or not record["location"].strip():
            raise ValueError(f"Invalid location in record {i}")
        if (
            not isinstance(record["location_area"], str)
            or not record["location_area"].strip()
        ):
            raise ValueError(f"Invalid location_area in record {i}")

        # A Pokémon should have a valid name and each Pokémon should only appear once.
        pokemon_name = record["pokemon"]
        if not isinstance(pokemon_name, str) or not pokemon_name.strip():
            raise ValueError(f"Invalid pokemon name in record {i}")
        if pokemon_name in seen_pokemon:
            raise ValueError(f"Duplicate pokemon '{pokemon_name}' found")
        seen_pokemon.add(pokemon_name)

        # Types must be a list and should not be empty.
        if not isinstance(record["types"], list):
            raise ValueError(f"Invalid 'types' in record {i}")
        if len(record["types"]) == 0:
            raise ValueError(f"Empty 'types' in record {i}")

        seen_types = set()
        for type_name in record["types"]:
            if not isinstance(type_name, str) or not type_name.strip():
                raise ValueError(f"Invalid type value in record {i}")
            normalized = type_name.lower()
            if normalized in seen_types:
                raise ValueError(f"Duplicate type '{type_name}' in record {i}")
            seen_types.add(normalized)

        if "abilities" in record:
            abilities = record["abilities"]
            if not isinstance(abilities, list):
                raise ValueError(f"Invalid 'abilities' in record {i}")
            if len(abilities) == 0:
                raise ValueError(f"Empty 'abilities' in record {i}")

            seen_abilities = set()
            for ability_name in abilities:
                if not isinstance(ability_name, str) or not ability_name.strip():
                    raise ValueError(f"Invalid ability value in record {i}")
                normalized = ability_name.lower()
                if normalized in seen_abilities:
                    raise ValueError(
                        f"Duplicate ability '{ability_name}' in record {i}"
                    )
                seen_abilities.add(normalized)

    return records


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: py -m pokemon_pipeline.validate <area-name>")
        raise SystemExit(1)

    area_name = sys.argv[1].strip().lower()
    file_path = Path("data/processed") / f"{area_name}.json"

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    validate_transformed_records(data)
    print(f"Validation passed: {file_path}")
