import json

from pokemon_pipeline.aggregate import (
    aggregate_by_location,
    load_processed_data,
)


def test_aggregate_by_location():
    records = [
        {
            "region": "sinnoh",
            "location": "canalave-city",
            "location_area": "canalave-city-area",
            "pokemon": "tentacool",
            "types": ["water", "poison"],
        },
        {
            "region": "sinnoh",
            "location": "canalave-city",
            "location_area": "canalave-city-area",
            "pokemon": "gastrodon",
            "types": ["water", "ground"],
        },
        {
            "region": "sinnoh",
            "location": "canalave-city",
            "location_area": "canalave-city-area",
            "pokemon": "tentacool",
            "types": ["water", "poison"],
        },
        {
            "region": "kanto",
            "location": "viridian-forest",
            "location_area": "viridian-forest-area",
            "pokemon": "pikachu",
            "types": ["electric"],
        },
    ]

    result = aggregate_by_location(records)

    assert result[0]["location"] == "canalave-city"
    assert result[0]["pokemon_count"] == 2
    assert result[0]["pokemons"] == ["gastrodon", "tentacool"]

    assert result[1]["location"] == "viridian-forest"
    assert result[1]["pokemon_count"] == 1


def test_empty_records():
    result = aggregate_by_location([])

    assert result == []


def test_invalid_records_are_skipped():
    records = [
        {"location": "", "pokemon": "pikachu"},
        {"location": "forest"},
        {"pokemon": "bulbasaur"},
    ]

    result = aggregate_by_location(records)

    assert result == []


def test_load_processed_data(tmp_path):
    first_file = tmp_path / "first.json"
    second_file = tmp_path / "second.json"

    first_file.write_text(
        json.dumps(
            [
                {
                    "location": "forest",
                    "pokemon": "pikachu",
                }
            ]
        ),
        encoding="utf-8",
    )

    second_file.write_text(
        json.dumps(
            [
                {
                    "location": "cave",
                    "pokemon": "zubat",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = load_processed_data(tmp_path)

    assert len(result) == 2
    assert result[0]["pokemon"] == "pikachu"
    assert result[1]["pokemon"] == "zubat"