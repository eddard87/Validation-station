from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import anthropic
import structlog

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    WAITING = "waiting"


class AgentResult:
    def __init__(
        self,
        status: AgentStatus,
        output: Any,
        agent_name: str,
        task_id: str,
        duration_seconds: float = 0.0,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.status = status
        self.output = output
        self.agent_name = agent_name
        self.task_id = task_id
        self.duration_seconds = duration_seconds
        self.error = error
        self.metadata = metadata or {}
        self.completed_at = datetime.utcnow()

    def succeeded(self) -> bool:
        return self.status == AgentStatus.SUCCEEDED

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat(),
        }


class BaseAgent(ABC):
    """
    Abstract base for all Generali Fabric platform agents.
    Each agent uses Claude with tool use to reason about and execute data tasks.
    """

    def __init__(
        self,
        name: str,
        description: str,
        config: dict,
        tools: Optional[list[dict]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.config = config
        self._tools = tools or []
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = config.get("model", "claude-opus-4-8")
        self._max_tokens = config.get("max_tokens", 8096)
        self._max_iterations = config.get("max_iterations", 10)
        self.status = AgentStatus.IDLE
        self.log = logger.bind(agent=self.name)

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Domain-specific system prompt for this agent."""
        ...

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return the list of Anthropic tool definitions this agent exposes."""
        ...

    @abstractmethod
    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Execute a tool call dispatched by the model."""
        ...

    def run(self, task: str, context: Optional[dict] = None, task_id: str = "") -> AgentResult:
        start = datetime.utcnow()
        self.status = AgentStatus.RUNNING
        self.log.info("agent_start", task=task[:120])

        messages: list[dict] = [{"role": "user", "content": task}]
        if context:
            messages[0]["content"] = (
                f"Context:\n{json.dumps(context, default=str, indent=2)}\n\nTask:\n{task}"
            )

        iterations = 0
        final_output = None

        try:
            while iterations < self._max_iterations:
                iterations += 1
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=self.system_prompt,
                    tools=self.get_tools(),
                    messages=messages,
                )

                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_output = block.text
                    break

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            self.log.info("tool_call", tool=block.name, input=block.input)
                            try:
                                result = self.execute_tool(block.name, block.input)
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, default=str),
                                })
                            except Exception as e:
                                self.log.error("tool_error", tool=block.name, error=str(e))
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"ERROR: {e}",
                                    "is_error": True,
                                })
                    messages.append({"role": "user", "content": tool_results})

            duration = (datetime.utcnow() - start).total_seconds()
            self.status = AgentStatus.SUCCEEDED
            self.log.info("agent_complete", duration_s=duration, iterations=iterations)
            return AgentResult(
                status=AgentStatus.SUCCEEDED,
                output=final_output,
                agent_name=self.name,
                task_id=task_id,
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = (datetime.utcnow() - start).total_seconds()
            self.status = AgentStatus.FAILED
            self.log.exception("agent_failed", error=str(exc))
            return AgentResult(
                status=AgentStatus.FAILED,
                output=None,
                agent_name=self.name,
                task_id=task_id,
                duration_seconds=duration,
                error=str(exc),
            )
