"""dispatch 工具 — 大脑用它创建/分派/查询持久 worker。注册进 nanobot 工具注册表。 [P1]

工具形态参照 nanobot/nanobot/agent/tools/spawn.py。
"""

from __future__ import annotations

from ..agents.manager import AgentWorkerManager
from ..contracts import CanUseTool, EventSink, TaskSpec, WorkerResult


class DispatchTool:
    name = "dispatch"
    description = (
        "把一个任务派给某个项目的持久 Claude Code worker（独立目录隔离 + 中期记忆）。"
        "关键步骤会停下来等用户审批；完成后返回结构化结果。"
    )
    # JSON schema(P1 细化): {project_id, goal, done_criteria[], context_refs[], allowed_mcp[]}

    def __init__(
        self,
        manager: AgentWorkerManager,
        *,
        worker_factory,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> None:
        self._m = manager
        self._factory = worker_factory
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
        session_id: str | None = None,
    ) -> WorkerResult:
        spec = TaskSpec(
            goal=goal,
            project_id=project_id,
            done_criteria=done_criteria or [],
            context_refs=context_refs or [],
            allowed_mcp=allowed_mcp or [],
            session_id=session_id,          # 非空=续会话(中期记忆)
        )
        worker = self._m.get_or_create(project_id, self._factory)
        return await self._m.dispatch(
            spec,
            worker=worker,
            on_event=self._on_event,
            can_use_tool=self._can_use_tool,
            env=self._env,
        )
