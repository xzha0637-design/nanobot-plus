"""
P2 demo — 审批策略 + 独立验证 + verify→retry 闭环。

  Case 1: 清晰任务 → dispatch_verified → 打印 status / verified / attempts
  Case 2: 审批拒绝写操作 → 任务被拦, 文件不落地

后端走你的 ~/.claude/settings.json。准备同 P0/P1。
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
from nanobot_plus.orchestrator.permission import PermissionPolicy  # noqa: E402
from nanobot_plus.orchestrator.verified_dispatch import dispatch_verified  # noqa: E402
from nanobot_plus.orchestrator.verifier import Verifier  # noqa: E402

BASE = Path("/tmp/nbplus_p2")


async def on_event(ev: dict) -> None:
    pass


async def yes(t, i) -> bool:
    return True


async def no(t, i) -> bool:
    return False


async def main() -> None:
    if BASE.exists():
        shutil.rmtree(BASE)
    projects: dict[str, ProjectConfig] = {}
    for pid in ("ok", "deny"):
        (BASE / pid).mkdir(parents=True)
        projects[pid] = ProjectConfig(project_id=pid, path=str(BASE / pid))
    factory = build_claude_factory(projects)
    mgr = AgentWorkerManager(max_concurrent=4)
    verifier = Verifier()

    # Case 1: 清晰任务，跑 verify→retry 闭环
    print("▶ Case 1: dispatch_verified（清晰任务）…")
    spec = TaskSpec(
        goal="创建 report.md, 写一句: done by p2", project_id="ok",
        permission_mode="default",
        done_criteria=["report.md 存在", "report.md 含 'done by p2'"],
    )
    out = await dispatch_verified(
        mgr, spec, factory=factory, on_event=on_event,
        can_use_tool=PermissionPolicy(yes).can_use_tool,
        verifier=verifier, project_dir=projects["ok"].path,
    )
    print(f"  status={out.result.status} verified={out.verdict.passed} "
          f"attempts={out.attempts} missing={out.verdict.missing}")

    # Case 2: 审批拒绝写 → 拦截
    print("▶ Case 2: 审批拒绝写操作 …")
    spec2 = TaskSpec(goal="创建 should_not_exist.txt", project_id="deny", permission_mode="default")
    r2 = await mgr.dispatch_to(
        spec2, factory=factory, on_event=on_event,
        can_use_tool=PermissionPolicy(no).can_use_tool,
    )
    blocked = not (Path(projects["deny"].path) / "should_not_exist.txt").exists()
    print(f"  status={r2.status} 文件未落地(被拦)={blocked}")

    await mgr.close_all()
    ok = out.verdict.passed and blocked
    print("\nP2:", "✅" if ok else "❌（看上面；先确认后端配好）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
