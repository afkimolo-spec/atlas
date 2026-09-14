from __future__ import annotations

import httpx

from atlas.memory.vector import (
    EmbeddingClient,
    EmbeddingResponseError,
)


class MockTransport:
    def __init__(
        self,
        payload,
        status_code: int = 200,
    ):
        self.payload = payload
        self.status_code = status_code

    def __call__(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            self.status_code,
            json=self.payload,
            request=request,
        )


def make_client(
    payload,
    status_code: int = 200,
) -> EmbeddingClient:
    client = EmbeddingClient(
        attempts=1,
    )

    client.client.close()

    client.client = httpx.Client(
        transport=httpx.MockTransport(
            MockTransport(
                payload,
                status_code,
            )
        ),
        base_url=client.endpoint,
    )

    return client


print("=" * 60)
print("ATLAS EMBEDDING CLIENT RESPONSE VALIDATION")
print("=" * 60)

client = make_client(
    {
        "data": [
            {
                "embedding": [0.1, 0.2, 0.3],
            }
        ]
    }
)

assert client.embed("Atlas") == [0.1, 0.2, 0.3]
print("Valid embedding            : PASS")
client.close()

client = make_client(
    {
        "data": []
    }
)

try:
    client.embed("Atlas")
except EmbeddingResponseError as exc:
    assert "'data' is empty" in str(exc)
    print("Empty data                 : PASS")
else:
    raise AssertionError(
        "Empty embedding data was accepted."
    )

client.close()

client = make_client(
    {
        "error": {
            "message": "embedding failure",
        }
    }
)

try:
    client.embed("Atlas")
except EmbeddingResponseError as exc:
    assert "embedding failure" in str(exc)
    print("API error payload          : PASS")
else:
    raise AssertionError(
        "Embedding API error was accepted."
    )

client.close()

print("=" * 60)
print("EMBEDDING CLIENT RESPONSE VALIDATION: VERIFIED")
print("=" * 60)
