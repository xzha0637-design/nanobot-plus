"""ClaudeCodeWorker — 每项目一个持久 ClaudeSDKClient 会话；经 ccswitch env 接 DeepSeek。

承重墙的工程化版本。可运行雏形见 spikes/p0_spike.py。
"""

from __future__ import annotations

from .base import BaseWorker
from ..contracts import (
    CanUseTool,
    EventSink,
    TaskSpec,
    WorkerCapabilities,
    WorkerResult,
)

# P1 时启用：
# from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions


class ClaudeCodeWorker(BaseWorker):
    capabilities = WorkerCapabilities(
        native_approval=True, resumable=True, mcp=True, streaming=True
    )

    def __init__(self, project_id: str, cwd: str, *, model: str | None = None) -> None:
        super().__init__(project_id)
        self.cwd = cwd                       # ← cwd 隔离(每项目独立目录)
        self.model = model
        self._client = None                  # 复用的持久 ClaudeSDKClient

    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        # TODO(P1):
        #   opts = ClaudeAgentOptions(
        #       cwd=self.cwd,
        #       permission_mode=spec.permission_mode,        # plan → 批 → acceptEdits
        #       can_use_tool=can_use_tool,                   # 人在环审批
        #       mcp_servers=_mcp_config(spec.allowed_mcp),   # 浏览器/Obsidian 等
        #       env=env,                                     # ← ccswitch: ANTHROPIC_BASE_URL/token
        #       model=self.model,
        #       resume=spec.session_id,                      # 续会话=中期记忆
        #   )
        #   持久会话：首次建 self._client = ClaudeSDKClient(opts) 并 connect；之后复用。
        #   await client.query(_render(spec))
        #   async for msg in client.receive_response(): await on_event(_event(msg))
        #   return _to_result(spec, collected)   # 压缩成 WorkerResult，回填 session_id
        raise NotImplementedError("P1: 驱动 ClaudeSDKClient，先看 spikes/p0_spike.py")

    async def interrupt(self) -> None:
        # TODO(P2): await self._client.interrupt()
        return None

    async def close(self) -> None:
        # TODO: await self._client.disconnect()  (session_id 可持久化供日后 resume)
        self._client = None
