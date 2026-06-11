"""Skill — 可复用的程序性记忆(procedural)。markdown + frontmatter 持久化。 [P3]

一个 skill = 一次【验证通过】的解法被结晶成的可复用流程：步骤/坑/验证步骤/依赖。
对齐 Hermes 的 skill；但只有 verified_by 非空（过了 Verifier）的才算数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# frontmatter 字段（不含正文 body）
_FIELDS = (
    "name", "scope", "scope_id", "id", "use_count", "patch_count",
    "created", "last_used", "state", "verified_by", "source_goal",
)
_INT = {"use_count", "patch_count"}
_FLOAT = {"created", "last_used"}


@dataclass
class Skill:
    name: str = "untitled"
    body: str = ""                 # markdown 正文：步骤/坑/验证/依赖
    scope: str = "project"         # project | shared
    scope_id: str = ""             # project_id 或 "shared"
    id: str = ""
    use_count: int = 0
    patch_count: int = 0
    created: float = 0.0           # epoch 秒
    last_used: float = 0.0
    state: str = "active"          # active | stale | archived
    verified_by: str = ""          # verifier id —— 空=未验证，不该作为 skill 存在
    source_goal: str = ""


def to_markdown(s: Skill) -> str:
    lines = ["---"]
    for k in _FIELDS:
        v = str(getattr(s, k)).replace("\n", " ")   # frontmatter 单行
        lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines) + s.body


def from_markdown(text: str) -> Skill:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return Skill(body=text)
    data: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k not in _FIELDS:
            continue
        if k in _INT:
            v = int(v or 0)
        elif k in _FLOAT:
            v = float(v or 0)
        data[k] = v
    return Skill(body=m.group(2), **data)
