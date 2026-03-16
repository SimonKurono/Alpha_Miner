from __future__ import annotations

import builtins

import pytest

from alpha_miner.agents.hypothesis_generation.model_factory import create_model_backend


def test_model_factory_deterministic_only():
    backend = create_model_backend("deterministic_only", "claude-3-5-sonnet-v2@20241022")
    assert backend.mode == "deterministic"
    assert backend.warning is None


def test_model_factory_fallback_when_anthropic_missing(monkeypatch):
    original_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ModuleNotFoundError("No module named anthropic")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)

    backend = create_model_backend("claude_with_fallback", "claude-3-5-sonnet-v2@20241022")
    assert backend.mode == "deterministic"
    assert backend.warning is not None


def test_model_factory_claude_only_raises_when_anthropic_missing(monkeypatch):
    original_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ModuleNotFoundError("No module named anthropic")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)

    with pytest.raises(RuntimeError):
        create_model_backend("claude_only", "claude-3-5-sonnet-v2@20241022")
