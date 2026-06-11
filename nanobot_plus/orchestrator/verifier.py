"""Verifier — 独立验证。全新上下文，只拿 done_criteria + diff + evidence，不看 worker transcript。 [P2]

DeepSeek 后端更易出"似是而非"，这层是收敛正确性的闸门。
只有通过的结果才允许晋升进长期/共享记忆（MemoryStore.promote 的 verified_by 来源）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import TaskSpec, WorkerResult


@dataclass
class Verdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)   # 哪些 done_criteria 未满足
    verifier_id: str = ""


class Verifier:
    def __init__(self, *, run_agent) -> None:
        self._run_agent = run_agent   # 注入"跑全新上下文 agent"的可调用

    async def verify(self, spec: TaskSpec, result: WorkerResult, diff: str) -> Verdict:
        # TODO(P2): prompt 只含 spec.done_criteria + diff + result.evidence（不含 transcript）；
        #           让全新 agent 逐条判定 → Verdict。
        raise NotImplementedError("P2")
