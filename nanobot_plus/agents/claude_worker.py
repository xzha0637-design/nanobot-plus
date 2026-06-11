"""ClaudeCodeWorker — 每项目一个持久 ClaudeSDKClient 会话；中期记忆靠它续。

SDK 全部惰性导入（方法内 import），所以本模块不装 claude-agent-sdk 也能 import，
只有真正 send() 时才需要 SDK + claude CLI + 你配好的后端。
"""

from __future__ import annotations

import asyncio
from typing import Any

from .base import BaseWorker
from ..contracts import CanUseTool, EventSink, TaskSpec, WorkerCapabilities, WorkerResult

_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _render(spec: TaskSpec) -> str:
    """TaskSpec → 给 worker 的 prompt。窄：goal + 指针 + 完成判据。"""
    parts = [spec.goal]
    if spec.context_refs:
        parts.append("\n相关上下文（按需自己读，不必全看）:\n" + "\n".join(f"- {r}" for r in spec.context_refs))
    if spec.done_criteria:
        parts.append("\n完成判据（满足才算做完）:\n" + "\n".join(f"- {c}" for c in spec.done_criteria))
    return "\n".join(parts)


def _event(msg: Any) -> dict:
    ev = {"type": type(msg).__name__}
    txt = getattr(msg, "result", None)
    if txt:
        ev["text"] = str(txt)[:200]
    return ev


class ClaudeCodeWorker(BaseWorker):
    capabilities = WorkerCapabilities(native_approval=True, resumable=True, mcp=True, streaming=True)

    def __init__(self, project_id: str, cwd: str, *, model: str | None = None, mcp_servers: dict | None = None) -> None:
        super().__init__(project_id)
        self.cwd = str(cwd)                 # ← cwd 隔离
        self.model = model                  # 一般为 None：模型由你的 settings.json 决定
        self._mcp_all = mcp_servers or {}   # name -> server config（按 spec.allowed_mcp 取子集）
        self._client = None                 # 持久 ClaudeSDKClient（复用=中期记忆）
        self._lock = asyncio.Lock()         # 同一会话不并发

    def _build_options(self, spec: TaskSpec, can_use_tool: CanUseTool, env: dict | None):
        from claude_agent_sdk import ClaudeAgentOptions
        kwargs: dict[str, Any] = dict(
            cwd=self.cwd,
            permission_mode=spec.permission_mode,
            can_use_tool=can_use_tool,
        )
        if self.model:
            kwargs["model"] = self.model
        if env:
            kwargs["env"] = env                       # ccswitch（一般用不到，后端走 settings.json）
        resume_id = spec.session_id or self.session_id
        if resume_id:
            kwargs["resume"] = resume_id              # 重建会话时续中期记忆
        servers = {n: self._mcp_all[n] for n in spec.allowed_mcp if n in self._mcp_all}
        if servers:
            kwargs["mcp_servers"] = servers
        return ClaudeAgentOptions(**kwargs)

    async def _ensure_client(self, spec: TaskSpec, can_use_tool: CanUseTool, env: dict | None):
        if self._client is None:
            from claude_agent_sdk import ClaudeSDKClient
            self._client = ClaudeSDKClient(options=self._build_options(spec, can_use_tool, env))
            await self._client.connect()
        return self._client

    async def send(
        self,
        spec: TaskSpec,
        *,
        on_event: EventSink,
        can_use_tool: CanUseTool,
        env: dict[str, str] | None = None,
    ) -> WorkerResult:
        from claude_agent_sdk import AssistantMessage, ResultMessage
        try:
            from claude_agent_sdk import TextBlock, ToolUseBlock
        except ImportError:
            from claude_agent_sdk.types import TextBlock, ToolUseBlock

        async with self._lock:                       # 持久会话串行
            client = await self._ensure_client(spec, can_use_tool, env)
            await client.query(_render(spec))

            texts: list[str] = []
            artifacts: list[str] = []
            result = None
            async for msg in client.receive_response():
                await on_event(_event(msg))
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            texts.append(b.text)
                        elif isinstance(b, ToolUseBlock) and b.name in _WRITE_TOOLS:
                            inp = b.input or {}
                            fp = inp.get("file_path") or inp.get("notebook_path")
                            if fp:
                                artifacts.append(fp)
                elif isinstance(msg, ResultMessage):
                    result = msg

            if result is not None and getattr(result, "session_id", None):
                self.session_id = result.session_id   # 中期记忆锚点

            return self._to_result(texts, artifacts, result)

    def _to_result(self, texts: list[str], artifacts: list[str], result: Any) -> WorkerResult:
        summary = (getattr(result, "result", None) or "".join(texts) or "").strip()
        status = "failed" if (result is None or getattr(result, "is_error", False)) else "done"
        usage = {"usd": getattr(result, "total_cost_usd", None)}
        usage.update(getattr(result, "usage", None) or {})
        denials = getattr(result, "permission_denials", None)
        if denials:
            usage["permission_denials"] = len(denials)
        return WorkerResult(
            status=status,
            summary=summary[:4000],
            artifacts=sorted(set(artifacts)),
            evidence="",                              # P2 verifier 再填实证
            session_id=self.session_id or "",
            usage=usage,
        )

    async def interrupt(self) -> None:
        if self._client is not None:
            await self._client.interrupt()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None                       # session_id 保留，便于日后 resume
