import json

import pokemon_pipeline.pipeline as pipeline


def test_run_pipeline_processes_multiple_areas_without_network(
    tmp_path,
    monkeypatch,
):
    raw_dir = tmp_path / "data" / "raw"
    processed_dir = tmp_path / "data" / "processed"
    aggregated_path = (
        tmp_path / "data" / "aggregated" / "location_summary.json"
    )

    payloads = {
        "canalave-city-area": {
            "location": {
                "name": "canalave-city",
                "region": {"name": "sinnoh"},
            },
            "location_area": {
                "name": "canalave-city-area",
            },
            "pokemon": {
                "gyarados": {
                    "types": [
                        {"type": {"name": "water"}},
                        {"type": {"name": "flying"}},
                    ],
                    "abilities": [
                        {"ability": {"name": "intimidate"}},
                        {"ability": {"name": "moxie"}},
                    ],
                },
            },
        },
        "eterna-forest-area": {
            "location": {
                "name": "eterna-forest",
                "region": {"name": "sinnoh"},
            },
            "location_area": {
                "name": "eterna-forest-area",
            },
            "pokemon": {
                "budew": {
                    "types": [
                        {"type": {"name": "grass"}},
                        {"type": {"name": "poison"}},
                    ],
                    "abilities": [
                        {"ability": {"name": "natural-cure"}},
                        {"ability": {"name": "poison-point"}},
                    ],
                },
            },
        },
    }

    extracted_areas = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    def fake_extract(client, area_name):
        extracted_areas.append(area_name)
        return payloads[area_name]

    monkeypatch.setattr(pipeline, "PokeAPIClient", FakeClient)
    monkeypatch.setattr(
        pipeline,
        "extract_location_area",
        fake_extract,
    )

    aggregated = pipeline.run_pipeline(
        [
            " Canalave-City-Area ",
            "eterna-forest-area",
        ],
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        aggregated_path=aggregated_path,
    )

    assert extracted_areas == [
        "canalave-city-area",
        "eterna-forest-area",
    ]

    assert (raw_dir / "canalave-city-area.json").exists()
    assert (raw_dir / "eterna-forest-area.json").exists()

    assert (
        processed_dir / "canalave-city-area.json"
    ).exists()
    assert (
        processed_dir / "eterna-forest-area.json"
    ).exists()

    assert aggregated_path.exists()
    assert json.loads(
        aggregated_path.read_text(encoding="utf-8")
    ) == aggregated

    locations = {
        entry["location"]: entry
        for entry in aggregated
    }

    assert set(locations) == {
        "canalave-city",
        "eterna-forest",
    }
    assert locations["canalave-city"]["pokemons"] == [
        "gyarados",
    ]
    assert locations["eterna-forest"]["pokemons"] == [
        "budew",
    ]

    assert not (tmp_path / "site" / "index.html").exists()
