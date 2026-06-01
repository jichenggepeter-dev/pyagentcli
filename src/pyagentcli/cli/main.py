from __future__ import annotations

import argparse

from pyagentcli.agent.loop import AgentLoop
from pyagentcli.agent.plan_executor import PlanExecutor
from pyagentcli.agent.plan_store import PlanStore
from pyagentcli.agent.planner import VALID_STEP_STATUSES, PlanRun, PlanRunStatus, Planner
from pyagentcli.agent.reviewer import Reviewer
from pyagentcli.cli.repl import run_repl
from pyagentcli.config import load_config
from pyagentcli.context_injection import inject_context_references
from pyagentcli.evals.runner import EvalRunner
from pyagentcli.llm.base import Message
from pyagentcli.llm.model_config import build_llm_client
from pyagentcli.llm.openai_compatible import LocalFallbackClient
from pyagentcli.memory.project_memory import ProjectMemory
from pyagentcli.rag.indexer import CodeIndexer
from pyagentcli.safety.approval import ApprovalHandler
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyPolicy
from pyagentcli.tools.base import ToolContext
from pyagentcli.tools.registry import default_registry


def build_agent(*, workspace: str | None = None, interactive: bool = True) -> AgentLoop:
    config = load_config(workspace=workspace, interactive=interactive)
    safety_policy = SafetyPolicy(config.workspace_root)
    approval_handler = ApprovalHandler(interactive=config.interactive)
    audit_logger = AuditLogger(config.workspace_root)
    tools = default_registry()
    llm = build_llm_client(config)

    def context_factory(*, goal: str, step: int) -> ToolContext:
        return ToolContext(
            workspace_root=config.workspace_root,
            safety_policy=safety_policy,
            approval_handler=approval_handler,
            audit_logger=audit_logger,
            goal=goal,
            step=step,
        )

    return AgentLoop(
        llm=llm,
        tools=tools,
        tool_context_factory=context_factory,
        max_steps=config.max_steps,
    )


def enrich_goal(goal: str, *, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    enriched = inject_context_references(goal, config.workspace_root).enriched_goal
    memory_block = ProjectMemory(config.workspace_root).format_context_block()
    if not memory_block:
        return enriched
    return f"{enriched}\n\n{memory_block}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pyagent",
        description="Local Python AI coding agent CLI.",
    )
    parser.add_argument("goal", nargs="*", help="Task for the agent. Omit to start REPL.")
    parser.add_argument("--workspace", "-w", help="Workspace root. Defaults to current directory.")
    parser.add_argument(
        "--no-input",
        action="store_true",
        help="Non-interactive mode. Approval-gated tools are denied unless policy allows them.",
    )
    parser.add_argument(
        "--check-model",
        action="store_true",
        help="Send a tiny tool-calling probe to the configured model.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Preview a plan for the task without executing tools.",
    )
    parser.add_argument(
        "--execute-plan",
        action="store_true",
        help="Preview a plan, ask for approval, then execute the task.",
    )
    parser.add_argument(
        "--show-plan",
        metavar="PLAN_ID",
        help="Show a persisted plan by id.",
    )
    parser.add_argument(
        "--list-plans",
        action="store_true",
        help="List persisted plans in the workspace.",
    )
    parser.add_argument(
        "--resume-plan",
        metavar="PLAN_ID",
        help="Resume a persisted planned or failed plan after approval.",
    )
    parser.add_argument(
        "--retry-step",
        nargs=2,
        metavar=("PLAN_ID", "STEP_ID"),
        help="Reset one step and following steps to pending, then resume after approval.",
    )
    parser.add_argument(
        "--set-step-status",
        nargs=3,
        metavar=("PLAN_ID", "STEP_ID", "STATUS"),
        help="Set a persisted plan step status.",
    )
    parser.add_argument(
        "--skip-step",
        nargs=2,
        metavar=("PLAN_ID", "STEP_ID"),
        help="Mark a persisted plan step as skipped.",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Rebuild the local SQLite FTS workspace index.",
    )
    parser.add_argument(
        "--memory",
        action="store_true",
        help="Show project memory and recent session summaries.",
    )
    parser.add_argument(
        "--remember",
        metavar="NOTE",
        help="Append a note to project memory.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run the built-in local evaluation harness.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    goal = " ".join(args.goal).strip()
    interactive = not args.no_input and not goal
    if goal:
        interactive = not args.no_input

    if args.check_model:
        check_model(workspace=args.workspace)
        return

    if args.index:
        print(index_workspace(workspace=args.workspace))
        return

    if args.memory:
        print(show_memory(workspace=args.workspace))
        return

    if args.remember:
        print(remember_note(args.remember, workspace=args.workspace))
        return

    if args.eval:
        print(run_evals(workspace=args.workspace))
        return

    if args.show_plan:
        print(show_plan(args.show_plan, workspace=args.workspace))
        return

    if args.list_plans:
        print(list_plans(workspace=args.workspace))
        return

    if args.resume_plan:
        print(resume_plan(args.resume_plan, workspace=args.workspace, interactive=not args.no_input))
        return

    if args.retry_step:
        plan_id, step_id = args.retry_step
        print(retry_step(plan_id, step_id, workspace=args.workspace, interactive=not args.no_input))
        return

    if args.set_step_status:
        plan_id, step_id, status = args.set_step_status
        print(set_step_status(plan_id, step_id, status, workspace=args.workspace))
        return

    if args.skip_step:
        plan_id, step_id = args.skip_step
        print(set_step_status(plan_id, step_id, "skipped", workspace=args.workspace, result_summary="Skipped by user."))
        return

    if args.execute_plan:
        if not goal:
            raise SystemExit("--execute-plan requires a task.")
        print(execute_planned_task(goal, workspace=args.workspace, interactive=not args.no_input))
        return

    if args.plan:
        if not goal:
            raise SystemExit("--plan requires a task.")
        print(plan_task(goal, workspace=args.workspace))
        return

    if goal:
        print(run_agent_task(goal, workspace=args.workspace, interactive=interactive))
        return
    agent = build_agent(workspace=args.workspace, interactive=interactive)
    run_repl(agent, goal_transform=lambda user_goal: enrich_goal(user_goal, workspace=args.workspace))


def check_model(*, workspace: str | None = None) -> None:
    config = load_config(workspace=workspace, interactive=False)
    tools = default_registry()
    llm = build_llm_client(config)
    if isinstance(llm, LocalFallbackClient):
        print("No OPENAI_API_KEY configured. Local fallback is active; real tool calling was not checked.")
        return

    response = llm.chat(
        [
            Message.system(
                "You are checking whether tool calling works. "
                "Call list_files with path '.' and do not answer directly."
            ),
            Message.user("Use the list_files tool for the current workspace."),
        ],
        tools.schemas(),
    )
    if response.tool_calls:
        for call in response.tool_calls:
            print(f"tool_call: {call.name} args={call.arguments}")
        return
    print(f"No tool call returned. Model answered: {response.content}")


def index_workspace(*, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    return CodeIndexer(config.workspace_root).rebuild().format_text()


def show_memory(*, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    return ProjectMemory(config.workspace_root).format_memory()


def remember_note(note: str, *, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    return ProjectMemory(config.workspace_root).remember(note)


def run_evals(*, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    summary, results, report_path = EvalRunner(workspace_root=config.workspace_root).run_builtin()
    lines = [summary.format_text(), f"Report: {report_path}", ""]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"{status} {result.case_id}: {result.name} ({result.duration_ms} ms)")
        if not result.passed:
            lines.append(f"  {result.message}")
    return "\n".join(lines).rstrip()


def run_agent_task(goal: str, *, workspace: str | None = None, interactive: bool = True) -> str:
    config = load_config(workspace=workspace, interactive=interactive)
    enriched_goal = enrich_goal(goal, workspace=workspace)
    agent = build_agent(workspace=workspace, interactive=interactive)
    result = agent.run(enriched_goal)
    ProjectMemory(config.workspace_root).record_session(
        goal=goal,
        mode="agent",
        status="completed",
        result=result,
        audit_goal=enriched_goal,
    )
    return result


def plan_task(goal: str, *, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    planner = Planner(build_llm_client(config))
    store = PlanStore(config.workspace_root)
    enriched_goal = inject_context_references(goal, config.workspace_root).enriched_goal
    run = store.save(
        PlanRun(
            plan_id=None,
            goal=goal,
            plan=planner.preview(enriched_goal),
            status=PlanRunStatus.PLANNED,
        )
    )
    return run.format_text()


def execute_planned_task(goal: str, *, workspace: str | None = None, interactive: bool = True) -> str:
    config = load_config(workspace=workspace, interactive=False)
    planner = Planner(build_llm_client(config))
    store = PlanStore(config.workspace_root)
    enriched_goal = inject_context_references(goal, config.workspace_root).enriched_goal
    plan = planner.preview(enriched_goal)
    planned_run = store.save(
        PlanRun(
            plan_id=None,
            goal=goal,
            plan=plan,
            status=PlanRunStatus.PLANNED,
        )
    )
    plan_text = _with_index_freshness_warning(planned_run.format_text(), config.workspace_root)

    if not interactive:
        return (
            f"{plan_text}\n\n"
            "Plan execution requires interactive approval. Re-run without --no-input to execute."
        )

    answer = input(f"{plan_text}\n\nExecute this plan? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        cancelled = store.save(
            PlanRun(
                plan_id=planned_run.plan_id,
                goal=goal,
                plan=plan,
                status=PlanRunStatus.CANCELLED,
                created_at=planned_run.created_at,
            )
        )
        return cancelled.format_text()

    executor = PlanExecutor(
        store=store,
        agent_factory=lambda: build_agent(workspace=workspace, interactive=True),
        approval_handler=ApprovalHandler(interactive=True),
    )
    completed = executor.execute(planned_run)
    completed = _review_plan_execution(config.workspace_root, store, completed)
    _record_plan_memory(config.workspace_root, completed)
    return completed.format_text()


def show_plan(plan_id: str, *, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    store = PlanStore(config.workspace_root)
    return store.load(plan_id).format_text()


def list_plans(*, workspace: str | None = None) -> str:
    config = load_config(workspace=workspace, interactive=False)
    store = PlanStore(config.workspace_root)
    runs = store.list_runs()
    if not runs:
        return "No plans found."

    lines = ["Plans:"]
    for run in runs:
        plan_id = run.plan_id or "<unknown>"
        updated_at = run.updated_at or run.created_at or "<unknown time>"
        status = str(run.status)
        goal = (run.goal or "").replace("\n", " ")
        if len(goal) > 80:
            goal = goal[:77] + "..."
        lines.append(f"{plan_id}  {status}  {updated_at}  {goal}")
    return "\n".join(lines)


def resume_plan(plan_id: str, *, workspace: str | None = None, interactive: bool = True) -> str:
    config = load_config(workspace=workspace, interactive=False)
    store = PlanStore(config.workspace_root)
    run = store.load(plan_id)
    current = _with_index_freshness_warning(run.format_text(), config.workspace_root)

    if run.status not in {PlanRunStatus.PLANNED, PlanRunStatus.FAILED}:
        return f"{current}\n\nPlan cannot be resumed from status: {run.status}"

    if not run.goal:
        return f"{current}\n\nPlan cannot be resumed because it has no saved goal."

    if not interactive:
        return f"{current}\n\nPlan resume requires interactive approval. Re-run without --no-input to execute."

    answer = input(f"{current}\n\nResume this plan? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        cancelled = store.save(
            PlanRun(
                plan_id=run.plan_id,
                goal=run.goal,
                plan=run.plan,
                status=PlanRunStatus.CANCELLED,
                execution_result=run.execution_result,
                created_at=run.created_at,
            )
        )
        return cancelled.format_text()

    executor = PlanExecutor(
        store=store,
        agent_factory=lambda: build_agent(workspace=workspace, interactive=True),
        approval_handler=ApprovalHandler(interactive=True),
    )
    completed = executor.execute(run)
    completed = _review_plan_execution(config.workspace_root, store, completed)
    _record_plan_memory(config.workspace_root, completed)
    return completed.format_text()


def retry_step(
    plan_id: str,
    step_id: str,
    *,
    workspace: str | None = None,
    interactive: bool = True,
) -> str:
    config = load_config(workspace=workspace, interactive=False)
    store = PlanStore(config.workspace_root)
    run = store.load(plan_id)

    if not run.goal:
        return f"{run.format_text()}\n\nPlan cannot be retried because it has no saved goal."

    try:
        retry_plan = run.plan.with_retry_from_step(step_id)
    except ValueError as exc:
        return f"{run.format_text()}\n\n{exc}"

    retry_run = store.save(
        PlanRun(
            plan_id=run.plan_id,
            goal=run.goal,
            plan=retry_plan,
            status=PlanRunStatus.PLANNED,
            execution_result=run.execution_result,
            created_at=run.created_at,
        )
    )
    current = _with_index_freshness_warning(retry_run.format_text(), config.workspace_root)

    if not interactive:
        return f"{current}\n\nStep retry requires interactive approval. Re-run without --no-input to execute."

    answer = input(f"{current}\n\nRetry from step {step_id}? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        cancelled = store.save(
            PlanRun(
                plan_id=retry_run.plan_id,
                goal=retry_run.goal,
                plan=retry_run.plan,
                status=PlanRunStatus.CANCELLED,
                execution_result=retry_run.execution_result,
                created_at=retry_run.created_at,
            )
        )
        return cancelled.format_text()

    executor = PlanExecutor(
        store=store,
        agent_factory=lambda: build_agent(workspace=workspace, interactive=True),
        approval_handler=ApprovalHandler(interactive=True),
    )
    completed = executor.execute(retry_run)
    completed = _review_plan_execution(config.workspace_root, store, completed)
    _record_plan_memory(config.workspace_root, completed)
    return completed.format_text()


def set_step_status(
    plan_id: str,
    step_id: str,
    status: str,
    *,
    workspace: str | None = None,
    result_summary: str | None = None,
) -> str:
    normalized_status = status.lower()
    if normalized_status not in VALID_STEP_STATUSES:
        valid = ", ".join(sorted(VALID_STEP_STATUSES))
        return f"Invalid step status: {status}. Valid statuses: {valid}"

    config = load_config(workspace=workspace, interactive=False)
    store = PlanStore(config.workspace_root)
    run = store.load(plan_id)
    summary = result_summary
    if summary is None and normalized_status in {"skipped", "cancelled"}:
        summary = f"Marked {normalized_status} by user."

    try:
        updated_plan = run.plan.with_updated_step(
            step_id,
            status=normalized_status,
            result_summary=summary,
        )
    except ValueError as exc:
        return f"{run.format_text()}\n\n{exc}"

    updated = store.save(
        PlanRun(
            plan_id=run.plan_id,
            goal=run.goal,
            plan=updated_plan,
            status=PlanRunStatus.PLANNED,
            execution_result=run.execution_result,
            created_at=run.created_at,
        )
    )
    return updated.format_text()


def _with_index_freshness_warning(text: str, workspace_root) -> str:
    stale_paths = CodeIndexer(workspace_root).stale_paths()
    if not stale_paths:
        return text
    stale = ", ".join(stale_paths[:10])
    if len(stale_paths) > 10:
        stale += ", ..."
    warning = (
        "Index freshness warning: the local search index may be stale for: "
        f"{stale}. Run `pyagent --index` before executing if this task depends on retrieval."
    )
    return f"{text}\n\n{warning}"


def _record_plan_memory(workspace_root, run: PlanRun) -> None:
    ProjectMemory(workspace_root).record_session(
        goal=run.goal or "",
        mode="plan",
        status=str(run.status),
        result=run.review_result or run.execution_result or run.format_text(),
        plan_id=run.plan_id,
    )


def _review_plan_execution(workspace_root, store: PlanStore, run: PlanRun) -> PlanRun:
    report = Reviewer(workspace_root).review_plan(run)
    return store.save(
        PlanRun(
            plan_id=run.plan_id,
            goal=run.goal,
            plan=run.plan,
            status=run.status,
            execution_result=run.execution_result,
            review_result=report.format_text(),
            created_at=run.created_at,
        )
    )


if __name__ == "__main__":
    main()
