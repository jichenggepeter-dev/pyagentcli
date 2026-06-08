from pathlib import Path

from pyagentcli.evals.runner import EvalRunner
from pyagentcli.llm.base import LLMResponse, Message, ToolCall


class FakeTraceLLM:
    def __init__(self) -> None:
        self.calls = 0

    def chat(self, messages: list[Message], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content=None,
                tool_calls=[ToolCall(id="fake_list", name="list_files", arguments={"path": "."})],
            )
        return LLMResponse(content="I inspected the workspace and found README.md.")


def test_eval_runner_runs_builtin_cases(tmp_path: Path) -> None:
    (
        summary,
        results,
        report_path,
        coding_summary,
        coding_results,
        rag_summary,
        rag_results,
        retriever_comparison_summary,
        retriever_comparison_results,
        browser_assertion_summary,
        browser_assertion_results,
        trace_summary,
        trace_results,
        reviewer_summary,
        reviewer_results,
        real_model_trace_summary,
        real_model_trace_results,
        model_trace_comparison_summary,
        model_trace_comparison_results,
        reviewer_proposal_comparison_summary,
        reviewer_proposal_comparison_results,
    ) = EvalRunner(
        workspace_root=tmp_path
    ).run_builtin()

    assert summary.total == 4
    assert summary.failed == 0
    assert all(result.passed for result in results)
    assert coding_summary.total == 1
    assert coding_summary.succeeded == 1
    assert coding_summary.tool_call_accuracy == 1.0
    assert coding_summary.diff_accuracy == 1.0
    assert coding_summary.safety_violations == 0
    assert all(result.succeeded for result in coding_results)
    assert coding_results[0].expected_diffs == 1
    assert coding_results[0].matched_diffs == 1
    assert rag_summary.total == 3
    assert rag_summary.failed == 0
    assert all(result.passed for result in rag_results)
    assert retriever_comparison_summary.total == 4
    assert retriever_comparison_summary.enabled == 3
    assert retriever_comparison_summary.disabled == 1
    assert retriever_comparison_summary.failed == 0
    assert {result.retriever_name for result in retriever_comparison_results} == {
        "exact",
        "vector-hash",
        "hybrid-hash",
        "vector-disabled",
    }
    assert all(result.passed for result in retriever_comparison_results if result.enabled)
    assert any(
        result.disabled_reason == "embedding provider is not configured"
        for result in retriever_comparison_results
        if not result.enabled
    )
    assert browser_assertion_summary.total == 2
    assert browser_assertion_summary.failed == 0
    assert browser_assertion_summary.expected_denials == 1
    assert all(result.passed for result in browser_assertion_results)
    assert {result.case_id for result in browser_assertion_results} == {
        "browser_assertion.local_static_pass",
        "browser_assertion.external_url_denied",
    }
    assert trace_summary.total == 2
    assert trace_summary.failed == 0
    assert trace_summary.tool_call_accuracy == 1.0
    assert trace_summary.safety_violations == 0
    assert all(result.passed for result in trace_results)
    assert reviewer_summary.total == 3
    assert reviewer_summary.failed == 0
    assert reviewer_summary.gate_matches == 3
    assert reviewer_summary.proposal_matches == 3
    assert all(result.passed for result in reviewer_results)
    proposal_actions = {result.case_id: result.proposal_action for result in reviewer_results}
    assert proposal_actions["reviewer.success_plan"] is None
    assert proposal_actions["reviewer.failed_step"] == "retry_step"
    assert proposal_actions["reviewer.skipped_step"] == "user_decision"
    assert real_model_trace_summary.enabled is False
    assert real_model_trace_summary.total == 0
    assert real_model_trace_results == []
    assert model_trace_comparison_summary.enabled is False
    assert model_trace_comparison_summary.total == 0
    assert model_trace_comparison_results == []
    assert reviewer_proposal_comparison_summary.total == 3
    assert reviewer_proposal_comparison_summary.failed == 0
    assert reviewer_proposal_comparison_summary.matched == 1
    assert reviewer_proposal_comparison_summary.mismatched == 2
    assert all(result.passed for result in reviewer_proposal_comparison_results)
    comparison_by_id = {result.case_id: result for result in reviewer_proposal_comparison_results}
    assert comparison_by_id["reviewer_proposal_compare.matched_retry"].matched is True
    assert comparison_by_id["reviewer_proposal_compare.mismatched_action"].model_action == "accept"
    assert comparison_by_id["reviewer_proposal_compare.invalid_json"].model_action == "inspect"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "tools.registry" in report_text
    assert "coding.update_readme_status" in report_text
    assert "rag_retrieval.typescript_symbol" in report_text
    assert "trace.update_readme_status" in report_text
    assert "agent_trace.list_workspace" in report_text
    assert "reviewer.failed_step" in report_text
    assert '"kind": "coding_task"' in report_text
    assert '"matched_diffs": 1' in report_text
    assert '"kind": "rag_retrieval"' in report_text
    assert '"kind": "retriever_comparison"' in report_text
    assert '"retriever_name": "hybrid-hash"' in report_text
    assert '"retriever_name": "vector-disabled"' in report_text
    assert '"kind": "browser_assertion"' in report_text
    assert "browser_assertion.external_url_denied" in report_text
    assert '"kind": "trace_eval"' in report_text
    assert '"kind": "reviewer_eval"' in report_text
    assert '"kind": "reviewer_proposal_comparison"' in report_text
    assert "reviewer_proposal_compare.invalid_json" in report_text
    assert '"kind": "real_model_trace_eval"' not in report_text
    assert '"kind": "model_trace_comparison"' not in report_text


def test_eval_runner_runs_opt_in_real_model_trace_with_fake_llm(tmp_path: Path) -> None:
    fake_llm = FakeTraceLLM()
    (
        *_,
        real_model_trace_summary,
        real_model_trace_results,
        model_trace_comparison_summary,
        model_trace_comparison_results,
        reviewer_proposal_comparison_summary,
        reviewer_proposal_comparison_results,
    ) = EvalRunner(workspace_root=tmp_path).run_builtin(
        include_real_model_trace=True,
        real_model_llm=fake_llm,
    )

    assert fake_llm.calls == 2
    assert real_model_trace_summary.enabled is True
    assert real_model_trace_summary.total == 1
    assert real_model_trace_summary.failed == 0
    assert real_model_trace_summary.tool_call_accuracy == 1.0
    assert len(real_model_trace_results) == 1
    assert real_model_trace_results[0].passed is True
    assert real_model_trace_results[0].used_tools == ["list_files"]
    assert model_trace_comparison_summary.enabled is False
    assert model_trace_comparison_results == []
    assert reviewer_proposal_comparison_summary.total == 3
    assert len(reviewer_proposal_comparison_results) == 3
    report_files = sorted((tmp_path / ".pyagent" / "evals").glob("eval_*.jsonl"))
    assert report_files
    report_text = report_files[-1].read_text(encoding="utf-8")
    assert '"kind": "real_model_trace_eval"' in report_text
    assert "real_model_trace.list_workspace" in report_text


def test_eval_runner_runs_per_model_trace_comparison_with_fake_llms(tmp_path: Path) -> None:
    fast_llm = FakeTraceLLM()
    careful_llm = FakeTraceLLM()
    (
        *_,
        model_trace_comparison_summary,
        model_trace_comparison_results,
        reviewer_proposal_comparison_summary,
        reviewer_proposal_comparison_results,
    ) = EvalRunner(workspace_root=tmp_path).run_builtin(
        model_trace_comparison_llms={
            "fast": fast_llm,
            "careful": careful_llm,
        },
    )

    assert fast_llm.calls == 2
    assert careful_llm.calls == 2
    assert model_trace_comparison_summary.enabled is True
    assert model_trace_comparison_summary.total == 2
    assert model_trace_comparison_summary.model_count == 2
    assert model_trace_comparison_summary.failed == 0
    assert model_trace_comparison_summary.tool_call_accuracy == 1.0
    assert model_trace_comparison_summary.safety_violations == 0
    assert {result.model_name for result in model_trace_comparison_results} == {"fast", "careful"}
    assert all(result.passed for result in model_trace_comparison_results)
    assert reviewer_proposal_comparison_summary.total == 3
    assert len(reviewer_proposal_comparison_results) == 3
    report_files = sorted((tmp_path / ".pyagent" / "evals").glob("eval_*.jsonl"))
    assert report_files
    report_text = report_files[-1].read_text(encoding="utf-8")
    assert '"kind": "model_trace_comparison"' in report_text
    assert '"model_name": "fast"' in report_text
    assert '"model_name": "careful"' in report_text
