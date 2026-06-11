"""
P3 demo — 自进化循环：结晶 → 召回注入 → curator。

  1) 任务1（首次）自进化跑一遍 → 结晶出一个 skill 入库
  2) 任务2（类似）再跑 → recall 命中刚才的 skill 并注入（recalled 非空）
  3) Curator 老化演示

后端走 ~/.claude/settings.json。准备同 P0/P1/P2。
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nanobot_plus.agents import AgentWorkerManager, build_claude_factory  # noqa: E402
from nanobot_plus.config import ProjectConfig  # noqa: E402
from nanobot_plus.contracts import TaskSpec  # noqa: E402
from nanobot_plus.memory.curator import Curator  # noqa: E402
from nanobot_plus.memory.skill_store import SkillStore  # noqa: E402
from nanobot_plus.memory.skill_synthesizer import SkillSynthesizer  # noqa: E402
from nanobot_plus.orchestrator.permission import PermissionPolicy  # noqa: E402
from nanobot_plus.orchestrator.self_evolve import run_self_evolving  # noqa: E402
from nanobot_plus.orchestrator.verifier import Verifier  # noqa: E402

BASE = Path("/tmp/nbplus_p3")


async def on_event(ev: dict) -> None:
    pass


async def yes(t, i) -> bool:
    return True


async def main() -> None:
    if BASE.exists():
        shutil.rmtree(BASE)
    proj = BASE / "proj"
    proj.mkdir(parents=True)
    projects = {"proj": ProjectConfig(project_id="proj", path=str(proj))}
    factory = build_claude_factory(projects)
    mgr = AgentWorkerManager(max_concurrent=2)
    verifier = Verifier()
    synth = SkillSynthesizer()
    store = SkillStore(proj / ".nbplus" / "skills")
    cut = PermissionPolicy(yes).can_use_tool

    print("▶ 任务1（首次）…")
    s1 = TaskSpec(
        goal="写一个 Python 脚本 add.py：定义 add(a,b) 返回 a+b，并在 __main__ 打印 add(2,3)",
        project_id="proj", permission_mode="default",
        done_criteria=["add.py 存在", "运行 add.py 输出 5"],
    )
    e1 = await run_self_evolving(mgr, s1, factory=factory, on_event=on_event, can_use_tool=cut,
                                 verifier=verifier, synthesizer=synth, skill_store=store, project_dir=str(proj))
    print(f"  verified={e1.outcome.verdict.passed} 新skill={'有' if e1.new_skill else '无'} 库存={len(store.all())}")
    if e1.new_skill:
        print(f"  结晶: {e1.new_skill.name}")

    print("▶ 任务2（类似）→ 看是否召回注入 …")
    s2 = TaskSpec(
        goal="写一个 Python 脚本 mul.py：定义 mul(a,b) 返回 a*b，并在 __main__ 打印 mul(2,3)",
        project_id="proj", permission_mode="default",
        done_criteria=["mul.py 存在", "运行 mul.py 输出 6"],
    )
    e2 = await run_self_evolving(mgr, s2, factory=factory, on_event=on_event, can_use_tool=cut,
                                 verifier=verifier, synthesizer=synth, skill_store=store, project_dir=str(proj))
    print(f"  召回注入 {len(e2.recalled)} 个 skill；verified={e2.outcome.verdict.passed} 库存={len(store.all())}")

    print("▶ Curator 老化演示 …")
    print(f"  {Curator().curate(store)}")

    await mgr.close_all()
    ok = e1.outcome.verdict.passed and (e1.new_skill is not None) and (len(e2.recalled) >= 1)
    print("\nP3:", "✅" if ok else "❌（看上面；先确认后端配好）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
