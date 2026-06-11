"""Tracer — 结构化 trace + 成本归因(按 worker)，可复现。 [P5]"""

from __future__ import annotations


class Tracer:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def record(self, event: dict) -> None:
        self.events.append(event)   # TODO(P5): 落盘 + 成本聚合 + 复现
