"""Extraction orchestration for location-area data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pokemon_pipeline.api import PokeAPIClient, PokeAPIError


class ExtractionError(RuntimeError):
    """Raised when a PokéAPI response is missing required references."""


def _required_url(resource: dict[str, Any], key: str) -> str:
    """Return a nested resource URL and fail clearly when it is missing."""
    value = resource.get(key)
    if not isinstance(value, dict):
        raise ExtractionError(f"Missing '{key}' resource reference")

    url = value.get("url")
    if not isinstance(url, str) or not url:
        raise ExtractionError(f"Missing URL for '{key}' resource reference")

    return url


def _pokemon_references(area_data: dict[str, Any]) -> dict[str, str]:
    """Return unique Pokémon names and URLs from location-area encounters."""
    encounters = area_data.get("pokemon_encounters", [])
    if not isinstance(encounters, list):
        raise ExtractionError("'pokemon_encounters' must be a list")

    references: dict[str, str] = {}

    for encounter in encounters:
        if not isinstance(encounter, dict):
            continue

        pokemon = encounter.get("pokemon")
        if not isinstance(pokemon, dict):
            continue

        name = pokemon.get("name")
        url = pokemon.get("url")

        if isinstance(name, str) and name and isinstance(url, str) and url:
            references[name] = url

    return references

def _ability_references(
    pokemon_resources: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """Return unique ability names and URLs from Pokémon resources."""
    references: dict[str, str] = {}

    for pokemon_data in pokemon_resources.values():
        abilities = pokemon_data.get("abilities", [])

        if not isinstance(abilities, list):
            continue

        for ability_entry in abilities:
            if not isinstance(ability_entry, dict):
                continue

            ability = ability_entry.get("ability")
            if not isinstance(ability, dict):
                continue

            name = ability.get("name")
            url = ability.get("url")

            if isinstance(name, str) and name and isinstance(url, str) and url:
                references[name] = url

    return references

def extract_location_area(
    client: PokeAPIClient,
    area_name: str,
) -> dict[str, Any]:
    """
    Extract raw PokéAPI resources needed by the downstream pipeline.

    The extractor intentionally keeps the original API objects. Cleaning,
    reshaping, filtering, and deriving values belong to the transform stage.
    """
    normalized_area_name = area_name.strip().lower()
    if not normalized_area_name:
        raise ValueError("area_name cannot be empty")

    try:
        area_data = client.get_location_area(normalized_area_name)
        location_data = client.get_json(_required_url(area_data, "location"))

        pokemon_resources = {
            name: client.get_json(url)
            for name, url in sorted(_pokemon_references(area_data).items())
        }

        ability_resources = {
            name: client.get_json(url)
            for name, url in sorted(
                _ability_references(pokemon_resources).items()
            )  
        }
    except PokeAPIError as exc:
        raise ExtractionError(str(exc)) from exc

    return {
        "metadata": {
            "source": "PokéAPI",
            "resource": "location-area",
            "requested_location_area": normalized_area_name,
            "extracted_at_utc": datetime.now(UTC).isoformat(),
        },
        "location_area": area_data,
        "location": location_data,
        "pokemon": pokemon_resources,
        "abilities": ability_resources,
    }
