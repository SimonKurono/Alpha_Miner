"""Base helpers for deterministic Feature 3 custom agents."""

from __future__ import annotations

from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types


class StatefulCustomAgent(BaseAgent):
    def _state_event(
        self,
        ctx: InvocationContext,
        state_delta: dict[str, Any],
        text: str | None = None,
        *,
        escalate: bool = False,
    ) -> Event:
        content = None
        if text is not None:
            content = types.Content(role="model", parts=[types.Part(text=text)])
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=content,
            actions=EventActions(state_delta=state_delta, escalate=escalate),
        )

    def _text_event(self, ctx: InvocationContext, text: str) -> Event:
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=text)]),
        )
