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
