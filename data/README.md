# Data Directory

This folder is the handoff point between the **Extract** stage and the next pipeline stage.

## `raw/`

The extractor writes PokéAPI snapshots here by default:

```text
data/raw/<location-area>.json
```

Example:

```text
data/raw/canalave-city-area.json
```

Generated `.json` files in `data/raw/` are ignored by Git because they are reproducible output and may become large or change frequently.

`.gitkeep` exists only so Git retains the otherwise empty `raw/` folder.

The transform-stage team member can read these files without changing the extractor itself.
