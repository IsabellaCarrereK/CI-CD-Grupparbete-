# Tests

This folder contains unit tests for the extraction project.

The important design choice is that the tests **do not call the live PokéAPI**. They use small fake clients and responses instead.

This gives the CI pipeline several benefits:

- tests run quickly
- tests are repeatable
- a PokéAPI outage cannot randomly fail a pull request
- tests verify our code rather than the availability of an external service

## Test files

### `test_api.py`

Checks the HTTP client behavior:

- valid JSON objects are returned
- HTTP failures become `PokeAPIError`
- unexpected non-object JSON is rejected

### `test_extract.py`

Checks extraction orchestration:

- the parent location is retrieved
- Pokémon resources are retrieved
- duplicate Pokémon references are fetched only once
- metadata is added correctly

### `test_storage.py`

Checks JSON persistence:

- missing parent directories are created
- the saved JSON can be read back correctly

## Run

From the repository root:

```bash
pytest
```
