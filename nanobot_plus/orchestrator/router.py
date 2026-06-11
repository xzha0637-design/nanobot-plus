"""Router — 目标 → 子任务 → 选项目/会话。独立项目场景下主要按 project 路由。 [P1]"""

from __future__ import annotations

from ..contracts import TaskSpec


class Router:
    def route(self, goal: str) -> list[TaskSpec]:
        # TODO(P1): 让大脑(LLM)把 goal 拆成按 project 的 TaskSpec 列表。
        raise NotImplementedError("P1")
