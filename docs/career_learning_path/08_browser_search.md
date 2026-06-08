# 08 Browser Tools 和联网搜索

这一篇对应 PaiCLI 学习路线里的浏览器能力、联网搜索和页面观察思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> PyAgentCLI 当前实现的是 local-first Browser Tools：服务本地 HTML、workspace file、localhost web app 和前端调试，不是任意外网浏览器，也不是通用爬虫。

联网搜索在当前项目里要分清边界：

- 已实现：`search_files`、`search_text`、`search_index`、RAG、本地页面 inspection。
- 已实现：localhost / file 页面 DOM、selector、assert、console、screenshot、network summary、interaction。
- 未实现：任意外部网页搜索、带登录态浏览外网、搜索引擎集成。

这个边界要讲清楚，否则很容易把 Browser Tools 说成不可控的“能上网”。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- 为什么 Coding Agent 需要浏览器能力。
- 为什么 PyAgentCLI 默认只允许 local browser target。
- `inspect_page`、`browser_dom_snapshot`、`browser_query_selector`、`browser_assert` 分别解决什么问题。
- 哪些工具需要 optional Playwright。
- 为什么 Playwright 不能作为默认依赖。
- `browser_interact` 为什么是 EXECUTE risk。
- screenshot 为什么限制输出到 `.pyagent/browser/`。
- network logs 为什么不记录 body 和 headers。
- Browser Tools 和 RAG/search 的关系。
- Safari 登录态 / Computer Use 和 PyAgentCLI browser tool 的区别。

## 为什么 Coding Agent 需要 Browser Tools

很多代码任务不是只改后端文件。

前端任务经常需要观察：

- 本地 HTML 页面。
- localhost web app。
- DOM 结构。
- 页面文本。
- 按钮和表单。
- console error。
- network request。
- 截图。
- 点击/输入后的状态变化。

如果 Agent 只能读源代码，就很难回答：

```text
页面上是否真的出现 Ready？
按钮点击后状态是否变化？
控制台有没有报错？
接口请求是否 200？
```

所以 Browser Tools 的目标是：

> 让 Coding Agent 能观察本地运行结果，而不是只根据源码猜 UI 状态。

## 为什么默认只允许 local

外部网页浏览风险更高：

- prompt injection。
- 登录态泄露。
- 网络副作用。
- 不可控内容。
- 数据外传。
- 版权和合规边界。
- 用户账号状态不透明。

PyAgentCLI 当前只允许：

```text
workspace-relative HTML paths
file:// URLs inside workspace
http://localhost:*
http://127.0.0.1:*
http://[::1]:*
```

默认拒绝：

```text
external HTTP/HTTPS URLs
file:// outside workspace
unsupported schemes
```

一句面试答案：

> Browser Tools 先服务本地开发调试，不把 Coding Agent 做成任意网页浏览器。

## PyAgentCLI 当前实现了什么

当前 Browser v0.5 工具：

- `inspect_page`
- `browser_dom_snapshot`
- `browser_query_selector`
- `browser_assert`
- `browser_console_logs`
- `browser_screenshot`
- `browser_network_logs`
- `browser_interact`
- `pyagent --check-browser`

当前 local search / RAG 工具：

- `search_files`
- `search_text`
- `search_index`
- `search_dependencies`

当前还没有落地的能力：

- 任意外部 web search。
- 搜索引擎 API。
- 带登录态外网浏览。
- 复杂浏览器 profile 管理。
- CDP 直连用户 Safari/Chrome 登录态。
- 外部 URL allowlist。
- 网络请求 body/header 采集。
- 跨站点自动操作。

所以最准确的表达是：

> PyAgentCLI 已实现本地页面观察和可选 Playwright 渲染能力，联网能力保持保守边界，后续可通过 allowlist、MCP 或专门 search provider 扩展。

## 最小运行例子

检查浏览器能力：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --check-browser
```

检查本地 HTML：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Inspect @site/index.html"
```

让 Agent 使用 browser tool：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Use browser_assert to check site/index.html contains READY"
```

安装 optional browser support：

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

运行 optional browser tests：

```bash
.venv/bin/python -m pytest tests/test_browser_playwright_optional.py
```

这些测试在 Playwright 或 Chromium 不可用时会 skip，而不是让核心测试套件失败。

## Browser 工具分工

### inspect_page

用途：

- 快速读本地 HTML 或 localhost 页面文本。
- 获取 URL、title、normalized text。
- 跳过 `script`、`style`、`noscript`。

它适合回答：

```text
页面大概显示了什么？
```

### browser_dom_snapshot

用途：

- 获取更 UI-oriented 的静态结构。

输出包括：

- title
- headings
- links
- controls
- text

它适合回答：

```text
页面有哪些标题、链接、按钮、输入框？
```

### browser_query_selector

用途：

- 对本地页面做简单 selector 查询。

当前支持：

```text
tag
#id
.class
```

当前拒绝：

```text
main .status
div > p
[data-testid=x]
复杂 CSS selector
```

为什么？

> 当前静态 fallback 是轻量 HTML parser，不是完整 CSS engine。复杂 selector 交给 Playwright 渲染路径或后续增强。

### browser_assert

用途：

- 自动验证页面是否满足条件。

支持检查：

- expected text。
- selector presence。
- expected status。

没有 Playwright 时：

- 对 workspace file 和 localhost HTML 使用 static fallback。
- 支持 tag / `#id` / `.class` selector。

有 Playwright 时：

- 等待页面渲染。
- 支持 JS 更新后的 DOM。
- 支持复杂 CSS selector。

这比单纯截图更适合 eval 和自动验收。

### browser_console_logs

用途：

- 收集本地页面 console logs。

要求：

- optional Playwright。

没有 Playwright：

```text
Playwright is not installed. Install optional browser dependencies to use this tool.
```

### browser_screenshot

用途：

- 截图本地页面。

要求：

- optional Playwright。
- output path 必须在 `.pyagent/browser/` 下。

为什么限制输出路径？

> screenshot 虽然是观察工具，但会写文件。只要写文件，就必须有路径边界。

### browser_network_logs

用途：

- 收集本地页面请求/响应摘要。

记录：

- method
- URL
- status
- resource type
- failure reason

不记录：

- request body
- response body
- headers

这是刻意保守设计。

网络日志用于调试请求是否发生、状态是否正确，不用于抓取敏感数据。

### browser_interact

用途：

- 对本地页面执行 click / type / fill / wait。

支持 actions：

```text
click
type
fill
wait
```

它是：

```text
RiskLevel.EXECUTE
```

所以必须走审批。

原因：

> 点击和输入会改变页面状态，可能触发请求、写入、提交表单，不能当成 read-only。

## Optional Playwright 设计

源码：

```text
src/pyagentcli/tools/browser.py
```

能力检查：

```text
check_browser_capabilities()
```

如果没装 Playwright：

```text
Playwright package: missing
Install optional browser support with `python -m pip install -e ".[browser]"`, then run `python -m playwright install chromium`.
```

为什么 optional？

- Playwright 包重。
- Chromium binary 重。
- CI 更复杂。
- 不是所有 Coding Agent 任务都需要浏览器。
- 核心 CLI 不应该被前端调试依赖拖慢。

所以 PyAgentCLI 的策略是：

```text
core CLI works without Playwright
static browser tools still available
rendered browser tools gracefully fail or skip
```

## URL 安全边界

源码：

```text
_prepare_local_url()
_prepare_browser_target()
```

workspace-relative path：

```text
site/index.html -> workspace/site/index.html
```

file URL：

```text
file:///workspace/site/index.html -> allowed
file:///Users/.../secret.html outside workspace -> denied
```

HTTP URL：

```text
http://localhost:3000 -> allowed
http://127.0.0.1:3000 -> allowed
http://[::1]:3000 -> allowed
https://example.com -> denied
```

所有 workspace path 都通过 SafetyPolicy。

这让 Browser Tools 和文件工具共享同一条安全边界。

## Browser 和 Search 的关系

本地 search / RAG 解决：

```text
代码在哪里？
symbol 定义在哪里？
哪些文件包含 READY？
```

Browser Tools 解决：

```text
页面现在显示什么？
DOM 里有没有这个 selector？
console 有没有报错？
network 有没有请求？
点击后状态有没有变化？
```

它们配合起来就是前端 Coding Agent 的闭环：

```text
search code
  -> edit files
  -> run local app
  -> browser_assert / console / network / screenshot
  -> reviewer suggests tests
```

## 和 Computer Use / Safari 登录态的区别

我们之前为了阅读 PaiCLI 登录态页面，尝试过 Computer Use / Safari。

这和 PyAgentCLI Browser Tools 不是同一个东西。

PyAgentCLI Browser Tools：

- 项目内实现。
- local-first。
- 不继承 Safari 登录态。
- 不控制用户真实浏览器窗口。
- 不读取外部网页登录 cookie。
- 通过 ToolRegistry 走 policy / approval / audit。

Computer Use / Safari：

- 是 Codex 协作环境的桌面自动化能力。
- 可能依赖前台窗口、Accessibility、屏幕状态。
- 可以受应用权限限制。
- 登录态只在用户真实浏览器里。
- 普通 HTTP fetch 不能继承 Safari 登录态。

我们遇到过的问题：

- Safari 能看到登录态，但普通网页抓取不能继承。
- Computer Use 有时能读 UI，但点击/滚动受窗口状态影响。
- Safari `do JavaScript` 需要额外 Apple Events 权限。
- Terminal 这类高风险 app 被 Computer Use 禁止操作。

这些经验说明：

> 浏览器能力要分清本地 tool、真实用户浏览器、桌面自动化和外部网络访问，不能混成一个“能看网页”。

## 源码阅读路线

建议按这个顺序看：

1. `docs/browser.md`
   - 先看 Browser v0.5 能力和边界。
2. `src/pyagentcli/tools/browser.py`
   - 看所有 browser tools。
   - 看 URL preparation。
   - 看 static HTML parser。
   - 看 optional Playwright loading。
3. `src/pyagentcli/tools/registry.py`
   - 看 browser tools 如何注册进 default registry。
4. `src/pyagentcli/cli/main.py`
   - 看 `--check-browser`。
5. `tests/test_tools.py`
   - 看 local URL 限制、DOM snapshot、selector、assert、screenshot path、interact approval。
6. `tests/test_browser_playwright_optional.py`
   - 看 Playwright success path 和 skip 逻辑。
7. `docs/career_learning_path/09_debug_pitfalls.md`
   - 看我们真实遇到的 browser / Computer Use / optional dependency 坑。

## 我们协作时真实遇到的坑

### 1. Safari 登录态不能被普通 fetch 继承

用户在 Safari 已登录 PaiCLI 页面。

但普通 web fetch 或命令行请求不会自动拥有 Safari cookie。

这说明：

> 登录态属于真实浏览器 session，不等于 Agent 的网络请求能力。

### 2. Computer Use 依赖前台窗口和权限

我们曾遇到：

- Safari 不是前台窗口时状态不稳定。
- 需要重新获取 app state。
- 点击/滚动可能受窗口状态影响。
- Terminal 被 Computer Use 明确禁止操作。

这说明桌面自动化不是稳定 API。

### 3. Playwright 不能放进默认依赖

Browser console、screenshot、network、interaction 都很有用。

但 Playwright 太重。

所以项目用了 optional extra：

```text
.[browser]
```

并提供：

```text
pyagent --check-browser
```

### 4. pytest.importorskip 的位置会影响 exit code

我们之前发现：

```text
module-level pytest.importorskip
```

可能导致单独运行 optional test 文件时出现不友好的 exit code。

后来改成在测试函数内部 importorskip。

学习点：

> 可选能力不仅要代码优雅降级，测试体验也要优雅降级。

### 5. Screenshot 不是纯 read-only

截图是观察页面，但会写文件。

所以必须限制：

```text
.pyagent/browser/
```

否则它可能变成任意写文件工具。

### 6. Network logs 不能记录太多

调试页面时 network logs 很有用。

但 body 和 headers 可能包含敏感信息。

PyAgentCLI 当前只记录摘要，不记录 body/header。

这是安全和实用之间的折中。

## 你自己开发时大概率会遇到的坑

### 1. 一开始就开放外部 URL

错误做法：

```text
browser.goto(any_url)
```

这会引入 prompt injection、数据泄露和登录态风险。

建议先做：

```text
workspace file
localhost
127.0.0.1
::1
```

### 2. 把 Browser Tool 当 read-only

并不是所有 browser 工具都是 read-only。

- inspect / DOM snapshot 是 READ。
- screenshot 会写文件。
- interact 会点击、输入、触发请求。
- network logs 可能观察敏感 URL。

风险等级要按真实副作用分。

### 3. Playwright 缺失时直接崩溃

如果用户没装 Playwright，工具应该返回清晰 failure。

不要让 import error 直接炸掉 Agent。

### 4. 不限制截图输出路径

任意 `output_path` 会变成写文件漏洞。

最低限度要限制到：

```text
.pyagent/browser/
```

### 5. 复杂 selector 在静态 parser 里假装支持

如果你没有 CSS selector engine，不要声称支持完整 CSS selector。

PyAgentCLI 静态 parser 只支持：

```text
tag
#id
.class
```

复杂 selector 要交给 Playwright 或后续实现。

### 6. 不区分静态 HTML 和渲染后 DOM

静态 HTML 看不到 JS 更新后的状态。

例如：

```text
setTimeout(() => app.textContent = "Ready")
```

只有 Playwright 渲染后才能看到。

所以 `browser_assert` 有 static fallback 和 Playwright mode 两种路径。

### 7. Network logs 记录 body/header

这很容易泄露 token、cookie、用户数据。

先记录摘要就够了：

```text
method, url, status, resource_type, failure
```

### 8. Interaction 没有审批

点击和输入可能触发真实副作用。

所以 `browser_interact` 必须是 EXECUTE risk，并且要有 preview。

### 9. 把真实浏览器登录态当成 Agent 能力

用户 Chrome/Safari 已登录，不代表你的 Agent tool 自动有登录态。

如果要接登录态，需要明确：

- 使用哪个浏览器 profile。
- cookie 如何授权。
- 是否允许读取页面内容。
- 是否允许点击。
- 审计如何记录。

### 10. 把 browser test 做成核心必需

如果 Browser 是 optional capability，核心测试不应该因为缺 Chromium 而失败。

optional tests 应该 skip，并保留能力诊断命令。

## 简历上怎么写

保守可信版：

> 为 PyAgentCLI 实现 local-first Browser Tools，支持 workspace HTML 与 localhost 页面 inspection、DOM snapshot、简单 selector 查询、页面断言、可选 Playwright console/screenshot/network/interaction，并通过 local URL allowlist、截图路径限制和 EXECUTE 审批控制浏览器工具风险。

更技术版：

> 设计浏览器工具安全边界：`inspect_page` / `browser_dom_snapshot` / `browser_query_selector` 使用静态 HTML parser 支持无 Playwright 的本地页面观察；`browser_assert` 在 Playwright 可用时验证渲染后 DOM，否则回退到静态断言；`browser_interact` 作为 EXECUTE 工具走审批，`browser_screenshot` 输出限制在 `.pyagent/browser/`，`browser_network_logs` 仅记录请求/响应摘要避免泄露 body/header。

不要这么写：

> 实现任意网页浏览、登录态网页操作和联网搜索 Agent。

除非后续真的实现外部 URL allowlist、登录态授权、搜索 provider、网络审计和更强安全策略。

## 面试官会怎么追问

### Q1：为什么 Coding Agent 需要 Browser Tools？

一句话答案：

> 因为前端任务需要观察页面运行结果，而不只是读源码。

展开回答：

- DOM 是否符合预期。
- 页面文本是否出现。
- console 是否报错。
- network 是否成功。
- 点击后状态是否变化。

### Q2：为什么默认只允许 local URL？

一句话答案：

> 外部网页有 prompt injection、登录态和数据泄露风险，PyAgentCLI 先服务本地开发调试。

展开回答：

- 允许 workspace file 和 localhost。
- 拒绝 external HTTP/HTTPS。
- file URL 必须在 workspace 内。
- 后续可加 allowlist。

### Q3：Playwright 为什么 optional？

一句话答案：

> 因为它重，而且不是所有 Coding Agent 任务都需要浏览器渲染。

展开回答：

- core CLI 不依赖 Playwright。
- static DOM tools 不需要 Playwright。
- console/screenshot/network/interact 需要 Playwright。
- `--check-browser` 诊断能力。

### Q4：DOM snapshot 和 screenshot 有什么区别？

一句话答案：

> DOM snapshot 是结构化文本，适合模型理解；screenshot 是视觉证据，适合人或视觉模型检查。

展开回答：

- DOM snapshot 可搜索、可进入 prompt。
- screenshot 需要 Playwright，并写文件。
- screenshot 输出必须限制路径。

### Q5：为什么 browser_interact 要审批？

一句话答案：

> 点击和输入会改变页面状态，可能触发请求或提交表单。

展开回答：

- 它是 EXECUTE risk。
- preview 展示 URL 和 actions。
- 通过 ToolRegistry 的 approval path。

### Q6：network logs 为什么不记录 body 和 headers？

一句话答案：

> body 和 headers 可能包含 token、cookie 或用户数据。

展开回答：

- 当前只记录摘要。
- 足够判断请求是否发生、状态是否成功。
- 更详细抓包需要额外审批和脱敏策略。

### Q7：为什么复杂 CSS selector 静态模式不支持？

一句话答案：

> 静态 parser 不是完整 CSS engine，不能假装支持。

展开回答：

- 当前支持 tag、id、class。
- Playwright mode 可以支持复杂 selector。
- 明确边界比错误匹配更好。

### Q8：PyAgentCLI 现在支持联网搜索吗？

一句话答案：

> 当前不支持任意外网搜索；它支持本地 search/RAG 和 local-first browser tools。

展开回答：

- `search_text/search_index` 是本地代码检索。
- Browser tools 只允许 local targets。
- 外部 web search 需要 provider、allowlist、审批和审计。
- 后续可以通过 MCP 或专门 search tool 扩展。

## 标准回答思路

如果面试官让你整体讲 Browser Tools，可以按这个顺序：

1. 先说明需求：前端任务需要观察页面运行结果。
2. 讲边界：local-first，不是任意外网浏览。
3. 讲工具分层：inspect、DOM、selector、assert、console、screenshot、network、interact。
4. 讲 optional Playwright：核心 CLI 不依赖，渲染能力可选。
5. 讲安全：URL allowlist、workspace path、screenshot path、interact approval。
6. 讲联网搜索边界：当前是 local search/RAG，外部搜索是后续扩展。
7. 讲开发坑：Playwright optional、importorskip、Safari 登录态、Computer Use 权限。

一版完整回答：

> PyAgentCLI 的 Browser Tools 是 local-first 设计，目标是帮助 Coding Agent 调试本地 HTML 和 localhost web app，而不是任意上网。当前支持 `inspect_page` 获取 title 和文本，`browser_dom_snapshot` 获取 headings/links/controls，`browser_query_selector` 做简单 tag/#id/.class 查询，`browser_assert` 验证 expected text、selector 和 status；如果安装了 optional Playwright，还能收集 console logs、截图、network summaries 和执行 click/type/fill/wait。安全上，只允许 workspace file、workspace 内 file URL、localhost/127.0.0.1/::1，外部 HTTP/HTTPS 默认拒绝；screenshot 输出限制在 `.pyagent/browser/`，`browser_interact` 是 EXECUTE risk，需要审批。当前不支持任意外网搜索，外部 search 需要后续通过 provider、allowlist、审批和审计扩展。

## 还能继续怎么增强

下一阶段可以增强：

- external URL allowlist。
- search provider tool。
- MCP web search adapter。
- browser trace artifact。
- screenshot diff。
- visual regression assertion。
- accessibility snapshot。
- richer selector support in static mode。
- authenticated browser profile with explicit approval。
- CDP integration。
- network body capture with redaction and approval。
- browser eval fixtures。

更工程化的方向：

- Browser tools 写 trace provenance。
- Reviewer 读取 browser_assert 结果。
- Eval 增加 browser task success cases。
- Screenshot artifact 加 metadata。
- Localhost server health check。

## 这一篇之后做什么

下一篇进入：

> [MCP 接入](09_mcp_integration.md)

Browser Tools 解决的是本地页面观察；MCP 解决的是如何把外部工具生态接入 PyAgentCLI，同时仍然复用本地 ToolRegistry、安全策略、审批和审计。
