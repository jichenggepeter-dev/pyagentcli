import os
from pathlib import Path

from pyagentcli.config import load_config


def test_load_config_reads_dotenv_without_overriding_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PYAGENT_MODEL", "from-env")
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY='from-dotenv'\nPYAGENT_MODEL=from-dotenv\nPYAGENT_MAX_STEPS=4\n",
        encoding="utf-8",
    )

    config = load_config(interactive=False)

    assert config.api_key == "from-dotenv"
    assert config.model == "from-env"
    assert config.max_steps == 4
    assert os.environ["OPENAI_API_KEY"] == "from-dotenv"


def test_load_config_reads_project_mcp_servers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyagent.toml").write_text(
        """
[mcp.servers.docs]
command = ["python", "docs_server.py"]
enabled = true

[mcp.servers.disabled]
command = ["python", "disabled.py"]
enabled = false
""".strip(),
        encoding="utf-8",
    )

    config = load_config(interactive=False)

    assert len(config.mcp_servers) == 2
    assert config.mcp_servers[0].name == "docs"
    assert config.mcp_servers[0].command == ("python", "docs_server.py")
    assert config.mcp_servers[0].enabled is True
    assert config.mcp_servers[1].enabled is False


def test_load_config_reads_embedding_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyagent.toml").write_text(
        """
[rag.embeddings]
provider = "openai-compatible"
model = "text-embedding-3-small"
base_url = "https://example.test/v1"
api_key_env = "PYAGENT_EMBEDDING_API_KEY"
dimensions = 24
""".strip(),
        encoding="utf-8",
    )

    config = load_config(interactive=False)

    assert config.embedding.provider == "openai-compatible"
    assert config.embedding.model == "text-embedding-3-small"
    assert config.embedding.base_url == "https://example.test/v1"
    assert config.embedding.api_key_env == "PYAGENT_EMBEDDING_API_KEY"
    assert config.embedding.dimensions == 24


def test_load_config_reads_agent_role_configs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyagent.toml").write_text(
        """
[agents.planner]
model = "planner-model"
system_prompt = "Plan with tiny safe steps."

[agents.executor]
model = "executor-model"
system_prompt = "Execute only the approved step."

[agents.reviewer]
model = "reviewer-model"
system_prompt = "Review conservatively."
""".strip(),
        encoding="utf-8",
    )

    config = load_config(interactive=False)

    assert config.role_config("planner").model == "planner-model"
    assert config.role_config("planner").system_prompt == "Plan with tiny safe steps."
    assert config.role_config("executor").model == "executor-model"
    assert config.role_config("reviewer").system_prompt == "Review conservatively."
    assert config.role_config("missing").model is None


def test_load_config_reads_eval_model_comparison_configs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyagent.toml").write_text(
        """
[evals.model_comparison.models.fast]
model = "gpt-4.1-mini"
base_url = "https://api.example.test/v1"
api_key_env = "FAST_MODEL_API_KEY"

[evals.model_comparison.models.reasoning]
model = "gpt-4.1"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(interactive=False)

    assert len(config.eval_models) == 2
    assert config.eval_models[0].name == "fast"
    assert config.eval_models[0].model == "gpt-4.1-mini"
    assert config.eval_models[0].base_url == "https://api.example.test/v1"
    assert config.eval_models[0].api_key_env == "FAST_MODEL_API_KEY"
    assert config.eval_models[1].name == "reasoning"
    assert config.eval_models[1].base_url == "https://api.openai.com/v1"
    assert config.eval_models[1].api_key_env == "OPENAI_API_KEY"
