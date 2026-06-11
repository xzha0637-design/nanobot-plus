"""CliWorker — 用 headless 子进程统一驱动非 Claude 的 CLI agent (Codex / Gemini)。 [P5]

无原生 can_use_tool 的后端 → 用沙箱/只读挂载兜底(能力降级)。
"""

from __future__ import annotations

from .base import BaseWorker
from ..contracts import CanUseTool, EventSink, TaskSpec, WorkerCapabilities, WorkerResult


class CliWorker(BaseWorker):
    capabilities = WorkerCapabilities(
        native_approval=False, resumable=True, mcp=False, streaming=True
    )

    def __init__(self, project_id: str, cwd: str, *, command: list[str]) -> None:
        super().__init__(project_id)
        self.cwd = cwd
        self.command = command            # e.g. ["claude","-p","--output-format","stream-json"]

    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        # TODO(P5): asyncio.create_subprocess_exec(cwd=self.cwd, env=...); 解析 stream-json；
        #           无原生审批 → 在受限沙箱内跑，关键写操作仍走 can_use_tool 的进程级近似。
        raise NotImplementedError("P5")
