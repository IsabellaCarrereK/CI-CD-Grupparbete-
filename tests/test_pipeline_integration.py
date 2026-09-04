import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_module(tmp_path: Path, module: str, *args: str) -> None:
    env = os.environ.copy()
    src_path = str(ROOT / "src")

    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path
        if not existing_pythonpath
        else src_path + os.pathsep + existing_pythonpath
    )

    subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_pipeline_from_multiple_raw_areas_to_report(tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    canalave_data = {
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
            "magikarp": {
                "types": [
                    {"type": {"name": "water"}},
                ],
                "abilities": [
                    {"ability": {"name": "swift-swim"}},
                    {"ability": {"name": "rattled"}},
                ],
            },
        },
    }

    jubilife_data = {
        "location": {
            "name": "jubilife-city",
            "region": {"name": "sinnoh"},
        },
        "location_area": {
            "name": "jubilife-city-area",
        },
        "pokemon": {
            "shinx": {
                "types": [
                    {"type": {"name": "electric"}},
                ],
                "abilities": [
                    {"ability": {"name": "rivalry"}},
                    {"ability": {"name": "intimidate"}},
                ],
            },
        },
    }

    (raw_dir / "canalave-city-area.json").write_text(
        json.dumps(canalave_data),
        encoding="utf-8",
    )
    (raw_dir / "jubilife-city-area.json").write_text(
        json.dumps(jubilife_data),
        encoding="utf-8",
    )

    run_module(tmp_path, "pokemon_pipeline.transform")

    run_module(
        tmp_path,
        "pokemon_pipeline.validate",
        "canalave-city-area",
    )
    run_module(
        tmp_path,
        "pokemon_pipeline.validate",
        "jubilife-city-area",
    )

    run_module(tmp_path, "pokemon_pipeline.aggregate")
    run_module(tmp_path, "pokemon_pipeline.report")

    canalave_processed_path = (
        tmp_path / "data" / "processed" / "canalave-city-area.json"
    )
    jubilife_processed_path = (
        tmp_path / "data" / "processed" / "jubilife-city-area.json"
    )
    aggregated_path = (
        tmp_path / "data" / "aggregated" / "location_summary.json"
    )
    report_path = tmp_path / "site" / "index.html"

    canalave_processed = json.loads(
        canalave_processed_path.read_text(encoding="utf-8")
    )
    jubilife_processed = json.loads(
        jubilife_processed_path.read_text(encoding="utf-8")
    )

    assert len(canalave_processed) == 2
    assert {
        record["pokemon"] for record in canalave_processed
    } == {
        "gyarados",
        "magikarp",
    }

    assert len(jubilife_processed) == 1
    assert jubilife_processed[0]["pokemon"] == "shinx"
    assert jubilife_processed[0]["location"] == "jubilife-city"
    assert jubilife_processed[0]["types"] == ["electric"]

    aggregated = json.loads(
        aggregated_path.read_text(encoding="utf-8")
    )

    assert len(aggregated) == 2

    locations = {
        location["location"]: location
        for location in aggregated
    }

    assert set(locations) == {
        "canalave-city",
        "jubilife-city",
    }

    canalave = locations["canalave-city"]
    assert canalave["region"] == "sinnoh"
    assert canalave["pokemon_count"] == 2
    assert canalave["ability_count"] == 4
    assert canalave["pokemons"] == [
        "gyarados",
        "magikarp",
    ]
    assert canalave["pokemon_abilities"] == {
        "gyarados": ["intimidate", "moxie"],
        "magikarp": ["rattled", "swift-swim"],
    }

    jubilife = locations["jubilife-city"]
    assert jubilife["region"] == "sinnoh"
    assert jubilife["pokemon_count"] == 1
    assert jubilife["ability_count"] == 2
    assert jubilife["pokemons"] == ["shinx"]
    assert jubilife["pokemon_abilities"] == {
        "shinx": ["intimidate", "rivalry"],
    }

    html = report_path.read_text(encoding="utf-8")
    assert "PokeAPI Pipeline Report" in html
    assert "canalave-city" in html
    assert "jubilife-city" in html
    assert "gyarados" in html
    assert "magikarp" in html
    assert "shinx" in html