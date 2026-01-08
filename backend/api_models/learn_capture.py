from typing import Literal, Optional

from pydantic import BaseModel, Field


class LearnCapture(BaseModel):
    remote_id: int = Field(..., gt=0)
    mode: Literal["press", "hold"] = Field(...)

    takes: Optional[int] = Field(default=None, gt=0, description="Number of takes (only used for mode=press). If omitted, uses settings default.")
    timeout_ms: Optional[int] = Field(default=None, gt=0, description="Capture timeout in ms. If omitted, uses settings default.")
    overwrite: bool = Field(default=False)

    button_name: Optional[str] = Field(
        default=None,
        description=(
            "For mode=press: if omitted, the service auto-creates BTN_0001, BTN_0002, ...\n"
            "For mode=hold: if omitted, the service uses the last button captured in this session"
        ),
    )
