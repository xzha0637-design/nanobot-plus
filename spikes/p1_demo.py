"""
P1 demo — 不接 nanobot 大脑, 直接驱动 manager + dispatch 证明编排可用。

验:
  - 配 2 个独立项目, 并发分派任务, 隔离跑, 回收结构化 WorkerResult
  - 给 alpha 发第二个任务, 证明【中期记忆 + 会话复用】(同一 session_id)

后端走你的 ~/.claude/settings.json。
准备同 P0: pip install claude-agent-sdk, 配好后端, 然后 python spikes/p1_demo.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 让脚本能 import nanobot_plus

from nanobot_plus.agents import AgentWorkerManager, build_claude_factory  # noqa: E402
from nanobot_plus.config import ProjectConfig  # noqa: E402
from nanobot_plus.contracts import TaskSpec  # noqa: E402
from nanobot_plus.orchestrator.permission import PermissionPolicy  # noqa: E402

BASE = Path("/tmp/nbplus_p1")


async def on_event(ev: dict) -> None:
    pass  # 接 UI/trace 的地方; demo 先吞掉


async def always_yes(tool_name, input_data) -> bool:
    return True  # 演示: 自动批准（真实用人在环）


def _spec(pid: str, goal: str, *, mode: str = "default", **kw) -> TaskSpec:
    # mode=default: 写操作落到 can_use_tool 并真正执行（plan 模式只会出计划不动手）
    return TaskSpec(goal=goal, project_id=pid, permission_mode=mode, **kw)


async def main() -> None:
    if BASE.exists():
        shutil.rmtree(BASE)
    projects: dict[str, ProjectConfig] = {}
    for pid in ("alpha", "beta"):
        (BASE / pid).mkdir(parents=True)
        projects[pid] = ProjectConfig(project_id=pid, path=str(BASE / pid))

    factory = build_claude_factory(projects)
    mgr = AgentWorkerManager(max_concurrent=4)
    cut = PermissionPolicy(ask_human=always_yes).can_use_tool

    # 1) 并发分派给两个独立项目
    specs = [
        _spec("alpha", "创建文件 hello.txt, 内容就一行: I am alpha",
              done_criteria=["hello.txt 存在且含 'I am alpha'"]),
        _spec("beta", "创建文件 hello.txt, 内容就一行: I am beta",
              done_criteria=["hello.txt 存在且含 'I am beta'"]),
    ]
    print("▶ 并发分派 alpha / beta …")
    results = await asyncio.gather(*[
        mgr.dispatch_to(s, factory=factory, on_event=on_event, can_use_tool=cut) for s in specs
    ])
    for s, r in zip(specs, results):
        print(f"  [{s.project_id}] status={r.status} artifacts={r.artifacts} "
              f"session={r.session_id[:8]}… summary={r.summary[:50]!r}")

    # 2) 给 alpha 发第二个任务（同一持久会话）→ 验中期记忆 + 会话复用
    print("▶ 给 alpha 追加第二个任务（验中期记忆 + session 复用）…")
    r2 = await mgr.dispatch_to(
        _spec("alpha", "在你刚才建的那个文件后面再追加一行: again"),
        factory=factory, on_event=on_event, can_use_tool=cut,
    )
    same = bool(r2.session_id) and r2.session_id == results[0].session_id
    print(f"  [alpha#2] status={r2.status} session={r2.session_id[:8]}… 复用同一会话={same}")

    await mgr.close_all()

    # 文件层面校验隔离 + 落地
    pa, pb = BASE / "alpha" / "hello.txt", BASE / "beta" / "hello.txt"
    a = pa.read_text(errors="ignore") if pa.exists() else ""
    b = pb.read_text(errors="ignore") if pb.exists() else ""
    iso = "I am alpha" in a and "I am beta" in b and "beta" not in a and "alpha" not in b
    mem = "again" in a
    print("\n隔离+回收:", "✅" if iso else "❌", "| 中期记忆(again 落地):", "✅" if mem else "❌")
    sys.exit(0 if (iso and mem and same) else 1)


if __name__ == "__main__":
    asyncio.run(main())
