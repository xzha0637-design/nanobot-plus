"""
P0 承重墙 spike — 一次性验掉最不确定的三件事：
  1) 多个持久 ClaudeSDKClient 并发，各自 cwd 隔离
  2) can_use_tool 能拦住关键(写)操作、等人审批
  3) 经 ccswitch 把 harness 接到 DeepSeek 后，tool-use 这条链不崩

重要：对你真实的 ccswitch + DeepSeek 跑，别拿真 Claude 验完就当成了。

准备：
  pip install claude-agent-sdk
  export ANTHROPIC_BASE_URL=...     # ccswitch 代理地址
  export ANTHROPIC_AUTH_TOKEN=...   # DeepSeek key
  python spikes/p0_spike.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
)

# ccswitch → DeepSeek：把 Claude Code harness 指向兼容代理
CCSWITCH_ENV = {
    "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL", ""),      # TODO 必填
    "ANTHROPIC_AUTH_TOKEN": os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),  # TODO 必填
}

KEY_TOOLS = {"Write", "Edit", "Bash"}   # 关键步骤：写 / 执行才拦


async def approve(tool_name, input_data, context):
    """人在环：关键操作前在终端等 y/N。"""
    if tool_name in KEY_TOOLS:
        preview = str(input_data)[:140]
        print(f"\n  ⏸  申请使用 {tool_name}: {preview}")
        loop = asyncio.get_event_loop()
        ans = await loop.run_in_executor(None, input, "     批准? [y/N] ")
        if ans.strip().lower() != "y":
            return PermissionResultDeny(message="用户拒绝")
    return PermissionResultAllow()


def _text_of(msg) -> str:
    """兼容不同消息类型，尽量取出文本。"""
    if getattr(msg, "result", None):
        return str(msg.result)
    content = getattr(msg, "content", None)
    if isinstance(content, list):
        return "".join(getattr(b, "text", "") or "" for b in content)
    return ""


async def run_worker(name: str, project_dir: str, task: str) -> None:
    Path(project_dir).mkdir(parents=True, exist_ok=True)
    opts = ClaudeAgentOptions(
        cwd=project_dir,            # ← 隔离：每项目独立目录
        permission_mode="default",  # 写操作落到 can_use_tool
        can_use_tool=approve,       # ← 人在环
        env=CCSWITCH_ENV,           # ← 路由到 DeepSeek
    )
    async with ClaudeSDKClient(options=opts) as client:
        await client.query(task)
        async for msg in client.receive_response():
            text = _text_of(msg)
            if text:
                print(f"[{name}] {text[:200]}")
    print(f"[{name}] ✅ done (cwd={project_dir})")


async def main() -> None:
    if not CCSWITCH_ENV["ANTHROPIC_BASE_URL"]:
        print("⚠️  先设好 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN (ccswitch→DeepSeek)\n")
    base = "/tmp/nbplus_p0"
    await asyncio.gather(
        run_worker("projA", f"{base}/projA", "在 README.md 写一行：hello from A"),
        run_worker("projB", f"{base}/projB", "在 notes.txt 写一行：hello from B"),
    )
    print("\n两个 worker 并发、各自独立目录、写操作经过审批 —— 到这没崩即承重墙通过。")


if __name__ == "__main__":
    asyncio.run(main())
