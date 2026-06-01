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
