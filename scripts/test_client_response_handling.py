from __future__ import annotations

import httpx

from atlas.core.client import (
    AtlasResponseError,
    LlamaClient,
)


class MockTransport:
    def __init__(self, payload, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            self.status_code,
            json=self.payload,
            request=request,
        )


def make_client(payload, status_code: int = 200) -> LlamaClient:
    client = LlamaClient(
        "http://test.local/v1",
        "test-model",
    )

    client.client.close()

    client.client = httpx.Client(
        transport=httpx.MockTransport(
            MockTransport(payload, status_code)
        ),
        base_url="http://test.local/v1",
    )

    return client


print("=" * 60)
print("ATLAS LLM CLIENT RESPONSE VALIDATION")
print("=" * 60)

client = make_client(
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"action":"finish","summary":"ok"}',
                }
            }
        ]
    }
)

result = client.chat("test")
assert result == '{"action":"finish","summary":"ok"}'

print("Valid response             : PASS")

client = make_client(
    {
        "choices": []
    }
)

try:
    client.chat("test")
except AtlasResponseError as exc:
    text = str(exc)

    assert "choices" in text
    assert "empty" in text

    print("Empty choices              : PASS")
else:
    raise AssertionError(
        "Empty choices were not rejected."
    )

client = make_client(
    {
        "error": {
            "message": "model unavailable",
        }
    }
)

try:
    client.chat("test")
except AtlasResponseError as exc:
    text = str(exc)

    assert "model unavailable" in text

    print("API error payload          : PASS")
else:
    raise AssertionError(
        "API error payload was not rejected."
    )

client = make_client(
    {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                }
            }
        ]
    }
)

try:
    client.chat("test")
except AtlasResponseError as exc:
    text = str(exc)

    assert "usable text content" in text

    print("Empty assistant content    : PASS")
else:
    raise AssertionError(
        "Empty assistant content was not rejected."
    )

client.close()

print("=" * 60)
print("LLM CLIENT RESPONSE VALIDATION: VERIFIED")
print("=" * 60)
