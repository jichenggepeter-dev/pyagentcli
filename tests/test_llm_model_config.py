from pyagentcli.config import AppConfig, AgentRoleConfig
from pyagentcli.llm.model_config import build_llm_client
from pyagentcli.llm.openai_compatible import OpenAICompatibleClient


def test_build_llm_client_uses_role_model_override(tmp_path) -> None:
    config = AppConfig(
        workspace_root=tmp_path,
        model="default-model",
        api_key="test-key",
        base_url="https://example.test/v1",
        max_steps=3,
        interactive=False,
        agent_roles=(AgentRoleConfig(role="planner", model="planner-model"),),
    )

    client = build_llm_client(config, role="planner")

    assert isinstance(client, OpenAICompatibleClient)
    assert client.model == "planner-model"


def test_build_llm_client_falls_back_to_default_model_for_missing_role(tmp_path) -> None:
    config = AppConfig(
        workspace_root=tmp_path,
        model="default-model",
        api_key="test-key",
        base_url="https://example.test/v1",
        max_steps=3,
        interactive=False,
    )

    client = build_llm_client(config, role="executor")

    assert isinstance(client, OpenAICompatibleClient)
    assert client.model == "default-model"
