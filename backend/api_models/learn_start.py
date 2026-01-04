from pydantic import BaseModel, Field


class LearnStart(BaseModel):
    remote_id: int = Field(..., gt=0)
    extend: bool = Field(default=False, description="If false: delete existing buttons/signals for the remote")
