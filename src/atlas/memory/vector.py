from __future__ import annotations

from typing import Any

import httpx

from atlas.config.loader import MODELS


class EmbeddingClient:
    """
    Client for the local llama.cpp embedding server.
    """

    def __init__(self) -> None:
        self.endpoint = MODELS.embeddings.endpoint.rstrip("/")
        self.model = MODELS.embeddings.model

        self.client = httpx.Client(
            base_url=self.endpoint,
            timeout=300.0,
        )

    def embed(
        self,
        text: str,
    ) -> list[float]:

        response = self.client.post(
            "/embeddings",
            json={
                "model": self.model,
                "input": text,
            },
        )

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        return data["data"][0]["embedding"]

    def dimensions(
        self,
    ) -> int:

        vector = self.embed("Atlas")

        return len(vector)
