"""Shared types for graded verifiers.

Contains the grading :class:`Criterion` and the lightweight ATIF trajectory
types (:class:`Trajectory`, :class:`Step`, :class:`ToolCall`). The trajectory
types are intentionally minimal read-only mirrors of the ATIF types defined in
``harbor.models.trajectories``. They use ``extra="ignore"`` throughout so that
forward-compatible ATIF schema additions (new fields, new versions) never cause
parse failures in verifier scripts.

Use ``Evaluator.load_trajectory()`` to get a typed ``Trajectory`` from the
agent log written during a trial.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field


class Criterion(BaseModel):
    """A single grading criterion registered via ``Evaluator.criterion``."""

    name: str
    weight: float = 1.0
    fatal: bool = False
    func: Callable[[Path], Any]

    model_config = {"arbitrary_types_allowed": True}


class ToolCall(BaseModel):
    """A single tool invocation within an agent step."""

    tool_call_id: str
    function_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}

    def arg(self, key: str, default: Any = None) -> Any:
        """Convenience accessor for a single argument value."""
        return self.arguments.get(key, default)


class Step(BaseModel):
    """One turn in the agent trajectory."""

    step_id: int
    source: str  # "user" | "agent" | "system"
    message: Any = ""  # str or list[ContentPart] — we accept either
    tool_calls: list[ToolCall] | None = None

    model_config = {"extra": "ignore"}


class Trajectory(BaseModel):
    """Parsed ATIF trajectory.  Exposes a small query API for verifier use."""

    schema_version: str = ""
    session_id: str | None = None
    steps: list[Step] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    # ------------------------------------------------------------------
    # Query primitives
    # ------------------------------------------------------------------

    def all_tool_calls(self) -> list[ToolCall]:
        """Flat list of every tool call made across all agent steps."""
        return [
            tc
            for step in self.steps
            if step.tool_calls
            for tc in step.tool_calls
        ]

    def tool_calls_for(self, function_name: str) -> list[ToolCall]:
        """All tool calls whose ``function_name`` matches exactly.

        Equivalent to ``find_all(function_name)``.
        """
        return self.find_all(function_name)

    def exists(
        self,
        function_name: str,
        predicate: Callable[[ToolCall], bool] | None = None,
    ) -> bool:
        """Return ``True`` if any tool call matches ``function_name`` and,
        optionally, satisfies ``predicate``.

        Examples::

            trajectory.exists("write_file")
            trajectory.exists(
                "write_file",
                lambda tc: PurePosixPath(tc.arg("path", "")).name == "blog_post.md",
            )
            trajectory.exists("terminal", lambda tc: "pytest" in tc.arg("command", ""))
        """
        return self.find(function_name, predicate) is not None

    def find(
        self,
        function_name: str,
        predicate: Callable[[ToolCall], bool] | None = None,
    ) -> ToolCall | None:
        """Return the first :class:`ToolCall` matching ``function_name`` (and
        ``predicate`` if given), or ``None`` if no match is found.

        Example::

            tc = trajectory.find("write_file")
            if tc:
                print(tc.arg("path"))
        """
        for tc in self.all_tool_calls():
            if tc.function_name != function_name:
                continue
            if predicate is None or predicate(tc):
                return tc
        return None

    def find_all(
        self,
        function_name: str,
        predicate: Callable[[ToolCall], bool] | None = None,
    ) -> list[ToolCall]:
        """Return all :class:`ToolCall` objects matching ``function_name`` (and
        ``predicate`` if given).

        Example::

            calls = trajectory.find_all("write_file")
            paths = [tc.arg("path") for tc in calls]
        """
        return [
            tc
            for tc in self.all_tool_calls()
            if tc.function_name == function_name
            and (predicate is None or predicate(tc))
        ]
