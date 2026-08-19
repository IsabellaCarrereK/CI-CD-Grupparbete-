"""HTTP client for the PokéAPI extraction stage."""

from __future__ import annotations

from typing import Any

import requests

DEFAULT_BASE_URL = "https://pokeapi.co/api/v2"
DEFAULT_TIMEOUT_SECONDS = 15.0


class PokeAPIError(RuntimeError):
    """Raised when PokéAPI data cannot be retrieved or decoded."""


class PokeAPIClient:
    """Small PokéAPI client responsible only for HTTP communication."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._owns_session = session is None

        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "DE25-CICD-PokeAPI-Extractor/1.0",
            }
        )

    def close(self) -> None:
        """Close the internally created HTTP session."""
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> PokeAPIClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_location_area(self, area_name: str) -> dict[str, Any]:
        """Return one location-area resource by name."""
        return self.get_json(f"{self.base_url}/location-area/{area_name}/")

    def get_json(self, url: str) -> dict[str, Any]:
        """Retrieve and decode one JSON object from PokéAPI."""
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise PokeAPIError(f"Request failed for {url}") from exc
        except ValueError as exc:
            raise PokeAPIError(f"Invalid JSON returned by {url}") from exc

        if not isinstance(payload, dict):
            raise PokeAPIError(f"Expected a JSON object from {url}")

        return payload
