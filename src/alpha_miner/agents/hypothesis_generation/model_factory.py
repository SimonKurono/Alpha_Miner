"""Model selection for Feature 2 with Claude + deterministic fallback support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class ModelBackend:
    mode: Literal["claude", "deterministic"]
    policy: Literal["claude_with_fallback", "claude_only", "deterministic_only"]
    primary_model: str
    warning: str | None = None

    def generate_text(self, prompt: str) -> str:
        if self.mode == "deterministic":
            raise RuntimeError("Deterministic backend does not provide free-form generation")
        return _generate_with_claude(prompt=prompt, model=self.primary_model)


def create_model_backend(
    model_policy: Literal["claude_with_fallback", "claude_only", "deterministic_only"],
    primary_model: str,
) -> ModelBackend:
    if model_policy == "deterministic_only":
        return ModelBackend(mode="deterministic", policy=model_policy, primary_model=primary_model)

    try:
        import anthropic  # noqa: F401
        from google.adk.models.anthropic_llm import Claude

        Claude(model=primary_model)
        return ModelBackend(mode="claude", policy=model_policy, primary_model=primary_model)
    except Exception as exc:  # noqa: BLE001
        if model_policy == "claude_only":
            raise RuntimeError(
                "Claude backend unavailable under claude_only policy"
            ) from exc

        return ModelBackend(
            mode="deterministic",
            policy=model_policy,
            primary_model=primary_model,
            warning=f"Claude unavailable; deterministic fallback enabled: {exc}",
        )


def _generate_with_claude(prompt: str, model: str) -> str:
    try:
        from anthropic import AnthropicVertex
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("anthropic package is required for Claude backend") from exc

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not project or not region:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set for Claude backend")

    client = AnthropicVertex(project_id=project, region=region)
    message = client.messages.create(
        model=model,
        max_tokens=800,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    )

    chunks: list[str] = []
    for block in getattr(message, "content", []):
        if getattr(block, "type", None) == "text":
            chunks.append(str(getattr(block, "text", "")).strip())

    text = "\n".join([c for c in chunks if c])
    if not text:
        raise RuntimeError("Claude returned empty content")

    return text
