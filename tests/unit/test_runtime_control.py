from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alpha_miner.agents.data_ingestion.runtime_control import (
    append_budget_exceeded_error,
    get_runtime_remaining_sec,
    is_runtime_exceeded,
)
from alpha_miner.agents.data_ingestion.schemas import RunMeta


def test_runtime_remaining_and_exceeded_flags():
    now = datetime.now(timezone.utc)
    run_meta = RunMeta(
        run_id="r1",
        status="running",
        started_at=now - timedelta(seconds=10),
        runtime_budget_sec=30,
    )
    assert get_runtime_remaining_sec(run_meta) > 0
    assert is_runtime_exceeded(run_meta) is False

    expired = RunMeta(
        run_id="r2",
        status="running",
        started_at=now - timedelta(seconds=100),
        runtime_budget_sec=30,
    )
    assert is_runtime_exceeded(expired) is True


def test_append_budget_exceeded_error_dedupes_by_source():
    errors: list[dict] = []
    errors = append_budget_exceeded_error(errors, source="gdelt", message="budget exceeded")
    errors = append_budget_exceeded_error(errors, source="gdelt", message="budget exceeded again")
    assert len(errors) == 1
    assert errors[0]["error_type"] == "budget_exceeded"
