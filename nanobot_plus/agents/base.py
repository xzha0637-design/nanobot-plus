"""所有 worker 的公共生命周期。具体后端实现 send()。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import (
    CanUseTool,
    EventSink,
    TaskSpec,
    WorkerCapabilities,
    WorkerResult,
)


class BaseWorker(ABC):
    """结构上满足 AgentWorker 协议。一个 worker 绑定一个 project，持有持久会话。"""

    capabilities: WorkerCapabilities = WorkerCapabilities()

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.session_id: str | None = None      # 持久会话锚点(中期记忆)

    @abstractmethod
    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        ...

    async def interrupt(self) -> None:
        # TODO: 默认 no-op；可中断的后端覆盖。
        return None

    async def close(self) -> None:
        return None
