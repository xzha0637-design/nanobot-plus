"""Curator — skill 生命周期：按"多久没用"做 active → stale → archived。 [P3]

借 Hermes 阈值：30 天没用 → stale，90 天 → archived。clock 可注入便于测试。
"""

from __future__ import annotations

import time


class Curator:
    def __init__(self, *, stale_days: int = 30, archive_days: int = 90, clock=time.time) -> None:
        self.stale = stale_days * 86400
        self.archive = archive_days * 86400
        self._clock = clock

    def curate(self, store) -> dict:
        """扫描全部 skill，按空闲时长更新 state，返回各状态计数。"""
        now = self._clock()
        counts = {"active": 0, "stale": 0, "archived": 0}
        for s in store.all():
            ref = s.last_used or s.created or now
            age = now - ref
            new = "archived" if age >= self.archive else ("stale" if age >= self.stale else "active")
            if new != s.state:
                s.state = new
                store.save(s)
            counts[new] += 1
        return counts
