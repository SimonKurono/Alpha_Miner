"""Shared runtime helpers for ADK pipeline entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.adk.runners import InMemoryRunner

GENERIC_DISALLOWED_APP_NAMES = {"agents", "agent", "sequential_agent", "parallel_agent", "loop_agent"}


@dataclass
class AgentHealth:
    status: str
    expected_app_name: str
    actual_app_name: str
    failure_reason: str | None = None
    remediation: str | None = None


class AgentConnectionError(RuntimeError):
    """Raised when runner app-name wiring is invalid for production runs."""


def canonical_app_name(root_agent: Any, fallback: str) -> str:
    agent_name = str(getattr(root_agent, "name", "") or "").strip()
    if agent_name:
        return agent_name
    return fallback


def validate_agent_health(root_agent: Any, app_name: str) -> AgentHealth:
    expected = canonical_app_name(root_agent, app_name)
    if app_name != expected:
        return AgentHealth(
            status="failed",
            expected_app_name=expected,
            actual_app_name=app_name,
            failure_reason="runner app_name does not match root workflow name",
            remediation=(
                "Use runtime_utils.build_runner() and avoid overriding app_name manually. "
                f"Expected '{expected}', got '{app_name}'."
            ),
        )

    if app_name.strip().lower() in GENERIC_DISALLOWED_APP_NAMES:
        return AgentHealth(
            status="failed",
            expected_app_name=expected,
            actual_app_name=app_name,
            failure_reason="generic app_name is not allowed for Alpha Miner runs",
            remediation="Set the root workflow name (e.g., RootIngestionWorkflow) and rebuild the runner.",
        )

    return AgentHealth(
        status="ok",
        expected_app_name=expected,
        actual_app_name=app_name,
    )


def build_runner(root_agent: Any, fallback_app_name: str, strict: bool = True) -> InMemoryRunner:
    app_name = canonical_app_name(root_agent, fallback_app_name)
    health = validate_agent_health(root_agent, app_name)
    if strict and health.status != "ok":
        raise AgentConnectionError(
            f"{health.failure_reason}. expected={health.expected_app_name} actual={health.actual_app_name}. "
            f"remediation={health.remediation}"
        )
    return InMemoryRunner(agent=root_agent, app_name=app_name)

