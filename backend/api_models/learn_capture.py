from typing import Literal, Optional

from pydantic import BaseModel, Field


class LearnCapture(BaseModel):
    remote_id: int = Field(..., gt=0)
    mode: Literal["press", "hold"] = Field(...)

    takes: int = Field(default=5, gt=0, description="Number of takes (only used for mode=press)")
    timeout_ms: int = Field(default=3000, gt=0)
    overwrite: bool = Field(default=False)

    button_name: Optional[str] = Field(
        default=None,
        description=(
            "For mode=press: if omitted, the service auto-creates BTN_0001, BTN_0002, ...\n"
            "For mode=hold: if omitted, the service uses the last button captured in this session"
        ),
    )
