"""
Base Agent Abstract Class
=========================
Every agent in the Opella platform must inherit from BaseAgent.
Adheres to:
  - Single Responsibility: Does one specialized function.
  - Dependency Inversion: Relies on injected interfaces/clients, never instantiates them directly.
  - State Communication: Reads from and returns updated AgentState.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

import structlog
from app.agents.types import AgentError, AgentState, ExecutionEvent

logger = structlog.get_logger(__name__)

StateT = TypeVar("StateT", bound=Dict[str, Any])


class BaseAgent(ABC, Generic[StateT]):
    """
    Abstract Base Class for all specialized agents.
    """

    name: str = "base_agent"
    version: str = "1.0.0"

    def __init__(self, **dependencies: Any) -> None:
        self.dependencies = dependencies
        self._logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    def validate_input(self, state: StateT) -> None:
        """
        Validates that required fields are present in the state
        before execution begins. Raises ValueError if invalid.
        """
        ...

    @abstractmethod
    async def process(self, state: StateT) -> StateT:
        """
        Core agent business logic. Must return updated state dict.
        """
        ...

    async def execute(self, state: StateT) -> StateT:
        """
        Template method wrapping execution with input validation,
        telemetry, execution duration, and structured error handling.
        """
        tracer = state.get("tracer")
        start_time = time.perf_counter()

        if tracer and hasattr(tracer, "node_start"):
            await tracer.node_start(self.name, f"Executing {self.name}...")

        try:
            self.validate_input(state)
            updated_state = await self.process(state)
            duration_ms = (time.perf_counter() - start_time) * 1000

            summary = self.summarize_execution(updated_state)
            if tracer and hasattr(tracer, "node_success"):
                await tracer.node_success(self.name, summary)

            # Record ExecutionEvent into state
            events = updated_state.get("execution_events") or []
            events.append(
                ExecutionEvent(
                    node=self.name,
                    status="success",
                    duration_ms=round(duration_ms, 2),
                    summary=summary,
                )
            )
            updated_state["execution_events"] = events
            return updated_state

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            err_msg = str(exc)
            self._logger.error("agent_execution_failed", agent=self.name, error=err_msg)

            if tracer and hasattr(tracer, "node_failed"):
                await tracer.node_failed(self.name, err_msg)

            # Record AgentError
            errors = state.get("errors") or []
            errors.append(AgentError(agent_name=self.name, error_message=err_msg))
            state["errors"] = errors

            # Graceful error handling in state
            events = state.get("execution_events") or []
            events.append(
                ExecutionEvent(
                    node=self.name,
                    status="failed",
                    duration_ms=round(duration_ms, 2),
                    summary=f"Failed: {err_msg}",
                    error=err_msg,
                )
            )
            state["execution_events"] = events
            return await self.handle_failure(state, exc)

    def summarize_execution(self, state: StateT) -> str:
        """Override to provide a human-readable summary for telemetry."""
        return f"{self.name} completed successfully."

    async def handle_failure(self, state: StateT, exc: Exception) -> StateT:
        """
        Graceful fallback when an agent fails.
        Can be overridden by subclasses to provide custom recovery.
        """
        return state

    def metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "dependencies": list(self.dependencies.keys()),
        }
