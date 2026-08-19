# Extraction Package

This folder contains the Python code for the PokéAPI **Extract** stage.

## `api.py`

Owns HTTP communication only.

`PokeAPIClient`:

- creates and reuses a `requests.Session`
- sends requests with a timeout
- checks HTTP errors
- validates that a JSON object was returned
- converts network/JSON failures into `PokeAPIError`

It does not decide which resources make up the final extraction.

## `extract.py`

Owns extraction orchestration.

`extract_location_area()`:

1. retrieves a `location-area`
2. follows its `location.url`
3. reads `pokemon_encounters`
4. follows each unique Pokémon URL
5. combines those raw resources into one extraction payload

It deliberately does not clean, normalize, aggregate, or rename the raw API fields. Those operations belong to the transformation stage.

## `transform.py`

Owns the transformation stage.

It:

- reads the raw extraction JSON from `data/raw/`
- extracts region, location, and location-area
- extracts each Pokémon and its type(s)
- creates a simpler structured dataset
- saves the transformed data to `data/processed/`

The raw extraction data is kept unchanged. The processed output contains only the fields needed for the next stages of the pipeline

## `storage.py`

Owns persistence only.

`save_json()` creates the parent directory when necessary and writes readable UTF-8 JSON.

It knows nothing about PokéAPI or extraction rules.

## `cli.py`

Owns command-line interaction.

It:

- reads the requested location-area name
- accepts an optional output directory
- calls the extraction workflow
- saves the result
- prints a concise success or failure message

## `__main__.py`

Allows the package to be run as:

```bash
python -m pokemon_pipeline canalave-city-area
```

## Why the package is separated this way

Each module has one main reason to change:

- API protocol changes -> `api.py`
- extraction requirements change -> `extract.py`
- file-storage rules change -> `storage.py`
- command-line behavior changes -> `cli.py`

That is the practical separation of concerns used in this project.
