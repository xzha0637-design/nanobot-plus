# nanobot-plus 部署 · 运行 · 测试指南

> 一份从零到跑通的中文手册：**改了什么 → 装什么 → 配后端 → 怎么跑 → 怎么测 → 出错怎么办**。

---

## 一、这是什么

在 [nanobot](./nanobot) 之上加一层**指挥层**。nanobot 是"大脑"，nanobot-plus 让它**指挥一批隔离的、持久的 Claude Code 工作会话**（每个项目一个），并带上**人在环审批**、**独立验证**、**自进化的 skill 记忆**。

数据流：

```
你 / 大脑(nanobot)
      │  下达目标
      ▼
AgentWorkerManager ──get_or_create──► ClaudeCodeWorker（每项目一个持久会话, cwd 隔离, 可 resume=中期记忆）
      │  dispatch                                  │  执行时每个工具调用
      │                                            ▼
      │                                   can_use_tool（审批策略：关键步骤等你点头）
      ▼
dispatch_verified ──► Verifier（全新上下文, 只读, 核对 done_criteria）──► 通过? 
      │                                                                   │是
      │否→带"未满足项"重试(回灌同一持久会话)                                  ▼
                                                          SkillSynthesizer 结晶成可复用 skill
                                                                          ▼
                                                          SkillStore（召回注入下次任务）+ Curator（老化）
```

> **后端**：worker 跑的是 Claude Code 的 harness，模型由你用 **ccswitch** 在 `~/.claude/settings.json` 改成 DeepSeek（Anthropic 兼容）。本项目代码**不碰**后端、不注入 env、不指定 model。

---

## 二、改了什么（P0–P3）

| 阶段 | 加了什么 | 关键文件 |
|---|---|---|
| **P0 承重墙** | 验证器：并发+cwd 隔离 / 审批拦截 / 持久会话中期记忆，带 PASS/FAIL | `spikes/p0_spike.py` |
| **P1 编排 MVP** | `ClaudeCodeWorker`(持久会话) + `AgentWorkerManager` + `DispatchTool` + 工厂 + 边界协议 | `nanobot_plus/agents/*`、`orchestrator/dispatch_tool.py`、`spikes/p1_demo.py` |
| **P2 安全层** | 独立 `Verifier` + `dispatch_verified`(verify→retry 闭环) + `PermissionPolicy` | `orchestrator/verifier.py`、`verified_dispatch.py`、`permission.py`、`spikes/p2_demo.py` |
| **P3 自进化** | `Skill`/`SkillStore`/`Curator`/`SkillSynthesizer` + `run_self_evolving`(结晶→召回注入→patch) | `nanobot_plus/memory/skill*.py`、`curator.py`、`orchestrator/self_evolve.py`、`spikes/p3_demo.py` |

3 个核心契约（一切挂在它们上，见 `nanobot_plus/contracts.py`）：
- **AgentWorker** — 执行层统一接口（持久会话、可 resume）。
- **TaskSpec / WorkerResult** — 大脑↔worker 的窄边界（下行只给指针，上行只给结构化结论）。
- **MemoryStore** — 长期记忆 + 验证晋升闸门。

目录：

```
nanobot-plus/
├─ nanobot/                  # vendored 基座框架（git-ignored；接大脑时才需要装）
├─ nanobot_plus/
│  ├─ contracts.py           # 3 个契约
│  ├─ config.py              # 项目登记表
│  ├─ agents/                # base / claude_worker / cli_worker / nanobot_worker / manager / factory
│  ├─ orchestrator/          # protocol / dispatch_tool / router / verifier / verified_dispatch / permission / self_evolve / trace
│  └─ memory/                # skill / skill_store / curator / skill_synthesizer / store / project_store / blackboard ...
├─ spikes/                   # p0_spike / p1_demo / p2_demo / p3_demo （可运行的端到端验证）
├─ tests/smoke_test.py       # 离线冒烟测试（不需 SDK/后端）
├─ PLAN.md                   # 总体计划（P0–P5 + §4b 自进化）
└─ GUIDE.md                  # 本文件
```

---

## 三、前置依赖

| 依赖 | 说明 | 检查 |
|---|---|---|
| Python ≥ 3.11 | 3.14 实测可用 | `python3 --version` |
| **claude CLI** | Claude Code 命令行（SDK 靠它驱动） | `claude --version` |
| **claude-agent-sdk** | Python 包，驱动 worker 会话 | `python -c "import claude_agent_sdk"` |
| **后端（ccswitch→DeepSeek）** | `~/.claude/settings.json` 配好 base_url/key/model | `claude -p "hi"` 能回话 |

> 跑 4 个 demo **只需**：claude CLI + claude-agent-sdk + 配好的后端。
> `pip install -e ./nanobot`（基座框架）只有等你**把 dispatch 接进 nanobot 大脑**时才需要。

---

## 四、安装部署

```bash
cd nanobot-plus

# 1) 隔离虚拟环境
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2) 装 worker 驱动
pip install claude-agent-sdk

# 3)（可选）装本项目本身，便于 import / 拿到 nanobot-plus 命令
pip install -e .

# 4)（可选，接大脑时再做）装 vendored 基座
pip install -e ./nanobot
```

> vendored 的 `nanobot/` 带自己的 `.git`，已被 `.gitignore` 忽略，不会进你的提交。

---

## 五、配置后端（ccswitch → DeepSeek）

用 **ccswitch** 把 `~/.claude/settings.json` 改成指向 DeepSeek。**字段以 ccswitch 写入为准，下面仅示意**，base_url / key / model 你自己填：

```jsonc
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://<你的-deepseek-anthropic兼容代理>",
    "ANTHROPIC_AUTH_TOKEN": "sk-<你的-deepseek-key>"
  },
  "model": "<你的-deepseek-model-id>"
}
```

配好后先单独验一发 claude CLI 能用：

```bash
claude -p "用一句话回复：ok"
```

能回话，说明后端通了，demo 才有意义。

---

## 六、运行（4 个 spike，每个验一件事）

> 都对你**真实的 ccswitch+DeepSeek 后端**跑。每个脚本结尾打印 PASS/FAIL，exit 0 = 通过。

```bash
source .venv/bin/activate

python spikes/p0_spike.py    # 承重墙：并发+cwd 隔离 / 审批拦截 / 持久会话中期记忆
python spikes/p1_demo.py     # 编排：并发分派两项目, 隔离跑, 结构化回收, 会话复用
python spikes/p2_demo.py     # 验证：dispatch_verified 闭环 + 审批拒绝拦截
python spikes/p3_demo.py     # 自进化：任务1结晶 skill → 任务2召回注入 → curator
```

各自预期：

| 脚本 | 通过时大致输出 | 证明 |
|---|---|---|
| `p0_spike.py` | 三项 `✅ PASS`，结尾"承重墙：全部通过 ✅" | SDK×并发 / cwd 隔离 / can_use_tool 审批 / 中期记忆 + **DeepSeek 后端 tool-use 不崩** |
| `p1_demo.py` | 两项目各 `status=done`，`复用同一会话=True`，"隔离+回收 ✅" | 编排器能分派、隔离、回收结构化结果、续会话 |
| `p2_demo.py` | `verified=True attempts=1...`，`文件未落地(被拦)=True` | 独立验证 + 验证-重试闭环 + 审批真能拦写 |
| `p3_demo.py` | `新skill=有`，`召回注入 ≥1 个 skill`，curator 计数 | 过验才结晶、相似任务召回复用、按用量老化 |

> 失败时脚本会打印 worker 的原话（`detail`），方便区分"DeepSeek tool-use 崩了"还是"模型没照做"。

---

## 七、测试

### 1）离线冒烟测试（**不需 SDK / 不连后端**，秒级）

验全部接线与纯逻辑（工厂/持久复用/dispatch/prompt、verify→retry、skill 序列化/召回/curator/注入/自进化闭环）：

```bash
python tests/smoke_test.py        # exit 0 = 全过
```

顺手做个语法编译检查：

```bash
python -m compileall -q nanobot_plus spikes tests
```

### 2）端到端测试（需 SDK + 后端）

就是上面第六节那 4 个 demo——它们本身就是带断言的端到端测试（exit code 可用于 CI）：

```bash
for s in p0_spike p1_demo p2_demo p3_demo; do
  echo "=== $s ==="; python "spikes/$s.py" || echo "FAILED: $s"
done
```

> 离线冒烟覆盖逻辑正确性；端到端 demo 覆盖"接上真模型后整条链通不通"。两者都过才算稳。

---

## 八、分支 / PR 结构

代码分阶段提交，方便逐段审核：

| PR | 分支 | base | 内容 |
|---|---|---|---|
| P0 | `feat/p0-harness` | `main` | 承重墙验证器 |
| P1 | `feat/p1-orchestration` | `main` | 编排 MVP + 自进化 plan |
| P2 | `feat/p2-verification` | `feat/p1-orchestration` | 验证闭环 + 审批策略 |
| P3 | `feat/p3-self-evolution` | `feat/p2-verification` | 自进化 |
| — | **`integration`** | — | **把上面全部合到一起：想一次性跑全套就用这个分支** |

- **审核合并顺序**：`p0`（独立）→ `p1 → p2 → p3`。
- **想直接跑全套**：`git checkout integration`（已含 P0–P3 + 本指南 + 冒烟测试）。

```bash
git checkout integration
python -m venv .venv && source .venv/bin/activate
pip install claude-agent-sdk
python tests/smoke_test.py        # 先离线验
# 配好后端后：
python spikes/p0_spike.py
```

---

## 九、故障排查

| 现象 | 多半原因 / 处理 |
|---|---|
| `ModuleNotFoundError: claude_agent_sdk` | `pip install claude-agent-sdk`（且在 venv 里） |
| `claude: command not found` | 没装 Claude Code CLI / 不在 PATH |
| demo 卡住或超时 | 后端没配通；先 `claude -p "hi"` 验；p0 有 180s/项超时 |
| p0/demo 里写操作没发生、模型只"说计划" | `permission_mode` 用了 `plan`（只规划不动手）；demo 已用 `default` |
| 审批测试"假通过"（deny 了还是建了文件） | 别给 worker 设 `allowed_tools`（allow 规则会抢在 can_use_tool 前放行） |
| 中期记忆没生效 | 确认是**同一个 worker 对象**多次 `send`（manager 持久复用），不是每次新建 |
| skill 召回不准 | 当前是关键词重叠、中文切得粗；后续上 FTS/embedding |
| `import nanobot_plus` 失败 | 用 `pip install -e .`，或运行时设 `PYTHONPATH=<repo根>`（demo/测试已自动插 path） |

---

## 十、还没做的 / 后续路线

- **P1 收尾**：把 `DispatchTool` 注册进 nanobot 的工具注册表 + AgentLoop，让 LLM 大脑自己调（现在 demo 是手动调 dispatch 模拟大脑）。
- **跨项目共享池 + 验证晋升**：现在 skill 是项目私有；把过验 skill `promote` 进 shared 池（接 `MemoryStore.promote` 的 `verified_by` 闸门）——完成多 agent 自进化。
- **P2.5**：plan→批→acceptEdits 动态切换；审批决策落到 SDK 会话规则（`updated_permissions`）。
- **P4 驾驶舱 UI**：Electron 多栏 + 实时流 + 点击审批。
- **召回升级**：FTS5 / embedding 取代关键词重叠。

详见 [PLAN.md](./PLAN.md)。
