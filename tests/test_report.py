import json

import pytest

from pokemon_pipeline import report


def test_load_aggregated_data(tmp_path):
    report_file = tmp_path / "location_summary.json"
    expected = [
        {
            "region": "sinnoh",
            "location": "canalave-city",
            "pokemon_count": 2,
            "pokemons": ["gastrodon", "tentacool"],
        }
    ]
    report_file.write_text(json.dumps(expected), encoding="utf-8")

    assert report.load_aggregated_data(report_file) == expected


def test_load_aggregated_data_rejects_non_list(tmp_path):
    report_file = tmp_path / "location_summary.json"
    report_file.write_text(json.dumps({"location": "canalave-city"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Aggregated data must be a JSON list"):
        report.load_aggregated_data(report_file)


def test_render_page_contains_summary_and_escaped_values():
    html = report.render_page(
        [
            {
                "region": "sinnoh",
                "location": "<canalave-city>",
                "pokemon_count": 2,
                "pokemons": ["gastrodon", "<tentacool>"],
            }
        ]
    )

    assert "<strong>1</strong>" in html
    assert "<strong>2</strong>" in html
    assert "&lt;canalave-city&gt;" in html
    assert "&lt;tentacool&gt;" in html
    assert "<canalave-city>" not in html
    assert "<tentacool>" not in html


def test_main_writes_site_index(tmp_path, monkeypatch):
    input_file = tmp_path / "data" / "aggregated" / "location_summary.json"
    output_dir = tmp_path / "site"
    output_file = output_dir / "index.html"
    input_file.parent.mkdir(parents=True)
    input_file.write_text(
        json.dumps(
            [
                {
                    "region": "kanto",
                    "location": "viridian-forest",
                    "pokemon_count": 1,
                    "pokemons": ["pikachu"],
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(report, "AGGREGATED_DATA_PATH", input_file)
    monkeypatch.setattr(report, "SITE_DIR", output_dir)
    monkeypatch.setattr(report, "SITE_OUTPUT_PATH", output_file)

    report.main()

    html = output_file.read_text(encoding="utf-8")
    assert "viridian-forest" in html
    assert "pikachu" in html
