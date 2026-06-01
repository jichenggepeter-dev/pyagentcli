# Interview Guide

This guide is the interview narrative for PyAgentCLI.

## 60-Second Pitch

PyAgentCLI is a local Python AI Coding Agent CLI that I designed and implemented from scratch. It is closer to a mini Claude Code or Codex CLI than a chatbot: it can inspect a local workspace, call tools, edit files, run commands with approval, retrieve code context, remember project facts, plan execution steps, review results, and run local evals.

The architecture is split into Agent Loop, LLM Client, Tool Registry, Safety Policy, RAG, Memory, Planner, Reviewer, and Eval Harness. The key design principle is that the model should propose actions, but all real-world actions go through typed tools, risk policy, human approval, and audit logs.

The project demonstrates how to turn a language model into a safer developer agent by combining tool calling, retrieval, memory, review, and evaluation instead of relying on prompting alone.

## Architecture Story

The flow is:

```text
CLI / REPL
  -> goal enrichment
    -> @file / @folder / @symbol context
    -> project memory
  -> Agent Loop
    -> LLM Client
    -> Tool Registry
      -> Safety Policy
      -> Approval
      -> Audit Log
  -> Plan / Reviewer / Eval
```

This separation matters because a coding agent touches real files and commands. The LLM does not directly mutate the workspace. It emits tool calls, and the local runtime decides whether those calls are allowed.

## Key Technical Decisions

### Why Tool Calling Instead Of Free-Form ReAct Text?

Tool Calling provides structured tool names and JSON arguments, which are easier to validate and audit. ReAct is still useful conceptually, but the executable layer should be typed and policy-controlled.

### Why Human Approval?

Coding agents can write files and execute commands. A wrong command can delete files, leak secrets, or mutate the environment. PyAgentCLI classifies tools by risk and asks for approval on write and execute operations.

### Why SQLite FTS Before Embeddings?

Code retrieval often starts with exact signals: file names, symbols, config keys, error messages, test names. SQLite FTS is deterministic, local, fast, auditable, and works before adding embedding infrastructure.

### Why Python AST Symbol Chunking?

Line-window chunks are simple but can cut across function boundaries. AST-based chunks let `@project_status` map directly to a function, class, or method. This improves context precision for coding tasks.

### Why Deterministic Reviewer First?

The first reviewer should be predictable. It can inspect plan risks, step statuses, audit logs, tools, and paths without another model call. A model-backed reviewer can be added later.

### Why Deterministic Eval First?

Before evaluating model intelligence, I wanted to ensure the platform substrate works: tools are registered, safety denies dangerous commands, RAG symbol search works, and memory persists notes.

## Common Interview Questions

### ReAct vs Function Calling

ReAct is a reasoning pattern: think, act, observe. Function Calling is an execution protocol: the model returns a structured tool call. In this project, Tool Calling powers execution, while the loop still follows a ReAct-like observe-and-continue cycle.

### How Do You Prevent Infinite Loops?

The current implementation has a max-step limit. The next improvements would be repeated-call detection, per-tool failure counters, command timeouts, and an explicit blocked state when the model cannot make progress.

### What Happens If A Tool Fails?

Tool failures are returned as observations instead of crashing the loop. The model can decide to retry, inspect another file, or stop. The registry also handles unknown tools and invalid preview failures.

### How Do You Keep The Agent Safe?

All tools have risk levels. Paths are resolved inside the workspace. Shell commands go through deny patterns and approval. Writes show previews. Audit logs record tool name, args, risk, decision, result, and duration.

### What Is Memory Used For?

Memory stores project-level notes and session summaries. It is injected as context, not as higher-priority instruction. This helps the agent avoid repeated discovery while keeping the user’s current task authoritative.

### How Would You Add MCP?

I would implement an MCP client, fetch remote tool schemas, adapt each MCP tool to the local `Tool` protocol, assign risk levels, and route execution through the same Safety, Approval, and Audit layers.

### How Would You Add Browser Tools?

I would add Playwright-backed tools such as `open_page`, `click`, `type`, `screenshot`, and `inspect_dom`, then classify them as read/network/execute risk depending on action.

### How Do You Measure Success?

There are two levels. Platform evals check deterministic capabilities. Model-backed evals should use fixture workspaces, expected file diffs, expected tool calls, task success, safety violations, and approval count.

## Strong Closing Statement

The point of PyAgentCLI is not just “calling an LLM from a CLI.” The point is building the runtime around the model: typed tools, retrieval, memory, planning, review, safety, and evals. That runtime is what turns model output into a usable coding agent.
