from dataclasses import dataclass, field
from typing import List, Optional

from .log_entry import LogEntry


@dataclass
class LearningSession:
    remote_id: int
    remote_name: str
    agent_id: str
    extend: bool
    started_at: float
    next_button_index: int
    last_button_id: Optional[int] = None
    last_button_name: Optional[str] = None
    logs: List[LogEntry] = field(default_factory=list)
