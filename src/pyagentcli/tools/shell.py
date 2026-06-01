from __future__ import annotations

import subprocess
from typing import Any

from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema


class RunShellTool:
    name = "run_shell"
    description = "Run a shell command in the workspace and return stdout, stderr, and exit code."
    risk_level = RiskLevel.EXECUTE

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to run in the workspace.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Command timeout in seconds. Defaults to 30.",
                    },
                },
                "required": ["command"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        command = str(args.get("command") or "")
        if not command:
            return ToolResult.failure("Missing required argument: command")
        timeout = args.get("timeout_seconds", 30)
        try:
            timeout_seconds = max(1, min(int(timeout), 300))
        except (TypeError, ValueError):
            timeout_seconds = 30

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=context.workspace_root,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult.failure(
                f"Command timed out after {timeout_seconds} seconds.",
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )

        content = (
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        if completed.returncode == 0:
            return ToolResult.success(content, exit_code=completed.returncode)
        return ToolResult.failure(
            f"Command exited with code {completed.returncode}.",
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

