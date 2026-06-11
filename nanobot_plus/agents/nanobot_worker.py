"""NanobotWorker — 把 nanobot 自带 in-process subagent 套进 AgentWorker 接口。 [P1]

用于无状态 fan-out 子任务（短期记忆即可）。持久项目追踪请用 ClaudeCodeWorker。
"""

from __future__ import annotations

from .base import BaseWorker
from ..contracts import CanUseTool, EventSink, TaskSpec, WorkerCapabilities, WorkerResult


class NanobotWorker(BaseWorker):
    capabilities = WorkerCapabilities(
        native_approval=False, resumable=False, mcp=True, streaming=True
    )

    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        # TODO(P1): 复用 nanobot.agent.subagent.SubagentManager.spawn(...)，
        #           把其 announce 结果映射成 WorkerResult。
        raise NotImplementedError("P1")
