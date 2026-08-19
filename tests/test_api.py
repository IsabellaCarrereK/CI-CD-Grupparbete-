"""Tests for the PokéAPI HTTP client."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from pokemon_pipeline.api import PokeAPIClient, PokeAPIError


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, float]] = []

    def get(self, url: str, *, timeout: float) -> FakeResponse:
        self.calls.append((url, timeout))
        return self.response

    def close(self) -> None:
        pass


def test_get_json_returns_object() -> None:
    session = FakeSession(FakeResponse({"name": "pikachu"}))
    client = PokeAPIClient(session=session)  # type: ignore[arg-type]

    result = client.get_json("https://example.test/pokemon/25/")

    assert result == {"name": "pikachu"}
    assert session.calls == [("https://example.test/pokemon/25/", 15.0)]


def test_get_json_wraps_request_errors() -> None:
    response = FakeResponse(error=requests.HTTPError("404"))
    session = FakeSession(response)
    client = PokeAPIClient(session=session)  # type: ignore[arg-type]

    with pytest.raises(PokeAPIError, match="Request failed"):
        client.get_json("https://example.test/missing/")


def test_get_json_rejects_non_object_payload() -> None:
    session = FakeSession(FakeResponse(["not", "an", "object"]))
    client = PokeAPIClient(session=session)  # type: ignore[arg-type]

    with pytest.raises(PokeAPIError, match="Expected a JSON object"):
        client.get_json("https://example.test/list/")
