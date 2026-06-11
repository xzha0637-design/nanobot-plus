"""编排层：边界协议、路由、dispatch 工具、验证、审批策略、trace。"""

from .permission import PermissionPolicy
from .protocol import TaskSpec, WorkerResult
from .self_evolve import EvolveOutcome, inject_skills, run_self_evolving
from .verified_dispatch import VerifiedOutcome, dispatch_verified
from .verifier import Verdict, Verifier

__all__ = [
    "TaskSpec", "WorkerResult", "Verifier", "Verdict", "PermissionPolicy",
    "dispatch_verified", "VerifiedOutcome",
    "run_self_evolving", "EvolveOutcome", "inject_skills",
]
