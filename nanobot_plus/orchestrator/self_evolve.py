"""自进化循环：recall → inject → dispatch+verify → (pass)结晶入库 / (fail)用中 patch。 [P3]

验证优先：只有 outcome.verdict.passed 才结晶 skill（不固化错解）。
Curator 另行周期跑（`Curator().curate(store)`），不在这条热路径里。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..contracts import TaskSpec
from .verified_dispatch import VerifiedOutcome, dispatch_verified


def inject_skills(spec: TaskSpec, skills) -> TaskSpec:
    """把召回的 skill 正文注入任务（procedural 记忆是给 worker 直接用的，不是指针）。"""
    if not skills:
        return spec
    block = "\n\n# 相关已验证经验（skills，可直接参考）\n" + "\n\n".join(s.body for s in skills[:3])
    return replace(spec, goal=spec.goal + block)


@dataclass
class EvolveOutcome:
    outcome: VerifiedOutcome
    new_skill: object | None       # Skill | None（passed 才结晶）
    patched: object | None         # Skill | None（用了旧 skill 但没过 → patch）
    recalled: list


async def run_self_evolving(
    mgr,
    spec: TaskSpec,
    *,
    factory,
    on_event,
    can_use_tool,
    verifier,
    synthesizer,
    skill_store,
    project_dir: str,
    max_retries: int = 2,
    env=None,
) -> EvolveOutcome:
    recalled = skill_store.recall(spec.goal)
    spec2 = inject_skills(spec, recalled)                  # 召回注入

    outcome = await dispatch_verified(
        mgr, spec2, factory=factory, on_event=on_event, can_use_tool=can_use_tool,
        verifier=verifier, project_dir=project_dir, max_retries=max_retries, env=env,
    )

    new_skill = patched = None
    if outcome.verdict.passed:
        # 用【原始 spec】结晶（不含注入的旧经验噪声）
        new_skill = await synthesizer.crystallize(spec, outcome.result, outcome.verdict)
        skill_store.save(new_skill)
        for s in recalled:
            skill_store.touch(s)                           # 用到的旧 skill 计数 +1
    elif recalled:
        patched = await synthesizer.patch(recalled[0], spec, outcome.result, outcome.verdict)
        skill_store.save(patched)                          # 用中 patch

    return EvolveOutcome(outcome=outcome, new_skill=new_skill, patched=patched, recalled=recalled)
