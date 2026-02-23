"""Runtime budget helpers for Feature 1 ingestion agents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.schemas import ErrorEvent, RunMeta


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_run_meta(ctx: InvocationContext) -> RunMeta:
    return RunMeta.model_validate(ctx.session.state.get("run.meta", {}))


def get_runtime_deadline(run_meta: RunMeta) -> datetime:
    return run_meta.started_at + timedelta(seconds=run_meta.runtime_budget_sec)


def get_runtime_remaining_sec(run_meta: RunMeta) -> float:
    return (get_runtime_deadline(run_meta) - _utc_now()).total_seconds()


def is_runtime_exceeded(run_meta: RunMeta) -> bool:
    return get_runtime_remaining_sec(run_meta) <= 0


def append_budget_exceeded_error(
    errors: list[dict],
    *,
    source: str,
    message: str,
    retry_count: int = 0,
) -> list[dict]:
    """Append one budget error unless the same source+type already exists."""

    for err in errors:
        if err.get("source") == source and err.get("error_type") == "budget_exceeded":
            return errors

    errors.append(
        ErrorEvent(
            source=source,
            error_type="budget_exceeded",
            message=message,
            retry_count=retry_count,
            is_fatal=True,
        ).model_dump(mode="json")
    )
    return errors
