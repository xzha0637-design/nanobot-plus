"""Blackboard — 运行时协调(E3 结构库)：谁动了哪些文件/模块、冲突、依赖边。 [P3]

注意：图指向【运行时协调】，不是静态代码结构（后者红海+易过时+agent 已会）。
用途：依赖感知派发 + 并发写冲突检测。后端先 sqlite，必要时换嵌入式图。
"""

from __future__ import annotations


class Blackboard:
    def __init__(self, db_path: str = ".nbplus/blackboard.sqlite") -> None:
        self.db_path = db_path

    def record_edit(self, *, project_id: str, worker_id: str, paths: list[str]) -> None:
        raise NotImplementedError("P3")

    def conflicts_with(self, *, project_id: str, paths: list[str]) -> list[str]:
        # 返回与给定 paths 并发写冲突的其它 worker_id
        raise NotImplementedError("P3")

    def add_dependency(self, a_task: str, b_task: str) -> None:
        raise NotImplementedError("P3")
