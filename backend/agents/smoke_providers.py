"""Small real-network smoke check for each configured reasoning provider."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .providers import ModelRequest, provider_chain_from_env


class SmokeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    summary: str = Field(min_length=1, max_length=80)


def main() -> int:
    providers = [provider for provider in provider_chain_from_env() if provider.configured]
    if not providers:
        print(json.dumps({"ok": False, "error": "No provider credentials configured."}))
        return 1

    results: list[dict[str, object]] = []
    request = ModelRequest(
        role="provider_smoke",
        system_prompt="Return the requested structured health response. Do not add extra fields.",
        payload={"task": "Return status ok and a summary shorter than 80 characters."},
        output_type=SmokeOutput,
    )
    for provider in providers:
        try:
            output = provider.generate(request)
            results.append({
                "provider": provider.name,
                "model": provider.model,
                "ok": output.status == "ok",
            })
        except Exception as exc:  # provider boundary; message is credential-safe
            results.append({
                "provider": provider.name,
                "model": provider.model,
                "ok": False,
                "error": str(exc),
            })

    print(json.dumps(results, indent=2))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
