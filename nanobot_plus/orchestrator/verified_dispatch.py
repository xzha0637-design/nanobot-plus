"""verify + retry 闭环：dispatch → verify → 不过则带 refined 指令重试。 [P2]

P2 的核心。通过的 outcome 才有资格在 P3 晋升进记忆 / 结晶成 skill。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agents.manager import AgentWorkerManager
from ..contracts import CanUseTool, EventSink, TaskSpec, WorkerResult
from .verifier import Verdict, Verifier


@dataclass
class VerifiedOutcome:
    result: WorkerResult
    verdict: Verdict
    attempts: int


async def dispatch_verified(
    mgr: AgentWorkerManager,
    spec: TaskSpec,
    *,
    factory,
    on_event: EventSink,
    can_use_tool: CanUseTool,
    verifier: Verifier,
    project_dir: str,
    max_retries: int = 2,
    env: dict[str, str] | None = None,
) -> VerifiedOutcome:
    attempt = 0
    cur = spec
    while True:
        attempt += 1
        result = await mgr.dispatch_to(
            cur, factory=factory, on_event=on_event, can_use_tool=can_use_tool, env=env,
        )
        verdict = await verifier.verify(cur, result, project_dir)
        if verdict.passed or attempt > max_retries:
            return VerifiedOutcome(result=result, verdict=verdict, attempts=attempt)

        # refine：把未满足的判据回灌同一持久 worker（它带着上次的中期记忆）
        miss = "\n".join(f"- {m}" for m in (verdict.missing or ["上次未达成目标"]))
        cur = TaskSpec(
            goal=f"{spec.goal}\n\n上一次验收未通过，请仅补齐以下未满足项:\n{miss}",
            project_id=spec.project_id,
            done_criteria=spec.done_criteria,
            context_refs=spec.context_refs,
            allowed_mcp=spec.allowed_mcp,
            permission_mode=spec.permission_mode,
        )
