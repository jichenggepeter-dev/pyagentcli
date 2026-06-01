from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pyagentcli.agent.planner import PlanRun


class PlanStore:
    def __init__(self, workspace_root: Path) -> None:
        self.plans_dir = workspace_root / ".pyagent" / "plans"

    def save(self, run: PlanRun) -> PlanRun:
        now = datetime.now(UTC).isoformat()
        plan_id = run.plan_id or self._new_plan_id()
        created_at = run.created_at or now
        updated = replace(run, plan_id=plan_id, created_at=created_at, updated_at=now)

        self.plans_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(plan_id)
        path.write_text(
            json.dumps(updated.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return updated

    def load(self, plan_id: str) -> PlanRun:
        path = self.path_for(plan_id)
        if not path.exists():
            raise FileNotFoundError(f"Plan not found: {plan_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return PlanRun.from_dict(payload)

    def list_runs(self) -> list[PlanRun]:
        if not self.plans_dir.exists():
            return []

        runs: list[PlanRun] = []
        for path in self.plans_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                runs.append(PlanRun.from_dict(payload))
            except (json.JSONDecodeError, OSError, ValueError):
                continue

        return sorted(runs, key=lambda run: run.updated_at or run.created_at or "", reverse=True)

    def path_for(self, plan_id: str) -> Path:
        safe_id = plan_id.replace("/", "_").replace("..", "_")
        return self.plans_dir / f"{safe_id}.json"

    @staticmethod
    def _new_plan_id() -> str:
        return f"plan_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
