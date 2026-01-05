from typing import Optional

from pydantic import BaseModel, Field


class ButtonUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    icon: Optional[str] = Field(default=None, description="MDI icon key (UI)")
    