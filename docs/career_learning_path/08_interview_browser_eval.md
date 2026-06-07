# 08 面试篇：Browser Tools、Eval Harness、Trace Eval

这一篇对应 Agent 的高级能力和效果评估。

## 01 为什么 Coding Agent 需要 Browser Tools

因为很多代码任务不是纯后端：

- 本地 HTML 页面
- localhost web app
- 前端组件
- 控制台报错
- 截图验证
- DOM 结构检查

如果 Agent 只能读文件，无法观察页面运行结果，就很难调试前端。

## 02 为什么默认只允许 local

外部网页浏览风险更高：

- 数据泄露
- 不可控内容
- prompt injection
- 网络副作用
- 登录态风险

PyAgentCLI 当前只允许：

- workspace relative file
- workspace 内 `file://`
- localhost
- 127.0.0.1
- ::1

面试回答：

> Browser tool 先服务本地开发调试，不把它做成任意网页浏览器。

## 03 Browser v0.2 有哪些工具

当前工具：

- `inspect_page`
- `browser_dom_snapshot`
- `browser_query_selector`
- `browser_console_logs`
- `browser_screenshot`

其中：

- DOM snapshot 和 selector query 不需要 Playwright。
- console logs 和 screenshot 需要 optional Playwright。
- 没有 Playwright 时给出明确提示。

## 04 browser_query_selector 的边界

支持：

- tag：`main`
- id：`#app`
- class：`.status`

拒绝：

- `main .status`
- `div > p`
- `[data-testid=x]`
- 复杂 CSS selector

为什么？

> 当前是静态 HTML parser slice，不是完整浏览器 CSS engine。复杂 selector 后续交给 Playwright。

## 05 Agent Eval 为什么重要

Agent 的输出不能只看最终文本。

一个 Agent 可能最终说“完成了”，但实际上：

- 没有调用正确工具
- 改错文件
- 跳过关键步骤
- 调用了 forbidden tool
- 使用了过期 RAG index

所以 Eval 要看行为。

## 06 PyAgentCLI Eval 类型

当前包括：

- platform eval
- coding task eval
- RAG retrieval eval
- trace eval
- optional browser success test

指标：

- task success
- tool-call accuracy
- safety violations
- expected final contains
- forbidden tools

## 07 Trace Eval 是什么

Trace 记录一次 Agent run 的关键事件：

```text
user goal
assistant tool_call
tool observation
assistant final
```

它让 Eval 能检查：

- 是否调用了期望工具
- 是否调用了 forbidden tool
- 最终输出是否包含关键文本

面试回答：

> Trace Eval 把 Agent 评估从“看最终回答”推进到“看完整行为轨迹”。

## 08 我们开发中遇到的相关问题

### Playwright optional

问题：

- Playwright 很重，不能成为核心依赖。

解决：

- 放入 `.[browser]`
- `--check-browser` 检查能力
- optional tests 没有 Playwright 时 skip

### Optional test exit code

问题：

- 模块级 `pytest.importorskip` 会导致 collected 0 items / 1 skipped，exit code 5。

解决：

- 把 `pytest.importorskip` 放到测试函数内部。

学习点：

> 可选测试也要保证命令行体验稳定。

### Browser output path

问题：

- screenshot 虽然是观察工具，但会写文件。

解决：

- 输出限制到 `.pyagent/browser/`。

学习点：

> 工具风险不只看“读还是写”，还要看运行副作用。

### Trace Eval 扩展

问题：

- 静态 eval 不能完全代表真实 Agent 行为。

解决：

- Agent loop 新增 trace capture。
- Eval runner 增加 captured trace scoring。

学习点：

> Agent 的行为链路本身就是可评估对象。

## 高频面试题

1. Coding Agent 为什么需要浏览器能力？
2. 为什么默认只允许 localhost？
3. Playwright 为什么做成 optional？
4. DOM snapshot 和 selector query 区别是什么？
5. 为什么复杂 CSS selector 暂不支持？
6. Agent Eval 应该评估哪些指标？
7. tool-call accuracy 怎么算？
8. safety violation 怎么定义？
9. Trace Eval 解决什么问题？
10. optional browser tests 为什么要 skip 而不是 fail？

