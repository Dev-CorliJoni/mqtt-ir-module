from typing import Literal, Optional

from pydantic import BaseModel, Field


class SendRequest(BaseModel):
    button_id: int = Field(..., gt=0)
    mode: Literal["press", "hold"] = Field(...)
    hold_ms: Optional[int] = Field(default=None, gt=0, description="Required for mode=hold")
