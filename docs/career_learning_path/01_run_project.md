# 01 先跑通 PyAgentCLI：安装、命令、演示、自检

这一篇的目标很简单：

> 用一天时间把 PyAgentCLI 在本地跑起来，并知道每个关键命令能证明什么。

不要一开始就陷进 ReAct、RAG、MCP、Memory 的概念里。AI Agent 项目最怕“看起来都懂，但打不开项目、跑不出命令、讲不出输出”。所以第一步必须是运行。

## 这一篇学什么

读完这一篇，你应该能完成：

- 安装 PyAgentCLI。
- 跑通 CLI help。
- 跑通本地 fallback 模式。
- 跑通 eval。
- 生成一次 plan preview。
- 建立 RAG 索引。
- 写入和查看 memory。
- 检查 browser capability。
- 运行测试。
- 准备一段最小演示话术。

这一步对应 PaiCLI 学习路线里的“先把项目跑起来”。区别是：这里全部回到 PyAgentCLI 的 Python 实现。

## 为什么第一步不是看源码

因为跑通项目能先验证五件事：

- 环境是否正确。
- CLI entry point 是否注册成功。
- 无 API key 时 fallback 是否可用。
- 项目是否有测试和 eval。
- `.pyagent/` 本地运行态是否能生成。

这五件事比“我看懂了 Agent 概念”更重要。一个能跑、能测、能演示的项目，才有资格继续写进简历。

## 安装项目

推荐用 editable install：

```bash
python -m pip install -e ".[dev]"
```

安装后运行：

```bash
pyagent --help
```

如果你不想安装，也可以用源码方式运行：

```bash
PYTHONPATH=src python -m pyagentcli --help
```

但正式演示时，更推荐使用 `pyagent` 命令。它能说明项目已经配置了 packaging 和 console script，而不是只能靠源码路径临时跑。

## 第一个命令：确认 CLI 能启动

运行：

```bash
pyagent --help
```

你要观察的是有没有这些能力入口：

- `--plan`
- `--execute-plan`
- `--index`
- `--memory`
- `--eval`
- `--list-skills`
- `--check-browser`

这说明 PyAgentCLI 不是一个单一聊天命令，而是一个带工具、计划、记忆、检索、评估和浏览器能力的本地 CLI。

面试时可以这样说：

> 我先从 CLI entry point 验证项目是否能作为真实命令行工具运行，而不是只用 `python script.py` 跑一个 demo。

## 第二个命令：确认本地 fallback 能用

如果没有配置真实模型 API key，PyAgentCLI 仍然可以跑本地 fallback。

运行：

```bash
pyagent "summarize this workspace"
```

你要理解：

- fallback 不是为了替代真实模型。
- fallback 是为了让 CLI、工具注册、测试和演示在无 key 环境下仍可验证。
- 真实模型能力需要配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`PYAGENT_MODEL`。

配置真实模型：

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

可选 `.env` 也支持，但环境变量优先级更高。

面试时可以这样说：

> 我把模型接入和本地运行解耦了。没有 API key 时，CLI 和工具链仍然能测试；有 key 时，再验证真实模型 tool call。

## 第三个命令：跑内置 Eval

运行：

```bash
pyagent --eval
```

你要关注的不是输出是否漂亮，而是它覆盖了哪些维度：

- platform eval
- coding task eval
- RAG retrieval eval
- trace eval
- tool-call accuracy
- safety violations

这说明 PyAgentCLI 不是只靠“最终回答看起来不错”来判断效果，而是有一套可回归的评估机制。

面试时可以这样说：

> 对 Coding Agent 来说，只看最终文本是不够的。我用 eval 检查工具调用、文件结果、RAG 检索、trace 行为和安全违规。

## 第四个命令：生成 Plan Preview

运行：

```bash
pyagent --plan "fix failing tests"
```

这一步只生成计划，不执行文件修改。

你要观察：

- 是否生成 plan id。
- plan status 是否是 `planned`。
- 每个 step 是否有目标和建议工具。
- 是否能看到风险提示。
- 是否有 agent handoff 记录。

这能证明 Plan-and-Execute 的核心价值：

> 复杂任务先拆解，再由用户审查，不让 Agent 一上来就乱改代码。

如果后续执行计划，再使用：

```bash
pyagent --execute-plan "fix failing tests"
```

但第一次学习时，先跑 `--plan` 更安全。

## 第五个命令：建立 RAG 索引

运行：

```bash
pyagent --index
```

它会生成本地索引，例如：

```text
.pyagent/index.sqlite
```

你要理解：

- SQLite FTS 用于本地全文检索。
- AST chunk 用于函数、类、方法等 symbol 级上下文。
- import graph 用于理解 Python 文件之间的依赖。
- 文件修改后，旧索引可能触发 stale warning。

面试时不要只说“我做了 RAG”，要说：

> 代码 RAG 不能只靠向量检索。PyAgentCLI 用 FTS、AST symbol chunk、import graph 和可选 embedding 组合，让 Agent 能拿到更准确、更可控的代码上下文。

## 第六个命令：写入和查看 Memory

运行：

```bash
pyagent --remember "Prefer edit_file for small edits."
pyagent --memory
```

你要观察：

- `.pyagent/memory/` 是否生成。
- project memory 是否可见。
- 后续任务是否可以注入 memory。

PyAgentCLI 的 Memory 要强调三点：

- 可见。
- 可删除。
- 可检查 stale。

它不是黑箱长期记忆。

面试时可以这样说：

> Memory 不是越多越好。它必须经过筛选才能变成 Context，并且要允许用户审查、删除和判断是否过期。

## 第七个命令：检查 Browser 能力

运行：

```bash
pyagent --check-browser
```

如果没有安装 Playwright，可能会看到：

```text
Browser capability status:
- Playwright package: missing
```

这不是失败，而是 graceful degradation。

Browser 能力是 optional：

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

学习时要记住：

- Browser tool 默认 local-first。
- 本地 HTML 和 localhost 是主要场景。
- 外部 URL、登录态、点击、输入、页面脚本都需要更强边界。

我们这次阅读 PaiCLI 登录态页面时也遇到了类似问题：

- Safari 已登录，但普通网络请求不能继承登录态。
- Computer Use 能读页面，但点击/滚动受窗口焦点影响。
- Safari `do JavaScript` 需要额外授权。

这些都说明：浏览器能力不是“能打开网页”这么简单。

## 第八个命令：跑测试

核心测试：

```bash
python -m pytest
```

测试覆盖方向包括：

- Agent loop
- CLI
- Tool Registry
- Safety Policy
- RAG
- Memory
- MCP
- Skill
- Browser
- Reviewer
- Eval
- Packaging

可选浏览器测试：

```bash
python -m pytest tests/test_browser_playwright_optional.py
```

没有 Playwright 时应该 skip，而不是让核心测试失败。

面试时可以这样说：

> 我把可选浏览器能力和核心 CLI 解耦。没有 Playwright 时，核心测试仍然能跑；浏览器成功路径单独用 optional test 验证。

## 一天跑通检查表

第一天结束前，你应该能打勾：

- [ ] `pyagent --help` 正常。
- [ ] `pyagent --eval` 正常。
- [ ] `pyagent --plan "fix failing tests"` 能生成计划。
- [ ] `pyagent --index` 能建立索引。
- [ ] `pyagent --remember` 和 `pyagent --memory` 能读写记忆。
- [ ] `pyagent --check-browser` 能输出能力状态。
- [ ] `python -m pytest` 能跑核心测试。
- [ ] 能讲清楚 `.pyagent/` 目录里存什么。
- [ ] 能讲清楚没有 API key 时 fallback 的作用。
- [ ] 能讲清楚 PyAgentCLI 和普通 chatbot 的区别。

## 第一天的最小演示脚本

推荐演示顺序：

```bash
pyagent --help
pyagent --eval
pyagent --plan "fix failing tests"
pyagent --index
pyagent --remember "Prefer edit_file for small edits."
pyagent --memory
pyagent --check-browser
```

演示时不要每个输出都解释很久。重点讲每个命令证明什么：

- help 证明 CLI 工具化。
- eval 证明可评估。
- plan 证明复杂任务先审查。
- index 证明代码检索。
- memory 证明跨任务上下文。
- browser check 证明可选浏览器能力和降级策略。

## 第一天的口播

可以这样讲：

> 我先把 PyAgentCLI 跑起来，而不是一上来背 Agent 概念。这个项目可以通过 `pyagent` 命令运行，支持 eval、plan、RAG index、memory 和 browser capability check。没有 API key 时，它有本地 fallback，方便验证 CLI 和工具链；有真实模型时，再验证 Function Calling。第一天我的目标是证明它不是一个聊天 demo，而是一个本地 Agent Runtime。

## 常见问题

### Q1：没有真实模型 API key，还能学习吗？

可以。

无 key 时可以先验证：

- CLI 是否正常。
- 工具是否注册。
- eval 是否能跑。
- plan 是否能生成。
- RAG / Memory / Browser capability check 是否工作。

真实模型主要用于验证 LLM tool call 的真实行为。

### Q2：为什么 `--plan` 比 `--execute-plan` 更适合第一天？

因为第一天重点是理解系统，不是让 Agent 改代码。

`--plan` 只生成计划，风险低；`--execute-plan` 涉及文件修改、shell、审批和 reviewer，适合你理解安全边界后再跑。

### Q3：`.pyagent/` 能不能删？

可以，但要知道里面是什么。

通常包括：

- memory
- plans
- eval reports
- audit logs
- browser artifacts
- index

它是 PyAgentCLI 的本地运行态，不是源码。

### Q4：为什么 Browser 能力不是默认全开？

因为浏览器工具风险更高。

它涉及：

- 本地文件。
- localhost 服务。
- 外部 URL。
- 登录态。
- DOM。
- 点击和输入。
- 截图输出路径。

所以 PyAgentCLI 先做 local-first 和 optional Playwright，后续再增强更复杂的交互。

## 这一篇之后做什么

跑通后不要马上乱翻所有源码。下一步应该进入核心实战篇：

1. ReAct 和 Tool Calling
2. Plan-and-Execute / DAG
3. Memory 系统
4. RAG 代码检索
5. Tool Call、HITL 和安全策略

这样你会从“能跑”进入“能解释”，最后再进入“能写简历、能面试”。
