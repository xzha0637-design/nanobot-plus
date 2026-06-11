"""SkillSynthesizer — 把【验证通过】的 episode 结晶成 skill；用中偏差则 patch。 [P3]

LLM 惰性导入。crystallize 只该在 Verdict.passed 后调用 —— 验证优先，不固化错解。
run_agent 可注入（测试用）：async (prompt) -> str。
"""

from __future__ import annotations

import re

from .skill import Skill

_SYS = (
    "你把一次【已验证成功】的解法提炼成一个可复用 skill。"
    "输出 markdown：第一行 `# 简短技能名`，然后 `## 步骤` / `## 坑` / `## 验证` / `## 依赖`。"
    "要可操作、可迁移；去掉本次特有的具体路径等噪声。"
)


def _name_of(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", md, re.M)
    return (m.group(1).strip() if m else fallback)[:60]


class SkillSynthesizer:
    def __init__(self, *, model: str | None = None, run_agent=None) -> None:
        self._model = model
        self._run = run_agent

    async def crystallize(self, spec, result, verdict) -> Skill:
        crit = "\n".join(f"- {c}" for c in spec.done_criteria)
        prompt = (
            f"任务目标:\n{spec.goal}\n\n判据(已通过独立验证):\n{crit}\n\n"
            f"做了什么: {', '.join(result.artifacts) or '见自述'}\n自述: {result.summary[:800]}\n\n"
            "把它提炼成可复用 skill（下次遇到类似任务能照着做）。"
        )
        md = await self._call(prompt)
        return Skill(
            name=_name_of(md, spec.goal[:40]),
            body=md,
            scope="project",
            scope_id=spec.project_id,
            verified_by=getattr(verdict, "verifier_id", "") or "verified",
            source_goal=spec.goal[:200],
        )

    async def patch(self, skill: Skill, spec, result, verdict) -> Skill:
        prompt = (
            f"已有 skill:\n{skill.body}\n\n"
            f"这次用它做「{spec.goal}」但验收未过，缺: {getattr(verdict, 'missing', [])}。"
            f"自述: {result.summary[:600]}\n请修订 skill（补坑/改步骤），输出完整新版 markdown。"
        )
        md = await self._call(prompt)
        skill.body = md
        skill.name = _name_of(md, skill.name)
        skill.patch_count += 1
        return skill

    async def _call(self, prompt: str) -> str:
        if self._run:
            return await self._run(prompt)
        from claude_agent_sdk import ClaudeAgentOptions, query
        kw = dict(
            system_prompt=_SYS,
            permission_mode="bypassPermissions",
            disallowed_tools=["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"],
        )
        if self._model:
            kw["model"] = self._model
        out: list[str] = []
        async for m in query(prompt=prompt, options=ClaudeAgentOptions(**kw)):
            r = getattr(m, "result", None)
            if r:
                out.append(str(r))
            else:
                for b in getattr(m, "content", None) or []:
                    t = getattr(b, "text", None)
                    if t:
                        out.append(t)
        return "".join(out)
