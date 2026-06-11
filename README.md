# nanobot-plus

A thin **orchestration layer on top of [nanobot](./nanobot)**. nanobot is the
**brain**; nanobot-plus lets that brain command many **isolated, persistent
Claude Code worker sessions** (one per independent project) with
**human-in-the-loop approval**, **independent verification**, and a real
**memory** subsystem.

> Workers run the **Claude Code harness via `ccswitch` → DeepSeek** (not real
> Anthropic). The harness is model-agnostic, so isolation / approval / resume
> all work unchanged; the proxy is injected per worker via `env`.

See **[PLAN.md](./PLAN.md)** for the full plan (phases, modules, risks) and
`nanobot_plus/contracts.py` for the 3 backbone contracts.

## Layout

```
nanobot-plus/
├─ nanobot/                 # vendored base framework (git-ignored; pip install -e ./nanobot)
├─ nanobot_plus/            # this package
│  ├─ contracts.py          # AgentWorker / TaskSpec·WorkerResult / MemoryStore  ← single source of truth
│  ├─ agents/               # execution layer: workers + manager
│  ├─ orchestrator/         # brain layer: protocol, dispatch tool, router, verifier, permission, trace
│  ├─ memory/               # memory layer: store, project text store, blackboard, router, dream_ext
│  ├─ config.py             # project registry + runtime config
│  └─ cli.py                # entry point
└─ spikes/p0_spike.py       # P0 承重墙: prove concurrent persistent workers + approval on ccswitch+DeepSeek
```

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./nanobot          # base framework (brain provider, bus, tools, memory)
pip install claude-agent-sdk      # worker driver
pip install -e .                  # this package
```

## Status

Scaffold only — every module is a stub tied to a PLAN.md phase (`# TODO(Pn)`).
Start at **P0**:

```bash
# set your ccswitch → DeepSeek env first (ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN)
python spikes/p0_spike.py
```

## Note on the vendored `nanobot/`

It currently carries its own `.git` (nested repo) and is git-ignored here. Either
keep depending on it via `pip install -e ./nanobot`, or — to vendor it as plain
files — remove `nanobot/.git` and unignore it. Decide before your first commit.
