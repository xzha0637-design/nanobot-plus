"""PermissionPolicy — can_use_tool 的策略层：风险分级 + 记住决策 + 只拦关键步。 [P2]

把 SDK 的 raw can_use_tool 升级成有判断力的守门人。
返回 PermissionResultAllow / PermissionResultDeny（claude_agent_sdk 提供）。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

# 关键步骤(默认要审批)：写 / 执行 / 出网
KEY_TOOLS = {"Write", "Edit", "Bash", "WebFetch"}
LOW_RISK = {"Read", "Grep", "Glob", "LS"}


class PermissionPolicy:
    def __init__(self, ask_human: Callable[[str, dict[str, Any]], Awaitable[bool]]) -> None:
        self._ask = ask_human
        self._remembered: set[str] = set()      # "以后自动放行"的规则键

    def _key(self, tool_name: str, input_data: dict[str, Any]) -> str:
        return tool_name                        # TODO(P2): 细到 Bash(rm *) 这种 scope

    def _risk(self, tool_name: str, input_data: dict[str, Any]) -> str:
        if tool_name in LOW_RISK:
            return "low"
        if tool_name in KEY_TOOLS:
            return "high"
        return "medium"

    async def can_use_tool(self, tool_name: str, input_data: dict[str, Any], context: Any):
        # 延迟导入，避免包导入期强依赖 SDK
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

        if self._risk(tool_name, input_data) == "low" or self._key(tool_name, input_data) in self._remembered:
            return PermissionResultAllow()

        ok = await self._ask(tool_name, input_data)
        if not ok:
            return PermissionResultDeny(message="用户拒绝")
        # TODO(P2): 若用户选"以后总是允许" → self._remembered.add(key)
        #           并用 PermissionResultAllow(updated_permissions=[...]) 落到会话规则。
        return PermissionResultAllow()
