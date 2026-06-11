"""FileMemoryStore — MemoryStore 的文本优先实现(E2)。 [P3]

  project scope → 每项目 .nbplus/ 文本库（随 repo, git 版本化, 人可编辑）
  shared scope  → sqlite 经验池（写入必须 verified_by，挡综述 M3 错误经验传播）
  量大后再在文本之上加 E1 向量索引做召回。
"""

from __future__ import annotations

from ..contracts import MemoryItem, Scope
from .project_store import ProjectTextStore


class FileMemoryStore:   # 实现 MemoryStore 协议
    def __init__(self, *, projects: dict[str, str] | None = None, shared_db: str = ".nbplus/shared.sqlite") -> None:
        self._paths = projects or {}                       # project_id -> 项目目录
        self._shared_db = shared_db
        self._proj_cache: dict[str, ProjectTextStore] = {}

    def _proj(self, project_id: str) -> ProjectTextStore:
        if project_id not in self._proj_cache:
            self._proj_cache[project_id] = ProjectTextStore(self._paths[project_id])
        return self._proj_cache[project_id]

    def write(self, item: MemoryItem) -> str:
        # TODO(P3): project → 写 .nbplus 对应文本(semantic/episodic/procedural);
        #           shared  → 必须 item.verified_by 非空，否则拒绝。
        raise NotImplementedError("P3")

    def recall(self, query: str, *, scope: Scope, scope_id: str, k: int = 8) -> list[MemoryItem]:
        raise NotImplementedError("P3")

    def promote(self, item_id: str, *, verified_by: str) -> None:
        # 唯一晋升入口：verified_by 必填。
        raise NotImplementedError("P3")

    def consolidate(self, project_id: str) -> None:
        raise NotImplementedError("P3")

    def context_pack(self, goal: str, *, project_id: str, budget_tokens: int) -> list[str]:
        raise NotImplementedError("P3")
