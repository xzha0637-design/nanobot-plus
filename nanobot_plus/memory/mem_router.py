"""MemoryRouter — 按 scope/project/role 路由读写（综述 E4 分层 / M2 routing）。 [P3]

私有项目记忆强隔离；shared 经验池只读受控、写需验证晋升。
"""

from __future__ import annotations

from ..contracts import MemoryStore


class MemoryRouter:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store
    # TODO(P3): route(scope, project_id, role) → 选择正确的 store/分区。
