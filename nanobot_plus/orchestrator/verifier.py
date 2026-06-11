"""Verifier — 独立验证。全新上下文（query 一次性），只读项目目录核对 done_criteria。 [P2]

与 worker 解耦：只拿 goal + done_criteria + artifacts 提示 + 只读权限，不看 worker transcript。
DeepSeek 后端更易出"似是而非"，这层是收敛正确性的闸门；通过的结果才能晋升进记忆（自进化前置）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..contracts import TaskSpec, WorkerResult

_VERIFIER_SYS = (
    "你是独立验收员。只依据给定判据和你亲自读到的项目文件下结论，"
    "不要相信 worker 的自述。只输出 JSON，不要多余文字。"
)


@dataclass
class Verdict:
    passed: bool
    criteria: list = field(default_factory=list)   # [{criterion, met, why}]
    missing: list = field(default_factory=list)     # 未满足的判据
    raw: str = ""


def _prompt(spec: TaskSpec, result: WorkerResult) -> str:
    crit = "\n".join(f"- {c}" for c in spec.done_criteria) or "(无显式判据：判断目标是否达成)"
    arts = ", ".join(result.artifacts) or "(未声明)"
    return (
        f"目标:\n{spec.goal}\n\n完成判据:\n{crit}\n\n"
        f"worker 声称改了: {arts}\nworker 自述: {result.summary[:800]}\n\n"
        "请亲自读项目里的文件逐条核对，只输出 JSON:\n"
        '{"passed": true/false, "criteria": [{"criterion": "...", "met": true/false, "why": "..."}], '
        '"missing": ["未满足的判据"]}'
    )


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


class Verifier:
    def __init__(self, *, model: str | None = None, run_agent=None) -> None:
        self._model = model
        self._run_agent = run_agent     # 可注入(测试): async (prompt, cwd) -> str

    async def verify(self, spec: TaskSpec, result: WorkerResult, project_dir: str) -> Verdict:
        prompt = _prompt(spec, result)
        text = await (self._run_agent(prompt, project_dir) if self._run_agent
                      else self._run_sdk(prompt, project_dir))
        data = _extract_json(text) or {}
        return Verdict(
            passed=bool(data.get("passed")),
            criteria=data.get("criteria", []),
            missing=data.get("missing", []),
            raw=text[:2000],
        )

    async def _run_sdk(self, prompt: str, cwd: str) -> str:
        from claude_agent_sdk import ClaudeAgentOptions, query
        kwargs = dict(
            cwd=cwd,
            system_prompt=_VERIFIER_SYS,
            permission_mode="bypassPermissions",                       # 仅剩只读工具，无副作用
            disallowed_tools=["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"],
        )
        if self._model:
            kwargs["model"] = self._model
        out: list[str] = []
        async for msg in query(prompt=prompt, options=ClaudeAgentOptions(**kwargs)):
            r = getattr(msg, "result", None)
            if r:
                out.append(str(r))
            else:
                for b in getattr(msg, "content", None) or []:
                    t = getattr(b, "text", None)
                    if t:
                        out.append(t)
        return "".join(out)
