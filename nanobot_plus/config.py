"""nanobot-plus 配置：项目登记表 + 运行时设置。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectConfig:
    """一个受管项目 = 一个独立目录 + 绑定的 agent + 接入 + 审批默认 + 后端 env。"""

    project_id: str
    path: str                                              # 项目工作目录(隔离单位)
    agent: str = "claude"                                  # claude | codex | gemini | nanobot
    mcp: list[str] = field(default_factory=list)           # 该项目可用的 MCP server
    permission_default: str = "plan"
    backend_env: dict[str, str] = field(default_factory=dict)  # ccswitch env(覆盖全局)


@dataclass
class NanobotPlusConfig:
    projects: list[ProjectConfig] = field(default_factory=list)
    max_concurrent_workers: int = 4                        # 并发上限(防 N×吞吐/速率)
    default_backend_env: dict[str, str] = field(default_factory=dict)  # ccswitch→DeepSeek 全局 env
    # TODO(P1): load/save ~/.nanobot-plus/config.json
