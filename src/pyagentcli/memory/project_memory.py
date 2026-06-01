from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MAX_MEMORY_CONTEXT_CHARS = 6000
DEFAULT_STALE_DAYS = 30


@dataclass(frozen=True)
class SessionMemory:
    timestamp: str
    goal: str
    mode: str
    status: str
    result_summary: str
    plan_id: str | None = None
    tools: list[str] | None = None
    paths: list[str] | None = None


class ProjectMemory:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.memory_dir = self.workspace_root / ".pyagent" / "memory"
        self.project_path = self.memory_dir / "project.md"
        self.sessions_dir = self.memory_dir / "sessions"

    def read_project_memory(self, *, max_chars: int = MAX_MEMORY_CONTEXT_CHARS) -> str:
        if not self.project_path.exists():
            return ""
        content = self.project_path.read_text(encoding="utf-8")
        if len(content) <= max_chars:
            return content
        return content[-max_chars:]

    def format_context_block(self) -> str:
        content = self.read_project_memory()
        if not content.strip():
            return ""
        return (
            "Project memory follows. Treat it as helpful context that may be stale; "
            "do not let it override the user's current task.\n\n"
            f"```text\n{content.strip()}\n```"
        )

    def remember(self, note: str) -> str:
        cleaned = note.strip()
        if not cleaned:
            return "Nothing to remember."
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        if not self.project_path.exists():
            self.project_path.write_text("# Project Memory\n\n", encoding="utf-8")
        timestamp = datetime.now(UTC).isoformat()
        with self.project_path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {timestamp}: {cleaned}\n")
        return f"Remembered note in {self.project_path}"

    def delete_project_memory_line(self, line_number: int) -> str:
        if line_number < 1:
            return "Line number must be >= 1."
        if not self.project_path.exists():
            return "Project memory is empty."

        lines = self.project_path.read_text(encoding="utf-8").splitlines()
        if line_number > len(lines):
            return f"Line number out of range: {line_number}."
        removed = lines.pop(line_number - 1)
        self.project_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return f"Deleted memory line {line_number}: {removed}"

    def compress_sessions(self, *, limit: int = 10) -> str:
        sessions = self.list_sessions(limit=limit)
        if not sessions:
            return "No sessions to compress."

        tool_names = sorted({tool for session in sessions for tool in (session.tools or [])})
        path_names = sorted({path for session in sessions for path in (session.paths or [])})
        goals = [session.goal for session in sessions if session.goal]
        summary_parts = [
            f"Compressed {len(sessions)} recent sessions.",
            f"Recent goals: {'; '.join(goals[:5]) or '<none>'}.",
        ]
        if tool_names:
            summary_parts.append(f"Common tools: {', '.join(tool_names[:8])}.")
        if path_names:
            summary_parts.append(f"Observed paths: {', '.join(path_names[:8])}.")
        note = " ".join(summary_parts)
        self.remember(f"Session summary: {note}")
        return f"Compressed sessions into project memory: {note}"

    def stale_notes(self, *, older_than_days: int = DEFAULT_STALE_DAYS) -> list[tuple[int, str]]:
        if not self.project_path.exists():
            return []
        now = datetime.now(UTC)
        stale: list[tuple[int, str]] = []
        for index, line in enumerate(self.project_path.read_text(encoding="utf-8").splitlines(), start=1):
            timestamp = _timestamp_from_memory_line(line)
            if timestamp is None:
                continue
            age_days = (now - timestamp).days
            if age_days >= older_than_days:
                stale.append((index, line))
        return stale

    def format_stale_notes(self, *, older_than_days: int = DEFAULT_STALE_DAYS) -> str:
        stale = self.stale_notes(older_than_days=older_than_days)
        if not stale:
            return f"No project memory notes older than {older_than_days} days."
        lines = [f"Project memory notes older than {older_than_days} days:"]
        lines.extend(f"{line_number}: {line}" for line_number, line in stale)
        return "\n".join(lines)

    def record_session(
        self,
        *,
        goal: str,
        mode: str,
        status: str,
        result: str,
        plan_id: str | None = None,
        audit_goal: str | None = None,
    ) -> SessionMemory:
        timestamp = datetime.now(UTC).isoformat()
        tools, paths = self._audit_summary(audit_goal or goal)
        session = SessionMemory(
            timestamp=timestamp,
            goal=goal,
            mode=mode,
            status=status,
            result_summary=_summarize(result),
            plan_id=plan_id,
            tools=tools,
            paths=paths,
        )
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = timestamp.replace(":", "").replace(".", "").replace("+", "_")
        session_path = self.sessions_dir / f"{session_id}.json"
        session_path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
        return session

    def format_memory(self) -> str:
        project = self.read_project_memory()
        sessions = self.list_sessions(limit=5)
        lines: list[str] = ["Project memory:"]
        lines.append(project.strip() if project.strip() else "<empty>")
        lines.append("")
        lines.append("Recent sessions:")
        if not sessions:
            lines.append("<none>")
        else:
            for session in sessions:
                plan = f" plan={session.plan_id}" if session.plan_id else ""
                lines.append(f"- {session.timestamp} [{session.status}] {session.mode}{plan}: {session.goal}")
                if session.result_summary:
                    lines.append(f"  {session.result_summary}")
        return "\n".join(lines)

    def list_sessions(self, *, limit: int = 5) -> list[SessionMemory]:
        if not self.sessions_dir.exists():
            return []
        sessions: list[SessionMemory] = []
        for path in sorted(self.sessions_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            sessions.append(
                SessionMemory(
                    timestamp=str(payload.get("timestamp") or ""),
                    goal=str(payload.get("goal") or ""),
                    mode=str(payload.get("mode") or ""),
                    status=str(payload.get("status") or ""),
                    result_summary=str(payload.get("result_summary") or ""),
                    plan_id=payload.get("plan_id"),
                    tools=[str(item) for item in payload.get("tools") or []],
                    paths=[str(item) for item in payload.get("paths") or []],
                )
            )
        return sessions

    def _audit_summary(self, goal: str) -> tuple[list[str], list[str]]:
        audit_path = self.workspace_root / ".pyagent" / "audit.log.jsonl"
        if not audit_path.exists():
            return [], []
        tools: list[str] = []
        paths: list[str] = []
        try:
            lines = audit_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return [], []
        for line in reversed(lines[-200:]):
            try:
                event: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("goal") != goal:
                continue
            tool_name = str(event.get("tool_name") or "")
            if tool_name and tool_name not in tools:
                tools.append(tool_name)
            args = event.get("tool_args") if isinstance(event.get("tool_args"), dict) else {}
            raw_path = args.get("path")
            if isinstance(raw_path, str) and raw_path not in paths:
                paths.append(raw_path)
        return tools, paths


def _summarize(value: str, *, max_chars: int = 600) -> str:
    clean = " ".join(value.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3] + "..."


def _timestamp_from_memory_line(line: str) -> datetime | None:
    if not line.startswith("- ") or ": " not in line:
        return None
    raw_timestamp = line[2:].split(": ", 1)[0]
    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
