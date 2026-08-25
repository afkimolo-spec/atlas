from __future__ import annotations

from typing import Any

import httpx


class LlamaClient:
    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout: float = 300.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model

        self.client = httpx.Client(
            base_url=self.endpoint,
            timeout=timeout,
        )

    def models(self) -> dict[str, Any]:
        response = self.client.get("/models")
        response.raise_for_status()
        return response.json()

    def chat(
        self,
        message: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:

        messages: list[dict[str, str]] = []

        if system is not None:
            messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        return data["choices"][0]["message"]["content"]

from atlas.models.router import ModelRouter


class AtlasClient:

    def __init__(self):
        router = ModelRouter()

        self.engineering = LlamaClient(
            router.engineering.endpoint,
            router.engineering.model,
        )

        self.research = LlamaClient(
            router.research.endpoint,
            router.research.model,
        )

        self.completion = LlamaClient(
            router.completion.endpoint,
            router.completion.model,
        )

    def chat(
        self,
        agent: str,
        message: str,
        **kwargs,
    ) -> str:

        clients = {
            "engineering": self.engineering,
            "research": self.research,
            "completion": self.completion,
        }

        if agent not in clients:
            raise ValueError(f"Unknown model '{agent}'")

        return clients[agent].chat(
            message,
            **kwargs,
        )
