"""ProjectTextStore — 每项目 .nbplus/ 文本库(E2)。随 repo、git 版本化、人可编辑。 [P3]

  core.md / facts.md  → semantic
  episodes.jsonl      → episodic（任务轨迹 {goal,attempts,patch,tests,verdict}）
  playbooks/          → procedural（可复用流程）
"""

from __future__ import annotations

from pathlib import Path


class ProjectTextStore:
    def __init__(self, project_path: str) -> None:
        self.root = Path(project_path) / ".nbplus"

    def append_episode(self, record: dict) -> None:
        raise NotImplementedError("P3")        # 追加到 episodes.jsonl

    def read_semantic(self) -> str:
        raise NotImplementedError("P3")        # core.md + facts.md

    def upsert_fact(self, text: str) -> None:
        raise NotImplementedError("P3")        # facts.md

    def add_playbook(self, name: str, body: str) -> None:
        raise NotImplementedError("P3")        # playbooks/<name>.md
