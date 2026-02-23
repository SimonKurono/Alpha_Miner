"""DSL parsing + allowed-operations validation for factor candidates."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.schemas import FactorCandidate
from alpha_miner.tools.factors.interfaces import parse_factor_expression, validate_factor_ast


class DslValidationAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="DslValidationAgent skipped due to run stop flag")
            return

        candidates = [FactorCandidate.model_validate(row) for row in ctx.session.state.get("factors.candidates", [])]

        validated: list[dict] = []
        rejected: list[dict] = []
        validation_rows: list[dict] = []

        for candidate in candidates:
            try:
                ast = parse_factor_expression(candidate.expression)
                report = validate_factor_ast(ast)
                if not report.passed:
                    candidate.passed_constraints = False
                    candidate.reject_reasons.extend(report.errors)
                    rejected.append(candidate.model_dump(mode="json"))
                    validation_rows.append(
                        {
                            "factor_id": candidate.factor_id,
                            "expression": candidate.expression,
                            "passed": False,
                            "errors": report.errors,
                            "stage": "dsl_validation",
                        }
                    )
                    continue

                validated.append(candidate.model_dump(mode="json"))
                validation_rows.append(
                    {
                        "factor_id": candidate.factor_id,
                        "expression": candidate.expression,
                        "passed": True,
                        "errors": [],
                        "stage": "dsl_validation",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                candidate.passed_constraints = False
                candidate.reject_reasons.append(f"parse_error: {exc}")
                rejected.append(candidate.model_dump(mode="json"))
                validation_rows.append(
                    {
                        "factor_id": candidate.factor_id,
                        "expression": candidate.expression,
                        "passed": False,
                        "errors": [f"parse_error: {exc}"],
                        "stage": "dsl_validation",
                    }
                )

        yield self._state_event(
            ctx,
            {
                "factors.validated": validated,
                "factors.rejected": rejected,
                "factors.validation": validation_rows,
            },
            text=(
                f"DslValidationAgent passed={len(validated)} rejected={len(rejected)}"
            ),
        )
