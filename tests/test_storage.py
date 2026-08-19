"""Tests for JSON persistence."""

from __future__ import annotations

import json

from pokemon_pipeline.storage import save_json


def test_save_json_creates_parent_directory(tmp_path) -> None:
    output_path = tmp_path / "data" / "raw" / "sample.json"
    payload = {"name": "pikachu", "type": "electric"}

    returned_path = save_json(payload, output_path)

    assert returned_path == output_path
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload
