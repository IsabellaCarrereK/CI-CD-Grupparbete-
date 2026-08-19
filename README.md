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
