"""Tests for the demo-report generator's sprite fallback behaviour.

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


def test_fetch_sprite_url_returns_none_on_connection_error():
    """A network failure must not raise; it should degrade to None."""
    assert gr.fetch_sprite_url("gyarados", _RaisingSession()) is None


def test_fetch_sprite_url_returns_none_on_http_error():
    """An unknown Pokemon name (404) should also degrade to None."""
    assert gr.fetch_sprite_url("missingno", _NotFoundSession()) is None


def test_render_pokemon_tile_falls_back_without_sprite():
    """No sprite URL -> a text placeholder, no broken <img> tag."""
    html = gr.render_pokemon_tile("missingno", None)

    assert "<img" not in html
    assert 'class="no-sprite"' in html
    assert "missingno" in html


def test_render_pokemon_tile_uses_sprite_when_available():
    """A sprite URL renders an <img> with the correct escaped src."""
    html = gr.render_pokemon_tile("gyarados", "https://example.com/gyarados.png")

    assert '<img src="https://example.com/gyarados.png"' in html
    assert "{{" not in html
    assert "}}" not in html


def test_build_sprite_map_handles_total_failure_gracefully():
    """If every request fails, we still get a complete map of None values."""
    names = ["gyarados", "magikarp"]

    original_session = gr.requests.Session
    gr.requests.Session = _RaisingSession  # type: ignore[assignment]
    try:
        sprite_map = gr.build_sprite_map(names)
    finally:
        gr.requests.Session = original_session

    assert sprite_map == {"gyarados": None, "magikarp": None}