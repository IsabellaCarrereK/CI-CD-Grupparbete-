"""Build a static HTML report from the aggregated Pokemon data.

Reads data/aggregated/location_summary.json (produced by
pokemon_pipeline.aggregate) and writes a single self-contained
site/index.html page that can be published to GitHub Pages.

Usage:
    python scripts/generate_report.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path

import requests

AGGREGATED_DATA_PATH = Path("data/aggregated/location_summary.json")
SITE_DIR = Path("site")
SITE_OUTPUT_PATH = SITE_DIR / "index.html"
POKEAPI_POKEMON_URL = "https://pokeapi.co/api/v2/pokemon/{name}"
REQUEST_TIMEOUT_SECONDS = 10


def load_aggregated_data(path: Path = AGGREGATED_DATA_PATH) -> list[dict]:
    """Load the aggregated location summary produced by the pipeline."""
    if not path.exists():
        raise FileNotFoundError(
            f"Aggregated data not found at {path}. "
            "Run the extract/transform/validate/aggregate stages first."
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Aggregated data must be a JSON list")

    return data


def collect_unique_pokemon_names(entries: list[dict]) -> list[str]:
    """Return every distinct Pokemon name referenced across all locations."""
    names: set[str] = set()

    for entry in entries:
        names.update(entry.get("pokemons", []))

    return sorted(names)


def fetch_sprite_url(name: str, session: requests.Session) -> str | None:
    """Best-effort lookup of a Pokemon's sprite image from PokeAPI.

    Returns None on any failure so a flaky request never breaks the report.
    """
    url = POKEAPI_POKEMON_URL.format(name=name)

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        sprites = response.json().get("sprites", {})
        return sprites.get("front_default")
    except (requests.RequestException, ValueError):
        return None


def build_sprite_map(names: list[str]) -> dict[str, str | None]:
    """Fetch sprite URLs for a list of Pokemon names, one request each."""
    sprite_map: dict[str, str | None] = {}

    with requests.Session() as session:
        for name in names:
            sprite_map[name] = fetch_sprite_url(name, session)

    return sprite_map


def render_pokemon_tile(name: str, sprite_url: str | None) -> str:
    """Render one Pokemon as a small tile with its sprite, when available."""
    safe_name = escape(str(name))

    if sprite_url:
        safe_sprite_url = escape(sprite_url)
        image = (
            f'<img src="{safe_sprite_url}" alt="{safe_name}" loading="lazy" '
            "onerror=\"this.replaceWith(Object.assign("
            "document.createElement('span'),{className:'no-sprite',"
            "textContent:'?'}))\">"
        )
    else:
        image = '<span class="no-sprite">?</span>'

    return f"""
      <figure class="pokemon-tile">
        {image}
        <figcaption>{safe_name}</figcaption>
      </figure>
    """


def render_location_card(entry: dict, sprite_map: dict[str, str | None]) -> str:
    """Render one location as an HTML card."""
    region = escape(str(entry.get("region", "unknown")))
    location = escape(str(entry.get("location", "unknown")))
    pokemon_count = int(entry.get("pokemon_count", 0))
    pokemons = entry.get("pokemons", [])

    tiles = "".join(
        render_pokemon_tile(name, sprite_map.get(name)) for name in pokemons
    )

    return f"""
    <article class="card">
      <header>
        <h2>{location}</h2>
        <span class="region">{region}</span>
      </header>
      <p class="count">{pokemon_count} Pok&eacute;mon</p>
      <div class="pokemon-grid">{tiles}</div>
    </article>
    """


def render_page(entries: list[dict], sprite_map: dict[str, str | None]) -> str:
    """Render the full HTML page for all aggregated locations."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total_locations = len(entries)
    total_pokemon = sum(int(e.get("pokemon_count", 0)) for e in entries)
    cards = "".join(
        render_location_card(entry, sprite_map) for entry in entries
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeAPI Pipeline Report</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f5f6fa;
    --card-bg: #ffffff;
    --text: #1c1e26;
    --muted: #666a77;
    --accent: #d9433f;
    --chip-bg: #eef0f5;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14151a;
      --card-bg: #1f212a;
      --text: #f1f2f6;
      --muted: #9a9ea8;
      --chip-bg: #2a2d38;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
  }}
  header.hero {{
    padding: 2.5rem 1.5rem 1.5rem;
    text-align: center;
  }}
  header.hero h1 {{ margin: 0 0 .25rem; font-size: 1.75rem; }}
  header.hero p {{ margin: .25rem 0; color: var(--muted); }}
  .stats {{
    display: flex; gap: 1.5rem; justify-content: center;
    margin-top: 1rem; flex-wrap: wrap;
  }}
  .stat {{ text-align: center; }}
  .stat strong {{ display: block; font-size: 1.5rem; }}
  .stat span {{ color: var(--muted); font-size: .85rem; }}
  main {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1rem;
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 1.5rem 3rem;
  }}
  .card {{
    background: var(--card-bg);
    border-radius: .75rem;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
  }}
  .card header {{
    display: flex; justify-content: space-between; align-items: baseline;
  }}
  .card h2 {{ margin: 0; font-size: 1.1rem; text-transform: capitalize; }}
  .region {{ color: var(--muted); font-size: .8rem; text-transform: capitalize; }}
  .count {{ margin: .35rem 0 .6rem; color: var(--accent); font-weight: 600; }}
  .pokemon-grid {{
    display: flex; flex-wrap: wrap; gap: .5rem;
  }}
  .pokemon-tile {{
    margin: 0;
    width: 4.5rem;
    text-align: center;
    background: var(--chip-bg);
    border-radius: .6rem;
    padding: .35rem .25rem .5rem;
  }}
  .pokemon-tile img {{
    width: 40px;
    height: 40px;
    display: block;
    margin: 0 auto;
    image-rendering: pixelated;
  }}
  .pokemon-tile .no-sprite {{
    display: block;
    width: 40px;
    height: 40px;
    line-height: 40px;
    margin: 0 auto;
    color: var(--muted);
    font-weight: 600;
  }}
  .pokemon-tile figcaption {{
    font-size: .7rem;
    text-transform: capitalize;
    margin-top: .2rem;
    overflow-wrap: break-word;
  }}
  footer {{
    text-align: center; color: var(--muted); font-size: .8rem;
    padding-bottom: 2rem;
  }}
</style>
</head>
<body>
  <header class="hero">
    <h1>PokeAPI Pipeline Report</h1>
    <p>
      DE25 CI/CD Grupparbete &mdash; extract &rarr; transform &rarr;
      validate &rarr; aggregate
    </p>
    <div class="stats">
      <div class="stat">
        <strong>{total_locations}</strong>
        <span>locations</span>
      </div>
      <div class="stat">
        <strong>{total_pokemon}</strong>
        <span>Pok&eacute;mon (with duplicates)</span>
      </div>
    </div>
  </header>
  <main>
    {cards if entries else '<p style="text-align:center">No aggregated data found.</p>'}
  </main>
  <footer>Generated automatically by GitHub Actions on {generated_at}</footer>
</body>
</html>
"""


def main() -> None:
    entries = load_aggregated_data()

    unique_names = collect_unique_pokemon_names(entries)
    sprite_map = build_sprite_map(unique_names)

    html = render_page(entries, sprite_map)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    SITE_OUTPUT_PATH.write_text(html, encoding="utf-8")

    found_sprites = sum(1 for url in sprite_map.values() if url)
    print(f"Report written to {SITE_OUTPUT_PATH} ({len(entries)} locations).")
    print(f"Sprites fetched: {found_sprites}/{len(unique_names)}")


if __name__ == "__main__":
    main()