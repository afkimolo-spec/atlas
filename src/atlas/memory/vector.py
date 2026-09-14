from __future__ import annotations

import time
from typing import Any

import httpx

from atlas.config.loader import MODELS


class EmbeddingClientError(RuntimeError):
    """Base exception for embedding-client failures."""


class EmbeddingTransportError(EmbeddingClientError):
    """Network or transport failure communicating with the embedding server."""


class EmbeddingResponseError(EmbeddingClientError):
    """Embedding server returned an invalid or unusable response."""


class EmbeddingClient:
    """
    Client for the local llama.cpp embedding server.

    The remote response is treated as an untrusted boundary. HTTP 200 is
    insufficient: the JSON structure and embedding payload are validated
    before use.

    Transient transport/server failures are retried with bounded backoff.
    """

    DEFAULT_TIMEOUT = 300.0
    DEFAULT_ATTEMPTS = 3
    DEFAULT_BACKOFF = 0.5

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        attempts: int = DEFAULT_ATTEMPTS,
        backoff: float = DEFAULT_BACKOFF,
    ) -> None:
        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        if attempts <= 0:
            raise ValueError(
                "attempts must be greater than zero"
            )

        if backoff < 0:
            raise ValueError(
                "backoff cannot be negative"
            )

        self.endpoint = MODELS.embeddings.endpoint.rstrip("/")
        self.model = MODELS.embeddings.model
        self.timeout = timeout
        self.attempts = attempts
        self.backoff = backoff

        self.client = httpx.Client(
            base_url=self.endpoint,
            timeout=self.timeout,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "EmbeddingClient":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def embed(
        self,
        text: str,
    ) -> list[float]:
        if not isinstance(text, str):
            raise TypeError(
                "embedding input must be a string"
            )

        text = text.strip()

        if not text:
            raise ValueError(
                "embedding input cannot be empty"
            )

        last_error: Exception | None = None

        for attempt in range(1, self.attempts + 1):
            try:
                response = self.client.post(
                    "/embeddings",
                    json={
                        "model": self.model,
                        "input": text,
                    },
                )

                if not response.is_success:
                    body = self._response_text(response)

                    error = EmbeddingResponseError(
                        "Embedding server returned HTTP "
                        f"{response.status_code}; "
                        f"endpoint={self.endpoint!r}; "
                        f"model={self.model!r}; "
                        f"body={self._truncate(body, 4000)!r}"
                    )

                    last_error = error

                    if response.status_code in {
                        408,
                        425,
                        429,
                        500,
                        502,
                        503,
                        504,
                    } and attempt < self.attempts:
                        self._sleep(attempt)
                        continue

                    raise error

                try:
                    data: Any = response.json()
                except ValueError as exc:
                    error = EmbeddingResponseError(
                        "Embedding server returned invalid JSON; "
                        f"endpoint={self.endpoint!r}; "
                        f"model={self.model!r}; "
                        f"body={self._truncate(self._response_text(response), 4000)!r}"
                    )

                    last_error = error

                    if attempt < self.attempts:
                        self._sleep(attempt)
                        continue

                    raise error from exc

                return self._extract_embedding(
                    data,
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as exc:
                last_error = EmbeddingTransportError(
                    "Embedding request timed out; "
                    f"endpoint={self.endpoint!r}; "
                    f"model={self.model!r}; "
                    f"timeout={self.timeout}"
                )

                if attempt < self.attempts:
                    self._sleep(attempt)
                    continue

                raise last_error from exc

            except httpx.HTTPError as exc:
                last_error = EmbeddingTransportError(
                    "Embedding request failed; "
                    f"endpoint={self.endpoint!r}; "
                    f"model={self.model!r}; "
                    f"error={type(exc).__name__}: {exc}"
                )

                if attempt < self.attempts:
                    self._sleep(attempt)
                    continue

                raise last_error from exc

        raise EmbeddingClientError(
            "Embedding request exhausted all attempts."
        ) from last_error

    def dimensions(self) -> int:
        vector = self.embed("Atlas")

        if not vector:
            raise EmbeddingResponseError(
                "Embedding service returned an empty vector "
                "during dimensions()"
            )

        return len(vector)

    def _extract_embedding(
        self,
        data: Any,
        *,
        status_code: int,
    ) -> list[float]:
        if not isinstance(data, dict):
            raise EmbeddingResponseError(
                self._diagnostic(
                    "response payload is not a JSON object",
                    status_code,
                    data,
                )
            )

        api_error = data.get("error")

        if api_error is not None:
            raise EmbeddingResponseError(
                self._diagnostic(
                    f"API error: {self._compact(api_error)}",
                    status_code,
                    data,
                )
            )

        items = data.get("data")

        if not isinstance(items, list):
            raise EmbeddingResponseError(
                self._diagnostic(
                    "'data' is missing or is not a list",
                    status_code,
                    data,
                )
            )

        if not items:
            raise EmbeddingResponseError(
                self._diagnostic(
                    "'data' is empty",
                    status_code,
                    data,
                )
            )

        item = items[0]

        if not isinstance(item, dict):
            raise EmbeddingResponseError(
                self._diagnostic(
                    "first embedding item is not a JSON object",
                    status_code,
                    data,
                )
            )

        embedding = item.get("embedding")

        if not isinstance(embedding, list):
            raise EmbeddingResponseError(
                self._diagnostic(
                    "'data[0].embedding' is missing or is not a list",
                    status_code,
                    data,
                )
            )

        if not embedding:
            raise EmbeddingResponseError(
                self._diagnostic(
                    "'data[0].embedding' is empty",
                    status_code,
                    data,
                )
            )

        vector: list[float] = []

        for index, value in enumerate(embedding):
            if isinstance(value, bool):
                raise EmbeddingResponseError(
                    self._diagnostic(
                        f"embedding value {index} is boolean",
                        status_code,
                        data,
                    )
                )

            if not isinstance(value, (int, float)):
                raise EmbeddingResponseError(
                    self._diagnostic(
                        f"embedding value {index} is not numeric",
                        status_code,
                        data,
                    )
                )

            vector.append(float(value))

        return vector

    def _sleep(
        self,
        attempt: int,
    ) -> None:
        if self.backoff <= 0:
            return

        time.sleep(
            self.backoff * attempt
        )

    @staticmethod
    def _response_text(
        response: httpx.Response,
    ) -> str:
        try:
            return response.text
        except Exception:
            return "<unable to read response body>"

    @staticmethod
    def _truncate(
        value: str,
        limit: int,
    ) -> str:
        if len(value) <= limit:
            return value

        return (
            value[:limit]
            + "\n[response body truncated]"
        )

    @staticmethod
    def _compact(
        value: Any,
    ) -> str:
        text = repr(value)

        if len(text) > 2000:
            return text[:2000] + "..."

        return text

    def _diagnostic(
        self,
        reason: str,
        status_code: int,
        payload: Any,
    ) -> str:
        return (
            f"{reason}; "
            f"endpoint={self.endpoint!r}; "
            f"model={self.model!r}; "
            f"http_status={status_code}; "
            f"payload={self._compact(payload)}"
        )


if __name__ == "__main__":
    client = EmbeddingClient()

    try:
        vector = client.embed("Atlas Engineering")
        print(
            f"Embedding OK: dimensions={len(vector)}"
        )
    finally:
        client.close()
