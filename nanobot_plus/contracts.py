"""
nanobot-plus — 3 个骨架契约（单一事实源 / canonical）

后面所有模块都挂在这三个契约上：
  1) AgentWorker            执行层：Claude Code / Codex / nanobot 统一长一个样
  2) TaskSpec/WorkerResult  边界协议：刻意做窄，决定"上下文隔离"的真正含金量
  3) MemoryStore            记忆层：三层记忆 + 验证晋升闸门

关键设计（源自"持久会话 / ccswitch+DeepSeek"两点）：
  - Worker 默认是【每项目一个持久、可 resume 的会话】= 中期记忆，不是 fire-and-forget。
  - 通过 `env` 按 worker 注入 ccswitch 的 ANTHROPIC_BASE_URL+token，把 harness 路由到 DeepSeek。
  - `can_use_tool` 签名直接对齐 Claude Agent SDK，方便 ClaudeCodeWorker 透传。

这是 spec：Protocol 体一律 `...`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Protocol, runtime_checkable

# ── 2) 边界协议 ──────────────────────────────────────────────────────


@dataclass
class TaskSpec:
    """大脑 → worker。窄，是为了不互相污染上下文。"""

    goal: str
    project_id: str                                            # 路由到哪个项目/持久会话
    context_refs: list[str] = field(default_factory=list)      # 只给指针(文件/规范/记忆id)，不灌全文
    done_criteria: list[str] = field(default_factory=list)     # 可验证判据 → 原样交给 Verifier
    allowed_mcp: list[str] = field(default_factory=list)       # 本任务可用的 MCP server 名
    permission_mode: Literal[
        "plan", "default", "acceptEdits", "bypassPermissions", "dontAsk"
    ] = "plan"                                                 # 默认 plan→批→acceptEdits
    session_id: str | None = None                             # 非空=续会话(中期记忆); None=新会话


@dataclass
class WorkerResult:
    """worker → 大脑。压缩后的结论，不是过程。"""

    status: Literal["done", "blocked", "failed"]
    summary: str                                              # 压缩摘要，不是 transcript
    artifacts: list[str] = field(default_factory=list)        # 改了哪些文件 / 产出
    evidence: str = ""                                        # 凭什么说做完：测试/diff 摘要
    open_questions: list[str] = field(default_factory=list)
    session_id: str = ""                                      # 本次会话 id → 下次 resume 锚点
    usage: dict[str, Any] = field(default_factory=dict)       # token/成本，按 worker 归因


# 与 Claude Agent SDK 对齐
PermissionResult = Any            # PermissionResultAllow | PermissionResultDeny（SDK 提供）
ToolPermissionContext = Any       # SDK 提供：suggestions / blocked_path / decision_reason
CanUseTool = Callable[[str, dict[str, Any], ToolPermissionContext], Awaitable[PermissionResult]]
EventSink = Callable[[dict[str, Any]], Awaitable[None]]       # 流式事件喂 UI / trace


@dataclass
class WorkerCapabilities:
    """后端能力不齐 → 适配层据此优雅降级。"""

    native_approval: bool = True      # 支持 can_use_tool（Claude Code: 是）
    resumable: bool = True            # 支持 resume（中期记忆）
    mcp: bool = True
    streaming: bool = True


# ── 1) AgentWorker ───────────────────────────────────────────────────


@runtime_checkable
class AgentWorker(Protocol):
    """
    一个 worker 绑定一个 project，内部持有可 resume 的持久会话(中期记忆)。
    同一 worker 可被多次 send，会话上下文在多次 send 间保留——这正是
    "用持久 Claude Code 窗口追踪项目进度"的程序化形态。
    一次性 fan-out = 建一个、send 一次、close。
    """

    project_id: str
    session_id: str | None
    capabilities: WorkerCapabilities

    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,   # ← 注入 ccswitch: ANTHROPIC_BASE_URL / token
    ) -> WorkerResult: ...

    async def interrupt(self) -> None: ...   # 卡死时打断（SDK client.interrupt()）

    async def close(self) -> None: ...


# ── 3) MemoryStore ───────────────────────────────────────────────────
#   short-term  一次 send 的工作记忆       → worker 上下文承载，不入库
#   mid-term    持久会话(session_id,resume)→ AgentWorker 承载，有界且压缩有损
#   long-term   本 Store                   → 文本优先(E2)+分层(E4)+协调黑板(E3)

Scope = Literal["project", "shared", "operator"]   # 私有项目 / 共享经验池 / 用户偏好
MemKind = Literal["semantic", "episodic", "procedural"]


@dataclass
class Provenance:
    worker_id: str
    project_id: str
    session_id: str
    task_goal: str
    ts: str                            # 时间戳由调用方注入


@dataclass
class MemoryItem:
    kind: MemKind
    scope: Scope
    scope_id: str                      # project_id / "shared" / "operator"
    text: str                          # 文本优先：透明/可审计/可人工编辑/可 git
    provenance: Provenance
    verified_by: str | None = None     # verifier id；None=未验证(禁止晋升)
    id: str = ""


@runtime_checkable
class MemoryStore(Protocol):

    def write(self, item: MemoryItem) -> str: ...

    def recall(self, query: str, *, scope: Scope, scope_id: str, k: int = 8) -> list[MemoryItem]: ...

    def promote(self, item_id: str, *, verified_by: str) -> None:
        """【唯一晋升入口】已验证才晋升到 shared 经验池。未带 verified_by 拒绝——挡综述 M3。"""
        ...

    def consolidate(self, project_id: str) -> None:
        """Dream 扩展：episodic → semantic 巩固（去噪/合并冲突）。"""
        ...

    def context_pack(self, goal: str, *, project_id: str, budget_tokens: int) -> list[str]:
        """为新 send 组装 context_refs：召回 + 项目地图指针，受 token 预算裁剪。返回指针不是全文。"""
        ...
