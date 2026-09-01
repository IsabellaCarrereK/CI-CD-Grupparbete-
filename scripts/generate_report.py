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

# Official-ish Pokemon type colors, used to give each tile a bit of
# personality. Falls back to a neutral gray for unknown/missing types.
TYPE_COLORS = {
    "normal": "#A8A878",
    "fire": "#F08030",
    "water": "#6890F0",
    "electric": "#F8D030",
    "grass": "#78C850",
    "ice": "#98D8D8",
    "fighting": "#C03028",
    "poison": "#A040A0",
    "ground": "#E0C068",
    "flying": "#A890F0",
    "psychic": "#F85888",
    "bug": "#A8B820",
    "rock": "#B8A038",
    "ghost": "#705898",
    "dragon": "#7038F8",
    "dark": "#705848",
    "steel": "#B8B8D0",
    "fairy": "#EE99AC",
}
DEFAULT_TYPE_COLOR = "#9aa0ac"

POKEBALL_SVG = (
    '<svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">'
    '<circle cx="16" cy="16" r="14" fill="#fff" stroke="#1c1e26" '
    'stroke-width="2"/>'
    '<path d="M2 16a14 14 0 0 1 28 0z" fill="#ee1515" '
    'stroke="#1c1e26" stroke-width="2"/>'
    '<rect x="2" y="15" width="28" height="2" fill="#1c1e26"/>'
    '<circle cx="16" cy="16" r="5" fill="#fff" stroke="#1c1e26" '
    'stroke-width="2"/>'
    '<circle cx="16" cy="16" r="2" fill="#fff"/>'
    "</svg>"
)


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


def fetch_pokemon_info(
    name: str, session: requests.Session
) -> tuple[str | None, list[str]]:
    """Best-effort lookup of a Pokemon's sprite and *all* of its types.

    Returns (sprite_url, types). sprite_url may be None and types may be
    an empty list on failure, so a flaky request never breaks the report.
    """
    url = POKEAPI_POKEMON_URL.format(name=name)

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()

        sprite_url = payload.get("sprites", {}).get("front_default")
        types = [
            t["type"]["name"]
            for t in payload.get("types", [])
            if isinstance(t, dict) and "type" in t
        ]

        return sprite_url, types
    except (requests.RequestException, ValueError, KeyError):
        return None, []


def build_pokemon_info_map(
    names: list[str],
) -> dict[str, tuple[str | None, list[str]]]:
    """Fetch (sprite_url, types) for a list of Pokemon names."""
    info_map: dict[str, tuple[str | None, list[str]]] = {}

    with requests.Session() as session:
        for name in names:
            info_map[name] = fetch_pokemon_info(name, session)

    return info_map


def render_type_badges(types: list[str]) -> str:
    """Render every type of a Pokemon as a small colored badge."""
    badges = []

    for type_name in types:
        color = TYPE_COLORS.get(type_name.lower(), DEFAULT_TYPE_COLOR)
        safe_type = escape(type_name)
        badges.append(
            f'<span class="type-badge" style="background:{color}">'
            f"{safe_type}</span>"
        )

    return "".join(badges)


def render_pokemon_tile(
    name: str,
    sprite_url: str | None,
    types: list[str] | None = None,
    abilities: list[str] | None = None,
) -> str:
    """Render one Pokemon as a small tile: sprite, type badges, name.

    Hovering (or focusing, for keyboard users) reveals its abilities in a
    small custom tooltip, so the grid stays compact while the detail is
    still one hover/tab away.
    """
    safe_name = escape(str(name))
    types = types or []
    abilities = abilities or []
    tooltip_text = ", ".join(abilities) if abilities else "No ability data"
    safe_tooltip = escape(f"Abilities: {tooltip_text}")
    accent_color = TYPE_COLORS.get(
        (types[0].lower() if types else ""), DEFAULT_TYPE_COLOR
    )

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

    type_badges = render_type_badges(types)

    return f"""
      <figure class="pokemon-tile" tabindex="0"
              data-tooltip="{safe_tooltip}"
              style="--type-color:{accent_color}">
        {image}
        <figcaption>{safe_name}</figcaption>
        <div class="type-badges">{type_badges}</div>
      </figure>
    """


def render_abilities_summary(abilities: list[str]) -> str:
    """Render the distinct abilities seen at a location as small pills."""
    if not abilities:
        return ""

    pills = "".join(
        f'<span class="ability-pill">{escape(str(a))}</span>' for a in abilities
    )

    return f"""
      <p class="abilities-label">Abilities in this area</p>
      <div class="ability-list">{pills}</div>
    """


def render_location_card(
    entry: dict, info_map: dict[str, tuple[str | None, list[str]]]
) -> str:
    """Render one location as an HTML card."""
    region = escape(str(entry.get("region", "unknown")))
    location = escape(str(entry.get("location", "unknown")))
    pokemon_count = int(entry.get("pokemon_count", 0))
    pokemons = entry.get("pokemons", [])
    pokemon_abilities = entry.get("pokemon_abilities", {})
    abilities = entry.get("abilities", [])

    tiles = "".join(
        render_pokemon_tile(
            name,
            *info_map.get(name, (None, [])),
            pokemon_abilities.get(name),
        )
        for name in pokemons
    )
    abilities_summary = render_abilities_summary(abilities)

    return f"""
    <article class="card">
      <header>
        <h2>{location}</h2>
        <span class="region">{region}</span>
      </header>
      <p class="count">{pokemon_count} Pok&eacute;mon</p>
      <div class="pokemon-grid">{tiles}</div>
      {abilities_summary}
    </article>
    """


def render_page(
    entries: list[dict], info_map: dict[str, tuple[str | None, list[str]]]
) -> str:
    """Render the full HTML page for all aggregated locations."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total_locations = len(entries)
    total_pokemon = sum(int(e.get("pokemon_count", 0)) for e in entries)
    total_abilities = sum(int(e.get("ability_count", 0)) for e in entries)
    cards = "".join(
        render_location_card(entry, info_map) for entry in entries
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeAPI Pipeline Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link
  href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;800&display=swap"
  rel="stylesheet">
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f5f6fa;
    --card-bg: #ffffff;
    --text: #1c1e26;
    --muted: #666a77;
    --accent: #d9433f;
    --chip-bg: #eef0f5;
    --brand-red: #ee1515;
    --brand-yellow: #ffcb05;
    --brand-blue: #3b4cca;
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
  .rainbow-bar {{
    height: 6px;
    background: linear-gradient(
      90deg,
      var(--brand-red), var(--brand-yellow), var(--brand-blue),
      var(--brand-red)
    );
    background-size: 200% 100%;
    animation: slide 6s linear infinite;
  }}
  @keyframes slide {{
    to {{ background-position: 200% 0; }}
  }}
  header.hero {{
    padding: 2.5rem 1.5rem 1.5rem;
    text-align: center;
  }}
  header.hero h1 {{
    margin: 0 0 .25rem;
    font-size: 2rem;
    font-family: "Baloo 2", "Segoe UI", sans-serif;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: .5rem;
  }}
  header.hero h1 svg {{ animation: wiggle 3.5s ease-in-out infinite; }}
  @keyframes wiggle {{
    0%, 100% {{ transform: rotate(0deg); }}
    50% {{ transform: rotate(-12deg); }}
  }}
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
    transition: transform .18s ease, box-shadow .18s ease;
  }}
  .card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 10px 20px rgba(0,0,0,.12);
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
    --type-color: {DEFAULT_TYPE_COLOR};
    position: relative;
    margin: 0;
    width: 5rem;
    text-align: center;
    background: var(--chip-bg);
    border: 2px solid var(--type-color);
    border-radius: .6rem;
    padding: .4rem .3rem .55rem;
    cursor: default;
    transition: transform .15s ease, box-shadow .15s ease;
  }}
  .pokemon-tile:hover, .pokemon-tile:focus-visible {{
    transform: translateY(-2px) scale(1.06);
    box-shadow: 0 4px 10px rgba(0,0,0,.15);
    outline: none;
  }}
  .pokemon-tile[data-tooltip]:hover::after,
  .pokemon-tile[data-tooltip]:focus-visible::after {{
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: var(--text);
    color: var(--card-bg);
    padding: .4rem .6rem;
    border-radius: .4rem;
    font-size: .7rem;
    text-transform: none;
    white-space: normal;
    width: max-content;
    max-width: 10rem;
    box-shadow: 0 6px 14px rgba(0,0,0,.25);
    z-index: 20;
    pointer-events: none;
  }}
  .pokemon-tile[data-tooltip]:hover::before,
  .pokemon-tile[data-tooltip]:focus-visible::before {{
    content: "";
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: var(--text);
    z-index: 20;
    pointer-events: none;
  }}
  .pokemon-tile img {{
    width: 52px;
    height: 52px;
    display: block;
    margin: 0 auto;
    image-rendering: pixelated;
    transition: transform .2s ease;
  }}
  .pokemon-tile:hover img {{ transform: scale(1.12) rotate(-4deg); }}
  .pokemon-tile .no-sprite {{
    display: block;
    width: 52px;
    height: 52px;
    line-height: 52px;
    margin: 0 auto;
    color: var(--muted);
    font-weight: 600;
    font-size: 1.3rem;
  }}
  .pokemon-tile figcaption {{
    font-size: .7rem;
    text-transform: capitalize;
    margin-top: .2rem;
    overflow-wrap: break-word;
  }}
  .type-badges {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: .2rem;
    margin-top: .3rem;
  }}
  .type-badge {{
    color: #fff;
    font-size: .6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .02em;
    border-radius: 999px;
    padding: .05rem .4rem;
    text-shadow: 0 1px 1px rgba(0,0,0,.25);
  }}
  .abilities-label {{
    margin: .9rem 0 .3rem;
    font-size: .75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .03em;
  }}
  .ability-list {{ display: flex; flex-wrap: wrap; gap: .35rem; }}
  .ability-pill {{
    background: transparent;
    border: 1px solid var(--chip-bg);
    color: var(--accent);
    border-radius: 999px;
    padding: .1rem .55rem;
    font-size: .75rem;
    text-transform: capitalize;
    transition: transform .15s ease;
  }}
  .ability-pill:hover {{
    transform: scale(1.08);
    background: var(--chip-bg);
  }}
  footer {{
    text-align: center; color: var(--muted); font-size: .8rem;
    padding-bottom: 2rem;
  }}
</style>
</head>
<body>
  <div class="rainbow-bar"></div>
  <header class="hero">
    <h1>{POKEBALL_SVG} PokeAPI Pipeline Report</h1>
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
      <div class="stat">
        <strong>{total_abilities}</strong>
        <span>abilities (with duplicates)</span>
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
    info_map = build_pokemon_info_map(unique_names)

    html = render_page(entries, info_map)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    SITE_OUTPUT_PATH.write_text(html, encoding="utf-8")

    found_sprites = sum(1 for sprite, _ in info_map.values() if sprite)
    print(f"Report written to {SITE_OUTPUT_PATH} ({len(entries)} locations).")
    print(f"Sprites fetched: {found_sprites}/{len(unique_names)}")


if __name__ == "__main__":
    main()