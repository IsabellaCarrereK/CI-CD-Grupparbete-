import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["region", "location", "location_area", "pokemon", "types"]


def validate_transformed_records(records):
    for i, record in enumerate(records):
        for field in REQUIRED_FIELDS:
            if field not in record:
                raise ValueError(f"Missing field '{field}' in record {i}")
            if record[field] is None:
                raise ValueError(f"Null value in field '{field}' in record {i}")
            if isinstance(record[field], str) and record[field].strip() == "":
                raise ValueError(f"Empty value in field '{field}' in record {i}")
            if field == "types":
                if not isinstance(record[field], list):
                    raise ValueError(f"Invalid 'types' in record {i}")
                if len(record[field]) == 0:
                    raise ValueError(f"Empty 'types' in record {i}")
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
