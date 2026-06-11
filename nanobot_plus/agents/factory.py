"""按项目登记表造 worker 的工厂。

把 project_id 映射到一个绑定了该项目目录的 ClaudeCodeWorker。
模型/后端不在这里设——走你 settings.json 里 ccswitch 配的那套。
"""

from __future__ import annotations

from typing import Callable, Mapping

from ..config import ProjectConfig
from ..contracts import AgentWorker


def build_claude_factory(
    projects: Mapping[str, ProjectConfig],
    *,
    mcp_servers: dict | None = None,
) -> Callable[[str], AgentWorker]:
    """返回 factory(project_id) -> ClaudeCodeWorker（cwd = 该项目目录）。"""
    from .claude_worker import ClaudeCodeWorker

    def factory(project_id: str) -> AgentWorker:
        pc = projects[project_id]
        return ClaudeCodeWorker(project_id, pc.path, mcp_servers=mcp_servers)

    return factory
