from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from atlas.models.router import ModelRouter


class AtlasClientError(RuntimeError):
    """
    Base exception for Atlas LLM client failures.
    """


class AtlasTransportError(AtlasClientError):
    """
    Network, timeout, or transport-level failure.
    """


class AtlasHTTPError(AtlasClientError):
    """
    HTTP/API failure returned by an LLM endpoint.
    """


class AtlasResponseError(AtlasClientError):
    """
    Successful HTTP response with an invalid/unusable API payload.
    """


@dataclass(frozen=True, slots=True)
class LLMResponseDiagnostics:
    """
    Diagnostic information retained for invalid model responses.
    """

    agent: str
    endpoint: str
    model: str
    http_status: int
    payload: Any


class LlamaClient:
    """
    OpenAI-compatible Atlas LLM client.

    The client treats the remote model endpoint as an untrusted boundary:
    HTTP success does not imply a valid chat-completion payload.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        timeout: float = 300.0,
    ) -> None:
        endpoint = endpoint.strip().rstrip("/")

        if not endpoint:
            raise ValueError("endpoint cannot be empty")

        if not model.strip():
            raise ValueError("model cannot be empty")

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

        self.client = httpx.Client(
            base_url=self.endpoint,
            timeout=self.timeout,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "LlamaClient":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def models(self) -> dict[str, Any]:
        try:
            response = self.client.get("/models")
        except httpx.HTTPError as exc:
            raise AtlasTransportError(
                f"LLM models request failed: "
                f"endpoint={self.endpoint!r} "
                f"error={type(exc).__name__}: {exc}"
            ) from exc

        if not response.is_success:
            body = self._safe_response_text(response)

            raise AtlasHTTPError(
                f"LLM models request returned HTTP "
                f"{response.status_code}: "
                f"endpoint={self.endpoint!r} "
                f"body={self._truncate(body, 4000)!r}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AtlasResponseError(
                f"LLM models endpoint returned non-JSON data: "
                f"endpoint={self.endpoint!r}"
            ) from exc

        if not isinstance(payload, dict):
            raise AtlasResponseError(
                f"LLM models endpoint returned invalid payload type: "
                f"{type(payload).__name__}"
            )

        return payload

    def chat(
        self,
        message: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message cannot be empty")

        if system is not None and not isinstance(system, str):
            raise TypeError("system must be a string or None")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")

        if temperature < 0:
            raise ValueError("temperature cannot be negative")

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

        request_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self.client.post(
                "/chat/completions",
                json=request_payload,
            )
        except httpx.TimeoutException as exc:
            raise AtlasTransportError(
                f"LLM request timed out: "
                f"endpoint={self.endpoint!r} "
                f"model={self.model!r} "
                f"timeout={self.timeout}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AtlasTransportError(
                f"LLM request failed: "
                f"endpoint={self.endpoint!r} "
                f"model={self.model!r} "
                f"error={type(exc).__name__}: {exc}"
            ) from exc

        if not response.is_success:
            body = self._safe_response_text(response)

            raise AtlasHTTPError(
                f"LLM request returned HTTP "
                f"{response.status_code}: "
                f"endpoint={self.endpoint!r} "
                f"model={self.model!r} "
                f"body={self._truncate(body, 4000)!r}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            body = self._safe_response_text(response)

            raise AtlasResponseError(
                f"LLM endpoint returned invalid JSON: "
                f"endpoint={self.endpoint!r} "
                f"model={self.model!r} "
                f"body={self._truncate(body, 4000)!r}"
            ) from exc

        return self._extract_content(
            data,
            http_status=response.status_code,
        )

    def _extract_content(
        self,
        data: Any,
        *,
        http_status: int,
    ) -> str:
        diagnostics = LLMResponseDiagnostics(
            agent="unknown",
            endpoint=self.endpoint,
            model=self.model,
            http_status=http_status,
            payload=data,
        )

        if not isinstance(data, dict):
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    "response payload is not a JSON object",
                )
            )

        api_error = data.get("error")

        if api_error is not None:
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    f"API payload contains error={self._compact(api_error)}",
                )
            )

        choices = data.get("choices")

        if not isinstance(choices, list):
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    "'choices' is missing or is not a list",
                )
            )

        if not choices:
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    "'choices' is empty",
                )
            )

        choice = choices[0]

        if not isinstance(choice, dict):
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    "first choice is not a JSON object",
                )
            )

        message = choice.get("message")

        if not isinstance(message, dict):
            raise AtlasResponseError(
                self._diagnostic_message(
                    diagnostics,
                    "'choices[0].message' is missing or invalid",
                )
            )

        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content

        if isinstance(content, list):
            text_parts: list[str] = []

            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                    continue

                if not isinstance(item, dict):
                    continue

                text = item.get("text")

                if isinstance(text, str):
                    text_parts.append(text)

            combined = "".join(text_parts).strip()

            if combined:
                return combined

        raise AtlasResponseError(
            self._diagnostic_message(
                diagnostics,
                "assistant message contains no usable text content",
            )
        )

    @staticmethod
    def _safe_response_text(
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

    @classmethod
    def _diagnostic_message(
        cls,
        diagnostics: LLMResponseDiagnostics,
        reason: str,
    ) -> str:
        return (
            "Invalid LLM response: "
            f"{reason}; "
            f"endpoint={diagnostics.endpoint!r}; "
            f"model={diagnostics.model!r}; "
            f"http_status={diagnostics.http_status}; "
            f"payload={cls._compact(diagnostics.payload)}"
        )


class AtlasClient:
    """
    Atlas model-routing facade.
    """

    def __init__(
        self,
        router: ModelRouter | None = None,
    ) -> None:
        self.router = router or ModelRouter()

        self.engineering = LlamaClient(
            self.router.engineering.endpoint,
            self.router.engineering.model,
        )

        self.research = LlamaClient(
            self.router.research.endpoint,
            self.router.research.model,
        )

        self.completion = LlamaClient(
            self.router.completion.endpoint,
            self.router.completion.model,
        )

    def close(self) -> None:
        self.engineering.close()
        self.research.close()
        self.completion.close()

    def __enter__(self) -> "AtlasClient":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def chat(
        self,
        agent: str,
        message: str,
        **kwargs: Any,
    ) -> str:
        clients = {
            "engineering": self.engineering,
            "research": self.research,
            "completion": self.completion,
        }

        if agent not in clients:
            raise ValueError(
                f"Unknown model '{agent}'. "
                f"Available models: {', '.join(sorted(clients))}"
            )

        return clients[agent].chat(
            message,
            **kwargs,
        )
