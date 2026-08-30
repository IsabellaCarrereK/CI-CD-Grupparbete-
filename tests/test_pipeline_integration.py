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


def test_pipeline_from_raw_data_to_report(tmp_path):
    raw_path = tmp_path / "data" / "raw" / "canalave-city-area.json"
    raw_path.parent.mkdir(parents=True)

    raw_data = {
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

    raw_path.write_text(json.dumps(raw_data), encoding="utf-8")

    run_module(tmp_path, "pokemon_pipeline.transform")
    run_module(
        tmp_path,
        "pokemon_pipeline.validate",
        "canalave-city-area",
    )
    run_module(tmp_path, "pokemon_pipeline.aggregate")
    run_module(tmp_path, "pokemon_pipeline.report")

    processed_path = (
        tmp_path / "data" / "processed" / "canalave-city-area.json"
    )
    aggregated_path = (
        tmp_path / "data" / "aggregated" / "location_summary.json"
    )
    report_path = tmp_path / "site" / "index.html"

    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    assert len(processed) == 2
    assert {record["pokemon"] for record in processed} == {
        "gyarados",
        "magikarp",
    }

    aggregated = json.loads(aggregated_path.read_text(encoding="utf-8"))
    assert len(aggregated) == 1

    location = aggregated[0]
    assert location["region"] == "sinnoh"
    assert location["location"] == "canalave-city"
    assert location["pokemon_count"] == 2
    assert location["ability_count"] == 4
    assert location["pokemons"] == ["gyarados", "magikarp"]
    assert location["abilities"] == [
        "intimidate",
        "moxie",
        "rattled",
        "swift-swim",
    ]
    assert location["pokemon_abilities"] == {
        "gyarados": ["intimidate", "moxie"],
        "magikarp": ["rattled", "swift-swim"],
    }

    html = report_path.read_text(encoding="utf-8")
    assert "PokeAPI Pipeline Report" in html
    assert "canalave-city" in html
    assert "gyarados" in html
    assert "magikarp" in html