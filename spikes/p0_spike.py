"""
P0 承重墙 — 验证 nanobot-plus 的最小核心是否成立（带 PASS/FAIL）。

跑 3 项检查：
  [1] 并发 + cwd 隔离    —— 2 个 worker 各在自己目录写 marker.txt，互不串目录
  [2] 审批拦截           —— deny 写操作 → 文件不该出现；allow → 文件出现
  [3] 持久会话中期记忆   —— 同一会话先告诉它暗号，再让它把暗号写文件，验证它记得

后端：用 Claude Code 默认。base_url / api key / model 由你在 ~/.claude/settings.json
（ccswitch）里自行配置，本脚本不碰、不注入任何 env、不指定 model。

准备：
  python -m venv .venv && source .venv/bin/activate
  pip install claude-agent-sdk          # claude CLI 也要装好
  # 用 ccswitch 配好后端后：
  python spikes/p0_spike.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        PermissionResultAllow,
        PermissionResultDeny,
    )
    try:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
    except ImportError:  # 某些版本类型在 .types 下
        from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock
except ImportError as e:
    sys.exit(f"无法导入 claude-agent-sdk: {e}\n先 `pip install claude-agent-sdk`（claude CLI 也要装好）。")

WORKDIR = Path("/tmp/nbplus_p0")
TASK_TIMEOUT = 180  # 秒 / 每项检查


# ── 审批回调（自动化：不需要人盯着终端）────────────────────────────
async def auto_allow(tool_name, input_data, context):
    return PermissionResultAllow()


async def deny_writes(tool_name, input_data, context):
    if tool_name in {"Write", "Edit", "Bash"}:
        return PermissionResultDeny(message="P0 测试: 拒绝写操作")
    return PermissionResultAllow()


def _opts(cwd, can_use_tool) -> ClaudeAgentOptions:
    # 不设 allowed_tools: 让写操作真正落到 can_use_tool（allow 规则会抢在回调前放行）。
    # 不设 model / env: 走 settings.json 里你配的后端。
    return ClaudeAgentOptions(cwd=str(cwd), permission_mode="default", can_use_tool=can_use_tool)


async def run_task(prompt, *, cwd=None, can_use_tool=auto_allow, client=None):
    """跑一个任务, 收集最终文本 + ResultMessage。client 非空=复用同一持久会话（测中期记忆）。"""
    own = client is None
    if own:
        client = ClaudeSDKClient(options=_opts(cwd, can_use_tool))
        await client.connect()
    parts, result = [], None
    await client.query(prompt)
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            parts += [b.text for b in msg.content if isinstance(b, TextBlock)]
        elif isinstance(msg, ResultMessage):
            result = msg
    if own:
        await client.disconnect()
    return "".join(parts), result


def _read(p: Path) -> str:
    return p.read_text(errors="ignore") if p.exists() else ""


def _snip(s: str) -> str:
    return " ".join(s.split())[:160]


# ── [1] 并发 + cwd 隔离 ─────────────────────────────────────────────
async def check_isolation():
    a, b = WORKDIR / "projA", WORKDIR / "projB"
    for d in (a, b):
        d.mkdir(parents=True, exist_ok=True)
    (ta, _), (tb, _) = await asyncio.gather(
        run_task("创建文件 marker.txt, 内容就写这一行: HELLO_FROM_A", cwd=a),
        run_task("创建文件 marker.txt, 内容就写这一行: HELLO_FROM_B", cwd=b),
    )
    a_ok = "HELLO_FROM_A" in _read(a / "marker.txt")
    b_ok = "HELLO_FROM_B" in _read(b / "marker.txt")
    cross = "HELLO_FROM_B" in _read(a / "marker.txt") or "HELLO_FROM_A" in _read(b / "marker.txt")
    ok = a_ok and b_ok and not cross
    detail = f"A={a_ok} B={b_ok} no_cross={not cross}"
    if not ok:
        detail += f" | A说:{_snip(ta)} | B说:{_snip(tb)}"
    return ok, detail


# ── [2] 审批拦截 ────────────────────────────────────────────────────
async def check_approval():
    d = WORKDIR / "approval"
    d.mkdir(parents=True, exist_ok=True)
    t_deny, _ = await run_task("创建文件 blocked.txt, 内容随便。", cwd=d, can_use_tool=deny_writes)
    denied_ok = not (d / "blocked.txt").exists()
    t_allow, _ = await run_task("创建文件 allowed.txt, 内容写 OK。", cwd=d, can_use_tool=auto_allow)
    allow_ok = (d / "allowed.txt").exists()
    ok = denied_ok and allow_ok
    detail = f"deny_blocks={denied_ok} allow_creates={allow_ok}"
    if not ok:
        detail += f" | deny后:{_snip(t_deny)} | allow后:{_snip(t_allow)}"
    return ok, detail


# ── [3] 持久会话中期记忆 ────────────────────────────────────────────
async def check_midterm_memory():
    d = WORKDIR / "memory"
    d.mkdir(parents=True, exist_ok=True)
    client = ClaudeSDKClient(options=_opts(d, auto_allow))
    await client.connect()
    try:
        _, r1 = await run_task("记住这个暗号: TIGER-7。只回复 OK, 先别做别的。", client=client)
        t2, r2 = await run_task("把我刚才给你的那个暗号写进文件 codeword.txt。", client=client)
    finally:
        await client.disconnect()
    sid = getattr(r2, "session_id", None) or getattr(r1, "session_id", None)
    ok = "TIGER-7" in _read(d / "codeword.txt")
    detail = f"remembered={ok} session_id={sid}"
    if not ok:
        detail += f" | 第二轮说:{_snip(t2)}"
    return ok, detail


CHECKS = [
    ("并发 + cwd 隔离", check_isolation),
    ("审批拦截 (deny/allow)", check_approval),
    ("持久会话中期记忆", check_midterm_memory),
]


async def main():
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)              # 清掉上次残留, 避免假 PASS
    WORKDIR.mkdir(parents=True)
    print(f"P0 承重墙 — {WORKDIR}")
    print("后端: Claude Code 默认（由 ~/.claude/settings.json 决定, 本脚本不碰）\n")

    results = []
    for name, fn in CHECKS:
        print(f"▶ {name} …")
        try:
            ok, detail = await asyncio.wait_for(fn(), TASK_TIMEOUT)
        except asyncio.TimeoutError:
            ok, detail = False, f"超时 (>{TASK_TIMEOUT}s)"
        except Exception as e:  # noqa: BLE001 — spike: 任何异常都算 FAIL 并打印
            ok, detail = False, f"异常 {type(e).__name__}: {e}"
        results.append((name, ok))
        print(f"  {'✅ PASS' if ok else '❌ FAIL'} — {detail}\n")

    print("=" * 52)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    print("=" * 52)
    allok = all(ok for _, ok in results)
    print("承重墙: " + ("全部通过 ✅" if allok else "有未通过 ❌（看 detail; 先确认 settings.json 后端配好）"))
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    asyncio.run(main())
