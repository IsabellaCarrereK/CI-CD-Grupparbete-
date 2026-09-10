![CI](https://github.com/IsabellaCarrereK/CI-CD-Grupparbete-/actions/workflows/ci.yml/badge.svg)

🔗 [Live demo](https://isabellacarrerek.github.io/CI-CD-Grupparbete-/)

# CI/CD Pokémon Data Pipeline

Group project for the DE25 DevOps CI/CD course.

The project demonstrates a complete data pipeline together with collaborative
development, automated testing, code review, continuous integration, and
deployment with GitHub Actions.

## Project goal

The goal is to retrieve Pokémon encounter data from PokéAPI and process it
through a complete pipeline.

The final result shows:

- which Pokémon can be encountered at each location
- how many unique Pokémon each location contains
- which abilities belong to the Pokémon
- which location contains the most unique Pokémon

The aggregated result is used to generate an HTML report that is deployed to
GitHub Pages.

## Pipeline overview

```text
PokéAPI
   ↓
Extract
   ↓
Transform
   ↓
Validate
   ↓
Aggregate
   ↓
Generate HTML report
   ↓
Deploy to GitHub Pages
```

## Pipeline stages

### 1. Extract

The extraction stage retrieves raw data from PokéAPI for a selected
`location-area`.

The extraction process:

1. retrieves the selected `location-area`
2. follows the parent `location` reference
3. reads the Pokémon references from `pokemon_encounters`
4. retrieves the complete resource for every unique Pokémon
5. retrieves the ability resources referenced by the Pokémon data

The extracted data includes:

- metadata about the extraction
- location-area data
- location and region data
- Pokémon resources
- ability resources

Raw JSON files are saved under:

```text
data/raw/<location-area>.json
```

Example:

```text
data/raw/canalave-city-area.json
```

Generated raw JSON files are intentionally ignored by Git because they can be
recreated from PokéAPI and may become large.

Run extraction from the repository root:

```bash
python -m pokemon_pipeline canalave-city-area
```

A successful extraction produces output similar to:

```text
Extraction completed: 11 Pokémon retrieved.
Saved to: data/raw/canalave-city-area.json
```

### 2. Transform

The transformation stage reads the nested raw PokéAPI data and converts it into
a simpler record-based format.

Each processed Pokémon record contains:

- region
- location
- location area
- Pokémon name
- Pokémon types
- Pokémon abilities

Example:

```json
{
  "region": "sinnoh",
  "location": "canalave-city",
  "location_area": "canalave-city-area",
  "pokemon": "tentacool",
  "types": [
    "water",
    "poison"
  ],
  "abilities": [
    "clear-body",
    "liquid-ooze",
    "rain-dish"
  ]
}
```

Processed JSON files are saved under:

```text
data/processed/<location-area>.json
```

Run the transformation:

```bash
python src/pokemon_pipeline/transform.py
```

### 3. Validate

The validation stage checks the transformed records before they are used by
the aggregation stage.

The validation includes checks for:

- missing required fields
- null values
- empty values
- invalid data types
- duplicate Pokémon
- empty or duplicate types
- empty or duplicate abilities

Run validation for a specific location area:

```bash
python -m pokemon_pipeline.validate canalave-city-area
```

A successful validation produces output similar to:

```text
Validation passed: data/processed/canalave-city-area.json
```

### 4. Aggregate

The aggregation stage loads the processed JSON files and groups the data by
location.

It calculates:

- unique Pokémon per location
- number of unique Pokémon
- unique abilities per location
- number of unique abilities
- abilities associated with each Pokémon

Duplicate Pokémon and ability names are removed during aggregation.

The locations are sorted by Pokémon count, so the location with the most unique
Pokémon appears first.

The aggregated result is saved under:

```text
data/aggregated/location_summary.json
```

Run aggregation:

```bash
python -m pokemon_pipeline.aggregate
```

Example output:

```json
{
  "region": "sinnoh",
  "location": "canalave-city",
  "location_areas": [
    "canalave-city-area"
  ],
  "pokemon_count": 11,
  "pokemons": [
    "finneon",
    "gyarados",
    "magikarp"
  ],
  "ability_count": 8,
  "abilities": [
    "intimidate",
    "moxie",
    "swift-swim"
  ],
  "pokemon_abilities": {
    "gyarados": [
      "intimidate",
      "moxie"
    ],
    "magikarp": [
      "swift-swim"
    ]
  }
}
```

### 5. Generate report

The report generator reads the aggregated JSON data and creates an HTML report.

The report presents:

- total number of processed locations
- Pokémon count for each location
- Pokémon names
- Pokémon sprite images when available

The generated report is saved as:

```text
site/index.html
```

Run the report generator:

```bash
python scripts/generate_report.py
```

### 6. Deploy

The HTML report is deployed to GitHub Pages through GitHub Actions.

The deployment workflow runs only after the CI workflow has completed
successfully on `main`. This creates a deployment gate: code must pass the
required quality checks before a new version of the report can be published.

Live report:

[Open the deployed Pokémon report](https://isabellacarrerek.github.io/CI-CD-Grupparbete-/)

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/IsabellaCarrereK/CI-CD-Grupparbete-.git
cd CI-CD-Grupparbete-
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows Git Bash:

```bash
source .venv/Scripts/activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install the project and development dependencies

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Configure the local environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

PokéAPI does not require an API key. The `.env` file is excluded from version
control through `.gitignore`.

### 5. Run the pipeline locally

Run extraction:

```bash
python -m pokemon_pipeline canalave-city-area
```

Run transformation:

```bash
python src/pokemon_pipeline/transform.py
```

Run validation:

```bash
python -m pokemon_pipeline.validate canalave-city-area
```

Run aggregation:

```bash
python -m pokemon_pipeline.aggregate
```

Generate the HTML report:

```bash
python scripts/generate_report.py
```

Open the generated file in a browser:

```text
site/index.html
```

## Automated checks

Run all automated tests:

```bash
pytest
```

Run code-quality checks with Ruff:

```bash
ruff check .
```

Both commands should pass before creating or updating a pull request.

## Continuous integration

The CI workflow runs automatically for pushes and pull requests targeting
`main`.

The workflow:

1. checks out the repository
2. sets up Python
3. installs the project and development dependencies
4. runs Ruff
5. runs pytest

A failing lint check or test prevents the pull request from being merged into
the protected `main` branch.

## Continuous deployment

After CI succeeds on `main`, the deployment workflow:

1. checks out the tested commit
2. installs the project
3. runs the data pipeline
4. generates the HTML report
5. uploads the generated site as an artifact
6. deploys the artifact to GitHub Pages

This ensures that deployment is connected to the automated quality checks.

## Collaboration workflow

The project is developed collaboratively with feature branches and reviewed
pull requests.

The standard workflow is:

```text
Create a feature branch
        ↓
Implement the change
        ↓
Run Ruff and pytest locally
        ↓
Commit and push
        IRequest
Create a pull request
        ↓
GitHub Actions runs CI
        ↓
Another team member reviews the code
        ↓
Approve and merge into main
        ↓
Deploy after successful CI
```

Example branch names:

```text
feature/pokeapi-extraction
feature/transform-data
feature/validate-transformed-data
feature/aggregate-data
feature/aggregate-abilities
feature/generate-report
feature/deploy-pages
```

## Branch protection

The `main` branch is protected.

Changes must:

- be submitted through a pull request
- receive at least one approving review
- pass the required CI checks

This reduces the risk of unreviewed or failing code being added to `main`.

## Project structure

```text
.github/workflows/       GitHub Actions workflows
data/raw/                Raw data retrieved from PokéAPI
data/processed/          Transformed and validated Pokémon records
data/aggregated/         Aggregated location summaries
scripts/                 HTML report generation
site/                    Generated website
src/pokemon_pipeline/    Pipeline source code
tests/                   Automated tests
.env.example             Example local configuration
.gitignore               Files excluded from version control
pyproject.toml           Project configuration and dependencies
README.md                Project overview and instructions
```

## Generated data

Generated JSON files are not committed to the repository because they:

- can be recreated by running the pipeline
- may change when PokéAPI data changes
- may become large
- are output data rather than source code

The `.gitkeep` files allow Git to retain otherwise empty data directories.

## API dependency

The deployment pipeline retrieves fresh data from PokéAPI. This keeps the
published report up to date, but it also creates an external dependency.

If PokéAPI is temporarily unavailable, the extraction stage and deployment may
fail.

Possible future improvements include:

- retrying temporary HTTP failures
- using exponential backoff
- caching previously retrieved data
- using the most recent successful dataset as a fallback
- separating data refresh from website deployment

## Future improvements

Potential improvements include:

- support for multiple location areas in one command
- additional end-to-end integration tests
- HTTP retry and resilience
- cached fallback data when PokéAPI is unavailable
- more detailed ability information in the report
- improved logging and error messages

## Additional documentation

For more detailed implementation information, see:

- [`src/pokemon_pipeline/README.md`](src/pokemon_pipeline/README.md)
- [`data/README.md`](data/README.md)
- [`tests/README.md`](tests/README.md)
- [`.github/workflows/README.md`](.github/workflows/README.md)