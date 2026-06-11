"""Dream 扩展 — episodic→semantic 巩固，按项目/agent 分层。 [P3]

复用/扩展 nanobot 的 Dream 两阶段记忆(nanobot/nanobot/agent/memory.py)：
  - 加 per-project / per-agent 维度
  - 巩固出的 semantic 走 Verifier→promote 才进共享池
"""

from __future__ import annotations

# TODO(P3): from nanobot.agent.memory import ...  # 接 Dream，包一层分项目/分 agent。
