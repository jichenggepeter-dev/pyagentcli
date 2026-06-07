# 02 先把项目跑起来：本地运行、测试、演示

## 为什么第一步是跑起来

学习 Agent 项目最容易犯的错误，是先看一堆概念：

- ReAct
- Function Calling
- RAG
- Memory
- MCP
- Multi-Agent

看完会觉得都懂，但一旦让你打开项目、跑命令、看输出，就会卡住。

所以 PyAgentCLI 的第一步是：

> 先让项目在你自己的电脑上跑起来。

这一步不是形式主义。它能让你确认：

- Python 环境是否正确
- CLI entry point 是否可用
- 测试是否能跑
- 本地 fallback 是否可用
- `.pyagent/` 运行态是否能生成
- GitHub 项目是否处在可演示状态

## 安装项目

推荐使用 editable install：

```bash
python -m pip install -e ".[dev]"
```

安装后应该能直接运行：

```bash
pyagent --help
```

如果只想用源码方式运行，也可以：

```bash
PYTHONPATH=src python -m pyagentcli --help
```

但简历项目演示时，推荐使用 `pyagent`，因为这说明你做了 packaging 和 console script。

## 第一个 smoke test

运行：

```bash
pyagent --help
```

你应该能看到：

- `--plan`
- `--execute-plan`
- `--index`
- `--memory`
- `--eval`
- `--list-skills`
- `--check-browser`

这说明 CLI 参数注册正常。

## 跑内置 Eval

运行：

```bash
pyagent --eval
```

你要关注的不是“输出好不好看”，而是这几类指标：

- platform eval 是否通过
- coding task eval 是否通过
- RAG retrieval eval 是否通过
- trace eval 是否通过
- tool-call accuracy 是否合理
- safety violations 是否为 0

这能证明项目不是只能跑 demo，而是有可回归评估。

## 跑计划预览

运行：

```bash
pyagent --plan "fix failing tests"
```

这一步不会改文件，只会生成计划。

你要观察：

- PlanRun status 是否是 `planned`
- 是否生成 Plan id
- 是否包含 Agent handoffs
- 每个 step 是否有 risk 和 suggested tools

这个命令能体现 Plan-and-Execute 的安全价值。

## 跑 RAG 索引

运行：

```bash
pyagent --index
```

这会生成 `.pyagent/index.sqlite`。

你要知道：

- SQLite FTS 用来做本地代码检索。
- AST chunk 用来做 symbol 级别检索。
- 修改文件后可能触发 stale index warning。

## 跑 Memory

运行：

```bash
pyagent --remember "Prefer edit_file for small edits."
pyagent --memory
```

你要观察：

- `.pyagent/memory/project.md` 是否生成。
- memory 是否会在后续任务中注入。
- memory 是可见、可审查、可删除的。

## 跑 Browser 检查

运行：

```bash
pyagent --check-browser
```

如果当前没有安装 Playwright，会看到类似：

```text
Browser capability status:
- Playwright package: missing
- Install optional browser support with ...
```

这不是失败，而是 graceful degradation。

如果想启用可选浏览器能力：

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

## 跑测试

核心测试：

```bash
python -m pytest
```

当前项目测试覆盖：

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

没有 Playwright 时会 skip，不影响核心 suite。

## 我们开发时遇到的真实运行问题

### 问题 1：网络权限导致无法 push

现象：

- sandbox 里普通 `git push` 不能解析 GitHub。
- 后来授权通道也被关闭。

处理：

- 本地继续 commit。
- 用户手动在 Terminal 执行 `git push`。

学习点：

> Agent 要尊重运行环境权限，不能为了完成任务绕过 sandbox。

### 问题 2：Computer Use 不能操作 Terminal

现象：

- Computer Use 能看到 Safari。
- 但 Terminal 被安全策略禁止操作。

处理：

- 不强行绕过。
- 改成用户手动执行敏感命令。

学习点：

> 桌面自动化也有权限边界，能看不代表能操作。

### 问题 3：可选 Playwright 测试不能污染核心测试

现象：

- 没装 Playwright 时，浏览器成功路径不能跑。
- 模块级 `pytest.importorskip` 会导致单文件运行 exit code 5。

处理：

- 把 `importorskip` 放进测试函数内部。
- 没有 Playwright 时单个测试 skip，而不是整个文件无测试。

学习点：

> 可选能力应该独立验证，不能让核心测试依赖大体积外部环境。

## 这一篇能沉淀成什么

你可以把这一篇当作：

- 项目启动手册
- 面试前自检清单
- 演示前 checklist
- 环境踩坑记录

面试时如果被问“你这个项目真跑过吗”，你可以回答：

> 跑过。我不仅跑了 CLI，还做了 full test、eval、browser capability check、optional browser test，并且把无法联网 push、Playwright optional、Computer Use 限制这些真实问题都记录进项目文档了。

