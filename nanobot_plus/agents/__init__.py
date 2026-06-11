"""执行层：worker 统一接口 + 生命周期管理。

具体 worker（ClaudeCodeWorker 等）按需从子模块导入，避免在包导入时
强依赖 claude-agent-sdk。
"""

from .base import BaseWorker
from .claude_worker import ClaudeCodeWorker
from .factory import build_claude_factory
from .manager import AgentWorkerManager

__all__ = ["BaseWorker", "AgentWorkerManager", "ClaudeCodeWorker", "build_claude_factory"]
