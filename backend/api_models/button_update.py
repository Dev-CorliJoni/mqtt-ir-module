from pydantic import BaseModel, Field


class ButtonUpdate(BaseModel):
    name: str = Field(..., min_length=1)
