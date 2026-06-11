"""AgentWorkerManager — 持久 worker 注册表 + 并发上限 + 生命周期。每项目一个长驻 worker。"""

from __future__ import annotations

import asyncio
from typing import Callable

from ..contracts import AgentWorker, CanUseTool, EventSink, TaskSpec, WorkerResult


class AgentWorkerManager:
    def __init__(self, *, max_concurrent: int = 4, default_env: dict[str, str] | None = None) -> None:
        self._workers: dict[str, AgentWorker] = {}            # project_id -> worker(持久)
        self._sem = asyncio.Semaphore(max_concurrent)         # 防 N× 吞吐/速率
        self._default_env = default_env or {}

    def get_or_create(self, project_id: str, factory: Callable[[str], AgentWorker]) -> AgentWorker:
        if project_id not in self._workers:
            self._workers[project_id] = factory(project_id)
        return self._workers[project_id]

    async def dispatch(
        self,
        spec: TaskSpec,
        *,
        worker: AgentWorker,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        async with self._sem:
            return await worker.send(
                spec,
                on_event=on_event,
                can_use_tool=can_use_tool,
                env=env or self._default_env,
            )

    async def dispatch_to(
        self,
        spec: TaskSpec,
        *,
        factory: Callable[[str], AgentWorker],
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        """get_or_create(该项目的持久 worker) 然后 dispatch。"""
        worker = self.get_or_create(spec.project_id, factory)
        return await self.dispatch(
            spec, worker=worker, on_event=on_event, can_use_tool=can_use_tool, env=env,
        )

    async def interrupt(self, project_id: str) -> None:
        if w := self._workers.get(project_id):
            await w.interrupt()

    async def close_all(self) -> None:
        for w in list(self._workers.values()):
            await w.close()
        self._workers.clear()
