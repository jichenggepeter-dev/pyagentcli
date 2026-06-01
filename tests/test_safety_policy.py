from pathlib import Path

import pytest

from pyagentcli.safety.policy import SafetyAction, SafetyPolicy
from pyagentcli.tools.base import RiskLevel


def test_resolve_workspace_path_allows_inside_workspace(tmp_path: Path) -> None:
    policy = SafetyPolicy(tmp_path)
    resolved = policy.resolve_workspace_path("notes/example.md")
    assert resolved == tmp_path / "notes" / "example.md"


def test_resolve_workspace_path_blocks_escape(tmp_path: Path) -> None:
    policy = SafetyPolicy(tmp_path)
    with pytest.raises(PermissionError):
        policy.resolve_workspace_path("../outside.txt")


def test_resolve_workspace_path_blocks_env(tmp_path: Path) -> None:
    policy = SafetyPolicy(tmp_path)
    with pytest.raises(PermissionError):
        policy.resolve_workspace_path(".env")


def test_shell_dangerous_command_is_denied(tmp_path: Path) -> None:
    policy = SafetyPolicy(tmp_path)
    decision = policy.evaluate_tool("run_shell", RiskLevel.EXECUTE, {"command": "rm -rf ."})
    assert decision.action == SafetyAction.DENY


def test_read_tool_is_allowed(tmp_path: Path) -> None:
    policy = SafetyPolicy(tmp_path)
    decision = policy.evaluate_tool("read_file", RiskLevel.READ, {"path": "README.md"})
    assert decision.action == SafetyAction.ALLOW

