from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    workspace_root: Path
    model: str
    api_key: str | None
    base_url: str
    max_steps: int
    interactive: bool = True


def load_config(workspace: str | None = None, *, interactive: bool = True) -> AppConfig:
    load_dotenv(Path.cwd() / ".env")
    workspace_value = workspace or os.getenv("PYAGENT_WORKSPACE") or "."
    workspace_root = Path(workspace_value).expanduser().resolve()
    load_dotenv(workspace_root / ".env")
    max_steps_raw = os.getenv("PYAGENT_MAX_STEPS", "10")
    try:
        max_steps = int(max_steps_raw)
    except ValueError:
        max_steps = 10

    return AppConfig(
        workspace_root=workspace_root,
        model=os.getenv("PYAGENT_MODEL", "gpt-4.1-mini"),
        api_key=os.getenv("OPENAI_API_KEY") or None,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        max_steps=max_steps,
        interactive=interactive,
    )


def load_dotenv(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _normalize_env_value(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
