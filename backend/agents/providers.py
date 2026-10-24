"""Provider-neutral, validated LLM access with run-level failover support."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Mapping, Protocol, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


OutputT = TypeVar("OutputT", bound=BaseModel)


class ProviderUnavailable(RuntimeError):
    """The configured provider cannot serve this run."""


class InvalidModelOutput(RuntimeError):
    """The model failed its typed contract after one repair attempt."""


@dataclass(frozen=True)
class ModelRequest(Generic[OutputT]):
    role: str
    system_prompt: str
    payload: Mapping[str, Any]
    output_type: type[OutputT]


class LLMProvider(Protocol):
    name: str
    model: str

    @property
    def configured(self) -> bool: ...

    def generate(self, request: ModelRequest[OutputT]) -> OutputT: ...


def _closed_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Adapt Pydantic JSON schema to constrained-decoding requirements."""
    schema = model.model_json_schema()

    def close(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(schema)
    return schema


class ValidatedProvider(ABC):
    """Validate every response, retrying malformed model output exactly once."""

    name: str
    model: str

    @property
    @abstractmethod
    def configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _complete(self, request: ModelRequest[OutputT], *, repair: str | None) -> Any:
        raise NotImplementedError

    def generate(self, request: ModelRequest[OutputT]) -> OutputT:
        if not self.configured:
            raise ProviderUnavailable(f"{self.name} is not configured")
        repair: str | None = None
        last_error = "unknown validation error"
        for attempt in range(2):
            raw = self._complete(request, repair=repair)
            try:
                if isinstance(raw, str):
                    return request.output_type.model_validate_json(raw)
                return request.output_type.model_validate(raw)
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                if attempt == 0:
                    repair = (
                        "Your previous response did not satisfy the required JSON schema. "
                        f"Return only corrected JSON. Validation error: {last_error[:1200]}"
                    )
        raise InvalidModelOutput(
            f"{self.name}/{self.model} returned invalid {request.output_type.__name__} twice: "
            f"{last_error[:500]}"
        )


class JsonHttpProvider(ValidatedProvider):
    """Shared JSON-over-HTTP behavior without adding provider SDK dependencies."""

    def __init__(self, *, name: str, model: str, api_key: str | None, url: str, timeout: float = 30.0) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self._url = url
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @abstractmethod
    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _body(self, request: ModelRequest[OutputT], repair: str | None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _extract(self, response: dict[str, Any]) -> Any:
        raise NotImplementedError

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self._url, data=encoded, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("retry-after")
            delay = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else 0.0
            if exc.code == 429 and 0 < delay <= 2:
                time.sleep(delay)
                try:
                    with urllib.request.urlopen(request, timeout=self._timeout) as response:
                        return json.loads(response.read().decode("utf-8"))
                except Exception as retry_exc:  # network boundary
                    raise ProviderUnavailable(f"{self.name} remained rate limited") from retry_exc
            detail = self._safe_http_error_detail(exc)
            suffix = f": {detail}" if detail else ""
            raise ProviderUnavailable(f"{self.name} HTTP {exc.code}{suffix}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"{self.name} request failed") from exc

    @staticmethod
    def _safe_http_error_detail(exc: urllib.error.HTTPError) -> str:
        """Return a short provider message without echoing request credentials."""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            return ""
        error = payload.get("error", payload) if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            detail = error.get("message") or error.get("status") or error.get("code")
        else:
            detail = error
        if not isinstance(detail, (str, int, float)):
            return ""
        text = " ".join(str(detail).split())
        return text[:300]

    def _complete(self, request: ModelRequest[OutputT], *, repair: str | None) -> Any:
        return self._extract(self._post(self._body(request, repair)))


class OpenAICompatibleProvider(JsonHttpProvider):
    """Groq and OpenRouter adapter using strict JSON-schema responses."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None,
        url: str,
        strict: bool,
        extra_headers: Mapping[str, str] | None = None,
        require_parameters: bool = False,
    ) -> None:
        super().__init__(name=name, model=model, api_key=api_key, url=url)
        self._strict = strict
        self._extra_headers = dict(extra_headers or {})
        self._require_parameters = require_parameters

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RecallScope/1.0",
            **self._extra_headers,
        }

    def _body(self, request: ModelRequest[OutputT], repair: str | None) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": json.dumps(request.payload, sort_keys=True)},
        ]
        if repair:
            messages.append({"role": "user", "content": repair})
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.output_type.__name__.lower(),
                    "strict": self._strict,
                    "schema": _closed_schema(request.output_type),
                },
            },
        }
        if self._require_parameters:
            body["provider"] = {"require_parameters": True}
        return body

    def _extract(self, response: dict[str, Any]) -> Any:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailable(f"{self.name} returned an unexpected response") from exc


class GeminiProvider(JsonHttpProvider):
    def __init__(self, *, model: str, api_key: str | None) -> None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        super().__init__(name="gemini", model=model, api_key=api_key, url=url)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "User-Agent": "RecallScope/1.0",
            "x-goog-api-key": self._api_key or "",
        }

    def _body(self, request: ModelRequest[OutputT], repair: str | None) -> dict[str, Any]:
        content = json.dumps(request.payload, sort_keys=True)
        if repair:
            content = f"{content}\n\n{repair}"
        return {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": request.output_type.model_json_schema(),
            },
        }

    def _extract(self, response: dict[str, Any]) -> Any:
        try:
            return response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailable("gemini returned an unexpected response") from exc


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    model: str
    error: str


def provider_chain_from_env(environ: Mapping[str, str] | None = None) -> list[LLMProvider]:
    """Build the approved priority order. The mock is appended by the workflow."""
    if environ is None:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
        env: Mapping[str, str] = os.environ
    else:
        env = environ
    generic_key = env.get("LLM_API_KEY")
    forced = env.get("LLM_PROVIDER", "").lower()

    groq = OpenAICompatibleProvider(
        name="groq",
        model=env.get("GROQ_MODEL", env.get("LLM_MODEL") if forced == "groq" else None) or "openai/gpt-oss-120b",
        api_key=env.get("GROQ_API_KEY") or (generic_key if forced == "groq" else None),
        url="https://api.groq.com/openai/v1/chat/completions",
        strict=True,
    )
    gemini = GeminiProvider(
        model=env.get("GEMINI_MODEL", env.get("LLM_MODEL") if forced == "gemini" else None) or "gemini-3.8-flash",
        api_key=env.get("GEMINI_API_KEY") or (generic_key if forced == "gemini" else None),
    )
    openrouter = OpenAICompatibleProvider(
        name="openrouter",
        model=env.get("OPENROUTER_MODEL", env.get("LLM_MODEL") if forced == "openrouter" else None)
        or "xingchen-agi/xing4.0-29b-a4b:free",
        api_key=env.get("OPENROUTER_API_KEY") or (generic_key if forced == "openrouter" else None),
        url="https://openrouter.ai/api/v1/chat/completions",
        strict=False,
        extra_headers={
            "HTTP-Referer": env.get("OPENROUTER_SITE_URL", "http://localhost:5173"),
            "X-Title": env.get("OPENROUTER_APP_NAME", "RecallScope"),
        },
        require_parameters=True,
    )
    providers: dict[str, LLMProvider] = {"groq": groq, "gemini": gemini, "openrouter": openrouter}
    if forced and forced != "mock":
        selected = providers.get(forced)
        if selected is None:
            raise ValueError(f"Unsupported LLM_PROVIDER: {forced}")
        return [selected, *(provider for name, provider in providers.items() if name != forced)]
    return [] if forced == "mock" else [groq, gemini, openrouter]
