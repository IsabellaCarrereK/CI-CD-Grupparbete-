"""Tests for extraction orchestration."""

from __future__ import annotations

from typing import Any

from pokemon_pipeline.extract import extract_location_area


class FakeClient:
    def __init__(self) -> None:
        self.area = {
            "name": "canalave-city-area",
            "location": {
                "name": "canalave-city",
                "url": "https://example.test/location/7/",
            },
            "pokemon_encounters": [
                {
                    "pokemon": {
                        "name": "tentacool",
                        "url": "https://example.test/pokemon/72/",
                    }
                },
                {
                    "pokemon": {
                        "name": "magikarp",
                        "url": "https://example.test/pokemon/129/",
                    }
                },
                # Duplicate reference: extractor should fetch it only once.
                {
                    "pokemon": {
                        "name": "tentacool",
                        "url": "https://example.test/pokemon/72/",
                    }
                },
            ],
        }
        self.resources: dict[str, dict[str, Any]] = {
            "https://example.test/location/7/": {
                "name": "canalave-city",
                "region": {"name": "sinnoh"},
            },
            "https://example.test/pokemon/72/": {
                "name": "tentacool",
                "types": [
                    {"type": {"name": "water"}},
                    {"type": {"name": "poison"}},
                ],
            },
            "https://example.test/pokemon/129/": {
                "name": "magikarp",
                "types": [{"type": {"name": "water"}}],
            },
        }
        self.requested_urls: list[str] = []

    def get_location_area(self, area_name: str) -> dict[str, Any]:
        assert area_name == "canalave-city-area"
        return self.area

    def get_json(self, url: str) -> dict[str, Any]:
        self.requested_urls.append(url)
        return self.resources[url]


def test_extract_location_area_collects_required_raw_resources() -> None:
    client = FakeClient()

    result = extract_location_area(  # type: ignore[arg-type]
        client,
        "  CANALAVE-CITY-AREA  ",
    )

    assert result["location_area"] == client.area
    assert result["location"]["region"]["name"] == "sinnoh"
    assert set(result["pokemon"]) == {"magikarp", "tentacool"}
    assert result["pokemon"]["tentacool"]["types"][0]["type"]["name"] == "water"
    assert result["metadata"]["requested_location_area"] == "canalave-city-area"
    assert result["metadata"]["source"] == "PokéAPI"

    assert client.requested_urls.count("https://example.test/pokemon/72/") == 1
    assert client.requested_urls.count("https://example.test/pokemon/129/") == 1
