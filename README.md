![CI](https://github.com/IsabellaCarrereK/CI-CD-Grupparbete-/actions/workflows/ci.yml/badge.svg)
🔗 [Live demo](https://isabellacarrerek.github.io/CI-CD-Grupparbete-/)
# CI-CD-Grupparbete

Group project for the DE25 DevOps CI/CD course.

## Pipeline stages

The project is developed collaboratively in feature branches and merged into `main`
through reviewed pull requests.

### Extract: PokéAPI

The extraction stage retrieves raw data from PokéAPI for a selected
`location-area`, follows the parent `location` reference, and retrieves the
Pokémon resources referenced by `pokemon_encounters`.

The extractor stores raw JSON under `data/raw/` for the next pipeline stage.
Generated JSON files are intentionally ignored by Git.

### Transform

The transform step reshapes the raw Pokémon data into a simpler processed format.
It keeps only the fields needed for the next stage.

### Validate

The validation step checks the transformed JSON for missing fields, null values,
and empty values before the data is used further.

Run validation for a specific area:

```bash
py -m pokemon_pipeline.validate canalave-city-area
```

For implementation details, see:

- [`src/pokemon_pipeline/README.md`](src/pokemon_pipeline/README.md)
- [`data/README.md`](data/README.md)
- [`tests/README.md`](tests/README.md)
- [`.github/workflows/README.md`](.github/workflows/README.md)

## Quick start

Create and activate a virtual environment, then install the project dependencies:

```bash
python -m venv .venv
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the extractor from the repository root:

```bash
python -m pokemon_pipeline canalave-city-area
```

Run the automated checks:

```bash
pytest
ruff check .
```
## Environment setup

Copy `.env.example` to `.env` before running the pipeline locally:

```
cp .env.example .env
```

No API key is required for PokéAPI, but keep `.env` out of version control (already handled by `.gitignore`).

## Branch protection

The `main` branch is protected: changes must go through a reviewed pull request with a passing CI check before merging.
