# 09 开发复盘：我们真实遇到的问题和解决方式

这一篇专门记录 PyAgentCLI 开发过程中遇到的真实问题。

它的价值是：

> 把“开发时的坑”转成“面试时可讲的工程经验”。

## 01 sandbox 网络权限导致无法 push

### 现象

一开始普通 `git push` 会失败：

```text
Could not resolve host: github.com
```

原因是：

- Codex sandbox 网络受限。
- GitHub 需要外部网络。

后来曾经可以通过授权网络推送。

再后来权限配置变化，`sandbox_approval` 被设置为自动拒绝，授权网络也不能用了。

### 解决

- 继续本地 commit。
- 明确告诉用户当前 `main...origin/main [ahead N]`。
- 用户手动在本机 Terminal 执行 `git push`。

### 学习点

本地 Agent 要尊重权限边界。

不能因为任务目标是“推到 GitHub”，就绕过 sandbox。

面试时可以说：

> 我们在开发中遇到过网络权限变化，所以把本地 commit 和远端 push 分离处理。Agent 负责保证本地状态干净、提交完整；需要外部授权的动作由用户确认执行。

## 02 Computer Use 不能操作 Terminal

### 现象

用户安装了 Computer Use 插件后，我们尝试用它操作 Terminal。

结果工具返回：

```text
Computer Use is not allowed to use the app 'com.apple.Terminal'
```

### 解决

- 不绕过。
- 尝试 VS Code，但当前 app target 不可用。
- 最终让用户手动 push。

### 学习点

桌面自动化不是万能的。

Agent 能看到某个应用，不代表能操作它。

面试时可以说：

> Desktop automation 也需要安全策略。尤其是 Terminal 这种高风险入口，禁止自动操作是合理的。

## 03 gpt-image-2 不存在

### 现象

某次会话中出现：

```text
The model 'gpt-image-2' does not exist.
```

### 判断

这不是 PyAgentCLI 项目代码调用的。

更像是 Codex/客户端侧因为用户发了截图，误触发了图像模型路由。

### 解决

- 明确不调用图像模型。
- 后续只用文本、文件、测试和本地工具。

### 学习点

多工具 Agent 环境中，错误可能来自：

- 项目代码
- 外部工具
- 客户端路由
- 模型权限

排查时要先判断问题边界。

## 04 Playwright optional dependency

### 现象

Browser console logs 和 screenshot 需要 Playwright。

但如果把 Playwright 放进默认依赖：

- 安装变慢
- 浏览器 binary 更重
- CI 更复杂
- 没做前端任务的用户也被迫安装

### 解决

- 新增 optional extra：`.[browser]`
- 新增 `pyagent --check-browser`
- 工具缺依赖时清晰失败
- optional tests 没依赖时 skip

### 学习点

可选能力要优雅降级。

面试时可以说：

> 我没有把 Playwright 做成默认依赖，而是拆成 optional extra，同时提供能力检测和可选成功路径测试。

## 05 pytest.importorskip 的坑

### 现象

最初把 `pytest.importorskip("playwright.sync_api")` 放在测试文件顶部。

单独运行该测试文件时出现：

```text
collected 0 items / 1 skipped
exit code 5
```

### 解决

把 `importorskip` 放进具体测试函数。

这样结果变成：

```text
2 skipped
exit code 0
```

### 学习点

测试不只是“能不能过”，还要关注命令行体验和 CI 行为。

## 06 Browser 外部 URL 限制

### 现象

浏览器工具如果开放外部 URL，会引入：

- 登录态风险
- prompt injection
- 数据泄露
- 不可控网络访问

### 解决

只允许：

- workspace file
- workspace 内 file URL
- localhost
- 127.0.0.1
- ::1

外部 URL 默认拒绝。

### 学习点

Agent 工具的能力边界要和用户任务一致。

PyAgentCLI 是 coding agent，不是通用爬虫。

## 07 Screenshot 输出路径限制

### 现象

`browser_screenshot` 虽然是观察工具，但会写截图文件。

如果允许任意 output path，就可能变成写文件工具。

### 解决

强制输出到：

```text
.pyagent/browser/
```

### 学习点

工具风险不能只看工具名字。

只要有文件写入，就必须考虑路径限制。

## 08 Reviewer Gate 防止假成功

### 现象

计划执行中可能有 step 被 skipped，但最终执行函数仍可能返回 success。

### 解决

Reviewer 检查所有 step status：

- failed
- skipped
- cancelled

只要出现这些状态，就 block success。

### 学习点

Agent 成功不能只看最终文本。

需要检查执行轨迹和中间状态。

## 09 Retry Proposal 的状态区分

### 现象

测试中曾把 skipped step 的 next action 写成 `retry_step`。

后来发现不准确。

### 正确设计

- failed -> `retry_step`
- skipped -> `user_decision`
- cancelled -> `resume_plan`

### 学习点

不同失败状态对应不同恢复策略。

不能把所有异常都粗暴 retry。

## 10 RAG stale index

### 现象

用户修改文件后，本地 SQLite FTS index 可能过期。

如果 Agent 继续用旧索引，就会基于错误上下文行动。

### 解决

- 执行计划前检查 stale paths。
- 输出 freshness warning。
- 不自动重建索引。

### 学习点

RAG 的工程难点不只是召回，还有上下文新鲜度。

## 11 Memory 生命周期

### 现象

Memory 如果只能增加，不能删除，会变成黑箱。

错误记忆可能影响后续任务。

### 解决

- `--memory`
- `--remember`
- `--compress-memory`
- `--delete-memory-line`
- `--stale-memory-days`

### 学习点

Memory 要有生命周期管理。

## 12 Skill 边界

### 现象

Skill 容易被误解成工具或插件。

### 解决

PyAgentCLI 明确：

- Skill 是 prompt guidance
- 不执行工具
- 不覆盖用户任务
- 不绕过安全策略

### 学习点

Skill 是知识复用，不是权限扩展。

## 13 Trace Eval 扩展

### 现象

早期 eval 更多是静态函数检查。

但 Agent 真正的质量要看行为轨迹。

### 解决

- Agent loop 捕获 trace。
- trace 记录 tool call、observation、final。
- eval 检查 expected tools、forbidden tools、final output。

### 学习点

Agent eval 的核心是行为评估，而不是只看最终回答。

