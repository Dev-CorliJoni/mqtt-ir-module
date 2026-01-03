from dataclasses import dataclass


@dataclass(frozen=True)
class LearnSession:
    device_id: int
    device_name: str
    lirc_name: str
    expires_at: float
    data_conf_path: str
    etc_conf_path: str
    