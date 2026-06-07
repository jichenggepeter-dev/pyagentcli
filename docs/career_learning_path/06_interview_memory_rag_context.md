# 06 面试篇：Memory、RAG、Context Engineering

这一篇对应上下文工程。

面试官问 Agent 项目时，经常会从这里判断你是不是真的理解 LLM 应用。

## 01 Memory 和 Context 的区别

Context：

- 当前请求真正发给模型的内容
- 有 token 限制
- 每次请求都要重新组织

Memory：

- 跨任务保存的信息
- 不一定每次都注入
- 必须可审查、可删除

面试回答：

> Memory 不是直接等于 prompt。Memory 需要被筛选、压缩、注入后，才成为当前请求的 context。

## 02 PyAgentCLI 的 Memory 分层

PyAgentCLI 当前主要有：

- Project Memory
- Session Summary
- Explicit Remember

对应路径：

```text
.pyagent/memory/project.md
.pyagent/memory/sessions/
```

CLI：

```bash
pyagent --remember "Prefer edit_file for small edits."
pyagent --memory
pyagent --compress-memory
pyagent --delete-memory-line 3
pyagent --stale-memory-days 30
```

## 03 为什么 Memory 要可删除？

因为错误记忆会污染后续任务。

如果 Agent 记住了错误偏好，比如：

```text
Always use write_file to edit files.
```

它可能破坏我们“优先 edit_file”的安全策略。

所以 PyAgentCLI 提供：

- 查看 memory
- 删除 memory line
- stale memory 检查

面试回答：

> Memory 不是越多越好，而是要可见、可控、可删除。

## 04 RAG 为什么不只是向量检索？

代码检索和普通文档检索不同。

代码场景里很多查询是精确的：

- 文件名
- 函数名
- 类名
- import 关系
- symbol 定义

所以 PyAgentCLI 没有只做 vector search，而是组合：

- SQLite FTS
- AST symbol chunk
- JS/TS chunk
- import graph
- optional embedding

面试回答：

> 对 coding agent 来说，RAG 的目标不是召回一段相似文本，而是给模型准确、新鲜、可控的代码上下文。

## 05 AST symbol chunk 解决什么问题？

普通按行 chunk 会把函数切碎。

AST symbol chunk 可以按结构切：

- function
- class
- method

优点：

- `@symbol` 能精确定位
- 上下文边界更自然
- 面试时更容易解释代码理解能力

PyAgentCLI 中：

- Python 使用 AST
- JS/TS 使用轻量语法规则识别常见 symbol

## 06 import graph 为什么重要？

只知道函数定义不够，还要知道依赖关系。

PyAgentCLI 构建 Python import graph：

- 当前文件 imports 什么
- 哪些文件 imported by 当前模块

对应工具：

```text
search_dependencies
```

面试回答：

> 代码理解不能只看一个文件，要看它和其他模块的依赖关系。

## 07 stale index 怎么处理？

问题：

- 用户修改文件后，索引可能过期。
- Agent 如果继续相信旧索引，就会用错上下文。

PyAgentCLI 做法：

- 检查 stale paths
- 在 plan / execute / retry 前提示 warning
- 不自动重建索引

为什么不自动重建？

> 因为检索上下文变化会影响 Agent 行为，应该显式、可审计。

## 08 Context Injection

PyAgentCLI 支持：

```text
@README.md
@src/pyagentcli
@AgentLoop
```

这些会被注入成用户提供的上下文。

同时还会注入：

- project memory
- skill guidance

上下文来源越多，越需要边界。

面试回答：

> Context engineering 的关键不是塞更多东西，而是把不同来源的信息按优先级、边界和 token 预算组织好。

## 09 我们开发中遇到的相关问题

### RAG stale warning

我们实现过测试：

- 先建索引
- 再修改 README
- 执行 plan 时提示 index freshness warning

这是很好的面试素材。

说明你理解：

> RAG 不是一次建索引就万事大吉，索引新鲜度本身就是工程问题。

### Dependency context 路径问题

开发 dependency context injection 时，曾遇到 macOS `/var` 和 `/private/var` 路径解析差异。

解决思路：

- 路径比较前做 resolve
- 不依赖表面字符串

面试可讲：

> 本地工具要注意不同系统路径规范化，否则安全围栏和上下文注入都可能误判。

### Memory 删除和 stale 检查

我们不是只做“记住”，还做了：

- 删除 memory line
- stale memory days
- session compression

这说明：

> Memory 是一套生命周期管理，而不是一个 append-only 文件。

## 高频面试题

1. Memory 和 Context 有什么区别？
2. 为什么 Memory 需要可删除？
3. 长上下文满了怎么办？
4. RAG 为什么不只是向量检索？
5. AST chunk 比按行 chunk 好在哪里？
6. 代码检索如何处理依赖关系？
7. stale index 会导致什么问题？
8. `@file`、`@folder`、`@symbol` 如何注入？
9. embedding provider 为什么要可选？
10. 如何防止错误 memory 污染后续任务？

