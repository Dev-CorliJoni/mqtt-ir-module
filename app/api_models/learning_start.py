from typing import Optional
from pydantic import BaseModel


class LearnStart(BaseModel):
    device_name: str
    timeout_s: Optional[int] = None
    