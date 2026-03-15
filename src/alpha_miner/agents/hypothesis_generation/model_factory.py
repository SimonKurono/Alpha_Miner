"""Model selection for Feature 2 with Gemini/Claude + deterministic fallback support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

ModelMode = Literal["claude", "gemini", "deterministic"]
ModelPolicy = Literal[
    "claude_with_fallback",
    "claude_only",
    "deterministic_only",
    "gemini_with_search",
    "gemini_only",
]


@dataclass
class ModelBackend:
    mode: ModelMode
    policy: ModelPolicy
    primary_model: str
    gemini_model: str = "gemini-2.5-flash"
    enable_google_search_tool: bool = True
    warning: str | None = None

    def generate_text(self, prompt: str) -> tuple[str, dict[str, Any]]:
        if self.mode == "deterministic":
            raise RuntimeError("Deterministic backend does not provide free-form generation")
        if self.mode == "claude":
            text = _generate_with_claude(prompt=prompt, model=self.primary_model)
            return text, {
                "provider": "claude",
                "model": self.primary_model,
                "google_search_tool_enabled": False,
                "attempts": 1,
                "fallback_used": False,
            }

        text = _generate_with_gemini(
            prompt=prompt,
            model=self.gemini_model,
            enable_google_search_tool=self.enable_google_search_tool,
        )
        return text, {
            "provider": "gemini",
            "model": self.gemini_model,
            "google_search_tool_enabled": bool(self.enable_google_search_tool),
            "attempts": 1,
            "fallback_used": False,
        }


def create_model_backend(
    model_policy: ModelPolicy,
    primary_model: str,
    gemini_model: str = "gemini-2.5-flash",
    enable_google_search_tool: bool = True,
) -> ModelBackend:
    if model_policy == "deterministic_only":
        return ModelBackend(
            mode="deterministic",
            policy=model_policy,
            primary_model=primary_model,
            gemini_model=gemini_model,
            enable_google_search_tool=enable_google_search_tool,
        )

    if model_policy in {"gemini_with_search", "gemini_only"}:
        try:
            _validate_gemini_backend(gemini_model)
            return ModelBackend(
                mode="gemini",
                policy=model_policy,
                primary_model=primary_model,
                gemini_model=gemini_model,
                enable_google_search_tool=enable_google_search_tool,
            )
        except Exception as exc:  # noqa: BLE001
            if model_policy == "gemini_only":
                raise RuntimeError("Gemini backend unavailable under gemini_only policy") from exc
            return ModelBackend(
                mode="deterministic",
                policy=model_policy,
                primary_model=primary_model,
                gemini_model=gemini_model,
                enable_google_search_tool=enable_google_search_tool,
                warning=f"Gemini unavailable; deterministic fallback enabled: {exc}",
            )

    try:
        import anthropic  # noqa: F401
        from google.adk.models.anthropic_llm import Claude

        Claude(model=primary_model)
        return ModelBackend(
            mode="claude",
            policy=model_policy,
            primary_model=primary_model,
            gemini_model=gemini_model,
            enable_google_search_tool=enable_google_search_tool,
        )
    except Exception as exc:  # noqa: BLE001
        if model_policy == "claude_only":
            raise RuntimeError("Claude backend unavailable under claude_only policy") from exc
        return ModelBackend(
            mode="deterministic",
            policy=model_policy,
            primary_model=primary_model,
            gemini_model=gemini_model,
            enable_google_search_tool=enable_google_search_tool,
            warning=f"Claude unavailable; deterministic fallback enabled: {exc}",
        )


def _validate_gemini_backend(model: str) -> None:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not project or not region:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set for Gemini backend")

    from google import genai

    # Instantiation validates auth/config shape without sending model traffic.
    genai.Client(vertexai=True, project=project, location=region)
    if not model.strip():
        raise RuntimeError("Gemini model cannot be empty")


def _extract_gemini_text(response: Any) -> str:
    direct = str(getattr(response, "text", "") or "").strip()
    if direct:
        return direct

    chunks: list[str] = []
    for candidate in list(getattr(response, "candidates", []) or []):
        content = getattr(candidate, "content", None)
        for part in list(getattr(content, "parts", []) or []):
            text = str(getattr(part, "text", "") or "").strip()
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def _generate_with_gemini(prompt: str, model: str, enable_google_search_tool: bool) -> str:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_LOCATION")
    if not project or not region:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set for Gemini backend")

    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=project, location=region)
    tools = []
    if enable_google_search_tool:
        tools = [types.Tool(googleSearch=types.GoogleSearch())]

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            maxOutputTokens=800,
            temperature=0.2,
            tools=tools,
        ),
    )

    text = _extract_gemini_text(response)
    if not text:
        raise RuntimeError("Gemini returned empty content")
    return text


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

    text = "\n".join([c for c in chunks if c]).strip()
    if not text:
        raise RuntimeError("Claude returned empty content")
    return text

