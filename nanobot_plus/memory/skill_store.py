"""SkillStore — 文件式 skill 库（每个 skill 一个 .md）。recall = 关键词重叠（FTS 后续）。 [P3]

落在 项目 .nbplus/skills/（项目私有）或一个共享目录（跨项目）。文本优先、可 git、可人工编辑。
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from .skill import Skill, from_markdown, to_markdown


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "skill"


def _tok(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9一-鿿]+", s.lower()))


class SkillStore:
    def __init__(self, root, *, clock=time.time) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, skill: Skill) -> Path:
        return self.root / f"{skill.id or _slug(skill.name)}.md"

    def save(self, skill: Skill) -> Path:
        if not skill.id:
            skill.id = _slug(skill.name)
        if not skill.created:
            skill.created = self._clock()
        p = self._path(skill)
        p.write_text(to_markdown(skill))
        return p

    def load(self, path) -> Skill:
        return from_markdown(Path(path).read_text())

    def all(self) -> list[Skill]:
        return [self.load(p) for p in sorted(self.root.glob("*.md"))]

    def recall(self, goal: str, k: int = 3, *, include_states=("active",)) -> list[Skill]:
        gt = _tok(goal)
        scored: list[tuple[int, Skill]] = []
        for s in self.all():
            if s.state not in include_states:
                continue
            overlap = len(gt & _tok(f"{s.name} {s.source_goal} {s.body[:400]}"))
            if overlap:
                scored.append((overlap, s))
        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:k]]

    def touch(self, skill: Skill) -> None:
        skill.use_count += 1
        skill.last_used = self._clock()
        self.save(skill)
