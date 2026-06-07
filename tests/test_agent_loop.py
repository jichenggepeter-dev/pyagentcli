from pathlib import Path

from pyagentcli.agent.loop import AgentLoop
from pyagentcli.llm.openai_compatible import LocalFallbackClient
from pyagentcli.safety.approval import ApprovalHandler
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyPolicy
from pyagentcli.tools.base import ToolContext
from pyagentcli.tools.registry import default_registry


def test_local_fallback_agent_lists_workspace(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    safety_policy = SafetyPolicy(tmp_path)
    approval_handler = ApprovalHandler(interactive=False)
    audit_logger = AuditLogger(tmp_path)

    def context_factory(*, goal: str, step: int) -> ToolContext:
        return ToolContext(
            workspace_root=tmp_path,
            safety_policy=safety_policy,
            approval_handler=approval_handler,
            audit_logger=audit_logger,
            goal=goal,
            step=step,
        )

    agent = AgentLoop(
        llm=LocalFallbackClient(),
        tools=default_registry(),
        tool_context_factory=context_factory,
        max_steps=3,
    )

    answer = agent.run("总结这个项目")
    assert "README.md" in answer


def test_agent_loop_can_capture_trace(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    safety_policy = SafetyPolicy(tmp_path)
    approval_handler = ApprovalHandler(interactive=False)
    audit_logger = AuditLogger(tmp_path)

    def context_factory(*, goal: str, step: int) -> ToolContext:
        return ToolContext(
            workspace_root=tmp_path,
            safety_policy=safety_policy,
            approval_handler=approval_handler,
            audit_logger=audit_logger,
            goal=goal,
            step=step,
        )

    agent = AgentLoop(
        llm=LocalFallbackClient(),
        tools=default_registry(),
        tool_context_factory=context_factory,
        max_steps=3,
    )

    result = agent.run_with_trace("总结这个项目")
    trace = result.trace.to_eval_trace()

    assert "README.md" in result.output
    assert result.trace.goal == "总结这个项目"
    assert trace[0]["role"] == "user"
    assert any(event.get("tool_call", {}).get("name") == "list_files" for event in trace)
    assert any(event.get("role") == "tool" and event.get("tool_name") == "list_files" for event in trace)
    assert trace[-1]["role"] == "assistant"
    assert "README.md" in trace[-1]["final"]
