"""Tests for the demo-report generator's sprite/type/ability behaviour.

These live in tests/ alongside the rest of the pipeline's tests. Since
generate_report.py lives in scripts/ (not src/), we add that folder to
sys.path directly instead of touching the shared pytest/pythonpath config
in pyproject.toml.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_report as gr  # noqa: E402


class _RaisingSession:
    """A fake requests.Session whose .get() always fails."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url, timeout):  # noqa: ARG002
        raise gr.requests.exceptions.ConnectionError("simulated network failure")


class _NotFoundResponse:
    """A fake response simulating PokeAPI's 404 for an unknown name."""

    def raise_for_status(self):
        raise gr.requests.exceptions.HTTPError("404 Not Found")

    def json(self):
        return {}


class _NotFoundSession:
    def get(self, url, timeout):  # noqa: ARG002
        return _NotFoundResponse()


class _OkResponse:
    """A fake successful PokeAPI response with a sprite and two types."""

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "sprites": {"front_default": "https://example.com/gyarados.png"},
            "types": [
                {"type": {"name": "water"}},
                {"type": {"name": "flying"}},
            ],
        }


class _OkSession:
    def get(self, url, timeout):  # noqa: ARG002
        return _OkResponse()


def test_fetch_pokemon_info_returns_empty_on_connection_error():
    """A network failure must not raise; it should degrade to (None, [])."""
    assert gr.fetch_pokemon_info("gyarados", _RaisingSession()) == (None, [])


def test_fetch_pokemon_info_returns_empty_on_http_error():
    """An unknown Pokemon name (404) should also degrade to (None, [])."""
    assert gr.fetch_pokemon_info("missingno", _NotFoundSession()) == (None, [])


def test_fetch_pokemon_info_returns_sprite_and_all_types():
    """A successful lookup returns the sprite URL and every type, in order."""
    sprite_url, types = gr.fetch_pokemon_info("gyarados", _OkSession())

    assert sprite_url == "https://example.com/gyarados.png"
    assert types == ["water", "flying"]


def test_render_pokemon_tile_falls_back_without_sprite():
    """No sprite URL -> a text placeholder, no broken <img> tag."""
    html = gr.render_pokemon_tile("missingno", None, [])

    assert "<img" not in html
    assert 'class="no-sprite"' in html
    assert "missingno" in html


def test_render_pokemon_tile_uses_sprite_when_available():
    """A sprite URL renders an <img> with the correct escaped src."""
    html = gr.render_pokemon_tile("gyarados", "https://example.com/gyarados.png", [])

    assert '<img src="https://example.com/gyarados.png"' in html
    assert "{{" not in html
    assert "}}" not in html


def test_render_pokemon_tile_shows_every_type_as_a_badge():
    """All of a Pokemon's types render as badges, not just the first."""
    html = gr.render_pokemon_tile("gyarados", None, ["water", "flying"])

    assert '<span class="type-badge" style="background:#6890F0">water</span>' in html
    assert (
        '<span class="type-badge" style="background:#A890F0">flying</span>' in html
    )


def test_render_pokemon_tile_puts_abilities_in_hover_tooltip():
    """Abilities show up as a data-tooltip attribute, not the native title."""
    html = gr.render_pokemon_tile(
        "gyarados", None, ["water"], ["intimidate", "moxie"]
    )

    assert 'data-tooltip="Abilities: intimidate, moxie"' in html
    assert "title=\"Abilities" not in html


def test_build_pokemon_info_map_handles_total_failure_gracefully():
    """If every request fails, we still get a complete map of (None, [])."""
    names = ["gyarados", "magikarp"]

    original_session = gr.requests.Session
    gr.requests.Session = _RaisingSession  # type: ignore[assignment]
    try:
        info_map = gr.build_pokemon_info_map(names)
    finally:
        gr.requests.Session = original_session

    assert info_map == {"gyarados": (None, []), "magikarp": (None, [])}


def test_render_pokemon_tile_exposes_search_metadata():
    """Pokemon tiles include searchable Pokemon and ability metadata."""
    html = gr.render_pokemon_tile(
        "Gyarados",
        None,
        ["water", "flying"],
        ["Intimidate", "Moxie"],
    )

    assert 'data-pokemon="gyarados"' in html
    assert 'data-abilities="intimidate moxie"' in html


def test_render_location_card_exposes_search_metadata():
    """Location cards include searchable region, location, and abilities."""
    entry = {
        "region": "Sinnoh",
        "location": "Canalave-City",
        "pokemon_count": 1,
        "pokemons": ["gyarados"],
        "pokemon_abilities": {
            "gyarados": ["intimidate", "moxie"],
        },
        "abilities": ["intimidate", "moxie"],
    }
    info_map = {
        "gyarados": (None, ["water", "flying"]),
    }

    html = gr.render_location_card(entry, info_map)

    assert 'data-region="sinnoh"' in html
    assert 'data-location="canalave-city"' in html
    assert 'data-ability="intimidate"' in html
    assert 'data-ability="moxie"' in html


def test_render_page_contains_live_filter_controls():
    """The generated report contains the live client-side filter UI."""
    entry = {
        "region": "Sinnoh",
        "location": "Canalave-City",
        "pokemon_count": 1,
        "pokemons": ["gyarados"],
        "pokemon_abilities": {
            "gyarados": ["intimidate", "moxie"],
        },
        "ability_count": 2,
        "abilities": ["intimidate", "moxie"],
    }
    info_map = {
        "gyarados": (None, ["water", "flying"]),
    }

    html = gr.render_page([entry], info_map)

    assert 'id="filter-pokemon"' in html
    assert 'id="filter-location"' in html
    assert 'id="filter-region"' in html
    assert 'id="filter-ability"' in html
    assert 'id="clear-filters"' in html
    assert 'id="filter-summary"' in html
    assert 'id="no-results"' in html
    assert 'addEventListener("input", applyFilters)' in html
    assert "visibleAbilities" in html
