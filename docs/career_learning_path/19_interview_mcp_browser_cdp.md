# 19 面试题第四弹：MCP、Browser Tools、CDP 思路

这一弹对应 Agent 的外部工具生态和浏览器能力。

面试官问到这里，通常已经不满足于“你能读写文件”。他们会追：

```text
怎么接外部工具？
MCP 是什么？
浏览器工具为什么默认只看 localhost？
Playwright 和 CDP 有什么区别？
登录态页面怎么处理？
外部网页会不会 prompt injection？
Browser 工具会不会绕过安全？
```

这一弹要把 MCP 和 Browser 都讲成“扩展观察能力和工具来源”，但不放松安全边界。

## 这一弹考什么

这一弹主要考 6 个能力：

1. 你是否知道 MCP 解决的是外部工具统一接入。
2. 你是否能讲清 stdio MCP 的 initialize、tools/list、tools/call。
3. 你是否理解 MCP tool 进入本地 ToolRegistry 后仍要走安全策略。
4. 你是否能解释 Browser Tools 为什么 local-first。
5. 你是否能讲清 Playwright optional、DOM snapshot、screenshot、network logs、browser_interact 的边界。
6. 你是否能把 CDP 讲成未来浏览器控制思路，而不是把未实现能力说成已完成。

对应源码：

```text
src/pyagentcli/mcp/client.py
src/pyagentcli/mcp/adapter.py
src/pyagentcli/config.py
src/pyagentcli/tools/browser.py
src/pyagentcli/tools/search.py
src/pyagentcli/cli/main.py
```

对应实战文档：

- [08 Browser Tools 和联网搜索](08_browser_search.md)
- [09 接入 MCP](09_mcp_integration.md)

## 哪些简历句子会触发这一弹

如果简历里写：

> 实现最小 MCP stdio client，支持 initialize、tools/list、tools/call 和项目级 `pyagent.toml` server 配置，并通过 MCPToolAdapter 将外部工具注册进本地 ToolRegistry，复用风险分级、人工审批和 JSONL 审计。

面试官会追问：

- MCP 解决什么问题？
- stdio transport 怎么工作？
- MCP tool 如何变成本地 Tool？
- readOnlyHint 怎么映射风险？
- 坏 MCP server 怎么隔离？

如果简历里写：

> 设计 local-first Browser Tools，支持本地 HTML / localhost 页面 inspection、DOM snapshot、selector query、browser assert、console logs、screenshot、network summary 和 browser interaction，并对外部 URL、截图输出和交互动作做安全约束。

面试官会追问：

- 为什么不默认浏览任意网页？
- Playwright 为什么 optional？
- screenshot 为什么要限制输出路径？
- browser_interact 为什么是 EXECUTE？
- CDP 和 Playwright 什么关系？

## 面试开场 30 秒回答

如果面试官问“你们怎么扩展工具和浏览器能力”，可以先这样答：

> PyAgentCLI 里 MCP 和 Browser 都是扩展 Agent 能力的方式，但不扩展权限边界。MCP 负责把外部工具用统一协议接入，目前实现的是 stdio tools slice：启动本地 MCP server 子进程，完成 initialize、tools/list、tools/call，然后用 MCPToolAdapter 把远程工具注册进本地 ToolRegistry；readOnlyHint 映射 READ，destructiveHint 映射 CRITICAL，openWorldHint 或无 annotation 默认 NETWORK，仍然走 SafetyPolicy、ApprovalHandler 和 AuditLogger。Browser 这块是 local-first，主要服务本地 HTML 和 localhost web app 调试，默认只允许 workspace file、file URL inside workspace、localhost/127.0.0.1/::1，不做任意外网浏览。Playwright 是 optional，用于 console、screenshot、network 和 interaction；browser_interact 是 EXECUTE risk，需要审批。

## Q1：MCP 解决什么问题？

一句话答案：

> MCP 解决外部工具、服务和数据源如何用统一协议接入 Agent 的问题。

展开回答：

没有 MCP 时，每接一个工具都要写 glue code：

```text
GitHub adapter
Docs adapter
Database adapter
Browser adapter
Search adapter
```

MCP 提供统一协议：

```text
initialize
tools/list
tools/call
```

落到 PyAgentCLI：

- 读取 `pyagent.toml` 中 MCP server 配置。
- 用 stdio 启动 server。
- 调 `tools/list` 发现工具。
- 用 `MCPToolAdapter` 注册到本地 ToolRegistry。

## Q2：MCP 会不会绕过本地安全策略？

一句话答案：

> 不会。MCP 扩展工具来源，不扩展工具权限。

展开回答：

PyAgentCLI 的链路是：

```text
MCP server tool
  -> MCPToolAdapter
  -> ToolRegistry
  -> SafetyPolicy
  -> ApprovalHandler
  -> AuditLogger
```

也就是说 MCP tool 进入本地 registry 后，和内置工具走同一条执行链路。

面试加分点：

> 外部工具越灵活，默认策略越应该保守。

## Q3：stdio MCP transport 怎么工作？

一句话答案：

> stdio transport 通过子进程 stdin/stdout 交换 JSON-RPC 消息。

展开回答：

`StdioMCPTransport` 做：

- 启动本地 server 子进程。
- 向 stdin 写 JSON-RPC request。
- 从 stdout 读 JSON-RPC response。
- reader thread 把消息放进 queue。
- close 时 terminate / kill。

`MCPClient` 做：

```text
initialize()
send notifications/initialized
list_tools()
call_tool(name, arguments)
```

如果超时：

```text
Timed out waiting for MCP response
```

如果返回 error：

```text
MCPError
```

## Q4：MCP tool 如何映射风险？

一句话答案：

> 通过 MCP annotations 映射到本地 RiskLevel；没有明确只读声明时默认 NETWORK。

展开回答：

PyAgentCLI 当前映射：

```text
destructiveHint: true -> CRITICAL
readOnlyHint: true    -> READ
openWorldHint: true   -> NETWORK
no annotation         -> NETWORK
```

为什么无 annotation 默认 NETWORK？

因为 MCP server 是外部工具来源。

如果工具没说自己只读，就不能假设安全。

## Q5：坏 MCP server 怎么办？

一句话答案：

> 一个 MCP server 注册失败时会被跳过，不影响内置工具和其他 server。

展开回答：

`register_configured_mcp_tools()` 会逐个注册 server。

如果某个 server：

- 启动失败。
- initialize 失败。
- tools/list 超时。
- 返回非法 payload。

PyAgentCLI 会记录 error，并 close client。

这样：

> bad MCP server 不会拖垮整个 Agent。

## Q6：当前 MCP 实现完整吗？

一句话答案：

> 不完整。当前是最小 stdio tools slice，不是完整 MCP 平台。

已实现：

- stdio。
- initialize。
- tools/list。
- tools/call。
- tool adapter。
- risk mapping。
- project config。

未实现：

- resources。
- prompts。
- sampling。
- HTTP/SSE。
- OAuth。
- credential 管理。
- server health UI。

诚实边界很重要。

## Q7：为什么 Coding Agent 需要 Browser Tools？

一句话答案：

> 因为很多代码任务需要观察本地页面运行结果，而不是只读源码。

展开回答：

前端任务经常要看：

- 页面 title。
- DOM 结构。
- selector 是否存在。
- 控制台是否报错。
- screenshot。
- network request summary。
- 点击或输入后的状态。

如果 Agent 只能读文件，它只能猜 UI 状态。

Browser Tools 让 Agent 能验证：

```text
页面上是否真的出现 READY
按钮是否可点击
console 是否有 error
请求是否失败
```

## Q8：为什么默认只允许 local target？

一句话答案：

> 因为外部网页有 prompt injection、登录态泄露、网络副作用和不可控内容风险；v0.1 先服务本地开发调试。

展开回答：

PyAgentCLI 当前允许：

```text
workspace-relative HTML paths
file:// inside workspace
http://localhost:*
http://127.0.0.1:*
http://[::1]:*
```

默认拒绝：

```text
external HTTP/HTTPS
file:// outside workspace
unsupported schemes
```

面试加分点：

> Browser tool 不是通用爬虫，而是本地开发观察工具。

## Q9：Browser Tools 当前有哪些？

一句话答案：

> 当前支持页面 inspection、DOM snapshot、简单 selector、assert、console logs、screenshot、network summary 和 interaction。

展开回答：

工具：

```text
inspect_page
browser_dom_snapshot
browser_query_selector
browser_assert
browser_console_logs
browser_screenshot
browser_network_logs
browser_interact
pyagent --check-browser
```

其中：

- 静态 HTML 观察不需要 Playwright。
- console、screenshot、network、interaction 需要 optional Playwright。
- 没有 Playwright 时给明确提示或 skip optional tests。

## Q10：Playwright 为什么 optional？

一句话答案：

> 因为 Playwright 体积和安装成本较高，不应该成为核心 CLI 的默认依赖。

展开回答：

默认安装应该轻：

```bash
python -m pip install -e ".[dev]"
```

浏览器能力单独启用：

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

这样：

- 核心 CLI 可快速运行。
- 浏览器功能可选。
- CI 不被浏览器依赖拖住。
- optional tests 可 skip。

## Q11：browser_query_selector 为什么只支持简单 selector？

一句话答案：

> 因为当前静态 HTML parser 不是完整浏览器 CSS engine。

展开回答：

当前支持：

```text
tag
#id
.class
```

拒绝：

```text
main .status
div > p
[data-testid=x]
```

复杂 selector 后续交给 Playwright 或真正浏览器引擎。

这体现边界：

> 不把轻量静态 parser 说成完整 DOM/CSS engine。

## Q12：browser_screenshot 为什么限制输出路径？

一句话答案：

> 因为 screenshot 虽然是观察工具，但会写文件，所以输出必须限制在 workspace 的 `.pyagent/browser/`。

展开回答：

风险：

- 任意路径写文件。
- 覆盖用户文件。
- 泄露截图内容到不该写的位置。

PyAgentCLI 限制：

```text
.pyagent/browser/
```

这说明：

> 工具风险不只看“读页面”，也要看它是否写产物。

## Q13：browser_network_logs 为什么不记录 body/header？

一句话答案：

> 因为请求 body 和 headers 可能包含 token、cookie、个人数据或密钥。

展开回答：

网络日志只做 summary 更安全：

- URL。
- method。
- status。
- timing。
- error。

不默认记录：

- request body。
- response body。
- cookies。
- auth headers。

这符合最小必要原则。

## Q14：browser_interact 为什么是 EXECUTE risk？

一句话答案：

> 因为点击、输入、提交可能改变页面状态，尤其登录态页面可能产生真实副作用。

展开回答：

`browser_interact` 支持：

- click。
- type/fill。
- press。
- wait。

风险：

- 提交表单。
- 触发删除。
- 修改账号状态。
- 发起网络请求。

所以它不能当 READ。

必须走审批。

## Q15：CDP 是什么，和 Playwright 什么关系？

一句话答案：

> CDP 是 Chrome DevTools Protocol，是浏览器底层调试协议；Playwright 是更高层的自动化库，可以通过浏览器协议控制页面。

展开回答：

CDP 能做：

- DOM inspection。
- console logs。
- network events。
- screenshots。
- input events。
- performance traces。

Playwright 提供更高层 API：

- page.goto。
- locator.click。
- page.screenshot。
- console event。
- request/response event。

PyAgentCLI 当前使用的是 optional Playwright 路线。

边界：

> 当前没有实现直接 CDP 连接用户浏览器 profile，也没有接 Safari 登录态。

## Q16：Safari 登录态 / Computer Use 和 PyAgentCLI Browser Tool 有什么区别？

一句话答案：

> Safari/Computer Use 是桌面 UI 自动化或用户浏览器状态，PyAgentCLI Browser Tool 是本地 CLI 工具链的一部分，两者能力和权限边界不同。

展开回答：

Safari 登录态适合：

- 用户已经登录的网站。
- 需要人工阅读网页。
- 需要桌面状态的任务。

PyAgentCLI Browser Tool 适合：

- 本地 HTML。
- localhost app。
- 可审计工具调用。
- eval 和 trace。

风险区别：

- 登录态页面副作用更高。
- Computer Use 依赖前台窗口和 UI 状态。
- CLI browser tool 更可测试、可审计。

我们之前遇到过：

> Computer Use 能看到 Safari，但登录态、点击、滚动、前台窗口和页面状态都有边界。

这就是为什么项目里 Browser Tools 先 local-first。

## Q17：外部 web search 怎么扩展才安全？

一句话答案：

> 先做 provider / allowlist / approval / audit，而不是让 Agent 任意访问外网。

展开回答：

未来可以加：

- search provider API。
- domain allowlist。
- query logging。
- result citation。
- robots / copyright 边界。
- network risk level。
- user approval。

默认不做任意外网浏览，是因为：

- prompt injection。
- 数据泄露。
- 网络副作用。
- 不可控内容。

## Q18：你们开发时这里遇到过什么真实问题？

可以讲 4 个。

### 1. Playwright optional

Playwright 很重。

所以放在：

```text
.[browser]
```

而不是核心依赖。

### 2. optional test exit code

模块级 `pytest.importorskip` 可能导致 collected 0 items / exit code 5。

解决：

> 把 importorskip 放进测试函数内部。

### 3. Browser output path

screenshot 会写文件。

所以限制到：

```text
.pyagent/browser/
```

### 4. Safari 登录态不等于 CLI Browser Tool

用户浏览器登录态很有用，但不等于可审计的本地工具。

桌面自动化会受权限、前台窗口、页面状态影响。

## Q19：如果面试官问“为什么不用浏览器直接上网搜”，怎么答？

一句话答案：

> 因为 Coding Agent 的 browser 能力优先服务本地开发验证，任意外网浏览需要额外的网络、隐私、登录态和 prompt injection 安全设计。

展开回答：

我会区分：

- 本地 search：`search_files/search_text/search_index`。
- 本地 browser：workspace HTML / localhost。
- 外部 web search：未来 provider + allowlist。

这样不会把工具边界讲混。

## 现场画图怎么画

可以画 MCP：

```text
pyagent.toml
  |
  v
MCPClient + StdioMCPTransport
  |
  v
initialize -> tools/list -> tools/call
  |
  v
MCPToolAdapter
  |
  v
ToolRegistry -> Safety -> Approval -> Audit
```

再画 Browser：

```text
User Goal
  |
  v
Browser Tool
  |-- static parser: inspect/dom/query/assert
  |-- optional Playwright: console/screenshot/network/interact
  |
  v
Local target policy
  |-- workspace file
  |-- file:// inside workspace
  |-- localhost / 127.0.0.1 / ::1
  |
  v
Observation / artifact / audit
```

## 必背 8 句

1. MCP 扩展工具来源，不扩展工具权限。
2. PyAgentCLI 当前 MCP 是最小 stdio tools slice，不是完整 MCP 平台。
3. MCP tool 注册后仍走 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger。
4. 没有 readOnlyHint 的 MCP tool 默认 NETWORK。
5. Browser Tools 先服务本地开发调试，不是任意网页浏览器。
6. Playwright 是 optional，因为浏览器依赖重，不应拖累核心 CLI。
7. screenshot 虽然是观察工具，但会写文件，所以输出限制到 `.pyagent/browser/`。
8. browser_interact 是 EXECUTE risk，因为点击和输入可能产生真实副作用。

## 一版完整回答

如果面试官问：

> 你们怎么做 MCP 和浏览器能力？

可以这样答：

> PyAgentCLI 里我把 MCP 和 Browser 都当成扩展 Agent 观察和工具能力的方式，但它们不能绕过本地安全执行层。MCP 当前实现的是最小 stdio tools slice：从 `pyagent.toml` 读取 server 命令，用 `StdioMCPTransport` 启动子进程，通过 JSON-RPC 完成 initialize、tools/list 和 tools/call，再用 `MCPToolAdapter` 把远程工具注册进本地 ToolRegistry，名字加 `mcp_<server>_<tool>` 前缀避免冲突。风险上 readOnlyHint 映射 READ，destructiveHint 映射 CRITICAL，openWorldHint 或无 annotation 默认 NETWORK，因此外部工具仍经过 SafetyPolicy、ApprovalHandler 和 AuditLogger。Browser 这块是 local-first：只允许 workspace file、workspace 内 file URL、localhost/127.0.0.1/::1，用于本地 HTML 和 localhost app 调试。静态工具可以做 inspect、DOM snapshot、简单 selector 和 assert；安装 optional Playwright 后可以收集 console logs、截图、network summary 和执行 interaction。screenshot 输出限制在 `.pyagent/browser/`，browser_interact 是 EXECUTE risk，需要审批。当前没有实现任意外网搜索、CDP 直连用户浏览器 profile 或 Safari 登录态自动化，这些是未来方向。

## 这一弹之后怎么复习

复习顺序：

1. 先读 [08 Browser Tools 和联网搜索](08_browser_search.md)。
2. 再读 [09 接入 MCP](09_mcp_integration.md)。
3. 再看源码：

```text
src/pyagentcli/mcp/client.py
src/pyagentcli/mcp/adapter.py
src/pyagentcli/tools/browser.py
src/pyagentcli/config.py
```

下一弹进入：

> Prompt 分层、Skill 系统、提示词工程
