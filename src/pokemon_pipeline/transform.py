import json
from pathlib import Path

# Path to raw JSON file
RAW_DATA_PATH = Path("data/raw/canalave-city-area.json")


# Load JSON data
with RAW_DATA_PATH.open("r", encoding="utf-8") as file:
    data = json.load(file)


# Get region name
region = data["location"]["region"]["name"]


# Get location name
location = data["location"]["name"]


# Get location area name
location_area = data["location_area"]["name"]


# Get Pokemon data
pokemon_data = data["pokemon"]

# Store transformed Pokemon data
transformed_data = []

# Get Pokemon names and types
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

    pokemon_record = {
        "region": region,
        "location": location,
        "location_area": location_area,
        "pokemon": pokemon_name,
        "types": types,
        "abilities": abilities,
    }

    transformed_data.append(pokemon_record)


# Path to processed data
PROCESSED_DATA_PATH = Path("data/processed/canalave-city-area.json")

# Create processed folder if it does not exist
PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

# Save transformed data as JSON
with PROCESSED_DATA_PATH.open("w", encoding="utf-8") as file:
    json.dump(transformed_data, file, indent=2)

print(f"Transformation completed: {len(transformed_data)} Pokémon processed.")
print(f"Saved to: {PROCESSED_DATA_PATH}")