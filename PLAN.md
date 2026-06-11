# nanobot-plus 总体计划

> 独立包，**依赖 nanobot 而不 fork**。用 nanobot 当**编排大脑**，手下管一批**持久的外部
> CLI agent 会话**（Claude Code 经 ccswitch 接 DeepSeek 等），每个 worker 钉在**一个独立项目
> 目录**上做上下文隔离，**关键步骤停下来等人审批**，所有产出**经验证才算完成、才进记忆**。

场景锚点：**并行推进多个独立项目**。护城河：**编排智能 + 协调 + 验证 + 记忆**，不在"代码索引"。

契约见 `nanobot_plus/contracts.py`；承重墙可运行雏形见 `spikes/p0_spike.py`。

---

## 0. 运行底座（重要前提）

- **形态**：独立 git 仓库 `nanobot-plus/`，内含 vendored 的 `nanobot/`（git-ignored；`pip install -e ./nanobot`）。代码命名空间 `nanobot_plus`。
- **Worker 模型不是真 Anthropic**：用 **ccswitch** 让 Claude Code 的 harness 接 **DeepSeek**（Anthropic 兼容代理）。
- **架构无关**：`cwd` 隔离 / `can_use_tool` 审批 / `permission_mode` / `resume` / `mcp_servers` 都是 harness 级能力，换模型不影响。
- **唯一硬集成点**：把 ccswitch 的 `ANTHROPIC_BASE_URL`+token 通过 `ClaudeAgentOptions.env` **按 worker 注入**。
- **大脑独立**：orchestrator 用 nanobot 原生 DeepSeek provider，不走 ccswitch。
- **三个连锁影响**：① 成本墙拆除 → 约束变成"代理吞吐/速率"；② 工具调用可靠性下降 → 验证闭环(P2)更不可省；③ 上下文窗口更小 → 中期记忆更快填满 → 长期记忆层(P3)更不可省。

---

## 1. 三条贯穿原则

1. **复用优先** —— 加一层 + 几处改写，不重写 nanobot。
2. **协议为骨** —— 钉死 3 个契约：`AgentWorker` / `TaskSpec`·`WorkerResult` / `MemoryStore`。
3. **验证晋升** —— 没被 verifier 确认的东西，不算完成、不进长期/共享记忆。

---

## 2. 记忆三层模型

| 层 | 载体 | 生命周期 | 谁负责 |
|---|---|---|---|
| 短期 / 工作记忆 | 单次 `send` 的上下文 | 一个任务 | worker 自身 |
| **中期记忆** | **持久会话** `session_id` + `resume` | 跨多次 send，直到被压缩/丢失 | **ClaudeCodeWorker：每项目一个长驻会话** |
| 长期记忆 | MemoryStore（文本 E2 + Dream + 共享池 E4 + 协调黑板 E3） | 永久，跨会话/项目 | 记忆层 + 验证晋升 |

每项目目录内 `.nbplus/`：`core.md`/`facts.md`(semantic) · `episodes.jsonl`(episodic) · `playbooks/`(procedural)。
编排器全局 sqlite/轻图：协调黑板(E3) + shared 经验池(只收已验证+带来源) + router。

---

## 3. 阶段路线图

| 阶段 | 目标 | 关键交付物 | 验收标准（可验证） | 依赖 |
|---|---|---|---|---|
| **P0 承重墙 spike** | 证明核心可行（**对真实 ccswitch+DeepSeek**） | `spikes/p0_spike.py`：N 个持久 client 并发、各自 cwd、can_use_tool 接控制台、注入 env | 2 项目并行跑通、写操作被审批拦住、tool-use 在 DeepSeek 后端不崩 | claude-agent-sdk + ccswitch |
| **P1 编排 MVP** | 端到端编排进 nanobot | AgentWorker + ClaudeCodeWorker(持久会话) + Manager + dispatch 工具 + 协议 | 大脑下"分派到项目甲/乙"，两 worker 隔离跑、结构化结果回收、会话可 resume | P0 |
| **P2 人在环 + 验证** | 安全且正确 | PermissionPolicy(plan→批→acceptEdits) + Verifier + 重试/卡死检测 | 危险操作必被拦、错误结果被打回、卡死能 interrupt | P1 |
| **P3 记忆 + 自进化** | 复利 / 自进化 | FileMemoryStore + 每项目文本库 + Dream 扩展 + 验证晋升 + 协调黑板 + **自进化循环(见 §4b)** | 跨会话召回事实、错误经验进不了共享池、**skill 从验证过的经验自动结晶并复用** | P1（晋升门依赖 P2） |
| **P4 驾驶舱 UI** | 打开即用 | Electron 多栏 + 实时流 + 点击审批（每个持久会话=一"窗口"） | 单窗口看全部 worker、点按钮批/拒 | P1–P3（最小 web 视图可在 P2 先有） |
| **P5 铺开** | 异构 + 接入 + 可观测 | CliWorker(Codex/Gemini) + 每项目 MCP + trace/成本归因 + 项目登记表 | 同屏跑 Claude+Codex、worker 能用浏览器/Obsidian、每 worker 成本可见 | P1–P4 |

---

## 4. 模块分解（落点 = `nanobot_plus/` 内）

性质：复用 / 新建 / 改写　｜　显水平：✓✓✓ 最高 · △ 一般 · ✗ 纯工程

### 执行层 · Workers
| 模块 | 性质 | 关键任务 | 落点 | 阶段 | 显水平 |
|---|---|---|---|---|---|
| AgentWorker 接口 | 改写 | 抽象 send/interrupt/close；支持持久会话多次投递 | `contracts.py` / `agents/base.py` | P1 | ✓✓✓ |
| ClaudeCodeWorker | 新建 | 每项目持久 `ClaudeSDKClient`：cwd/审批/resume/mcp/env 注入 | `agents/claude_worker.py` | P1 | ✓✓ |
| CliWorker | 新建 | headless 子进程驱动 Codex/Gemini；能力降级 | `agents/cli_worker.py` | P5 | ✓ |
| NanobotWorker | 改写 | nanobot in-process subagent 套进接口（fan-out） | `agents/nanobot_worker.py` | P1 | △ |
| AgentWorkerManager | 改写 | 生命周期、并发上限、按 project 索引 | `agents/manager.py` | P1 | △ |

### 编排层 · Brain
| 模块 | 性质 | 关键任务 | 落点 | 阶段 | 显水平 |
|---|---|---|---|---|---|
| dispatch 工具 | 新建 | 大脑创建/分派/查询持久 worker | `orchestrator/dispatch_tool.py` | P1 | ✓ |
| 任务拆解 / 路由 | 新建 | 目标→子任务→选项目/会话 | `orchestrator/router.py` | P1 | ✓ |
| **边界协议** | 新建 | TaskSpec/WorkerResult（窄）+ context_refs | `contracts.py` / `orchestrator/protocol.py` | P1 | ✓✓✓ |
| 大脑 system prompt | 新建 | orchestrator 人格：何时拆/合/停审批 | (nanobot templates) | P1 | ✓ |

### 安全层 · 人在环 + 验证
| 模块 | 性质 | 关键任务 | 落点 | 阶段 | 显水平 |
|---|---|---|---|---|---|
| **审批策略引擎** | 新建 | 风险分级、记忆决策、只拦关键步、plan→批→acceptEdits | `orchestrator/permission.py` | P2 | ✓✓✓ |
| **Verifier** | 新建 | 全新上下文对照 done_criteria 复核；DeepSeek 更需要 | `orchestrator/verifier.py` | P2 | ✓✓✓ |
| 审批总线 | 新建 | can_use_tool → nanobot bus → UI → 回 Allow/Deny | (接 nanobot bus) | P2 | ✓ |
| 重试 / 卡死检测 | 新建 | refined 重试；卡死 interrupt() | `agents/manager.py` | P2 | ✓ |

### 记忆层 · Memory
| 模块 | 性质 | 关键任务 | 落点 | 阶段 | 显水平 |
|---|---|---|---|---|---|
| MemoryStore / FileMemoryStore | 新建 | 写读更压忘 + 晋升；文本优先 | `contracts.py` / `memory/store.py` | P3 | ✓✓ |
| 每项目文本库(E2) | 新建 | `.nbplus/` core/facts/episodes/playbooks | `memory/project_store.py` | P3 | ✓ |
| **验证晋升 + provenance** | 新建 | 只有 verifier 过的才晋升 shared（挡 M3） | `memory/store.py`(promote) | P3 | ✓✓✓ |
| **协调黑板**(E3) | 新建 | 谁动哪些文件/模块、冲突、依赖边 | `memory/blackboard.py` | P3 | ✓✓✓ |
| 路由(E4) + Dream 扩展 | 新建/改写 | 分层路由 + episodic→semantic 巩固 | `memory/mem_router.py` / `memory/dream_ext.py` | P3 | ✓✓ |

### 接入层 + UI + 横切
| 模块 | 性质 | 关键任务 | 落点 | 阶段 | 显水平 |
|---|---|---|---|---|---|
| MCP per worker | 复用 | MCP 配置塞进 worker 的 mcp_servers | (nanobot mcp) | P5 | △ |
| 项目登记表 | 新建 | config：目录+agent+MCP+审批默认+后端 env | `config.py` | P1雏形/P5 | △ |
| Electron 驾驶舱 | 复用+扩 | 多栏 + 实时流 + 审批弹窗 | (nanobot desktop/) | P4 | ✗ |
| 可观测 / trace | 新建 | 结构化 trace + 成本归因 | `orchestrator/trace.py` | P5 | ✓ |

---

## 4b. 自进化循环（skills，对齐 Hermes；属 P3）

把"验证通过的经验"自动结晶成可复用 skill，越用越强。对齐 Nous Hermes 的 skill 自进化，
但**验证优先 + 多 agent**。

闭环：`dispatch → execute → verify → 结晶 skill → 召回注入 → 用中 patch → 按用量 curate`

四件新增（落点 `nanobot_plus/memory/`，P3 实现）：

| 件 | 做什么 | 落点 |
|---|---|---|
| **SkillSynthesizer** | 吃「已验证 WorkerResult + episode」→ 吐结构化 playbook（步骤/坑/验证步骤/依赖） | `memory/skill_synthesizer.py` |
| **召回→注入** | 相关 playbook 经 `context_refs` 喂回 worker（也可投成 Claude Code skill） | `memory/mem_router.py` + `agents/claude_worker.py` |
| **Curator** | use_count/patch_count 统计 + active/stale/archived 老化（借 Hermes 30/90 天阈值） | `memory/curator.py` |
| **用中 patch** | skill 用后偏差则回写修订（接 P2 的 retry/verifier） | `memory/skill_synthesizer.py` + `orchestrator/verifier.py` |

相对 Hermes 的两点增量（= 护城河）：
1. **结晶前过独立 Verifier** —— 不把错解固化、不让它扩散（堵综述 M3「错误经验传播」）。Hermes 是完成即结晶、靠事后用量淘汰；我们前置正确性，二者最好都要。
2. **多 agent** —— skill 分**项目私有** + **跨项目共享池**（验证后晋升、带 provenance）。单 agent 的 Hermes 不面对这问题，原生 Agent Teams 也没做透。

skill 分两层：**worker 层**（项目内即时复用，可接 agentskills.io 社区库）+ **编排器层**（跨项目、验证晋升、全局 curate）。

## 5. 三个最大风险 + 对策

1. **DeepSeek 后端 tool-use 不稳** → P0 直接对真实后端验证；验证闭环(P2)兜底。
2. **Anthropic 原生碾压**（Agent Teams / Dynamic Workflows 商品化纯 fan-out）→ 差异化只押异构 + 跨独立项目 + 验证 + 记忆。
3. **范围蔓延**（记忆/UI 吃掉编排精力）→ 严守 P0→P1 先证承重墙，UI 推 P4、记忆推 P3。

---

## 6. 待定决策

- ✅ **已定**：独立 `nanobot-plus` 包，依赖 nanobot 不 fork。
- vendored `nanobot/` 带自己的 `.git`（嵌套仓库），当前 git-ignored。首次 commit 前定：继续 `pip install -e ./nanobot`，还是去掉其 `.git` 真 vendored。
- 协调黑板存储：sqlite vs 嵌入式图（kuzu/networkx）——P3 前定。
- 持久会话上限与回收策略（空闲多久关、何时 resume）。
- playbook "晋升为 skill" 是否需人工确认。
