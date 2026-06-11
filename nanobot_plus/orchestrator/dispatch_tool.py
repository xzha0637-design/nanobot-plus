"""dispatch 工具 — 大脑用它把任务派给某个项目的持久 worker。 [P1]

execute() 已可用。接进 nanobot：用 nanobot 的 Tool 基类包一层 execute() 并注册到
工具注册表（参照 nanobot/nanobot/agent/tools/spawn.py），这步留作 P1 收尾。
"""

from __future__ import annotations

from typing import Callable

from ..agents.manager import AgentWorkerManager
from ..contracts import AgentWorker, CanUseTool, EventSink, TaskSpec, WorkerResult


class DispatchTool:
    name = "dispatch"
    description = (
        "把一个任务派给某个项目的持久 Claude Code worker（独立目录隔离 + 中期记忆）。"
        "关键步骤会停下来等用户审批；完成后返回结构化结果。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "目标项目 id（已在项目登记表里）"},
            "goal": {"type": "string", "description": "要这个项目完成什么"},
            "done_criteria": {"type": "array", "items": {"type": "string"}, "description": "可验证的完成判据"},
            "context_refs": {"type": "array", "items": {"type": "string"}, "description": "相关文件/规范/记忆条目的指针，不灌全文"},
            "allowed_mcp": {"type": "array", "items": {"type": "string"}, "description": "本任务可用的 MCP server 名"},
        },
        "required": ["project_id", "goal"],
    }

    def __init__(
        self,
        manager: AgentWorkerManager,
        *,
        factory: Callable[[str], AgentWorker],
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> None:
        self._m = manager
        self._factory = factory
        self._on_event = on_event
        self._can_use_tool = can_use_tool
        self._env = env

    async def execute(
        self,
        *,
        project_id: str,
        goal: str,
        done_criteria: list[str] | None = None,
        context_refs: list[str] | None = None,
        allowed_mcp: list[str] | None = None,
        permission_mode: str = "plan",
        session_id: str | None = None,
    ) -> WorkerResult:
        spec = TaskSpec(
            goal=goal,
            project_id=project_id,
            done_criteria=done_criteria or [],
            context_refs=context_refs or [],
            allowed_mcp=allowed_mcp or [],
            permission_mode=permission_mode,
            session_id=session_id,
        )
        return await self._m.dispatch_to(
            spec,
            factory=self._factory,
            on_event=self._on_event,
            can_use_tool=self._can_use_tool,
            env=self._env,
        )
