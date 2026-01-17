from pathlib import Path
from typing import Optional
import uuid

AGENT_ID_RELATIVE_PATH = Path("agent") / "agent_id"


def get_or_create_agent_id(data_dir: str) -> str:
    data_dir = (data_dir or "").strip()
    if not data_dir:
        raise ValueError("data_dir must not be empty")

    id_path = Path(data_dir) / AGENT_ID_RELATIVE_PATH
    existing = _read_agent_id(id_path)
    if existing:
        return existing

    agent_id = str(uuid.uuid4())
    _write_agent_id(id_path, agent_id)
    return agent_id


def _read_agent_id(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Failed to read agent id file at {path}") from exc
    return value or None


def _write_agent_id(path: Path, agent_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(f"{agent_id}\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to write agent id file at {path}") from exc
