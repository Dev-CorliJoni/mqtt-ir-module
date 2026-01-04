from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LogEntry:
    timestamp: float
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None
