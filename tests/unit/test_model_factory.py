from __future__ import annotations

import builtins

import pytest

from alpha_miner.agents.hypothesis_generation import model_factory
from alpha_miner.agents.hypothesis_generation.model_factory import create_model_backend


def test_model_factory_deterministic_only():
    backend = create_model_backend(
        "deterministic_only",
        "claude-3-5-sonnet-v2@20241022",
        gemini_model="gemini-2.5-flash",
        enable_google_search_tool=True,
    )
    assert backend.mode == "deterministic"
    assert backend.warning is None


def test_model_factory_gemini_with_search_uses_gemini(monkeypatch):
    monkeypatch.setattr(model_factory, "_validate_gemini_backend", lambda _model: None)
    backend = create_model_backend(
        "gemini_with_search",
        "claude-3-5-sonnet-v2@20241022",
        gemini_model="gemini-2.5-flash",
        enable_google_search_tool=True,
    )
    assert backend.mode == "gemini"
    assert backend.enable_google_search_tool is True


def test_model_factory_fallback_when_gemini_unavailable(monkeypatch):
    def fail(_model):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr(model_factory, "_validate_gemini_backend", fail)
    backend = create_model_backend(
        "gemini_with_search",
        "claude-3-5-sonnet-v2@20241022",
        gemini_model="gemini-2.5-flash",
        enable_google_search_tool=True,
    )
    assert backend.mode == "deterministic"
    assert backend.warning is not None


def test_model_factory_gemini_only_raises_when_gemini_unavailable(monkeypatch):
    def fail(_model):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr(model_factory, "_validate_gemini_backend", fail)
    with pytest.raises(RuntimeError):
        create_model_backend(
            "gemini_only",
            "claude-3-5-sonnet-v2@20241022",
            gemini_model="gemini-2.5-flash",
            enable_google_search_tool=True,
        )


def test_model_factory_claude_only_raises_when_anthropic_missing(monkeypatch):
    original_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ModuleNotFoundError("No module named anthropic")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(RuntimeError):
        create_model_backend(
            "claude_only",
            "claude-3-5-sonnet-v2@20241022",
            gemini_model="gemini-2.5-flash",
            enable_google_search_tool=True,
        )

