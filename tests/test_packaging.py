import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_pyproject() -> dict:
    return tomllib.loads(ROOT.joinpath("pyproject.toml").read_text(encoding="utf-8"))


def test_project_metadata_is_release_ready() -> None:
    project = load_pyproject()["project"]

    assert project["name"] == "pyagentcli"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    assert project["readme"] == "README.md"
    assert project["description"]


def test_console_script_entrypoint_is_declared() -> None:
    project = load_pyproject()["project"]

    assert project["scripts"]["pyagent"] == "pyagentcli.cli.main:main"
    assert ROOT.joinpath("src", "pyagentcli", "__main__.py").exists()


def test_readme_quick_start_mentions_install_and_console_script() -> None:
    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")

    assert 'python -m pip install -e ".[dev]"' in readme
    assert "pyagent --help" in readme
