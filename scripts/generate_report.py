"""Build a static HTML report from the aggregated Pokemon data.

Reads data/aggregated/location_summary.json (produced by
pokemon_pipeline.aggregate) and writes a single self-contained
site/index.html page that can be published to GitHub Pages.

Usage:
    python scripts/generate_report.py
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from html import escape
from pathlib import Path

import requests

AGGREGATED_DATA_PATH = Path("data/aggregated/location_summary.json")
SITE_DIR = Path("site")
SITE_OUTPUT_PATH = SITE_DIR / "index.html"
POKEAPI_POKEMON_URL = "https://pokeapi.co/api/v2/pokemon/{name}"
REQUEST_TIMEOUT_SECONDS = 10
PREVIEW_POKEMON_COUNT = 6

LOCATION_BANNERS = {
    "johto-route-34": "johto-route-34.webp",
    "fuego-ironworks": "fuego-ironworks.webp",
    "valley-windworks": "valley-windworks.webp",
    "eterna-forest": "eterna-forest.webp",
    "ilex-forest": "ilex-forest.webp",
    "johto-route-32": "johto-route-32.webp",
    "viridian-forest": "viridian-forest.webp",
    "kanto-route-22": "kanto-route-22.webp",
    "kanto-route-25": "kanto-route-25.webp",
}

BANNER_SOURCE_DIR = Path("assets/location-banners")
BANNER_SITE_DIR = SITE_DIR / "assets" / "location-banners"


def location_banner_css_value(location_value: str) -> str:
    """Return the deployed banner URL used by one location card."""
    filename = LOCATION_BANNERS.get(location_value.lower())

    if filename is None:
        return "none"

    return f"url('assets/location-banners/{filename}')"


def copy_location_banners() -> None:
    """Copy committed location artwork into the generated Pages site."""
    BANNER_SITE_DIR.mkdir(parents=True, exist_ok=True)

    for filename in LOCATION_BANNERS.values():
        source = BANNER_SOURCE_DIR / filename

        if not source.exists():
            raise FileNotFoundError(
                f"Location banner not found: {source}"
            )

        shutil.copy2(
            source,
            BANNER_SITE_DIR / filename,
        )


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


def load_aggregated_data(
    path: Path = AGGREGATED_DATA_PATH,
) -> list[dict]:
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


def collect_unique_pokemon_names(
    entries: list[dict],
) -> list[str]:
    """Return every distinct Pokemon name referenced across all locations."""
    names: set[str] = set()

    for entry in entries:
        names.update(entry.get("pokemons", []))

    return sorted(names)


def fetch_pokemon_info(
    name: str,
    session: requests.Session,
) -> tuple[str | None, list[str]]:
    """Best-effort lookup of a Pokemon's sprite and all of its types."""
    url = POKEAPI_POKEMON_URL.format(name=name)

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()

        sprite_url = payload.get(
            "sprites",
            {},
        ).get("front_default")

        types = [
            item["type"]["name"]
            for item in payload.get("types", [])
            if isinstance(item, dict) and "type" in item
        ]

        return sprite_url, types

    except (
        requests.RequestException,
        ValueError,
        KeyError,
    ):
        return None, []


def build_pokemon_info_map(
    names: list[str],
) -> dict[str, tuple[str | None, list[str]]]:
    """Fetch sprite URL and types for each Pokemon name."""
    info_map: dict[
        str,
        tuple[str | None, list[str]],
    ] = {}

    with requests.Session() as session:
        for name in names:
            info_map[name] = fetch_pokemon_info(
                name,
                session,
            )

    return info_map


def render_type_badges(types: list[str]) -> str:
    """Render every Pokemon type as a colored badge."""
    badges = []

    for type_name in types:
        color = TYPE_COLORS.get(
            type_name.lower(),
            DEFAULT_TYPE_COLOR,
        )
        safe_type = escape(type_name)

        badges.append(
            f'<span class="type-badge" '
            f'style="background:{color}">'
            f"{safe_type}</span>"
        )

    return "".join(badges)


def render_pokemon_tile(
    name: str,
    sprite_url: str | None,
    types: list[str] | None = None,
    abilities: list[str] | None = None,
) -> str:
    """Render one searchable Pokemon tile."""
    safe_name = escape(str(name))
    types = types or []
    abilities = abilities or []

    search_pokemon = escape(
        str(name).lower(),
        quote=True,
    )

    search_abilities = escape(
        " ".join(
            str(ability).lower()
            for ability in abilities
        ),
        quote=True,
    )

    tooltip_text = (
        ", ".join(abilities)
        if abilities
        else "No ability data"
    )

    safe_tooltip = escape(
        f"Abilities: {tooltip_text}"
    )

    accent_color = TYPE_COLORS.get(
        types[0].lower() if types else "",
        DEFAULT_TYPE_COLOR,
    )

    if sprite_url:
        safe_sprite_url = escape(sprite_url)

        image = (
            f'<img src="{safe_sprite_url}" '
            f'alt="{safe_name}" '
            'loading="lazy" '
            'onerror="this.replaceWith(Object.assign('
            "document.createElement('span'),"
            "{className:'no-sprite',"
            "textContent:'?'}))\">"
        )
    else:
        image = '<span class="no-sprite">?</span>'

    type_badges = render_type_badges(types)

    return f"""
      <figure class="pokemon-tile"
              tabindex="0"
              data-pokemon="{search_pokemon}"
              data-abilities="{search_abilities}"
              data-tooltip="{safe_tooltip}"
              style="--type-color:{accent_color}">
        {image}
        <figcaption>{safe_name}</figcaption>
        <div class="type-badges">
          {type_badges}
        </div>
      </figure>
    """


def render_abilities_summary(
    abilities: list[str],
) -> str:
    """Render the distinct abilities seen at a location."""
    if not abilities:
        return ""

    pills = "".join(
        (
            '<span class="ability-pill" '
            f'data-ability="{escape(str(ability).lower(), quote=True)}">'
            f"{escape(str(ability))}</span>"
        )
        for ability in abilities
    )

    return f"""
      <p class="abilities-label">
        Abilities in this area
      </p>
      <div class="ability-list">
        {pills}
      </div>
    """


def format_location_name(location_value: str, region_value: str) -> str:
    """Turn API location slugs into compact human-readable labels."""
    normalized = location_value.lower()
    region_prefix = f"{region_value.lower()}-"

    if normalized.startswith(region_prefix):
        normalized = normalized[len(region_prefix):]

    words = normalized.replace("-", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in words)


def render_location_card(
    entry: dict, info_map: dict[str, tuple[str | None, list[str]]]
) -> str:
    """Render one expandable location card."""
    region_value = str(entry.get("region", "unknown"))
    location_value = str(entry.get("location", "unknown"))

    region = escape(region_value)
    display_location = escape(
        format_location_name(location_value, region_value)
    )

    search_region = escape(region_value.lower(), quote=True)
    search_location = escape(location_value.lower(), quote=True)
    search_location_label = escape(
        format_location_name(location_value, region_value).lower(),
        quote=True,
    )

    pokemon_count = int(entry.get("pokemon_count", 0))
    pokemons = entry.get("pokemons", [])
    pokemon_abilities = entry.get("pokemon_abilities", {})
    abilities = entry.get("abilities", [])
    banner_image = location_banner_css_value(location_value)

    tiles = "".join(
        render_pokemon_tile(
            name,
            *info_map.get(name, (None, [])),
            pokemon_abilities.get(name),
        )
        for name in pokemons
    )

    abilities_summary = render_abilities_summary(abilities)

    if pokemon_count > PREVIEW_POKEMON_COUNT:
        preview_note = (
            f'<p class="preview-note">'
            f"Showing {PREVIEW_POKEMON_COUNT} of {pokemon_count} Pokémon"
            "</p>"
        )
        expand_button = (
            '<button class="expand-toggle" type="button" '
            'aria-expanded="false">'
            f"Show all {pokemon_count} Pokémon "
            '<span aria-hidden="true">▾</span>'
            "</button>"
        )
    else:
        preview_note = ""
        expand_button = ""

    return f"""
    <article class="card"
             data-region="{search_region}"
             data-location="{search_location}"
             data-location-label="{search_location_label}"
             data-expanded="false"
             data-preview-count="{PREVIEW_POKEMON_COUNT}"
             style="--banner-image: {banner_image}">
      <div class="card-banner">
        <span class="region-badge">{region}</span>
        <span class="count-badge"
              data-total-count="{pokemon_count}">
          {pokemon_count} Pokémon
        </span>
      </div>

      <div class="card-body">
        <h2>{display_location}</h2>

        <div class="pokemon-grid">
          {tiles}
        </div>

        {preview_note}
        {expand_button}
        {abilities_summary}
      </div>
    </article>
    """


def render_page(
    entries: list[dict], info_map: dict[str, tuple[str | None, list[str]]]
) -> str:
    """Render the full searchable location explorer."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    total_locations = len(entries)
    total_pokemon_entries = sum(
        int(entry.get("pokemon_count", 0))
        for entry in entries
    )
    unique_pokemon = len(collect_unique_pokemon_names(entries))

    regions = {
        str(entry.get("region", "")).strip().lower()
        for entry in entries
        if str(entry.get("region", "")).strip()
    }
    total_regions = len(regions)

    display_order = [
        "eterna-forest",
        "valley-windworks",
        "fuego-ironworks",
        "johto-route-34",
        "ilex-forest",
        "johto-route-32",
        "viridian-forest",
        "kanto-route-22",
        "kanto-route-25",
    ]

    order_index = {
        location: index
        for index, location in enumerate(display_order)
    }

    display_entries = sorted(
        entries,
        key=lambda entry: order_index.get(
            str(entry.get("location", "")),
            len(display_order),
        ),
    )

    cards = "".join(
        render_location_card(entry, info_map)
        for entry in display_entries
    )

    if entries:
        page_content = cards
    else:
        page_content = (
            '<p class="empty-state">No aggregated data found.</p>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokéAPI Location Explorer</title>

<style>
  :root {{
    --bg: #eaf0f7;
    --bg-deep: #e3ebf5;
    --surface: #ffffff;
    --surface-soft: #f7f9fc;
    --text: #172033;
    --muted: #69758b;
    --border: #d6dfeb;
    --accent: #1f5fd6;
    --accent-soft: #e8f1ff;
    --ability-bg: #eaf3ff;
    --shadow: 0 12px 30px rgba(33, 55, 88, .12);
  }}

  * {{
    box-sizing: border-box;
  }}

  body {{
    margin: 0;
    min-height: 100vh;
    font-family:
      Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Roboto, Arial, sans-serif;
    background:
      linear-gradient(
        180deg,
        #ffffff 0%,
        #f8fafc 48%,
        #f1f4f8 100%
      );
    color: var(--text);
  }}

  header.hero {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 3rem 1.5rem 1.5rem;
    text-align: center;
  }}

  .eyebrow {{
    margin: 0 0 .55rem;
    color: var(--accent);
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
  }}

  header.hero h1 {{
    margin: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: .65rem;
    font-size: clamp(2rem, 5vw, 3rem);
    line-height: 1.08;
    letter-spacing: -.035em;
  }}

  header.hero h1 svg {{
    flex: 0 0 auto;
  }}

  .hero-copy {{
    max-width: 620px;
    margin: .8rem auto 0;
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.6;
  }}

  .stats {{
    display: flex;
    justify-content: center;
    gap: 3.5rem;
    margin-top: 1.8rem;
    flex-wrap: wrap;
  }}

  .stat {{
    min-width: 110px;
    text-align: center;
  }}

  .stat strong {{
    display: block;
    font-size: 1.75rem;
    line-height: 1;
  }}

  .stat span {{
    display: block;
    margin-top: .35rem;
    color: var(--muted);
    font-size: .78rem;
    font-weight: 600;
  }}

  .record-note {{
    margin: 1rem 0 0;
    color: var(--muted);
    font-size: .78rem;
  }}

  .filters {{
    max-width: 1180px;
    margin: 0 auto 1.4rem;
    padding: 0 1.5rem;
  }}

  .filter-panel {{
    padding: 1.15rem;
    background: #ffffff;
    border: 1px solid #d2dce8;
    border-radius: 1rem;
    box-shadow: 0 8px 24px rgba(33, 55, 88, .08);
  }}

  .filter-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .85rem;
  }}

  .filter-field {{
    display: flex;
    flex-direction: column;
    gap: .4rem;
    color: #39465c;
    font-size: .78rem;
    font-weight: 700;
  }}

  .filter-field input {{
    width: 100%;
    min-height: 42px;
    border: 1px solid #c9d3e1;
    border-radius: .55rem;
    padding: .65rem .75rem;
    background: #fff;
    color: var(--text);
    font: inherit;
    font-weight: 500;
  }}

  .filter-field input::placeholder {{
    color: #9aa5b6;
  }}

  .filter-field input:focus {{
    outline: 2px solid var(--text);
    outline-offset: 2px;
  }}

  .filter-actions {{
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: .9rem;
    flex-wrap: wrap;
  }}

  #clear-filters {{
    border: 1px solid var(--border);
    border-radius: .55rem;
    padding: .55rem .9rem;
    background: var(--surface-soft);
    color: var(--text);
    cursor: pointer;
    font: inherit;
    font-size: .82rem;
    font-weight: 700;
  }}

  #clear-filters:hover {{
    background: var(--accent-soft);
  }}

  #filter-summary {{
    margin: 0;
    color: var(--muted);
    font-size: .86rem;
  }}

  main {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    align-items: start;
    gap: 1.25rem;
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 1.5rem 3.5rem;
  }}

  .card {{
    overflow: hidden;
    background: var(--surface);
    border: 1px solid #ccd8e6;
    border-radius: 1rem;
    box-shadow: var(--shadow);
  }}

  .card-banner {{
    position: relative;
    height: 94px;
    overflow: hidden;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: .85rem;
    background:
      linear-gradient(
        135deg,
        #a8d8ff 0%,
        #d9efff 45%,
        #b9e6c8 100%
      );
  }}

  .card[data-region="johto"] .card-banner {{
    background:
      linear-gradient(
        135deg,
        #bbd9ef 0%,
        #e1edf4 42%,
        #c9dfbc 100%
      );
  }}

  .card-banner::before {{
    content: "";
    position: absolute;
    width: 125%;
    height: 75px;
    left: -15%;
    bottom: -46px;
    border-radius: 50%;
    background: rgba(85, 153, 104, .20);
  }}

  .card-banner::after {{
    content: "";
    position: absolute;
    width: 90%;
    height: 58px;
    right: -25%;
    bottom: -34px;
    border-radius: 50%;
    background: rgba(54, 114, 151, .13);
  }}

  /* Subdued location illustrations.
     The pale overlay keeps them atmospheric rather than noisy. */
  .card-banner {{
    isolation: isolate;
    background: #dce8f2;
  }}

  .card-banner::before {{
    content: "";
    display: block;
    position: absolute;
    inset: -5px;
    width: auto;
    height: auto;
    border-radius: 0;
    z-index: 0;

    background-image: var(--banner-image);
    background-size: cover;
    background-position: center;

    filter:
      saturate(1.04)
      contrast(1.04)
      brightness(.99);

    transform: scale(1.045);

    animation:
      scenic-drift
      28s
      ease-in-out
      infinite
      alternate;

    will-change: transform;
  }}

  .card-banner::after {{
    content: "";
    display: block;
    position: absolute;
    inset: 0;
    width: auto;
    height: auto;
    border-radius: 0;
    z-index: 1;

    background:
      linear-gradient(
        180deg,
        rgba(10, 28, 50, .015),
        rgba(255, 255, 255, .10)
      );

    pointer-events: none;
  }}

  @keyframes scenic-drift {{
    from {{
      transform:
        scale(1.045)
        translate3d(-.35%, 0, 0);
    }}

    to {{
      transform:
        scale(1.075)
        translate3d(.35%, -.35%, 0);
    }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    .card-banner::before {{
      animation: none;
      transform: scale(1.05);
    }}
  }}

  .region-badge,
  .count-badge {{
    position: relative;
    z-index: 2;
    border-radius: 999px;
    padding: .32rem .65rem;
    background: rgba(255, 255, 255, .96);
    box-shadow: 0 3px 10px rgba(33, 55, 88, .14);
    color: #253a5a;
    font-size: .7rem;
    font-weight: 800;
  }}

  .region-badge {{
    text-transform: uppercase;
    letter-spacing: .04em;
  }}

  .card-body {{
    padding: 1rem 1rem 1.15rem;
  }}

  .card h2 {{
    margin: 0 0 .85rem;
    font-size: 1.15rem;
    letter-spacing: -.015em;
  }}

  .pokemon-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .6rem;
  }}

  .pokemon-tile {{
    --type-color: {DEFAULT_TYPE_COLOR};
    position: relative;
    min-width: 0;
    margin: 0;
    padding: .45rem .3rem .5rem;
    text-align: center;
    background: #ffffff;
    border: 1px solid #d7e0eb;
    border-top: 3px solid var(--type-color);
    border-radius: .65rem;
    cursor: default;
  }}

  .pokemon-tile:focus-visible {{
    outline: 2px solid var(--text);
    outline-offset: 2px;
  }}

  .pokemon-tile img {{
    display: block;
    width: 58px;
    height: 58px;
    margin: 0 auto;
    image-rendering: pixelated;
  }}

  .pokemon-tile .no-sprite {{
    display: block;
    width: 58px;
    height: 58px;
    margin: 0 auto;
    color: var(--muted);
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 58px;
  }}

  .pokemon-tile figcaption {{
    margin-top: .15rem;
    overflow-wrap: anywhere;
    font-size: .69rem;
    font-weight: 700;
    text-transform: capitalize;
  }}

  .type-badges {{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: .2rem;
    margin-top: .3rem;
  }}

  .type-badge {{
    border-radius: 999px;
    padding: .05rem .32rem;
    color: #fff;
    font-size: .52rem;
    font-weight: 800;
    letter-spacing: .015em;
    text-shadow: 0 1px 1px rgba(0, 0, 0, .18);
    text-transform: uppercase;
  }}

  .pokemon-tile[data-tooltip]:hover::after,
  .pokemon-tile[data-tooltip]:focus-visible::after {{
    content: attr(data-tooltip);
    position: absolute;
    z-index: 20;
    bottom: calc(100% + 7px);
    left: 50%;
    width: max-content;
    max-width: 180px;
    transform: translateX(-50%);
    border-radius: .45rem;
    padding: .42rem .58rem;
    background: #172033;
    color: #fff;
    box-shadow: 0 6px 16px rgba(0, 0, 0, .18);
    font-size: .68rem;
    font-weight: 500;
    line-height: 1.35;
    pointer-events: none;
  }}

  .preview-note {{
    margin: .85rem 0 .45rem;
    color: var(--muted);
    font-size: .75rem;
    text-align: center;
  }}

  .expand-toggle {{
    display: block;
    width: 100%;
    margin: .2rem 0 .9rem;
    border: 1px solid var(--border);
    border-radius: .55rem;
    padding: .52rem .7rem;
    background: var(--surface-soft);
    color: var(--accent);
    cursor: pointer;
    font: inherit;
    font-size: .78rem;
    font-weight: 800;
  }}

  .expand-toggle:hover {{
    background: var(--accent-soft);
  }}

  .expand-toggle:focus-visible {{
    outline: 2px solid var(--text);
    outline-offset: 2px;
  }}

  .abilities-label {{
    margin: .9rem 0 .4rem;
    color: var(--muted);
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .045em;
    text-transform: uppercase;
  }}

  .ability-list {{
    display: flex;
    flex-wrap: wrap;
    gap: .3rem;
  }}

  .ability-pill {{
    border: 1px solid #cfe0f7;
    border-radius: 999px;
    padding: .16rem .5rem;
    background: var(--ability-bg);
    color: #234e88;
    font-size: .69rem;
    font-weight: 650;
    text-transform: capitalize;
  }}

  .no-results,
  .empty-state {{
    max-width: 1180px;
    margin: 0 auto 2rem;
    padding: 1rem 1.5rem;
    color: var(--muted);
    text-align: center;
  }}

  [hidden] {{
    display: none !important;
  }}

  footer {{
    padding: 0 1.5rem 2.5rem;
    color: var(--muted);
    font-size: .76rem;
    text-align: center;
  }}


  /* Spacious desktop presentation */
  @media (min-width: 951px) {{
    header.hero {{
      padding: 2rem 1.5rem 1.05rem;
    }}

    .stats {{
      margin-top: 1.25rem;
    }}

    .record-note {{
      margin-top: .65rem;
    }}

    .filters,
    main {{
      width: calc(100vw - 72px) !important;
      max-width: 1900px !important;
      margin-left: auto !important;
      margin-right: auto !important;
    }}

    .filters {{
      margin-bottom: 1.9rem !important;
    }}

    .filter-panel {{
      padding: 1.25rem 1.5rem !important;
    }}

    .filter-grid {{
      gap: 1.15rem !important;
    }}

    .filter-field input {{
      min-height: 46px !important;
      padding: .74rem .85rem !important;
    }}

    main {{
      grid-template-columns:
        repeat(3, minmax(0, 1fr)) !important;
      gap: 2.3rem !important;
      padding-bottom: 4.5rem !important;
    }}

    .card-banner {{
      height: 114px !important;
    }}

    .card-body {{
      padding: 1.55rem 1.5rem 1.7rem !important;
    }}

    .card h2 {{
      margin-bottom: 1.15rem !important;
      font-size: 1.25rem !important;
    }}

    .pokemon-grid {{
      grid-template-columns:
        repeat(6, minmax(0, 1fr)) !important;
      column-gap: .65rem !important;
      row-gap: .75rem !important;
      justify-content: stretch !important;
    }}

    .pokemon-tile {{
      width: auto !important;
      min-height: 105px !important;
      padding: .58rem .28rem .62rem !important;
    }}

    .pokemon-tile img,
    .pokemon-tile .no-sprite {{
      width: 58px !important;
      height: 58px !important;
    }}

    .pokemon-tile .no-sprite {{
      line-height: 58px !important;
    }}

    .pokemon-tile figcaption {{
      margin-top: .22rem !important;
      font-size: .72rem !important;
    }}

    .type-badges {{
      gap: .15rem !important;
      margin-top: .22rem !important;
    }}

    .type-badge {{
      padding: .05rem .3rem !important;
      font-size: .52rem !important;
    }}

    .preview-note {{
      margin: 1.05rem 0 .55rem !important;
    }}

    .expand-toggle {{
      margin: .25rem 0 1.25rem !important;
      padding: .62rem .8rem !important;
    }}

    .abilities-label {{
      margin-top: 1.2rem !important;
      padding-top: 1rem !important;
    }}

    .ability-list {{
      column-gap: .48rem !important;
      row-gap: .42rem !important;
    }}

    .ability-pill {{
      padding: .17rem .5rem !important;
      font-size: .68rem !important;
    }}
  }}

  @media (max-width: 950px) {{
    main {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}

    .filter-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
  }}

  @media (max-width: 620px) {{
    header.hero {{
      padding-top: 2rem;
    }}

    .stats {{
      gap: 1.4rem;
    }}

    main {{
      grid-template-columns: 1fr;
      padding-left: 1rem;
      padding-right: 1rem;
    }}

    .filters {{
      padding-left: 1rem;
      padding-right: 1rem;
    }}

    .filter-grid {{
      grid-template-columns: 1fr;
    }}
  }}
</style>
</head>

<body>
  <header class="hero">
    <p class="eyebrow">PokéAPI Pipeline Report</p>

    <h1>
      {POKEBALL_SVG}
      <span>PokéAPI Location Explorer</span>
    </h1>

    <p class="hero-copy">
      Explore Pokémon across real PokéAPI locations and filter the results
      by Pokémon, location, region, or ability.
    </p>

    <div class="stats">
      <div class="stat">
        <strong>{total_locations}</strong>
        <span>Locations</span>
      </div>

      <div class="stat">
        <strong>{unique_pokemon}</strong>
        <span>Unique Pokémon</span>
      </div>

      <div class="stat">
        <strong>{total_regions}</strong>
        <span>Regions</span>
      </div>
    </div>

    <p class="record-note">
      {total_pokemon_entries} Pokémon-location records loaded
    </p>
  </header>

  <section class="filters" aria-label="Report filters">
    <div class="filter-panel">
      <div class="filter-grid">
        <label class="filter-field">
          Pokémon
          <input id="filter-pokemon"
                 type="search"
                 placeholder="e.g. gyarados"
                 autocomplete="off">
        </label>

        <label class="filter-field">
          Location
          <input id="filter-location"
                 type="search"
                 placeholder="e.g. Eterna Forest"
                 autocomplete="off">
        </label>

        <label class="filter-field">
          Region
          <input id="filter-region"
                 type="search"
                 placeholder="e.g. Sinnoh"
                 autocomplete="off">
        </label>

        <label class="filter-field">
          Ability
          <input id="filter-ability"
                 type="search"
                 placeholder="e.g. intimidate"
                 autocomplete="off">
        </label>
      </div>

      <div class="filter-actions">
        <button id="clear-filters" type="button">
          Clear filters
        </button>
        <p id="filter-summary" aria-live="polite"></p>
      </div>
    </div>
  </section>

  <main>
    {page_content}
  </main>

  <p id="no-results" class="no-results" hidden>
    No matching results.
  </p>

  <script>
    (() => {{
      const pokemonInput =
        document.getElementById("filter-pokemon");
      const locationInput =
        document.getElementById("filter-location");
      const regionInput =
        document.getElementById("filter-region");
      const abilityInput =
        document.getElementById("filter-ability");
      const clearButton =
        document.getElementById("clear-filters");
      const summary =
        document.getElementById("filter-summary");
      const noResults =
        document.getElementById("no-results");

      const cards =
        Array.from(document.querySelectorAll(".card"));

      const totalEntries = {total_pokemon_entries};

      const normalize = (value) =>
        value.trim().toLowerCase();

      function applyFilters() {{
        const pokemonFilter = normalize(pokemonInput.value);
        const locationFilter = normalize(locationInput.value);
        const regionFilter = normalize(regionInput.value);
        const abilityFilter = normalize(abilityInput.value);

        const pokemonFiltering =
          Boolean(pokemonFilter || abilityFilter);

        const cardFiltering =
          Boolean(locationFilter || regionFilter);

        let visibleLocations = 0;
        let visiblePokemon = 0;

        cards.forEach((card) => {{
          const locationMatches =
            card.dataset.location.includes(locationFilter) ||
            card.dataset.locationLabel.includes(locationFilter);

          const regionMatches =
            card.dataset.region.includes(regionFilter);

          const cardMatches =
            locationMatches && regionMatches;

          const expanded =
            card.dataset.expanded === "true";

          const previewCount =
            Number(card.dataset.previewCount);

          const tiles =
            Array.from(
              card.querySelectorAll(".pokemon-tile")
            );

          let matchingInCard = 0;

          tiles.forEach((tile, index) => {{
            const pokemonMatches =
              tile.dataset.pokemon.includes(pokemonFilter);

            const abilityMatches =
              !abilityFilter ||
              tile.dataset.abilities
                .split(" ")
                .some((ability) => ability.includes(abilityFilter));

            const matches =
              cardMatches &&
              pokemonMatches &&
              abilityMatches;

            if (matches) {{
              matchingInCard += 1;
            }}

            const previewAllows =
              expanded || index < previewCount;

            const visible =
              matches &&
              (pokemonFiltering || previewAllows);

            tile.hidden = !visible;
          }});

          card.hidden =
            !cardMatches || matchingInCard === 0;

          const visibleAbilities = new Set();

          card
            .querySelectorAll(".pokemon-tile:not([hidden])")
            .forEach((tile) => {{
              tile.dataset.abilities
                .split(" ")
                .filter(Boolean)
                .forEach(
                  (ability) => visibleAbilities.add(ability)
                );
            }});

          card
            .querySelectorAll(".ability-pill")
            .forEach((pill) => {{
              pill.hidden =
                !visibleAbilities.has(pill.dataset.ability);
            }});

          const abilitiesLabel =
            card.querySelector(".abilities-label");
          const abilityList =
            card.querySelector(".ability-list");

          if (abilitiesLabel && abilityList) {{
            const hasVisibleAbilities =
              visibleAbilities.size > 0;

            abilitiesLabel.hidden =
              !hasVisibleAbilities;

            abilityList.hidden =
              !hasVisibleAbilities;
          }}

          const countBadge =
            card.querySelector(".count-badge");

          const totalCount =
            countBadge
              ? Number(countBadge.dataset.totalCount)
              : tiles.length;

          if (countBadge) {{
            if (pokemonFiltering) {{
              countBadge.textContent =
                matchingInCard + " matching Pokémon";
            }} else {{
              countBadge.textContent =
                totalCount + " Pokémon";
            }}
          }}

          const previewNote =
            card.querySelector(".preview-note");

          if (previewNote) {{
            previewNote.hidden =
              pokemonFiltering ||
              expanded ||
              !cardMatches;

            previewNote.textContent =
              "Showing " +
              Math.min(previewCount, totalCount) +
              " of " +
              totalCount +
              " Pokémon";
          }}

          const toggle =
            card.querySelector(".expand-toggle");

          if (toggle) {{
            toggle.hidden =
              pokemonFiltering || !cardMatches;

            toggle.setAttribute(
              "aria-expanded",
              expanded ? "true" : "false"
            );

            if (expanded) {{
              toggle.innerHTML =
                'Show less <span aria-hidden="true">▴</span>';
            }} else {{
              toggle.innerHTML =
                "Show all " +
                totalCount +
                ' Pokémon <span aria-hidden="true">▾</span>';
            }}
          }}

          if (!card.hidden) {{
            visibleLocations += 1;

            if (pokemonFiltering) {{
              visiblePokemon += matchingInCard;
            }}
          }}
        }});

        if (pokemonFiltering) {{
          const locationWord =
            visibleLocations === 1
              ? "location"
              : "locations";

          summary.textContent =
            visiblePokemon +
            " matching Pokémon in " +
            visibleLocations +
            " " +
            locationWord;
        }} else if (cardFiltering) {{
          const locationWord =
            visibleLocations === 1
              ? "location"
              : "locations";

          summary.textContent =
            visibleLocations +
            " matching " +
            locationWord;
        }} else {{
          summary.textContent =
            cards.length +
            " locations · " +
            totalEntries +
            " Pokémon-location records";
        }}

        noResults.hidden =
          visibleLocations !== 0;
      }}

      [
        pokemonInput,
        locationInput,
        regionInput,
        abilityInput,
      ].forEach((input) => {{
        input.addEventListener("input", applyFilters);
      }});

      document
        .querySelectorAll(".expand-toggle")
        .forEach((button) => {{
          button.addEventListener("click", () => {{
            const card = button.closest(".card");

            if (!card) {{
              return;
            }}

            const expanded =
              card.dataset.expanded === "true";

            card.dataset.expanded =
              expanded ? "false" : "true";

            applyFilters();
          }});
        }});

      clearButton.addEventListener("click", () => {{
        pokemonInput.value = "";
        locationInput.value = "";
        regionInput.value = "";
        abilityInput.value = "";

        applyFilters();
        pokemonInput.focus();
      }});

      applyFilters();
    }})();
  </script>

  <footer>
    Generated from the pipeline data on {generated_at}
  </footer>
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
    copy_location_banners()

    found_sprites = sum(1 for sprite, _ in info_map.values() if sprite)
    print(f"Report written to {SITE_OUTPUT_PATH} ({len(entries)} locations).")
    print(f"Sprites fetched: {found_sprites}/{len(unique_names)}")


if __name__ == "__main__":
    main()
