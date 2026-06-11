"""离线冒烟测试 —— 不需 claude-agent-sdk / 不连后端，验 P1/P2/P3 的接线与纯逻辑。

跑:  python tests/smoke_test.py     (exit 0 = 全过)
真实端到端验证见 spikes/p0..p3_demo.py（需 SDK + 你的后端）。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nanobot_plus.agents import AgentWorkerManager, ClaudeCodeWorker, build_claude_factory
from nanobot_plus.agents.claude_worker import _render
from nanobot_plus.config import ProjectConfig
from nanobot_plus.contracts import TaskSpec, WorkerCapabilities, WorkerResult
from nanobot_plus.memory import Curator, Skill, SkillStore, SkillSynthesizer
from nanobot_plus.memory.skill import from_markdown, to_markdown
from nanobot_plus.orchestrator import dispatch_verified, inject_skills, run_self_evolving
from nanobot_plus.orchestrator.dispatch_tool import DispatchTool
from nanobot_plus.orchestrator.verifier import Verdict

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}")


class FakeWorker:
    def __init__(self, pid):
        self.project_id = pid
        self.session_id = "s"
        self.capabilities = WorkerCapabilities()

    async def send(self, spec, *, on_event, can_use_tool, env=None):
        return WorkerResult(status="done", summary="ok", artifacts=["out.py"], session_id="s")

    async def interrupt(self):
        pass

    async def close(self):
        pass


async def _oe(e):
    pass


async def _cut(n, i, c):
    pass


async def main() -> None:
    print("nanobot-plus 离线冒烟测试\n")
    mgr = AgentWorkerManager(max_concurrent=2)

    # ---- P1: 工厂 / 持久复用 / dispatch 工具 / prompt 渲染 ----
    f = build_claude_factory({"a": ProjectConfig(project_id="a", path="/tmp/x")})
    w = f("a")
    check("P1 factory→ClaudeCodeWorker(cwd 隔离)", isinstance(w, ClaudeCodeWorker) and w.cwd == "/tmp/x")
    check("P1 manager 持久复用同一 worker", mgr.get_or_create("a", f) is mgr.get_or_create("a", f))
    dt = DispatchTool(mgr, factory=f, on_event=_oe, can_use_tool=_cut)
    check("P1 dispatch 工具 schema", dt.name == "dispatch" and "project_id" in dt.parameters["properties"])
    r = _render(TaskSpec(goal="X", project_id="a", context_refs=["a.py"], done_criteria=["pass"]))
    check("P1 prompt 渲染(goal/指针/判据)", "X" in r and "a.py" in r and "pass" in r)

    # ---- P2: verify→retry 闭环 ----
    class FailThenPass:
        def __init__(self):
            self.n = 0

        async def verify(self, spec, res, pd):
            self.n += 1
            return Verdict(passed=self.n >= 2, missing=[] if self.n >= 2 else ["缺X"])

    o = await dispatch_verified(mgr, TaskSpec(goal="g", project_id="p"), factory=lambda p: FakeWorker("p"),
                                on_event=_oe, can_use_tool=_cut, verifier=FailThenPass(),
                                project_dir="/tmp", max_retries=2)
    check("P2 verify→retry: 失败重试后通过(attempts=2)", o.attempts == 2 and o.verdict.passed)

    class AlwaysFail:
        async def verify(self, spec, res, pd):
            return Verdict(passed=False, missing=["永远缺"])

    o2 = await dispatch_verified(mgr, TaskSpec(goal="g2", project_id="q"), factory=lambda p: FakeWorker("q"),
                                 on_event=_oe, can_use_tool=_cut, verifier=AlwaysFail(),
                                 project_dir="/tmp", max_retries=2)
    check("P2 retry 用尽放弃(attempts=3, 未过)", o2.attempts == 3 and not o2.verdict.passed)

    # ---- P3: skill 模型 / store / curator / inject / 自进化闭环 ----
    s = Skill(name="加法", body="# 加法\n## 步骤\nx", use_count=2, source_goal="写 add")
    rt = from_markdown(to_markdown(s))
    check("P3 skill 序列化往返", rt.name == "加法" and rt.use_count == 2 and "## 步骤" in rt.body)

    clock = [1000.0]
    st = SkillStore(tempfile.mkdtemp(), clock=lambda: clock[0])
    st.save(Skill(name="python 加法脚本", body="def add", source_goal="写 python 脚本 add 返回 a+b"))
    st.save(Skill(name="读 csv", body="pandas", source_goal="读取 csv 文件"))
    rec = st.recall("写一个 python 脚本做乘法 mul 返回")
    check("P3 store 召回命中相关 skill", bool(rec) and rec[0].name == "python 加法脚本")
    b = rec[0].use_count
    st.touch(rec[0])
    check("P3 touch 用量计数", st.recall("python 脚本")[0].use_count == b + 1)
    clock[0] = 1000.0 + 100 * 86400
    cnt = Curator(clock=lambda: clock[0]).curate(st)
    check("P3 curator 老化(100天→archived)", cnt["archived"] >= 1)
    inj = inject_skills(TaskSpec(goal="做X", project_id="p"), [Skill(name="经验", body="步骤ABC")])
    check("P3 召回注入(不改原 spec)", "步骤ABC" in inj.goal)

    async def canned(prompt):
        return "# Sum helper\n## 步骤\n1. 定义函数\n## 验证\n运行"

    class Pass:
        async def verify(self, spec, res, pd):
            return Verdict(passed=True)

    store = SkillStore(tempfile.mkdtemp())
    synth = SkillSynthesizer(run_agent=canned)
    fw2 = FakeWorker("p")
    e1 = await run_self_evolving(mgr, TaskSpec(goal="写 python 脚本 add 返回 a+b", project_id="p", done_criteria=["x"]),
                                 factory=lambda p: fw2, on_event=_oe, can_use_tool=_cut, verifier=Pass(),
                                 synthesizer=synth, skill_store=store, project_dir="/tmp")
    e2 = await run_self_evolving(mgr, TaskSpec(goal="写 python 脚本 mul 返回 a*b", project_id="p", done_criteria=["x"]),
                                 factory=lambda p: fw2, on_event=_oe, can_use_tool=_cut, verifier=Pass(),
                                 synthesizer=synth, skill_store=store, project_dir="/tmp")
    check("P3 自进化闭环(结晶→召回注入)", bool(e1.new_skill) and len(e2.recalled) >= 1)

    print(f"\n{'=' * 44}\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("未过:", FAIL)
    sys.exit(0 if not FAIL else 1)


if __name__ == "__main__":
    asyncio.run(main())
