from pyagentcli.agent.plan_store import PlanStore
from pyagentcli.agent.planner import PlanPreview, PlanRun, PlanRunStatus, PlanStep
from pyagentcli.cli.main import (
    _review_plan_execution,
    build_agent,
    check_browser,
    compress_memory,
    delete_memory_line,
    enrich_goal,
    execute_planned_task,
    index_workspace,
    list_skills,
    list_plans,
    parse_args,
    plan_task,
    remember_note,
    resume_plan,
    retry_step,
    run_evals,
    run_agent_task,
    set_step_status,
    show_memory,
    show_stale_memory,
    show_plan,
)
from pyagentcli.rag.indexer import CodeIndexer


def test_parse_execute_plan_flag() -> None:
    args = parse_args(["--execute-plan", "fix", "tests"])

    assert args.execute_plan is True
    assert args.goal == ["fix", "tests"]


def test_build_agent_uses_executor_role_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / "pyagent.toml").write_text(
        """
[agents.executor]
system_prompt = "Executor role prompt from project config."
""".strip(),
        encoding="utf-8",
    )

    agent = build_agent(workspace=str(tmp_path), interactive=False, role="executor")

    assert agent.system_prompt == "Executor role prompt from project config."


def test_parse_memory_flags() -> None:
    memory_args = parse_args(["--memory"])
    remember_args = parse_args(["--remember", "Use focused edits."])
    compress_args = parse_args(["--compress-memory"])
    delete_args = parse_args(["--delete-memory-line", "3"])
    stale_args = parse_args(["--stale-memory-days", "30"])
    eval_args = parse_args(["--eval"])
    eval_real_model_args = parse_args(["--eval", "--eval-real-model"])
    skills_args = parse_args(["--list-skills"])
    browser_args = parse_args(["--check-browser"])

    assert memory_args.memory is True
    assert remember_args.remember == "Use focused edits."
    assert compress_args.compress_memory is True
    assert delete_args.delete_memory_line == 3
    assert stale_args.stale_memory_days == 30
    assert eval_args.eval is True
    assert eval_real_model_args.eval is True
    assert eval_real_model_args.eval_real_model is True
    assert skills_args.list_skills is True
    assert browser_args.check_browser is True


def test_check_browser_outputs_status() -> None:
    result = check_browser()

    assert "Browser capability status:" in result
    assert "Playwright package:" in result


def test_execute_planned_task_non_interactive_does_not_execute(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = execute_planned_task(
        "change README",
        workspace=str(tmp_path),
        interactive=False,
    )

    assert "Plan:" in result
    assert "PlanRun status: planned" in result
    assert "Plan id:" in result
    assert "requires interactive approval" in result
    assert "Executing approved plan" not in result


def test_execute_planned_task_warns_when_index_is_stale(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    target = tmp_path / "README.md"
    target.write_text("Project status: TODO\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()
    target.write_text("Project status: READY\n", encoding="utf-8")

    result = execute_planned_task(
        "change README",
        workspace=str(tmp_path),
        interactive=False,
    )

    assert "Index freshness warning" in result
    assert "README.md" in result
    assert "Run `pyagent --index`" in result


def test_index_workspace_uses_hash_embedding_config(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / "README.md").write_text("Project status READY\n", encoding="utf-8")
    (tmp_path / "pyagent.toml").write_text(
        """
[rag.embeddings]
provider = "hash"
dimensions = 8
""".strip(),
        encoding="utf-8",
    )

    result = index_workspace(workspace=str(tmp_path))

    assert "vectors" in result
    assert "0 vectors" not in result


def test_plan_task_persists_and_show_plan_loads_it(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = plan_task("change README", workspace=str(tmp_path))

    plan_id_line = next(line for line in result.splitlines() if line.startswith("Plan id: "))
    plan_id = plan_id_line.removeprefix("Plan id: ")
    shown = show_plan(plan_id, workspace=str(tmp_path))

    assert "PlanRun status: planned" in result
    assert "Agent handoffs:" in result
    assert "planner: Produced structured execution plan" in result
    assert "Goal: change README" in shown
    assert plan_id in shown


def test_list_plans_shows_persisted_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    plan_task("change README", workspace=str(tmp_path))

    result = list_plans(workspace=str(tmp_path))

    assert "Plans:" in result
    assert "planned" in result
    assert "change README" in result


def test_list_plans_empty_workspace(tmp_path) -> None:
    assert list_plans(workspace=str(tmp_path)) == "No plans found."


def test_resume_plan_non_interactive_does_not_execute(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    plan_output = plan_task("change README", workspace=str(tmp_path))
    plan_id = next(line for line in plan_output.splitlines() if line.startswith("Plan id: ")).removeprefix("Plan id: ")

    result = resume_plan(plan_id, workspace=str(tmp_path), interactive=False)

    assert "PlanRun status: planned" in result
    assert "requires interactive approval" in result


def test_resume_plan_warns_when_index_is_stale(tmp_path) -> None:
    target = tmp_path / "README.md"
    target.write_text("Project status: TODO\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()
    target.write_text("Project status: READY\n", encoding="utf-8")
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_stale_resume",
            goal="resume task",
            status=PlanRunStatus.PLANNED,
            plan=PlanPreview(summary="Resume", steps=[]),
        )
    )

    result = resume_plan(saved.plan_id or "", workspace=str(tmp_path), interactive=False)

    assert "Index freshness warning" in result
    assert "README.md" in result


def test_resume_plan_refuses_success_status(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_done",
            goal="done task",
            status=PlanRunStatus.SUCCESS,
            plan=PlanPreview(summary="Done", steps=[]),
        )
    )

    result = resume_plan(saved.plan_id or "", workspace=str(tmp_path), interactive=False)

    assert "PlanRun status: success" in result
    assert "cannot be resumed" in result


def test_execute_plan_help_flag_exists() -> None:
    args = parse_args(["--resume-plan", "plan_123"])

    assert args.resume_plan == "plan_123"


def test_parse_retry_step_flag() -> None:
    args = parse_args(["--retry-step", "plan_123", "S2"])

    assert args.retry_step == ["plan_123", "S2"]


def test_parse_step_edit_flags() -> None:
    set_args = parse_args(["--set-step-status", "plan_123", "S2", "skipped"])
    skip_args = parse_args(["--skip-step", "plan_123", "S2"])

    assert set_args.set_step_status == ["plan_123", "S2", "skipped"]
    assert skip_args.skip_step == ["plan_123", "S2"]


def test_retry_step_non_interactive_resets_step_and_following_steps(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_retry",
            goal="retry task",
            status=PlanRunStatus.FAILED,
            plan=PlanPreview(
                summary="Retry",
                steps=[
                    PlanStep(id="S1", title="Read", description="Read.", status="success", result_summary="done"),
                    PlanStep(id="S2", title="Edit", description="Edit.", status="failed", result_summary="bad"),
                    PlanStep(id="S3", title="Verify", description="Verify.", status="success", result_summary="old"),
                ],
            ),
        )
    )

    result = retry_step(saved.plan_id or "", "S2", workspace=str(tmp_path), interactive=False)
    reloaded = store.load(saved.plan_id or "")

    assert "Step retry requires interactive approval" in result
    assert [step.status for step in reloaded.plan.steps] == ["success", "pending", "pending"]
    assert reloaded.plan.steps[0].result_summary == "done"
    assert reloaded.plan.steps[1].result_summary is None
    assert reloaded.plan.steps[2].result_summary is None


def test_retry_step_warns_when_index_is_stale(tmp_path) -> None:
    target = tmp_path / "README.md"
    target.write_text("Project status: TODO\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()
    target.write_text("Project status: READY\n", encoding="utf-8")
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_stale_retry",
            goal="retry task",
            status=PlanRunStatus.FAILED,
            plan=PlanPreview(
                summary="Retry",
                steps=[PlanStep(id="S1", title="Edit", description="Edit.", status="failed")],
            ),
        )
    )

    result = retry_step(saved.plan_id or "", "S1", workspace=str(tmp_path), interactive=False)

    assert "Index freshness warning" in result
    assert "README.md" in result


def test_retry_step_reports_missing_step(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_retry_missing",
            goal="retry task",
            status=PlanRunStatus.FAILED,
            plan=PlanPreview(summary="Retry", steps=[]),
        )
    )

    result = retry_step(saved.plan_id or "", "S99", workspace=str(tmp_path), interactive=False)

    assert "Step not found: S99" in result


def test_set_step_status_updates_persisted_plan(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_status",
            goal="status task",
            status=PlanRunStatus.FAILED,
            plan=PlanPreview(
                summary="Status",
                steps=[PlanStep(id="S1", title="Read", description="Read.", status="failed")],
            ),
        )
    )

    result = set_step_status(saved.plan_id or "", "S1", "success", workspace=str(tmp_path))
    reloaded = store.load(saved.plan_id or "")

    assert "PlanRun status: planned" in result
    assert reloaded.plan.steps[0].status == "success"


def test_skip_step_marks_step_skipped(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_skip",
            goal="skip task",
            status=PlanRunStatus.PLANNED,
            plan=PlanPreview(
                summary="Skip",
                steps=[PlanStep(id="S1", title="Optional", description="Optional.")],
            ),
        )
    )

    result = set_step_status(
        saved.plan_id or "",
        "S1",
        "skipped",
        workspace=str(tmp_path),
        result_summary="Skipped by user.",
    )
    reloaded = store.load(saved.plan_id or "")

    assert "[skipped] Optional" in result
    assert reloaded.plan.steps[0].status == "skipped"
    assert reloaded.plan.steps[0].result_summary == "Skipped by user."


def test_review_gate_blocks_successful_plan_with_skipped_step(tmp_path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_gate",
            goal="update docs",
            status=PlanRunStatus.SUCCESS,
            execution_result="S1 ok\nS2 skipped",
            plan=PlanPreview(
                summary="Gate",
                steps=[
                    PlanStep(id="S1", title="Read", description="Read.", risk="READ", status="success"),
                    PlanStep(id="S2", title="Edit", description="Edit.", risk="WRITE", status="skipped"),
                ],
            ),
        )
    )

    reviewed = _review_plan_execution(tmp_path, store, saved)

    assert reviewed.status == PlanRunStatus.FAILED
    assert reviewed.review_result is not None
    assert "Gate: block" in reviewed.review_result
    assert "Retry proposal:" in reviewed.review_result
    assert reviewed.handoffs[-1].role == "reviewer"
    assert reviewed.handoffs[-1].status == "blocked"
    assert reviewed.handoffs[-1].next_action == "user_decision"


def test_set_step_status_rejects_invalid_status(tmp_path) -> None:
    result = set_step_status("plan_missing", "S1", "weird", workspace=str(tmp_path))

    assert "Invalid step status" in result


def test_enrich_goal_loads_context_reference(tmp_path) -> None:
    (tmp_path / "README.md").write_text("Demo context\n", encoding="utf-8")

    enriched = enrich_goal("Summarize @README.md", workspace=str(tmp_path))

    assert "Demo context" in enriched
    assert "User-provided context references" in enriched


def test_enrich_goal_loads_project_memory(tmp_path) -> None:
    remember_note("Project prefers focused tests.", workspace=str(tmp_path))

    enriched = enrich_goal("Run tests", workspace=str(tmp_path))

    assert "Project memory follows" in enriched
    assert "Project prefers focused tests." in enriched


def test_enrich_goal_loads_skill_context(tmp_path) -> None:
    skill_dir = tmp_path / ".pyagent" / "skills" / "python-testing"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("skill.toml").write_text(
        """
name = "python-testing"
description = "Python testing workflow."
triggers = ["pytest"]
enabled = true
""".strip(),
        encoding="utf-8",
    )
    skill_dir.joinpath("SKILL.md").write_text("Run focused pytest before finishing.", encoding="utf-8")

    enriched = enrich_goal("Please run pytest", workspace=str(tmp_path))

    assert "Skill guidance follows" in enriched
    assert "Python testing workflow." in enriched
    assert "Run focused pytest before finishing." in enriched


def test_list_skills_outputs_enabled_local_skills(tmp_path) -> None:
    skill_dir = tmp_path / ".pyagent" / "skills" / "python-testing"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("skill.toml").write_text(
        """
name = "python-testing"
description = "Python testing workflow."
triggers = ["pytest"]
enabled = true
""".strip(),
        encoding="utf-8",
    )
    skill_dir.joinpath("SKILL.md").write_text("Run focused pytest before finishing.", encoding="utf-8")

    result = list_skills(workspace=str(tmp_path))

    assert "Skills:" in result
    assert "python-testing" in result
    assert "pytest" in result


def test_show_and_remember_memory(tmp_path) -> None:
    remember_result = remember_note("Use edit_file for small edits.", workspace=str(tmp_path))
    memory_result = show_memory(workspace=str(tmp_path))

    assert "Remembered note" in remember_result
    assert "Use edit_file for small edits." in memory_result


def test_memory_review_delete_and_compress_cli_helpers(tmp_path) -> None:
    remember_note("Use edit_file for small edits.", workspace=str(tmp_path))

    delete_result = delete_memory_line(3, workspace=str(tmp_path))
    stale_result = show_stale_memory(0, workspace=str(tmp_path))
    compress_result = compress_memory(workspace=str(tmp_path))

    assert "Deleted memory line 3" in delete_result
    assert "No project memory notes" in stale_result
    assert "No sessions to compress" in compress_result


def test_run_agent_task_records_session_memory(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = run_agent_task("hello", workspace=str(tmp_path), interactive=False)
    memory_result = show_memory(workspace=str(tmp_path))

    assert "本地 fallback" in result
    assert "Recent sessions:" in memory_result
    assert "hello" in memory_result


def test_run_evals_outputs_summary(tmp_path) -> None:
    result = run_evals(workspace=str(tmp_path))

    assert "Eval summary:" in result
    assert "4/4 passed" in result
    assert "diff accuracy 100%" in result
    assert "tools.registry" in result
    assert "Trace eval:" in result
    assert "trace.update_readme_status" in result
    assert "Reviewer eval:" in result
    assert "reviewer.failed_step" in result
    assert "proposal=retry_step" in result
    assert "Real model trace eval: disabled (enable with --eval-real-model)." in result


def test_run_evals_real_model_without_api_key_is_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = run_evals(workspace=str(tmp_path), include_real_model_trace=True)

    assert "Real model trace eval: disabled (OPENAI_API_KEY is not configured)." in result
    assert "real_model_trace.list_workspace" not in result


def test_index_workspace_builds_index(tmp_path) -> None:
    (tmp_path / "README.md").write_text("hello index\n", encoding="utf-8")

    result = index_workspace(workspace=str(tmp_path))

    assert "Indexed 1 files" in result
    assert (tmp_path / ".pyagent" / "index.sqlite").exists()
