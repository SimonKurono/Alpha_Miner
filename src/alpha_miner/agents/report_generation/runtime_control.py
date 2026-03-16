"""Runtime budget helpers for Feature 5."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.schemas import ErrorEvent, RunMeta


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_run_meta(ctx: InvocationContext) -> RunMeta:
    return RunMeta.model_validate(ctx.session.state.get("run.meta", {}))


def get_runtime_deadline(run_meta: RunMeta) -> datetime:
    return run_meta.started_at + timedelta(seconds=run_meta.runtime_budget_sec)


def is_runtime_exceeded(run_meta: RunMeta) -> bool:
    return _utc_now() >= get_runtime_deadline(run_meta)


def append_budget_exceeded_error(errors: list[dict], *, source: str, message: str) -> list[dict]:
    for err in errors:
        if err.get("source") == source and err.get("error_type") == "budget_exceeded":
            return errors
    errors.append(
        ErrorEvent(
            source=source,
            error_type="budget_exceeded",
            message=message,
            is_fatal=True,
        ).model_dump(mode="json")
    )
    return errors
